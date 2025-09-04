# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 CRITICAL: Testing & Code Quality Requirements

### ⚠️ MANDATORY: Test Before AND After Changes
**YOU MUST ALWAYS:**
1. Run tests AFTER making changes to verify nothing broke
2. If tests fail, tell user
3. Never commit code with failing tests

```bash
# After making changes:
./scripts/run_tests.sh fast  # Verify nothing broke

# Before major changes or deployment:
./scripts/run_tests.sh pre-prod  # Full validation
```

### 🤔 MANDATORY: Ask Before Significant Changes
**ALWAYS ask for clarification when:**
- Making architectural changes or adding new features
- Modifying authentication, security, or admin functionality
- Changing database schema or Firebase collections
- Unclear about requirements or implementation approach
- Impact affects multiple files or core systems

### 📝 Code Simplicity & Quality Rules
**ALWAYS write simple, maintainable code:**
- **Prefer simple over clever**
- **Follow existing patterns** - Look at similar code in the project first
- **Add error handling** - Every external call needs try/except
- **Use descriptive names** - `user_decks` not `ud`, `card_collection` not `cc`
- **Keep functions small** - If it's over 20 lines, split it up
- **Document complex logic** - Add comments only where necessary

### 🛡️ Error Handling Requirements
**EVERY piece of code must handle errors gracefully:**
```python
# ✅ GOOD - Proper error handling
try:
    cards = db.collection('cards').get()
    return [card.to_dict() for card in cards]
except Exception as e:
    app.logger.error(f"Failed to fetch cards: {e}")
    return []  # Return safe default

# ❌ BAD - No error handling
cards = db.collection('cards').get()  # Could crash the app!
return [card.to_dict() for card in cards]
```

## 🎯 Quick Start

**Pokemon TCG Pocket app** running on Google Cloud with automated testing & deployment.

**Key URLs:**
- **Production**: https://pvpocket.xyz  
- **Test**: https://test-env-dot-pvpocket-dd286.uc.r.appspot.com
- **Local Flask**: http://localhost:5002  
- **Local React Dev**: http://localhost:5173

**Daily Development:**
```bash
PORT=5002 python3 run.py  # Run Flask backend locally (port 5002)
./scripts/run_tests.sh fast  # Test after changes

# React UI Development (Current Phase)  
cd frontend && npm run dev  # Run React development server (port 5173)
```

## 🚀 Deployment & Architecture

**Automated Deployment:**
- Push to `main` → Production deploy  
- Push to `development` → Test environment deploy
- All secrets in Google Secret Manager (NEVER in code)
- **🧹 AUTO-CLEANUP**: Old App Engine versions automatically deleted after deployment

**💰 COST CONTROL (CRITICAL):**
- **Scheduler jobs ACTIVE** (re-enabled for automatic card scraping)
- **Auto version cleanup** prevents App Engine version buildup
- **Manual cleanup script**: `./scripts/cleanup_app_versions.sh`
- **Cost monitoring**: `/internal/firestore-usage`
- **Target cost**: <$0.15/day (includes minimal networking for scraping)

**Firebase Emulator:**
- Local dev uses emulator with production data mirror (FREE)
- Tests use emulator with test data (FREE)
- Auto-starts with `python run.py`

**Performance Optimizations:**
- Extended cache TTLs, client-side filtering, connection pooling

See `DEPLOYMENT_GUIDE.md` for detailed deployment instructions.

## ⚛️ React UI Development (Current Phase)

**Current Focus**: Building interactive React battle simulator for visual engine testing

**Development Status**:
- ✅ **Production Card Database**: 1,576 cards, 86.9% effect coverage 
- 🚧 **React UI**: In development for visual effect testing
- 🐛 **Known Critical Bug**: Pikachu ex Circle Circuit coin flip damage not scaling

**React Development Setup**:
```bash
# Setup React development environment
cd frontend
npm install
npm run dev  # Start development server (port 5173)

# WebSocket integration with Flask backend  
# Backend runs on :5002, React dev server on :5173
```

**Battle Simulator Access**:
- **Flask-Integrated Version**: http://localhost:5002/battle-simulator (uses pre-built React components)
- **React Development Version**: http://localhost:5173 (live React development with hot reload)
- Both versions connect to the same Flask backend on port 5002

**Priority Testing Through UI**:
- **Visual Effect Validation**: See effects work in real-time
- **Engine Bug Discovery**: UI reveals issues unit tests miss  
- **Card Effect Verification**: Test problematic cards through gameplay

**✅ Recent Battle Engine Improvements:**
- **Effect Execution Pipeline**: All parsed effects (coin flips, healing, status, energy scaling) now execute correctly
- **Pikachu ex Circle Circuit**: FIXED - coin flip damage scaling now works with variable bench Pokemon count
- **Status Conditions**: Complete timing system - applied after attacks, processed between turns
- **Effect Registry System**: NEW - Clean, modular effect handlers with decorator pattern
- **Comprehensive Testing**: All 18 battle engine tests passing

**🎯 Current Focus: Engine Completeness (Before AI Development)**
Priority is making battle engine 100% correct and fully playable:
- **Phase A**: Common card effects (basic damage, simple status, healing, retreat)
- **Phase B**: Intermediate effects (trainers, evolution, energy manipulation)  
- **Phase C**: Advanced effects (stadiums, complex interactions, continuous effects)
- **Testing Order**: Start with simplest/most common cards, gradually add complexity

## Git Workflow & Testing

**Branch Strategy:**
- `main` → Production auto-deploy
- `development` → Test environment auto-deploy  
- Feature branches → Tests only, no deploy

**Testing Protocol:**
- Always run `./scripts/run_tests.sh fast` after changes
- Add tests for new features in appropriate directories:
  - `tests/unit/` - Business logic
  - `tests/integration/` - API endpoints  
  - `tests/security/` - Auth/admin features

See `TESTING.md` and `TESTING_CHEAT_SHEET.md` for complete testing docs.

## 💡 Key Development Info

**Common Tasks:**
- Force card refresh: POST `/api/refresh-cards` with `X-Refresh-Key` header
- Default Flask dev port: 5002
- Cache TTL: Cards 24h, Users 30min
- Admin access: `ADMIN_EMAILS` env var

**🚨 COST MANAGEMENT:**
- **Scheduler jobs NOW ACTIVE** (re-enabled with App Engine cleanup - costs controlled)
- **Run cleanup after manual deployments**: `./scripts/cleanup_app_versions.sh`
- **Check App Engine versions**: `gcloud app versions list --project=pvpocket-dd286`
- **Emergency cost fix**: See `IMMEDIATE_COST_FIX.md`

**Core Patterns:**
```python
# API endpoints - always validate input and handle errors
@app.route('/api/endpoint')
def api_endpoint():
    if not request.args.get('param'):
        return jsonify({'error': 'Missing parameter'}), 400
    try:
        result = process_request(request.args)
        return jsonify(result), 200
    except Exception as e:
        app.logger.error(f"API error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Caching - check cache first, fallback to DB
def get_data():
    cached = cache_manager.get('key')
    if cached:
        return cached
    try:
        data = fetch_from_database()
        cache_manager.set('key', data, ttl=3600)
        return data
    except Exception as e:
        app.logger.error(f"Failed to fetch: {e}")
        return []
```

See `DEVELOPMENT.md` for detailed development workflows and commands.

## Project Structure

```
pokemon_tcg_pocket/
├── app/                    # Core Flask application
│   ├── __init__.py        # App factory, Firebase/OAuth setup
│   ├── config.py          # Environment configs
│   ├── models.py          # User models
│   ├── alerts.py          # Alert system
│   ├── cache_manager.py   # In-memory caching
│   ├── monitoring.py      # Performance monitoring
│   ├── services.py        # Business logic
│   ├── db_service.py      # Database operations
│   ├── email_service.py   # Email notifications
│   ├── firestore_cache.py # Alternative caching
│   ├── gcp_exceptions.py  # GCP error handling
│   ├── secret_manager_utils.py # Secret management
│   ├── security.py        # Security utilities
│   ├── task_queue.py      # Background tasks
│   └── routes/            # Route handlers
│       ├── admin.py       # Admin dashboard & metrics
│       ├── auth.py        # OAuth login/logout
│       ├── battle.py      # Battle simulation
│       ├── collection.py  # Card collection
│       ├── decks.py       # Deck building
│       ├── friends.py     # Friend system
│       ├── internal.py    # Internal/monitoring routes
│       ├── main.py        # Home page
│       └── meta.py        # Meta-game analysis
├── templates/             # Jinja2 HTML templates
│   ├── admin_dashboard.html # Admin interface
│   ├── about.html, faq.html, support.html # Static pages
│   ├── terms_of_service.html, privacy_policy.html
│   └── [other templates...]
├── static/js/             # Client-side JavaScript
│   ├── client-cache.js, image-utils.js
│   └── [performance/mobile scripts...]
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   ├── security/         # Security tests
│   └── performance/      # Performance tests
├── scripts/              # Utility scripts
│   ├── run_tests.sh      # Test runner
│   ├── create_test_data.py, setup_*.py
│   └── [other scripts...]
├── docs/                 # Documentation
├── monitoring/           # Monitoring configs
├── scraping/             # Data pipeline
├── checker/              # Change detection
├── Card.py, Deck.py      # Core models
├── shared_utils.py       # Firebase utilities
├── run.py                # Dev server
└── [config files...]     # app.yaml, requirements.txt, etc.
```

## Architecture & Key Systems

**Core Architecture:**
- Flask app factory pattern with Blueprint-based routing
- Environment-based configuration (dev/test/prod/staging)
- Firebase integration (Firestore DB, Storage, OAuth)
- In-memory caching system (24h cards, 30min users, 98%+ hit rate)

**Key Components:**
- `Card.py` / `Deck.py` - Core data models
- `app/services.py` - Business logic layer
- `app/cache_manager.py` - High-performance caching
- `app/monitoring.py` - Performance metrics & alerts
- `app/routes/admin.py` - Admin dashboard with metrics
- `scraping/` - Data pipeline from Limitless TCG
- `checker/` - Change detection system

**Firebase Collections:**
```
users/          # User profiles & auth
decks/          # User decks (20-card format, 2-copy limit)
cards/          # Master card database
internal_config/ # System configuration
```

**Performance:**
- Cache hit rate: 98%+, Response time: <500ms
- Auto-scaling on Google App Engine
- CDN integration for static assets

## 📚 Documentation References

- `TESTING.md` - Complete testing strategy
- `DEPLOYMENT_GUIDE.md` - Deployment procedures  
- `DEVELOPMENT.md` - Development workflows
- `ALERTS_SETUP.md` - Monitoring & alerting
- `SCRAPING.md` - Data pipeline details

## 🔄 Maintaining This File

**Update CLAUDE.md when making significant changes to:**
- Core architecture or major features
- Testing requirements or procedures
- Deployment processes or environments
- New critical patterns or best practices

**Keep updates minimal** - Reference external docs for details to maintain conciseness.

## 🎯 Battle Simulator Development Guidelines

### 📋 Documentation Requirements
**ALWAYS maintain these living documents when working on battle simulator:**
- **`battle_sim_design.md`** - Update architecture, mechanics, or implementation changes
- **`battle_rules_db.md`** - Update data structures or database schema changes
- **CLAUDE.md** (this file) - Update development procedures or critical patterns

### ⚙️ Battle Sim Coding Standards
**Follow these patterns for battle simulator code:**
```python
# ✅ GOOD - Battle state management
class GameState:
    def validate_action(self, action: Action) -> Tuple[bool, str]:
        try:
            # Validate action legality
            if not self._is_legal_action(action):
                return False, "Illegal action"
            return True, ""
        except Exception as e:
            self.logger.error(f"Action validation failed: {e}")
            return False, "Validation error"

# ✅ GOOD - AI decision making with fallbacks
def choose_attack(self, available_attacks: List[Attack]) -> Attack:
    try:
        # AI logic here
        return self._calculate_best_attack(available_attacks)
    except Exception as e:
        self.logger.error(f"AI attack selection failed: {e}")
        # Fallback to first valid attack
        return available_attacks[0] if available_attacks else None
```

### 🧪 Battle Sim Testing Protocol
**Testing requirements for battle simulator components:**
```bash
# Test battle components after changes
python -m pytest simulator/tests/ -v

# Test integration with existing app
./scripts/run_tests.sh fast

# Performance testing for battle speed
python -m pytest simulator/tests/test_performance.py -v
```

### 📊 Battle Logging Standards
**All battle components must log consistently:**
```python
# Turn-by-turn logging (JSONL format)
battle_log = {
    "turn": turn_number,
    "player": current_player,
    "action": action_type,
    "details": action_details,
    "game_state": current_state_snapshot,
    "timestamp": datetime.utcnow().isoformat()
}

# Error logging with context
try:
    result = execute_battle_action(action)
except Exception as e:
    self.logger.error(f"Battle action failed", extra={
        "action": action.to_dict(),
        "game_state": game_state.to_dict(),
        "error": str(e)
    })
```

### 🔄 Ability Effect Workflow (Phase 2+)
**When implementing card abilities and effects:**
1. **Define Effect**: Add to `battle_rules_db.md` effect registry
2. **Implement Logic**: Create effect class in simulator/effects/
3. **Add Tests**: Unit tests for effect behavior
4. **Update Docs**: Document effect in `battle_sim_design.md`
5. **Integration Test**: Test effect in full battle context

### 🎮 AI Development Standards
**AI implementations must be:**
- **Deterministic**: Same input → same output (given same RNG seed)
- **Legal**: Only make moves allowed by game rules
- **Safe**: Handle invalid states gracefully
- **Fast**: <10ms per decision for meta analysis
- **Logged**: All decisions logged for analysis

### 🔧 Performance Requirements
**Battle simulator performance targets:**
- **Battle Speed**: <100ms per complete battle
- **Memory Usage**: <50MB for 1000 concurrent battles  
- **Validation**: All moves validated before execution
- **Timeout**: 30 second max per battle (prevent infinite loops)

### 🚨 Battle Sim Commit Gates
**Never commit battle simulator code that:**
- Allows illegal game moves
- Crashes on invalid input
- Lacks comprehensive error handling
- Missing corresponding test coverage
- Breaks existing battle functionality

### 🔍 Battle Debugging Workflow
```python
# Enable detailed battle logging for debugging
BATTLE_DEBUG = True

# Run single battle with full logging
python main.py --debug --seed 12345 --log-level DEBUG

# Validate battle state consistency
python -m simulator.tests.test_state_validation
```