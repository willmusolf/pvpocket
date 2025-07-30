#!/usr/bin/env python3
"""
Create comprehensive test data for GitHub Actions tests.
This provides a consistent set of test data for CI/CD pipelines.
"""

import os
import sys
import firebase_admin
from firebase_admin import firestore, credentials
import tempfile
import json
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_test_data():
    """Create comprehensive test data for GitHub Actions tests."""
    
    print(f"🔍 FIRESTORE_EMULATOR_HOST = {os.environ.get('FIRESTORE_EMULATOR_HOST')}")
    print(f"🔍 GOOGLE_APPLICATION_CREDENTIALS = {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")
    print(f"🔍 Using demo project: demo-test-project")
    
    # Initialize Firebase app for emulator
    if not firebase_admin._apps:
        # For Firebase emulator, we need to bypass authentication entirely
        print("🔧 Configuring Firebase Admin SDK for emulator...")
        
        # Set GCLOUD_PROJECT environment variable as an alternative
        os.environ['GCLOUD_PROJECT'] = 'demo-test-project'
        
        try:
            # When using emulator, try to initialize without credentials
            # The emulator host environment variable should be sufficient
            firebase_admin.initialize_app(options={
                'projectId': 'demo-test-project'
            })
            print("✅ Firebase initialized successfully for emulator")
            
        except Exception as e:
            print(f"⚠️ Standard initialization failed: {e}")
            print("🔄 Trying alternative approach for emulator...")
            
            try:
                # Alternative: Set a fake service account to satisfy the SDK
                fake_sa_path = '/tmp/fake_service_account.json'
                fake_service_account = {
                    "type": "service_account",
                    "project_id": "demo-test-project", 
                    "private_key_id": "fake",
                    "private_key": "-----BEGIN PRIVATE KEY-----\\nfake\\n-----END PRIVATE KEY-----\\n",
                    "client_email": "fake@demo-test-project.iam.gserviceaccount.com",
                    "client_id": "fake",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
                
                with open(fake_sa_path, 'w') as f:
                    json.dump(fake_service_account, f)
                
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = fake_sa_path
                
                # Re-initialize
                firebase_admin.initialize_app(options={
                    'projectId': 'demo-test-project'
                })
                print("✅ Firebase initialized with fake service account for emulator")
                
            except Exception as e2:
                print(f"❌ Alternative initialization also failed: {e2}")
                print("⚠️ Continuing anyway - emulator might still work via direct connection")
                # Initialize with minimal config as last resort  
                firebase_admin.initialize_app()
    
    # Connect to emulator
    db = firestore.client()
    
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
    
    for user_data in test_users:
        user_id = user_data.pop("id")
        db.collection("users").document(user_id).set(user_data)
    
    print(f"  ✅ Created {len(test_users)} test users")
    
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
    
    # Add cards directly to cards collection (not in subcollection)
    for card_data in test_cards:
        card_id = str(card_data["id"])
        db.collection("cards").document(card_id).set(card_data)
    
    print(f"  ✅ Created {len(test_cards)} test cards")
    
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
    
    for deck_data in test_decks:
        deck_id = deck_data.pop("id")
        db.collection("decks").document(deck_id).set(deck_data)
    
    print(f"  ✅ Created {len(test_decks)} test decks")
    
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
    
    for config_id, config_value in config_data.items():
        db.collection("internal_config").document(config_id).set(config_value)
    
    print(f"  ✅ Created {len(config_data)} config documents")
    
    # Summary
    print("\n✅ Test data creation complete!")
    print("📊 Summary:")
    print(f"  • {len(test_users)} users")
    print(f"  • {len(test_cards)} cards") 
    print(f"  • {len(test_decks)} decks")
    print(f"  • {len(config_data)} config documents")
    
    # Clean up temporary credentials file if it exists
    fake_sa_path = '/tmp/fake_service_account.json'
    if os.path.exists(fake_sa_path):
        try:
            os.unlink(fake_sa_path)
        except:
            pass
    

if __name__ == "__main__":
    # Ensure we're using emulator
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        print("⚠️  WARNING: FIRESTORE_EMULATOR_HOST not set!")
        print("   This script should only run against the emulator.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    create_test_data()