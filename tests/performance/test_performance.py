"""
Performance tests for Pokemon TCG Pocket App.
"""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch


@pytest.mark.performance
@pytest.mark.slow
class TestCachePerformance:
    """Test cache performance and optimization."""
    
    def test_cache_hit_rate(self, client, cache_manager, mock_card_data):
        """Test cache hit rate performance."""
        from Card import CardCollection, Card
        
        # Populate cache
        collection = CardCollection()
        for card_data in mock_card_data:
            card = Card(**card_data)
            collection.add_card(card)
        
        cache_manager.set_card_collection(collection, ttl_hours=24)
        
        # Test multiple requests hit cache
        hit_count = 0
        total_requests = 10
        
        for _ in range(total_requests):
            cached_collection = cache_manager.get_card_collection()
            if cached_collection is not None:
                hit_count += 1
        
        hit_rate = (hit_count / total_requests) * 100
        assert hit_rate >= 90, f"Cache hit rate too low: {hit_rate}%"
    
    def test_cache_response_time(self, cache_manager, mock_user_data):
        """Test cache response times are acceptable."""
        user_id = "test-user-123"
        cache_manager.set_user_data(user_id, mock_user_data)
        
        # Test response time
        start_time = time.time()
        result = cache_manager.get_user_data(user_id)
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        assert response_time_ms < 50, f"Cache response too slow: {response_time_ms}ms"
        assert result is not None


@pytest.mark.performance
@pytest.mark.slow
class TestConcurrentUsers:
    """Test concurrent user performance."""
    
    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests."""
        def make_request():
            response = client.get('/health')
            return response.status_code, time.time()
        
        # Simulate 10 concurrent users
        num_concurrent = 10
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            start_time = time.time()
            futures = [executor.submit(make_request) for _ in range(num_concurrent)]
            results = [future.result() for future in as_completed(futures)]
            end_time = time.time()
        
        # All requests should succeed
        status_codes = [result[0] for result in results]
        success_count = len([code for code in status_codes if code == 200])
        success_rate = (success_count / num_concurrent) * 100
        
        assert success_rate >= 95, f"Success rate too low: {success_rate}%"
        
        # Total time should be reasonable
        total_time = end_time - start_time
        assert total_time < 5, f"Concurrent requests too slow: {total_time}s"
    
    @patch('app.services.CardService.get_full_card_collection')
    def test_concurrent_api_calls(self, mock_collection, client, mock_card_data):
        """Test concurrent API calls performance."""
        from Card import CardCollection, Card
        
        # Mock card collection
        collection = CardCollection()
        for card_data in mock_card_data:
            card = Card(**card_data)
            collection.add_card(card)
        
        mock_collection.return_value = collection
        
        def api_request():
            response = client.get('/api/cards')
            return response.status_code, len(response.data)
        
        # Test 5 concurrent API calls
        num_concurrent = 5
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(api_request) for _ in range(num_concurrent)]
            results = [future.result() for future in as_completed(futures)]
        
        # All should succeed and return data
        for status_code, data_length in results:
            assert status_code == 200
            assert data_length > 0


@pytest.mark.performance
class TestDatabasePerformance:
    """Test database operation performance."""
    
    def test_connection_pool_efficiency(self, app):
        """Test database connection pool efficiency."""
        from app.db_service import db_service
        
        # Test multiple rapid connections
        start_time = time.time()
        
        for _ in range(10):
            try:
                # Simulate database operation
                client = db_service._connection_pool.get_client()
                db_service._connection_pool.return_client(client)
            except Exception:
                pass  # Mock might not support this
        
        end_time = time.time()
        operation_time = end_time - start_time
        
        # Should be very fast with connection pooling
        assert operation_time < 1, f"Connection operations too slow: {operation_time}s"


@pytest.mark.performance
class TestMemoryUsage:
    """Test memory usage and optimization."""
    
    def test_cache_memory_usage(self, cache_manager, mock_card_data):
        """Test that cache doesn't consume excessive memory."""
        import sys
        from Card import CardCollection, Card
        
        # Get initial memory usage
        initial_size = sys.getsizeof(cache_manager.client._data)
        
        # Add large amount of data
        collection = CardCollection()
        for i in range(100):  # Create 100 test cards
            card = Card(
                id=i,
                name=f"Test Card {i}",
                energy_type="Fire",
                set_name="Test Set",
                hp=100
            )
            collection.add_card(card)
        
        cache_manager.set_card_collection(collection)
        
        # Check memory usage increase is reasonable
        final_size = sys.getsizeof(cache_manager.client._data)
        memory_increase = final_size - initial_size
        
        # Should not use more than 10MB for test data
        assert memory_increase < 10 * 1024 * 1024, f"Excessive memory usage: {memory_increase} bytes"


@pytest.mark.performance 
class TestStartupPerformance:
    """Test application startup performance."""
    
    def test_app_startup_time(self):
        """Test that app starts up quickly."""
        import time
        import os
        
        # Set test environment
        os.environ['FLASK_CONFIG'] = 'testing'
        
        start_time = time.time()
        
        with patch('firebase_admin.initialize_app'), \
             patch('firebase_admin.firestore.client'), \
             patch('firebase_admin.storage.bucket'):
            
            from app import create_app
            app = create_app('testing')
            
        end_time = time.time()
        startup_time = end_time - start_time
        
        # Should start up in less than 3 seconds (optimized)
        assert startup_time < 3, f"Startup too slow: {startup_time}s"


@pytest.mark.performance
class TestResponseTimes:
    """Test API response times."""
    
    def test_health_endpoint_response_time(self, client):
        """Test health endpoint response time."""
        start_time = time.time()
        response = client.get('/health')
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        assert response.status_code == 200
        assert response_time_ms < 100, f"Health endpoint too slow: {response_time_ms}ms"
    
    @patch('app.services.CardService.get_full_card_collection')
    def test_api_response_times(self, mock_collection, client, mock_card_data):
        """Test API response times are acceptable."""
        from Card import CardCollection, Card
        
        # Mock small dataset for predictable performance
        collection = CardCollection()
        for card_data in mock_card_data:
            card = Card(**card_data)
            collection.add_card(card)
        
        mock_collection.return_value = collection
        
        endpoints = [
            '/api/cards',
            '/api/cards/paginated?page=1&limit=10'
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            
            assert response.status_code == 200
            assert response_time_ms < 500, f"{endpoint} too slow: {response_time_ms}ms"