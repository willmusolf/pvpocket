# Battle Simulator Testing Documentation

## Overview

This document provides comprehensive testing guidelines and procedures for the Pokemon TCG Pocket Battle Simulator. It covers testing strategies, validation procedures, and troubleshooting workflows specifically designed for the battle engine.

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Categories](#test-categories)
3. [Quick Testing Procedures](#quick-testing-procedures)
4. [Comprehensive Testing Workflows](#comprehensive-testing-workflows)
5. [Card Ability Testing](#card-ability-testing)
6. [Performance Testing](#performance-testing)
7. [Integration Testing](#integration-testing)
8. [Debugging & Troubleshooting](#debugging--troubleshooting)
9. [Test Data Management](#test-data-management)
10. [Continuous Testing](#continuous-testing)

---

## Testing Philosophy

The battle simulator testing follows these core principles:

### 🎯 **Test-Driven Validation**
- Every card ability must have corresponding tests
- All game mechanics must be validated before deployment
- Regression testing prevents breaking existing functionality

### ⚡ **Performance-First**
- Battles must complete in <100ms for AI training compatibility
- Memory usage must remain efficient during extended testing
- No memory leaks during repeated battle execution

### 🔄 **Reproducible Results**
- All tests use deterministic seeds for consistent results
- Battle outcomes must be reproducible given the same inputs
- Debug information must be comprehensive and actionable

---

## Test Categories

### 1. Unit Tests (`simulator/tests/`)

**Core Mechanics Testing:**
- ✅ Energy attachment rules
- ✅ Attack damage calculation
- ✅ Pokemon knockout detection
- ✅ Prize point awarding (including EX Pokemon)
- ✅ Turn progression and phase management

**Command to run:**
```bash
python -m pytest simulator/tests/ -v
```

### 2. Feature Tests (`test_battle_features.py`)

**Advanced Features Testing:**
- ✅ Status conditions (burn, poison, paralysis, sleep)
- ✅ Coin flip mechanics and randomness
- ✅ Trainer card rules and limitations
- ✅ Evolution system and validation
- ✅ Effect engine coordination

**Command to run:**
```bash
python test_battle_features.py
```

### 3. Integration Tests

**Full Battle Testing:**
- Complete AI vs AI battles
- Real card data integration
- Web interface functionality
- API endpoint validation

**Command to run:**
```bash
python battle_main.py --battles 1 --debug --seed 42
```

---

## Quick Testing Procedures

### 🚀 **5-Minute Smoke Test**

Run this before any development session:

```bash
# 1. Verify basic functionality
python test_battle_features.py

# 2. Run a quick battle
python battle_main.py --battles 1 --seed 42

# 3. Check web interface
# Navigate to http://localhost:5001/battle-simulator
# Click "Test Advanced" button
```

**Expected Results:**
- ✅ All feature tests pass (19/19 - 100%)
- ✅ Battle completes without errors
- ✅ Web interface loads and shows test results

### ⚡ **10-Minute Development Test**

Run this after making changes:

```bash
# 1. Run unit tests
python -m pytest simulator/tests/ -v

# 2. Run feature validation
python test_battle_features.py

# 3. Test multiple battles
python battle_main.py --battles 5 --seed 42

# 4. Test web interface thoroughly
# Use the Card Ability Testing section to test specific cards
```

---

## Comprehensive Testing Workflows

### 🔍 **Pre-Deployment Validation**

**Full Test Suite (15-20 minutes):**

```bash
# 1. All unit tests
python -m pytest simulator/tests/ -v --cov=simulator

# 2. Feature validation
python test_battle_features.py

# 3. Performance testing
python battle_main.py --battles 50 --seed 42

# 4. Integration testing
./scripts/run_tests.sh fast

# 5. Real card validation
python battle_main.py --battles 10 --deck1 fire --deck2 water --seed 42
```

**Success Criteria:**
- ✅ 100% unit test pass rate
- ✅ 100% feature test pass rate
- ✅ Average battle time <100ms
- ✅ No memory leaks in 50+ battles
- ✅ Web interface fully functional

### 🎯 **Card Release Validation**

When new cards are added to the database:

```bash
# 1. Verify card import
python -c "from simulator.core.card_bridge import load_real_card_collection; cards = load_real_card_collection(); print(f'Loaded {len(cards)} cards')"

# 2. Test with new cards
python battle_main.py --battles 10 --use-real-cards

# 3. Ability-specific testing
# Use web interface Card Ability Testing to test new cards individually

# 4. Effect parsing validation
python test_battle_features.py
```

---

## Card Ability Testing

### 🃏 **Individual Card Testing**

**Web Interface Method:**
1. Navigate to `/battle-simulator`
2. Use "Card Ability Testing" section
3. Search for specific card by name
4. Click "Test Selected Card"
5. Review ability detection results

**Command Line Method:**
```python
# Example: Test Charizard ex abilities
from test_battle_features import BattleFeatureTester
from simulator.core.card_bridge import load_real_card_collection

cards = load_real_card_collection()
charizard = next(card for card in cards if 'charizard ex' in card.name.lower())

# Test specific abilities
tester = BattleFeatureTester()
results = tester.test_single_card_abilities(charizard)
```

### 🔧 **Ability Categories**

**Status Effects:**
- Cards with burn, poison, paralysis, sleep effects
- Test effect application and duration
- Verify damage-over-time mechanics

**Coin Flips:**
- Cards with randomized effects
- Test statistical distribution over multiple runs
- Verify damage scaling with flip results

**Energy Manipulation:**
- Cards that attach, remove, or modify energy
- Test energy type constraints
- Verify turn-based energy limits

**Damage Modifiers:**
- Cards with weakness/resistance effects
- Test damage calculation accuracy
- Verify conditional damage bonuses

---

## Performance Testing

### ⚡ **Speed Benchmarks**

**Target Metrics:**
- Single battle: <100ms
- 100 battles: <10 seconds
- Memory usage: <50MB for 1000 battles

**Testing Commands:**
```bash
# Speed test
time python battle_main.py --battles 100 --seed 42

# Memory test (requires memory_profiler)
mprof run python battle_main.py --battles 1000 --seed 42
mprof plot
```

### 📊 **Performance Validation**

```python
import time
from battle_main import run_single_battle, create_sample_card_collection, create_sample_deck

collection = create_sample_card_collection()
deck1 = create_sample_deck(collection, "fire")
deck2 = create_sample_deck(collection, "water")

# Time 100 battles
start_time = time.time()
for i in range(100):
    result = run_single_battle(deck1, deck2, rng_seed=42+i)
    if not result:
        print(f"Battle {i} failed")
        break
        
total_time = time.time() - start_time
avg_time = total_time / 100

print(f"Average battle time: {avg_time*1000:.1f}ms")
assert avg_time < 0.1, f"Battles too slow: {avg_time*1000:.1f}ms"
```

---

## Integration Testing

### 🌐 **Web Interface Testing**

**Manual Test Checklist:**
- [ ] Battle simulator page loads without errors
- [ ] "Test Advanced" button executes successfully
- [ ] Card search functionality works
- [ ] Individual card testing displays results
- [ ] Feature tests run and show detailed results
- [ ] Battle log displays properly (no duplicates)

**API Endpoint Testing:**
```bash
# Test card search
curl "http://localhost:5001/api/cards/search?q=char&limit=5"

# Test ability validation
curl "http://localhost:5001/api/test-abilities"

# Test feature validation
curl "http://localhost:5001/api/test-features"

# Test battle execution
curl "http://localhost:5001/api/test-battle"
```

### 🔗 **Database Integration**

**Real Card Loading:**
```python
from simulator.core.card_bridge import load_real_card_collection

# Verify card loading
cards = load_real_card_collection()
assert len(cards) > 1000, f"Expected >1000 cards, got {len(cards)}"

# Verify card data quality
for card in cards[:10]:
    assert card.name, "Card missing name"
    assert card.card_type, "Card missing type"
    if 'Pokémon' in card.card_type:
        assert card.hp and card.hp > 0, f"Pokemon {card.name} missing HP"
```

---

## Debugging & Troubleshooting

### 🐛 **Common Issues & Solutions**

**Battle Fails to Start:**
```bash
# Check card loading
python -c "from simulator.core.card_bridge import load_real_card_collection; print(len(load_real_card_collection()))"

# Check deck creation
python -c "from battle_main import create_real_card_collection, create_real_card_deck; cards = create_real_card_collection(); deck = create_real_card_deck(cards, 'fire'); print(f'Deck has {len(deck.cards)} cards')"
```

**Effects Not Working:**
```bash
# Test effect engine
python test_battle_features.py | grep -A 5 "effect_engine"

# Debug specific card
python -c "from test_battle_features import BattleFeatureTester; tester = BattleFeatureTester(); tester.test_effect_engine_integration()"
```

**Performance Issues:**
```bash
# Profile slow battles
python -m cProfile -o battle_profile.stats battle_main.py --battles 10
python -c "import pstats; pstats.Stats('battle_profile.stats').sort_stats('cumulative').print_stats(20)"
```

### 📝 **Debug Logging**

**Enable Detailed Logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run battle with full debug output
python battle_main.py --battles 1 --debug --log-level DEBUG
```

---

## Test Data Management

### 📋 **Test Card Sets**

**Sample Cards (for testing):**
- Basic Pokemon with simple attacks
- EX Pokemon for prize point testing  
- Cards with status effects
- Cards with coin flip mechanics
- Trainer cards for rule testing

**Real Cards (production data):**
- Full card database from Limitless TCG
- Updated nightly via scraping pipeline
- Validated for battle compatibility

### 🎲 **Seed Management**

**Reproducible Testing:**
```python
# Use consistent seeds for regression testing
REGRESSION_SEED = 42
PERFORMANCE_SEED = 12345
RANDOMNESS_SEED = None  # For true randomness testing
```

**Seed-based Test Scenarios:**
- Seed 42: Standard regression test scenario
- Seed 12345: Performance benchmark scenario  
- Seed 999: Edge case testing scenario

---

## Continuous Testing

### 🔄 **Automated Testing Pipeline**

**Pre-commit Hooks:**
```bash
#!/bin/sh
# .git/hooks/pre-commit
python test_battle_features.py
if [ $? -ne 0 ]; then
    echo "Battle feature tests failed!"
    exit 1
fi
```

**CI/CD Integration:**
```yaml
# .github/workflows/battle_tests.yml
- name: Run Battle Tests
  run: |
    python test_battle_features.py
    python battle_main.py --battles 5 --seed 42
    python -m pytest simulator/tests/ -v
```

### 📊 **Test Metrics Tracking**

**Key Metrics to Monitor:**
- Feature test pass rate (target: 100%)
- Average battle duration (target: <100ms)
- Memory usage per battle (target: <1MB)
- Card ability coverage (target: >90%)

**Monitoring Commands:**
```bash
# Generate test report
python test_battle_features.py > test_report.txt
python battle_main.py --battles 100 --seed 42 2>&1 | grep "duration"
```

---

## Conclusion

This testing framework ensures the battle simulator maintains high quality and performance standards. Regular execution of these test procedures will:

- ✅ Prevent regressions in core functionality
- ✅ Validate new card abilities and effects
- ✅ Maintain performance targets for AI training
- ✅ Ensure consistent behavior across environments

For questions or issues with testing procedures, refer to the battle simulator development team or create an issue in the project repository.

---

*Last Updated: 2025-08-20*  
*Version: 1.0*  
*Maintained by: Battle Simulator Development Team*