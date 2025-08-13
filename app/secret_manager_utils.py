"""
Secure utilities for accessing Google Secret Manager.
"""

from google.cloud import secretmanager
from flask import current_app
import logging
import os
from typing import Optional

# Cache for email credentials to avoid repeated fetches
_email_credentials_cache = None

def get_secret(secret_name: str, project_id: Optional[str] = None) -> Optional[str]:
    """
    Securely fetch a secret from Google Secret Manager.
    
    Args:
        secret_name: Name of the secret to fetch
        project_id: GCP project ID (defaults to app config)
        
    Returns:
        Secret value as string, or None if not found/error
    """
    try:
        # Use project ID from config if not provided
        if not project_id:
            try:
                project_id = current_app.config.get('GCP_PROJECT_ID')
            except RuntimeError:
                # No app context, try environment variable
                import os
                project_id = os.environ.get('GCP_PROJECT_ID')
            
        if not project_id:
            try:
                current_app.logger.warning("No GCP_PROJECT_ID configured for Secret Manager")
            except RuntimeError:
                print("No GCP_PROJECT_ID configured for Secret Manager")
            return None
            
        # Only log in debug mode
        debug_mode = os.environ.get('FLASK_DEBUG') == '1'
        
        # Create the Secret Manager client
        client = secretmanager.SecretManagerServiceClient()
        
        # Build the resource name of the secret version
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        
        # Access the secret version
        response = client.access_secret_version(request={"name": name})
        
        # Return the decoded secret value
        secret_value = response.payload.data.decode("UTF-8")
        return secret_value
        
    except Exception as e:
        try:
            current_app.logger.error(f"Failed to retrieve secret '{secret_name}': {str(e)}")
            current_app.logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
        except RuntimeError:
            print(f"Failed to retrieve secret '{secret_name}': {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
        return None


def get_email_credentials() -> tuple[Optional[str], Optional[str]]:
    """
    Get email credentials from Secret Manager with fallback to environment variables.
    Uses caching to avoid repeated Secret Manager calls.
    
    Returns:
        Tuple of (username, password) or (None, None) if not available
    """
    global _email_credentials_cache
    
    # Return cached credentials if available
    if _email_credentials_cache is not None:
        return _email_credentials_cache
    
    try:
        # Try Secret Manager first
        username = get_secret("mail-username")
        password = get_secret("mail-password") 
        
        if username and password:
            # Clean up Gmail App Password - remove spaces, non-breaking spaces, and other Unicode issues
            import re
            # Remove all whitespace characters including non-breaking spaces (\xa0)
            cleaned_password = re.sub(r'\s+', '', password)  # Removes all whitespace including \xa0
            # Ensure only ASCII characters (Gmail App Passwords are always ASCII)
            cleaned_password = ''.join(char for char in cleaned_password if ord(char) < 128)
            
            # Cache the credentials
            _email_credentials_cache = (username.strip(), cleaned_password)
            return _email_credentials_cache
            
        # Fallback to environment variables (development)
        env_username = os.environ.get("MAIL_USERNAME")
        env_password = os.environ.get("MAIL_PASSWORD")
        
        if env_username and env_password:
            # Cache the credentials
            _email_credentials_cache = (env_username.strip(), env_password.strip())
            return _email_credentials_cache
            
        # No credentials available
        _email_credentials_cache = (None, None)
        return _email_credentials_cache
        
    except Exception as e:
        try:
            current_app.logger.error(f"Error loading email credentials: {str(e)}")
        except RuntimeError:
            print(f"Error loading email credentials: {str(e)}")  # Fallback logging
        return None, None


def test_secret_manager_access() -> dict:
    """
    Test Secret Manager connectivity and permissions.
    
    Returns:
        Dict with test results
    """
    try:
        project_id = current_app.config.get('GCP_PROJECT_ID')
        if not project_id:
            return {"success": False, "error": "No GCP_PROJECT_ID configured"}
            
        client = secretmanager.SecretManagerServiceClient()
        
        # Try to list secrets (requires Secret Manager Secret Accessor role)
        parent = f"projects/{project_id}"
        
        try:
            secrets = list(client.list_secrets(request={"parent": parent}))
            secret_names = [secret.name.split('/')[-1] for secret in secrets[:5]]  # First 5
            
            return {
                "success": True,
                "project_id": project_id,
                "accessible_secrets": secret_names,
                "total_secrets": len(secrets) if len(secrets) <= 100 else "100+"
            }
        except Exception as list_error:
            # Try to access a specific secret instead
            test_result = get_secret("mail-username")
            if test_result:
                return {
                    "success": True,
                    "project_id": project_id,
                    "note": "Can access secrets but not list them (limited permissions)"
                }
            else:
                return {
                    "success": False, 
                    "error": f"Cannot access Secret Manager: {str(list_error)}"
                }
                
    except Exception as e:
        return {"success": False, "error": f"Secret Manager test failed: {str(e)}"}