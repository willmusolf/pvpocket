# shared_utils.py

import os
import requests
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud import secretmanager
import json


def initialize_firebase():
    """Initializes a single Firebase app instance if not already done."""
    if not firebase_admin._apps:
        try:
            project_id = os.environ.get("GCP_PROJECT_ID")
            secret_name = os.environ.get("FIREBASE_SECRET_NAME")
            bucket_name = os.environ.get("FIREBASE_STORAGE_BUCKET")

            if not bucket_name:
                raise ValueError(
                    "FIREBASE_STORAGE_BUCKET environment variable not set."
                )

            if project_id and secret_name:
                # Only log Firebase initialization in development
                if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
                    print("Initializing Firebase from Secret Manager...")
                client = secretmanager.SecretManagerServiceClient()
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                secret_payload = response.payload.data.decode("UTF-8")
                cred_dict = json.loads(secret_payload)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
            else:
                # Only log Firebase initialization in development
                if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
                    print("Initializing Firebase with Application Default Credentials...")
                firebase_admin.initialize_app(options={"storageBucket": bucket_name})

            # Only log success in development
            if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
                print("Firebase initialized successfully.")
        except Exception as e:
            # Always log critical Firebase errors
            print(f"CRITICAL ERROR: Failed to initialize Firebase Admin SDK: {e}")
            exit(1)


def trigger_cache_refresh():
    """Triggers the cache refresh endpoint on your web app."""
    load_dotenv()
    base_url = os.getenv("WEBSITE_URL")
    refresh_key = os.getenv("REFRESH_SECRET_KEY")

    if not base_url or not refresh_key:
        # Only log in development
        if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
            print(
                "ERROR: WEBSITE_URL or REFRESH_SECRET_KEY not set. Cannot trigger refresh."
            )
        return

    refresh_url = f"{base_url}/api/refresh-cards"
    headers = {"X-Refresh-Key": refresh_key}
    # Only log cache refresh in development
    if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
        print(f"Triggering cache refresh at {refresh_url}...")
    try:
        response = requests.post(refresh_url, headers=headers, timeout=60)
        if response.status_code == 200:
            # Only log success in development
            if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
                print(f"SUCCESS: Cache refresh triggered: {response.json()}")
        else:
            # Only log errors in development
            if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
                print(
                    f"ERROR: Cache refresh failed. Status: {response.status_code}, Text: {response.text}"
                )
    except requests.exceptions.RequestException as e:
        # Only log connection errors in development
        if os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_CONFIG') == 'development':
            print(f"CRITICAL ERROR: Could not connect to refresh cache: {e}")
