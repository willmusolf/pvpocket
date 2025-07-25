#!/usr/bin/env python3
"""
Quick script to test production alerts.
Run this after deploying to production to verify alerts work.
"""

import requests
import os
from google.cloud import secretmanager

def get_auth_token():
    """Get the task auth token from Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/pvpocket-dd286/secrets/task-auth-token/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"❌ Failed to get auth token: {e}")
        return None

def test_production_alerts():
    """Send a test alert to production."""
    print("🧪 Testing Production Alert System...")
    
    # Get auth token
    auth_token = get_auth_token()
    if not auth_token:
        print("❌ Cannot get auth token. Make sure you're authenticated with gcloud.")
        return
    
    # Test alert endpoint
    url = "https://pvpocket.xyz/internal/test-alert"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    try:
        print("📤 Sending test alert...")
        response = requests.post(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result['message']}")
            print("📧 Check your email for the detailed alert")
            print("📱 Check your phone for the SMS alert")
        else:
            print(f"❌ Test failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_production_alerts()