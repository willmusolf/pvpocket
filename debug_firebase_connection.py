#!/usr/bin/env python3
"""
Debug script to test Firebase Admin SDK vs REST API data visibility.
This will help identify the exact cause of the namespace isolation issue.
"""

import os
import sys
import json
import requests
import firebase_admin
from firebase_admin import credentials, firestore

def test_rest_api_access():
    """Test accessing data via REST API (like seeding script)."""
    print("="*60)
    print("🌐 TESTING REST API ACCESS (same as seeding)")
    print("="*60)
    
    emulator_host = os.environ.get('FIRESTORE_EMULATOR_HOST', '127.0.0.1:8080')
    project_id = 'demo-test-project'
    
    url = f"http://{emulator_host}/v1/projects/{project_id}/databases/(default)/documents/cards"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"🔍 REST API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            docs = data.get('documents', [])
            print(f"📋 REST API found {len(docs)} documents in cards collection")
            
            for i, doc in enumerate(docs[:3]):
                doc_id = doc['name'].split('/')[-1]
                doc_fields = doc.get('fields', {})
                name = doc_fields.get('name', {}).get('stringValue', 'Unknown')
                print(f"  - Document {doc_id}: {name}")
            
            return len(docs)
        else:
            print(f"❌ REST API Error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return 0
            
    except Exception as e:
        print(f"❌ REST API Exception: {e}")
        return 0

def test_admin_sdk_access():
    """Test accessing data via Firebase Admin SDK (like Flask app)."""
    print("\n" + "="*60)
    print("🔥 TESTING FIREBASE ADMIN SDK ACCESS (same as Flask app)")
    print("="*60)
    
    # Initialize Firebase Admin SDK exactly like Flask app
    if firebase_admin._apps:
        app = firebase_admin.get_app()
        print("🔄 Using existing Firebase app")
    else:
        print("🆕 Initializing new Firebase app")
        
        # Set environment variables like Flask app does
        emulator_project_id = 'demo-test-project'
        os.environ['GCLOUD_PROJECT'] = emulator_project_id
        os.environ['FIREBASE_PROJECT_ID'] = emulator_project_id
        
        print(f"📋 Setting project ID: {emulator_project_id}")
        print(f"🔗 Emulator host: {os.environ.get('FIRESTORE_EMULATOR_HOST')}")
        
        try:
            app = firebase_admin.initialize_app(options={
                'projectId': emulator_project_id,
                'storageBucket': 'pvpocket-dd286.firebasestorage.app'
            })
            print("✅ Firebase Admin SDK initialized successfully")
        except Exception as e:
            print(f"❌ Firebase Admin SDK initialization failed: {e}")
            return 0
    
    # Test database access
    try:
        db = firestore.client()
        print(f"🔍 Admin SDK client created, project: {db.project}")
        print(f"🔍 Admin SDK using emulator: {bool(os.environ.get('FIRESTORE_EMULATOR_HOST'))}")
        
        # List all collections
        collections = list(db.collections())
        print(f"📂 Admin SDK found {len(collections)} collections:")
        for col in collections:
            print(f"  - Collection: {col.id}")
        
        # Try to access cards collection
        cards_ref = db.collection('cards')
        cards = list(cards_ref.stream())
        print(f"📋 Admin SDK found {len(cards)} documents in cards collection")
        
        for i, card in enumerate(cards[:3]):
            card_data = card.to_dict()
            name = card_data.get('name', 'Unknown')
            print(f"  - Document {card.id}: {name}")
        
        return len(cards)
        
    except Exception as e:
        print(f"❌ Admin SDK Exception: {e}")
        import traceback
        traceback.print_exc()
        return 0

def test_environment_variables():
    """Test environment variable configuration."""
    print("\n" + "="*60)
    print("🔧 TESTING ENVIRONMENT VARIABLES")
    print("="*60)
    
    env_vars = [
        'FIRESTORE_EMULATOR_HOST',
        'GCP_PROJECT_ID', 
        'GCLOUD_PROJECT',
        'FIREBASE_PROJECT_ID',
        'RUN_INTEGRATION_TESTS',
        'FORCE_EMULATOR_MODE',
        'FLASK_CONFIG'
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        print(f"🔍 {var}: {value}")

def main():
    """Run all diagnostic tests."""
    print("🚀 FIREBASE CONNECTION DIAGNOSTIC")
    print("This script will help identify why Flask app can't see seeded data")
    
    # Test environment
    test_environment_variables()
    
    # Test both access methods
    rest_count = test_rest_api_access()
    admin_count = test_admin_sdk_access()
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"REST API found: {rest_count} cards")
    print(f"Admin SDK found: {admin_count} cards")
    
    if rest_count > 0 and admin_count == 0:
        print("❌ PROBLEM IDENTIFIED: Admin SDK namespace isolation issue")
        print("   - REST API can see data (seeding works)")
        print("   - Admin SDK cannot see data (Flask app fails)")
        print("   - This confirms namespace/project mismatch")
    elif rest_count > 0 and admin_count > 0:
        print("✅ SUCCESS: Both methods can see data")
        print("   - Data visibility confirmed for both REST API and Admin SDK")
    elif rest_count == 0:
        print("❌ SEEDING FAILED: No data found via REST API")
        print("   - The seeding process may have failed")
    else:
        print("❓ UNKNOWN STATE: Unexpected result pattern")
    
    return admin_count > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)