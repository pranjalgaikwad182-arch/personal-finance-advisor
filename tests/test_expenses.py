from datetime import date
from app.models import db, Expense
from app.services.financial_service import calculate_total_expenses, get_expenses_by_category
from tests.conftest import login


def test_add_expense(client, test_user, app):
    """Test adding an expense."""
    login(client, email=test_user.email, password="Password123")

    response = client.post(
        "/expenses/add",
        data={
            "amount": "2400.0",
            "category": "Groceries",
            "expense_date": "2026-09-05",
            "description": "Weekly pantry restock",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Recorded expense of" in response.data

    with app.app_context():
        exp = Expense.query.filter_by(user_id=test_user.id).first()
        assert exp is not None
        assert exp.amount == 2400.0
        assert exp.category == "Groceries"


def test_add_expense_invalid_amount(client, test_user):
    """Test rejecting negative or zero expense amounts."""
    login(client, email=test_user.email, password="Password123")

    response = client.post(
        "/expenses/add",
        data={
            "amount": "0",
            "category": "Food",
            "expense_date": "2026-09-05",
        },
        follow_redirects=True,
    )
    assert b"must be greater than zero" in response.data


def test_edit_expense(client, test_user, app):
    """Test editing an expense entry."""
    login(client, email=test_user.email, password="Password123")

    with app.app_context():
        exp = Expense(
            user_id=test_user.id,
            amount=1500.0,
            category="Food",
            expense_date=date(2026, 9, 5),
        )
        db.session.add(exp)
        db.session.commit()
        exp_id = exp.id

    response = client.post(
        f"/expenses/edit/{exp_id}",
        data={
            "amount": "1800.0",
            "category": "Food",
            "expense_date": "2026-09-05",
            "description": "Dinner with friends",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"updated successfully" in response.data

    with app.app_context():
        updated = db.session.get(Expense, exp_id)
        assert updated.amount == 1800.0


def test_delete_expense(client, test_user, app):
    """Test deleting an expense entry."""
    login(client, email=test_user.email, password="Password123")

    with app.app_context():
        exp = Expense(
            user_id=test_user.id,
            amount=800.0,
            category="Transport",
            expense_date=date(2026, 9, 5),
        )
        db.session.add(exp)
        db.session.commit()
        exp_id = exp.id

    response = client.post(f"/expenses/delete/{exp_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"Expense entry removed" in response.data

    with app.app_context():
        assert db.session.get(Expense, exp_id) is None


def test_expenses_by_category_service(app, test_user):
    """Test category grouping and total expense calculations."""
    with app.app_context():
        db.session.add(Expense(user_id=test_user.id, amount=12000.0, category="Rent", expense_date=date(2026, 9, 1)))
        db.session.add(Expense(user_id=test_user.id, amount=3000.0, category="Food", expense_date=date(2026, 9, 3)))
        db.session.add(Expense(user_id=test_user.id, amount=2000.0, category="Food", expense_date=date(2026, 9, 7)))
        db.session.add(Expense(user_id=test_user.id, amount=1500.0, category="Utilities", expense_date=date(2026, 9, 10)))
        db.session.commit()

        total = calculate_total_expenses(test_user.id, 9, 2026)
        cat_map = get_expenses_by_category(test_user.id, 9, 2026)

        assert total == 18500.0
        assert cat_map["Rent"] == 12000.0
        assert cat_map["Food"] == 5000.0
        assert cat_map["Utilities"] == 1500.0
