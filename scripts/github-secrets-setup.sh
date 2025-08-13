#!/bin/bash

# GitHub Secrets Setup Script
# This script helps set up GitHub repository secrets for CI/CD deployment

set -e

echo "🔐 GitHub Secrets Setup for Pokemon TCG Pocket App"
echo "=================================================="

# Check if GitHub CLI is available
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed."
    echo "   Please install it: https://cli.github.com/"
    exit 1
fi

# Check if user is authenticated with GitHub
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub CLI."
    echo "   Please run: gh auth login"
    exit 1
fi

REPO="pokemon_tcg_pocket"  # Update this to match your actual repo name
PROJECT_ID="pvpocket-dd286"

echo "🏗️  Setting up GitHub secrets for repository: $REPO"
echo "📍 Google Cloud Project: $PROJECT_ID"

# Function to set a GitHub secret from Google Secret Manager
set_github_secret_from_gcp() {
    local github_secret_name=$1
    local gcp_secret_name=$2
    
    echo "📥 Retrieving $gcp_secret_name from Secret Manager..."
    local secret_value=$(gcloud secrets versions access latest --secret="$gcp_secret_name" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$secret_value" ]; then
        echo "📤 Setting GitHub secret: $github_secret_name"
        echo "$secret_value" | gh secret set "$github_secret_name" -R "$REPO"
        echo "✅ $github_secret_name set successfully"
    else
        echo "❌ Failed to retrieve $gcp_secret_name from Secret Manager"
        return 1
    fi
}

# Set up service account key for GitHub Actions authentication
echo ""
echo "🔑 Setting up GCP_SA_KEY (Service Account Key)..."
SA_EMAIL="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

# Create and download service account key
echo "📋 Creating service account key for $SA_EMAIL..."
gcloud iam service-accounts keys create github-actions-key.json --iam-account="$SA_EMAIL"

if [ -f "github-actions-key.json" ]; then
    echo "📤 Setting GitHub secret: GCP_SA_KEY"
    gh secret set GCP_SA_KEY -R "$REPO" < github-actions-key.json
    echo "✅ GCP_SA_KEY set successfully"
    
    # Clean up the key file for security
    rm github-actions-key.json
    echo "🗑️  Temporary key file removed"
else
    echo "❌ Failed to create service account key"
    exit 1
fi

# Set up application secrets from Google Secret Manager
echo ""
echo "🔐 Setting up application secrets from Secret Manager..."

set_github_secret_from_gcp "SECRET_KEY" "flask-secret-key"
set_github_secret_from_gcp "REFRESH_SECRET_KEY" "refresh-secret-key"
set_github_secret_from_gcp "GOOGLE_OAUTH_CLIENT_ID" "google-oauth-client-id"
set_github_secret_from_gcp "GOOGLE_OAUTH_CLIENT_SECRET" "google-oauth-client-secret"
set_github_secret_from_gcp "TASK_AUTH_TOKEN" "task-auth-token"
set_github_secret_from_gcp "ADMIN_EMAILS" "admin-emails"

echo ""
echo "🎉 GitHub Secrets Setup Complete!"
echo "=================================="
echo ""
echo "✅ All required secrets have been configured:"
echo "   • GCP_SA_KEY - Service account key for Google Cloud authentication"
echo "   • SECRET_KEY - Flask secret key"
echo "   • REFRESH_SECRET_KEY - API refresh token"
echo "   • GOOGLE_OAUTH_CLIENT_ID - OAuth client ID"
echo "   • GOOGLE_OAUTH_CLIENT_SECRET - OAuth client secret"
echo "   • TASK_AUTH_TOKEN - Background task authentication"
echo "   • ADMIN_EMAILS - Admin email addresses"
echo ""
echo "🚀 Your GitHub Actions CI/CD pipeline should now work correctly!"
echo "   Test it by pushing to the 'development' branch for test deployment"
echo "   or 'main' branch for production deployment."