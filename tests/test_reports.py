from datetime import date
from app.models import db, Income, Expense, Budget, SavingsGoal
from app.services.report_service import generate_monthly_report_data, generate_csv_report
from app.services.financial_service import get_financial_health_indicators


def test_monthly_report_data_assembly(app, test_user):
    """Test comprehensive monthly report generation service."""
    with app.app_context():
        # Setup financial records for 09/2026
        db.session.add(Income(user_id=test_user.id, amount=60000.0, source="Salary", income_date=date(2026, 9, 1)))
        db.session.add(Income(user_id=test_user.id, amount=10000.0, source="Bonus", income_date=date(2026, 9, 15)))

        db.session.add(Expense(user_id=test_user.id, amount=15000.0, category="Rent", expense_date=date(2026, 9, 2)))
        db.session.add(Expense(user_id=test_user.id, amount=5000.0, category="Food", expense_date=date(2026, 9, 5)))
        db.session.add(Expense(user_id=test_user.id, amount=3000.0, category="Transport", expense_date=date(2026, 9, 10)))

        db.session.add(Budget(user_id=test_user.id, category="Rent", amount=15000.0, month=9, year=2026))
        db.session.add(Budget(user_id=test_user.id, category="Food", amount=4000.0, month=9, year=2026))

        db.session.add(
            SavingsGoal(
                user_id=test_user.id,
                name="Emergency Reserve",
                target_amount=100000.0,
                current_amount=35000.0,
                target_date=date(2027, 6, 30),
            )
        )
        db.session.commit()

        report = generate_monthly_report_data(test_user.id, 9, 2026)

        assert report["total_income"] == 70000.0
        assert report["total_expenses"] == 23000.0
        assert report["savings"] == 47000.0
        assert report["savings_rate"] == round(47000.0 / 70000.0 * 100, 1)
        assert len(report["income_items"]) == 2
        assert len(report["expense_items"]) == 3
        assert len(report["goals"]) == 1


def test_csv_report_generation(app, test_user):
    """Test exporting monthly financial statement to downloadable CSV text."""
    with app.app_context():
        db.session.add(Income(user_id=test_user.id, amount=50000.0, source="Salary", income_date=date(2026, 9, 1)))
        db.session.add(Expense(user_id=test_user.id, amount=20000.0, category="Rent", expense_date=date(2026, 9, 2)))
        db.session.commit()

        report_data = generate_monthly_report_data(test_user.id, 9, 2026)
        csv_content = generate_csv_report(report_data)

        assert "PERSONAL FINANCE ADVISOR - MONTHLY STATEMENT" in csv_content
        assert "Total Income,50000.00" in csv_content
        assert "Total Expenses,20000.00" in csv_content
        assert "Net Savings,30000.00" in csv_content


def test_financial_health_indicators(app, test_user):
    """Test non-arbitrary indicators: savings rate, adherence %, over-budget count, and emergency fund."""
    with app.app_context():
        db.session.add(Income(user_id=test_user.id, amount=50000.0, source="Salary", income_date=date(2026, 9, 1)))
        db.session.add(Expense(user_id=test_user.id, amount=10000.0, category="Rent", expense_date=date(2026, 9, 2)))
        db.session.add(Budget(user_id=test_user.id, category="Rent", amount=12000.0, month=9, year=2026))

        db.session.add(
            SavingsGoal(
                user_id=test_user.id,
                name="Emergency Fund",
                target_amount=100000.0,
                current_amount=40000.0,
                target_date=date(2027, 1, 1),
            )
        )
        db.session.commit()

        health = get_financial_health_indicators(test_user.id, 9, 2026)

        assert health["savings_rate"] == 80.0
        assert health["savings_status"] == "Optimal"
        assert health["over_budget_count"] == 0
        assert health["budget_adherence"] == 100.0
        assert health["emergency_fund_progress"] == 40.0
