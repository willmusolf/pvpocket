#!/bin/bash

# cleanup_app_versions.sh
# Script to delete old App Engine versions to reduce costs
# Run after each deployment to keep only the most recent versions

set -e

PROJECT_ID="pvpocket-dd286"

echo "🧹 Starting App Engine version cleanup..."

# Function to cleanup versions for a service
cleanup_service_versions() {
    local service=$1
    local keep_count=${2:-2}  # Keep 2 most recent versions by default
    
    echo "📋 Cleaning up service: $service (keeping $keep_count versions)"
    
    # Get all versions for the service, sorted by creation time (oldest first)
    versions_to_delete=$(gcloud app versions list \
        --service="$service" \
        --format="value(version.id)" \
        --sort-by=createTime \
        --project="$PROJECT_ID" | head -n -"$keep_count")
    
    if [ -z "$versions_to_delete" ]; then
        echo "✅ No old versions to delete for service: $service"
        return
    fi
    
    echo "🗑️  Deleting old versions for $service:"
    echo "$versions_to_delete"
    
    # Delete old versions in batches to avoid command length limits
    echo "$versions_to_delete" | while IFS= read -r version; do
        if [ ! -z "$version" ]; then
            echo "   Deleting: $service/$version"
            gcloud app versions delete "$version" \
                --service="$service" \
                --project="$PROJECT_ID" \
                --quiet
        fi
    done
    
    echo "✅ Cleanup complete for service: $service"
}

# Cleanup default service (keep 2 versions)
cleanup_service_versions "default" 2

# Cleanup test-env service (keep 1 version - it's just for testing)
cleanup_service_versions "test-env" 1

# Cleanup test service if it exists
if gcloud app services describe test --project="$PROJECT_ID" &>/dev/null; then
    cleanup_service_versions "test" 1
else
    echo "ℹ️  Service 'test' does not exist, skipping"
fi

echo ""
echo "🎉 App Engine version cleanup complete!"
echo "💰 This should significantly reduce your daily costs."
echo ""
echo "📊 Current remaining versions:"
gcloud app versions list --project="$PROJECT_ID" --format="table(service,version.id,traffic_split)"