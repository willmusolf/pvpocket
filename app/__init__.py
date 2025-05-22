# app/__init__.py

from flask import Flask, session, current_app
from .config import config
import os
import json
from datetime import datetime
import secrets

# --- Flask-Login and Flask-Dance Imports ---
from flask_login import (
    current_user,
)  # Keep UserMixin if used elsewhere, User is now in models
from flask_dance.contrib.google import make_google_blueprint

# --- Import from new models.py ---
from .models import (
    login_manager,
    User,
)  # Import User if needed directly, load_user is tied to login_manager

# --- Your existing blueprint and class imports ---
from .routes.main import main_bp
from .routes.auth import auth_bp
from .routes.auth import google_authorized as google_auth_handler_function
from .routes.battle import battle_bp
from .routes.decks import decks_bp
from .routes.meta import meta_bp
from .routes.collection import collection_bp
from Card import Card, CardCollection
from Deck import Deck

from flask_dance.consumer import oauth_authorized


# --- Helper functions (load_json_file, save_json_file) ---
def load_json_file(filepath, default=None):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}


def save_json_file(data, filepath):
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Data saved to {filepath}")
    except Exception as e:
        print(f"Error saving JSON file {filepath}: {e}")


# --- Main Application Factory ---
def create_app(config_name="default"):
    # from dotenv import load_dotenv # Ensure this is called in run.py or very top of __init__
    # load_dotenv()

    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../images",
        static_url_path="/images",
    )
    app_config = config[config_name]
    app.config.from_object(app_config)

    if not app.config.get("SECRET_KEY"):
        # This block runs ONLY if os.environ.get('SECRET_KEY') in config.py returned None
        app.config["SECRET_KEY"] = secrets.token_hex(24)
        print("WARNING: SECRET_KEY was not set from environment. Using a temporary random key.", flush=True)
    else:
        print(f"SECRET_KEY loaded successfully from environment/config.", flush=True)

    app_config.create_directories()

    # --- Initialize Flask-Login (using login_manager from models.py) ---
    login_manager.init_app(app)
    # login_view and messages are already set on login_manager in models.py
    # If you want to override them per-app instance, you can do it here:
    # login_manager.login_view = "auth.login_prompt_page"
    # login_manager.login_message = "Please sign in via Google."
    # --- End Flask-Login Init ---

    # --- Flask-Dance Google OAuth Blueprint Setup ---
    if not app.config.get("GOOGLE_OAUTH_CLIENT_ID") or not app.config.get(
        "GOOGLE_OAUTH_CLIENT_SECRET"
    ):
        print(
            "WARNING: Google OAuth credentials not configured. Google Sign-In disabled."
        )
        google_bp = None
    else:
        google_bp = make_google_blueprint(
            client_id=app.config["GOOGLE_OAUTH_CLIENT_ID"],
            client_secret=app.config["GOOGLE_OAUTH_CLIENT_SECRET"],
            scope=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ]
        )
        app.register_blueprint(google_bp, url_prefix="/login")
    # --- End Flask-Dance Setup ---

    # Initialize card collection (your existing logic)
    card_collection = CardCollection()
    try:
        print("Loading card collection from database...")
        card_collection.load_from_db()
        print(f"Loaded {len(card_collection)} cards from database.")
    except Exception as e:
        print(f"Error loading from database: {e}")

    # Load or initialize other data files (your existing logic)
    battle_history = load_json_file(app_config.BATTLE_HISTORY_FILE, [])
    meta_stats = load_json_file(
        app_config.META_STATS_FILE, {"decks": {}, "last_updated": ""}
    )
    users = load_json_file(
        app_config.USERS_FILE, {}
    )  # This will be modified by auth logic

    # Store global-like variables and save functions in app config
    app.config["card_collection"] = card_collection
    app.config["battle_history"] = battle_history
    app.config["meta_stats"] = meta_stats
    app.config["users"] = users
    app.config["save_battle_history"] = lambda history: save_json_file(
        history, app_config.BATTLE_HISTORY_FILE
    )
    app.config["save_meta_stats"] = lambda stats: save_json_file(
        {
            "decks": stats.get("decks", {}),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        app_config.META_STATS_FILE,
    )
    app.config["save_users"] = lambda: save_json_file(users, app_config.USERS_FILE)

    if google_bp:  # Check if the blueprint was actually created
        oauth_authorized.connect(
            google_auth_handler_function, sender=google_bp
        )
        print(
            f"Signal oauth_authorized connected from sender '{google_bp.name}' to handler 'google_auth_handler_function'.",
            flush=True,
        )
    else:
        print(
            "Google blueprint not available, oauth_authorized signal not connected.",
            flush=True,
        )
    # ***** END OF ADDED BLOCK *****
    # app.config['update_meta_stats'] = update_meta_stats # Your existing function for this

    # --- Context Processor for Templates ---
    # Updated to use Flask-Login's current_user
    @app.context_processor
    def inject_user_for_templates():
        return dict(
            user_logged_in=current_user.is_authenticated,
            username=current_user.username if current_user.is_authenticated else None,
            # You can add current_user directly if you want access to the full User object in templates
            # current_user_obj=current_user
        )

    # --- Register your application blueprints ---
    # Ensure they are imported at the top of the file
    app.register_blueprint(main_bp)
    app.register_blueprint(
        auth_bp
    )  # This blueprint will now handle Google callback and logout
    app.register_blueprint(battle_bp)
    app.register_blueprint(decks_bp)
    app.register_blueprint(meta_bp)
    app.register_blueprint(collection_bp)

    return app
