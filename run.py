import os
from app import create_app

# Determine configuration environment (defaults to development)
env_config = os.getenv("FLASK_ENV", "development")
app = create_app(env_config)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # Run locally on 127.0.0.1 for development
    app.run(host="127.0.0.1", port=port, debug=True)
