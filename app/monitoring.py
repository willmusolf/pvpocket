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
        }
        self.active_alerts = {}
        self.alert_cooldown = timedelta(minutes=15)  # Don't spam alerts
    
    def check_alerts(self, metrics: PerformanceMetrics):
        """Check for alert conditions."""
        alerts = []
        current_time = datetime.utcnow()
        
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
                
                # Log alerts (in production, send to alerting system)
                for alert in alerts:
                    severity = alert.get('severity', 'info')
                    message = alert.get('message', 'Unknown alert')
                    alert_type = alert.get('type', 'general')
                    
                    try:
                        if severity == 'critical':
                            current_app.logger.error(f"🚨 ALERT [{alert_type.upper()}]: {message}")
                        elif severity == 'warning':
                            current_app.logger.warning(f"⚠️ ALERT [{alert_type.upper()}]: {message}")
                        else:
                            current_app.logger.info(f"ℹ️ ALERT [{alert_type.upper()}]: {message}")
                    except RuntimeError:
                        # No Flask context available, use print as fallback
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
            "active_alerts": len(self.alert_manager.active_alerts)
        }


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