from flask import Flask, session
from .config import config
from .routes.main import main_bp
from .routes.auth import auth_bp
from .routes.battle import battle_bp
from .routes.decks import decks_bp
from .routes.meta import meta_bp
from .routes.collection import collection_bp
from Card import Card, CardCollection
from Deck import Deck
from battle_engine import BattleEngine, SimpleAI
import os
import json
import sys
import random
import time
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

def create_app(config_name='default'):
    # Create Flask application
    # Add the template_folder parameter pointing to the correct directory
    app = Flask(__name__, template_folder='../templates', static_folder='../images', static_url_path='/images')
    
    # Load configuration
    app_config = config[config_name]
    app.config.from_object(app_config)
    
    # Create necessary directories
    app_config.create_directories()

    # Initialize card collection
    card_collection = CardCollection()
    try:
        print("Loading card collection from database...")
        card_collection.load_from_db()
        print(f"Loaded {len(card_collection)} cards from database.")
    except Exception as e:
        print(f"Error loading from database: {e}")
        try:
            print("Trying to load from CSV...")
            card_collection.load_from_csv()
            print(f"Loaded {len(card_collection)} cards from CSV.")
        except Exception as e:
            print(f"Error loading from CSV: {e}")
            print("Could not load card collection. Please ensure database or CSV file exists.")
            sys.exit(1)

    # Load or initialize data files
    def load_json_file(filepath, default=None):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default or {}

    # Load battle history, meta stats, and users
    battle_history = load_json_file(app_config.BATTLE_HISTORY_FILE, [])
    meta_stats = load_json_file(app_config.META_STATS_FILE, {"decks": {}, "last_updated": ""})
    users = load_json_file(app_config.USERS_FILE, {})

    # Save functions
    def save_battle_history(history):
        with open(app_config.BATTLE_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)

    def save_meta_stats(stats):
        stats["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(app_config.META_STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)

    def save_users():
        with open(app_config.USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)

    def update_meta_stats(deck1_name, deck2_name, winner_name, turns):
        # (Existing update_meta_stats implementation from original app.py)
        # Full implementation would be here
        pass
    
    @app.context_processor
    def inject_user():
        """Make user data and login status available to all templates."""
        user = None
        if 'user_id' in session:
            user = app.config['users'].get(session.get('user_id'))
        
        return {
            'user_logged_in': 'user_id' in session,
            'username': session.get('username', None)
        }
    


    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(battle_bp)
    app.register_blueprint(decks_bp)
    app.register_blueprint(meta_bp)
    app.register_blueprint(collection_bp)

    # Store global variables and functions in app config
    app.config['card_collection'] = card_collection
    app.config['battle_history'] = battle_history
    app.config['meta_stats'] = meta_stats
    app.config['users'] = users
    
    # Store save functions in app config
    app.config['save_battle_history'] = save_battle_history
    app.config['save_meta_stats'] = save_meta_stats
    app.config['save_users'] = save_users
    app.config['update_meta_stats'] = update_meta_stats


    return app