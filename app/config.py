import os
from datetime import timedelta

import secrets

class Config:
    # Secret key for sessions and security - auto-generated for security
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(24))
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    
    # Directories and file paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    PROJECT_ROOT = os.path.dirname(BASE_DIR)
    
    # Ensure necessary directories exist
    @classmethod
    def create_directories(cls):
        """Create required directories if they don't exist."""
        directories = [
            os.path.join(cls.PROJECT_ROOT, 'decks'),
            os.path.join(cls.PROJECT_ROOT, 'data'),
            os.path.join(cls.PROJECT_ROOT, 'users')
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    # Data file paths
    BATTLE_HISTORY_FILE = os.path.join(PROJECT_ROOT, 'data', 'battle_history.json')
    META_STATS_FILE = os.path.join(PROJECT_ROOT, 'data', 'meta_stats.json')
    USERS_FILE = os.path.join(PROJECT_ROOT, 'data', 'users.json')
    
    # Card collection paths
    CARD_CSV_PATH = os.path.join(PROJECT_ROOT, 'pokemon_cards.csv')
    CARD_DB_PATH = os.path.join(PROJECT_ROOT, 'pokemon_cards.db')
    
    # Flask configurations
    DEBUG = True
    TESTING = False
    
    # Additional configurations can be added here
    # For example:
    # MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    # PREFERRED_URL_SCHEME = 'https'

class DevelopmentConfig(Config):
    """Configuration for development environment."""
    DEBUG = True

class ProductionConfig(Config):
    """Configuration for production environment."""
    DEBUG = False
    # Add production-specific configurations here

class TestingConfig(Config):
    """Configuration for testing environment."""
    TESTING = True
    # Add testing-specific configurations here

# Choose the appropriate configuration
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
