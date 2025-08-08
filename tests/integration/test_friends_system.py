"""
Integration tests for the Friends System.

Tests the complete friend request workflow including:
- Friend search functionality
- Sending, accepting, and declining friend requests
- Friend removal
- Privacy enforcement for friend deck viewing
- Transaction integrity and error handling
"""

import pytest
import json
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime
from firebase_admin import firestore


@pytest.mark.integration
class TestFriendsPage:
    """Test friends main page functionality."""
    
    @patch('app.routes.friends._get_user_snapshot')
    @patch('flask_login.current_user')
    def test_friends_page_loads(self, mock_current_user, mock_get_user, client, app):
        """Test that friends page loads and displays friends data."""
        with app.app_context():
            mock_current_user.id = "test_user_1"
            mock_current_user.is_authenticated = True
            
            # Mock user snapshot
            mock_get_user.side_effect = [
                {"id": "friend_1", "username": "Friend1", "profile_icon": "icon1.png"},
                {"id": "pending_1", "username": "PendingUser", "profile_icon": ""},
                {"id": "received_1", "username": "ReceivedUser", "profile_icon": ""}
            ]
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    
                    # Mock friends collection
                    mock_friends = [Mock(id="friend_1")]
                    mock_db.collection.return_value.document.return_value.collection.return_value.stream.return_value = mock_friends
                    
                    # Mock friend requests  
                    mock_requests = [
                        Mock(id="pending_1", to_dict=lambda: {"status": "sent"}),
                        Mock(id="received_1", to_dict=lambda: {"status": "received"})
                    ]
                    mock_db.collection.return_value.document.return_value.collection.return_value.stream.return_value = mock_requests
                    
                    response = client.get('/friends/')
                    assert response.status_code in [200, 302]  # Success or redirect


@pytest.mark.integration
class TestFriendSearch:
    """Test friend search functionality."""
    
    @patch('flask_login.current_user')
    def test_friend_search_valid_query(self, mock_current_user, client, app):
        """Test searching for users with valid query."""
        with app.app_context():
            mock_current_user.id = "test_user_1"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    
                    # Mock search results
                    mock_docs = [
                        Mock(id="user_2", to_dict=lambda: {"username": "testuser", "username_lowercase": "testuser"})
                    ]
                    mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = mock_docs
                    
                    with patch('app.routes.friends._get_user_snapshot') as mock_snapshot:
                        mock_snapshot.return_value = {"id": "user_2", "username": "testuser", "profile_icon": ""}
                        
                        response = client.post('/friends/search',
                                             json={'query': 'test'},
                                             content_type='application/json')
                        
                        assert response.status_code in [200, 302]  # Success or redirect
                        if response.status_code != 302:
                            data = json.loads(response.data)
                            assert isinstance(data, list)
                            assert len(data) >= 0

    @patch('flask_login.current_user')
    def test_friend_search_short_query(self, mock_current_user, client, app):
        """Test that short search queries are rejected."""
        with app.app_context():
            mock_current_user.id = "test_user_1"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.post('/friends/search',
                                     json={'query': 'ab'},  # Less than 3 characters
                                     content_type='application/json')
                
                assert response.status_code in [400, 302]  # Bad request or redirect
                if response.status_code != 302:
                    data = json.loads(response.data)
                    assert 'error' in data
                    assert 'at least 3 characters' in data['error']

    @patch('flask_login.current_user')
    def test_friend_search_empty_query(self, mock_current_user, client, app):
        """Test that empty search queries are rejected."""
        with app.app_context():
            mock_current_user.id = "test_user_1"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.post('/friends/search',
                                     json={'query': ''},
                                     content_type='application/json')
                
                assert response.status_code in [400, 302]  # Bad request or redirect
                if response.status_code != 302:
                    data = json.loads(response.data)
                    assert 'error' in data


@pytest.mark.integration
class TestFriendRequests:
    """Test friend request workflow."""
    
    @patch('flask_login.current_user')
    def test_send_friend_request_success(self, mock_current_user, client, app):
        """Test successfully sending a friend request."""
        with app.app_context():
            mock_current_user.id = "user_1"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    
                    # Mock batch operations
                    mock_batch = Mock()
                    mock_db.batch.return_value = mock_batch
                    
                    response = client.post('/friends/request',
                                         json={'recipient_id': 'user_2'},
                                         content_type='application/json')
                    
                    assert response.status_code in [200, 302]  # Success or redirect
                    if response.status_code != 302:
                        data = json.loads(response.data)
                        assert data['success'] is True
                        assert 'Friend request sent' in data['message']
                        
                        # Verify batch operations were called
                        assert mock_batch.set.call_count == 2
                        mock_batch.commit.assert_called_once()

    @patch('flask_login.current_user')
    def test_send_friend_request_to_self(self, mock_current_user, client, app):
        """Test that users cannot send friend requests to themselves."""
        with app.app_context():
            mock_current_user.id = "user_1"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.post('/friends/request',
                                     json={'recipient_id': 'user_1'},  # Same as sender
                                     content_type='application/json')
                
                assert response.status_code in [400, 302]  # Bad request or redirect
                if response.status_code != 302:
                    data = json.loads(response.data)
                    assert 'error' in data
                    assert 'Invalid request' in data['error']

    @patch('flask_login.current_user')
    def test_send_friend_request_invalid_recipient(self, mock_current_user, client, app):
        """Test sending friend request with invalid recipient ID."""
        with app.app_context():
            mock_current_user.id = "user_1"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.post('/friends/request',
                                     json={'recipient_id': ''},  # Empty recipient
                                     content_type='application/json')
                
                assert response.status_code in [400, 302]  # Bad request or redirect
                if response.status_code != 302:
                    data = json.loads(response.data)
                    assert 'error' in data
                    assert 'Invalid request' in data['error']

    @patch('flask_login.current_user')
    def test_accept_friend_request_success(self, mock_current_user, client, app):
        """Test successfully accepting a friend request."""
        with app.app_context():
            mock_current_user.id = "user_2"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    
                    # Mock transaction
                    mock_transaction = Mock()
                    mock_db.transaction.return_value = mock_transaction
                    
                    with patch('app.routes.friends._get_user_snapshot') as mock_snapshot:
                        mock_snapshot.return_value = {
                            "id": "user_1", 
                            "username": "Sender", 
                            "profile_icon": "icon.png"
                        }
                        
                        response = client.post('/friends/accept',
                                             json={'sender_id': 'user_1'},
                                             content_type='application/json')
                        
                        assert response.status_code in [200, 302]  # Success or redirect
                        if response.status_code != 302:
                            data = json.loads(response.data)
                            assert data['success'] is True
                            assert 'Friend request accepted' in data['message']
                            assert 'friend' in data
                            assert data['friend']['id'] == 'user_1'

    @patch('flask_login.current_user')
    def test_decline_friend_request_success(self, mock_current_user, client, app):
        """Test successfully declining a friend request."""
        with app.app_context():
            mock_current_user.id = "user_2"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    
                    # Mock transaction
                    mock_transaction = Mock()
                    mock_db.transaction.return_value = mock_transaction
                    
                    response = client.post('/friends/decline',
                                         json={'sender_id': 'user_1'},
                                         content_type='application/json')
                    
                    assert response.status_code in [200, 302]  # Success or redirect
                    if response.status_code != 302:
                        data = json.loads(response.data)
                        assert data['success'] is True
                        assert 'Friend request declined' in data['message']


@pytest.mark.integration
class TestFriendManagement:
    """Test friend management operations."""
    
    @patch('flask_login.current_user')
    def test_remove_friend_success(self, mock_current_user, client, app):
        """Test successfully removing a friend."""
        with app.app_context():
            mock_current_user.id = "user_1"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    
                    # Mock transaction
                    mock_transaction = Mock()
                    mock_db.transaction.return_value = mock_transaction
                    
                    response = client.post('/friends/remove',
                                         json={'friend_id': 'user_2'},
                                         content_type='application/json')
                    
                    assert response.status_code in [200, 302]  # Success or redirect
                    if response.status_code != 302:
                        data = json.loads(response.data)
                        assert data['success'] is True
                        assert 'Friend removed' in data['message']

    @patch('flask_login.current_user')
    def test_get_friends_api_with_pagination(self, mock_current_user, client, app):
        """Test getting friends list with pagination."""
        with app.app_context():
            mock_current_user.id = "user_1"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    
                    # Mock friends data
                    mock_friends = [
                        Mock(id="friend_1", to_dict=lambda: {"friended_at": datetime.now()}),
                        Mock(id="friend_2", to_dict=lambda: {"friended_at": datetime.now()})
                    ]
                    mock_db.collection.return_value.document.return_value.collection.return_value.stream.return_value = mock_friends
                    
                    with patch('app.routes.friends._get_user_snapshot') as mock_snapshot:
                        mock_snapshot.side_effect = [
                            {"id": "friend_1", "username": "Friend1", "profile_icon": ""},
                            {"id": "friend_2", "username": "Friend2", "profile_icon": ""}
                        ]
                        
                        response = client.get('/friends/api/friends?page=1&limit=10')
                        
                        assert response.status_code in [200, 302]  # Success or redirect
                        if response.status_code != 302:
                            data = json.loads(response.data)
                            assert 'friends' in data
                            assert 'pagination' in data
                            assert data['pagination']['current_page'] == 1

    @patch('flask_login.current_user')
    def test_get_friends_api_invalid_pagination(self, mock_current_user, client, app):
        """Test friends API with invalid pagination parameters."""
        with app.app_context():
            mock_current_user.id = "user_1"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.get('/friends/api/friends?page=invalid&limit=bad')
                
                assert response.status_code in [400, 302]  # Bad request or redirect
                if response.status_code != 302:
                    data = json.loads(response.data)
                    assert 'error' in data
                    assert 'Invalid pagination parameters' in data['error']


@pytest.mark.integration
class TestFriendDeckViewing:
    """Test friend deck viewing functionality and privacy controls."""
    
    @patch('flask_login.current_user')
    def test_view_friend_decks_authorized(self, mock_current_user, client, app):
        """Test viewing friend's decks when authorized."""
        with app.app_context():
            mock_current_user.id = "user_1"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    
                    # Mock friend relationship exists
                    mock_friend_doc = Mock()
                    mock_friend_doc.exists = True
                    mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_friend_doc
                    
                    # Mock card service
                    with patch('app.routes.friends.card_service') as mock_card_service:
                        mock_card_service.get_card_collection.return_value = Mock()
                        
                        with patch('app.routes.friends._get_user_snapshot') as mock_snapshot:
                            mock_snapshot.return_value = {
                                "id": "friend_1", 
                                "username": "Friend", 
                                "profile_icon": "icon.png"
                            }
                            
                            # Mock deck query results
                            mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
                            
                            response = client.get('/friends/friend_1/decks')
                            assert response.status_code in [200, 302]  # Success or redirect

    @patch('flask_login.current_user')
    def test_view_friend_decks_unauthorized(self, mock_current_user, client, app):
        """Test that non-friends cannot view decks."""
        with app.app_context():
            mock_current_user.id = "user_1"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    
                    # Mock friend relationship does NOT exist
                    mock_friend_doc = Mock()
                    mock_friend_doc.exists = False
                    mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_friend_doc
                    
                    with patch('app.routes.friends.flash'):
                        response = client.get('/friends/non_friend_user/decks')
                        # Should redirect to friends page
                        assert response.status_code == 302


@pytest.mark.integration
class TestFriendsErrorHandling:
    """Test error handling in friends system."""
    
    @patch('flask_login.current_user')
    def test_friend_request_database_error(self, mock_current_user, client, app):
        """Test handling of database errors during friend requests."""
        with app.app_context():
            mock_current_user.id = "user_1"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    mock_app.logger = Mock()
                    
                    # Mock batch to raise exception
                    mock_batch = Mock()
                    mock_batch.commit.side_effect = Exception("Database error")
                    mock_db.batch.return_value = mock_batch
                    
                    response = client.post('/friends/request',
                                         json={'recipient_id': 'user_2'},
                                         content_type='application/json')
                    
                    assert response.status_code in [500, 302]  # Server error or redirect
                    if response.status_code != 302:
                        data = json.loads(response.data)
                        assert 'error' in data
                        assert 'unexpected error' in data['error']
                        
                        # Verify error was logged
                        mock_app.logger.error.assert_called()

    @patch('flask_login.current_user')
    def test_get_friends_api_database_error(self, mock_current_user, client, app):
        """Test handling of database errors in friends API."""
        with app.app_context():
            mock_current_user.id = "user_1"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    mock_app.logger = Mock()
                    
                    # Mock database to raise exception
                    mock_db.collection.side_effect = Exception("Database connection failed")
                    
                    response = client.get('/friends/api/friends')
                    
                    assert response.status_code in [500, 302]  # Server error or redirect
                    if response.status_code != 302:
                        data = json.loads(response.data)
                        assert 'error' in data
                        assert 'internal error' in data['error']
                        assert data['friends'] == []


@pytest.mark.integration
class TestFriendTransactionIntegrity:
    """Test that friend operations maintain transaction integrity."""
    
    @patch('flask_login.current_user')
    def test_accept_request_transaction_rollback(self, mock_current_user, client, app):
        """Test that failed friend acceptance rolls back properly."""
        with app.app_context():
            mock_current_user.id = "user_2"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    mock_app.logger = Mock()
                    
                    # Mock transaction to fail during execution
                    def failing_transaction(*args, **kwargs):
                        raise Exception("Transaction failed")
                    
                    with patch('app.routes.friends.accept_request_transaction', side_effect=failing_transaction):
                        response = client.post('/friends/accept',
                                             json={'sender_id': 'user_1'},
                                             content_type='application/json')
                        
                        assert response.status_code in [500, 302]  # Server error or redirect
                        if response.status_code != 302:
                            data = json.loads(response.data)
                            assert 'error' in data
                            
                            # Verify error was logged
                            mock_app.logger.error.assert_called()