import pytest
from app import create_app
from app.models import db, User


@pytest.fixture
def app():
    """Application fixture configured for isolated in-memory unit testing."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test HTTP client."""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """Primary authenticated user fixture."""
    with app.app_context():
        user = User(
            name="Test User",
            email="test@example.com",
            user_type="Salaried Professional",
        )
        user.set_password("Password123")
        db.session.add(user)
        db.session.commit()
        # Refresh from session
        user_id = user.id
    
    with app.app_context():
        return db.session.get(User, user_id)


@pytest.fixture
def other_user(app):
    """Second user fixture to rigorously test tenant data isolation."""
    with app.app_context():
        user = User(
            name="Other User",
            email="other@example.com",
            user_type="Student",
        )
        user.set_password("Password123")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with app.app_context():
        return db.session.get(User, user_id)


def login(client, email="test@example.com", password="Password123"):
    """Helper function to log in a test client."""
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )
