from datetime import datetime, date
from models import db


class Income(db.Model):
    """Income entry model."""

    __tablename__ = "incomes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    amount = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    income_date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def date(self):
        """Alias for income_date to match requirements."""
        return self.income_date

    @date.setter
    def date(self, val):
        self.income_date = val

    def to_dict(self) -> dict:
        """Serialize income object to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": self.amount,
            "source": self.source,
            "description": self.description or "",
            "date": self.income_date.isoformat() if self.income_date else None,
            "income_date": self.income_date.isoformat() if self.income_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Income {self.source}: ₹{self.amount} on {self.income_date}>"
