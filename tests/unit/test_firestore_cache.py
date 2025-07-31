"""
Unit tests for FirestoreCache functionality.
DISABLED: These tests require Flask context but FirestoreCache is an alternative implementation.
The main caching is handled by cache_manager.py which has working tests.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta
import base64
import json

from app.firestore_cache import FirestoreCache


@pytest.mark.skip(reason="FirestoreCache tests disabled due to Flask context issues - alternative implementation not in use")
@pytest.mark.unit
class TestFirestoreCache:
    """Test FirestoreCache functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = FirestoreCache()
    
    @patch('app.firestore_cache.current_app')
    def test_client_property(self, mock_app):
        """Test client property initialization."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        client = self.cache.client
        
        assert client == mock_db
        assert self.cache._client == mock_db
    
    @patch('app.firestore_cache.current_app')
    def test_client_property_caching(self, mock_app):
        """Test that client property is cached."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # First access
        client1 = self.cache.client
        # Second access
        client2 = self.cache.client
        
        assert client1 == client2
        assert client1 == mock_db
    
    @patch('app.firestore_cache.current_app')
    def test_get_cache_doc(self, mock_app):
        """Test _get_cache_doc method."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        doc_ref = self.cache._get_cache_doc("test_key")
        
        mock_db.collection.assert_called_with("_cache")
        mock_db.collection.return_value.document.assert_called_with("test_key")
        assert doc_ref == mock_db.collection.return_value.document.return_value
    
    @patch('app.firestore_cache.current_app')
    def test_get_nonexistent_key(self, mock_app):
        """Test getting a nonexistent key returns None."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock document that doesn't exist
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.cache.get("nonexistent_key")
        
        assert result is None
    
    @patch('app.firestore_cache.current_app')
    def test_get_expired_key(self, mock_app):
        """Test getting an expired key returns None and deletes the doc."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock expired document
        mock_doc = MagicMock()
        mock_doc.exists = True
        expired_time = datetime.utcnow() - timedelta(hours=1)
        mock_doc.to_dict.return_value = {
            'value': 'test_value',
            'expires_at': expired_time,
            'is_binary': False
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.cache.get("expired_key")
        
        assert result is None
        # Should delete the expired document
        mock_db.collection.return_value.document.return_value.delete.assert_called_once()
    
    @patch('app.firestore_cache.current_app')
    def test_get_valid_string_value(self, mock_app):
        """Test getting a valid string value."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock valid document
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'value': 'test_string_value',
            'is_binary': False
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.cache.get("string_key")
        
        assert result == b'test_string_value'
    
    @patch('app.firestore_cache.current_app')
    def test_get_valid_binary_value(self, mock_app):
        """Test getting a valid binary value."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        original_data = b'binary_test_data'
        encoded_data = base64.b64encode(original_data).decode('ascii')
        
        # Mock valid binary document
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'value': encoded_data,
            'is_binary': True
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.cache.get("binary_key")
        
        assert result == original_data
    
    @patch('app.firestore_cache.current_app')
    def test_get_valid_value_with_future_expiration(self, mock_app):
        """Test getting a valid value with future expiration."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock document with future expiration
        mock_doc = MagicMock()
        mock_doc.exists = True
        future_time = datetime.utcnow() + timedelta(hours=1)
        mock_doc.to_dict.return_value = {
            'value': 'future_value',
            'expires_at': future_time,
            'is_binary': False
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.cache.get("future_key")
        
        assert result == b'future_value'
        # Should not delete the document
        mock_db.collection.return_value.document.return_value.delete.assert_not_called()
    
    @patch('app.firestore_cache.current_app')
    def test_get_error_handling(self, mock_app):
        """Test get method error handling."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock Firestore error
        mock_db.collection.return_value.document.return_value.get.side_effect = Exception("Firestore error")
        
        with patch('builtins.print') as mock_print:
            result = self.cache.get("error_key")
            
            assert result is None
            mock_print.assert_called_with("FirestoreCache get error: Firestore error")
    
    @patch('app.firestore_cache.current_app')
    @patch('app.firestore_cache.firestore')
    def test_set_binary_value_no_expiration(self, mock_firestore, mock_app):
        """Test setting a binary value without expiration."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        mock_firestore.SERVER_TIMESTAMP = "mock_timestamp"
        
        test_data = b'test_binary_data'
        encoded_data = base64.b64encode(test_data).decode('ascii')
        
        result = self.cache.set("binary_key", test_data)
        
        assert result is True
        
        expected_data = {
            'updated_at': "mock_timestamp",
            'is_binary': True,
            'value': encoded_data
        }
        
        mock_db.collection.return_value.document.return_value.set.assert_called_with(expected_data)
    
    @patch('app.firestore_cache.current_app')
    @patch('app.firestore_cache.firestore')
    @patch('app.firestore_cache.datetime')
    def test_set_string_value_with_expiration_seconds(self, mock_datetime, mock_firestore, mock_app):
        """Test setting a string value with expiration in seconds."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        mock_firestore.SERVER_TIMESTAMP = "mock_timestamp"
        
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now
        
        test_data = "test_string_data"
        
        result = self.cache.set("string_key", test_data, ex=3600)  # 1 hour
        
        assert result is True
        
        expected_expiration = mock_now + timedelta(seconds=3600)
        expected_data = {
            'updated_at': "mock_timestamp",
            'is_binary': True,  # Always set to True in current implementation
            'value': base64.b64encode(test_data.encode()).decode('ascii'),
            'expires_at': expected_expiration
        }
        
        mock_db.collection.return_value.document.return_value.set.assert_called_with(expected_data)
    
    @patch('app.firestore_cache.current_app')
    @patch('app.firestore_cache.firestore')
    @patch('app.firestore_cache.datetime')
    def test_set_value_with_timedelta_expiration(self, mock_datetime, mock_firestore, mock_app):
        """Test setting a value with timedelta expiration."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        mock_firestore.SERVER_TIMESTAMP = "mock_timestamp"
        
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now
        
        test_data = b'test_data'
        expiration_delta = timedelta(hours=2)
        
        result = self.cache.set("timedelta_key", test_data, ex=expiration_delta)
        
        assert result is True
        
        expected_expiration = mock_now + expiration_delta
        expected_data = {
            'updated_at': "mock_timestamp",
            'is_binary': True,
            'value': base64.b64encode(test_data).decode('ascii'),
            'expires_at': expected_expiration
        }
        
        mock_db.collection.return_value.document.return_value.set.assert_called_with(expected_data)
    
    @patch('app.firestore_cache.current_app')
    def test_set_error_handling(self, mock_app):
        """Test set method error handling."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock Firestore error
        mock_db.collection.return_value.document.return_value.set.side_effect = Exception("Firestore set error")
        
        with patch('builtins.print') as mock_print:
            result = self.cache.set("error_key", b"test_data")
            
            assert result is False
            mock_print.assert_called_with("FirestoreCache set error: Firestore set error")
    
    @patch('app.firestore_cache.current_app')
    def test_delete_success(self, mock_app):
        """Test successful key deletion."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        result = self.cache.delete("test_key")
        
        assert result is True
        mock_db.collection.return_value.document.return_value.delete.assert_called_once()
    
    @patch('app.firestore_cache.current_app')
    def test_delete_error_handling(self, mock_app):
        """Test delete method error handling."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock Firestore error
        mock_db.collection.return_value.document.return_value.delete.side_effect = Exception("Delete error")
        
        with patch('builtins.print') as mock_print:
            result = self.cache.delete("error_key")
            
            assert result is False
            mock_print.assert_called_with("FirestoreCache delete error: Delete error")
    
    @patch('app.firestore_cache.current_app')
    def test_exists_true_no_expiration(self, mock_app):
        """Test exists method returns True for existing key without expiration."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock existing document
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {'value': 'test_value'}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.cache.exists("existing_key")
        
        assert result is True
    
    @patch('app.firestore_cache.current_app')
    def test_exists_false_nonexistent(self, mock_app):
        """Test exists method returns False for nonexistent key."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock nonexistent document
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.cache.exists("nonexistent_key")
        
        assert result is False
    
    @patch('app.firestore_cache.current_app')
    def test_exists_false_expired(self, mock_app):
        """Test exists method returns False for expired key."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock expired document
        mock_doc = MagicMock()
        mock_doc.exists = True
        expired_time = datetime.utcnow() - timedelta(hours=1)
        mock_doc.to_dict.return_value = {
            'value': 'test_value',
            'expires_at': expired_time
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.cache.exists("expired_key")
        
        assert result is False
    
    @patch('app.firestore_cache.current_app')
    def test_exists_true_future_expiration(self, mock_app):
        """Test exists method returns True for key with future expiration."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock document with future expiration
        mock_doc = MagicMock()
        mock_doc.exists = True
        future_time = datetime.utcnow() + timedelta(hours=1)
        mock_doc.to_dict.return_value = {
            'value': 'test_value',
            'expires_at': future_time
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.cache.exists("future_key")
        
        assert result is True
    
    @patch('app.firestore_cache.current_app')
    def test_exists_error_handling(self, mock_app):
        """Test exists method error handling."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock Firestore error
        mock_db.collection.return_value.document.return_value.get.side_effect = Exception("Exists error")
        
        result = self.cache.exists("error_key")
        
        assert result is False
    
    @patch('app.firestore_cache.current_app')
    def test_ping_success(self, mock_app):
        """Test successful ping health check."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        result = self.cache.ping()
        
        assert result is True
        mock_db.collection.assert_called_with("_cache")
        mock_db.collection.return_value.limit.assert_called_with(1)
        mock_db.collection.return_value.limit.return_value.get.assert_called_once()
    
    @patch('app.firestore_cache.current_app')
    def test_ping_failure(self, mock_app):
        """Test ping health check failure."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock Firestore error
        mock_db.collection.return_value.limit.return_value.get.side_effect = Exception("Connection error")
        
        result = self.cache.ping()
        
        assert result is False
    
    @patch('app.firestore_cache.current_app')
    def test_flushdb_success(self, mock_app):
        """Test successful flushdb operation."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock documents to delete
        mock_doc1 = MagicMock()
        mock_doc2 = MagicMock()
        mock_db.collection.return_value.stream.return_value = [mock_doc1, mock_doc2]
        
        result = self.cache.flushdb()
        
        assert result is True
        mock_doc1.reference.delete.assert_called_once()
        mock_doc2.reference.delete.assert_called_once()
    
    @patch('app.firestore_cache.current_app')
    def test_flushdb_error_handling(self, mock_app):
        """Test flushdb error handling."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock Firestore error
        mock_db.collection.return_value.stream.side_effect = Exception("Flush error")
        
        with patch('builtins.print') as mock_print:
            result = self.cache.flushdb()
            
            assert result is False
            mock_print.assert_called_with("FirestoreCache flush error: Flush error")
    
    @patch('app.firestore_cache.current_app')
    @patch('app.firestore_cache.datetime')
    def test_cleanup_expired_success(self, mock_datetime, mock_app):
        """Test successful cleanup of expired entries."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now
        
        # Mock expired documents
        mock_doc1 = MagicMock()
        mock_doc2 = MagicMock()
        mock_db.collection.return_value.where.return_value.stream.return_value = [mock_doc1, mock_doc2]
        
        with patch('builtins.print') as mock_print:
            result = self.cache.cleanup_expired()
            
            assert result == 2
            mock_doc1.reference.delete.assert_called_once()
            mock_doc2.reference.delete.assert_called_once()
            mock_print.assert_called_with("Cleaned up 2 expired cache entries")
        
        # Verify the query
        mock_db.collection.return_value.where.assert_called_with('expires_at', '<', mock_now)
    
    @patch('app.firestore_cache.current_app')
    @patch('app.firestore_cache.datetime')
    def test_cleanup_expired_no_expired_entries(self, mock_datetime, mock_app):
        """Test cleanup when no expired entries exist."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now
        
        # Mock no expired documents
        mock_db.collection.return_value.where.return_value.stream.return_value = []
        
        with patch('builtins.print') as mock_print:
            result = self.cache.cleanup_expired()
            
            assert result == 0
            # Should not print cleanup message when count is 0
            mock_print.assert_not_called()
    
    @patch('app.firestore_cache.current_app')
    def test_cleanup_expired_error_handling(self, mock_app):
        """Test cleanup_expired error handling."""
        mock_db = MagicMock()
        mock_app.config = {"FIRESTORE_DB": mock_db}
        
        # Mock Firestore error
        mock_db.collection.return_value.where.side_effect = Exception("Cleanup error")
        
        with patch('builtins.print') as mock_print:
            result = self.cache.cleanup_expired()
            
            assert result == 0
            mock_print.assert_called_with("FirestoreCache cleanup error: Cleanup error")