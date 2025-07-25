import os
from dotenv import load_dotenv

load_dotenv()
from app import create_app

config_name = os.getenv("FLASK_CONFIG", os.getenv("FLASK_ENV", "default"))

# Only show startup config in development and in main process
if config_name == "development" and os.environ.get('WERKZEUG_RUN_MAIN'):
    print(f"Starting app with configuration: {config_name}")

app = create_app(config_name)

if __name__ == "__main__":
    app.run(
        debug=app.config.get("DEBUG", True),
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5001)),
    )
