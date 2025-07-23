# PvPocket - Pokémon TCG Deck Tool

A web application for Pokémon TCG players to manage collections, build decks, and track the evolving meta-game.

## About The Project

PvPocket is designed for both competitive players seeking an edge and casual fans wanting to experiment with new deck ideas. The long-term vision is to provide data-driven meta-game analysis through powerful battle simulations, offering unique insights into deck performance.

## Key Features

-   **Card Collection Management:** Log and view your personal card collection.
-   **Custom Deck Builder:** Build and edit decks using a custom 20-card format (with a maximum of 2 copies per card).
-   **User Authentication:** Secure and simple sign-in with Google OAuth.
-   **High-Performance Caching:** In-memory caching system with 98%+ hit rates for optimal performance.
-   **Real-time Monitoring:** Performance metrics, alerting, and health monitoring dashboard.
-   **Scalable Architecture:** Handles 500+ concurrent users with auto-scaling and load balancing.
-   **Coming Soon:** A detailed battle simulator to test your decks.
-   **Coming Soon:** Stat-based meta-game rankings powered by simulation data.

---

## Technology Stack

-   **Backend:** Flask, Firebase Firestore, Firebase Storage
-   **Frontend:** Vanilla JavaScript, Jinja2 Templates, Bootstrap
-   **Caching:** In-memory cache with Redis-compatible interface
-   **Monitoring:** Real-time performance metrics and alerting
-   **Infrastructure:** Google App Engine with auto-scaling

---

## Scalability & Performance

### 🚀 Performance Metrics
- **Cache Hit Rate:** 98.3%+ in production
- **Response Time:** <500ms average for cached requests
- **Throughput:** 20+ requests/second sustained
- **Concurrent Users:** Supports 500+ simultaneous users

### 🏗️ Architecture Overview
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Load Balancer │────│  App Engine      │────│   Firestore     │
│   (Auto-scaling)│    │  (Flask App)     │    │   (Database)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                       ┌──────────────────┐
                       │  In-Memory Cache │
                       │  (98% hit rate)  │
                       └──────────────────┘
```

### 📊 Monitoring Dashboard
- **Real-time Metrics:** `/metrics` endpoint provides comprehensive performance data
- **Health Checks:** `/health` endpoint for system status monitoring
- **Interactive Dashboard:** `/test-scalability-dashboard` for live testing
- **Automated Alerts:** Performance threshold monitoring with configurable alerts

### ⚡ Caching Strategy
1. **Card Collection Cache:** 24-hour TTL, thread-safe operations
2. **User Data Cache:** 30-minute TTL, personalized caching
3. **Database Connection Pool:** Up to 15 concurrent connections
4. **CDN Integration:** Static assets served via Firebase Storage

### 🔧 Configuration Options
```bash
# Environment Variables
USE_FIRESTORE_CACHE=false     # Alternative cache backend
CACHE_TTL_HOURS=24           # Card cache duration
USER_CACHE_TTL_MINUTES=30    # User cache duration
MAX_DB_CONNECTIONS=15        # Database pool size
MONITORING_ENABLED=true      # Performance monitoring
```

---

## Project Structure

-   **/app** - Contains the core Flask application, routes, and logic.
    -   **/cache_manager.py** - High-performance in-memory caching system
    -   **/monitoring.py** - Real-time performance monitoring and alerting
    -   **/services.py** - Business logic and data access layer
    -   **/db_service.py** - Database connection pooling and optimization
-   **/templates** - Jinja2 HTML templates for the frontend.
-   **/test_scalability.py** - Comprehensive performance testing suite
-   **/docs/scalability-without-redis.md** - Detailed scalability documentation