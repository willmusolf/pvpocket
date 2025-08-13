import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    REFRESH_SECRET_KEY = os.environ.get("REFRESH_SECRET_KEY")
    # Critical: Must be set in production environment
    TASK_AUTH_TOKEN = os.environ.get("TASK_AUTH_TOKEN")
    if not TASK_AUTH_TOKEN and os.environ.get("FLASK_ENV") == "production":
        raise ValueError("TASK_AUTH_TOKEN must be set in production environment")

    GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

    GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
    FIREBASE_SECRET_NAME = os.environ.get("FIREBASE_SECRET_NAME")
    
    # Email Configuration - Using port 465 (SSL) due to port 587 network blocking
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 465))  # Changed from 587 to 465
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "false").lower() == "true"  # TLS disabled for SSL
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "true").lower() == "true"   # SSL enabled for port 465
    MAIL_TIMEOUT = int(os.environ.get("MAIL_TIMEOUT", 10))  # 10 second timeout
    
    # Email credentials from Secret Manager (fallback to env vars for development)
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "willmusolf@gmail.com")

    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    PROJECT_ROOT = os.path.dirname(BASE_DIR)

    # Asset URL Configuration
    FIREBASE_STORAGE_BASE_URL = 'https://firebasestorage.googleapis.com/v0/b/pvpocket-dd286.firebasestorage.app/o'
    ASSET_BASE_URL = FIREBASE_STORAGE_BASE_URL  # Default for development

    DEBUG = (
        os.environ.get("FLASK_DEBUG", "0") == "1"
    )
    TESTING = False
    @classmethod
    def create_directories(cls):
        """Create required data directories if they don't exist."""
        os.makedirs(cls.DATA_DIR, exist_ok=True)

class DevelopmentConfig(Config):
    """Configuration for development environment."""
    DEBUG = True
    # Always use full data in development - emulator provides 1327 cards for free
    # If no emulator is available, the app will fall back to production Firestore
    USE_MINIMAL_DATA = False


class ProductionConfig(Config):
    """Configuration for production environment."""
    DEBUG = False
    ASSET_BASE_URL = 'https://cdn.pvpocket.xyz'
    # Only load cards when actually needed (lazy loading)
    LAZY_LOAD_CARDS = True


class StagingConfig(ProductionConfig):
    """Configuration for staging environment."""
    DEBUG = True  # Enable debug logging for test environment


class TestingConfig(Config):
    """Configuration for testing environment."""
    TESTING = True
    DEBUG = True
    
    # Override to provide defaults for testing
    SECRET_KEY = os.environ.get("SECRET_KEY", "test-secret-key-for-testing")
    REFRESH_SECRET_KEY = os.environ.get("REFRESH_SECRET_KEY", "test-refresh-key")
    GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "test-project")
    FIREBASE_SECRET_NAME = os.environ.get("FIREBASE_SECRET_NAME", "test-secret")

config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "staging": StagingConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
