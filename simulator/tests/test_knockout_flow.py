"""
Test knockout and Pokemon replacement flow in battle simulator
"""

import unittest
import logging

# Import existing models
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from Card import Card
from Deck import Deck
from simulator.core.game import GameState, BattleAction, ActionType, GamePhase
from simulator.ai.rule_based import RuleBasedAI


class TestKnockoutFlow(unittest.TestCase):
    """Test Pokemon knockout and replacement mechanics"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.logger = logging.getLogger("test_knockout")
        
        # Create test cards
        self.weak_pokemon = Card(
            id=1, name="Weak Pokemon", energy_type="Fire", 
            card_type="Basic Pokémon", hp=10,  # Very low HP for easy knockout
            attacks=[{"name": "Weak Attack", "cost": ["C"], "damage": "5"}],
            weakness="Water", retreat_cost=1
        )
        
        self.strong_pokemon = Card(
            id=2, name="Strong Pokemon", energy_type="Water", 
            card_type="Basic Pokémon", hp=100,
            attacks=[{"name": "Strong Attack", "cost": ["W"], "damage": "50"}],
            weakness="Lightning", retreat_cost=1
        )
        
        self.replacement_pokemon = Card(
            id=3, name="Replacement Pokemon", energy_type="Fire", 
            card_type="Basic Pokémon", hp=60,
            attacks=[{"name": "Replace Attack", "cost": ["F"], "damage": "20"}],
            weakness="Water", retreat_cost=1
        )
        
        self.trainer_card = Card(
            id=4, name="Test Trainer", energy_type="", 
            card_type="Trainer - Item", attacks=[]
        )
        
        # Create balanced decks
        self.deck1 = Deck("Player 0 Deck")
        self.deck2 = Deck("Player 1 Deck")
        
        # Deck 1: Mostly weak Pokemon (will get knocked out)
        cards_to_add = [
            (self.weak_pokemon, 2),
            (self.replacement_pokemon, 2),
            (self.strong_pokemon, 2),
            (self.trainer_card, 2)
        ]
        
        # Fill to 20 cards with variety
        for i in range(6):  # Add 12 more cards
            extra_card = Card(
                id=10+i, name=f"Extra Card {i}", energy_type="Colorless",
                card_type="Basic Pokémon" if i < 4 else "Trainer - Item", hp=50,
                attacks=[{"name": "Extra Attack", "cost": ["C"], "damage": "15"}] if i < 4 else []
            )
            cards_to_add.append((extra_card, 2))
        
        for card, count in cards_to_add:
            for _ in range(count):
                self.deck1.add_card(card)
                
        # Deck 2: Strong attackers
        for card, count in cards_to_add:
            for _ in range(count):
                self.deck2.add_card(card)
        
        self.deck1.deck_types = ["Fire"]
        self.deck2.deck_types = ["Water"]
    
    def test_knockout_triggers_forced_selection(self):
        """Test that knockout properly triggers forced Pokemon selection phase"""
        game = GameState(
            player_decks=[self.deck1, self.deck2],
            battle_id="knockout_test",
            rng_seed=12345,
            logger=self.logger
        )
        
        # Start battle
        success = game.start_battle()
        self.assertTrue(success, "Battle should start successfully")
        
        # Verify initial state
        self.assertEqual(game.phase, GamePhase.PLAYER_TURN)
        self.assertIsNotNone(game.players[0].active_pokemon)
        self.assertIsNotNone(game.players[1].active_pokemon)
        
        # Simulate knockout by directly damaging active Pokemon to 0 HP
        defender = game.players[1]
        original_hp = defender.active_pokemon.current_hp
        defender.active_pokemon.take_damage(original_hp)  # Knock out Pokemon
        
        self.assertTrue(defender.active_pokemon.is_knocked_out(), "Pokemon should be knocked out")
        
        # Trigger knockout handling
        game._handle_knockout(attacker_id=0, defender_id=1)
        
        # Verify game entered forced selection phase
        self.assertEqual(game.phase, GamePhase.FORCED_POKEMON_SELECTION)
        self.assertEqual(game.forced_selection_player, 1)
        self.assertIsNone(defender.active_pokemon, "Active Pokemon should be removed")
        
        # Verify attacker got prize points
        self.assertGreater(game.players[0].prize_points, 0)
        
    def test_ai_handles_forced_pokemon_selection(self):
        """Test that AI can properly select replacement Pokemon after knockout"""
        game = GameState(
            player_decks=[self.deck1, self.deck2],
            battle_id="ai_knockout_test", 
            rng_seed=12345,
            logger=self.logger
        )
        
        # Create AI for player 1 (defender)
        ai = RuleBasedAI(player_id=1, logger=self.logger, rng_seed=54321)
        
        game.start_battle()
        
        # Place a Pokemon on player 1's bench for replacement
        player1 = game.players[1]
        if player1.get_bench_space() > 0:
            # Find a basic Pokemon in hand and place on bench
            basic_pokemon = player1.get_playable_basic_pokemon()
            if basic_pokemon:
                player1.place_pokemon_bench(basic_pokemon[0])
        
        # Knock out player 1's active Pokemon
        original_hp = player1.active_pokemon.current_hp
        player1.active_pokemon.take_damage(original_hp)
        
        # Trigger knockout
        game._handle_knockout(attacker_id=0, defender_id=1)
        
        # Verify forced selection phase
        self.assertEqual(game.phase, GamePhase.FORCED_POKEMON_SELECTION)
        self.assertEqual(game.forced_selection_player, 1)
        
        # AI should choose replacement action
        action = ai.choose_action(game)
        self.assertIsNotNone(action, "AI should choose a replacement action")
        self.assertEqual(action.action_type, ActionType.SELECT_ACTIVE_POKEMON)
        self.assertEqual(action.player_id, 1)
        
        # Validate and execute the action
        is_valid, error = game.validate_action(action)
        self.assertTrue(is_valid, f"Action should be valid: {error}")
        
        success = game.execute_action(action)
        self.assertTrue(success, "Action execution should succeed")
        
        # Verify battle returned to normal state
        self.assertEqual(game.phase, GamePhase.PLAYER_TURN)
        self.assertIsNone(game.forced_selection_player)
        self.assertIsNotNone(player1.active_pokemon, "Player 1 should have new active Pokemon")
        
    def test_turn_cannot_end_during_forced_selection(self):
        """Test that players cannot end turn during forced Pokemon selection"""
        game = GameState(
            player_decks=[self.deck1, self.deck2],
            battle_id="turn_end_test",
            rng_seed=12345,
            logger=self.logger
        )
        
        game.start_battle()
        
        # Knock out player 1's active Pokemon
        player1 = game.players[1]
        original_hp = player1.active_pokemon.current_hp
        player1.active_pokemon.take_damage(original_hp)
        game._handle_knockout(attacker_id=0, defender_id=1)
        
        # Verify in forced selection phase
        self.assertEqual(game.phase, GamePhase.FORCED_POKEMON_SELECTION)
        
        # Try to end turn - should fail
        end_turn_action = BattleAction(
            action_type=ActionType.END_TURN,
            player_id=0,  # Attacker trying to end turn
            details={}
        )
        
        is_valid, error = game.validate_action(end_turn_action)
        self.assertFalse(is_valid, "Should not be able to end turn during forced selection")
        self.assertIn("forced pokemon selection", error.lower())
        
    def test_complete_knockout_and_replacement_flow(self):
        """Test complete flow from attack -> knockout -> replacement -> battle continues"""
        game = GameState(
            player_decks=[self.deck1, self.deck2],
            battle_id="complete_flow_test",
            rng_seed=12345,
            logger=self.logger
        )
        
        # Create AIs for both players
        ai_players = [
            RuleBasedAI(player_id=0, logger=self.logger, rng_seed=12345),
            RuleBasedAI(player_id=1, logger=self.logger, rng_seed=54321)
        ]
        
        game.start_battle()
        
        # Store initial state
        initial_turn = game.turn_number
        initial_player = game.current_player
        
        # Ensure player 1 has Pokemon on bench for replacement
        player1 = game.players[1]
        if player1.get_bench_space() > 0:
            basic_pokemon = player1.get_playable_basic_pokemon()
            if basic_pokemon:
                player1.place_pokemon_bench(basic_pokemon[0])
        
        # Manually trigger a knockout scenario
        # Set player 1's active Pokemon to very low HP
        player1.active_pokemon.current_hp = 1
        
        # Run battle loop until knockout occurs or battle ends
        max_actions = 50
        actions_taken = 0
        knockout_occurred = False
        attacking_player_during_knockout = None
        
        while not game.is_battle_over() and actions_taken < max_actions:
            current_player = game.current_player
            ai = ai_players[current_player]
            
            # Get action from AI
            action = ai.choose_action(game)
            self.assertIsNotNone(action, f"AI should always provide an action (turn {actions_taken})")
            
            # Execute action
            success = game.execute_action(action)
            if not success:
                self.fail(f"Action execution failed: {action.action_type.value}")
            
            # Check if we entered forced selection phase (knockout occurred)
            if game.phase == GamePhase.FORCED_POKEMON_SELECTION:
                knockout_occurred = True
                attacking_player_during_knockout = current_player
                self.logger.info("Knockout occurred, testing replacement flow")
                
                # The defending player should be prompted for replacement
                defending_player = game.forced_selection_player
                defending_ai = ai_players[defending_player]
                
                # Get replacement action
                replacement_action = defending_ai.choose_action(game)
                self.assertIsNotNone(replacement_action, "AI should choose replacement Pokemon")
                self.assertEqual(replacement_action.action_type, ActionType.SELECT_ACTIVE_POKEMON)
                
                # Execute replacement
                success = game.execute_action(replacement_action)
                self.assertTrue(success, "Pokemon replacement should succeed")
                
                # Verify battle returned to normal
                self.assertEqual(game.phase, GamePhase.PLAYER_TURN)
                self.assertIsNotNone(game.players[defending_player].active_pokemon)
                
                # Battle should continue with the attacking player's turn (who caused the knockout)
                self.assertEqual(game.current_player, attacking_player_during_knockout)
                break
                
            actions_taken += 1
        
        self.assertTrue(knockout_occurred or game.is_battle_over(), 
                       "Should have triggered knockout scenario or battle ended naturally")
        
        if knockout_occurred:
            self.assertEqual(game.phase, GamePhase.PLAYER_TURN, 
                           "Battle should return to normal turn phase after replacement")


if __name__ == "__main__":
    # Set up logging for tests
    logging.basicConfig(level=logging.INFO)
    unittest.main()