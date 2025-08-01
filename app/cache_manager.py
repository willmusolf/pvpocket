"""
In-memory cache manager for improving performance.
Provides thread-safe caching without external dependencies.
"""

import json
import pickle
import os
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import threading
from flask import current_app
from Card import CardCollection


class InMemoryCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self):
        self._data = {}
        self._expiry = {}
        self._lock = threading.Lock()
    
    def get(self, key):
        with self._lock:
            # Check if key exists and hasn't expired
            if key in self._data:
                if key in self._expiry and datetime.now() > self._expiry[key]:
                    # Expired - remove it
                    del self._data[key]
                    del self._expiry[key]
                    return None
                return self._data[key]
            return None
    
    def set(self, key, value, ex=None):
        with self._lock:
            self._data[key] = value
            if ex:
                if isinstance(ex, timedelta):
                    self._expiry[key] = datetime.now() + ex
                else:  # seconds
                    self._expiry[key] = datetime.now() + timedelta(seconds=ex)
            return True
    
    def delete(self, key):
        with self._lock:
            self._data.pop(key, None)
            self._expiry.pop(key, None)
            return 1
    
    def exists(self, key):
        with self._lock:
            if key in self._data:
                # Check expiry
                if key in self._expiry and datetime.now() > self._expiry[key]:
                    return False
                return True
            return False
    
    def ping(self):
        return True
    
    def flushdb(self):
        with self._lock:
            self._data.clear()
            self._expiry.clear()
            return True


class CacheManager:
    """In-memory cache manager for scalable caching operations."""
    
    def __init__(self):
        """Initialize in-memory cache manager."""
        self._client = InMemoryCache()
        # Only log in debug mode
        from flask import current_app
        if current_app and current_app.debug:
            print("✅ CACHE: Using in-memory cache system")
    
    @property
    def client(self):
        """Get the cache client."""
        return self._client
    
    def get_card_collection(self, cache_key: str = "global_cards") -> Optional[CardCollection]:
        """Get card collection from cache."""
        try:
            cached_data = self.client.get(f"cards:{cache_key}")
            if cached_data:
                collection = pickle.loads(cached_data)
                # Record cache hit
                try:
                    from .monitoring import performance_monitor
                    performance_monitor.metrics.record_cache_hit("card_collection")
                except ImportError:
                    pass
                return collection
            # Record cache miss
            try:
                from .monitoring import performance_monitor
                performance_monitor.metrics.record_cache_miss("card_collection")
            except ImportError:
                pass
            return None
        except Exception as e:
            # Record cache error
            try:
                from .monitoring import performance_monitor
                performance_monitor.metrics.record_cache_error("card_collection")
            except ImportError:
                pass
            return None
    
    def set_card_collection(self, collection: CardCollection, cache_key: str = "global_cards", ttl_hours: int = 24) -> bool:
        """Cache card collection with TTL."""
        try:
            pickled_data = pickle.dumps(collection)
            ttl = timedelta(hours=ttl_hours)
            return self.client.set(f"cards:{cache_key}", pickled_data, ex=ttl)
        except Exception as e:
            # Only log in debug mode
            from flask import current_app
            if current_app and current_app.debug:
                print(f"Error caching card collection: {e}")
            return False
    
    def get_user_data(self, user_id: str) -> Optional[Dict]:
        """Get cached user data."""
        try:
            cached_data = self.client.get(f"user:{user_id}")
            if cached_data:
                try:
                    from .monitoring import performance_monitor
                    performance_monitor.metrics.record_cache_hit("user_data")
                except ImportError:
                    pass
                return json.loads(cached_data)
            try:
                from .monitoring import performance_monitor
                performance_monitor.metrics.record_cache_miss("user_data")
            except ImportError:
                pass
            return None
        except Exception as e:
            try:
                from .monitoring import performance_monitor
                performance_monitor.metrics.record_cache_error("user_data")
            except ImportError:
                pass
            return None
    
    def set_user_data(self, user_id: str, user_data: Dict, ttl_minutes: int = 120) -> bool:
        """Cache user data with TTL."""
        try:
            # Convert Firestore datetime objects to strings
            serializable_data = self._make_serializable(user_data)
            json_data = json.dumps(serializable_data)
            ttl = timedelta(minutes=ttl_minutes)
            return self.client.set(f"user:{user_id}", json_data, ex=ttl)
        except Exception as e:
            # Only log in debug mode
            from flask import current_app
            if current_app and current_app.debug:
                print(f"Error caching user data: {e}")
            return False
    
    def _make_serializable(self, obj):
        """Convert Firestore objects to JSON serializable format."""
        import json
        from datetime import datetime
        
        if hasattr(obj, '__dict__'):
            # Convert object to dict
            obj = obj.__dict__
        
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                result[key] = self._make_serializable(value)
            return result
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif hasattr(obj, 'timestamp'):  # Firestore DatetimeWithNanoseconds
            return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            # Try to serialize, if it fails convert to string
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)
    
    def get_user_collection(self, user_id: str) -> Optional[Dict]:
        """Get user's personal card collection."""
        try:
            cached_data = self.client.get(f"user_collection:{user_id}")
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            # Only log in debug mode
            from flask import current_app
            if current_app and current_app.debug:
                print(f"Error retrieving user collection from cache: {e}")
            return None
    
    def set_user_collection(self, user_id: str, collection_data: Dict, ttl_hours: int = 6) -> bool:
        """Cache user's personal collection."""
        try:
            serializable_data = self._make_serializable(collection_data)
            json_data = json.dumps(serializable_data)
            ttl = timedelta(hours=ttl_hours)
            return self.client.set(f"user_collection:{user_id}", json_data, ex=ttl)
        except Exception as e:
            # Only log in debug mode
            from flask import current_app
            if current_app and current_app.debug:
                print(f"Error caching user collection: {e}")
            return False
    
    def get_user_decks(self, user_id: str) -> Optional[List[Dict]]:
        """Get cached user decks."""
        try:
            cached_data = self.client.get(f"user_decks:{user_id}")
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            # Only log in debug mode
            from flask import current_app
            if current_app and current_app.debug:
                print(f"Error retrieving user decks from cache: {e}")
            return None
    
    def set_user_decks(self, user_id: str, decks_data: List[Dict], ttl_hours: int = 2) -> bool:
        """Cache user decks."""
        try:
            serializable_data = self._make_serializable(decks_data)
            json_data = json.dumps(serializable_data)
            ttl = timedelta(hours=ttl_hours)
            return self.client.set(f"user_decks:{user_id}", json_data, ex=ttl)
        except Exception as e:
            # Only log in debug mode
            from flask import current_app
            if current_app and current_app.debug:
                print(f"Error caching user decks: {e}")
            return False
    
    def invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate all cached data for a user."""
        try:
            keys_to_delete = [
                f"user:{user_id}",
                f"user_collection:{user_id}",
                f"user_decks:{user_id}"
            ]
            for key in keys_to_delete:
                self.client.delete(key)
            # Only log in debug mode
            from flask import current_app
            if current_app and current_app.debug:
                print(f"Invalidated cache for user {user_id}")
        except Exception as e:
            if current_app and current_app.debug:
                print(f"Error invalidating user cache: {e}")
    
    def invalidate_card_cache(self, cache_key: str = "global_cards") -> None:
        """Invalidate card collection cache."""
        try:
            self.client.delete(f"cards:{cache_key}")
            # Only log in debug mode
            from flask import current_app
            if current_app and current_app.debug:
                print(f"Invalidated card cache: {cache_key}")
        except Exception as e:
            if current_app and current_app.debug:
                print(f"Error invalidating card cache: {e}")
    
    def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            self.client.ping()
            return True
        except Exception:
            return False


# Global cache manager instance
cache_manager = CacheManager()