"""
Test suite for battle rules engine
"""

import unittest
import logging

# Import existing models
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from Card import Card
from Deck import Deck
from simulator.core.rules import RulesEngine, BattleRules, WinCondition
from simulator.core.pokemon import BattlePokemon
from simulator.core.game import GameState


class TestBattleRules(unittest.TestCase):
    """Test BattleRules configuration"""
    
    def test_default_rules(self):
        """Test default rule values"""
        rules = BattleRules()
        
        self.assertEqual(rules.max_deck_size, 20)
        self.assertEqual(rules.max_card_copies, 2)
        self.assertEqual(rules.max_hand_size, 10)
        self.assertEqual(rules.max_bench_size, 3)
        self.assertEqual(rules.max_prize_points, 3)
        self.assertEqual(rules.max_turns, 100)
        self.assertEqual(rules.weakness_damage_bonus, 20)
        self.assertTrue(rules.require_basic_pokemon)
        self.assertTrue(rules.player_1_no_energy_turn_1)
    
    def test_custom_rules(self):
        """Test custom rule configuration"""
        rules = BattleRules(
            max_prize_points=5,
            weakness_damage_bonus=30,
            max_turns=50
        )
        
        self.assertEqual(rules.max_prize_points, 5)
        self.assertEqual(rules.weakness_damage_bonus, 30)
        self.assertEqual(rules.max_turns, 50)
        # Other rules should remain default
        self.assertEqual(rules.max_deck_size, 20)
    
    def test_rules_serialization(self):
        """Test rules to_dict method"""
        rules = BattleRules()
        rules_dict = rules.to_dict()
        
        required_keys = [
            "max_deck_size", "max_card_copies", "max_hand_size",
            "max_bench_size", "max_prize_points", "max_turns",
            "weakness_damage_bonus", "require_basic_pokemon"
        ]
        
        for key in required_keys:
            self.assertIn(key, rules_dict)


class TestRulesEngine(unittest.TestCase):
    """Test RulesEngine functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.logger = logging.getLogger("test")
        self.rules = BattleRules()
        self.engine = RulesEngine(self.rules, self.logger)
        
        # Create test cards
        self.basic_pokemon = Card(
            id=1, name="Test Pokemon", energy_type="Fire",
            card_type="Basic Pokémon", hp=60,
            attacks=[{"name": "Test Attack", "cost": ["F"], "damage": "20"}],
            weakness="Water", retreat_cost=1
        )
        
        self.evolution_pokemon = Card(
            id=2, name="Test Evolution", energy_type="Fire",
            card_type="Stage 1 Pokémon", hp=90,
            attacks=[{"name": "Strong Attack", "cost": ["F", "F"], "damage": "40"}],
            weakness="Water", retreat_cost=2
        )
        
        self.trainer_card = Card(
            id=3, name="Test Trainer", energy_type="",
            card_type="Trainer - Item", attacks=[]
        )
    
    def test_valid_deck_validation(self):
        """Test validation of a valid deck"""
        deck = Deck("Valid Deck")
        
        # Create multiple different trainer cards to avoid copy limit
        trainer_cards = []
        for i in range(8):  # Create 8 different trainer cards
            trainer_cards.append(Card(
                id=10+i, name=f"Test Trainer {i+1}", energy_type="",
                card_type="Trainer - Item", attacks=[]
            ))
        
        # Add exactly 20 cards with valid composition
        # Add 2 copies of basic Pokemon (respects MAX_COPIES and provides required basic)
        for i in range(2):
            deck.add_card(self.basic_pokemon)
        # Add 2 copies of evolution Pokemon  
        for i in range(2):
            deck.add_card(self.evolution_pokemon)
        # Add trainer cards (2 copies each of 8 different trainers = 16 cards)
        for trainer in trainer_cards:
            for i in range(2):
                deck.add_card(trainer)
        
        is_valid, errors = self.engine.validate_deck(deck)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_invalid_deck_size(self):
        """Test deck size validation"""
        deck = Deck("Invalid Size Deck")
        
        # Add only 19 cards
        for i in range(19):
            deck.add_card(self.basic_pokemon)
        
        is_valid, errors = self.engine.validate_deck(deck)
        
        self.assertFalse(is_valid)
        self.assertTrue(any("must contain exactly 20 cards" in error for error in errors))
    
    def test_too_many_card_copies(self):
        """Test card copy limit validation"""
        deck = Deck("Too Many Copies Deck")
        
        # Manually add 3 copies by bypassing the add_card limit enforcement
        # (since add_card enforces the limit we're trying to test)
        for i in range(3):
            deck.cards.append(self.basic_pokemon)
        deck.card_counts[self.basic_pokemon.name] = 3
        
        # Add trainer cards normally
        for i in range(17):
            deck.add_card(self.trainer_card)
        
        is_valid, errors = self.engine.validate_deck(deck)
        
        self.assertFalse(is_valid)
        self.assertTrue(any("Too many copies" in error for error in errors))
    
    def test_no_basic_pokemon(self):
        """Test basic Pokemon requirement"""
        deck = Deck("No Basic Pokemon Deck")
        
        # Add only non-Basic cards
        for i in range(20):
            deck.add_card(self.trainer_card)
        
        is_valid, errors = self.engine.validate_deck(deck)
        
        self.assertFalse(is_valid)
        self.assertTrue(any("at least one Basic Pokémon" in error for error in errors))
    
    def test_hand_size_validation(self):
        """Test hand size limit validation"""
        is_valid, msg = self.engine.validate_hand_size(10)  # At limit
        self.assertTrue(is_valid)
        
        is_valid, msg = self.engine.validate_hand_size(11)  # Over limit
        self.assertFalse(is_valid)
        self.assertIn("exceeds maximum", msg)
    
    def test_bench_size_validation(self):
        """Test bench size limit validation"""
        is_valid, msg = self.engine.validate_bench_size(3)  # At limit
        self.assertTrue(is_valid)
        
        is_valid, msg = self.engine.validate_bench_size(4)  # Over limit
        self.assertFalse(is_valid)
        self.assertIn("exceeds maximum", msg)
    
    def test_energy_attachment_rules(self):
        """Test energy attachment rule validation"""
        # Player 1, turn 1 - should not be allowed
        can_attach, reason = self.engine.can_attach_energy(
            turn_number=1, player_id=0, already_attached=False
        )
        self.assertFalse(can_attach)
        self.assertIn("Player 1 cannot attach energy on turn 1", reason)
        
        # Player 2, turn 1 - should be allowed
        can_attach, reason = self.engine.can_attach_energy(
            turn_number=1, player_id=1, already_attached=False
        )
        self.assertTrue(can_attach)
        
        # Already attached this turn - should not be allowed
        can_attach, reason = self.engine.can_attach_energy(
            turn_number=2, player_id=0, already_attached=True
        )
        self.assertFalse(can_attach)
        self.assertIn("already attached", reason)
    
    def test_attack_validation(self):
        """Test attack validation"""
        attacker = BattlePokemon(self.basic_pokemon)
        target = BattlePokemon(self.basic_pokemon)
        
        # Add energy to attacker
        attacker.attach_energy("Fire")
        
        attack = {"name": "Test Attack", "cost": ["F"], "damage": "20"}
        
        # Valid attack
        is_valid, msg = self.engine.validate_attack(attacker, attack, target)
        self.assertTrue(is_valid)
        
        # Attacker knocked out
        attacker.current_hp = 0
        is_valid, msg = self.engine.validate_attack(attacker, attack, target)
        self.assertFalse(is_valid)
        self.assertIn("knocked out", msg)
    
    def test_damage_calculation(self):
        """Test damage calculation with weakness"""
        fire_pokemon = BattlePokemon(self.basic_pokemon)  # Fire type
        water_pokemon = BattlePokemon(Card(
            id=4, name="Water Pokemon", energy_type="Water",
            card_type="Basic Pokémon", hp=60,
            weakness="Lightning"  # Not weak to Fire
        ))
        grass_pokemon = BattlePokemon(Card(
            id=5, name="Grass Pokemon", energy_type="Grass", 
            card_type="Basic Pokémon", hp=60,
            weakness="Fire"  # Weak to Fire
        ))
        
        attack = {"name": "Test Attack", "cost": ["F"], "damage": "20"}
        
        # No weakness
        damage = self.engine.calculate_damage(attack, fire_pokemon, water_pokemon)
        self.assertEqual(damage, 20)
        
        # With weakness
        damage = self.engine.calculate_damage(attack, fire_pokemon, grass_pokemon)
        self.assertEqual(damage, 40)  # 20 + 20 weakness bonus
    
    def test_prize_points_calculation(self):
        """Test prize points for different Pokemon types"""
        normal_pokemon = BattlePokemon(self.basic_pokemon)
        ex_pokemon = BattlePokemon(Card(
            id=6, name="Test Pokemon ex", energy_type="Fire",
            card_type="Basic Pokémon", hp=120
        ))
        
        # Normal Pokemon = 1 point
        points = self.engine.get_prize_points_for_knockout(normal_pokemon)
        self.assertEqual(points, 1)
        
        # EX Pokemon = 2 points
        points = self.engine.get_prize_points_for_knockout(ex_pokemon)
        self.assertEqual(points, 2)
    
    def test_retreat_validation(self):
        """Test retreat validation"""
        retreating_pokemon = BattlePokemon(self.basic_pokemon)
        replacement_pokemon = BattlePokemon(self.basic_pokemon)
        
        # No energy attached - cannot retreat (retreat cost = 1)
        is_valid, msg = self.engine.validate_retreat(retreating_pokemon, replacement_pokemon)
        self.assertFalse(is_valid)
        self.assertIn("Insufficient energy", msg)
        
        # Add enough energy
        retreating_pokemon.attach_energy("Fire")
        is_valid, msg = self.engine.validate_retreat(retreating_pokemon, replacement_pokemon)
        self.assertTrue(is_valid)
        
        # Replacement Pokemon knocked out
        replacement_pokemon.current_hp = 0
        is_valid, msg = self.engine.validate_retreat(retreating_pokemon, replacement_pokemon)
        self.assertFalse(is_valid)
        self.assertIn("not valid", msg)
    
    def test_pokemon_placement_validation(self):
        """Test Pokemon placement validation"""
        # Valid basic Pokemon placement
        is_valid, msg = self.engine.validate_pokemon_placement(
            card=self.basic_pokemon,
            position="active",
            current_bench_count=0,
            has_active=False
        )
        self.assertTrue(is_valid)
        
        # Non-Pokemon card
        is_valid, msg = self.engine.validate_pokemon_placement(
            card=self.trainer_card,
            position="active", 
            current_bench_count=0,
            has_active=False
        )
        self.assertFalse(is_valid)
        self.assertIn("not a Pokémon", msg)
        
        # Evolution Pokemon (should fail - only Basic allowed from hand)
        is_valid, msg = self.engine.validate_pokemon_placement(
            card=self.evolution_pokemon,
            position="active",
            current_bench_count=0,
            has_active=False
        )
        self.assertFalse(is_valid)
        self.assertIn("not a Basic Pokémon", msg)
        
        # Bench full
        is_valid, msg = self.engine.validate_pokemon_placement(
            card=self.basic_pokemon,
            position="bench",
            current_bench_count=3,  # Max bench size
            has_active=True
        )
        self.assertFalse(is_valid)
        self.assertIn("Bench is full", msg)
    
    def test_hand_limit_enforcement(self):
        """Test hand size limit enforcement"""
        # Create oversized hand
        oversized_hand = [self.trainer_card for _ in range(15)]
        
        limited_hand = self.engine.enforce_hand_limit(oversized_hand)
        
        self.assertEqual(len(limited_hand), self.rules.max_hand_size)
        self.assertLessEqual(len(limited_hand), len(oversized_hand))
    
    def test_rules_summary(self):
        """Test rules summary generation"""
        summary = self.engine.get_rules_summary()
        
        required_sections = ["deck_rules", "game_rules", "energy_rules", "damage_rules"]
        for section in required_sections:
            self.assertIn(section, summary)
    
    def test_win_condition_checking(self):
        """Test win condition detection with mock game state"""
        # Create mock game state
        game_state = type('MockGameState', (), {})()
        game_state.turn_number = 10
        game_state.players = []
        
        # Create mock players
        for i in range(2):
            player = type('MockPlayer', (), {})()
            player.prize_points = 0
            player.can_continue_battle = lambda: True
            game_state.players.append(player)
        
        # No win condition initially
        condition, winner, reason = self.engine.check_win_condition(game_state)
        self.assertIsNone(condition)
        self.assertIsNone(winner)
        
        # Prize points victory
        game_state.players[0].prize_points = self.rules.max_prize_points
        condition, winner, reason = self.engine.check_win_condition(game_state)
        self.assertEqual(condition, WinCondition.PRIZE_POINTS)
        self.assertEqual(winner, 0)
        
        # Reset and test turn limit
        game_state.players[0].prize_points = 0
        game_state.turn_number = self.rules.max_turns
        condition, winner, reason = self.engine.check_win_condition(game_state)
        self.assertEqual(condition, WinCondition.TURN_LIMIT)
        self.assertIsNone(winner)


if __name__ == "__main__":
    # Set up logging for tests
    logging.basicConfig(level=logging.WARNING)
    unittest.main()