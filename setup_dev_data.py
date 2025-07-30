#!/usr/bin/env python3
"""
Setup development data for Firebase emulator.
Exports production data and imports it to local emulator for free development.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path

# Data directory for emulator persistence
EMULATOR_DATA_DIR = Path(__file__).parent / "emulator_data"

def check_firebase_cli():
    """Check if Firebase CLI is installed."""
    try:
        subprocess.run(['firebase', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Firebase CLI not found!")
        print("   Install with: npm install -g firebase-tools")
        return False

def setup_emulator_persistence():
    """Configure emulator to use persistent data directory."""
    EMULATOR_DATA_DIR.mkdir(exist_ok=True)
    
    # Create .firebaserc if it doesn't exist
    firebaserc_path = Path(__file__).parent / ".firebaserc"
    if not firebaserc_path.exists():
        firebaserc_content = {
            "projects": {
                "default": "pvpocket-dd286"
            }
        }
        with open(firebaserc_path, 'w') as f:
            json.dump(firebaserc_content, f, indent=2)
    
    print(f"✅ Emulator data directory: {EMULATOR_DATA_DIR}")
    return str(EMULATOR_DATA_DIR)

def export_production_data():
    """Export data from production Firestore."""
    print("📤 Exporting production data...")
    
    export_path = EMULATOR_DATA_DIR / "production_export"
    export_path.mkdir(exist_ok=True)
    
    try:
        # Export only the cards collection (most important for development)
        cmd = [
            'gcloud', 'firestore', 'export',
            f'gs://pvpocket-dd286.firebasestorage.app/emulator_exports/{int(time.time())}',
            '--collection-ids=cards,users',  # Export cards and a few sample users
            '--project=pvpocket-dd286'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        export_uri = result.stdout.strip().split('\n')[-1]
        
        print(f"✅ Exported to: {export_uri}")
        return export_uri
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Export failed: {e}")
        print("Make sure you're authenticated: gcloud auth login")
        return None

def import_to_emulator():
    """Import production data to local emulator."""
    print("📥 Starting emulator and importing data...")
    
    # Start emulator with data directory
    emulator_cmd = [
        'firebase', 'emulators:start',
        '--only', 'firestore',
        '--import', str(EMULATOR_DATA_DIR),
        '--export-on-exit', str(EMULATOR_DATA_DIR)
    ]
    
    print("🔥 Starting Firebase emulator with persistent data...")
    print("   This will keep running in the background")
    print("   Use Ctrl+C to stop and save data")
    
    try:
        subprocess.run(emulator_cmd, check=True)
    except KeyboardInterrupt:
        print("\n✅ Emulator stopped and data saved")
    except subprocess.CalledProcessError as e:
        print(f"❌ Emulator failed: {e}")

def create_sample_data():
    """Create sample data directly in emulator (simpler approach)."""
    print("📝 Creating sample development data...")
    
    # This is a simpler approach - create a Python script that populates
    # the emulator with just enough data for development
    sample_data_script = '''
import os
import firebase_admin
from firebase_admin import credentials, firestore
from Card import Card

# Connect to emulator
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
firebase_admin.initialize_app(project_id="demo-project")
db = firestore.client()

# Create sample cards
sample_cards = [
    {"id": 1, "name": "Pikachu", "energy_type": "Lightning", "set_name": "Base Set", "hp": 60},
    {"id": 2, "name": "Charizard", "energy_type": "Fire", "set_name": "Base Set", "hp": 120},
    {"id": 3, "name": "Blastoise", "energy_type": "Water", "set_name": "Base Set", "hp": 100},
    # Add more cards as needed for testing
]

# Add cards to emulator
for card_data in sample_cards:
    doc_ref = db.collection("cards").document("base_set").collection("set_cards").document(str(card_data["id"]))
    doc_ref.set(card_data)
    print(f"Added {card_data['name']}")

print("✅ Sample data created in emulator")
'''
    
    sample_script_path = EMULATOR_DATA_DIR / "create_sample_data.py"
    with open(sample_script_path, 'w') as f:
        f.write(sample_data_script)
    
    print(f"✅ Sample data script created: {sample_script_path}")
    print("   Run it after starting emulator to populate data")

def main():
    """Main setup function."""
    print("🛠️  Setting up Pokemon TCG Pocket development environment")
    print("=" * 60)
    
    if not check_firebase_cli():
        return 1
    
    # Setup persistent data directory
    data_dir = setup_emulator_persistence()
    
    print("\n🎯 Choose setup method:")
    print("1. Simple: Create sample data for development")
    print("2. Full: Export production data (requires gcloud auth)")
    print("3. Skip: Just configure emulator")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        create_sample_data()
        print("\n📋 Next steps:")
        print("1. Start emulator: firebase emulators:start --only firestore")
        print("2. Run sample data script in another terminal")
        print("3. Use: python3 run.py (will automatically use emulator)")
        
    elif choice == "2":
        export_uri = export_production_data()
        if export_uri:
            print("\n📋 Next steps:")
            print("1. Download and import the exported data")
            print("2. Start emulator with imported data")
        
    else:
        print("✅ Emulator configured for persistence")
    
    print(f"\n💾 Emulator data will be saved to: {data_dir}")
    print("🚀 Run 'python3 run.py' to start development with emulator!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())