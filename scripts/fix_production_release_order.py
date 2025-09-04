#!/usr/bin/env python3
"""
Fix production Firestore by adding release_order fields to set documents and cards
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path to import app module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set release order mapping based on Pokemon TCG Pocket release dates
SET_RELEASE_ORDER = {
    "Genetic Apex": 1,
    "Promo-A": 2,
    "Mythical Island": 3,
    "Triumphant Light": 4,
    "Shining Revelry": 5,
    "Space-Time Smackdown": 4,  # Same as Triumphant Light
    "Celestial Guardians": 7,
    "Extradimensional Crisis": 8,
    "Eevee Grove": 9,
    "Wisdom of Sea and Sky": 10,
    "Secluded Springs": 11,
}

def fix_production_firestore():
    """Add release_order fields to production Firestore"""
    print("🔧 FIXING PRODUCTION FIRESTORE RELEASE ORDER")
    print("=" * 60)
    
    try:
        # Use app context to connect to production Firestore
        from app import create_app
        from flask import current_app
        
        # Create production app
        app = create_app('production')
        
        with app.app_context():
            db_client = current_app.config.get("FIRESTORE_DB")
            if not db_client:
                print("❌ No Firestore client available")
                return False
            
            # Step 1: Update set documents with release_order
            print("📝 Step 1: Adding release_order to set documents...")
            
            sets_ref = db_client.collection('cards')
            sets_docs = list(sets_ref.stream())
            
            print(f"Found {len(sets_docs)} set documents in production:")
            
            updated_sets = 0
            for doc in sets_docs:
                data = doc.to_dict()
                set_name = data.get('set_name', 'Unknown')
                current_release_order = data.get('release_order')
                
                # Look up the correct release order
                correct_release_order = SET_RELEASE_ORDER.get(set_name)
                
                print(f"  - {set_name}: current={current_release_order}, should be={correct_release_order}")
                
                if correct_release_order and current_release_order != correct_release_order:
                    # Update the set document
                    doc.reference.update({'release_order': correct_release_order})
                    print(f"    ✅ Updated {set_name} to release_order={correct_release_order}")
                    updated_sets += 1
                elif correct_release_order is None:
                    print(f"    ⚠️  Unknown set: {set_name} - please add to SET_RELEASE_ORDER")
            
            print(f"\n📊 Updated {updated_sets} set documents")
            
            # Step 2: Update all cards with set_release_order from their parent set
            print("\n📝 Step 2: Adding set_release_order to all cards...")
            
            updated_cards = 0
            total_cards = 0
            
            for doc in sets_docs:
                data = doc.to_dict()
                set_name = data.get('set_name', 'Unknown')
                set_release_order = data.get('release_order')
                
                if set_release_order is None:
                    print(f"  ⚠️  Skipping {set_name} - no release_order in set document")
                    continue
                
                # Update all cards in this set's subcollection
                cards_ref = doc.reference.collection('set_cards')
                cards_docs = list(cards_ref.stream())
                
                print(f"  📦 {set_name}: updating {len(cards_docs)} cards...")
                
                set_updated_cards = 0
                for card_doc in cards_docs:
                    card_data = card_doc.to_dict()
                    current_set_release_order = card_data.get('set_release_order')
                    
                    if current_set_release_order != set_release_order:
                        # Update the card with set_release_order
                        card_doc.reference.update({'set_release_order': set_release_order})
                        set_updated_cards += 1
                    
                    total_cards += 1
                
                if set_updated_cards > 0:
                    print(f"    ✅ Updated {set_updated_cards} cards with set_release_order={set_release_order}")
                else:
                    print(f"    ✅ All {len(cards_docs)} cards already have correct set_release_order")
                
                updated_cards += set_updated_cards
            
            print(f"\n🎉 SUMMARY:")
            print(f"  - Updated {updated_sets} set documents with release_order")
            print(f"  - Updated {updated_cards} out of {total_cards} cards with set_release_order")
            print(f"  - Production should now match local behavior!")
            
            return True
            
    except Exception as e:
        print(f"❌ Error fixing production: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_production_firestore()
    if success:
        print("\n✅ Production fix completed! Try your website now.")
    else:
        print("\n❌ Production fix failed. Check the errors above.")