#!/usr/bin/env python3
"""
CI-friendly performance testing script for Pokemon TCG Pocket app.
Designed to run in GitHub Actions with proper exit codes and reporting.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
from concurrent.futures import ThreadPoolExecutor
import statistics

# Configure logging for CI
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CIPerformanceTestSuite:
    def __init__(self, base_url: str = None, max_workers: int = 10):
        self.base_url = base_url or os.environ.get('TEST_BASE_URL', 'http://localhost:5001')
        self.max_workers = max_workers
        self.results = []
        self.test_session = requests.Session()
        
        # Performance thresholds for CI
        self.thresholds = {
            'response_time_p95': 2000,  # 95th percentile response time in ms
            'response_time_avg': 500,   # Average response time in ms
            'error_rate': 0.02,         # Maximum 2% error rate
            'throughput_min': 10        # Minimum requests per second
        }
        
    def run_endpoint_test(self, endpoint: str, method: str = 'GET', 
                         data: Dict = None, expected_status: int = 200,
                         timeout: int = 10) -> Dict[str, Any]:
        """Run a single endpoint test and return performance metrics."""
        start_time = time.time()
        
        try:
            if method.upper() == 'GET':
                response = self.test_session.get(
                    f"{self.base_url}{endpoint}", 
                    timeout=timeout
                )
            elif method.upper() == 'POST':
                response = self.test_session.post(
                    f"{self.base_url}{endpoint}", 
                    json=data, 
                    timeout=timeout
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                'endpoint': endpoint,
                'method': method,
                'status_code': response.status_code,
                'response_time_ms': response_time,
                'success': response.status_code == expected_status,
                'error': None,
                'content_length': len(response.content) if response.content else 0
            }
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return {
                'endpoint': endpoint,
                'method': method,
                'status_code': 0,
                'response_time_ms': response_time,
                'success': False,
                'error': str(e),
                'content_length': 0
            }
    
    def load_test_endpoint(self, endpoint: str, duration_seconds: int = 30,
                          concurrent_users: int = 5) -> Dict[str, Any]:
        """Run a load test on a specific endpoint."""
        logger.info(f"Load testing {endpoint} for {duration_seconds}s with {concurrent_users} users")
        
        results = []
        start_test_time = time.time()
        
        def make_request():
            return self.run_endpoint_test(endpoint)
            
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            while time.time() - start_test_time < duration_seconds:
                # Submit batch of requests
                futures = [executor.submit(make_request) for _ in range(concurrent_users)]
                
                # Collect results
                for future in futures:
                    result = future.result()
                    results.append(result)
                    
                # Small delay to prevent overwhelming the server
                time.sleep(0.1)
        
        # Calculate metrics
        successful_requests = [r for r in results if r['success']]
        response_times = [r['response_time_ms'] for r in results]
        
        if not results:
            return {'error': 'No requests completed'}
            
        total_requests = len(results)
        successful_count = len(successful_requests)
        error_rate = (total_requests - successful_count) / total_requests
        
        return {
            'endpoint': endpoint,
            'duration_seconds': duration_seconds,
            'total_requests': total_requests,
            'successful_requests': successful_count,
            'error_rate': error_rate,
            'avg_response_time_ms': statistics.mean(response_times) if response_times else 0,
            'p95_response_time_ms': statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times) if response_times else 0,
            'p99_response_time_ms': statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max(response_times) if response_times else 0,
            'min_response_time_ms': min(response_times) if response_times else 0,
            'max_response_time_ms': max(response_times) if response_times else 0,
            'requests_per_second': total_requests / duration_seconds,
            'throughput_rps': successful_count / duration_seconds
        }
    
    def test_health_endpoints(self) -> bool:
        """Test health and basic endpoints."""
        logger.info("Testing health endpoints...")
        
        endpoints = [
            {'endpoint': '/health', 'expected_status': 200},
            {'endpoint': '/metrics', 'expected_status': 200},
            {'endpoint': '/', 'expected_status': 200}
        ]
        
        all_passed = True
        for test in endpoints:
            result = self.run_endpoint_test(
                test['endpoint'], 
                expected_status=test['expected_status']
            )
            
            if result['success'] and result['response_time_ms'] < 1000:
                logger.info(f"✅ {test['endpoint']}: {result['response_time_ms']:.1f}ms")
            else:
                logger.error(f"❌ {test['endpoint']}: {result}")
                all_passed = False
                
            self.results.append(result)
            
        return all_passed
    
    def test_api_performance(self) -> bool:
        """Test API endpoint performance under light load."""
        logger.info("Testing API performance...")
        
        # Test critical endpoints with light load
        api_endpoints = [
            '/internal/health',
            '/internal/metrics'
        ]
        
        all_passed = True
        for endpoint in api_endpoints:
            load_result = self.load_test_endpoint(
                endpoint, 
                duration_seconds=15, 
                concurrent_users=3
            )
            
            if 'error' in load_result:
                logger.error(f"❌ Load test failed for {endpoint}: {load_result['error']}")
                all_passed = False
                continue
                
            # Check against thresholds
            passed_checks = []
            
            if load_result['avg_response_time_ms'] <= self.thresholds['response_time_avg']:
                passed_checks.append(f"Avg response time: {load_result['avg_response_time_ms']:.1f}ms")
            else:
                logger.error(f"❌ {endpoint} avg response time too high: {load_result['avg_response_time_ms']:.1f}ms")
                all_passed = False
                
            if load_result['error_rate'] <= self.thresholds['error_rate']:
                passed_checks.append(f"Error rate: {load_result['error_rate']:.1%}")
            else:
                logger.error(f"❌ {endpoint} error rate too high: {load_result['error_rate']:.1%}")
                all_passed = False
                
            if load_result['throughput_rps'] >= self.thresholds['throughput_min']:
                passed_checks.append(f"Throughput: {load_result['throughput_rps']:.1f} RPS")
            else:
                logger.error(f"❌ {endpoint} throughput too low: {load_result['throughput_rps']:.1f} RPS")
                all_passed = False
                
            if passed_checks:
                logger.info(f"✅ {endpoint}: {', '.join(passed_checks)}")
                
            self.results.append(load_result)
            
        return all_passed
    
    def generate_ci_report(self) -> Dict[str, Any]:
        """Generate a CI-friendly test report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.get('success', False) or r.get('error_rate', 1) <= self.thresholds['error_rate'])
        
        # Calculate overall metrics
        all_response_times = []
        for result in self.results:
            if 'response_time_ms' in result:
                all_response_times.append(result['response_time_ms'])
            elif 'avg_response_time_ms' in result:
                all_response_times.append(result['avg_response_time_ms'])
                
        report = {
            'timestamp': datetime.now().isoformat(),
            'test_environment': {
                'base_url': self.base_url,
                'max_workers': self.max_workers,
                'thresholds': self.thresholds
            },
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'success_rate': passed_tests / total_tests if total_tests > 0 else 0,
                'overall_avg_response_time_ms': statistics.mean(all_response_times) if all_response_times else 0
            },
            'detailed_results': self.results,
            'recommendations': []
        }
        
        # Add recommendations based on results
        if report['summary']['success_rate'] < 0.95:
            report['recommendations'].append("Consider investigating failing tests before deployment")
            
        if report['summary']['overall_avg_response_time_ms'] > 1000:
            report['recommendations'].append("Response times are high - consider performance optimization")
            
        return report
    
    def run_ci_tests(self) -> bool:
        """Run the complete CI test suite."""
        logger.info("Starting CI performance test suite...")
        
        # Run all test phases
        health_ok = self.test_health_endpoints()
        api_ok = self.test_api_performance()
        
        # Generate report
        report = self.generate_ci_report()
        
        # Output report for CI
        print("\n" + "="*50)
        print("PERFORMANCE TEST REPORT")
        print("="*50)
        print(f"Tests: {report['summary']['passed_tests']}/{report['summary']['total_tests']} passed")
        print(f"Success Rate: {report['summary']['success_rate']:.1%}")
        print(f"Average Response Time: {report['summary']['overall_avg_response_time_ms']:.1f}ms")
        
        if report['recommendations']:
            print("\nRecommendations:")
            for rec in report['recommendations']:
                print(f"  - {rec}")
        
        # Save detailed report for CI artifacts
        with open('performance_test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info("Performance test report saved to performance_test_report.json")
        
        # Return overall success
        overall_success = health_ok and api_ok and report['summary']['success_rate'] >= 0.8
        
        if overall_success:
            logger.info("✅ All performance tests passed!")
        else:
            logger.error("❌ Performance tests failed!")
            
        return overall_success


def main():
    """Main entry point for CI performance testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='CI Performance Test Suite')
    parser.add_argument('--base-url', default=None, help='Base URL to test')
    parser.add_argument('--workers', type=int, default=5, help='Max concurrent workers')
    parser.add_argument('--quick', action='store_true', help='Run quick tests only')
    
    args = parser.parse_args()
    
    # Initialize test suite
    suite = CIPerformanceTestSuite(
        base_url=args.base_url,
        max_workers=args.workers
    )
    
    # Adjust thresholds for quick tests
    if args.quick:
        suite.thresholds['response_time_avg'] = 1000
        suite.thresholds['throughput_min'] = 5
        
    try:
        success = suite.run_ci_tests()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Test suite failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()