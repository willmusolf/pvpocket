# Terraform Infrastructure for Pokemon TCG Pocket

This directory contains Terraform configuration to provision the complete infrastructure for the Pokemon TCG Pocket application on Google Cloud Platform.

## Prerequisites

1. **Install Terraform**: Version >= 1.0
2. **Google Cloud SDK**: `gcloud` CLI installed and authenticated
3. **Project Setup**: Ensure you have owner/editor permissions on the GCP project

## Infrastructure Components

### Core Services
- **App Engine**: Main application hosting with auto-scaling
- **Firestore**: NoSQL database for application data
- **Firebase Storage**: File storage for card images and user content
- **Secret Manager**: Secure storage for application secrets

### Supporting Services
- **Cloud Storage**: CDN bucket for static assets and logs storage
- **Cloud Scheduler**: Automated data refresh jobs
- **Cloud Monitoring**: Uptime checks and alerting
- **Cloud Logging**: Centralized log collection

### Security & IAM
- Service accounts with least-privilege permissions
- Secret Manager integration for sensitive configuration
- IAM bindings for service-to-service authentication

## Usage

### 1. Initialize Terraform
```bash
cd terraform
terraform init
```

### 2. Plan Infrastructure Changes
```bash
terraform plan -var="project_id=your-project-id"
```

### 3. Apply Infrastructure
```bash
terraform apply -var="project_id=your-project-id"
```

### 4. Destroy Infrastructure (if needed)
```bash
terraform destroy -var="project_id=your-project-id"
```

## Configuration Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `project_id` | GCP Project ID | `pvpocket-dd286` | Yes |
| `region` | GCP region | `us-central1` | No |
| `app_engine_location` | App Engine location | `us-central` | No |
| `firestore_location` | Firestore location | `us-central1` | No |
| `storage_location` | Storage location | `US` | No |
| `environment` | Environment name | `prod` | No |

## Outputs

After applying, Terraform will output:
- App Engine application URL
- Service account emails
- Storage bucket names
- CDN URLs
- Monitoring check IDs

## Post-Deployment Setup

1. **Store Secrets**: Add actual secret values to Secret Manager:
   ```bash
   echo "your-secret-value" | gcloud secrets versions add flask-secret-key --data-file=-
   ```

2. **Configure OAuth**: Update Google OAuth console with App Engine URL

3. **Upload Static Assets**: Deploy static assets to CDN bucket

4. **Test Application**: Verify all services are working correctly

## State Management

For production use, enable remote state storage by uncommenting the backend configuration in `main.tf` and creating a GCS bucket for state storage.

## Security Considerations

- All secrets are stored in Secret Manager, never in code
- Service accounts follow principle of least privilege
- All storage buckets have appropriate lifecycle policies
- Monitoring and logging are configured for security events

## Maintenance

- Review and update resource configurations regularly
- Monitor costs through GCP billing console
- Update Terraform and provider versions as needed
- Regularly rotate secrets in Secret Manager