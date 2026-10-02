from datetime import date
from app.models import db, Income
from app.services.financial_service import calculate_total_income
from tests.conftest import login


def test_add_income(client, test_user, app):
    """Test creating an income record."""
    login(client, email=test_user.email, password="Password123")

    response = client.post(
        "/income/add",
        data={
            "amount": "45000.50",
            "source": "Salary",
            "income_date": "2026-09-01",
            "description": "Monthly paycheck",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Successfully recorded income" in response.data

    with app.app_context():
        inc = Income.query.filter_by(user_id=test_user.id).first()
        assert inc is not None
        assert inc.amount == 45000.50
        assert inc.source == "Salary"


def test_add_income_invalid_amount(client, test_user):
    """Test rejecting negative or zero income."""
    login(client, email=test_user.email, password="Password123")

    response = client.post(
        "/income/add",
        data={
            "amount": "-500",
            "source": "Salary",
            "income_date": "2026-09-01",
        },
        follow_redirects=True,
    )
    assert b"must be greater than zero" in response.data


def test_edit_income(client, test_user, app):
    """Test modifying existing income."""
    login(client, email=test_user.email, password="Password123")

    with app.app_context():
        inc = Income(
            user_id=test_user.id,
            amount=30000.0,
            source="Salary",
            income_date=date(2026, 9, 1),
        )
        db.session.add(inc)
        db.session.commit()
        inc_id = inc.id

    response = client.post(
        f"/income/edit/{inc_id}",
        data={
            "amount": "35000.0",
            "source": "Business",
            "income_date": "2026-09-01",
            "description": "Updated revenue",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"updated successfully" in response.data

    with app.app_context():
        updated = db.session.get(Income, inc_id)
        assert updated.amount == 35000.0
        assert updated.source == "Business"


def test_delete_income(client, test_user, app):
    """Test removing an income record."""
    login(client, email=test_user.email, password="Password123")

    with app.app_context():
        inc = Income(
            user_id=test_user.id,
            amount=5000.0,
            source="Bonus",
            income_date=date(2026, 9, 1),
        )
        db.session.add(inc)
        db.session.commit()
        inc_id = inc.id

    response = client.post(f"/income/delete/{inc_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"Income entry removed" in response.data

    with app.app_context():
        assert db.session.get(Income, inc_id) is None


def test_income_calculation_service(app, test_user):
    """Test deterministic Python income summation service."""
    with app.app_context():
        # Empty user has 0 income
        assert calculate_total_income(test_user.id, 9, 2026) == 0.0

        # Add multiple transactions
        db.session.add(Income(user_id=test_user.id, amount=50000.0, source="Salary", income_date=date(2026, 9, 1)))
        db.session.add(Income(user_id=test_user.id, amount=8500.0, source="Bonus", income_date=date(2026, 9, 15)))
        # Transaction in different month
        db.session.add(Income(user_id=test_user.id, amount=40000.0, source="Salary", income_date=date(2026, 8, 1)))
        db.session.commit()

        total_sep = calculate_total_income(test_user.id, 9, 2026)
        total_aug = calculate_total_income(test_user.id, 8, 2026)
        assert total_sep == 58500.0
        assert total_aug == 40000.0
