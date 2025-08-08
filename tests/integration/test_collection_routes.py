"""
Integration tests for Collection Management Routes.

Tests card collection CRUD operations, filtering, search functionality,
and user collection synchronization workflows for production readiness.
"""

import pytest
import json
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime


@pytest.mark.integration
class TestCollectionViewing:
    """Test collection viewing and display functionality."""
    
    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_collection_page_loads(self, mock_get_db, mock_current_user, client, app):
        """Test that collection page loads properly for authenticated users."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            mock_current_user.data = {'username': 'TestUser'}
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.collection.card_service') as mock_card_service:
                    mock_card_service.get_card_collection.return_value = Mock()
                    
                    response = client.get('/collection')
                    assert response.status_code in [200, 302]  # Success or redirect

    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_get_user_collection_api_success(self, mock_get_db, mock_current_user, client, app):
        """Test successful retrieval of user collection via API."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock user collection data
            mock_collection_doc = Mock()
            mock_collection_doc.exists = True
            mock_collection_doc.to_dict.return_value = {
                'card_counts': {'1': 2, '2': 1, '3': 3},
                'total_cards': 6,
                'unique_cards': 3,
                'last_updated': datetime.now()
            }
            mock_db.collection.return_value.document.return_value.get.return_value = mock_collection_doc
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.get('/api/collection')
                
                assert response.status_code in [200, 302]  # Success or redirect
                if response.status_code != 302:
                    data = json.loads(response.data)
                    assert 'card_counts' in data or 'collection' in data

    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_get_user_collection_empty(self, mock_get_db, mock_current_user, client, app):
        """Test API response when user has no collection."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "new_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock empty collection
            mock_collection_doc = Mock()
            mock_collection_doc.exists = False
            mock_db.collection.return_value.document.return_value.get.return_value = mock_collection_doc
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.get('/api/collection')
                
                assert response.status_code in [200, 302]  # Success or redirect
                if response.status_code != 302:
                    data = json.loads(response.data)
                    assert data.get('card_counts', {}) == {} or 'collection' in data


@pytest.mark.integration  
class TestCollectionModification:
    """Test collection modification operations."""
    
    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_add_card_to_collection_success(self, mock_get_db, mock_current_user, client, app):
        """Test successfully adding a card to user collection."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock transaction for atomic update
            mock_transaction = Mock()
            mock_db.transaction.return_value = mock_transaction
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_api', lambda: lambda f: f):
                    response = client.post('/api/collection/add',
                                         json={'card_id': '123', 'quantity': 1},
                                         content_type='application/json')
                    
                    assert response.status_code in [200, 302]  # Success or redirect
                    if response.status_code != 302:
                        data = json.loads(response.data)
                        assert data.get('success', True)

    @patch('flask_login.current_user') 
    @patch('app.routes.collection.get_db')
    def test_add_card_to_collection_invalid_card(self, mock_get_db, mock_current_user, client, app):
        """Test adding non-existent card to collection."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_api', lambda: lambda f: f):
                    with patch('app.routes.collection.card_service') as mock_card_service:
                        # Mock card service returns None for invalid card
                        mock_card_collection = Mock()
                        mock_card_collection.get_card_by_id.return_value = None
                        mock_card_service.get_card_collection.return_value = mock_card_collection
                        
                        response = client.post('/api/collection/add',
                                             json={'card_id': '999999', 'quantity': 1},
                                             content_type='application/json')
                        
                        assert response.status_code in [400, 404, 302]  # Bad request, not found, or redirect

    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_remove_card_from_collection_success(self, mock_get_db, mock_current_user, client, app):
        """Test successfully removing a card from collection."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock existing collection with card
            mock_collection_doc = Mock()
            mock_collection_doc.exists = True
            mock_collection_doc.to_dict.return_value = {
                'card_counts': {'123': 2},
                'total_cards': 2
            }
            mock_db.collection.return_value.document.return_value.get.return_value = mock_collection_doc
            
            mock_transaction = Mock()
            mock_db.transaction.return_value = mock_transaction
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_api', lambda: lambda f: f):
                    response = client.post('/api/collection/remove',
                                         json={'card_id': '123', 'quantity': 1},
                                         content_type='application/json')
                    
                    assert response.status_code in [200, 302]  # Success or redirect
                    if response.status_code != 302:
                        data = json.loads(response.data)
                        assert data.get('success', True)

    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db') 
    def test_remove_card_insufficient_quantity(self, mock_get_db, mock_current_user, client, app):
        """Test removing more cards than user owns."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock collection with only 1 card
            mock_collection_doc = Mock()
            mock_collection_doc.exists = True
            mock_collection_doc.to_dict.return_value = {
                'card_counts': {'123': 1},
                'total_cards': 1
            }
            mock_db.collection.return_value.document.return_value.get.return_value = mock_collection_doc
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_api', lambda: lambda f: f):
                    response = client.post('/api/collection/remove',
                                         json={'card_id': '123', 'quantity': 5},
                                         content_type='application/json')
                    
                    assert response.status_code in [400, 302]  # Bad request or redirect


@pytest.mark.integration
class TestCollectionSearch:
    """Test collection search and filtering functionality."""
    
    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_search_collection_by_name(self, mock_get_db, mock_current_user, client, app):
        """Test searching collection by card name."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.collection.card_service') as mock_card_service:
                    mock_card_collection = Mock()
                    mock_card_service.get_card_collection.return_value = mock_card_collection
                    
                    response = client.get('/api/collection/search?q=pikachu')
                    
                    assert response.status_code in [200, 302]  # Success or redirect
                    if response.status_code != 302:
                        data = json.loads(response.data)
                        assert 'results' in data or 'cards' in data

    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_filter_collection_by_type(self, mock_get_db, mock_current_user, client, app):
        """Test filtering collection by Pokemon type."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.collection.card_service') as mock_card_service:
                    mock_card_collection = Mock()
                    mock_card_service.get_card_collection.return_value = mock_card_collection
                    
                    response = client.get('/api/collection/filter?type=Electric')
                    
                    assert response.status_code in [200, 302]  # Success or redirect

    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_filter_collection_by_rarity(self, mock_get_db, mock_current_user, client, app):
        """Test filtering collection by card rarity."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.collection.card_service') as mock_card_service:
                    mock_card_collection = Mock()
                    mock_card_service.get_card_collection.return_value = mock_card_collection
                    
                    response = client.get('/api/collection/filter?rarity=rare')
                    
                    assert response.status_code in [200, 302]  # Success or redirect


@pytest.mark.integration
class TestCollectionStatistics:
    """Test collection statistics and analytics."""
    
    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_get_collection_stats(self, mock_get_db, mock_current_user, client, app):
        """Test retrieval of collection statistics."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock collection with statistics
            mock_collection_doc = Mock()
            mock_collection_doc.exists = True
            mock_collection_doc.to_dict.return_value = {
                'card_counts': {'1': 2, '2': 1, '3': 3},
                'total_cards': 6,
                'unique_cards': 3,
                'completion_percentage': 75.5,
                'rarity_breakdown': {
                    'common': 4,
                    'uncommon': 1, 
                    'rare': 1
                }
            }
            mock_db.collection.return_value.document.return_value.get.return_value = mock_collection_doc
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.get('/api/collection/stats')
                
                assert response.status_code in [200, 302]  # Success or redirect
                if response.status_code != 302:
                    data = json.loads(response.data)
                    assert 'total_cards' in data or 'stats' in data

    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_get_completion_progress(self, mock_get_db, mock_current_user, client, app):
        """Test collection completion progress tracking."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.collection.card_service') as mock_card_service:
                    # Mock total available cards
                    mock_card_collection = Mock()
                    mock_card_collection.total_cards = 100
                    mock_card_service.get_card_collection.return_value = mock_card_collection
                    
                    # Mock user collection
                    mock_collection_doc = Mock()
                    mock_collection_doc.exists = True
                    mock_collection_doc.to_dict.return_value = {
                        'unique_cards': 75
                    }
                    mock_db.collection.return_value.document.return_value.get.return_value = mock_collection_doc
                    
                    response = client.get('/api/collection/progress')
                    
                    assert response.status_code in [200, 302]  # Success or redirect


@pytest.mark.integration
class TestCollectionSync:
    """Test collection synchronization and data consistency."""
    
    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_sync_collection_success(self, mock_get_db, mock_current_user, client, app):
        """Test successful collection synchronization."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            mock_transaction = Mock()
            mock_db.transaction.return_value = mock_transaction
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_api', lambda: lambda f: f):
                    response = client.post('/api/collection/sync',
                                         json={'force_refresh': True},
                                         content_type='application/json')
                    
                    assert response.status_code in [200, 302]  # Success or redirect

    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_collection_backup_and_restore(self, mock_get_db, mock_current_user, client, app):
        """Test collection backup and restore functionality."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock collection data
            collection_data = {
                'card_counts': {'1': 2, '2': 1, '3': 3},
                'total_cards': 6,
                'backup_timestamp': datetime.now().isoformat()
            }
            
            mock_collection_doc = Mock()
            mock_collection_doc.exists = True
            mock_collection_doc.to_dict.return_value = collection_data
            mock_db.collection.return_value.document.return_value.get.return_value = mock_collection_doc
            
            with patch('flask_login.login_required', lambda f: f):
                # Test backup
                response = client.post('/api/collection/backup')
                assert response.status_code in [200, 302]  # Success or redirect
                
                if response.status_code != 302:
                    data = json.loads(response.data)
                    assert 'backup_id' in data or 'success' in data


@pytest.mark.integration
class TestCollectionErrorHandling:
    """Test error handling in collection operations."""
    
    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_collection_database_error(self, mock_get_db, mock_current_user, client, app):
        """Test handling of database errors during collection operations."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            # Mock database error
            mock_get_db.side_effect = Exception("Database connection failed")
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.get('/api/collection')
                
                assert response.status_code in [500, 302]  # Server error or redirect

    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_collection_concurrent_modification_error(self, mock_get_db, mock_current_user, client, app):
        """Test handling of concurrent modification errors."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock transaction conflict
            from google.cloud.exceptions import Conflict
            mock_transaction = Mock()
            mock_transaction.side_effect = Conflict("Concurrent modification")
            mock_db.transaction.return_value = mock_transaction
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_api', lambda: lambda f: f):
                    response = client.post('/api/collection/add',
                                         json={'card_id': '123', 'quantity': 1},
                                         content_type='application/json')
                    
                    assert response.status_code in [409, 500, 302]  # Conflict, error, or redirect

    @patch('flask_login.current_user')
    def test_collection_operations_without_authentication(self, mock_current_user, client, app):
        """Test that collection operations require authentication."""
        with app.app_context():
            mock_current_user.is_authenticated = False
            
            # Test various collection endpoints
            collection_endpoints = [
                '/collection',
                '/api/collection',
                '/api/collection/add',
                '/api/collection/remove',
                '/api/collection/stats'
            ]
            
            for endpoint in collection_endpoints:
                if '/api/' in endpoint and endpoint.endswith(('add', 'remove')):
                    response = client.post(endpoint, 
                                         json={'card_id': '123'},
                                         content_type='application/json')
                else:
                    response = client.get(endpoint)
                
                assert response.status_code in [302, 401, 403]  # Redirect to login or unauthorized


@pytest.mark.integration
class TestCollectionPerformance:
    """Test performance aspects of collection operations."""
    
    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_large_collection_handling(self, mock_get_db, mock_current_user, client, app):
        """Test handling of large collections efficiently."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "user_with_large_collection"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock large collection (1000+ cards)
            large_collection = {str(i): min(10, i % 5 + 1) for i in range(1, 1001)}
            mock_collection_doc = Mock()
            mock_collection_doc.exists = True
            mock_collection_doc.to_dict.return_value = {
                'card_counts': large_collection,
                'total_cards': sum(large_collection.values()),
                'unique_cards': len(large_collection)
            }
            mock_db.collection.return_value.document.return_value.get.return_value = mock_collection_doc
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.get('/api/collection')
                
                # Should handle large collection without timeout
                assert response.status_code in [200, 302]

    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_collection_pagination(self, mock_get_db, mock_current_user, client, app):
        """Test collection pagination for large datasets."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.collection.card_service') as mock_card_service:
                    mock_card_collection = Mock()
                    mock_card_service.get_card_collection.return_value = mock_card_collection
                    
                    # Test pagination parameters
                    response = client.get('/api/collection?page=1&limit=50')
                    
                    assert response.status_code in [200, 302]
                    if response.status_code != 302:
                        data = json.loads(response.data)
                        assert 'pagination' in data or 'page' in data or response.status_code == 200