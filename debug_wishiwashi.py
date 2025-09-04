#!/usr/bin/env python3
"""
Debug Wishiwashi ex effect parsing issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simulator.core.card_bridge import load_real_card_collection

# Load cards and find Wishiwashi ex
cards = load_real_card_collection()
print(f"Loaded {len(cards)} cards")

for card in cards:
    if "wishiwashi" in card.name.lower() and "ex" in card.name.lower():
        print(f"\n🔍 Found: {card.name}")
        print(f"   ID: {card.id}")
        print(f"   Type: {card.card_type}")
        
        if hasattr(card, 'attacks') and card.attacks:
            for i, attack in enumerate(card.attacks):
                print(f"\n   Attack {i+1}: {attack.get('name', 'Unknown')}")
                print(f"   Damage: {attack.get('damage', 'None')}")
                effect_text = attack.get('effect_text', '') or attack.get('effect', '')
                if effect_text:
                    print(f"   Effect: {effect_text}")
                else:
                    print(f"   Effect: None")
        break
else:
    print("Wishiwashi ex not found in card collection")
    
    # Show some cards for debugging
    print("\nFirst 10 cards:")
    for i, card in enumerate(cards[:10]):
        print(f"   {i+1}. {card.name}")