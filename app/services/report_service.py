import io
import csv
from datetime import date
from app.models import Income, Expense, Budget, SavingsGoal
from app.services.financial_service import (
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
    top_categories = get_top_expense_categories(user_id, month, year, limit=5)

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
    }


def generate_csv_report(report_data: dict) -> str:
    """Generates a downloadable CSV text string for the monthly report."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["PERSONAL FINANCE ADVISOR - MONTHLY STATEMENT"])
    writer.writerow([f"Period: {report_data['month_name']} {report_data['year']}"])
    writer.writerow([])

    # Executive Summary
    writer.writerow(["EXECUTIVE SUMMARY"])
    writer.writerow(["Metric", "Amount (INR)"])
    writer.writerow(["Total Income", f"{report_data['total_income']:.2f}"])
    writer.writerow(["Total Expenses", f"{report_data['total_expenses']:.2f}"])
    writer.writerow(["Net Savings", f"{report_data['savings']:.2f}"])
    writer.writerow(["Savings Rate", f"{report_data['savings_rate']:.1f}%"])
    writer.writerow([])

    # Income Breakdown
    writer.writerow(["INCOME BREAKDOWN"])
    writer.writerow(["Source", "Amount (INR)", "Share (%)"])
    for item in report_data["income_items"]:
        writer.writerow([item["source"], f"{item['amount']:.2f}", f"{item['percentage']:.1f}%"])
    writer.writerow([])

    # Expense Breakdown
    writer.writerow(["EXPENSE BREAKDOWN BY CATEGORY"])
    writer.writerow(["Category", "Amount (INR)", "Share (%)"])
    for item in report_data["expense_items"]:
        writer.writerow([item["category"], f"{item['amount']:.2f}", f"{item['percentage']:.1f}%"])
    writer.writerow([])

    # Budget Comparison
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

    # Savings Goals
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

    return output.getvalue()
