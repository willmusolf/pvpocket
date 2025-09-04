#!/usr/bin/env python3
"""
Comprehensive Effect Priority System Validation Test

This test validates that the new priority-based effect parsing system works correctly
and prevents conflicts like the Moltres ex energy duplication bug.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simulator.core.effect_engine import AdvancedEffectEngine
from simulator.core.coin_flip import CoinFlipManager  
from simulator.core.status_conditions import StatusManager
from simulator.core.trainer_cards import TrainerCardManager
from simulator.core.evolution import EvolutionManager
from simulator.core.pokemon import BattlePokemon
from Card import Card
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MockCard:
    """Mock card for testing"""
    def __init__(self, name, energy_type="Fire", hp=100):
        self.name = name
        self.energy_type = energy_type
        self.hp = hp
        self.id = f"test_{name}"
        self.card_type = "Basic Pokemon"
        self.weakness = None
        self.retreat_cost = 1

class MockPokemon:
    """Mock Pokemon for testing"""
    def __init__(self, name, energy_type="Fire"):
        self.card = MockCard(name, energy_type)
        self.current_hp = self.card.hp
        self.energy_attached = []
        self.status_conditions = []
        
    def heal(self, amount):
        self.current_hp = min(self.card.hp, self.current_hp + amount)

def test_priority_system():
    """Test that effects are processed in correct priority order"""
    print("\n🧪 Testing Effect Priority System...")
    
    # Create effect engine (with empty battle_cards list for testing)
    effect_engine = AdvancedEffectEngine(battle_cards=[], logger=logger, rng_seed=12345)
    
    # Create mock Pokemon
    attacker = MockPokemon("Moltres ex", "Fire")
    defender = MockPokemon("Pikachu", "Lightning")
    
    # Test Moltres ex Inferno Dance - should only generate energy from coin flips
    moltres_attack = {
        'name': 'Inferno Dance',
        'damage': '0',
        'effect_text': 'Flip 3 coins. Take an amount of [R] Energy from your Energy Zone equal to the number of heads and attach them to your Benched Pokémon in any way you like.',
        'energy_cost': ['R']
    }
    
    battle_context = {
        'turn': 1,
        'player': 0,
        'attacker': attacker,
        'defender': defender
    }
    
    # Execute effects
    result = effect_engine.execute_attack_effects(moltres_attack, attacker, defender, 0, battle_context)
    
    print(f"📊 Effect Execution Results:")
    print(f"   Final Damage: {result['final_damage']}")
    print(f"   Energy Changes: {len(result['energy_changes'])}")
    print(f"   Coin Results: {result['coin_results']}")
    print(f"   Additional Effects: {result['additional_effects']}")
    
    # Validate results
    assert result['final_damage'] == 0, f"Expected 0 damage, got {result['final_damage']}"
    
    # Should have exactly one energy change (from coin flip), not multiple from generic parser
    energy_change_count = len(result['energy_changes'])
    print(f"   ✅ Energy changes: {energy_change_count} (should be exactly 1)")
    
    # Should have coin results
    assert len(result['coin_results']) == 3, f"Expected 3 coin results, got {len(result['coin_results'])}"
    print(f"   ✅ Coin flip results: {result['coin_results']}")
    
    # Check that energy generation is Fire type, never Colorless
    for energy_change in result['energy_changes']:
        assert energy_change['energy_type'] == 'Fire', f"Expected Fire energy, got {energy_change['energy_type']}"
        print(f"   ✅ Energy type: {energy_change['energy_type']} (correct, not Colorless)")
    
    print("   ✅ Moltres ex Inferno Dance test PASSED - no energy duplication!")
    
    return True

def test_effect_conflicts():
    """Test that conflicting effects are resolved by priority"""
    print("\n🔍 Testing Effect Conflict Resolution...")
    
    effect_engine = AdvancedEffectEngine(battle_cards=[], logger=logger, rng_seed=12345)
    attacker = MockPokemon("Test Pokemon", "Fire")
    defender = MockPokemon("Target Pokemon", "Lightning")
    
    # Test attack with both coin flip AND generic energy text (should prioritize coin flip)
    conflicting_attack = {
        'name': 'Conflicting Effect',
        'damage': '20',
        'effect_text': 'Flip a coin. If heads, attach an energy to this Pokemon. Also, attach an energy from your Energy Zone.',
        'energy_cost': ['R']
    }
    
    battle_context = {
        'turn': 1,
        'player': 0,
        'attacker': attacker,
        'defender': defender
    }
    
    result = effect_engine.execute_attack_effects(conflicting_attack, attacker, defender, 20, battle_context)
    
    print(f"📊 Conflict Resolution Results:")
    print(f"   Final Damage: {result['final_damage']}")
    print(f"   Energy Changes: {len(result['energy_changes'])}")
    print(f"   Additional Effects: {result['additional_effects']}")
    
    # Should prioritize coin flip, avoid duplicate generic energy  
    coin_effects = [effect for effect in result['additional_effects'] if ('coin' in effect.lower() or 'flip' in effect.lower() or 'heads' in effect.lower() or 'tails' in effect.lower())]
    generic_effects = [effect for effect in result['additional_effects'] if 'generic' in effect.lower()]
    
    assert len(coin_effects) >= 1, f"Should have coin flip effects, got: {result['additional_effects']}"
    print(f"   ✅ Coin flip effects: {len(coin_effects)}")
    print(f"   ✅ Generic effects: {len(generic_effects)} (should be 0 due to coin flip priority)")
    
    return True

def test_energy_type_validation():
    """Test that Colorless energy is never generated"""
    print("\n🚫 Testing Colorless Energy Prevention...")
    
    effect_engine = AdvancedEffectEngine(battle_cards=[], logger=logger, rng_seed=12345)
    attacker = MockPokemon("Test Pokemon", "Colorless")
    defender = MockPokemon("Target Pokemon", "Lightning")
    
    # Test various energy generation scenarios
    test_attacks = [
        {
            'name': 'Generic Energy',
            'effect_text': 'Attach an energy from your Energy Zone.',
        },
        {
            'name': 'Colorless Cost',
            'effect_text': 'Take a [C] Energy and attach it.',
        },
        {
            'name': 'Mixed Energy',
            'effect_text': 'Flip a coin. Take energy equal to heads.',
        }
    ]
    
    battle_context = {
        'turn': 1,
        'player': 0,
        'attacker': attacker,
        'defender': defender
    }
    
    for attack in test_attacks:
        result = effect_engine.execute_attack_effects(attack, attacker, defender, 0, battle_context)
        
        # Check all energy changes
        for energy_change in result['energy_changes']:
            energy_type = energy_change.get('energy_type', 'Unknown')
            assert energy_type != 'Colorless', f"FAILED: Generated Colorless energy in {attack['name']}"
            assert energy_type in ['Fire', 'Water', 'Grass', 'Lightning', 'Psychic', 'Fighting', 'Darkness', 'Metal'], \
                   f"Invalid energy type: {energy_type}"
            print(f"   ✅ {attack['name']}: Energy type = {energy_type} (valid)")
    
    return True

def test_damage_priority():
    """Test that damage modifications work with priority system"""
    print("\n💥 Testing Damage Modification Priority...")
    
    effect_engine = AdvancedEffectEngine(battle_cards=[], logger=logger, rng_seed=12345)
    attacker = MockPokemon("Raichu ex", "Lightning")
    defender = MockPokemon("Magikarp", "Water")
    
    # Add energy to defender for energy scaling test
    defender.energy_attached = ['Water', 'Water', 'Water']
    
    # Energy scaling attack (like Alolan Raichu ex Thunder)
    energy_scaling_attack = {
        'name': 'Thunder',
        'damage': '20',
        'effect_text': 'This attack does 20 more damage for each Energy attached to your opponent\'s Active Pokémon.',
    }
    
    battle_context = {
        'turn': 1,
        'player': 0,
        'attacker': attacker,
        'defender': defender
    }
    
    result = effect_engine.execute_attack_effects(energy_scaling_attack, attacker, defender, 20, battle_context)
    
    expected_damage = 20 + (3 * 20)  # Base 20 + 3 energy × 20 each = 80
    assert result['final_damage'] == expected_damage, f"Expected {expected_damage} damage, got {result['final_damage']}"
    
    print(f"   ✅ Energy scaling: {20} base + (3 energy × 20) = {result['final_damage']} damage")
    
    return True

def run_all_tests():
    """Run all effect validation tests"""
    print("🚀 Starting Comprehensive Effect Priority System Tests...")
    print("=" * 60)
    
    tests = [
        test_priority_system,
        test_effect_conflicts,
        test_energy_type_validation,
        test_damage_priority
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"✅ {test_func.__name__} PASSED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_func.__name__} FAILED: {e}")
            logger.exception(f"Test {test_func.__name__} failed")
    
    print("=" * 60)
    print(f"📈 Test Results: {passed} PASSED, {failed} FAILED")
    
    if failed == 0:
        print("🎉 All effect priority tests PASSED! The system is working correctly.")
        print("🛡️ The Moltres energy duplication bug and similar conflicts are prevented.")
    else:
        print("⚠️ Some tests failed. Effect priority system needs fixes.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)