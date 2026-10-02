"""
Personal Finance Advisor Bot (FinanceBot)
Main Application Server Entry Point
"""
import os
import logging
from app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("personal_finance_advisor")

env_config = os.getenv("FLASK_ENV", "development")
app = create_app(env_config)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    print(f"================================================================")
    print(f" FinanceBot — Smart Personal Finance Management Platform")
    print(f" Running at: http://127.0.0.1:{port}")
    print(f" Environment: {env_config.upper()}")
    print(f"================================================================")
    app.run(host="127.0.0.1", port=port, debug=debug)
