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
    
    # Import Firebase modules
    import firebase_admin
    from firebase_admin import credentials, firestore
    import json
    import tempfile
    
    # Clear any existing Firebase apps to ensure clean initialization
    try:
        firebase_admin.delete_app(firebase_admin.get_app())
    except ValueError:
        pass  # No app to delete
    
    # Create a minimal dummy credentials file for emulator use
    dummy_creds = {
        "type": "service_account",
        "project_id": "demo-test-project",
        "private_key_id": "dummy",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF32yr5HsbeKlDmIzil6MwNP3LJxF\nHNLiVlDpUEY8K1E95ThFqbxd5rXhXqW/5VHGhKYH6/cR1H4O5L+MhcEfPIPKHWtP\nLjAzNxYJZF7nEO5Q1mEBqAEF6m2RKK+MqJyVr6p3On3Fni04SYuFVw1UYwj4lQHx\n9C8Xbpix5Kl8rJPvw6kMhW7GkU6WR0VH5ls9eqTBrCTivzSVWsUPHa3T4CWbB5Y5\ny6DkuZkWtGmWEMPh2kH+5hEaKJR8ByrTYMXXDmOGLxiVP0qCPcie+FLHmQSfzoNS\nXQmj7qKDPqIJYGHUgmQMuVCda+BpjQsjQu8aOQIDAQABAoIBAQCi6q+Q0DMXM7g/\nNxMPz8TG7gp6Xh4J3rPfTO4u7MN2K9V2dLu5nPgu1iwNWy0FEOr8Qrp7OGMF3gXQ\nWl0FVzD0lHJBcr9m8Bxjd4TEAGpMfqJBGe1KfLqmQpHPB5fYKzw/Z9lCJW1d3L3g\nlIsVEYNz/lEAqGMTF9glR6FO0S3D8uyJ7KIqCqmGpJZkiDh7gB1mD/VdstMiWWMF\nONJEJUm3jtTVJOa6VJHsX7Uj9x3e/DyNND7y3bjI28qC8FtGl+0E1po5K2o9Qhqk\nLdU9Y/kZ8LtqT5t3XN8DF+rCMZT6rUl/COHpDYNYvNBJVUzQW3SAH9q1PYo+/ioN\n6czF7EGxAoGBAPX6h6K/1w2Gb6JUmZF+oZVgJlBFCbfQYF7Cz4EJb2wPCMLMJUFx\nDZB++J5nSQ3GQSJ9MfHIJeLanwJkla2DPaKtqbEOUbjtLpH0GirtQ3P/8IXvpNK5\niFSAFqzWgzI4G8r2mVUe2yIwYaFWsnE9WkJkNGX1cD9jiVN/3vCyXTj9AoGBANqK\nNDYWyE0DEXdgKz1clvLdVRxBuAkBNadVZDhtSQMMKvMNwfSRSEdaGTOYQD9qf+U9\n4OwWWXQ+6JU+kB39+JoRJvgSFAuNEJHGfKxGRdRSIiTSlhtcNJw7nSr9Oj4pN7/k\nyKBNI+mJqGZHa3N8KfZIncaLQrfVTmXVRl4rHFY9AoGBAMQy0kfWGcRFI4HZDUJj\nrVDKaiYXBowZHpTRCnVdRlJmLNJIXUmg0ePlBkqNvF2TpFseiHGXYDeWMSbc8PYO\nWO8H6dLmgLmBrZk4xMWf3Bq9FQeeKPTTPNhfSUmgTdVMdGHklYQZzpJcO1d3Un5V\npDHkj8hFbW6j0LcWjEK1iVLNAoGABEV8CxCTcE5nBOCOr9LPGjQxLLZBc4DUf5HW\nPhBPKxZbsxqI5573hSrPJ6uOWx+8MOcaWQA2gJdjDnPQdFl0TQU0EJ0WhZTCKgqV\nvhe7AhxKPCU3dJC1AbMXQpCLaghH8Hk9s5vKKLNVMELHqVyp2U/F7kTKlJ5lPiVT\nFzKZPD0CgYA4Z6IZIUA1qNqH0IUj1XvQr8mQv1qmU9BpB0R1YWr5g4gR+Wvq9Xet\n/mZcgZCbb3SJFXK5sFoRuVBD6VFMKFBBTGaHdFQfQXvdRaj8KitQGwJDBpklRmDJ\nq2T9p7Ah2CM2pXFaRqC5YeWVIKkCPBWow2hun7vPVQsYv3c8b/fVxA==\n-----END RSA PRIVATE KEY-----\n",
        "client_email": "dummy@demo-test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/dummy%40demo-test-project.iam.gserviceaccount.com"
    }
    
    # Write dummy credentials to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(dummy_creds, f)
        dummy_creds_path = f.name
    
    # Set the credentials path
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = dummy_creds_path
    
    # Create app with real Firebase connection (no mocking)
    app = create_app('testing')
    
    # Clean up the temp file
    try:
        os.unlink(dummy_creds_path)
    except:
        pass
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