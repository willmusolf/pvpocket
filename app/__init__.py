from flask import Flask, session, current_app, request, jsonify, g, render_template
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
from typing import Dict, Any
from google.cloud import secretmanager
from google.api_core.exceptions import NotFound, PermissionDenied
from .cache_manager import cache_manager
from .security import init_security, security_manager
from flask_mail import Mail

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
from .routes.internal import internal_bp
from .routes.admin import admin_bp
from Card import Card, CardCollection
from Deck import Deck

from flask_dance.consumer import oauth_authorized

from better_profanity import profanity

from dotenv import (
    load_dotenv,
)

load_dotenv()

def _load_cards_from_firestore_and_cache():
    """Load card collection from Firestore and cache in Redis."""
    # Only log in debug mode
    if current_app.debug:
        print("Attempting to load card collection from Firestore...", flush=True)
    db_client = current_app.config.get("FIRESTORE_DB")
    if not db_client:
        if current_app.debug:
            print("ERROR: Firestore client not available for card loading.", flush=True)
        return None

    try:
        card_collection = CardCollection()
        card_collection.load_from_firestore(db_client)
        # Only log in debug mode
        if current_app.debug:
            print(
                f"Loaded {len(card_collection)} cards from Firestore. Saving to Redis cache.",
                flush=True,
            )
        # Cache for 24 hours instead of 30 days for better data freshness
        cache_manager.set_card_collection(card_collection, ttl_hours=24)
        return card_collection
    except Exception as e:
        # Only log critical errors in debug mode
        if current_app.debug:
            print(
                f"CRITICAL: Failed to load cards from Firestore and update cache: {e}",
                flush=True,
            )
        return None


def create_app(config_name="default"):
    startup_start_time = time.time()
    
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

    # Initialize critical services first (security, auth, database)
    
    profanity.load_censor_words()

    # Initialize Firebase (critical for database access)
    
    if not firebase_admin._apps:
        try:
            bucket_name = "pvpocket-dd286.firebasestorage.app"
            project_id = app.config.get("GCP_PROJECT_ID")
            secret_name = app.config.get("FIREBASE_SECRET_NAME")

            # Check if running with Firebase emulator
            # Only use emulator for local development, never in cloud environments
            is_local_development = (
                os.environ.get('SERVER_SOFTWARE', '').startswith('werkzeug') or  # Flask dev server
                not os.environ.get('GAE_ENV') and not os.environ.get('GAE_APPLICATION')  # Not Google App Engine
            )
            
            if (is_local_development and 
                (os.environ.get('FIRESTORE_EMULATOR_HOST') or 
                 os.environ.get('RUN_INTEGRATION_TESTS') or 
                 os.environ.get('FORCE_EMULATOR_MODE'))):
                # Use emulator configuration - match sync process project ID 
                emulator_project_id = os.environ.get('GCP_PROJECT_ID', 'demo-test-project')
                
                # Only show in main process
                if os.environ.get('WERKZEUG_RUN_MAIN'):
                    print("🔥 FIREBASE: Using Firebase Emulator (FREE - no production costs!)")
                    print(f"🔗 Emulator Host: {os.environ.get('FIRESTORE_EMULATOR_HOST', 'localhost:8080')}")
                    print(f"📋 Project ID: {emulator_project_id} (matching REST API seeding)")
                # Emulator mode detected
                
                # Set environment variable to ensure consistent project ID
                os.environ['GCLOUD_PROJECT'] = emulator_project_id
                os.environ['FIREBASE_PROJECT_ID'] = emulator_project_id
                
                # Ensure emulator host is properly set - CRITICAL for CI
                emulator_host = os.environ.get('FIRESTORE_EMULATOR_HOST')
                if not emulator_host:
                    # Force emulator host if not set (CI environment)
                    emulator_host = '127.0.0.1:8080'
                    print("⚠️ FIRESTORE_EMULATOR_HOST not set, forcing to 127.0.0.1:8080")
                elif ':' not in emulator_host:
                    emulator_host = f"{emulator_host}:8080"
                
                # CRITICAL: Set the emulator host environment variable
                os.environ['FIRESTORE_EMULATOR_HOST'] = emulator_host
                
                # CRITICAL: Disable credentials for emulator to bypass authentication
                if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                    del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
                    
                # Only show debug messages in main process
                if os.environ.get('WERKZEUG_RUN_MAIN'):
                    print(f"🎯 FORCED FIRESTORE_EMULATOR_HOST: {emulator_host}")
                    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                        print("🔧 Removed GOOGLE_APPLICATION_CREDENTIALS for emulator")
                    else:
                        print("🔧 GOOGLE_APPLICATION_CREDENTIALS already not set")
                
                # Environment variables configured for emulator
                
                try:
                    # Try to initialize without credentials first (emulator mode)
                    firebase_admin.initialize_app(options={
                        'projectId': emulator_project_id,
                        'storageBucket': bucket_name
                    })
                    if os.environ.get('WERKZEUG_RUN_MAIN'):
                        print("✅ Firebase Admin SDK initialized with emulator settings (no auth)")
                except Exception as e:
                    print(f"⚠️ Firebase Admin SDK init failed: {e}")
                    # Fallback initialization
                    firebase_admin.initialize_app()
                    print("✅ Firebase Admin SDK initialized with fallback")
            elif not is_local_development and (os.environ.get('FIRESTORE_EMULATOR_HOST') or 
                                               os.environ.get('RUN_INTEGRATION_TESTS') or 
                                               os.environ.get('FORCE_EMULATOR_MODE')):
                # Running in cloud environment but emulator variables are set - ignore them
                print("🚨 FIREBASE: Emulator variables detected in cloud environment - ignoring for production safety")
                # Cloud environment detected with emulator variables - ignoring
                
                # Clear any emulator environment variables to ensure production Firestore connection
                if 'FIRESTORE_EMULATOR_HOST' in os.environ:
                    del os.environ['FIRESTORE_EMULATOR_HOST']
                    print("🔧 Cleared FIRESTORE_EMULATOR_HOST for production")
                
                # Use production configuration
                if project_id and secret_name:
                    client = secretmanager.SecretManagerServiceClient()
                    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                    response = client.access_secret_version(request={"name": name})
                    secret_payload = response.payload.data.decode("UTF-8")
                    cred_dict = json.loads(secret_payload)
                    cred = credentials.Certificate(cred_dict)
                    print("🔥 FIREBASE: Using Production Firestore (REAL COSTS)")
                    print(f"📊 Project: {project_id}")
                    firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
                else:
                    print("🔥 FIREBASE: Using Default Configuration (REAL COSTS)")
                    firebase_admin.initialize_app(options={"storageBucket": bucket_name})
            elif project_id and secret_name:
                client = secretmanager.SecretManagerServiceClient()
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                secret_payload = response.payload.data.decode("UTF-8")
                cred_dict = json.loads(secret_payload)
                cred = credentials.Certificate(cred_dict)
                print("🔥 FIREBASE: Using Production Firestore (REAL COSTS)")
                print(f"📊 Project: {project_id}")
                firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
            else:
                print("🔥 FIREBASE: Using Default Configuration (REAL COSTS)")
                firebase_admin.initialize_app(options={"storageBucket": bucket_name})
        except Exception as e:
            # Only log critical Firebase errors in debug mode
            if config_name == 'development':
                print(
                    f"CRITICAL ERROR: Failed to initialize Firebase Admin SDK: {e}",
                    flush=True,
                )
            firebase_admin.initialize_app()

    db_client = firestore.client()
    app.config["FIRESTORE_DB"] = db_client
    
    # Firestore client initialized
    login_manager.init_app(app)
    
    # Initialize Flask-Mail for email functionality with secure credentials
    # Only initialize once in the main process, not in the reloader process
    if os.environ.get('WERKZEUG_RUN_MAIN') or not app.debug:
        try:
            from .secret_manager_utils import get_email_credentials
            
            # Load email credentials securely (will use cache on restart)
            mail_username, mail_password = get_email_credentials()
            if mail_username and mail_password:
                app.config['MAIL_USERNAME'] = mail_username
                app.config['MAIL_PASSWORD'] = mail_password
            else:
                app.logger.warning("Email credentials not available - email functionality disabled")
            
            mail = Mail(app)
            
            # Initialize email service
            from .email_service import init_email_service
            init_email_service(app, mail)
            
        except Exception as e:
            app.logger.error(f"Failed to initialize email service: {str(e)}")
            import traceback
            app.logger.error(f"Email service traceback: {traceback.format_exc()}")
            # Initialize basic mail anyway to prevent app startup failure
            mail = Mail(app)
    else:
        # Email service skipped in reloader process
        mail = None
    
    # Initialize security middleware (rate limiting, security headers)
    init_security(app)
    
    # Initialize non-critical services (can be moved later if needed)
    
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
        # Only log profile icon errors in debug mode
        if config_name == 'development':
            print(f"CRITICAL ERROR in profile icon loading: {e}", flush=True)
        app.config["PROFILE_ICON_FILENAMES"] = []
        app.config["PROFILE_ICON_URLS"] = {}
        app.config["DEFAULT_PROFILE_ICON_URL"] = ""

    # Schedule deferred card collection initialization
    # This prevents blocking startup while ensuring cards are available quickly
    # Schedule deferred card collection initialization
    
    # Import services to register background task handlers
    from .services import CardService
    from .task_queue import task_queue
    
    # Register card loading task handler
    def card_loading_handler(payload: Dict[str, Any]):
        """Background task to load card collection after startup."""
        try:
            with app.app_context():
                # Preserve emulator environment in background task
                emulator_host = os.environ.get('FIRESTORE_EMULATOR_HOST')
                if emulator_host:
                    # Ensure emulator connection is maintained in background task
                    os.environ['FIRESTORE_EMULATOR_HOST'] = emulator_host
                
                # Only log background loading in debug
                if config_name == 'development':
                    app.logger.debug("🔄 Background: Loading card collection...")
                collection = CardService._load_full_collection(cache_as_full=True)
                # Only log success in debug
                if config_name == 'development':
                    app.logger.debug(f"✅ Background: Loaded and cached {len(collection)} cards.")
        except Exception as e:
            # Only log errors in debug
            if config_name == 'development':
                app.logger.error(f"❌ Background card loading failed: {e}")
            import traceback
            traceback.print_exc()
    
    task_queue.register_task_handler("load_card_collection", card_loading_handler)
    
    # Schedule the card loading task to run after startup (5 second delay)
    # Only run in main process, not in Flask reloader process
    # Skip card loading in reloader process, use appropriate loading strategy for environment
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        # This is the reloader process, skip background task scheduling
        pass
    elif app.config.get('LAZY_LOAD_CARDS'):
        # Production lazy loading - only load cards when actually requested
        print("💰 CARD LOADING: LAZY (only loads on first user request)")
        print("📊 Cards loaded: 0 (will load ~1300 when user visits)")
        if config_name == 'production':
            print("⚡ Deferred card loading: LAZY (will load on first user request)")
    elif os.environ.get('FIRESTORE_EMULATOR_HOST'):
        # Emulator mode - load immediately since it's free and fast
        if os.environ.get('WERKZEUG_RUN_MAIN'):
            print("💰 CARD LOADING: EMULATOR (loads full collection immediately)")
            print("📊 Cards loaded: All production data from emulator (FREE)")
        try:
            # Load cards immediately from emulator within app context
            with app.app_context():
                collection = CardService._load_full_collection(cache_as_full=True)
                if config_name == 'development' and os.environ.get('WERKZEUG_RUN_MAIN'):
                    print(f"✅ Loaded {len(collection)} cards from emulator")
        except Exception as e:
            if config_name == 'development':
                print(f"❌ Error loading from emulator: {e}")
    else:
        # This is the main app process and not minimal mode, schedule the background task
        print("💰 CARD LOADING: FULL (loads all cards immediately)")
        print("📊 Cards loaded: ~1300 (full collection)")
        task_queue.enqueue_task("load_card_collection", {}, delay_seconds=5)
    
    # Deferred card collection loading scheduled
    
    # Note: Cards will be loaded on-demand if requested before background loading completes
    # This ensures the app starts quickly while maintaining functionality

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
        context_vars = {}
        
        if current_user.is_authenticated:
            user_data = getattr(current_user, "data", {})
            icon_filename = user_data.get("profile_icon")
            icon_urls = current_app.config.get("PROFILE_ICON_URLS", {})
            default_url = current_app.config.get("DEFAULT_PROFILE_ICON_URL", "")
            profile_icon_url = icon_urls.get(icon_filename, default_url)
            context_vars["current_user_profile_icon_url"] = profile_icon_url
            
            # Check if user is admin using ADMIN_EMAILS environment variable
            env_admins = os.environ.get("ADMIN_EMAILS", "")
            is_admin = False
            if env_admins and hasattr(current_user, 'email'):
                admin_emails = [email.strip() for email in env_admins.split(",") if email.strip()]
                is_admin = current_user.email in admin_emails
            context_vars["is_admin"] = is_admin
        else:
            context_vars["current_user_profile_icon_url"] = current_app.config.get(
                "DEFAULT_PROFILE_ICON_URL", ""
            )
            context_vars["is_admin"] = False
        
        return context_vars

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

    @app.route("/metrics", methods=["GET"])
    def metrics():
        """Get basic performance metrics."""
        try:
            from .monitoring import performance_monitor
            from .cache_manager import cache_manager
            
            # Determine Firebase mode
            firebase_mode = "Unknown"
            if os.environ.get('FIRESTORE_EMULATOR_HOST'):
                firebase_mode = "Emulator (FREE)"
            elif app.config.get('LAZY_LOAD_CARDS'):
                firebase_mode = "Production + Lazy Loading (SMART)"
            else:
                firebase_mode = "Production + Full Loading (EXPENSIVE)"
            
            metrics_data = {
                "firebase_mode": firebase_mode,
                "app_config": config_name,
                "cache_hit_rate": f"{performance_monitor.metrics.get_cache_hit_rate():.1f}%",
                "cache_healthy": cache_manager.health_check(),
                "firestore_usage": performance_monitor.metrics.get_firestore_usage_stats(),
                "cost_optimizations": {
                    "using_emulator": bool(os.environ.get('FIRESTORE_EMULATOR_HOST')),
                    "lazy_loading": app.config.get('LAZY_LOAD_CARDS', False)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return jsonify(metrics_data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/refresh-cards", methods=["POST"])
    @security_manager.require_refresh_key
    def refresh_cards_cache():
        """Refresh card collection cache using Redis."""
        
        try:
            # Invalidate existing cache
            cache_manager.invalidate_card_cache()
            
            # Load fresh data from Firestore  
            from .services import card_service
            success = card_service.refresh_card_collection()
            if success:
                message = f"Successfully refreshed card collection cache."
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
        except Exception as e:
            # Only log cache refresh errors in debug
            if config_name == 'development':
                print(f"Error refreshing cards cache: {e}")
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Error refreshing cache: {str(e)}",
                    }
                ),
                500,
            )

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(battle_bp)
    app.register_blueprint(decks_bp)
    app.register_blueprint(meta_bp)
    app.register_blueprint(collection_bp)
    app.register_blueprint(friends_bp)
    app.register_blueprint(internal_bp)
    app.register_blueprint(admin_bp)

    # Initialize monitoring system (after all other services)
    # Start performance monitoring only in main process
    from .monitoring import performance_monitor
    if os.environ.get('WERKZEUG_RUN_MAIN'):
        performance_monitor.start_monitoring()
    
    # Startup summary
    startup_time = time.time() - startup_start_time
    # Only show startup summary in debug mode and in the main process (not reloader)
    if config_name == 'development' and os.environ.get('WERKZEUG_RUN_MAIN'):
        print("\n" + "="*50)
        print("🚀 POKEMON TCG POCKET - OPTIMIZED STARTUP")
        print("="*50)
        print("✅ In-Memory Cache: Active")
        print("✅ Database Connection Pool: Active") 
        print("✅ Background Task Queue: Active")
        print("✅ Performance Monitor: Active")
        print("✅ Service Layer: Loaded")
        print("⚡ Deferred Card Loading: Scheduled")
        print(f"⏱️  Total Startup Time: {startup_time:.2f}s")
        print("="*50 + "\n")

    app.before_request(check_username_requirement)

    @app.after_request
    def add_cache_control_headers(response):
        if 'user_id' in session:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # Add critical error handlers for production alerts
    if config_name == 'production':
        from .alerts import alert_server_error, alert_database_failure
        
        @app.errorhandler(500)
        def handle_500_error(e):
            alert_server_error(f"500 Error: {str(e)}")
            # Return proper HTML error page, not JSON
            try:
                return render_template('error.html', error="Internal server error"), 500
            except:
                return "<h1>Internal Server Error</h1><p>Something went wrong. The team has been notified.</p>", 500

    # Track app startup time for lazy loading
    app._startup_time = time.time()
    
    return app
