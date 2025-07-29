#!/usr/bin/env python3
"""
Development script for Pokemon TCG Pocket App.
Automatically starts Firebase emulator and uses minimal data to save costs.
"""

import os
import sys
import subprocess
import time
import signal
import threading
from threading import Thread

def start_emulator():
    """Start Firebase emulator in the background."""
    try:
        print("🔥 Starting Firebase emulator...")
        # Start emulator process
        emulator_process = subprocess.Popen(
            ['firebase', 'emulators:start', '--only', 'firestore'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for emulator to be ready
        while True:
            line = emulator_process.stdout.readline()
            if "All emulators ready" in line or "Emulator UI running at" in line:
                print("✅ Firebase emulator ready!")
                break
            if emulator_process.poll() is not None:
                print("❌ Failed to start Firebase emulator")
                return None
        
        return emulator_process
    except FileNotFoundError:
        print("❌ Firebase CLI not found. Install with: npm install -g firebase-tools")
        return None
    except Exception as e:
        print(f"❌ Error starting emulator: {e}")
        return None

def cleanup_emulator(emulator_process):
    """Clean up emulator process."""
    if emulator_process:
        print("\n🛑 Stopping Firebase emulator...")
        emulator_process.terminate()
        emulator_process.wait()

if __name__ == '__main__':
    # Set development environment
    os.environ['FLASK_CONFIG'] = 'development'
    
    print("🎮 Pokemon TCG Pocket - Development Mode")
    print("💰 Starting with automatic cost optimization...")
    print("-" * 50)
    
    # Start Firebase emulator
    emulator_process = start_emulator()
    
    # Set up cleanup on exit
    def signal_handler(sig, frame):
        cleanup_emulator(emulator_process)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Give emulator a moment to fully start
        time.sleep(2)
        
        # Import and run the app
        from run import app
        
        print("🌐 App running at: http://localhost:5001")
        print("💾 Using Firebase emulator (FREE Firestore)")
        print("📊 Minimal data loaded (fast startup)")
        print("\nPress Ctrl+C to stop everything")
        print("-" * 50)
        
        app.run(host='0.0.0.0', port=5001, debug=True)
        
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_emulator(emulator_process)