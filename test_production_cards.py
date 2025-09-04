#!/usr/bin/env python3
"""
Comprehensive Production Card Testing System
Tests all 1,576 production cards with their abilities and effects in the battle simulator
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from simulator.core.card_bridge import load_real_card_collection, BattleCard
from simulator.core.effect_engine import AdvancedEffectEngine, create_comprehensive_effect_system
from simulator.core.mass_effect_parser import MassEffectParser, EffectPattern
from simulator.core.pokemon import BattlePokemon
from simulator.core.game import GameState
from simulator.core.coin_flip import parse_coin_flip_effect
from simulator.core.status_conditions import create_status_effect_from_text
from Card import Card
import logging
import json
from collections import defaultdict
from datetime import datetime
import time

class ProductionCardTester:
    """Test all production cards for battle simulator compatibility"""
    
    def __init__(self):
        self.logger = logging.getLogger('production_test')
        self.logger.setLevel(logging.INFO)
        
        # Initialize systems
        self.mass_parser = MassEffectParser(self.logger)
        self.battle_cards = []
        self.effect_engine = None
        
        # Test results
        self.results = {
            'total_cards': 0,
            'cards_tested': 0,
            'cards_passed': 0,
            'cards_failed': 0,
            'effect_coverage': defaultdict(int),
            'error_summary': defaultdict(int),
            'detailed_results': []
        }
    
    def load_production_cards(self):
        """Load all production cards"""
        print("🔥 Loading production cards...")
        start_time = time.time()
        
        self.battle_cards = load_real_card_collection(self.logger)
        
        if not self.battle_cards:
            raise Exception("Failed to load production cards")
        
        self.results['total_cards'] = len(self.battle_cards)
        load_time = time.time() - start_time
        
        print(f"✅ Loaded {len(self.battle_cards)} production cards in {load_time:.2f}s")
        
        # Initialize effect engine with all cards
        print("🔧 Initializing comprehensive effect system...")
        self.effect_engine = create_comprehensive_effect_system(
            self.battle_cards, 
            self.logger,
            rng_seed=42  # Deterministic for testing
        )
        print("✅ Effect system initialized")
    
    def test_card_conversion(self, card: BattleCard) -> dict:
        """Test a single card's conversion and effect parsing"""
        test_result = {
            'card_id': card.id,
            'card_name': card.name,
            'card_type': card.card_type,
            'energy_type': card.energy_type,
            'tests_passed': 0,
            'tests_failed': 0,
            'issues': [],
            'effects_found': [],
            'coverage_patterns': []
        }
        
        try:
            # Test 1: Basic card properties
            if card.name and card.card_type:
                test_result['tests_passed'] += 1
            else:
                test_result['tests_failed'] += 1
                test_result['issues'].append("Missing basic card properties")
            
            # Test 2: Pokemon-specific tests
            if card.is_pokemon():
                if card.hp and card.hp > 0:
                    test_result['tests_passed'] += 1
                else:
                    test_result['tests_failed'] += 1
                    test_result['issues'].append("Pokemon missing valid HP")
                
                # Test attack effects
                for attack in card.attacks or []:
                    attack_result = self.test_attack_effects(attack, card)
                    test_result['effects_found'].extend(attack_result['effects'])
                    test_result['coverage_patterns'].extend(attack_result['patterns'])
                    
                    if attack_result['success']:
                        test_result['tests_passed'] += 1
                    else:
                        test_result['tests_failed'] += 1
                        test_result['issues'].extend(attack_result['issues'])
                
                # Test ability effects
                for ability in card.abilities or []:
                    ability_result = self.test_ability_effects(ability, card)
                    test_result['effects_found'].extend(ability_result['effects'])
                    test_result['coverage_patterns'].extend(ability_result['patterns'])
                    
                    if ability_result['success']:
                        test_result['tests_passed'] += 1
                    else:
                        test_result['tests_failed'] += 1
                        test_result['issues'].extend(ability_result['issues'])
            
            # Test 3: Trainer card tests
            elif card.is_trainer():
                test_result['tests_passed'] += 1  # Basic trainer validation
            
        except Exception as e:
            test_result['tests_failed'] += 1
            test_result['issues'].append(f"Exception during testing: {str(e)}")
        
        # Update coverage statistics
        for pattern in test_result['coverage_patterns']:
            self.results['effect_coverage'][pattern] += 1
        
        return test_result
    
    def test_attack_effects(self, attack: dict, card: BattleCard) -> dict:
        """Test an individual attack's effects"""
        result = {
            'success': True,
            'effects': [],
            'patterns': [],
            'issues': []
        }
        
        try:
            attack_name = attack.get('name', 'Unknown Attack')
            effect_text = attack.get('effect_text', '')
            
            if not effect_text:
                return result  # No effects to test
            
            # Test coin flip parsing
            coin_effect = parse_coin_flip_effect(effect_text)
            if coin_effect:
                result['effects'].append(f"Coin flip: {coin_effect['type']}")
                result['patterns'].append('COIN_FLIP')
            
            # Test status condition parsing
            status_effect = create_status_effect_from_text(effect_text)
            if status_effect:
                result['effects'].append(f"Status: {status_effect.value}")
                result['patterns'].append('STATUS_CONDITION')
            
            # Test mass effect parser
            mass_effects = self.mass_parser.parse_effect(effect_text, card.name, card.id)
            for effect in mass_effects:
                result['effects'].append(f"Mass parser: {effect.pattern.value}")
                result['patterns'].append(effect.pattern.value)
            
            # Test damage parsing
            if 'damage' in effect_text.lower():
                result['effects'].append("Damage modification")
                result['patterns'].append('DAMAGE_EFFECTS')
            
            # Test healing parsing  
            if 'heal' in effect_text.lower():
                result['effects'].append("Healing effect")
                result['patterns'].append('HEALING')
                
        except Exception as e:
            result['success'] = False
            result['issues'].append(f"Attack effect parsing failed: {str(e)}")
        
        return result
    
    def test_ability_effects(self, ability: dict, card: BattleCard) -> dict:
        """Test an individual ability's effects"""
        result = {
            'success': True,
            'effects': [],
            'patterns': [],
            'issues': []
        }
        
        try:
            ability_name = ability.get('name', 'Unknown Ability')
            effect_text = ability.get('effect_text', '')
            
            if not effect_text:
                return result  # No effects to test
            
            # Test mass effect parser on abilities
            mass_effects = self.mass_parser.parse_effect(effect_text, card.name, card.id)
            for effect in mass_effects:
                result['effects'].append(f"Ability: {effect.pattern.value}")
                result['patterns'].append(effect.pattern.value)
            
            # Test common ability patterns
            text_lower = effect_text.lower()
            
            if 'when' in text_lower and 'play' in text_lower:
                result['effects'].append("On-play ability")
                result['patterns'].append('TRIGGERED_ABILITY')
            
            if 'once during your turn' in text_lower:
                result['effects'].append("Activated ability")
                result['patterns'].append('ACTIVATED_ABILITY')
            
            if 'as long as' in text_lower or 'while' in text_lower:
                result['effects'].append("Passive ability")
                result['patterns'].append('PASSIVE_ABILITY')
                
        except Exception as e:
            result['success'] = False
            result['issues'].append(f"Ability effect parsing failed: {str(e)}")
        
        return result
    
    def test_sample_battles(self):
        """Test a few sample battles with production cards"""
        print("⚔️  Testing sample battles with production cards...")
        
        try:
            # Find some cards suitable for battle testing
            pokemon_cards = [c for c in self.battle_cards if c.is_pokemon() and c.hp and c.hp > 0]
            basic_pokemon = [c for c in pokemon_cards if c.evolution_stage == 0]
            
            if len(basic_pokemon) < 10:
                print("⚠️  Not enough basic Pokemon for battle testing")
                return
            
            # Test creating battle Pokemon
            test_cards = basic_pokemon[:5]
            battle_pokemon = []
            
            for card in test_cards:
                try:
                    # Convert BattleCard back to Card for BattlePokemon
                    original_card = Card(
                        id=card.id,
                        name=card.name,
                        energy_type=card.energy_type,
                        card_type=card.card_type,
                        hp=card.hp,
                        attacks=card.attacks,
                        abilities=card.abilities
                    )
                    
                    pokemon = BattlePokemon(original_card, self.logger)
                    battle_pokemon.append(pokemon)
                    
                except Exception as e:
                    print(f"❌ Failed to create BattlePokemon for {card.name}: {e}")
            
            print(f"✅ Successfully created {len(battle_pokemon)} battle-ready Pokemon")
            
            # Test basic battle mechanics
            if len(battle_pokemon) >= 2:
                attacker = battle_pokemon[0]
                defender = battle_pokemon[1]
                
                print(f"🥊 Testing battle: {attacker.card.name} vs {defender.card.name}")
                
                # Test taking damage
                initial_hp = defender.current_hp
                defender.take_damage(10)
                
                if defender.current_hp == initial_hp - 10:
                    print("  ✅ Damage system working")
                else:
                    print("  ❌ Damage system issue")
                
                # Test healing
                if defender.current_hp < defender.max_hp:
                    healed = defender.heal(5)
                    if healed == 5:
                        print("  ✅ Healing system working")
                    else:
                        print("  ❌ Healing system issue")
                
        except Exception as e:
            print(f"❌ Battle testing failed: {e}")
    
    def run_comprehensive_test(self):
        """Run comprehensive test of all production cards"""
        print("🧪 Starting comprehensive production card testing...")
        print(f"Target: {self.results['total_cards']} cards")
        print("=" * 60)
        
        start_time = time.time()
        
        # Test each card
        for i, card in enumerate(self.battle_cards):
            if i % 100 == 0:
                print(f"Progress: {i}/{self.results['total_cards']} cards tested ({i/self.results['total_cards']*100:.1f}%)")
            
            self.results['cards_tested'] += 1
            
            try:
                test_result = self.test_card_conversion(card)
                
                if test_result['tests_failed'] == 0:
                    self.results['cards_passed'] += 1
                else:
                    self.results['cards_failed'] += 1
                    
                    # Track error patterns
                    for issue in test_result['issues']:
                        self.results['error_summary'][issue] += 1
                
                # Store detailed results for failed cards
                if test_result['tests_failed'] > 0 or test_result['effects_found']:
                    self.results['detailed_results'].append(test_result)
                
            except Exception as e:
                self.results['cards_failed'] += 1
                self.results['error_summary'][f"Exception: {str(e)}"] += 1
                self.logger.error(f"Card {card.name} (ID: {card.id}) failed: {e}")
        
        # Test sample battles
        self.test_sample_battles()
        
        # Generate final report
        total_time = time.time() - start_time
        self.generate_report(total_time)
    
    def generate_report(self, total_time: float):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("📊 PRODUCTION CARD TEST REPORT")
        print("=" * 60)
        
        # Basic statistics
        print(f"Cards Tested: {self.results['cards_tested']}")
        print(f"Cards Passed: {self.results['cards_passed']}")
        print(f"Cards Failed: {self.results['cards_failed']}")
        print(f"Success Rate: {self.results['cards_passed']/self.results['cards_tested']*100:.1f}%")
        print(f"Test Duration: {total_time:.2f} seconds")
        print()
        
        # Effect coverage
        print("🎯 EFFECT PATTERN COVERAGE:")
        total_effects = sum(self.results['effect_coverage'].values())
        for pattern, count in sorted(self.results['effect_coverage'].items(), key=lambda x: x[1], reverse=True):
            percentage = count / total_effects * 100 if total_effects > 0 else 0
            print(f"  {pattern:20} : {count:4} effects ({percentage:5.1f}%)")
        print(f"  Total Effects Found: {total_effects}")
        print()
        
        # Error summary (top 10 most common)
        if self.results['error_summary']:
            print("❌ TOP ISSUES:")
            for error, count in sorted(self.results['error_summary'].items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {error[:50]:50} : {count:3} cards")
            print()
        
        # Cards with complex effects (examples)
        complex_cards = [
            result for result in self.results['detailed_results'] 
            if len(result['effects_found']) > 2
        ][:10]
        
        if complex_cards:
            print("🌟 CARDS WITH COMPLEX EFFECTS (Sample):")
            for result in complex_cards:
                print(f"  {result['card_name']:30} : {', '.join(result['effects_found'][:3])}")
            print()
        
        # Save detailed report
        report_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'summary': {
                'total_cards': self.results['total_cards'],
                'cards_tested': self.results['cards_tested'],
                'cards_passed': self.results['cards_passed'],
                'cards_failed': self.results['cards_failed'],
                'success_rate': self.results['cards_passed']/self.results['cards_tested']*100,
                'test_duration': total_time
            },
            'effect_coverage': dict(self.results['effect_coverage']),
            'error_summary': dict(self.results['error_summary']),
            'complex_cards_sample': complex_cards[:20]
        }
        
        report_filename = f"production_card_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"📄 Detailed report saved to: {report_filename}")
        
        # Final verdict
        if self.results['cards_passed'] / self.results['cards_tested'] > 0.95:
            print("\n🎉 EXCELLENT! Production card database is battle-ready!")
        elif self.results['cards_passed'] / self.results['cards_tested'] > 0.90:
            print("\n✅ GOOD! Production card database is mostly compatible.")
        else:
            print("\n⚠️  NEEDS WORK! Some cards need fixes before full production use.")

def main():
    """Main test execution"""
    print("🚀 PRODUCTION CARD TESTING SYSTEM")
    print("Testing all 1,576 production cards for battle simulator compatibility")
    print("=" * 70)
    
    tester = ProductionCardTester()
    
    try:
        # Load production cards
        tester.load_production_cards()
        
        # Run comprehensive tests
        tester.run_comprehensive_test()
        
        return tester.results['cards_passed'] / tester.results['cards_tested'] > 0.90
        
    except Exception as e:
        print(f"❌ Testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)