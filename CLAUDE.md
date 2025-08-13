# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 CRITICAL: Testing & Code Quality Requirements

### ⚠️ MANDATORY: Test Before AND After Changes
**YOU MUST ALWAYS:**
1. Run tests BEFORE making any code changes to establish baseline
2. Run tests AFTER making changes to verify nothing broke
3. If tests fail, FIX THEM before proceeding
4. Never commit code with failing tests

```bash
# ALWAYS run this before making changes:
./scripts/run_tests.sh fast  # Takes only 1-3 seconds!

# After making changes:
./scripts/run_tests.sh fast  # Verify nothing broke

# Before major changes or deployment:
./scripts/run_tests.sh pre-prod  # Full validation
```

### 📝 Code Simplicity & Quality Rules
**ALWAYS write simple, maintainable code:**
- **Prefer simple over clever** - Code should be easily understood by beginners
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

## 🎯 Simple Overview for Beginners

### What We Built
1. **Your App**: A Pokemon TCG Pocket app that runs on Google Cloud
2. **Security**: All passwords/secrets are safely stored (not in code)
3. **Automation**: Push code → Tests run → Deploys automatically
4. **Monitoring**: Tracks if your app is healthy and fast
5. **Backups**: Saves your database automatically every day

### Key URLs
- **Your Website**: https://pvpocket.xyz
- **Test Version**: https://test-env-dot-pvpocket-dd286.uc.r.appspot.com
- **Local Testing**: http://localhost:5001 (on your computer)

### Daily Development (What You'll Actually Do)
```bash
# 1. Run tests first (MANDATORY)
./scripts/run_tests.sh fast  # Establish baseline (1-3 seconds)

# 2. Start working
python run.py  # Run app locally

# 3. After making changes, test again (MANDATORY)
./scripts/run_tests.sh fast  # Verify nothing broke

# 4. Save to GitHub (only if tests pass)
git add .
git commit -m "Description of what I changed"
git push

# ✅ CI/CD Pipeline: Fully configured with service account permissions
```

## 🚀 Deployment & Infrastructure Overview

### Current Setup
- **Production URL**: https://pvpocket.xyz (and https://pvpocket-dd286.uc.r.appspot.com)
- **Test Environment**: https://test-env-dot-pvpocket-dd286.uc.r.appspot.com
- **Local Development**: http://localhost:5001

### Security & Secrets Management
- **All secrets removed from code** - stored in Google Secret Manager
- **Local development**: Uses `.env` file (never commit this!)
- **Cloud deployment**: Uses `deploy_secrets.py` script to fetch from Secret Manager
- **GitHub Actions**: Secrets stored in repository settings

### Firebase Cost Optimizations (Jan 2025)
- **Extended Cache TTLs**: Card collection (72h), user data (2h), user collections (24h), decks (6h)
- **Client-Side Filtering**: Deck searches filter locally after initial load, reducing Firestore reads by 50%+
- **Connection Pool Optimization**: Reduced from 15 to 10 concurrent connections
- **Batch Size Reduction**: Limited to 100 documents per batch (from 500)
- **Composite Indexes**: Added for common query patterns (owner_id + updated_at, etc.)
- **Usage Monitoring**: Track Firestore operations at `/internal/firestore-usage`
- **Cost Alerts**: Automatic warnings when approaching daily limits or high costs

### How to Deploy (GitHub Actions)

#### Automated Deployment via GitHub
Your app uses GitHub Actions for continuous deployment:

**Production Deployment:**
```bash
# Push to main branch triggers production deployment
git checkout main
git merge development  # or your feature branch
git push origin main
```

**Test Environment Deployment:**
```bash
# Push to development branch triggers test deployment  
git checkout development
git push origin development
```

#### Manual Deployment (if needed)
```bash
# Generate deployment config with secrets
python3 deploy_secrets.py --project-id pvpocket-dd286 --environment production
gcloud app deploy app.yaml --project=pvpocket-dd286
rm app.yaml  # Clean up temporary file with secrets

# For test environment
python3 deploy_secrets.py --project-id pvpocket-dd286 --environment test  
gcloud app deploy app-test.yaml --project=pvpocket-dd286
rm app-test.yaml
```

#### Environment Variables (Automatically Configured in GitHub Actions)
- ✅ `ADMIN_EMAILS` - Admin access control (stored in Google Secret Manager)
- ✅ `TASK_AUTH_TOKEN` - Secure background task authentication  
- ✅ `SECRET_KEY` - Flask secret key
- ✅ `REFRESH_SECRET_KEY` - API refresh key
- ✅ `GOOGLE_OAUTH_CLIENT_ID/SECRET` - OAuth authentication
- ✅ All alert system credentials

### Firebase Emulator Strategy

#### Local Development
- **Purpose**: Free local development with full production data mirror
- **Auto-start**: `python3 run.py` starts emulator and syncs if needed
- **Data sync**: Syncs ALL collections from production on first run
- **Persistence**: Data saved in `emulator_data/` directory
- **Isolation**: Local changes don't affect production
- **Collections synced**: cards (~1327), users (all), decks (all), internal_config, etc.

#### GitHub Actions Tests
- **Test data**: Uses `scripts/create_test_data.py` for consistent test data
- **Content**: 10 test cards, 3 test users, 3 test decks
- **Isolation**: Each test run gets fresh emulator instance
- **All test types**: Fast, full, unit, security, performance tests use emulator

#### Environment Summary
| Environment | Firebase Mode | Data Content | Cost |
|-------------|--------------|--------------|------|
| Local Dev | Emulator | Full production mirror | FREE |
| GitHub CI | Emulator | Test data (10 cards) | FREE |
| Staging | Real Firestore | Production data | MINIMAL |
| Production | Real Firestore | Production data | OPTIMIZED |

## Git Workflow & CI/CD

### Branch Strategy
- **main branch**: Auto-deploys to production when you push
- **develop branch**: Auto-deploys to test environment when you push
- **feature branches**: Run tests but don't deploy

### Typical Development Flow
1. Create feature branch: `git checkout -b feature/my-new-feature`
2. Make changes and test locally: `python run.py`
3. Commit and push: `git add . && git commit -m "Add feature" && git push`
4. Create Pull Request to main branch
5. GitHub Actions automatically runs tests
6. Merge PR → Auto-deploys to production

### What Happens Automatically
- **Claude runs tests** before and after every code change
- **Security scanning** on every push
- **Performance tests** on every push  
- **Auto-deployment** when pushing to main/develop
- **Health checks** after each deployment
- **Test failure blocking** - PRs can't merge with failing tests

### Claude's Automated Behavior
When you ask Claude to make changes, Claude will:
1. **Run baseline tests** before starting work (`./scripts/run_tests.sh fast`)
2. **Follow existing patterns** by examining similar code in the project
3. **Add proper error handling** to all new code with try/except blocks
4. **Run tests after changes** to verify nothing broke
5. **Report test results** in the response to you
6. **Fix any test failures** before considering the task complete
7. **Add new tests** when creating new features or modifying critical functionality
8. **Use appropriate test types**: Unit tests for business logic, integration tests for API endpoints, security tests for auth features

### 🧪 Claude's Testing Protocol
**For any significant change, Claude will:**
- Run `./scripts/run_tests.sh fast` before and after changes
- Add appropriate test files if creating new functionality:
  - `tests/unit/` for business logic and data models
  - `tests/integration/` for API endpoints and workflows  
  - `tests/security/` for authentication and authorization
- Ensure test coverage for new code meets project standards
- Fix any test failures before completing the task
- Report test results and coverage in the response

## Development Workflow

### Local Development Setup
1. **Environment Setup**: Configure environment variables (see Environment Variables section)
2. **Dependencies**: Install Python packages (`pip install -r requirements.txt`) and Node.js dependencies (`npm install`)
3. **Firebase Config**: Ensure Firebase credentials are available (local file or Secret Manager)
4. **Run Application**: Use `python3 run.py` for development server (not `python`)

### Development Best Practices
- **Configuration**: Use environment variables for all sensitive data
- **Caching**: Card collection cached for 24 hours - use `/api/refresh-cards` to force refresh
- **Authentication**: Google OAuth requires proper redirect URIs in development
- **Background Jobs**: Test scraping and checker modules independently
- **Port Configuration**: Default development port is 5001, production uses `$PORT` environment variable

### Common Development Tasks
- **Force Card Refresh**: POST to `/api/refresh-cards` with `X-Refresh-Key` header
- **Debug Firebase**: Check `app/__init__.py` for Firebase initialization and connection logs
- **Profile Icon Management**: Icons stored in Firebase Storage under `profile_icons/`
- **Energy Type Icons**: Predefined URLs in `app/__init__.py` for energy type visualization

## 🧪 Testing Strategy (CRITICAL - READ THIS!)

### ⚡ Quick Reference - What to Run When

| Scenario | Command | Duration | Purpose |
|----------|---------|----------|---------|
| **Before ANY code changes** | `./scripts/run_tests.sh fast` | 1-3 sec | Baseline |
| **After making changes** | `./scripts/run_tests.sh fast` | 1-3 sec | Verify |
| **Before pushing to repo** | `./scripts/run_tests.sh fast` | 1-3 sec | Final check |
| **Major feature complete** | `./scripts/run_tests.sh pre-prod` | 20-30 sec | Full validation |
| **Debugging specific area** | `pytest -m unit -v` | Varies | Targeted testing |

### 🔴 Test Failure Protocol
**If tests fail after your changes:**
1. **STOP** - Do not proceed with other tasks
2. **IDENTIFY** - Run failing test individually: `pytest path/to/test.py::TestClass::test_method -v`
3. **FIX** - Correct the issue in your code
4. **VERIFY** - Run tests again until they pass
5. **NEVER** skip tests or comment them out

### 📋 Automatic Testing Checklist
When working on any task, Claude should:
- [ ] Run fast tests before starting work
- [ ] Check if specific test files exist for the module being modified
- [ ] Run tests after each significant change
- [ ] Run full test suite before marking task complete
- [ ] Include test results in response to user

### Quick Test Commands
```bash
# MOST COMMON - Use this 90% of the time:
./scripts/run_tests.sh fast      # 1-3 seconds, catches most issues

# When working on specific areas:
pytest tests/unit/ -v            # Unit tests only
pytest tests/security/ -v        # Security tests
pytest tests/performance/ -v     # Performance tests
pytest -m "not slow" -v         # Skip slow tests

# Before deployment or major changes:
./scripts/run_tests.sh pre-prod  # Full suite with Firebase emulator

# If you need to debug a specific test:
pytest path/to/test.py -v --tb=short  # Verbose with short traceback
```

### What Tests Catch
- ✅ Syntax errors and import failures
- ✅ Missing configuration fields 
- ✅ Firebase connection issues  
- ✅ API endpoint breakages
- ✅ Authentication problems
- ✅ Security vulnerabilities
- ✅ Performance regressions
- ✅ Data model inconsistencies

### Test Coverage Requirements
- **Minimum coverage**: 30% (enforced in CI/CD)
- **Target coverage**: 80% for critical modules
- **New code**: Must include tests if modifying core functionality

### 🆕 New Test Categories Added (2025)
**Critical Areas With Test Framework:**
- **Friends System**: Framework created (`tests/integration/test_friends_system.py`)
  - Comprehensive test structure for friend workflows
  - Note: Some tests need Flask context fixes for full CI/CD integration
- **Deck Routes**: Framework created (`tests/integration/test_deck_routes.py`)
  - Complete CRUD operation test structure
  - Note: Requires proper mocking of Deck class methods
- **Admin Security**: Working tests (`tests/security/test_admin_access.py`)
  - Admin authentication and access control validation
  - Note: Some tests need authentication context adjustments
- **Deck Business Rules**: Fully working (`tests/unit/test_deck_business_rules.py`)
  - ✅ 20-card limit and 2-copy-per-name rules tested
  - ✅ Basic Pokemon requirements validated
  - ✅ All validation and edge cases covered
- **Authentication Flows**: Framework created (`tests/integration/test_auth_flows.py`)
  - Complete auth lifecycle test structure
  - Note: Flask-Dance OAuth integration needs context fixes

**✅ RECOMMENDATION**: Focus on unit tests first (like `test_deck_business_rules.py`) as they are more reliable, then gradually improve integration tests.

### When to Add Tests for New Features
**ALWAYS add tests when creating:**
- New API endpoints or routes
- Authentication or authorization features
- Database operations or transactions
- Business logic or validation rules
- User-facing forms or workflows
- Admin or security features

See `TESTING.md` and `TESTING_CHEAT_SHEET.md` for complete testing documentation.

## 💡 Code Patterns & Best Practices

### Writing Simple, Maintainable Code

#### ✅ GOOD Examples:
```python
# Simple, clear function with error handling
def get_user_decks(user_id):
    """Fetch all decks for a user."""
    try:
        decks = db.collection('decks').where('owner_id', '==', user_id).get()
        return [deck.to_dict() for deck in decks]
    except Exception as e:
        app.logger.error(f"Error fetching decks for user {user_id}: {e}")
        return []

# Clear variable names and simple logic
def calculate_deck_cost(deck_cards):
    """Calculate total pack cost for a deck."""
    total_cost = 0
    for card in deck_cards:
        total_cost += card.get('pack_cost', 0)
    return total_cost
```

#### ❌ BAD Examples:
```python
# Too clever, hard to understand
def gd(u):
    return [d.to_dict() for d in db.collection('decks').where('owner_id','==',u).get()]

# No error handling, complex nested logic
def process_data(data):
    result = data['items'][0]['attributes']['value'] * 2
    for item in data['items']:
        if item['type'] == 'special':
            result += item['attributes']['bonus']
    return result  # Will crash if any key is missing!
```

### Common Patterns to Follow

#### Database Operations
```python
# Always use try/except for Firestore operations
try:
    # Get with limit to prevent excessive reads
    docs = db.collection('cards').limit(100).get()
    return [doc.to_dict() for doc in docs]
except Exception as e:
    app.logger.error(f"Database error: {e}")
    return []  # Safe fallback
```

#### API Endpoints
```python
@app.route('/api/endpoint')
def api_endpoint():
    # Input validation
    if not request.args.get('param'):
        return jsonify({'error': 'Missing parameter'}), 400
    
    try:
        # Process request
        result = process_request(request.args)
        return jsonify(result), 200
    except Exception as e:
        app.logger.error(f"API error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
```

#### Caching Pattern
```python
# Check cache first, fallback to database
def get_cards():
    # Try cache
    cached = cache_manager.get('cards')
    if cached:
        return cached
    
    # Fallback to database
    try:
        cards = fetch_from_database()
        cache_manager.set('cards', cards, ttl=3600)
        return cards
    except Exception as e:
        app.logger.error(f"Failed to fetch cards: {e}")
        return []
```

### Performance Considerations
- **Use batch operations** for multiple Firestore writes
- **Implement caching** for frequently accessed data
- **Limit query results** to prevent excessive reads
- **Use pagination** for large datasets
- **Profile before optimizing** - don't guess at performance issues

### Security Best Practices
- **Never trust user input** - Always validate and sanitize
- **Use parameterized queries** - Prevent injection attacks
- **Check authentication** - Verify user permissions
- **Log security events** - Track failed auth attempts
- **Keep secrets in Secret Manager** - Never hardcode credentials

## 🚨 Troubleshooting & Debugging Guide

### Test Failures - Common Issues & Solutions

#### "ModuleNotFoundError" or Import Errors
```bash
# Check if running from correct directory
pwd  # Should be in pokemon_tcg_pocket/

# Install dependencies
pip install -r requirements.txt

# Run specific failing test
pytest path/to/failing_test.py -v --tb=long
```

#### "Firebase Connection Failed"
```bash
# For local development - start emulator
firebase emulators:start --only firestore,storage

# For tests - use fast tests instead
./scripts/run_tests.sh fast  # Uses mocked data
```

#### "Tests Pass Locally but Fail in CI"
```bash
# Run the exact same command as CI
pytest tests/test_fast_development.py -v --tb=short --cov-fail-under=0

# Check environment variables match CI
echo $FLASK_CONFIG  # Should be 'testing'
```

### Code Issues - Debugging Steps

#### "Function Not Working"
1. **Add logging**: Use `app.logger.error()` to see what's happening
2. **Check inputs**: Validate parameters are correct
3. **Test in isolation**: Create simple test case
4. **Check similar code**: Find working examples in codebase

#### "Performance Issues"
1. **Check caching**: Is data cached when it should be?
2. **Database queries**: Are you fetching too much data?
3. **Run performance tests**: `pytest -m performance -v`

#### "Security Issues"
1. **Input validation**: Are you sanitizing user input?
2. **Authentication**: Are you checking user permissions?
3. **Run security tests**: `pytest -m security -v`

### Emergency Procedures

#### "I Broke Something Critical"
```bash
# 1. STOP - Don't make more changes
# 2. Run tests to see what's broken
./scripts/run_tests.sh fast

# 3. If many tests fail, check recent changes
git diff HEAD~1

# 4. If needed, revert last change
git revert HEAD

# 5. Run tests again to confirm fix
./scripts/run_tests.sh fast
```

#### "Tests Won't Run"
```bash
# Check Python path
which python3
python3 --version  # Should be 3.11+

# Reinstall test dependencies
pip install pytest pytest-mock

# Run single test to isolate issue
python3 -m pytest tests/test_fast_development.py::TestBasicImports::test_core_modules_import -v
```

### Getting Help
- **Test documentation**: See `TESTING.md` and `TESTING_CHEAT_SHEET.md`
- **API documentation**: Check existing route handlers in `app/routes/`
- **Database patterns**: Look at `app/services.py` for examples
- **Error patterns**: Check `app/__init__.py` for error handling examples

## 🚨 CI/CD Troubleshooting Guide

### GitHub Actions Authentication Issues

**Problem**: `HTTPSConnectionPool(host='oauth2.googleapis.com', port=443): Max retries exceeded`

**Root Causes & Solutions**:

1. **Service Account Key Issues**:
   ```bash
   # Regenerate GitHub secrets using the setup script
   ./scripts/github-secrets-setup.sh
   ```

2. **Missing GitHub Secrets**:
   Required secrets in your GitHub repository settings:
   - `GCP_SA_KEY` - Service account JSON key
   - `SECRET_KEY`, `REFRESH_SECRET_KEY` - From Secret Manager
   - `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` - OAuth credentials
   - `TASK_AUTH_TOKEN`, `ADMIN_EMAILS` - App configuration

3. **Network Connectivity**: The updated CI/CD pipeline includes network diagnostics and retry logic.

### App Engine 502 Bad Gateway

**Problem**: Manual deployment works but GitHub Actions deployment gives 502 error.

**Root Cause**: Missing environment variables in deployment configuration.

**Solution**: Ensure `app-test.yaml` includes all required environment variables:
```yaml
env_variables:
  SECRET_KEY: 'your-secret-key'
  REFRESH_SECRET_KEY: 'your-refresh-key'
  GOOGLE_OAUTH_CLIENT_ID: 'your-client-id'
  GOOGLE_OAUTH_CLIENT_SECRET: 'your-client-secret'
  TASK_AUTH_TOKEN: 'your-task-token'
  ADMIN_EMAILS: 'your-admin-emails'
```

### Service Account Permissions

**Required IAM Roles for GitHub Actions Service Account**:
```bash
# Check current permissions
gcloud projects get-iam-policy pvpocket-dd286 --flatten="bindings[].members" --filter="bindings.members:github-actions@pvpocket-dd286.iam.gserviceaccount.com"

# Should include:
# - roles/appengine.appAdmin
# - roles/appengine.deployer  
# - roles/secretmanager.secretAccessor
# - roles/storage.admin
```

### Quick Fixes

**If GitHub Actions fails**:
1. Check network diagnostics in the action logs
2. Verify authentication step completes successfully
3. Ensure all required secrets are set
4. Use the retry logic (automatically included)

**If manual deployment fails**:
1. Verify all environment variables in `app-test.yaml`
2. Check that secrets exist in Secret Manager
3. Confirm service account has necessary permissions

**Emergency Manual Deployment**:
```bash
# If GitHub Actions is broken, deploy manually:
gcloud app deploy app-test.yaml  # Test environment
gcloud app deploy app.yaml      # Production (create from app-test.yaml template)
```

## Development Commands

### Environment Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies (Firebase client SDK)
npm install
```

### Running the Application
```bash
# Development server (default port 5001)
python run.py

# Development server with specific port
PORT=8080 python run.py

# Production (Google App Engine)
gunicorn -b :$PORT run:app
```

### Development Workflow
```bash
# Run locally with development config
FLASK_CONFIG=development python run.py

# Run with production config locally
FLASK_CONFIG=production python run.py

# Debug mode (automatic in development)
FLASK_DEBUG=1 python run.py
```

### Testing and Performance
```bash
# Run comprehensive scalability tests
python test_scalability.py

# Run quick performance tests
python test_quick.py

# Access admin metrics dashboard (while app running)
# http://localhost:5001/admin/metrics

# Check application health
curl http://localhost:5001/health

# View performance metrics
curl http://localhost:5001/metrics
```

### Deployment Commands
```bash
# Deploy to Google App Engine (production)
gcloud app deploy app.yaml

# Deploy to test environment
gcloud app deploy app-test.yaml

# View logs
gcloud app logs tail -s default
```

### Background Jobs
```bash
# Build and run scraping job container
docker build -t scraping-job .
docker run scraping-job

# Run checker module locally
cd checker && python main.py
```

## Project Structure

### Application Organization
```
pokemon_tcg_pocket/
├── app/                    # Core Flask application
│   ├── __init__.py        # App factory and Flask-Dance OAuth setup
│   ├── config.py          # Environment-based configuration classes
│   ├── models.py          # User authentication and profile models
│   ├── cache_manager.py   # High-performance in-memory caching system
│   ├── monitoring.py      # Real-time performance monitoring and alerting
│   ├── services.py        # Business logic and data access layer
│   ├── db_service.py      # Database connection pooling and optimization
│   ├── firestore_cache.py # Alternative Firestore-based caching
│   ├── task_queue.py      # Background task processing
│   └── routes/            # Modular route handlers
│       ├── __init__.py    # Blueprint registration
│       ├── auth.py        # Google OAuth login/logout
│       ├── battle.py      # Battle simulation (in development)
│       ├── collection.py  # Personal card collection management
│       ├── decks.py       # Deck building and sharing
│       ├── friends.py     # Friend system and social features
│       ├── internal.py    # Internal system routes and monitoring
│       ├── main.py        # Home page and core navigation
│       └── meta.py        # Meta-game analysis and rankings
├── static/                # Static web assets
│   ├── js/               # JavaScript files
│   │   ├── image-cache-sw.js    # Service worker for image caching
│   │   ├── client-cache.js      # Client-side caching utilities
│   │   └── image-utils.js       # Image loading and optimization
│   ├── favicon.ico       # Site favicon
│   └── navbar-icon.png   # Navigation bar icon
├── templates/            # Jinja2 HTML templates
│   ├── base.html         # Base template with navigation
│   ├── main_index.html   # Homepage
│   ├── collection.html   # Card collection interface
│   ├── decks.html        # Deck management interface
│   ├── deck_image_export.html  # Deck export functionality
│   ├── friends.html      # Friend management
│   ├── friend_decks.html # Browse friend decks
│   ├── profile.html      # User profile management
│   ├── login_prompt.html # Authentication flow
│   ├── set_username.html # Username setup
│   ├── battle.html       # Battle interface
│   ├── meta_rankings.html # Meta-game statistics
│   ├── navbar.html       # Navigation component
│   └── test_scalability.html # Scalability testing dashboard
├── scraping/             # Data acquisition pipeline
│   ├── __init__.py       # Package initialization
│   ├── scraper.py        # Web scraping from Limitless TCG
│   ├── download_icons.py # Card image downloading
│   ├── post_processor.py # Data cleaning and normalization
│   └── run_job.py        # Background job orchestration
├── checker/              # Data monitoring system
│   ├── main.py           # Cloud Run job for change detection
│   └── requirements.txt  # Checker-specific dependencies
├── docs/                 # Project documentation
│   └── scalability-without-redis.md # Scalability architecture guide
├── Card.py               # Core card data models
├── Deck.py               # Deck building logic and validation
├── shared_utils.py       # Common Firebase utilities
├── main.py               # Cloud Function entry point
├── run.py                # Development server entry point
├── test_scalability.py   # Comprehensive performance testing suite
├── test_quick.py         # Quick performance tests
├── requirements.txt      # Python dependencies
├── package.json          # Node.js dependencies (Firebase client)
├── Dockerfile           # Container configuration for jobs
├── app.yaml             # Google App Engine production config
├── app-test.yaml        # Google App Engine test config
├── cors-config.json     # CORS configuration for Firebase Storage
├── credentials.json     # Firebase service account (local dev)
├── token.json           # Google API tokens (local dev)
└── CLAUDE.md            # Development documentation
```

### Architecture Overview

#### Core Application Structure
- **Flask App Factory Pattern**: App created via `create_app()` in `app/__init__.py`
- **Configuration Management**: Environment-based configs in `app/config.py` (development/production/staging/testing)
- **Blueprint-based Routing**: Modular routes in `app/routes/` (auth, battle, collection, decks, friends, internal, main, meta)

#### High-Performance Scalability Architecture
- **In-Memory Caching System** (`app/cache_manager.py`):
  - Card collection cache with 24-hour TTL, 98%+ hit rates
  - User data cache with 30-minute TTL
  - Thread-safe operations with automatic cache refresh
  - Redis-compatible interface with Firestore fallback
- **Service Layer** (`app/services.py`):
  - Clean data access patterns and business logic separation
  - Connection pooling and query optimization
  - Batch operations for improved performance
- **Performance Monitoring** (`app/monitoring.py`):
  - Real-time metrics collection (response times, cache hit rates, throughput)
  - Performance threshold alerts and health monitoring
  - Configurable alerting system
- **Database Optimization** (`app/db_service.py`):
  - Connection pooling (up to 15 concurrent connections)
  - Optimized Firestore queries and batch operations
- **Background Task Queue** (`app/task_queue.py`):
  - Asynchronous processing for heavy operations
  - Task prioritization and retry logic

#### Data Layer Architecture
- **Firebase Integration**: 
  - Firestore for data persistence with collections: `users/`, `decks/`, `cards/`, `internal_config/`
  - Firebase Storage for card images and profile icons with CDN integration
  - Firebase Auth via Google OAuth with Flask-Dance integration
  - Secret Manager for secure credential management
- **Card Data Models**: 
  - `Card` class in `Card.py` - Individual Pokémon TCG cards with comprehensive attributes (HP, attacks, energy type, rarity, pack info)
  - `CardCollection` class - In-memory collection with Firestore sync and 24-hour caching
  - `Deck` class in `Deck.py` - Custom 20-card format, 2-copy limit per card name, with Firestore persistence and validation
- **User Management**: Flask-Login with Firestore-backed User model, profile icon management, username requirements
- **CDN Integration**: All static assets served via CDN (https://cdn.pvpocket.xyz) for optimal performance

#### Data Synchronization System
- **Card Cache**: In-memory with 24-hour TTL, thread-safe cache refresh system
- **Cache Refresh API**: `/api/refresh-cards` endpoint with `X-Refresh-Key` header authentication
- **Automated Data Pipeline**: 
  - `main.py` - Cloud Function for monitoring external data sources and triggering updates
  - `scraping/` module - Web scraping from Limitless TCG, Google Drive API integration for high-res images
  - `checker/main.py` - Cloud Run jobs for data change detection and pipeline triggering
  - `shared_utils.py` - Common Firebase initialization and utility functions
- **Background Job Architecture**: Containerized scraping jobs with Docker, Cloud Run deployment

#### Key Features Implementation
- **Deck Building**: Custom 20-card format with type validation and energy cost analysis
- **Collection Management**: Personal card tracking with rarity and pack information
- **Meta-game Analysis**: Battle simulation data aggregation (in development)
- **Authentication**: Google OAuth with username setup flow
- **Performance Monitoring**: Real-time metrics, health checks, and scalability testing dashboard

#### External Dependencies
- **Data Sources**: Limitless TCG for card data, Google Drive for high-res images
- **Cloud Services**: Google App Engine hosting with auto-scaling, Cloud Run for background jobs, Secret Manager for credentials
- **Frontend**: Vanilla JavaScript + Bootstrap + Jinja2 templates with client-side caching

## Performance and Scalability

### Performance Metrics
- **Cache Hit Rate**: 98.3%+ in production
- **Response Time**: <500ms average for cached requests
- **Throughput**: 20+ requests/second sustained
- **Concurrent Users**: Supports 500+ simultaneous users

### Scalability Features
- **Auto-scaling**: Google App Engine with configurable scaling parameters
- **Load Balancing**: Automatic request distribution across instances
- **Connection Pooling**: Up to 15 concurrent database connections
- **CDN Integration**: Static asset delivery via global CDN
- **Client-side Caching**: Image and data caching in browser

### Monitoring and Testing
- **Health Endpoint**: `/health` - System status and diagnostics
- **Metrics Endpoint**: `/metrics` - Performance data in JSON format
- **Automated Testing**: `test_scalability.py` - Comprehensive load testing suite

## Testing and Quality Assurance

### Testing Approach
- **Performance Testing**: Comprehensive scalability testing with `test_scalability.py`
- **Load Testing**: Concurrent user simulation and stress testing
- **Manual Testing**: Flask routes, Firebase integration, and UI workflows
- **Health Monitoring**: Automated health checks and performance alerts

### Code Quality
- **Type Hints**: Comprehensive type hints throughout critical modules
- **Error Handling**: Graceful fallbacks and comprehensive exception handling
- **Security**: Input validation with `better-profanity`, secure credential management
- **Performance Patterns**: Caching, connection pooling, and optimized queries

### Firebase Collections Structure
```
users/              # User profiles and authentication data
decks/              # User-created decks with card lists and metadata  
cards/              # Master card database with all TCG data
internal_config/    # System configuration (sets_tracker, drive_tracker, etc.)
```

### Important Patterns
- **Error Handling**: Graceful fallbacks for Firebase connectivity issues, comprehensive exception handling in data loading
- **Security**: Secret key rotation via Google Secret Manager, OAuth scoping, input sanitization with `better-profanity` filtering
- **Performance**: 
  - High-performance in-memory caching with 98%+ hit rates
  - Database connection pooling and query optimization
  - CDN integration for static assets
  - Client-side caching for improved user experience
  - Background task processing for heavy operations
- **Deployment**: 
  - Multi-environment configs (`app.yaml`, `app-test.yaml`)
  - Google App Engine hosting with automatic scaling
  - Containerized background jobs with Cloud Run
  - Environment variable management across development/production
- **Data Consistency**: Profile icon URL generation, energy type icon mapping, case-insensitive deck name searching

## Environment and Configuration

### Required Environment Variables
```bash
# Core Flask configuration
SECRET_KEY=<flask-secret-key>
REFRESH_SECRET_KEY=<api-refresh-key>
TASK_AUTH_TOKEN=<background-task-auth-token>

# Google Cloud Platform
GCP_PROJECT_ID=<gcp-project-id>
FIREBASE_SECRET_NAME=<secret-manager-name>

# OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID=<oauth-client-id>
GOOGLE_OAUTH_CLIENT_SECRET=<oauth-client-secret>

# Optional - Scalability Configuration
USE_FIRESTORE_CACHE=false        # Alternative cache backend
CACHE_TTL_HOURS=24              # Card cache duration
USER_CACHE_TTL_MINUTES=30       # User cache duration
MAX_DB_CONNECTIONS=15           # Database pool size
MONITORING_ENABLED=true         # Performance monitoring

# Optional - General
FLASK_CONFIG=development        # development/production/staging/testing
FLASK_DEBUG=1                  # Enable debug mode
PORT=5001                      # Server port
```

### Configuration Hierarchy
1. **Base Config** (`app/config.py`): Common settings across environments
2. **Development Config**: Debug enabled, local development settings
3. **Production Config**: Optimized for Google App Engine deployment with CDN
4. **Staging Config**: Production-like environment for testing
5. **Testing Config**: Isolated configuration for testing scenarios

### Firebase Setup
- **Authentication**: Google OAuth with Flask-Dance integration
- **Database**: Firestore with automatic retry and connection handling
- **Storage**: Firebase Storage for images with CDN integration
- **Security**: Credentials managed via Google Secret Manager in production