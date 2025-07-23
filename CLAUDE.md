# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
# 1. Start working
python run.py  # Run app locally

# 2. Make changes, then save to GitHub
git add .
git commit -m "Description of what I changed"
git push

# That's it! Everything else happens automatically
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

### How to Deploy
```bash
# Deploy to production
python deploy_secrets.py --environment production
gcloud app deploy app-production-deploy.yaml
rm app-production-deploy.yaml

# Deploy to test environment
python deploy_secrets.py --environment test
gcloud app deploy app-test-deploy.yaml
rm app-test-deploy.yaml
```

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
- **Security scanning** on every push
- **Performance tests** on every push
- **Auto-deployment** when pushing to main/develop
- **Health checks** after each deployment

## Development Workflow

### Local Development Setup
1. **Environment Setup**: Configure environment variables (see Environment Variables section)
2. **Dependencies**: Install Python packages (`pip install -r requirements.txt`) and Node.js dependencies (`npm install`)
3. **Firebase Config**: Ensure Firebase credentials are available (local file or Secret Manager)
4. **Run Application**: Use `python run.py` for development server

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

# Access performance monitoring dashboard (while app running)
# http://localhost:5001/test-scalability-dashboard

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
- **Testing Dashboard**: `/test-scalability-dashboard` - Interactive performance testing
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