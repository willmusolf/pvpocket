"""
Simple production alert system for critical errors.
Sends email/SMS when things truly break.
"""

import smtplib
from email.mime.text import MIMEText
import os
from datetime import datetime
from flask import current_app, request
import traceback

def send_critical_alert(error_message, error_type="CRITICAL ERROR", extra_info=""):
    """
    Send immediate alert for critical production errors.
    Only sends in production environment.
    """
    # Only alert in production
    if os.environ.get('FLASK_ENV') != 'production':
        return
        
    try:
        # Email configuration (from environment variables)
        EMAIL_USER = os.environ.get('ALERT_EMAIL_USER')  # your-gmail@gmail.com
        EMAIL_PASS = os.environ.get('ALERT_EMAIL_PASS')  # Gmail app password
        ALERT_EMAIL = os.environ.get('ALERT_EMAIL_TO')   # your-email@gmail.com
        ALERT_SMS = os.environ.get('ALERT_SMS_TO')       # your-phone@carrier.com (for SMS)
        
        if not all([EMAIL_USER, EMAIL_PASS, ALERT_EMAIL]):
            current_app.logger.error("Alert email configuration missing")
            return
            
        # Get request context if available
        try:
            request_info = f"{request.method} {request.path} from {request.remote_addr}"
            user_agent = request.headers.get('User-Agent', 'Unknown')[:100]
        except:
            request_info = "No request context"
            user_agent = "Unknown"
            
        # Create alert message (without emojis to avoid encoding issues)
        alert_body = f"""
CRITICAL ERROR in Pokemon TCG Pocket Production

ERROR TYPE: {error_type}
TIME: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
SITE: https://pvpocket.xyz

ERROR DETAILS:
{error_message}

REQUEST INFO:
{request_info}

ADDITIONAL INFO:
{extra_info}

QUICK LINKS:
- View Logs: https://console.cloud.google.com/logs/query;query=resource.type%3D%22gae_app%22%0Aseverity%3E%3DERROR?project=pvpocket-dd286
- Site Status: https://pvpocket.xyz/health

This is an automated alert - something is seriously broken and needs immediate attention.
        """
        
        # Create email with proper UTF-8 encoding
        msg = MIMEText(alert_body, 'plain', 'utf-8')
        msg['Subject'] = f'CRITICAL: Pokemon TCG Pocket - {error_type}'
        msg['From'] = EMAIL_USER
        msg['To'] = ALERT_EMAIL
        
        # Send email alert
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
            
        # Send SMS alert if configured (shorter message)
        if ALERT_SMS:
            sms_body = f"CRITICAL ERROR: Pokemon TCG Pocket\n{error_type}\n{datetime.utcnow().strftime('%H:%M UTC')}\nCheck email for details"
            
            sms_msg = MIMEText(sms_body, 'plain', 'utf-8')
            sms_msg['Subject'] = 'POKEMON TCG ERROR'
            sms_msg['From'] = EMAIL_USER
            sms_msg['To'] = ALERT_SMS
            
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASS)
                server.send_message(sms_msg)
                
        current_app.logger.info(f"Critical alert sent for: {error_type}")
        
    except Exception as e:
        # Don't let alerting break the app, but log the failure
        current_app.logger.error(f"Failed to send critical alert: {e}")

def alert_database_failure(error):
    """Alert for database connection/query failures."""
    send_critical_alert(
        error_message=str(error),
        error_type="DATABASE FAILURE",
        extra_info="Database is unreachable or queries are failing"
    )

def alert_authentication_failure(error):
    """Alert for authentication system failures."""
    send_critical_alert(
        error_message=str(error),
        error_type="AUTH SYSTEM FAILURE", 
        extra_info="Users cannot log in - authentication is broken"
    )

def alert_server_error(error):
    """Alert for 500 server errors."""
    send_critical_alert(
        error_message=str(error),
        error_type="SERVER ERROR (500)",
        extra_info="Application is returning 500 errors to users"
    )

def alert_site_down():
    """Alert when the entire site is unreachable."""
    send_critical_alert(
        error_message="Site health check failed",
        error_type="SITE DOWN",
        extra_info="The entire website appears to be unreachable"
    )