import io
import csv
from datetime import date, datetime
from models import db, Income, Expense, Budget, SavingsGoal, FinancialReport
from services.financial_analyzer import (
    calculate_total_income,
    calculate_total_expenses,
    calculate_savings,
    calculate_savings_rate,
    get_income_by_source,
    get_expenses_by_category,
    get_budget_status,
    get_top_expense_categories,
    get_financial_health_indicators,
)


def generate_monthly_report_data(user_id: int, month: int, year: int) -> dict:
    """Consolidates complete financial data for a specified monthly statement."""
    total_income = calculate_total_income(user_id, month, year)
    total_expenses = calculate_total_expenses(user_id, month, year)
    savings = calculate_savings(user_id, month, year)
    savings_rate = calculate_savings_rate(total_income, savings)

    # Income sources
    income_by_source = get_income_by_source(user_id, month, year)
    income_items = []
    for source, amt in income_by_source.items():
        pct = round((amt / total_income * 100), 1) if total_income > 0 else 0.0
        income_items.append({"source": source, "amount": amt, "percentage": pct})

    # Expenses by category
    expense_by_cat = get_expenses_by_category(user_id, month, year)
    expense_items = []
    for cat, amt in expense_by_cat.items():
        pct = round((amt / total_expenses * 100), 1) if total_expenses > 0 else 0.0
        expense_items.append({"category": cat, "amount": amt, "percentage": pct})

    # Budget status
    budget_data = get_budget_status(user_id, month, year)

    # Top spending categories
    top_categories = get_top_expense_categories(user_id, month, year, limit=3)

    # Goals
    goals = (
        SavingsGoal.query.filter_by(user_id=user_id)
        .order_by(SavingsGoal.target_date.asc())
        .all()
    )

    # Financial health indicators
    health = get_financial_health_indicators(user_id, month, year)

    report_date = date(year, month, 1)
    month_name = report_date.strftime("%B")

    # Generate personalized recommendations for the report
    recommendations = []
    if savings_rate >= 20.0:
        recommendations.append(f"Outstanding discipline! Your savings rate of {savings_rate}% exceeds standard financial planning benchmarks.")
    elif savings_rate > 0:
        recommendations.append(f"Your savings rate is {savings_rate}%. Focus on reducing discretionary spending in {top_categories[0]['category'] if top_categories else 'non-essentials'} to reach 20%.")
    else:
        recommendations.append("Expenses exceeded income this month. Immediate expense auditing is recommended to curb deficit spending.")

    if budget_data["over_budget_count"] > 0:
        recommendations.append(f"You exceeded limits in {budget_data['over_budget_count']} budget categories. Consider adjusting category caps or monitoring daily transactions.")
    else:
        recommendations.append("All active budget categories were respected this month without overspending.")

    if top_categories:
        top_cat = top_categories[0]
        recommendations.append(f"Top expenditure was {top_cat['category']} at ₹{top_cat['amount']:,.0f} ({top_cat['percentage']}% of total outgo).")

    return {
        "user_id": user_id,
        "month": month,
        "year": year,
        "month_name": month_name,
        "report_title": f"{month_name} {year} Financial Statement",
        "total_income": total_income,
        "income_items": income_items,
        "total_expenses": total_expenses,
        "expense_items": expense_items,
        "savings": savings,
        "savings_rate": savings_rate,
        "budget_data": budget_data,
        "top_categories": top_categories,
        "goals": goals,
        "health": health,
        "recommendations": recommendations,
    }


def save_financial_report(user_id: int, month: int, year: int) -> FinancialReport:
    """Creates or updates a persistent snapshot record in financial_reports table."""
    total_income = calculate_total_income(user_id, month, year)
    total_expenses = calculate_total_expenses(user_id, month, year)
    total_savings = calculate_savings(user_id, month, year)

    report = FinancialReport.query.filter_by(
        user_id=user_id, month=month, year=year
    ).first()

    if not report:
        report = FinancialReport(
            user_id=user_id,
            month=month,
            year=year,
            total_income=total_income,
            total_expenses=total_expenses,
            total_savings=total_savings,
            generated_at=datetime.utcnow(),
        )
        db.session.add(report)
    else:
        report.total_income = total_income
        report.total_expenses = total_expenses
        report.total_savings = total_savings
        report.generated_at = datetime.utcnow()

    db.session.commit()
    return report


def generate_csv_report(report_data: dict) -> str:
    """Generates a downloadable CSV text string for the monthly report."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["PERSONAL FINANCE ADVISOR - MONTHLY STATEMENT"])
    writer.writerow([f"Period: {report_data['month_name']} {report_data['year']}"])
    writer.writerow([])

    writer.writerow(["EXECUTIVE SUMMARY"])
    writer.writerow(["Metric", "Amount (INR)"])
    writer.writerow(["Total Income", f"{report_data['total_income']:.2f}"])
    writer.writerow(["Total Expenses", f"{report_data['total_expenses']:.2f}"])
    writer.writerow(["Net Savings", f"{report_data['savings']:.2f}"])
    writer.writerow(["Savings Rate", f"{report_data['savings_rate']:.1f}%"])
    writer.writerow([])

    writer.writerow(["INCOME BREAKDOWN"])
    writer.writerow(["Source", "Amount (INR)", "Share (%)"])
    for item in report_data["income_items"]:
        writer.writerow([item["source"], f"{item['amount']:.2f}", f"{item['percentage']:.1f}%"])
    writer.writerow([])

    writer.writerow(["EXPENSE BREAKDOWN BY CATEGORY"])
    writer.writerow(["Category", "Amount (INR)", "Share (%)"])
    for item in report_data["expense_items"]:
        writer.writerow([item["category"], f"{item['amount']:.2f}", f"{item['percentage']:.1f}%"])
    writer.writerow([])

    writer.writerow(["BUDGET VS ACTUAL SPENDING"])
    writer.writerow(["Category", "Budget Limit (INR)", "Actual Spent (INR)", "Variance (INR)", "Status"])
    for b in report_data["budget_data"]["items"]:
        writer.writerow([
            b["category"],
            f"{b['budgeted']:.2f}",
            f"{b['spent']:.2f}",
            f"{b['remaining']:.2f}",
            b["status_label"],
        ])
    writer.writerow([])

    writer.writerow(["SAVINGS GOALS PROGRESS"])
    writer.writerow(["Goal Name", "Target Amount (INR)", "Current Saved (INR)", "Progress (%)", "Target Date"])
    for g in report_data["goals"]:
        writer.writerow([
            g.name,
            f"{g.target_amount:.2f}",
            f"{g.current_amount:.2f}",
            f"{g.progress_pct:.1f}%",
            g.target_date.strftime("%Y-%m-%d"),
        ])
    writer.writerow([])

    writer.writerow(["RECOMMENDATIONS"])
    for rec in report_data.get("recommendations", []):
        writer.writerow([rec])

    return output.getvalue()
