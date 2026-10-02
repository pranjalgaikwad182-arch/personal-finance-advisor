import os
from datetime import datetime
from flask import Flask, render_template
from flask_login import LoginManager
from config import config_by_name
from app.models import (
    db,
    User,
    DEFAULT_EXPENSE_CATEGORIES,
    DEFAULT_INCOME_SOURCES,
    USER_TYPES,
    SAVINGS_GOAL_TYPES,
)
from app.services.ai_advisor_service import (
    CATEGORY_TIPS,
    GOAL_DESCRIPTIONS,
    build_prompt,
    extract_json,
    generate_rule_based_analysis,
    analyze_finances_with_gemini,
)

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def format_currency(value, symbol="₹"):
    """Format float or int as currency with thousands separator (Indian grouping style)."""
    if value is None:
        return f"{symbol}0"
    try:
        val = float(value)
    except (ValueError, TypeError):
        return f"{symbol}0"

    is_negative = val < 0
    val = abs(val)

    # Format integer part with Indian number grouping
    parts = f"{val:.2f}".split(".")
    integer_part = parts[0]
    decimal_part = parts[1]

    if len(integer_part) > 3:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        # Group in pairs from right to left
        groups = []
        while remaining:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        groups.reverse()
        formatted_int = ",".join(groups) + "," + last_three
    else:
        formatted_int = integer_part

    # Drop .00 if whole number for cleaner UI
    if decimal_part == "00":
        formatted_str = formatted_int
    else:
        formatted_str = f"{formatted_int}.{decimal_part}"

    prefix = f"-{symbol}" if is_negative else symbol
    return f"{prefix}{formatted_str}"


def create_app(config_name="default"):
    """Application factory for Personal Finance Advisor."""
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    import jinja2
    app.jinja_loader = jinja2.ChoiceLoader([
        app.jinja_loader,
        jinja2.FileSystemLoader([
            os.path.join(app.root_path, "..", "templates"),
            os.path.join(app.root_path, "templates"),
            os.path.join(app.root_path, "templates", "auth"),
            os.path.join(app.root_path, "templates", "dashboard"),
            os.path.join(app.root_path, "templates", "income"),
            os.path.join(app.root_path, "templates", "expenses"),
            os.path.join(app.root_path, "templates", "budgets"),
            os.path.join(app.root_path, "templates", "savings"),
            os.path.join(app.root_path, "templates", "reports"),
            os.path.join(app.root_path, "templates", "advisor"),
        ])
    ])

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Context processors for global template variables
    @app.context_processor
    def inject_globals():
        now = datetime.now()
        return {
            "current_year": now.year,
            "current_month": now.month,
            "currency_symbol": app.config.get("CURRENCY_SYMBOL", "₹"),
            "expense_categories": DEFAULT_EXPENSE_CATEGORIES,
            "income_sources": DEFAULT_INCOME_SOURCES,
            "user_types": USER_TYPES,
            "savings_goal_types": SAVINGS_GOAL_TYPES,
        }

    # Custom Jinja filters
    @app.template_filter("currency")
    def currency_filter(val):
        symbol = app.config.get("CURRENCY_SYMBOL", "₹")
        return format_currency(val, symbol=symbol)

    @app.template_filter("month_name")
    def month_name_filter(month_int):
        months = [
            "",
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        try:
            return months[int(month_int)]
        except (IndexError, ValueError, TypeError):
            return ""

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.income import income_bp
    from app.routes.expenses import expenses_bp
    from app.routes.budgets import budgets_bp
    from app.routes.savings import savings_bp
    from app.routes.reports import reports_bp
    from app.routes.advisor import advisor_bp
    from app.routes.profile import profile_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(income_bp, url_prefix="/income")
    app.register_blueprint(expenses_bp, url_prefix="/expenses")
    app.register_blueprint(budgets_bp, url_prefix="/budgets")
    app.register_blueprint(savings_bp, url_prefix="/savings")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(advisor_bp, url_prefix="/advisor")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(api_bp)

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/404.html"), 403

    # Ensure tables exist
    with app.app_context():
        db.create_all()

    return app
