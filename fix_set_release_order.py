#!/usr/bin/env python3
"""
Script to check and fix set_release_order values in Firebase.

This script will:
1. Check current set_release_order values for all sets in the database
2. Update them to the correct order based on the provided mapping
3. Update all cards within each set to have the correct set_release_order

Correct order:
- Wisdom of Sea and Sky: 10 (newest)
- Eevee Grove: 9  
- Extradimensional Crisis: 8
- Celestial Guardians: 7
- Shining Revelry: 5
- Space-Time Smackdown: 4
- Triumphant Light: 4
- Mythical Island: 3
- Promo-A: 2
- Genetic Apex: 1 (oldest)
"""

import os
import sys
from dotenv import load_dotenv
from shared_utils import initialize_firebase
from firebase_admin import firestore
import json

# Load environment variables
load_dotenv()

# Correct set release order mapping (using underscore format as stored in database)
CORRECT_SET_ORDER = {
    "Wisdom_of_Sea_and_Sky": 10,
    "Eevee_Grove": 9,
    "Extradimensional_Crisis": 8,
    "Celestial_Guardians": 7,
    "Shining_Revelry": 5,
    "Space_Time_Smackdown": 4,
    "Triumphant_Light": 4,
    "Mythical_Island": 3,
    "Promo_A": 2,
    "Genetic_Apex": 1,
}

def check_current_set_orders():
    """Check and display current set_release_order values in the database."""
    print("🔍 Checking current set_release_order values in Firebase...")
    
    # Initialize Firebase
    initialize_firebase()
    db = firestore.client()
    
    # Get all sets from the cards collection
    sets_collection = db.collection("cards")
    set_docs = list(sets_collection.stream())
    
    print(f"\nFound {len(set_docs)} set documents in the cards collection:")
    print("-" * 70)
    
    current_orders = {}
    
    for set_doc in set_docs:
        set_data = set_doc.to_dict()
        set_name = set_data.get("name", set_doc.id)
        release_order = set_data.get("release_order")
        
        current_orders[set_name] = release_order
        
        # Show current vs expected
        expected_order = CORRECT_SET_ORDER.get(set_name, "UNKNOWN")
        status = "✅" if release_order == expected_order else "❌"
        
        print(f"{status} {set_name:<30} | Current: {release_order:<4} | Expected: {expected_order}")
    
    print("-" * 70)
    return current_orders

def update_set_orders(dry_run=True):
    """Update set_release_order values to the correct order."""
    action = "DRY RUN" if dry_run else "UPDATING"
    print(f"\n🔧 {action}: Fixing set_release_order values...")
    
    # Initialize Firebase
    initialize_firebase()
    db = firestore.client()
    
    # Get all sets from the cards collection
    sets_collection = db.collection("cards")
    set_docs = list(sets_collection.stream())
    
    updates_needed = []
    cards_to_update = []
    
    # Check each set document
    for set_doc in set_docs:
        set_data = set_doc.to_dict()
        set_name = set_data.get("name", set_doc.id)
        current_order = set_data.get("release_order")
        
        if set_name in CORRECT_SET_ORDER:
            correct_order = CORRECT_SET_ORDER[set_name]
            
            if current_order != correct_order:
                updates_needed.append({
                    "doc_ref": set_doc.reference,
                    "set_name": set_name,
                    "current_order": current_order,
                    "correct_order": correct_order
                })
                
                # Also collect cards that need updating
                cards_subcoll = set_doc.reference.collection("set_cards")
                card_docs = list(cards_subcoll.stream())
                
                for card_doc in card_docs:
                    card_data = card_doc.to_dict()
                    card_release_order = card_data.get("set_release_order")
                    
                    if card_release_order != correct_order:
                        cards_to_update.append({
                            "doc_ref": card_doc.reference,
                            "card_name": card_data.get("name", "Unknown"),
                            "set_name": set_name,
                            "current_order": card_release_order,
                            "correct_order": correct_order
                        })
        else:
            print(f"⚠️  Unknown set found: {set_name} (not in correct order mapping)")
    
    print(f"\nSets that need updating: {len(updates_needed)}")
    print(f"Cards that need updating: {len(cards_to_update)}")
    
    if updates_needed:
        print("\nSet updates needed:")
        for update in updates_needed:
            print(f"  • {update['set_name']}: {update['current_order']} → {update['correct_order']}")
    
    if not dry_run:
        print(f"\n🚀 Applying {len(updates_needed)} set updates and {len(cards_to_update)} card updates...")
        
        # Update set documents
        for update in updates_needed:
            try:
                update["doc_ref"].update({"release_order": update["correct_order"]})
                print(f"✅ Updated {update['set_name']} release_order: {update['current_order']} → {update['correct_order']}")
            except Exception as e:
                print(f"❌ Failed to update {update['set_name']}: {e}")
        
        # Update card documents in batches
        batch_size = 100
        for i in range(0, len(cards_to_update), batch_size):
            batch = cards_to_update[i:i + batch_size]
            
            # Use Firestore batch for efficient updates
            batch_writer = db.batch()
            
            for card_update in batch:
                batch_writer.update(card_update["doc_ref"], {"set_release_order": card_update["correct_order"]})
            
            try:
                batch_writer.commit()
                print(f"✅ Updated batch of {len(batch)} cards ({i+1} to {min(i+batch_size, len(cards_to_update))})")
            except Exception as e:
                print(f"❌ Failed to update card batch: {e}")
        
        print(f"\n🎉 Update complete! Updated {len(updates_needed)} sets and {len(cards_to_update)} cards")
    else:
        print(f"\n📝 This was a dry run. Run with --apply to actually make changes.")
    
    return len(updates_needed), len(cards_to_update)

def main():
    """Main function to check and optionally fix set release orders."""
    print("🏟️  Pokemon TCG Pocket - Set Release Order Fixer")
    print("=" * 50)
    
    # Check if we should apply changes
    apply_changes = "--apply" in sys.argv
    
    try:
        # Step 1: Check current values
        current_orders = check_current_set_orders()
        
        # Step 2: Show what needs fixing
        sets_to_fix, cards_to_fix = update_set_orders(dry_run=not apply_changes)
        
        if sets_to_fix == 0 and cards_to_fix == 0:
            print("\n🎉 All set_release_order values are already correct!")
        elif not apply_changes:
            print(f"\n🔧 To apply these fixes, run: python {sys.argv[0]} --apply")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()