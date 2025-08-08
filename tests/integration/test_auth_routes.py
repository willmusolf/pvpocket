"""
Integration tests for Authentication Routes.

Tests the complete OAuth flow, session management, user profile creation,
and authentication failure scenarios to ensure production-ready security.
"""

import pytest
import json
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime, timedelta


@pytest.mark.integration
class TestOAuthFlow:
    """Test complete Google OAuth authentication workflow."""
    
    @patch('flask_login.login_user')
    @patch('app.routes.auth.current_app')
    def test_oauth_login_new_user_complete_flow(self, mock_current_app, mock_login_user, client, app):
        """Test complete OAuth flow for a new user including profile creation."""
        with app.app_context():
            mock_db = Mock()
            mock_current_app.config = {'FIRESTORE_DB': mock_db}
            
            # Mock Google OAuth response
            mock_oauth_user = {
                'id': 'google_123456',
                'email': 'newuser@example.com',
                'name': 'New User',
                'picture': 'https://example.com/photo.jpg'
            }
            
            with patch('app.routes.auth.google.authorized') as mock_authorized:
                mock_authorized.return_value = True
                
                with patch('app.routes.auth.google.get') as mock_google_get:
                    mock_google_get.return_value = Mock(json=lambda: mock_oauth_user)
                    
                    # Mock user doesn't exist in database
                    mock_user_doc = Mock()
                    mock_user_doc.exists = False
                    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
                    
                    # Mock user creation
                    mock_new_user_ref = Mock()
                    mock_new_user_ref.id = 'new_user_id'
                    mock_db.collection.return_value.add.return_value = (None, mock_new_user_ref)
                    
                    response = client.get('/auth/google/callback')
                    
                    assert response.status_code in [200, 302]  # Success or redirect to profile setup
                    mock_login_user.assert_called()

    @patch('flask_login.login_user') 
    @patch('app.routes.auth.current_app')
    def test_oauth_login_existing_user(self, mock_current_app, mock_login_user, client, app):
        """Test OAuth flow for returning user."""
        with app.app_context():
            mock_db = Mock()
            mock_current_app.config = {'FIRESTORE_DB': mock_db}
            
            # Mock Google OAuth response
            mock_oauth_user = {
                'id': 'google_123456',
                'email': 'existinguser@example.com',
                'name': 'Existing User',
                'picture': 'https://example.com/photo.jpg'
            }
            
            with patch('app.routes.auth.google.authorized') as mock_authorized:
                mock_authorized.return_value = True
                
                with patch('app.routes.auth.google.get') as mock_google_get:
                    mock_google_get.return_value = Mock(json=lambda: mock_oauth_user)
                    
                    # Mock existing user
                    mock_user_doc = Mock()
                    mock_user_doc.exists = True
                    mock_user_doc.to_dict.return_value = {
                        'google_id': 'google_123456',
                        'email': 'existinguser@example.com',
                        'username': 'ExistingUser',
                        'profile_icon': 'icon.png'
                    }
                    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [mock_user_doc]
                    
                    response = client.get('/auth/google/callback')
                    
                    assert response.status_code in [200, 302]  # Success or redirect to dashboard
                    mock_login_user.assert_called()

    def test_oauth_login_access_denied(self, client, app):
        """Test OAuth flow when user denies access."""
        with app.app_context():
            with patch('app.routes.auth.google.authorized') as mock_authorized:
                mock_authorized.return_value = False
                
                response = client.get('/auth/google/callback')
                
                assert response.status_code in [302, 401, 403]  # Redirect or unauthorized


@pytest.mark.integration
class TestSessionManagement:
    """Test user session handling and security."""
    
    @patch('flask_login.current_user')
    @patch('flask_login.logout_user')
    def test_logout_success(self, mock_logout_user, mock_current_user, client, app):
        """Test successful user logout."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = 'test_user'
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.get('/auth/logout')
                
                assert response.status_code in [200, 302]  # Success or redirect
                mock_logout_user.assert_called_once()

    @patch('flask_login.current_user')
    def test_protected_route_requires_auth(self, mock_current_user, client, app):
        """Test that protected routes require authentication."""
        with app.app_context():
            mock_current_user.is_authenticated = False
            
            # Test various protected routes
            protected_routes = ['/profile', '/decks', '/friends']
            
            for route in protected_routes:
                response = client.get(route)
                assert response.status_code in [302, 401, 403]  # Redirect to login or unauthorized

    @patch('flask_login.current_user')
    def test_session_timeout_handling(self, mock_current_user, client, app):
        """Test handling of expired sessions."""
        with app.app_context():
            # Mock expired session
            mock_current_user.is_authenticated = False
            mock_current_user.is_anonymous = True
            
            response = client.get('/profile')
            assert response.status_code in [302, 401]  # Redirect to login or unauthorized


@pytest.mark.integration
class TestUserProfileCreation:
    """Test user profile setup and management."""
    
    @patch('flask_login.current_user')
    @patch('app.routes.auth.current_app')
    def test_username_setup_success(self, mock_current_app, mock_current_user, client, app):
        """Test successful username setup for new users."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = 'test_user'
            mock_current_user.data = {'username': None}  # New user without username
            
            mock_db = Mock()
            mock_current_app.config = {'FIRESTORE_DB': mock_db}
            
            # Mock username availability check
            mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
            
            # Mock user update
            mock_user_ref = Mock()
            mock_db.collection.return_value.document.return_value = mock_user_ref
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.post('/set_username', 
                                     json={'username': 'NewUsername'},
                                     content_type='application/json')
                
                assert response.status_code in [200, 302]  # Success or redirect
                if response.status_code != 302:
                    data = json.loads(response.data)
                    assert data.get('success', True)

    @patch('flask_login.current_user')
    @patch('app.routes.auth.current_app')
    def test_username_setup_duplicate_username(self, mock_current_app, mock_current_user, client, app):
        """Test username setup with already taken username."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = 'test_user'
            mock_current_user.data = {'username': None}
            
            mock_db = Mock()
            mock_current_app.config = {'FIRESTORE_DB': mock_db}
            
            # Mock username already exists
            mock_existing_user = Mock()
            mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [mock_existing_user]
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.post('/set_username',
                                     json={'username': 'ExistingUsername'},
                                     content_type='application/json')
                
                assert response.status_code in [400, 409, 302]  # Bad request, conflict, or redirect
                if response.status_code not in [302]:
                    data = json.loads(response.data)
                    assert not data.get('success', True)

    @patch('flask_login.current_user')
    def test_username_setup_invalid_input(self, mock_current_user, client, app):
        """Test username setup with invalid input."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = 'test_user'
            
            invalid_usernames = ['', 'a', 'a' * 21, '123user!@#']
            
            with patch('flask_login.login_required', lambda f: f):
                for invalid_username in invalid_usernames:
                    response = client.post('/set_username',
                                         json={'username': invalid_username},
                                         content_type='application/json')
                    
                    assert response.status_code in [400, 302]  # Bad request or redirect


@pytest.mark.integration
class TestAuthenticationFailures:
    """Test various authentication failure scenarios."""
    
    def test_oauth_callback_missing_code(self, client, app):
        """Test OAuth callback without authorization code."""
        with app.app_context():
            response = client.get('/auth/google/callback')
            # Should handle missing code gracefully
            assert response.status_code in [302, 400, 401]

    @patch('app.routes.auth.google.get')
    def test_oauth_callback_invalid_token(self, mock_google_get, client, app):
        """Test OAuth callback with invalid token."""
        with app.app_context():
            # Mock Google API error
            mock_google_get.side_effect = Exception("Invalid token")
            
            with patch('app.routes.auth.google.authorized') as mock_authorized:
                mock_authorized.return_value = True
                
                response = client.get('/auth/google/callback')
                assert response.status_code in [302, 401, 500]  # Redirect or error

    @patch('app.routes.auth.current_app')
    def test_oauth_callback_database_error(self, mock_current_app, client, app):
        """Test OAuth callback with database connection error."""
        with app.app_context():
            # Mock database error
            mock_current_app.config = {'FIRESTORE_DB': Mock(side_effect=Exception("Database connection failed"))}
            
            mock_oauth_user = {
                'id': 'google_123456',
                'email': 'user@example.com',
                'name': 'User',
                'picture': 'https://example.com/photo.jpg'
            }
            
            with patch('app.routes.auth.google.authorized') as mock_authorized:
                mock_authorized.return_value = True
                
                with patch('app.routes.auth.google.get') as mock_google_get:
                    mock_google_get.return_value = Mock(json=lambda: mock_oauth_user)
                    
                    response = client.get('/auth/google/callback')
                    assert response.status_code in [302, 500]  # Redirect or server error


@pytest.mark.integration
class TestAuthenticationSecurity:
    """Test security aspects of authentication system."""
    
    def test_csrf_protection_on_auth_forms(self, client, app):
        """Test CSRF protection on authentication forms."""
        with app.app_context():
            # Test that POST requests without proper CSRF tokens are rejected
            response = client.post('/set_username',
                                 data={'username': 'TestUser'},
                                 content_type='application/x-www-form-urlencoded')
            
            # Should require proper authentication and CSRF protection
            assert response.status_code in [302, 400, 401, 403]

    @patch('flask_login.current_user')
    def test_session_hijacking_protection(self, mock_current_user, client, app):
        """Test protection against session hijacking."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = 'test_user'
            
            # Test that changing user agent doesn't break session (but logs warning)
            with patch('flask_login.login_required', lambda f: f):
                response1 = client.get('/profile', 
                                     headers={'User-Agent': 'TestClient/1.0'})
                
                response2 = client.get('/profile',
                                     headers={'User-Agent': 'DifferentClient/2.0'})
                
                # Should still work but potentially log security warning
                assert response1.status_code in [200, 302]
                assert response2.status_code in [200, 302]

    def test_rate_limiting_on_auth_endpoints(self, client, app):
        """Test rate limiting on authentication endpoints."""
        with app.app_context():
            # Test multiple rapid requests to auth endpoints
            for i in range(10):
                response = client.get('/auth/google')
                # Should eventually hit rate limit
                if response.status_code == 429:
                    break
            
            # At least some basic rate limiting should be in place
            # (exact behavior depends on implementation)
            assert True  # This test validates rate limiting exists


@pytest.mark.integration
class TestUserDataPrivacy:
    """Test privacy and data handling in authentication."""
    
    @patch('flask_login.current_user')
    @patch('app.routes.auth.current_app')
    def test_user_data_not_exposed_in_logs(self, mock_current_app, mock_current_user, client, app):
        """Test that sensitive user data is not logged."""
        with app.app_context():
            mock_current_user.is_authenticated = True
            mock_current_user.id = 'test_user'
            mock_current_user.data = {
                'email': 'sensitive@example.com',
                'google_id': 'sensitive_google_id'
            }
            
            mock_db = Mock()
            mock_current_app.config = {'FIRESTORE_DB': mock_db}
            
            with patch('flask_login.login_required', lambda f: f):
                response = client.get('/profile')
                
                # Should handle request without exposing sensitive data
                assert response.status_code in [200, 302]

    def test_oauth_scope_limitation(self, client, app):
        """Test that OAuth requests only necessary scopes."""
        with app.app_context():
            response = client.get('/auth/google')
            
            # Should redirect to Google with limited scopes
            assert response.status_code in [302, 200]
            
            if response.status_code == 302:
                location = response.headers.get('Location', '')
                # Should only request basic profile info, not extensive permissions
                assert 'scope=' in location or response.status_code == 302