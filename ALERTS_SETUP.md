# Production Alert System

## When Alerts Fire

The production alert system will automatically send email notifications for the following critical errors:

### 1. 500 Server Errors
- **Location**: Global error handler in `app/__init__.py`
- **Triggers**: Any unhandled exception that causes a 500 error
- **Alert Type**: `SERVER ERROR (500)`

### 2. Database Connection Pool Exhaustion
- **Location**: `app/db_service.py` (FirestoreConnectionPool)
- **Triggers**: When all database connections are in use and new requests can't get a connection
- **Alert Type**: `DATABASE FAILURE`

### 3. Database Operation Failures (After Retries)
- **Location**: `app/db_service.py` (retry decorator)
- **Triggers**: When database operations fail after 3 retry attempts
- **Includes**: ServiceUnavailable, DeadlineExceeded, InternalServerError, Cancelled, ResourceExhausted errors
- **Alert Type**: `DATABASE FAILURE`

### 4. Authentication System Failures
- **Location**: `app/routes/auth.py` (Google OAuth handler)
- **Triggers**: When Firestore client is not available during login attempts
- **Alert Type**: `AUTH SYSTEM FAILURE`

## Alert Contents

Each alert email includes:
- Error type and message
- Timestamp (UTC)
- Request information (if available)
- Quick links to logs and health check
- Clear indication that immediate attention is needed

## Testing

To test the alert system:
```bash
python test_alerts.py
```

This will send a test alert to verify the email configuration is working correctly.

## Configuration

Alerts are configured via environment variables in Google Secret Manager:
- `ALERT_EMAIL_USER`: Gmail account sending alerts
- `ALERT_EMAIL_PASS`: Gmail app password
- `ALERT_EMAIL_TO`: Email address to receive alerts
- `ALERT_SMS_TO`: (Optional) SMS gateway for text alerts

## Important Notes

- Alerts only fire in production (when `FLASK_ENV=production`)
- The system is designed to alert only for truly critical errors requiring immediate attention
- Non-critical errors are logged but do not trigger alerts