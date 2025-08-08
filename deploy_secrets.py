#!/usr/bin/env python3
"""
Deployment script to set environment variables from Google Secret Manager.
Run this before deploying to populate secrets in the environment.
"""

import os
import subprocess
import sys
from google.cloud import secretmanager


def get_secret(project_id: str, secret_name: str, version: str = "latest") -> str:
    """Retrieve a secret from Google Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_name}/versions/{version}"
    
    try:
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8").strip()
    except Exception as e:
        print(f"Error accessing secret {secret_name}: {e}")
        sys.exit(1)


def set_deployment_secrets(project_id: str, environment: str = "production"):
    """Set environment variables from Secret Manager for deployment."""
    
    # Define secrets to retrieve
    secrets_map = {
        "SECRET_KEY": "flask-secret-key",
        "REFRESH_SECRET_KEY": "refresh-secret-key", 
        "GOOGLE_OAUTH_CLIENT_ID": "google-oauth-client-id",
        "GOOGLE_OAUTH_CLIENT_SECRET": "google-oauth-client-secret",
        "TASK_AUTH_TOKEN": "task-auth-token",
        "ADMIN_EMAILS": "admin-emails",  # Admin access control
        # Alert system configuration
        "ALERT_EMAIL_USER": "alert-email-user",
        "ALERT_EMAIL_PASS": "alert-email-pass",
        "ALERT_EMAIL_TO": "alert-email-to",
        "ALERT_SMS_TO": "alert-sms-to"
    }
    
    print(f"Retrieving secrets from project: {project_id}")
    print(f"Environment: {environment}")
    
    # Environment-specific configuration
    if environment == "test":
        flask_env = "staging"
        service_config = 'service: test-env\n\n'
        scaling_config = """automatic_scaling:
  target_cpu_utilization: 0.6
  max_instances: 3
  min_instances: 0

resources:
  cpu: 1
  memory_gb: 1
  disk_size_gb: 10"""
        max_connections = "10"
    else:
        flask_env = "production"
        service_config = ""
        scaling_config = """automatic_scaling:
  target_cpu_utilization: 0.6
  target_throughput_utilization: 0.6
  max_concurrent_requests: 50
  max_instances: 10
  min_instances: 1

resources:
  cpu: 1
  memory_gb: 2
  disk_size_gb: 10"""
        max_connections = "15"
    
    # Create app.yaml with secrets
    app_yaml_content = f"""{service_config}runtime: python311
entrypoint: gunicorn -b :$PORT run:app

# Scalability and Performance Settings
{scaling_config}

handlers:
- url: /.*
  script: auto
  secure: always

env_variables:
  FLASK_CONFIG: '{flask_env}'
  FLASK_ENV: '{flask_env}'
  GCP_PROJECT_ID: "{project_id}"
  FIREBASE_SECRET_NAME: "firebase-admin-sdk-json"
"""
    
    # Add secrets to environment variables
    for env_var, secret_name in secrets_map.items():
        secret_value = get_secret(project_id, secret_name)
        app_yaml_content += f'  {env_var}: "{secret_value}"\n'
    
    # Add scalability configuration
    app_yaml_content += f"""  
  # Scalability Configuration
  USE_FIRESTORE_CACHE: 'false'  # Set to 'true' to use Firestore as cache backend
  CACHE_TTL_HOURS: '24'         # Card collection cache TTL in hours
  USER_CACHE_TTL_MINUTES: '30'  # User data cache TTL in minutes
  MAX_DB_CONNECTIONS: '{max_connections}'      # Maximum database connection pool size
  MONITORING_ENABLED: 'true'    # Enable performance monitoring
"""
    
    # Write to appropriate yaml file
    if environment == "production":
        filename = "app.yaml"
        print(f"Updated {filename} with secrets from Secret Manager")
        print(f"Deploy with: gcloud app deploy {filename}")
    else:
        filename = f"app-{environment}.yaml"  
        print(f"Created {filename} with secrets from Secret Manager")
        print(f"Deploy with: gcloud app deploy {filename}")
        print(f"Remember to delete {filename} after deployment!")
    
    with open(filename, "w") as f:
        f.write(app_yaml_content)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy with secrets from Secret Manager')
    parser.add_argument('--project-id', default=os.environ.get("GCP_PROJECT_ID", "pvpocket-dd286"),
                       help='GCP Project ID')
    parser.add_argument('--environment', choices=['production', 'test'], default='production',
                       help='Deployment environment')
    
    args = parser.parse_args()
    set_deployment_secrets(args.project_id, args.environment)