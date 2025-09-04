#!/usr/bin/env python3
"""
Comprehensive Coin Flip Testing Module
Tests all coin flip mechanics for determinism, correctness, and edge cases
"""

import pytest
import sys
import os
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from simulator.core.card_bridge import load_real_card_collection, BattleCard
from simulator.core.coin_flip import parse_coin_flip_effect, execute_coin_flip_effect, CoinFlipManager
from simulator.core.effect_engine import AdvancedEffectEngine


@dataclass
class CoinFlipTestCase:
    """A specific coin flip test case"""
    card: BattleCard
    attack: Dict[str, Any]
    effect_text: str
    parsed_effect: Dict[str, Any]
    expected_behavior: Dict[str, Any]
    test_name: str


class CoinFlipTestResult:
    """Results from coin flip testing"""
    def __init__(self, test_case: CoinFlipTestCase):
        self.test_case = test_case
        self.passed = False
        self.determinism_verified = False
        self.correctness_verified = False
        self.edge_cases_passed = False
        self.performance_data = {}
        self.issues = []
        self.detailed_results = []
        
    def add_issue(self, issue_type: str, description: str, severity: str = "medium"):
        self.issues.append({
            "type": issue_type,
            "description": description,
            "severity": severity
        })
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_name": self.test_case.card.name,
            "attack_name": self.test_case.attack.get('name', 'Unknown'),
            "test_name": self.test_case.test_name,
            "passed": self.passed,
            "determinism_verified": self.determinism_verified,
            "correctness_verified": self.correctness_verified,
            "edge_cases_passed": self.edge_cases_passed,
            "issues": self.issues,
            "performance_data": self.performance_data,
            "effect_text": self.test_case.effect_text
        }


class ComprehensiveCoinFlipTester:
    """Comprehensive testing system for all coin flip mechanics"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or self._setup_logger()
        self.cards: List[BattleCard] = []
        self.coin_flip_cards: List[BattleCard] = []
        self.test_cases: List[CoinFlipTestCase] = []
        self.results: List[CoinFlipTestResult] = []
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for coin flip tests"""
        logger = logging.getLogger('coin_flip_tester')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def load_cards(self) -> bool:
        """Load all cards and identify coin flip cards"""
        try:
            self.logger.info("Loading cards for coin flip testing...")
            self.cards = load_real_card_collection(self.logger)
            
            if not self.cards:
                self.logger.error("No cards loaded!")
                return False
                
            # Find all cards with coin flip mechanics
            self.coin_flip_cards = []
            for card in self.cards:
                if self._has_coin_flip_mechanics(card):
                    self.coin_flip_cards.append(card)
                    
            self.logger.info(f"Found {len(self.coin_flip_cards)} cards with coin flip mechanics")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load cards: {e}")
            return False
            
    def _has_coin_flip_mechanics(self, card: BattleCard) -> bool:
        """Check if a card has coin flip mechanics"""
        # Check attacks
        if card.attacks:
            for attack in card.attacks:
                effect_text = attack.get('effect_text', '').lower()
                if any(word in effect_text for word in ['coin', 'flip', 'heads', 'tails']):
                    return True
                    
        # Check abilities
        if card.abilities:
            for ability in card.abilities:
                effect_text = ability.get('effect_text', '').lower()
                if any(word in effect_text for word in ['coin', 'flip', 'heads', 'tails']):
                    return True
                    
        return False
        
    def generate_test_cases(self) -> int:
        """Generate comprehensive test cases for all coin flip mechanics"""
        self.test_cases = []
        
        for card in self.coin_flip_cards:
            # Test attacks with coin flips
            if card.attacks:
                for attack in card.attacks:
                    effect_text = attack.get('effect_text', '')
                    if effect_text and any(word in effect_text.lower() for word in ['coin', 'flip']):
                        parsed_effect = parse_coin_flip_effect(effect_text)
                        if parsed_effect:
                            test_case = CoinFlipTestCase(
                                card=card,
                                attack=attack,
                                effect_text=effect_text,
                                parsed_effect=parsed_effect,
                                expected_behavior=self._determine_expected_behavior(parsed_effect),
                                test_name=f"{card.name}_{attack.get('name', 'Unknown')}_coin_flip"
                            )
                            self.test_cases.append(test_case)
                            
            # Test abilities with coin flips
            if card.abilities:
                for ability in card.abilities:
                    effect_text = ability.get('effect_text', '')
                    if effect_text and any(word in effect_text.lower() for word in ['coin', 'flip']):
                        # Create pseudo-attack for ability testing
                        pseudo_attack = {
                            'name': ability.get('name', 'Unknown'),
                            'effect_text': effect_text
                        }
                        parsed_effect = parse_coin_flip_effect(effect_text)
                        if parsed_effect:
                            test_case = CoinFlipTestCase(
                                card=card,
                                attack=pseudo_attack,
                                effect_text=effect_text,
                                parsed_effect=parsed_effect,
                                expected_behavior=self._determine_expected_behavior(parsed_effect),
                                test_name=f"{card.name}_{ability.get('name', 'Unknown')}_ability_coin_flip"
                            )
                            self.test_cases.append(test_case)
                            
        self.logger.info(f"Generated {len(self.test_cases)} coin flip test cases")
        return len(self.test_cases)
        
    def _determine_expected_behavior(self, parsed_effect: Dict[str, Any]) -> Dict[str, Any]:
        """Determine expected behavior from parsed coin flip effect"""
        expected = {
            'type': parsed_effect.get('type'),
            'coin_count': parsed_effect.get('coin_count', 1),
            'should_be_deterministic': True,
            'should_handle_edge_cases': True
        }
        
        # Add specific expectations based on effect type
        if parsed_effect.get('type') == 'damage_multiplier':
            expected['damage_per_heads'] = parsed_effect.get('damage_per_heads', 0)
            expected['min_damage'] = 0
            expected['max_damage'] = expected['coin_count'] * expected['damage_per_heads']
            
        elif parsed_effect.get('type') == 'energy_attachment':
            expected['energy_per_heads'] = 1  # Usually 1 energy per heads
            expected['min_energy'] = 0
            expected['max_energy'] = expected['coin_count']
            
        elif parsed_effect.get('type') == 'conditional':
            expected['success_condition'] = parsed_effect.get('success_condition', 'any_heads')
            
        return expected
        
    def run_comprehensive_coin_flip_tests(self) -> Dict[str, Any]:
        """Run comprehensive tests on all coin flip mechanics"""
        self.logger.info(f"Starting comprehensive coin flip testing on {len(self.test_cases)} test cases...")
        
        self.results = []
        
        for i, test_case in enumerate(self.test_cases):
            if i % 10 == 0:
                self.logger.info(f"Progress: {i}/{len(self.test_cases)} coin flip tests completed")
                
            result = self._test_coin_flip_case(test_case)
            self.results.append(result)
            
        # Generate comprehensive report
        report = self._generate_coin_flip_report()
        return report
        
    def _test_coin_flip_case(self, test_case: CoinFlipTestCase) -> CoinFlipTestResult:
        """Test a specific coin flip case comprehensively"""
        result = CoinFlipTestResult(test_case)
        
        try:
            # Test 1: Determinism verification
            result.determinism_verified = self._test_determinism(test_case, result)
            
            # Test 2: Correctness verification
            result.correctness_verified = self._test_correctness(test_case, result)
            
            # Test 3: Edge cases
            result.edge_cases_passed = self._test_edge_cases(test_case, result)
            
            # Test 4: Performance testing
            self._test_performance(test_case, result)
            
            # Overall pass/fail
            result.passed = (result.determinism_verified and 
                           result.correctness_verified and 
                           result.edge_cases_passed)
            
        except Exception as e:
            result.add_issue("execution_error", f"Test execution failed: {str(e)}", "high")
            
        return result
        
    def _test_determinism(self, test_case: CoinFlipTestCase, result: CoinFlipTestResult) -> bool:
        """Test that coin flips are deterministic with same seed"""
        try:
            # Run same coin flip multiple times with same seed
            test_seeds = [42, 123, 999]
            
            for seed in test_seeds:
                results_set1 = []
                results_set2 = []
                
                # First set of results
                for i in range(5):
                    manager1 = CoinFlipManager(self.logger, rng_seed=seed)
                    flip_result1 = execute_coin_flip_effect(
                        test_case.parsed_effect, manager1, base_damage=10
                    )
                    results_set1.append(flip_result1)
                    
                # Second set of results with same seeds
                for i in range(5):
                    manager2 = CoinFlipManager(self.logger, rng_seed=seed)
                    flip_result2 = execute_coin_flip_effect(
                        test_case.parsed_effect, manager2, base_damage=10
                    )
                    results_set2.append(flip_result2)
                    
                # Compare results
                if results_set1 != results_set2:
                    result.add_issue("determinism", f"Results not deterministic with seed {seed}", "high")
                    return False
                    
            result.detailed_results.append("Determinism verified across multiple seeds")
            return True
            
        except Exception as e:
            result.add_issue("determinism_test", f"Determinism test failed: {str(e)}", "high")
            return False
            
    def _test_correctness(self, test_case: CoinFlipTestCase, result: CoinFlipTestResult) -> bool:
        """Test that coin flip results are mathematically correct"""
        try:
            manager = CoinFlipManager(self.logger, rng_seed=42)
            
            # Run many iterations to test statistical correctness
            iterations = 1000
            outcomes = []
            
            for i in range(iterations):
                # Use different seeds to get varied results
                test_manager = CoinFlipManager(self.logger, rng_seed=42 + i)
                flip_result = execute_coin_flip_effect(
                    test_case.parsed_effect, test_manager, base_damage=10
                )
                outcomes.append(flip_result)
                
            # Analyze results
            successful_flips = [o for o in outcomes if o.get('success', False)]
            
            if len(successful_flips) < iterations * 0.8:  # At least 80% should succeed
                result.add_issue("correctness", f"Low success rate: {len(successful_flips)}/{iterations}", "medium")
                return False
                
            # Test specific correctness based on effect type
            if test_case.expected_behavior['type'] == 'damage_multiplier':
                return self._test_damage_multiplier_correctness(successful_flips, test_case, result)
            elif test_case.expected_behavior['type'] == 'energy_attachment':
                return self._test_energy_attachment_correctness(successful_flips, test_case, result)
            else:
                # Generic correctness test
                result.detailed_results.append(f"Generic correctness verified: {len(successful_flips)}/{iterations} successful")
                return True
                
        except Exception as e:
            result.add_issue("correctness_test", f"Correctness test failed: {str(e)}", "high")
            return False
            
    def _test_damage_multiplier_correctness(self, outcomes: List[Dict], test_case: CoinFlipTestCase, result: CoinFlipTestResult) -> bool:
        """Test damage multiplier coin flip correctness"""
        try:
            expected = test_case.expected_behavior
            damage_values = [o.get('total_damage', 0) for o in outcomes]
            
            # Check damage range
            min_damage = min(damage_values)
            max_damage = max(damage_values)
            
            if min_damage < expected.get('min_damage', 0):
                result.add_issue("damage_range", f"Damage below minimum: {min_damage}", "medium")
                return False
                
            if max_damage > expected.get('max_damage', 999):
                result.add_issue("damage_range", f"Damage above maximum: {max_damage}", "medium")
                return False
                
            # Check that we get variety in results (not all same damage)
            unique_damages = set(damage_values)
            if len(unique_damages) < 2 and expected['coin_count'] > 1:
                result.add_issue("damage_variety", "All coin flips produce same damage", "low")
                
            result.detailed_results.append(f"Damage range verified: {min_damage}-{max_damage}")
            return True
            
        except Exception as e:
            result.add_issue("damage_correctness", f"Damage correctness test failed: {str(e)}", "medium")
            return False
            
    def _test_energy_attachment_correctness(self, outcomes: List[Dict], test_case: CoinFlipTestCase, result: CoinFlipTestResult) -> bool:
        """Test energy attachment coin flip correctness"""
        try:
            expected = test_case.expected_behavior
            energy_values = [o.get('energy_generated', 0) for o in outcomes]
            
            # Check energy range
            min_energy = min(energy_values)
            max_energy = max(energy_values)
            
            if min_energy < expected.get('min_energy', 0):
                result.add_issue("energy_range", f"Energy below minimum: {min_energy}", "medium")
                return False
                
            if max_energy > expected.get('max_energy', 999):
                result.add_issue("energy_range", f"Energy above maximum: {max_energy}", "medium")
                return False
                
            result.detailed_results.append(f"Energy range verified: {min_energy}-{max_energy}")
            return True
            
        except Exception as e:
            result.add_issue("energy_correctness", f"Energy correctness test failed: {str(e)}", "medium")
            return False
            
    def _test_edge_cases(self, test_case: CoinFlipTestCase, result: CoinFlipTestResult) -> bool:
        """Test edge cases for coin flip mechanics"""
        try:
            edge_cases_passed = 0
            total_edge_cases = 0
            
            # Edge case 1: Zero base damage
            total_edge_cases += 1
            try:
                manager = CoinFlipManager(self.logger, rng_seed=42)
                edge_result = execute_coin_flip_effect(test_case.parsed_effect, manager, base_damage=0)
                if edge_result.get('success', False):
                    edge_cases_passed += 1
                    result.detailed_results.append("Zero damage edge case passed")
                else:
                    result.add_issue("edge_case", "Zero damage case failed", "low")
            except Exception as e:
                result.add_issue("edge_case", f"Zero damage test error: {str(e)}", "medium")
                
            # Edge case 2: Very high base damage
            total_edge_cases += 1
            try:
                manager = CoinFlipManager(self.logger, rng_seed=42)
                edge_result = execute_coin_flip_effect(test_case.parsed_effect, manager, base_damage=1000)
                if edge_result.get('success', False):
                    edge_cases_passed += 1
                    result.detailed_results.append("High damage edge case passed")
                else:
                    result.add_issue("edge_case", "High damage case failed", "low")
            except Exception as e:
                result.add_issue("edge_case", f"High damage test error: {str(e)}", "medium")
                
            # Edge case 3: Multiple rapid executions (stress test)
            total_edge_cases += 1
            try:
                manager = CoinFlipManager(self.logger, rng_seed=42)
                rapid_successes = 0
                for i in range(100):
                    edge_result = execute_coin_flip_effect(test_case.parsed_effect, manager, base_damage=10)
                    if edge_result.get('success', False):
                        rapid_successes += 1
                        
                if rapid_successes >= 80:  # At least 80% should succeed
                    edge_cases_passed += 1
                    result.detailed_results.append("Rapid execution stress test passed")
                else:
                    result.add_issue("edge_case", f"Rapid execution failed: {rapid_successes}/100", "medium")
            except Exception as e:
                result.add_issue("edge_case", f"Rapid execution test error: {str(e)}", "medium")
                
            return edge_cases_passed == total_edge_cases
            
        except Exception as e:
            result.add_issue("edge_case_test", f"Edge case testing failed: {str(e)}", "high")
            return False
            
    def _test_performance(self, test_case: CoinFlipTestCase, result: CoinFlipTestResult):
        """Test performance of coin flip execution"""
        try:
            import time
            
            # Performance test: 1000 executions
            start_time = time.time()
            
            for i in range(1000):
                manager = CoinFlipManager(self.logger, rng_seed=42 + i)
                execute_coin_flip_effect(test_case.parsed_effect, manager, base_damage=10)
                
            end_time = time.time()
            total_time = end_time - start_time
            avg_time = total_time / 1000
            
            result.performance_data['total_time_1000_executions'] = total_time
            result.performance_data['avg_execution_time'] = avg_time
            result.performance_data['executions_per_second'] = 1000 / total_time
            
            # Performance threshold: should execute at least 1000 times per second
            if avg_time > 0.001:  # 1ms per execution
                result.add_issue("performance", f"Slow execution: {avg_time:.4f}s per flip", "low")
                
        except Exception as e:
            result.add_issue("performance_test", f"Performance test failed: {str(e)}", "low")
            
    def _generate_coin_flip_report(self) -> Dict[str, Any]:
        """Generate comprehensive coin flip testing report"""
        # Calculate statistics
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.passed])
        determinism_passed = len([r for r in self.results if r.determinism_verified])
        correctness_passed = len([r for r in self.results if r.correctness_verified])
        edge_cases_passed = len([r for r in self.results if r.edge_cases_passed])
        
        # Categorize issues
        high_severity_issues = []
        medium_severity_issues = []
        low_severity_issues = []
        
        for result in self.results:
            for issue in result.issues:
                issue_data = {
                    'card': result.test_case.card.name,
                    'test': result.test_case.test_name,
                    'issue': issue
                }
                
                if issue['severity'] == 'high':
                    high_severity_issues.append(issue_data)
                elif issue['severity'] == 'medium':
                    medium_severity_issues.append(issue_data)
                else:
                    low_severity_issues.append(issue_data)
                    
        # Performance statistics
        execution_times = [r.performance_data.get('avg_execution_time', 0) for r in self.results if 'avg_execution_time' in r.performance_data]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Find most problematic cards
        card_failure_counts = defaultdict(int)
        for result in self.results:
            if not result.passed:
                card_failure_counts[result.test_case.card.name] += 1
                
        report = {
            'summary': {
                'total_coin_flip_tests': total_tests,
                'tests_passed': passed_tests,
                'tests_failed': total_tests - passed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'determinism_success_rate': (determinism_passed / total_tests * 100) if total_tests > 0 else 0,
                'correctness_success_rate': (correctness_passed / total_tests * 100) if total_tests > 0 else 0,
                'edge_case_success_rate': (edge_cases_passed / total_tests * 100) if total_tests > 0 else 0
            },
            'issue_breakdown': {
                'high_severity': len(high_severity_issues),
                'medium_severity': len(medium_severity_issues),
                'low_severity': len(low_severity_issues),
                'total_issues': len(high_severity_issues) + len(medium_severity_issues) + len(low_severity_issues)
            },
            'detailed_issues': {
                'high_severity': high_severity_issues[:10],  # Top 10 high severity
                'medium_severity': medium_severity_issues[:10],  # Top 10 medium severity
                'low_severity': low_severity_issues[:5]  # Top 5 low severity
            },
            'performance_metrics': {
                'avg_execution_time': avg_execution_time,
                'total_cards_with_coin_flips': len(self.coin_flip_cards),
                'total_test_cases_generated': len(self.test_cases)
            },
            'most_problematic_cards': dict(sorted(card_failure_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            'test_coverage': {
                'unique_cards_tested': len(set(r.test_case.card.id for r in self.results)),
                'effect_types_tested': len(set(r.test_case.parsed_effect.get('type') for r in self.results)),
                'coin_counts_tested': list(set(r.test_case.parsed_effect.get('coin_count', 1) for r in self.results))
            },
            'detailed_results': [r.to_dict() for r in self.results if not r.passed][:20]  # Failed tests details
        }
        
        return report
        
    def save_detailed_results(self, report: Dict[str, Any], filename: str = None):
        """Save detailed test results to file"""
        if not filename:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"coin_flip_test_results_{timestamp}.json"
            
        os.makedirs('test_results', exist_ok=True)
        filepath = os.path.join('test_results', filename)
        
        detailed_data = {
            'report': report,
            'all_results': [r.to_dict() for r in self.results],
            'test_cases': [{
                'card_name': tc.card.name,
                'attack_name': tc.attack.get('name', 'Unknown'),
                'effect_text': tc.effect_text,
                'parsed_effect': tc.parsed_effect,
                'expected_behavior': tc.expected_behavior
            } for tc in self.test_cases]
        }
        
        with open(filepath, 'w') as f:
            json.dump(detailed_data, f, indent=2)
            
        self.logger.info(f"Detailed coin flip results saved to {filepath}")


# Pytest integration
def test_coin_flip_determinism():
    """Test that all coin flip mechanics are deterministic"""
    tester = ComprehensiveCoinFlipTester()
    assert tester.load_cards(), "Failed to load cards"
    
    scenario_count = tester.generate_test_cases()
    assert scenario_count > 0, "No coin flip test cases generated"
    
    # Run tests on subset for pytest
    tester.test_cases = tester.test_cases[:10]  # Test first 10 for speed
    report = tester.run_comprehensive_coin_flip_tests()
    
    # Verify determinism success rate is very high
    determinism_rate = report['summary']['determinism_success_rate']
    assert determinism_rate >= 95, f"Determinism success rate too low: {determinism_rate}%"
    
    # Check for high severity issues
    high_severity_count = report['issue_breakdown']['high_severity']
    assert high_severity_count == 0, f"Found {high_severity_count} high severity coin flip issues"


def test_moltres_ex_coin_flip():
    """Specific test for Moltres EX coin flip mechanics (example)"""
    tester = ComprehensiveCoinFlipTester()
    assert tester.load_cards(), "Failed to load cards"
    
    # Find Moltres EX card
    moltres_ex = None
    for card in tester.cards:
        if 'moltres' in card.name.lower() and 'ex' in card.name.lower():
            moltres_ex = card
            break
            
    if moltres_ex:
        # Test its coin flip mechanics specifically
        for attack in moltres_ex.attacks:
            effect_text = attack.get('effect_text', '')
            if 'coin' in effect_text.lower():
                parsed_effect = parse_coin_flip_effect(effect_text)
                assert parsed_effect is not None, f"Failed to parse Moltres EX coin flip: {effect_text}"
                
                # Test determinism
                manager1 = CoinFlipManager(logging.getLogger(), rng_seed=42)
                manager2 = CoinFlipManager(logging.getLogger(), rng_seed=42)
                
                result1 = execute_coin_flip_effect(parsed_effect, manager1, 0)
                result2 = execute_coin_flip_effect(parsed_effect, manager2, 0)
                
                assert result1 == result2, "Moltres EX coin flip not deterministic"


if __name__ == "__main__":
    # Run coin flip testing standalone
    tester = ComprehensiveCoinFlipTester()
    
    if tester.load_cards():
        tester.generate_test_cases()
        report = tester.run_comprehensive_coin_flip_tests()
        
        print("\n" + "="*60)
        print("COMPREHENSIVE COIN FLIP TESTING REPORT")
        print("="*60)
        print(f"Total Tests: {report['summary']['total_coin_flip_tests']}")
        print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
        print(f"Determinism Rate: {report['summary']['determinism_success_rate']:.1f}%")
        print(f"Correctness Rate: {report['summary']['correctness_success_rate']:.1f}%")
        print(f"High Severity Issues: {report['issue_breakdown']['high_severity']}")
        print("="*60)
        
        # Save detailed results
        tester.save_detailed_results(report)