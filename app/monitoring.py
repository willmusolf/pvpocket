"""
Performance monitoring and alerting system for the Pokemon TCG Pocket application.
Tracks key metrics and provides alerts for performance issues.
"""

import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import json
import os
from flask import current_app


class PerformanceMetrics:
    """Tracks performance metrics in memory."""
    
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self._lock = threading.RLock()
        
        # Metrics storage
        self.request_times = defaultdict(lambda: deque(maxlen=max_samples))
        self.error_counts = defaultdict(int)
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0
        }
        self.db_query_times = defaultdict(lambda: deque(maxlen=max_samples))
        self.active_users = set()
        self.endpoint_calls = defaultdict(int)
        
        # Firestore usage tracking for cost monitoring
        self.firestore_operations = {
            "reads": defaultdict(int),
            "writes": defaultdict(int),
            "deletes": defaultdict(int),
            "batch_reads": defaultdict(int),
            "total_reads_today": 0,
            "total_writes_today": 0,
            "total_deletes_today": 0,
            "last_reset": datetime.now()
        }
        
        # System health
        self.last_health_check = None
        self.health_status = {}
        
    def record_request_time(self, endpoint: str, duration_ms: float):
        """Record request processing time."""
        with self._lock:
            self.request_times[endpoint].append(duration_ms)
            self.endpoint_calls[endpoint] += 1
    
    def record_error(self, error_type: str):
        """Record an error occurrence."""
        with self._lock:
            self.error_counts[error_type] += 1
    
    def record_cache_hit(self, cache_type: str = "general"):
        """Record a cache hit."""
        with self._lock:
            self.cache_stats["hits"] += 1
    
    def record_cache_miss(self, cache_type: str = "general"):
        """Record a cache miss."""
        with self._lock:
            self.cache_stats["misses"] += 1
    
    def record_cache_error(self, cache_type: str = "general"):
        """Record a cache error."""
        with self._lock:
            self.cache_stats["errors"] += 1
    
    def record_db_query_time(self, query_type: str, duration_ms: float):
        """Record database query time."""
        with self._lock:
            self.db_query_times[query_type].append(duration_ms)
    
    def record_active_user(self, user_id: str):
        """Record an active user."""
        with self._lock:
            self.active_users.add(user_id)
    
    def record_firestore_read(self, collection: str, count: int = 1):
        """Record Firestore read operations."""
        with self._lock:
            # Check if we need to reset daily counters
            self._check_daily_reset()
            self.firestore_operations["reads"][collection] += count
            self.firestore_operations["total_reads_today"] += count
    
    def record_firestore_write(self, collection: str, count: int = 1):
        """Record Firestore write operations."""
        with self._lock:
            self._check_daily_reset()
            self.firestore_operations["writes"][collection] += count
            self.firestore_operations["total_writes_today"] += count
    
    def record_firestore_delete(self, collection: str, count: int = 1):
        """Record Firestore delete operations."""
        with self._lock:
            self._check_daily_reset()
            self.firestore_operations["deletes"][collection] += count
            self.firestore_operations["total_deletes_today"] += count
    
    def record_firestore_batch_read(self, collection: str, count: int):
        """Record Firestore batch read operations."""
        with self._lock:
            self._check_daily_reset()
            self.firestore_operations["batch_reads"][collection] += count
            self.firestore_operations["total_reads_today"] += count
    
    def _check_daily_reset(self):
        """Reset daily counters if it's a new day."""
        now = datetime.now()
        last_reset = self.firestore_operations["last_reset"]
        
        if now.date() > last_reset.date():
            # Reset daily counters
            self.firestore_operations["total_reads_today"] = 0
            self.firestore_operations["total_writes_today"] = 0
            self.firestore_operations["total_deletes_today"] = 0
            self.firestore_operations["last_reset"] = now
    
    def get_firestore_usage_stats(self) -> Dict[str, Any]:
        """Get Firestore usage statistics."""
        with self._lock:
            self._check_daily_reset()
            return {
                "daily_reads": self.firestore_operations["total_reads_today"],
                "daily_writes": self.firestore_operations["total_writes_today"],
                "daily_deletes": self.firestore_operations["total_deletes_today"],
                "reads_by_collection": dict(self.firestore_operations["reads"]),
                "writes_by_collection": dict(self.firestore_operations["writes"]),
                "estimated_daily_cost": self._estimate_firestore_cost()
            }
    
    def _estimate_firestore_cost(self) -> float:
        """Estimate daily Firestore cost based on usage."""
        # Firestore pricing (approximate):
        # $0.06 per 100,000 document reads
        # $0.18 per 100,000 document writes
        # $0.02 per 100,000 document deletes
        
        reads_cost = (self.firestore_operations["total_reads_today"] / 100000) * 0.06
        writes_cost = (self.firestore_operations["total_writes_today"] / 100000) * 0.18
        deletes_cost = (self.firestore_operations["total_deletes_today"] / 100000) * 0.02
        
        return round(reads_cost + writes_cost + deletes_cost, 4)
    
    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_stats["hits"] + self.cache_stats["misses"]
        if total == 0:
            return 0.0
        return (self.cache_stats["hits"] / total) * 100
    
    def get_average_response_time(self, endpoint: str = None) -> float:
        """Get average response time for endpoint or overall."""
        with self._lock:
            if endpoint:
                times = list(self.request_times[endpoint])
                return statistics.mean(times) if times else 0.0
            
            all_times = []
            for times in self.request_times.values():
                all_times.extend(times)
            
            return statistics.mean(all_times) if all_times else 0.0
    
    def get_p95_response_time(self, endpoint: str = None) -> float:
        """Get 95th percentile response time."""
        with self._lock:
            if endpoint:
                times = list(self.request_times[endpoint])
            else:
                all_times = []
                for times in self.request_times.values():
                    all_times.extend(times)
                times = all_times
            
            if not times:
                return 0.0
            
            times.sort()
            index = int(0.95 * len(times))
            return times[index] if index < len(times) else times[-1]
    
    def get_active_user_count(self) -> int:
        """Get count of active users."""
        return len(self.active_users)
    
    def get_error_rate(self) -> Dict[str, int]:
        """Get error counts by type."""
        with self._lock:
            return dict(self.error_counts)
    
    def get_top_endpoints(self, limit: int = 10) -> List[tuple]:
        """Get most called endpoints."""
        with self._lock:
            sorted_endpoints = sorted(self.endpoint_calls.items(), 
                                    key=lambda x: x[1], reverse=True)
            return sorted_endpoints[:limit]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary."""
        return {
            "avg_response_time": round(self.get_average_response_time(), 2),
            "p95_response_time": round(self.get_p95_response_time(), 2),
            "cache_hit_rate": round(self.get_cache_hit_rate(), 2),
            "active_users": self.get_active_user_count(),
            "total_requests": sum(self.endpoint_calls.values()),
            "error_rate": self.get_error_rate(),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def reset_periodic_metrics(self):
        """Reset metrics that should be cleared periodically."""
        with self._lock:
            self.active_users.clear()  # Reset active users count


class AlertManager:
    """Manages alerts for performance issues."""
    
    def __init__(self):
        self.alert_thresholds = {
            "response_time_ms": 5000,  # 5 seconds
            "error_rate": 5.0,  # 5% error rate
            "cache_hit_rate": 70.0,  # Below 70% hit rate
            "memory_usage_mb": 1024,  # 1GB memory usage
            "daily_cost_usd": 2.0,  # $2 daily cost threshold
            "hourly_cost_usd": 0.2,  # $0.20 hourly cost spike threshold
            "daily_reads": 10000,  # 10k reads per day warning
            "hourly_reads": 1000,  # 1k reads per hour spike warning
        }
        self.active_alerts = {}
        self.alert_cooldown = timedelta(minutes=15)  # Don't spam alerts
        self.cost_tracking = {
            "hourly_reads": deque(maxlen=24),  # Track reads per hour for 24 hours
            "hourly_costs": deque(maxlen=24),  # Track costs per hour for 24 hours
            "last_hour_check": datetime.now().replace(minute=0, second=0, microsecond=0),
            "current_hour_reads": 0,
            "current_hour_cost": 0.0
        }
    
    def check_alerts(self, metrics: PerformanceMetrics):
        """Check for alert conditions."""
        alerts = []
        current_time = datetime.utcnow()
        
        # Update hourly cost tracking
        self._update_hourly_tracking(metrics)
        
        # Check Firestore cost alerts
        cost_alerts = self._check_cost_alerts(metrics, current_time)
        alerts.extend(cost_alerts)
        
        # Check response time
        avg_response = metrics.get_average_response_time()
        if avg_response > self.alert_thresholds["response_time_ms"]:
            alert_key = "high_response_time"
            if self._should_alert(alert_key, current_time):
                alerts.append({
                    "type": "high_response_time",
                    "message": f"High average response time: {avg_response:.2f}ms",
                    "severity": "warning",
                    "timestamp": current_time.isoformat()
                })
        
        # Check cache hit rate
        hit_rate = metrics.get_cache_hit_rate()
        if hit_rate < self.alert_thresholds["cache_hit_rate"]:
            alert_key = "low_cache_hit_rate"
            if self._should_alert(alert_key, current_time):
                alerts.append({
                    "type": "low_cache_hit_rate",
                    "message": f"Low cache hit rate: {hit_rate:.2f}%",
                    "severity": "warning",
                    "timestamp": current_time.isoformat()
                })
        
        # Check error rate
        error_counts = metrics.get_error_rate()
        total_requests = sum(metrics.endpoint_calls.values())
        if total_requests > 0:
            total_errors = sum(error_counts.values())
            error_rate = (total_errors / total_requests) * 100
            
            if error_rate > self.alert_thresholds["error_rate"]:
                alert_key = "high_error_rate"
                if self._should_alert(alert_key, current_time):
                    alerts.append({
                        "type": "high_error_rate",
                        "message": f"High error rate: {error_rate:.2f}%",
                        "severity": "critical",
                        "timestamp": current_time.isoformat()
                    })
        
        return alerts
    
    def _should_alert(self, alert_key: str, current_time: datetime) -> bool:
        """Check if we should send an alert (respect cooldown)."""
        last_alert = self.active_alerts.get(alert_key)
        if not last_alert:
            self.active_alerts[alert_key] = current_time
            return True
        
        if current_time - last_alert > self.alert_cooldown:
            self.active_alerts[alert_key] = current_time
            return True
        
        return False
    
    def _update_hourly_tracking(self, metrics: PerformanceMetrics):
        """Update hourly cost and read tracking."""
        current_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Check if we need to roll over to a new hour
        if current_time > self.cost_tracking["last_hour_check"]:
            # Save the completed hour's data
            if self.cost_tracking["current_hour_reads"] > 0 or self.cost_tracking["current_hour_cost"] > 0:
                self.cost_tracking["hourly_reads"].append(self.cost_tracking["current_hour_reads"])
                self.cost_tracking["hourly_costs"].append(self.cost_tracking["current_hour_cost"])
            
            # Reset for new hour
            self.cost_tracking["current_hour_reads"] = 0
            self.cost_tracking["current_hour_cost"] = 0.0
            self.cost_tracking["last_hour_check"] = current_time
        
        # Add current metrics to running totals
        usage_stats = metrics.get_firestore_usage_stats()
        self.cost_tracking["current_hour_cost"] = usage_stats["estimated_daily_cost"]
        self.cost_tracking["current_hour_reads"] = usage_stats["daily_reads"]
    
    def _check_cost_alerts(self, metrics: PerformanceMetrics, current_time: datetime) -> list:
        """Check for cost-related alerts."""
        alerts = []
        usage_stats = metrics.get_firestore_usage_stats()
        
        # Daily cost threshold alert
        daily_cost = usage_stats["estimated_daily_cost"]
        if daily_cost > self.alert_thresholds["daily_cost_usd"]:
            alert_key = "high_daily_cost"
            if self._should_alert(alert_key, current_time):
                alerts.append({
                    "type": "high_daily_cost",
                    "message": f"High daily Firestore cost: ${daily_cost:.2f} (threshold: ${self.alert_thresholds['daily_cost_usd']:.2f})",
                    "severity": "critical",
                    "timestamp": current_time.isoformat(),
                    "cost_details": {
                        "daily_reads": usage_stats["daily_reads"],
                        "daily_writes": usage_stats["daily_writes"],
                        "reads_by_collection": usage_stats["reads_by_collection"]
                    }
                })
        
        # Daily reads threshold alert (early warning)
        daily_reads = usage_stats["daily_reads"]
        if daily_reads > self.alert_thresholds["daily_reads"]:
            alert_key = "high_daily_reads"
            if self._should_alert(alert_key, current_time):
                alerts.append({
                    "type": "high_daily_reads",
                    "message": f"High daily Firestore reads: {daily_reads:,} (threshold: {self.alert_thresholds['daily_reads']:,})",
                    "severity": "warning",
                    "timestamp": current_time.isoformat(),
                    "cost_details": {
                        "estimated_cost": daily_cost,
                        "reads_by_collection": usage_stats["reads_by_collection"]
                    }
                })
        
        # Hourly spike detection (if we have historical data)
        if len(self.cost_tracking["hourly_reads"]) > 1:
            recent_avg = sum(list(self.cost_tracking["hourly_reads"])[-3:]) / min(3, len(self.cost_tracking["hourly_reads"]))
            current_hour = self.cost_tracking["current_hour_reads"]
            
            # Alert if current hour is 3x higher than recent average
            if current_hour > recent_avg * 3 and current_hour > self.alert_thresholds["hourly_reads"]:
                alert_key = "read_spike"
                if self._should_alert(alert_key, current_time):
                    alerts.append({
                        "type": "read_spike",
                        "message": f"Unusual Firestore read spike: {current_hour:,} reads this hour (avg: {recent_avg:.0f})",
                        "severity": "warning",
                        "timestamp": current_time.isoformat(),
                        "cost_details": {
                            "hourly_reads": current_hour,
                            "recent_average": recent_avg,
                            "reads_by_collection": usage_stats["reads_by_collection"]
                        }
                    })
        
        return alerts
    
    def get_cost_trends(self) -> dict:
        """Get cost trend data for monitoring dashboard."""
        return {
            "hourly_reads": list(self.cost_tracking["hourly_reads"]),
            "hourly_costs": list(self.cost_tracking["hourly_costs"]),
            "current_hour_reads": self.cost_tracking["current_hour_reads"],
            "current_hour_cost": self.cost_tracking["current_hour_cost"],
            "trend_direction": self._calculate_cost_trend()
        }
    
    def _calculate_cost_trend(self) -> str:
        """Calculate if costs are trending up, down, or stable."""
        if len(self.cost_tracking["hourly_costs"]) < 3:
            return "insufficient_data"
        
        recent_costs = list(self.cost_tracking["hourly_costs"])[-3:]
        if recent_costs[-1] > recent_costs[-2] > recent_costs[-3]:
            return "increasing"
        elif recent_costs[-1] < recent_costs[-2] < recent_costs[-3]:
            return "decreasing" 
        else:
            return "stable"


class PerformanceMonitor:
    """Main performance monitoring coordinator."""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.alert_manager = AlertManager()
        self._monitoring_thread = None
        self._running = False
    
    def start_monitoring(self, interval_seconds: int = 60):
        """Start background monitoring thread."""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            return
        
        self._running = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop, 
            args=(interval_seconds,),
            daemon=True
        )
        self._monitoring_thread.start()
        # Only log monitor start in main process
        if os.environ.get('WERKZEUG_RUN_MAIN'):
            print("✅ MONITOR: Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring thread."""
        self._running = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        print("Performance monitoring stopped")
    
    def _monitoring_loop(self, interval_seconds: int):
        """Main monitoring loop."""
        while self._running:
            try:
                # Check for alerts
                alerts = self.alert_manager.check_alerts(self.metrics)
                
                # Log alerts and send critical alerts to external systems
                for alert in alerts:
                    severity = alert.get('severity', 'info')
                    message = alert.get('message', 'Unknown alert')
                    alert_type = alert.get('type', 'general')
                    
                    try:
                        if severity == 'critical':
                            current_app.logger.error(f"🚨 ALERT [{alert_type.upper()}]: {message}")
                            # Send critical cost alerts via email/SMS
                            self._send_critical_cost_alert(alert)
                        elif severity == 'warning':
                            current_app.logger.warning(f"⚠️ ALERT [{alert_type.upper()}]: {message}")
                        else:
                            current_app.logger.info(f"ℹ️ ALERT [{alert_type.upper()}]: {message}")
                    except RuntimeError:
                        # No Flask context available - suppress alerts during startup
                        # Only print critical alerts
                        if severity == 'critical':
                            print(f"ALERT [{severity.upper()}] [{alert_type.upper()}]: {message}")
                
                # Reset periodic metrics
                self.metrics.reset_periodic_metrics()
                
                # Wait for next interval
                time.sleep(interval_seconds)
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(interval_seconds)  # Continue monitoring even on error
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard."""
        return {
            "health_summary": self.metrics.get_health_summary(),
            "top_endpoints": self.metrics.get_top_endpoints(),
            "cache_stats": self.metrics.cache_stats,
            "active_alerts": len(self.alert_manager.active_alerts),
            "cost_trends": self.alert_manager.get_cost_trends()
        }
    
    def _send_critical_cost_alert(self, alert: dict):
        """Send critical cost alerts via external alerting system."""
        try:
            from app.alerts import alert_high_firestore_cost, alert_firestore_read_spike
            
            alert_type = alert.get('type')
            cost_details = alert.get('cost_details', {})
            
            if alert_type == 'high_daily_cost':
                alert_high_firestore_cost(
                    daily_cost=cost_details.get('daily_reads', 0) / 100000 * 0.06,  # Recalculate cost
                    daily_reads=cost_details.get('daily_reads', 0),
                    reads_by_collection=cost_details.get('reads_by_collection', {})
                )
            elif alert_type == 'read_spike':
                alert_firestore_read_spike(
                    hourly_reads=cost_details.get('hourly_reads', 0),
                    recent_avg=cost_details.get('recent_average', 0),
                    reads_by_collection=cost_details.get('reads_by_collection', {})
                )
        except Exception as e:
            print(f"Failed to send critical cost alert: {e}")


# Global monitor instance
performance_monitor = PerformanceMonitor()


def track_request_time(endpoint: str):
    """Decorator to track request processing time."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = (time.time() - start_time) * 1000  # Convert to milliseconds
                performance_monitor.metrics.record_request_time(endpoint, duration)
        return wrapper
    return decorator


def track_db_query_time(query_type: str):
    """Decorator to track database query time."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                performance_monitor.metrics.record_error(f"db_error_{query_type}")
                raise
            finally:
                duration = (time.time() - start_time) * 1000
                performance_monitor.metrics.record_db_query_time(query_type, duration)
        return wrapper
    return decorator