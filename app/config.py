import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    REFRESH_SECRET_KEY = os.environ.get("REFRESH_SECRET_KEY")

    GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

    GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
    FIREBASE_SECRET_NAME = os.environ.get("FIREBASE_SECRET_NAME")

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


class ProductionConfig(Config):
    """Configuration for production environment."""
    DEBUG = False
    ASSET_BASE_URL = 'https://cdn.pvpocket.xyz'


class StagingConfig(ProductionConfig):
    """Configuration for staging environment."""
    pass


class TestingConfig(Config):
    """Configuration for testing environment."""
    TESTING = True
    DEBUG = True

config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "staging": StagingConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
