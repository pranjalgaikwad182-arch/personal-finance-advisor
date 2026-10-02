from app.models import User
from tests.conftest import login


def test_password_hashing(app):
    """Ensure passwords are cryptographically hashed and never stored as plaintext."""
    with app.app_context():
        user = User(name="Crypto Test", email="crypto@example.com")
        user.set_password("MySecurePass@123")
        assert user.password_hash != "MySecurePass@123"
        assert len(user.password_hash) > 20
        assert user.check_password("MySecurePass@123") is True
        assert user.check_password("WrongPassword") is False


def test_register_success(client, app):
    """Test standard user registration flow."""
    response = client.post(
        "/register",
        data={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
            "user_type": "Student",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Account created successfully" in response.data

    with app.app_context():
        user = User.query.filter_by(email="jane@example.com").first()
        assert user is not None
        assert user.name == "Jane Doe"
        assert user.user_type == "Student"


def test_register_duplicate_email(client, test_user):
    """Test registration with existing email address is rejected."""
    response = client.post(
        "/register",
        data={
            "name": "Another Person",
            "email": test_user.email,
            "password": "Password123",
            "confirm_password": "Password123",
            "user_type": "Freelancer",
        },
        follow_redirects=True,
    )
    assert b"already exists" in response.data


def test_register_password_mismatch(client):
    """Test registration with mismatched passwords is rejected."""
    response = client.post(
        "/register",
        data={
            "name": "Mismatch User",
            "email": "mismatch@example.com",
            "password": "Password123",
            "confirm_password": "DifferentPassword123",
            "user_type": "Salaried Professional",
        },
        follow_redirects=True,
    )
    assert b"Passwords do not match" in response.data


def test_register_short_password(client):
    """Test registration with password < 6 chars is rejected."""
    response = client.post(
        "/register",
        data={
            "name": "Short Pass User",
            "email": "short@example.com",
            "password": "123",
            "confirm_password": "123",
            "user_type": "Salaried Professional",
        },
        follow_redirects=True,
    )
    assert b"at least 6 characters" in response.data


def test_login_success(client, test_user):
    """Test valid user login."""
    response = login(client, email=test_user.email, password="Password123")
    assert response.status_code == 200
    assert b"Welcome back" in response.data


def test_login_invalid_password(client, test_user):
    """Test login with wrong password."""
    response = login(client, email=test_user.email, password="IncorrectPassword")
    assert b"Invalid email or password" in response.data


def test_login_nonexistent_user(client):
    """Test login with unregistered email."""
    response = login(client, email="doesnotexist@example.com", password="Password123")
    assert b"Invalid email or password" in response.data


def test_logout(client, test_user):
    """Test user logout."""
    login(client, email=test_user.email, password="Password123")
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"successfully logged out" in response.data
