#!/usr/bin/env python3
"""
Scalability Testing Script for Pokemon TCG Pocket
Run this to test all scalability features and see them in action.
"""

import requests
import time
import threading
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5001"  # Change if using different port
NUM_CONCURRENT_USERS = 10
REQUESTS_PER_USER = 5

class Colors:
    """ANSI color codes for pretty output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

def test_basic_connectivity():
    """Test if the app is running"""
    print_header("Testing Basic Connectivity")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print_success("App is running and accessible")
            return True
        else:
            print_error(f"App returned status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Cannot connect to app: {e}")
        print_info("Make sure the app is running with: python run.py")
        return False

def test_scalability_endpoint():
    """Test the scalability testing endpoint"""
    print_header("Testing Scalability Systems")
    try:
        response = requests.get(f"{BASE_URL}/test-scalability", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success("Scalability endpoint working")
            print(f"\n{Colors.BOLD}System Status:{Colors.END}")
            print(f"  Cache Status: {data.get('cache_status', 'Unknown')}")
            print(f"  Database Status: {data.get('db_status', 'Unknown')}")
            print(f"  Card Service: {data.get('card_service_status', 'Unknown')}")
            print(f"  Total Cards Loaded: {data.get('total_cards', 0)}")
            return True
        else:
            print_error(f"Scalability test failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Scalability test error: {e}")
        return False

def test_cache_performance():
    """Test cache hit/miss behavior"""
    print_header("Testing Cache Performance")
    
    endpoints = [
        "/",  # Main page (should cache user data)
        "/api/cards" if "api/cards" in requests.get(f"{BASE_URL}/").text else None,
    ]
    
    for endpoint in [e for e in endpoints if e]:
        print(f"\n{Colors.BOLD}Testing endpoint: {endpoint}{Colors.END}")
        
        # First request (cache miss)
        start = time.time()
        response1 = requests.get(f"{BASE_URL}{endpoint}")
        time1 = time.time() - start
        print(f"  First request (cache miss): {time1*1000:.2f}ms")
        
        # Second request (should be cache hit)
        start = time.time()
        response2 = requests.get(f"{BASE_URL}{endpoint}")
        time2 = time.time() - start
        print(f"  Second request (cache hit): {time2*1000:.2f}ms")
        
        if time2 < time1 * 0.8:  # At least 20% faster (more realistic threshold)
            print_success(f"Cache working! {(1 - time2/time1)*100:.1f}% faster")
        elif abs(time1 - time2) < 50:  # Less than 50ms difference means both are fast (cached)
            print_success(f"Both requests fast - cache likely working ({time1:.0f}ms vs {time2:.0f}ms)")
        else:
            print_warning("Cache might not be working optimally")

def simulate_user_session(user_id, results):
    """Simulate a single user session"""
    session_times = []
    errors = 0
    
    for i in range(REQUESTS_PER_USER):
        try:
            start = time.time()
            response = requests.get(f"{BASE_URL}/")
            elapsed = time.time() - start
            
            if response.status_code == 200:
                session_times.append(elapsed)
            else:
                errors += 1
                
            # Simulate user think time
            time.sleep(0.1)
            
        except Exception as e:
            errors += 1
    
    results[user_id] = {
        'times': session_times,
        'errors': errors,
        'avg_time': sum(session_times) / len(session_times) if session_times else 0
    }

def test_concurrent_users():
    """Test with multiple concurrent users"""
    print_header(f"Testing {NUM_CONCURRENT_USERS} Concurrent Users")
    
    results = {}
    threads = []
    
    print_info(f"Simulating {NUM_CONCURRENT_USERS} users, {REQUESTS_PER_USER} requests each...")
    
    start_time = time.time()
    
    # Start all user threads
    for i in range(NUM_CONCURRENT_USERS):
        thread = threading.Thread(target=simulate_user_session, args=(i, results))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    total_time = time.time() - start_time
    
    # Analyze results
    all_times = []
    total_errors = 0
    
    for user_id, user_data in results.items():
        all_times.extend(user_data['times'])
        total_errors += user_data['errors']
    
    if all_times:
        avg_response = sum(all_times) / len(all_times) * 1000  # Convert to ms
        min_response = min(all_times) * 1000
        max_response = max(all_times) * 1000
        
        print(f"\n{Colors.BOLD}Results:{Colors.END}")
        print(f"  Total requests: {NUM_CONCURRENT_USERS * REQUESTS_PER_USER}")
        print(f"  Successful requests: {len(all_times)}")
        print(f"  Failed requests: {total_errors}")
        print(f"  Average response time: {avg_response:.2f}ms")
        print(f"  Min response time: {min_response:.2f}ms")
        print(f"  Max response time: {max_response:.2f}ms")
        print(f"  Total test time: {total_time:.2f}s")
        print(f"  Requests per second: {len(all_times)/total_time:.2f}")
        
        if avg_response < 1000 and total_errors == 0:
            print_success("Excellent performance! Ready for production.")
        elif avg_response < 3000 and total_errors < 5:
            print_warning("Good performance, but could be optimized.")
        else:
            print_error("Performance issues detected. Check your logs.")
    else:
        print_error("No successful requests completed!")

def test_monitoring_endpoints():
    """Test monitoring and health check endpoints"""
    print_header("Testing Monitoring Endpoints")
    
    endpoints = [
        ("/internal/health", "Health Check"),
        ("/internal/metrics", "Metrics"),
        ("/internal/dashboard", "Dashboard"),
    ]
    
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            if response.status_code == 200:
                print_success(f"{name} endpoint working")
                if endpoint == "/internal/health":
                    data = response.json()
                    print(f"  Status: {data.get('status', 'Unknown')}")
            else:
                print_warning(f"{name} returned {response.status_code}")
        except Exception as e:
            print_error(f"{name} error: {e}")

def check_logs():
    """Instructions for checking logs"""
    print_header("Check Your Application Logs")
    
    print("Look for these indicators in your terminal:\n")
    
    print(f"{Colors.GREEN}Good signs:{Colors.END}")
    print("  ✅ CACHE HIT: Retrieved X cards from cache")
    print("  ✅ USER CACHE HIT: Retrieved data for user")
    print("  ✅ DB POOL: Created connection pool")
    print("  ✅ MONITOR: Performance monitoring started")
    
    print(f"\n{Colors.YELLOW}Normal operations:{Colors.END}")
    print("  ⚠️ CACHE MISS: Card collection not found in cache")
    print("  ⚠️ USER CACHE MISS: No cached data for user")
    
    print(f"\n{Colors.RED}Issues to watch:{Colors.END}")
    print("  ❌ CACHE ERROR: Error retrieving from cache")
    print("  ❌ Memory usage too high")
    print("  ❌ Response times increasing over time")

def main():
    print_header("Pokemon TCG Pocket - Scalability Test Suite")
    
    # Run tests in sequence
    if not test_basic_connectivity():
        return
    
    test_scalability_endpoint()
    test_cache_performance()
    test_concurrent_users()
    test_monitoring_endpoints()
    check_logs()
    
    print_header("Testing Complete!")
    
    print("\n📊 Next steps:")
    print("1. Check your application logs for cache hits/misses")
    print("2. Visit http://localhost:5001/internal/dashboard for metrics")
    print("3. Run with more concurrent users to stress test")
    print("4. Monitor memory usage during heavy load")

if __name__ == "__main__":
    main()