import os
import socket
import subprocess
import time
import atexit

# Set emulator environment BEFORE any other imports
try:
    with socket.create_connection(('localhost', 8080), timeout=1):
        os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
        print("🔗 Early emulator detection: Connected")
except (socket.error, ConnectionRefusedError):
    pass

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
    """Sync all production data to emulator."""
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
        
        if card_count == 0:
            print("📥 Emulator is empty - syncing all production data...")
            print("   This may take a few minutes for the first sync...")
        else:
            print("🔄 Smart sync: Checking for changes...")
        
        # Always run smart sync (it only updates what's different)
        from shared_utils import sync_to_local_emulator
        sync_to_local_emulator()
        
        if card_count == 0:
            print("✅ Initial sync complete! All production data now available locally.")
        else:
            print("✅ Smart sync complete!")
            
    except Exception as e:
        print(f"⚠️  Sync check failed: {e}")
        print("   Continuing with existing emulator data...")

# Auto-start emulator for local development
emulator_started = start_emulator_if_needed()

# Sync production data to emulator if needed
if emulator_started and os.environ.get('FIRESTORE_EMULATOR_HOST'):
    if os.environ.get('SKIP_EMULATOR_SYNC') != '1':
        sync_emulator_data()

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
        print("✅ All production data synced locally")
        print("🔄 Run 'rm -rf emulator_data' then restart to force fresh sync")
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