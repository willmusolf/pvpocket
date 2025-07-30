# shared_utils.py

import os
import requests
import socket
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud import secretmanager
import json


def initialize_firebase():
    """Initializes a single Firebase app instance if not already done."""
    if not firebase_admin._apps:
        try:
            project_id = os.environ.get("GCP_PROJECT_ID")
            secret_name = os.environ.get("FIREBASE_SECRET_NAME")
            bucket_name = os.environ.get("FIREBASE_STORAGE_BUCKET")

            if not bucket_name:
                raise ValueError(
                    "FIREBASE_STORAGE_BUCKET environment variable not set."
                )

            if project_id and secret_name:
                # Only log Firebase initialization in development
                if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
                    print("Initializing Firebase from Secret Manager...")
                client = secretmanager.SecretManagerServiceClient()
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                secret_payload = response.payload.data.decode("UTF-8")
                cred_dict = json.loads(secret_payload)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
            else:
                # Only log Firebase initialization in development
                if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
                    print("Initializing Firebase with Application Default Credentials...")
                firebase_admin.initialize_app(options={"storageBucket": bucket_name})

            # Only log success in development
            if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
                print("Firebase initialized successfully.")
        except Exception as e:
            # Always log critical Firebase errors
            print(f"CRITICAL ERROR: Failed to initialize Firebase Admin SDK: {e}")
            exit(1)


def trigger_cache_refresh():
    """Triggers the cache refresh endpoint on your web app."""
    load_dotenv()
    base_url = os.getenv("WEBSITE_URL")
    refresh_key = os.getenv("REFRESH_SECRET_KEY")

    if not base_url or not refresh_key:
        # Only log in development
        if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
            print(
                "ERROR: WEBSITE_URL or REFRESH_SECRET_KEY not set. Cannot trigger refresh."
            )
        return

    refresh_url = f"{base_url}/api/refresh-cards"
    headers = {"X-Refresh-Key": refresh_key}
    # Only log cache refresh in development
    if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
        print(f"Triggering cache refresh at {refresh_url}...")
    try:
        response = requests.post(refresh_url, headers=headers, timeout=60)
        if response.status_code == 200:
            # Only log success in development
            if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
                print(f"SUCCESS: Cache refresh triggered: {response.json()}")
        else:
            # Only log errors in development
            if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
                print(
                    f"ERROR: Cache refresh failed. Status: {response.status_code}, Text: {response.text}"
                )
    except requests.exceptions.RequestException as e:
        # Only log connection errors in development
        if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
            print(f"CRITICAL ERROR: Could not connect to refresh cache: {e}")


def is_emulator_running(host='localhost', port=8080):
    """Check if Firebase emulator is running on the specified port."""
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except (socket.error, ConnectionRefusedError):
        return False


def create_initial_emulator_data():
    """Create initial sample data in emulator if it's empty."""
    if not is_emulator_running():
        return
    
    try:
        # Connect to emulator using the same project ID as the main app
        main_project_id = os.environ.get('GCP_PROJECT_ID', 'pvpocket-dd286')
        emulator_app = firebase_admin.initialize_app(
            name='emulator_check_app',
            options={'projectId': main_project_id}
        )
        
        # Set emulator environment
        old_host = os.environ.get('FIRESTORE_EMULATOR_HOST')
        os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
        
        emulator_db = firestore.client(app=emulator_app)
        
        # Check if cards collection exists
        cards_ref = emulator_db.collection('cards')
        existing_cards = list(cards_ref.limit(1).stream())
        
        if existing_cards:
            print("📊 Emulator already has data")
            return
        
        print("📝 Creating initial sample data in emulator...")
        
        # Create sample data (same as services.py sample cards but in emulator)
        from Card import Card
        
        sample_cards = [
            {
                "id": 1,
                "name": "Pikachu",
                "energy_type": "Lightning",
                "set_name": "Sample Set",
                "set_code": "SAM",
                "card_number": 1,
                "card_number_str": "001",
                "card_type": "Pokemon",
                "hp": 60,
                "attacks": [{"name": "Thunder Shock", "cost": ["Lightning"], "damage": 30}],
                "firebase_image_url": "https://cdn.pvpocket.xyz/cards/sample_pikachu.png",
                "rarity": "Common",
                "pack": "Sample Pack"
            },
            {
                "id": 2,
                "name": "Charizard",
                "energy_type": "Fire",
                "set_name": "Sample Set",
                "set_code": "SAM",
                "card_number": 2,
                "card_number_str": "002",
                "card_type": "Pokemon",
                "hp": 120,
                "attacks": [{"name": "Fire Blast", "cost": ["Fire", "Fire"], "damage": 80}],
                "firebase_image_url": "https://cdn.pvpocket.xyz/cards/sample_charizard.png",
                "rarity": "Rare",
                "pack": "Sample Pack"
            },
            {
                "id": 3,
                "name": "Blastoise",
                "energy_type": "Water",
                "set_name": "Sample Set",
                "set_code": "SAM",
                "card_number": 3,
                "card_number_str": "003",
                "card_type": "Pokemon",
                "hp": 100,
                "attacks": [{"name": "Hydro Pump", "cost": ["Water", "Water"], "damage": 70}],
                "firebase_image_url": "https://cdn.pvpocket.xyz/cards/sample_blastoise.png",
                "rarity": "Rare",
                "pack": "Sample Pack"
            }
        ]
        
        # Create set document
        set_ref = emulator_db.collection("cards").document("sample_set")
        set_ref.set({"name": "Sample Set", "description": "Development cards"})
        
        # Add cards
        for card_data in sample_cards:
            card_ref = set_ref.collection("set_cards").document(str(card_data["id"]))
            card_ref.set(card_data)
        
        # Create sample configuration
        config_ref = emulator_db.collection("internal_config").document("sets_tracker")
        config_ref.set({
            "known_codes": ["SAM"],
            "last_updated": firestore.SERVER_TIMESTAMP
        })
        
        # Create a sample user (for when you're logged in)
        sample_user_ref = emulator_db.collection("users").document("sample-user-id")
        sample_user_ref.set({
            "email": "user@example.com",
            "username": "developer",
            "deck_ids": [],
            "collection": {},
            "created_at": firestore.SERVER_TIMESTAMP
        })
        
        print("✅ Created sample data in emulator")
        
    except Exception as e:
        print(f"❌ Error creating initial data: {e}")
    finally:
        # Cleanup
        if old_host:
            os.environ['FIRESTORE_EMULATOR_HOST'] = old_host
        elif 'FIRESTORE_EMULATOR_HOST' in os.environ:
            del os.environ['FIRESTORE_EMULATOR_HOST']
        
        if 'emulator_check_app' in firebase_admin._apps:
            firebase_admin.delete_app(firebase_admin.get_app('emulator_check_app'))


def sync_to_local_emulator():
    """Sync production Firestore data to local emulator for development."""
    # Only attempt sync if we're in development/scraping context
    if not (os.environ.get('FLASK_DEBUG') == '1' or 
            os.environ.get('FLASK_CONFIG') == 'development' or
            os.environ.get('JOB_TYPE')):  # Running in scraping job
        return
    
    if not is_emulator_running():
        print("🔍 Local emulator not running - skipping sync")
        return
    
    print("🔄 Syncing production data to local emulator...")
    
    try:
        # Temporarily clear emulator environment to connect to production
        original_emulator_host = os.environ.get('FIRESTORE_EMULATOR_HOST')
        if 'FIRESTORE_EMULATOR_HOST' in os.environ:
            del os.environ['FIRESTORE_EMULATOR_HOST']
        
        # Get production Firestore client (should connect to real Firestore)
        prod_db = firestore.client()
        
        # Connect to emulator
        emulator_app = None
        try:
            # Create separate app for emulator connection using same project ID
            main_project_id = os.environ.get('GCP_PROJECT_ID', 'pvpocket-dd286')
            emulator_app = firebase_admin.initialize_app(
                name='emulator_app',
                options={'projectId': main_project_id}
            )
            
            # Set emulator environment for this connection
            old_host = os.environ.get('FIRESTORE_EMULATOR_HOST')
            os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
            
            emulator_db = firestore.client(app=emulator_app)
            
            # Sync cards collection (most important for development)
            print("📋 Syncing cards collection...")
            cards_ref = prod_db.collection('cards')
            
            # Get all card set documents from production
            set_docs = list(cards_ref.stream())
            print(f"🔍 Found {len(set_docs)} card sets in production")
            
            if not set_docs:
                print("❌ No card sets found in production database!")
                return
            
            total_synced = 0
            for set_doc in set_docs:
                set_data = set_doc.to_dict()
                set_id = set_doc.id
                
                # Copy set document to emulator
                emulator_cards_ref = emulator_db.collection('cards').document(set_id)
                emulator_cards_ref.set(set_data)
                
                # Copy all cards in this set's subcollection
                cards_subcollection = set_doc.reference.collection('set_cards')
                card_docs = list(cards_subcollection.stream())
                card_count = 0
                
                for card_doc in card_docs:
                    card_data = card_doc.to_dict()
                    card_id = card_doc.id
                    
                    # Copy card to emulator
                    emulator_card_ref = emulator_cards_ref.collection('set_cards').document(card_id)
                    emulator_card_ref.set(card_data)
                    card_count += 1
                
                total_synced += card_count
                if card_count > 0:
                    print(f"  ✅ {set_id}: {card_count} cards")
                else:
                    print(f"  ⚠️  {set_id}: 0 cards")
            
            print(f"📊 Total cards synced: {total_synced}")
            
            # Sync internal_config collection (for app configuration)
            print("⚙️  Syncing internal configuration...")
            config_ref = prod_db.collection('internal_config')
            for config_doc in config_ref.stream():
                config_data = config_doc.to_dict()
                config_id = config_doc.id
                
                emulator_config_ref = emulator_db.collection('internal_config').document(config_id)
                emulator_config_ref.set(config_data)
                print(f"  ✅ Config: {config_id}")
            
            print("✅ Emulator sync completed successfully!")
            
        finally:
            # Restore original emulator host setting for emulator connection
            if old_host:
                os.environ['FIRESTORE_EMULATOR_HOST'] = old_host
            elif 'FIRESTORE_EMULATOR_HOST' in os.environ:
                del os.environ['FIRESTORE_EMULATOR_HOST']
            
            # Clean up emulator app
            if emulator_app:
                firebase_admin.delete_app(emulator_app)
                
        # Restore emulator environment for main app
        if original_emulator_host:
            os.environ['FIRESTORE_EMULATOR_HOST'] = original_emulator_host
                
    except Exception as e:
        print(f"❌ Error syncing to emulator: {e}")
        # Don't fail the main scraping job if emulator sync fails
        pass
