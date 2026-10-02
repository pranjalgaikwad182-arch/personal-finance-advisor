from datetime import datetime, date
from models import db


class SavingsGoal(db.Model):
    """Target savings goal model with contribution tracking."""

    __tablename__ = "savings_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, nullable=False, default=0.0)
    target_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="In Progress")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    contributions = db.relationship(
        "SavingsContribution",
        backref="goal",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="desc(SavingsContribution.contribution_date)",
    )

    @property
    def goal_name(self) -> str:
        """Alias for name to match requirements."""
        return self.name

    @goal_name.setter
    def goal_name(self, val: str):
        self.name = val

    @property
    def deadline(self) -> date:
        """Alias for target_date to match requirements."""
        return self.target_date

    @deadline.setter
    def deadline(self, val: date):
        self.target_date = val

    @property
    def progress_pct(self) -> float:
        """Percentage achieved towards the target amount."""
        if self.target_amount <= 0:
            return 0.0
        return min(100.0, round((self.current_amount / self.target_amount) * 100, 1))

    @property
    def remaining_amount(self) -> float:
        """Remaining amount required to meet the goal."""
        return max(0.0, round(self.target_amount - self.current_amount, 2))

    @property
    def months_remaining(self) -> int:
        """Calculates rough number of months remaining until target date."""
        today = date.today()
        if self.target_date <= today:
            return 0
        diff_years = self.target_date.year - today.year
        diff_months = self.target_date.month - today.month
        total_months = diff_years * 12 + diff_months
        return max(1, total_months)

    @property
    def monthly_required(self) -> float:
        """Estimated monthly contribution needed to meet the goal on time."""
        if self.remaining_amount <= 0:
            return 0.0
        months = self.months_remaining
        return round(self.remaining_amount / max(1, months), 2)

    def to_dict(self) -> dict:
        """Serialize savings goal object to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "goal_name": self.name,
            "target_amount": self.target_amount,
            "current_amount": self.current_amount,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "deadline": self.target_date.isoformat() if self.target_date else None,
            "description": self.description or "",
            "status": "Completed" if self.current_amount >= self.target_amount else self.status,
            "progress_pct": self.progress_pct,
            "remaining_amount": self.remaining_amount,
            "monthly_required": self.monthly_required,
            "months_remaining": self.months_remaining,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<SavingsGoal {self.name}: ₹{self.current_amount} of ₹{self.target_amount}>"


class SavingsContribution(db.Model):
    """Individual deposit contribution to a savings goal."""

    __tablename__ = "savings_contributions"

    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(
        db.Integer, db.ForeignKey("savings_goals.id"), nullable=False, index=True
    )
    amount = db.Column(db.Float, nullable=False)
    contribution_date = db.Column(db.Date, nullable=False, default=date.today)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "amount": self.amount,
            "contribution_date": self.contribution_date.isoformat() if self.contribution_date else None,
            "description": self.description or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Contribution ₹{self.amount} to goal {self.goal_id}>"
