#!/usr/bin/env python3
"""
Quick script to sync your user data from production to emulator.
This allows you to use your existing account in local development.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if emulator is running
import socket
try:
    with socket.create_connection(('localhost', 8080), timeout=1):
        print("✅ Firebase emulator detected")
except (socket.error, ConnectionRefusedError):
    print("❌ Firebase emulator not running. Start it with: python3 run.py")
    sys.exit(1)

# Initialize Firebase for production
from shared_utils import initialize_firebase
initialize_firebase()

import firebase_admin
from firebase_admin import firestore

# Get your user ID from the error message or command line
if len(sys.argv) > 1:
    user_id = sys.argv[1]
else:
    user_id = input("Enter your user ID (from the error message): ").strip()
    
if not user_id:
    print("❌ No user ID provided")
    print("Usage: python3 sync_my_user.py <user-id>")
    sys.exit(1)

print(f"🔄 Syncing user {user_id} from production to emulator...")

try:
    # Clear emulator host to connect to production
    old_host = os.environ.get('FIRESTORE_EMULATOR_HOST')
    if 'FIRESTORE_EMULATOR_HOST' in os.environ:
        del os.environ['FIRESTORE_EMULATOR_HOST']
    
    # Get production database
    prod_db = firestore.client()
    
    # Get user data from production
    user_ref = prod_db.collection('users').document(user_id)
    user_doc = user_ref.get()
    
    if not user_doc.exists:
        print(f"❌ User {user_id} not found in production")
        sys.exit(1)
    
    user_data = user_doc.to_dict()
    print(f"✅ Found user: {user_data.get('username', 'No username')}")
    
    # Get user's decks
    decks_ref = prod_db.collection('decks').where('user_id', '==', user_id)
    user_decks = list(decks_ref.stream())
    print(f"📦 Found {len(user_decks)} decks")
    
    # Connect to emulator
    main_project_id = os.environ.get('GCP_PROJECT_ID', 'pvpocket-dd286')
    emulator_app = firebase_admin.initialize_app(
        name='emulator_sync_app',
        options={'projectId': main_project_id}
    )
    
    # Set emulator environment
    os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
    emulator_db = firestore.client(app=emulator_app)
    
    # Copy user to emulator
    print("📝 Copying user data to emulator...")
    emulator_user_ref = emulator_db.collection('users').document(user_id)
    emulator_user_ref.set(user_data)
    
    # Copy user's decks
    print("🃏 Copying decks to emulator...")
    for deck_doc in user_decks:
        deck_data = deck_doc.to_dict()
        deck_id = deck_doc.id
        
        emulator_deck_ref = emulator_db.collection('decks').document(deck_id)
        emulator_deck_ref.set(deck_data)
        print(f"  ✅ Deck: {deck_data.get('name', 'Unnamed')}")
    
    print(f"\n✅ Successfully synced user {user_id} to emulator!")
    print("🎉 You can now use your account in local development")
    
except Exception as e:
    print(f"❌ Error syncing user: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Cleanup
    if old_host:
        os.environ['FIRESTORE_EMULATOR_HOST'] = old_host
    
    if 'emulator_sync_app' in firebase_admin._apps:
        firebase_admin.delete_app(firebase_admin.get_app('emulator_sync_app'))