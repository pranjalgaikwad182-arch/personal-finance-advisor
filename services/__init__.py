"""
Services package providing business logic, financial analysis, budget generation,
report generation, savings advisory, and AI engine capabilities.
"""
from services.financial_analyzer import (
    calculate_total_income,
    calculate_total_expenses,
    calculate_savings,
    calculate_savings_rate,
    get_expenses_by_category,
    get_income_by_source,
    get_top_expense_categories,
    get_budget_status,
    get_monthly_savings_trend,
    get_financial_health_indicators,
    get_dashboard_summary,
)
from services.budget_generator import generate_recommended_budgets
from services.savings_advisor import get_savings_advice, get_goal_projections
from services.report_generator import generate_monthly_report_data, generate_csv_report, save_financial_report
from services.ai_engine import generate_ai_insights, answer_financial_query

__all__ = [
    "calculate_total_income",
    "calculate_total_expenses",
    "calculate_savings",
    "calculate_savings_rate",
    "get_expenses_by_category",
    "get_income_by_source",
    "get_top_expense_categories",
    "get_budget_status",
    "get_monthly_savings_trend",
    "get_financial_health_indicators",
    "get_dashboard_summary",
    "generate_recommended_budgets",
    "get_savings_advice",
    "get_goal_projections",
    "generate_monthly_report_data",
    "generate_csv_report",
    "save_financial_report",
    "generate_ai_insights",
    "answer_financial_query",
]
