"""
Re-export all models and database instances for backwards compatibility.
"""
from models import (
    db,
    DEFAULT_EXPENSE_CATEGORIES,
    DEFAULT_INCOME_SOURCES,
    USER_TYPES,
    SAVINGS_GOAL_TYPES,
    User,
    Income,
    Expense,
    Budget,
    SavingsGoal,
    SavingsContribution,
    FinancialReport,
)

__all__ = [
    "db",
    "DEFAULT_EXPENSE_CATEGORIES",
    "DEFAULT_INCOME_SOURCES",
    "USER_TYPES",
    "SAVINGS_GOAL_TYPES",
    "User",
    "Income",
    "Expense",
    "Budget",
    "SavingsGoal",
    "SavingsContribution",
    "FinancialReport",
]
