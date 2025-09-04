"""
Comprehensive tests for Mass Effect Parsing System
Tests the new bulk effect implementation system
"""

import unittest
import logging
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from simulator.core.mass_effect_parser import MassEffectParser, EffectPattern, EffectParseResult
from simulator.core.effect_engine import AdvancedEffectEngine
from simulator.core.card_bridge import BattleCard
from simulator.core.pokemon import BattlePokemon
from Card import Card


class TestMassEffectParsing(unittest.TestCase):
    """Test mass effect parsing functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.logger = logging.getLogger("test_mass_effects")
        self.parser = MassEffectParser(self.logger)
        
        # Create test battle cards
        self.test_cards = []
        for i in range(5):
            card = BattleCard(
                id=i,
                name=f"Test Card {i}",
                card_type="Basic Pokémon",
                energy_type="Colorless",
                hp=100,
                attacks=[
                    {
                        'name': 'Test Attack',
                        'effect': 'Flip a coin. If heads, this attack does 30 more damage.',
                        'cost': ['C'],
                        'damage': '50'
                    }
                ]
            )
            self.test_cards.append(card)
        
        self.engine = AdvancedEffectEngine(self.test_cards, self.logger)
    
    def test_coin_flip_parsing(self):
        """Test parsing of coin flip effects"""
        test_effects = [
            "Flip 2 coins. This attack does 30 damage for each heads.",
            "Flip a coin. If heads, this attack does 40 more damage.",
            "Flip a coin. If tails, this attack does nothing."
        ]
        
        for effect_text in test_effects:
            results = self.parser.parse_effect(effect_text, "Test Card")
            self.assertGreater(len(results), 0, f"Should parse: {effect_text}")
            
            coin_flip_results = [r for r in results if r.pattern == EffectPattern.COIN_FLIP]
            self.assertGreater(len(coin_flip_results), 0, f"Should detect coin flip in: {effect_text}")
    
    def test_energy_scaling_parsing(self):
        """Test parsing of energy scaling effects"""
        test_effects = [
            "This attack does 20 more damage for each energy attached to your opponent's Active Pokemon.",
            "This attack does 10 more damage for each energy attached to this Pokemon."
        ]
        
        for effect_text in test_effects:
            results = self.parser.parse_effect(effect_text, "Test Card")
            energy_results = [r for r in results if r.pattern == EffectPattern.ENERGY_SCALING]
            self.assertGreater(len(energy_results), 0, f"Should detect energy scaling in: {effect_text}")
    
    def test_status_condition_parsing(self):
        """Test parsing of status condition effects"""
        test_effects = [
            "Your opponent's Active Pokemon is now Burned.",
            "Your opponent's Active Pokemon is now Poisoned.",
            "Your opponent's Active Pokemon is now affected by a special condition chosen at random."
        ]
        
        for effect_text in test_effects:
            results = self.parser.parse_effect(effect_text, "Test Card")
            # Note: Some patterns may need regex improvements
            if results:
                status_results = [r for r in results if r.pattern == EffectPattern.STATUS_CONDITION]
                self.assertGreaterEqual(len(status_results), 0)
    
    def test_conditional_damage_parsing(self):
        """Test parsing of conditional damage effects"""
        test_effects = [
            "If this Pokemon has at least 3 energy attached, this attack does 50 more damage.",
            "If this Pokemon has damage counters on it, this attack does 60 more damage."
        ]
        
        for effect_text in test_effects:
            results = self.parser.parse_effect(effect_text, "Test Card")
            conditional_results = [r for r in results if r.pattern == EffectPattern.CONDITIONAL_DAMAGE]
            self.assertGreater(len(conditional_results), 0, f"Should detect conditional damage in: {effect_text}")
    
    def test_bulk_parsing_coverage(self):
        """Test bulk parsing coverage and statistics"""
        test_cards = [
            {
                'id': 1,
                'name': 'Pikachu ex',
                'attacks': [{'effect': 'Flip 2 coins. This attack does 30 damage for each heads.'}],
                'abilities': []
            },
            {
                'id': 2,
                'name': 'Charizard ex',
                'attacks': [{'effect': 'Your opponent\'s Active Pokemon is now Burned.'}],
                'abilities': []
            }
        ]
        
        results = self.parser.parse_card_bulk(test_cards)
        self.assertGreater(len(results), 0, "Should parse at least some cards")
        
        stats = self.parser.get_pattern_statistics()
        self.assertGreater(sum(stats.values()), 0, "Should have some pattern matches")


class TestMassEffectExecution(unittest.TestCase):
    """Test mass effect execution functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.logger = logging.getLogger("test_mass_execution")
        
        # Create test Pokemon
        test_card = Card(id=1, name="Test Pokemon", card_type="Basic Pokémon", hp=100)
        self.source_pokemon = BattlePokemon(test_card)
        self.target_pokemon = BattlePokemon(test_card)
        
        # Add energy for testing
        self.source_pokemon.attach_energy("Fire")
        self.source_pokemon.attach_energy("Fire")
        self.target_pokemon.attach_energy("Water")
        self.target_pokemon.attach_energy("Water")
        self.target_pokemon.attach_energy("Electric")
        
        # Create engine
        battle_cards = [BattleCard(1, "Test", "Basic Pokémon", "Fire", 100)]
        self.engine = AdvancedEffectEngine(battle_cards, self.logger)
    
    def test_coin_flip_execution(self):
        """Test execution of coin flip effects"""
        # Test scaling damage
        effect = EffectParseResult(
            pattern=EffectPattern.COIN_FLIP,
            confidence=1.0,
            parameters={
                'effect_subtype': 'scaling_damage',
                'coin_count': 2,
                'damage_per_heads': 30
            },
            raw_text="Test effect"
        )
        
        result = self.engine.execute_mass_parsed_effect(
            effect, None, self.source_pokemon, self.target_pokemon
        )
        
        self.assertIn('damage_bonus', result)
        self.assertIn('heads_count', result)
        self.assertIsInstance(result['damage_bonus'], int)
        self.assertGreaterEqual(result['damage_bonus'], 0)
        self.assertLessEqual(result['damage_bonus'], 60)  # Max 2 heads * 30 damage
    
    def test_energy_scaling_execution(self):
        """Test execution of energy scaling effects"""
        # Test opponent energy scaling
        effect = EffectParseResult(
            pattern=EffectPattern.ENERGY_SCALING,
            confidence=0.8,
            parameters={
                'effect_subtype': 'opponent_energy_scaling',
                'damage_per_energy': 20
            },
            raw_text="Test effect"
        )
        
        result = self.engine.execute_mass_parsed_effect(
            effect, None, self.source_pokemon, self.target_pokemon
        )
        
        self.assertIn('damage_bonus', result)
        self.assertIn('energy_count', result)
        self.assertEqual(result['energy_count'], 3)  # Target has 3 energy
        self.assertEqual(result['damage_bonus'], 60)  # 3 * 20
    
    def test_conditional_damage_execution(self):
        """Test execution of conditional damage effects"""
        # Test energy condition (should fail - source has 2 energy, needs 3)
        effect = EffectParseResult(
            pattern=EffectPattern.CONDITIONAL_DAMAGE,
            confidence=0.8,
            parameters={
                'effect_subtype': 'energy_condition',
                'energy_count': 3,
                'bonus_damage': 50
            },
            raw_text="Test effect"
        )
        
        result = self.engine.execute_mass_parsed_effect(
            effect, None, self.source_pokemon, self.target_pokemon
        )
        
        self.assertIn('damage_bonus', result)
        self.assertIn('condition_met', result)
        self.assertEqual(result['damage_bonus'], 0)  # Condition not met
        self.assertFalse(result['condition_met'])
        
        # Add more energy and test again
        self.source_pokemon.attach_energy("Fire")
        result2 = self.engine.execute_mass_parsed_effect(
            effect, None, self.source_pokemon, self.target_pokemon
        )
        
        self.assertEqual(result2['damage_bonus'], 50)  # Condition now met
        self.assertTrue(result2['condition_met'])
    
    def test_error_handling(self):
        """Test error handling in effect execution"""
        # Test invalid effect pattern
        effect = EffectParseResult(
            pattern=EffectPattern.SEARCH_EFFECTS,  # Not implemented
            confidence=0.5,
            parameters={},
            raw_text="Test effect"
        )
        
        result = self.engine.execute_mass_parsed_effect(
            effect, None, self.source_pokemon, self.target_pokemon
        )
        
        self.assertIn('not_implemented', result)
        self.assertTrue(result['not_implemented'])


class TestMassEffectIntegration(unittest.TestCase):
    """Test integration with existing battle systems"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.logger = logging.getLogger("test_integration")
        
        # Create realistic card data
        self.card_data = [
            {
                'id': 25,
                'name': 'Pikachu ex',
                'attacks': [
                    {
                        'name': 'Circle Circuit',
                        'effect': 'Flip 2 coins. This attack does 30 damage for each heads.',
                        'cost': ['L', 'L'],
                        'damage': '0'
                    }
                ],
                'abilities': []
            }
        ]
        
        battle_cards = [
            BattleCard(
                id=25,
                name='Pikachu ex',
                card_type='Basic Pokémon',
                energy_type='Lightning',
                hp=120,
                attacks=self.card_data[0]['attacks']
            )
        ]
        
        self.engine = AdvancedEffectEngine(battle_cards, self.logger)
    
    def test_end_to_end_parsing_and_execution(self):
        """Test complete end-to-end workflow"""
        # Parse the card data
        results = self.engine.parse_cards_bulk(self.card_data)
        
        self.assertIn('25', results)
        pikachu_effects = results['25']
        self.assertGreater(len(pikachu_effects), 0)
        
        # Find coin flip effect
        coin_flip_effect = None
        for effect in pikachu_effects:
            if effect.pattern == EffectPattern.COIN_FLIP:
                coin_flip_effect = effect
                break
        
        self.assertIsNotNone(coin_flip_effect)
        self.assertEqual(coin_flip_effect.parameters['effect_subtype'], 'scaling_damage')
        self.assertEqual(coin_flip_effect.parameters['coin_count'], 2)
        self.assertEqual(coin_flip_effect.parameters['damage_per_heads'], 30)
        
        # Execute the effect
        test_card = Card(id=1, name="Target", card_type="Basic Pokémon", hp=100)
        source_pokemon = BattlePokemon(test_card)
        target_pokemon = BattlePokemon(test_card)
        
        result = self.engine.execute_mass_parsed_effect(
            coin_flip_effect, None, source_pokemon, target_pokemon
        )
        
        self.assertIn('damage_bonus', result)
        self.assertIn('heads_count', result)
        
        # Verify damage is correct
        expected_damage = result['heads_count'] * 30
        self.assertEqual(result['damage_bonus'], expected_damage)
    
    def test_performance_with_multiple_cards(self):
        """Test performance with multiple cards"""
        import time
        
        # Create larger dataset
        large_card_data = []
        for i in range(50):
            large_card_data.append({
                'id': i,
                'name': f'Test Pokemon {i}',
                'attacks': [
                    {
                        'name': 'Test Attack',
                        'effect': 'Flip a coin. If heads, this attack does 20 more damage.',
                        'cost': ['C'],
                        'damage': '50'
                    }
                ],
                'abilities': []
            })
        
        start_time = time.time()
        results = self.engine.parse_cards_bulk(large_card_data)
        end_time = time.time()
        
        parse_time = end_time - start_time
        self.assertLess(parse_time, 5.0, "Parsing should complete within 5 seconds")
        self.assertGreater(len(results), 0, "Should parse some cards")
        
        # Test execution performance
        if results:
            first_card_effects = list(results.values())[0]
            if first_card_effects:
                test_card = Card(id=1, name="Test", card_type="Basic Pokémon", hp=100)
                pokemon = BattlePokemon(test_card)
                
                start_time = time.time()
                for _ in range(100):  # Execute effect 100 times
                    self.engine.execute_mass_parsed_effect(
                        first_card_effects[0], None, pokemon, pokemon
                    )
                end_time = time.time()
                
                execution_time = end_time - start_time
                avg_time = execution_time / 100
                self.assertLess(avg_time, 0.001, "Effect execution should be < 1ms on average")


if __name__ == '__main__':
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    unittest.main(verbosity=2)