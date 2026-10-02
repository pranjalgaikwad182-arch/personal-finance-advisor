from datetime import date
from app.models import db, Budget, Expense, Income
from app.services.financial_service import get_budget_status
from app.services.budget_service import generate_recommended_budgets, apply_recommended_budgets
from tests.conftest import login


def test_add_and_update_budget(client, test_user, app):
    """Test creating and updating (upserting) a category budget."""
    login(client, email=test_user.email, password="Password123")

    # 1. Create Budget
    response = client.post(
        "/budgets/add",
        data={
            "category": "Food",
            "amount": "5000.0",
            "month": "9",
            "year": "2026",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Created Food budget" in response.data

    with app.app_context():
        b = Budget.query.filter_by(user_id=test_user.id, category="Food", month=9, year=2026).first()
        assert b is not None
        assert b.amount == 5000.0

    # 2. Update same category budget for same month/year
    response = client.post(
        "/budgets/add",
        data={
            "category": "Food",
            "amount": "6000.0",
            "month": "9",
            "year": "2026",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Updated Food budget" in response.data

    with app.app_context():
        # Count should still be 1 (upsert)
        assert Budget.query.filter_by(user_id=test_user.id, category="Food", month=9, year=2026).count() == 1
        b = Budget.query.filter_by(user_id=test_user.id, category="Food", month=9, year=2026).first()
        assert b.amount == 6000.0


def test_budget_status_calculation(app, test_user):
    """
    Test budget status classification:
    - Within: < 80%
    - Approaching: 80% - 100%
    - Exceeded: > 100%
    """
    with app.app_context():
        # Category 1: Within limit (Spent 300 of 1000 = 30%)
        db.session.add(Budget(user_id=test_user.id, category="Transport", amount=1000.0, month=9, year=2026))
        db.session.add(Expense(user_id=test_user.id, category="Transport", amount=300.0, expense_date=date(2026, 9, 2)))

        # Category 2: Approaching limit (Spent 850 of 1000 = 85%)
        db.session.add(Budget(user_id=test_user.id, category="Groceries", amount=1000.0, month=9, year=2026))
        db.session.add(Expense(user_id=test_user.id, category="Groceries", amount=850.0, expense_date=date(2026, 9, 5)))

        # Category 3: Exceeded limit (Spent 1200 of 1000 = 120%)
        db.session.add(Budget(user_id=test_user.id, category="Food", amount=1000.0, month=9, year=2026))
        db.session.add(Expense(user_id=test_user.id, category="Food", amount=1200.0, expense_date=date(2026, 9, 8)))

        db.session.commit()

        status = get_budget_status(test_user.id, 9, 2026)
        item_map = {item["category"]: item for item in status["items"]}

        assert item_map["Transport"]["status"] == "within"
        assert item_map["Transport"]["status_label"] == "Within Budget"

        assert item_map["Groceries"]["status"] == "approaching"
        assert item_map["Groceries"]["status_label"] == "Approaching Limit"

        assert item_map["Food"]["status"] == "exceeded"
        assert item_map["Food"]["status_label"] == "Exceeded Budget"
        assert status["over_budget_count"] == 1


def test_auto_budget_recommendations_engine(app, test_user):
    """Test Python budget recommendation engine calculations and allocations."""
    with app.app_context():
        # Setup income 50,000
        db.session.add(Income(user_id=test_user.id, amount=50000.0, source="Salary", income_date=date(2026, 9, 1)))

        # Setup historical expenses
        db.session.add(Expense(user_id=test_user.id, amount=15000.0, category="Rent", expense_date=date(2026, 9, 1)))
        db.session.add(Expense(user_id=test_user.id, amount=5000.0, category="Food", expense_date=date(2026, 9, 5)))
        db.session.add(Expense(user_id=test_user.id, amount=2000.0, category="Transport", expense_date=date(2026, 9, 10)))
        db.session.commit()

        # Generate recommendation with 20% savings target
        rec_data = generate_recommended_budgets(test_user.id, month=9, year=2026, savings_target_pct=20.0)

        assert rec_data["income"] == 50000.0
        assert rec_data["savings_target_pct"] == 20.0
        assert rec_data["target_savings_amount"] == 10000.0
        assert rec_data["allocatable_spending"] == 40000.0
        assert len(rec_data["recommendations"]) > 0

        # Apply recommendations
        count = apply_recommended_budgets(
            test_user.id,
            [
                {"category": "Rent", "amount": 15000.0},
                {"category": "Food", "amount": 5000.0},
            ],
            month=10,
            year=2026,
        )
        assert count == 2

        applied_rent = Budget.query.filter_by(user_id=test_user.id, category="Rent", month=10, year=2026).first()
        assert applied_rent is not None
        assert applied_rent.amount == 15000.0
