import json
import pytest
from models import db, User, Income, Expense, Budget, SavingsGoal
from services.ai_engine import answer_financial_query


def test_api_register_and_login(client):
    """Test POST /api/register and POST /api/login."""
    # Register
    res = client.post(
        "/api/register",
        json={
            "name": "API Test User",
            "email": "apitest@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
            "user_type": "Freelancer",
        },
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["email"] == "apitest@example.com"
    assert data["user"]["user_type"] == "Freelancer"

    # Logout
    client.post("/api/logout")

    # Login
    res_login = client.post(
        "/api/login",
        json={"email": "apitest@example.com", "password": "Password123"},
    )
    assert res_login.status_code == 200
    data_login = res_login.get_json()
    assert data_login["success"] is True
    assert data_login["user"]["name"] == "API Test User"


def test_api_income_crud(client, test_user):
    """Test GET, POST, PUT, DELETE for /api/income."""
    # Login session
    client.post("/login", data={"email": "test@example.com", "password": "Password123"})

    # POST income
    res = client.post(
        "/api/income",
        json={
            "amount": 45000.0,
            "source": "Salary",
            "date": "2026-10-01",
            "description": "Monthly paycheck",
        },
    )
    assert res.status_code == 201
    inc_data = res.get_json()["income"]
    inc_id = inc_data["id"]

    # GET income
    res_get = client.get("/api/income?month=10&year=2026")
    assert res_get.status_code == 200
    assert res_get.get_json()["count"] >= 1
    assert res_get.get_json()["total_amount"] >= 45000.0

    # PUT income
    res_put = client.put(f"/api/income/{inc_id}", json={"amount": 48000.0})
    assert res_put.status_code == 200
    assert res_put.get_json()["income"]["amount"] == 48000.0

    # DELETE income
    res_del = client.delete(f"/api/income/{inc_id}")
    assert res_del.status_code == 200


def test_api_expenses_crud(client, test_user):
    """Test GET, POST, PUT, DELETE for /api/expenses."""
    client.post("/login", data={"email": "test@example.com", "password": "Password123"})

    # POST expense
    res = client.post(
        "/api/expenses",
        json={
            "amount": 3500.0,
            "category": "Food",
            "date": "2026-10-02",
            "description": "Supermarket snacks",
        },
    )
    assert res.status_code == 201
    exp_id = res.get_json()["expense"]["id"]

    # GET expenses with search filter
    res_get = client.get("/api/expenses?search=snacks")
    assert res_get.status_code == 200
    assert res_get.get_json()["count"] == 1

    # PUT expense
    res_put = client.put(f"/api/expenses/{exp_id}", json={"amount": 3800.0})
    assert res_put.status_code == 200
    assert res_put.get_json()["expense"]["amount"] == 3800.0

    # DELETE expense
    res_del = client.delete(f"/api/expenses/{exp_id}")
    assert res_del.status_code == 200


def test_api_budgets_and_savings_goals(client, test_user):
    """Test /api/budgets and /api/savings-goals."""
    client.post("/login", data={"email": "test@example.com", "password": "Password123"})

    # Create budget
    res_b = client.post(
        "/api/budgets",
        json={
            "category": "Food",
            "amount": 6000.0,
            "month": 10,
            "year": 2026,
        },
    )
    assert res_b.status_code == 201

    # Create savings goal
    res_g = client.post(
        "/api/savings-goals",
        json={
            "name": "Vacation Fund",
            "target_amount": 50000.0,
            "current_amount": 15000.0,
            "deadline": "2027-04-30",
            "description": "Trip to mountains",
        },
    )
    assert res_g.status_code == 201
    goal = res_g.get_json()["goal"]
    assert goal["progress_pct"] == 30.0
    assert goal["remaining_amount"] == 35000.0


def test_api_advisor_chat_engine(client, test_user):
    """Test /api/advisor/chat endpoint and natural language rule responses."""
    client.post("/login", data={"email": "test@example.com", "password": "Password123"})

    # Seed income and expense for test user
    client.post("/api/income", json={"amount": 50000.0, "source": "Salary", "date": "2026-10-01"})
    client.post("/api/expenses", json={"amount": 12000.0, "category": "Rent", "date": "2026-10-02"})

    # Ask spending query
    res = client.post(
        "/api/advisor/chat",
        json={"query": "How much did I spend this month?", "month": 10, "year": 2026},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "₹12,000.00" in data["answer"] or "12,000" in data["answer"]
    assert data["mode"] == "rule_based"

    # Ask budget query
    res_b = client.post(
        "/api/advisor/chat",
        json={"query": "Give me a budget for next month.", "month": 10, "year": 2026},
    )
    assert res_b.status_code == 200
    assert res_b.get_json()["success"] is True


def test_api_report_snapshot(client, test_user):
    """Test GET /api/reports/<year>/<month>."""
    client.post("/login", data={"email": "test@example.com", "password": "Password123"})
    res = client.get("/api/reports/2026/10")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "total_income" in data
    assert "total_expenses" in data
    assert "savings" in data
    assert "savings_rate" in data
