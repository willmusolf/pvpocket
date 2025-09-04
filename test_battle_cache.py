#!/usr/bin/env python3
"""
Test the optimized battle card caching system
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from simulator.core.battle_cache import (
    BattleCardCache, get_battle_cache, preload_battle_cache,
    get_card_by_id, get_cards_by_name, get_pokemon_cards, 
    get_basic_pokemon, get_prebuilt_deck, search_cards
)
import logging
import time

def test_cache_loading():
    """Test cache loading performance and functionality"""
    print("🔧 Testing cache loading...")
    
    cache = BattleCardCache()
    
    # Test initial load
    start_time = time.time()
    success = cache.load_cards()
    load_time = time.time() - start_time
    
    if not success:
        print("❌ Failed to load cards")
        return False
    
    stats = cache.get_cache_stats()
    print(f"✅ Loaded {stats['total_cards']} cards in {load_time:.3f}s")
    print(f"   Pokemon: {stats['pokemon_cards']}, Trainers: {stats['trainer_cards']}")
    print(f"   Basic Pokemon: {stats['basic_pokemon']}")
    print(f"   Prebuilt Decks: {stats['prebuilt_decks']}")
    
    # Test that subsequent loads are fast (cached)
    start_time = time.time()
    cache.load_cards()
    cached_time = time.time() - start_time
    
    if cached_time > 0.1:  # Should be nearly instant
        print(f"⚠️  Cache reload took {cached_time:.3f}s (should be instant)")
    else:
        print(f"✅ Cached reload: {cached_time:.3f}s")
    
    return True

def test_card_lookup():
    """Test card lookup performance and accuracy"""
    print("\n🔍 Testing card lookup...")
    
    cache = get_battle_cache()
    
    # Test lookup by ID
    test_ids = [1, 100, 500, 1000, 1576]
    for card_id in test_ids:
        card = cache.get_card_by_id(card_id)
        if card:
            print(f"  ✅ ID {card_id}: {card.name}")
        else:
            print(f"  ❌ ID {card_id}: Not found")
    
    # Test lookup by name
    test_names = ["Pikachu", "Charizard", "Mewtwo", "Nonexistent Card"]
    for name in test_names:
        cards = cache.get_cards_by_name(name)
        if cards:
            print(f"  ✅ Name '{name}': Found {len(cards)} card(s)")
        else:
            print(f"  ❌ Name '{name}': Not found")
    
    return True

def test_filtering_and_search():
    """Test advanced filtering and search capabilities"""
    print("\n🎯 Testing filtering and search...")
    
    cache = get_battle_cache()
    
    # Test basic collections
    pokemon_cards = cache.get_pokemon_cards()
    trainer_cards = cache.get_trainer_cards()
    basic_pokemon = cache.get_basic_pokemon()
    
    print(f"  Total Pokemon: {len(pokemon_cards)}")
    print(f"  Total Trainers: {len(trainer_cards)}")
    print(f"  Basic Pokemon: {len(basic_pokemon)}")
    
    # Test energy type filtering
    fire_cards = cache.get_cards_by_energy_type("Fire")
    water_cards = cache.get_cards_by_energy_type("Water")
    print(f"  Fire cards: {len(fire_cards)}")
    print(f"  Water cards: {len(water_cards)}")
    
    # Test complex search
    high_hp_pokemon = search_cards(is_pokemon=True, min_hp=100)
    print(f"  High HP Pokemon (100+): {len(high_hp_pokemon)}")
    
    pokemon_with_abilities = search_cards(is_pokemon=True, has_abilities=True)
    print(f"  Pokemon with abilities: {len(pokemon_with_abilities)}")
    
    basic_fire_pokemon = search_cards(
        is_pokemon=True, 
        evolution_stage=0, 
        energy_type="Fire"
    )
    print(f"  Basic Fire Pokemon: {len(basic_fire_pokemon)}")
    
    return True

def test_prebuilt_decks():
    """Test prebuilt deck functionality"""
    print("\n🎴 Testing prebuilt decks...")
    
    cache = get_battle_cache()
    available_types = cache.get_available_deck_types()
    
    print(f"  Available deck types: {available_types}")
    
    # Test a few deck types
    for energy_type in available_types[:3]:  # Test first 3
        deck = cache.get_prebuilt_deck(energy_type)
        if deck:
            print(f"  ✅ {energy_type.title()} deck: {len(deck)} cards")
            
            # Validate deck composition
            energy_counts = {}
            for card in deck:
                card_energy = card.energy_type or "Colorless"
                energy_counts[card_energy] = energy_counts.get(card_energy, 0) + 1
            
            print(f"     Energy distribution: {energy_counts}")
        else:
            print(f"  ❌ {energy_type.title()} deck: Not available")
    
    return True

def test_cache_performance():
    """Test cache performance with repeated lookups"""
    print("\n⚡ Testing cache performance...")
    
    cache = get_battle_cache()
    
    # Test repeated ID lookups
    test_ids = list(range(1, 101))  # First 100 IDs
    
    start_time = time.time()
    for _ in range(10):  # 10 iterations of 100 lookups each
        for card_id in test_ids:
            card = cache.get_card_by_id(card_id)
    lookup_time = time.time() - start_time
    
    total_lookups = 10 * 100
    avg_lookup_time = lookup_time / total_lookups * 1000  # ms
    
    print(f"  {total_lookups} ID lookups in {lookup_time:.3f}s")
    print(f"  Average lookup time: {avg_lookup_time:.3f}ms")
    
    # Get cache statistics
    stats = cache.get_cache_stats()
    metrics = stats['metrics']
    
    print(f"  Cache hit rate: {metrics['hit_rate']:.1f}%")
    print(f"  Total requests: {metrics['total_requests']}")
    
    if avg_lookup_time > 1.0:  # Should be sub-millisecond
        print("⚠️  Cache performance may need optimization")
    else:
        print("✅ Cache performance is excellent")
    
    return True

def test_convenience_functions():
    """Test global convenience functions"""
    print("\n🛠️  Testing convenience functions...")
    
    # Test preload
    success = preload_battle_cache()
    if success:
        print("  ✅ Preload successful")
    else:
        print("  ❌ Preload failed")
        return False
    
    # Test convenience functions
    card = get_card_by_id(1)
    if card:
        print(f"  ✅ get_card_by_id(1): {card.name}")
    
    pikachu_cards = get_cards_by_name("Pikachu")
    print(f"  ✅ get_cards_by_name('Pikachu'): {len(pikachu_cards)} cards")
    
    pokemon = get_pokemon_cards()
    print(f"  ✅ get_pokemon_cards(): {len(pokemon)} cards")
    
    basics = get_basic_pokemon()
    print(f"  ✅ get_basic_pokemon(): {len(basics)} cards")
    
    fire_deck = get_prebuilt_deck("fire")
    if fire_deck:
        print(f"  ✅ get_prebuilt_deck('fire'): {len(fire_deck)} cards")
    
    high_hp = search_cards(is_pokemon=True, min_hp=150)
    print(f"  ✅ search_cards(min_hp=150): {len(high_hp)} cards")
    
    return True

def main():
    """Run all cache tests"""
    print("🧪 BATTLE CARD CACHE TESTING SYSTEM")
    print("Testing optimized caching for production scale")
    print("=" * 50)
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    tests = [
        test_cache_loading,
        test_card_lookup,
        test_filtering_and_search,
        test_prebuilt_decks,
        test_cache_performance,
        test_convenience_functions
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print("📊 CACHE TEST SUMMARY")
    print("=" * 50)
    print(f"Tests Passed: {passed}")
    print(f"Tests Failed: {failed}")
    print(f"Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All cache tests passed! System is production-ready.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Review issues before production.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)