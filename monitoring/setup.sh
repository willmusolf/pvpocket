#!/bin/bash
# Setup script for monitoring and alerting

set -e

PROJECT_ID=${1:-"pvpocket-dd286"}
NOTIFICATION_EMAIL=${2:-"admin@example.com"}

echo "Setting up monitoring for project: $PROJECT_ID"

# Create notification channel for email alerts
echo "Creating email notification channel..."
CHANNEL_ID=$(gcloud alpha monitoring channels create \
  --display-name="Pokemon TCG Pocket Alerts" \
  --type=email \
  --channel-labels=email_address=$NOTIFICATION_EMAIL \
  --format="value(name)" \
  --project=$PROJECT_ID)

echo "Created notification channel: $CHANNEL_ID"

# Update alerting.yaml with the notification channel
sed -i.bak "s|# - projects/YOUR_PROJECT/notificationChannels/YOUR_CHANNEL_ID|  - $CHANNEL_ID|g" alerting.yaml

# Create dashboard
echo "Creating monitoring dashboard..."
gcloud monitoring dashboards create --config-from-file=dashboard.json --project=$PROJECT_ID

# Create alert policies (Note: This requires splitting the YAML file)
# For now, users need to create alerts manually or use the Cloud Console

echo "Monitoring setup complete!"
echo "Dashboard created. View at: https://console.cloud.google.com/monitoring/dashboards"
echo "Create alert policies manually using the alerting.yaml as reference"
echo ""
echo "To create uptime checks manually:"
echo "1. Go to Cloud Monitoring > Uptime Checks"
echo "2. Create check for: https://$PROJECT_ID.uc.r.appspot.com/health"
echo "3. Set up alerting on check failures"