#!/usr/bin/env python3
"""
Check the current image URLs for Ho-oh and Lugia in our Firestore data.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from shared_utils import initialize_firebase
from firebase_admin import firestore

def check_current_images():
    """Check what image URLs we currently have for Ho-oh and Lugia."""
    
    # Initialize Firebase
    initialize_firebase()
    db = firestore.client()
    
    print("Checking current Ho-oh and Lugia image URLs in Firestore...")
    
    # Look for Ho-oh and Lugia in the Wisdom of Sea and Sky set
    set_name = "Wisdom_of_Sea_and_Sky"  # This is how it's sanitized in Firestore
    
    try:
        set_doc_ref = db.collection("cards").document(set_name)
        set_cards_ref = set_doc_ref.collection("set_cards")
        
        # Look for cards 240 and 241
        for card_num in ["240", "241"]:
            print(f"\n--- Card {card_num} ---")
            
            # Try different possible document ID formats
            possible_ids = [
                f"Ho_Oh_ex_A4_{card_num}",
                f"Lugia_ex_A4_{card_num}",
                f"Ho_oh_ex_A4_{card_num}",
            ]
            
            # Also search by querying
            cards_query = set_cards_ref.where("card_number_str", "==", card_num).stream()
            
            found = False
            for card_doc in cards_query:
                found = True
                card_data = card_doc.to_dict()
                print(f"Document ID: {card_doc.id}")
                print(f"Name: {card_data.get('name', 'Unknown')}")
                print(f"Original Image URL: {card_data.get('original_image_url', 'None')}")
                print(f"Firebase Image URL: {card_data.get('firebase_image_url', 'None')}")
                
                # Check the timestamp if available
                if 'updated_at' in card_data:
                    print(f"Last Updated: {card_data.get('updated_at')}")
                    
            if not found:
                print(f"No card found with card_number_str = {card_num}")
                
    except Exception as e:
        print(f"Error checking Firestore: {e}")

if __name__ == "__main__":
    check_current_images()