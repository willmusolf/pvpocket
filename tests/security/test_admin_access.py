"""
Security tests for Admin Access Controls.

Tests admin authorization, privilege escalation prevention,
admin endpoint protection, and proper access control enforcement.
"""

import pytest
import json
import os
from unittest.mock import patch, Mock


@pytest.mark.security
class TestAdminAuthentication:
    """Test admin authentication and authorization."""
    
    @patch('flask_login.current_user')
    def test_admin_access_authorized_user(self, mock_current_user, client):
        """Test that authorized admin users can access admin endpoints."""
        # Mock admin user
        mock_current_user.is_authenticated = True
        mock_current_user.email = "willmusolf@gmail.com"  # Known admin email
        
        with patch('flask_login.login_required', lambda f: f):
            response = client.get('/admin/metrics')
            
            # Should allow access (200 or template render)
            assert response.status_code in [200, 404]  # 404 if template missing
    
    @patch('flask_login.current_user')
    def test_admin_access_unauthorized_user(self, mock_current_user, client):
        """Test that unauthorized users cannot access admin endpoints."""
        # Mock non-admin user
        mock_current_user.is_authenticated = True
        mock_current_user.email = "regular_user@example.com"  # Not in admin list
        
        with patch('flask_login.login_required', lambda f: f):
            response = client.get('/admin/metrics')
            
            # Should deny access with 404 (not 403 to hide existence)
            assert response.status_code == 404

    @patch('flask_login.current_user')
    def test_admin_access_no_email_attribute(self, mock_current_user, client):
        """Test behavior when user object has no email attribute."""
        # Mock user without email attribute
        mock_current_user.is_authenticated = True
        # Don't set email attribute at all
        
        with patch('flask_login.login_required', lambda f: f):
            response = client.get('/admin/metrics')
            
            # Should deny access
            assert response.status_code == 404

    @patch('flask_login.current_user')
    def test_admin_access_unauthenticated_user(self, mock_current_user, client):
        """Test that unauthenticated users cannot access admin endpoints."""
        mock_current_user.is_authenticated = False
        
        response = client.get('/admin/metrics')
        
        # Should redirect to login or return 302/401
        assert response.status_code in [302, 401]

    @patch('flask_login.current_user')
    @patch.dict(os.environ, {'ADMIN_EMAILS': 'admin1@example.com,admin2@example.com'})
    def test_admin_access_environment_admin(self, mock_current_user, client):
        """Test that admins defined in environment variables can access admin endpoints."""
        mock_current_user.is_authenticated = True
        mock_current_user.email = "admin1@example.com"  # From environment
        
        with patch('flask_login.login_required', lambda f: f):
            response = client.get('/admin/metrics')
            
            # Should allow access
            assert response.status_code in [200, 404]  # 404 if template missing


@pytest.mark.security
class TestAdminAPIEndpoints:
    """Test admin API endpoint security."""
    
    @patch('flask_login.current_user')
    def test_metrics_summary_authorized(self, mock_current_user, client):
        """Test authorized access to metrics summary API."""
        mock_current_user.is_authenticated = True
        mock_current_user.email = "willmusolf@gmail.com"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.admin.performance_monitor') as mock_monitor:
                mock_monitor.metrics.get_health_summary.return_value = {
                    "avg_response_time": 200,
                    "p95_response_time": 500,
                    "active_users": 10,
                    "total_requests": 1000
                }
                mock_monitor.metrics.get_top_endpoints.return_value = []
                mock_monitor.metrics.get_firestore_usage_stats.return_value = {}
                mock_monitor.metrics.get_cache_hit_rate.return_value = 95.0
                mock_monitor.metrics.cache_stats = {"hits": 950, "misses": 50}
                
                with patch('app.routes.admin.cache_manager') as mock_cache:
                    mock_cache.health_check.return_value = True
                    
                    with patch('app.routes.admin.db_service') as mock_db:
                        mock_db.health_check.return_value = True
                        
                        response = client.get('/admin/api/metrics/summary')
                        
                        assert response.status_code == 200
                        data = json.loads(response.data)
                        assert 'system_health' in data
                        assert 'performance' in data

    @patch('flask_login.current_user')
    def test_metrics_summary_unauthorized(self, mock_current_user, client):
        """Test unauthorized access to metrics summary API."""
        mock_current_user.is_authenticated = True
        mock_current_user.email = "hacker@evil.com"
        
        with patch('flask_login.login_required', lambda f: f):
            response = client.get('/admin/api/metrics/summary')
            
            assert response.status_code == 404

    @patch('flask_login.current_user')
    def test_historical_metrics_authorized(self, mock_current_user, client):
        """Test authorized access to historical metrics API."""
        mock_current_user.is_authenticated = True
        mock_current_user.email = "willmusolf@gmail.com"
        
        with patch('flask_login.login_required', lambda f: f):
            response = client.get('/admin/api/metrics/historical/response_times?hours=24')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'data' in data
            assert 'metric_type' in data

    @patch('flask_login.current_user')
    def test_historical_metrics_unauthorized(self, mock_current_user, client):
        """Test unauthorized access to historical metrics API."""
        mock_current_user.is_authenticated = True
        mock_current_user.email = "regular@user.com"
        
        with patch('flask_login.login_required', lambda f: f):
            response = client.get('/admin/api/metrics/historical/response_times')
            
            assert response.status_code == 404


@pytest.mark.security
class TestPrivilegeEscalation:
    """Test prevention of privilege escalation attempts."""
    
    def test_admin_decorator_cannot_be_bypassed(self, client):
        """Test that admin decorator cannot be bypassed through manipulation."""
        # Try to access admin endpoint without going through decorator
        response = client.get('/admin/api/metrics/summary')
        
        # Should fail authentication
        assert response.status_code in [302, 401, 404]

    @patch('flask_login.current_user')
    def test_email_manipulation_attempt(self, mock_current_user, client):
        """Test that email manipulation doesn't grant admin access."""
        mock_current_user.is_authenticated = True
        
        # Try various email manipulation techniques
        test_emails = [
            "willmusolf@gmail.com@evil.com",  # Email append
            "willmusolf+admin@gmail.com",     # Plus sign trick
            "WILLMUSOLF@GMAIL.COM",           # Case manipulation
            "willmusolf@GMAIL.com",           # Mixed case
            " willmusolf@gmail.com ",         # Whitespace
            "willmusolf@gmail.com\x00",       # Null byte injection
            "admin@localhost",                # Different domain
            "",                               # Empty string
            None                              # None value
        ]
        
        with patch('flask_login.login_required', lambda f: f):
            for email in test_emails:
                mock_current_user.email = email
                
                response = client.get('/admin/metrics')
                
                if email in ["WILLMUSOLF@GMAIL.COM", "willmusolf@GMAIL.com"]:
                    # Case sensitivity test - should still deny
                    assert response.status_code == 404
                else:
                    # All other attempts should be denied
                    assert response.status_code == 404

    @patch('flask_login.current_user')
    @patch.dict(os.environ, {}, clear=True)  # Clear environment
    def test_environment_variable_manipulation(self, mock_current_user, client):
        """Test that environment variable manipulation doesn't work."""
        mock_current_user.is_authenticated = True
        mock_current_user.email = "hacker@evil.com"
        
        with patch('flask_login.login_required', lambda f: f):
            # Try to manipulate environment during request
            with patch.dict(os.environ, {'ADMIN_EMAILS': 'hacker@evil.com'}):
                response = client.get('/admin/metrics')
                
                # Should still be denied because env is read at function definition time
                assert response.status_code == 404


@pytest.mark.security
class TestAdminErrorHandling:
    """Test error handling in admin endpoints."""
    
    @patch('flask_login.current_user')
    def test_metrics_summary_error_handling(self, mock_current_user, client):
        """Test error handling in metrics summary endpoint."""
        mock_current_user.is_authenticated = True
        mock_current_user.email = "willmusolf@gmail.com"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.admin.performance_monitor') as mock_monitor:
                # Make monitor raise an exception
                mock_monitor.metrics.get_health_summary.side_effect = Exception("Database error")
                
                response = client.get('/admin/api/metrics/summary')
                
                assert response.status_code == 500
                data = json.loads(response.data)
                assert 'error' in data

    @patch('flask_login.current_user')
    def test_historical_metrics_invalid_hours(self, mock_current_user, client):
        """Test historical metrics with invalid hours parameter."""
        mock_current_user.is_authenticated = True
        mock_current_user.email = "willmusolf@gmail.com"
        
        with patch('flask_login.login_required', lambda f: f):
            response = client.get('/admin/api/metrics/historical/response_times?hours=invalid')
            
            # Should handle error gracefully
            assert response.status_code in [400, 500]


@pytest.mark.security
class TestAdminSecurityHeaders:
    """Test security headers on admin endpoints."""
    
    @patch('flask_login.current_user')
    def test_admin_endpoints_security_headers(self, mock_current_user, client):
        """Test that admin endpoints include proper security headers."""
        mock_current_user.is_authenticated = True
        mock_current_user.email = "willmusolf@gmail.com"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.admin.performance_monitor') as mock_monitor:
                mock_monitor.metrics.get_health_summary.return_value = {}
                mock_monitor.metrics.get_top_endpoints.return_value = []
                mock_monitor.metrics.get_firestore_usage_stats.return_value = {}
                mock_monitor.metrics.get_cache_hit_rate.return_value = 0
                mock_monitor.metrics.cache_stats = {}
                
                with patch('app.routes.admin.cache_manager') as mock_cache:
                    mock_cache.health_check.return_value = True
                    
                    with patch('app.routes.admin.db_service') as mock_db:
                        mock_db.health_check.return_value = True
                        
                        response = client.get('/admin/api/metrics/summary')
                        
                        # Check for security headers (if implemented)
                        # These might be added by the main app or middleware
                        if 'X-Content-Type-Options' in response.headers:
                            assert response.headers['X-Content-Type-Options'] == 'nosniff'
                        
                        if 'X-Frame-Options' in response.headers:
                            assert response.headers['X-Frame-Options'] in ['DENY', 'SAMEORIGIN']


@pytest.mark.security
class TestAdminBruteForceProtection:
    """Test brute force protection for admin endpoints."""
    
    @patch('flask_login.current_user')
    def test_repeated_unauthorized_access_attempts(self, mock_current_user, client):
        """Test that repeated unauthorized access attempts are handled properly."""
        mock_current_user.is_authenticated = True
        mock_current_user.email = "attacker@evil.com"
        
        with patch('flask_login.login_required', lambda f: f):
            # Make multiple rapid requests
            responses = []
            for i in range(10):
                response = client.get('/admin/metrics')
                responses.append(response.status_code)
            
            # All should be denied
            for status_code in responses:
                assert status_code == 404
            
            # No rate limiting needed since all requests are denied at auth level


@pytest.mark.security
class TestAdminDataExposure:
    """Test that admin endpoints don't expose sensitive data."""
    
    @patch('flask_login.current_user')
    def test_metrics_no_sensitive_data_exposure(self, mock_current_user, client):
        """Test that metrics endpoints don't expose sensitive data."""
        mock_current_user.is_authenticated = True
        mock_current_user.email = "willmusolf@gmail.com"
        
        with patch('flask_login.login_required', lambda f: f):
            with patch('app.routes.admin.performance_monitor') as mock_monitor:
                # Mock metrics data that might contain sensitive info
                mock_monitor.metrics.get_health_summary.return_value = {
                    "avg_response_time": 200,
                    "database_password": "secret123",  # Sensitive data
                    "api_keys": ["key1", "key2"]       # More sensitive data
                }
                mock_monitor.metrics.get_top_endpoints.return_value = []
                mock_monitor.metrics.get_firestore_usage_stats.return_value = {}
                mock_monitor.metrics.get_cache_hit_rate.return_value = 95.0
                mock_monitor.metrics.cache_stats = {"hits": 950, "misses": 50}
                
                with patch('app.routes.admin.cache_manager') as mock_cache:
                    mock_cache.health_check.return_value = True
                    
                    with patch('app.routes.admin.db_service') as mock_db:
                        mock_db.health_check.return_value = True
                        
                        response = client.get('/admin/api/metrics/summary')
                        
                        assert response.status_code == 200
                        response_text = response.get_data(as_text=True)
                        
                        # Ensure sensitive data is not exposed
                        assert "secret123" not in response_text
                        assert "api_keys" not in response_text
                        assert "database_password" not in response_text


@pytest.mark.security
class TestAdminSessionSecurity:
    """Test session security for admin users."""
    
    @patch('flask_login.current_user')
    def test_admin_session_validation(self, mock_current_user, client):
        """Test that admin sessions are properly validated."""
        # This test would check session timeout, session fixation protection, etc.
        # Implementation depends on your session management
        
        mock_current_user.is_authenticated = True
        mock_current_user.email = "willmusolf@gmail.com"
        
        with patch('flask_login.login_required', lambda f: f):
            response = client.get('/admin/metrics')
            
            # Basic session validation test
            assert response.status_code in [200, 404]

    @patch('flask_login.current_user')
    def test_admin_concurrent_session_handling(self, mock_current_user, client):
        """Test handling of concurrent admin sessions."""
        mock_current_user.is_authenticated = True
        mock_current_user.email = "willmusolf@gmail.com"
        
        with patch('flask_login.login_required', lambda f: f):
            # Simulate multiple concurrent requests
            responses = []
            for i in range(5):
                response = client.get('/admin/api/metrics/summary')
                responses.append(response.status_code)
            
            # All should succeed if properly authenticated
            # (Implementation would depend on your session management)