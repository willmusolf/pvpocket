#!/usr/bin/env python3
"""
Seed Firebase emulator with test data for integration testing.
Run this before running integration tests locally or in CI.
"""

import os
import json
import tempfile
import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path


def seed_emulator():
    """Seed Firebase emulator with test data."""
    # Set emulator environment variables
    os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
    os.environ['FIREBASE_STORAGE_EMULATOR_HOST'] = 'localhost:9199'
    
    # For emulator, skip authentication entirely by setting this environment variable
    os.environ['FIREBASE_AUTH_EMULATOR_HOST'] = 'localhost:9099'  
    # This tells Firebase Admin SDK to skip authentication for emulator
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = ''
    os.environ['GCLOUD_PROJECT'] = 'demo-test-project'
    
    temp_cred_file = None  # Initialize for cleanup
    
    try:
        # Initialize Firebase Admin SDK for emulator without credentials 
        if not firebase_admin._apps:
            # Use mock credentials - create a valid RSA key for emulator
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.backends import default_backend
            
            # Generate a temporary RSA key for the emulator
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            pem_private = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            service_account_info = {
                "type": "service_account",
                "project_id": "demo-test-project",
                "private_key_id": "fake-key-id",
                "private_key": pem_private.decode('utf-8'),
                "client_email": "test@demo-test-project.iam.gserviceaccount.com",
                "client_id": "123456789012345678901",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://accounts.google.com/o/oauth2/token"
            }
            
            # Write to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(service_account_info, f)
                temp_cred_file = f.name
            
            # Use the temporary credentials
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_cred_file
            
            firebase_admin.initialize_app(options={
                'projectId': 'demo-test-project',
            })
        
        db = firestore.client()
        
        # Test connection to emulator
        try:
            test_doc = db.collection('_test').document('_connection_test')
            test_doc.set({'test': True})
            test_doc.delete()
            print("✅ Successfully connected to Firebase emulator!")
        except Exception as e:
            print(f"❌ Failed to connect to Firebase emulator: {e}")
            print("Make sure the Firebase emulator is running on localhost:8080")
            raise
        
        # Load seed data
        seed_file = Path(__file__).parent.parent / 'tests' / 'test_seed_data.json'
        if not seed_file.exists():
            print(f"❌ Seed data file not found: {seed_file}")
            raise FileNotFoundError(f"Seed data file not found: {seed_file}")
            
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
        
    except Exception as e:
        print(f"❌ Failed to seed Firebase emulator: {e}")
        raise
    finally:
        # Clean up temporary credentials file
        if temp_cred_file and os.path.exists(temp_cred_file):
            try:
                os.unlink(temp_cred_file)
            except:
                pass


if __name__ == "__main__":
    seed_emulator()