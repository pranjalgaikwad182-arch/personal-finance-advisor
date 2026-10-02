"""
Application Blueprints package.
"""
from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.income import income_bp
from app.routes.expenses import expenses_bp
from app.routes.budgets import budgets_bp
from app.routes.savings import savings_bp
from app.routes.reports import reports_bp
from app.routes.advisor import advisor_bp
from app.routes.api import api_bp

__all__ = [
    "auth_bp",
    "dashboard_bp",
    "income_bp",
    "expenses_bp",
    "budgets_bp",
    "savings_bp",
    "reports_bp",
    "advisor_bp",
    "api_bp",
]
