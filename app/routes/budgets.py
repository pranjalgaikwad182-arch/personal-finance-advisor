from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Budget, DEFAULT_EXPENSE_CATEGORIES
from app.services.financial_service import get_budget_status
from app.services.budget_service import (
    generate_recommended_budgets,
    apply_recommended_budgets,
)

budgets_bp = Blueprint("budgets", __name__)


@budgets_bp.route("/")
@login_required
def index():
    """Display monthly category budgets with utilization and visual indicators."""
    today = date.today()
    try:
        month = int(request.args.get("month", today.month))
        year = int(request.args.get("year", today.year))
    except (ValueError, TypeError):
        month = today.month
        year = today.year

    if month < 1 or month > 12:
        month = today.month

    budget_status = get_budget_status(current_user.id, month, year)
    years = [today.year - 2, today.year - 1, today.year, today.year + 1]

    # Pre-generate budget recommendations for preview/generator modal
    recommendation_data = generate_recommended_budgets(
        current_user.id, month=month, year=year, savings_target_pct=20.0
    )

    return render_template(
        "budgets/index.html",
        budget_status=budget_status,
        selected_month=month,
        selected_year=year,
        available_years=years,
        categories=DEFAULT_EXPENSE_CATEGORIES,
        recommendations=recommendation_data,
    )


@budgets_bp.route("/add", methods=["POST"])
@login_required
def add():
    """Create or update a category budget limit for a specific month and year."""
    category = request.form.get("category", "").strip()
    try:
        amount = float(request.form.get("amount", 0))
        month = int(request.form.get("month", date.today().month))
        year = int(request.form.get("year", date.today().year))
    except (ValueError, TypeError):
        amount = 0.0
        month = date.today().month
        year = date.today().year

    if not category:
        flash("Category is required to set a budget.", "danger")
        return redirect(url_for("budgets.index", month=month, year=year))

    if amount <= 0:
        flash("Budget amount must be greater than zero.", "danger")
        return redirect(url_for("budgets.index", month=month, year=year))

    # Upsert: update if already exists for this month/year, else insert
    budget = Budget.query.filter_by(
        user_id=current_user.id, category=category, month=month, year=year
    ).first()

    if budget:
        budget.amount = amount
        flash(f"Updated {category} budget to ₹{amount:,.2f} for {month}/{year}.", "success")
    else:
        new_budget = Budget(
            user_id=current_user.id,
            category=category,
            amount=amount,
            month=month,
            year=year,
        )
        db.session.add(new_budget)
        flash(f"Created {category} budget of ₹{amount:,.2f} for {month}/{year}!", "success")

    db.session.commit()
    return redirect(url_for("budgets.index", month=month, year=year))


@budgets_bp.route("/delete/<int:budget_id>", methods=["POST"])
@login_required
def delete(budget_id):
    """Delete a budget limit owned by current user."""
    # Strict tenant isolation
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first_or_404()
    month = budget.month
    year = budget.year

    db.session.delete(budget)
    db.session.commit()

    flash("Budget limit removed.", "info")
    return redirect(url_for("budgets.index", month=month, year=year))


@budgets_bp.route("/generate", methods=["GET", "POST"])
@login_required
def generate():
    """Execute Python budget recommendation engine with custom savings target."""
    today = date.today()
    try:
        month = int(request.form.get("month") or request.args.get("month", today.month))
        year = int(request.form.get("year") or request.args.get("year", today.year))
        target_pct = float(request.form.get("savings_target_pct", 20.0))
    except (ValueError, TypeError):
        month = today.month
        year = today.year
        target_pct = 20.0

    recommendations = generate_recommended_budgets(
        current_user.id, month=month, year=year, savings_target_pct=target_pct
    )

    budget_status = get_budget_status(current_user.id, month, year)
    years = [today.year - 2, today.year - 1, today.year, today.year + 1]

    return render_template(
        "budgets/index.html",
        budget_status=budget_status,
        selected_month=month,
        selected_year=year,
        available_years=years,
        categories=DEFAULT_EXPENSE_CATEGORIES,
        recommendations=recommendations,
        show_recommendation_modal=True,
    )


@budgets_bp.route("/apply-recommendations", methods=["POST"])
@login_required
def apply():
    """Apply generated or user-adjusted recommendations to active budgets."""
    try:
        month = int(request.form.get("month", date.today().month))
        year = int(request.form.get("year", date.today().year))
    except (ValueError, TypeError):
        month = date.today().month
        year = date.today().year

    # Extract all submitted category amounts
    budget_items = []
    for key, val in request.form.items():
        if key.startswith("rec_amount_"):
            cat = key.replace("rec_amount_", "")
            try:
                amt = float(val)
                if amt > 0:
                    budget_items.append({"category": cat, "amount": amt})
            except (ValueError, TypeError):
                continue

    if not budget_items:
        flash("No valid category amounts were provided to apply.", "warning")
        return redirect(url_for("budgets.index", month=month, year=year))

    count = apply_recommended_budgets(current_user.id, budget_items, month, year)
    flash(f"Successfully applied {count} recommended category budgets for {month}/{year}!", "success")
    return redirect(url_for("budgets.index", month=month, year=year))
