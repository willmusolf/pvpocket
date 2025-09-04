#!/usr/bin/env python3
"""
One-time script to assign release_order to existing sets in Firestore.
This ensures the automatic set priority system works properly.
"""

import os
import sys
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import secretmanager
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Known set release order (from newest to oldest)
# Higher numbers = newer sets
SET_RELEASE_ORDER = {
    "Secluded Springs": 11,       # Most recent (highest number)
    "Wisdom of Sea and Sky": 10,
    "Eevee Grove": 9,
    "Extradimensional Crisis": 8,
    "Celestial Guardians": 7,
    "Shining Revelry": 5,
    "Triumphant Light": 4,
    "Space-Time Smackdown": 4,    # Same as Triumphant Light
    "Mythical Island": 3,
    "Promo-A": 2,
    "Genetic Apex": 1,            # Oldest set
}

def initialize_firebase():
    """Initialize Firebase Admin SDK."""
    if not firebase_admin._apps:
        try:
            # Try local credentials file first
            cred_path = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
            if os.path.exists(cred_path):
                print("Initializing Firebase from local credentials...")
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print("Firebase initialized successfully.")
                return
                
            # Try Secret Manager if no local file
            project_id = os.environ.get("GCP_PROJECT_ID", "pvpocket-dd286")
            secret_name = os.environ.get("FIREBASE_SECRET_NAME", "firebase-admin-key")
            
            if project_id and secret_name:
                print(f"Initializing Firebase from Secret Manager...")
                client = secretmanager.SecretManagerServiceClient()
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                secret_payload = response.payload.data.decode("UTF-8")
                cred_dict = json.loads(secret_payload)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print("Firebase initialized successfully.")
            else:
                print("Initializing Firebase with Application Default Credentials...")
                firebase_admin.initialize_app()
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            exit(1)

def assign_release_orders():
    """Assign release_order to all sets based on known order."""
    db = firestore.client()
    
    print("\nAssigning release_order to sets...")
    
    # Get all sets
    sets_ref = db.collection("cards")
    sets = list(sets_ref.stream())
    
    updates_made = 0
    
    for set_doc in sets:
        set_data = set_doc.to_dict()
        set_name = set_data.get("set_name", "")
        current_release_order = set_data.get("release_order")
        
        # Get the correct release_order
        correct_release_order = SET_RELEASE_ORDER.get(set_name)
        
        if correct_release_order is not None:
            if current_release_order != correct_release_order:
                # Update the release_order
                set_doc.reference.update({"release_order": correct_release_order})
                print(f"✓ Updated {set_name}: release_order = {correct_release_order}")
                updates_made += 1
            else:
                print(f"  {set_name} already has correct release_order: {correct_release_order}")
        else:
            print(f"⚠️  Unknown set: {set_name} (document: {set_doc.id})")
    
    print(f"\nCompleted! Updated {updates_made} sets.")
    
    # Show final state
    print("\nFinal release_order values (highest = newest):")
    sets = list(sets_ref.order_by("release_order", direction=firestore.Query.DESCENDING).stream())
    for set_doc in sets:
        set_data = set_doc.to_dict()
        print(f"  {set_data.get('release_order', '?')}: {set_data.get('set_name', 'Unknown')}")

if __name__ == "__main__":
    print("Release Order Assignment Script")
    print("=" * 50)
    
    initialize_firebase()
    assign_release_orders()
    
    print("\nDone! The automatic set priority system is now active.")
    print("New sets will automatically get the highest priority when scraped.")