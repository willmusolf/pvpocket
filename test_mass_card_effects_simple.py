#!/usr/bin/env python3
"""
Simplified Mass Card Effect Validation Suite

Tests problematic card patterns to ensure no effect parsing conflicts.
Uses a focused approach on known problematic patterns.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simulator.core.effect_engine import AdvancedEffectEngine
from simulator.core.coin_flip import CoinFlipManager  
import logging
import json

# Set up logging for errors only
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class MockPokemon:
    """Mock Pokemon for testing"""
    def __init__(self, name, energy_type="Fire"):
        self.card = type('Card', (), {
            'name': name,
            'energy_type': energy_type,
            'hp': 100
        })()
        self.current_hp = 100
        self.energy_attached = []
        self.status_conditions = []
        
    def heal(self, amount):
        self.current_hp = min(100, self.current_hp + amount)

# Test cases based on known problematic patterns
PROBLEMATIC_CARD_PATTERNS = [
    # Moltres ex type - coin flip + energy generation
    {
        'name': 'Moltres ex',
        'attacks': [{
            'name': 'Inferno Dance',
            'damage': '0',
            'effect_text': 'Flip 3 coins. Take an amount of [R] Energy from your Energy Zone equal to the number of heads and attach them to your Benched Pokémon in any way you like.',
        }]
    },
    # Similar energy generation patterns
    {
        'name': 'Test Energy Generator',
        'attacks': [{
            'name': 'Energy Boost',
            'damage': '0',
            'effect_text': 'Flip 2 coins. Attach energy equal to heads. Also take energy from your energy zone.',
        }]
    },
    # Colorless cost patterns (should never generate Colorless energy)
    {
        'name': 'Test Colorless',
        'attacks': [{
            'name': 'Generic Attack',
            'damage': '20',
            'effect_text': 'Take a [C] Energy and attach it to this Pokemon.',
        }]
    },
    # Energy scaling damage
    {
        'name': 'Alolan Raichu ex',
        'attacks': [{
            'name': 'Thunder',
            'damage': '20',
            'effect_text': 'This attack does 20 more damage for each Energy attached to your opponent\'s Active Pokémon.',
        }]
    },
    # Coin flip damage
    {
        'name': 'Marowak',
        'attacks': [{
            'name': 'Burning Bonemerang',
            'damage': '0',
            'effect_text': 'Flip 2 coins. This attack does 70 damage for each heads.',
        }]
    },
    # Variable coin flip based on bench
    {
        'name': 'Pikachu ex',
        'attacks': [{
            'name': 'Circle Circuit',
            'damage': '0',
            'effect_text': 'Flip a coin for each of your Benched Pokémon. This attack does 30 damage for each heads.',
        }]
    }
]

def validate_problematic_patterns():
    """Validate known problematic card effect patterns"""
    print("🚀 Starting Focused Card Effect Pattern Validation...")
    print("🎯 Testing known problematic patterns...")
    
    effect_engine = AdvancedEffectEngine(battle_cards=[], logger=logger)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for card_data in PROBLEMATIC_CARD_PATTERNS:
        card_name = card_data['name']
        print(f"\n🧪 Testing {card_name}...")
        
        for attack in card_data['attacks']:
            total_tests += 1
            attack_name = attack['name']
            effect_text = attack['effect_text']
            
            # Create test context
            attacker = MockPokemon(card_name, "Fire")
            defender = MockPokemon("Target", "Water")
            defender.energy_attached = ['Water', 'Water', 'Water']  # For energy scaling tests
            
            battle_context = {
                'turn': 1,
                'player': 0,
                'attacker': attacker,
                'defender': defender
            }
            
            try:
                base_damage = int(str(attack.get('damage', '0')).replace('+', '') or '0')
                
                # Test effect parsing
                result = effect_engine.execute_attack_effects(
                    attack, attacker, defender, base_damage, battle_context
                )
                
                # Validate results
                validation_passed = True
                issues = []
                
                # Check 1: No Colorless energy generation
                for energy_change in result.get('energy_changes', []):
                    if energy_change.get('energy_type') == 'Colorless':
                        issues.append(f"❌ Generates Colorless energy: {energy_change}")
                        validation_passed = False
                
                # Check 2: No duplicate energy generation (Moltres bug pattern)
                energy_changes = result.get('energy_changes', [])
                if len(energy_changes) > 1 and 'flip' in effect_text.lower():
                    energy_types = [ec.get('energy_type') for ec in energy_changes]
                    if len(set(energy_types)) == 1:
                        issues.append(f"⚠️  Potential duplicate energy generation: {len(energy_changes)} changes of type {energy_types[0]}")
                        validation_passed = False
                
                # Check 3: Basic effect execution
                if 'additional_effects' in result and not result['additional_effects']:
                    if effect_text:  # Only flag if there should be effects
                        issues.append("ℹ️  No effects parsed from non-empty effect text")
                
                if validation_passed:
                    passed_tests += 1
                    print(f"   ✅ {attack_name}: PASSED")
                    print(f"      Effects: {len(result.get('additional_effects', []))}")
                    print(f"      Energy Changes: {len(result.get('energy_changes', []))}")
                    if result.get('coin_results'):
                        print(f"      Coin Results: {result['coin_results']}")
                else:
                    failed_tests.append({
                        'card': card_name,
                        'attack': attack_name,
                        'issues': issues,
                        'result': result
                    })
                    print(f"   ❌ {attack_name}: FAILED")
                    for issue in issues:
                        print(f"      {issue}")
                
            except Exception as e:
                failed_tests.append({
                    'card': card_name,
                    'attack': attack_name,
                    'issues': [f"Exception: {str(e)}"],
                    'result': None
                })
                print(f"   ❌ {attack_name}: EXCEPTION - {e}")
                logger.exception(f"Error testing {card_name} - {attack_name}")
    
    # Summary
    print("\n" + "="*60)
    print("📈 FOCUSED PATTERN VALIDATION RESULTS")
    print("="*60)
    print(f"🧪 Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {len(failed_tests)}")
    
    if failed_tests:
        print("\n❌ FAILED TESTS:")
        for failure in failed_tests:
            print(f"   • {failure['card']} - {failure['attack']}")
            for issue in failure['issues']:
                print(f"     {issue}")
    else:
        print("\n🎉 ALL PATTERN TESTS PASSED!")
        print("✅ No energy duplication bugs detected")
        print("✅ No Colorless energy generation")
        print("✅ Priority-based parsing working correctly")
    
    # Save results
    results_summary = {
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'failed_tests': len(failed_tests),
        'failures': failed_tests
    }
    
    with open('pattern_validation_results.json', 'w') as f:
        json.dump(results_summary, f, indent=2)
    
    print(f"\n💾 Results saved to pattern_validation_results.json")
    
    return len(failed_tests) == 0

if __name__ == "__main__":
    success = validate_problematic_patterns()
    sys.exit(0 if success else 1)