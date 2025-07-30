#!/usr/bin/env python3
"""
Create comprehensive test data for GitHub Actions tests.
This provides a consistent set of test data for CI/CD pipelines.
Uses REST API for Firestore emulator to ensure maximum compatibility.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def convert_to_firestore_value(value):
    """Convert Python value to Firestore REST API format."""
    if value is None:
        return {"nullValue": None}
    elif isinstance(value, bool):
        return {"booleanValue": value}
    elif isinstance(value, int):
        return {"integerValue": str(value)}
    elif isinstance(value, float):
        return {"doubleValue": value}
    elif isinstance(value, str):
        return {"stringValue": value}
    elif isinstance(value, datetime):
        return {"timestampValue": value.isoformat() + "Z"}
    elif isinstance(value, list):
        return {
            "arrayValue": {
                "values": [convert_to_firestore_value(item) for item in value]
            }
        }
    elif isinstance(value, dict):
        return {
            "mapValue": {
                "fields": {k: convert_to_firestore_value(v) for k, v in value.items()}
            }
        }
    else:
        # Fallback to string
        return {"stringValue": str(value)}

def create_firestore_document(collection_name, document_id, data):
    """Create a document in Firestore emulator using REST API."""
    emulator_host = os.environ.get('FIRESTORE_EMULATOR_HOST', '127.0.0.1:8080')
    project_id = 'demo-test-project'
    
    # Convert data to Firestore format
    firestore_data = {
        "fields": {k: convert_to_firestore_value(v) for k, v in data.items()}
    }
    
    url = f"http://{emulator_host}/v1/projects/{project_id}/databases/(default)/documents/{collection_name}?documentId={document_id}"
    
    try:
        response = requests.post(
            url,
            json=firestore_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            return True
        else:
            print(f"❌ Failed to create {collection_name}/{document_id}: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating {collection_name}/{document_id}: {e}")
        return False

def verify_document_creation(collection_name, document_id):
    """Verify that a document was created by reading it back via REST API."""
    emulator_host = os.environ.get('FIRESTORE_EMULATOR_HOST', '127.0.0.1:8080')
    project_id = 'demo-test-project'
    
    url = f"http://{emulator_host}/v1/projects/{project_id}/databases/(default)/documents/{collection_name}/{document_id}"
    
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"⚠️ Error verifying {collection_name}/{document_id}: {e}")
        return False

def list_collection_documents(collection_name, limit=5):
    """List documents in a collection for debugging using REST API."""
    emulator_host = os.environ.get('FIRESTORE_EMULATOR_HOST', '127.0.0.1:8080')
    project_id = 'demo-test-project'
    
    url = f"http://{emulator_host}/v1/projects/{project_id}/databases/(default)/documents/{collection_name}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            docs = data.get('documents', [])
            print(f"📋 Found {len(docs)} documents in {collection_name} collection")
            for i, doc in enumerate(docs[:limit]):
                doc_id = doc['name'].split('/')[-1]
                print(f"  - Document ID: {doc_id}")
            if len(docs) > limit:
                print(f"  ... and {len(docs) - limit} more")
            return len(docs)
        else:
            print(f"❌ Error listing {collection_name}: HTTP {response.status_code}")
            return 0
    except Exception as e:
        print(f"❌ Error listing {collection_name}: {e}")
        return 0

def create_test_data():
    """Create comprehensive test data for GitHub Actions tests."""
    
    print(f"🔍 FIRESTORE_EMULATOR_HOST = {os.environ.get('FIRESTORE_EMULATOR_HOST')}")
    print(f"🔍 Using demo project: demo-test-project")
    print("🌐 Using REST API for maximum emulator compatibility")
    
    # Check if emulator is running
    emulator_host = os.environ.get('FIRESTORE_EMULATOR_HOST', '127.0.0.1:8080')
    try:
        response = requests.get(f"http://{emulator_host}", timeout=5)
        print("✅ Firestore emulator is reachable")
    except Exception as e:
        print(f"❌ Failed to connect to Firestore emulator: {e}")
        return
    
    print("🧪 Creating test data for GitHub Actions...")
    
    # 1. Create test users
    print("👥 Creating test users...")
    test_users = [
        {
            "id": "test-user-1",
            "username": "testuser1",
            "email": "test1@example.com",
            "profile_icon": "default.png",
            "created_at": datetime.utcnow(),
            "collection": {
                "1": 2,  # Pikachu x2
                "2": 1,  # Charizard x1
                "5": 2,  # Blastoise x2
            }
        },
        {
            "id": "test-user-2", 
            "username": "testuser2",
            "email": "test2@example.com",
            "profile_icon": "eevee.png",
            "created_at": datetime.utcnow() - timedelta(days=7),
            "collection": {
                "2": 2,  # Charizard x2
                "10": 1, # Mewtwo x1
                "15": 2, # Articuno x2
            }
        },
        {
            "id": "test-user-3",
            "username": "testuser3", 
            "email": "test3@example.com",
            "profile_icon": "pikachu.png",
            "created_at": datetime.utcnow() - timedelta(days=30),
            "collection": {}  # New player
        }
    ]
    
    users_created = 0
    for user_data in test_users:
        user_id = user_data.pop("id")
        if create_firestore_document("users", user_id, user_data):
            users_created += 1
    
    print(f"  ✅ Created {users_created}/{len(test_users)} test users")
    
    # 2. Create test cards directly in cards collection
    print("🃏 Creating test cards...")
    
    # Create test cards (representative sample) - store directly in cards/{id}
    test_cards = [
        # Pokémon cards
        {"id": 1, "name": "Pikachu", "energy_type": "Lightning", "card_type": "Pokemon", 
         "hp": 60, "rarity": "Common", "pack": "Pikachu Pack", 
         "set_name": "Test Set", "set_code": "TST", "card_number": 1,
         "attacks": [{"name": "Thunder Shock", "damage": 20, "cost": ["Lightning"]}],
         "firebase_image_url": "https://example.com/pikachu.png"},
         
        {"id": 2, "name": "Charizard", "energy_type": "Fire", "card_type": "Pokemon",
         "hp": 120, "rarity": "Rare", "pack": "Charizard Pack",
         "set_name": "Test Set", "set_code": "TST", "card_number": 2,
         "attacks": [{"name": "Fire Blast", "damage": 80, "cost": ["Fire", "Fire", "Fire"]}],
         "firebase_image_url": "https://example.com/charizard.png"},
         
        {"id": 5, "name": "Blastoise", "energy_type": "Water", "card_type": "Pokemon",
         "hp": 100, "rarity": "Rare", "pack": "Blastoise Pack", 
         "set_name": "Test Set", "set_code": "TST", "card_number": 5,
         "attacks": [{"name": "Hydro Pump", "damage": 60, "cost": ["Water", "Water"]}],
         "firebase_image_url": "https://example.com/blastoise.png"},
         
        {"id": 10, "name": "Mewtwo", "energy_type": "Psychic", "card_type": "Pokemon",
         "hp": 130, "rarity": "Ultra Rare", "pack": "Mewtwo Pack",
         "set_name": "Test Set", "set_code": "TST", "card_number": 10,
         "attacks": [{"name": "Psychic", "damage": 90, "cost": ["Psychic", "Psychic", "Colorless"]}],
         "firebase_image_url": "https://example.com/mewtwo.png"},
         
        {"id": 15, "name": "Articuno", "energy_type": "Water", "card_type": "Pokemon",
         "hp": 110, "rarity": "Rare", "pack": "Articuno Pack",
         "set_name": "Test Set", "set_code": "TST", "card_number": 15,
         "attacks": [{"name": "Ice Beam", "damage": 70, "cost": ["Water", "Water", "Colorless"]}],
         "firebase_image_url": "https://example.com/articuno.png"},
         
        # Trainer cards
        {"id": 20, "name": "Professor Oak", "card_type": "Trainer",
         "rarity": "Common", "pack": "Trainer Pack",
         "set_name": "Test Set", "set_code": "TST", "card_number": 20,
         "trainer_type": "Supporter", "effect": "Draw 3 cards",
         "firebase_image_url": "https://example.com/professor_oak.png"},
         
        {"id": 21, "name": "Potion", "card_type": "Trainer", 
         "rarity": "Common", "pack": "Trainer Pack",
         "set_name": "Test Set", "set_code": "TST", "card_number": 21,
         "trainer_type": "Item", "effect": "Heal 30 damage",
         "firebase_image_url": "https://example.com/potion.png"},
         
        # More Pokémon for variety
        {"id": 25, "name": "Bulbasaur", "energy_type": "Grass", "card_type": "Pokemon",
         "hp": 60, "rarity": "Common", "pack": "Grass Pack",
         "set_name": "Test Set", "set_code": "TST", "card_number": 25,
         "attacks": [{"name": "Vine Whip", "damage": 20, "cost": ["Grass"]}],
         "firebase_image_url": "https://example.com/bulbasaur.png"},
         
        {"id": 30, "name": "Squirtle", "energy_type": "Water", "card_type": "Pokemon",
         "hp": 50, "rarity": "Common", "pack": "Water Pack",
         "set_name": "Test Set", "set_code": "TST", "card_number": 30,
         "attacks": [{"name": "Water Gun", "damage": 20, "cost": ["Water"]}],
         "firebase_image_url": "https://example.com/squirtle.png"},
         
        {"id": 35, "name": "Charmander", "energy_type": "Fire", "card_type": "Pokemon",
         "hp": 50, "rarity": "Common", "pack": "Fire Pack",
         "set_name": "Test Set", "set_code": "TST", "card_number": 35,
         "attacks": [{"name": "Ember", "damage": 20, "cost": ["Fire"]}],
         "firebase_image_url": "https://example.com/charmander.png"}
    ]
    
    # Add cards directly to cards collection using REST API
    cards_created = 0
    for card_data in test_cards:
        card_id = str(card_data["id"])
        if create_firestore_document("cards", card_id, card_data):
            cards_created += 1
    
    # Debug: Verify some cards were created and can be read back
    print("🔍 Verifying card creation...")
    verified_cards = 0
    for i in [1, 2, 5]:  # Check first few cards
        if verify_document_creation("cards", str(i)):
            verified_cards += 1
    print(f"  ✅ Verified {verified_cards}/3 sample cards can be read back")
    
    print(f"  ✅ Created {cards_created}/{len(test_cards)} test cards")
    
    # 3. Create test decks
    print("🎯 Creating test decks...")
    
    test_decks = [
        {
            "id": "test-deck-1",
            "name": "Pikachu Rush",
            "user_id": "test-user-1",
            "username": "testuser1",
            "card_ids": ["1"] * 2 + ["20"] * 2 + ["21"] * 2 + ["25"] * 2 + 
                       ["30"] * 2 + ["35"] * 2 + ["2"] * 1 + ["5"] * 1 + 
                       ["10"] * 1 + ["15"] * 1 + ["1"] * 2 + ["20"] * 2,  # 20 cards total
            "cover_card_id": "1",
            "is_public": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": "test-deck-2",
            "name": "Charizard Control", 
            "user_id": "test-user-2",
            "username": "testuser2",
            "card_ids": ["2"] * 2 + ["35"] * 2 + ["20"] * 2 + ["21"] * 2 +
                       ["1"] * 2 + ["5"] * 2 + ["10"] * 1 + ["15"] * 1 +
                       ["25"] * 2 + ["30"] * 2 + ["35"] * 2,  # 20 cards total
            "cover_card_id": "2",
            "is_public": True,
            "created_at": datetime.utcnow() - timedelta(days=3),
            "updated_at": datetime.utcnow() - timedelta(days=1)
        },
        {
            "id": "test-deck-3",
            "name": "Water Deck",
            "user_id": "test-user-1", 
            "username": "testuser1",
            "card_ids": ["5"] * 2 + ["30"] * 2 + ["15"] * 2 + ["20"] * 2 +
                       ["21"] * 2 + ["1"] * 2 + ["2"] * 1 + ["10"] * 1 +
                       ["25"] * 2 + ["35"] * 2 + ["30"] * 2,  # 20 cards total
            "cover_card_id": "5",
            "is_public": False,  # Private deck
            "created_at": datetime.utcnow() - timedelta(days=7),
            "updated_at": datetime.utcnow() - timedelta(days=7)
        }
    ]
    
    decks_created = 0
    for deck_data in test_decks:
        deck_id = deck_data.pop("id")
        if create_firestore_document("decks", deck_id, deck_data):
            decks_created += 1
    
    print(f"  ✅ Created {decks_created}/{len(test_decks)} test decks")
    
    # 4. Create internal config
    print("⚙️  Creating internal configuration...")
    
    config_data = {
        "sets_tracker": {
            "known_codes": ["TST"],
            "last_updated": datetime.utcnow()
        },
        "app_config": {
            "maintenance_mode": False,
            "announcement": "Test environment active"
        }
    }
    
    configs_created = 0
    for config_id, config_value in config_data.items():
        if create_firestore_document("internal_config", config_id, config_value):
            configs_created += 1
    
    print(f"  ✅ Created {configs_created}/{len(config_data)} config documents")
    
    # Summary
    print("\n✅ Test data creation complete!")
    print("📊 Summary:")
    print(f"  • {users_created}/{len(test_users)} users")
    print(f"  • {cards_created}/{len(test_cards)} cards") 
    print(f"  • {decks_created}/{len(test_decks)} decks")
    print(f"  • {configs_created}/{len(config_data)} config documents")
    
    total_created = users_created + cards_created + decks_created + configs_created
    total_expected = len(test_users) + len(test_cards) + len(test_decks) + len(config_data)
    
    if total_created == total_expected:
        print(f"🎉 All {total_created} documents created successfully!")
    else:
        print(f"⚠️  Created {total_created}/{total_expected} documents - some failures occurred")
    
    # Final debugging - list what's actually in the database
    print("\n🔍 Final database verification:")
    print("=" * 50)
    list_collection_documents("cards", 5)
    list_collection_documents("users", 3)
    list_collection_documents("decks", 3)
    print("=" * 50)
    
    # Give emulator a moment to process all documents
    import time
    print("⏱️ Waiting 2 seconds for emulator to process all documents...")
    time.sleep(2)
    
    # Final check
    final_card_count = list_collection_documents("cards", 1)
    if final_card_count >= 10:
        print("✅ Database contains expected number of cards - ready for CardCollection!")
    else:
        print(f"⚠️ Database only contains {final_card_count} cards - CardCollection might not find them")
    

if __name__ == "__main__":
    # Ensure we're using emulator
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        print("⚠️  WARNING: FIRESTORE_EMULATOR_HOST not set!")
        print("   This script should only run against the emulator.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    create_test_data()