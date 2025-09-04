# Battle Simulator Testing Cheat Sheet

Quick reference for testing the Pokemon TCG Pocket Battle Simulator.

## 🚀 Quick Tests (1-2 minutes)

```bash
# Feature validation (30 seconds)
python test_battle_features.py

# Single battle test (10 seconds)
python battle_main.py --battles 1 --debug --seed 42

# Web interface test
# Visit http://localhost:5001/battle-simulator → Click "Test Advanced"
```

## 🧪 Development Tests (5 minutes)

```bash
# Unit tests
python -m pytest simulator/tests/ -v

# Multiple battles
python battle_main.py --battles 5 --seed 42

# Fast integration test
./scripts/run_tests.sh fast
```

## 📊 Performance Tests

```bash
# Speed test (target: <100ms per battle)
time python battle_main.py --battles 100 --seed 42

# Memory test
python battle_main.py --battles 1000 --seed 42
```

## 🃏 Card Testing

### Web Interface
1. Go to `/battle-simulator`
2. Use "Card Ability Testing" section
3. Search for card → Select → Test

### Command Line
```bash
# Test specific card abilities
python -c "
from test_battle_features import BattleFeatureTester
tester = BattleFeatureTester()
# Add custom card testing here
"
```

## 🐛 Debug Commands

```bash
# Check card loading
python -c "from simulator.core.card_bridge import load_real_card_collection; print(f'Loaded {len(load_real_card_collection())} cards')"

# Debug battle with full logging
python battle_main.py --battles 1 --debug --log-level DEBUG --seed 42

# Profile performance
python -m cProfile battle_main.py --battles 10
```

## 🔧 API Testing

```bash
# Test card search
curl "http://localhost:5001/api/cards/search?q=pikachu&limit=5"

# Test abilities
curl "http://localhost:5001/api/test-abilities"

# Test features
curl "http://localhost:5001/api/test-features"

# Test battle
curl "http://localhost:5001/api/test-battle"
```

## ✅ Success Criteria

### Feature Tests
- ✅ Status conditions: 4/4 tests pass
- ✅ Coin flips: 5/5 tests pass  
- ✅ Trainer cards: 4/4 tests pass
- ✅ Evolution: 3/3 tests pass
- ✅ Effect engine: 3/3 tests pass
- **Target: 19/19 (100%)**

### Performance
- ✅ Battle speed: <100ms
- ✅ Memory usage: <50MB for 1000 battles
- ✅ No crashes in 100+ battles

### Integration
- ✅ Web interface loads
- ✅ Real cards load (>1000 cards)
- ✅ API endpoints respond
- ✅ No duplicate battle log entries

## 🚨 Common Issues

**"Failed to load real cards"**
```bash
# Check if Flask app is running on port 5001
curl http://localhost:5001/api/cards
```

**"Battle failed to start"**
```bash
# Test with sample cards
python battle_main.py --use-sample-cards --battles 1
```

**"Tests timing out"**
```bash
# Use smaller test sets
python battle_main.py --battles 1 --seed 42
```

## 📋 Testing Checklist

### Before Committing
- [ ] `python test_battle_features.py` → 19/19 pass
- [ ] `python battle_main.py --battles 1 --seed 42` → completes
- [ ] Web interface `/battle-simulator` → loads and works

### Before Deploying
- [ ] `./scripts/run_tests.sh fast` → all pass
- [ ] `python battle_main.py --battles 10` → <100ms avg
- [ ] Real cards load → >1000 cards
- [ ] Web interface fully functional

### After New Cards
- [ ] Card count increased → verify with API
- [ ] New abilities detected → test individually
- [ ] Performance maintained → run speed test

## 🔗 Related Docs

- [BATTLE_SIMULATOR_TESTING.md](BATTLE_SIMULATOR_TESTING.md) - Complete testing guide
- [battle_sim_design.md](battle_sim_design.md) - Architecture & design
- [battle_rules_db.md](battle_rules_db.md) - Data structures & rules
- [TESTING.md](TESTING.md) - General testing guidelines

---

*Quick reference for battle simulator testing. See BATTLE_SIMULATOR_TESTING.md for detailed procedures.*