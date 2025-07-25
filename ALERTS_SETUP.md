# 🚨 Production Alerts Setup Guide

## Quick Setup (5 minutes)

### Step 1: Get Gmail App Password
1. Go to your **Gmail Settings** → **Security** → **2-Step Verification**
2. Go to **App passwords** 
3. Create new app password for "Pokemon TCG Alerts"
4. **Save the 16-character password** (you'll need it)

### Step 2: Find Your SMS Email Gateway
Your phone carrier has an email-to-SMS gateway:

- **Verizon:** `your-phone-number@vtext.com`
- **AT&T:** `your-phone-number@txt.att.net`
- **T-Mobile:** `your-phone-number@tmomail.net`
- **Sprint:** `your-phone-number@messaging.sprintpcs.com`

Example: If your number is 555-123-4567 on Verizon: `5551234567@vtext.com`
`9522559890@tmomail.net`

### Step 3: Add Secrets to Google Cloud
```bash
# Add your email credentials
echo "your-email@gmail.com" | gcloud secrets create alert-email-user --data-file=-

# Add your Gmail app password (16 characters)
echo "your-16-char-app-password" | gcloud secrets create alert-email-pass --data-file=-

# Add your email (for detailed alerts)
echo "your-email@gmail.com" | gcloud secrets create alert-email-to --data-file=-

# Add your SMS gateway (for instant alerts)
echo "5551234567@vtext.com" | gcloud secrets create alert-sms-to --data-file=-
```

### Step 4: Deploy to Production
```bash
python deploy_secrets.py --environment production
gcloud app deploy app-production-deploy.yaml
rm app-production-deploy.yaml
```

## What Gets Alerted

### 🚨 CRITICAL ALERTS (Email + SMS):
- **500 Server Errors** - App is broken for users
- **Database Failures** - Can't connect to Firestore
- **Authentication Failures** - Users can't log in
- **Site Down** - Health check fails

### ❌ WON'T Alert:
- 404 errors (normal user navigation)
- Individual user mistakes
- Development/test environment issues

## Testing the Alerts

### Test in Development (Won't Send):
```bash
# Alerts only work in production
FLASK_ENV=development python run.py
# Visit /some-broken-route - no alert sent
```

### Test in Production:
```bash
# After deployment, visit your site
# If something breaks, you'll get:
# 📧 Email with full details
# 📱 SMS with brief alert
```

## Example Alert Messages

### Email Alert:
```
🚨 CRITICAL ERROR in Pokemon TCG Pocket Production 🚨

ERROR TYPE: SERVER ERROR (500)
TIME: 2025-07-25 14:30:00 UTC
SITE: https://pvpocket.xyz

ERROR DETAILS:
Database connection failed

REQUEST INFO:
GET /decks from 192.168.1.100

QUICK LINKS:
• View Logs: [direct link to Cloud Console]
• Site Status: https://pvpocket.xyz/health
```

### SMS Alert:
```
🚨 CRITICAL ERROR: Pokemon TCG Pocket
SERVER ERROR (500)
14:30 UTC
Check email for details
```

## Troubleshooting

### If Alerts Don't Work:
1. **Check Gmail app password** - Make sure it's correct
2. **Check phone carrier** - Verify your SMS gateway
3. **Check logs:** `gcloud app logs tail -s default --filter="alert"`
4. **Test Gmail:** Send regular email first

### If Too Many Alerts:
- Alerts only send for truly critical errors
- Each error type is limited to prevent spam
- Only happens in production environment

## Quick Commands

```bash
# Check if alerts are configured
gcloud secrets list | grep alert

# View recent alerts in logs
gcloud app logs read --filter="textPayload:alert" --limit=10

# Test site health
curl https://pvpocket.xyz/health
```

You're all set! Now you'll know immediately when something breaks in production. 🚀