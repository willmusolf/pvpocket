"""
Integration tests that use real Firebase emulator data.
These tests are slower but test actual Firebase interactions.
"""

import pytest
import json
import os
from pathlib import Path


@pytest.mark.integration
@pytest.mark.real_data
class TestRealDataIntegration:
    """Tests that require real Firebase emulator data."""
    
    @pytest.fixture(scope="class", autouse=True)
    def seed_firebase_data(self, app):
        """Verify Firebase emulator has test data (seeded by CI workflow)."""
        # Only run if we're in integration test mode
        if not os.environ.get('RUN_INTEGRATION_TESTS'):
            pytest.skip("Skipping real data tests - set RUN_INTEGRATION_TESTS=1")
            
        # Check if Firebase emulator is running
        import requests
        try:
            response = requests.get('http://localhost:8080')
            if response.status_code != 200:
                pytest.skip("Firebase emulator not running")
        except:
            pytest.skip("Firebase emulator not reachable")
            
        # Test data should already be seeded by CI workflow
        # Just verify we can access the database
        db = app.config.get('FIRESTORE_DB')
        if not db:
            pytest.skip("Firestore database not configured")
            
        yield
        
        # No cleanup needed - emulator is ephemeral in CI
    
    def test_real_cards_api(self, client):
        """Test /api/cards with real Firebase data."""
        response = client.get('/api/cards')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'cards' in data
        assert len(data['cards']) >= 10  # We seeded 10 cards
        
        # Check specific cards exist
        card_names = [card['name'] for card in data['cards']]
        assert 'Pikachu' in card_names
        assert 'Charizard' in card_names
    
    def test_real_card_collection_loading(self, client):
        """Test that card collection loads properly from Firebase."""
        response = client.get('/api/cards/paginated?limit=10')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['pagination']['total_count'] >= 10
        assert len(data['cards']) >= 10
    
    def test_real_deck_operations(self, client):
        """Test deck operations with real data."""
        # This would require authenticated user
        # For now, just test that the endpoint exists
        response = client.get('/api/decks/test-deck-1')
        # Can be 302 (redirect to login), 401, or 403 without auth - all expected
        assert response.status_code in [200, 302, 401, 403]