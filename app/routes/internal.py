"""
Internal routes for handling background tasks and system operations.
These endpoints are used by Cloud Tasks and other internal services.
"""

from flask import Blueprint, request, jsonify, current_app
import json
import os
from datetime import datetime
from ..task_queue import task_queue
from ..monitoring import performance_monitor


internal_bp = Blueprint("internal", __name__, url_prefix="/internal")


def verify_task_auth():
    """Verify that the request is from an authorized task queue."""
    auth_token = request.headers.get("X-Task-Auth")
    expected_token = current_app.config.get("TASK_AUTH_TOKEN", "dev-token")
    
    if not auth_token or auth_token != expected_token:
        return False
    
    # Additional verification for Cloud Tasks
    if "X-CloudTasks-QueueName" in request.headers:
        return True  # Request from Cloud Tasks
    
    # For development/testing
    if current_app.config.get("FLASK_ENV") == "development":
        return True
    
    return False


@internal_bp.route("/tasks/<task_type>", methods=["POST"])
def handle_task(task_type: str):
    """Handle background task execution."""
    
    if not verify_task_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # Parse task payload
        task_data = request.get_json()
        if not task_data:
            return jsonify({"error": "Invalid task payload"}), 400
        
        payload = task_data.get("payload", {})
        
        # Get handler from task registry
        handler = task_queue._task_registry.get(task_type)
        if not handler:
            return jsonify({"error": f"No handler for task type: {task_type}"}), 400
        
        # Execute the task
        print(f"Executing task: {task_type}")
        handler(payload)
        
        return jsonify({"status": "success", "task_type": task_type}), 200
        
    except Exception as e:
        print(f"Error executing task {task_type}: {e}")
        return jsonify({"error": str(e)}), 500


@internal_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for internal services."""
    try:
        from ..cache_manager import cache_manager
        from ..db_service import db_service
        
        health_status = {
            "cache": cache_manager.health_check(),
            "database": db_service.health_check(),
            "task_queue": task_queue.health_check(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        overall_healthy = all(health_status.values())
        status_code = 200 if overall_healthy else 503
        
        return jsonify({
            "status": "healthy" if overall_healthy else "unhealthy",
            "components": health_status
        }), status_code
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "error": str(e)
        }), 500


@internal_bp.route("/metrics", methods=["GET"])
def get_metrics():
    """Get comprehensive application metrics."""
    try:
        from ..cache_manager import cache_manager
        from ..monitoring import performance_monitor
        
        # Comprehensive metrics
        metrics = {
            "cache_healthy": cache_manager.health_check(),
            "performance": performance_monitor.get_dashboard_data(),
            "timestamp": datetime.utcnow().isoformat(),
            "app_version": current_app.config.get("VERSION", "unknown")
        }
        
        return jsonify(metrics), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@internal_bp.route("/dashboard", methods=["GET"])
def monitoring_dashboard():
    """Get monitoring dashboard data."""
    try:
        from ..monitoring import performance_monitor
        
        dashboard_data = performance_monitor.get_dashboard_data()
        return jsonify(dashboard_data), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@internal_bp.route("/test-alert", methods=["POST"])
def test_alert():
    """Test the production alert system. Only works in production."""
    try:
        # Only allow in production environment
        if os.environ.get('FLASK_ENV') != 'production':
            return jsonify({
                "status": "skipped",
                "message": "Test alerts only work in production environment"
            }), 200
            
        # Verify auth token
        auth_header = request.headers.get('Authorization')
        expected_token = os.environ.get('TASK_AUTH_TOKEN')
        
        if not auth_header or not expected_token:
            return jsonify({"error": "Missing authorization"}), 401
            
        if auth_header != f"Bearer {expected_token}":
            return jsonify({"error": "Invalid authorization"}), 401
        
        # Send test alert
        from ..alerts import send_critical_alert
        send_critical_alert(
            error_message="This is a test alert to verify the alerting system is working correctly.",
            error_type="ALERT SYSTEM TEST",
            extra_info="If you received this alert, the system is configured properly and will notify you of real production issues."
        )
        
        return jsonify({
            "status": "success",
            "message": "Test alert sent! Check your email and SMS."
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to send test alert: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@internal_bp.route("/firestore-usage", methods=["GET"])
def firestore_usage():
    """Get Firestore usage statistics for cost monitoring."""
    try:
        # Basic auth check - in production, use proper authentication
        auth_header = request.headers.get('Authorization')
        expected_token = os.environ.get('TASK_AUTH_TOKEN', 'dev-token')
        
        if current_app.config.get("FLASK_ENV") != "development":
            if not auth_header or auth_header != f"Bearer {expected_token}":
                return jsonify({"error": "Unauthorized"}), 401
        
        # Get Firestore usage statistics
        usage_stats = performance_monitor.metrics.get_firestore_usage_stats()
        
        # Add warnings if approaching limits
        warnings = []
        daily_reads = usage_stats.get("daily_reads", 0)
        daily_writes = usage_stats.get("daily_writes", 0)
        
        # Warn if approaching free tier limits (50K reads/day, 20K writes/day)
        if daily_reads > 40000:
            warnings.append(f"Approaching daily read limit: {daily_reads}/50,000")
        if daily_writes > 15000:
            warnings.append(f"Approaching daily write limit: {daily_writes}/20,000")
        
        # Warn if estimated cost is high
        estimated_cost = usage_stats.get("estimated_daily_cost", 0)
        if estimated_cost > 5.0:
            warnings.append(f"High daily cost detected: ${estimated_cost:.2f}")
        
        usage_stats["warnings"] = warnings
        usage_stats["timestamp"] = datetime.utcnow().isoformat()
        
        return jsonify(usage_stats), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting Firestore usage stats: {e}")
        return jsonify({"error": str(e)}), 500


