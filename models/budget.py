from datetime import datetime
from models import db


class Budget(db.Model):
    """Monthly budget limit per expense category."""

    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1 - 12
    year = db.Column(db.Integer, nullable=False)   # e.g., 2026
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "category", "month", "year", name="uq_user_cat_month_year"
        ),
    )

    @property
    def monthly_limit(self) -> float:
        """Alias for amount to match requirements."""
        return self.amount

    @monthly_limit.setter
    def monthly_limit(self, val: float):
        self.amount = float(val)

    def to_dict(self) -> dict:
        """Serialize budget object to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category": self.category,
            "amount": self.amount,
            "monthly_limit": self.amount,
            "month": self.month,
            "year": self.year,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Budget {self.category}: ₹{self.amount} ({self.month}/{self.year})>"
