import os
import sys
import socket
import subprocess
import time
import atexit

# Set emulator environment BEFORE any other imports - ONLY in local development
# Don't run emulator detection in cloud environments like Google App Engine
is_cloud_environment = (
    os.environ.get('GAE_ENV') or  # Google App Engine
    os.environ.get('GAE_APPLICATION') or  # Google App Engine
    os.environ.get('GOOGLE_CLOUD_PROJECT') or  # Generic Google Cloud
    'gunicorn' in ' '.join(sys.argv)  # Running via gunicorn (production)
)

if not is_cloud_environment:
    try:
        with socket.create_connection(('localhost', 8080), timeout=1):
            os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
            print("🔗 Early emulator detection: Connected")
    except (socket.error, ConnectionRefusedError):
        pass
else:
    print("🚨 CLOUD ENVIRONMENT: Skipping emulator detection for production safety")

from dotenv import load_dotenv
load_dotenv()

# Global variable to track emulator process
emulator_process = None

def cleanup_emulator():
    """Clean up emulator process on exit."""
    global emulator_process
    if emulator_process:
        print("\n🛑 Stopping Firebase emulator...")
        emulator_process.terminate()
        try:
            emulator_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            emulator_process.kill()

def start_emulator_if_needed():
    """Start emulator if not running and Firebase CLI is available."""
    global emulator_process
    
    # Check if emulator is already running
    try:
        with socket.create_connection(('localhost', 8080), timeout=1):
            os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
            print("🔥 Using Firebase Emulator (FREE) - already running")
            return True
    except (socket.error, ConnectionRefusedError):
        pass
    
    # Check if Firebase CLI is available
    try:
        subprocess.run(['firebase', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("💰 Using Production Firestore (COSTS MONEY)")
        print("   Install Firebase CLI for free development:")
        print("   npm install -g firebase-tools")
        return False
    
    print("🚀 Starting Firebase emulator...")
    
    try:
        # Create emulator data directory if it doesn't exist
        emulator_data_dir = os.path.join(os.path.dirname(__file__), 'emulator_data')
        os.makedirs(emulator_data_dir, exist_ok=True)
        
        # Start emulator with data persistence
        emulator_process = subprocess.Popen([
            'firebase', 'emulators:start', 
            '--only', 'firestore',
            '--import', emulator_data_dir,
            '--export-on-exit', emulator_data_dir
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Wait for emulator to be ready
        print("⏳ Waiting for emulator to start...")
        for _ in range(30):  # 30 second timeout
            try:
                with socket.create_connection(('localhost', 8080), timeout=1):
                    print("✅ Firebase emulator ready!")
                    os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
                    
                    # Register cleanup function
                    atexit.register(cleanup_emulator)
                    return True
            except (socket.error, ConnectionRefusedError):
                time.sleep(1)
        
        # If we get here, emulator failed to start
        print("❌ Emulator failed to start - using production Firestore")
        if emulator_process:
            emulator_process.terminate()
            emulator_process = None
        return False
        
    except Exception as e:
        print(f"❌ Error starting emulator: {e}")
        print("   Using production Firestore instead")
        return False

def sync_emulator_data():
    """Smart sync: Only sync production data when actually needed."""
    import sys
    from datetime import datetime, timedelta
    
    # Check for force sync flag
    force_sync = '--force-sync' in sys.argv
    if force_sync:
        print("\n🔄 Force sync requested - syncing all production data...")
    else:
        print("\n🔄 Checking emulator data...")
    
    try:
        import firebase_admin
        from firebase_admin import firestore
        
        # Create a simple app for emulator check
        if not firebase_admin._apps:
            main_project_id = os.environ.get('GCP_PROJECT_ID', 'pvpocket-dd286')
            bucket_name = os.environ.get('FIREBASE_STORAGE_BUCKET', f'{main_project_id}.appspot.com')
            emulator_app = firebase_admin.initialize_app(
                options={
                    'projectId': main_project_id,
                    'storageBucket': bucket_name
                }
            )
        else:
            emulator_app = firebase_admin.get_app()
        
        # Connect to emulator
        os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
        emulator_db = firestore.client()
        
        # Quick check if we have data
        cards_ref = emulator_db.collection('cards')
        card_count = len(list(cards_ref.limit(1).stream()))
        
        # Check last sync timestamp
        internal_config_ref = emulator_db.collection('internal_config').document('sync_metadata')
        sync_metadata = internal_config_ref.get()
        
        last_sync_time = None
        if sync_metadata.exists:
            sync_data = sync_metadata.to_dict()
            last_sync_time = sync_data.get('last_sync_timestamp')
        
        # Determine if sync is needed
        needs_sync = False
        sync_reason = ""
        
        if force_sync:
            needs_sync = True
            sync_reason = "Force sync requested - bypassing all cache checks"
        elif card_count == 0:
            needs_sync = True
            sync_reason = "Emulator is empty"
        elif last_sync_time is None:
            needs_sync = True
            sync_reason = "No sync timestamp found"
        else:
            # Check if data is stale (older than 24 hours)
            try:
                if isinstance(last_sync_time, str):
                    last_sync = datetime.fromisoformat(last_sync_time.replace('Z', '+00:00'))
                else:
                    last_sync = last_sync_time
                
                if datetime.now().astimezone() - last_sync.astimezone() > timedelta(hours=24):
                    needs_sync = True
                    sync_reason = f"Data is stale (last sync: {last_sync.strftime('%Y-%m-%d %H:%M')})"
                else:
                    print(f"✅ Emulator data is fresh (last sync: {last_sync.strftime('%Y-%m-%d %H:%M')})")
                    print("   Skipping sync to save Firebase costs")
                    return
            except Exception as e:
                needs_sync = True
                sync_reason = f"Invalid sync timestamp: {e}"
        
        if needs_sync:
            print(f"📥 {sync_reason} - syncing production data...")
            if card_count == 0:
                print("   This may take a few minutes for the first sync...")
            
            # Run the actual sync
            from shared_utils import sync_to_local_emulator
            sync_to_local_emulator()
            
            # Clear app cache so fresh data is loaded
            try:
                from app.cache_manager import cache_manager
                cache_manager.invalidate_card_cache()
                print("🗑️ Cleared app cache - fresh data will be loaded on next request")
            except Exception as cache_error:
                print(f"⚠️ Could not clear app cache: {cache_error}")
                print("   You may need to refresh your browser to see updated cards")
            
            # Update sync timestamp
            sync_metadata_doc = {
                'last_sync_timestamp': datetime.now().isoformat(),
                'sync_reason': sync_reason,
                'card_count': len(list(cards_ref.limit(10).stream()))  # Quick recount
            }
            internal_config_ref.set(sync_metadata_doc)
            
            if card_count == 0:
                print("✅ Initial sync complete! All production data now available locally.")
            else:
                print("✅ Smart sync complete! Fresh data ready.")
            
    except Exception as e:
        print(f"⚠️  Sync check failed: {e}")
        print("   Continuing with existing emulator data...")

# Auto-start emulator for local development ONLY
# Don't run emulator startup in cloud environments
if not is_cloud_environment:
    emulator_started = start_emulator_if_needed()
    
    # Sync production data to emulator if needed
    # Skip sync on Flask auto-restart (when WERKZEUG_RUN_MAIN is set)
    if emulator_started and os.environ.get('FIRESTORE_EMULATOR_HOST'):
        if os.environ.get('SKIP_EMULATOR_SYNC') != '1':
            # Only sync on initial run, not on Flask restart
            if not os.environ.get('WERKZEUG_RUN_MAIN'):
                sync_emulator_data()
            else:
                print("🔄 Skipping sync on Flask auto-restart (already synced)")
else:
    emulator_started = False
    print("🚨 CLOUD: Skipping emulator startup (production environment)")

# Now import and create the Flask app
from app import create_app

config_name = os.getenv("FLASK_CONFIG", os.getenv("FLASK_ENV", "default"))

# Only show startup config in development and in main process
if config_name == "development" and os.environ.get('WERKZEUG_RUN_MAIN'):
    using_emulator = bool(os.environ.get('FIRESTORE_EMULATOR_HOST'))
    
    print("\n🎮 Pokemon TCG Pocket - Development Mode")
    print("=" * 50)
    
    if using_emulator:
        print("📊 Data Source: Firebase Emulator (FREE)")
        print("✅ Smart sync: Only syncs when data is stale (>24h old)")
        print("🔄 Force fresh sync: python3 run.py --force-sync")
        print("💡 Force sync automatically clears app cache for instant refresh")
        print("⚡ Sync runs only once (skipped on Flask auto-restart)")
    else:
        print("📊 Data Source: Production Firestore (COSTS MONEY)")
        print("⚠️  Install Firebase CLI for free emulator:")
        print("   npm install -g firebase-tools")
    
    print("=" * 50 + "\n")

app = create_app(config_name)

if __name__ == "__main__":
    app.run(
        debug=app.config.get("DEBUG", True),
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5001)),
    )