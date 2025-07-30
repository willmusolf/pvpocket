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

# Auto-start emulator for local development
emulator_started = start_emulator_if_needed()

# Sync production data to emulator if emulator is running
if emulator_started and os.environ.get('FIRESTORE_EMULATOR_HOST'):
    try:
        from shared_utils import sync_to_local_emulator, is_emulator_running
        # Check if emulator already has data
        import firebase_admin
        from firebase_admin import firestore
        
        # Initialize Firebase for production connection
        from shared_utils import initialize_firebase
        initialize_firebase()
        
        # Check if emulator has cards
        main_project_id = os.environ.get('GCP_PROJECT_ID', 'pvpocket-dd286')
        emulator_app = firebase_admin.initialize_app(
            name='emulator_data_check',
            options={'projectId': main_project_id}
        )
        
        old_host = os.environ.get('FIRESTORE_EMULATOR_HOST')
        os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
        
        try:
            emulator_db = firestore.client(app=emulator_app)
            cards_ref = emulator_db.collection('cards')
            
            # Count total cards in emulator
            total_cards = 0
            for set_doc in cards_ref.stream():
                cards_subcollection = set_doc.reference.collection('set_cards')
                set_cards = list(cards_subcollection.stream())
                total_cards += len(set_cards)
            
            if total_cards < 100:  # If less than 100 cards, sync from production
                print(f"📥 Emulator has only {total_cards} cards - syncing full production data...")
                print("   This may take a moment for 1300+ cards...")
                
                # Ensure environment variables are set for sync
                os.environ['FLASK_CONFIG'] = 'development'
                os.environ['FLASK_DEBUG'] = '1'
                
                sync_to_local_emulator()
                
                # Wait for sync to settle and verify
                import time
                print("⏳ Waiting for emulator data to settle...")
                time.sleep(3)
                
                # Verify the sync worked
                final_count = 0
                for set_doc in cards_ref.stream():
                    cards_subcollection = set_doc.reference.collection('set_cards')
                    set_cards = list(cards_subcollection.stream())
                    final_count += len(set_cards)
                
                print(f"✅ Sync complete! {final_count} cards now available locally!")
            else:
                print(f"📊 Emulator already has {total_cards} cards - skipping sync")
                
        finally:
            # Restore emulator host
            if old_host:
                os.environ['FIRESTORE_EMULATOR_HOST'] = old_host
            elif 'FIRESTORE_EMULATOR_HOST' in os.environ:
                del os.environ['FIRESTORE_EMULATOR_HOST']
            
            # Clean up temporary app
            if 'emulator_data_check' in firebase_admin._apps:
                firebase_admin.delete_app(firebase_admin.get_app('emulator_data_check'))
        
    except Exception as e:
        print(f"⚠️  Could not sync production data: {e}")
        print("   Falling back to sample data...")
        try:
            from shared_utils import create_initial_emulator_data
            create_initial_emulator_data()
        except Exception as e2:
            print(f"⚠️  Could not create sample data either: {e2}")

from app import create_app

config_name = os.getenv("FLASK_CONFIG", os.getenv("FLASK_ENV", "default"))

# Only show startup config in development and in main process
if config_name == "development" and os.environ.get('WERKZEUG_RUN_MAIN'):
    using_emulator = bool(os.environ.get('FIRESTORE_EMULATOR_HOST'))
    
    print("🎮 Pokemon TCG Pocket - Development Mode")
    print("=" * 50)
    
    if using_emulator:
        print("📊 Card Loading: FULL (~1300 cards)")
        print("💾 Data Source: Firebase Emulator (FREE)")
        print("✅ Perfect for testing decks/exports")
        print("🔄 Auto-syncs when new cards drop")
    else:
        print("📊 Card Loading: MINIMAL (3 sample cards)")
        print("💾 Data Source: Production Firestore (COSTS MONEY)")
        print("⚠️  Install Firebase CLI for free full cards:")
        print("   npm install -g firebase-tools")
    
    print("=" * 50)

app = create_app(config_name)

if __name__ == "__main__":
    # Ensure emulator environment is set for Flask reloader
    if os.environ.get('FIRESTORE_EMULATOR_HOST'):
        import subprocess
        import sys
        
        # Pass environment to subprocess
        env = os.environ.copy()
        env['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
        
    app.run(
        debug=app.config.get("DEBUG", True),
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5001)),
    )
