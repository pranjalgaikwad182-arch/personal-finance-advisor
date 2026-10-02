import json
import pytest
from app.services.ai_advisor_service import (
    CATEGORY_TIPS,
    GOAL_DESCRIPTIONS,
    build_prompt,
    extract_json,
    generate_rule_based_analysis,
    analyze_finances_with_gemini,
)


def test_build_prompt_includes_categories_and_goals():
    """Verify build_prompt incorporates categories, thresholds, and financial goals."""
    income = 50000.0
    expenses = {"rent": 15000.0, "food": 6000.0, "transport": 3000.0}
    goal = "emergency_fund"

    prompt = build_prompt(income, expenses, goal)
    assert "₹50,000.00" in prompt
    assert "Rent" in prompt
    assert "Food" in prompt
    assert "emergency_fund" in prompt
    assert "CATEGORY_TIPS" not in prompt  # Not the variable name itself
    assert "should not exceed 30% of income" in prompt
    assert "under 15%" in prompt


def test_extract_json_direct():
    """Verify extract_json parses direct JSON cleanly."""
    valid_obj = {"budget": {}, "analysis": [], "suggestions": [], "summary": "Done"}
    text = json.dumps(valid_obj)
    res = extract_json(text)
    assert res == valid_obj


def test_extract_json_markdown_fence():
    """Verify extract_json parses JSON wrapped in markdown code fences."""
    text = """Here is your financial advice:
```json
{
  "budget": {"rent": {"actual_amount": 10000}},
  "analysis": [],
  "suggestions": ["Save ₹500"],
  "summary": "Solid month"
}
```
Hope this helps!"""
    res = extract_json(text)
    assert "budget" in res
    assert res["budget"]["rent"]["actual_amount"] == 10000
    assert res["suggestions"] == ["Save ₹500"]


def test_extract_json_raw_fallback():
    """Verify extract_json extracts raw JSON using regex fallback."""
    text = "Result is: {\"budget\": {}, \"analysis\": [{\"category\": \"Food\"}], \"suggestions\": []} Enjoy."
    res = extract_json(text)
    assert res["analysis"][0]["category"] == "Food"


def test_rule_based_fallback_calculations():
    """Verify deterministic fallback engine produces correct calculations and required keys."""
    income = 50000.0
    expenses = {
        "rent": 18000.0,  # 36% -> over 30% threshold -> overspending
        "food": 6000.0,   # 12% -> under 15% threshold -> on track
    }
    goal = "emergency_fund"
    result = generate_rule_based_analysis(income, expenses, goal)

    assert "budget" in result
    assert "analysis" in result
    assert "suggestions" in result
    assert "summary" in result

    # Check rent calculations
    rent_budget = result["budget"]["rent"]
    assert rent_budget["actual_amount"] == 18000.0
    assert rent_budget["recommended_amount"] == 15000.0  # 30% of 50000
    assert rent_budget["status"] == "exceeded"

    # Check analysis items
    rent_analysis = next(a for a in result["analysis"] if a["category"] == "Rent")
    assert rent_analysis["status"] == "overspending"

    food_analysis = next(a for a in result["analysis"] if a["category"] == "Food")
    assert food_analysis["status"] == "on track"

    # Check suggestions contain rupee symbol
    assert any("₹" in s for s in result["suggestions"])


def test_analyse_endpoint_success(client):
    """Test POST /analyse endpoint returns 200 with required structure."""
    payload = {
        "income": 50000,
        "expenses": {
            "rent": 15000,
            "food": 6000,
            "transport": 3000,
        },
        "goal": "emergency_fund",
    }
    response = client.post(
        "/analyse",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "budget" in data
    assert "analysis" in data
    assert "suggestions" in data
    assert "summary" in data


def test_analyse_endpoint_missing_income(client):
    """Test POST /analyse endpoint rejects missing or zero income."""
    payload = {
        "income": 0,
        "expenses": {"rent": 5000},
    }
    response = client.post(
        "/analyse",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "Income must be greater than 0" in data["error"]


def test_analyse_endpoint_missing_expenses(client):
    """Test POST /analyse endpoint rejects payload with no positive expense entries."""
    payload = {
        "income": 40000,
        "expenses": {"rent": 0, "food": 0},
    }
    response = client.post(
        "/analyse",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "At least one expense entry must be greater than 0" in data["error"]


def test_generate_endpoint_success(client):
    """Test POST /generate endpoint returns 200 with content."""
    payload = {
        "product_info": "Personal Finance Advisor Bot smart budgeting",
        "platform": "Twitter / X",
        "tone": "enthusiastic",
    }
    response = client.post(
        "/generate",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "content" in data
    assert len(data["content"]) > 10


def test_generate_endpoint_validation(client):
    """Test POST /generate endpoint validates product_info."""
    # Empty product_info
    res1 = client.post(
        "/generate",
        data=json.dumps({"product_info": ""}),
        content_type="application/json",
    )
    assert res1.status_code == 400

    # Over 2000 chars product_info
    res2 = client.post(
        "/generate",
        data=json.dumps({"product_info": "a" * 2001}),
        content_type="application/json",
    )
    assert res2.status_code == 400
