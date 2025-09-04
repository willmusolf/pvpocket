#!/usr/bin/env python3
"""
Comprehensive Ability Test Runner
Orchestrates all ability testing modules and generates consolidated reports
"""

import sys
import os
import logging
import json
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import all test modules
from scripts.test_all_cards import ComprehensiveCardTester
from tests.abilities.test_ability_automation import ComprehensiveAbilityTester
from tests.abilities.test_coin_flip_determinism import ComprehensiveCoinFlipTester
from tests.abilities.test_status_effects import ComprehensiveStatusEffectTester
from tests.abilities.test_energy_effects import ComprehensiveEnergyEffectTester
from tests.regression.test_card_regression import CardRegressionTester


class ComprehensiveAbilityTestRunner:
    """Orchestrates all ability testing modules and generates consolidated reports"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or self._setup_logger()
        self.test_results = {}
        self.start_time = datetime.now()
        self.results_dir = "comprehensive_test_results"
        
        # Ensure results directory exists
        os.makedirs(self.results_dir, exist_ok=True)
        
    def _setup_logger(self) -> logging.Logger:
        """Setup comprehensive logging"""
        logger = logging.getLogger('comprehensive_test_runner')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # File handler
            os.makedirs('logs', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_handler = logging.FileHandler(f'logs/comprehensive_test_{timestamp}.log')
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
        return logger
        
    def run_all_tests(self, test_config: Dict[str, bool] = None) -> Dict[str, Any]:
        """Run all comprehensive ability tests"""
        if test_config is None:
            test_config = {
                'basic_card_tests': True,
                'ability_tests': True,
                'coin_flip_tests': True,
                'status_effect_tests': True,
                'energy_effect_tests': True,
                'regression_tests': True
            }
            
        self.logger.info("Starting comprehensive ability testing suite...")
        self.logger.info(f"Test configuration: {test_config}")
        
        # Test 1: Basic card functionality tests
        if test_config.get('basic_card_tests', True):
            self.logger.info("Running basic card functionality tests...")
            try:
                basic_tester = ComprehensiveCardTester(self.logger)
                if basic_tester.load_cards():
                    basic_report = basic_tester.test_all_cards()
                    self.test_results['basic_card_tests'] = basic_report
                    self.logger.info(f"Basic card tests completed: {basic_report['summary']['overall_success_rate']:.1f}% success rate")
                else:
                    self.test_results['basic_card_tests'] = {'error': 'Failed to load cards'}
            except Exception as e:
                self.logger.error(f"Basic card tests failed: {e}")
                self.test_results['basic_card_tests'] = {'error': str(e)}
                
        # Test 2: Comprehensive ability tests
        if test_config.get('ability_tests', True):
            self.logger.info("Running comprehensive ability tests...")
            try:
                ability_tester = ComprehensiveAbilityTester(self.logger)
                if ability_tester.load_cards():
                    ability_tester.generate_test_scenarios()
                    ability_report = ability_tester.run_all_ability_tests()
                    self.test_results['ability_tests'] = ability_report
                    self.logger.info(f"Ability tests completed: {ability_report['summary']['success_rate']:.1f}% success rate")
                else:
                    self.test_results['ability_tests'] = {'error': 'Failed to load cards'}
            except Exception as e:
                self.logger.error(f"Ability tests failed: {e}")
                self.test_results['ability_tests'] = {'error': str(e)}
                
        # Test 3: Coin flip determinism tests
        if test_config.get('coin_flip_tests', True):
            self.logger.info("Running coin flip determinism tests...")
            try:
                coin_tester = ComprehensiveCoinFlipTester(self.logger)
                if coin_tester.load_cards():
                    coin_tester.generate_test_cases()
                    coin_report = coin_tester.run_comprehensive_coin_flip_tests()
                    self.test_results['coin_flip_tests'] = coin_report
                    self.logger.info(f"Coin flip tests completed: {coin_report['summary']['success_rate']:.1f}% success rate")
                else:
                    self.test_results['coin_flip_tests'] = {'error': 'Failed to load cards'}
            except Exception as e:
                self.logger.error(f"Coin flip tests failed: {e}")
                self.test_results['coin_flip_tests'] = {'error': str(e)}
                
        # Test 4: Status effect tests
        if test_config.get('status_effect_tests', True):
            self.logger.info("Running status effect tests...")
            try:
                status_tester = ComprehensiveStatusEffectTester(self.logger)
                if status_tester.load_cards():
                    status_tester.generate_test_cases()
                    status_report = status_tester.run_comprehensive_status_effect_tests()
                    self.test_results['status_effect_tests'] = status_report
                    self.logger.info(f"Status effect tests completed: {status_report['summary']['success_rate']:.1f}% success rate")
                else:
                    self.test_results['status_effect_tests'] = {'error': 'Failed to load cards'}
            except Exception as e:
                self.logger.error(f"Status effect tests failed: {e}")
                self.test_results['status_effect_tests'] = {'error': str(e)}
                
        # Test 5: Energy effect tests
        if test_config.get('energy_effect_tests', True):
            self.logger.info("Running energy effect tests...")
            try:
                energy_tester = ComprehensiveEnergyEffectTester(self.logger)
                if energy_tester.load_cards():
                    energy_tester.generate_test_cases()
                    energy_report = energy_tester.run_comprehensive_energy_effect_tests()
                    self.test_results['energy_effect_tests'] = energy_report
                    self.logger.info(f"Energy effect tests completed: {energy_report['summary']['success_rate']:.1f}% success rate")
                else:
                    self.test_results['energy_effect_tests'] = {'error': 'Failed to load cards'}
            except Exception as e:
                self.logger.error(f"Energy effect tests failed: {e}")
                self.test_results['energy_effect_tests'] = {'error': str(e)}
                
        # Test 6: Regression tests (if baseline exists)
        if test_config.get('regression_tests', True):
            self.logger.info("Running regression tests...")
            try:
                regression_tester = CardRegressionTester(self.logger)
                if regression_tester.load_cards():
                    if regression_tester.load_baseline():
                        regression_report = regression_tester.run_regression_tests()
                        self.test_results['regression_tests'] = regression_report
                        self.logger.info(f"Regression tests completed: {regression_report['summary']['total_regressions']} regressions found")
                    else:
                        self.logger.warning("No regression baseline found, skipping regression tests")
                        self.test_results['regression_tests'] = {'skipped': 'No baseline found'}
                else:
                    self.test_results['regression_tests'] = {'error': 'Failed to load cards'}
            except Exception as e:
                self.logger.error(f"Regression tests failed: {e}")
                self.test_results['regression_tests'] = {'error': str(e)}
                
        # Generate consolidated report
        consolidated_report = self._generate_consolidated_report()
        
        self.logger.info("Comprehensive ability testing suite completed")
        return consolidated_report
        
    def _generate_consolidated_report(self) -> Dict[str, Any]:
        """Generate consolidated report from all test results"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        # Calculate overall statistics
        total_tests = 0
        total_passed = 0
        total_failed = 0
        critical_issues = 0
        
        test_summaries = {}
        
        for test_name, result in self.test_results.items():
            if 'error' in result:
                test_summaries[test_name] = {
                    'status': 'error',
                    'error': result['error'],
                    'tests_run': 0,
                    'success_rate': 0
                }
                continue
                
            if 'skipped' in result:
                test_summaries[test_name] = {
                    'status': 'skipped',
                    'reason': result['skipped'],
                    'tests_run': 0,
                    'success_rate': 0
                }
                continue
                
            summary = result.get('summary', {})
            
            # Extract relevant metrics based on test type
            if test_name == 'basic_card_tests':
                tests_run = summary.get('total_tests_run', 0)
                passed = summary.get('total_tests_passed', 0)
                success_rate = summary.get('overall_success_rate', 0)
            elif test_name == 'ability_tests':
                tests_run = summary.get('total_scenarios_tested', 0)
                passed = summary.get('scenarios_passed', 0)
                success_rate = summary.get('success_rate', 0)
            elif test_name == 'coin_flip_tests':
                tests_run = summary.get('total_coin_flip_tests', 0)
                passed = summary.get('tests_passed', 0)
                success_rate = summary.get('success_rate', 0)
            elif test_name == 'status_effect_tests':
                tests_run = summary.get('total_status_effect_tests', 0)
                passed = summary.get('tests_passed', 0)
                success_rate = summary.get('success_rate', 0)
            elif test_name == 'energy_effect_tests':
                tests_run = summary.get('total_energy_effect_tests', 0)
                passed = summary.get('tests_passed', 0)
                success_rate = summary.get('success_rate', 0)
            elif test_name == 'regression_tests':
                tests_run = summary.get('total_cards_tested', 0)
                regressions = summary.get('total_regressions', 0)
                passed = tests_run - regressions
                success_rate = (passed / tests_run * 100) if tests_run > 0 else 100
                critical_issues += summary.get('critical_regressions', 0)
            else:
                tests_run = 0
                passed = 0
                success_rate = 0
                
            test_summaries[test_name] = {
                'status': 'completed',
                'tests_run': tests_run,
                'tests_passed': passed,
                'tests_failed': tests_run - passed,
                'success_rate': success_rate
            }
            
            total_tests += tests_run
            total_passed += passed
            total_failed += (tests_run - passed)
            
        # Calculate overall success rate
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        # Identify most problematic areas
        problematic_areas = []
        for test_name, summary in test_summaries.items():
            if summary.get('status') == 'completed' and summary.get('success_rate', 0) < 80:
                problematic_areas.append({
                    'test_area': test_name,
                    'success_rate': summary.get('success_rate', 0),
                    'tests_failed': summary.get('tests_failed', 0)
                })
                
        problematic_areas.sort(key=lambda x: x['success_rate'])
        
        # Generate recommendations
        recommendations = self._generate_recommendations(test_summaries, problematic_areas)
        
        consolidated_report = {
            'metadata': {
                'test_timestamp': end_time.isoformat(),
                'test_duration_seconds': duration.total_seconds(),
                'test_duration_human': str(duration),
                'runner_version': '1.0'
            },
            'overall_summary': {
                'total_tests_run': total_tests,
                'total_tests_passed': total_passed,
                'total_tests_failed': total_failed,
                'overall_success_rate': overall_success_rate,
                'critical_issues_found': critical_issues,
                'test_areas_completed': len([s for s in test_summaries.values() if s.get('status') == 'completed']),
                'test_areas_failed': len([s for s in test_summaries.values() if s.get('status') == 'error'])
            },
            'test_area_summaries': test_summaries,
            'problematic_areas': problematic_areas,
            'recommendations': recommendations,
            'detailed_results': self.test_results,
            'test_health_score': self._calculate_health_score(test_summaries, critical_issues)
        }
        
        return consolidated_report
        
    def _generate_recommendations(self, test_summaries: Dict, problematic_areas: List) -> List[str]:
        """Generate actionable recommendations based on test results"""
        recommendations = []
        
        # Check for critical issues
        for test_name, summary in test_summaries.items():
            if summary.get('status') == 'error':
                recommendations.append(f"URGENT: Fix {test_name} - test suite is failing to run")
                
        # Check for low success rates
        for area in problematic_areas:
            if area['success_rate'] < 50:
                recommendations.append(f"CRITICAL: {area['test_area']} has very low success rate ({area['success_rate']:.1f}%)")
            elif area['success_rate'] < 80:
                recommendations.append(f"Review {area['test_area']} - success rate below threshold ({area['success_rate']:.1f}%)")
                
        # Check for regression issues
        regression_summary = test_summaries.get('regression_tests', {})
        if regression_summary.get('status') == 'skipped':
            recommendations.append("Generate regression baseline to enable regression testing")
            
        # General recommendations
        if len(problematic_areas) > 2:
            recommendations.append("Consider focusing on highest-impact issues first")
            
        if not recommendations:
            recommendations.append("All tests are performing well - consider expanding test coverage")
            
        recommendations.append("Run this test suite daily to catch regressions early")
        recommendations.append("Update regression baseline after major changes")
        
        return recommendations
        
    def _calculate_health_score(self, test_summaries: Dict, critical_issues: int) -> Dict[str, Any]:
        """Calculate overall health score for the card ability system"""
        # Base score
        health_score = 100
        
        # Deduct for failed test areas
        for test_name, summary in test_summaries.items():
            if summary.get('status') == 'error':
                health_score -= 20  # Major deduction for failed test suites
            elif summary.get('status') == 'completed':
                success_rate = summary.get('success_rate', 0)
                if success_rate < 50:
                    health_score -= 15
                elif success_rate < 70:
                    health_score -= 10
                elif success_rate < 90:
                    health_score -= 5
                    
        # Deduct for critical issues
        health_score -= (critical_issues * 5)
        
        # Ensure score doesn't go below 0
        health_score = max(0, health_score)
        
        # Categorize health
        if health_score >= 90:
            health_category = "Excellent"
            health_description = "Card ability system is functioning very well"
        elif health_score >= 75:
            health_category = "Good"
            health_description = "Card ability system is mostly functional with minor issues"
        elif health_score >= 60:
            health_category = "Fair"
            health_description = "Card ability system has some significant issues that need attention"
        elif health_score >= 40:
            health_category = "Poor"
            health_description = "Card ability system has major issues that require immediate attention"
        else:
            health_category = "Critical"
            health_description = "Card ability system is severely compromised"
            
        return {
            'score': health_score,
            'category': health_category,
            'description': health_description
        }
        
    def save_consolidated_report(self, report: Dict[str, Any], filename: str = None):
        """Save consolidated report to file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"comprehensive_ability_test_report_{timestamp}.json"
            
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
            
        self.logger.info(f"Consolidated report saved to {filepath}")
        
        # Also save a summary report for quick viewing
        summary_filename = filename.replace('.json', '_summary.txt')
        summary_filepath = os.path.join(self.results_dir, summary_filename)
        
        with open(summary_filepath, 'w') as f:
            self._write_summary_report(report, f)
            
        self.logger.info(f"Summary report saved to {summary_filepath}")
        
    def _write_summary_report(self, report: Dict[str, Any], file):
        """Write human-readable summary report"""
        file.write("="*80 + "\n")
        file.write("COMPREHENSIVE CARD ABILITY TESTING REPORT\n")
        file.write("="*80 + "\n")
        file.write(f"Generated: {report['metadata']['test_timestamp']}\n")
        file.write(f"Duration: {report['metadata']['test_duration_human']}\n")
        file.write("\n")
        
        # Overall summary
        overall = report['overall_summary']
        file.write("OVERALL SUMMARY\n")
        file.write("-" * 40 + "\n")
        file.write(f"Total Tests Run: {overall['total_tests_run']:,}\n")
        file.write(f"Tests Passed: {overall['total_tests_passed']:,}\n")
        file.write(f"Tests Failed: {overall['total_tests_failed']:,}\n")
        file.write(f"Success Rate: {overall['overall_success_rate']:.1f}%\n")
        file.write(f"Critical Issues: {overall['critical_issues_found']}\n")
        file.write("\n")
        
        # Health score
        health = report['test_health_score']
        file.write("SYSTEM HEALTH\n")
        file.write("-" * 40 + "\n")
        file.write(f"Health Score: {health['score']}/100 ({health['category']})\n")
        file.write(f"Description: {health['description']}\n")
        file.write("\n")
        
        # Test area breakdown
        file.write("TEST AREA BREAKDOWN\n")
        file.write("-" * 40 + "\n")
        for test_name, summary in report['test_area_summaries'].items():
            status = summary.get('status', 'unknown')
            if status == 'completed':
                file.write(f"{test_name}: {summary['success_rate']:.1f}% ({summary['tests_passed']}/{summary['tests_run']})\n")
            else:
                file.write(f"{test_name}: {status.upper()}\n")
        file.write("\n")
        
        # Problematic areas
        if report['problematic_areas']:
            file.write("AREAS NEEDING ATTENTION\n")
            file.write("-" * 40 + "\n")
            for area in report['problematic_areas']:
                file.write(f"- {area['test_area']}: {area['success_rate']:.1f}% success rate\n")
            file.write("\n")
            
        # Recommendations
        file.write("RECOMMENDATIONS\n")
        file.write("-" * 40 + "\n")
        for i, rec in enumerate(report['recommendations'], 1):
            file.write(f"{i}. {rec}\n")
        file.write("\n")
        
        file.write("="*80 + "\n")


def main():
    """Main entry point for comprehensive ability testing"""
    parser = argparse.ArgumentParser(description="Comprehensive Card Ability Test Runner")
    parser.add_argument("--skip-basic", action="store_true", help="Skip basic card tests")
    parser.add_argument("--skip-abilities", action="store_true", help="Skip ability tests")
    parser.add_argument("--skip-coin-flips", action="store_true", help="Skip coin flip tests")
    parser.add_argument("--skip-status", action="store_true", help="Skip status effect tests")
    parser.add_argument("--skip-energy", action="store_true", help="Skip energy effect tests")
    parser.add_argument("--skip-regression", action="store_true", help="Skip regression tests")
    parser.add_argument("--output-dir", default="comprehensive_test_results", help="Output directory for results")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure test settings
    test_config = {
        'basic_card_tests': not args.skip_basic,
        'ability_tests': not args.skip_abilities,
        'coin_flip_tests': not args.skip_coin_flips,
        'status_effect_tests': not args.skip_status,
        'energy_effect_tests': not args.skip_energy,
        'regression_tests': not args.skip_regression
    }
    
    # Create test runner
    runner = ComprehensiveAbilityTestRunner()
    runner.results_dir = args.output_dir
    
    if args.verbose:
        runner.logger.setLevel(logging.DEBUG)
        
    # Run tests
    print("Starting comprehensive card ability testing...")
    print("This may take several minutes to complete.")
    print("-" * 60)
    
    try:
        report = runner.run_all_tests(test_config)
        
        # Save results
        runner.save_consolidated_report(report)
        
        # Print summary
        print("\n" + "="*60)
        print("COMPREHENSIVE ABILITY TESTING COMPLETED")
        print("="*60)
        
        overall = report['overall_summary']
        print(f"Total Tests: {overall['total_tests_run']:,}")
        print(f"Success Rate: {overall['overall_success_rate']:.1f}%")
        print(f"Critical Issues: {overall['critical_issues_found']}")
        
        health = report['test_health_score']
        print(f"System Health: {health['score']}/100 ({health['category']})")
        
        print(f"\nDetailed results saved to: {runner.results_dir}/")
        
        # Exit with appropriate code
        if overall['critical_issues_found'] > 0:
            print("\nWARNING: Critical issues found!")
            return 1
        elif overall['overall_success_rate'] < 80:
            print("\nWARNING: Overall success rate below 80%")
            return 1
        else:
            print("\nAll tests completed successfully!")
            return 0
            
    except Exception as e:
        print(f"\nERROR: Comprehensive testing failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)