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
    
    # Configure Firebase emulator environment variables
    os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
    os.environ['FIREBASE_STORAGE_EMULATOR_HOST'] = 'localhost:9199'
    
    # Mock Firebase to avoid external dependencies
    with patch('firebase_admin.initialize_app'), \
         patch('firebase_admin.firestore.client') as mock_firestore, \
         patch('firebase_admin.storage.bucket'), \
         patch('app.services.CardService.get_full_card_collection') as mock_card_service:
        
        # Configure mock Firestore with better defaults
        mock_db = Mock()
        # Mock collection() method to return empty collections by default
        mock_collection = Mock()
        mock_collection.stream.return_value = []  # Empty collection
        mock_db.collection.return_value = mock_collection
        mock_firestore.return_value = mock_db
        
        # Mock card service to provide test data
        from Card import CardCollection, Card
        test_collection = CardCollection()
        test_card = Card(
            id=1,
            name="Test Card",
            energy_type="Fire",
            set_name="Test Set",
            hp=100
        )
        test_collection.add_card(test_card)
        mock_card_service.return_value = test_collection
        
        app = create_app('testing')
        app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'FIRESTORE_DB': mock_db,
            'SECRET_KEY': 'test-secret-key-for-pytest',
            'REFRESH_SECRET_KEY': 'test-refresh-key'
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


@pytest.fixture(scope="session")
def real_firebase_app():
    """Create application with real Firebase emulator connection for integration tests."""
    # Only create if we're running integration tests
    if not os.environ.get('RUN_INTEGRATION_TESTS'):
        return None
        
    # Set test environment variables
    os.environ['FLASK_CONFIG'] = 'testing'
    os.environ['SECRET_KEY'] = 'test-secret-key-for-pytest'
    os.environ['REFRESH_SECRET_KEY'] = 'test-refresh-key'
    os.environ['GCP_PROJECT_ID'] = 'demo-test-project'
    os.environ['FIREBASE_SECRET_NAME'] = 'test-secret'
    
    # Configure Firebase emulator environment variables
    os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
    os.environ['FIREBASE_STORAGE_EMULATOR_HOST'] = 'localhost:9199'
    
    # Check if emulator is running before attempting to connect
    import socket
    def is_emulator_running(host, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    if not is_emulator_running('localhost', 8080):
        pytest.skip("Firebase emulator not running on localhost:8080")
        return None
    
    # Don't initialize Firebase here - let create_app handle it
    # The app initialization already has logic to detect and use emulators
    
    # Create app with real Firebase connection (no mocking)
    app = create_app('testing')
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key-for-pytest',
        'REFRESH_SECRET_KEY': 'test-refresh-key'
    })
    
    return app


@pytest.fixture
def real_firebase_client(real_firebase_app):
    """Create test client with real Firebase emulator connection."""
    if not real_firebase_app:
        pytest.skip("Real Firebase tests require RUN_INTEGRATION_TESTS=1")
    return real_firebase_app.test_client()


@pytest.fixture(autouse=True)
def reset_cache(cache_manager):
    """Reset cache before each test."""
    if hasattr(cache_manager, 'client'):
        cache_manager.client.flushdb()
    yield
    if hasattr(cache_manager, 'client'):
        cache_manager.client.flushdb()