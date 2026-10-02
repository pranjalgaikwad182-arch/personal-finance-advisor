from datetime import date
from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
from app.services.report_service import generate_monthly_report_data, generate_csv_report
from app.services.gemini_service import generate_ai_insights

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/")
@login_required
def index():
    """Monthly Financial Statement page with full income/expense/budget/goals breakdown."""
    today = date.today()
    try:
        month = int(request.args.get("month", today.month))
        year = int(request.args.get("year", today.year))
    except (ValueError, TypeError):
        month = today.month
        year = today.year

    if month < 1 or month > 12:
        month = today.month

    report_data = generate_monthly_report_data(current_user.id, month, year)

    # Fetch AI summary for report
    from app.services.financial_service import get_dashboard_summary
    financial_data = get_dashboard_summary(current_user.id, month, year)
    ai_summary = generate_ai_insights(financial_data, current_user.user_type)

    years = [today.year - 2, today.year - 1, today.year, today.year + 1]

    return render_template(
        "reports/index.html",
        report=report_data,
        ai_summary=ai_summary,
        selected_month=month,
        selected_year=year,
        available_years=years,
    )


@reports_bp.route("/download")
@login_required
def download_csv():
    """Download the monthly report in standard CSV format."""
    today = date.today()
    try:
        month = int(request.args.get("month", today.month))
        year = int(request.args.get("year", today.year))
    except (ValueError, TypeError):
        month = today.month
        year = today.year

    report_data = generate_monthly_report_data(current_user.id, month, year)
    csv_text = generate_csv_report(report_data)

    filename = f"finance_report_{report_data['month_name'].lower()}_{year}.csv"
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@reports_bp.route("/print")
@login_required
def print_view():
    """Clean, dedicated print-ready layout for exporting or printing to PDF."""
    today = date.today()
    try:
        month = int(request.args.get("month", today.month))
        year = int(request.args.get("year", today.year))
    except (ValueError, TypeError):
        month = today.month
        year = today.year

    report_data = generate_monthly_report_data(current_user.id, month, year)
    from app.services.financial_service import get_dashboard_summary
    financial_data = get_dashboard_summary(current_user.id, month, year)
    ai_summary = generate_ai_insights(financial_data, current_user.user_type)

    return render_template(
        "reports/print.html",
        report=report_data,
        ai_summary=ai_summary,
        selected_month=month,
        selected_year=year,
    )
