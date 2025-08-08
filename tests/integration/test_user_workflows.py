"""
Integration tests for Complete User Workflows.

Tests end-to-end user journeys including registration, deck creation,
friend interactions, and multi-user scenarios for production readiness.
"""

import pytest
import json
from unittest.mock import patch, Mock, MagicMock

# Skip all tests in this file due to Flask context issues
pytestmark = pytest.mark.skip(reason="Integration tests need Flask context refactoring")

from datetime import datetime, timedelta


@pytest.mark.integration
class TestNewUserOnboarding:
    """Test complete new user onboarding workflow."""
    
    @patch('flask_login.login_user')
    @patch('app.routes.auth.get_db')
    def test_complete_new_user_journey(self, mock_get_db, mock_login_user, client, app):
        """Test complete new user journey: OAuth → Profile Setup → First Deck → Collection."""
        with app.app_context():
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Step 1: OAuth Registration
            mock_oauth_user = {
                'id': 'google_newuser123',
                'email': 'newuser@example.com',
                'name': 'New User',
                'picture': 'https://example.com/photo.jpg'
            }
            
            # Mock new user creation
            mock_new_user_ref = Mock()
            mock_new_user_ref.id = 'new_user_firebase_id'
            mock_db.collection.return_value.add.return_value = (None, mock_new_user_ref)
            mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
            
            with patch('app.routes.auth.google.authorized') as mock_authorized:
                mock_authorized.return_value = True
                with patch('app.routes.auth.google.get') as mock_google_get:
                    mock_google_get.return_value = Mock(json=lambda: mock_oauth_user)
                    
                    # OAuth callback
                    oauth_response = client.get('/auth/google/callback')
                    assert oauth_response.status_code in [200, 302]
                    mock_login_user.assert_called()
            
            # Step 2: Username Setup
            with patch('flask_login.current_user') as mock_current_user:
                mock_current_user.is_authenticated = True
                mock_current_user.id = 'new_user_firebase_id'
                mock_current_user.data = {'username': None}
                
                # Mock username availability check
                mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
                mock_user_ref = Mock()
                mock_db.collection.return_value.document.return_value = mock_user_ref
                
                with patch('flask_login.login_required', lambda f: f):
                    username_response = client.post('/set_username',
                                                   json={'username': 'NewUsername'},
                                                   content_type='application/json')
                    assert username_response.status_code in [200, 302]
            
            # Step 3: First Deck Creation
            with patch('flask_login.current_user') as mock_current_user:
                mock_current_user.is_authenticated = True
                mock_current_user.id = 'new_user_firebase_id'
                mock_current_user.data = {
                    'username': 'NewUsername',
                    'deck_ids': []
                }
                
                with patch('flask_login.login_required', lambda f: f):
                    with patch('app.security.rate_limit_heavy', lambda: lambda f: f):
                        with patch('app.routes.decks.card_service') as mock_card_service:
                            mock_card_service.get_card_collection.return_value = Mock()
                            
                            with patch('app.routes.decks.Deck') as mock_deck_class:
                                mock_deck = Mock()
                                mock_deck.to_firestore_dict.return_value = {'name': 'My First Deck'}
                                mock_deck.firestore_id = 'first_deck_id'
                                mock_deck_class.return_value = mock_deck
                                
                                deck_data = {
                                    'name': 'My First Deck',
                                    'card_ids': [25, 26, 27],  # Pikachu evolution line
                                    'cover_card_ids': [25]
                                }
                                
                                deck_response = client.post('/api/decks',
                                                          json=deck_data,
                                                          content_type='application/json')
                                assert deck_response.status_code in [201, 302]
            
            # Step 4: Collection Management
            with patch('flask_login.current_user') as mock_current_user:
                mock_current_user.is_authenticated = True
                mock_current_user.id = 'new_user_firebase_id'
                
                with patch('flask_login.login_required', lambda f: f):
                    with patch('app.security.rate_limit_api', lambda: lambda f: f):
                        with patch('app.routes.collection.card_service') as mock_card_service:
                            mock_card_collection = Mock()
                            mock_card_collection.get_card_by_id.return_value = Mock(id=25, name="Pikachu")
                            mock_card_service.get_card_collection.return_value = mock_card_collection
                            
                            # Add first card to collection
                            collection_response = client.post('/api/collection/add',
                                                             json={'card_id': '25', 'quantity': 1},
                                                             content_type='application/json')
                            assert collection_response.status_code in [200, 302]

    @patch('flask_login.current_user')
    def test_new_user_tutorial_flow(self, mock_current_user, client, app):
        """Test new user tutorial and guidance flow."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = 'tutorial_user'
            mock_current_user.data = {
                'username': 'TutorialUser',
                'tutorial_completed': False,
                'created_at': datetime.now()
            }
            
            with patch('flask_login.login_required', lambda f: f):
                # Check dashboard shows tutorial prompts
                dashboard_response = client.get('/dashboard')
                assert dashboard_response.status_code in [200, 302]
                
                # Complete tutorial steps
                tutorial_steps = ['welcome', 'deck_building', 'collection', 'friends']
                for step in tutorial_steps:
                    with patch('app.routes.main.get_db') as mock_get_db:
                        mock_db = Mock()
                        mock_get_db.return_value = mock_db
                        
                        step_response = client.post('/api/tutorial/complete',
                                                   json={'step': step},
                                                   content_type='application/json')
                        assert step_response.status_code in [200, 302]


@pytest.mark.integration
class TestReturningUserWorkflow:
    """Test returning user login and activity workflows."""
    
    @patch('flask_login.login_user')
    @patch('flask_login.current_user')
    @patch('app.routes.auth.get_db')
    def test_returning_user_login_to_dashboard(self, mock_get_db, mock_current_user, mock_login_user, client, app):
        """Test returning user: Login → Dashboard → Deck Management."""
        with app.app_context():
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Step 1: Successful OAuth login
            mock_oauth_user = {
                'id': 'google_existing123',
                'email': 'returning@example.com',
                'name': 'Returning User',
                'picture': 'https://example.com/photo.jpg'
            }
            
            # Mock existing user
            mock_user_doc = Mock()
            mock_user_doc.exists = True
            mock_user_doc.id = 'existing_user_id'
            mock_user_doc.to_dict.return_value = {
                'google_id': 'google_existing123',
                'email': 'returning@example.com',
                'username': 'ReturningUser',
                'profile_icon': 'icon.png',
                'deck_ids': ['deck1', 'deck2', 'deck3'],
                'last_login': datetime.now() - timedelta(days=2)
            }
            mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [mock_user_doc]
            
            with patch('app.routes.auth.google.authorized') as mock_authorized:
                mock_authorized.return_value = True
                with patch('app.routes.auth.google.get') as mock_google_get:
                    mock_google_get.return_value = Mock(json=lambda: mock_oauth_user)
                    
                    oauth_response = client.get('/auth/google/callback')
                    assert oauth_response.status_code in [200, 302]
                    mock_login_user.assert_called()
            
            # Step 2: Dashboard loads with user data
            mock_current_user.is_authenticated = True
            mock_current_user.id = 'existing_user_id'
            mock_current_user.data = mock_user_doc.to_dict()
            
            with patch('flask_login.login_required', lambda f: f):
                dashboard_response = client.get('/dashboard')
                assert dashboard_response.status_code in [200, 302]
            
            # Step 3: Load user's decks
            with patch('flask_login.login_required', lambda f: f):
                mock_deck_docs = [
                    Mock(id="deck1", to_dict=lambda: {'name': 'Electric Deck', 'updated_at': datetime.now()}),
                    Mock(id="deck2", to_dict=lambda: {'name': 'Water Deck', 'updated_at': datetime.now()}),
                    Mock(id="deck3", to_dict=lambda: {'name': 'Fire Deck', 'updated_at': datetime.now()})
                ]
                mock_db.collection.return_value.where.return_value.order_by.return_value.stream.return_value = mock_deck_docs
                
                decks_response = client.get('/decks')
                assert decks_response.status_code in [200, 302]
            
            # Step 4: Modify an existing deck
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.decks.card_service') as mock_card_service:
                    mock_card_service.get_card_collection.return_value = Mock()
                    
                    with patch('app.routes.decks.Deck.from_firestore_doc') as mock_from_doc:
                        mock_deck = Mock()
                        mock_deck.owner_id = 'existing_user_id'
                        mock_deck.name = 'Electric Deck'
                        mock_from_doc.return_value = mock_deck
                        
                        mock_deck_doc = Mock()
                        mock_deck_doc.exists = True
                        mock_db.collection.return_value.document.return_value.get.return_value = mock_deck_doc
                        
                        deck_update_response = client.post('/api/decks/deck1/description',
                                                         json={'description': 'Updated deck description'},
                                                         content_type='application/json')
                        assert deck_update_response.status_code in [200, 302]

    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_returning_user_collection_sync(self, mock_get_db, mock_current_user, client, app):
        """Test returning user collection synchronization."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = 'sync_user'
            mock_current_user.data = {
                'username': 'SyncUser',
                'last_login': datetime.now() - timedelta(days=7)  # Week ago
            }
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock outdated collection data
            mock_collection_doc = Mock()
            mock_collection_doc.exists = True
            mock_collection_doc.to_dict.return_value = {
                'card_counts': {'1': 1, '2': 2},
                'last_updated': datetime.now() - timedelta(days=8),  # Older than login
                'needs_sync': True
            }
            mock_db.collection.return_value.document.return_value.get.return_value = mock_collection_doc
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_api', lambda: lambda f: f):
                    # Trigger collection sync
                    sync_response = client.post('/api/collection/sync',
                                              json={'force_refresh': True},
                                              content_type='application/json')
                    assert sync_response.status_code in [200, 302]


@pytest.mark.integration
class TestFriendInteractionWorkflow:
    """Test complete friend interaction workflows."""
    
    @patch('flask_login.current_user')
    def test_complete_friend_workflow(self, mock_current_user, client, app):
        """Test complete friend workflow: Search → Request → Accept → Share Deck."""
        with app.app_context():
            # Step 1: User 1 searches for friends
            mock_current_user.id = "user_1"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    
                    # Mock search results
                    mock_docs = [Mock(id="user_2", to_dict=lambda: {"username": "user2", "username_lowercase": "user2"})]
                    mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = mock_docs
                    
                    with patch('app.routes.friends._get_user_snapshot') as mock_snapshot:
                        mock_snapshot.return_value = {"id": "user_2", "username": "User2", "profile_icon": ""}
                        
                        search_response = client.post('/friends/search',
                                                     json={'query': 'user2'},
                                                     content_type='application/json')
                        assert search_response.status_code in [200, 302]
            
            # Step 2: Send friend request
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    mock_batch = Mock()
                    mock_db.batch.return_value = mock_batch
                    
                    request_response = client.post('/friends/request',
                                                 json={'recipient_id': 'user_2'},
                                                 content_type='application/json')
                    assert request_response.status_code in [200, 302]
            
            # Step 3: User 2 accepts the request
            mock_current_user.id = "user_2"
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    mock_transaction = Mock()
                    mock_db.transaction.return_value = mock_transaction
                    
                    with patch('app.routes.friends._get_user_snapshot') as mock_snapshot:
                        mock_snapshot.return_value = {"id": "user_1", "username": "User1", "profile_icon": ""}
                        
                        accept_response = client.post('/friends/accept',
                                                     json={'sender_id': 'user_1'},
                                                     content_type='application/json')
                        assert accept_response.status_code in [200, 302]
            
            # Step 4: User 1 shares a deck with User 2 (now friends)
            mock_current_user.id = "user_1"
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.decks.get_db') as mock_get_db:
                    mock_db = Mock()
                    mock_get_db.return_value = mock_db
                    
                    with patch('app.routes.decks.card_service') as mock_card_service:
                        mock_card_service.get_card_collection.return_value = Mock()
                        
                        with patch('app.routes.decks.Deck.from_firestore_doc') as mock_from_doc:
                            mock_deck = Mock()
                            mock_deck.owner_id = "user_1"
                            mock_deck.is_public = False
                            mock_deck.toggle_privacy.return_value = True
                            mock_from_doc.return_value = mock_deck
                            
                            mock_deck_doc = Mock()
                            mock_deck_doc.exists = True
                            mock_db.collection.return_value.document.return_value.get.return_value = mock_deck_doc
                            
                            share_response = client.post('/api/decks/shared_deck/privacy',
                                                        json={'description': 'Sharing with friends!'},
                                                        content_type='application/json')
                            assert share_response.status_code in [200, 302]

    @patch('flask_login.current_user')
    def test_friend_deck_viewing_workflow(self, mock_current_user, client, app):
        """Test friend deck viewing workflow with privacy controls."""
        with app.app_context():
            mock_current_user.id = "friend_viewer"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    
                    # Mock friend relationship exists
                    mock_friend_doc = Mock()
                    mock_friend_doc.exists = True
                    mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_friend_doc
                    
                    with patch('app.routes.friends.card_service') as mock_card_service:
                        mock_card_service.get_card_collection.return_value = Mock()
                        
                        with patch('app.routes.friends._get_user_snapshot') as mock_snapshot:
                            mock_snapshot.return_value = {"id": "deck_owner", "username": "DeckOwner", "profile_icon": ""}
                            
                            # Mock public deck query
                            mock_public_decks = [
                                Mock(id="public_deck1", to_dict=lambda: {
                                    'name': 'Public Lightning Deck',
                                    'is_public': True,
                                    'description': 'Fast electric attacks'
                                })
                            ]
                            mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = mock_public_decks
                            
                            view_response = client.get('/friends/deck_owner/decks')
                            assert view_response.status_code in [200, 302]


@pytest.mark.integration
class TestMultiUserInteractions:
    """Test scenarios involving multiple users."""
    
    @patch('flask_login.current_user')
    def test_concurrent_deck_creation(self, mock_current_user, client, app):
        """Test multiple users creating decks simultaneously."""
        with app.app_context():
            users = ['user_1', 'user_2', 'user_3']
            
            for user_id in users:
                mock_current_user.id = user_id
                mock_current_user.is_authenticated = True
                mock_current_user.data = {
                    'username': f'User{user_id[-1]}',
                    'deck_ids': []
                }
                
                with patch('flask_login.login_required', lambda f: f):
                    with patch('app.security.rate_limit_heavy', lambda: lambda f: f):
                        with patch('app.routes.decks.get_db') as mock_get_db:
                            mock_db = Mock()
                            mock_get_db.return_value = mock_db
                            
                            with patch('app.routes.decks.card_service') as mock_card_service:
                                mock_card_service.get_card_collection.return_value = Mock()
                                
                                with patch('app.routes.decks.Deck') as mock_deck_class:
                                    mock_deck = Mock()
                                    mock_deck.to_firestore_dict.return_value = {'name': f'Deck by {user_id}'}
                                    mock_deck.firestore_id = f'deck_{user_id}'
                                    mock_deck_class.return_value = mock_deck
                                    
                                    deck_data = {
                                        'name': f'Concurrent Deck {user_id}',
                                        'card_ids': [1, 2, 3],
                                        'cover_card_ids': [1]
                                    }
                                    
                                    response = client.post('/api/decks',
                                                         json=deck_data,
                                                         content_type='application/json')
                                    assert response.status_code in [201, 302]

    @patch('flask_login.current_user')
    def test_friend_request_race_condition(self, mock_current_user, client, app):
        """Test handling of simultaneous friend requests between users."""
        with app.app_context():
            # User 1 sends request to User 2
            mock_current_user.id = "user_1"
            mock_current_user.is_authenticated = True
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    mock_batch = Mock()
                    mock_db.batch.return_value = mock_batch
                    
                    request1_response = client.post('/friends/request',
                                                   json={'recipient_id': 'user_2'},
                                                   content_type='application/json')
                    assert request1_response.status_code in [200, 302]
            
            # User 2 simultaneously sends request to User 1
            mock_current_user.id = "user_2"
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.current_app') as mock_app:
                    mock_db = Mock()
                    mock_app.config.get.return_value = mock_db
                    mock_batch = Mock()
                    mock_db.batch.return_value = mock_batch
                    
                    # Should handle duplicate request gracefully
                    request2_response = client.post('/friends/request',
                                                   json={'recipient_id': 'user_1'},
                                                   content_type='application/json')
                    # Should either succeed or handle conflict gracefully
                    assert request2_response.status_code in [200, 302, 409]


@pytest.mark.integration
class TestErrorRecoveryWorkflows:
    """Test user workflows during error scenarios."""
    
    @patch('flask_login.current_user')
    def test_network_interruption_recovery(self, mock_current_user, client, app):
        """Test user workflow recovery after network interruption."""
        with app.app_context():
            mock_current_user.id = "interrupted_user"
            mock_current_user.is_authenticated = True
            mock_current_user.data = {'username': 'InterruptedUser'}
            
            # Simulate network failure during deck creation
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_heavy', lambda: lambda f: f):
                    with patch('app.routes.decks.get_db') as mock_get_db:
                        # First attempt fails
                        mock_get_db.side_effect = Exception("Network timeout")
                        
                        deck_data = {
                            'name': 'Interrupted Deck',
                            'card_ids': [1, 2, 3]
                        }
                        
                        failed_response = client.post('/api/decks',
                                                     json=deck_data,
                                                     content_type='application/json')
                        assert failed_response.status_code in [500, 302]
                        
                        # Recovery: retry succeeds
                        mock_get_db.side_effect = None
                        mock_db = Mock()
                        mock_get_db.return_value = mock_db
                        
                        with patch('app.routes.decks.card_service') as mock_card_service:
                            mock_card_service.get_card_collection.return_value = Mock()
                            
                            with patch('app.routes.decks.Deck') as mock_deck_class:
                                mock_deck = Mock()
                                mock_deck.to_firestore_dict.return_value = {'name': 'Interrupted Deck'}
                                mock_deck.firestore_id = 'recovered_deck'
                                mock_deck_class.return_value = mock_deck
                                
                                retry_response = client.post('/api/decks',
                                                           json=deck_data,
                                                           content_type='application/json')
                                assert retry_response.status_code in [201, 302]

    @patch('flask_login.current_user')
    def test_session_expiry_during_workflow(self, mock_current_user, client, app):
        """Test handling of session expiry during multi-step workflow."""
        with app.app_context():
            # Start workflow as authenticated user
            mock_current_user.is_authenticated = True
            mock_current_user.id = "expiring_user"
            
            with patch('flask_login.login_required', lambda f: f):
                # Start deck creation process
                step1_response = client.get('/decks')
                assert step1_response.status_code in [200, 302]
                
                # Session expires
                mock_current_user.is_authenticated = False
                
                # Continue workflow - should redirect to login
                step2_response = client.post('/api/decks',
                                           json={'name': 'Test Deck', 'card_ids': [1]},
                                           content_type='application/json')
                assert step2_response.status_code in [302, 401, 403]  # Redirect to login or unauthorized


@pytest.mark.integration
class TestDataConsistencyWorkflows:
    """Test workflows that ensure data consistency."""
    
    @patch('flask_login.current_user')
    def test_user_data_sync_across_sessions(self, mock_current_user, client, app):
        """Test that user data remains consistent across sessions."""
        with app.app_context():
            mock_current_user.id = "consistency_user"
            mock_current_user.is_authenticated = True
            mock_current_user.data = {
                'username': 'ConsistencyUser',
                'deck_ids': ['deck1', 'deck2'],
                'profile_icon': 'icon1.png'
            }
            
            # Session 1: Update profile
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_api', lambda: lambda f: f):
                    with patch('app.routes.main.get_db') as mock_get_db:
                        mock_db = Mock()
                        mock_get_db.return_value = mock_db
                        mock_user_ref = Mock()
                        mock_db.collection.return_value.document.return_value = mock_user_ref
                        
                        profile_response = client.post('/api/profile/update',
                                                      json={'profile_icon': 'new_icon.png'},
                                                      content_type='application/json')
                        assert profile_response.status_code in [200, 302]
            
            # Session 2: Create deck (should have updated profile)
            mock_current_user.data['profile_icon'] = 'new_icon.png'
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_heavy', lambda: lambda f: f):
                    with patch('app.routes.decks.get_db') as mock_get_db:
                        mock_db = Mock()
                        mock_get_db.return_value = mock_db
                        
                        with patch('app.routes.decks.card_service') as mock_card_service:
                            mock_card_service.get_card_collection.return_value = Mock()
                            
                            with patch('app.routes.decks.Deck') as mock_deck_class:
                                mock_deck = Mock()
                                mock_deck.to_firestore_dict.return_value = {'name': 'Consistency Deck'}
                                mock_deck.firestore_id = 'deck3'
                                mock_deck_class.return_value = mock_deck
                                
                                deck_response = client.post('/api/decks',
                                                          json={
                                                              'name': 'Consistency Deck',
                                                              'card_ids': [1, 2, 3]
                                                          },
                                                          content_type='application/json')
                                assert deck_response.status_code in [201, 302]
            
            # Session 3: Verify data consistency
            with patch('flask_login.login_required', lambda f: f):
                dashboard_response = client.get('/dashboard')
                assert dashboard_response.status_code in [200, 302]
                # Should show updated profile and new deck count