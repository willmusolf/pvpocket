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
    
    # Check if we're in a Cloud Run job (scraping context)
    is_cloud_job = os.environ.get('JOB_TYPE') is not None
    should_log = (os.environ.get('FLASK_DEBUG') == '1' or 
                  os.environ.get('FLASK_CONFIG') == 'development' or
                  is_cloud_job)

    if not base_url or not refresh_key:
        if should_log:
            print("ERROR: WEBSITE_URL or REFRESH_SECRET_KEY not set. Cannot trigger refresh.")
            if not base_url:
                print("  Missing: WEBSITE_URL")
            if not refresh_key:
                print("  Missing: REFRESH_SECRET_KEY")
        return

    refresh_url = f"{base_url}/api/refresh-cards"
    headers = {"X-Refresh-Key": refresh_key}
    
    if should_log:
        print(f"Triggering cache refresh at {refresh_url}...")
        
    try:
        response = requests.post(refresh_url, headers=headers, timeout=120)  # Increased timeout
        if response.status_code == 200:
            if should_log:
                print(f"SUCCESS: Cache refresh triggered: {response.json()}")
        else:
            # Always log errors
            print(f"ERROR: Cache refresh failed. Status: {response.status_code}, Text: {response.text}")
    except requests.exceptions.Timeout:
        # Always log timeout errors  
        print("ERROR: Cache refresh timed out after 120 seconds. The site may still be processing.")
    except requests.exceptions.RequestException as e:
        # Always log connection errors
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
        bucket_name = os.environ.get('FIREBASE_STORAGE_BUCKET', f'{main_project_id}.appspot.com')
        emulator_app = firebase_admin.initialize_app(
            name='emulator_check_app',
            options={
                'projectId': main_project_id,
                'storageBucket': bucket_name
            }
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


def documents_are_different(emulator_data, production_data):
    """Compare two document data dictionaries to see if they're different."""
    if emulator_data is None and production_data is None:
        return False
    if emulator_data is None or production_data is None:
        return True
    
    # Remove timestamp fields that always differ
    def clean_data(data):
        if not data:
            return {}
        cleaned = data.copy()
        # Remove fields that naturally differ between environments
        timestamp_fields = ['created_at', 'updated_at', 'last_login', 'timestamp']
        for field in timestamp_fields:
            if field in cleaned:
                cleaned.pop(field)
        return cleaned
    
    clean_emulator = clean_data(emulator_data)
    clean_production = clean_data(production_data)
    
    return clean_emulator != clean_production


def sync_to_local_emulator():
    """Smart sync: Only update differences between production and emulator."""
    import time
    
    # CRITICAL: Only run in scraping jobs, NOT in local development
    # This prevents local development from hitting production Firebase and causing costs
    if not os.environ.get('JOB_TYPE'):  # Only run in scraping jobs
        print("🔒 Sync skipped - only runs in scraping jobs to prevent production costs")
        return
    
    if not is_emulator_running():
        print("🔍 Local emulator not running - skipping sync")
        return
    
    print("🔄 Smart sync: Comparing emulator vs production...")
    start_time = time.time()
    
    # Store original emulator setting
    original_emulator_host = os.environ.get('FIRESTORE_EMULATOR_HOST')
    prod_app = None
    emulator_app = None
    
    try:
        # Clear emulator setting temporarily for production connection
        if 'FIRESTORE_EMULATOR_HOST' in os.environ:
            del os.environ['FIRESTORE_EMULATOR_HOST']
        
        # Initialize dedicated production app
        main_project_id = os.environ.get('GCP_PROJECT_ID', 'pvpocket-dd286')
        print("🔧 Initializing dedicated production Firebase connection...")
        
        # Initialize Firebase if not already done (for production access)
        if not firebase_admin._apps:
            initialize_firebase()
            prod_app = firebase_admin.get_app()
        else:
            # Create a separate app for production
            try:
                prod_app = firebase_admin.initialize_app(
                    name='production_sync_app',
                    options={'projectId': main_project_id}
                )
            except ValueError:
                # App already exists, get it
                prod_app = firebase_admin.get_app('production_sync_app')
        
        # Get production Firestore client (should connect to real Firestore)
        prod_db = firestore.client(app=prod_app)
        
        # Create separate app for emulator connection
        try:
            bucket_name = os.environ.get('FIREBASE_STORAGE_BUCKET', f'{main_project_id}.appspot.com')
            emulator_app = firebase_admin.initialize_app(
                name='emulator_app',
                options={
                    'projectId': main_project_id,
                    'storageBucket': bucket_name
                }
            )
        except ValueError:
            # App already exists, get it
            emulator_app = firebase_admin.get_app('emulator_app')
        
        # Set emulator environment for this connection
        os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
        emulator_db = firestore.client(app=emulator_app)
        
        # Get all collections dynamically with error handling
        print("🔍 Discovering collections...")
        try:
            prod_collections = list(prod_db.collections())
            print(f"📁 Found {len(prod_collections)} collections in production")
            
            if len(prod_collections) == 0:
                print("⚠️  No collections found in production - check Firebase connection")
                return
        except Exception as e:
            print(f"❌ Failed to discover collections: {e}")
            print("   This may be due to permissions or connectivity issues")
            return
        
        total_added = 0
        total_updated = 0
        total_unchanged = 0
        total_removed = 0
        
        # Sync each collection
        for collection in prod_collections:
            collection_id = collection.id
            print(f"\n📁 Checking '{collection_id}' collection...")
            
            # Get all production documents
            prod_docs = {doc.id: doc for doc in collection.stream()}
            
            # Get all emulator documents
            emulator_collection = emulator_db.collection(collection_id)
            emulator_docs = {doc.id: doc for doc in emulator_collection.stream()}
            
            added = 0
            updated = 0
            unchanged = 0
            removed = 0
            
            # Check each production document
            for doc_id, prod_doc in prod_docs.items():
                prod_data = prod_doc.to_dict()
                emulator_doc = emulator_docs.get(doc_id)
                emulator_data = emulator_doc.to_dict() if emulator_doc else None
                
                if documents_are_different(emulator_data, prod_data):
                    # Document is different - update it
                    emulator_doc_ref = emulator_collection.document(doc_id)
                    emulator_doc_ref.set(prod_data)
                    
                    if emulator_data is None:
                        added += 1
                    else:
                        updated += 1
                    
                    # Handle subcollections
                    subcollections = list(prod_doc.reference.collections())
                    for subcollection in subcollections:
                        subcoll_id = subcollection.id
                        
                        # Get production subcollection docs
                        prod_subdocs = {subdoc.id: subdoc for subdoc in subcollection.stream()}
                        
                        # Get emulator subcollection docs
                        emulator_subcoll = emulator_doc_ref.collection(subcoll_id)
                        emulator_subdocs = {subdoc.id: subdoc for subdoc in emulator_subcoll.stream()}
                        
                        # Sync subcollection
                        for subdoc_id, prod_subdoc in prod_subdocs.items():
                            prod_subdata = prod_subdoc.to_dict()
                            emulator_subdoc = emulator_subdocs.get(subdoc_id)
                            emulator_subdata = emulator_subdoc.to_dict() if emulator_subdoc else None
                            
                            if documents_are_different(emulator_subdata, prod_subdata):
                                emulator_subdoc_ref = emulator_subcoll.document(subdoc_id)
                                emulator_subdoc_ref.set(prod_subdata)
                        
                        # Remove subcollection docs that no longer exist in production
                        for subdoc_id in emulator_subdocs:
                            if subdoc_id not in prod_subdocs:
                                emulator_subcoll.document(subdoc_id).delete()
                else:
                    unchanged += 1
            
            # Remove documents that no longer exist in production
            # (but preserve sync metadata - it's only for local development)
            for doc_id in emulator_docs:
                if doc_id not in prod_docs:
                    # Don't remove sync metadata - it's local-only
                    if collection_id == 'internal_config' and doc_id == 'sync_metadata':
                        continue
                    emulator_collection.document(doc_id).delete()
                    removed += 1
            
            # Report results for this collection
            changes = []
            if added > 0:
                changes.append(f"{added} added")
            if updated > 0:
                changes.append(f"{updated} updated")
            if removed > 0:
                changes.append(f"{removed} removed")
            if unchanged > 0:
                changes.append(f"{unchanged} unchanged")
            
            if changes:
                print(f"  ✅ {', '.join(changes)}")
            else:
                print(f"  ✅ No changes needed")
            
            total_added += added
            total_updated += updated
            total_unchanged += unchanged
            total_removed += removed
        
        # Final summary
        print(f"\n📊 Smart Sync Complete:")
        if total_added > 0:
            print(f"  • {total_added} documents added")
        if total_updated > 0:
            print(f"  • {total_updated} documents updated")
        if total_removed > 0:
            print(f"  • {total_removed} documents removed")
        print(f"  • {total_unchanged} documents unchanged")
        
        total_changes = total_added + total_updated + total_removed
        if total_changes == 0:
            print("✅ Emulator already matches production!")
        else:
            print(f"✅ Applied {total_changes} changes, emulator now matches production!")
            
    except Exception as e:
        print(f"❌ Error during smart sync: {e}")
        import traceback
        traceback.print_exc()
        # Don't fail the main scraping job if emulator sync fails
        
    finally:
        
        # Log timing
        elapsed = time.time() - start_time
        print(f"⏱️ Sync operation took {elapsed:.2f} seconds")
        
        # Clean up apps and restore environment
        if emulator_app and emulator_app.name == 'emulator_app':
            try:
                firebase_admin.delete_app(emulator_app)
            except:
                pass
        
        if prod_app and prod_app.name == 'production_sync_app':
            try:
                firebase_admin.delete_app(prod_app)
            except:
                pass
        
        # Restore emulator environment for main app
        if original_emulator_host:
            os.environ['FIRESTORE_EMULATOR_HOST'] = original_emulator_host
