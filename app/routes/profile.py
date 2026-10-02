from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, USER_TYPES

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    """User profile management to change name, persona, or update password."""
    if request.method == "POST":
        action = request.form.get("action", "update_info")

        if action == "update_info":
            name = request.form.get("name", "").strip()
            user_type = request.form.get("user_type", current_user.user_type)

            if not name or len(name) < 2:
                flash("Name must be at least 2 characters long.", "danger")
                return redirect(url_for("profile.index"))

            if user_type in USER_TYPES:
                current_user.user_type = user_type

            current_user.name = name
            db.session.commit()
            flash("Profile information updated successfully!", "success")

        elif action == "change_password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_new = request.form.get("confirm_new_password", "")

            if not current_user.check_password(current_password):
                flash("Current password is incorrect.", "danger")
                return redirect(url_for("profile.index"))

            if not new_password or len(new_password) < 6:
                flash("New password must be at least 6 characters long.", "danger")
                return redirect(url_for("profile.index"))

            if new_password != confirm_new:
                flash("New passwords do not match.", "danger")
                return redirect(url_for("profile.index"))

            current_user.set_password(new_password)
            db.session.commit()
            flash("Password changed successfully!", "success")

        return redirect(url_for("profile.index"))

    # Quick profile statistics
    total_incomes_logged = len(current_user.incomes)
    total_expenses_logged = len(current_user.expenses)
    total_goals_set = len(current_user.savings_goals)

    return render_template(
        "profile/index.html",
        user_types=USER_TYPES,
        total_incomes=total_incomes_logged,
        total_expenses=total_expenses_logged,
        total_goals=total_goals_set,
    )
