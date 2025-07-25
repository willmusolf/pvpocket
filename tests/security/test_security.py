"""
Security tests for Pokemon TCG Pocket App.
"""

import pytest
import json
from unittest.mock import patch


@pytest.mark.security
class TestSecurityHeaders:
    """Test security headers and configurations."""
    
    def test_secure_headers_present(self, client):
        """Test that security headers are present in responses."""
        response = client.get('/')
        
        # Check for basic security headers
        headers = response.headers
        
        # Note: These should be added in the security middleware
        # Currently missing - this test will fail until implemented
        expected_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection'
        ]
        
        for header in expected_headers:
            assert header in headers, f"Missing security header: {header}"
    
    def test_cors_configuration(self, client):
        """Test CORS configuration is properly restricted."""
        # Test OPTIONS request
        response = client.options('/')
        
        if 'Access-Control-Allow-Origin' in response.headers:
            origin = response.headers['Access-Control-Allow-Origin']
            # Should not be wildcard for authenticated endpoints
            assert origin != '*' or response.status_code == 404


@pytest.mark.security
class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limiting_exists(self, client):
        """Test that rate limiting is implemented."""
        # Make multiple requests to test rate limiting using health endpoint
        responses = []
        for i in range(1050):  # Exceed the 1000/minute limit we set for testing
            response = client.get('/health')
            responses.append(response.status_code)
        
        # Should eventually get rate limited (429)
        assert 429 in responses, "Rate limiting not implemented"


@pytest.mark.security
class TestAuthenticationSecurity:
    """Test authentication security measures."""
    
    def test_unauthenticated_access_restricted(self, client):
        """Test that protected endpoints require authentication."""
        protected_endpoints = [
            '/api/my-decks',
            '/user/profile',
            '/api/refresh-cards'
        ]
        
        for endpoint in protected_endpoints:
            if endpoint == '/api/refresh-cards':
                # This endpoint expects POST, not GET
                response = client.post(endpoint)
            else:
                response = client.get(endpoint)
            # Should redirect to login or return 401/403
            assert response.status_code in [302, 401, 403], \
                f"Endpoint {endpoint} not properly protected"
    
    def test_refresh_cards_requires_auth_header(self, client):
        """Test that refresh cards endpoint requires proper authentication."""
        # Test without header
        response = client.post('/api/refresh-cards')
        assert response.status_code == 401
        
        # Test with wrong header
        response = client.post('/api/refresh-cards', 
                             headers={'X-Refresh-Key': 'wrong-key'})
        assert response.status_code == 401


@pytest.mark.security
class TestInputValidation:
    """Test input validation and sanitization."""
    
    def test_image_proxy_validates_domains(self, client):
        """Test that image proxy validates allowed domains."""
        # Test malicious URL
        response = client.get('/api/proxy-image?url=http://evil.com/malware.exe')
        assert response.status_code == 400
        
        # Test valid domain
        response = client.get('/api/proxy-image?url=https://storage.googleapis.com/test.png')
        # Should not be 400 (bad request) due to domain validation
        assert response.status_code != 400
    
    def test_xss_prevention(self, client):
        """Test XSS prevention in user inputs."""
        # Test XSS in search parameters
        xss_payload = "<script>alert('xss')</script>"
        response = client.get(f'/api/cards?search={xss_payload}')
        
        # Response should not contain unescaped script tags
        assert b'<script>' not in response.data
        assert b'alert(' not in response.data
    
    def test_sql_injection_prevention(self, client):
        """Test SQL injection prevention (applicable to NoSQL too)."""
        # Test injection in search parameters using health endpoint
        injection_payload = "'; DROP TABLE users; --"
        response = client.get(f'/health?test={injection_payload}')
        
        # Should handle gracefully, not crash
        assert response.status_code < 500


@pytest.mark.security
class TestDataExposure:
    """Test for sensitive data exposure."""
    
    def test_no_sensitive_data_in_logs(self, client, caplog):
        """Test that sensitive data is not logged."""
        # Make request that might log sensitive data
        response = client.post('/api/refresh-cards', 
                             headers={'X-Refresh-Key': 'test-secret'})
        
        # Check logs don't contain sensitive information
        log_output = caplog.text.lower()
        sensitive_terms = ['password', 'secret', 'key', 'token']
        
        for term in sensitive_terms:
            assert term not in log_output, f"Sensitive term '{term}' found in logs"
    
    def test_error_messages_not_verbose(self, client):
        """Test that error messages don't expose system details."""
        # Trigger an error
        response = client.get('/nonexistent-endpoint')
        
        # Should not expose system paths or detailed error info
        response_text = response.get_data(as_text=True).lower()
        sensitive_info = ['traceback', '/users/', 'python', 'firestore']
        
        for info in sensitive_info:
            assert info not in response_text, f"Sensitive info '{info}' exposed in error"


@pytest.mark.security
class TestFirebaseSecurity:
    """Test Firebase security configurations."""
    
    def test_firebase_rules_exist(self):
        """Test that Firebase security rules are configured."""
        # This test checks if security rules files exist
        import os
        
        rules_files = [
            'firestore.rules',
            'storage.rules'
        ]
        
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        for rules_file in rules_files:
            rules_path = os.path.join(project_root, rules_file)
            assert os.path.exists(rules_path), f"Missing Firebase rules: {rules_file}"
    
    @patch('firebase_admin.storage.bucket')
    def test_storage_access_controlled(self, mock_bucket, client):
        """Test that Firebase Storage access is properly controlled."""
        # Test that storage operations require proper authentication
        # This is a placeholder for actual storage security tests
        pass