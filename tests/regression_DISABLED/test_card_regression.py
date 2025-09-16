#!/usr/bin/env python3
"""
Comprehensive Card Regression Testing Framework
Catches when updates break existing card functionality by comparing against baseline results
"""

import pytest
import sys
import os
import logging
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from simulator.core.card_bridge import load_real_card_collection, BattleCard
from simulator.core.pokemon import BattlePokemon
from simulator.core.coin_flip import parse_coin_flip_effect, execute_coin_flip_effect, CoinFlipManager
from simulator.core.effect_engine import AdvancedEffectEngine
from simulator.core.status_conditions import StatusManager, StatusCondition
from scripts.test_all_cards import ComprehensiveCardTester


@dataclass
class CardBaseline:
    """Baseline data for a card's expected behavior"""
    card_id: int
    card_name: str
    card_hash: str  # Hash of card data for change detection
    baseline_results: Dict[str, Any]
    test_timestamp: str
    version: str = "1.0"


@dataclass
class RegressionTestResult:
    """Result of a regression test comparison"""
    card_id: int
    card_name: str
    test_name: str
    passed: bool
    baseline_value: Any
    current_value: Any
    difference_detected: bool
    severity: str  # "critical", "major", "minor", "informational"
    description: str


class CardRegressionTester:
    """Comprehensive regression testing system for card functionality"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or self._setup_logger()
        self.cards: List[BattleCard] = []
        self.baselines: Dict[int, CardBaseline] = {}
        self.regression_results: List[RegressionTestResult] = []
        self.baseline_dir = "test_baselines"
        self.results_dir = "test_results"
        
        # Ensure directories exist
        os.makedirs(self.baseline_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for regression tests"""
        logger = logging.getLogger('regression_tester')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def load_cards(self) -> bool:
        """Load all cards for regression testing"""
        try:
            self.logger.info("Loading cards for regression testing...")
            self.cards = load_real_card_collection(self.logger)
            
            if not self.cards:
                self.logger.error("No cards loaded!")
                return False
                
            self.logger.info(f"Loaded {len(self.cards)} cards for regression testing")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load cards: {e}")
            return False
            
    def generate_baseline(self, force_regenerate: bool = False) -> bool:
        """Generate baseline test results for all cards"""
        baseline_file = os.path.join(self.baseline_dir, "card_baselines.json")
        
        # Check if baseline exists and is recent
        if os.path.exists(baseline_file) and not force_regenerate:
            try:
                age_hours = (datetime.now().timestamp() - os.path.getmtime(baseline_file)) / 3600
                if age_hours < 24:  # Baseline is less than 24 hours old
                    self.logger.info(f"Using existing baseline (age: {age_hours:.1f} hours)")
                    return self.load_baseline()
            except:
                pass
                
        self.logger.info("Generating new baseline results...")
        
        # Run comprehensive card tests to generate baseline
        card_tester = ComprehensiveCardTester(self.logger)
        if not card_tester.load_cards():
            self.logger.error("Failed to load cards for baseline generation")
            return False
            
        # Generate baseline data for each card
        baseline_data = []
        
        for i, card in enumerate(self.cards):
            if i % 100 == 0:
                self.logger.info(f"Generating baseline: {i}/{len(self.cards)} cards processed")
                
            baseline = self._generate_card_baseline(card)
            if baseline:
                baseline_data.append(asdict(baseline))
                self.baselines[card.id] = baseline
                
        # Save baseline to file
        baseline_metadata = {
            "generated_timestamp": datetime.now().isoformat(),
            "total_cards": len(baseline_data),
            "version": "1.0",
            "generator": "CardRegressionTester"
        }
        
        with open(baseline_file, 'w') as f:
            json.dump({
                "metadata": baseline_metadata,
                "baselines": baseline_data
            }, f, indent=2)
            
        self.logger.info(f"Baseline generated for {len(baseline_data)} cards and saved to {baseline_file}")
        return True
        
    def load_baseline(self) -> bool:
        """Load existing baseline from file"""
        baseline_file = os.path.join(self.baseline_dir, "card_baselines.json")
        
        if not os.path.exists(baseline_file):
            self.logger.warning("No baseline file found")
            return False
            
        try:
            with open(baseline_file, 'r') as f:
                data = json.load(f)
                
            baseline_data = data.get("baselines", [])
            metadata = data.get("metadata", {})
            
            self.baselines = {}
            for baseline_dict in baseline_data:
                baseline = CardBaseline(**baseline_dict)
                self.baselines[baseline.card_id] = baseline
                
            self.logger.info(f"Loaded baseline for {len(self.baselines)} cards (generated: {metadata.get('generated_timestamp', 'unknown')})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load baseline: {e}")
            return False
            
    def _generate_card_baseline(self, card: BattleCard) -> Optional[CardBaseline]:
        """Generate baseline test results for a single card"""
        try:
            baseline_results = {}
            
            # Basic card data baseline
            baseline_results['basic_data'] = {
                'name': card.name,
                'card_type': card.card_type,
                'energy_type': card.energy_type,
                'hp': card.hp,
                'retreat_cost': card.retreat_cost,
                'attacks_count': len(card.attacks) if card.attacks else 0,
                'abilities_count': len(card.abilities) if card.abilities else 0
            }
            
            # Attack-specific baselines
            if card.attacks:
                baseline_results['attacks'] = []
                for attack in card.attacks:
                    attack_baseline = self._generate_attack_baseline(card, attack)
                    baseline_results['attacks'].append(attack_baseline)
                    
            # Ability-specific baselines
            if card.abilities:
                baseline_results['abilities'] = []
                for ability in card.abilities:
                    ability_baseline = self._generate_ability_baseline(card, ability)
                    baseline_results['abilities'].append(ability_baseline)
                    
            # Pokemon-specific baselines
            if card.is_pokemon():
                baseline_results['pokemon_mechanics'] = self._generate_pokemon_baseline(card)
                
            # Generate card hash for change detection
            card_hash = self._generate_card_hash(card)
            
            return CardBaseline(
                card_id=card.id,
                card_name=card.name,
                card_hash=card_hash,
                baseline_results=baseline_results,
                test_timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate baseline for {card.name}: {e}")
            return None
            
    def _generate_attack_baseline(self, card: BattleCard, attack: Dict[str, Any]) -> Dict[str, Any]:
        """Generate baseline for a specific attack"""
        baseline = {
            'name': attack.get('name', 'Unknown'),
            'cost': attack.get('cost', []),
            'damage': attack.get('damage', 0),
            'effect_text': attack.get('effect_text', ''),
            'has_coin_flip': False,
            'coin_flip_data': None,
            'energy_effects': False,
            'status_effects': False
        }
        
        effect_text = attack.get('effect_text', '').lower()
        
        # Test coin flip mechanics
        if any(word in effect_text for word in ['coin', 'flip', 'heads', 'tails']):
            baseline['has_coin_flip'] = True
            coin_effect = parse_coin_flip_effect(attack.get('effect_text', ''))
            if coin_effect:
                baseline['coin_flip_data'] = coin_effect
                
                # Test deterministic results
                coin_manager = CoinFlipManager(self.logger, rng_seed=42)
                flip_result = execute_coin_flip_effect(coin_effect, coin_manager, 10)
                baseline['coin_flip_baseline'] = flip_result
                
        # Test energy effects
        if any(word in effect_text for word in ['energy', 'attach', 'discard']):
            baseline['energy_effects'] = True
            
        # Test status effects
        if any(word in effect_text for word in ['burn', 'poison', 'paralyz', 'sleep', 'confus']):
            baseline['status_effects'] = True
            
        return baseline
        
    def _generate_ability_baseline(self, card: BattleCard, ability: Dict[str, Any]) -> Dict[str, Any]:
        """Generate baseline for a specific ability"""
        baseline = {
            'name': ability.get('name', 'Unknown'),
            'effect_text': ability.get('effect_text', ''),
            'has_energy_effects': False,
            'has_status_effects': False,
            'has_coin_flips': False
        }
        
        effect_text = ability.get('effect_text', '').lower()
        
        # Check for various effect types
        if any(word in effect_text for word in ['energy', 'attach', 'discard']):
            baseline['has_energy_effects'] = True
            
        if any(word in effect_text for word in ['burn', 'poison', 'paralyz', 'sleep', 'confus']):
            baseline['has_status_effects'] = True
            
        if any(word in effect_text for word in ['coin', 'flip', 'heads', 'tails']):
            baseline['has_coin_flips'] = True
            
        return baseline
        
    def _generate_pokemon_baseline(self, card: BattleCard) -> Dict[str, Any]:
        """Generate baseline for Pokemon-specific mechanics"""
        try:
            battle_pokemon = BattlePokemon(card, self.logger)
            
            baseline = {
                'can_create_battle_pokemon': True,
                'initial_hp': battle_pokemon.current_hp,
                'max_hp': battle_pokemon.max_hp,
                'energy_attachment_works': False,
                'attack_usability': {},
                'ko_detection_works': False
            }
            
            # Test energy attachment
            try:
                initial_energy_count = len(battle_pokemon.energy_attached)
                battle_pokemon.attach_energy('Fire')
                if len(battle_pokemon.energy_attached) > initial_energy_count:
                    baseline['energy_attachment_works'] = True
            except:
                pass
                
            # Test attack usability
            if card.attacks:
                for attack in card.attacks:
                    attack_name = attack.get('name', 'Unknown')
                    can_use_without_energy = battle_pokemon.can_use_attack(attack)
                    
                    # Add required energy
                    for energy_type in attack.get('cost', []):
                        battle_pokemon.attach_energy(energy_type)
                        
                    can_use_with_energy = battle_pokemon.can_use_attack(attack)
                    
                    baseline['attack_usability'][attack_name] = {
                        'without_energy': can_use_without_energy,
                        'with_energy': can_use_with_energy,
                        'energy_cost': attack.get('cost', [])
                    }
                    
            # Test KO detection
            try:
                battle_pokemon.take_damage(battle_pokemon.current_hp)
                baseline['ko_detection_works'] = battle_pokemon.is_knocked_out()
            except:
                pass
                
            return baseline
            
        except Exception as e:
            return {'can_create_battle_pokemon': False, 'error': str(e)}
            
    def _generate_card_hash(self, card: BattleCard) -> str:
        """Generate a hash of card data for change detection"""
        card_data = {
            'name': card.name,
            'card_type': card.card_type,
            'energy_type': card.energy_type,
            'hp': card.hp,
            'attacks': card.attacks,
            'abilities': card.abilities,
            'retreat_cost': card.retreat_cost,
            'weakness': card.weakness
        }
        
        # Convert to string and hash
        card_str = json.dumps(card_data, sort_keys=True)
        return hashlib.md5(card_str.encode()).hexdigest()
        
    def run_regression_tests(self) -> Dict[str, Any]:
        """Run regression tests against baseline"""
        if not self.baselines:
            self.logger.error("No baseline loaded. Generate baseline first.")
            return {}
            
        self.logger.info(f"Running regression tests against baseline with {len(self.baselines)} cards...")
        
        self.regression_results = []
        cards_tested = 0
        cards_with_regressions = 0
        
        for card in self.cards:
            if card.id not in self.baselines:
                self.logger.warning(f"No baseline found for card {card.name} (ID: {card.id})")
                continue
                
            baseline = self.baselines[card.id]
            card_regressions = self._test_card_regression(card, baseline)
            
            if card_regressions:
                cards_with_regressions += 1
                self.regression_results.extend(card_regressions)
                
            cards_tested += 1
            
            if cards_tested % 100 == 0:
                self.logger.info(f"Regression testing progress: {cards_tested}/{len(self.baselines)} cards tested")
                
        # Generate regression report
        report = self._generate_regression_report()
        
        self.logger.info(f"Regression testing completed: {cards_tested} cards tested, {cards_with_regressions} cards with regressions")
        return report
        
    def _test_card_regression(self, card: BattleCard, baseline: CardBaseline) -> List[RegressionTestResult]:
        """Test a single card for regressions against its baseline"""
        regressions = []
        
        try:
            # Test 1: Card data changes
            current_hash = self._generate_card_hash(card)
            if current_hash != baseline.card_hash:
                regressions.append(RegressionTestResult(
                    card_id=card.id,
                    card_name=card.name,
                    test_name="card_data_change",
                    passed=False,
                    baseline_value=baseline.card_hash,
                    current_value=current_hash,
                    difference_detected=True,
                    severity="informational",
                    description="Card data has changed since baseline"
                ))
                
            # Test 2: Basic data consistency
            baseline_basic = baseline.baseline_results.get('basic_data', {})
            current_basic = {
                'name': card.name,
                'card_type': card.card_type,
                'energy_type': card.energy_type,
                'hp': card.hp,
                'retreat_cost': card.retreat_cost,
                'attacks_count': len(card.attacks) if card.attacks else 0,
                'abilities_count': len(card.abilities) if card.abilities else 0
            }
            
            regressions.extend(self._compare_basic_data(card, baseline_basic, current_basic))
            
            # Test 3: Attack regressions
            if card.attacks and baseline.baseline_results.get('attacks'):
                regressions.extend(self._test_attack_regressions(card, baseline.baseline_results['attacks']))
                
            # Test 4: Ability regressions
            if card.abilities and baseline.baseline_results.get('abilities'):
                regressions.extend(self._test_ability_regressions(card, baseline.baseline_results['abilities']))
                
            # Test 5: Pokemon mechanics regressions
            if card.is_pokemon() and baseline.baseline_results.get('pokemon_mechanics'):
                regressions.extend(self._test_pokemon_regressions(card, baseline.baseline_results['pokemon_mechanics']))
                
        except Exception as e:
            regressions.append(RegressionTestResult(
                card_id=card.id,
                card_name=card.name,
                test_name="regression_test_error",
                passed=False,
                baseline_value="N/A",
                current_value=str(e),
                difference_detected=True,
                severity="critical",
                description=f"Regression test failed with error: {str(e)}"
            ))
            
        return regressions
        
    def _compare_basic_data(self, card: BattleCard, baseline_basic: Dict, current_basic: Dict) -> List[RegressionTestResult]:
        """Compare basic card data for regressions"""
        regressions = []
        
        for key, baseline_value in baseline_basic.items():
            current_value = current_basic.get(key)
            
            if baseline_value != current_value:
                severity = "major" if key in ['hp', 'card_type'] else "minor"
                
                regressions.append(RegressionTestResult(
                    card_id=card.id,
                    card_name=card.name,
                    test_name=f"basic_data_{key}",
                    passed=False,
                    baseline_value=baseline_value,
                    current_value=current_value,
                    difference_detected=True,
                    severity=severity,
                    description=f"Basic data field '{key}' changed from {baseline_value} to {current_value}"
                ))
                
        return regressions
        
    def _test_attack_regressions(self, card: BattleCard, baseline_attacks: List[Dict]) -> List[RegressionTestResult]:
        """Test attack-specific regressions"""
        regressions = []
        
        # Create mapping of attack names to current attacks
        current_attacks = {attack.get('name', 'Unknown'): attack for attack in card.attacks}
        
        for baseline_attack in baseline_attacks:
            attack_name = baseline_attack.get('name', 'Unknown')
            current_attack = current_attacks.get(attack_name)
            
            if not current_attack:
                regressions.append(RegressionTestResult(
                    card_id=card.id,
                    card_name=card.name,
                    test_name=f"attack_{attack_name}_missing",
                    passed=False,
                    baseline_value="attack_exists",
                    current_value="attack_missing",
                    difference_detected=True,
                    severity="critical",
                    description=f"Attack '{attack_name}' is missing"
                ))
                continue
                
            # Test coin flip mechanics if present
            if baseline_attack.get('has_coin_flip', False):
                coin_regression = self._test_coin_flip_regression(card, current_attack, baseline_attack)
                if coin_regression:
                    regressions.append(coin_regression)
                    
        return regressions
        
    def _test_coin_flip_regression(self, card: BattleCard, current_attack: Dict, baseline_attack: Dict) -> Optional[RegressionTestResult]:
        """Test coin flip mechanics for regressions"""
        try:
            effect_text = current_attack.get('effect_text', '')
            current_coin_effect = parse_coin_flip_effect(effect_text)
            baseline_coin_data = baseline_attack.get('coin_flip_data')
            
            if not current_coin_effect and baseline_coin_data:
                return RegressionTestResult(
                    card_id=card.id,
                    card_name=card.name,
                    test_name=f"coin_flip_{current_attack.get('name', 'Unknown')}",
                    passed=False,
                    baseline_value="coin_flip_parseable",
                    current_value="coin_flip_not_parseable",
                    difference_detected=True,
                    severity="major",
                    description=f"Coin flip effect no longer parseable for attack {current_attack.get('name', 'Unknown')}"
                )
                
            if current_coin_effect and baseline_coin_data:
                # Test deterministic behavior
                coin_manager = CoinFlipManager(self.logger, rng_seed=42)
                current_result = execute_coin_flip_effect(current_coin_effect, coin_manager, 10)
                baseline_result = baseline_attack.get('coin_flip_baseline')
                
                if current_result != baseline_result:
                    return RegressionTestResult(
                        card_id=card.id,
                        card_name=card.name,
                        test_name=f"coin_flip_behavior_{current_attack.get('name', 'Unknown')}",
                        passed=False,
                        baseline_value=baseline_result,
                        current_value=current_result,
                        difference_detected=True,
                        severity="major",
                        description=f"Coin flip behavior changed for attack {current_attack.get('name', 'Unknown')}"
                    )
                    
        except Exception as e:
            return RegressionTestResult(
                card_id=card.id,
                card_name=card.name,
                test_name=f"coin_flip_test_error_{current_attack.get('name', 'Unknown')}",
                passed=False,
                baseline_value="test_success",
                current_value=str(e),
                difference_detected=True,
                severity="critical",
                description=f"Coin flip test failed with error: {str(e)}"
            )
            
        return None
        
    def _test_ability_regressions(self, card: BattleCard, baseline_abilities: List[Dict]) -> List[RegressionTestResult]:
        """Test ability-specific regressions"""
        regressions = []
        
        # Create mapping of ability names to current abilities
        current_abilities = {ability.get('name', 'Unknown'): ability for ability in card.abilities}
        
        for baseline_ability in baseline_abilities:
            ability_name = baseline_ability.get('name', 'Unknown')
            current_ability = current_abilities.get(ability_name)
            
            if not current_ability:
                regressions.append(RegressionTestResult(
                    card_id=card.id,
                    card_name=card.name,
                    test_name=f"ability_{ability_name}_missing",
                    passed=False,
                    baseline_value="ability_exists",
                    current_value="ability_missing",
                    difference_detected=True,
                    severity="critical",
                    description=f"Ability '{ability_name}' is missing"
                ))
                continue
                
            # Test effect text changes
            baseline_text = baseline_ability.get('effect_text', '')
            current_text = current_ability.get('effect_text', '')
            
            if baseline_text != current_text:
                regressions.append(RegressionTestResult(
                    card_id=card.id,
                    card_name=card.name,
                    test_name=f"ability_{ability_name}_text_changed",
                    passed=False,
                    baseline_value=baseline_text,
                    current_value=current_text,
                    difference_detected=True,
                    severity="minor",
                    description=f"Ability '{ability_name}' effect text changed"
                ))
                
        return regressions
        
    def _test_pokemon_regressions(self, card: BattleCard, baseline_pokemon: Dict) -> List[RegressionTestResult]:
        """Test Pokemon-specific mechanics for regressions"""
        regressions = []
        
        try:
            battle_pokemon = BattlePokemon(card, self.logger)
            
            # Test battle Pokemon creation
            if not baseline_pokemon.get('can_create_battle_pokemon', False):
                if battle_pokemon:  # If we can now create it but couldn't before
                    regressions.append(RegressionTestResult(
                        card_id=card.id,
                        card_name=card.name,
                        test_name="battle_pokemon_creation_fixed",
                        passed=True,
                        baseline_value=False,
                        current_value=True,
                        difference_detected=True,
                        severity="informational",
                        description="Battle Pokemon creation now works (was broken in baseline)"
                    ))
            else:
                # Test HP values
                baseline_hp = baseline_pokemon.get('initial_hp', 0)
                current_hp = battle_pokemon.current_hp
                
                if baseline_hp != current_hp:
                    regressions.append(RegressionTestResult(
                        card_id=card.id,
                        card_name=card.name,
                        test_name="pokemon_initial_hp",
                        passed=False,
                        baseline_value=baseline_hp,
                        current_value=current_hp,
                        difference_detected=True,
                        severity="major",
                        description=f"Initial HP changed from {baseline_hp} to {current_hp}"
                    ))
                    
                # Test energy attachment
                baseline_energy_works = baseline_pokemon.get('energy_attachment_works', False)
                
                initial_energy_count = len(battle_pokemon.energy_attached)
                battle_pokemon.attach_energy('Fire')
                current_energy_works = len(battle_pokemon.energy_attached) > initial_energy_count
                
                if baseline_energy_works != current_energy_works:
                    regressions.append(RegressionTestResult(
                        card_id=card.id,
                        card_name=card.name,
                        test_name="pokemon_energy_attachment",
                        passed=False,
                        baseline_value=baseline_energy_works,
                        current_value=current_energy_works,
                        difference_detected=True,
                        severity="major",
                        description=f"Energy attachment functionality changed"
                    ))
                    
        except Exception as e:
            regressions.append(RegressionTestResult(
                card_id=card.id,
                card_name=card.name,
                test_name="pokemon_regression_test_error",
                passed=False,
                baseline_value="test_success",
                current_value=str(e),
                difference_detected=True,
                severity="critical",
                description=f"Pokemon regression test failed: {str(e)}"
            ))
            
        return regressions
        
    def _generate_regression_report(self) -> Dict[str, Any]:
        """Generate comprehensive regression test report"""
        # Calculate statistics
        total_regressions = len(self.regression_results)
        critical_regressions = len([r for r in self.regression_results if r.severity == "critical"])
        major_regressions = len([r for r in self.regression_results if r.severity == "major"])
        minor_regressions = len([r for r in self.regression_results if r.severity == "minor"])
        informational_regressions = len([r for r in self.regression_results if r.severity == "informational"])
        
        # Group by card
        card_regression_counts = defaultdict(int)
        for regression in self.regression_results:
            card_regression_counts[regression.card_name] += 1
            
        # Group by test type
        test_type_counts = defaultdict(int)
        for regression in self.regression_results:
            test_type = regression.test_name.split('_')[0]
            test_type_counts[test_type] += 1
            
        # Most problematic cards
        most_problematic = sorted(card_regression_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        report = {
            'summary': {
                'total_regressions': total_regressions,
                'critical_regressions': critical_regressions,
                'major_regressions': major_regressions,
                'minor_regressions': minor_regressions,
                'informational_regressions': informational_regressions,
                'cards_with_regressions': len(card_regression_counts),
                'total_cards_tested': len(self.baselines)
            },
            'severity_breakdown': {
                'critical': critical_regressions,
                'major': major_regressions,
                'minor': minor_regressions,
                'informational': informational_regressions
            },
            'test_type_breakdown': dict(test_type_counts),
            'most_problematic_cards': most_problematic,
            'critical_regressions': [
                {
                    'card_name': r.card_name,
                    'test_name': r.test_name,
                    'description': r.description,
                    'baseline_value': r.baseline_value,
                    'current_value': r.current_value
                } for r in self.regression_results if r.severity == "critical"
            ][:20],
            'major_regressions': [
                {
                    'card_name': r.card_name,
                    'test_name': r.test_name,
                    'description': r.description,
                    'baseline_value': r.baseline_value,
                    'current_value': r.current_value
                } for r in self.regression_results if r.severity == "major"
            ][:20],
            'test_timestamp': datetime.now().isoformat(),
            'baseline_timestamp': list(self.baselines.values())[0].test_timestamp if self.baselines else None
        }
        
        return report
        
    def save_regression_results(self, report: Dict[str, Any], filename: str = None):
        """Save regression test results to file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"regression_test_results_{timestamp}.json"
            
        filepath = os.path.join(self.results_dir, filename)
        
        detailed_data = {
            'report': report,
            'all_regressions': [asdict(r) for r in self.regression_results],
            'baseline_info': {
                'total_baselines': len(self.baselines),
                'baseline_timestamp': list(self.baselines.values())[0].test_timestamp if self.baselines else None
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(detailed_data, f, indent=2)
            
        self.logger.info(f"Regression test results saved to {filepath}")


# Pytest integration
def test_regression_suite():
    """Run the full regression test suite"""
    tester = CardRegressionTester()
    
    # Load cards
    assert tester.load_cards(), "Failed to load cards"
    
    # Try to load existing baseline, generate if needed
    if not tester.load_baseline():
        pytest.skip("No baseline found and baseline generation takes too long for pytest")
        
    # Run regression tests
    report = tester.run_regression_tests()
    
    # Check for critical regressions
    critical_count = report['summary']['critical_regressions']
    assert critical_count == 0, f"Found {critical_count} critical regressions"
    
    # Check for too many major regressions
    major_count = report['summary']['major_regressions']
    assert major_count <= 10, f"Too many major regressions: {major_count}"


def test_baseline_generation():
    """Test that baseline generation works"""
    tester = CardRegressionTester()
    assert tester.load_cards(), "Failed to load cards"
    
    # Test generating baseline for a small subset
    tester.cards = tester.cards[:5]  # Only test first 5 cards
    
    success = tester.generate_baseline(force_regenerate=True)
    assert success, "Failed to generate baseline"
    assert len(tester.baselines) > 0, "No baselines generated"


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Card Regression Testing System")
    parser.add_argument("--generate-baseline", action="store_true", help="Generate new baseline")
    parser.add_argument("--force", action="store_true", help="Force regenerate baseline")
    parser.add_argument("--run-tests", action="store_true", help="Run regression tests")
    
    args = parser.parse_args()
    
    tester = CardRegressionTester()
    
    if not tester.load_cards():
        print("Failed to load cards")
        exit(1)
        
    if args.generate_baseline or args.force:
        print("Generating baseline...")
        success = tester.generate_baseline(force_regenerate=args.force)
        if success:
            print("Baseline generation completed successfully")
        else:
            print("Baseline generation failed")
            exit(1)
            
    if args.run_tests:
        print("Running regression tests...")
        if not tester.load_baseline():
            print("No baseline found. Generate baseline first with --generate-baseline")
            exit(1)
            
        report = tester.run_regression_tests()
        
        print("\n" + "="*60)
        print("REGRESSION TEST REPORT")
        print("="*60)
        print(f"Total Regressions: {report['summary']['total_regressions']}")
        print(f"Critical: {report['summary']['critical_regressions']}")
        print(f"Major: {report['summary']['major_regressions']}")
        print(f"Minor: {report['summary']['minor_regressions']}")
        print(f"Cards Affected: {report['summary']['cards_with_regressions']}")
        print("="*60)
        
        if report['summary']['critical_regressions'] > 0:
            print("\nCRITICAL REGRESSIONS:")
            for regression in report['critical_regressions'][:5]:
                print(f"  - {regression['card_name']}: {regression['description']}")
                
        # Save results
        tester.save_regression_results(report)
        
        # Exit with error code if critical regressions found
        if report['summary']['critical_regressions'] > 0:
            exit(1)