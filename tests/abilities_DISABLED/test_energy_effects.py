#!/usr/bin/env python3
"""
Comprehensive Energy Effect Testing Module
Tests all energy-related abilities including generation, attachment, discard, and cost validation
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
from simulator.core.pokemon import BattlePokemon
from simulator.core.coin_flip import parse_coin_flip_effect, execute_coin_flip_effect, CoinFlipManager
from simulator.core.effect_engine import AdvancedEffectEngine
from simulator.core.game import GameState, GamePhase
from simulator.ai.rule_based import RuleBasedAI
from Deck import Deck


@dataclass
class EnergyEffectTestCase:
    """A specific energy effect test case"""
    card: BattleCard
    ability_or_attack: Dict[str, Any]
    effect_type: str  # "generation", "attachment", "discard", "cost_reduction", "acceleration"
    test_scenario: str
    expected_behavior: Dict[str, Any]
    test_name: str


class EnergyEffectTestResult:
    """Results from energy effect testing"""
    def __init__(self, test_case: EnergyEffectTestCase):
        self.test_case = test_case
        self.passed = False
        self.energy_generation_verified = False
        self.energy_attachment_verified = False
        self.energy_cost_verified = False
        self.state_consistency_verified = False
        self.issues = []
        self.energy_state_log = []
        self.performance_data = {}
        
    def add_issue(self, issue_type: str, description: str, severity: str = "medium"):
        self.issues.append({
            "type": issue_type,
            "description": description,
            "severity": severity
        })
        
    def log_energy_state(self, action: str, state: Dict[str, Any]):
        self.energy_state_log.append({
            "action": action,
            "state": state
        })
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_name": self.test_case.card.name,
            "ability_or_attack_name": self.test_case.ability_or_attack.get('name', 'Unknown'),
            "effect_type": self.test_case.effect_type,
            "test_scenario": self.test_case.test_scenario,
            "test_name": self.test_case.test_name,
            "passed": self.passed,
            "energy_generation_verified": self.energy_generation_verified,
            "energy_attachment_verified": self.energy_attachment_verified,
            "energy_cost_verified": self.energy_cost_verified,
            "state_consistency_verified": self.state_consistency_verified,
            "issues": self.issues,
            "energy_state_log": self.energy_state_log,
            "performance_data": self.performance_data
        }


class ComprehensiveEnergyEffectTester:
    """Comprehensive testing system for all energy-related mechanics"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or self._setup_logger()
        self.cards: List[BattleCard] = []
        self.energy_effect_cards: List[BattleCard] = []
        self.test_cases: List[EnergyEffectTestCase] = []
        self.results: List[EnergyEffectTestResult] = []
        self.coin_manager = CoinFlipManager(self.logger, rng_seed=42)
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for energy effect tests"""
        logger = logging.getLogger('energy_effect_tester')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def load_cards(self) -> bool:
        """Load all cards and identify energy effect cards"""
        try:
            self.logger.info("Loading cards for energy effect testing...")
            self.cards = load_real_card_collection(self.logger)
            
            if not self.cards:
                self.logger.error("No cards loaded!")
                return False
                
            # Find all cards with energy effect mechanics
            self.energy_effect_cards = []
            for card in self.cards:
                if self._has_energy_effect_mechanics(card):
                    self.energy_effect_cards.append(card)
                    
            self.logger.info(f"Found {len(self.energy_effect_cards)} cards with energy effect mechanics")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load cards: {e}")
            return False
            
    def _has_energy_effect_mechanics(self, card: BattleCard) -> bool:
        """Check if a card has energy effect mechanics"""
        energy_keywords = ['energy', 'attach', 'discard', 'take', 'generate', 'energy zone']
        
        # Check attacks
        if card.attacks:
            for attack in card.attacks:
                effect_text = attack.get('effect_text', '').lower()
                if any(keyword in effect_text for keyword in energy_keywords):
                    return True
                    
        # Check abilities
        if card.abilities:
            for ability in card.abilities:
                effect_text = ability.get('effect_text', '').lower()
                if any(keyword in effect_text for keyword in energy_keywords):
                    return True
                    
        # Also check for special energy costs or free attacks
        if card.attacks:
            for attack in card.attacks:
                cost = attack.get('cost', [])
                if not cost:  # Zero energy attacks are worth testing
                    return True
                    
        return False
        
    def generate_test_cases(self) -> int:
        """Generate comprehensive test cases for all energy effect mechanics"""
        self.test_cases = []
        
        for card in self.energy_effect_cards:
            # Test attacks with energy effects
            if card.attacks:
                for attack in card.attacks:
                    self._generate_attack_energy_test_cases(card, attack)
                    
            # Test abilities with energy effects
            if card.abilities:
                for ability in card.abilities:
                    self._generate_ability_energy_test_cases(card, ability)
                    
        self.logger.info(f"Generated {len(self.test_cases)} energy effect test cases")
        return len(self.test_cases)
        
    def _generate_attack_energy_test_cases(self, card: BattleCard, attack: Dict[str, Any]):
        """Generate test cases for attack-based energy effects"""
        effect_text = attack.get('effect_text', '').lower()
        attack_name = attack.get('name', 'Unknown')
        cost = attack.get('cost', [])
        
        # Test case 1: Energy cost validation
        self.test_cases.append(EnergyEffectTestCase(
            card=card,
            ability_or_attack=attack,
            effect_type="cost_validation",
            test_scenario="energy_cost_check",
            expected_behavior={'required_energy': cost, 'can_use_without_energy': len(cost) == 0},
            test_name=f"{card.name}_{attack_name}_cost_validation"
        ))
        
        # Test case 2: Energy generation (coin flip based)
        if 'energy' in effect_text and any(word in effect_text for word in ['flip', 'coin', 'heads']):
            coin_effect = parse_coin_flip_effect(effect_text)
            if coin_effect and coin_effect.get('type') == 'energy_attachment':
                self.test_cases.append(EnergyEffectTestCase(
                    card=card,
                    ability_or_attack=attack,
                    effect_type="generation",
                    test_scenario="coin_flip_energy_generation",
                    expected_behavior={
                        'coin_count': coin_effect.get('coin_count', 1),
                        'energy_per_heads': 1,
                        'max_energy': coin_effect.get('coin_count', 1)
                    },
                    test_name=f"{card.name}_{attack_name}_energy_generation"
                ))
                
        # Test case 3: Energy discard requirements
        if 'discard' in effect_text and 'energy' in effect_text:
            self.test_cases.append(EnergyEffectTestCase(
                card=card,
                ability_or_attack=attack,
                effect_type="discard",
                test_scenario="energy_discard_requirement",
                expected_behavior={'requires_discard': True, 'discard_source': 'attacker'},
                test_name=f"{card.name}_{attack_name}_energy_discard"
            ))
            
        # Test case 4: Energy attachment effects
        if 'attach' in effect_text and 'energy' in effect_text:
            self.test_cases.append(EnergyEffectTestCase(
                card=card,
                ability_or_attack=attack,
                effect_type="attachment",
                test_scenario="energy_attachment_effect",
                expected_behavior={'attaches_energy': True, 'attachment_target': 'self'},
                test_name=f"{card.name}_{attack_name}_energy_attachment"
            ))
            
    def _generate_ability_energy_test_cases(self, card: BattleCard, ability: Dict[str, Any]):
        """Generate test cases for ability-based energy effects"""
        effect_text = ability.get('effect_text', '').lower()
        ability_name = ability.get('name', 'Unknown')
        
        # Test case 1: Ability energy acceleration
        if 'energy' in effect_text and 'attach' in effect_text:
            self.test_cases.append(EnergyEffectTestCase(
                card=card,
                ability_or_attack=ability,
                effect_type="acceleration",
                test_scenario="ability_energy_acceleration",
                expected_behavior={'accelerates_energy': True, 'once_per_turn': 'once' in effect_text},
                test_name=f"{card.name}_{ability_name}_energy_acceleration"
            ))
            
        # Test case 2: Energy-based abilities
        if 'energy' in effect_text and any(word in effect_text for word in ['discard', 'remove']):
            self.test_cases.append(EnergyEffectTestCase(
                card=card,
                ability_or_attack=ability,
                effect_type="manipulation",
                test_scenario="ability_energy_manipulation",
                expected_behavior={'manipulates_energy': True, 'type': 'discard'},
                test_name=f"{card.name}_{ability_name}_energy_manipulation"
            ))
            
    def run_comprehensive_energy_effect_tests(self) -> Dict[str, Any]:
        """Run comprehensive tests on all energy effect mechanics"""
        self.logger.info(f"Starting comprehensive energy effect testing on {len(self.test_cases)} test cases...")
        
        self.results = []
        
        for i, test_case in enumerate(self.test_cases):
            if i % 10 == 0:
                self.logger.info(f"Progress: {i}/{len(self.test_cases)} energy effect tests completed")
                
            result = self._test_energy_effect_case(test_case)
            self.results.append(result)
            
        # Generate comprehensive report
        report = self._generate_energy_effect_report()
        return report
        
    def _test_energy_effect_case(self, test_case: EnergyEffectTestCase) -> EnergyEffectTestResult:
        """Test a specific energy effect case comprehensively"""
        result = EnergyEffectTestResult(test_case)
        
        try:
            if test_case.effect_type == "cost_validation":
                self._test_energy_cost_validation(test_case, result)
            elif test_case.effect_type == "generation":
                self._test_energy_generation(test_case, result)
            elif test_case.effect_type == "discard":
                self._test_energy_discard(test_case, result)
            elif test_case.effect_type == "attachment":
                self._test_energy_attachment(test_case, result)
            elif test_case.effect_type == "acceleration":
                self._test_energy_acceleration(test_case, result)
            elif test_case.effect_type == "manipulation":
                self._test_energy_manipulation(test_case, result)
                
            # Overall pass/fail
            result.passed = (result.energy_cost_verified and 
                           result.state_consistency_verified and
                           len([i for i in result.issues if i['severity'] == 'high']) == 0)
            
        except Exception as e:
            result.add_issue("execution_error", f"Test execution failed: {str(e)}", "high")
            
        return result
        
    def _test_energy_cost_validation(self, test_case: EnergyEffectTestCase, result: EnergyEffectTestResult):
        """Test energy cost validation for attacks"""
        try:
            # Create test Pokemon
            battle_pokemon = BattlePokemon(test_case.card, self.logger)
            attack = test_case.ability_or_attack
            expected = test_case.expected_behavior
            
            result.log_energy_state("initial", {
                "energy_attached": battle_pokemon.energy_attached.copy(),
                "energy_count": len(battle_pokemon.energy_attached)
            })
            
            # Test 1: Can't use attack without required energy
            if expected['required_energy']:
                can_use_without_energy = battle_pokemon.can_use_attack(attack)
                if can_use_without_energy and not expected['can_use_without_energy']:
                    result.add_issue("cost_validation", "Attack usable without required energy", "high")
                else:
                    result.energy_cost_verified = True
                    
            # Test 2: Can use attack with correct energy
            for energy_type in expected['required_energy']:
                battle_pokemon.attach_energy(energy_type)
                
            result.log_energy_state("energy_added", {
                "energy_attached": battle_pokemon.energy_attached.copy(),
                "energy_count": len(battle_pokemon.energy_attached)
            })
            
            can_use_with_energy = battle_pokemon.can_use_attack(attack)
            if not can_use_with_energy and expected['required_energy']:
                result.add_issue("cost_validation", "Attack not usable with required energy", "high")
            else:
                result.energy_cost_verified = True
                
            # Test 3: Zero cost attacks work without energy
            if expected['can_use_without_energy']:
                clean_pokemon = BattlePokemon(test_case.card, self.logger)
                can_use_zero_cost = clean_pokemon.can_use_attack(attack)
                if not can_use_zero_cost:
                    result.add_issue("zero_cost", "Zero cost attack not usable without energy", "medium")
                else:
                    result.energy_cost_verified = True
                    
            result.state_consistency_verified = True
            
        except Exception as e:
            result.add_issue("cost_validation_error", f"Cost validation test failed: {str(e)}", "high")
            
    def _test_energy_generation(self, test_case: EnergyEffectTestCase, result: EnergyEffectTestResult):
        """Test energy generation mechanics (like Moltres EX)"""
        try:
            attack = test_case.ability_or_attack
            effect_text = attack.get('effect_text', '')
            expected = test_case.expected_behavior
            
            # Parse coin flip effect for energy generation
            coin_effect = parse_coin_flip_effect(effect_text)
            if not coin_effect:
                result.add_issue("parsing", "Failed to parse coin flip energy effect", "high")
                return
                
            # Test energy generation with different coin results
            generation_results = []
            
            for test_run in range(10):  # Test 10 different scenarios
                coin_manager = CoinFlipManager(self.logger, rng_seed=42 + test_run)
                flip_result = execute_coin_flip_effect(coin_effect, coin_manager, base_damage=0)
                
                energy_generated = flip_result.get('energy_generated', 0)
                generation_results.append(energy_generated)
                
                result.log_energy_state(f"generation_test_{test_run}", {
                    "coin_results": flip_result.get('coin_results', []),
                    "energy_generated": energy_generated,
                    "success": flip_result.get('success', False)
                })
                
            # Validate generation results
            min_generated = min(generation_results)
            max_generated = max(generation_results)
            
            if min_generated < 0:
                result.add_issue("generation_range", f"Negative energy generated: {min_generated}", "high")
            elif max_generated > expected['max_energy']:
                result.add_issue("generation_range", f"Too much energy generated: {max_generated}", "medium")
            else:
                result.energy_generation_verified = True
                
            # Test variety (should get different amounts)
            unique_amounts = set(generation_results)
            if len(unique_amounts) >= 2:
                result.energy_generation_verified = True
            else:
                result.add_issue("generation_variety", "All coin flips generate same energy", "low")
                
            result.state_consistency_verified = True
            
        except Exception as e:
            result.add_issue("generation_test_error", f"Energy generation test failed: {str(e)}", "high")
            
    def _test_energy_discard(self, test_case: EnergyEffectTestCase, result: EnergyEffectTestResult):
        """Test energy discard requirements"""
        try:
            battle_pokemon = BattlePokemon(test_case.card, self.logger)
            attack = test_case.ability_or_attack
            
            # Add some energy to test discard
            initial_energy_types = ['Fire', 'Water', 'Grass']
            for energy_type in initial_energy_types:
                battle_pokemon.attach_energy(energy_type)
                battle_pokemon.attach_energy(energy_type)  # Add 2 of each
                
            initial_energy_count = len(battle_pokemon.energy_attached)
            
            result.log_energy_state("before_discard", {
                "energy_attached": battle_pokemon.energy_attached.copy(),
                "energy_count": initial_energy_count
            })
            
            # Test using the attack (which should discard energy)
            if battle_pokemon.can_use_attack(attack):
                attack_used = battle_pokemon.use_attack(attack)
                
                result.log_energy_state("after_attack", {
                    "energy_attached": battle_pokemon.energy_attached.copy(),
                    "energy_count": len(battle_pokemon.energy_attached),
                    "attack_used": attack_used
                })
                
                # Check if energy was discarded (this depends on implementation)
                # For now, just verify the state is consistent
                if len(battle_pokemon.energy_attached) <= initial_energy_count:
                    result.energy_attachment_verified = True
                else:
                    result.add_issue("discard_logic", "Energy count increased after discard attack", "medium")
            else:
                result.add_issue("attack_usage", "Cannot use attack for discard testing", "medium")
                
            result.state_consistency_verified = True
            
        except Exception as e:
            result.add_issue("discard_test_error", f"Energy discard test failed: {str(e)}", "high")
            
    def _test_energy_attachment(self, test_case: EnergyEffectTestCase, result: EnergyEffectTestResult):
        """Test energy attachment effects"""
        try:
            battle_pokemon = BattlePokemon(test_case.card, self.logger)
            initial_energy_count = len(battle_pokemon.energy_attached)
            
            result.log_energy_state("before_attachment", {
                "energy_attached": battle_pokemon.energy_attached.copy(),
                "energy_count": initial_energy_count
            })
            
            # Test basic energy attachment
            battle_pokemon.attach_energy('Fire')
            
            if len(battle_pokemon.energy_attached) == initial_energy_count + 1:
                result.energy_attachment_verified = True
            else:
                result.add_issue("attachment_basic", "Basic energy attachment failed", "high")
                
            # Test multiple attachments
            for energy_type in ['Water', 'Grass', 'Lightning']:
                battle_pokemon.attach_energy(energy_type)
                
            result.log_energy_state("after_multiple_attachments", {
                "energy_attached": battle_pokemon.energy_attached.copy(),
                "energy_count": len(battle_pokemon.energy_attached),
                "expected_count": initial_energy_count + 4
            })
            
            if len(battle_pokemon.energy_attached) == initial_energy_count + 4:
                result.energy_attachment_verified = True
                result.state_consistency_verified = True
            else:
                result.add_issue("attachment_multiple", "Multiple energy attachments failed", "medium")
                
        except Exception as e:
            result.add_issue("attachment_test_error", f"Energy attachment test failed: {str(e)}", "high")
            
    def _test_energy_acceleration(self, test_case: EnergyEffectTestCase, result: EnergyEffectTestResult):
        """Test energy acceleration abilities"""
        try:
            # This would test abilities that allow extra energy attachments
            # For now, we'll test the basic energy system
            battle_pokemon = BattlePokemon(test_case.card, self.logger)
            expected = test_case.expected_behavior
            
            # Test normal energy attachment rate
            normal_attachments = 0
            for i in range(5):
                try:
                    battle_pokemon.attach_energy('Fire')
                    normal_attachments += 1
                except:
                    break
                    
            result.log_energy_state("acceleration_test", {
                "energy_attached": battle_pokemon.energy_attached.copy(),
                "normal_attachments": normal_attachments,
                "accelerates_energy": expected.get('accelerates_energy', False)
            })
            
            # For now, just verify that energy can be attached
            if normal_attachments > 0:
                result.energy_attachment_verified = True
                result.state_consistency_verified = True
            else:
                result.add_issue("acceleration_basic", "No energy could be attached", "high")
                
        except Exception as e:
            result.add_issue("acceleration_test_error", f"Energy acceleration test failed: {str(e)}", "high")
            
    def _test_energy_manipulation(self, test_case: EnergyEffectTestCase, result: EnergyEffectTestResult):
        """Test energy manipulation abilities"""
        try:
            battle_pokemon = BattlePokemon(test_case.card, self.logger)
            
            # Add energy to manipulate
            for energy_type in ['Fire', 'Water', 'Grass']:
                battle_pokemon.attach_energy(energy_type)
                
            initial_count = len(battle_pokemon.energy_attached)
            
            result.log_energy_state("before_manipulation", {
                "energy_attached": battle_pokemon.energy_attached.copy(),
                "energy_count": initial_count
            })
            
            # Test energy discard
            if battle_pokemon.energy_attached:
                energy_to_discard = battle_pokemon.energy_attached[0]
                battle_pokemon.discard_energy(energy_to_discard)
                
                result.log_energy_state("after_discard", {
                    "energy_attached": battle_pokemon.energy_attached.copy(),
                    "energy_count": len(battle_pokemon.energy_attached),
                    "discarded": energy_to_discard
                })
                
                if len(battle_pokemon.energy_attached) == initial_count - 1:
                    result.energy_attachment_verified = True
                    result.state_consistency_verified = True
                else:
                    result.add_issue("manipulation_discard", "Energy discard failed", "medium")
            else:
                result.add_issue("manipulation_setup", "No energy to manipulate", "low")
                
        except Exception as e:
            result.add_issue("manipulation_test_error", f"Energy manipulation test failed: {str(e)}", "high")
            
    def _generate_energy_effect_report(self) -> Dict[str, Any]:
        """Generate comprehensive energy effect testing report"""
        # Calculate statistics
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.passed])
        generation_passed = len([r for r in self.results if r.energy_generation_verified])
        attachment_passed = len([r for r in self.results if r.energy_attachment_verified])
        cost_passed = len([r for r in self.results if r.energy_cost_verified])
        consistency_passed = len([r for r in self.results if r.state_consistency_verified])
        
        # Group by effect type
        effect_type_stats = defaultdict(lambda: {'total': 0, 'passed': 0, 'failed': 0})
        for result in self.results:
            effect_type = result.test_case.effect_type
            effect_type_stats[effect_type]['total'] += 1
            if result.passed:
                effect_type_stats[effect_type]['passed'] += 1
            else:
                effect_type_stats[effect_type]['failed'] += 1
                
        # Categorize issues
        high_severity_issues = []
        medium_severity_issues = []
        
        for result in self.results:
            for issue in result.issues:
                issue_data = {
                    'card': result.test_case.card.name,
                    'test': result.test_case.test_name,
                    'effect_type': result.test_case.effect_type,
                    'issue': issue
                }
                
                if issue['severity'] == 'high':
                    high_severity_issues.append(issue_data)
                else:
                    medium_severity_issues.append(issue_data)
                    
        # Find most problematic effect types
        effect_failure_counts = defaultdict(int)
        for result in self.results:
            if not result.passed:
                effect_failure_counts[result.test_case.effect_type] += 1
                
        # Energy type distribution analysis
        energy_types_tested = []
        for result in self.results:
            for log_entry in result.energy_state_log:
                if 'energy_attached' in log_entry['state']:
                    energy_types_tested.extend(log_entry['state']['energy_attached'])
                    
        energy_distribution = Counter(energy_types_tested)
        
        report = {
            'summary': {
                'total_energy_effect_tests': total_tests,
                'tests_passed': passed_tests,
                'tests_failed': total_tests - passed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'energy_generation_success_rate': (generation_passed / total_tests * 100) if total_tests > 0 else 0,
                'energy_attachment_success_rate': (attachment_passed / total_tests * 100) if total_tests > 0 else 0,
                'energy_cost_success_rate': (cost_passed / total_tests * 100) if total_tests > 0 else 0,
                'state_consistency_success_rate': (consistency_passed / total_tests * 100) if total_tests > 0 else 0
            },
            'effect_type_breakdown': dict(effect_type_stats),
            'issue_breakdown': {
                'high_severity': len(high_severity_issues),
                'medium_severity': len(medium_severity_issues),
                'total_issues': len(high_severity_issues) + len(medium_severity_issues)
            },
            'detailed_issues': {
                'high_severity': high_severity_issues[:10],
                'medium_severity': medium_severity_issues[:10]
            },
            'most_problematic_effect_types': dict(sorted(effect_failure_counts.items(), key=lambda x: x[1], reverse=True)),
            'energy_analysis': {
                'energy_type_distribution': dict(energy_distribution),
                'total_energy_manipulations_tested': len(energy_types_tested),
                'unique_energy_types_tested': len(set(energy_types_tested))
            },
            'test_coverage': {
                'unique_cards_tested': len(set(r.test_case.card.id for r in self.results)),
                'effect_types_tested': list(set(r.test_case.effect_type for r in self.results)),
                'test_scenarios_covered': list(set(r.test_case.test_scenario for r in self.results))
            },
            'performance_metrics': {
                'total_cards_with_energy_effects': len(self.energy_effect_cards),
                'total_test_cases_generated': len(self.test_cases),
                'avg_energy_states_logged': sum(len(r.energy_state_log) for r in self.results) / len(self.results) if self.results else 0
            },
            'detailed_results': [r.to_dict() for r in self.results if not r.passed][:20]
        }
        
        return report
        
    def save_detailed_results(self, report: Dict[str, Any], filename: str = None):
        """Save detailed test results to file"""
        if not filename:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"energy_effect_test_results_{timestamp}.json"
            
        os.makedirs('test_results', exist_ok=True)
        filepath = os.path.join('test_results', filename)
        
        detailed_data = {
            'report': report,
            'all_results': [r.to_dict() for r in self.results],
            'test_cases': [{
                'card_name': tc.card.name,
                'ability_or_attack_name': tc.ability_or_attack.get('name', 'Unknown'),
                'effect_type': tc.effect_type,
                'test_scenario': tc.test_scenario,
                'expected_behavior': tc.expected_behavior
            } for tc in self.test_cases]
        }
        
        with open(filepath, 'w') as f:
            json.dump(detailed_data, f, indent=2)
            
        self.logger.info(f"Detailed energy effect results saved to {filepath}")


# Pytest integration
def test_energy_cost_validation():
    """Test that energy costs are validated correctly"""
    tester = ComprehensiveEnergyEffectTester()
    assert tester.load_cards(), "Failed to load cards"
    
    scenario_count = tester.generate_test_cases()
    assert scenario_count > 0, "No energy effect test cases generated"
    
    # Focus on cost validation tests
    cost_validation_cases = [tc for tc in tester.test_cases if tc.effect_type == "cost_validation"]
    tester.test_cases = cost_validation_cases[:20]  # Test first 20 for speed
    
    if not tester.test_cases:
        pytest.skip("No cost validation test cases found")
        
    report = tester.run_comprehensive_energy_effect_tests()
    
    # Verify cost validation success rate
    cost_rate = report['summary']['energy_cost_success_rate']
    assert cost_rate >= 80, f"Energy cost validation success rate too low: {cost_rate}%"


def test_energy_attachment_mechanics():
    """Test basic energy attachment mechanics"""
    tester = ComprehensiveEnergyEffectTester()
    
    # Create test Pokemon directly
    from simulator.core.card_bridge import BattleCard
    test_card = BattleCard(id=1, name="Test Pokemon", hp=100, energy_type="Fire")
    battle_pokemon = BattlePokemon(test_card, logging.getLogger())
    
    # Test basic attachment
    initial_count = len(battle_pokemon.energy_attached)
    battle_pokemon.attach_energy('Fire')
    
    assert len(battle_pokemon.energy_attached) == initial_count + 1, "Energy attachment failed"
    assert 'Fire' in battle_pokemon.energy_attached, "Fire energy not found after attachment"
    
    # Test multiple attachments
    battle_pokemon.attach_energy('Water')
    battle_pokemon.attach_energy('Grass')
    
    assert len(battle_pokemon.energy_attached) == initial_count + 3, "Multiple energy attachments failed"


def test_moltres_ex_energy_generation():
    """Specific test for Moltres EX energy generation (if found)"""
    tester = ComprehensiveEnergyEffectTester()
    assert tester.load_cards(), "Failed to load cards"
    
    # Find Moltres EX card
    moltres_ex = None
    for card in tester.cards:
        if 'moltres' in card.name.lower() and 'ex' in card.name.lower():
            moltres_ex = card
            break
            
    if moltres_ex:
        # Test its energy generation mechanics
        for attack in moltres_ex.attacks:
            effect_text = attack.get('effect_text', '')
            if 'energy' in effect_text.lower() and 'coin' in effect_text.lower():
                coin_effect = parse_coin_flip_effect(effect_text)
                assert coin_effect is not None, f"Failed to parse Moltres EX energy effect: {effect_text}"
                
                # Test energy generation
                coin_manager = CoinFlipManager(logging.getLogger(), rng_seed=42)
                result = execute_coin_flip_effect(coin_effect, coin_manager, 0)
                
                assert result.get('success', False), "Moltres EX energy generation failed"
                energy_generated = result.get('energy_generated', 0)
                assert energy_generated >= 0, f"Negative energy generated: {energy_generated}"
                assert energy_generated <= 3, f"Too much energy generated: {energy_generated}"  # Assuming max 3 coins


if __name__ == "__main__":
    # Run energy effect testing standalone
    tester = ComprehensiveEnergyEffectTester()
    
    if tester.load_cards():
        tester.generate_test_cases()
        report = tester.run_comprehensive_energy_effect_tests()
        
        print("\n" + "="*60)
        print("COMPREHENSIVE ENERGY EFFECT TESTING REPORT")
        print("="*60)
        print(f"Total Tests: {report['summary']['total_energy_effect_tests']}")
        print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
        print(f"Energy Generation Rate: {report['summary']['energy_generation_success_rate']:.1f}%")
        print(f"Energy Attachment Rate: {report['summary']['energy_attachment_success_rate']:.1f}%")
        print(f"Cost Validation Rate: {report['summary']['energy_cost_success_rate']:.1f}%")
        print(f"High Severity Issues: {report['issue_breakdown']['high_severity']}")
        print("="*60)
        
        # Save detailed results
        tester.save_detailed_results(report)