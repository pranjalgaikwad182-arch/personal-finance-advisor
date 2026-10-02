from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import extract
from app.models import db, Income, DEFAULT_INCOME_SOURCES

income_bp = Blueprint("income", __name__)


@income_bp.route("/")
@login_required
def index():
    """List income transactions with optional month/year and source filtering."""
    today = date.today()
    try:
        month_param = request.args.get("month")
        year_param = request.args.get("year")
        source_param = request.args.get("source", "").strip()

        month = int(month_param) if month_param and month_param != "all" else None
        year = int(year_param) if year_param and year_param != "all" else today.year
    except (ValueError, TypeError):
        month = None
        year = today.year
        source_param = ""

    query = Income.query.filter_by(user_id=current_user.id)

    if year:
        query = query.filter(extract("year", Income.income_date) == year)
    if month:
        query = query.filter(extract("month", Income.income_date) == month)
    if source_param and source_param != "all":
        query = query.filter(Income.source == source_param)

    incomes = query.order_by(Income.income_date.desc(), Income.id.desc()).all()
    total_filtered_income = round(sum(i.amount for i in incomes), 2)

    years = [today.year - 2, today.year - 1, today.year, today.year + 1]

    return render_template(
        "income/index.html",
        incomes=incomes,
        total_income=total_filtered_income,
        selected_month=month,
        selected_year=year,
        selected_source=source_param,
        available_years=years,
        today_date=today.strftime("%Y-%m-%d"),
    )


@income_bp.route("/add", methods=["POST"])
@login_required
def add():
    """Add new income record."""
    try:
        amount = float(request.form.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0.0

    source = request.form.get("source", "").strip()
    custom_source = request.form.get("custom_source", "").strip()
    if source == "Other" and custom_source:
        source = custom_source

    description = request.form.get("description", "").strip()
    date_str = request.form.get("income_date")

    # Validation
    if amount <= 0:
        flash("Income amount must be greater than zero.", "danger")
        return redirect(url_for("income.index"))

    if not source:
        flash("Income source is required.", "danger")
        return redirect(url_for("income.index"))

    try:
        income_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        flash("Invalid income date format. Please use YYYY-MM-DD.", "danger")
        return redirect(url_for("income.index"))

    new_income = Income(
        user_id=current_user.id,
        amount=amount,
        source=source,
        description=description,
        income_date=income_date,
    )
    db.session.add(new_income)
    db.session.commit()

    flash(f"Successfully recorded income of ₹{amount:,.2f} from {source}!", "success")
    return redirect(url_for("income.index"))


@income_bp.route("/edit/<int:income_id>", methods=["POST"])
@login_required
def edit(income_id):
    """Edit an existing income record owned by current user."""
    # Strict tenant isolation
    income = Income.query.filter_by(id=income_id, user_id=current_user.id).first_or_404()

    try:
        amount = float(request.form.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0.0

    source = request.form.get("source", "").strip()
    description = request.form.get("description", "").strip()
    date_str = request.form.get("income_date")

    if amount <= 0:
        flash("Income amount must be greater than zero.", "danger")
        return redirect(url_for("income.index"))

    if not source:
        flash("Income source is required.", "danger")
        return redirect(url_for("income.index"))

    try:
        income.income_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else income.income_date
    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for("income.index"))

    income.amount = amount
    income.source = source
    income.description = description
    db.session.commit()

    flash("Income entry updated successfully.", "success")
    return redirect(url_for("income.index"))


@income_bp.route("/delete/<int:income_id>", methods=["POST"])
@login_required
def delete(income_id):
    """Delete an income record owned by current user."""
    # Strict tenant isolation
    income = Income.query.filter_by(id=income_id, user_id=current_user.id).first_or_404()
    db.session.delete(income)
    db.session.commit()

    flash("Income entry removed.", "info")
    return redirect(url_for("income.index"))
