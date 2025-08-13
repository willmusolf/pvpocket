"""
Email service module for sending support ticket replies.
"""

from flask import current_app
from flask_mail import Message
import logging
from typing import Optional, Dict, Any
from datetime import datetime


class EmailService:
    """Service class for handling email operations."""
    
    def __init__(self, mail_instance=None):
        """Initialize the email service with a Mail instance."""
        self.mail = mail_instance
    
    def send_support_reply(self, 
                          to_email: str, 
                          ticket_data: Dict[str, Any], 
                          admin_reply: str,
                          admin_email: str) -> bool:
        """
        Send a support ticket reply email.
        
        Args:
            to_email: Email address to send the reply to
            ticket_data: Original ticket data dictionary
            admin_reply: The admin's reply message
            admin_email: Email of the admin who replied
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            if not self.mail:
                current_app.logger.error("Email service not initialized - Mail instance is None")
                return False
            
            # Validate email configuration
            mail_username = current_app.config.get('MAIL_USERNAME')
            mail_password = current_app.config.get('MAIL_PASSWORD')
            
            if not mail_username:
                current_app.logger.error("Email service not configured - MAIL_USERNAME is missing")
                return False
                
            if not mail_password:
                current_app.logger.error("Email service not configured - MAIL_PASSWORD is missing")
                return False
                
            # Create email subject
            subject = f"Re: {ticket_data.get('subject', 'Support Request')}"
            
            # Create email body
            body = self._create_reply_email_body(ticket_data, admin_reply, admin_email)
            
            # Create message
            msg = Message(
                subject=subject,
                recipients=[to_email],
                body=body,
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', mail_username)
            )
            
            # Send the email
            self.mail.send(msg)
            
            current_app.logger.info(f"Support reply email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to send support reply email to {to_email}: {str(e)}")
            current_app.logger.error(f"Exception type: {type(e).__name__}")
            
            # Log specific Gmail errors for debugging
            error_str = str(e).lower()
            if 'authentication' in error_str or 'username' in error_str or 'password' in error_str:
                current_app.logger.error("Gmail authentication failed - check App Password")
                current_app.logger.error(f"Current username: {current_app.config.get('MAIL_USERNAME')}")
                current_app.logger.error(f"Password format (should be 16 chars): {len(current_app.config.get('MAIL_PASSWORD', ''))}")
            elif 'connection' in error_str or 'timeout' in error_str:
                current_app.logger.error("SMTP connection failed - check network/firewall")
            elif 'tls' in error_str or 'ssl' in error_str:
                current_app.logger.error("TLS/SSL error - check Gmail security settings")
            
            import traceback
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    def _create_reply_email_body(self, 
                                ticket_data: Dict[str, Any], 
                                admin_reply: str,
                                admin_email: str) -> str:
        """
        Create the email body for a support reply.
        
        Args:
            ticket_data: Original ticket data
            admin_reply: Admin's reply message
            admin_email: Admin's email address
            
        Returns:
            str: Formatted email body
        """
        # Get the date, with multiple fallbacks
        date_str = ticket_data.get('formatted_date', 'Unknown')
        
        # If formatted_date is missing or Unknown, try to format timestamp directly
        if date_str == 'Unknown' or not date_str:
            timestamp = ticket_data.get('timestamp')
            if timestamp:
                try:
                    # Handle datetime object
                    if hasattr(timestamp, 'strftime'):
                        date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
                    # Handle string representation
                    elif isinstance(timestamp, str):
                        date_str = timestamp
                    else:
                        # Convert to string as last resort
                        date_str = str(timestamp)
                except Exception as e:
                    current_app.logger.warning(f"Could not format timestamp in email: {e}")
                    date_str = "Date not available"
        
        body = f"""Dear {ticket_data.get('name', 'User')},

Thank you for contacting PvPocket support. We've reviewed your inquiry and here's our response:

{admin_reply}

If you need further assistance, please feel free to reply to this email or submit a new support request through our website.

---
Original Support Request:
Subject: {ticket_data.get('subject', 'No subject')}
Date: {date_str}
Your Message: {ticket_data.get('message', 'No message')}

Best regards,
PvPocket Support Team
Replied by: {admin_email}

This is an automated response from PvPocket (https://pvpocket.xyz)
"""
        return body
    
    def test_email_configuration(self) -> Dict[str, Any]:
        """
        Test the email configuration without sending an actual email.
        
        Returns:
            dict: Status and configuration details
        """
        try:
            config_status = {
                'configured': True,
                'mail_server': current_app.config.get('MAIL_SERVER'),
                'mail_port': current_app.config.get('MAIL_PORT'),
                'mail_username': current_app.config.get('MAIL_USERNAME'),
                'mail_use_tls': current_app.config.get('MAIL_USE_TLS'),
                'mail_default_sender': current_app.config.get('MAIL_DEFAULT_SENDER'),
                'errors': []
            }
            
            # Check required configuration
            if not current_app.config.get('MAIL_USERNAME'):
                config_status['errors'].append('MAIL_USERNAME not configured')
                config_status['configured'] = False
                
            if not current_app.config.get('MAIL_PASSWORD'):
                config_status['errors'].append('MAIL_PASSWORD not configured')
                config_status['configured'] = False
                
            if not self.mail:
                config_status['errors'].append('Mail instance not initialized')
                config_status['configured'] = False
            
            return config_status
            
        except Exception as e:
            current_app.logger.error(f"Error testing email configuration: {str(e)}")
            return {
                'configured': False,
                'error': str(e)
            }


# Global email service instance - will be initialized in app factory
email_service: Optional[EmailService] = None


def init_email_service(app, mail_instance):
    """
    Initialize the email service with Flask app and Mail instance.
    
    Args:
        app: Flask application instance
        mail_instance: Flask-Mail instance
    """
    global email_service
    email_service = EmailService(mail_instance)
    
    with app.app_context():
        # Log email configuration status
        config_test = email_service.test_email_configuration()
        if config_test.get('configured'):
            app.logger.info("Email service initialized successfully")
        else:
            app.logger.warning(f"Email service configuration issues: {config_test.get('errors', [])}")


def get_email_service() -> Optional[EmailService]:
    """
    Get the global email service instance.
    
    Returns:
        EmailService instance or None if not initialized
    """
    return email_service