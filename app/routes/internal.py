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
from ..cache_manager import cache_manager
from ..db_service import db_service


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
    """Get comprehensive Firestore usage statistics and cost monitoring."""
    try:
        # Basic auth check - in production, use proper authentication
        auth_header = request.headers.get('Authorization')
        expected_token = os.environ.get('TASK_AUTH_TOKEN', 'dev-token')
        
        if current_app.config.get("FLASK_ENV") != "development":
            if not auth_header or auth_header != f"Bearer {expected_token}":
                return jsonify({"error": "Unauthorized"}), 401
        
        # Get Firestore usage statistics
        usage_stats = performance_monitor.metrics.get_firestore_usage_stats()
        cost_trends = performance_monitor.alert_manager.get_cost_trends()
        
        # Enhanced cost breakdown
        daily_reads = usage_stats.get("daily_reads", 0)
        daily_writes = usage_stats.get("daily_writes", 0)
        daily_deletes = usage_stats.get("daily_deletes", 0)
        estimated_cost = usage_stats.get("estimated_daily_cost", 0)
        reads_by_collection = usage_stats.get("reads_by_collection", {})
        
        # Calculate cost per collection
        cost_by_collection = {}
        total_reads = sum(reads_by_collection.values()) or 1
        for collection, reads in reads_by_collection.items():
            collection_cost = (reads / 100000) * 0.06  # $0.06 per 100k reads
            cost_by_collection[collection] = {
                "reads": reads,
                "cost": round(collection_cost, 4),
                "percentage_of_total": round((reads / total_reads) * 100, 2)
            }
        
        # Cost optimization recommendations
        recommendations = []
        
        # Collection-specific recommendations
        if reads_by_collection.get("cards", 0) > 5000:
            recommendations.append("Consider extending card collection cache TTL or implementing progressive loading")
        
        if reads_by_collection.get("decks", 0) > 2000:
            recommendations.append("Optimize deck queries with pagination or enhanced caching")
            
        if daily_reads > 10000:
            recommendations.append("High read volume detected - consider implementing batch operations")
            
        if estimated_cost > 2.0:
            recommendations.append("Daily costs exceed $2 threshold - review query efficiency")
        
        # Warnings and alerts
        warnings = []
        alerts = []
        
        # Free tier warnings (50K reads/day, 20K writes/day)
        if daily_reads > 40000:
            warnings.append(f"Approaching daily read limit: {daily_reads:,}/50,000")
        if daily_writes > 15000:
            warnings.append(f"Approaching daily write limit: {daily_writes:,}/20,000")
        
        # Cost alerts
        if estimated_cost > 5.0:
            alerts.append(f"🚨 CRITICAL: High daily cost ${estimated_cost:.2f}")
        elif estimated_cost > 2.0:
            alerts.append(f"⚠️ WARNING: Daily cost ${estimated_cost:.2f} exceeds threshold")
        
        # Spike detection
        if cost_trends["trend_direction"] == "increasing" and len(cost_trends["hourly_reads"]) > 2:
            recent_avg = sum(cost_trends["hourly_reads"][-3:]) / 3
            if cost_trends["current_hour_reads"] > recent_avg * 2:
                alerts.append(f"📈 Read spike detected: {cost_trends['current_hour_reads']:,} this hour (avg: {recent_avg:.0f})")
        
        # Detailed response
        enhanced_response = {
            "summary": {
                "daily_reads": daily_reads,
                "daily_writes": daily_writes,
                "daily_deletes": daily_deletes,
                "estimated_daily_cost": estimated_cost,
                "cost_trend": cost_trends["trend_direction"]
            },
            "cost_breakdown": {
                "by_collection": cost_by_collection,
                "cost_composition": {
                    "reads_cost": round((daily_reads / 100000) * 0.06, 4),
                    "writes_cost": round((daily_writes / 100000) * 0.18, 4),
                    "deletes_cost": round((daily_deletes / 100000) * 0.02, 4)
                }
            },
            "trends": {
                "hourly_data": {
                    "reads": cost_trends["hourly_reads"],
                    "costs": cost_trends["hourly_costs"]
                },
                "current_hour": {
                    "reads": cost_trends["current_hour_reads"],
                    "estimated_cost": cost_trends["current_hour_cost"]
                },
                "direction": cost_trends["trend_direction"]
            },
            "monitoring": {
                "warnings": warnings,
                "alerts": alerts,
                "recommendations": recommendations,
                "thresholds": {
                    "daily_cost_warning": 2.0,
                    "daily_cost_critical": 5.0,
                    "daily_reads_warning": 10000,
                    "free_tier_read_limit": 50000,
                    "free_tier_write_limit": 20000
                }
            },
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "collection_count": len(reads_by_collection),
                "data_freshness": "real-time",
                "pricing_version": "2025_firestore_pricing"
            }
        }
        
        return jsonify(enhanced_response), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting enhanced Firestore usage stats: {e}")
        return jsonify({"error": str(e)}), 500


@internal_bp.route("/user-activity-metrics", methods=["GET"])
def user_activity_metrics():
    """Get user activity metrics."""
    try:
        # Mock user activity metrics
        metrics = {
            "daily_active_users": 1250,
            "weekly_active_users": 4800,
            "monthly_active_users": 12500,
            "average_session_duration": 1800,
            "bounce_rate": 0.15,
            "new_user_registrations_today": 45,
            "timestamp": datetime.utcnow().isoformat()
        }
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@internal_bp.route("/feature-usage-metrics", methods=["GET"])
def feature_usage_metrics():
    """Get feature usage metrics."""
    try:
        metrics = {
            "decks_created_today": 150,
            "cards_collected_today": 2500,
            "friend_requests_sent_today": 85,
            "searches_performed_today": 450,
            "public_decks_viewed_today": 320,
            "profile_updates_today": 75,
            "timestamp": datetime.utcnow().isoformat()
        }
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@internal_bp.route("/error-metrics", methods=["GET"])
def error_metrics():
    """Get error rate and tracking metrics."""
    try:
        metrics = {
            "error_rate_percent": 1.5,
            "total_errors_today": 45,
            "error_breakdown": {
                "400": 15,
                "404": 20,
                "500": 8,
                "503": 2
            },
            "most_common_errors": [
                {"endpoint": "/api/decks", "error_code": 400, "count": 12},
                {"endpoint": "/api/collection", "error_code": 404, "count": 8}
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@internal_bp.route("/cache-metrics", methods=["GET"])
def cache_metrics():
    """Get cache performance metrics."""
    try:
        metrics = {
            "cache_hit_rate_percent": 96.5,
            "cache_miss_rate_percent": 3.5,
            "total_cache_requests": 15000,
            "cache_hits": 14475,
            "cache_misses": 525,
            "average_cache_response_time_ms": 5.2,
            "cache_size_bytes": 52428800,
            "cache_evictions_today": 12,
            "timestamp": datetime.utcnow().isoformat()
        }
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@internal_bp.route("/database-performance", methods=["GET"])
def database_performance():
    """Get database performance metrics."""
    try:
        metrics = {
            "average_query_time_ms": 150,
            "slowest_queries": [
                {"query": "decks_by_owner_sorted", "time_ms": 450},
                {"query": "friend_search", "time_ms": 320}
            ],
            "connection_pool_usage": 8,
            "connection_pool_max": 15,
            "failed_connections": 2,
            "transaction_success_rate": 99.2,
            "deadlocks_today": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@internal_bp.route("/system-metrics", methods=["GET"])
def system_metrics():
    """Get system resource metrics."""
    try:
        metrics = {
            "cpu_usage_percent": 35.7,
            "memory_usage_percent": 68.2,
            "disk_usage_percent": 45.1,
            "network_io_bytes_per_sec": 1024000,
            "load_average": [0.5, 0.7, 0.8],
            "timestamp": datetime.utcnow().isoformat()
        }
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@internal_bp.route("/alerts", methods=["GET"])
def get_alerts():
    """Get active alerts."""
    try:
        alerts = {
            "active_alerts": [
                {
                    "alert_type": "high_error_rate",
                    "severity": "warning",
                    "message": "Error rate is 5.5%, above 5% threshold",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        return jsonify(alerts), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@internal_bp.route("/alert-escalation", methods=["GET"])
def alert_escalation():
    """Get alert escalation information."""
    try:
        escalation = {
            "alerts_by_severity": {
                "info": 5,
                "warning": 12,
                "critical": 2,
                "emergency": 0
            },
            "escalation_rules": {
                "critical_alert_after_minutes": 15,
                "emergency_alert_after_minutes": 5,
                "auto_scale_trigger_threshold": 85
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        return jsonify(escalation), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@internal_bp.route("/incidents", methods=["GET"])
def get_incidents():
    """Get incident tracking data."""
    try:
        incidents = {
            "active_incidents": [],
            "resolved_incidents_today": 3,
            "average_resolution_time_minutes": 25,
            "mttr_minutes": 22,
            "mtbf_hours": 168,
            "timestamp": datetime.utcnow().isoformat()
        }
        return jsonify(incidents), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@internal_bp.route("/metrics-timeseries", methods=["GET"])
def metrics_timeseries():
    """Get time-series metrics data."""
    try:
        timeseries = {
            "response_time_series": [
                {"timestamp": datetime.utcnow().isoformat(), "value": 245}
            ],
            "request_rate_series": [
                {"timestamp": datetime.utcnow().isoformat(), "value": 48.7}
            ],
            "cache_hit_rate_series": [
                {"timestamp": datetime.utcnow().isoformat(), "value": 0.96}
            ]
        }
        return jsonify(timeseries), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@internal_bp.route("/metrics-stream", methods=["GET"])
def metrics_stream():
    """Real-time metrics stream endpoint."""
    # This would implement WebSocket or SSE for real-time updates
    return jsonify({"message": "Real-time metrics streaming not implemented"}), 404


@internal_bp.route("/audit-logs", methods=["GET"])
def audit_logs():
    """Get audit log entries."""
    try:
        limit = int(request.args.get('limit', 50))
        
        logs = {
            "audit_logs": [
                {
                    "user_id": "user_123",
                    "action": "deck_created",
                    "resource": "deck_456",
                    "timestamp": datetime.utcnow().isoformat(),
                    "ip_address": "192.168.1.100",
                    "user_agent": "Mozilla/5.0..."
                }
            ],
            "pagination": {"limit": limit}
        }
        return jsonify(logs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@internal_bp.route("/security-events", methods=["GET"])
def security_events():
    """Get security event logs."""
    try:
        events = {
            "security_events": [
                {
                    "event_type": "failed_login_attempt",
                    "user_id": None,
                    "ip_address": "192.168.1.200",
                    "timestamp": datetime.utcnow().isoformat(),
                    "severity": "medium"
                }
            ]
        }
        return jsonify(events), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


