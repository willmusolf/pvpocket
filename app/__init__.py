from flask import Flask, session, current_app, request, jsonify, g
from .config import config
import firebase_admin
from firebase_admin import credentials, firestore, storage
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
from .routes.friends import friends_bp
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
        static_folder="../static",
    )
    app_config = config[config_name]
    app.config.from_object(app_config)
    app.config['FLASK_ENV'] = config_name
    

    if not app.config.get("SECRET_KEY"):
        raise ValueError(
            "FATAL ERROR: SECRET_KEY is not set. Please set it in your .env file."
        )

    profanity.load_censor_words()

    if not firebase_admin._apps:
        try:
            bucket_name = "pvpocket-dd286.firebasestorage.app"
            project_id = app.config.get("GCP_PROJECT_ID")
            secret_name = app.config.get("FIREBASE_SECRET_NAME")

            if project_id and secret_name:
                client = secretmanager.SecretManagerServiceClient()
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                secret_payload = response.payload.data.decode("UTF-8")
                cred_dict = json.loads(secret_payload)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
            else:
                firebase_admin.initialize_app(options={"storageBucket": bucket_name})
        except Exception as e:
            print(
                f"CRITICAL ERROR: Failed to initialize Firebase Admin SDK: {e}",
                flush=True,
            )
            firebase_admin.initialize_app()

    app.config["FIRESTORE_DB"] = firestore.client()
    login_manager.init_app(app)

    try:
        bucket = storage.bucket()
        blobs = list(bucket.list_blobs(prefix="profile_icons/"))
        icon_filenames = [
            blob.name.split("/")[-1]
            for blob in blobs
            if blob.name.split("/")[-1] and not blob.name.endswith("/")
        ]

        DEFAULT_PROFILE_ICON = "default.png"
        if DEFAULT_PROFILE_ICON in icon_filenames:
            icon_filenames.remove(DEFAULT_PROFILE_ICON)

        base_url = app.config['ASSET_BASE_URL']
        all_icon_urls = {}
        # Always use CDN for profile icons to avoid CORS issues
        cdn_base_url = 'https://cdn.pvpocket.xyz'
        for icon in icon_filenames + [DEFAULT_PROFILE_ICON]:
            all_icon_urls[icon] = f"{cdn_base_url}/profile_icons/{icon}"

        app.config["PROFILE_ICON_FILENAMES"] = sorted(icon_filenames)
        app.config["PROFILE_ICON_URLS"] = all_icon_urls
        app.config["DEFAULT_PROFILE_ICON_URL"] = all_icon_urls.get(
            DEFAULT_PROFILE_ICON, ""
        )

    except Exception as e:
        print(f"CRITICAL ERROR in profile icon loading: {e}", flush=True)
        app.config["PROFILE_ICON_FILENAMES"] = []
        app.config["PROFILE_ICON_URLS"] = {}
        app.config["DEFAULT_PROFILE_ICON_URL"] = ""

    card_collection = None
    db_client = app.config.get("FIRESTORE_DB")
    try:
        cache_is_valid = False
        if os.path.exists(CARD_CACHE_PATH):
            file_mod_time = os.path.getmtime(CARD_CACHE_PATH)
            if (time.time() - file_mod_time) < CACHE_DURATION_SECONDS:
                with open(CARD_CACHE_PATH, "rb") as f:
                    card_collection = pickle.load(f)
                cache_is_valid = True
        if not cache_is_valid and db_client:
            card_collection = CardCollection()
            card_collection.load_from_firestore(db_client)
            with open(CARD_CACHE_PATH, "wb") as f:
                pickle.dump(card_collection, f)
        elif not card_collection:
            card_collection = CardCollection()
    except Exception as e:
        print(f"CRITICAL: Error loading card collection: {e}", flush=True)
        card_collection = CardCollection()

    app.config["card_collection"] = card_collection

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
        oauth_authorized.connect(google_auth_handler_function, sender=google_bp)

    # Energy icon mapping
    energy_icon_files = {
        "Grass": "grass.png",
        "Fire": "fire.png",
        "Water": "water.png",
        "Lightning": "electric.png",
        "Psychic": "psychic.png",
        "Fighting": "fighting.png",
        "Darkness": "dark.png",
        "Metal": "metal.png",
        "Dragon": "dragon.png",
        "Colorless": "colorless.png",
    }

    energy_icon_urls = {}
    # Always use CDN for energy icons to avoid CORS issues
    cdn_base_url = 'https://cdn.pvpocket.xyz'
    for energy_type, filename in energy_icon_files.items():
        energy_icon_urls[energy_type] = f"{cdn_base_url}/energy_icons/{filename}"

    app.config["ENERGY_ICON_URLS"] = energy_icon_urls

    @app.context_processor
    def inject_user_profile_icon():
        if current_user.is_authenticated:
            user_data = getattr(current_user, "data", {})
            icon_filename = user_data.get("profile_icon")
            icon_urls = current_app.config.get("PROFILE_ICON_URLS", {})
            default_url = current_app.config.get("DEFAULT_PROFILE_ICON_URL", "")
            profile_icon_url = icon_urls.get(icon_filename, default_url)
            return dict(current_user_profile_icon_url=profile_icon_url)
        return dict(
            current_user_profile_icon_url=current_app.config.get(
                "DEFAULT_PROFILE_ICON_URL", ""
            )
        )

    @app.template_filter('cdn_url')
    def cdn_url_filter(original_url):
        """Convert Firebase Storage URLs to CDN URLs"""
        if not original_url:
            return ''
        
        # If the URL already includes the CDN domain, return as-is
        if original_url.startswith('https://cdn.pvpocket.xyz'):
            return original_url
        
        # Convert Firebase Storage URLs to CDN URLs
        if 'firebasestorage.googleapis.com' in original_url or 'storage.googleapis.com' in original_url:
            import re
            from urllib.parse import unquote
            
            path = ''
            
            if 'firebasestorage.googleapis.com' in original_url:
                # Handle Firebase Storage URLs with encoded paths
                path_match = re.search(r'/o/([^?]+)', original_url)
                if path_match:
                    path = '/' + unquote(path_match.group(1))
            elif 'storage.googleapis.com' in original_url:
                # Handle Google Cloud Storage URLs  
                path_match = re.search(r'pvpocket-dd286\.firebasestorage\.app/(.+)$', original_url)
                if path_match:
                    path = '/' + path_match.group(1)
            
            if path:
                return 'https://cdn.pvpocket.xyz' + path
        
        # If it's a relative path, prepend the CDN base URL
        if original_url.startswith('/') or '://' not in original_url:
            return 'https://cdn.pvpocket.xyz' + (original_url if original_url.startswith('/') else '/' + original_url)
        
        # For any other URLs, return as-is (fallback)
        return original_url

    @app.route("/api/refresh-cards", methods=["POST"])
    def refresh_cards_cache():
        provided_key = request.headers.get("X-Refresh-Key")
        if not provided_key or provided_key != current_app.config["REFRESH_SECRET_KEY"]:
            return jsonify({"error": "Unauthorized"}), 401
        if cache_lock.acquire(blocking=False):
            try:
                new_collection = _load_cards_from_firestore_and_cache()
                if new_collection:
                    current_app.config["card_collection"] = new_collection
                    message = f"Successfully reloaded {len(new_collection)} cards."
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
    app.register_blueprint(friends_bp)

    app.before_request(check_username_requirement)

    @app.after_request
    def add_cache_control_headers(response):
        if 'user_id' in session:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    return app
