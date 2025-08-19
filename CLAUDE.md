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
- **Local**: http://localhost:5001

**Daily Development:**
```bash
python run.py  # Run locally
./scripts/run_tests.sh fast  # Test after changes
```

## 🚀 Deployment & Architecture

**Automated Deployment:**
- Push to `main` → Production deploy  
- Push to `development` → Test environment deploy
- All secrets in Google Secret Manager (NEVER in code)

**Firebase Emulator:**
- Local dev uses emulator with production data mirror (FREE)
- Tests use emulator with test data (FREE)
- Auto-starts with `python run.py`

**Performance Optimizations:**
- Extended cache TTLs, client-side filtering, connection pooling
- Cost monitoring at `/internal/firestore-usage`

See `DEPLOYMENT_GUIDE.md` for detailed deployment instructions.

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
- Default dev port: 5001
- Cache TTL: Cards 24h, Users 30min
- Admin access: `ADMIN_EMAILS` env var

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