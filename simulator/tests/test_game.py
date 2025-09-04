"""
Test suite for battle game core functionality
"""

import unittest
import logging
from unittest.mock import Mock, patch

# Import existing models
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from Card import Card, CardCollection
from Deck import Deck
from simulator.core.game import GameState, BattleResult, BattleAction, ActionType
from simulator.core.rules import BattleRules


class TestGameCore(unittest.TestCase):
    """Test core game functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.logger = logging.getLogger("test")
        
        # Create multiple different Pokemon cards (need unique names due to 2-copy limit)
        self.fire_pokemon1 = Card(
            id=1, name="Charmander", energy_type="Fire", 
            card_type="Basic Pokémon", hp=60,
            attacks=[{"name": "Scratch", "cost": ["C"], "damage": "10"}],
            weakness="Water", retreat_cost=1
        )
        
        self.fire_pokemon2 = Card(
            id=2, name="Growlithe", energy_type="Fire", 
            card_type="Basic Pokémon", hp=70,
            attacks=[{"name": "Bite", "cost": ["F"], "damage": "20"}],
            weakness="Water", retreat_cost=1
        )
        
        self.water_pokemon1 = Card(
            id=3, name="Squirtle", energy_type="Water", 
            card_type="Basic Pokémon", hp=60,
            attacks=[{"name": "Bubble", "cost": ["W"], "damage": "10"}],
            weakness="Lightning", retreat_cost=1
        )
        
        self.water_pokemon2 = Card(
            id=4, name="Psyduck", energy_type="Water", 
            card_type="Basic Pokémon", hp=70,
            attacks=[{"name": "Water Gun", "cost": ["W", "C"], "damage": "20"}],
            weakness="Lightning", retreat_cost=2
        )
        
        self.colorless_pokemon1 = Card(
            id=5, name="Rattata", energy_type="Colorless", 
            card_type="Basic Pokémon", hp=40,
            attacks=[{"name": "Quick Attack", "cost": ["C"], "damage": "10"}],
            weakness="Fighting", retreat_cost=1
        )
        
        self.colorless_pokemon2 = Card(
            id=6, name="Pidgey", energy_type="Colorless", 
            card_type="Basic Pokémon", hp=50,
            attacks=[{"name": "Gust", "cost": ["C"], "damage": "10"}],
            weakness="Lightning", retreat_cost=1
        )
        
        # Create trainer cards with different names
        self.trainer1 = Card(
            id=7, name="Professor Oak", energy_type="", 
            card_type="Trainer - Supporter", attacks=[]
        )
        
        self.trainer2 = Card(
            id=8, name="Potion", energy_type="", 
            card_type="Trainer - Item", attacks=[]
        )
        
        self.trainer3 = Card(
            id=9, name="Bill", energy_type="", 
            card_type="Trainer - Supporter", attacks=[]
        )
        
        self.trainer4 = Card(
            id=10, name="Switch", energy_type="", 
            card_type="Trainer - Item", attacks=[]
        )
        
        self.trainer5 = Card(
            id=11, name="Energy Search", energy_type="", 
            card_type="Trainer - Item", attacks=[]
        )
        
        # Create sample decks with exactly 20 cards each
        self.deck1 = Deck("Test Fire Deck")
        self.deck2 = Deck("Test Water Deck")
        
        # Add cards to deck 1 (Fire deck: 6 Fire Pokemon, 4 Colorless, 10 Trainers)
        # 2 copies of each Pokemon (max allowed)
        for _ in range(2):
            self.deck1.add_card(self.fire_pokemon1)     # 2x Charmander
            self.deck1.add_card(self.fire_pokemon2)     # 2x Growlithe
            self.deck1.add_card(self.water_pokemon1)    # 2x Squirtle (for variety)
            self.deck1.add_card(self.colorless_pokemon1) # 2x Rattata
            self.deck1.add_card(self.colorless_pokemon2) # 2x Pidgey
            
            # Add trainer cards (2 copies each)
            self.deck1.add_card(self.trainer1)          # 2x Professor Oak
            self.deck1.add_card(self.trainer2)          # 2x Potion
            self.deck1.add_card(self.trainer3)          # 2x Bill
            self.deck1.add_card(self.trainer4)          # 2x Switch
            self.deck1.add_card(self.trainer5)          # 2x Energy Search
            
        # Add cards to deck 2 (Water deck: similar structure)
        for _ in range(2):
            self.deck2.add_card(self.water_pokemon1)    # 2x Squirtle
            self.deck2.add_card(self.water_pokemon2)    # 2x Psyduck
            self.deck2.add_card(self.fire_pokemon1)     # 2x Charmander (for variety)
            self.deck2.add_card(self.colorless_pokemon1) # 2x Rattata
            self.deck2.add_card(self.colorless_pokemon2) # 2x Pidgey
            
            # Add trainer cards (2 copies each)
            self.deck2.add_card(self.trainer1)          # 2x Professor Oak
            self.deck2.add_card(self.trainer2)          # 2x Potion
            self.deck2.add_card(self.trainer3)          # 2x Bill
            self.deck2.add_card(self.trainer4)          # 2x Switch
            self.deck2.add_card(self.trainer5)          # 2x Energy Search
        
        self.deck1.deck_types = ["Fire"]
        self.deck2.deck_types = ["Water"]
    
    def test_game_initialization(self):
        """Test game state initialization"""
        game = GameState(
            player_decks=[self.deck1, self.deck2],
            battle_id="test_battle",
            rng_seed=12345,
            logger=self.logger
        )
        
        self.assertEqual(game.battle_id, "test_battle")
        self.assertEqual(game.turn_number, 0)
        self.assertEqual(game.current_player, 0)
        self.assertEqual(len(game.players), 2)
        self.assertIsNone(game.winner)
        self.assertFalse(game.is_tie)
        self.assertEqual(game.rng_seed, 12345)
    
    def test_invalid_player_count(self):
        """Test that invalid player count raises error"""
        with self.assertRaises(ValueError):
            GameState([self.deck1])  # Only 1 deck
            
        with self.assertRaises(ValueError):
            GameState([self.deck1, self.deck2, self.deck1])  # 3 decks
    
    def test_battle_start(self):
        """Test battle initialization"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        
        success = game.start_battle()
        self.assertTrue(success)
        
        # Check game state after start - should be in initial placement phase
        self.assertEqual(game.turn_number, 0)  # Turn hasn't started yet
        self.assertEqual(game.current_player, 0)  # P0 goes first in placement
        self.assertEqual(game.phase.value, "initial_pokemon_placement")
        
        # Check players have 5-card hands (no active Pokemon placed yet)
        for player in game.players:
            self.assertIsNone(player.active_pokemon)  # Not placed yet
            self.assertEqual(len(player.hand), 5)  # 5 cards as per new rules
    
    def test_action_validation(self):
        """Test action validation"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        success = game.start_battle()
        self.assertTrue(success)  # Ensure battle started successfully
        
        # Valid end turn action
        valid_action = BattleAction(
            action_type=ActionType.END_TURN,
            player_id=0,
            details={}
        )
        is_valid, msg = game.validate_action(valid_action)
        self.assertTrue(is_valid)
        
        # Invalid player turn
        invalid_action = BattleAction(
            action_type=ActionType.END_TURN,
            player_id=1,  # Not current player's turn
            details={}
        )
        is_valid, msg = game.validate_action(invalid_action)
        self.assertFalse(is_valid)
        self.assertIn("Not this player's turn", msg)
    
    def test_energy_attachment_validation(self):
        """Test energy attachment validation"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        success = game.start_battle()
        self.assertTrue(success)  # Ensure battle started successfully
        
        # Player 1 should not be able to attach energy on turn 1
        energy_action = BattleAction(
            action_type=ActionType.ATTACH_ENERGY,
            player_id=0,
            details={"energy_type": "Fire"}
        )
        is_valid, msg = game.validate_action(energy_action)
        self.assertFalse(is_valid)
        self.assertIn("Player 1 cannot attach energy on turn 1", msg)
        
        # Switch to player 2's turn
        game.current_player = 1
        
        # Player 2 should be able to attach energy
        energy_action.player_id = 1
        is_valid, msg = game.validate_action(energy_action)
        self.assertTrue(is_valid)
    
    def test_win_condition_checking(self):
        """Test win condition detection"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        game.start_battle()
        
        # Initially no winner
        self.assertFalse(game.is_battle_over())
        
        # Set one player to max prize points
        game.players[0].prize_points = game.max_prize_points
        self.assertTrue(game.is_battle_over())
        self.assertEqual(game.winner, 0)
        self.assertEqual(game.end_reason, "prize_points")
    
    def test_turn_limit(self):
        """Test turn limit enforcement"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        game.start_battle()
        
        # Set turn number to limit
        game.turn_number = game.max_turns
        
        self.assertTrue(game.is_battle_over())
        self.assertIsNone(game.winner)
        self.assertTrue(game.is_tie)
        self.assertEqual(game.end_reason, "turn_limit")
    
    def test_battle_result_generation(self):
        """Test battle result generation"""
        game = GameState([self.deck1, self.deck2], rng_seed=12345, logger=self.logger)
        game.start_battle()
        
        # End battle with winner
        game._end_battle_winner(1, "test_win")
        
        result = game.get_battle_result()
        
        self.assertIsInstance(result, BattleResult)
        self.assertEqual(result.winner, 1)
        self.assertFalse(result.is_tie)
        self.assertEqual(result.end_reason, "test_win")
        self.assertEqual(result.rng_seed, 12345)
        self.assertEqual(len(result.final_scores), 2)
        self.assertEqual(len(result.deck_types), 2)
    
    def test_action_execution(self):
        """Test action execution"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        game.start_battle()
        
        # Test end turn action
        end_turn_action = BattleAction(
            action_type=ActionType.END_TURN,
            player_id=0,
            details={}
        )
        
        initial_player = game.current_player
        success = game.execute_action(end_turn_action)
        
        self.assertTrue(success)
        self.assertEqual(game.current_player, 1 - initial_player)
    
    def test_game_state_snapshot(self):
        """Test game state snapshot generation"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        game.start_battle()
        
        snapshot = game.get_current_state_snapshot()
        
        required_keys = [
            "turn", "current_player", "phase",
            "player_0_active_hp", "player_1_active_hp",
            "player_0_bench_count", "player_1_bench_count",
            "player_0_prize_points", "player_1_prize_points",
            "player_0_hand_size", "player_1_hand_size"
        ]
        
        for key in required_keys:
            self.assertIn(key, snapshot)
    
    def test_logging_functionality(self):
        """Test that actions are properly logged"""
        game = GameState([self.deck1, self.deck2], logger=self.logger)
        game.start_battle()
        
        initial_log_count = len(game.turn_log)
        
        # Execute an action
        end_turn_action = BattleAction(
            action_type=ActionType.END_TURN,
            player_id=0,
            details={}
        )
        game.execute_action(end_turn_action)
        
        # Check that log was updated
        self.assertGreater(len(game.turn_log), initial_log_count)
        
        # Check log entry structure
        latest_log = game.turn_log[-1]
        self.assertIn("turn", latest_log)
        self.assertIn("player", latest_log)
        self.assertIn("action", latest_log)
        self.assertIn("game_state", latest_log)
        self.assertIn("timestamp", latest_log)


class TestBattleActions(unittest.TestCase):
    """Test battle action classes"""
    
    def test_battle_action_creation(self):
        """Test BattleAction creation and serialization"""
        action = BattleAction(
            action_type=ActionType.ATTACK,
            player_id=1,
            details={"attack_name": "Test Attack", "target": "opponent"}
        )
        
        self.assertEqual(action.action_type, ActionType.ATTACK)
        self.assertEqual(action.player_id, 1)
        self.assertEqual(action.details["attack_name"], "Test Attack")
        
        # Test serialization
        action_dict = action.to_dict()
        self.assertEqual(action_dict["action_type"], "attack")
        self.assertEqual(action_dict["player_id"], 1)
        self.assertEqual(action_dict["details"]["attack_name"], "Test Attack")
    
    def test_battle_result_serialization(self):
        """Test BattleResult serialization"""
        result = BattleResult(
            winner=0,
            is_tie=False,
            total_turns=10,
            final_scores=[3, 1],
            duration_seconds=15.5,
            battle_id="test_battle",
            deck_types=[["Fire"], ["Water"]],
            rng_seed=12345,
            end_reason="prize_points"
        )
        
        result_dict = result.to_dict()
        
        # Check all required fields
        required_fields = [
            "battle_id", "winner", "is_tie", "total_turns",
            "final_scores", "duration_seconds", "deck_types",
            "rng_seed", "end_reason", "timestamp"
        ]
        
        for field in required_fields:
            self.assertIn(field, result_dict)
        
        self.assertEqual(result_dict["winner"], 0)
        self.assertFalse(result_dict["is_tie"])
        self.assertEqual(result_dict["total_turns"], 10)


if __name__ == "__main__":
    # Set up logging for tests
    logging.basicConfig(level=logging.WARNING)
    unittest.main()