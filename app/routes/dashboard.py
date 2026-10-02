from datetime import date
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.services.financial_service import (
    get_dashboard_summary,
    get_budget_status,
    get_expenses_by_category,
    get_monthly_savings_trend,
    calculate_total_income,
    calculate_total_expenses,
    calculate_savings,
)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    """Main authenticated financial dashboard."""
    today = date.today()
    try:
        month = int(request.args.get("month", today.month))
        year = int(request.args.get("year", today.year))
    except (ValueError, TypeError):
        month = today.month
        year = today.year

    if month < 1 or month > 12:
        month = today.month

    summary = get_dashboard_summary(current_user.id, month, year)

    # Years selection for dropdown
    years = [today.year - 2, today.year - 1, today.year, today.year + 1]

    return render_template(
        "dashboard/dashboard.html",
        summary=summary,
        selected_month=month,
        selected_year=year,
        available_years=years,
    )


@dashboard_bp.route("/api/dashboard-charts")
@login_required
def dashboard_charts():
    """API endpoint providing dynamic JSON datasets for Chart.js."""
    today = date.today()
    try:
        month = int(request.args.get("month", today.month))
        year = int(request.args.get("year", today.year))
    except (ValueError, TypeError):
        month = today.month
        year = today.year

    # 1. Income vs Expenses for current month
    inc = calculate_total_income(current_user.id, month, year)
    exp = calculate_total_expenses(current_user.id, month, year)
    sav = calculate_savings(current_user.id, month, year)

    income_vs_expense = {
        "labels": ["Income", "Expenses", "Savings"],
        "datasets": [
            {
                "label": "Current Month (₹)",
                "data": [inc, exp, sav],
                "backgroundColor": [
                    "rgba(16, 185, 129, 0.8)",   # Green
                    "rgba(239, 68, 68, 0.8)",    # Red
                    "rgba(59, 130, 246, 0.8)",   # Blue
                ],
                "borderColor": [
                    "rgb(16, 185, 129)",
                    "rgb(239, 68, 68)",
                    "rgb(59, 130, 246)",
                ],
                "borderWidth": 1,
            }
        ],
    }

    # 2. Category Expenses Doughnut Chart
    cat_expenses = get_expenses_by_category(current_user.id, month, year)
    cat_labels = list(cat_expenses.keys())
    cat_data = list(cat_expenses.values())
    
    palette = [
        "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
        "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16", "#06b6d4"
    ]

    category_chart = {
        "labels": cat_labels if cat_labels else ["No Expenses"],
        "datasets": [
            {
                "data": cat_data if cat_data else [0],
                "backgroundColor": palette[:max(1, len(cat_labels))],
                "borderWidth": 1,
            }
        ],
    }

    # 3. Monthly Savings Trend (past 6 months)
    trend_data = get_monthly_savings_trend(current_user.id, num_months=6)
    trend_chart = {
        "labels": [t["label"] for t in trend_data],
        "datasets": [
            {
                "label": "Income",
                "data": [t["income"] for t in trend_data],
                "borderColor": "rgb(16, 185, 129)",
                "backgroundColor": "rgba(16, 185, 129, 0.15)",
                "type": "line",
                "tension": 0.3,
                "fill": False,
            },
            {
                "label": "Expenses",
                "data": [t["expenses"] for t in trend_data],
                "borderColor": "rgb(239, 68, 68)",
                "backgroundColor": "rgba(239, 68, 68, 0.15)",
                "type": "line",
                "tension": 0.3,
                "fill": False,
            },
            {
                "label": "Savings",
                "data": [t["savings"] for t in trend_data],
                "borderColor": "rgb(59, 130, 246)",
                "backgroundColor": "rgba(59, 130, 246, 0.7)",
                "type": "bar",
            },
        ],
    }

    # 4. Budget vs Actual Bar Chart
    budget_info = get_budget_status(current_user.id, month, year)
    budget_items = budget_info["items"]

    b_labels = [item["category"] for item in budget_items]
    b_allocated = [item["budgeted"] for item in budget_items]
    b_spent = [item["spent"] for item in budget_items]

    budget_vs_actual = {
        "labels": b_labels if b_labels else ["No Budgets Configured"],
        "datasets": [
            {
                "label": "Budget Limit",
                "data": b_allocated if b_allocated else [0],
                "backgroundColor": "rgba(148, 163, 184, 0.7)",
            },
            {
                "label": "Actual Spent",
                "data": b_spent if b_spent else [0],
                "backgroundColor": "rgba(245, 158, 11, 0.8)",
            },
        ],
    }

    return jsonify(
        {
            "income_vs_expense": income_vs_expense,
            "category_chart": category_chart,
            "trend_chart": trend_chart,
            "budget_vs_actual": budget_vs_actual,
        }
    )
