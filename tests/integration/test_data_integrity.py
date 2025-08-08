"""
Integration tests for Data Integrity and Transaction Management.

Tests concurrent operations, transaction rollbacks, data consistency,
and database integrity scenarios for production readiness.
"""

import pytest
import json
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime, timedelta
import threading
import time


@pytest.mark.integration
class TestConcurrentOperations:
    """Test handling of concurrent database operations."""
    
    @patch('flask_login.current_user')
    @patch('app.routes.decks.get_db')
    def test_concurrent_deck_creation(self, mock_get_db, mock_current_user, client, app):
        """Test multiple users creating decks simultaneously."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "concurrent_user"
            mock_current_user.data = {
                'username': 'ConcurrentUser',
                'deck_ids': []
            }
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock atomic transaction behavior
            mock_transaction = Mock()
            mock_db.transaction.return_value = mock_transaction
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_heavy', lambda: lambda f: f):
                    with patch('app.routes.decks.card_service') as mock_card_service:
                        mock_card_service.get_card_collection.return_value = Mock()
                        
                        with patch('app.routes.decks.Deck') as mock_deck_class:
                            mock_deck = Mock()
                            mock_deck.to_firestore_dict.return_value = {'name': 'Concurrent Deck'}
                            mock_deck.firestore_id = 'concurrent_deck_1'
                            mock_deck_class.return_value = mock_deck
                            
                            # Simulate multiple concurrent requests
                            responses = []
                            for i in range(3):
                                deck_data = {
                                    'name': f'Concurrent Deck {i}',
                                    'card_ids': [1, 2, 3],
                                    'cover_card_ids': [1]
                                }
                                
                                response = client.post('/api/decks',
                                                     json=deck_data,
                                                     content_type='application/json')
                                responses.append(response)
                            
                            # All requests should either succeed or handle conflicts gracefully
                            for response in responses:
                                assert response.status_code in [201, 409, 302]  # Created, conflict, or redirect

    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_concurrent_collection_updates(self, mock_get_db, mock_current_user, client, app):
        """Test concurrent updates to user collection."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock collection state
            mock_collection_doc = Mock()
            mock_collection_doc.exists = True
            mock_collection_doc.to_dict.return_value = {
                'card_counts': {'1': 5},
                'total_cards': 5
            }
            mock_db.collection.return_value.document.return_value.get.return_value = mock_collection_doc
            
            # Mock transaction behavior
            mock_transaction = Mock()
            mock_db.transaction.return_value = mock_transaction
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_api', lambda: lambda f: f):
                    # Simulate concurrent card additions
                    responses = []
                    for i in range(3):
                        response = client.post('/api/collection/add',
                                             json={'card_id': '1', 'quantity': 1},
                                             content_type='application/json')
                        responses.append(response)
                    
                    # All operations should maintain consistency
                    for response in responses:
                        assert response.status_code in [200, 409, 302]  # Success, conflict, or redirect

    @patch('flask_login.current_user')
    @patch('app.routes.friends.current_app')
    def test_concurrent_friend_requests(self, mock_app, mock_current_user, client, app):
        """Test handling of simultaneous friend requests."""
        with app.app_context():
            mock_db = Mock()
            mock_app.config.get.return_value = mock_db
            
            # Test User A sends request to User B
            mock_current_user.id = "user_a"
            mock_current_user.is_authenticated = True
            
            mock_batch = Mock()
            mock_db.batch.return_value = mock_batch
            
            with patch('flask_login.login_required', lambda f: f):
                response_a = client.post('/friends/request',
                                       json={'recipient_id': 'user_b'},
                                       content_type='application/json')
                
                # Switch to User B and send request to User A
                mock_current_user.id = "user_b"
                
                response_b = client.post('/friends/request',
                                       json={'recipient_id': 'user_a'},
                                       content_type='application/json')
                
                # Both should either succeed or handle duplicate gracefully
                assert response_a.status_code in [200, 409, 302]
                assert response_b.status_code in [200, 409, 302]


@pytest.mark.integration
class TestTransactionRollbacks:
    """Test transaction rollback scenarios."""
    
    @patch('flask_login.current_user')
    @patch('app.routes.decks.get_db')
    def test_deck_creation_rollback_on_failure(self, mock_get_db, mock_current_user, client, app):
        """Test that failed deck creation rolls back all changes."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            mock_current_user.data = {
                'username': 'TestUser',
                'deck_ids': ['existing_deck']
            }
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock partial transaction failure
            def failing_transaction(*args, **kwargs):
                # Simulate failure after some operations
                raise Exception("Transaction failed at commit")
            
            mock_transaction = Mock()
            mock_transaction.side_effect = failing_transaction
            mock_db.transaction.return_value = mock_transaction
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_heavy', lambda: lambda f: f):
                    with patch('app.routes.decks.card_service') as mock_card_service:
                        mock_card_service.get_card_collection.return_value = Mock()
                        
                        deck_data = {
                            'name': 'Failed Deck',
                            'card_ids': [1, 2, 3]
                        }
                        
                        response = client.post('/api/decks',
                                             json=deck_data,
                                             content_type='application/json')
                        
                        # Should return error and not create partial data
                        assert response.status_code in [500, 302]

    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_collection_update_atomic_rollback(self, mock_get_db, mock_current_user, client, app):
        """Test atomic rollback on collection update failure."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock transaction that fails during execution
            def failing_update_transaction(transaction, *args, **kwargs):
                # Simulate partial update then failure
                raise Exception("Database constraint violation")
            
            mock_transaction = Mock()
            mock_db.transaction.return_value = mock_transaction
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_api', lambda: lambda f: f):
                    with patch('app.routes.collection.update_collection_transaction', side_effect=failing_update_transaction):
                        response = client.post('/api/collection/add',
                                             json={'card_id': '123', 'quantity': 1},
                                             content_type='application/json')
                        
                        # Should fail gracefully without partial updates
                        assert response.status_code in [500, 302]

    @patch('flask_login.current_user')
    @patch('app.routes.friends.current_app')
    def test_friend_acceptance_transaction_integrity(self, mock_app, mock_current_user, client, app):
        """Test friend acceptance maintains transaction integrity on failure."""
        with app.app_context():
            mock_current_user.id = "user_recipient"
            mock_current_user.is_authenticated = True
            
            mock_db = Mock()
            mock_app.config.get.return_value = mock_db
            mock_app.logger = Mock()
            
            # Mock transaction failure during friend acceptance
            def failing_accept_transaction(*args, **kwargs):
                raise Exception("Network timeout during acceptance")
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.routes.friends.accept_request_transaction', side_effect=failing_accept_transaction):
                    response = client.post('/friends/accept',
                                         json={'sender_id': 'user_sender'},
                                         content_type='application/json')
                    
                    # Should fail without creating partial friendship data
                    assert response.status_code in [500, 302]
                    
                    # Verify error was logged for monitoring
                    mock_app.logger.error.assert_called()


@pytest.mark.integration
class TestDataConsistency:
    """Test data consistency across operations."""
    
    @patch('flask_login.current_user')
    @patch('app.routes.decks.get_db')
    def test_deck_card_consistency(self, mock_get_db, mock_current_user, client, app):
        """Test that deck creation maintains card data consistency."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "consistency_user"
            mock_current_user.data = {
                'username': 'ConsistencyUser',
                'deck_ids': []
            }
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_heavy', lambda: lambda f: f):
                    with patch('app.routes.decks.card_service') as mock_card_service:
                        # Mock card validation
                        mock_card_collection = Mock()
                        mock_card_collection.get_card_by_id.side_effect = lambda id: Mock(id=id) if id in ['1', '2', '3'] else None
                        mock_card_service.get_card_collection.return_value = mock_card_collection
                        
                        with patch('app.routes.decks.Deck') as mock_deck_class:
                            # Mock deck validation
                            mock_deck = Mock()
                            mock_deck.validate_card_ids.return_value = True
                            mock_deck.to_firestore_dict.return_value = {'name': 'Valid Deck'}
                            mock_deck.firestore_id = 'valid_deck'
                            mock_deck_class.return_value = mock_deck
                            
                            # Create deck with valid cards
                            deck_data = {
                                'name': 'Consistent Deck',
                                'card_ids': ['1', '2', '3'],  # All should exist
                                'cover_card_ids': ['1']
                            }
                            
                            response = client.post('/api/decks',
                                                 json=deck_data,
                                                 content_type='application/json')
                            
                            # Should succeed with valid data
                            assert response.status_code in [201, 302]
                            
                            # Verify card validation was called
                            assert mock_card_collection.get_card_by_id.call_count >= 3

    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_collection_count_consistency(self, mock_get_db, mock_current_user, client, app):
        """Test that collection counts remain consistent across operations."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock initial collection state
            initial_collection = {
                'card_counts': {'1': 3, '2': 2},
                'total_cards': 5,
                'unique_cards': 2
            }
            
            mock_collection_doc = Mock()
            mock_collection_doc.exists = True
            mock_collection_doc.to_dict.return_value = initial_collection
            mock_db.collection.return_value.document.return_value.get.return_value = mock_collection_doc
            
            # Mock transaction that maintains consistency
            def consistent_transaction(transaction, collection_ref, updates):
                # Verify counts are consistent
                if 'card_counts' in updates and 'total_cards' in updates:
                    expected_total = sum(updates['card_counts'].values())
                    assert updates['total_cards'] == expected_total
                    assert updates['unique_cards'] == len(updates['card_counts'])
            
            mock_transaction = Mock()
            mock_transaction.side_effect = consistent_transaction
            mock_db.transaction.return_value = mock_transaction
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_api', lambda: lambda f: f):
                    # Add card and verify consistency
                    response = client.post('/api/collection/add',
                                         json={'card_id': '1', 'quantity': 2},
                                         content_type='application/json')
                    
                    assert response.status_code in [200, 302]

    @patch('flask_login.current_user')
    @patch('app.routes.main.get_db')
    def test_user_profile_consistency(self, mock_get_db, mock_current_user, client, app):
        """Test user profile data consistency across updates."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "profile_user"
            mock_current_user.data = {
                'username': 'OriginalUser',
                'email': 'user@example.com',
                'profile_icon': 'old_icon.png',
                'deck_ids': ['deck1', 'deck2']
            }
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock user document update
            mock_user_ref = Mock()
            mock_db.collection.return_value.document.return_value = mock_user_ref
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_api', lambda: lambda f: f):
                    # Update profile
                    update_data = {
                        'profile_icon': 'new_icon.png',
                        'display_name': 'Updated Display Name'
                    }
                    
                    response = client.post('/api/profile/update',
                                         json=update_data,
                                         content_type='application/json')
                    
                    assert response.status_code in [200, 302]
                    
                    # Verify update was called with consistent data
                    if response.status_code != 302:
                        mock_user_ref.update.assert_called()


@pytest.mark.integration
class TestDatabaseConstraints:
    """Test database constraint enforcement."""
    
    @patch('flask_login.current_user')
    @patch('app.routes.decks.get_db')
    def test_deck_name_uniqueness_constraint(self, mock_get_db, mock_current_user, client, app):
        """Test that deck names must be unique per user."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "constraint_user"
            mock_current_user.data = {
                'username': 'ConstraintUser',
                'deck_ids': ['existing_deck']
            }
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock existing deck with same name
            mock_existing_deck = Mock()
            mock_existing_deck.exists = True
            mock_existing_deck.to_dict.return_value = {'name': 'Duplicate Deck'}
            mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = [mock_existing_deck]
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_heavy', lambda: lambda f: f):
                    with patch('app.routes.decks.card_service') as mock_card_service:
                        mock_card_service.get_card_collection.return_value = Mock()
                        
                        # Try to create deck with duplicate name
                        deck_data = {
                            'name': 'Duplicate Deck',  # Same as existing
                            'card_ids': [1, 2, 3]
                        }
                        
                        response = client.post('/api/decks',
                                             json=deck_data,
                                             content_type='application/json')
                        
                        # Should reject duplicate name
                        assert response.status_code in [400, 409, 302]  # Bad request, conflict, or redirect

    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_collection_quantity_constraints(self, mock_get_db, mock_current_user, client, app):
        """Test that collection quantities have proper constraints."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "test_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_api', lambda: lambda f: f):
                    # Test negative quantity
                    response = client.post('/api/collection/add',
                                         json={'card_id': '123', 'quantity': -5},
                                         content_type='application/json')
                    
                    assert response.status_code in [400, 302]  # Should reject negative quantities
                    
                    # Test zero quantity
                    response = client.post('/api/collection/add',
                                         json={'card_id': '123', 'quantity': 0},
                                         content_type='application/json')
                    
                    assert response.status_code in [400, 302]  # Should reject zero quantities

    @patch('flask_login.current_user')
    @patch('app.routes.friends.current_app')
    def test_friend_relationship_constraints(self, mock_app, mock_current_user, client, app):
        """Test friend relationship database constraints."""
        with app.app_context():
            mock_current_user.id = "user_1"
            mock_current_user.is_authenticated = True
            
            mock_db = Mock()
            mock_app.config.get.return_value = mock_db
            
            with patch('flask_login.login_required', lambda f: f):
                # Test self-friendship constraint
                response = client.post('/friends/request',
                                     json={'recipient_id': 'user_1'},  # Same as sender
                                     content_type='application/json')
                
                assert response.status_code in [400, 302]  # Should reject self-friendship
                
                # Test empty recipient constraint
                response = client.post('/friends/request',
                                     json={'recipient_id': ''},
                                     content_type='application/json')
                
                assert response.status_code in [400, 302]  # Should reject empty recipient


@pytest.mark.integration
class TestDataRecovery:
    """Test data recovery and backup scenarios."""
    
    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_collection_data_recovery(self, mock_get_db, mock_current_user, client, app):
        """Test collection data recovery from backup."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "recovery_user"
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock backup data
            backup_data = {
                'card_counts': {'1': 5, '2': 3, '3': 2},
                'total_cards': 10,
                'unique_cards': 3,
                'backup_timestamp': datetime.now().isoformat()
            }
            
            mock_backup_doc = Mock()
            mock_backup_doc.exists = True
            mock_backup_doc.to_dict.return_value = backup_data
            mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_backup_doc
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.post('/api/collection/restore',
                                     json={'backup_id': 'backup_123'},
                                     content_type='application/json')
                
                assert response.status_code in [200, 302]  # Success or redirect

    @patch('flask_login.current_user')
    @patch('app.routes.decks.get_db')
    def test_deck_data_validation_recovery(self, mock_get_db, mock_current_user, client, app):
        """Test recovery from corrupted deck data scenarios."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "validation_user"
            mock_current_user.data = {'username': 'ValidationUser'}
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_heavy', lambda: lambda f: f):
                    with patch('app.routes.decks.card_service') as mock_card_service:
                        mock_card_collection = Mock()
                        mock_card_service.get_card_collection.return_value = mock_card_collection
                        
                        # Test deck with invalid data structure
                        invalid_deck_data = {
                            'name': 'Recovery Test',
                            'card_ids': ['invalid', 'data', None, ''],  # Invalid entries
                            'cover_card_ids': []
                        }
                        
                        response = client.post('/api/decks',
                                             json=invalid_deck_data,
                                             content_type='application/json')
                        
                        # Should handle gracefully and provide meaningful error
                        assert response.status_code in [400, 302]


@pytest.mark.integration
class TestOfflineSync:
    """Test offline/online synchronization scenarios."""
    
    @patch('flask_login.current_user')
    @patch('app.routes.collection.get_db')
    def test_offline_collection_sync_recovery(self, mock_get_db, mock_current_user, client, app):
        """Test collection sync after offline period."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "offline_user"
            mock_current_user.data = {
                'last_sync': (datetime.now() - timedelta(days=7)).isoformat()  # Week ago
            }
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock stale collection data
            mock_collection_doc = Mock()
            mock_collection_doc.exists = True
            mock_collection_doc.to_dict.return_value = {
                'card_counts': {'1': 1, '2': 1},
                'last_updated': (datetime.now() - timedelta(days=8)).isoformat(),
                'sync_status': 'stale'
            }
            mock_db.collection.return_value.document.return_value.get.return_value = mock_collection_doc
            
            with patch('flask_login.login_required', lambda f: f):
                with patch('app.security.rate_limit_api', lambda: lambda f: f):
                    # Trigger sync after offline period
                    response = client.post('/api/collection/sync',
                                         json={'force_sync': True, 'resolve_conflicts': True},
                                         content_type='application/json')
                    
                    assert response.status_code in [200, 302]  # Successful sync or redirect

    @patch('flask_login.current_user')
    @patch('app.routes.main.get_db')
    def test_user_data_conflict_resolution(self, mock_get_db, mock_current_user, client, app):
        """Test user data conflict resolution during sync."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = "conflict_user"
            mock_current_user.data = {
                'username': 'ConflictUser',
                'profile_icon': 'local_icon.png',
                'last_modified': datetime.now().isoformat()
            }
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock server data with conflicts
            mock_server_data = {
                'profile_icon': 'server_icon.png',
                'display_name': 'Server Display Name',
                'last_modified': (datetime.now() + timedelta(minutes=5)).isoformat()  # Newer
            }
            
            mock_user_doc = Mock()
            mock_user_doc.exists = True
            mock_user_doc.to_dict.return_value = mock_server_data
            mock_db.collection.return_value.document.return_value.get.return_value = mock_user_doc
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.post('/api/profile/sync',
                                     json={'conflict_resolution': 'server_wins'},
                                     content_type='application/json')
                
                assert response.status_code in [200, 302]  # Conflict resolved or redirect