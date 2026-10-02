"""
seed_data.py - Populates comprehensive demonstration data for Personal Finance Advisor Bot.
Includes 4 real-world user scenarios:
1. Salaried Professional (salaried@example.com / Password123 or demo@example.com / Demo@12345)
2. College Student (student@example.com / Password123)
3. Freelancer (freelancer@example.com / Password123)
4. Household Manager (household@example.com / Password123)
"""
import os
from datetime import date, timedelta
from app import create_app
from models import (
    db,
    User,
    Income,
    Expense,
    Budget,
    SavingsGoal,
    SavingsContribution,
    FinancialReport,
)


def seed_database():
    app = create_app(os.getenv("FLASK_ENV", "development"))

    with app.app_context():
        # Ensure database tables exist
        db.create_all()

        today = date.today()
        current_year = today.year
        current_month = today.month

        def get_date(offset_months, day):
            yr = current_year
            mo = current_month - offset_months
            while mo <= 0:
                mo += 12
                yr -= 1
            return date(yr, mo, min(day, 28))

        # ==============================================================================
        # Scenario 1: Salaried Professional (salaried@example.com / demo@example.com)
        # ==============================================================================
        print("Seeding Scenario 1: Salaried Professional...")
        salaried_emails = ["salaried@example.com", "demo@example.com"]
        for email in salaried_emails:
            old_user = User.query.filter_by(email=email).first()
            if old_user:
                db.session.delete(old_user)
            db.session.commit()

            user = User(
                name="Rahul Sharma",
                email=email,
                user_type="Salaried Professional",
            )
            user.set_password("Demo@12345" if email == "demo@example.com" else "Password123")
            db.session.add(user)
            db.session.commit()

            # Incomes across past 4 months
            months_data = [
                (0, 60000.0, 5000.0),   # Current month: Salary + Bonus
                (1, 60000.0, 0.0),      # Last month
                (2, 60000.0, 4000.0),   # 2 months ago
                (3, 58000.0, 0.0),      # 3 months ago
            ]
            for offset, base_sal, bonus in months_data:
                db.session.add(Income(
                    user_id=user.id,
                    amount=base_sal,
                    source="Salary",
                    description="Monthly corporate salary credit",
                    income_date=get_date(offset, 1),
                ))
                if bonus > 0:
                    db.session.add(Income(
                        user_id=user.id,
                        amount=bonus,
                        source="Bonus",
                        description="Performance quarterly bonus",
                        income_date=get_date(offset, 15),
                    ))

            # Expenses across past 4 months
            expense_plan = [
                {"cat": "Rent", "amt": 16000.0, "day": 2, "desc": "Apartment monthly rent"},
                {"cat": "Groceries", "amt": 6500.0, "day": 5, "desc": "Supermarket essentials and pantry"},
                {"cat": "Food", "amt": 4500.0, "day": 10, "desc": "Dining out and weekend meals"},
                {"cat": "Transport", "amt": 3000.0, "day": 12, "desc": "Metro smart card recharge & fuel"},
                {"cat": "Utilities", "amt": 2500.0, "day": 15, "desc": "Electricity, water and high-speed Wi-Fi"},
                {"cat": "Entertainment", "amt": 2000.0, "day": 18, "desc": "Streaming platforms & movie tickets"},
                {"cat": "Shopping", "amt": 2500.0, "day": 22, "desc": "Apparel and personal care"},
                {"cat": "Healthcare", "amt": 1200.0, "day": 25, "desc": "Health insurance copay and medicines"},
            ]
            for offset in range(4):
                for item in expense_plan:
                    db.session.add(Expense(
                        user_id=user.id,
                        amount=item["amt"],
                        category=item["cat"],
                        description=item["desc"],
                        expense_date=get_date(offset, item["day"]),
                    ))

            # Budgets for current month
            budgets_plan = [
                ("Rent", 17000.0),
                ("Groceries", 7000.0),
                ("Food", 4000.0),
                ("Transport", 3500.0),
                ("Utilities", 3000.0),
                ("Entertainment", 2500.0),
                ("Shopping", 3000.0),
                ("Healthcare", 2000.0),
            ]
            for cat, limit in budgets_plan:
                db.session.add(Budget(
                    user_id=user.id,
                    category=cat,
                    amount=limit,
                    month=current_month,
                    year=current_year,
                ))

            # Savings Goals
            g1 = SavingsGoal(
                user_id=user.id,
                name="Emergency Liquidity Fund",
                target_amount=180000.0,
                current_amount=95000.0,
                target_date=date(current_year + 1, 6, 30),
                description="6 months of essential living expenses buffer",
            )
            g2 = SavingsGoal(
                user_id=user.id,
                name="New Tech Laptop",
                target_amount=85000.0,
                current_amount=45000.0,
                target_date=date(current_year, 12, 31),
                description="MacBook Pro upgrade for professional development",
            )
            db.session.add_all([g1, g2])
            db.session.commit()

            # Snapshot report
            db.session.add(FinancialReport(
                user_id=user.id,
                month=current_month,
                year=current_year,
                total_income=65000.0,
                total_expenses=38200.0,
                total_savings=26800.0,
            ))
            db.session.commit()

        # ==============================================================================
        # Scenario 2: College Student (student@example.com / Password123)
        # ==============================================================================
        print("Seeding Scenario 2: College Student...")
        old_student = User.query.filter_by(email="student@example.com").first()
        if old_student:
            db.session.delete(old_student)
            db.session.commit()

        student = User(
            name="Aarav Verma",
            email="student@example.com",
            user_type="Student",
        )
        student.set_password("Password123")
        db.session.add(student)
        db.session.commit()

        for offset in range(3):
            db.session.add(Income(
                user_id=student.id,
                amount=12000.0,
                source="Allowance",
                description="Monthly parent education allowance",
                income_date=get_date(offset, 1),
            ))
            db.session.add(Income(
                user_id=student.id,
                amount=3000.0,
                source="Freelance",
                description="Campus coding tutoring stipend",
                income_date=get_date(offset, 14),
            ))

            student_expenses = [
                ("Food", 4200.0, 3, "Campus cafeteria and snack breaks"),
                ("Education", 2800.0, 7, "Semester textbooks & lab subscriptions"),
                ("Transport", 1500.0, 11, "Student bus & subway monthly pass"),
                ("Entertainment", 1200.0, 16, "Weekend movies and gaming pass"),
                ("Shopping", 1000.0, 20, "Stationery and personal items"),
            ]
            for cat, amt, day, desc in student_expenses:
                db.session.add(Expense(
                    user_id=student.id,
                    amount=amt,
                    category=cat,
                    description=desc,
                    expense_date=get_date(offset, day),
                ))

        for cat, limit in [("Food", 4500.0), ("Education", 3000.0), ("Transport", 1600.0), ("Entertainment", 1000.0), ("Shopping", 1200.0)]:
            db.session.add(Budget(
                user_id=student.id,
                category=cat,
                amount=limit,
                month=current_month,
                year=current_year,
            ))

        db.session.add(SavingsGoal(
            user_id=student.id,
            name="Cloud Certification Exam",
            target_amount=15000.0,
            current_amount=9500.0,
            target_date=date(current_year, 11, 30),
            description="AWS Certified Developer Associate exam fee",
        ))
        db.session.commit()

        # ==============================================================================
        # Scenario 3: Freelancer (freelancer@example.com / Password123)
        # ==============================================================================
        print("Seeding Scenario 3: Freelancer...")
        old_free = User.query.filter_by(email="freelancer@example.com").first()
        if old_free:
            db.session.delete(old_free)
            db.session.commit()

        freelancer = User(
            name="Priya Patel",
            email="freelancer@example.com",
            user_type="Freelancer",
        )
        freelancer.set_password("Password123")
        db.session.add(freelancer)
        db.session.commit()

        freelance_incomes = [
            (0, 45000.0, 30000.0), # Current month: ₹75,000 total
            (1, 40000.0, 15000.0), # Last month: ₹55,000 total
            (2, 60000.0, 25000.0), # 2 months ago: ₹85,000 total
        ]
        for offset, client1, client2 in freelance_incomes:
            db.session.add(Income(
                user_id=freelancer.id,
                amount=client1,
                source="Freelance",
                description="Client Alpha UI/UX milestone retainer",
                income_date=get_date(offset, 4),
            ))
            db.session.add(Income(
                user_id=freelancer.id,
                amount=client2,
                source="Freelance",
                description="Client Beta Frontend development sprint",
                income_date=get_date(offset, 18),
            ))

            free_expenses = [
                ("Rent", 18000.0, 2, "Co-living studio and home office"),
                ("Groceries", 7000.0, 6, "Organic pantry and healthy groceries"),
                ("Utilities", 3500.0, 10, "Gigabit fiber internet & electricity"),
                ("Food", 5000.0, 14, "Coffee shop co-working & dinners"),
                ("Transport", 2500.0, 17, "Cab commutes for client meetings"),
                ("Healthcare", 2000.0, 21, "Private health insurance premium"),
            ]
            for cat, amt, day, desc in free_expenses:
                db.session.add(Expense(
                    user_id=freelancer.id,
                    amount=amt,
                    category=cat,
                    description=desc,
                    expense_date=get_date(offset, day),
                ))

        for cat, limit in [("Rent", 18000.0), ("Groceries", 7500.0), ("Utilities", 4000.0), ("Food", 4500.0), ("Healthcare", 2500.0)]:
            db.session.add(Budget(
                user_id=freelancer.id,
                category=cat,
                amount=limit,
                month=current_month,
                year=current_year,
            ))

        db.session.add(SavingsGoal(
            user_id=freelancer.id,
            name="Freelancer 9-Month Emergency Runway",
            target_amount=350000.0,
            current_amount=210000.0,
            target_date=date(current_year + 1, 8, 31),
            description="Safety cushion to absorb volatile client payment cycles",
        ))
        db.session.commit()

        # ==============================================================================
        # Scenario 4: Household Manager (household@example.com / Password123)
        # ==============================================================================
        print("Seeding Scenario 4: Household Manager...")
        old_house = User.query.filter_by(email="household@example.com").first()
        if old_house:
            db.session.delete(old_house)
            db.session.commit()

        household = User(
            name="Sunita & Vikram Desai",
            email="household@example.com",
            user_type="Household Manager",
        )
        household.set_password("Password123")
        db.session.add(household)
        db.session.commit()

        for offset in range(3):
            db.session.add(Income(
                user_id=household.id,
                amount=85000.0,
                source="Salary",
                description="Consolidated dual household family income",
                income_date=get_date(offset, 1),
            ))

            house_expenses = [
                ("Groceries", 15000.0, 3, "Monthly family provisions, dairy and fruits"),
                ("Rent", 22000.0, 5, "Family apartment mortgage/rent payment"),
                ("Utilities", 7500.0, 9, "Electricity, piped cooking gas, water, internet"),
                ("Education", 8000.0, 12, "Children school fees and extracurriculars"),
                ("Healthcare", 4500.0, 16, "Family health policy and pediatric care"),
                ("Household", 5000.0, 20, "Domestic help and home maintenance"),
                ("Transport", 4000.0, 23, "Car fuel and vehicle servicing"),
            ]
            for cat, amt, day, desc in house_expenses:
                db.session.add(Expense(
                    user_id=household.id,
                    amount=amt,
                    category=cat,
                    description=desc,
                    expense_date=get_date(offset, day),
                ))

        for cat, limit in [
            ("Groceries", 16000.0),
            ("Rent", 22000.0),
            ("Utilities", 8000.0),
            ("Education", 8500.0),
            ("Healthcare", 5000.0),
            ("Household", 5500.0),
            ("Transport", 4500.0),
        ]:
            db.session.add(Budget(
                user_id=household.id,
                category=cat,
                amount=limit,
                month=current_month,
                year=current_year,
            ))

        db.session.add(SavingsGoal(
            user_id=household.id,
            name="Family Emergency Reserve",
            target_amount=300000.0,
            current_amount=165000.0,
            target_date=date(current_year + 1, 4, 30),
            description="Comprehensive household contingency fund",
        ))
        db.session.commit()

        print("================================================================")
        print(" Sample demonstration database successfully seeded!")
        print(" Test Accounts Available:")
        print(" 1. Salaried Pro:  salaried@example.com  / Password123")
        print("    (or demo):    demo@example.com      / Demo@12345")
        print(" 2. Student:       student@example.com   / Password123")
        print(" 3. Freelancer:    freelancer@example.com / Password123")
        print(" 4. Household:     household@example.com / Password123")
        print("================================================================")


if __name__ == "__main__":
    seed_database()
