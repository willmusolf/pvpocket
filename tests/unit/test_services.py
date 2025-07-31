"""
Unit tests for services functionality.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from Card import CardCollection, Card

from app.services import CardService, UserService


@pytest.mark.unit
class TestCardService:
    """Test CardService functionality."""
    
    def test_get_sample_card_collection(self):
        """Test sample card collection creation."""
        collection = CardService._get_sample_card_collection()
        
        assert isinstance(collection, CardCollection)
        assert len(collection) == 3
        
        # Check specific cards
        pikachu = collection.get_card_by_id(1)
        assert pikachu is not None
        assert pikachu.name == "Pikachu"
        assert pikachu.energy_type == "Lightning"
        assert pikachu.hp == 60
        
        charizard = collection.get_card_by_id(2)
        assert charizard is not None
        assert charizard.name == "Charizard"
        assert charizard.energy_type == "Fire"
        assert charizard.hp == 120
        
        blastoise = collection.get_card_by_id(3)
        assert blastoise is not None
        assert blastoise.name == "Blastoise"
        assert blastoise.energy_type == "Water"
        assert blastoise.hp == 100
    
    def test_priority_sets_defined(self):
        """Test that priority sets are properly defined."""
        assert len(CardService.PRIORITY_SETS) == 5
        assert "Eevee Grove" in CardService.PRIORITY_SETS
        assert "Extradimensional Crisis" in CardService.PRIORITY_SETS
        assert "Celestial Guardians" in CardService.PRIORITY_SETS
    
    @patch('app.services.cache_manager')
    def test_get_card_collection_from_cache(self, mock_cache):
        """Test getting card collection from cache."""
        mock_collection = MagicMock()
        mock_cache.get_card_collection.return_value = mock_collection
        
        result = CardService.get_card_collection()
        
        assert result == mock_collection
        mock_cache.get_card_collection.assert_called_once()
    
    @patch('app.services.cache_manager')
    @patch('app.services.CardService._get_sample_card_collection')
    def test_get_card_collection_cache_miss_development(self, mock_sample, mock_cache):
        """Test fallback to sample collection in development when cache misses."""
        mock_cache.get_card_collection.return_value = None
        mock_sample_collection = MagicMock()
        mock_sample.return_value = mock_sample_collection
        
        with patch('os.environ.get', return_value='development'):
            result = CardService.get_card_collection()
            
            assert result == mock_sample_collection
            mock_sample.assert_called_once()
    
    @patch('app.services.threading.Thread')
    def test_background_loading_thread_creation(self, mock_thread):
        """Test background loading thread creation."""
        CardService._trigger_background_loading()
        
        mock_thread.assert_called_once()
        # Verify thread was started
        mock_thread.return_value.start.assert_called_once()
    
    def test_background_loading_lock_prevents_duplicate(self):
        """Test that background loading lock prevents duplicate loading."""
        # Set loading as active
        CardService._background_loading_active = True
        
        with patch('app.services.threading.Thread') as mock_thread:
            CardService._trigger_background_loading()
            
            # Should not create thread when already loading
            mock_thread.assert_not_called()
        
        # Reset for other tests
        CardService._background_loading_active = False


@pytest.mark.unit 
class TestUserService:
    """Test UserService functionality."""
    
    @patch('app.services.cache_manager')
    def test_get_user_collection_from_cache(self, mock_cache):
        """Test getting user collection from cache."""
        user_id = "test-user-123"
        mock_collection = {"card-1": {"count": 2}, "card-2": {"count": 1}}
        mock_cache.get_user_collection.return_value = mock_collection
        
        result = UserService.get_user_collection(user_id)
        
        assert result == mock_collection
        mock_cache.get_user_collection.assert_called_once_with(user_id)
    
    @patch('app.services.cache_manager')
    @patch('app.services.db_service')
    def test_get_user_collection_cache_miss_firestore_success(self, mock_db, mock_cache):
        """Test getting user collection from Firestore when cache misses."""
        user_id = "test-user-123"
        mock_cache.get_user_collection.return_value = None
        
        firestore_data = {"card-1": {"count": 2}, "card-2": {"count": 1}}
        mock_db.get_document.return_value = {"collection": firestore_data}
        
        result = UserService.get_user_collection(user_id)
        
        assert result == firestore_data
        mock_db.get_document.assert_called_once_with("users", user_id)
        mock_cache.set_user_collection.assert_called_once_with(user_id, firestore_data, ttl_hours=24)
    
    @patch('app.services.cache_manager')
    @patch('app.services.db_service')
    def test_get_user_collection_cache_miss_no_firestore_data(self, mock_db, mock_cache):
        """Test getting user collection when no data exists."""
        user_id = "test-user-123"
        mock_cache.get_user_collection.return_value = None
        mock_db.get_document.return_value = None
        
        result = UserService.get_user_collection(user_id)
        
        assert result == {}
        mock_cache.set_user_collection.assert_not_called()
    
    @patch('app.services.cache_manager')
    @patch('app.services.db_service')
    def test_save_user_collection_success(self, mock_db, mock_cache):
        """Test saving user collection successfully."""
        user_id = "test-user-123"
        collection_data = {"card-1": {"count": 3}, "card-2": {"count": 2}}
        
        mock_db.update_document.return_value = True
        
        result = UserService.save_user_collection(user_id, collection_data)
        
        assert result is True
        mock_db.update_document.assert_called_once_with(
            "users", user_id, {"collection": collection_data}, merge=True
        )
        mock_cache.set_user_collection.assert_called_once_with(user_id, collection_data, ttl_hours=24)
    
    @patch('app.services.cache_manager')
    @patch('app.services.db_service')
    def test_save_user_collection_firestore_failure(self, mock_db, mock_cache):
        """Test handling of Firestore save failure."""
        user_id = "test-user-123"
        collection_data = {"card-1": {"count": 3}}
        
        mock_db.update_document.return_value = False
        
        result = UserService.save_user_collection(user_id, collection_data)
        
        assert result is False
        mock_cache.set_user_collection.assert_not_called()
    
    @patch('app.services.cache_manager')
    def test_invalidate_user_cache(self, mock_cache):
        """Test user cache invalidation."""
        user_id = "test-user-123"
        
        UserService.invalidate_user_cache(user_id)
        
        mock_cache.invalidate_user_cache.assert_called_once_with(user_id)
    
    @patch('app.services.db_service')
    def test_get_user_decks_success(self, mock_db):
        """Test getting user decks successfully."""
        user_id = "test-user-123"
        mock_decks = [
            {"id": "deck1", "name": "My Deck 1"},
            {"id": "deck2", "name": "My Deck 2"}
        ]
        mock_db.query_collection.return_value = mock_decks
        
        result = UserService.get_user_decks(user_id)
        
        assert result == mock_decks
        mock_db.query_collection.assert_called_once_with(
            "decks",
            filters=[("owner_id", "==", user_id)],
            order_by="updated_at",
            limit=50
        )
    
    @patch('app.services.db_service')
    def test_get_user_decks_empty_result(self, mock_db):
        """Test getting user decks when none exist."""
        user_id = "test-user-123"
        mock_db.query_collection.return_value = []
        
        result = UserService.get_user_decks(user_id)
        
        assert result == []
    
    @patch('app.services.db_service')
    def test_create_user_deck_success(self, mock_db):
        """Test creating user deck successfully."""
        user_id = "test-user-123"
        deck_data = {
            "name": "Test Deck",
            "cards": [{"card_id": 1, "count": 2}],
            "owner_id": user_id
        }
        
        mock_db.create_document.return_value = "deck123"
        
        result = UserService.create_user_deck(user_id, deck_data)
        
        assert result == "deck123"
        # Verify the deck data includes timestamps and owner
        create_call_args = mock_db.create_document.call_args[0]
        assert create_call_args[0] == "decks"
        deck_data_sent = create_call_args[1]
        assert deck_data_sent["owner_id"] == user_id
        assert "created_at" in deck_data_sent
        assert "updated_at" in deck_data_sent
    
    @patch('app.services.db_service')
    def test_update_user_deck_success(self, mock_db):
        """Test updating user deck successfully."""
        user_id = "test-user-123"
        deck_id = "deck123"
        updates = {"name": "Updated Deck Name"}
        
        mock_db.update_document.return_value = True
        
        result = UserService.update_user_deck(user_id, deck_id, updates)
        
        assert result is True
        # Verify update includes timestamp
        update_call_args = mock_db.update_document.call_args[0]
        updates_sent = update_call_args[2]
        assert "updated_at" in updates_sent
        assert updates_sent["name"] == "Updated Deck Name"
    
    @patch('app.services.db_service')
    def test_delete_user_deck_success(self, mock_db):
        """Test deleting user deck successfully."""
        user_id = "test-user-123"
        deck_id = "deck123"
        
        mock_db.delete_document.return_value = True
        
        result = UserService.delete_user_deck(user_id, deck_id)
        
        assert result is True
        mock_db.delete_document.assert_called_once_with("decks", deck_id)


@pytest.mark.unit
class TestServiceHelpers:
    """Test service helper functions."""
    
    def test_priority_sets_ordering(self):
        """Test that priority sets are in correct order."""
        priority_sets = CardService.PRIORITY_SETS
        
        # Should be ordered from most recent to older
        assert priority_sets[0] == "Eevee Grove"  # Most recent
        assert priority_sets[-1] == "Triumphant Light"  # Oldest in priority
    
    @patch('app.services.firestore.SERVER_TIMESTAMP')
    def test_timestamp_generation(self, mock_timestamp):
        """Test that services generate proper timestamps."""
        mock_timestamp_value = "2024-01-01T00:00:00Z"
        mock_timestamp.return_value = mock_timestamp_value
        
        # This tests that the import and usage pattern works
        from app.services import firestore
        timestamp = firestore.SERVER_TIMESTAMP
        
        assert timestamp == mock_timestamp_value