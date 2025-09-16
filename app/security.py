"""
Security middleware and configuration for Pokemon TCG Pocket App.
Implements rate limiting, security headers, and other security measures.
"""

from flask import request, jsonify, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
import logging
from functools import wraps
import time
import os
from typing import Dict, Any, Optional


# Configure security logging
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)


class SecurityManager:
    """Centralized security management for the application."""
    
    def __init__(self, app=None):
        self.app = app
        self.limiter = None
        self.talisman = None
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security components with Flask app."""
        self.app = app
        
        # Initialize rate limiter with different limits based on environment
        if app.config.get('TESTING'):
            # Very lenient limits for testing
            default_limits = ["10000 per day", "5000 per hour", "1000 per minute"]
        elif app.config.get('FLASK_ENV') == 'development':
            # Very lenient limits for development and load testing
            default_limits = ["10000 per day", "5000 per hour", "1000 per minute"]
        else:
            # Production limits
            default_limits = ["200 per day", "50 per hour", "10 per minute"]
            
        self.limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=default_limits,
            storage_uri="memory://",  # Use in-memory storage for simplicity
            strategy="fixed-window"
        )
        
        # Configure Content Security Policy - more permissive for development
        if app.config.get('FLASK_ENV') == 'development':
            # Development CSP - more permissive
            csp = {
                'default-src': "'self' 'unsafe-inline' 'unsafe-eval'",
                'script-src': "'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://pagead2.googlesyndication.com https://googleads.g.doubleclick.net https://tpc.googlesyndication.com https://www.google.com https://www.gstatic.com https://ep2.adtrafficquality.google",
                'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
                'img-src': "'self' data: https: blob: http:",
                'font-src': "'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com",
                'connect-src': "'self' https://api.github.com https://pvpocket.xyz ws: wss: https://ep1.adtrafficquality.google https://googleads.g.doubleclick.net https://pagead2.googlesyndication.com https://tpc.googlesyndication.com https://www.google.com https://www.gstatic.com https://csi.gstatic.com https://adnxs.com https://adsystem.amazon.com",
                'frame-src': "'self' https://googleads.g.doubleclick.net https://tpc.googlesyndication.com https://ep2.adtrafficquality.google https://www.google.com",
                'frame-ancestors': "'none'",
                'base-uri': "'self'",
                'form-action': "'self'"
            }
        else:
            # Production CSP - secure but allows necessary external resources
            csp = {
                'default-src': "'self'",
                'script-src': "'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://pagead2.googlesyndication.com https://googleads.g.doubleclick.net https://tpc.googlesyndication.com https://www.google.com https://www.gstatic.com https://ep2.adtrafficquality.google",
                'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
                'img-src': "'self' data: https: blob:",
                'font-src': "'self' https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
                'connect-src': "'self' https://api.github.com https://pvpocket.xyz https://ep1.adtrafficquality.google https://googleads.g.doubleclick.net https://pagead2.googlesyndication.com https://tpc.googlesyndication.com https://www.google.com https://www.gstatic.com https://csi.gstatic.com https://adnxs.com https://adsystem.amazon.com",
                'frame-src': "'self' https://googleads.g.doubleclick.net https://tpc.googlesyndication.com https://ep2.adtrafficquality.google https://www.google.com",
                'frame-ancestors': "'none'",
                'base-uri': "'self'",
                'form-action': "'self'"
            }
        
        # Initialize Talisman for security headers
        if app.config.get('FLASK_ENV') == 'development':
            # Skip Talisman in development to avoid CSS/JS blocking issues
            self.talisman = None
            # Only log Talisman warning in main process
            if os.environ.get('WERKZEUG_RUN_MAIN'):
                print("⚠️ SECURITY: Talisman disabled in development mode")
        else:
            # Production - full security
            self.talisman = Talisman(
                app,
                force_https=True,
                strict_transport_security=True,
                strict_transport_security_max_age=31536000,
                content_security_policy=csp,
                # Remove nonce for now to avoid inline style conflicts
                content_security_policy_nonce_in=[],
                feature_policy={
                    'geolocation': "'none'",
                    'camera': "'none'",
                    'microphone': "'none'",
                    'payment': "'none'"
                }
            )
        
        # Register security event handlers
        self._register_security_handlers()
        
        # Add basic security headers for all environments
        @app.after_request
        def add_security_headers(response):
            """Add basic security headers and aggressive caching for static assets."""
            response.headers['X-XSS-Protection'] = '1; mode=block'

            # Add aggressive caching headers for static assets to reduce CDN costs
            if request.endpoint == 'static' or request.path.startswith('/static/'):
                # Cache static assets for 1 year
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                response.headers['Expires'] = 'Thu, 31 Dec 2025 23:59:59 GMT'
            elif any(request.path.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.css', '.js']):
                # Cache image and asset files for 1 year
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                response.headers['Expires'] = 'Thu, 31 Dec 2025 23:59:59 GMT'
            elif request.path.startswith('/energy_icons/') or request.path.startswith('/cards/'):
                # Cache CDN assets for 1 year (these are served through CDN)
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                response.headers['Expires'] = 'Thu, 31 Dec 2025 23:59:59 GMT'

            # Only add other headers if Talisman isn't handling them
            if not self.talisman:  # Development/test mode
                response.headers['X-Frame-Options'] = 'SAMEORIGIN'
                response.headers['X-Content-Type-Options'] = 'nosniff'
                response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            return response
        
        # Only log security config in main process
        if os.environ.get('WERKZEUG_RUN_MAIN'):
            print("✅ SECURITY: Rate limiting and security headers configured")
    
    def _register_security_handlers(self):
        """Register security-related event handlers."""
        
        @self.limiter.request_filter
        def filter_internal_requests():
            """Skip rate limiting for internal health checks."""
            return request.endpoint in ['main.health', 'internal.metrics']
        
        @self.app.errorhandler(429)
        def handle_rate_limit_exceeded(e):
            """Handle rate limit exceeded errors."""
            security_logger.warning(
                f"Rate limit exceeded for IP: {get_remote_address()}, "
                f"endpoint: {request.endpoint}, "
                f"user_agent: {request.headers.get('User-Agent', 'unknown')}"
            )
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.',
                'retry_after': e.retry_after
            }), 429
        
        @self.app.before_request
        def log_security_events():
            """Log security-relevant events."""
            # Log suspicious requests
            if self._is_suspicious_request():
                security_logger.warning(
                    f"Suspicious request from {get_remote_address()}: "
                    f"{request.method} {request.path} "
                    f"User-Agent: {request.headers.get('User-Agent', 'unknown')}"
                )
    
    def _is_suspicious_request(self) -> bool:
        """Check if request appears suspicious."""
        suspicious_patterns = [
            'wp-admin', 'phpmyadmin', '.env', '.git',
            'login.php', 'wp-login.php',
            'xmlrpc.php', 'config.php'
        ]
        
        # Check path for suspicious patterns
        path = request.path.lower()
        
        # Skip legitimate admin routes for authenticated admin users
        if path.startswith('/admin/'):
            from flask_login import current_user
            if current_user.is_authenticated and hasattr(current_user, 'email'):
                env_admins = os.environ.get("ADMIN_EMAILS", "")
                if env_admins:
                    admin_emails = [email.strip() for email in env_admins.split(",") if email.strip()]
                    if current_user.email in admin_emails:
                        return False  # Not suspicious for legitimate admin
        
        # Check for other suspicious patterns (but not legitimate admin routes)
        for pattern in suspicious_patterns:
            if pattern in path:
                return True
        
        # Flag generic 'admin' attempts that aren't our legitimate admin routes
        if 'admin' in path and not path.startswith('/admin/'):
            return True
        
        # Check for suspicious user agents
        user_agent = request.headers.get('User-Agent', '').lower()
        if not user_agent or 'bot' in user_agent and 'googlebot' not in user_agent:
            return True
        
        return False
    
    def require_api_key(self, key_header: str = 'X-API-Key'):
        """Decorator to require API key for endpoints."""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                api_key = request.headers.get(key_header)
                expected_key = current_app.config.get('API_KEY')
                
                if not api_key or not expected_key or api_key != expected_key:
                    security_logger.warning(
                        f"Invalid API auth attempt from {get_remote_address()}"
                    )
                    return jsonify({'error': 'Invalid or missing API key'}), 401
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def require_refresh_key(self, f):
        """Decorator to require refresh key for sensitive operations."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            refresh_key = request.headers.get('X-Refresh-Key')
            expected_key = current_app.config.get('REFRESH_SECRET_KEY')
            
            if not refresh_key or not expected_key or refresh_key != expected_key:
                security_logger.warning(
                    f"Invalid refresh auth attempt from {get_remote_address()}"
                )
                return jsonify({'error': 'Invalid or missing refresh key'}), 401
            
            return f(*args, **kwargs)
        return decorated_function


# Global security manager instance
security_manager = SecurityManager()


def init_security(app):
    """Initialize security for the Flask app."""
    security_manager.init_app(app)
    return security_manager


# Common rate limit decorators
def rate_limit_auth():
    """Rate limit for authentication endpoints."""
    def decorator(f):
        if security_manager.limiter:
            return security_manager.limiter.limit("5 per minute")(f)
        return f
    return decorator


def rate_limit_api():
    """Rate limit for API endpoints."""
    def decorator(f):
        if security_manager.limiter:
            return security_manager.limiter.limit("100 per minute")(f)
        return f
    return decorator


def rate_limit_api_paginated():
    """Higher rate limit for paginated endpoints that users scroll through quickly."""
    def decorator(f):
        if security_manager.limiter:
            return security_manager.limiter.limit("1000 per minute")(f)  # Temporarily very high to debug
        return f
    return decorator


def rate_limit_heavy():
    """Rate limit for resource-intensive endpoints."""
    def decorator(f):
        if security_manager.limiter:
            return security_manager.limiter.limit("10 per minute")(f)
        return f
    return decorator


def rate_limit_refresh():
    """Rate limit for cache refresh operations."""
    def decorator(f):
        if security_manager.limiter:
            return security_manager.limiter.limit("2 per minute")(f)
        return f
    return decorator


# Security monitoring utilities
class SecurityMonitor:
    """Monitor and track security events."""
    
    def __init__(self):
        self.failed_attempts: Dict[str, int] = {}
        self.last_reset = time.time()
    
    def record_failed_attempt(self, identifier: str) -> None:
        """Record a failed authentication attempt."""
        current_time = time.time()
        
        # Reset counters every hour
        if current_time - self.last_reset > 3600:
            self.failed_attempts.clear()
            self.last_reset = current_time
        
        self.failed_attempts[identifier] = self.failed_attempts.get(identifier, 0) + 1
        
        if self.failed_attempts[identifier] > 5:
            security_logger.error(
                f"Multiple failed attempts detected for {identifier}: "
                f"{self.failed_attempts[identifier]} attempts"
            )
    
    def is_blocked(self, identifier: str) -> bool:
        """Check if identifier should be blocked due to failed attempts."""
        return self.failed_attempts.get(identifier, 0) > 10
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get current security metrics."""
        return {
            'failed_attempts': dict(self.failed_attempts),
            'blocked_ips': [ip for ip, count in self.failed_attempts.items() if count > 10],
            'total_failed_attempts': sum(self.failed_attempts.values()),
            'monitoring_since': self.last_reset
        }


# Global security monitor
security_monitor = SecurityMonitor()