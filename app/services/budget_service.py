from datetime import date
from sqlalchemy import func, extract
from app.models import db, Income, Expense, Budget, DEFAULT_EXPENSE_CATEGORIES
from app.services.financial_service import calculate_total_income


def generate_recommended_budgets(
    user_id: int,
    month: int = None,
    year: int = None,
    savings_target_pct: float = 20.0,
) -> dict:
    """
    Transparent, explainable Python budget recommendation engine.
    
    Methodology:
    1. Determine baseline monthly income (selected month or average recent income).
    2. Reserve the user's desired savings target (e.g., 20% of income).
    3. Analyze historical average monthly spending per category across previous records.
    4. Detect unusually high spending categories (> 25% of total spend).
    5. Proportionally scale historical averages into the allocatable spending pool.
    6. Provide a clear, natural-language explanation for every category recommendation.
    """
    today = date.today()
    target_month = month or today.month
    target_year = year or today.year

    # 1. Determine Income
    income = calculate_total_income(user_id, target_month, target_year)
    if income <= 0:
        # Fall back to average past monthly income if current month income isn't entered yet
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
            income = 50000.0  # Reasonable default baseline for demonstration

    # 2. Reserve Savings Target
    savings_target_pct = max(5.0, min(80.0, float(savings_target_pct)))
    target_savings_amount = round(income * (savings_target_pct / 100.0), 2)
    allocatable_spending = max(0.0, round(income - target_savings_amount, 2))

    # 3. Analyze Historical Monthly Expenses by Category
    # Query distinct months of expense data to compute true historical monthly averages
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

    recommendations = []
    total_recommended = 0.0

    # 4. Handle Case: New User with No Prior Expense History
    if total_historical_spend == 0:
        # Standard balanced distribution baseline (50/30/20 rule inspired)
        baseline_weights = {
            "Rent": 0.30,
            "Groceries": 0.15,
            "Food": 0.12,
            "Utilities": 0.08,
            "Transport": 0.08,
            "Healthcare": 0.07,
            "Education": 0.05,
            "Shopping": 0.05,
            "Entertainment": 0.05,
            "Household": 0.03,
            "Other": 0.02,
        }
        for cat, weight in baseline_weights.items():
            raw_rec = allocatable_spending * weight
            rounded_rec = max(500.0, round(raw_rec / 100.0) * 100.0)
            total_recommended += rounded_rec
            recommendations.append(
                {
                    "category": cat,
                    "historical_avg": 0.0,
                    "recommended_amount": rounded_rec,
                    "is_high_spending": False,
                    "explanation": f"Initial allocation baseline ({int(weight * 100)}% of allocatable spending) to support your {int(savings_target_pct)}% savings target.",
                }
            )
    else:
        # 5. Proportionally Allocate Based on Past Patterns with Outlier Dampening
        for cat, avg_spend in category_averages.items():
            if avg_spend <= 0:
                continue

            pct_of_total_expense = (
                (avg_spend / total_historical_spend * 100)
                if total_historical_spend > 0
                else 0
            )
            is_high = pct_of_total_expense >= 25.0

            # Compute proportion of allocatable spending
            proportion = avg_spend / total_historical_spend
            raw_recommendation = allocatable_spending * proportion

            # If unusually high spending, gently trim by 10% to encourage optimization
            if is_high and cat not in ["Rent", "Groceries"]:
                raw_recommendation *= 0.90
                explanation = (
                    f"Consistently high spending area ({pct_of_total_expense:.1f}% of expenses, avg ₹{avg_spend:,.0f}). "
                    f"Recommended trimming by ~10% to curb overspending and secure your savings target."
                )
            else:
                explanation = (
                    f"Based on your historical monthly average of ₹{avg_spend:,.0f} "
                    f"({pct_of_total_expense:.1f}% of overall expenses), scaled to meet your {int(savings_target_pct)}% savings goal."
                )

            # Round to nearest 100 for clean figures
            rounded_rec = max(100.0, round(raw_recommendation / 100.0) * 100.0)
            total_recommended += rounded_rec

            recommendations.append(
                {
                    "category": cat,
                    "historical_avg": avg_spend,
                    "recommended_amount": rounded_rec,
                    "is_high_spending": is_high,
                    "explanation": explanation,
                }
            )

        # Sort recommendations by highest amount first
        recommendations.sort(key=lambda x: x["recommended_amount"], reverse=True)

    return {
        "target_month": target_month,
        "target_year": target_year,
        "income": round(income, 2),
        "savings_target_pct": savings_target_pct,
        "target_savings_amount": target_savings_amount,
        "allocatable_spending": allocatable_spending,
        "total_recommended": round(total_recommended, 2),
        "recommendations": recommendations,
        "disclaimer": (
            "Disclaimer: These budget targets are algorithmic guidelines generated from your "
            "recorded financial data and mathematical proportion rules. They are intended as "
            "practical planning suggestions, not certified or guaranteed financial advice."
        ),
    }


def apply_recommended_budgets(
    user_id: int, budget_data: list, month: int, year: int
) -> int:
    """
    Saves or updates budget entries based on approved recommendation items.
    Returns the count of budgets saved.
    """
    saved_count = 0
    for item in budget_data:
        category = item.get("category")
        amount = float(item.get("amount", 0.0))
        if not category or amount <= 0:
            continue

        existing_budget = Budget.query.filter_by(
            user_id=user_id, category=category, month=month, year=year
        ).first()

        if existing_budget:
            existing_budget.amount = amount
        else:
            new_budget = Budget(
                user_id=user_id,
                category=category,
                amount=amount,
                month=month,
                year=year,
            )
            db.session.add(new_budget)
        saved_count += 1

    db.session.commit()
    return saved_count
