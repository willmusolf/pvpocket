# Deployment Security Fix - No More Hardcoded Secrets

## What Was Fixed
- Removed `app-test.yaml` from Git tracking (contained hardcoded OAuth secrets)
- Added deployment files with secrets to `.gitignore`
- Created `app-test.yaml.template` as reference without secrets

## Proper Deployment Workflow

### For Test Environment:
```bash
# Generate app-test.yaml with secrets from Google Secret Manager
python3 deploy_secrets.py --project-id pvpocket-dd286 --environment test

# Deploy to test environment  
gcloud app deploy app-test.yaml --project=pvpocket-dd286

# Clean up (remove file with secrets)
rm app-test.yaml
```

### For Production Environment:
```bash
# Generate app.yaml with secrets from Google Secret Manager
python3 deploy_secrets.py --project-id pvpocket-dd286 --environment production

# Deploy to production
gcloud app deploy app.yaml --project=pvpocket-dd286

# Clean up (remove file with secrets)
rm app.yaml
```

## Security Benefits
✅ No hardcoded secrets in Git repository
✅ Secrets managed centrally in Google Secret Manager
✅ Deployment files generated dynamically with proper secrets
✅ GitHub push protection no longer blocks commits

## Files Changed
- `app-test.yaml` - Removed from Git tracking
- `.gitignore` - Added deployment files with secrets  
- `app-test.yaml.template` - Added as reference template
- `app/security.py` - Fixed CSP for Google AdSense
  * Added `ep2.adtrafficquality.google` and `csi.gstatic.com` to connect-src
  * Added `ep2.adtrafficquality.google` to script-src
  * Added `ep2.adtrafficquality.google` and `www.google.com` to frame-src

## Next Steps
- Use `deploy_secrets.py` for all future deployments
- Never commit files containing actual secrets
- Use template files for reference structure