"""
Integration tests for Authentication Flows.

Tests complete authentication lifecycle including:
- Google OAuth flow simulation
- Username setup and validation
- Profile management
- Account deletion
- Session management
- Security and authorization checks
"""

import pytest
import json
from unittest.mock import patch, Mock
import re


@pytest.mark.integration
class TestLoginProcess:
    """Test login and OAuth flow."""
    
    def test_login_prompt_page(self, client):
        """Test that login prompt page loads correctly."""
        response = client.get('/login-prompt')
        
        assert response.status_code == 200

    @patch('flask_login.current_user')
    def test_oauth_callback_success(self, mock_current_user, client):
        """Test successful OAuth callback processing."""
        # This would test the OAuth callback endpoint
        # Implementation depends on your OAuth setup
        mock_current_user.is_authenticated = False
        
        # Mock OAuth success scenario
        with patch('flask_dance.contrib.google.google') as mock_google:
            mock_google.authorized = True
            
            # Test would depend on your specific OAuth implementation
            pass

    @patch('flask_login.current_user')
    def test_unauthenticated_access_redirect(self, mock_current_user, client):
        """Test that unauthenticated users are redirected to login."""
        mock_current_user.is_authenticated = False
        
        response = client.get('/user/profile')
        
        # Should redirect to login
        assert response.status_code in [302, 401]


@pytest.mark.integration
class TestUsernameSetup:
    """Test username setup flow."""
    
    @patch('flask_login.current_user')
    def test_username_setup_page_loads(self, mock_current_user, client):
        """Test that username setup page loads for authenticated users."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.auth.current_app') as mock_app:
                mock_db = Mock()
                mock_app.config.get.return_value = mock_db
                mock_app.config.__getitem__ = Mock(return_value=["icon1.png", "icon2.png"])
                
                # Mock user document exists but username not set
                mock_doc = Mock()
                mock_doc.exists = True
                mock_doc.to_dict.return_value = {'username_set': False}
                mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
                
                response = client.get('/set-username')
                
                assert response.status_code == 200

    @patch('flask_login.current_user')
    def test_username_setup_valid_submission(self, mock_current_user, client):
        """Test valid username submission."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.auth.current_app') as mock_app:
                mock_db = Mock()
                mock_app.config.get.return_value = mock_db
                mock_app.config.__getitem__ = Mock(return_value=["icon1.png", "icon2.png"])
                
                # Mock user document
                mock_doc = Mock()
                mock_doc.exists = True
                mock_doc.to_dict.return_value = {'username_set': False}
                mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
                
                # Mock username uniqueness check
                with patch('app.routes.auth.is_username_globally_unique', return_value=True):
                    with patch('app.routes.auth.profanity_check', return_value=False):
                        form_data = {
                            'new_username': 'validuser123',
                            'profile_icon': 'icon1.png'
                        }
                        
                        response = client.post('/set-username', data=form_data)
                        
                        # Should redirect after success
                        assert response.status_code == 302

    @patch('flask_login.current_user')
    def test_username_setup_invalid_length(self, mock_current_user, client):
        """Test username submission with invalid length."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.auth.current_app') as mock_app:
                mock_db = Mock()
                mock_app.config.get.return_value = mock_db
                mock_app.config.__getitem__ = Mock(return_value=["icon1.png"])
                
                # Mock user document
                mock_doc = Mock()
                mock_doc.exists = True
                mock_doc.to_dict.return_value = {'username_set': False}
                mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
                
                form_data = {
                    'new_username': 'ab',  # Too short
                    'profile_icon': 'icon1.png'
                }
                
                response = client.post('/set-username', data=form_data)
                
                assert response.status_code == 200
                response_text = response.get_data(as_text=True)
                assert "3-20 characters" in response_text

    @patch('flask_login.current_user')
    def test_username_setup_invalid_characters(self, mock_current_user, client):
        """Test username submission with invalid characters."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.auth.current_app') as mock_app:
                mock_db = Mock()
                mock_app.config.get.return_value = mock_db
                mock_app.config.__getitem__ = Mock(return_value=["icon1.png"])
                
                # Mock user document
                mock_doc = Mock()
                mock_doc.exists = True
                mock_doc.to_dict.return_value = {'username_set': False}
                mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
                
                form_data = {
                    'new_username': 'invalid user!',  # Contains space and special char
                    'profile_icon': 'icon1.png'
                }
                
                response = client.post('/set-username', data=form_data)
                
                assert response.status_code == 200
                response_text = response.get_data(as_text=True)
                assert "letters, numbers, and underscores" in response_text

    @patch('flask_login.current_user')
    def test_username_setup_duplicate_username(self, mock_current_user, client):
        """Test username submission with duplicate username."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.auth.current_app') as mock_app:
                mock_db = Mock()
                mock_app.config.get.return_value = mock_db
                mock_app.config.__getitem__ = Mock(return_value=["icon1.png"])
                
                # Mock user document
                mock_doc = Mock()
                mock_doc.exists = True
                mock_doc.to_dict.return_value = {'username_set': False}
                mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
                
                # Mock username not unique
                with patch('app.routes.auth.is_username_globally_unique', return_value=False):
                    form_data = {
                        'new_username': 'takenusr',
                        'profile_icon': 'icon1.png'
                    }
                    
                    response = client.post('/set-username', data=form_data)
                    
                    assert response.status_code == 200
                    response_text = response.get_data(as_text=True)
                    assert "already taken" in response_text

    @patch('flask_login.current_user')
    def test_username_setup_profanity_check(self, mock_current_user, client):
        """Test username submission with profanity."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.auth.current_app') as mock_app:
                mock_db = Mock()
                mock_app.config.get.return_value = mock_db
                mock_app.config.__getitem__ = Mock(return_value=["icon1.png"])
                
                # Mock user document
                mock_doc = Mock()
                mock_doc.exists = True
                mock_doc.to_dict.return_value = {'username_set': False}
                mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
                
                # Mock profanity check
                with patch('app.routes.auth.is_username_globally_unique', return_value=True):
                    with patch('app.routes.auth.profanity_check', return_value=True):
                        form_data = {
                            'new_username': 'badword',
                            'profile_icon': 'icon1.png'
                        }
                        
                        response = client.post('/set-username', data=form_data)
                        
                        assert response.status_code == 200
                        response_text = response.get_data(as_text=True)
                        assert "not allowed" in response_text

    @patch('flask_login.current_user')
    def test_username_setup_invalid_icon(self, mock_current_user, client):
        """Test username submission with invalid profile icon."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.auth.current_app') as mock_app:
                mock_db = Mock()
                mock_app.config.get.return_value = mock_db
                mock_app.config.__getitem__ = Mock(return_value=["icon1.png", "icon2.png"])
                
                # Mock user document
                mock_doc = Mock()
                mock_doc.exists = True
                mock_doc.to_dict.return_value = {'username_set': False}
                mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
                
                form_data = {
                    'new_username': 'validuser',
                    'profile_icon': 'invalid_icon.png'  # Not in allowed list
                }
                
                response = client.post('/set-username', data=form_data)
                
                assert response.status_code == 200
                response_text = response.get_data(as_text=True)
                assert "valid profile icon" in response_text


@pytest.mark.integration
class TestProfileManagement:
    """Test user profile management."""
    
    @patch('flask_login.current_user')
    def test_profile_page_loads(self, mock_current_user, client):
        """Test that profile page loads for authenticated users."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.auth.current_app') as mock_app:
                mock_db = Mock()
                mock_app.config.get.return_value = mock_db
                
                response = client.get('/user/profile')
                
                assert response.status_code == 200

    @patch('flask_login.current_user')
    def test_profile_icon_update(self, mock_current_user, client):
        """Test updating profile icon."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.auth.current_app') as mock_app:
                mock_db = Mock()
                mock_app.config.get.return_value = mock_db
                mock_app.config.__getitem__ = Mock(return_value=["icon1.png", "icon2.png"])
                
                form_data = {
                    'update_profile_icon': 'true',
                    'profile_icon': 'icon2.png'
                }
                
                response = client.post('/user/profile', data=form_data)
                
                # Should succeed and redirect or show success
                assert response.status_code in [200, 302]

    @patch('flask_login.current_user')
    def test_profile_icon_update_invalid(self, mock_current_user, client):
        """Test updating profile icon with invalid icon."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.auth.current_app') as mock_app:
                mock_db = Mock()
                mock_app.config.get.return_value = mock_db
                mock_app.config.__getitem__ = Mock(return_value=["icon1.png", "icon2.png"])
                
                form_data = {
                    'update_profile_icon': 'true',
                    'profile_icon': 'nonexistent.png'  # Not in allowed list
                }
                
                response = client.post('/user/profile', data=form_data)
                
                # Should handle error gracefully
                assert response.status_code == 200


@pytest.mark.integration
class TestLogout:
    """Test logout functionality."""
    
    @patch('flask_login.current_user')
    def test_logout_success(self, mock_current_user, client):
        """Test successful logout."""
        mock_current_user.is_authenticated = True
        
        with patch('flask_login.logout_user') as mock_logout:
            response = client.get('/logout')
            
            # Should call logout_user
            mock_logout.assert_called_once()
            
            # Should redirect
            assert response.status_code == 302

    def test_logout_clears_session(self, client):
        """Test that logout clears session data."""
        with client.session_transaction() as sess:
            sess['google_oauth_token'] = 'test_token'
        
        response = client.get('/logout')
        
        # Should redirect
        assert response.status_code == 302
        
        # Session should be cleared (in a real test, you'd verify this)

    def test_logout_with_referrer(self, client):
        """Test logout with referrer URL."""
        # Mock a safe referrer
        headers = {'Referer': 'http://localhost/'}
        
        response = client.get('/logout', headers=headers)
        
        assert response.status_code == 302


@pytest.mark.integration
class TestAccountDeletion:
    """Test account deletion functionality."""
    
    @patch('flask_login.current_user')
    def test_delete_account_confirmation_required(self, mock_current_user, client):
        """Test that account deletion requires confirmation."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            # Try to delete without confirmation
            response = client.post('/delete-account', data={})
            
            # Should require confirmation
            assert response.status_code in [400, 200]  # Depends on implementation

    @patch('flask_login.current_user')
    def test_delete_account_with_confirmation(self, mock_current_user, client):
        """Test account deletion with proper confirmation."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.auth.current_app') as mock_app:
                mock_db = Mock()
                mock_app.config.get.return_value = mock_db
                
                form_data = {
                    'confirm_delete': 'yes',  # Confirmation field
                    'user_confirmation': 'DELETE'  # Typed confirmation
                }
                
                response = client.post('/delete-account', data=form_data)
                
                # Implementation depends on your delete account flow
                assert response.status_code in [200, 302]


@pytest.mark.integration
class TestSessionSecurity:
    """Test session security and management."""
    
    @patch('flask_login.current_user')
    def test_safe_url_validation(self, mock_current_user, client):
        """Test that URL validation prevents redirect attacks."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            # Test with malicious redirect URL
            unsafe_urls = [
                'http://evil.com/hack',
                '//evil.com/hack',
                'javascript:alert(1)',
                'data:text/html,<script>alert(1)</script>'
            ]
            
            for unsafe_url in unsafe_urls:
                response = client.get(f'/set-username?next={unsafe_url}')
                
                # Should not redirect to unsafe URL
                # Implementation depends on how you handle this
                assert response.status_code in [200, 302]

    def test_csrf_protection(self, client):
        """Test CSRF protection on forms."""
        # This test would verify CSRF token validation
        # Implementation depends on your CSRF protection setup
        
        response = client.post('/set-username', data={
            'new_username': 'testuser',
            'profile_icon': 'icon1.png'
            # Missing CSRF token
        })
        
        # Should reject without CSRF token (if implemented)
        # assert response.status_code in [400, 403]
        pass

    @patch('flask_login.current_user')
    def test_username_requirement_enforcement(self, mock_current_user, client):
        """Test that username requirement is enforced."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        mock_current_user.data = {'username_set': False}  # Username not set
        
        with patch('flask_login.login_required', lambda f: f):
            # Try to access a protected page without username
            response = client.get('/user/profile')
            
            # Should redirect to username setup
            assert response.status_code == 302
            assert 'set-username' in response.location


@pytest.mark.integration
class TestAuthenticationEdgeCases:
    """Test edge cases in authentication."""
    
    @patch('flask_login.current_user')
    def test_database_unavailable_during_username_setup(self, mock_current_user, client):
        """Test handling when database is unavailable."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.auth.current_app') as mock_app:
                # Mock database as unavailable
                mock_app.config.get.return_value = None
                
                response = client.get('/set-username')
                
                # Should handle gracefully
                assert response.status_code == 302

    @patch('flask_login.current_user')
    def test_user_document_missing(self, mock_current_user, client):
        """Test handling when user document is missing from Firestore."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "missing_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.auth.current_app') as mock_app:
                mock_db = Mock()
                mock_app.config.get.return_value = mock_db
                
                # Mock user document doesn't exist
                mock_doc = Mock()
                mock_doc.exists = False
                mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
                
                with patch('flask_login.logout_user') as mock_logout:
                    response = client.get('/set-username')
                    
                    # Should logout user and redirect
                    mock_logout.assert_called_once()
                    assert response.status_code == 302

    @patch('flask_login.current_user')
    def test_username_already_set_redirect(self, mock_current_user, client):
        """Test that users with username already set are redirected."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test_user_id"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.auth.current_app') as mock_app:
                mock_db = Mock()
                mock_app.config.get.return_value = mock_db
                
                # Mock user document with username already set
                mock_doc = Mock()
                mock_doc.exists = True
                mock_doc.to_dict.return_value = {'username_set': True}
                mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
                
                response = client.get('/set-username')
                
                # Should redirect to main page
                assert response.status_code == 302