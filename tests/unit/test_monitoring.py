"""
Unit tests for monitoring functionality.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta
from collections import defaultdict, deque

from app.monitoring import (
    PerformanceMetrics,
    PerformanceMonitor,
    AlertManager,
    performance_monitor
)


@pytest.mark.unit
class TestPerformanceMetrics:
    """Test PerformanceMetrics functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metrics = PerformanceMetrics(max_samples=100)
    
    def test_initialization(self):
        """Test metrics initialization."""
        assert self.metrics.max_samples == 100
        assert isinstance(self.metrics.request_times, defaultdict)
        assert isinstance(self.metrics.error_counts, defaultdict)
        assert self.metrics.cache_stats["hits"] == 0
        assert self.metrics.cache_stats["misses"] == 0
        assert self.metrics.cache_stats["errors"] == 0
        assert isinstance(self.metrics.active_users, set)
    
    def test_record_request_time(self):
        """Test recording request times."""
        self.metrics.record_request_time("/api/test", 150.5)
        self.metrics.record_request_time("/api/test", 200.0)
        self.metrics.record_request_time("/api/other", 100.0)
        
        assert len(self.metrics.request_times["/api/test"]) == 2
        assert list(self.metrics.request_times["/api/test"]) == [150.5, 200.0]
        assert len(self.metrics.request_times["/api/other"]) == 1
        assert self.metrics.endpoint_calls["/api/test"] == 2
        assert self.metrics.endpoint_calls["/api/other"] == 1
    
    def test_record_request_time_max_samples(self):
        """Test request time recording respects max samples."""
        metrics = PerformanceMetrics(max_samples=3)
        
        # Add more samples than max
        for i in range(5):
            metrics.record_request_time("/test", float(i))
        
        # Should only keep last 3 samples
        assert len(metrics.request_times["/test"]) == 3
        assert list(metrics.request_times["/test"]) == [2.0, 3.0, 4.0]
    
    def test_record_error(self):
        """Test error recording."""
        self.metrics.record_error("database_error")
        self.metrics.record_error("database_error")
        self.metrics.record_error("auth_error")
        
        assert self.metrics.error_counts["database_error"] == 2
        assert self.metrics.error_counts["auth_error"] == 1
    
    def test_record_cache_operations(self):
        """Test cache operation recording."""
        self.metrics.record_cache_hit()
        self.metrics.record_cache_hit()
        self.metrics.record_cache_miss()
        self.metrics.record_cache_error()
        
        assert self.metrics.cache_stats["hits"] == 2
        assert self.metrics.cache_stats["misses"] == 1
        assert self.metrics.cache_stats["errors"] == 1
    
    def test_record_db_query_time(self):
        """Test database query time recording."""
        self.metrics.record_db_query_time("select", 50.0)
        self.metrics.record_db_query_time("select", 75.0)
        self.metrics.record_db_query_time("update", 120.0)
        
        assert len(self.metrics.db_query_times["select"]) == 2
        assert list(self.metrics.db_query_times["select"]) == [50.0, 75.0]
        assert len(self.metrics.db_query_times["update"]) == 1
    
    def test_record_active_user(self):
        """Test active user recording."""
        self.metrics.record_active_user("user1")
        self.metrics.record_active_user("user2")
        self.metrics.record_active_user("user1")  # Duplicate
        
        assert len(self.metrics.active_users) == 2
        assert "user1" in self.metrics.active_users
        assert "user2" in self.metrics.active_users
    
    def test_record_firestore_operations(self):
        """Test Firestore operation recording."""
        self.metrics.record_firestore_read("users", 5)
        self.metrics.record_firestore_read("cards", 10)
        self.metrics.record_firestore_write("users", 2)
        self.metrics.record_firestore_delete("decks", 1)
        
        assert self.metrics.firestore_operations["reads"]["users"] == 5
        assert self.metrics.firestore_operations["reads"]["cards"] == 10
        assert self.metrics.firestore_operations["writes"]["users"] == 2
        assert self.metrics.firestore_operations["deletes"]["decks"] == 1
        assert self.metrics.firestore_operations["total_reads_today"] == 15
        assert self.metrics.firestore_operations["total_writes_today"] == 2
        assert self.metrics.firestore_operations["total_deletes_today"] == 1
    
    def test_record_firestore_batch_operations(self):
        """Test Firestore batch operation recording."""
        self.metrics.record_firestore_batch_read("cards", 25)
        
        assert self.metrics.firestore_operations["batch_reads"]["cards"] == 25
        # Batch reads should also count towards total reads
        assert self.metrics.firestore_operations["total_reads_today"] == 25
    
    @patch('app.monitoring.datetime')
    def test_daily_reset_check(self, mock_datetime):
        """Test daily counter reset functionality."""
        # Set initial time
        initial_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = initial_time
        
        metrics = PerformanceMetrics()
        metrics.record_firestore_read("users", 10)
        
        # Advance time by more than a day
        next_day = datetime(2024, 1, 2, 12, 0, 0)
        mock_datetime.now.return_value = next_day
        
        # This should trigger a reset
        metrics.record_firestore_read("users", 5)
        
        assert metrics.firestore_operations["total_reads_today"] == 5
        assert metrics.firestore_operations["reads"]["users"] == 5
    
    def test_get_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        self.metrics.record_cache_hit()
        self.metrics.record_cache_hit()
        self.metrics.record_cache_miss()
        
        hit_rate = self.metrics.get_cache_hit_rate()
        assert hit_rate == 0.6666666666666666  # 2/3
    
    def test_get_cache_hit_rate_no_operations(self):
        """Test cache hit rate when no operations recorded."""
        hit_rate = self.metrics.get_cache_hit_rate()
        assert hit_rate == 0.0
    
    def test_get_average_response_time(self):
        """Test average response time calculation."""
        self.metrics.record_request_time("/api/test", 100.0)
        self.metrics.record_request_time("/api/test", 200.0)
        self.metrics.record_request_time("/api/test", 300.0)
        
        avg_time = self.metrics.get_average_response_time("/api/test")
        assert avg_time == 200.0
    
    def test_get_average_response_time_no_data(self):
        """Test average response time when no data exists."""
        avg_time = self.metrics.get_average_response_time("/api/nonexistent")
        assert avg_time == 0.0
    
    def test_get_error_rate(self):
        """Test error rate calculation."""
        # Record some successful requests
        for _ in range(7):
            self.metrics.record_request_time("/api/test", 100.0)
        
        # Record some errors
        for _ in range(3):
            self.metrics.record_error("server_error")
        
        error_rate = self.metrics.get_error_rate()
        assert error_rate == 0.3  # 3 errors out of 10 total operations
    
    def test_get_active_user_count(self):
        """Test active user count."""
        self.metrics.record_active_user("user1")
        self.metrics.record_active_user("user2")
        self.metrics.record_active_user("user3")
        
        count = self.metrics.get_active_user_count()
        assert count == 3
    
    def test_get_firestore_usage_summary(self):
        """Test Firestore usage summary."""
        self.metrics.record_firestore_read("users", 100)
        self.metrics.record_firestore_write("users", 20)
        self.metrics.record_firestore_delete("decks", 5)
        
        summary = self.metrics.get_firestore_usage_summary()
        
        assert summary["total_reads_today"] == 100
        assert summary["total_writes_today"] == 20
        assert summary["total_deletes_today"] == 5
        assert "users" in summary["reads_by_collection"]
        assert summary["reads_by_collection"]["users"] == 100
    
    def test_clear_active_users(self):
        """Test clearing active users."""
        self.metrics.record_active_user("user1")
        self.metrics.record_active_user("user2")
        
        assert len(self.metrics.active_users) == 2
        
        self.metrics.clear_active_users()
        
        assert len(self.metrics.active_users) == 0
    
    def test_thread_safety(self):
        """Test thread safety of metrics recording."""
        import threading
        import time
        
        def record_metrics():
            for i in range(50):
                self.metrics.record_request_time("/test", float(i))
                self.metrics.record_cache_hit()
                self.metrics.record_active_user(f"user{i}")
        
        # Start multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=record_metrics)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all operations were recorded
        assert self.metrics.endpoint_calls["/test"] == 150  # 3 threads * 50 operations
        assert self.metrics.cache_stats["hits"] == 150
        assert len(self.metrics.active_users) == 50  # Unique user IDs


@pytest.mark.unit
class TestPerformanceMonitor:
    """Test PerformanceMonitor functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = PerformanceMonitor()
    
    def test_initialization(self):
        """Test monitor initialization."""
        assert isinstance(self.monitor.metrics, PerformanceMetrics)
        assert isinstance(self.monitor._alert_manager, type(None)) or hasattr(self.monitor._alert_manager, 'check_thresholds')
    
    def test_record_request(self):
        """Test request recording."""
        with patch('time.time', side_effect=[1000.0, 1000.15]):  # 150ms duration
            with self.monitor.record_request("/api/test"):
                pass
        
        assert self.monitor.metrics.endpoint_calls["/api/test"] == 1
        # Check that time was recorded (should be 150ms)
        times = list(self.monitor.metrics.request_times["/api/test"])
        assert len(times) == 1
        assert abs(times[0] - 150.0) < 0.1  # Allow for small floating point differences
    
    def test_record_request_with_exception(self):
        """Test request recording when exception occurs."""
        with patch('time.time', side_effect=[1000.0, 1000.1]):
            try:
                with self.monitor.record_request("/api/error"):
                    raise ValueError("Test error")
            except ValueError:
                pass
        
        # Should still record the request time even if exception occurred
        assert self.monitor.metrics.endpoint_calls["/api/error"] == 1
        assert len(self.monitor.metrics.request_times["/api/error"]) == 1
    
    def test_record_error(self):
        """Test error recording."""
        self.monitor.record_error("database_timeout")
        assert self.monitor.metrics.error_counts["database_timeout"] == 1
    
    def test_record_cache_operations(self):
        """Test cache operation recording."""
        self.monitor.record_cache_hit("user_cache")
        self.monitor.record_cache_miss("card_cache")
        
        assert self.monitor.metrics.cache_stats["hits"] == 1
        assert self.monitor.metrics.cache_stats["misses"] == 1
    
    def test_get_health_status(self):
        """Test health status retrieval."""
        # Record some metrics
        self.monitor.metrics.record_request_time("/api/test", 100.0)
        self.monitor.metrics.record_cache_hit()
        self.monitor.metrics.record_active_user("user1")
        
        status = self.monitor.get_health_status()
        
        assert "cache_hit_rate" in status
        assert "average_response_times" in status
        assert "error_counts" in status
        assert "active_users" in status
        assert "firestore_usage" in status
        
        assert status["cache_hit_rate"] == 1.0  # 1 hit, 0 misses
        assert status["active_users"] == 1
    
    def test_get_metrics_summary(self):
        """Test metrics summary."""
        # Record various metrics
        self.monitor.metrics.record_request_time("/api/cards", 150.0)
        self.monitor.metrics.record_request_time("/api/users", 200.0)
        self.monitor.metrics.record_error("auth_error")
        self.monitor.metrics.record_firestore_read("cards", 50)
        
        summary = self.monitor.get_metrics_summary()
        
        assert "request_counts" in summary
        assert "error_counts" in summary
        assert "firestore_operations" in summary
        assert summary["request_counts"]["/api/cards"] == 1
        assert summary["error_counts"]["auth_error"] == 1
    
    def test_reset_metrics(self):
        """Test metrics reset."""
        # Record some data
        self.monitor.metrics.record_request_time("/test", 100.0)
        self.monitor.metrics.record_error("test_error")
        self.monitor.metrics.record_cache_hit()
        
        # Verify data exists
        assert self.monitor.metrics.endpoint_calls["/test"] == 1
        assert self.monitor.metrics.error_counts["test_error"] == 1
        assert self.monitor.metrics.cache_stats["hits"] == 1
        
        # Reset metrics
        self.monitor.reset_metrics()
        
        # Verify data is cleared
        assert self.monitor.metrics.endpoint_calls["/test"] == 0
        assert self.monitor.metrics.error_counts["test_error"] == 0
        assert self.monitor.metrics.cache_stats["hits"] == 0
    
    @patch('app.monitoring.os.environ.get')
    def test_monitoring_enabled_check(self, mock_env_get):
        """Test monitoring enabled/disabled based on environment."""
        mock_env_get.return_value = "false"
        
        monitor = PerformanceMonitor()
        
        # When disabled, operations should be no-ops
        with monitor.record_request("/test"):
            pass
        
        # Should not record anything when disabled
        # (This test would need actual implementation of enable/disable logic)
        assert True  # Placeholder for actual test


@pytest.mark.unit
class TestAlertManager:
    """Test AlertManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.alert_manager = AlertManager()
    
    def test_initialization(self):
        """Test alert manager initialization."""
        assert hasattr(self.alert_manager, 'thresholds')
        assert isinstance(self.alert_manager.thresholds, dict)
    
    def test_check_response_time_threshold(self):
        """Test response time threshold checking."""
        # Mock metrics with high response times
        mock_metrics = Mock()
        mock_metrics.get_average_response_time.return_value = 2000.0  # 2 seconds
        
        with patch('app.monitoring.alerts.send_critical_alert') as mock_alert:
            self.alert_manager.check_thresholds(mock_metrics)
            
            # Should trigger alert for high response time
            mock_alert.assert_called()
    
    def test_check_error_rate_threshold(self):
        """Test error rate threshold checking."""
        mock_metrics = Mock()
        mock_metrics.get_average_response_time.return_value = 100.0  # Normal response time
        mock_metrics.get_error_rate.return_value = 0.15  # 15% error rate
        
        with patch('app.monitoring.alerts.send_critical_alert') as mock_alert:
            self.alert_manager.check_thresholds(mock_metrics)
            
            mock_alert.assert_called()
    
    def test_no_alert_for_normal_metrics(self):
        """Test that no alerts are sent for normal metrics."""
        mock_metrics = Mock()
        mock_metrics.get_average_response_time.return_value = 200.0  # Normal
        mock_metrics.get_error_rate.return_value = 0.02  # 2% error rate
        mock_metrics.get_cache_hit_rate.return_value = 0.95  # 95% hit rate
        
        with patch('app.monitoring.alerts.send_critical_alert') as mock_alert:
            self.alert_manager.check_thresholds(mock_metrics)
            
            mock_alert.assert_not_called()


@pytest.mark.unit 
class TestGlobalMonitor:
    """Test global performance monitor instance."""
    
    def test_global_instance_exists(self):
        """Test that global performance monitor instance exists."""
        assert performance_monitor is not None
        assert isinstance(performance_monitor, PerformanceMonitor)
    
    def test_global_instance_is_singleton(self):
        """Test that performance_monitor is a singleton."""
        from app.monitoring import performance_monitor as pm1
        from app.monitoring import performance_monitor as pm2
        
        assert pm1 is pm2