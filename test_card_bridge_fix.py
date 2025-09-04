#!/usr/bin/env python3
"""
Test the CardDataBridge fixes for NoneType errors
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from Card import Card
from simulator.core.card_bridge import CardDataBridge, BattleCard
import logging

def test_card_bridge_fixes():
    """Test the fixes for NoneType errors in CardDataBridge"""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('test')
    
    print("Testing CardDataBridge fixes...")
    
    bridge = CardDataBridge(logger)
    
    # Test cases with various problematic data
    test_cards = [
        # Normal card
        Card(
            id=1,
            name="Pikachu",
            energy_type="Lightning",
            card_type="Basic Pokémon", 
            hp=60,
            attacks=[{"name": "Thunder Shock", "cost": ["L"], "damage": "30", "effect": "Flip a coin. If tails, this attack does nothing."}],
            abilities=[{"name": "Static", "effect": "When this Pokémon takes damage, flip a coin. If heads, the attacking Pokémon is now Paralyzed."}]
        ),
        
        # Card with None values (this would cause the original error)
        Card(
            id=2,
            name=None,  # This would cause "NoneType has no attribute 'lower'"
            energy_type=None,
            card_type=None,
            hp=70,
            attacks=[],
            abilities=None
        ),
        
        # Card with empty/malformed data
        Card(
            id=3,
            name="",
            energy_type="Fire",
            card_type="Stage 1 Pokémon",
            hp=80,
            attacks=[{"name": "Flame Thrower", "cost": None, "damage": None, "effect": None}],
            abilities=[None]
        ),
        
        # Card with complex attack costs and effects
        Card(
            id=4,
            name="Charizard ex",
            energy_type="Fire",
            card_type="Stage 2 Pokémon",
            hp=180,
            attacks=[
                {"name": "Crimson Storm", "cost": ["R", "R", "C"], "damage": "120", "effect": "Discard 2 Fire Energy from this Pokémon."},
                {"name": "Burning Claws", "cost": ["R"], "damage": "50", "effect": "Your opponent's Active Pokémon is now Burned."}
            ],
            abilities=[{"name": "Blaze", "effect": "As long as this Pokémon has damage counters on it, its attacks do 50 more damage."}]
        )
    ]
    
    results = []
    
    for i, card in enumerate(test_cards):
        print(f"\nTesting card {i+1}...")
        try:
            battle_card = bridge.convert_to_battle_card(card)
            
            # Validate the conversion worked
            assert isinstance(battle_card, BattleCard), "Should return BattleCard instance"
            assert battle_card.id == card.id, "ID should be preserved"
            assert battle_card.name, "Name should not be empty"
            assert isinstance(battle_card.attacks, list), "Attacks should be a list"
            assert isinstance(battle_card.abilities, list), "Abilities should be a list"
            
            print(f"✅ Card {i+1}: {battle_card.name} - {battle_card.energy_type}")
            print(f"   Attacks: {len(battle_card.attacks)}, Abilities: {len(battle_card.abilities)}")
            
            # Test attack parsing
            for attack in battle_card.attacks:
                print(f"   Attack: {attack['name']} - Cost: {attack['cost']} - Damage: {attack['damage']}")
                
            results.append(("PASS", battle_card.name or "Unknown"))
            
        except Exception as e:
            print(f"❌ Card {i+1} failed: {e}")
            results.append(("FAIL", str(e)))
    
    # Summary
    print(f"\n=== Test Results ===")
    passed = sum(1 for result in results if result[0] == "PASS")
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    for i, (status, details) in enumerate(results):
        print(f"  Card {i+1}: {status} - {details}")
    
    if passed == total:
        print("🎉 All tests passed! CardDataBridge fixes are working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. CardDataBridge needs more fixes.")
        return False

if __name__ == "__main__":
    success = test_card_bridge_fixes()
    sys.exit(0 if success else 1)