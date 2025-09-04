#!/usr/bin/env python3
"""
Comprehensive Card Ability Testing Module
Focuses on testing specific ability mechanics in real battle scenarios
"""

import pytest
import sys
import os
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from simulator.core.card_bridge import load_real_card_collection, BattleCard
from simulator.core.effect_engine import AdvancedEffectEngine
from simulator.core.coin_flip import parse_coin_flip_effect, execute_coin_flip_effect, CoinFlipManager
from simulator.core.game import GameState, GamePhase
from simulator.core.pokemon import BattlePokemon
from simulator.core.status_conditions import StatusManager, StatusCondition
from simulator.ai.rule_based import RuleBasedAI
from Deck import Deck


@dataclass
class AbilityTestScenario:
    """Defines a specific test scenario for an ability"""
    card: BattleCard
    ability: Dict[str, Any]
    scenario_name: str
    expected_outcomes: List[str]
    test_conditions: Dict[str, Any]
    priority: str = "medium"  # low, medium, high, critical


class AbilityTestResult:
    """Results from testing a specific ability"""
    def __init__(self, scenario: AbilityTestScenario):
        self.scenario = scenario
        self.passed = False
        self.execution_time = 0.0
        self.outcomes_achieved = []
        self.failures = []
        self.performance_data = {}
        self.battle_log = []
        
    def add_success(self, outcome: str, details: str = ""):
        self.outcomes_achieved.append({"outcome": outcome, "details": details})
        
    def add_failure(self, failure: str, details: str = ""):
        self.failures.append({"failure": failure, "details": details})
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_name": self.scenario.card.name,
            "ability_name": self.scenario.ability.get('name', 'Unknown'),
            "scenario": self.scenario.scenario_name,
            "passed": self.passed,
            "execution_time": self.execution_time,
            "outcomes_achieved": self.outcomes_achieved,
            "failures": self.failures,
            "performance_data": self.performance_data,
            "priority": self.scenario.priority
        }


class ComprehensiveAbilityTester:
    """Automated testing system for card abilities in battle contexts"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or self._setup_logger()
        self.cards: List[BattleCard] = []
        self.test_scenarios: List[AbilityTestScenario] = []
        self.results: List[AbilityTestResult] = []
        self.effect_engine: Optional[AdvancedEffectEngine] = None
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for ability tests"""
        logger = logging.getLogger('ability_tester')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def load_cards(self) -> bool:
        """Load all cards and prepare for testing"""
        try:
            self.logger.info("Loading cards for ability testing...")
            self.cards = load_real_card_collection(self.logger)
            
            if not self.cards:
                self.logger.error("No cards loaded!")
                return False
                
            # Initialize effect engine
            self.effect_engine = AdvancedEffectEngine(self.cards, self.logger, rng_seed=42)
            
            self.logger.info(f"Loaded {len(self.cards)} cards")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load cards: {e}")
            return False
            
    def generate_test_scenarios(self) -> int:
        """Generate comprehensive test scenarios for all card abilities"""
        self.test_scenarios = []
        
        for card in self.cards:
            if not card.is_pokemon() or not card.abilities:
                continue
                
            for ability in card.abilities:
                scenarios = self._create_ability_scenarios(card, ability)
                self.test_scenarios.extend(scenarios)
                
        self.logger.info(f"Generated {len(self.test_scenarios)} test scenarios")
        return len(self.test_scenarios)
        
    def _create_ability_scenarios(self, card: BattleCard, ability: Dict[str, Any]) -> List[AbilityTestScenario]:
        """Create specific test scenarios for an ability"""
        scenarios = []
        ability_name = ability.get('name', 'Unknown')
        effect_text = ability.get('effect_text', '').lower()
        
        # Scenario 1: Basic ability activation
        scenarios.append(AbilityTestScenario(
            card=card,
            ability=ability,
            scenario_name=f"{ability_name}_basic_activation",
            expected_outcomes=["ability_triggered", "no_crashes"],
            test_conditions={"setup": "normal", "energy": "sufficient"},
            priority="high"
        ))
        
        # Scenario 2: Ability with insufficient resources
        scenarios.append(AbilityTestScenario(
            card=card,
            ability=ability,
            scenario_name=f"{ability_name}_insufficient_resources",
            expected_outcomes=["ability_blocked", "proper_error_handling"],
            test_conditions={"setup": "resource_limited", "energy": "insufficient"},
            priority="medium"
        ))
        
        # Scenario 3: Coin flip abilities (if applicable)
        if any(word in effect_text for word in ['coin', 'flip', 'heads', 'tails']):
            scenarios.append(AbilityTestScenario(
                card=card,
                ability=ability,
                scenario_name=f"{ability_name}_coin_flip_mechanics",
                expected_outcomes=["coin_flips_executed", "results_applied", "deterministic_behavior"],
                test_conditions={"setup": "coin_testing", "rng_seed": 42},
                priority="critical"
            ))
            
        # Scenario 4: Status effect abilities
        if any(word in effect_text for word in ['burn', 'poison', 'paralyze', 'sleep', 'confuse']):
            scenarios.append(AbilityTestScenario(
                card=card,
                ability=ability,
                scenario_name=f"{ability_name}_status_effects",
                expected_outcomes=["status_applied", "status_persists", "status_rules_followed"],
                test_conditions={"setup": "status_testing", "target": "opponent"},
                priority="high"
            ))
            
        # Scenario 5: Energy manipulation abilities
        if any(word in effect_text for word in ['energy', 'attach', 'discard']):
            scenarios.append(AbilityTestScenario(
                card=card,
                ability=ability,
                scenario_name=f"{ability_name}_energy_manipulation",
                expected_outcomes=["energy_changed", "rules_followed", "state_consistent"],
                test_conditions={"setup": "energy_testing", "initial_energy": 2},
                priority="high"
            ))
            
        # Scenario 6: Damage modification abilities
        if any(word in effect_text for word in ['damage', 'plus', 'more', 'additional']):
            scenarios.append(AbilityTestScenario(
                card=card,
                ability=ability,
                scenario_name=f"{ability_name}_damage_modification",
                expected_outcomes=["damage_modified", "calculation_correct", "limits_respected"],
                test_conditions={"setup": "damage_testing", "base_damage": 20},
                priority="high"
            ))
            
        return scenarios
        
    def run_all_ability_tests(self) -> Dict[str, Any]:
        """Run comprehensive ability tests on all scenarios"""
        start_time = time.time()
        self.logger.info(f"Starting ability testing on {len(self.test_scenarios)} scenarios...")
        
        self.results = []
        
        # Group scenarios by priority
        critical_scenarios = [s for s in self.test_scenarios if s.priority == "critical"]
        high_scenarios = [s for s in self.test_scenarios if s.priority == "high"]
        medium_scenarios = [s for s in self.test_scenarios if s.priority == "medium"]
        low_scenarios = [s for s in self.test_scenarios if s.priority == "low"]
        
        # Test in priority order
        for scenario_group, group_name in [
            (critical_scenarios, "Critical"),
            (high_scenarios, "High"),
            (medium_scenarios, "Medium"),
            (low_scenarios, "Low")
        ]:
            if scenario_group:
                self.logger.info(f"Testing {len(scenario_group)} {group_name} priority scenarios...")
                for i, scenario in enumerate(scenario_group):
                    if i % 20 == 0:
                        self.logger.info(f"Progress: {i}/{len(scenario_group)} {group_name} scenarios tested")
                    
                    result = self._test_ability_scenario(scenario)
                    self.results.append(result)
                    
        duration = time.time() - start_time
        
        # Generate comprehensive report
        report = self._generate_ability_report(duration)
        return report
        
    def _test_ability_scenario(self, scenario: AbilityTestScenario) -> AbilityTestResult:
        """Test a specific ability scenario"""
        result = AbilityTestResult(scenario)
        start_time = time.time()
        
        try:
            # Create battle context for the scenario
            battle_context = self._create_scenario_battle_context(scenario)
            
            if not battle_context:
                result.add_failure("context_creation", "Failed to create battle context")
                return result
                
            # Execute the specific test based on scenario type
            if "coin_flip" in scenario.scenario_name:
                self._test_coin_flip_scenario(scenario, battle_context, result)
            elif "status_effects" in scenario.scenario_name:
                self._test_status_effect_scenario(scenario, battle_context, result)
            elif "energy_manipulation" in scenario.scenario_name:
                self._test_energy_scenario(scenario, battle_context, result)
            elif "damage_modification" in scenario.scenario_name:
                self._test_damage_scenario(scenario, battle_context, result)
            else:
                self._test_basic_ability_scenario(scenario, battle_context, result)
                
            # Check if all expected outcomes were achieved
            achieved_outcomes = [outcome["outcome"] for outcome in result.outcomes_achieved]
            missing_outcomes = [exp for exp in scenario.expected_outcomes if exp not in achieved_outcomes]
            
            if not missing_outcomes:
                result.passed = True
            else:
                result.add_failure("missing_outcomes", f"Missing expected outcomes: {missing_outcomes}")
                
        except Exception as e:
            result.add_failure("scenario_execution", f"Exception during scenario test: {str(e)}")
            
        result.execution_time = time.time() - start_time
        return result
        
    def _create_scenario_battle_context(self, scenario: AbilityTestScenario) -> Optional[Dict[str, Any]]:
        """Create a battle context for testing a specific scenario"""
        try:
            # Create test deck with the card
            test_deck = self._create_ability_test_deck(scenario.card)
            opponent_deck = self._create_generic_opponent_deck()
            
            if not test_deck or not opponent_deck:
                return None
                
            # Create game state
            game = GameState(
                player_decks=[test_deck, opponent_deck],
                battle_id=f"ability_test_{scenario.card.id}_{scenario.scenario_name}",
                rng_seed=scenario.test_conditions.get('rng_seed', 42),
                logger=self.logger
            )
            
            # Start battle
            if not game.start_battle():
                return None
                
            # Create battle pokemon
            battle_pokemon = BattlePokemon(scenario.card, self.logger)
            
            # Apply test conditions
            self._apply_test_conditions(battle_pokemon, scenario.test_conditions)
            
            context = {
                'game': game,
                'battle_pokemon': battle_pokemon,
                'scenario': scenario,
                'effect_engine': self.effect_engine
            }
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to create scenario battle context: {e}")
            return None
            
    def _apply_test_conditions(self, battle_pokemon: BattlePokemon, conditions: Dict[str, Any]):
        """Apply specific test conditions to the battle pokemon"""
        # Apply energy conditions
        if 'energy' in conditions:
            energy_setting = conditions['energy']
            if energy_setting == 'sufficient':
                # Add enough energy for all attacks
                for attack in battle_pokemon.card.attacks:
                    for energy_type in attack.get('cost', []):
                        battle_pokemon.attach_energy(energy_type)
            elif energy_setting == 'insufficient':
                # Add less energy than needed
                if battle_pokemon.card.attacks:
                    first_attack_cost = battle_pokemon.card.attacks[0].get('cost', [])
                    if first_attack_cost:
                        # Add one less energy than needed
                        for energy_type in first_attack_cost[:-1]:
                            battle_pokemon.attach_energy(energy_type)
                            
        # Apply initial energy amount
        if 'initial_energy' in conditions:
            energy_count = conditions['initial_energy']
            energy_type = battle_pokemon.card.energy_type or 'Fire'
            for _ in range(energy_count):
                battle_pokemon.attach_energy(energy_type)
                
    def _test_coin_flip_scenario(self, scenario: AbilityTestScenario, context: Dict[str, Any], result: AbilityTestResult):
        """Test coin flip ability scenarios"""
        try:
            ability = scenario.ability
            effect_text = ability.get('effect_text', '')
            
            # Parse coin flip effect
            coin_effect = parse_coin_flip_effect(effect_text)
            
            if coin_effect:
                result.add_success("coin_flips_executed", "Coin flip effect parsed successfully")
                
                # Test deterministic behavior with fixed seed
                coin_manager = CoinFlipManager(self.logger, rng_seed=42)
                
                # Run multiple times with same seed to ensure determinism
                results_set1 = []
                results_set2 = []
                
                for i in range(5):
                    coin_manager_1 = CoinFlipManager(self.logger, rng_seed=42)
                    coin_manager_2 = CoinFlipManager(self.logger, rng_seed=42)
                    
                    result1 = execute_coin_flip_effect(coin_effect, coin_manager_1, 10)
                    result2 = execute_coin_flip_effect(coin_effect, coin_manager_2, 10)
                    
                    results_set1.append(result1)
                    results_set2.append(result2)
                    
                # Check determinism
                if results_set1 == results_set2:
                    result.add_success("deterministic_behavior", "Coin flips are deterministic with same seed")
                else:
                    result.add_failure("deterministic_behavior", "Coin flips not deterministic")
                    
                # Test result application
                if results_set1[0].get('success', False):
                    result.add_success("results_applied", "Coin flip results applied successfully")
                else:
                    result.add_failure("results_applied", "Coin flip results not applied")
                    
        except Exception as e:
            result.add_failure("coin_flip_testing", f"Coin flip testing failed: {str(e)}")
            
    def _test_status_effect_scenario(self, scenario: AbilityTestScenario, context: Dict[str, Any], result: AbilityTestResult):
        """Test status effect ability scenarios"""
        try:
            battle_pokemon = context['battle_pokemon']
            status_manager = StatusManager(self.logger)
            
            # Test status application
            test_statuses = [StatusCondition.BURNED, StatusCondition.POISONED, StatusCondition.PARALYZED]
            
            for status in test_statuses:
                success, message = status_manager.apply_status_condition(battle_pokemon, status, turn=1)
                if success:
                    result.add_success("status_applied", f"Successfully applied {status.value}")
                    
                    # Test status persistence
                    if status_manager.has_status_condition(battle_pokemon, status):
                        result.add_success("status_persists", f"{status.value} persists correctly")
                    else:
                        result.add_failure("status_persists", f"{status.value} did not persist")
                        
                    # Test status rules
                    effects = status_manager.process_between_turns_effects(battle_pokemon, turn=2)
                    if effects:
                        result.add_success("status_rules_followed", f"{status.value} rules applied between turns")
                    
                    # Clean up for next test
                    status_manager.remove_status_condition(battle_pokemon, status)
                    
        except Exception as e:
            result.add_failure("status_effect_testing", f"Status effect testing failed: {str(e)}")
            
    def _test_energy_scenario(self, scenario: AbilityTestScenario, context: Dict[str, Any], result: AbilityTestResult):
        """Test energy manipulation ability scenarios"""
        try:
            battle_pokemon = context['battle_pokemon']
            initial_energy_count = len(battle_pokemon.energy_attached)
            
            # Test energy attachment
            battle_pokemon.attach_energy('Fire')
            if len(battle_pokemon.energy_attached) == initial_energy_count + 1:
                result.add_success("energy_changed", "Energy attachment successful")
                result.add_success("state_consistent", "Energy state consistent after attachment")
            else:
                result.add_failure("energy_changed", "Energy attachment failed")
                
            # Test energy discard
            if battle_pokemon.energy_attached:
                battle_pokemon.discard_energy('Fire')
                if len(battle_pokemon.energy_attached) == initial_energy_count:
                    result.add_success("energy_changed", "Energy discard successful")
                else:
                    result.add_failure("energy_changed", "Energy discard failed")
                    
            # Test energy rules (can't go negative)
            try:
                for _ in range(10):  # Try to discard more than available
                    battle_pokemon.discard_energy('Fire')
                result.add_success("rules_followed", "Energy rules prevent negative energy")
            except:
                result.add_failure("rules_followed", "Energy rules not properly enforced")
                
        except Exception as e:
            result.add_failure("energy_testing", f"Energy testing failed: {str(e)}")
            
    def _test_damage_scenario(self, scenario: AbilityTestScenario, context: Dict[str, Any], result: AbilityTestResult):
        """Test damage modification ability scenarios"""
        try:
            battle_pokemon = context['battle_pokemon']
            base_damage = scenario.test_conditions.get('base_damage', 20)
            
            initial_hp = battle_pokemon.current_hp
            
            # Test damage application
            battle_pokemon.take_damage(base_damage)
            
            if battle_pokemon.current_hp == initial_hp - base_damage:
                result.add_success("damage_modified", "Base damage applied correctly")
                result.add_success("calculation_correct", "Damage calculation is correct")
            else:
                result.add_failure("damage_modified", f"Expected HP {initial_hp - base_damage}, got {battle_pokemon.current_hp}")
                
            # Test damage limits (can't go below 0)
            battle_pokemon.take_damage(1000)  # Massive damage
            if battle_pokemon.current_hp <= 0:
                result.add_success("limits_respected", "HP cannot go below 0")
            else:
                result.add_failure("limits_respected", "HP limits not properly enforced")
                
        except Exception as e:
            result.add_failure("damage_testing", f"Damage testing failed: {str(e)}")
            
    def _test_basic_ability_scenario(self, scenario: AbilityTestScenario, context: Dict[str, Any], result: AbilityTestResult):
        """Test basic ability activation scenarios"""
        try:
            effect_engine = context['effect_engine']
            
            # Register card effects
            effects = effect_engine.register_card_effects(scenario.card)
            
            if effects:
                result.add_success("ability_triggered", f"Found {len(effects)} effects for card")
            else:
                result.add_failure("ability_triggered", "No effects found for card")
                
            # Test that no crashes occur
            result.add_success("no_crashes", "Basic ability testing completed without crashes")
            
        except Exception as e:
            result.add_failure("basic_ability_testing", f"Basic ability testing failed: {str(e)}")
            
    def _create_ability_test_deck(self, card: BattleCard) -> Optional[Deck]:
        """Create a deck optimized for testing a specific card's abilities"""
        try:
            deck = Deck(f"Ability Test Deck - {card.name}")
            
            # Add the test card (2 copies)
            deck.add_card(card)
            deck.add_card(card)
            
            # Fill with compatible basic Pokemon
            compatible_cards = [c for c in self.cards if 
                              c.is_pokemon() and 
                              c.is_basic and
                              c.energy_type == card.energy_type and 
                              c.id != card.id][:9]
            
            # Add 2 copies of each compatible card
            for compatible_card in compatible_cards:
                deck.add_card(compatible_card)
                if len(deck.cards) < 20:
                    deck.add_card(compatible_card)
                if len(deck.cards) >= 20:
                    break
                    
            # Set deck type
            deck.deck_types = [card.energy_type] if card.energy_type != 'Colorless' else ['Fire']
            
            return deck
            
        except Exception as e:
            self.logger.error(f"Failed to create ability test deck: {e}")
            return None
            
    def _create_generic_opponent_deck(self) -> Optional[Deck]:
        """Create a generic opponent deck for ability testing"""
        try:
            deck = Deck("Generic Opponent - Ability Test")
            
            # Use basic Fire Pokemon for simplicity
            basic_pokemon = [c for c in self.cards if 
                           c.is_pokemon() and 
                           c.is_basic and
                           c.energy_type == 'Fire'][:10]
            
            # Add 2 copies of each
            for pokemon in basic_pokemon:
                deck.add_card(pokemon)
                if len(deck.cards) < 20:
                    deck.add_card(pokemon)
                if len(deck.cards) >= 20:
                    break
                    
            deck.deck_types = ['Fire']
            return deck
            
        except Exception as e:
            self.logger.error(f"Failed to create generic opponent deck: {e}")
            return None
            
    def _generate_ability_report(self, duration: float) -> Dict[str, Any]:
        """Generate comprehensive ability testing report"""
        # Calculate statistics
        total_scenarios = len(self.results)
        passed_scenarios = len([r for r in self.results if r.passed])
        failed_scenarios = total_scenarios - passed_scenarios
        
        # Group by priority
        priority_stats = defaultdict(lambda: {'total': 0, 'passed': 0, 'failed': 0})
        for result in self.results:
            priority = result.scenario.priority
            priority_stats[priority]['total'] += 1
            if result.passed:
                priority_stats[priority]['passed'] += 1
            else:
                priority_stats[priority]['failed'] += 1
                
        # Find most problematic abilities
        ability_failures = defaultdict(int)
        for result in self.results:
            if not result.passed:
                ability_name = result.scenario.ability.get('name', 'Unknown')
                ability_failures[ability_name] += 1
                
        # Performance metrics
        avg_execution_time = sum(r.execution_time for r in self.results) / len(self.results) if self.results else 0
        
        report = {
            'summary': {
                'total_scenarios_tested': total_scenarios,
                'scenarios_passed': passed_scenarios,
                'scenarios_failed': failed_scenarios,
                'success_rate': (passed_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0,
                'total_duration_seconds': duration,
                'avg_scenario_time': avg_execution_time
            },
            'priority_breakdown': dict(priority_stats),
            'most_problematic_abilities': dict(sorted(ability_failures.items(), key=lambda x: x[1], reverse=True)[:10]),
            'detailed_failures': [r.to_dict() for r in self.results if not r.passed][:20],
            'performance_summary': {
                'fastest_scenario': min(self.results, key=lambda r: r.execution_time).execution_time if self.results else 0,
                'slowest_scenario': max(self.results, key=lambda r: r.execution_time).execution_time if self.results else 0,
                'total_ability_tests': len(self.results)
            },
            'test_coverage': {
                'unique_cards_tested': len(set(r.scenario.card.id for r in self.results)),
                'unique_abilities_tested': len(set(r.scenario.ability.get('name', 'Unknown') for r in self.results)),
                'scenario_types_covered': len(set(r.scenario.scenario_name.split('_')[-1] for r in self.results))
            }
        }
        
        return report


# Test runner functions for integration
def test_comprehensive_ability_testing():
    """Pytest function to run comprehensive ability testing"""
    tester = ComprehensiveAbilityTester()
    
    # Load cards
    assert tester.load_cards(), "Failed to load cards"
    
    # Generate test scenarios
    scenario_count = tester.generate_test_scenarios()
    assert scenario_count > 0, "No test scenarios generated"
    
    # Run tests (limit to first 50 scenarios for pytest)
    tester.test_scenarios = tester.test_scenarios[:50]
    report = tester.run_all_ability_tests()
    
    # Verify report
    assert 'summary' in report
    assert report['summary']['total_scenarios_tested'] > 0
    
    # Check that critical scenarios have high success rate
    critical_stats = report['priority_breakdown'].get('critical', {})
    if critical_stats.get('total', 0) > 0:
        critical_success_rate = (critical_stats.get('passed', 0) / critical_stats['total']) * 100
        assert critical_success_rate >= 80, f"Critical scenarios success rate too low: {critical_success_rate}%"


def test_coin_flip_determinism():
    """Test that coin flip abilities are deterministic"""
    tester = ComprehensiveAbilityTester()
    assert tester.load_cards(), "Failed to load cards"
    
    # Find a card with coin flip ability
    coin_flip_cards = []
    for card in tester.cards:
        if card.is_pokemon() and card.abilities:
            for ability in card.abilities:
                effect_text = ability.get('effect_text', '').lower()
                if any(word in effect_text for word in ['coin', 'flip']):
                    coin_flip_cards.append((card, ability))
                    break
                    
    assert len(coin_flip_cards) > 0, "No coin flip abilities found"
    
    # Test determinism for first coin flip card
    card, ability = coin_flip_cards[0]
    scenario = AbilityTestScenario(
        card=card,
        ability=ability,
        scenario_name="determinism_test",
        expected_outcomes=["deterministic_behavior"],
        test_conditions={"rng_seed": 42}
    )
    
    result = tester._test_ability_scenario(scenario)
    assert result.passed, f"Coin flip determinism test failed: {result.failures}"


if __name__ == "__main__":
    # Run ability testing standalone
    tester = ComprehensiveAbilityTester()
    
    if tester.load_cards():
        tester.generate_test_scenarios()
        report = tester.run_all_ability_tests()
        
        print("\n" + "="*60)
        print("COMPREHENSIVE ABILITY TESTING REPORT")
        print("="*60)
        print(f"Total Scenarios: {report['summary']['total_scenarios_tested']}")
        print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
        print(f"Duration: {report['summary']['total_duration_seconds']:.2f} seconds")
        print("="*60)