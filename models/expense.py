from datetime import datetime, date
from models import db


class Expense(db.Model):
    """Expense entry model."""

    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    expense_date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def date(self):
        """Alias for expense_date to match requirements."""
        return self.expense_date

    @date.setter
    def date(self, val):
        self.expense_date = val

    def to_dict(self) -> dict:
        """Serialize expense object to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": self.amount,
            "category": self.category,
            "description": self.description or "",
            "date": self.expense_date.isoformat() if self.expense_date else None,
            "expense_date": self.expense_date.isoformat() if self.expense_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Expense {self.category}: ₹{self.amount} on {self.expense_date}>"
