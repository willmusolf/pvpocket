"""
Unit tests for monitoring functionality - Fixed version.
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


@pytest.mark.unit
class TestPerformanceMonitor:
    """Test PerformanceMonitor functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = PerformanceMonitor()
    
    def test_initialization(self):
        """Test monitor initialization."""
        assert isinstance(self.monitor.metrics, PerformanceMetrics)
        # Don't assume specific internal attributes


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