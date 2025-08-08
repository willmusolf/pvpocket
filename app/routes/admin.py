"""
Admin routes for metrics and monitoring.
"""

from flask import Blueprint, render_template, jsonify, request, current_app, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
import os
from datetime import datetime, timedelta
from ..monitoring import performance_monitor
from ..cache_manager import cache_manager
from ..db_service import db_service

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    """Decorator to require admin access."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Get admin emails from environment variable
        env_admins = os.environ.get("ADMIN_EMAILS", "")
        if not env_admins:
            # No admins configured - deny all access
            from flask import abort
            abort(404)
        
        # Parse comma-separated admin emails
        admin_emails = [email.strip() for email in env_admins.split(",") if email.strip()]
        
        # Check if current user is admin
        if not hasattr(current_user, 'email') or current_user.email not in admin_emails:
            # Return 404 instead of 403 to hide the existence of admin pages
            from flask import abort
            abort(404)
            
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route("/metrics")
@admin_required
def metrics_dashboard():
    """Admin metrics dashboard with visualizations."""
    return render_template("admin_metrics.html")


@admin_bp.route("/api/metrics/summary")
@admin_required
def metrics_summary():
    """Get summary metrics for the dashboard."""
    try:
        # Get various metrics
        health_summary = performance_monitor.metrics.get_health_summary()
        
        metrics = {
            "system_health": {
                "cache": cache_manager.health_check(),
                "database": db_service.health_check(),
                "timestamp": datetime.utcnow().isoformat()
            },
            "performance": {
                "response_times": {
                    "average": health_summary.get("avg_response_time", 0),
                    "p95": health_summary.get("p95_response_time", 0)
                },
                "active_users": health_summary.get("active_users", 0),
                "total_requests": health_summary.get("total_requests", 0),
                "top_endpoints": performance_monitor.metrics.get_top_endpoints()
            },
            "firestore_usage": performance_monitor.metrics.get_firestore_usage_stats(),
            "cache_stats": {
                "hit_rate": performance_monitor.metrics.get_cache_hit_rate(),
                "total_hits": performance_monitor.metrics.cache_stats.get("hits", 0),
                "total_misses": performance_monitor.metrics.cache_stats.get("misses", 0)
            }
        }
        
        return jsonify(metrics), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting metrics summary: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/metrics/historical/<metric_type>")
@admin_required
def metrics_historical(metric_type):
    """Get historical metrics data for charts."""
    try:
        # For now, return sample data
        # In production, you'd query from a time-series database
        hours = int(request.args.get("hours", 24))
        
        # Generate sample historical data
        now = datetime.utcnow()
        data_points = []
        
        for i in range(hours):
            timestamp = now - timedelta(hours=i)
            
            if metric_type == "response_time":
                data_points.append({
                    "timestamp": timestamp.isoformat(),
                    "avg": 150 + (i % 10) * 5,
                    "p95": 250 + (i % 10) * 10
                })
            elif metric_type == "requests":
                data_points.append({
                    "timestamp": timestamp.isoformat(),
                    "count": 1000 + (i % 20) * 50
                })
            elif metric_type == "firestore_reads":
                data_points.append({
                    "timestamp": timestamp.isoformat(),
                    "reads": 5000 + (i % 30) * 100,
                    "writes": 500 + (i % 30) * 10
                })
        
        return jsonify({"data": data_points}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting historical metrics: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/metrics/reset")
@admin_required
def reset_metrics():
    """Reset daily metrics counters (admin only)."""
    try:
        # Only allow in development
        if current_app.config.get("FLASK_ENV") != "development":
            return jsonify({"error": "Reset only allowed in development"}), 403
        
        # Reset the daily counters
        performance_monitor.metrics._check_daily_reset()
        performance_monitor.metrics.firestore_operations["total_reads_today"] = 0
        performance_monitor.metrics.firestore_operations["total_writes_today"] = 0
        performance_monitor.metrics.firestore_operations["total_deletes_today"] = 0
        performance_monitor.metrics.firestore_operations["last_reset"] = datetime.now()
        
        return jsonify({"status": "Metrics reset successfully"}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error resetting metrics: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/test-cards")
def test_cards_endpoint():
    """Rate-limit-free cards endpoint for admin testing.""" 
    # Get the limiter from current_app and exempt this route
    try:
        limiter = getattr(current_app, 'limiter', None)
        if limiter:
            # Mark this view as exempt from rate limiting
            limiter.exempt(test_cards_endpoint)
    except:
        pass  # Ignore if limiter not available
    
    # Simple test endpoint that always succeeds
    return jsonify({
        "status": "success",
        "message": "Load test endpoint working (rate limit bypassed)",
        "timestamp": datetime.utcnow().isoformat(),
        "test_data": {
            "sample_cards": [
                {"id": 1, "name": "Test Card 1", "energy_type": "Electric"},
                {"id": 2, "name": "Test Card 2", "energy_type": "Fire"},
                {"id": 3, "name": "Test Card 3", "energy_type": "Water"}
            ],
            "total_available": 3,
            "sample_size": 3
        }
    }), 200


@admin_bp.route("/dashboard")
@admin_required
def admin_dashboard():
    """Admin monitoring dashboard page."""
    return render_template("admin_dashboard.html")