from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models import db


class User(UserMixin, db.Model):
    """User account model supporting multiple personal financial profiles."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(
        db.String(50), nullable=False, default="Salaried Professional"
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships with cascade deletion
    incomes = db.relationship(
        "Income", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    expenses = db.relationship(
        "Expense", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    budgets = db.relationship(
        "Budget", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    savings_goals = db.relationship(
        "SavingsGoal", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    financial_reports = db.relationship(
        "FinancialReport", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        """Hash and store the user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """Serialize user object to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "user_type": self.user_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.user_type})>"
