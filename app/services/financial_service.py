from datetime import date, datetime
from sqlalchemy import func, extract
from app.models import db, Income, Expense, Budget, SavingsGoal


def calculate_total_income(user_id: int, month: int, year: int) -> float:
    """Deterministic calculation of total income for given user and month/year."""
    result = (
        db.session.query(func.coalesce(func.sum(Income.amount), 0.0))
        .filter(
            Income.user_id == user_id,
            extract("month", Income.income_date) == month,
            extract("year", Income.income_date) == year,
        )
        .scalar()
    )
    return round(float(result), 2)


def calculate_total_expenses(user_id: int, month: int, year: int) -> float:
    """Deterministic calculation of total expenses for given user and month/year."""
    result = (
        db.session.query(func.coalesce(func.sum(Expense.amount), 0.0))
        .filter(
            Expense.user_id == user_id,
            extract("month", Expense.expense_date) == month,
            extract("year", Expense.expense_date) == year,
        )
        .scalar()
    )
    return round(float(result), 2)


def calculate_savings(user_id: int, month: int, year: int) -> float:
    """Calculate net savings (income - expenses). Can be negative if overspending."""
    income = calculate_total_income(user_id, month, year)
    expenses = calculate_total_expenses(user_id, month, year)
    return round(income - expenses, 2)


def calculate_savings_rate(income: float, savings: float) -> float:
    """Calculate savings percentage of total income. Handles 0 income safely."""
    if income <= 0:
        return 0.0
    return round((savings / income) * 100, 1)


def get_expenses_by_category(user_id: int, month: int, year: int) -> dict:
    """Returns a dictionary of category totals sorted descending."""
    results = (
        db.session.query(Expense.category, func.sum(Expense.amount))
        .filter(
            Expense.user_id == user_id,
            extract("month", Expense.expense_date) == month,
            extract("year", Expense.expense_date) == year,
        )
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )
    return {category: round(float(total), 2) for category, total in results}


def get_income_by_source(user_id: int, month: int, year: int) -> dict:
    """Returns a dictionary of income source totals sorted descending."""
    results = (
        db.session.query(Income.source, func.sum(Income.amount))
        .filter(
            Income.user_id == user_id,
            extract("month", Income.income_date) == month,
            extract("year", Income.income_date) == year,
        )
        .group_by(Income.source)
        .order_by(func.sum(Income.amount).desc())
        .all()
    )
    return {source: round(float(total), 2) for source, total in results}


def get_top_expense_categories(user_id: int, month: int, year: int, limit: int = 5) -> list:
    """Returns list of (category, total, percentage) for top spending categories."""
    category_totals = get_expenses_by_category(user_id, month, year)
    total_expenses = sum(category_totals.values())

    top_items = []
    for cat, amt in list(category_totals.items())[:limit]:
        pct = round((amt / total_expenses * 100), 1) if total_expenses > 0 else 0.0
        top_items.append({"category": cat, "amount": amt, "percentage": pct})
    return top_items


def get_budget_status(user_id: int, month: int, year: int) -> dict:
    """
    Compares budgeted category limits against actual expenses.
    Status logic:
    - Green / 'within': utilization < 80%
    - Yellow / 'approaching': 80% <= utilization <= 100%
    - Red / 'exceeded': utilization > 100%
    """
    budgets = (
        Budget.query.filter_by(user_id=user_id, month=month, year=year)
        .order_by(Budget.category)
        .all()
    )
    category_expenses = get_expenses_by_category(user_id, month, year)

    items = []
    total_budgeted = 0.0
    total_spent_on_budgeted = 0.0
    over_budget_count = 0

    seen_categories = set()

    for b in budgets:
        seen_categories.add(b.category)
        spent = category_expenses.get(b.category, 0.0)
        remaining = round(b.amount - spent, 2)
        utilization = round((spent / b.amount * 100), 1) if b.amount > 0 else 0.0

        if utilization > 100.0:
            status = "exceeded"
            status_label = "Exceeded Budget"
            badge_class = "danger"
            over_budget_count += 1
        elif utilization >= 80.0:
            status = "approaching"
            status_label = "Approaching Limit"
            badge_class = "warning text-dark"
        else:
            status = "within"
            status_label = "Within Budget"
            badge_class = "success"

        total_budgeted += b.amount
        total_spent_on_budgeted += spent

        items.append(
            {
                "budget_id": b.id,
                "category": b.category,
                "budgeted": b.amount,
                "spent": spent,
                "remaining": remaining,
                "utilization": utilization,
                "status": status,
                "status_label": status_label,
                "badge_class": badge_class,
            }
        )

    # Categories with spending but no set budget
    unbudgeted_items = []
    for cat, spent in category_expenses.items():
        if cat not in seen_categories:
            unbudgeted_items.append(
                {
                    "category": cat,
                    "budgeted": 0.0,
                    "spent": spent,
                    "remaining": -spent,
                    "utilization": 100.0,
                    "status": "unbudgeted",
                    "status_label": "Unbudgeted",
                    "badge_class": "secondary",
                }
            )

    overall_utilization = (
        round((total_spent_on_budgeted / total_budgeted * 100), 1)
        if total_budgeted > 0
        else 0.0
    )

    return {
        "budget_items": items,
        "items": items,
        "unbudgeted_items": unbudgeted_items,
        "total_budgeted": round(total_budgeted, 2),
        "total_spent_budgeted": round(total_spent_on_budgeted, 2),
        "remaining_budget": round(total_budgeted - total_spent_on_budgeted, 2),
        "overall_utilization": overall_utilization,
        "over_budget_count": over_budget_count,
        "total_categories_budgeted": len(items),
    }


def get_monthly_savings_trend(user_id: int, num_months: int = 6) -> list:
    """Calculates income, expenses, and savings for the past N calendar months."""
    trend = []
    today = date.today()

    # Calculate month offsets going backward
    for i in range(num_months - 1, -1, -1):
        # Calculate target month and year
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1

        month_date = date(year, month, 1)
        month_label = month_date.strftime("%b %Y")

        inc = calculate_total_income(user_id, month, year)
        exp = calculate_total_expenses(user_id, month, year)
        sav = round(inc - exp, 2)
        rate = calculate_savings_rate(inc, sav)

        trend.append(
            {
                "month": month,
                "year": year,
                "label": month_label,
                "income": inc,
                "expenses": exp,
                "savings": sav,
                "savings_rate": rate,
            }
        )
    return trend


def get_financial_health_indicators(user_id: int, month: int, year: int) -> dict:
    """
    Computes transparent, deterministic financial health indicators without arbitrary scores:
    1. Savings rate
    2. Budget adherence (% of budgeted categories kept within limit)
    3. Over-budget category count
    4. Emergency fund progress
    5. Expense-to-income ratio
    """
    income = calculate_total_income(user_id, month, year)
    expenses = calculate_total_expenses(user_id, month, year)
    savings = round(income - expenses, 2)
    savings_rate = calculate_savings_rate(income, savings)

    # Budget adherence
    budget_info = get_budget_status(user_id, month, year)
    total_budgeted_cats = budget_info["total_categories_budgeted"]
    over_budget_count = budget_info["over_budget_count"]

    if total_budgeted_cats > 0:
        within_budget_count = total_budgeted_cats - over_budget_count
        budget_adherence = round((within_budget_count / total_budgeted_cats) * 100, 1)
    else:
        budget_adherence = 100.0 if expenses == 0 else 0.0

    # Expense-to-income ratio
    if income > 0:
        expense_ratio = round((expenses / income) * 100, 1)
    else:
        expense_ratio = 100.0 if expenses > 0 else 0.0

    # Emergency fund progress
    emergency_goal = (
        SavingsGoal.query.filter(
            SavingsGoal.user_id == user_id,
            func.lower(SavingsGoal.name).like("%emergency%"),
        ).first()
    )

    if not emergency_goal:
        # Fall back to first active savings goal
        emergency_goal = SavingsGoal.query.filter_by(user_id=user_id).first()

    if emergency_goal:
        ef_progress = emergency_goal.progress_pct
        ef_name = emergency_goal.name
        ef_target = emergency_goal.target_amount
        ef_current = emergency_goal.current_amount
    else:
        ef_progress = 0.0
        ef_name = "Not Set"
        ef_target = 0.0
        ef_current = 0.0

    # Status benchmarks
    if savings_rate >= 20.0:
        savings_status = "Optimal"
        savings_badge = "success"
    elif savings_rate >= 10.0:
        savings_status = "Moderate"
        savings_badge = "warning text-dark"
    elif savings_rate >= 0.0:
        savings_status = "Low"
        savings_badge = "warning text-dark"
    else:
        savings_status = "Negative (Deficit)"
        savings_badge = "danger"

    if budget_adherence >= 85.0:
        adherence_status = "Strong"
        adherence_badge = "success"
    elif budget_adherence >= 60.0:
        adherence_status = "Needs Attention"
        adherence_badge = "warning text-dark"
    else:
        adherence_status = "Poor Adherence"
        adherence_badge = "danger"

    if expense_ratio <= 70.0:
        ratio_status = "Comfortable"
        ratio_badge = "success"
    elif expense_ratio <= 90.0:
        ratio_status = "Tight"
        ratio_badge = "warning text-dark"
    else:
        ratio_status = "High Stress"
        ratio_badge = "danger"

    return {
        "savings_rate": savings_rate,
        "savings_status": savings_status,
        "savings_badge": savings_badge,
        "budget_adherence": budget_adherence,
        "adherence_status": adherence_status,
        "adherence_badge": adherence_badge,
        "over_budget_count": over_budget_count,
        "expense_ratio": expense_ratio,
        "ratio_status": ratio_status,
        "ratio_badge": ratio_badge,
        "emergency_fund_progress": ef_progress,
        "emergency_fund_name": ef_name,
        "emergency_fund_target": ef_target,
        "emergency_fund_current": ef_current,
    }


def get_dashboard_summary(user_id: int, month: int, year: int) -> dict:
    """Consolidated summary dictionary for rendering dashboard cards and charts."""
    income = calculate_total_income(user_id, month, year)
    expenses = calculate_total_expenses(user_id, month, year)
    savings = round(income - expenses, 2)
    savings_rate = calculate_savings_rate(income, savings)

    category_expenses = get_expenses_by_category(user_id, month, year)
    top_categories = get_top_expense_categories(user_id, month, year, limit=5)
    top_category_name = top_categories[0]["category"] if top_categories else "None"
    top_category_amount = top_categories[0]["amount"] if top_categories else 0.0

    budget_info = get_budget_status(user_id, month, year)
    health = get_financial_health_indicators(user_id, month, year)
    trend = get_monthly_savings_trend(user_id, num_months=6)

    # Active savings goals
    goals = (
        SavingsGoal.query.filter_by(user_id=user_id)
        .order_by(SavingsGoal.target_date.asc())
        .limit(4)
        .all()
    )

    return {
        "income": income,
        "expenses": expenses,
        "savings": savings,
        "savings_rate": savings_rate,
        "remaining_budget": budget_info["remaining_budget"],
        "total_budgeted": budget_info["total_budgeted"],
        "budget_utilization": budget_info["overall_utilization"],
        "over_budget_count": budget_info["over_budget_count"],
        "top_category_name": top_category_name,
        "top_category_amount": top_category_amount,
        "category_expenses": category_expenses,
        "budget_info": budget_info,
        "health": health,
        "trend": trend,
        "active_goals": goals,
    }
