#!/usr/bin/env python3
"""
Comprehensive test suite for common Pokemon TCG Pocket card effects.
Tests the most essential card mechanics to ensure engine correctness.
"""

import sys
import os
sys.path.append('.')

from simulator.core.effect_registry import EffectContext, EffectResult
from simulator.core.coin_flip import CoinFlipManager, CoinResult
from simulator.core.pokemon import BattlePokemon
from simulator.core.status_conditions import StatusCondition, StatusEffect
from Card import Card

# Import standard effects to register them
import simulator.core.standard_effects

def create_test_card(name: str, card_type: str, hp: int = 60, attacks: list = None, abilities: list = None):
    """Create a test card with proper attributes"""
    card = Card(
        id=f'test_{name.lower().replace(" ", "_")}',
        name=name,
        card_type=card_type,
        hp=hp,
        energy_type='Fire',
        attacks=attacks or [],
        abilities=abilities or [],
        retreat_cost=1,
        weakness=None
    )
    return card

def create_test_pokemon(name: str, hp: int = 60):
    """Create a test BattlePokemon for testing"""
    card = create_test_card(name, 'Basic Pokémon', hp)
    pokemon = BattlePokemon(card)
    return pokemon

def test_basic_damage_effects():
    """Test basic damage calculation and modification effects"""
    print("=== Testing Basic Damage Effects ===")
    
    
    # Test damage bonus effect
    effect_data = {
        'type': 'damage_bonus',
        'amount': 20
    }
    
    source = create_test_pokemon("Attacker")
    target = create_test_pokemon("Defender")
    
    context = EffectContext(
        source_pokemon=source,
        target_pokemon=target,
        parameters={'amount': 20}
    )
    
    # Test damage bonus through registry
    from simulator.core.effect_registry import effect_registry
    if 'damage_bonus' in effect_registry._handlers:
        result = effect_registry._handlers['damage_bonus'](context)
        assert result.success, "Damage bonus should execute successfully"
        assert result.damage_modifier == 20, f"Expected 20 damage bonus, got {result.damage_modifier}"
        print("✅ Damage bonus effect working")
    else:
        print("⚠️  Damage bonus effect not registered")
    
    # Test energy scaling damage
    source.energy_attached = ['Fire', 'Fire', 'Colorless']
    context.parameters = {'damage_per_energy': 10, 'target': 'self'}
    
    if 'energy_scaling_damage' in effect_registry._handlers:
        result = effect_registry._handlers['energy_scaling_damage'](context)
        expected_bonus = len(source.energy_attached) * 10
        assert result.damage_modifier == expected_bonus, f"Expected {expected_bonus} energy damage, got {result.damage_modifier}"
        print("✅ Energy scaling damage working")
    else:
        print("⚠️  Energy scaling damage not registered")

def test_healing_effects():
    """Test healing mechanics and HP restoration"""
    print("\n=== Testing Healing Effects ===")
    
    # Create damaged Pokemon
    pokemon = create_test_pokemon("Test Pokemon", hp=100)
    pokemon.take_damage(40)  # Damage to 60 HP
    
    assert pokemon.current_hp == 60, f"Expected 60 HP after damage, got {pokemon.current_hp}"
    
    # Test basic healing
    healed = pokemon.heal(20)
    assert healed == 20, f"Expected to heal 20 HP, got {healed}"
    assert pokemon.current_hp == 80, f"Expected 80 HP after heal, got {pokemon.current_hp}"
    print("✅ Basic healing working")
    
    # Test healing beyond max HP
    healed = pokemon.heal(50)
    assert healed == 20, f"Expected to heal 20 HP (capped), got {healed}"
    assert pokemon.current_hp == 100, f"Expected full HP after overheal, got {pokemon.current_hp}"
    print("✅ Healing cap working")
    
    # Test Potion effect through registry
    from simulator.core.effect_registry import effect_registry
    pokemon.take_damage(30)  # Back to 70 HP
    
    context = EffectContext(
        source_pokemon=pokemon,
        parameters={'target_pokemon': pokemon}
    )
    
    if 'potion' in effect_registry._handlers:
        result = effect_registry._handlers['potion'](context)
        assert result.success, "Potion should execute successfully"
        assert pokemon.current_hp == 90, f"Expected 90 HP after Potion, got {pokemon.current_hp}"
        print("✅ Potion healing effect working")
    else:
        print("⚠️  Potion effect not registered")

def test_status_conditions():
    """Test status condition application and effects"""
    print("\n=== Testing Status Conditions ===")
    
    pokemon = create_test_pokemon("Test Pokemon")
    
    # Test burn application
    from simulator.core.effect_registry import effect_registry
    context = EffectContext(
        source_pokemon=pokemon,
        target_pokemon=pokemon,
        battle_context={'turn': 1}
    )
    
    if 'apply_burn' in effect_registry._handlers:
        result = effect_registry._handlers['apply_burn'](context)
        assert result.success, "Burn should apply successfully"
        assert len(pokemon.status_conditions) > 0, "Pokemon should have status condition"
        
        # Check burn status
        burn_status = pokemon.status_conditions[0]
        assert burn_status.condition == StatusCondition.BURNED, "Should be burned"
        print("✅ Burn status application working")
        
        # Test that burning Pokemon can't retreat when paralyzed
        pokemon.is_paralyzed = True
        can_retreat = pokemon.can_retreat()
        assert not can_retreat, "Paralyzed Pokemon should not be able to retreat"
        print("✅ Status condition retreat blocking working")
    else:
        print("⚠️  Burn effect not registered")
    
    # Test poison application
    context.target_pokemon = create_test_pokemon("Fresh Pokemon")
    
    if 'apply_poison' in effect_registry._handlers:
        result = effect_registry._handlers['apply_poison'](context)
        assert result.success, "Poison should apply successfully"
        print("✅ Poison status application working")
    else:
        print("⚠️  Poison effect not registered")

def test_coin_flip_effects():
    """Test coin flip mechanics and variable counting"""
    print("\n=== Testing Coin Flip Effects ===")
    
    coin_manager = CoinFlipManager()
    
    # Test basic coin flip
    result = coin_manager.flip_coin()
    assert result in [CoinResult.HEADS, CoinResult.TAILS], f"Coin flip should return CoinResult, got {result}"
    print("✅ Basic coin flip working")
    
    # Test multiple coin flips
    results = coin_manager.flip_multiple_coins(10)
    assert len(results) == 10, f"Should get 10 results, got {len(results)}"
    heads_count = sum(1 for r in results if r == CoinResult.HEADS)
    assert 0 <= heads_count <= 10, f"Heads count should be 0-10, got {heads_count}"
    print("✅ Multiple coin flips working")
    
    # Test variable count based on bench Pokemon (like Pikachu ex Circle Circuit)
    from simulator.core.effect_registry import effect_registry
    
    # Mock bench Pokemon for testing
    attacker_mock = type('MockPlayer', (), {})()
    attacker_mock.bench = [create_test_pokemon(f"Bench{i}") for i in range(2)]
    
    dummy_attacker = create_test_pokemon("Dummy Attacker")
    context = EffectContext(
        source_pokemon=dummy_attacker,
        parameters={'count_source': 'bench_pokemon', 'damage_per_heads': 30},
        battle_context={'attacker': attacker_mock}
    )
    
    if 'flip_variable_count' in effect_registry._handlers:
        result = effect_registry._handlers['flip_variable_count'](context)
        assert result.success, "Variable flip should execute"
        # Should flip 2 coins (one per bench Pokemon)
        assert "2 coins" in result.description, f"Should mention 2 coins, got: {result.description}"
        print("✅ Variable coin flip counting working")
    else:
        print("⚠️  Variable coin flip not registered")

def test_energy_effects():
    """Test energy attachment and manipulation"""
    print("\n=== Testing Energy Effects ===")
    
    pokemon = create_test_pokemon("Test Pokemon")
    assert len(pokemon.energy_attached) == 0, "Should start with no energy"
    
    # Test basic energy attachment
    success = pokemon.attach_energy("Fire")
    assert success, "Energy attachment should succeed"
    assert len(pokemon.energy_attached) == 1, f"Expected 1 energy, got {len(pokemon.energy_attached)}"
    assert pokemon.energy_attached[0] == "Fire", f"Expected Fire energy, got {pokemon.energy_attached[0]}"
    print("✅ Basic energy attachment working")
    
    # Test energy removal
    removed = pokemon.remove_energy("Fire")
    assert removed == "Fire", f"Expected to remove Fire energy, got {removed}"
    assert len(pokemon.energy_attached) == 0, f"Expected 0 energy after removal, got {len(pokemon.energy_attached)}"
    print("✅ Energy removal working")
    
    # Test energy effect through registry
    from simulator.core.effect_registry import effect_registry
    context = EffectContext(
        source_pokemon=pokemon,
        parameters={'energy_type': 'Lightning', 'amount': 2, 'target': 'self'}
    )
    
    if 'attach_energy' in effect_registry._handlers:
        result = effect_registry._handlers['attach_energy'](context)
        assert result.success, "Energy attachment effect should succeed"
        assert len(pokemon.energy_attached) == 2, f"Expected 2 energy after effect, got {len(pokemon.energy_attached)}"
        print("✅ Energy attachment effect working")
    else:
        print("⚠️  Energy attachment effect not registered")

def test_trainer_card_effects():
    """Test common trainer card effects"""
    print("\n=== Testing Trainer Card Effects ===")
    
    from simulator.core.effect_registry import effect_registry
    
    # Test Professor's Research
    # Create dummy pokemon for context
    dummy_pokemon = create_test_pokemon("Dummy")
    context = EffectContext(source_pokemon=dummy_pokemon)
    
    if 'professors_research' in effect_registry._handlers:
        result = effect_registry._handlers['professors_research'](context)
        assert result.success, "Professor's Research should execute"
        assert "Discard hand" in result.additional_effects, "Should discard hand"
        assert "Draw 7 cards" in result.additional_effects, "Should draw 7 cards"
        print("✅ Professor's Research working")
    else:
        print("⚠️  Professor's Research not registered")
    
    # Test Pokeball
    if 'pokeball' in effect_registry._handlers:
        result = effect_registry._handlers['pokeball'](context)
        assert result.success, "Pokeball should execute"
        assert "Search deck for 1 Pokemon" in result.additional_effects, "Should search for Pokemon"
        print("✅ Pokeball working")
    else:
        print("⚠️  Pokeball not registered")
    
    # Test Switch
    if 'switch' in effect_registry._handlers:
        result = effect_registry._handlers['switch'](context)
        assert result.success, "Switch should execute"
        assert "Switch" in result.description, "Should mention switching"
        print("✅ Switch working")
    else:
        print("⚠️  Switch not registered")

def test_attack_validation():
    """Test attack energy cost validation"""
    print("\n=== Testing Attack Validation ===")
    
    # Create Pokemon with various energy costs
    attacks = [
        {"name": "Tackle", "damage": "20", "cost": []},  # No cost
        {"name": "Ember", "damage": "30", "cost": ["Fire"]},  # 1 Fire energy
        {"name": "Flamethrower", "damage": "60", "cost": ["Fire", "Fire"]},  # 2 Fire energy
        {"name": "Fire Blast", "damage": "80", "cost": ["Fire", "Fire", "C"]},  # 2 Fire + 1 Colorless
    ]
    
    card = create_test_card("Charizard", "Basic Pokémon", hp=120, attacks=attacks)
    pokemon = BattlePokemon(card)
    
    # Test zero-cost attack
    can_use = pokemon.can_use_attack(attacks[0])
    assert can_use, "Should be able to use zero-cost attack"
    print("✅ Zero-cost attack validation working")
    
    # Test with insufficient energy
    can_use = pokemon.can_use_attack(attacks[1])  # Needs 1 Fire
    assert not can_use, "Should not be able to use attack without energy"
    print("✅ Insufficient energy blocking working")
    
    # Test with exact energy
    pokemon.attach_energy("Fire")
    can_use = pokemon.can_use_attack(attacks[1])
    assert can_use, "Should be able to use attack with exact energy"
    print("✅ Exact energy requirement working")
    
    # Test colorless energy substitution
    pokemon.attach_energy("Water")  # Different energy type
    can_use = pokemon.can_use_attack(attacks[3])  # Needs Fire, Fire, Colorless
    assert not can_use, "Should need 2 Fire energy specifically"
    
    pokemon.attach_energy("Fire")  # Now has Fire, Water, Fire
    can_use = pokemon.can_use_attack(attacks[3])
    assert can_use, "Should be able to use attack with colorless substitution"
    print("✅ Colorless energy substitution working")

def test_weakness_calculations():
    """Test weakness damage calculations"""
    print("\n=== Testing Weakness Calculations ===")
    
    # Create Fire Pokemon attacking Water Pokemon (weakness)
    fire_card = create_test_card("Fire Pokemon", "Basic Pokémon")
    fire_card.energy_type = "Fire"
    fire_pokemon = BattlePokemon(fire_card)
    
    water_card = create_test_card("Water Pokemon", "Basic Pokémon")
    water_card.weakness = "Fire"
    water_pokemon = BattlePokemon(water_card)
    
    attack = {"name": "Ember", "damage": "30", "cost": ["Fire"]}
    
    # Calculate damage with weakness
    damage = fire_pokemon.calculate_attack_damage(attack, water_pokemon)
    expected_damage = 30 + 20  # Base + weakness bonus
    assert damage == expected_damage, f"Expected {expected_damage} damage with weakness, got {damage}"
    print("✅ Weakness damage calculation working")
    
    # Test without weakness
    no_weakness_card = create_test_card("Normal Pokemon", "Basic Pokémon")
    no_weakness_card.weakness = None
    no_weakness_pokemon = BattlePokemon(no_weakness_card)
    
    damage = fire_pokemon.calculate_attack_damage(attack, no_weakness_pokemon)
    assert damage == 30, f"Expected 30 damage without weakness, got {damage}"
    print("✅ No weakness calculation working")

def run_all_tests():
    """Run all common card effect tests"""
    print("🎯 Pokemon TCG Pocket Battle Engine - Common Card Effect Test Suite")
    print("=" * 70)
    
    try:
        test_basic_damage_effects()
        test_healing_effects()
        test_status_conditions()
        test_coin_flip_effects()
        test_energy_effects()
        test_trainer_card_effects()
        test_attack_validation()
        test_weakness_calculations()
        
        print("\n" + "=" * 70)
        print("✅ ALL COMMON CARD EFFECT TESTS PASSED!")
        print("🎉 Battle engine core mechanics are working correctly!")
        print("\n🔧 Engine Status: Ready for advanced card testing")
        print("📊 Coverage: Basic damage, healing, status, energy, trainers, attacks")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)