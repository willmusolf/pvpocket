"""
Integration tests for the complete battle simulator
"""

import unittest
import logging
import time

# Import existing models
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from Card import Card, CardCollection
from Deck import Deck
from simulator.core.game import GameState, BattleResult
from simulator.ai.rule_based import RuleBasedAI


class TestBattleIntegration(unittest.TestCase):
    """Integration tests for complete battle scenarios"""
    
    def _get_acting_player_and_ai(self, game, ai_players):
        """Get the player and AI that should act in current game state"""
        from simulator.core.game import GamePhase
        if game.phase == GamePhase.FORCED_POKEMON_SELECTION:
            # During forced selection, only the forced_selection_player can act
            acting_player = game.forced_selection_player
        else:
            # Normal turn - current player acts
            acting_player = game.current_player
        
        return acting_player, ai_players[acting_player]
    
    def setUp(self):
        """Set up test fixtures"""
        self.logger = logging.getLogger("test")
        
        # Create sample card collection
        self.collection = self.create_test_collection()
        
        # Create test decks
        self.fire_deck = self.create_test_deck("fire")
        self.water_deck = self.create_test_deck("water")
    
    def create_test_collection(self) -> CardCollection:
        """Create a test card collection with enough variety for 20-card decks"""
        collection = CardCollection()
        
        # Fire Pokemon (6 different Fire Pokemon for variety)
        fire_pokemon = [
            (1, "Charmander", 60, "Scratch", "10"),
            (2, "Growlithe", 70, "Bite", "20"),
            (8, "Vulpix", 50, "Ember", "15"),
            (9, "Ponyta", 60, "Flame Tail", "20"),
            (10, "Magmar", 80, "Fire Punch", "30"),
            (11, "Flareon", 90, "Flamethrower", "35")
        ]
        
        for pid, name, hp, attack, damage in fire_pokemon:
            collection.add_card(Card(
                id=pid, name=name, energy_type="Fire", card_type="Basic Pokémon", hp=hp,
                attacks=[{"name": attack, "cost": ["F"], "damage": damage}],
                weakness="Water", retreat_cost=1
            ))
        
        # Water Pokemon (6 different)
        water_pokemon = [
            (3, "Squirtle", 60, "Bubble", "10"),
            (4, "Psyduck", 70, "Water Gun", "20"),
            (12, "Staryu", 50, "Swift", "15"),
            (13, "Goldeen", 55, "Horn Attack", "20"),
            (14, "Magikarp", 30, "Splash", "0"),
            (15, "Vaporeon", 90, "Hydro Pump", "35")
        ]
        
        for pid, name, hp, attack, damage in water_pokemon:
            collection.add_card(Card(
                id=pid, name=name, energy_type="Water", card_type="Basic Pokémon", hp=hp,
                attacks=[{"name": attack, "cost": ["W"], "damage": damage}],
                weakness="Lightning", retreat_cost=1
            ))
        
        # Colorless Pokemon (4 different)
        colorless_pokemon = [
            (5, "Rattata", 40, "Quick Attack", "10"),
            (16, "Pidgey", 50, "Gust", "10"),
            (17, "Spearow", 40, "Peck", "10"),
            (18, "Meowth", 50, "Scratch", "10")
        ]
        
        for pid, name, hp, attack, damage in colorless_pokemon:
            collection.add_card(Card(
                id=pid, name=name, energy_type="Colorless", card_type="Basic Pokémon", hp=hp,
                attacks=[{"name": attack, "cost": ["C"], "damage": damage}],
                weakness="Fighting", retreat_cost=1
            ))
        
        # Trainer cards (8 different trainers)
        trainers = [
            (6, "Professor Oak", "Trainer - Supporter"),
            (7, "Potion", "Trainer - Item"),
            (19, "Bill", "Trainer - Supporter"),
            (20, "Switch", "Trainer - Item"),
            (21, "Energy Search", "Trainer - Item"),
            (22, "Pokédex", "Trainer - Item"),
            (23, "Computer Search", "Trainer - Item"),
            (24, "Item Finder", "Trainer - Item")
        ]
        
        for tid, name, card_type in trainers:
            collection.add_card(Card(
                id=tid, name=name, energy_type="", card_type=card_type, attacks=[]
            ))
        
        return collection
    
    def create_test_deck(self, deck_type: str) -> Deck:
        """Create a test deck of specified type"""
        deck = Deck(f"Test {deck_type.title()} Deck")
        
        if deck_type == "fire":
            # Fire deck: 6 Fire Pokemon + 4 Colorless + 10 Trainers = 20 cards (2 copies each)
            cards_config = [
                # Fire Pokemon (6 different, 2 copies each = 12 cards)
                (1, 2), (2, 2), (8, 2), (9, 2), (10, 2), (11, 2),
                # Trainers (4 different, 2 copies each = 8 cards)
                (6, 2), (7, 2), (19, 2), (20, 2)
            ]
            deck.deck_types = ["Fire"]
        elif deck_type == "water":
            # Water deck: 6 Water Pokemon + 4 Colorless + 10 Trainers = 20 cards
            cards_config = [
                # Water Pokemon (6 different, 2 copies each = 12 cards)
                (3, 2), (4, 2), (12, 2), (13, 2), (14, 2), (15, 2),
                # Trainers (4 different, 2 copies each = 8 cards)
                (6, 2), (7, 2), (21, 2), (22, 2)
            ]
            deck.deck_types = ["Water"]
        else:
            # Default colorless deck: 8 Colorless Pokemon + 12 Trainers = 20 cards
            cards_config = [
                # Colorless Pokemon (4 different, 2 copies each = 8 cards)
                (5, 2), (16, 2), (17, 2), (18, 2),
                # Trainers (6 different, 2 copies each = 12 cards)
                (6, 2), (7, 2), (19, 2), (20, 2), (23, 2), (24, 2)
            ]
            deck.deck_types = ["Colorless"]
        
        # Add cards to deck
        for card_id, count in cards_config:
            card = self.collection.get_card_by_id(card_id)
            if card:
                for _ in range(count):
                    deck.add_card(card)
        
        return deck
    
    def test_complete_battle_simulation(self):
        """Test a complete battle from start to finish"""
        game = GameState(
            player_decks=[self.fire_deck, self.water_deck],
            battle_id="integration_test_battle",
            rng_seed=12345,
            logger=self.logger
        )
        
        # Create AI players
        ai_players = [
            RuleBasedAI(player_id=0, logger=self.logger, rng_seed=12345),
            RuleBasedAI(player_id=1, logger=self.logger, rng_seed=54321)
        ]
        
        # Start battle
        self.assertTrue(game.start_battle())
        
        # Battle loop with safety limits
        max_actions = 1000
        actions_taken = 0
        
        while not game.is_battle_over() and actions_taken < max_actions:
            # Determine which player should act
            from simulator.core.game import GamePhase
            if game.phase == GamePhase.FORCED_POKEMON_SELECTION:
                # During forced selection, only the forced_selection_player can act
                acting_player = game.forced_selection_player
            else:
                # Normal turn - current player acts
                acting_player = game.current_player
            
            ai = ai_players[acting_player]
            
            # Get action from appropriate AI
            action = ai.choose_action(game)
            self.assertIsNotNone(action, f"AI should provide action in phase {game.phase.value}")
            
            # Execute action
            success = game.execute_action(action)
            if not success:
                # If action fails during normal play, try to end turn
                if game.phase == GamePhase.PLAYER_TURN:
                    end_turn = ai._create_end_turn_action()
                    game.execute_action(end_turn)
                else:
                    # During forced selection, failure means no valid Pokemon available
                    self.fail(f"Forced Pokemon selection failed - player {acting_player} has no valid Pokemon")
            
            actions_taken += 1
        
        # Battle should have ended
        self.assertTrue(game.is_battle_over())
        
        # Get result
        result = game.get_battle_result()
        self.assertIsInstance(result, BattleResult)
        
        # Validate result
        if result.is_tie:
            self.assertIsNone(result.winner)
        else:
            self.assertIn(result.winner, [0, 1])
        
        self.assertGreater(result.total_turns, 0)
        self.assertEqual(len(result.final_scores), 2)
        self.assertGreater(result.duration_seconds, 0)
    
    def test_battle_with_different_strategies(self):
        """Test battle with different AI strategies"""
        game = GameState(
            player_decks=[self.fire_deck, self.water_deck],
            rng_seed=11111,
            logger=self.logger
        )
        
        # Create AIs with different strategies
        aggro_ai = RuleBasedAI(player_id=0, rng_seed=11111)
        aggro_ai.set_strategy("aggro")
        
        control_ai = RuleBasedAI(player_id=1, rng_seed=22222)
        control_ai.set_strategy("control")
        
        ai_players = [aggro_ai, control_ai]
        
        # Start and run battle
        self.assertTrue(game.start_battle())
        
        actions_taken = 0
        max_actions = 1000
        
        while not game.is_battle_over() and actions_taken < max_actions:
            acting_player, ai = self._get_acting_player_and_ai(game, ai_players)
            
            action = ai.choose_action(game)
            if action:
                game.execute_action(action)
            
            actions_taken += 1
        
        # Battle should complete
        self.assertTrue(game.is_battle_over())
        result = game.get_battle_result()
        self.assertIsNotNone(result)
    
    def test_multiple_battle_consistency(self):
        """Test running multiple battles with same setup"""
        results = []
        
        # Run multiple battles with same seed
        for i in range(3):
            game = GameState(
                player_decks=[self.fire_deck, self.water_deck],
                rng_seed=99999,
                logger=self.logger
            )
            
            ai_players = [
                RuleBasedAI(player_id=0, rng_seed=99999),
                RuleBasedAI(player_id=1, rng_seed=99999)
            ]
            
            game.start_battle()
            
            actions_taken = 0
            while not game.is_battle_over() and actions_taken < 500:
                acting_player, ai = self._get_acting_player_and_ai(game, ai_players)
                action = ai.choose_action(game)
                if action:
                    game.execute_action(action)
                actions_taken += 1
            
            result = game.get_battle_result()
            results.append(result)
        
        # All battles should have same outcome with same seed
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertEqual(result.winner, results[0].winner)
            self.assertEqual(result.is_tie, results[0].is_tie)
            self.assertEqual(result.total_turns, results[0].total_turns)
    
    def test_battle_performance(self):
        """Test battle performance characteristics"""
        start_time = time.time()
        
        game = GameState(
            player_decks=[self.fire_deck, self.water_deck],
            rng_seed=77777,
            logger=self.logger
        )
        
        ai_players = [
            RuleBasedAI(player_id=0, rng_seed=77777),
            RuleBasedAI(player_id=1, rng_seed=88888)
        ]
        
        game.start_battle()
        
        actions_taken = 0
        while not game.is_battle_over() and actions_taken < 200:
            acting_player, ai = self._get_acting_player_and_ai(game, ai_players)
            action = ai.choose_action(game)
            if action:
                game.execute_action(action)
            actions_taken += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Battle should complete quickly (under 1 second for integration test)
        self.assertLess(duration, 1.0)
        
        result = game.get_battle_result()
        self.assertLess(result.duration_seconds, 1.0)
    
    def test_error_recovery(self):
        """Test battle simulator error recovery"""
        game = GameState(
            player_decks=[self.fire_deck, self.water_deck],
            logger=self.logger
        )
        
        ai = RuleBasedAI(player_id=0, logger=self.logger)
        
        game.start_battle()
        
        # Corrupt game state intentionally
        original_active = game.players[0].active_pokemon
        game.players[0].active_pokemon = None
        
        # AI should handle missing active Pokemon gracefully
        action = ai.choose_action(game)
        self.assertIsNotNone(action)
        
        # Restore game state
        game.players[0].active_pokemon = original_active
    
    def test_deck_validation_integration(self):
        """Test deck validation in battle context"""
        # Create invalid deck (no Basic Pokemon)
        invalid_deck = Deck("Invalid Deck")
        for _ in range(20):
            invalid_deck.add_card(self.collection.get_card_by_id(6))  # All trainers
        
        # Should fail to start battle
        game = GameState(
            player_decks=[invalid_deck, self.water_deck],
            logger=self.logger
        )
        
        # Battle start should fail due to invalid deck
        success = game.start_battle()
        self.assertFalse(success)
    
    def test_battle_logging(self):
        """Test battle logging functionality"""
        game = GameState(
            player_decks=[self.fire_deck, self.water_deck],
            rng_seed=33333,
            logger=self.logger
        )
        
        ai_players = [
            RuleBasedAI(player_id=0, rng_seed=33333),
            RuleBasedAI(player_id=1, rng_seed=44444)
        ]
        
        game.start_battle()
        
        initial_log_size = len(game.turn_log)
        
        # Execute a few actions
        for _ in range(5):
            if not game.is_battle_over():
                acting_player, ai = self._get_acting_player_and_ai(game, ai_players)
                action = ai.choose_action(game)
                if action:
                    game.execute_action(action)
        
        # Log should have grown
        self.assertGreater(len(game.turn_log), initial_log_size)
        
        # Check log entry structure
        if game.turn_log:
            log_entry = game.turn_log[-1]
            required_fields = ["turn", "player", "action", "game_state", "timestamp"]
            for field in required_fields:
                self.assertIn(field, log_entry)
    
    def test_battle_result_completeness(self):
        """Test that battle results contain all required information"""
        game = GameState(
            player_decks=[self.fire_deck, self.water_deck],
            battle_id="completeness_test",
            rng_seed=55555,
            logger=self.logger
        )
        
        ai_players = [
            RuleBasedAI(player_id=0, rng_seed=55555),
            RuleBasedAI(player_id=1, rng_seed=66666)
        ]
        
        game.start_battle()
        
        # Run battle to completion
        actions_taken = 0
        while not game.is_battle_over() and actions_taken < 300:
            acting_player, ai = self._get_acting_player_and_ai(game, ai_players)
            action = ai.choose_action(game)
            if action:
                game.execute_action(action)
            actions_taken += 1
        
        result = game.get_battle_result()
        result_dict = result.to_dict()
        
        # Check all required fields
        required_fields = [
            "battle_id", "winner", "is_tie", "total_turns",
            "final_scores", "duration_seconds", "deck_types",
            "rng_seed", "end_reason", "timestamp"
        ]
        
        for field in required_fields:
            self.assertIn(field, result_dict)
        
        # Validate field values
        self.assertEqual(result_dict["battle_id"], "completeness_test")
        self.assertEqual(result_dict["rng_seed"], 55555)
        self.assertEqual(len(result_dict["final_scores"]), 2)
        self.assertEqual(len(result_dict["deck_types"]), 2)
        self.assertGreater(result_dict["total_turns"], 0)
        self.assertGreater(result_dict["duration_seconds"], 0)


if __name__ == "__main__":
    # Set up logging for tests
    logging.basicConfig(level=logging.WARNING)
    unittest.main()