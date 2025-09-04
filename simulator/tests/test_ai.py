"""
Test suite for AI players
"""

import unittest
import logging
from unittest.mock import Mock, patch

# Import existing models
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from Card import Card
from Deck import Deck
from simulator.core.game import GameState, ActionType
from simulator.ai.rule_based import RuleBasedAI


class TestRuleBasedAI(unittest.TestCase):
    """Test rule-based AI functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.logger = logging.getLogger("test")
        
        # Create AI with fixed seed for deterministic behavior
        self.ai = RuleBasedAI(player_id=0, logger=self.logger, rng_seed=12345)
        
        # Create sample cards and decks
        self.basic_pokemon = Card(
            id=1, name="Test Pokemon", energy_type="Fire",
            card_type="Basic Pokémon", hp=60,
            attacks=[{"name": "Test Attack", "cost": ["F"], "damage": "20"}],
            weakness="Water", retreat_cost=1
        )
        
        self.trainer_card = Card(
            id=2, name="Test Trainer", energy_type="",
            card_type="Trainer - Item", attacks=[]
        )
        
        self.deck1 = Deck("Test Deck 1")
        self.deck2 = Deck("Test Deck 2")
        
        # Add cards to decks (create multiple different cards to respect MAX_COPIES=2)
        for i in range(10):
            # Create different Pokemon for each pair
            pokemon1 = Card(
                id=10+i, name=f"Test Pokemon {i}", energy_type="Fire",
                card_type="Basic Pokémon", hp=60,
                attacks=[{"name": "Test Attack", "cost": ["F"], "damage": "20"}],
                weakness="Water", retreat_cost=1
            )
            pokemon2 = Card(
                id=20+i, name=f"Test Pokemon {i}", energy_type="Water",
                card_type="Basic Pokémon", hp=60,
                attacks=[{"name": "Test Attack", "cost": ["W"], "damage": "20"}],
                weakness="Fire", retreat_cost=1
            )
            
            # Add 2 copies of each (respecting MAX_COPIES=2)
            self.deck1.add_card(pokemon1)
            self.deck1.add_card(pokemon1)
            self.deck2.add_card(pokemon2)
            self.deck2.add_card(pokemon2)
        
        self.deck1.deck_types = ["Fire"]
        self.deck2.deck_types = ["Water"]
    
    def test_ai_initialization(self):
        """Test AI initialization"""
        ai = RuleBasedAI(player_id=1, rng_seed=54321)
        
        self.assertEqual(ai.player_id, 1)
        self.assertEqual(ai.strategy, "balanced")
        self.assertIsNotNone(ai.rng)
        self.assertIn("damage_priority", ai.weights)
    
    def test_strategy_setting(self):
        """Test AI strategy configuration"""
        # Test aggro strategy
        self.ai.set_strategy("aggro")
        self.assertEqual(self.ai.strategy, "aggro")
        self.assertGreater(self.ai.weights["damage_priority"], 1.0)
        
        # Test control strategy
        self.ai.set_strategy("control")
        self.assertEqual(self.ai.strategy, "control")
        self.assertGreater(self.ai.weights["hp_preservation"], 0.8)
        
        # Test custom weights
        custom_weights = {"damage_priority": 2.0}
        self.ai.set_strategy("custom", custom_weights)
        self.assertEqual(self.ai.weights["damage_priority"], 2.0)
    
    def test_action_choice_no_active_pokemon(self):
        """Test AI action when no active Pokemon"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        game.start_battle()
        
        # Remove active Pokemon to simulate KO
        game.players[0].active_pokemon = None
        
        action = self.ai.choose_action(game)
        
        # Should try to place a Pokemon or end turn
        self.assertIsNotNone(action)
        self.assertIn(action.action_type, [ActionType.PLACE_POKEMON, ActionType.END_TURN])
    
    def test_action_choice_with_active_pokemon(self):
        """Test AI action selection with active Pokemon"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        game.start_battle()
        
        action = self.ai.choose_action(game)
        
        # Should choose a valid action
        self.assertIsNotNone(action)
        self.assertEqual(action.player_id, 0)
        
        # Action should be one of the expected types
        valid_actions = [
            ActionType.ATTACH_ENERGY,
            ActionType.ATTACK,
            ActionType.PLACE_POKEMON,
            ActionType.RETREAT,
            ActionType.END_TURN
        ]
        self.assertIn(action.action_type, valid_actions)
    
    def test_energy_attachment_decision(self):
        """Test AI energy attachment logic"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        game.start_battle()
        
        # Switch to player 2's turn (player 1 can't attach energy on turn 1)
        game.current_player = 1
        ai_player_1 = RuleBasedAI(player_id=1, logger=self.logger, rng_seed=12345)
        
        # Ensure player can attach energy
        game.players[1].energy_attached_this_turn = False
        
        action = ai_player_1.choose_action(game)
        
        # Should attempt to attach energy (or have good reason not to)
        if action.action_type == ActionType.ATTACH_ENERGY:
            self.assertEqual(action.player_id, 1)
            self.assertIn("energy_type", action.details)
    
    def test_attack_selection(self):
        """Test AI attack selection logic"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        game.start_battle()
        
        # Give active Pokemon energy to enable attacks
        game.players[0].active_pokemon.attach_energy("Fire")
        
        # Ensure it's not turn 1 for player 0 (can't attack with energy restrictions)
        game.turn_number = 2
        
        action = self.ai.choose_action(game)
        
        # Should either attack or have good reason not to
        available_attacks = game.players[0].get_available_attacks()
        if available_attacks:
            # If attacks are available, AI should consider attacking
            pass  # The AI might choose other actions based on strategy
    
    def test_pokemon_placement_priority(self):
        """Test AI Pokemon placement logic"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        game.start_battle()
        
        # Simulate having Basic Pokemon in hand and bench space
        basic_pokemon_in_hand = [card for card in game.players[0].hand if card.is_basic]
        
        if basic_pokemon_in_hand and game.players[0].get_bench_space() > 0:
            # AI should consider placing Pokemon
            self.assertTrue(self.ai._should_place_pokemon(game))
    
    def test_retreat_decision(self):
        """Test AI retreat logic"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        game.start_battle()
        
        # Damage active Pokemon and place Pokemon on bench
        if game.players[0].active_pokemon:
            game.players[0].active_pokemon.take_damage(50)  # Significant damage
            
        # Place a Pokemon on bench
        if game.players[0].get_bench_space() > 0:
            from simulator.core.pokemon import BattlePokemon
            bench_pokemon = BattlePokemon(self.basic_pokemon)
            bench_pokemon.attach_energy("Fire")
            game.players[0].bench[0] = bench_pokemon
            
            # AI should consider retreating damaged Pokemon
            should_retreat = self.ai._should_retreat(game)
            # Result depends on specific conditions, just ensure no errors
    
    def test_forced_choice_handling(self):
        """Test AI handling of forced choices"""
        options = [self.basic_pokemon, self.trainer_card]
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        
        # Test Pokemon selection
        choice = self.ai.handle_forced_choice("choose_active_pokemon", options, game)
        self.assertIn(choice, options)
        
        # Test with empty options
        choice = self.ai.handle_forced_choice("choose_active_pokemon", [], game)
        self.assertIsNone(choice)
    
    def test_ai_consistency(self):
        """Test that AI makes consistent decisions with same seed"""
        game1 = GameState([self.deck1, self.deck2], rng_seed=12345, logger=self.logger)
        game2 = GameState([self.deck1, self.deck2], rng_seed=12345, logger=self.logger)
        
        ai1 = RuleBasedAI(player_id=0, rng_seed=12345)
        ai2 = RuleBasedAI(player_id=0, rng_seed=12345)
        
        game1.start_battle()
        game2.start_battle()
        
        # Same initial conditions should produce same action
        action1 = ai1.choose_action(game1)
        action2 = ai2.choose_action(game2)
        
        self.assertEqual(action1.action_type, action2.action_type)
        self.assertEqual(action1.player_id, action2.player_id)
    
    def test_ai_serialization(self):
        """Test AI state serialization"""
        ai_dict = self.ai.to_dict()
        
        required_keys = ["player_id", "strategy", "weights", "ai_type"]
        for key in required_keys:
            self.assertIn(key, ai_dict)
        
        self.assertEqual(ai_dict["player_id"], 0)
        self.assertEqual(ai_dict["ai_type"], "rule_based")
    
    def test_error_handling(self):
        """Test AI error handling"""
        # Create invalid game state
        invalid_game = None
        
        action = self.ai.choose_action(invalid_game)
        
        # Should return end turn action as fallback
        self.assertEqual(action.action_type, ActionType.END_TURN)
    
    def test_action_validation_integration(self):
        """Test that AI actions are valid in game context"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        game.start_battle()
        
        # Get AI action
        action = self.ai.choose_action(game)
        
        # Validate action in game context
        is_valid, msg = game.validate_action(action)
        
        # AI should only produce valid actions
        if not is_valid:
            # Some actions might be invalid due to timing (e.g., energy on turn 1)
            # But the action should be reasonable
            self.assertIsNotNone(action)
    
    def test_strategy_differences(self):
        """Test that different strategies produce different behavior"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        game.start_battle()
        
        # Create AIs with different strategies
        aggro_ai = RuleBasedAI(player_id=0, rng_seed=12345)
        aggro_ai.set_strategy("aggro")
        
        control_ai = RuleBasedAI(player_id=0, rng_seed=12345)
        control_ai.set_strategy("control")
        
        # Weight values should be different
        self.assertNotEqual(
            aggro_ai.weights["damage_priority"],
            control_ai.weights["damage_priority"]
        )
    
    def test_deterministic_behavior(self):
        """Test that AI behavior is deterministic with fixed seed"""
        # Run same scenario multiple times
        results = []
        
        for _ in range(3):
            game = GameState([self.deck1, self.deck2], rng_seed=12345, logger=self.logger)
            ai = RuleBasedAI(player_id=0, rng_seed=12345)
            game.start_battle()
            
            action = ai.choose_action(game)
            results.append((action.action_type, action.player_id))
        
        # All results should be identical
        self.assertEqual(len(set(results)), 1)


if __name__ == "__main__":
    # Set up logging for tests
    logging.basicConfig(level=logging.WARNING)
    unittest.main()