from flask import Flask, session, current_app, request, jsonify
from .config import config
import firebase_admin
from firebase_admin import credentials, firestore
import os
import pickle
import time
from datetime import datetime
import secrets
import threading
import json
from google.cloud import secretmanager
from google.api_core.exceptions import NotFound, PermissionDenied

from flask_login import (
    current_user,
) 
from flask_dance.contrib.google import make_google_blueprint

from .models import (
    login_manager,
    User,
)

from .routes.main import main_bp
from .routes.auth import auth_bp
from .routes.auth import google_authorized as google_auth_handler_function
from .routes.auth import check_username_requirement
from .routes.battle import battle_bp
from .routes.decks import decks_bp
from .routes.meta import meta_bp
from .routes.collection import collection_bp
from Card import Card, CardCollection
from Deck import Deck

from flask_dance.consumer import oauth_authorized

from better_profanity import profanity

from dotenv import (
    load_dotenv,
)

load_dotenv()

CARD_CACHE_PATH = "/tmp/card_collection.pkl"
CACHE_DURATION_SECONDS = 30 * 24 * 60 * 60

cache_lock = threading.Lock()


def _load_cards_from_firestore_and_cache():
    """
    Helper function to load cards from Firestore and update the cache file.
    This is the new "single source of truth" for loading data.
    """
    print("Attempting to load card collection from Firestore...", flush=True)
    db_client = current_app.config.get("FIRESTORE_DB")
    if not db_client:
        print("ERROR: Firestore client not available for card loading.", flush=True)
        return None

    try:
        card_collection = CardCollection()
        card_collection.load_from_firestore(db_client)
        print(
            f"Loaded {len(card_collection)} cards from Firestore. Saving to cache.",
            flush=True,
        )
        with open(CARD_CACHE_PATH, "wb") as f:
            pickle.dump(card_collection, f)
        return card_collection
    except Exception as e:
        print(
            f"CRITICAL: Failed to load cards from Firestore and update cache: {e}",
            flush=True,
        )
        return None


def create_app(config_name="default"):
    app = Flask(
        __name__,
        template_folder="../templates",
    )
    app_config = config[config_name]
    app.config.from_object(app_config)

    if not app.config.get("SECRET_KEY"):
        raise ValueError(
            "FATAL ERROR: SECRET_KEY is not set. Please set it in your .env file."
        )
    else:
        print("SECRET_KEY loaded successfully from environment.", flush=True)

    profanity.load_censor_words()

    if not firebase_admin._apps:
        try:
            # Production/Staging Logic: Fetch credentials from Secret Manager
            project_id = app.config.get("GCP_PROJECT_ID")
            secret_name = app.config.get("FIREBASE_SECRET_NAME")

            if project_id and secret_name:
                print(
                    "Attempting to initialize Firebase from Google Secret Manager...",
                    flush=True,
                )
                client = secretmanager.SecretManagerServiceClient()
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})

                secret_payload = response.payload.data.decode("UTF-8")
                cred_dict = json.loads(secret_payload)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print(
                    "Firebase initialized successfully from Secret Manager.", flush=True
                )
            else:
                print(
                    "Secret Manager config not found. Falling back to Application Default Credentials.",
                    flush=True,
                )
                firebase_admin.initialize_app()
                print(
                    "Firebase initialized successfully with Application Default Credentials.",
                    flush=True,
                )

        except (NotFound, PermissionDenied):
            print(
                "ERROR: Could not access secret in Secret Manager. Check name and permissions.",
                flush=True,
            )
            print("Falling back to Application Default Credentials.", flush=True)
            firebase_admin.initialize_app()
        except Exception as e:
            print(
                f"CRITICAL ERROR: Failed to initialize Firebase Admin SDK: {e}",
                flush=True,
            )

    app.config["FIRESTORE_DB"] = firestore.client()

    login_manager.init_app(app)

    # --- Cached Card Collection Loading Logic ---
    card_collection = None
    db_client = app.config.get("FIRESTORE_DB")

    try:
        cache_is_valid = False
        if os.path.exists(CARD_CACHE_PATH):
            file_mod_time = os.path.getmtime(CARD_CACHE_PATH)
            if (time.time() - file_mod_time) < CACHE_DURATION_SECONDS:
                with open(CARD_CACHE_PATH, "rb") as f:
                    card_collection = pickle.load(f)
                print(
                    f"Loaded {len(card_collection)} cards from local cache file.",
                    flush=True,
                )
                cache_is_valid = True

        if not cache_is_valid and db_client:
            print(
                "Local cache missing or expired. Loading card collection from Firestore...",
                flush=True,
            )
            card_collection = CardCollection()
            card_collection.load_from_firestore(db_client)
            print(
                f"Loaded {len(card_collection)} cards from Firestore. Saving to cache.",
                flush=True,
            )
            with open(CARD_CACHE_PATH, "wb") as f:
                pickle.dump(card_collection, f)
        elif not card_collection:
            print(
                "WARNING: Firestore client not available and no local cache. Card collection will be empty.",
                flush=True,
            )
            card_collection = CardCollection()

    except Exception as e:
        print(f"CRITICAL: Error loading card collection: {e}", flush=True)
        card_collection = CardCollection()

    app.config["card_collection"] = card_collection

    google_bp = None
    if app.config.get("GOOGLE_OAUTH_CLIENT_ID") and app.config.get(
        "GOOGLE_OAUTH_CLIENT_SECRET"
    ):
        google_bp = make_google_blueprint(
            client_id=app.config["GOOGLE_OAUTH_CLIENT_ID"],
            client_secret=app.config["GOOGLE_OAUTH_CLIENT_SECRET"],
            scope=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ],
        )
        app.register_blueprint(google_bp, url_prefix="/login")
        from .routes.auth import google_authorized as google_auth_handler_function

        oauth_authorized.connect(google_auth_handler_function, sender=google_bp)
        print(
            f"Signal oauth_authorized connected for sender '{google_bp.name}'.",
            flush=True,
        )
    else:
        print(
            "WARNING: Google OAuth credentials not configured. Google Sign-In disabled."
        )

    app.config["ENERGY_ICON_URLS"] = {
        "Grass": "https://firebasestorage.googleapis.com/v0/b/pvpocket-dd286.firebasestorage.app/o/energy_icons%2Fgrass.png?alt=media&token=4d91420b-c0f1-47e6-9d4b-c9599f9a4d34",
        "Fire": "https://firebasestorage.googleapis.com/v0/b/pvpocket-dd286.firebasestorage.app/o/energy_icons%2Ffire.png?alt=media&token=476db9b6-f69a-41b6-beaf-fe44fcbe883c",
        "Water": "https://firebasestorage.googleapis.com/v0/b/pvpocket-dd286.firebasestorage.app/o/energy_icons%2Fwater.png?alt=media&token=f9903896-59b8-4122-83e4-35d4660be54c",
        "Lightning": "https://firebasestorage.googleapis.com/v0/b/pvpocket-dd286.firebasestorage.app/o/energy_icons%2Felectric.png?alt=media&token=f3593c9f-e4b1-45cb-b021-8e92c5b3117f",
        "Psychic": "https://firebasestorage.googleapis.com/v0/b/pvpocket-dd286.firebasestorage.app/o/energy_icons%2Fpsychic.png?alt=media&token=ece52e71-9a49-4200-8424-7f2708ca7b96",
        "Fighting": "https://firebasestorage.googleapis.com/v0/b/pvpocket-dd286.firebasestorage.app/o/energy_icons%2Ffighting.png?alt=media&token=c8269b93-7ed5-4f3c-bceb-324074dc5207",
        "Darkness": "https://firebasestorage.googleapis.com/v0/b/pvpocket-dd286.firebasestorage.app/o/energy_icons%2Fdark.png?alt=media&token=358b8eba-e5ef-4293-95cc-5c745591472b",
        "Metal": "https://firebasestorage.googleapis.com/v0/b/pvpocket-dd286.firebasestorage.app/o/energy_icons%2Fmetal.png?alt=media&token=d0c1481a-c9e5-49a8-a8cd-8300a3c4f73e",
        "Dragon": "https://firebasestorage.googleapis.com/v0/b/pvpocket-dd286.firebasestorage.app/o/energy_icons%2Fdragon.png?alt=media&token=0f9630da-e7a2-478b-a0d3-f3b6d5948eb3",
        "Colorless": "https://firebasestorage.googleapis.com/v0/b/pvpocket-dd286.firebasestorage.app/o/energy_icons%2Fcolorless.png?alt=media&token=ffbd920d-85e9-4a92-b9a3-54494ff69060",
    }

    @app.route("/api/refresh-cards", methods=["POST"])
    def refresh_cards_cache():
        # 1. Security Check
        provided_key = request.headers.get("X-Refresh-Key")
        if not provided_key or provided_key != current_app.config["REFRESH_SECRET_KEY"]:
            return jsonify({"error": "Unauthorized"}), 401

        # 2. Acquire Lock and Refresh
        if cache_lock.acquire(blocking=False):
            try:
                print(
                    "Refresh request received. Forcing reload from Firestore...",
                    flush=True,
                )
                new_collection = _load_cards_from_firestore_and_cache()
                if new_collection:
                    current_app.config["card_collection"] = new_collection
                    message = f"Successfully reloaded {len(new_collection)} cards."
                    print(message, flush=True)
                    return jsonify({"status": "success", "message": message}), 200
                else:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "Failed to load cards from Firestore.",
                            }
                        ),
                        500,
                    )
            finally:
                cache_lock.release()
        else:
            return (
                jsonify(
                    {
                        "status": "ignored",
                        "message": "A refresh is already in progress.",
                    }
                ),
                429,
            )

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(battle_bp)
    app.register_blueprint(decks_bp)
    app.register_blueprint(meta_bp)
    app.register_blueprint(collection_bp)

    app.before_request(check_username_requirement)

    return app
