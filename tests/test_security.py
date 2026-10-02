from datetime import date
from app.models import db, Income, Expense, Budget, SavingsGoal
from tests.conftest import login


def test_unauthorized_dashboard_access_redirects(client):
    """Ensure unauthenticated requests to protected endpoints redirect to login."""
    protected_urls = [
        "/dashboard",
        "/income/",
        "/expenses/",
        "/budgets/",
        "/savings/",
        "/advisor/",
        "/reports/",
        "/profile/",
    ]
    for url in protected_urls:
        response = client.get(url)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


def test_user_cannot_access_or_edit_other_user_income(client, test_user, other_user, app):
    """Ensure User A cannot edit or delete User B's income transactions."""
    # Create income belonging to other_user
    with app.app_context():
        other_inc = Income(
            user_id=other_user.id,
            amount=50000.0,
            source="Client X",
            income_date=date(2026, 9, 1),
        )
        db.session.add(other_inc)
        db.session.commit()
        target_id = other_inc.id

    # Log in as test_user
    login(client, email=test_user.email, password="Password123")

    # Attempt to edit other_user's income
    response = client.post(
        f"/income/edit/{target_id}",
        data={"amount": "1.0", "source": "Hacked", "income_date": "2026-09-01"},
    )
    # Must return 404 (or forbidden) due to strict tenant isolation filter_by(id, user_id)
    assert response.status_code == 404

    # Attempt to delete other_user's income
    delete_response = client.post(f"/income/delete/{target_id}")
    assert delete_response.status_code == 404

    # Verify other_user's data was not modified or deleted
    with app.app_context():
        inc = db.session.get(Income, target_id)
        assert inc is not None
        assert inc.amount == 50000.0
        assert inc.source == "Client X"


def test_user_cannot_edit_other_user_expense(client, test_user, other_user, app):
    """Ensure User A cannot edit or delete User B's expense records."""
    with app.app_context():
        other_exp = Expense(
            user_id=other_user.id,
            amount=3000.0,
            category="Rent",
            expense_date=date(2026, 9, 1),
        )
        db.session.add(other_exp)
        db.session.commit()
        exp_id = other_exp.id

    login(client, email=test_user.email, password="Password123")

    # Try to edit
    res_edit = client.post(
        f"/expenses/edit/{exp_id}",
        data={"amount": "10.0", "category": "Food", "expense_date": "2026-09-01"},
    )
    assert res_edit.status_code == 404

    # Try to delete
    res_del = client.post(f"/expenses/delete/{exp_id}")
    assert res_del.status_code == 404

    with app.app_context():
        exp = db.session.get(Expense, exp_id)
        assert exp is not None
        assert exp.amount == 3000.0


def test_user_cannot_tamper_with_other_user_savings_goal(client, test_user, other_user, app):
    """Ensure User A cannot modify, delete, or contribute to User B's savings goal."""
    with app.app_context():
        other_goal = SavingsGoal(
            user_id=other_user.id,
            name="Private Goal",
            target_amount=100000.0,
            current_amount=20000.0,
            target_date=date(2027, 1, 1),
        )
        db.session.add(other_goal)
        db.session.commit()
        goal_id = other_goal.id

    login(client, email=test_user.email, password="Password123")

    # Try to contribute
    res_contrib = client.post(
        f"/savings/{goal_id}/contribute",
        data={"amount": "5000.0", "contribution_date": "2026-09-01"},
    )
    assert res_contrib.status_code == 404

    # Try to edit
    res_edit = client.post(
        f"/savings/edit/{goal_id}",
        data={"name": "Hacked Goal", "target_amount": "1.0", "target_date": "2027-01-01"},
    )
    assert res_edit.status_code == 404

    # Try to delete
    res_del = client.post(f"/savings/delete/{goal_id}")
    assert res_del.status_code == 404
