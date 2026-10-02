from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import extract
from app.models import db, Expense, DEFAULT_EXPENSE_CATEGORIES

expenses_bp = Blueprint("expenses", __name__)


@expenses_bp.route("/")
@login_required
def index():
    """List expense transactions with month/year and category filters."""
    today = date.today()
    try:
        month_param = request.args.get("month")
        year_param = request.args.get("year")
        category_param = request.args.get("category", "").strip()
        search_param = request.args.get("search", "").strip()

        month = int(month_param) if month_param and month_param != "all" else None
        year = int(year_param) if year_param and year_param != "all" else today.year
    except (ValueError, TypeError):
        month = None
        year = today.year
        category_param = ""
        search_param = ""

    query = Expense.query.filter_by(user_id=current_user.id)

    if year:
        query = query.filter(extract("year", Expense.expense_date) == year)
    if month:
        query = query.filter(extract("month", Expense.expense_date) == month)
    if category_param and category_param != "all":
        query = query.filter(Expense.category == category_param)
    if search_param:
        query = query.filter(Expense.description.ilike(f"%{search_param}%"))

    expenses = query.order_by(Expense.expense_date.desc(), Expense.id.desc()).all()
    total_filtered_expenses = round(sum(e.amount for e in expenses), 2)

    years = [today.year - 2, today.year - 1, today.year, today.year + 1]

    return render_template(
        "expenses/index.html",
        expenses=expenses,
        total_expenses=total_filtered_expenses,
        selected_month=month,
        selected_year=year,
        selected_category=category_param,
        search_query=search_param,
        available_years=years,
        today_date=today.strftime("%Y-%m-%d"),
    )


@expenses_bp.route("/add", methods=["POST"])
@login_required
def add():
    """Add new expense transaction."""
    try:
        amount = float(request.form.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0.0

    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    date_str = request.form.get("expense_date")

    # Validation
    if amount <= 0:
        flash("Expense amount must be greater than zero.", "danger")
        return redirect(url_for("expenses.index"))

    if not category:
        flash("Expense category is required.", "danger")
        return redirect(url_for("expenses.index"))

    try:
        expense_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        flash("Invalid expense date format. Please use YYYY-MM-DD.", "danger")
        return redirect(url_for("expenses.index"))

    new_expense = Expense(
        user_id=current_user.id,
        amount=amount,
        category=category,
        description=description,
        expense_date=expense_date,
    )
    db.session.add(new_expense)
    db.session.commit()

    flash(f"Recorded expense of ₹{amount:,.2f} for {category}!", "success")
    return redirect(url_for("expenses.index"))


@expenses_bp.route("/edit/<int:expense_id>", methods=["POST"])
@login_required
def edit(expense_id):
    """Edit an existing expense owned by the current user."""
    # Strict tenant isolation
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()

    try:
        amount = float(request.form.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0.0

    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    date_str = request.form.get("expense_date")

    if amount <= 0:
        flash("Expense amount must be greater than zero.", "danger")
        return redirect(url_for("expenses.index"))

    if not category:
        flash("Expense category is required.", "danger")
        return redirect(url_for("expenses.index"))

    try:
        expense.expense_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else expense.expense_date
    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for("expenses.index"))

    expense.amount = amount
    expense.category = category
    expense.description = description
    db.session.commit()

    flash("Expense entry updated successfully.", "success")
    return redirect(url_for("expenses.index"))


@expenses_bp.route("/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete(expense_id):
    """Delete an expense record owned by the current user."""
    # Strict tenant isolation
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    db.session.delete(expense)
    db.session.commit()

    flash("Expense entry removed.", "info")
    return redirect(url_for("expenses.index"))
