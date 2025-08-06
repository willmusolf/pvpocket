"""
Integration tests for Deck Management Routes.

Tests deck CRUD operations, privacy controls, export functionality,
search and filtering, and business rule enforcement.
"""

import pytest
import json
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime


@pytest.mark.integration
class TestDeckViewing:
    """Test deck viewing and listing functionality."""
    
    @patch('flask_login.current_user')
    def test_decks_page_loads(self, mock_current_user, client):
        """Test that decks page loads properly."""
        mock_current_user.id = "test_user"
        mock_current_user.is_authenticated = True
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                response = client.get('/decks')
                assert response.status_code == 200

    @patch('flask_login.current_user')
    def test_get_deck_api_success(self, mock_current_user, client):
        """Test successful deck retrieval via API."""
        mock_current_user.id = "owner_id"
        mock_current_user.is_authenticated = True
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                # Mock deck document
                mock_deck_doc = Mock()
                mock_deck_doc.exists = True
                mock_deck_doc.to_dict.return_value = {
                    'owner_id': 'owner_id',
                    'name': 'Test Deck',
                    'card_ids': [1, 2, 3],
                    'is_public': True
                }
                mock_db.collection.return_value.document.return_value.get.return_value = mock_deck_doc
                
                # Mock card service
                with patch('app.routes.decks.card_service') as mock_card_service:
                    mock_card_service.get_card_collection.return_value = Mock()
                    
                    with patch('Deck.from_firestore_doc') as mock_from_doc:
                        mock_deck = Mock()
                        mock_deck.to_dict.return_value = {'name': 'Test Deck', 'owner_id': 'owner_id'}
                        mock_from_doc.return_value = mock_deck
                        
                        response = client.get('/api/decks/test_deck_id')
                        assert response.status_code == 200

    @patch('flask_login.current_user')
    def test_get_deck_api_not_found(self, mock_current_user, client):
        """Test API response when deck is not found."""
        mock_current_user.id = "test_user"
        mock_current_user.is_authenticated = True
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                # Mock deck document doesn't exist
                mock_deck_doc = Mock()
                mock_deck_doc.exists = False
                mock_db.collection.return_value.document.return_value.get.return_value = mock_deck_doc
                
                response = client.get('/api/decks/nonexistent_deck')
                assert response.status_code == 404
                data = json.loads(response.data)
                assert 'error' in data


@pytest.mark.integration
class TestDeckCreation:
    """Test deck creation functionality."""
    
    @patch('flask_login.current_user')
    def test_create_deck_success(self, mock_current_user, client):
        """Test successful deck creation."""
        mock_current_user.id = "test_user"
        mock_current_user.is_authenticated = True
        mock_current_user.data = {'deck_ids': []}  # User has no existing decks
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.rate_limit_heavy', lambda: lambda f: f):
                with patch('app.routes.decks.get_db') as mock_get_db:
                    mock_db = Mock()
                    mock_get_db.return_value = mock_db
                    
                    # Mock card service
                    with patch('app.routes.decks.card_service') as mock_card_service:
                        mock_collection = Mock()
                        mock_card_service.get_card_collection.return_value = mock_collection
                        
                        # Mock Deck creation
                        with patch('Deck.from_cards_data') as mock_from_cards:
                            mock_deck = Mock()
                            mock_deck.to_firestore_dict.return_value = {'name': 'Test Deck'}
                            mock_deck.firestore_id = 'new_deck_id'
                            mock_from_cards.return_value = mock_deck
                            
                            deck_data = {
                                'name': 'Test Deck',
                                'card_ids': [1, 2, 3],
                                'cover_card_ids': [1, 2, 3]
                            }
                            
                            response = client.post('/api/decks',
                                                 json=deck_data,
                                                 content_type='application/json')
                            
                            assert response.status_code == 201
                            data = json.loads(response.data)
                            assert data['success'] is True
                            assert 'deck_id' in data

    @patch('flask_login.current_user')
    def test_create_deck_max_limit_reached(self, mock_current_user, client):
        """Test deck creation when user has reached maximum deck limit."""
        mock_current_user.id = "test_user"
        mock_current_user.is_authenticated = True
        # Create a list of 200 deck IDs to simulate max limit
        deck_ids = [f"deck_{i}" for i in range(200)]
        mock_current_user.data = {'deck_ids': deck_ids}
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.rate_limit_heavy', lambda: lambda f: f):
                deck_data = {
                    'name': 'One Too Many',
                    'card_ids': [1, 2, 3]
                }
                
                response = client.post('/api/decks',
                                     json=deck_data,
                                     content_type='application/json')
                
                assert response.status_code == 403
                data = json.loads(response.data)
                assert data['success'] is False
                assert 'maximum limit' in data['error']

    @patch('flask_login.current_user')
    def test_create_deck_no_data(self, mock_current_user, client):
        """Test deck creation with no request data."""
        mock_current_user.id = "test_user"
        mock_current_user.is_authenticated = True
        mock_current_user.data = {'deck_ids': []}
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.rate_limit_heavy', lambda: lambda f: f):
                response = client.post('/api/decks',
                                     json=None,  # No data
                                     content_type='application/json')
                
                assert response.status_code == 400
                data = json.loads(response.data)
                assert data['success'] is False
                assert 'No data received' in data['error']

    @patch('flask_login.current_user')
    def test_create_deck_card_service_unavailable(self, mock_current_user, client):
        """Test deck creation when card service is unavailable."""
        mock_current_user.id = "test_user"
        mock_current_user.is_authenticated = True
        mock_current_user.data = {'deck_ids': []}
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.rate_limit_heavy', lambda: lambda f: f):
                with patch('app.routes.decks.get_db') as mock_get_db:
                    mock_get_db.return_value = Mock()
                    
                    # Mock card service returns None
                    with patch('app.routes.decks.card_service') as mock_card_service:
                        mock_card_service.get_card_collection.return_value = None
                        
                        deck_data = {'name': 'Test Deck', 'card_ids': [1, 2, 3]}
                        
                        response = client.post('/api/decks',
                                             json=deck_data,
                                             content_type='application/json')
                        
                        assert response.status_code == 503
                        data = json.loads(response.data)
                        assert data['success'] is False
                        assert 'Card data unavailable' in data['error']


@pytest.mark.integration
class TestDeckDeletion:
    """Test deck deletion functionality."""
    
    @patch('flask_login.current_user')
    def test_delete_deck_success(self, mock_current_user, client):
        """Test successful deck deletion."""
        mock_current_user.id = "owner_id"
        mock_current_user.is_authenticated = True
        mock_current_user.data = {'deck_ids': ['test_deck_id']}
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                # Mock deck document exists and is owned by user
                mock_deck_doc = Mock()
                mock_deck_doc.exists = True
                mock_deck_doc.to_dict.return_value = {'owner_id': 'owner_id'}
                mock_db.collection.return_value.document.return_value.get.return_value = mock_deck_doc
                
                # Mock batch operations
                mock_batch = Mock()
                mock_db.batch.return_value = mock_batch
                
                response = client.delete('/api/decks/test_deck_id')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                
                # Verify batch operations were called
                mock_batch.delete.assert_called()
                mock_batch.update.assert_called()
                mock_batch.commit.assert_called()

    @patch('flask_login.current_user')
    def test_delete_deck_not_found(self, mock_current_user, client):
        """Test deleting non-existent deck."""
        mock_current_user.id = "test_user"
        mock_current_user.is_authenticated = True
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                # Mock deck document doesn't exist
                mock_deck_doc = Mock()
                mock_deck_doc.exists = False
                mock_db.collection.return_value.document.return_value.get.return_value = mock_deck_doc
                
                response = client.delete('/api/decks/nonexistent_deck')
                
                assert response.status_code == 404
                data = json.loads(response.data)
                assert data['success'] is False
                assert 'Deck not found' in data['error']

    @patch('flask_login.current_user')
    def test_delete_deck_permission_denied(self, mock_current_user, client):
        """Test deleting deck owned by another user."""
        mock_current_user.id = "user_1"
        mock_current_user.is_authenticated = True
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                # Mock deck exists but is owned by different user
                mock_deck_doc = Mock()
                mock_deck_doc.exists = True
                mock_deck_doc.to_dict.return_value = {'owner_id': 'different_user'}
                mock_db.collection.return_value.document.return_value.get.return_value = mock_deck_doc
                
                response = client.delete('/api/decks/someone_elses_deck')
                
                assert response.status_code == 403
                data = json.loads(response.data)
                assert data['success'] is False
                assert 'Permission denied' in data['error']


@pytest.mark.integration
class TestDeckPrivacy:
    """Test deck privacy controls."""
    
    @patch('flask_login.current_user')
    def test_toggle_deck_privacy_success(self, mock_current_user, client):
        """Test successful deck privacy toggle."""
        mock_current_user.id = "owner_id"
        mock_current_user.is_authenticated = True
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                # Mock card service
                with patch('app.routes.decks.card_service') as mock_card_service:
                    mock_card_service.get_card_collection.return_value = Mock()
                    
                    # Mock deck document and Deck object
                    mock_deck_doc = Mock()
                    mock_deck_doc.exists = True
                    mock_db.collection.return_value.document.return_value.get.return_value = mock_deck_doc
                    
                    with patch('Deck.from_firestore_doc') as mock_from_doc:
                        mock_deck = Mock()
                        mock_deck.owner_id = "owner_id"
                        mock_deck.is_public = False
                        mock_deck.toggle_privacy.return_value = True  # Now public
                        mock_from_doc.return_value = mock_deck
                        
                        request_data = {'description': 'My awesome deck!'}
                        
                        response = client.post('/api/decks/test_deck/privacy',
                                             json=request_data,
                                             content_type='application/json')
                        
                        assert response.status_code == 200
                        data = json.loads(response.data)
                        assert data['success'] is True
                        assert 'privacy updated' in data['message']
                        
                        # Verify toggle_privacy was called
                        mock_deck.toggle_privacy.assert_called_once()

    @patch('flask_login.current_user')
    def test_toggle_deck_privacy_permission_denied(self, mock_current_user, client):
        """Test privacy toggle on deck owned by another user."""
        mock_current_user.id = "user_1"
        mock_current_user.is_authenticated = True
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                # Mock card service
                with patch('app.routes.decks.card_service') as mock_card_service:
                    mock_card_service.get_card_collection.return_value = Mock()
                    
                    # Mock deck document
                    mock_deck_doc = Mock()
                    mock_deck_doc.exists = True
                    mock_db.collection.return_value.document.return_value.get.return_value = mock_deck_doc
                    
                    with patch('Deck.from_firestore_doc') as mock_from_doc:
                        mock_deck = Mock()
                        mock_deck.owner_id = "different_user"  # Different owner
                        mock_from_doc.return_value = mock_deck
                        
                        response = client.post('/api/decks/someone_elses_deck/privacy',
                                             json={'description': 'Test'},
                                             content_type='application/json')
                        
                        assert response.status_code == 403
                        data = json.loads(response.data)
                        assert 'only modify your own decks' in data['error']

    @patch('flask_login.current_user')
    def test_toggle_deck_privacy_description_too_long(self, mock_current_user, client):
        """Test privacy toggle with description exceeding length limit."""
        mock_current_user.id = "owner_id"
        mock_current_user.is_authenticated = True
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                # Mock card service
                with patch('app.routes.decks.card_service') as mock_card_service:
                    mock_card_service.get_card_collection.return_value = Mock()
                    
                    # Mock deck document
                    mock_deck_doc = Mock()
                    mock_deck_doc.exists = True
                    mock_db.collection.return_value.document.return_value.get.return_value = mock_deck_doc
                    
                    with patch('Deck.from_firestore_doc') as mock_from_doc:
                        mock_deck = Mock()
                        mock_deck.owner_id = "owner_id"
                        mock_from_doc.return_value = mock_deck
                        
                        # Description over 100 characters
                        long_description = "a" * 101
                        request_data = {'description': long_description}
                        
                        response = client.post('/api/decks/test_deck/privacy',
                                             json=request_data,
                                             content_type='application/json')
                        
                        assert response.status_code == 400
                        data = json.loads(response.data)
                        assert '100 characters or less' in data['error']

    @patch('flask_login.current_user')
    def test_toggle_deck_privacy_profanity_check(self, mock_current_user, client):
        """Test privacy toggle with profanity in description."""
        mock_current_user.id = "owner_id"
        mock_current_user.is_authenticated = True
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                # Mock card service
                with patch('app.routes.decks.card_service') as mock_card_service:
                    mock_card_service.get_card_collection.return_value = Mock()
                    
                    # Mock deck document
                    mock_deck_doc = Mock()
                    mock_deck_doc.exists = True
                    mock_db.collection.return_value.document.return_value.get.return_value = mock_deck_doc
                    
                    with patch('Deck.from_firestore_doc') as mock_from_doc:
                        mock_deck = Mock()
                        mock_deck.owner_id = "owner_id"
                        mock_from_doc.return_value = mock_deck
                        
                        # Mock profanity check
                        with patch('better_profanity.profanity') as mock_profanity:
                            mock_profanity.contains_profanity.return_value = True
                            
                            request_data = {'description': 'inappropriate content'}
                            
                            response = client.post('/api/decks/test_deck/privacy',
                                                 json=request_data,
                                                 content_type='application/json')
                            
                            assert response.status_code == 400
                            data = json.loads(response.data)
                            assert 'inappropriate language' in data['error']


@pytest.mark.integration
class TestDeckExport:
    """Test deck export functionality."""
    
    @patch('flask_login.current_user')
    def test_deck_export_success(self, mock_current_user, client):
        """Test successful deck export."""
        mock_current_user.id = "owner_id"
        mock_current_user.is_authenticated = True
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                # Mock deck document
                mock_deck_doc = Mock()
                mock_deck_doc.exists = True
                mock_db.collection.return_value.document.return_value.get.return_value = mock_deck_doc
                
                # Mock card service and Deck creation
                with patch('app.routes.decks.card_service') as mock_card_service:
                    mock_card_service.get_card_collection.return_value = Mock()
                    
                    with patch('Deck.from_firestore_doc') as mock_from_doc:
                        mock_deck = Mock()
                        mock_deck.owner_id = "owner_id"
                        mock_deck.is_public = True
                        mock_deck.name = "Test Deck"
                        mock_from_doc.return_value = mock_deck
                        
                        response = client.get('/deck/test_deck_id/export/json')
                        
                        # Should return successful response (exact status depends on implementation)
                        assert response.status_code in [200, 302]  # 302 if redirecting

    @patch('flask_login.current_user')
    def test_deck_export_private_deck_unauthorized(self, mock_current_user, client):
        """Test that private decks cannot be exported by non-owners."""
        mock_current_user.id = "different_user"
        mock_current_user.is_authenticated = True
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                # Mock deck document
                mock_deck_doc = Mock()
                mock_deck_doc.exists = True
                mock_db.collection.return_value.document.return_value.get.return_value = mock_deck_doc
                
                # Mock card service and Deck creation
                with patch('app.routes.decks.card_service') as mock_card_service:
                    mock_card_service.get_card_collection.return_value = Mock()
                    
                    with patch('Deck.from_firestore_doc') as mock_from_doc:
                        mock_deck = Mock()
                        mock_deck.owner_id = "deck_owner"
                        mock_deck.is_public = False  # Private deck
                        mock_from_doc.return_value = mock_deck
                        
                        with patch('app.routes.decks.flash'):
                            response = client.get('/deck/private_deck_id/export/json')
                            
                            # Should redirect due to permission denial
                            assert response.status_code == 302


@pytest.mark.integration
class TestDeckDescription:
    """Test deck description update functionality."""
    
    @patch('flask_login.current_user')
    def test_update_deck_description_success(self, mock_current_user, client):
        """Test successful deck description update."""
        mock_current_user.id = "owner_id"
        mock_current_user.is_authenticated = True
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                # Mock deck document
                mock_deck_doc = Mock()
                mock_deck_doc.exists = True
                mock_db.collection.return_value.document.return_value.get.return_value = mock_deck_doc
                
                # Mock card service
                with patch('app.routes.decks.card_service') as mock_card_service:
                    mock_card_service.get_card_collection.return_value = Mock()
                    
                    with patch('Deck.from_firestore_doc') as mock_from_doc:
                        mock_deck = Mock()
                        mock_deck.owner_id = "owner_id"
                        mock_deck.name = "Test Deck"
                        mock_from_doc.return_value = mock_deck
                        
                        request_data = {'description': 'Updated description'}
                        
                        response = client.post('/api/decks/test_deck/description',
                                             json=request_data,
                                             content_type='application/json')
                        
                        assert response.status_code == 200
                        data = json.loads(response.data)
                        assert data['success'] is True


@pytest.mark.integration
class TestDeckErrorHandling:
    """Test error handling in deck operations."""
    
    @patch('flask_login.current_user')
    def test_deck_operations_database_error(self, mock_current_user, client):
        """Test handling of database errors during deck operations."""
        mock_current_user.id = "test_user"
        mock_current_user.is_authenticated = True
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.get_db') as mock_get_db:
                # Mock database to raise exception
                mock_get_db.side_effect = Exception("Database connection failed")
                
                response = client.get('/api/decks/test_deck_id')
                
                # Should handle error gracefully
                assert response.status_code == 500

    @patch('flask_login.current_user')
    def test_deck_creation_validation_error(self, mock_current_user, client):
        """Test deck creation with invalid data."""
        mock_current_user.id = "test_user"
        mock_current_user.is_authenticated = True
        mock_current_user.data = {'deck_ids': []}
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.decks.rate_limit_heavy', lambda: lambda f: f):
                with patch('app.routes.decks.get_db') as mock_get_db:
                    mock_db = Mock()
                    mock_get_db.return_value = mock_db
                    
                    # Mock card service
                    with patch('app.routes.decks.card_service') as mock_card_service:
                        mock_card_service.get_card_collection.return_value = Mock()
                        
                        # Mock Deck.from_cards_data to raise validation error
                        with patch('Deck.from_cards_data') as mock_from_cards:
                            mock_from_cards.side_effect = ValueError("Invalid deck data")
                            
                            deck_data = {
                                'name': '',  # Invalid: empty name
                                'card_ids': []  # Invalid: no cards
                            }
                            
                            response = client.post('/api/decks',
                                                 json=deck_data,
                                                 content_type='application/json')
                            
                            assert response.status_code == 400
                            data = json.loads(response.data)
                            assert data['success'] is False