from datetime import date
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from services.financial_analyzer import get_dashboard_summary
from services.ai_engine import generate_ai_insights, answer_financial_query

advisor_bp = Blueprint("advisor", __name__)


@advisor_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Dedicated AI Financial Advisor page presenting Gemini-powered insights & interactive Chat."""
    today = date.today()
    try:
        month = int(
            request.form.get("month")
            or request.args.get("month", today.month)
        )
        year = int(
            request.form.get("year")
            or request.args.get("year", today.year)
        )
    except (ValueError, TypeError):
        month = today.month
        year = today.year

    if month < 1 or month > 12:
        month = today.month

    # Step 1: Calculate all deterministic financial facts strictly in Python
    financial_data = get_dashboard_summary(current_user.id, month, year)

    # Step 2: Pass deterministic facts to Gemini service (or graceful fallback)
    advisory_output = generate_ai_insights(
        financial_data=financial_data,
        user_type=current_user.user_type,
    )

    years = [today.year - 2, today.year - 1, today.year, today.year + 1]

    # Sample starter questions for the chat interface
    starter_questions = [
        "How much did I spend this month?",
        "Where am I overspending?",
        "How much can I save?",
        "Give me a budget for next month.",
        "Which category costs me the most?",
        "How can I reduce my expenses?",
        "How much have I saved?",
        "Am I within my budget?",
    ]

    return render_template(
        "advisor/index.html",
        financial_data=financial_data,
        advisory=advisory_output,
        selected_month=month,
        selected_year=year,
        available_years=years,
        starter_questions=starter_questions,
    )


@advisor_bp.route("/chat", methods=["POST"])
@login_required
def chat():
    """Interactive AI Financial Advisor Chat endpoint."""
    data = request.get_json(silent=True) or request.form
    query = str(data.get("query", "")).strip()

    if not query:
        return jsonify({"success": False, "error": "Query cannot be empty."}), 400

    today = date.today()
    try:
        month = int(data.get("month", today.month))
        year = int(data.get("year", today.year))
    except (ValueError, TypeError):
        month = today.month
        year = today.year

    result = answer_financial_query(current_user.id, query, month, year)

    return jsonify({
        "success": True,
        "query": query,
        "answer": result["answer"],
        "mode": result.get("mode", "rule_based"),
    })
