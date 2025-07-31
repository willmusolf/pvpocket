"""
Unit tests for models functionality.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from app.models import User, load_user, login_manager


@pytest.mark.unit
class TestUser:
    """Test User class functionality."""
    
    def test_user_initialization_with_data(self):
        """Test User initialization with complete data."""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "google_id": "123456789",
            "username_set": True,
            "email_visible_to_friends": True,
            "profile_public": False,
            "profile_icon": "icon123",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        user = User("user123", user_data)
        
        assert user.id == "user123"
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.google_id == "123456789"
        assert user.username_set is True
        assert user.email_visible_to_friends is True
        assert user.profile_public is False
        assert user.data == user_data
    
    def test_user_initialization_without_data(self):
        """Test User initialization with no data (defaults)."""
        user = User("user456")
        
        assert user.id == "user456"
        assert user.username == ""
        assert user.email == ""
        assert user.google_id == ""
        assert user.username_set is False
        assert user.email_visible_to_friends is False
        assert user.profile_public is True
        assert user.data == {}
    
    def test_user_initialization_with_partial_data(self):
        """Test User initialization with partial data."""
        user_data = {
            "username": "partialuser",
            "email": "partial@example.com"
        }
        
        user = User("user789", user_data)
        
        assert user.id == "user789"
        assert user.username == "partialuser"
        assert user.email == "partial@example.com"
        assert user.google_id == ""  # Default
        assert user.username_set is False  # Default
        assert user.email_visible_to_friends is False  # Default
        assert user.profile_public is True  # Default
    
    def test_user_id_string_conversion(self):
        """Test that user ID is always converted to string."""
        user = User(12345)
        assert user.id == "12345"
        assert isinstance(user.id, str)
    
    def test_get_public_profile_data_basic(self):
        """Test getting public profile data without friend status."""
        user_data = {
            "username": "publicuser",
            "email": "public@example.com",
            "profile_icon": "icon456",
            "created_at": "2024-01-01T00:00:00Z",
            "email_visible_to_friends": True
        }
        
        user = User("user123", user_data)
        profile_data = user.get_public_profile_data()
        
        expected_data = {
            "username": "publicuser",
            "profile_icon": "icon456",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        assert profile_data == expected_data
        assert "email" not in profile_data  # Should not include email for non-friends
    
    def test_get_public_profile_data_friend_email_visible(self):
        """Test getting public profile data as friend with email visibility."""
        user_data = {
            "username": "frienduser",
            "email": "friend@example.com",
            "profile_icon": "icon789",
            "created_at": "2024-01-01T00:00:00Z",
            "email_visible_to_friends": True
        }
        
        user = User("user456", user_data)
        profile_data = user.get_public_profile_data(is_friend=True)
        
        expected_data = {
            "username": "frienduser",
            "profile_icon": "icon789",
            "created_at": "2024-01-01T00:00:00Z",
            "email": "friend@example.com"
        }
        
        assert profile_data == expected_data
        assert profile_data["email"] == "friend@example.com"
    
    def test_get_public_profile_data_friend_email_hidden(self):
        """Test getting public profile data as friend with email hidden."""
        user_data = {
            "username": "privateuser",
            "email": "private@example.com",
            "profile_icon": "icon101",
            "created_at": "2024-01-01T00:00:00Z",
            "email_visible_to_friends": False
        }
        
        user = User("user789", user_data)
        profile_data = user.get_public_profile_data(is_friend=True)
        
        expected_data = {
            "username": "privateuser",
            "profile_icon": "icon101",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        assert profile_data == expected_data
        assert "email" not in profile_data  # Should not include email when hidden
    
    def test_get_public_profile_data_missing_fields(self):
        """Test getting public profile data with missing optional fields."""
        user_data = {
            "username": "minimaluser"
        }
        
        user = User("user999", user_data)
        profile_data = user.get_public_profile_data()
        
        expected_data = {
            "username": "minimaluser",
            "profile_icon": "",  # Default empty string
            "created_at": None   # Missing field returns None
        }
        
        assert profile_data == expected_data


@pytest.mark.unit
class TestLoginManager:
    """Test login manager configuration."""
    
    def test_login_manager_configuration(self):
        """Test that login manager is properly configured."""
        assert login_manager.login_view == "auth.login_prompt_page"
        assert login_manager.login_message == "Please sign in with Google to access this page."
        assert login_manager.login_message_category == "info"


@pytest.mark.unit
class TestLoadUser:
    """Test load_user function."""
    
    def test_load_user_none_input(self):
        """Test load_user with None input."""
        result = load_user(None)
        assert result is None
    
    def test_load_user_empty_string(self):
        """Test load_user with empty string."""
        result = load_user("")
        assert result is None
    
    @patch('app.models.cache_manager')
    def test_load_user_from_cache_success(self, mock_cache_manager):
        """Test successful user loading from cache."""
        user_data = {
            "username": "cacheduser",
            "email": "cached@example.com",
            "google_id": "123456"
        }
        
        mock_cache_manager.get_user_data.return_value = user_data
        
        result = load_user("user123")
        
        assert result is not None
        assert isinstance(result, User)
        assert result.id == "user123"
        assert result.username == "cacheduser"
        assert result.email == "cached@example.com"
        
        mock_cache_manager.get_user_data.assert_called_once_with("user123")
    
    def test_load_user_integer_id_conversion(self):
        """Test that integer user IDs are converted to strings."""
        with patch('app.models.cache_manager') as mock_cache_manager:
            mock_cache_manager.get_user_data.return_value = {"username": "testuser"}
            
            result = load_user(12345)
            
            assert result is not None
            assert result.id == "12345"
            mock_cache_manager.get_user_data.assert_called_once_with("12345")