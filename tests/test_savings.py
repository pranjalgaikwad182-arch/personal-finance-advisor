from datetime import date
from app.models import db, SavingsGoal, SavingsContribution
from tests.conftest import login


def test_create_savings_goal(client, test_user, app):
    """Test creating a new savings goal with initial deposit."""
    login(client, email=test_user.email, password="Password123")

    response = client.post(
        "/savings/add",
        data={
            "name": "Emergency Fund",
            "target_amount": "100000.0",
            "current_amount": "20000.0",
            "target_date": "2027-06-30",
            "description": "Six months baseline safety net",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"created successfully" in response.data

    with app.app_context():
        goal = SavingsGoal.query.filter_by(user_id=test_user.id, name="Emergency Fund").first()
        assert goal is not None
        assert goal.target_amount == 100000.0
        assert goal.current_amount == 20000.0
        assert goal.progress_pct == 20.0
        assert goal.remaining_amount == 80000.0


def test_contribute_to_savings_goal(client, test_user, app):
    """Test adding a contribution to an existing savings goal."""
    login(client, email=test_user.email, password="Password123")

    with app.app_context():
        goal = SavingsGoal(
            user_id=test_user.id,
            name="New Laptop",
            target_amount=80000.0,
            current_amount=30000.0,
            target_date=date(2027, 1, 1),
        )
        db.session.add(goal)
        db.session.commit()
        goal_id = goal.id

    response = client.post(
        f"/savings/{goal_id}/contribute",
        data={
            "amount": "10000.0",
            "contribution_date": "2026-09-15",
            "description": "Bonus payout deposit",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Contributed" in response.data

    with app.app_context():
        updated_goal = db.session.get(SavingsGoal, goal_id)
        assert updated_goal.current_amount == 40000.0
        assert updated_goal.progress_pct == 50.0
        assert updated_goal.remaining_amount == 40000.0

        # Check contribution ledger
        assert len(updated_goal.contributions) == 1
        assert updated_goal.contributions[0].amount == 10000.0


def test_monthly_required_calculation(app, test_user):
    """Test mathematical calculation of required monthly contribution."""
    with app.app_context():
        today = date.today()
        # Goal 10 months in the future
        target = date(today.year + (1 if today.month > 2 else 0), (today.month + 10) % 12 or 12, 1)

        goal = SavingsGoal(
            user_id=test_user.id,
            name="Vacation Fund",
            target_amount=50000.0,
            current_amount=10000.0,
            target_date=target,
        )
        db.session.add(goal)
        db.session.commit()

        assert goal.remaining_amount == 40000.0
        assert goal.months_remaining > 0
        assert goal.monthly_required > 0
        assert goal.monthly_required == round(40000.0 / goal.months_remaining, 2)


def test_delete_savings_goal(client, test_user, app):
    """Test deleting a savings goal and its cascading contributions."""
    login(client, email=test_user.email, password="Password123")

    with app.app_context():
        goal = SavingsGoal(
            user_id=test_user.id,
            name="Vehicle Fund",
            target_amount=200000.0,
            current_amount=15000.0,
            target_date=date(2028, 1, 1),
        )
        db.session.add(goal)
        db.session.commit()
        goal_id = goal.id

    response = client.post(f"/savings/delete/{goal_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"deleted" in response.data

    with app.app_context():
        assert db.session.get(SavingsGoal, goal_id) is None
