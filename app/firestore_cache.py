"""
Firestore-based cache implementation as an alternative to Redis.
Uses your existing Firestore database for caching with TTL support.
"""

import json
import pickle
import base64
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
from flask import current_app
from google.cloud import firestore


class FirestoreCache:
    """Cache implementation using Firestore - no additional infrastructure needed."""
    
    def __init__(self):
        self.collection_name = "_cache"  # Firestore collection for cache
        self._client = None
    
    @property
    def client(self):
        """Get Firestore client from app config."""
        if not self._client:
            self._client = current_app.config.get("FIRESTORE_DB")
        return self._client
    
    def _get_cache_doc(self, key: str):
        """Get cache document reference."""
        return self.client.collection(self.collection_name).document(key)
    
    def get(self, key: str) -> Optional[bytes]:
        """Get value from cache."""
        try:
            doc = self._get_cache_doc(key).get()
            
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            
            # Check if expired
            if 'expires_at' in data:
                expires_at = data['expires_at']
                if isinstance(expires_at, datetime) and expires_at < datetime.utcnow():
                    # Expired - delete and return None
                    self._get_cache_doc(key).delete()
                    return None
            
            # Return the cached value
            value = data.get('value')
            if value and data.get('is_binary'):
                # Decode base64 for binary data
                return base64.b64decode(value)
            elif value:
                return value.encode('utf-8')
            
            return None
            
        except Exception as e:
            print(f"FirestoreCache get error: {e}")
            return None
    
    def set(self, key: str, value: bytes, ex: Optional[timedelta] = None) -> bool:
        """Set value in cache with optional expiration."""
        try:
            data = {
                'updated_at': firestore.SERVER_TIMESTAMP,
                'is_binary': True
            }
            
            # Handle expiration
            if ex:
                if isinstance(ex, int):  # seconds
                    expires_at = datetime.utcnow() + timedelta(seconds=ex)
                else:  # timedelta
                    expires_at = datetime.utcnow() + ex
                data['expires_at'] = expires_at
            
            # Encode binary data as base64
            if isinstance(value, bytes):
                data['value'] = base64.b64encode(value).decode('ascii')
                data['is_binary'] = True
            else:
                data['value'] = str(value)
                data['is_binary'] = False
            
            # Store in Firestore
            self._get_cache_doc(key).set(data)
            return True
            
        except Exception as e:
            print(f"FirestoreCache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            self._get_cache_doc(key).delete()
            return True
        except Exception as e:
            print(f"FirestoreCache delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            doc = self._get_cache_doc(key).get()
            if not doc.exists:
                return False
            
            # Check expiration
            data = doc.to_dict()
            if 'expires_at' in data:
                expires_at = data['expires_at']
                if isinstance(expires_at, datetime) and expires_at < datetime.utcnow():
                    return False
            
            return True
        except:
            return False
    
    def ping(self) -> bool:
        """Health check."""
        try:
            # Try to read a test document
            self.client.collection(self.collection_name).limit(1).get()
            return True
        except:
            return False
    
    def flushdb(self) -> bool:
        """Clear all cache entries (use with caution)."""
        try:
            # Delete all documents in cache collection
            docs = self.client.collection(self.collection_name).stream()
            for doc in docs:
                doc.reference.delete()
            return True
        except Exception as e:
            print(f"FirestoreCache flush error: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """Clean up expired cache entries."""
        try:
            count = 0
            now = datetime.utcnow()
            
            # Query for expired documents
            expired_docs = (
                self.client.collection(self.collection_name)
                .where('expires_at', '<', now)
                .stream()
            )
            
            # Delete expired documents
            for doc in expired_docs:
                doc.reference.delete()
                count += 1
            
            if count > 0:
                print(f"Cleaned up {count} expired cache entries")
            
            return count
            
        except Exception as e:
            print(f"FirestoreCache cleanup error: {e}")
            return 0


# Usage in cache_manager.py:
# Just replace the Redis client with FirestoreCache:
#
# def __init__(self):
#     if USE_FIRESTORE_CACHE:
#         self._client = FirestoreCache()
#     else:
#         # existing Redis code...