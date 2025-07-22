"""
Service layer for handling data access patterns.
Provides clean interfaces for accessing cached data without storing in app config.
"""

from typing import Optional, List, Dict, Any
from flask import current_app
from Card import CardCollection, Card
from .cache_manager import cache_manager
from .db_service import db_service


class CardService:
    """Service for handling card collection operations."""
    
    @staticmethod
    def get_card_collection() -> CardCollection:
        """Get card collection from cache or load from Firestore."""
        # Try Redis cache first
        collection = cache_manager.get_card_collection()
        
        if collection:
            return collection
        
        # If not in cache, load from Firestore
        db_client = current_app.config.get("FIRESTORE_DB")
        if not db_client:
            print("ERROR: Firestore client not available for card loading.")
            return CardCollection()
        
        try:
            print("Loading card collection from Firestore (cache miss)...")
            collection = CardCollection()
            collection.load_from_firestore(db_client)
            
            # Cache for future requests
            cache_manager.set_card_collection(collection, ttl_hours=24)
            print(f"Loaded and cached {len(collection)} cards.")
            
            return collection
        except Exception as e:
            print(f"Error loading card collection: {e}")
            return CardCollection()
    
    @staticmethod
    def get_card_by_id(card_id: int) -> Optional[Card]:
        """Get a specific card by ID."""
        collection = CardService.get_card_collection()
        return collection.get_card_by_id(card_id)
    
    @staticmethod
    def get_cards_by_name(name: str) -> List[Card]:
        """Get cards by name."""
        collection = CardService.get_card_collection()
        return collection.get_cards_by_name(name)
    
    @staticmethod
    def filter_cards(**kwargs) -> List[Card]:
        """Filter cards by various criteria."""
        collection = CardService.get_card_collection()
        return collection.filter(**kwargs)
    
    @staticmethod
    def refresh_card_collection() -> bool:
        """Force refresh of card collection from Firestore."""
        try:
            # Invalidate cache
            cache_manager.invalidate_card_cache()
            
            # Load fresh data
            db_client = current_app.config.get("FIRESTORE_DB")
            if not db_client:
                return False
            
            collection = CardCollection()
            collection.load_from_firestore(db_client)
            
            # Update cache
            cache_manager.set_card_collection(collection, ttl_hours=24)
            
            return True
        except Exception as e:
            print(f"Error refreshing card collection: {e}")
            return False


class UserService:
    """Service for handling user data operations."""
    
    @staticmethod
    def get_user_collection(user_id: str) -> Optional[Dict]:
        """Get user's personal card collection with enhanced database service."""
        # Try cache first
        cached_collection = cache_manager.get_user_collection(user_id)
        if cached_collection:
            return cached_collection
        
        # Load from Firestore using enhanced service
        try:
            user_data = db_service.get_document("users", user_id)
            if user_data:
                collection_data = user_data.get("collection", {})
                
                # Cache for 6 hours
                cache_manager.set_user_collection(user_id, collection_data, ttl_hours=6)
                return collection_data
            
        except Exception as e:
            print(f"Error loading user collection for {user_id}: {e}")
        
        return None
    
    @staticmethod
    def get_user_decks(user_id: str) -> List[Dict]:
        """Get user's decks with enhanced database service and caching."""
        # Try cache first
        cached_decks = cache_manager.get_user_decks(user_id)
        if cached_decks:
            return cached_decks
        
        # Load from Firestore using enhanced service
        try:
            filters = [("user_id", "==", user_id)]
            decks_data = db_service.query_collection("decks", filters=filters)
            
            # Cache for 2 hours
            cache_manager.set_user_decks(user_id, decks_data, ttl_hours=2)
            return decks_data
            
        except Exception as e:
            print(f"Error loading user decks for {user_id}: {e}")
            return []
    
    @staticmethod
    def invalidate_user_cache(user_id: str) -> None:
        """Invalidate all cached data for a user."""
        cache_manager.invalidate_user_cache(user_id)


class MetricsService:
    """Service for tracking application metrics."""
    
    @staticmethod
    def track_cache_hit(cache_type: str) -> None:
        """Track cache hits for monitoring."""
        # This could be expanded to send metrics to monitoring systems
        print(f"Cache hit: {cache_type}")
    
    @staticmethod
    def track_cache_miss(cache_type: str) -> None:
        """Track cache misses for monitoring."""
        print(f"Cache miss: {cache_type}")
    
    @staticmethod
    def track_db_query(query_type: str, duration_ms: int) -> None:
        """Track database query performance."""
        print(f"DB query {query_type}: {duration_ms}ms")


# Convenience instances
card_service = CardService()
user_service = UserService()
metrics_service = MetricsService()