"""
Unit tests for alerts functionality.
"""

import pytest
from unittest.mock import patch, MagicMock, call
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

from app.alerts import (
    send_critical_alert,
    alert_database_failure,
    alert_authentication_failure,
    alert_server_error,
    alert_site_down
)


@pytest.mark.unit
class TestAlerts:
    """Test alerts functionality."""
    
    @patch.dict(os.environ, {'FLASK_ENV': 'development'})
    def test_send_critical_alert_non_production(self):
        """Test that alerts are not sent in non-production environments."""
        with patch('app.alerts.smtplib.SMTP') as mock_smtp:
            send_critical_alert("Test error", "TEST")
            mock_smtp.assert_not_called()
    
    @patch.dict(os.environ, {
        'FLASK_ENV': 'production',
        'ALERT_EMAIL_USER': '',
        'ALERT_EMAIL_PASS': '',
        'ALERT_EMAIL_TO': ''
    })
    def test_send_critical_alert_missing_config(self, app):
        """Test handling of missing email configuration."""
        with app.app_context():
            mock_logger = MagicMock()
            app.logger = mock_logger
            
            with patch('app.alerts.smtplib.SMTP') as mock_smtp:
                send_critical_alert("Test error", "TEST")
                mock_smtp.assert_not_called()
                mock_logger.error.assert_called_with("Alert email configuration missing")
    
    @patch.dict(os.environ, {
        'FLASK_ENV': 'production',
        'ALERT_EMAIL_USER': 'test@gmail.com',
        'ALERT_EMAIL_PASS': 'password123',
        'ALERT_EMAIL_TO': 'alert@example.com'
    })
    @patch('app.alerts.smtplib.SMTP')
    def test_send_critical_alert_success(self, mock_smtp, app):
        """Test successful alert sending with request context."""
        with app.app_context():
            with app.test_request_context('/test', method='GET', 
                                        environ_base={'REMOTE_ADDR': '192.168.1.1'},
                                        headers={'User-Agent': 'TestAgent/1.0'}):
                mock_logger = MagicMock()
                app.logger = mock_logger
                
                # Mock SMTP server
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server
                
                send_critical_alert("Database connection failed", "DB_ERROR", "Additional context")
                
                # Verify SMTP operations
                mock_smtp.assert_called_with('smtp.gmail.com', 587)
                mock_server.starttls.assert_called_once()
                mock_server.login.assert_called_with('test@gmail.com', 'password123')
                mock_server.send_message.assert_called_once()
                
                # Verify success logging
                mock_logger.info.assert_called_with("Critical alert sent for: DB_ERROR")
    
    @patch.dict(os.environ, {
        'FLASK_ENV': 'production',
        'ALERT_EMAIL_USER': 'test@gmail.com',
        'ALERT_EMAIL_PASS': 'password123',
        'ALERT_EMAIL_TO': 'alert@example.com',
        'ALERT_SMS_TO': 'sms@carrier.com'
    })
    @patch('app.alerts.smtplib.SMTP')
    def test_send_critical_alert_with_sms(self, mock_smtp, app):
        """Test alert sending with SMS enabled."""
        with app.app_context():
            with app.test_request_context('/api/test', method='POST',
                                        environ_base={'REMOTE_ADDR': '10.0.0.1'},
                                        headers={'User-Agent': 'TestBot/2.0'}):
                mock_logger = MagicMock()
                app.logger = mock_logger
                
                # Mock SMTP server
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server
                
                send_critical_alert("API failure", "API_ERROR")
                
                # Should be called twice - once for email, once for SMS
                assert mock_smtp.call_count == 2
                assert mock_server.send_message.call_count == 2
                mock_logger.info.assert_called_with("Critical alert sent for: API_ERROR")
    
    @patch.dict(os.environ, {
        'FLASK_ENV': 'production',
        'ALERT_EMAIL_USER': 'test@gmail.com',
        'ALERT_EMAIL_PASS': 'password123',
        'ALERT_EMAIL_TO': 'alert@example.com'
    })
    @patch('app.alerts.smtplib.SMTP')
    def test_send_critical_alert_no_request_context(self, mock_smtp, app):
        """Test alert sending without request context."""
        with app.app_context():
            mock_logger = MagicMock()
            app.logger = mock_logger
            
            # Mock SMTP server
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            send_critical_alert("Background job failed", "BACKGROUND_ERROR")
            
            # Should still work without request context
            mock_server.send_message.assert_called_once()
            mock_logger.info.assert_called_with("Critical alert sent for: BACKGROUND_ERROR")
    
    @patch.dict(os.environ, {
        'FLASK_ENV': 'production',
        'ALERT_EMAIL_USER': 'test@gmail.com',
        'ALERT_EMAIL_PASS': 'password123',
        'ALERT_EMAIL_TO': 'alert@example.com'
    })
    @patch('app.alerts.smtplib.SMTP')
    def test_send_critical_alert_smtp_failure(self, mock_smtp, app):
        """Test handling of SMTP failures."""
        with app.app_context():
            mock_logger = MagicMock()
            app.logger = mock_logger
            
            # Mock SMTP failure
            mock_smtp.side_effect = smtplib.SMTPException("SMTP connection failed")
            
            send_critical_alert("Test error", "TEST")
            
            # Should log the failure without breaking
            mock_logger.error.assert_called_with("Failed to send critical alert: SMTP connection failed")
    
    @patch('app.alerts.send_critical_alert')
    def test_alert_database_failure(self, mock_send_alert):
        """Test database failure alert wrapper."""
        error = Exception("Connection timeout")
        
        alert_database_failure(error)
        
        mock_send_alert.assert_called_once_with(
            error_message="Connection timeout",
            error_type="DATABASE FAILURE",
            extra_info="Database is unreachable or queries are failing"
        )
    
    @patch('app.alerts.send_critical_alert')
    def test_alert_authentication_failure(self, mock_send_alert):
        """Test authentication failure alert wrapper."""
        error = Exception("OAuth provider unavailable")
        
        alert_authentication_failure(error)
        
        mock_send_alert.assert_called_once_with(
            error_message="OAuth provider unavailable",
            error_type="AUTH SYSTEM FAILURE",
            extra_info="Users cannot log in - authentication is broken"
        )
    
    @patch('app.alerts.send_critical_alert')
    def test_alert_server_error(self, mock_send_alert):
        """Test server error alert wrapper."""
        error = Exception("Internal server error")
        
        alert_server_error(error)
        
        mock_send_alert.assert_called_once_with(
            error_message="Internal server error",
            error_type="SERVER ERROR (500)",
            extra_info="Application is returning 500 errors to users"
        )
    
    @patch('app.alerts.send_critical_alert')
    def test_alert_site_down(self, mock_send_alert):
        """Test site down alert wrapper."""
        alert_site_down()
        
        mock_send_alert.assert_called_once_with(
            error_message="Site health check failed",
            error_type="SITE DOWN",
            extra_info="The entire website appears to be unreachable"
        )
    
    @patch.dict(os.environ, {
        'FLASK_ENV': 'production',
        'ALERT_EMAIL_USER': 'test@gmail.com',
        'ALERT_EMAIL_PASS': 'password123',
        'ALERT_EMAIL_TO': 'alert@example.com'
    })
    @patch('app.alerts.datetime')
    @patch('app.alerts.smtplib.SMTP')
    def test_alert_message_content(self, mock_smtp, mock_datetime, app):
        """Test that alert message contains expected content."""
        with app.app_context():
            with app.test_request_context('/api/critical', method='POST',
                                        environ_base={'REMOTE_ADDR': '203.0.113.1'},
                                        headers={'User-Agent': 'Mozilla/5.0 (Test Browser)'}):
                mock_logger = MagicMock()
                app.logger = mock_logger
                
                # Mock datetime
                mock_datetime.utcnow.return_value.strftime.return_value = "2024-01-01 12:00:00 UTC"
                
                # Mock SMTP server and capture the message
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server
                
                send_critical_alert("Database connection lost", "DB_CONNECTION", "Pool exhausted")
                
                # Verify message was sent
                mock_server.send_message.assert_called_once()
                sent_message = mock_server.send_message.call_args[0][0]
                
                # Verify message was sent (basic check)
                message_body = str(sent_message)
                assert "DB_CONNECTION" in message_body  # Should be in subject line
                assert "test@gmail.com" in message_body  # Should be in from field
    
    @patch.dict(os.environ, {
        'FLASK_ENV': 'production',
        'ALERT_EMAIL_USER': 'test@gmail.com',
        'ALERT_EMAIL_PASS': 'password123',
        'ALERT_EMAIL_TO': 'alert@example.com'
    })
    @patch('app.alerts.smtplib.SMTP')
    def test_request_context_exception_handling(self, mock_smtp, app):
        """Test handling of request context exceptions."""
        with app.app_context():
            mock_logger = MagicMock()
            app.logger = mock_logger
            
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            # Test outside request context to trigger exception handling
            send_critical_alert("Test error", "TEST")
            
            # Should still send alert
            mock_server.send_message.assert_called_once()
            sent_message = mock_server.send_message.call_args[0][0]
            message_body = str(sent_message)
            assert "TEST" in message_body  # Should be in subject line