import re
from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import (
    db,
    User,
    Income,
    Expense,
    Budget,
    SavingsGoal,
    FinancialReport,
    USER_TYPES,
    DEFAULT_EXPENSE_CATEGORIES,
    DEFAULT_INCOME_SOURCES,
)
from services.financial_analyzer import (
    calculate_total_income,
    calculate_total_expenses,
    calculate_savings,
    calculate_savings_rate,
    get_dashboard_summary,
    get_budget_status,
)
from services.report_generator import generate_monthly_report_data, save_financial_report
from services.ai_engine import generate_ai_insights, answer_financial_query
from app.services.ai_advisor_service import (
    CATEGORY_TIPS,
    GOAL_DESCRIPTIONS,
    build_prompt,
    extract_json,
    analyze_finances_with_gemini,
    generate_product_content,
)

api_bp = Blueprint("api", __name__)

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


# ==============================================================================
# Authentication REST API Endpoints
# ==============================================================================

@api_bp.route("/api/register", methods=["POST"])
def api_register():
    """Register a new user account via JSON API."""
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    confirm_password = str(data.get("confirm_password", ""))
    user_type = str(data.get("user_type", "Salaried Professional")).strip()

    if not name or len(name) < 2:
        return jsonify({"success": False, "error": "Name must be at least 2 characters."}), 400
    if not email or not EMAIL_REGEX.match(email):
        return jsonify({"success": False, "error": "Invalid email address format."}), 400
    if not password or len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters."}), 400
    if confirm_password and password != confirm_password:
        return jsonify({"success": False, "error": "Passwords do not match."}), 400
    if user_type not in USER_TYPES:
        user_type = "Salaried Professional"

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "error": "An account with this email already exists."}), 409

    user = User(name=name, email=email, user_type=user_type)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return jsonify({
        "success": True,
        "message": "User registered and logged in successfully.",
        "user": user.to_dict(),
    }), 201


@api_bp.route("/api/login", methods=["POST"])
def api_login():
    """Authenticate user and initialize session."""
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    remember = bool(data.get("remember", False))

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"success": False, "error": "Invalid email or password."}), 401

    login_user(user, remember=remember)
    return jsonify({
        "success": True,
        "message": "Login successful.",
        "user": user.to_dict(),
    }), 200


@api_bp.route("/api/logout", methods=["POST", "GET"])
@login_required
def api_logout():
    """Terminate authenticated session."""
    logout_user()
    return jsonify({"success": True, "message": "Logged out successfully."}), 200


# ==============================================================================
# Dashboard REST API Endpoint
# ==============================================================================

@api_bp.route("/api/dashboard", methods=["GET"])
@login_required
def api_dashboard():
    """Retrieve complete financial dashboard metrics for current user."""
    today = date.today()
    try:
        month = int(request.args.get("month", today.month))
        year = int(request.args.get("year", today.year))
    except (ValueError, TypeError):
        month = today.month
        year = today.year

    summary = get_dashboard_summary(current_user.id, month, year)
    
    # Serialize active goals
    serialized_goals = [g.to_dict() for g in summary["active_goals"]]
    summary_copy = dict(summary)
    summary_copy["active_goals"] = serialized_goals
    summary_copy["user"] = current_user.to_dict()

    return jsonify({"success": True, "data": summary_copy}), 200


# ==============================================================================
# Income Management REST API Endpoints
# ==============================================================================

@api_bp.route("/api/income", methods=["GET", "POST"])
@login_required
def api_income():
    """GET user incomes with filtering or POST a new income record."""
    if request.method == "GET":
        today = date.today()
        month = request.args.get("month")
        year = request.args.get("year")
        source = request.args.get("source")

        query = Income.query.filter_by(user_id=current_user.id)
        if month:
            try:
                query = query.filter(db.extract("month", Income.income_date) == int(month))
            except ValueError:
                pass
        if year:
            try:
                query = query.filter(db.extract("year", Income.income_date) == int(year))
            except ValueError:
                pass
        if source:
            query = query.filter(Income.source == source)

        incomes = query.order_by(Income.income_date.desc()).all()
        total_amount = sum(inc.amount for inc in incomes)

        return jsonify({
            "success": True,
            "count": len(incomes),
            "total_amount": round(total_amount, 2),
            "incomes": [inc.to_dict() for inc in incomes],
        }), 200

    # POST new income
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Amount must be a valid number."}), 400

    if amount <= 0:
        return jsonify({"success": False, "error": "Income amount must be greater than 0."}), 400

    source = str(data.get("source", "")).strip()
    if not source:
        return jsonify({"success": False, "error": "Income source is required."}), 400

    date_str = data.get("date") or data.get("income_date")
    try:
        income_date = datetime.strptime(str(date_str).strip(), "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        return jsonify({"success": False, "error": "Invalid date format. Expected YYYY-MM-DD."}), 400

    description = str(data.get("description", "")).strip()

    new_income = Income(
        user_id=current_user.id,
        amount=amount,
        source=source,
        income_date=income_date,
        description=description,
    )
    db.session.add(new_income)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Income recorded successfully.",
        "income": new_income.to_dict(),
    }), 201


@api_bp.route("/api/income/<int:income_id>", methods=["PUT", "DELETE"])
@login_required
def api_income_detail(income_id):
    """PUT to update or DELETE an existing income entry."""
    income = Income.query.filter_by(id=income_id, user_id=current_user.id).first()
    if not income:
        return jsonify({"success": False, "error": "Income entry not found or unauthorized."}), 404

    if request.method == "DELETE":
        db.session.delete(income)
        db.session.commit()
        return jsonify({"success": True, "message": "Income entry deleted successfully."}), 200

    # PUT update
    data = request.get_json(silent=True) or {}
    if "amount" in data:
        try:
            amt = float(data["amount"])
            if amt <= 0:
                return jsonify({"success": False, "error": "Amount must be greater than 0."}), 400
            income.amount = amt
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Invalid amount value."}), 400

    if "source" in data and str(data["source"]).strip():
        income.source = str(data["source"]).strip()

    date_str = data.get("date") or data.get("income_date")
    if date_str:
        try:
            income.income_date = datetime.strptime(str(date_str).strip(), "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "error": "Invalid date format. Expected YYYY-MM-DD."}), 400

    if "description" in data:
        income.description = str(data["description"]).strip()

    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Income entry updated successfully.",
        "income": income.to_dict(),
    }), 200


# ==============================================================================
# Expense Management REST API Endpoints
# ==============================================================================

@api_bp.route("/api/expenses", methods=["GET", "POST"])
@login_required
def api_expenses():
    """GET user expenses with filtering or POST a new expense record."""
    if request.method == "GET":
        month = request.args.get("month")
        year = request.args.get("year")
        category = request.args.get("category")
        search = request.args.get("search")

        query = Expense.query.filter_by(user_id=current_user.id)
        if month:
            try:
                query = query.filter(db.extract("month", Expense.expense_date) == int(month))
            except ValueError:
                pass
        if year:
            try:
                query = query.filter(db.extract("year", Expense.expense_date) == int(year))
            except ValueError:
                pass
        if category:
            query = query.filter(Expense.category == category)
        if search:
            query = query.filter(Expense.description.ilike(f"%{search}%"))

        expenses = query.order_by(Expense.expense_date.desc()).all()
        total_amount = sum(exp.amount for exp in expenses)

        return jsonify({
            "success": True,
            "count": len(expenses),
            "total_amount": round(total_amount, 2),
            "expenses": [exp.to_dict() for exp in expenses],
        }), 200

    # POST new expense
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Amount must be a valid number."}), 400

    if amount <= 0:
        return jsonify({"success": False, "error": "Expense amount must be positive."}), 400

    category = str(data.get("category", "")).strip()
    if not category:
        return jsonify({"success": False, "error": "Category is required."}), 400

    date_str = data.get("date") or data.get("expense_date")
    try:
        expense_date = datetime.strptime(str(date_str).strip(), "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        return jsonify({"success": False, "error": "Invalid date format. Expected YYYY-MM-DD."}), 400

    description = str(data.get("description", "")).strip()

    new_expense = Expense(
        user_id=current_user.id,
        amount=amount,
        category=category,
        expense_date=expense_date,
        description=description,
    )
    db.session.add(new_expense)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Expense recorded successfully.",
        "expense": new_expense.to_dict(),
    }), 201


@api_bp.route("/api/expenses/<int:expense_id>", methods=["PUT", "DELETE"])
@login_required
def api_expense_detail(expense_id):
    """PUT to update or DELETE an existing expense entry."""
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first()
    if not expense:
        return jsonify({"success": False, "error": "Expense entry not found or unauthorized."}), 404

    if request.method == "DELETE":
        db.session.delete(expense)
        db.session.commit()
        return jsonify({"success": True, "message": "Expense entry deleted successfully."}), 200

    # PUT update
    data = request.get_json(silent=True) or {}
    if "amount" in data:
        try:
            amt = float(data["amount"])
            if amt <= 0:
                return jsonify({"success": False, "error": "Amount must be positive."}), 400
            expense.amount = amt
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Invalid amount value."}), 400

    if "category" in data and str(data["category"]).strip():
        expense.category = str(data["category"]).strip()

    date_str = data.get("date") or data.get("expense_date")
    if date_str:
        try:
            expense.expense_date = datetime.strptime(str(date_str).strip(), "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "error": "Invalid date format. Expected YYYY-MM-DD."}), 400

    if "description" in data:
        expense.description = str(data["description"]).strip()

    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Expense entry updated successfully.",
        "expense": expense.to_dict(),
    }), 200


# ==============================================================================
# Budget Management REST API Endpoints
# ==============================================================================

@api_bp.route("/api/budgets", methods=["GET", "POST"])
@login_required
def api_budgets():
    """GET monthly budgets or POST to create/update a budget limit."""
    today = date.today()
    if request.method == "GET":
        try:
            month = int(request.args.get("month", today.month))
            year = int(request.args.get("year", today.year))
        except (ValueError, TypeError):
            month = today.month
            year = today.year

        budget_status = get_budget_status(current_user.id, month, year)
        return jsonify({"success": True, "data": budget_status}), 200

    # POST new or update existing budget
    data = request.get_json(silent=True) or {}
    category = str(data.get("category", "")).strip()
    if not category:
        return jsonify({"success": False, "error": "Category is required."}), 400

    raw_amt = data.get("amount") or data.get("monthly_limit")
    try:
        amount = float(raw_amt)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Budget limit must be a number."}), 400

    if amount <= 0:
        return jsonify({"success": False, "error": "Budget limit must be greater than zero."}), 400

    try:
        month = int(data.get("month", today.month))
        year = int(data.get("year", today.year))
    except (ValueError, TypeError):
        month = today.month
        year = today.year

    if month < 1 or month > 12:
        return jsonify({"success": False, "error": "Month must be between 1 and 12."}), 400

    existing = Budget.query.filter_by(
        user_id=current_user.id, category=category, month=month, year=year
    ).first()

    if existing:
        existing.amount = amount
        message = f"Budget for {category} updated to ₹{amount:,.2f}."
        b_obj = existing
    else:
        b_obj = Budget(
            user_id=current_user.id,
            category=category,
            amount=amount,
            month=month,
            year=year,
        )
        db.session.add(b_obj)
        message = f"Budget for {category} created at ₹{amount:,.2f}."

    db.session.commit()
    return jsonify({
        "success": True,
        "message": message,
        "budget": b_obj.to_dict(),
    }), 201


@api_bp.route("/api/budgets/<int:budget_id>", methods=["PUT", "DELETE"])
@login_required
def api_budget_detail(budget_id):
    """PUT to update or DELETE an existing category budget."""
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first()
    if not budget:
        return jsonify({"success": False, "error": "Budget not found or unauthorized."}), 404

    if request.method == "DELETE":
        db.session.delete(budget)
        db.session.commit()
        return jsonify({"success": True, "message": "Budget deleted successfully."}), 200

    data = request.get_json(silent=True) or {}
    raw_amt = data.get("amount") or data.get("monthly_limit")
    if raw_amt is not None:
        try:
            amt = float(raw_amt)
            if amt <= 0:
                return jsonify({"success": False, "error": "Budget limit must be greater than 0."}), 400
            budget.amount = amt
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Invalid amount value."}), 400

    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Budget updated successfully.",
        "budget": budget.to_dict(),
    }), 200


# ==============================================================================
# Savings Goals REST API Endpoints
# ==============================================================================

@api_bp.route("/api/savings-goals", methods=["GET", "POST"])
@login_required
def api_savings_goals():
    """GET user savings goals or POST to create a new goal."""
    if request.method == "GET":
        goals = SavingsGoal.query.filter_by(user_id=current_user.id).order_by(SavingsGoal.target_date.asc()).all()
        return jsonify({
            "success": True,
            "count": len(goals),
            "goals": [g.to_dict() for g in goals],
        }), 200

    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or data.get("goal_name") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "Goal name is required."}), 400

    try:
        target_amount = float(data.get("target_amount", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Target amount must be a number."}), 400

    if target_amount <= 0:
        return jsonify({"success": False, "error": "Target amount must be greater than 0."}), 400

    try:
        current_amount = float(data.get("current_amount", 0.0))
        if current_amount < 0:
            current_amount = 0.0
    except (ValueError, TypeError):
        current_amount = 0.0

    deadline_str = data.get("deadline") or data.get("target_date")
    if not deadline_str:
        return jsonify({"success": False, "error": "Target deadline is required."}), 400

    try:
        target_date = datetime.strptime(str(deadline_str).strip(), "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "error": "Invalid date format. Expected YYYY-MM-DD."}), 400

    description = str(data.get("description", "")).strip()

    new_goal = SavingsGoal(
        user_id=current_user.id,
        name=name,
        target_amount=target_amount,
        current_amount=current_amount,
        target_date=target_date,
        description=description,
        status="Completed" if current_amount >= target_amount else "In Progress",
    )
    db.session.add(new_goal)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Savings goal created successfully.",
        "goal": new_goal.to_dict(),
    }), 201


@api_bp.route("/api/savings-goals/<int:goal_id>", methods=["PUT", "DELETE"])
@login_required
def api_savings_goal_detail(goal_id):
    """PUT to update or DELETE an existing savings goal."""
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=current_user.id).first()
    if not goal:
        return jsonify({"success": False, "error": "Savings goal not found or unauthorized."}), 404

    if request.method == "DELETE":
        db.session.delete(goal)
        db.session.commit()
        return jsonify({"success": True, "message": "Savings goal deleted successfully."}), 200

    data = request.get_json(silent=True) or {}
    if "name" in data or "goal_name" in data:
        name = str(data.get("name") or data.get("goal_name")).strip()
        if name:
            goal.name = name

    if "target_amount" in data:
        try:
            t_amt = float(data["target_amount"])
            if t_amt <= 0:
                return jsonify({"success": False, "error": "Target amount must be greater than 0."}), 400
            goal.target_amount = t_amt
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Invalid target amount."}), 400

    if "current_amount" in data:
        try:
            c_amt = float(data["current_amount"])
            if c_amt >= 0:
                goal.current_amount = c_amt
        except (ValueError, TypeError):
            pass

    deadline_str = data.get("deadline") or data.get("target_date")
    if deadline_str:
        try:
            goal.target_date = datetime.strptime(str(deadline_str).strip(), "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "error": "Invalid deadline format. Expected YYYY-MM-DD."}), 400

    if "description" in data:
        goal.description = str(data["description"]).strip()

    if goal.current_amount >= goal.target_amount:
        goal.status = "Completed"

    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Savings goal updated successfully.",
        "goal": goal.to_dict(),
    }), 200


# ==============================================================================
# Monthly Financial Reports REST API Endpoint
# ==============================================================================

@api_bp.route("/api/reports/<int:year>/<int:month>", methods=["GET"])
@login_required
def api_monthly_report(year, month):
    """Retrieve full monthly financial statement data and save snapshot."""
    if month < 1 or month > 12:
        return jsonify({"success": False, "error": "Month must be between 1 and 12."}), 400

    report_data = generate_monthly_report_data(current_user.id, month, year)
    # Save persistent snapshot
    save_financial_report(current_user.id, month, year)

    # Serialize goals
    report_data["goals"] = [g.to_dict() for g in report_data["goals"]]

    return jsonify({"success": True, "data": report_data}), 200


# ==============================================================================
# AI Financial Advisor REST API Endpoints
# ==============================================================================

@api_bp.route("/api/advisor/analyze", methods=["POST"])
@login_required
def api_advisor_analyze():
    """Generates structured financial analysis for current user using AI or rule engine."""
    today = date.today()
    data = request.get_json(silent=True) or {}
    try:
        month = int(data.get("month", today.month))
        year = int(data.get("year", today.year))
    except (ValueError, TypeError):
        month = today.month
        year = today.year

    financial_data = get_dashboard_summary(current_user.id, month, year)
    advisory_output = generate_ai_insights(
        financial_data=financial_data,
        user_type=current_user.user_type,
    )

    return jsonify({
        "success": True,
        "advisory": advisory_output,
        "financial_summary": {
            "income": financial_data["income"],
            "expenses": financial_data["expenses"],
            "savings": financial_data["savings"],
            "savings_rate": financial_data["savings_rate"],
        },
    }), 200


@api_bp.route("/api/advisor/chat", methods=["POST"])
@login_required
def api_advisor_chat():
    """Interactive AI financial chat endpoint."""
    data = request.get_json(silent=True) or {}
    query = str(data.get("query", "")).strip()

    if not query:
        return jsonify({"success": False, "error": "Query cannot be empty."}), 400

    today = date.today()
    try:
        month = int(data.get("month", today.month))
        year = int(data.get("year", today.year))
    except (ValueError, TypeError):
        month = today.month
        year = today.year

    result = answer_financial_query(current_user.id, query, month, year)

    return jsonify({
        "success": True,
        "answer": result["answer"],
        "mode": result.get("mode", "rule_based"),
    }), 200


# ==============================================================================
# Compatibility Endpoints (/analyse and /generate)
# ==============================================================================

@api_bp.route("/analyse", methods=["POST"])
def analyse():
    """
    POST /analyse compatibility endpoint:
    Accepts JSON input, invokes Gemini AI or fallback, and returns structured financial advice.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid request body. Expected JSON object."}), 400

    raw_income = data.get("income")
    if raw_income is None:
        return jsonify({"success": False, "error": "Income is required."}), 400

    try:
        income = float(raw_income)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Income must be a valid number."}), 400

    if income <= 0:
        return jsonify({"success": False, "error": "Income must be greater than 0."}), 400

    if income > 100_000_000:
        return jsonify({"success": False, "error": "Income exceeds maximum supported limit."}), 400

    raw_expenses = data.get("expenses")
    if not raw_expenses or not isinstance(raw_expenses, dict):
        return jsonify({"success": False, "error": "At least one expense category entry is required."}), 400

    validated_expenses = {}
    has_positive_expense = False

    for cat_name, raw_val in raw_expenses.items():
        if not cat_name or not isinstance(cat_name, str):
            continue
        clean_cat = cat_name.strip()
        if not clean_cat:
            continue
        try:
            val = float(raw_val)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": f"Expense amount for '{clean_cat}' must be a number."}), 400

        if val < 0:
            return jsonify({"success": False, "error": f"Expense amount for '{clean_cat}' cannot be negative."}), 400

        if val > 100_000_000:
            return jsonify({"success": False, "error": f"Expense amount for '{clean_cat}' exceeds maximum limit."}), 400

        if val > 0:
            has_positive_expense = True
            validated_expenses[clean_cat] = val

    if not has_positive_expense or not validated_expenses:
        return jsonify({
            "success": False,
            "error": "At least one expense entry must be greater than 0."
        }), 400

    goal = str(data.get("goal") or "emergency_fund").strip()

    try:
        result = analyze_finances_with_gemini(income, validated_expenses, goal)

        if not all(k in result for k in ("budget", "analysis", "suggestions")):
            return jsonify({
                "success": False,
                "error": "Response was missing required keys: budget, analysis, suggestions."
            }), 500

        return jsonify({
            "success": True,
            "budget": result["budget"],
            "analysis": result["analysis"],
            "suggestions": result["suggestions"],
            "summary": result.get("summary", ""),
        }), 200

    except Exception as exc:
        return jsonify({
            "success": False,
            "error": f"An error occurred while processing your analysis: {str(exc)}"
        }), 500


@api_bp.route("/generate", methods=["POST"])
def generate():
    """POST /generate compatibility endpoint for product copywriting."""
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid request body. Expected JSON object."}), 400

    product_info = data.get("product_info")
    if not product_info or not isinstance(product_info, str) or not product_info.strip():
        return jsonify({"success": False, "error": "product_info cannot be empty."}), 400

    product_info = product_info.strip()
    if len(product_info) > 2000:
        return jsonify({
            "success": False,
            "error": "product_info exceeds maximum length of 2000 characters."
        }), 400

    platform = str(data.get("platform") or "general").strip()
    tone = str(data.get("tone") or "professional").strip()

    try:
        content = generate_product_content(product_info, platform, tone)
        return jsonify({"success": True, "content": content}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": f"Content generation error: {str(exc)}"}), 500
