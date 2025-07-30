#!/usr/bin/env python3
"""Simple run script that starts the app without complex sync logic."""

import os
import subprocess
import time
import atexit
from dotenv import load_dotenv

# Load environment variables
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

# Check if emulator is already running
import socket
try:
    with socket.create_connection(('localhost', 8080), timeout=1):
        os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
        print("🔥 Using Firebase Emulator (FREE) - already running")
except (socket.error, ConnectionRefusedError):
    # Try to start emulator
    try:
        subprocess.run(['firebase', '--version'], capture_output=True, check=True)
        
        print("🚀 Starting Firebase emulator...")
        
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
                    atexit.register(cleanup_emulator)
                    break
            except (socket.error, ConnectionRefusedError):
                time.sleep(1)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("💰 Using Production Firestore (COSTS MONEY)")
        print("   Install Firebase CLI for free development:")
        print("   npm install -g firebase-tools")

# Now start the Flask app
from app import create_app

config_name = os.getenv("FLASK_CONFIG", os.getenv("FLASK_ENV", "default"))

print("\n🎮 Pokemon TCG Pocket - Development Mode")
print("=" * 50)

if os.environ.get('FIRESTORE_EMULATOR_HOST'):
    print("📊 Data Source: Firebase Emulator (FREE)")
    print("💡 To sync your user data, run:")
    print(f"   python3 sync_my_user.py YOUR_USER_ID")
else:
    print("📊 Data Source: Production Firestore (COSTS MONEY)")

print("=" * 50 + "\n")

app = create_app(config_name)

if __name__ == "__main__":
    app.run(
        debug=app.config.get("DEBUG", True),
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5001)),
    )