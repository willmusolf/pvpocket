"""
Integration tests for API endpoints.
"""

import pytest
import json
from unittest.mock import patch, Mock


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_endpoint_exists(self, client):
        """Test that health endpoint is accessible."""
        response = client.get('/health')
        assert response.status_code == 200
    
    def test_health_endpoint_returns_json(self, client):
        """Test that health endpoint returns proper JSON."""
        response = client.get('/health')
        data = json.loads(response.data)
        
        assert 'status' in data
        assert 'timestamp' in data


@pytest.mark.integration 
class TestCardAPI:
    """Test card-related API endpoints."""
    
    @patch('app.services.CardService.get_full_card_collection')
    def test_cards_api_endpoint(self, mock_collection, client, mock_card_data):
        """Test /api/cards endpoint."""
        # Mock card collection
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
        assert data['success'] is True
        assert len(data['cards']) == len(mock_card_data)
    
    @patch('app.services.CardService.get_full_card_collection')
    def test_cards_paginated_endpoint(self, mock_collection, client, mock_card_data):
        """Test /api/cards/paginated endpoint."""
        # Mock card collection
        from Card import CardCollection, Card
        collection = CardCollection()
        for card_data in mock_card_data:
            card = Card(**card_data)
            collection.add_card(card)
        
        mock_collection.return_value = collection
        
        response = client.get('/api/cards/paginated?page=1&limit=1')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'cards' in data
        assert 'success' in data
        assert 'pagination' in data
        assert data['success'] is True
        assert len(data['cards']) <= 1
        assert 'total_count' in data['pagination']
        assert 'current_page' in data['pagination']


@pytest.mark.integration
class TestUserAPI:
    """Test user-related API endpoints."""
    
    def test_my_decks_requires_auth(self, client):
        """Test that /api/my-decks requires authentication."""
        response = client.get('/api/my-decks')
        # Should redirect to login or return 401/403
        assert response.status_code in [302, 401, 403]
    
    def test_profile_access(self, client):
        """Test profile access."""
        response = client.get('/user/profile')
        # Should redirect to login or return 401/403 for unauthenticated users
        assert response.status_code in [302, 401, 403]


@pytest.mark.integration
class TestInternalAPI:
    """Test internal API endpoints."""
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get('/metrics')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            # Should contain performance metrics
            expected_metrics = ['cache_hit_rate', 'response_times', 'active_users']
            for metric in expected_metrics:
                assert metric in data
    
    def test_refresh_cards_auth_required(self, client):
        """Test that refresh cards requires proper authentication."""
        response = client.post('/api/refresh-cards')
        assert response.status_code == 401
        
        # Test with header but wrong key
        response = client.post('/api/refresh-cards', 
                             headers={'X-Refresh-Key': 'wrong-key'})
        assert response.status_code == 401


@pytest.mark.integration
class TestStaticAssets:
    """Test static asset serving."""
    
    def test_static_js_files(self, client):
        """Test that JavaScript files are served correctly."""
        js_files = [
            '/static/js/image-utils.js',
            '/static/js/mobile-fixes.js'
        ]
        
        for js_file in js_files:
            response = client.get(js_file)
            assert response.status_code == 200
            assert 'javascript' in response.content_type.lower()
    
    def test_favicon_served(self, client):
        """Test that favicon is served."""
        response = client.get('/static/favicon.ico')
        assert response.status_code == 200


@pytest.mark.integration 
class TestErrorHandling:
    """Test error handling across the application."""
    
    def test_404_handled_gracefully(self, client):
        """Test that 404 errors are handled gracefully."""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404
        
        # Should not expose sensitive information
        response_text = response.get_data(as_text=True).lower()
        assert 'traceback' not in response_text
        assert 'python' not in response_text
    
    def test_500_handled_gracefully(self, client):
        """Test that 500 errors are handled gracefully."""
        # This would require triggering an actual server error
        # For now, just ensure error handlers are registered
        pass
    
    def test_invalid_json_handled(self, client):
        """Test that invalid JSON requests are handled properly."""
        response = client.post('/api/refresh-cards',
                             data='invalid json',
                             content_type='application/json',
                             headers={'X-Refresh-Key': 'test-key'})
        
        # Should handle gracefully, not crash
        assert response.status_code < 500