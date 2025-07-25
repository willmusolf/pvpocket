#!/usr/bin/env python3
"""
Seed Firebase emulator with test data for integration testing.
Run this before running integration tests locally or in CI.
"""

import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path


def seed_emulator():
    """Seed Firebase emulator with test data."""
    # Set emulator environment variables
    os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
    os.environ['FIREBASE_STORAGE_EMULATOR_HOST'] = 'localhost:9199'
    
    # Initialize Firebase Admin SDK for emulator
    if not firebase_admin._apps:
        # Use demo project for emulator
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {
            'projectId': 'demo-test-project',
        })
    
    db = firestore.client()
    
    # Load seed data
    seed_file = Path(__file__).parent.parent / 'tests' / 'test_seed_data.json'
    with open(seed_file) as f:
        seed_data = json.load(f)
    
    print("🌱 Seeding Firebase emulator with test data...")
    
    # Add cards
    cards_ref = db.collection('cards')
    for card in seed_data['cards']:
        cards_ref.document(card['id']).set(card)
        print(f"  ✅ Added card: {card['name']}")
    
    # Add users
    users_ref = db.collection('users')
    for user in seed_data['users']:
        users_ref.document(user['id']).set(user)
        print(f"  ✅ Added user: {user['username']}")
    
    # Add decks
    decks_ref = db.collection('decks')
    for deck in seed_data['decks']:
        decks_ref.document(deck['id']).set(deck)
        print(f"  ✅ Added deck: {deck['name']}")
    
    # Add a card set for the cards
    sets_ref = db.collection('internal_config').document('sets_tracker')
    sets_ref.set({
        'available_sets': ['Genetic Apex'],
        'last_updated': firestore.SERVER_TIMESTAMP
    })
    print("  ✅ Added card sets configuration")
    
    print("\n✨ Firebase emulator seeded successfully!")
    print("You can now run integration tests with: RUN_INTEGRATION_TESTS=1 pytest tests/integration/")


if __name__ == "__main__":
    seed_emulator()