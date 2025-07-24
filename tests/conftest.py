"""
Pytest configuration and fixtures for Pokemon TCG Pocket App tests.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from app import create_app
from app.cache_manager import CacheManager


@pytest.fixture(scope="session")
def app():
    """Create application for testing session."""
    # Set test environment variables
    os.environ['FLASK_CONFIG'] = 'testing'
    os.environ['SECRET_KEY'] = 'test-secret-key-for-pytest'
    os.environ['REFRESH_SECRET_KEY'] = 'test-refresh-key'
    os.environ['GCP_PROJECT_ID'] = 'test-project'
    os.environ['FIREBASE_SECRET_NAME'] = 'test-secret'
    
    # Mock Firebase to avoid external dependencies
    with patch('firebase_admin.initialize_app'), \
         patch('firebase_admin.firestore.client') as mock_firestore, \
         patch('firebase_admin.storage.bucket'):
        
        # Configure mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        app = create_app('testing')
        app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'FIRESTORE_DB': mock_db
        })
        
        return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def cache_manager():
    """Create clean cache manager for each test."""
    return CacheManager()


@pytest.fixture
def mock_user_data():
    """Mock user data for testing."""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "username": "testuser",
        "profile_icon": "default.png",
        "collection": {
            "card-1": {"count": 2, "pack": "Charizard Pack"},
            "card-2": {"count": 1, "pack": "Pikachu Pack"}
        }
    }


@pytest.fixture
def mock_card_data():
    """Mock card data for testing."""
    return [
        {
            "id": 1,
            "name": "Pikachu",
            "energy_type": "Lightning",
            "set_name": "Genetic Apex",
            "hp": 60,
            "rarity": "Common"
        },
        {
            "id": 2,
            "name": "Charizard",
            "energy_type": "Fire", 
            "set_name": "Genetic Apex",
            "hp": 180,
            "rarity": "Rare"
        }
    ]


@pytest.fixture(autouse=True)
def reset_cache(cache_manager):
    """Reset cache before each test."""
    if hasattr(cache_manager, 'client'):
        cache_manager.client.flushdb()
    yield
    if hasattr(cache_manager, 'client'):
        cache_manager.client.flushdb()