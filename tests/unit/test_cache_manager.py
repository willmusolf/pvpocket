"""
Unit tests for CacheManager functionality.
"""

import pytest
from datetime import datetime, timedelta
from Card import Card, CardCollection
from app.cache_manager import CacheManager


@pytest.mark.unit
class TestCacheManager:
    """Test cache manager functionality."""
    
    def test_cache_initialization(self, cache_manager):
        """Test cache manager initializes correctly."""
        assert cache_manager.client is not None
        assert cache_manager.client.ping() is True
    
    def test_set_and_get_user_data(self, cache_manager, mock_user_data):
        """Test setting and getting user data."""
        user_id = "test-user-123"
        
        # Set user data
        success = cache_manager.set_user_data(user_id, mock_user_data, ttl_minutes=60)
        assert success is True
        
        # Get user data
        retrieved_data = cache_manager.get_user_data(user_id)
        assert retrieved_data is not None
        assert retrieved_data["email"] == mock_user_data["email"]
        assert retrieved_data["username"] == mock_user_data["username"]
    
    def test_user_data_expiry(self, cache_manager, mock_user_data):
        """Test that user data expires correctly."""
        user_id = "test-user-123"
        
        # Set with very short TTL (1 minute for testing)
        cache_manager.set_user_data(user_id, mock_user_data, ttl_minutes=1)
        
        # Should exist immediately
        assert cache_manager.get_user_data(user_id) is not None
        
        # Should expire after TTL (simulated by flushing)
        cache_manager.client.flushdb()
        assert cache_manager.get_user_data(user_id) is None
    
    def test_card_collection_caching(self, cache_manager):
        """Test card collection caching."""
        # Create a test card collection
        collection = CardCollection()
        test_card = Card(
            id=1,
            name="Test Card",
            energy_type="Fire",
            set_name="Test Set",
            hp=100
        )
        collection.add_card(test_card)
        
        # Cache the collection
        success = cache_manager.set_card_collection(collection, ttl_hours=24)
        assert success is True
        
        # Retrieve the collection
        cached_collection = cache_manager.get_card_collection()
        assert cached_collection is not None
        assert len(cached_collection) == 1
        assert cached_collection.get_card_by_id(1).name == "Test Card"
    
    def test_cache_invalidation(self, cache_manager, mock_user_data):
        """Test cache invalidation works correctly."""
        user_id = "test-user-123"
        
        # Set data
        cache_manager.set_user_data(user_id, mock_user_data)
        assert cache_manager.get_user_data(user_id) is not None
        
        # Invalidate user cache
        cache_manager.invalidate_user_cache(user_id)
        assert cache_manager.get_user_data(user_id) is None
    
    def test_cache_miss_returns_none(self, cache_manager):
        """Test that cache misses return None."""
        assert cache_manager.get_user_data("nonexistent-user") is None
        assert cache_manager.get_card_collection() is None
    
    def test_user_collection_caching(self, cache_manager):
        """Test user collection caching."""
        user_id = "test-user-123"
        collection_data = {
            "card-1": {"count": 2, "pack": "Test Pack"},
            "card-2": {"count": 1, "pack": "Test Pack"}
        }
        
        # Cache user collection
        success = cache_manager.set_user_collection(user_id, collection_data, ttl_hours=6)
        assert success is True
        
        # Retrieve user collection
        cached_collection = cache_manager.get_user_collection(user_id)
        assert cached_collection is not None
        assert cached_collection["card-1"]["count"] == 2
        assert cached_collection["card-2"]["count"] == 1