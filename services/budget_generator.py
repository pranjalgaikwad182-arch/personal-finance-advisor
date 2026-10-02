from datetime import date
from sqlalchemy import func, extract
from models import db, Income, Expense, Budget, User, DEFAULT_EXPENSE_CATEGORIES
from services.financial_analyzer import calculate_total_income


def generate_recommended_budgets(
    user_id: int,
    month: int = None,
    year: int = None,
    savings_target_pct: float = 20.0,
) -> dict:
    """
    Intelligent, transparent budget recommendation engine based on:
    - Monthly income
    - User type persona (Student, Salaried Professional, Freelancer, Household Manager)
    - Historical spending patterns
    - 50/30/20 Needs / Wants / Savings rules
    """
    today = date.today()
    target_month = month or today.month
    target_year = year or today.year

    # 1. Fetch user persona
    user = db.session.get(User, user_id)
    user_type = user.user_type if user else "Salaried Professional"

    # 2. Determine Monthly Income
    income = calculate_total_income(user_id, target_month, target_year)
    if income <= 0:
        avg_income_row = (
            db.session.query(
                extract("year", Income.income_date).label("yr"),
                extract("month", Income.income_date).label("mo"),
                func.sum(Income.amount).label("monthly_total"),
            )
            .filter(Income.user_id == user_id)
            .group_by("yr", "mo")
            .all()
        )
        if avg_income_row:
            income = round(
                sum(row.monthly_total for row in avg_income_row) / len(avg_income_row),
                2,
            )
        else:
            # Baseline defaults by persona if no income recorded yet
            persona_defaults = {
                "Student": 15000.0,
                "Salaried Professional": 50000.0,
                "Freelancer": 60000.0,
                "Household Manager": 75000.0,
            }
            income = persona_defaults.get(user_type, 50000.0)

    # 3. Reserve Savings Target
    savings_target_pct = max(5.0, min(80.0, float(savings_target_pct)))
    target_savings_amount = round(income * (savings_target_pct / 100.0), 2)
    allocatable_spending = max(0.0, round(income - target_savings_amount, 2))

    # 4. Analyze Historical Monthly Expenses by Category
    monthly_cat_data = (
        db.session.query(
            Expense.category,
            extract("year", Expense.expense_date).label("yr"),
            extract("month", Expense.expense_date).label("mo"),
            func.sum(Expense.amount).label("monthly_total"),
        )
        .filter(Expense.user_id == user_id)
        .group_by(Expense.category, "yr", "mo")
        .all()
    )

    category_history = {}
    distinct_months = set()

    for cat, yr, mo, monthly_total in monthly_cat_data:
        distinct_months.add((yr, mo))
        category_history.setdefault(cat, []).append(float(monthly_total))

    month_count = max(1, len(distinct_months))

    category_averages = {}
    for cat in DEFAULT_EXPENSE_CATEGORIES:
        if cat in category_history:
            avg_val = sum(category_history[cat]) / month_count
            category_averages[cat] = round(avg_val, 2)
        else:
            category_averages[cat] = 0.0

    total_historical_spend = sum(category_averages.values())

    # Persona-specific weight distribution (Needs vs Wants)
    persona_weights = {
        "Student": {
            "Food": 0.25,
            "Education": 0.20,
            "Transport": 0.15,
            "Entertainment": 0.12,
            "Shopping": 0.10,
            "Utilities": 0.08,
            "Healthcare": 0.05,
            "Other": 0.05,
        },
        "Salaried Professional": {
            "Rent": 0.30,
            "Groceries": 0.15,
            "Food": 0.12,
            "Transport": 0.10,
            "Utilities": 0.08,
            "Entertainment": 0.08,
            "Shopping": 0.07,
            "Healthcare": 0.05,
            "Education": 0.03,
            "Other": 0.02,
        },
        "Freelancer": {
            "Rent": 0.28,
            "Groceries": 0.14,
            "Utilities": 0.12,
            "Food": 0.10,
            "Transport": 0.08,
            "Healthcare": 0.08,
            "Shopping": 0.06,
            "Entertainment": 0.06,
            "Education": 0.04,
            "Other": 0.04,
        },
        "Household Manager": {
            "Groceries": 0.24,
            "Rent": 0.22,
            "Utilities": 0.14,
            "Healthcare": 0.10,
            "Education": 0.10,
            "Household": 0.08,
            "Transport": 0.06,
            "Shopping": 0.04,
            "Other": 0.02,
        },
    }

    base_weights = persona_weights.get(user_type, persona_weights["Salaried Professional"])

    recommendations = []
    total_recommended = 0.0

    if total_historical_spend == 0:
        for cat, weight in base_weights.items():
            allocated = round(allocatable_spending * weight, 0)
            if allocated > 0:
                recommendations.append(
                    {
                        "category": cat,
                        "recommended_amount": allocated,
                        "historical_avg": 0.0,
                        "pct_of_spending": round(weight * 100, 1),
                        "rationale": f"Benchmark recommendation based on {user_type} allocation ({round(weight * 100)}% of spending pool).",
                        "is_overspending_flag": False,
                    }
                )
                total_recommended += allocated
    else:
        # Scale historical proportions into the allocatable spending pool
        for cat in DEFAULT_EXPENSE_CATEGORIES:
            hist_avg = category_averages.get(cat, 0.0)
            if hist_avg <= 0:
                continue

            hist_pct = (hist_avg / total_historical_spend) if total_historical_spend > 0 else 0
            is_high_spend = hist_pct > 0.30

            if total_historical_spend > allocatable_spending:
                scale_factor = allocatable_spending / total_historical_spend
                scaled_amt = round(hist_avg * scale_factor, 0)
                rationale = (
                    f"Trimmed by {round((1 - scale_factor) * 100, 1)}% from your past average (₹{hist_avg:,.0f}) "
                    f"to honor your {savings_target_pct}% monthly savings target."
                )
            else:
                scaled_amt = hist_avg
                rationale = f"Maintained in alignment with your historical spending average (₹{hist_avg:,.0f})."

            if is_high_spend:
                rationale += f" [High spend alert: consumed {round(hist_pct * 100, 1)}% of past budget]."

            recommendations.append(
                {
                    "category": cat,
                    "recommended_amount": scaled_amt,
                    "historical_avg": hist_avg,
                    "pct_of_spending": round((scaled_amt / allocatable_spending * 100), 1) if allocatable_spending > 0 else 0.0,
                    "rationale": rationale,
                    "is_overspending_flag": is_high_spend,
                }
            )
            total_recommended += scaled_amt

    recommendations.sort(key=lambda x: x["recommended_amount"], reverse=True)

    # Group into Needs, Wants, and Savings for presentation
    needs_categories = {"Rent", "Groceries", "Utilities", "Healthcare", "Education", "Household", "Transport"}
    wants_categories = {"Food", "Entertainment", "Shopping", "Other"}

    needs_items = [r for r in recommendations if r["category"] in needs_categories]
    wants_items = [r for r in recommendations if r["category"] in wants_categories]
    savings_items = [
        {"category": "Emergency Fund Cushion", "recommended_amount": round(target_savings_amount * 0.5, 0), "rationale": "High-priority liquidity buffer"},
        {"category": "Target / General Savings", "recommended_amount": round(target_savings_amount * 0.5, 0), "rationale": "Long-term goals & future investments"},
    ]

    return {
        "user_type": user_type,
        "income": income,
        "savings_target_pct": savings_target_pct,
        "target_savings_amount": target_savings_amount,
        "allocatable_spending": allocatable_spending,
        "total_recommended": round(total_recommended, 2),
        "month": target_month,
        "year": target_year,
        "recommendations": recommendations,
        "needs_items": needs_items,
        "wants_items": wants_items,
        "savings_items": savings_items,
    }
