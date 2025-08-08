"""
Google Cloud Platform exception handling module.

This module provides compatibility for GCP exceptions that may not be available
in all environments or package versions.
"""

# Try to import from google-cloud-core or firestore
try:
    from google.cloud.exceptions import (
        DeadlineExceeded,
        PermissionDenied,
        ResourceExhausted,
        ServiceUnavailable,
        Conflict,
        NotFound
    )
except ImportError:
    # Fallback: create custom exception classes
    class GoogleCloudException(Exception):
        """Base class for Google Cloud exceptions."""
        pass
    
    class DeadlineExceeded(GoogleCloudException):
        """Operation timed out."""
        pass
    
    class PermissionDenied(GoogleCloudException):
        """Permission denied by security rules."""
        pass
    
    class ResourceExhausted(GoogleCloudException):
        """Quota exceeded."""
        pass
    
    class ServiceUnavailable(GoogleCloudException):
        """Service temporarily unavailable."""
        pass
    
    class Conflict(GoogleCloudException):
        """Transaction conflict."""
        pass
    
    class NotFound(GoogleCloudException):
        """Resource not found."""
        pass

# Export all exception classes
__all__ = [
    'DeadlineExceeded',
    'PermissionDenied', 
    'ResourceExhausted',
    'ServiceUnavailable',
    'Conflict',
    'NotFound'
]