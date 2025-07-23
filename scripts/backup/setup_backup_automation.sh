#!/bin/bash
# Setup automated backup system for Pokemon TCG Pocket

set -e

PROJECT_ID=${1:-"pvpocket-dd286"}
BACKUP_BUCKET="${PROJECT_ID}-backups"

echo "Setting up backup automation for project: $PROJECT_ID"

# Create backup bucket if it doesn't exist
echo "Creating backup bucket..."
gsutil mb -p $PROJECT_ID gs://$BACKUP_BUCKET 2>/dev/null || echo "Bucket already exists"

# Set lifecycle policy for backup bucket
cat > lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 30}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://$BACKUP_BUCKET
rm lifecycle.json

# Build backup job Docker image
echo "Building backup job Docker image..."
cat > Dockerfile.backup << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install required packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install google-cloud-firestore-admin google-cloud-storage

# Copy backup script
COPY scripts/backup/firestore_backup.py .

# Make script executable
RUN chmod +x firestore_backup.py

# Set entrypoint
ENTRYPOINT ["python", "firestore_backup.py"]
EOF

# Build and push Docker image
docker build -f Dockerfile.backup -t gcr.io/$PROJECT_ID/backup-job:latest .
docker push gcr.io/$PROJECT_ID/backup-job:latest

# Create Cloud Scheduler jobs for automated backups
echo "Creating Cloud Scheduler jobs..."

# Daily export backup at 2 AM UTC
gcloud scheduler jobs create http daily-firestore-export \
  --schedule="0 2 * * *" \
  --uri="https://run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --message-body='{"apiVersion":"run.googleapis.com/v1","kind":"Job","metadata":{"name":"daily-backup-'$(date +%s)'","labels":{"type":"daily-backup"}},"spec":{"spec":{"template":{"spec":{"template":{"spec":{"serviceAccountName":"pokemon-tcg-pocket-jobs@'$PROJECT_ID'.iam.gserviceaccount.com","containers":[{"name":"backup","image":"gcr.io/'$PROJECT_ID'/backup-job:latest","args":["export"],"env":[{"name":"GCP_PROJECT_ID","value":"'$PROJECT_ID'"}]}],"restartPolicy":"Never"}}}}}}}}' \
  --time-zone="UTC" \
  --project=$PROJECT_ID || echo "Daily backup job already exists"

# Weekly JSON backup on Sundays at 3 AM UTC
gcloud scheduler jobs create http weekly-firestore-json \
  --schedule="0 3 * * 0" \
  --uri="https://run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --message-body='{"apiVersion":"run.googleapis.com/v1","kind":"Job","metadata":{"name":"weekly-backup-'$(date +%s)'","labels":{"type":"weekly-backup"}},"spec":{"spec":{"template":{"spec":{"template":{"spec":{"serviceAccountName":"pokemon-tcg-pocket-jobs@'$PROJECT_ID'.iam.gserviceaccount.com","containers":[{"name":"backup","image":"gcr.io/'$PROJECT_ID'/backup-job:latest","args":["json"],"env":[{"name":"GCP_PROJECT_ID","value":"'$PROJECT_ID'"}]}],"restartPolicy":"Never"}}}}}}}}' \
  --time-zone="UTC" \
  --project=$PROJECT_ID || echo "Weekly backup job already exists"

# Monthly cleanup on the 1st at 4 AM UTC
gcloud scheduler jobs create http monthly-backup-cleanup \
  --schedule="0 4 1 * *" \
  --uri="https://run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --message-body='{"apiVersion":"run.googleapis.com/v1","kind":"Job","metadata":{"name":"cleanup-backup-'$(date +%s)'","labels":{"type":"cleanup-backup"}},"spec":{"spec":{"template":{"spec":{"template":{"spec":{"serviceAccountName":"pokemon-tcg-pocket-jobs@'$PROJECT_ID'.iam.gserviceaccount.com","containers":[{"name":"backup","image":"gcr.io/'$PROJECT_ID'/backup-job:latest","args":["cleanup","60"],"env":[{"name":"GCP_PROJECT_ID","value":"'$PROJECT_ID'"}]}],"restartPolicy":"Never"}}}}}}}}' \
  --time-zone="UTC" \
  --project=$PROJECT_ID || echo "Cleanup job already exists"

# Clean up temporary files
rm -f Dockerfile.backup

echo ""
echo "Backup automation setup complete!"
echo ""
echo "Backup schedule:"
echo "  - Daily exports: 2:00 AM UTC"
echo "  - Weekly JSON backups: 3:00 AM UTC on Sundays" 
echo "  - Monthly cleanup: 4:00 AM UTC on 1st of month"
echo ""
echo "Manual backup usage:"
echo "  python scripts/backup/firestore_backup.py export"
echo "  python scripts/backup/firestore_backup.py json"
echo "  python scripts/backup/firestore_backup.py list"
echo "  python scripts/backup/firestore_backup.py cleanup 30"
echo ""
echo "Backup location: gs://$BACKUP_BUCKET"