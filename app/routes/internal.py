"""
Internal routes for handling background tasks and system operations.
These endpoints are used by Cloud Tasks and other internal services.
"""

from flask import Blueprint, request, jsonify, current_app
import json
from datetime import datetime
from ..task_queue import task_queue


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
    return jsonify({"status": "ok"}), 200


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