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
    
    def test_real_cards_api(self, real_firebase_client):
        """Test /api/cards with real Firebase data."""
        # The seeding should have been done by the CI/CD script
        response = real_firebase_client.get('/api/cards')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'cards' in data
        assert len(data['cards']) >= 2  # We seeded 2 cards
        
        # Check specific cards exist
        card_names = [card['name'] for card in data['cards']]
        assert 'Pikachu' in card_names
        assert 'Charizard' in card_names
    
    def test_real_card_collection_loading(self, real_firebase_client):
        """Test that card collection loads properly from Firebase."""
        response = real_firebase_client.get('/api/cards/paginated?limit=10')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['pagination']['total_count'] >= 2
        assert len(data['cards']) >= 2
    
    def test_real_deck_operations(self, real_firebase_client):
        """Test deck operations with real data."""
        # This would require authenticated user
        # For now, just test that the endpoint exists
        response = real_firebase_client.get('/api/decks/test-deck-1')
        # Can be 302 (redirect to login), 401, or 403 without auth - all expected
        assert response.status_code in [200, 302, 401, 403]