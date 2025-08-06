#!/usr/bin/env python3
"""
Debug script to check Firestore data structure in production vs local
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

def check_firestore_data():
    """Check the actual Firestore data structure"""
    
    # First check local emulator data
    print("🔍 CHECKING LOCAL EMULATOR DATA:")
    print("=" * 50)
    
    try:
        os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
        import firebase_admin
        from firebase_admin import firestore
        
        if not firebase_admin._apps:
            emulator_app = firebase_admin.initialize_app(name='emulator')
        else:
            try:
                emulator_app = firebase_admin.get_app('emulator')
            except ValueError:
                emulator_app = firebase_admin.initialize_app(name='emulator')
        
        emulator_db = firestore.client(emulator_app)
        
        # Check first few set documents in emulator
        sets_ref = emulator_db.collection('cards')
        sets_docs = list(sets_ref.limit(3).stream())
        
        print(f"Found {len(sets_docs)} set documents in EMULATOR:")
        for doc in sets_docs:
            data = doc.to_dict()
            set_name = data.get('set_name', 'Unknown')
            release_order = data.get('release_order')
            print(f"  - {set_name}: release_order = {release_order}")
            
            # Check if this has subcollection
            subcollection_ref = doc.reference.collection('set_cards')
            cards = list(subcollection_ref.limit(1).stream())
            print(f"     Has {len(cards)} cards in subcollection")
            if cards:
                card_data = cards[0].to_dict()
                card_set_release_order = card_data.get('set_release_order')
                print(f"     Card set_release_order: {card_set_release_order}")
        
    except Exception as e:
        print(f"❌ Error checking emulator: {e}")
    
    print("\n" + "=" * 50)
    print("🔍 CHECKING PRODUCTION DATA:")
    print("=" * 50)
    
    try:
        # Clear emulator env var to connect to production
        if 'FIRESTORE_EMULATOR_HOST' in os.environ:
            del os.environ['FIRESTORE_EMULATOR_HOST']
        
        # Initialize production Firebase
        import firebase_admin
        from firebase_admin import firestore, credentials
        
        # Initialize production app
        try:
            prod_app = firebase_admin.get_app('production')
        except ValueError:
            # Use service account for production
            cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                prod_app = firebase_admin.initialize_app(cred, name='production')
            else:
                # Use default credentials
                prod_app = firebase_admin.initialize_app(name='production')
        
        prod_db = firestore.client(prod_app)
        
        # Check first few set documents in production
        sets_ref = prod_db.collection('cards')
        sets_docs = list(sets_ref.limit(3).stream())
        
        print(f"Found {len(sets_docs)} set documents in PRODUCTION:")
        for doc in sets_docs:
            data = doc.to_dict()
            set_name = data.get('set_name', 'Unknown')
            release_order = data.get('release_order')
            print(f"  - {set_name}: release_order = {release_order}")
            
            # Check if this has subcollection  
            subcollection_ref = doc.reference.collection('set_cards')
            cards = list(subcollection_ref.limit(1).stream())
            print(f"     Has {len(cards)} cards in subcollection")
            if cards:
                card_data = cards[0].to_dict()
                card_set_release_order = card_data.get('set_release_order')
                print(f"     Card set_release_order: {card_set_release_order}")
        
    except Exception as e:
        print(f"❌ Error checking production: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_firestore_data()