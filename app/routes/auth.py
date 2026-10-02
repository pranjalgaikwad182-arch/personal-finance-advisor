import re
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, USER_TYPES

auth_bp = Blueprint("auth", __name__)

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


@auth_bp.route("/")
def index():
    """Public home/landing page or redirect to dashboard if authenticated."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    return render_template("index.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login route."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("auth/login.html")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f"Welcome back, {user.name}!", "success")
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("dashboard.dashboard"))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """New user registration route."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        user_type = request.form.get("user_type", "Salaried Professional")

        # Validation
        errors = []
        if not name or len(name) < 2:
            errors.append("Please enter a valid full name (at least 2 characters).")
        if not email or not EMAIL_REGEX.match(email):
            errors.append("Please provide a valid email address.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters long.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if user_type not in USER_TYPES:
            user_type = "Salaried Professional"

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("auth/register.html", name=name, email=email, selected_type=user_type)

        # Check existing email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email address already exists. Please log in.", "warning")
            return redirect(url_for("auth.login"))

        # Create new user
        new_user = User(
            name=name,
            email=email,
            user_type=user_type,
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash(f"Account created successfully as {user_type}! Welcome to Personal Finance Advisor.", "success")
        return redirect(url_for("dashboard.dashboard"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Logs out the current user."""
    logout_user()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("auth.login"))
