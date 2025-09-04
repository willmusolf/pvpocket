#!/usr/bin/env python3
"""
Test Wishiwashi ex bench scaling damage fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simulator.core.effect_engine import AdvancedEffectEngine
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockPokemon:
    def __init__(self, name):
        self.card = type('Card', (), {'name': name})()

class MockAttacker:
    def __init__(self):
        self.bench = [None, None, None]

def test_wishiwashi_bench_scaling():
    """Test that Wishiwashi ex School Storm scales correctly with bench Pokemon"""
    print("🧪 Testing Wishiwashi ex bench scaling damage...")
    
    effect_engine = AdvancedEffectEngine(battle_cards=[], logger=logger)
    
    # Test cases
    test_cases = [
        {
            'bench_pokemon': [],
            'expected_bonus': 0,
            'description': 'No bench Pokemon'
        },
        {
            'bench_pokemon': ['Magikarp', 'Gyarados', 'Pikachu'],
            'expected_bonus': 0,
            'description': 'Non-Wishiwashi bench Pokemon'
        },
        {
            'bench_pokemon': ['Wishiwashi', 'Magikarp', 'Gyarados'],
            'expected_bonus': 40,
            'description': 'One Wishiwashi on bench'
        },
        {
            'bench_pokemon': ['Wishiwashi ex', 'Magikarp', 'Gyarados'],
            'expected_bonus': 40,
            'description': 'One Wishiwashi ex on bench'
        },
        {
            'bench_pokemon': ['Wishiwashi', 'Wishiwashi ex', 'Magikarp'],
            'expected_bonus': 80,
            'description': 'Both Wishiwashi and Wishiwashi ex on bench'
        },
        {
            'bench_pokemon': ['Wishiwashi', 'Wishiwashi', 'Wishiwashi ex'],
            'expected_bonus': 120,
            'description': 'Three qualifying Pokemon on bench'
        }
    ]
    
    school_storm_attack = {
        'name': 'School Storm',
        'damage': '30',
        'effect_text': 'This attack does 40 more damage for each of your Benched Wishiwashi or Wishiwashi ex.'
    }
    
    for test_case in test_cases:
        print(f"\n🔍 Test: {test_case['description']}")
        
        # Set up mock attacker with specific bench
        attacker = MockAttacker()
        for i, pokemon_name in enumerate(test_case['bench_pokemon']):
            if i < 3:  # Max bench size
                attacker.bench[i] = MockPokemon(pokemon_name) if pokemon_name else None
        
        defender = MockPokemon('Target')
        
        battle_context = {
            'attacker': attacker,
            'defender': defender
        }
        
        # Execute attack effects
        result = effect_engine.execute_attack_effects(
            school_storm_attack, attacker, defender, 30, battle_context
        )
        
        expected_total = 30 + test_case['expected_bonus']
        actual_bonus = result['final_damage'] - 30
        
        print(f"   Expected: {expected_total} damage (30 base + {test_case['expected_bonus']} bonus)")
        print(f"   Actual: {result['final_damage']} damage (30 base + {actual_bonus} bonus)")
        print(f"   Effects: {result.get('additional_effects', [])}")
        
        if result['final_damage'] == expected_total:
            print(f"   ✅ PASSED")
        else:
            print(f"   ❌ FAILED")
            return False
    
    print(f"\n🎉 All Wishiwashi bench scaling tests PASSED!")
    print(f"✅ The bench scaling damage calculation is working correctly!")
    return True

if __name__ == "__main__":
    success = test_wishiwashi_bench_scaling()
    sys.exit(0 if success else 1)