from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, SavingsGoal, SavingsContribution, SAVINGS_GOAL_TYPES

savings_bp = Blueprint("savings", __name__)


@savings_bp.route("/")
@login_required
def index():
    """List all user savings goals with visual progress bars and contribution history."""
    goals = (
        SavingsGoal.query.filter_by(user_id=current_user.id)
        .order_by(SavingsGoal.target_date.asc())
        .all()
    )

    total_target = sum(g.target_amount for g in goals)
    total_saved = sum(g.current_amount for g in goals)
    total_remaining = max(0.0, total_target - total_saved)
    overall_progress = (
        round((total_saved / total_target * 100), 1) if total_target > 0 else 0.0
    )

    today = date.today()
    default_target_date = date(today.year + 1, today.month, 1).strftime("%Y-%m-%d")

    return render_template(
        "savings/index.html",
        goals=goals,
        total_target=total_target,
        total_saved=total_saved,
        total_remaining=total_remaining,
        overall_progress=overall_progress,
        goal_types=SAVINGS_GOAL_TYPES,
        today_date=today.strftime("%Y-%m-%d"),
        default_target_date=default_target_date,
    )


@savings_bp.route("/add", methods=["POST"])
@login_required
def add():
    """Create a new savings goal."""
    name = request.form.get("name", "").strip()
    custom_name = request.form.get("custom_name", "").strip()
    if name == "Other" and custom_name:
        name = custom_name

    try:
        target_amount = float(request.form.get("target_amount", 0))
        current_amount = float(request.form.get("current_amount", 0))
    except (ValueError, TypeError):
        target_amount = 0.0
        current_amount = 0.0

    target_date_str = request.form.get("target_date")
    description = request.form.get("description", "").strip()

    # Validation
    if not name:
        flash("Goal name is required.", "danger")
        return redirect(url_for("savings.index"))

    if target_amount <= 0:
        flash("Target amount must be greater than zero.", "danger")
        return redirect(url_for("savings.index"))

    if current_amount < 0:
        flash("Initial saved amount cannot be negative.", "danger")
        return redirect(url_for("savings.index"))

    try:
        target_date = (
            datetime.strptime(target_date_str, "%Y-%m-%d").date()
            if target_date_str
            else date(date.today().year + 1, 1, 1)
        )
    except ValueError:
        flash("Invalid target date format. Please use YYYY-MM-DD.", "danger")
        return redirect(url_for("savings.index"))

    goal = SavingsGoal(
        user_id=current_user.id,
        name=name,
        target_amount=target_amount,
        current_amount=current_amount,
        target_date=target_date,
        description=description,
    )
    db.session.add(goal)
    db.session.commit()

    # If starting balance was provided, record it as initial contribution
    if current_amount > 0:
        contribution = SavingsContribution(
            goal_id=goal.id,
            amount=current_amount,
            contribution_date=date.today(),
            description="Initial balance when goal was created",
        )
        db.session.add(contribution)
        db.session.commit()

    flash(f"Savings goal '{name}' for ₹{target_amount:,.2f} created successfully!", "success")
    return redirect(url_for("savings.index"))


@savings_bp.route("/<int:goal_id>/contribute", methods=["POST"])
@login_required
def contribute(goal_id):
    """Add a deposit contribution to a savings goal."""
    # Strict tenant isolation
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()

    try:
        amount = float(request.form.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0.0

    date_str = request.form.get("contribution_date")
    description = request.form.get("description", "").strip() or "Regular savings deposit"

    if amount <= 0:
        flash("Contribution amount must be greater than zero.", "danger")
        return redirect(url_for("savings.index"))

    try:
        contrib_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str
            else date.today()
        )
    except ValueError:
        flash("Invalid contribution date format.", "danger")
        return redirect(url_for("savings.index"))

    goal.current_amount = round(goal.current_amount + amount, 2)

    contribution = SavingsContribution(
        goal_id=goal.id,
        amount=amount,
        contribution_date=contrib_date,
        description=description,
    )
    db.session.add(contribution)
    db.session.commit()

    flash(
        f"Contributed ₹{amount:,.2f} to '{goal.name}'! Current progress: {goal.progress_pct}%.",
        "success",
    )
    return redirect(url_for("savings.index"))


@savings_bp.route("/edit/<int:goal_id>", methods=["POST"])
@login_required
def edit(goal_id):
    """Edit goal details owned by the current user."""
    # Strict tenant isolation
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()

    name = request.form.get("name", "").strip()
    try:
        target_amount = float(request.form.get("target_amount", 0))
    except (ValueError, TypeError):
        target_amount = 0.0

    target_date_str = request.form.get("target_date")
    description = request.form.get("description", "").strip()

    if not name:
        flash("Goal name is required.", "danger")
        return redirect(url_for("savings.index"))

    if target_amount <= 0:
        flash("Target amount must be greater than zero.", "danger")
        return redirect(url_for("savings.index"))

    try:
        goal.target_date = (
            datetime.strptime(target_date_str, "%Y-%m-%d").date()
            if target_date_str
            else goal.target_date
        )
    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for("savings.index"))

    goal.name = name
    goal.target_amount = target_amount
    goal.description = description
    db.session.commit()

    flash(f"Goal '{goal.name}' updated successfully.", "success")
    return redirect(url_for("savings.index"))


@savings_bp.route("/delete/<int:goal_id>", methods=["POST"])
@login_required
def delete(goal_id):
    """Delete a savings goal owned by current user."""
    # Strict tenant isolation
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    goal_name = goal.name

    db.session.delete(goal)
    db.session.commit()

    flash(f"Savings goal '{goal_name}' deleted.", "info")
    return redirect(url_for("savings.index"))
