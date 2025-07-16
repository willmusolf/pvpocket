# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Development server
python run.py

# Production (Google App Engine)
gunicorn -b :$PORT run:app
```

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install Node.js dependencies (Firebase client SDK)
npm install

# Set up environment variables
cp .env.example .env  # Create and configure .env file
```

## Architecture Overview

### Core Application Structure
- **Flask App Factory Pattern**: App created via `create_app()` in `app/__init__.py`
- **Configuration Management**: Environment-based configs in `app/config.py` (development/production/testing)
- **Blueprint-based Routing**: Modular routes in `app/routes/` (auth, battle, collection, decks, friends, main, meta)

### Data Layer Architecture
- **Firebase Integration**: Firestore for data persistence, Firebase Storage for images, Firebase Auth via Google OAuth
- **Card Data Models**: 
  - `Card` class in `Card.py` - Individual Pokémon TCG cards with attributes (HP, attacks, energy type, etc.)
  - `CardCollection` class - In-memory collection with Firestore sync and 30-day pickle caching
  - `Deck` class in `Deck.py` - 20-card max, 2-copy limit per card, with Firestore persistence
- **User Management**: Flask-Login with Firestore-backed User model in `app/models.py`

### Data Synchronization System
- **Card Cache**: `/tmp/card_collection.pkl` with 30-day TTL, automatically refreshes from Firestore
- **Cache Refresh API**: `/api/refresh-cards` endpoint with secret key authentication
- **Automated Data Pipeline**: 
  - `main.py` - Cloud Function for monitoring external data sources
  - `scraping/` module - Web scraping from Limitless TCG, Google Drive image sync, icon scraping
  - `checker/` - Cloud Run jobs triggered by data changes

### Key Features Implementation
- **Deck Building**: Custom 20-card format with type validation and energy cost analysis
- **Collection Management**: Personal card tracking with rarity and pack information
- **Meta-game Analysis**: Battle simulation data aggregation (in development)
- **Authentication**: Google OAuth with username setup flow

### External Dependencies
- **Data Sources**: Limitless TCG for card data, Google Drive for high-res images
- **Cloud Services**: Google App Engine hosting, Cloud Run for background jobs, Secret Manager for credentials
- **Frontend**: Vanilla JavaScript + Bootstrap + Jinja2 templates

### Firebase Collections Structure
```
users/              # User profiles and authentication data
decks/              # User-created decks with card lists and metadata  
cards/              # Master card database with all TCG data
internal_config/    # System configuration (sets_tracker, drive_tracker, etc.)
```

### Important Patterns
- **Error Handling**: Graceful fallbacks for Firebase connectivity issues
- **Security**: Secret key rotation, OAuth scoping, input sanitization with profanity filtering
- **Performance**: Card collection caching, selective Firestore queries, threaded cache updates
- **Deployment**: Environment-specific configs, Google Cloud integration, containerized jobs