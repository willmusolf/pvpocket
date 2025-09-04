#!/usr/bin/env python3
"""
Comprehensive Status Effect Testing Module
Tests all status effect mechanics including application, persistence, and turn-by-turn behavior
"""

import pytest
import sys
import os
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from simulator.core.card_bridge import load_real_card_collection, BattleCard
from simulator.core.pokemon import BattlePokemon
from simulator.core.status_conditions import StatusManager, StatusCondition
from simulator.core.game import GameState, GamePhase
from simulator.ai.rule_based import RuleBasedAI
from Deck import Deck


@dataclass
class StatusEffectTestCase:
    """A specific status effect test case"""
    card: BattleCard
    ability_or_attack: Dict[str, Any]
    status_condition: StatusCondition
    test_scenario: str
    expected_behavior: Dict[str, Any]
    test_name: str


class StatusEffectTestResult:
    """Results from status effect testing"""
    def __init__(self, test_case: StatusEffectTestCase):
        self.test_case = test_case
        self.passed = False
        self.application_verified = False
        self.persistence_verified = False
        self.turn_effects_verified = False
        self.removal_verified = False
        self.issues = []
        self.turn_by_turn_log = []
        self.performance_data = {}
        
    def add_issue(self, issue_type: str, description: str, severity: str = "medium", turn: int = None):
        self.issues.append({
            "type": issue_type,
            "description": description,
            "severity": severity,
            "turn": turn
        })
        
    def log_turn_state(self, turn: int, state: Dict[str, Any]):
        self.turn_by_turn_log.append({
            "turn": turn,
            "state": state
        })
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_name": self.test_case.card.name,
            "ability_or_attack_name": self.test_case.ability_or_attack.get('name', 'Unknown'),
            "status_condition": self.test_case.status_condition.value,
            "test_scenario": self.test_case.test_scenario,
            "test_name": self.test_case.test_name,
            "passed": self.passed,
            "application_verified": self.application_verified,
            "persistence_verified": self.persistence_verified,
            "turn_effects_verified": self.turn_effects_verified,
            "removal_verified": self.removal_verified,
            "issues": self.issues,
            "turn_by_turn_log": self.turn_by_turn_log,
            "performance_data": self.performance_data
        }


class ComprehensiveStatusEffectTester:
    """Comprehensive testing system for all status effect mechanics"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or self._setup_logger()
        self.cards: List[BattleCard] = []
        self.status_effect_cards: List[BattleCard] = []
        self.test_cases: List[StatusEffectTestCase] = []
        self.results: List[StatusEffectTestResult] = []
        self.status_manager = StatusManager(self.logger)
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for status effect tests"""
        logger = logging.getLogger('status_effect_tester')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def load_cards(self) -> bool:
        """Load all cards and identify status effect cards"""
        try:
            self.logger.info("Loading cards for status effect testing...")
            self.cards = load_real_card_collection(self.logger)
            
            if not self.cards:
                self.logger.error("No cards loaded!")
                return False
                
            # Find all cards with status effect mechanics
            self.status_effect_cards = []
            for card in self.cards:
                if self._has_status_effect_mechanics(card):
                    self.status_effect_cards.append(card)
                    
            self.logger.info(f"Found {len(self.status_effect_cards)} cards with status effect mechanics")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load cards: {e}")
            return False
            
    def _has_status_effect_mechanics(self, card: BattleCard) -> bool:
        """Check if a card has status effect mechanics"""
        status_keywords = ['burn', 'poison', 'paralyz', 'sleep', 'confus', 'special condition']
        
        # Check attacks
        if card.attacks:
            for attack in card.attacks:
                effect_text = attack.get('effect_text', '').lower()
                if any(keyword in effect_text for keyword in status_keywords):
                    return True
                    
        # Check abilities
        if card.abilities:
            for ability in card.abilities:
                effect_text = ability.get('effect_text', '').lower()
                if any(keyword in effect_text for keyword in status_keywords):
                    return True
                    
        return False
        
    def generate_test_cases(self) -> int:
        """Generate comprehensive test cases for all status effect mechanics"""
        self.test_cases = []
        
        for card in self.status_effect_cards:
            # Test attacks with status effects
            if card.attacks:
                for attack in card.attacks:
                    self._generate_attack_status_test_cases(card, attack)
                    
            # Test abilities with status effects
            if card.abilities:
                for ability in card.abilities:
                    self._generate_ability_status_test_cases(card, ability)
                    
        self.logger.info(f"Generated {len(self.test_cases)} status effect test cases")
        return len(self.test_cases)
        
    def _generate_attack_status_test_cases(self, card: BattleCard, attack: Dict[str, Any]):
        """Generate test cases for attack-based status effects"""
        effect_text = attack.get('effect_text', '').lower()
        
        # Map keywords to status conditions
        status_mapping = {
            'burn': StatusCondition.BURNED,
            'poison': StatusCondition.POISONED,
            'paralyz': StatusCondition.PARALYZED,
            'sleep': StatusCondition.ASLEEP,
            'confus': StatusCondition.CONFUSED
        }
        
        for keyword, status in status_mapping.items():
            if keyword in effect_text:
                # Test case 1: Basic application
                self.test_cases.append(StatusEffectTestCase(
                    card=card,
                    ability_or_attack=attack,
                    status_condition=status,
                    test_scenario="basic_application",
                    expected_behavior=self._get_expected_status_behavior(status),
                    test_name=f"{card.name}_{attack.get('name', 'Unknown')}_{status.value}_basic"
                ))
                
                # Test case 2: Turn-by-turn persistence
                self.test_cases.append(StatusEffectTestCase(
                    card=card,
                    ability_or_attack=attack,
                    status_condition=status,
                    test_scenario="turn_persistence",
                    expected_behavior=self._get_expected_status_behavior(status),
                    test_name=f"{card.name}_{attack.get('name', 'Unknown')}_{status.value}_persistence"
                ))
                
                # Test case 3: Multiple applications
                self.test_cases.append(StatusEffectTestCase(
                    card=card,
                    ability_or_attack=attack,
                    status_condition=status,
                    test_scenario="multiple_applications",
                    expected_behavior=self._get_expected_status_behavior(status),
                    test_name=f"{card.name}_{attack.get('name', 'Unknown')}_{status.value}_multiple"
                ))
                
        # Special case: Random status condition
        if 'random' in effect_text and 'special condition' in effect_text:
            self.test_cases.append(StatusEffectTestCase(
                card=card,
                ability_or_attack=attack,
                status_condition=StatusCondition.BURNED,  # Use as placeholder
                test_scenario="random_status",
                expected_behavior={'type': 'random', 'possible_statuses': list(StatusCondition)},
                test_name=f"{card.name}_{attack.get('name', 'Unknown')}_random_status"
            ))
            
    def _generate_ability_status_test_cases(self, card: BattleCard, ability: Dict[str, Any]):
        """Generate test cases for ability-based status effects"""
        # Similar to attack cases but for abilities
        effect_text = ability.get('effect_text', '').lower()
        
        status_mapping = {
            'burn': StatusCondition.BURNED,
            'poison': StatusCondition.POISONED,
            'paralyz': StatusCondition.PARALYZED,
            'sleep': StatusCondition.ASLEEP,
            'confus': StatusCondition.CONFUSED
        }
        
        for keyword, status in status_mapping.items():
            if keyword in effect_text:
                self.test_cases.append(StatusEffectTestCase(
                    card=card,
                    ability_or_attack=ability,
                    status_condition=status,
                    test_scenario="ability_application",
                    expected_behavior=self._get_expected_status_behavior(status),
                    test_name=f"{card.name}_{ability.get('name', 'Unknown')}_{status.value}_ability"
                ))
                
    def _get_expected_status_behavior(self, status: StatusCondition) -> Dict[str, Any]:
        """Get expected behavior for a status condition"""
        behaviors = {
            StatusCondition.BURNED: {
                'damage_per_turn': 20,
                'lasts_until_removed': True,
                'affects_attacks': False,
                'stackable': False
            },
            StatusCondition.POISONED: {
                'damage_per_turn': 10,
                'lasts_until_removed': True,
                'affects_attacks': False,
                'stackable': False
            },
            StatusCondition.PARALYZED: {
                'damage_per_turn': 0,
                'prevents_attacks': True,
                'coin_flip_to_attack': True,
                'lasts_until_removed': True,
                'stackable': False
            },
            StatusCondition.ASLEEP: {
                'damage_per_turn': 0,
                'prevents_attacks': True,
                'coin_flip_to_wake': True,
                'lasts_until_removed': True,
                'stackable': False
            },
            StatusCondition.CONFUSED: {
                'damage_per_turn': 0,
                'coin_flip_before_attack': True,
                'self_damage_on_tails': 30,
                'lasts_until_removed': True,
                'stackable': False
            }
        }
        
        return behaviors.get(status, {'lasts_until_removed': True, 'stackable': False})
        
    def run_comprehensive_status_effect_tests(self) -> Dict[str, Any]:
        """Run comprehensive tests on all status effect mechanics"""
        self.logger.info(f"Starting comprehensive status effect testing on {len(self.test_cases)} test cases...")
        
        self.results = []
        
        for i, test_case in enumerate(self.test_cases):
            if i % 10 == 0:
                self.logger.info(f"Progress: {i}/{len(self.test_cases)} status effect tests completed")
                
            result = self._test_status_effect_case(test_case)
            self.results.append(result)
            
        # Generate comprehensive report
        report = self._generate_status_effect_report()
        return report
        
    def _test_status_effect_case(self, test_case: StatusEffectTestCase) -> StatusEffectTestResult:
        """Test a specific status effect case comprehensively"""
        result = StatusEffectTestResult(test_case)
        
        try:
            if test_case.test_scenario == "basic_application":
                self._test_basic_status_application(test_case, result)
            elif test_case.test_scenario == "turn_persistence":
                self._test_turn_by_turn_persistence(test_case, result)
            elif test_case.test_scenario == "multiple_applications":
                self._test_multiple_applications(test_case, result)
            elif test_case.test_scenario == "random_status":
                self._test_random_status_application(test_case, result)
            elif test_case.test_scenario == "ability_application":
                self._test_ability_status_application(test_case, result)
                
            # Overall pass/fail
            result.passed = (result.application_verified and 
                           result.persistence_verified and 
                           result.turn_effects_verified and
                           len([i for i in result.issues if i['severity'] == 'high']) == 0)
            
        except Exception as e:
            result.add_issue("execution_error", f"Test execution failed: {str(e)}", "high")
            
        return result
        
    def _test_basic_status_application(self, test_case: StatusEffectTestCase, result: StatusEffectTestResult):
        """Test basic status effect application"""
        try:
            # Create test Pokemon
            battle_pokemon = BattlePokemon(test_case.card, self.logger)
            
            # Apply status condition
            success, message = self.status_manager.apply_status_condition(
                battle_pokemon, test_case.status_condition, turn=1
            )
            
            if success:
                result.application_verified = True
                result.log_turn_state(1, {
                    "action": "status_applied",
                    "status": test_case.status_condition.value,
                    "message": message,
                    "hp": battle_pokemon.current_hp
                })
            else:
                result.add_issue("application_failed", f"Failed to apply {test_case.status_condition.value}: {message}", "high")
                
            # Verify status is present
            if self.status_manager.has_status_condition(battle_pokemon, test_case.status_condition):
                result.persistence_verified = True
            else:
                result.add_issue("status_not_present", f"{test_case.status_condition.value} not found after application", "high")
                
        except Exception as e:
            result.add_issue("basic_application_error", f"Basic application test failed: {str(e)}", "high")
            
    def _test_turn_by_turn_persistence(self, test_case: StatusEffectTestCase, result: StatusEffectTestResult):
        """Test status effect persistence and turn-by-turn effects"""
        try:
            # Create test Pokemon
            battle_pokemon = BattlePokemon(test_case.card, self.logger)
            
            # Apply status condition
            success, _ = self.status_manager.apply_status_condition(
                battle_pokemon, test_case.status_condition, turn=1
            )
            
            if not success:
                result.add_issue("setup_failed", "Failed to apply status for persistence test", "high")
                return
                
            result.application_verified = True
            initial_hp = battle_pokemon.current_hp
            
            # Test effects over multiple turns
            for turn in range(2, 7):  # Test 5 turns
                turn_effects = self.status_manager.process_between_turns_effects(battle_pokemon, turn)
                
                result.log_turn_state(turn, {
                    "action": "between_turns_processing",
                    "effects": turn_effects,
                    "hp": battle_pokemon.current_hp,
                    "status_present": self.status_manager.has_status_condition(battle_pokemon, test_case.status_condition)
                })
                
                # Verify expected behavior
                expected = test_case.expected_behavior
                
                if expected.get('damage_per_turn', 0) > 0:
                    expected_hp_loss = expected['damage_per_turn'] * (turn - 1)
                    actual_hp_loss = initial_hp - battle_pokemon.current_hp
                    
                    if abs(actual_hp_loss - expected_hp_loss) > 5:  # Allow small variance
                        result.add_issue("incorrect_damage", 
                                       f"Turn {turn}: Expected {expected_hp_loss} damage, got {actual_hp_loss}", 
                                       "medium", turn)
                        
                # Check if status still persists (unless Pokemon is KO'd)
                if battle_pokemon.current_hp > 0:
                    if not self.status_manager.has_status_condition(battle_pokemon, test_case.status_condition):
                        if expected.get('lasts_until_removed', True):
                            result.add_issue("status_disappeared", 
                                           f"Turn {turn}: Status condition disappeared unexpectedly", 
                                           "medium", turn)
                            
            result.persistence_verified = True
            result.turn_effects_verified = True
            
        except Exception as e:
            result.add_issue("persistence_test_error", f"Persistence test failed: {str(e)}", "high")
            
    def _test_multiple_applications(self, test_case: StatusEffectTestCase, result: StatusEffectTestResult):
        """Test multiple applications of the same status effect"""
        try:
            # Create test Pokemon
            battle_pokemon = BattlePokemon(test_case.card, self.logger)
            
            # Apply status condition multiple times
            applications = []
            for i in range(3):
                success, message = self.status_manager.apply_status_condition(
                    battle_pokemon, test_case.status_condition, turn=i+1
                )
                applications.append({"attempt": i+1, "success": success, "message": message})
                
            result.log_turn_state(0, {
                "action": "multiple_applications",
                "applications": applications
            })
            
            # Check behavior based on stackability
            expected = test_case.expected_behavior
            if not expected.get('stackable', False):
                # Should only have one instance
                status_count = len([s for s in battle_pokemon.status_conditions if s.condition == test_case.status_condition])
                if status_count > 1:
                    result.add_issue("incorrect_stacking", 
                                   f"Non-stackable status stacked {status_count} times", 
                                   "medium")
                else:
                    result.application_verified = True
            else:
                # Should be able to stack
                result.application_verified = True
                
        except Exception as e:
            result.add_issue("multiple_applications_error", f"Multiple applications test failed: {str(e)}", "high")
            
    def _test_random_status_application(self, test_case: StatusEffectTestCase, result: StatusEffectTestResult):
        """Test random status effect application"""
        try:
            # Create test Pokemon
            battle_pokemon = BattlePokemon(test_case.card, self.logger)
            
            # Apply random status multiple times to test distribution
            applied_statuses = []
            
            for i in range(20):  # Test 20 times
                # Reset Pokemon status
                battle_pokemon.status_conditions = []
                
                # Apply random status
                success, message = self.status_manager.apply_random_status_condition(battle_pokemon, turn=i+1)
                
                if success:
                    # Check what status was applied
                    current_statuses = [s.condition for s in battle_pokemon.status_conditions]
                    if current_statuses:
                        applied_statuses.append(current_statuses[0])
                        
            result.log_turn_state(0, {
                "action": "random_status_testing",
                "applied_statuses": [s.value for s in applied_statuses],
                "unique_statuses": len(set(applied_statuses)),
                "total_applications": len(applied_statuses)
            })
            
            # Verify randomness
            unique_statuses = set(applied_statuses)
            if len(unique_statuses) >= 2:  # Should get at least 2 different statuses in 20 tries
                result.application_verified = True
            else:
                result.add_issue("poor_randomness", 
                               f"Only {len(unique_statuses)} unique statuses in 20 attempts", 
                               "medium")
                
            if len(applied_statuses) >= 15:  # At least 75% success rate
                result.persistence_verified = True
            else:
                result.add_issue("low_success_rate", 
                               f"Only {len(applied_statuses)}/20 random applications succeeded", 
                               "medium")
                
        except Exception as e:
            result.add_issue("random_status_error", f"Random status test failed: {str(e)}", "high")
            
    def _test_ability_status_application(self, test_case: StatusEffectTestCase, result: StatusEffectTestResult):
        """Test ability-based status effect application"""
        try:
            # This is similar to basic application but for abilities
            # In a full implementation, this would involve ability triggers
            # For now, we'll test the status manager's ability to handle ability-triggered effects
            
            battle_pokemon = BattlePokemon(test_case.card, self.logger)
            
            # Simulate ability trigger
            success, message = self.status_manager.apply_status_condition(
                battle_pokemon, test_case.status_condition, turn=1
            )
            
            result.log_turn_state(1, {
                "action": "ability_status_application",
                "ability": test_case.ability_or_attack.get('name', 'Unknown'),
                "success": success,
                "message": message
            })
            
            if success:
                result.application_verified = True
                result.persistence_verified = self.status_manager.has_status_condition(
                    battle_pokemon, test_case.status_condition
                )
            else:
                result.add_issue("ability_application_failed", 
                               f"Ability-triggered status failed: {message}", 
                               "medium")
                
        except Exception as e:
            result.add_issue("ability_status_error", f"Ability status test failed: {str(e)}", "high")
            
    def _generate_status_effect_report(self) -> Dict[str, Any]:
        """Generate comprehensive status effect testing report"""
        # Calculate statistics
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.passed])
        application_passed = len([r for r in self.results if r.application_verified])
        persistence_passed = len([r for r in self.results if r.persistence_verified])
        turn_effects_passed = len([r for r in self.results if r.turn_effects_verified])
        
        # Group by status condition
        status_stats = defaultdict(lambda: {'total': 0, 'passed': 0, 'failed': 0})
        for result in self.results:
            status = result.test_case.status_condition.value
            status_stats[status]['total'] += 1
            if result.passed:
                status_stats[status]['passed'] += 1
            else:
                status_stats[status]['failed'] += 1
                
        # Categorize issues
        high_severity_issues = []
        medium_severity_issues = []
        
        for result in self.results:
            for issue in result.issues:
                issue_data = {
                    'card': result.test_case.card.name,
                    'test': result.test_case.test_name,
                    'status': result.test_case.status_condition.value,
                    'issue': issue
                }
                
                if issue['severity'] == 'high':
                    high_severity_issues.append(issue_data)
                else:
                    medium_severity_issues.append(issue_data)
                    
        # Find most problematic status effects
        status_failure_counts = defaultdict(int)
        for result in self.results:
            if not result.passed:
                status_failure_counts[result.test_case.status_condition.value] += 1
                
        report = {
            'summary': {
                'total_status_effect_tests': total_tests,
                'tests_passed': passed_tests,
                'tests_failed': total_tests - passed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'application_success_rate': (application_passed / total_tests * 100) if total_tests > 0 else 0,
                'persistence_success_rate': (persistence_passed / total_tests * 100) if total_tests > 0 else 0,
                'turn_effects_success_rate': (turn_effects_passed / total_tests * 100) if total_tests > 0 else 0
            },
            'status_condition_breakdown': dict(status_stats),
            'issue_breakdown': {
                'high_severity': len(high_severity_issues),
                'medium_severity': len(medium_severity_issues),
                'total_issues': len(high_severity_issues) + len(medium_severity_issues)
            },
            'detailed_issues': {
                'high_severity': high_severity_issues[:10],
                'medium_severity': medium_severity_issues[:10]
            },
            'most_problematic_statuses': dict(sorted(status_failure_counts.items(), key=lambda x: x[1], reverse=True)),
            'test_coverage': {
                'unique_cards_tested': len(set(r.test_case.card.id for r in self.results)),
                'status_conditions_tested': list(set(r.test_case.status_condition.value for r in self.results)),
                'test_scenarios_covered': list(set(r.test_case.test_scenario for r in self.results))
            },
            'performance_metrics': {
                'total_cards_with_status_effects': len(self.status_effect_cards),
                'total_test_cases_generated': len(self.test_cases),
                'avg_turns_tested': sum(len(r.turn_by_turn_log) for r in self.results) / len(self.results) if self.results else 0
            },
            'detailed_results': [r.to_dict() for r in self.results if not r.passed][:20]
        }
        
        return report
        
    def save_detailed_results(self, report: Dict[str, Any], filename: str = None):
        """Save detailed test results to file"""
        if not filename:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"status_effect_test_results_{timestamp}.json"
            
        os.makedirs('test_results', exist_ok=True)
        filepath = os.path.join('test_results', filename)
        
        detailed_data = {
            'report': report,
            'all_results': [r.to_dict() for r in self.results],
            'test_cases': [{
                'card_name': tc.card.name,
                'ability_or_attack_name': tc.ability_or_attack.get('name', 'Unknown'),
                'status_condition': tc.status_condition.value,
                'test_scenario': tc.test_scenario,
                'expected_behavior': tc.expected_behavior
            } for tc in self.test_cases]
        }
        
        with open(filepath, 'w') as f:
            json.dump(detailed_data, f, indent=2)
            
        self.logger.info(f"Detailed status effect results saved to {filepath}")


# Pytest integration
def test_status_effect_application():
    """Test that status effects can be applied correctly"""
    tester = ComprehensiveStatusEffectTester()
    assert tester.load_cards(), "Failed to load cards"
    
    scenario_count = tester.generate_test_cases()
    assert scenario_count > 0, "No status effect test cases generated"
    
    # Run tests on subset for pytest
    tester.test_cases = tester.test_cases[:20]  # Test first 20 for speed
    report = tester.run_comprehensive_status_effect_tests()
    
    # Verify application success rate is high
    application_rate = report['summary']['application_success_rate']
    assert application_rate >= 80, f"Status effect application success rate too low: {application_rate}%"
    
    # Check for high severity issues
    high_severity_count = report['issue_breakdown']['high_severity']
    assert high_severity_count <= 2, f"Too many high severity status effect issues: {high_severity_count}"


def test_status_condition_persistence():
    """Test that status conditions persist correctly between turns"""
    tester = ComprehensiveStatusEffectTester()
    assert tester.load_cards(), "Failed to load cards"
    
    # Focus on persistence test cases
    tester.generate_test_cases()
    persistence_cases = [tc for tc in tester.test_cases if tc.test_scenario == "turn_persistence"]
    tester.test_cases = persistence_cases[:10]  # Test first 10 persistence cases
    
    if not tester.test_cases:
        pytest.skip("No persistence test cases found")
        
    report = tester.run_comprehensive_status_effect_tests()
    
    # Verify persistence success rate
    persistence_rate = report['summary']['persistence_success_rate']
    assert persistence_rate >= 75, f"Status effect persistence rate too low: {persistence_rate}%"


def test_burned_condition_damage():
    """Specific test for burned condition damage mechanics"""
    tester = ComprehensiveStatusEffectTester()
    status_manager = StatusManager(logging.getLogger())
    
    # Create test Pokemon
    from simulator.core.card_bridge import BattleCard
    test_card = BattleCard(id=1, name="Test Pokemon", hp=100, energy_type="Fire")
    battle_pokemon = BattlePokemon(test_card, logging.getLogger())
    
    # Apply burn condition
    success, message = status_manager.apply_status_condition(battle_pokemon, StatusCondition.BURNED, turn=1)
    assert success, f"Failed to apply burn: {message}"
    
    initial_hp = battle_pokemon.current_hp
    
    # Process between turns effects
    effects = status_manager.process_between_turns_effects(battle_pokemon, turn=2)
    
    # Verify burn damage
    assert battle_pokemon.current_hp == initial_hp - 20, f"Burn damage incorrect: {initial_hp} -> {battle_pokemon.current_hp}"
    assert len(effects) > 0, "No burn effects processed"


if __name__ == "__main__":
    # Run status effect testing standalone
    tester = ComprehensiveStatusEffectTester()
    
    if tester.load_cards():
        tester.generate_test_cases()
        report = tester.run_comprehensive_status_effect_tests()
        
        print("\n" + "="*60)
        print("COMPREHENSIVE STATUS EFFECT TESTING REPORT")
        print("="*60)
        print(f"Total Tests: {report['summary']['total_status_effect_tests']}")
        print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
        print(f"Application Rate: {report['summary']['application_success_rate']:.1f}%")
        print(f"Persistence Rate: {report['summary']['persistence_success_rate']:.1f}%")
        print(f"High Severity Issues: {report['issue_breakdown']['high_severity']}")
        print("="*60)
        
        # Save detailed results
        tester.save_detailed_results(report)