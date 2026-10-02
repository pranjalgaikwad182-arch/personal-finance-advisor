from datetime import datetime
from models import db


class FinancialReport(db.Model):
    """Monthly financial report snapshot model."""

    __tablename__ = "financial_reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    total_income = db.Column(db.Float, nullable=False, default=0.0)
    total_expenses = db.Column(db.Float, nullable=False, default=0.0)
    total_savings = db.Column(db.Float, nullable=False, default=0.0)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "month", "year", name="uq_user_report_month_year"
        ),
    )

    @property
    def savings_rate(self) -> float:
        if self.total_income <= 0:
            return 0.0
        return round((self.total_savings / self.total_income) * 100, 1)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "month": self.month,
            "year": self.year,
            "total_income": self.total_income,
            "total_expenses": self.total_expenses,
            "total_savings": self.total_savings,
            "savings_rate": self.savings_rate,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }

    def __repr__(self) -> str:
        return f"<FinancialReport user={self.user_id} {self.month}/{self.year}: income=₹{self.total_income} exp=₹{self.total_expenses}>"
