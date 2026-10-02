import os
from datetime import date, timedelta
from app import create_app
from app.models import (
    db,
    User,
    Income,
    Expense,
    Budget,
    SavingsGoal,
    SavingsContribution,
)


def seed_database():
    """
    Populates realistic demonstration financial data for internship evaluation.
    Account: demo@example.com / Demo@12345
    Role: Salaried Professional
    """
    app = create_app(os.getenv("FLASK_ENV", "development"))

    with app.app_context():
        # Clean existing demo user if present to ensure clean idempotency
        existing_user = User.query.filter_by(email="demo@example.com").first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()
            print("Purged old demo user data.")

        # 1. Create Demo User
        demo_user = User(
            name="Demo User",
            email="demo@example.com",
            user_type="Salaried Professional",
        )
        demo_user.set_password("Demo@12345")
        db.session.add(demo_user)
        db.session.commit()
        print(f"Created demo user: {demo_user.email} (ID: {demo_user.id})")

        today = date.today()
        current_year = today.year
        current_month = today.month

        # Helper to compute date in month offset
        def get_date(offset_months, day):
            yr = current_year
            mo = current_month - offset_months
            while mo <= 0:
                mo += 12
                yr -= 1
            return date(yr, mo, min(day, 28))

        # 2. Seed Multi-Month Income (Past 4 months to render rich Trend charts)
        months_to_seed = [
            (0, 50000.0, 5000.0),   # Current month: Salary + Bonus/Dividend
            (1, 50000.0, 0.0),      # Last month: Salary
            (2, 50000.0, 4000.0),   # 2 months ago: Salary + Freelance
            (3, 48000.0, 0.0),      # 3 months ago: Salary
        ]

        for offset, base_salary, extra_amt in months_to_seed:
            salary_date = get_date(offset, 1)
            db.session.add(
                Income(
                    user_id=demo_user.id,
                    amount=base_salary,
                    source="Salary",
                    description="Monthly corporate salary deposit (Demo Data)",
                    income_date=salary_date,
                )
            )
            if extra_amt > 0:
                extra_date = get_date(offset, 15)
                db.session.add(
                    Income(
                        user_id=demo_user.id,
                        amount=extra_amt,
                        source="Bonus" if offset == 0 else "Freelance Client A",
                        description="Performance incentive bonus (Demo Data)",
                        income_date=extra_date,
                    )
                )

        # 3. Seed Realistic Expenses for Current Month & Previous Months
        # Standard monthly expense blueprint
        expense_templates = [
            {"cat": "Rent", "amt": 15000.0, "day": 2, "desc": "Apartment monthly rent payment"},
            {"cat": "Groceries", "amt": 6500.0, "day": 5, "desc": "Supermarket fresh groceries and pantry supplies"},
            {"cat": "Food", "amt": 4200.0, "day": 10, "desc": "Weekend dining out and coffee runs"},
            {"cat": "Transport", "amt": 2800.0, "day": 12, "desc": "Metro card recharge and cab rides"},
            {"cat": "Utilities", "amt": 2400.0, "day": 14, "desc": "High-speed broadband and electricity bill"},
            {"cat": "Entertainment", "amt": 1500.0, "day": 18, "desc": "Streaming subscriptions and cinema tickets"},
            {"cat": "Healthcare", "amt": 1200.0, "day": 22, "desc": "Prescription medicines and dental checkup"},
            {"cat": "Shopping", "amt": 2000.0, "day": 25, "desc": "Apparel and personal care essentials"},
        ]

        for offset in range(4):
            for tpl in expense_templates:
                # Add slight realistic variance for previous months
                variance_mult = 1.0 if offset == 0 else (0.95 + (offset * 0.03))
                actual_amt = round(tpl["amt"] * variance_mult, 2)
                exp_date = get_date(offset, tpl["day"])

                db.session.add(
                    Expense(
                        user_id=demo_user.id,
                        amount=actual_amt,
                        category=tpl["cat"],
                        description=f"{tpl['desc']} (Demo Data)",
                        expense_date=exp_date,
                    )
                )

        # 4. Seed Monthly Budgets for Current Month
        budget_limits = [
            ("Rent", 15000.0),
            ("Groceries", 6000.0),       # Approaching limit
            ("Food", 3500.0),            # Exceeded budget! (Great for demonstrating red alerts)
            ("Transport", 3000.0),       # Within budget (Green)
            ("Utilities", 2500.0),       # Within budget (Green)
            ("Entertainment", 2000.0),   # Within budget (Green)
            ("Shopping", 2500.0),        # Within budget (Green)
            ("Healthcare", 2000.0),      # Within budget (Green)
        ]

        for cat, limit_amt in budget_limits:
            db.session.add(
                Budget(
                    user_id=demo_user.id,
                    category=cat,
                    amount=limit_amt,
                    month=current_month,
                    year=current_year,
                )
            )

        # 5. Seed Savings Goals
        # Goal 1: Emergency Fund
        ef_goal = SavingsGoal(
            user_id=demo_user.id,
            name="Emergency Fund",
            target_amount=100000.0,
            current_amount=45000.0,
            target_date=date(current_year + 1, 6, 30),
            description="6 months baseline safety net for emergency expenses (Demo Data)",
        )
        db.session.add(ef_goal)
        db.session.flush()

        # Add contributions to Emergency Fund
        db.session.add(
            SavingsContribution(
                goal_id=ef_goal.id,
                amount=25000.0,
                contribution_date=get_date(2, 5),
                description="Initial reserve allocation",
            )
        )
        db.session.add(
            SavingsContribution(
                goal_id=ef_goal.id,
                amount=10000.0,
                contribution_date=get_date(1, 5),
                description="Salary savings transfer",
            )
        )
        db.session.add(
            SavingsContribution(
                goal_id=ef_goal.id,
                amount=10000.0,
                contribution_date=get_date(0, 5),
                description="Current month savings deposit",
            )
        )

        # Goal 2: Tech Upgrade / New Laptop
        laptop_goal = SavingsGoal(
            user_id=demo_user.id,
            name="New Laptop",
            target_amount=80000.0,
            current_amount=48000.0,
            target_date=date(current_year, 12, 31),
            description="Workstation development machine replacement (Demo Data)",
        )
        db.session.add(laptop_goal)
        db.session.flush()

        db.session.add(
            SavingsContribution(
                goal_id=laptop_goal.id,
                amount=48000.0,
                contribution_date=get_date(1, 15),
                description="Accumulated project bonus",
            )
        )

        # Goal 3: Annual Vacation
        vacation_goal = SavingsGoal(
            user_id=demo_user.id,
            name="Vacation",
            target_amount=35000.0,
            current_amount=12000.0,
            target_date=date(current_year + 1, 3, 31),
            description="Himalayan trekking holiday (Demo Data)",
        )
        db.session.add(vacation_goal)
        db.session.flush()

        db.session.add(
            SavingsContribution(
                goal_id=vacation_goal.id,
                amount=12000.0,
                contribution_date=get_date(0, 10),
                description="Monthly leisure savings pool",
            )
        )

        db.session.commit()
        print("Successfully seeded all demonstration financial data!")
        print("Demo credentials:")
        print("  Email:    demo@example.com")
        print("  Password: Demo@12345")
        print("  Persona:  Salaried Professional")


if __name__ == "__main__":
    seed_database()
