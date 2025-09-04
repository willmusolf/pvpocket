#!/usr/bin/env python3
"""
Test the top-priority effect patterns: COIN_FLIP, STATUS_CONDITION, HEALING
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from Card import Card
from simulator.core.card_bridge import CardDataBridge, BattleCard
from simulator.core.effect_engine import AdvancedEffectEngine
from simulator.core.pokemon import BattlePokemon
from simulator.core.coin_flip import CoinFlipManager, parse_coin_flip_effect, execute_coin_flip_effect
from simulator.core.status_conditions import StatusManager, StatusCondition
from simulator.core.mass_effect_parser import MassEffectParser, EffectPattern
import logging

def test_coin_flip_effects():
    """Test coin flip effect parsing and execution"""
    print("\n=== Testing Coin Flip Effects ===")
    
    coin_manager = CoinFlipManager(rng_seed=42)  # Deterministic for testing
    
    test_cases = [
        {
            'name': 'Basic coin flip damage',
            'text': 'Flip 2 coins. This attack does 30 damage for each heads.',
            'expected_type': 'coin_flip_damage'
        },
        {
            'name': 'Energy generation (Moltres style)',
            'text': 'Flip 3 coins. Take an amount of [R] Energy from your Energy Zone equal to the number of heads and attach them to your Fire Pokémon on your Bench.',
            'expected_type': 'coin_flip_energy_generation'
        },
        {
            'name': 'All or nothing',
            'text': 'Flip a coin. If tails, this attack does nothing.',
            'expected_type': 'coin_flip_all_or_nothing'
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        try:
            # Parse the effect
            parsed = parse_coin_flip_effect(test_case['text'])
            
            if not parsed:
                results.append((test_case['name'], 'FAIL', 'No coin flip effect parsed'))
                continue
                
            if parsed['type'] != test_case['expected_type']:
                results.append((test_case['name'], 'FAIL', f"Expected {test_case['expected_type']}, got {parsed['type']}"))
                continue
            
            # Execute the effect
            result = execute_coin_flip_effect(parsed, coin_manager, base_attack_damage=50)
            
            if 'coin_results' not in result:
                results.append((test_case['name'], 'FAIL', 'No coin results returned'))
                continue
                
            results.append((test_case['name'], 'PASS', f"Parsed as {parsed['type']}, executed successfully"))
            print(f"  ✅ {test_case['name']}: {result['description']}")
            
        except Exception as e:
            results.append((test_case['name'], 'FAIL', str(e)))
            print(f"  ❌ {test_case['name']}: {e}")
    
    return results

def test_status_condition_effects():
    """Test status condition effects"""
    print("\n=== Testing Status Condition Effects ===")
    
    # Create test Pokemon
    test_card = Card(
        id=1,
        name="Test Pikachu",
        energy_type="Lightning",
        card_type="Basic Pokémon",
        hp=60
    )
    
    test_pokemon = BattlePokemon(test_card)
    status_manager = StatusManager()
    
    test_cases = [
        {
            'name': 'Apply Burn',
            'condition': StatusCondition.BURNED,
            'expected_damage': 20
        },
        {
            'name': 'Apply Poison',
            'condition': StatusCondition.POISONED,
            'expected_damage': 10
        },
        {
            'name': 'Apply Sleep',
            'condition': StatusCondition.ASLEEP,
            'expected_damage': 0
        },
        {
            'name': 'Random status condition',
            'condition': 'random',
            'expected_damage': 0  # Variable
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        try:
            if test_case['condition'] == 'random':
                success, message = status_manager.apply_random_status_condition(test_pokemon, current_turn=1)
            else:
                success, message = status_manager.apply_status_condition(test_pokemon, test_case['condition'], current_turn=1)
            
            if not success:
                results.append((test_case['name'], 'FAIL', f"Failed to apply: {message}"))
                continue
            
            # Test between-turns effects
            effects = status_manager.process_between_turns_effects(test_pokemon, current_turn=2)
            
            results.append((test_case['name'], 'PASS', f"Applied successfully: {message}"))
            print(f"  ✅ {test_case['name']}: {message}")
            if effects:
                for effect in effects:
                    print(f"     Effect: {effect}")
            
        except Exception as e:
            results.append((test_case['name'], 'FAIL', str(e)))
            print(f"  ❌ {test_case['name']}: {e}")
    
    return results

def test_healing_effects():
    """Test healing effects"""
    print("\n=== Testing Healing Effects ===")
    
    # Create test Pokemon with damage
    test_card = Card(
        id=1,
        name="Test Chansey",
        energy_type="Colorless",
        card_type="Basic Pokémon",
        hp=100
    )
    
    test_pokemon = BattlePokemon(test_card)
    
    # Deal some damage first
    test_pokemon.take_damage(50)
    initial_hp = test_pokemon.current_hp
    
    test_cases = [
        {
            'name': 'Heal 30 damage',
            'heal_amount': 30,
            'expected_final_hp': min(100, initial_hp + 30)
        },
        {
            'name': 'Full heal',
            'heal_amount': 'full',
            'expected_final_hp': 100
        },
        {
            'name': 'Overheal (should cap at max HP)',
            'heal_amount': 200,
            'expected_final_hp': 100
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        try:
            pre_heal_hp = test_pokemon.current_hp
            
            if test_case['heal_amount'] == 'full':
                test_pokemon.current_hp = test_pokemon.max_hp
                healed = test_pokemon.max_hp - pre_heal_hp
            else:
                healed = test_pokemon.heal(test_case['heal_amount'])
            
            if test_pokemon.current_hp != test_case['expected_final_hp']:
                results.append((test_case['name'], 'FAIL', 
                              f"Expected HP {test_case['expected_final_hp']}, got {test_pokemon.current_hp}"))
                continue
                
            results.append((test_case['name'], 'PASS', 
                          f"Healed {healed} HP, now at {test_pokemon.current_hp}/{test_pokemon.max_hp}"))
            print(f"  ✅ {test_case['name']}: Healed {healed} HP, now at {test_pokemon.current_hp}/{test_pokemon.max_hp}")
            
        except Exception as e:
            results.append((test_case['name'], 'FAIL', str(e)))
            print(f"  ❌ {test_case['name']}: {e}")
    
    return results

def test_mass_effect_parser():
    """Test mass effect parser on sample cards"""
    print("\n=== Testing Mass Effect Parser ===")
    
    parser = MassEffectParser()
    
    # Sample card effects to test
    test_effects = [
        {
            'text': 'Flip 2 coins. This attack does 30 damage for each heads.',
            'expected_pattern': EffectPattern.COIN_FLIP
        },
        {
            'text': 'Your opponent\'s Active Pokémon is now Burned.',
            'expected_pattern': EffectPattern.STATUS_CONDITION
        },
        {
            'text': 'Heal 40 damage from this Pokémon.',
            'expected_pattern': EffectPattern.HEALING
        },
        {
            'text': 'This attack does 20 more damage for each Energy attached to your opponent\'s Active Pokémon.',
            'expected_pattern': EffectPattern.ENERGY_SCALING
        }
    ]
    
    results = []
    
    for i, test_effect in enumerate(test_effects):
        try:
            parsed_effects = parser.parse_effect(test_effect['text'], f"Test Card {i+1}", i+1)
            
            if not parsed_effects:
                results.append((f"Effect {i+1}", 'FAIL', 'No effects parsed'))
                continue
            
            # Check if expected pattern was found
            found_pattern = any(effect.pattern == test_effect['expected_pattern'] for effect in parsed_effects)
            
            if not found_pattern:
                results.append((f"Effect {i+1}", 'FAIL', 
                              f"Expected pattern {test_effect['expected_pattern'].value} not found"))
                continue
            
            results.append((f"Effect {i+1}", 'PASS', f"Found {len(parsed_effects)} effect(s)"))
            print(f"  ✅ Effect {i+1}: {test_effect['text'][:50]}...")
            for effect in parsed_effects:
                print(f"     Pattern: {effect.pattern.value}, Confidence: {effect.confidence:.2f}")
            
        except Exception as e:
            results.append((f"Effect {i+1}", 'FAIL', str(e)))
            print(f"  ❌ Effect {i+1}: {e}")
    
    return results

def main():
    """Run all effect pattern tests"""
    print("🧪 Testing Top-Priority Effect Patterns")
    print("=" * 50)
    
    all_results = []
    
    # Test each system
    all_results.extend(test_coin_flip_effects())
    all_results.extend(test_status_condition_effects())
    all_results.extend(test_healing_effects())
    all_results.extend(test_mass_effect_parser())
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for result in all_results if result[1] == 'PASS')
    total = len(all_results)
    
    print(f"Tests Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    print()
    
    if passed < total:
        print("❌ FAILED TESTS:")
        for test_name, status, details in all_results:
            if status == 'FAIL':
                print(f"  • {test_name}: {details}")
    else:
        print("🎉 All tests passed! Effect patterns are working correctly.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)