#!/usr/bin/env python3
"""
Setup Firebase emulator for Pokemon TCG Pocket development.
Creates persistent emulator data and configures the development environment.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path

# Configuration
EMULATOR_DATA_DIR = Path(__file__).parent / "emulator_data"
FIREBASE_JSON_PATH = Path(__file__).parent / "firebase.json"

def check_firebase_cli():
    """Check if Firebase CLI is installed."""
    try:
        result = subprocess.run(['firebase', '--version'], capture_output=True, text=True, check=True)
        print(f"✅ Firebase CLI found: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Firebase CLI not found!")
        print("   Install with: npm install -g firebase-tools")
        return False

def check_node_js():
    """Check if Node.js is installed (required for Firebase CLI)."""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True, check=True)
        print(f"✅ Node.js found: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Node.js not found!")
        print("   Download from: https://nodejs.org/")
        return False

def setup_emulator_directory():
    """Create emulator data directory for persistence."""
    EMULATOR_DATA_DIR.mkdir(exist_ok=True)
    print(f"✅ Emulator data directory: {EMULATOR_DATA_DIR}")
    
    # Create .gitignore for emulator data
    gitignore_path = EMULATOR_DATA_DIR / ".gitignore"
    if not gitignore_path.exists():
        with open(gitignore_path, 'w') as f:
            f.write("# Firebase emulator data - exclude from git\n*\n!.gitignore\n")
        print("✅ Created .gitignore for emulator data")

def configure_firebase_json():
    """Update firebase.json for emulator persistence."""
    if not FIREBASE_JSON_PATH.exists():
        print("❌ firebase.json not found!")
        return False
    
    with open(FIREBASE_JSON_PATH, 'r') as f:
        config = json.load(f)
    
    # Ensure emulator configuration exists
    if 'emulators' not in config:
        config['emulators'] = {}
    
    # Configure emulator for persistence
    config['emulators'].update({
        "firestore": {
            "port": 8080
        },
        "ui": {
            "enabled": True,
            "port": 4000
        },
        "singleProjectMode": True
    })
    
    # Write updated configuration
    with open(FIREBASE_JSON_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ Updated firebase.json for emulator persistence")
    return True

def create_sample_data_script():
    """Create a script to populate emulator with sample data."""
    script_content = '''#!/usr/bin/env python3
"""
Populate Firebase emulator with sample data for development.
Run this after starting the emulator to create test data.
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore

def create_sample_data():
    """Create sample data in the emulator."""
    # Connect to emulator
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
    
    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={'projectId': 'demo-project'})
    
    db = firestore.client()
    
    print("Creating sample cards in emulator...")
    
    # Create sample card set
    set_ref = db.collection("cards").document("sample_set")
    set_ref.set({
        "name": "Sample Set",
        "description": "Development testing cards"
    })
    
    # Create sample cards
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
    
    # Add cards to emulator
    cards_collection = set_ref.collection("set_cards")
    for card in sample_cards:
        card_ref = cards_collection.document(str(card["id"]))
        card_ref.set(card)
        print(f"  ✅ Added {card['name']}")
    
    # Create sample configuration
    config_ref = db.collection("internal_config").document("sets_tracker")
    config_ref.set({
        "known_codes": ["SAM"],
        "last_updated": firestore.SERVER_TIMESTAMP
    })
    print("  ✅ Added configuration")
    
    print("\\n✅ Sample data created successfully!")
    print("   You can now use python3 run.py for development")

if __name__ == "__main__":
    create_sample_data()
'''
    
    script_path = Path(__file__).parent / "create_sample_data.py"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Make executable
    os.chmod(script_path, 0o755)
    print(f"✅ Created sample data script: {script_path}")
    return script_path

def main():
    """Main setup function."""
    print("🛠️  Firebase Emulator Setup for Pokemon TCG Pocket")
    print("=" * 60)
    
    # Check prerequisites
    if not check_node_js():
        return 1
        
    if not check_firebase_cli():
        return 1
    
    # Setup emulator environment
    setup_emulator_directory()
    
    if not configure_firebase_json():
        return 1
    
    sample_script = create_sample_data_script()
    
    print("\\n📋 Setup Complete! Next Steps:")
    print("=" * 60)
    print("1. Start the emulator:")
    print(f"   firebase emulators:start --only firestore --import {EMULATOR_DATA_DIR} --export-on-exit {EMULATOR_DATA_DIR}")
    print()
    print("2. In another terminal, create sample data:")
    print(f"   python3 {sample_script.name}")
    print()
    print("3. Start development:")
    print("   python3 run.py")
    print()
    print("💡 Tips:")
    print("   - Emulator UI: http://localhost:4000")
    print("   - Data persists between restarts")
    print("   - Use Ctrl+C to stop emulator and save data")
    print("   - run.py auto-detects and connects to emulator")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())