# run.py

from dotenv import load_dotenv
import os  # Import os to get environment variables

# --- ADD THIS LINE AT THE VERY TOP ---
load_dotenv()

from app import create_app  # Your existing import

# Determine which configuration to use (development, production, etc.)
# You can make this dynamic using an environment variable like FLASK_CONFIG
# For example: config_name = os.getenv('FLASK_CONFIG', 'development')
# For now, we'll stick to your explicit 'development' for simplicity,
# but the .env file can set FLASK_CONFIG too.
config_name = os.getenv("FLASK_CONFIG") or "development"
print(f"Starting app with configuration: {config_name}")  # For debugging

app = create_app(config_name)

if __name__ == "__main__":
    # It's good practice to let Flask's config control debug mode
    # The development server should not be used in production.
    # In production, you'll use a WSGI server like Gunicorn.
    app.run(
        debug=app.config.get("DEBUG", True),
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5001)),
    )
