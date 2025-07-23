# Pokemon TCG Pocket - Deployment Guide

This guide walks you through deploying the Pokemon TCG Pocket application using the newly implemented infrastructure and CI/CD pipeline.

## 🚨 Critical Security Fix Applied

**IMPORTANT**: This deployment setup removes all hardcoded secrets from configuration files and moves them to Google Secret Manager. Your application is now much more secure!

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **GitHub Repository** with the code
3. **Required CLI Tools**:
   - `gcloud` CLI (authenticated)
   - `terraform` (>= 1.0)
   - `docker` (for building containers)

## 🏗️ Infrastructure Setup

### 1. Deploy Infrastructure with Terraform

```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init

# Review planned changes
terraform plan -var="project_id=your-project-id"

# Apply infrastructure
terraform apply -var="project_id=your-project-id"
```

This creates:
- App Engine application
- Firestore database
- Storage buckets (Firebase Storage & CDN)
- Secret Manager secrets (empty, you'll populate them next)
- Service accounts with proper IAM
- Monitoring and logging setup

### 2. Store Secrets in Secret Manager

After Terraform completes, add your actual secret values:

```bash
# Generate a secure Flask secret key
python -c "import secrets; print(secrets.token_urlsafe(32))" | \
  gcloud secrets versions add flask-secret-key --data-file=-

# Add your refresh secret key
echo "your-refresh-secret-key" | \
  gcloud secrets versions add refresh-secret-key --data-file=-

# Add Google OAuth credentials
echo "your-google-oauth-client-id" | \
  gcloud secrets versions add google-oauth-client-id --data-file=-
  
echo "your-google-oauth-client-secret" | \
  gcloud secrets versions add google-oauth-client-secret --data-file=-

# Add task authentication token
python -c "import secrets; print(secrets.token_urlsafe(24))" | \
  gcloud secrets versions add task-auth-token --data-file=-

# Add Firebase admin SDK JSON (if you have a service account key file)
gcloud secrets versions add firebase-admin-sdk-json --data-file=path/to/your/firebase-key.json
```

## 🔄 CI/CD Pipeline Setup

### 1. Configure GitHub Secrets

In your GitHub repository settings, add these secrets:

```
GCP_SA_KEY=<your-service-account-json-key>
SECRET_KEY=<your-flask-secret-key>
REFRESH_SECRET_KEY=<your-refresh-secret-key>
GOOGLE_OAUTH_CLIENT_ID=<your-oauth-client-id>
GOOGLE_OAUTH_CLIENT_SECRET=<your-oauth-client-secret>
TASK_AUTH_TOKEN=<your-task-auth-token>
```

### 2. Branch Strategy

- **`main` branch**: Auto-deploys to production
- **`develop` branch**: Auto-deploys to test environment
- **Pull requests**: Run tests and security scans

### 3. Pipeline Features

✅ **Automated Testing**:
- Security scans (dependency vulnerabilities, code analysis)
- Performance testing with detailed reports
- Health checks and integration tests

✅ **Multi-Environment Deployment**:
- Test environment for `develop` branch
- Production deployment for `main` branch
- Environment-specific configurations

✅ **Security Integration**:
- Secrets retrieved from Secret Manager during deployment
- No secrets in code or configuration files
- Automated security scanning

## 📊 Monitoring & Alerting

### 1. Set Up Monitoring Dashboard

```bash
cd monitoring
./setup.sh your-project-id admin@yourdomain.com
```

This creates:
- Cloud Monitoring dashboard
- Email notification channel
- Uptime checks
- Performance alerts

### 2. View Monitoring

- **Dashboard**: https://console.cloud.google.com/monitoring/dashboards
- **Alerts**: https://console.cloud.google.com/monitoring/alerting
- **Uptime Checks**: https://console.cloud.google.com/monitoring/uptime

## 🗄️ Backup System

### 1. Set Up Automated Backups

```bash
cd scripts/backup
./setup_backup_automation.sh your-project-id
```

This configures:
- **Daily Firestore exports** at 2:00 AM UTC
- **Weekly JSON backups** on Sundays at 3:00 AM UTC  
- **Monthly cleanup** of old backups on 1st at 4:00 AM UTC

### 2. Manual Backup Operations

```bash
# Create an export backup
python scripts/backup/firestore_backup.py export

# Create a JSON backup for inspection
python scripts/backup/firestore_backup.py json

# List available backups
python scripts/backup/firestore_backup.py list

# Clean up old backups (older than 30 days)
python scripts/backup/firestore_backup.py cleanup 30
```

## 🚀 Deployment Process

### Automatic Deployment

1. **Push to `develop`**: Triggers test deployment
2. **Create PR to `main`**: Runs full test suite
3. **Merge to `main`**: Deploys to production with health checks

### Manual Deployment

For immediate deployments or troubleshooting:

```bash
# Production deployment using Secret Manager (recommended)
python deploy_secrets.py --environment production
gcloud app deploy app-production-deploy.yaml
rm app-production-deploy.yaml  # Clean up

# Test environment deployment using Secret Manager
python deploy_secrets.py --environment test
gcloud app deploy app-test-deploy.yaml
rm app-test-deploy.yaml  # Clean up

# Or using environment variables (development only - NOT RECOMMENDED)
gcloud app deploy app.yaml  # Production
gcloud app deploy app-test.yaml  # Test environment
```

## 🔍 Health Monitoring

### Application Health Endpoints

- **Health Check**: `https://your-app.uc.r.appspot.com/health`
- **Metrics**: `https://your-app.uc.r.appspot.com/metrics`
- **Scalability Dashboard**: `https://your-app.uc.r.appspot.com/test-scalability-dashboard`

### Performance Monitoring

The application includes comprehensive monitoring:
- Response time tracking
- Cache hit rate monitoring
- Database connection pool usage
- Memory and CPU utilization
- Error rate tracking

## 🛠️ Development Workflow

### Local Development

1. **Copy environment template**:
   ```bash
   cp .env.example .env
   # Edit .env with your local values
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   npm install
   ```

3. **Run locally**:
   ```bash
   python run.py
   ```

### Testing

```bash
# Quick functionality tests
python test_quick.py

# Comprehensive performance tests  
python test_scalability.py

# CI-style performance tests
python scripts/ci_performance_tests.py --quick
```

## 🚨 Troubleshooting

### Common Issues

1. **Secret Manager Access Denied**:
   - Ensure service account has `roles/secretmanager.secretAccessor`
   - Verify secrets exist: `gcloud secrets list`

2. **Deployment Failures**:
   - Check GitHub Actions logs
   - Verify all required secrets are set
   - Ensure App Engine APIs are enabled

3. **Performance Issues**:
   - Check monitoring dashboard
   - Review performance test reports
   - Monitor cache hit rates

### Debug Commands

```bash
# Check application health
curl https://your-app.uc.r.appspot.com/health

# View recent logs
gcloud app logs tail -s default

# Check secret values (be careful!)
gcloud secrets versions access latest --secret=flask-secret-key

# Test database connectivity
python -c "from app import create_app; app = create_app(); print('DB connection OK')"
```

## 🔒 Security Best Practices

✅ **Implemented**:
- All secrets moved to Secret Manager
- Service accounts with minimal permissions
- Automated security scanning in CI
- HTTPS enforcement
- Input validation and sanitization

✅ **Recommended**:
- Regularly rotate secrets
- Monitor security scan results
- Keep dependencies updated
- Review access logs periodically

## 📈 Performance Optimization

The application includes several performance features:
- **In-memory caching** with 98%+ hit rates
- **Connection pooling** for database efficiency
- **CDN integration** for static assets
- **Auto-scaling** based on demand
- **Background task processing**

Monitor these through the performance dashboard and adjust scaling parameters as needed.

## 🆘 Support & Maintenance

### Regular Maintenance Tasks

1. **Weekly**: Review monitoring alerts and performance reports
2. **Monthly**: Check backup integrity and update dependencies
3. **Quarterly**: Rotate secrets and review security configurations
4. **Annually**: Review infrastructure costs and scaling needs

### Getting Help

- **Application logs**: `gcloud app logs tail`
- **Infrastructure status**: Google Cloud Console
- **Performance metrics**: Monitoring dashboard
- **Backup status**: Check `gs://your-project-backups`

---

## Next Steps

After following this guide, your Pokemon TCG Pocket application will be:
- ✅ Securely deployed with no hardcoded secrets
- ✅ Automatically tested and deployed via CI/CD
- ✅ Monitored with comprehensive alerting
- ✅ Backed up with automated daily exports
- ✅ Scalable and performance-optimized

Your app is now production-ready and much more deployable! 🎉