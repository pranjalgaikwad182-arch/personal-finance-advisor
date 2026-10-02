from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Standard predefined category and source options
DEFAULT_EXPENSE_CATEGORIES = [
    "Rent",
    "Food",
    "Transport",
    "Utilities",
    "Healthcare",
    "Education",
    "Entertainment",
    "Shopping",
    "Groceries",
    "Household",
    "Other",
]

DEFAULT_INCOME_SOURCES = [
    "Salary",
    "Allowance",
    "Freelance",
    "Business",
    "Investment",
    "Bonus",
    "Other",
]

USER_TYPES = [
    "Salaried Professional",
    "Student",
    "Freelancer",
    "Household Manager",
]

SAVINGS_GOAL_TYPES = [
    "Emergency Fund",
    "New Laptop",
    "Education",
    "Travel",
    "Vacation",
    "Personal Goal",
    "Vehicle",
    "Home",
    "Other",
]

# Import models to register them with SQLAlchemy
from models.user import User
from models.income import Income
from models.expense import Expense
from models.budget import Budget
from models.savings_goal import SavingsGoal, SavingsContribution
from models.financial_report import FinancialReport

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
