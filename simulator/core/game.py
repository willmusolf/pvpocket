"""
Core game engine for Pokemon TCG Pocket battle simulation

Handles game state, turn management, and battle flow
"""

import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any
from enum import Enum

# Import existing models
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from Card import Card
from Deck import Deck

# Import advanced effect system
from simulator.core.effect_engine import AdvancedEffectEngine
from simulator.core.card_bridge import BattleCard, CardDataBridge


class GamePhase(Enum):
    """Current phase of the game"""
    SETUP = "setup"
    INITIAL_POKEMON_PLACEMENT = "initial_pokemon_placement"
    PLAYER_TURN = "player_turn"
    FORCED_POKEMON_SELECTION = "forced_pokemon_selection"
    BATTLE_END = "battle_end"


class ActionType(Enum):
    """Types of actions players can take"""
    ATTACH_ENERGY = "attach_energy"
    ATTACK = "attack"
    PLACE_POKEMON = "place_pokemon"
    RETREAT = "retreat"
    SWITCH_POKEMON = "switch_pokemon"  # Added for frontend compatibility
    SELECT_ACTIVE_POKEMON = "select_active_pokemon"
    USE_ABILITY = "use_ability"  # Added for ability execution
    END_TURN = "end_turn"
    INITIAL_POKEMON_PLACEMENT = "initial_pokemon_placement"


@dataclass
class BattleAction:
    """Represents a single action in battle"""
    action_type: ActionType
    player_id: int
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "player_id": self.player_id,
            "details": self.details
        }


@dataclass
class BattleResult:
    """Final result of a battle"""
    winner: Optional[int]  # None for tie
    is_tie: bool
    total_turns: int
    final_scores: List[int]
    duration_seconds: float
    battle_id: str
    deck_types: List[List[str]]
    rng_seed: Optional[int]
    end_reason: str  # "prize_points", "no_pokemon", "turn_limit", "timeout"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "battle_id": self.battle_id,
            "winner": self.winner,
            "is_tie": self.is_tie,
            "total_turns": self.total_turns,
            "final_scores": self.final_scores,
            "duration_seconds": self.duration_seconds,
            "deck_types": self.deck_types,
            "rng_seed": self.rng_seed,
            "end_reason": self.end_reason,
            "timestamp": datetime.utcnow().isoformat()
        }


class GameState:
    """Main game state manager for battle simulation"""
    
    def __init__(self, 
                 player_decks: List[Deck], 
                 battle_id: str = None,
                 rng_seed: Optional[int] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize a new battle
        
        Args:
            player_decks: List of 2 Deck objects for the players
            battle_id: Unique identifier for this battle
            rng_seed: Random seed for reproducible battles
            logger: Logger instance for battle events
        """
        if len(player_decks) != 2:
            raise ValueError("Battle requires exactly 2 players")
            
        # Core game state
        self.battle_id = battle_id or f"battle_{int(time.time())}"
        self.turn_number = 0
        self.current_player = 0  # 0 or 1
        self.phase = GamePhase.SETUP
        self.winner: Optional[int] = None
        self.is_tie = False
        self.end_reason = ""
        
        # Forced Pokemon selection state
        self.forced_selection_player: Optional[int] = None  # Player who must select new active Pokemon
        
        # Initial Pokemon placement state
        self.initial_placement_completed = [False, False]  # Track which players completed initial placement
        
        # Battle configuration
        self.max_turns = 100
        self.max_prize_points = 3
        self.weakness_damage_bonus = 20
        
        # Random number generation
        if rng_seed is not None:
            self.rng = random.Random(rng_seed)
            self.rng_seed = rng_seed
        else:
            self.rng = random.Random()
            self.rng_seed = None
            
        # Logging
        self.logger = logger or logging.getLogger(__name__)
        self.turn_log: List[Dict[str, Any]] = []
        self.start_time = time.time()
        
        # Advanced effect system (will be initialized when battle starts)
        self.effect_engine: Optional[AdvancedEffectEngine] = None
        self.card_bridge = CardDataBridge(self.logger)
        
        # Initialize players (will be implemented when player.py is ready)
        from .player import PlayerState
        self.players: List[PlayerState] = []
        
        try:
            for i, deck in enumerate(player_decks):
                player = PlayerState(
                    player_id=i,
                    deck=deck,
                    rng=self.rng,
                    logger=self.logger
                )
                self.players.append(player)
        except Exception as e:
            self.logger.error(f"Failed to initialize players: {e}")
            raise
            
        self.logger.info(f"Initialized battle {self.battle_id} with {len(self.players)} players")
    
    def validate_action(self, action: BattleAction) -> Tuple[bool, str]:
        """
        Validate if an action is legal in the current game state
        
        Returns:
            (is_valid, error_message)
        """
        try:
            # Special handling for initial Pokemon placement phase
            if self.phase == GamePhase.INITIAL_POKEMON_PLACEMENT:
                if action.action_type != ActionType.INITIAL_POKEMON_PLACEMENT:
                    return False, "Must place Pokemon during initial placement phase"
                return self._validate_initial_pokemon_placement(action)
            
            # Special handling for forced Pokemon selection
            if self.phase == GamePhase.FORCED_POKEMON_SELECTION:
                # Check action type first to provide more specific error messages
                if action.action_type == ActionType.END_TURN:
                    return False, "Cannot end turn during forced Pokemon selection"
                
                if action.player_id != self.forced_selection_player:
                    return False, "Not the player who must select Pokemon"
                if action.action_type != ActionType.SELECT_ACTIVE_POKEMON:
                    return False, "Must select active Pokemon during forced selection phase"
                return self._validate_pokemon_selection(action)
            
            if action.player_id != self.current_player:
                return False, "Not this player's turn"
                
            if self.phase != GamePhase.PLAYER_TURN:
                return False, "Not in player turn phase"
                
            if self.is_battle_over():
                return False, "Battle is already over"
                
            player = self.players[action.player_id]
            
            # STRICT VALIDATION: No actions allowed after attacking (except END_TURN)
            # This enforces Pokemon TCG rules that attacks immediately end the turn
            if (player.attacked_this_turn and 
                action.action_type != ActionType.END_TURN):
                return False, f"Cannot perform {action.action_type.value} after attacking - attacks end the turn"
            
            # Validate specific action types
            if action.action_type == ActionType.ATTACH_ENERGY:
                return self._validate_energy_attachment(player, action)
            elif action.action_type == ActionType.ATTACK:
                return self._validate_attack(player, action)
            elif action.action_type == ActionType.PLACE_POKEMON:
                return self._validate_pokemon_placement(player, action)
            elif action.action_type == ActionType.RETREAT:
                return self._validate_retreat(player, action)
            elif action.action_type == ActionType.SWITCH_POKEMON:
                # Switch Pokemon is essentially the same as retreat
                return self._validate_retreat(player, action)
            elif action.action_type == ActionType.USE_ABILITY:
                return self._validate_ability_use(player, action)
            elif action.action_type == ActionType.END_TURN:
                return self._validate_end_turn(player, action)
            else:
                return False, f"Unknown action type: {action.action_type}"
                
        except Exception as e:
            self.logger.error(f"Action validation failed: {e}")
            return False, "Validation error"
    
    def execute_action(self, action: BattleAction) -> bool:
        """
        Execute a validated action
        
        Returns:
            True if action executed successfully
        """
        try:
            is_valid, error_msg = self.validate_action(action)
            if not is_valid:
                self.logger.warning(f"Invalid action: {error_msg}")
                return False
                
            # Log action
            self._log_action(action)
            
            # Execute specific action
            if action.action_type == ActionType.INITIAL_POKEMON_PLACEMENT:
                return self._execute_initial_pokemon_placement(action)
            elif action.action_type == ActionType.ATTACH_ENERGY:
                return self._execute_energy_attachment(action)
            elif action.action_type == ActionType.ATTACK:
                return self._execute_attack(action)
            elif action.action_type == ActionType.PLACE_POKEMON:
                return self._execute_pokemon_placement(action)
            elif action.action_type == ActionType.RETREAT:
                return self._execute_retreat(action)
            elif action.action_type == ActionType.SWITCH_POKEMON:
                # Switch Pokemon is essentially the same as retreat
                return self._execute_retreat(action)
            elif action.action_type == ActionType.USE_ABILITY:
                return self._execute_ability_use(action)
            elif action.action_type == ActionType.SELECT_ACTIVE_POKEMON:
                return self._execute_pokemon_selection(action)
            elif action.action_type == ActionType.END_TURN:
                return self._execute_end_turn(action)
                
            return False
            
        except Exception as e:
            self.logger.error(f"Action execution failed: {e}")
            return False
    
    def start_battle(self) -> bool:
        """
        Initialize battle and move to first turn
        
        Returns:
            True if battle started successfully
        """
        try:
            self.logger.info(f"Starting battle {self.battle_id}")
            
            # Validate both decks
            for i, player in enumerate(self.players):
                is_valid, error = player.deck.is_valid()
                if not is_valid:
                    self.logger.error(f"Player {i} deck invalid: {error}")
                    return False
            
            # Initialize player hands and active Pokemon
            for player in self.players:
                if not player.setup_initial_state():
                    self.logger.error(f"Failed to setup player {player.player_id}")
                    return False
            
            # Initialize advanced effect system
            self._initialize_effect_engine()
                    
            # Move to initial Pokemon placement phase
            self.phase = GamePhase.INITIAL_POKEMON_PLACEMENT
            self.turn_number = 0  # Haven't started actual turns yet
            self.current_player = 0  # Start with player 0 for placement
            
            self.logger.info("Battle setup complete - entering initial Pokemon placement phase")
            self.logger.info("Both players must place at least one Basic Pokemon as active before turn 1 begins")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start battle: {e}")
            return False
    
    def is_battle_over(self) -> bool:
        """Check if battle has ended"""
        if self.winner is not None or self.is_tie:
            return True
            
        # Check turn limit
        if self.turn_number >= self.max_turns:
            self._end_battle_tie("turn_limit")
            return True
            
        # Check if any player has won by prize points
        for i, player in enumerate(self.players):
            if player.prize_points >= self.max_prize_points:
                self.logger.info(f"DEFENSIVE PRIZE POINTS WIN CHECK: Player {i} has {player.prize_points} points (max: {self.max_prize_points})")
                if self.winner is None and not self.is_tie:  # Only set winner if not already set
                    self._end_battle_winner(i, "prize_points")
                return True
                
        # Check if any player cannot continue
        unable_to_continue = []
        for i, player in enumerate(self.players):
            if not player.can_continue_battle():
                unable_to_continue.append(i)
                
        if len(unable_to_continue) == 2:
            # Both players cannot continue
            self._end_battle_tie("both_unable")
            return True
        elif len(unable_to_continue) == 1:
            # One player cannot continue
            winner = 1 - unable_to_continue[0]
            self._end_battle_winner(winner, "opponent_unable")
            return True
            
        return False
    
    def get_battle_result(self) -> BattleResult:
        """Get final battle result"""
        duration = time.time() - self.start_time
        
        return BattleResult(
            winner=self.winner,
            is_tie=self.is_tie,
            total_turns=self.turn_number,
            final_scores=[p.prize_points for p in self.players],
            duration_seconds=duration,
            battle_id=self.battle_id,
            deck_types=[p.deck.deck_types for p in self.players],
            rng_seed=self.rng_seed,
            end_reason=self.end_reason
        )
    
    def get_current_state_snapshot(self) -> Dict[str, Any]:
        """Get current game state for logging"""
        return {
            "turn": self.turn_number,
            "current_player": self.current_player,
            "phase": self.phase.value,
            "player_0_active_hp": self.players[0].get_active_pokemon_hp(),
            "player_1_active_hp": self.players[1].get_active_pokemon_hp(),
            "player_0_bench_count": len([p for p in self.players[0].bench if p is not None]),
            "player_1_bench_count": len([p for p in self.players[1].bench if p is not None]),
            "player_0_prize_points": self.players[0].prize_points,
            "player_1_prize_points": self.players[1].prize_points,
            "player_0_hand_size": len(self.players[0].hand),
            "player_1_hand_size": len(self.players[1].hand)
        }
    
    # Private helper methods
    
    def _validate_energy_attachment(self, player, action) -> Tuple[bool, str]:
        """Validate energy attachment action"""
        if player.energy_attached_this_turn:
            return False, "Already attached energy this turn"
            
        # Pokemon TCG Pocket rule: Player 1 cannot attach energy on turn 1
        if self.current_player == 0 and self.turn_number == 1:
            return False, "Player 1 cannot attach energy on turn 1"
            
        if not player.active_pokemon:
            return False, "No active Pokemon to attach energy to"
            
        return True, ""
    
    def _get_attack_from_action(self, player, action) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Helper method to get attack and attack_name from action details
        Handles both attack_name and attack_index parameters
        Returns: (attack_dict, attack_name) or (None, None) if not found
        """
        if not player.active_pokemon:
            return None, None
            
        # Try to get attack_name first
        attack_name = action.details.get("attack_name")
        if attack_name:
            attack = player.active_pokemon.card.get_attack(attack_name)
            if attack:
                return attack, attack_name
        
        # Try to get attack by index
        attack_index = action.details.get("attack_index")
        if attack_index is not None and isinstance(attack_index, int):
            attacks = player.active_pokemon.card.attacks
            if 0 <= attack_index < len(attacks):
                attack = attacks[attack_index]
                attack_name = attack.get("name", f"Attack_{attack_index}")
                return attack, attack_name
        
        return None, None

    def _validate_attack(self, player, action) -> Tuple[bool, str]:
        """Validate attack action"""
        if not player.active_pokemon:
            return False, "No active Pokemon to attack with"
            
        # Prevent multiple attacks per turn
        if player.attacked_this_turn:
            return False, "Already attacked this turn"
            
        attack, attack_name = self._get_attack_from_action(player, action)
        if not attack or not attack_name:
            return False, "No valid attack specified or attack not found"
            
        # Check energy requirements
        if not player.active_pokemon.can_use_attack(attack):
            return False, f"Insufficient energy for {attack_name}"
        
        # Check status conditions that prevent attacking
        if self.effect_engine and hasattr(player.active_pokemon, 'status_conditions'):
            for status_effect in player.active_pokemon.status_conditions:
                if status_effect.condition.value in ['asleep', 'paralyzed']:
                    return False, f"Cannot attack while {status_effect.condition.value}"
        
        return True, ""
    
    def _validate_pokemon_placement(self, player, action) -> Tuple[bool, str]:
        """Validate Pokemon placement action"""
        card_id = action.details.get("card_id")
        if not card_id:
            return False, "No card specified"
            
        # Find card in hand
        card = None
        for c in player.hand:
            if c.id == card_id:
                card = c
                break
                
        if not card:
            return False, "Card not in hand"
            
        if not card.is_basic:
            return False, "Can only place Basic Pokemon"
            
        if not player.active_pokemon and action.details.get("position") != "active":
            return False, "Must place first Pokemon as active"
            
        if action.details.get("position") == "bench" and player.get_bench_space() <= 0:
            return False, "Bench is full"
            
        return True, ""
    
    def _validate_retreat(self, player, action) -> Tuple[bool, str]:
        """Validate retreat action"""
        if not player.active_pokemon:
            return False, "No active Pokemon to retreat"
            
        if player.get_bench_pokemon_count() == 0:
            return False, "No Pokemon on bench to switch to"
            
        retreat_cost = player.active_pokemon.card.retreat_cost or 0
        if len(player.active_pokemon.energy_attached) < retreat_cost:
            return False, f"Insufficient energy to retreat (need {retreat_cost})"
            
        return True, ""
    
    def _validate_ability_use(self, player, action) -> Tuple[bool, str]:
        """Validate ability use action"""
        if not player.active_pokemon:
            return False, "No active Pokemon to use ability with"
        
        ability_index = action.details.get("ability_index")
        if ability_index is None:
            return False, "No ability specified"
        
        abilities = getattr(player.active_pokemon.card, 'abilities', [])
        if not abilities or ability_index >= len(abilities):
            return False, f"Ability index {ability_index} not found"
        
        # Check if Pokemon is asleep or paralyzed (prevents ability use)
        if self.effect_engine and hasattr(player.active_pokemon, 'status_conditions'):
            for status_effect in player.active_pokemon.status_conditions:
                if status_effect.condition.value in ['asleep', 'paralyzed']:
                    return False, f"Cannot use ability while {status_effect.condition.value}"
        
        return True, ""
    
    def _validate_pokemon_selection(self, action) -> Tuple[bool, str]:
        """Validate forced Pokemon selection action"""
        player = self.players[action.player_id]
        
        selection_type = action.details.get("selection_type")
        if not selection_type:
            return False, "No selection type specified"
            
        if selection_type == "bench":
            bench_index = action.details.get("bench_index")
            if bench_index is None:
                return False, "No bench index specified"
            if bench_index < 0 or bench_index >= len(player.bench):
                return False, "Invalid bench index"
            if player.bench[bench_index] is None:
                return False, "No Pokemon at specified bench position"
            if player.bench[bench_index].is_knocked_out():
                return False, "Cannot select knocked out Pokemon"
                
        elif selection_type == "hand":
            card_id = action.details.get("card_id")
            if not card_id:
                return False, "No card ID specified"
            
            # Find card in hand
            card = None
            for c in player.hand:
                if c.id == card_id:
                    card = c
                    break
                    
            if not card:
                return False, "Card not in hand"
            if not card.is_pokemon or not card.is_basic:
                return False, "Can only select Basic Pokemon from hand"
        else:
            return False, f"Invalid selection type: {selection_type}"
            
        return True, ""
    
    def _validate_end_turn(self, player, action) -> Tuple[bool, str]:
        """Validate end turn action"""
        # Cannot end turn during forced Pokemon selection
        if self.phase == GamePhase.FORCED_POKEMON_SELECTION:
            return False, "Cannot end turn during forced Pokemon selection"
            
        # Must be in player turn phase
        if self.phase != GamePhase.PLAYER_TURN:
            return False, f"Cannot end turn in phase: {self.phase.value}"
            
        # Player must have an active Pokemon
        if not player.active_pokemon:
            return False, "Cannot end turn without an active Pokemon"
            
        return True, ""
    
    def _validate_initial_pokemon_placement(self, action) -> Tuple[bool, str]:
        """Validate initial Pokemon placement action"""
        player = self.players[action.player_id]
        
        # Check if player has already completed placement
        if self.initial_placement_completed[action.player_id]:
            return False, "Player has already completed initial Pokemon placement"
        
        placements = action.details.get("placements", [])
        if not placements:
            return False, "No Pokemon placements specified"
        
        # Must place at least one active Pokemon
        has_active = any(p.get("position") == "active" for p in placements)
        if not has_active:
            return False, "Must place at least one Basic Pokemon as active"
        
        # Validate each placement
        for placement in placements:
            card_id = placement.get("card_id")
            position = placement.get("position")  # "active" or "bench"
            
            if not card_id:
                return False, "Card ID required for each placement"
            if position not in ["active", "bench"]:
                return False, "Position must be 'active' or 'bench'"
                
            # Find card in hand
            card = None
            for c in player.hand:
                if c.id == card_id:
                    card = c
                    break
                    
            if not card:
                return False, f"Card {card_id} not in hand"
            if not card.is_pokemon or not card.is_basic:
                return False, f"Card {card.name} is not a Basic Pokemon"
        
        return True, ""
    
    def _execute_initial_pokemon_placement(self, action) -> bool:
        """Execute initial Pokemon placement"""
        try:
            player = self.players[action.player_id]
            placements = action.details.get("placements", [])
            
            # Place each Pokemon
            for placement in placements:
                card_id = placement.get("card_id")
                position = placement.get("position")
                
                # Find and remove card from hand
                card = None
                for i, c in enumerate(player.hand):
                    if c.id == card_id:
                        card = player.hand.pop(i)
                        break
                        
                if not card:
                    return False
                    
                # Create battle Pokemon
                from .pokemon import BattlePokemon
                battle_pokemon = BattlePokemon(card)
                
                # Place Pokemon
                if position == "active":
                    player.active_pokemon = battle_pokemon
                    self.logger.info(f"Player {action.player_id} placed {card.name} as active Pokemon")
                else:  # bench
                    for i in range(len(player.bench)):
                        if player.bench[i] is None:
                            player.bench[i] = battle_pokemon
                            self.logger.info(f"Player {action.player_id} placed {card.name} on bench")
                            break
            
            # Mark this player as completed
            self.initial_placement_completed[action.player_id] = True
            
            # Check if both players have completed placement
            if all(self.initial_placement_completed):
                # Start the actual battle - move to turn 1
                self.phase = GamePhase.PLAYER_TURN
                self.turn_number = 1
                self.current_player = 0
                
                # Player 0 draws their first card (turn 1)
                drawn_card = self.players[0].draw_card()
                if drawn_card:
                    self._log_card_draw(0, 1)
                
                # Log turn start
                self._log_turn_start()
                
                self.logger.info("Initial Pokemon placement complete - Turn 1 begins!")
            else:
                # Switch to other player for their placement
                waiting_player = 1 - action.player_id
                if not self.initial_placement_completed[waiting_player]:
                    self.current_player = waiting_player
                    self.logger.info(f"Player {waiting_player} must now place their initial Pokemon")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Initial Pokemon placement failed: {e}")
            return False
    
    def _execute_energy_attachment(self, action) -> bool:
        """Execute energy attachment"""
        try:
            player = self.players[action.player_id]
            energy_type = action.details.get("energy_type")
            
            if not energy_type:
                # Auto-select energy type based on deck
                if player.deck.deck_types:
                    energy_type = self.rng.choice(player.deck.deck_types)
                else:
                    energy_type = "Colorless"
            
            player.active_pokemon.energy_attached.append(energy_type)
            player.energy_attached_this_turn = True
            
            self.logger.debug(f"Player {action.player_id} attached {energy_type} energy")
            return True
            
        except Exception as e:
            self.logger.error(f"Energy attachment failed: {e}")
            return False
    
    def _execute_attack(self, action) -> bool:
        """Execute attack action with advanced effect processing"""
        try:
            attacker = self.players[action.player_id]
            defender = self.players[1 - action.player_id]
            
            attack, attack_name = self._get_attack_from_action(attacker, action)
            if not attack or not attack_name:
                self.logger.error(f"Attack not found: {action.details}")
                return False
            
            # Calculate base damage (handle both string and int damage values)
            damage_value = attack.get("damage", "0")
            if isinstance(damage_value, str):
                base_damage = int(damage_value.replace("+", ""))
            elif isinstance(damage_value, int):
                base_damage = damage_value
            else:
                base_damage = 0
            
            # Apply weakness
            weakness_damage = 0
            if (defender.active_pokemon.card.weakness and 
                attacker.active_pokemon.card.energy_type == defender.active_pokemon.card.weakness):
                weakness_damage = self.weakness_damage_bonus
                
            initial_damage = base_damage + weakness_damage
            
            # Process attack effects through the effect engine
            effect_results = {'final_damage': initial_damage, 'status_effects': [], 'energy_changes': [], 'coin_results': [], 'additional_effects': []}
            
            if self.effect_engine:
                try:
                    # Create battle context
                    battle_context = {
                        'turn': self.turn_number,
                        'player': action.player_id,
                        'attacker': attacker,
                        'defender': defender
                    }
                    
                    # Execute attack effects (this handles coin flips, energy generation, status conditions, etc.)
                    effect_results = self.effect_engine.execute_attack_effects(
                        attack, attacker.active_pokemon, defender.active_pokemon, initial_damage, battle_context
                    )
                    
                    self.logger.info(f"Attack effects processed: {effect_results}")
                    
                except Exception as e:
                    self.logger.warning(f"Effect engine processing failed: {e}, using basic damage calculation")
                    effect_results = {'final_damage': initial_damage, 'status_effects': [], 'energy_changes': [], 'coin_results': [], 'additional_effects': []}
            
            # Extract results
            final_damage = effect_results.get('final_damage', initial_damage)
            status_effects = effect_results.get('status_effects', [])
            energy_changes = effect_results.get('energy_changes', [])
            coin_results = effect_results.get('coin_results', [])
            additional_effects = effect_results.get('additional_effects', [])
            
            # Process energy changes (for attacks like Moltres EX Inferno Dance)
            self._process_energy_changes(energy_changes, attacker, action.player_id)
            
            # Apply damage if any
            knockout_occurred = False
            if final_damage > 0:
                defender.active_pokemon.take_damage(final_damage)
                
                # Check for KO
                if defender.active_pokemon.is_knocked_out():
                    self._handle_knockout(action.player_id, 1 - action.player_id)
                    knockout_occurred = True
            
            # Trigger post-attack abilities
            self._trigger_abilities('on_attack', {
                'attacker': attacker.active_pokemon,
                'defender': defender.active_pokemon,
                'damage_dealt': final_damage,
                'attack_name': attack_name
            })
            
            # Mark that player has attacked this turn
            attacker.attacked_this_turn = True
            
            # Log comprehensive attack results
            attack_log = f"Player {action.player_id} used {attack_name} for {final_damage} damage"
            if coin_results:
                attack_log += f" (coins: {coin_results})"
            if status_effects:
                attack_log += f" (status: {status_effects})"
            if additional_effects:
                attack_log += f" (effects: {', '.join(additional_effects)})"
            
            self.logger.info(attack_log)
            
            # Store effect details for battle log
            action.details.update({
                'final_damage': final_damage,
                'coin_results': coin_results,
                'status_effects': status_effects,
                'energy_changes': energy_changes,
                'additional_effects': additional_effects
            })
            
            # AUTOMATICALLY END TURN AFTER ATTACK (enforcing Pokemon TCG rules)
            # Only auto-end if battle hasn't ended and we're not waiting for Pokemon selection
            if (self.phase == GamePhase.PLAYER_TURN and 
                not self.is_battle_over() and 
                self.winner is None):
                
                self.logger.info(f"Auto-ending turn after attack - attacks immediately end the turn per Pokemon TCG rules")
                
                # Create an auto end-turn action to use existing turn-ending logic
                auto_end_turn_action = BattleAction(ActionType.END_TURN, action.player_id, {})
                
                # Execute the turn end using existing logic
                turn_end_success = self._execute_end_turn(auto_end_turn_action)
                if not turn_end_success:
                    self.logger.error(f"Auto turn-end failed after attack")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Attack execution failed: {e}")
            return False
    
    def _execute_pokemon_placement(self, action) -> bool:
        """Execute Pokemon placement"""
        try:
            player = self.players[action.player_id]
            card_id = action.details["card_id"]
            position = action.details.get("position", "active")
            
            # Find and remove card from hand
            card = None
            for i, c in enumerate(player.hand):
                if c.id == card_id:
                    card = player.hand.pop(i)
                    break
                    
            if not card:
                return False
                
            # Create battle Pokemon
            from .pokemon import BattlePokemon
            battle_pokemon = BattlePokemon(card)
            
            # Place Pokemon
            if position == "active":
                player.active_pokemon = battle_pokemon
            else:  # bench
                for i in range(len(player.bench)):
                    if player.bench[i] is None:
                        player.bench[i] = battle_pokemon
                        break
            
            # Trigger on-play abilities for the newly placed Pokemon
            self._trigger_abilities('on_play', {
                'pokemon': battle_pokemon,
                'player_id': action.player_id,
                'position': position
            })
                        
            self.logger.debug(f"Player {action.player_id} placed {card.name} as {position}")
            return True
            
        except Exception as e:
            self.logger.error(f"Pokemon placement failed: {e}")
            return False
    
    def _execute_retreat(self, action) -> bool:
        """Execute retreat action"""
        try:
            player = self.players[action.player_id]
            bench_index = action.details.get("bench_index", 0)
            
            # Use player's proper retreat method
            success = player.retreat_active_pokemon(bench_index)
            
            if success:
                self.logger.debug(f"Player {action.player_id} retreated active Pokemon")
                return True
            else:
                self.logger.warning(f"Player {action.player_id} retreat failed")
                return False
            
        except Exception as e:
            self.logger.error(f"Retreat failed: {e}")
            return False
    
    def _execute_ability_use(self, action) -> bool:
        """Execute ability use action"""
        try:
            player = self.players[action.player_id]
            ability_index = action.details.get("ability_index", 0)
            
            abilities = getattr(player.active_pokemon.card, 'abilities', [])
            if ability_index >= len(abilities):
                self.logger.error(f"Invalid ability index: {ability_index}")
                return False
            
            ability = abilities[ability_index]
            ability_name = ability.get("name", f"Ability_{ability_index}")
            
            # Log ability use
            self.logger.info(f"Player {action.player_id}'s {player.active_pokemon.card.name} used ability: {ability_name}")
            
            # Process ability effects through the effect engine
            if self.effect_engine:
                try:
                    battle_context = {
                        'turn': self.turn_number,
                        'player': action.player_id,
                        'user': player,
                        'opponent': self.players[1 - action.player_id]
                    }
                    
                    # Execute ability effects
                    effect_results = self.effect_engine.execute_ability_effects(
                        ability, player.active_pokemon, battle_context
                    )
                    
                    self.logger.info(f"Ability effects processed: {effect_results}")
                    
                except Exception as e:
                    self.logger.warning(f"Effect engine processing failed for ability: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ability execution failed: {e}")
            return False
    
    def _execute_pokemon_selection(self, action) -> bool:
        """Execute forced Pokemon selection"""
        try:
            player = self.players[action.player_id]
            selection_type = action.details["selection_type"]
            
            # Validate that we're in the correct phase
            if self.phase != GamePhase.FORCED_POKEMON_SELECTION:
                self.logger.error(f"Pokemon selection executed but not in forced selection phase")
                return False
                
            if self.forced_selection_player != action.player_id:
                self.logger.error(f"Wrong player attempting Pokemon selection")
                return False
            
            new_active_pokemon = None
            
            if selection_type == "bench":
                bench_index = action.details["bench_index"]
                
                # Additional validation
                if bench_index < 0 or bench_index >= len(player.bench):
                    self.logger.error(f"Invalid bench index: {bench_index}")
                    return False
                    
                if player.bench[bench_index] is None:
                    self.logger.error(f"No Pokemon at bench index {bench_index}")
                    return False
                    
                if player.bench[bench_index].is_knocked_out():
                    self.logger.error(f"Cannot select knocked out Pokemon from bench")
                    return False
                
                # Move bench Pokemon to active
                new_active_pokemon = player.bench[bench_index]
                player.active_pokemon = new_active_pokemon
                player.bench[bench_index] = None
                self.logger.info(f"Player {action.player_id} selected {new_active_pokemon.card.name} from bench as active Pokemon")
                
            elif selection_type == "hand":
                card_id = action.details["card_id"]
                
                # Find and validate card in hand
                card = None
                card_index = None
                for i, c in enumerate(player.hand):
                    if c.id == card_id:
                        card = c
                        card_index = i
                        break
                        
                if not card:
                    self.logger.error(f"Card ID {card_id} not found in player hand")
                    return False
                    
                if not card.is_pokemon or not card.is_basic:
                    self.logger.error(f"Card {card.name} is not a Basic Pokemon")
                    return False
                
                # Remove card from hand and create battle Pokemon
                player.hand.pop(card_index)
                from .pokemon import BattlePokemon
                new_active_pokemon = BattlePokemon(card)
                player.active_pokemon = new_active_pokemon
                self.logger.info(f"Player {action.player_id} played {card.name} from hand as active Pokemon")
            
            else:
                self.logger.error(f"Invalid selection type: {selection_type}")
                return False
            
            # Validate that player now has an active Pokemon
            if not player.active_pokemon:
                self.logger.error(f"Player {action.player_id} still has no active Pokemon after selection")
                return False
            
            # Return to normal player turn phase - battle continues with current player
            self.phase = GamePhase.PLAYER_TURN
            self.forced_selection_player = None
            
            # Log the successful Pokemon replacement
            self.logger.info(f"Player {action.player_id} successfully selected new active Pokemon: {player.active_pokemon.card.name} (HP: {player.active_pokemon.current_hp})")
            
            # Check if battle should end due to win conditions
            if self.is_battle_over():
                return True
            
            # Turn continues with the same player who was attacking before the knockout
            self.logger.debug(f"Battle continues with player {self.current_player}'s turn")
            return True
            
        except Exception as e:
            self.logger.error(f"Pokemon selection failed: {e}")
            # Try to end battle safely if there's a critical error
            if self.forced_selection_player is not None:
                self._end_battle_winner(1 - self.forced_selection_player, "selection_error")
            return False
    
    def _execute_end_turn(self, action) -> bool:
        """Execute end turn action"""
        try:
            # Check if we're in a valid state to end turn
            if self.phase == GamePhase.FORCED_POKEMON_SELECTION:
                self.logger.warning(f"Cannot end turn during forced Pokemon selection phase")
                return False
                
            if self.phase != GamePhase.PLAYER_TURN:
                self.logger.warning(f"Cannot end turn in phase: {self.phase.value}")
                return False
            
            # Validate it's the current player trying to end turn
            if action.player_id != self.current_player:
                self.logger.warning(f"Player {action.player_id} cannot end turn - it's player {self.current_player}'s turn")
                return False
            
            # Reset turn-based flags for current player
            self.players[self.current_player].reset_turn_state()
            
            # Process between-turns status effects for all Pokemon
            if self.effect_engine:
                try:
                    all_pokemon = []
                    for player in self.players:
                        if player.active_pokemon:
                            all_pokemon.append(player.active_pokemon)
                        for bench_pokemon in player.bench:
                            if bench_pokemon:
                                all_pokemon.append(bench_pokemon)
                    
                    status_effects = self.effect_engine.process_between_turns_effects(all_pokemon)
                    if status_effects:
                        self.logger.info(f"Between-turns status effects: {status_effects}")
                        for effect in status_effects:
                            # Log status effects directly instead of using _log_action
                            self.logger.info(f"Status effect processed: {effect}")
                    
                    # Process sleep wake-up checks for the player about to take their turn
                    current_player_pokemon = self.players[self.current_player].active_pokemon
                    if current_player_pokemon and hasattr(current_player_pokemon, 'status_conditions'):
                        sleep_removed = False
                        for status_effect in current_player_pokemon.status_conditions[:]:  # Copy list to safely modify
                            if status_effect.condition.value == 'asleep':
                                # 50% chance to wake up at the start of each turn
                                if random.random() < 0.5:
                                    current_player_pokemon.status_conditions.remove(status_effect)
                                    self.logger.info(f"{current_player_pokemon.card.name} woke up from sleep!")
                                    sleep_removed = True
                                else:
                                    self.logger.info(f"{current_player_pokemon.card.name} is still asleep")
                        
                        if sleep_removed:
                            # Log status removal directly instead of using _log_action
                            self.logger.info(f"{current_player_pokemon.card.name} woke up from sleep!")
                            
                except Exception as e:
                    self.logger.error(f"Between-turns status processing failed: {e}")
            
            # Log turn end before switching
            self._log_turn_end()
            
            # Switch to next player
            previous_player = self.current_player
            self.current_player = 1 - self.current_player
            
            # If back to player 0, increment turn number
            if self.current_player == 0:
                self.turn_number += 1
            
            # FIRST: Draw card at the very beginning of the turn
            drawn_card = self.players[self.current_player].draw_card()
            if drawn_card:
                self._log_card_draw(self.current_player, 1)
            else:
                # Log if unable to draw (empty deck or full hand)
                if len(self.players[self.current_player].deck_cards) == 0:
                    self.logger.warning(f"Player {self.current_player} cannot draw - deck is empty")
                elif len(self.players[self.current_player].hand) >= self.players[self.current_player].max_hand_size:
                    self.logger.warning(f"Player {self.current_player} cannot draw - hand is full")
            
            # SECOND: Log turn transition (after card draw)
            self._log_turn_start()
            
            # THIRD: Trigger turn start abilities for the new current player
            self._trigger_abilities('turn_start', {
                'player_id': self.current_player,
                'turn_number': self.turn_number
            })
            
            self.logger.info(f"Player {previous_player} ended turn - now player {self.current_player}'s turn (turn {self.turn_number})")
            return True
            
        except Exception as e:
            self.logger.error(f"End turn failed: {e}")
            return False
    
    def _process_energy_changes(self, energy_changes: List[Dict[str, Any]], target_player, player_id: int):
        """Process energy generation and attachment effects (like Moltres EX's Inferno Dance)"""
        try:
            if not energy_changes:
                return
            
            for energy_change in energy_changes:
                change_type = energy_change.get('type')
                target = energy_change.get('target', 'active')
                energy_type = energy_change.get('energy_type', 'Fire')
                amount = energy_change.get('amount', 0)
                
                if change_type == 'attach' and amount > 0:
                    # Determine target Pokemon
                    target_pokemon = None
                    if target == 'active' and target_player.active_pokemon:
                        target_pokemon = target_player.active_pokemon
                    elif target == 'bench' and energy_change.get('bench_index') is not None:
                        bench_index = energy_change.get('bench_index')
                        if 0 <= bench_index < len(target_player.bench) and target_player.bench[bench_index]:
                            target_pokemon = target_player.bench[bench_index]
                    
                    # Attach energy to target Pokemon
                    if target_pokemon:
                        for _ in range(amount):
                            target_pokemon.attach_energy(energy_type)
                        
                        self.logger.info(f"Energy effect: Attached {amount}x {energy_type} to {target_pokemon.card.name}")
                    else:
                        self.logger.warning(f"Energy effect failed: No valid target Pokemon for {energy_change}")
                
                elif change_type == 'remove' and amount > 0:
                    # Remove energy (for future expansion)
                    target_pokemon = None
                    if target == 'active' and target_player.active_pokemon:
                        target_pokemon = target_player.active_pokemon
                    elif target == 'bench' and energy_change.get('bench_index') is not None:
                        bench_index = energy_change.get('bench_index')
                        if 0 <= bench_index < len(target_player.bench) and target_player.bench[bench_index]:
                            target_pokemon = target_player.bench[bench_index]
                    
                    if target_pokemon:
                        removed_count = 0
                        energy_type_to_remove = energy_type if energy_type != 'any' else None
                        
                        for _ in range(amount):
                            removed = target_pokemon.remove_energy(energy_type_to_remove)
                            if not removed:
                                break  # No more energy to remove
                            removed_count += 1
                        
                        if removed_count > 0:
                            energy_desc = energy_type if energy_type != 'any' else 'energy'
                            self.logger.info(f"Energy effect: Removed {removed_count}x {energy_desc} from {target_pokemon.card.name}")
                
                elif change_type == 'distribute_to_bench':
                    # Handle Moltres-style energy distribution to bench Pokemon
                    self._distribute_energy_to_bench(energy_change, target_player, player_id)
                
                else:
                    self.logger.warning(f"Unknown energy change type or invalid amount: {energy_change}")
                    
        except Exception as e:
            self.logger.error(f"Energy processing failed: {e}")
    
    def _distribute_energy_to_bench(self, energy_change: Dict[str, Any], target_player, player_id: int):
        """Handle Moltres-style energy distribution to bench Pokemon"""
        try:
            energy_type = energy_change.get('energy_type', 'Fire')
            amount = energy_change.get('amount', 0)
            target_filter = energy_change.get('target_filter', '')
            
            if amount <= 0:
                return
            
            # Find eligible bench Pokemon (matching energy type for Moltres)
            eligible_pokemon = []
            for i, bench_pokemon in enumerate(target_player.bench):
                if bench_pokemon and not bench_pokemon.is_knocked_out():
                    # Check if Pokemon matches filter (e.g., Fire type for Moltres)
                    if (not target_filter or 
                        bench_pokemon.card.energy_type.lower() == target_filter.lower() or
                        target_filter.lower() in bench_pokemon.card.name.lower()):
                        eligible_pokemon.append((i, bench_pokemon))
            
            if not eligible_pokemon:
                self.logger.warning(f"No eligible bench Pokemon found for energy distribution")
                return
            
            # For AI: distribute energy optimally
            # Priority: Pokemon with attacks that need this energy type
            energy_distributed = 0
            distribution_log = []
            
            # Simple distribution strategy: spread evenly, prefer Pokemon that can use the energy
            remaining_energy = amount
            
            while remaining_energy > 0 and eligible_pokemon:
                # Find Pokemon that can benefit most from this energy type
                best_target = None
                best_priority = -1
                
                for bench_idx, bench_pokemon in eligible_pokemon:
                    priority = 0
                    
                    # Check if Pokemon has attacks requiring this energy type
                    for attack in bench_pokemon.card.attacks:
                        energy_cost = attack.get('cost', [])
                        for cost_energy in energy_cost:
                            if (cost_energy == energy_type or 
                                (cost_energy in ['C', 'Colorless'] and energy_type != 'Colorless')):
                                priority += 10  # High priority for Pokemon that need this energy
                    
                    # Prefer Pokemon with fewer energy attached (spread strategy)
                    energy_count = len(bench_pokemon.energy_attached)
                    priority += max(0, 3 - energy_count)  # Bonus for Pokemon with less energy
                    
                    if priority > best_priority:
                        best_priority = priority
                        best_target = (bench_idx, bench_pokemon)
                
                # Attach energy to best target
                if best_target:
                    bench_idx, bench_pokemon = best_target
                    bench_pokemon.attach_energy(energy_type)
                    remaining_energy -= 1
                    energy_distributed += 1
                    distribution_log.append(f"{bench_pokemon.card.name}")
                    
                    # Remove from eligible list if it has enough energy
                    if len(bench_pokemon.energy_attached) >= 3:  # Reasonable energy limit
                        eligible_pokemon = [(i, p) for i, p in eligible_pokemon if i != bench_idx]
                else:
                    # No more eligible targets
                    break
            
            # Log the distribution
            if energy_distributed > 0:
                self.logger.info(f"Distributed {energy_distributed}x {energy_type} energy to bench: {', '.join(distribution_log)}")
            
            if remaining_energy > 0:
                self.logger.warning(f"Could not distribute {remaining_energy}x {energy_type} energy - no eligible targets")
                
        except Exception as e:
            self.logger.error(f"Energy distribution failed: {e}")
    
    def _trigger_abilities(self, trigger_timing: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Trigger all abilities that match the specified timing"""
        try:
            if not self.effect_engine:
                return []
            
            if context is None:
                context = {}
            
            ability_results = []
            
            # Collect all Pokemon with abilities
            all_pokemon = []
            for player in self.players:
                if player.active_pokemon:
                    all_pokemon.append((player.active_pokemon, player.player_id))
                for bench_pokemon in player.bench:
                    if bench_pokemon:
                        all_pokemon.append((bench_pokemon, player.player_id))
            
            # Process abilities for each Pokemon
            for pokemon, player_id in all_pokemon:
                try:
                    # Convert to battle card for ability checking
                    battle_card = self.card_bridge.convert_to_battle_card(pokemon.card)
                    
                    # Check if this Pokemon has abilities that match the trigger
                    for ability in battle_card.abilities or []:
                        ability_type = ability.get('type', '')
                        ability_name = ability.get('name', 'Unknown')
                        
                        # Check if ability should trigger
                        if self._should_trigger_ability(ability, trigger_timing, context):
                            # Execute ability effect
                            result = self._execute_ability(ability, pokemon, player_id, context)
                            if result:
                                ability_results.append(result)
                                self.logger.info(f"Triggered ability '{ability_name}' on {pokemon.card.name}")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to process abilities for {pokemon.card.name}: {e}")
            
            return ability_results
            
        except Exception as e:
            self.logger.error(f"Ability triggering failed: {e}")
            return []
    
    def _should_trigger_ability(self, ability: Dict[str, Any], trigger_timing: str, context: Dict[str, Any]) -> bool:
        """Check if an ability should trigger based on timing and conditions"""
        try:
            ability_type = ability.get('type', '')
            effect_text = ability.get('effect_text', '').lower()
            
            # Map trigger timing to ability conditions
            timing_checks = {
                'on_play': ['when you play', 'when this pokémon enters'],
                'on_attack': ['when this pokémon attacks', 'when attacking'],
                'on_damage': ['when this pokémon takes damage', 'when damaged'],
                'on_knockout': ['when this pokémon is knocked out', 'when ko'],
                'turn_start': ['at the beginning of your turn', 'each turn'],
                'turn_end': ['at the end of your turn', 'end of turn'],
                'passive': ['as long as', 'while', 'continuous']
            }
            
            # Check if any timing condition matches
            relevant_phrases = timing_checks.get(trigger_timing, [])
            for phrase in relevant_phrases:
                if phrase in effect_text:
                    return True
            
            # Special case for passive abilities
            if trigger_timing == 'passive' and ability_type == 'passive':
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Ability trigger check failed: {e}")
            return False
    
    def _execute_ability(self, ability: Dict[str, Any], pokemon, player_id: int, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a triggered ability"""
        try:
            ability_name = ability.get('name', 'Unknown')
            effect_text = ability.get('effect_text', '')
            
            result = {
                'ability_name': ability_name,
                'pokemon_name': pokemon.card.name,
                'player_id': player_id,
                'effects_applied': []
            }
            
            # Parse and execute common ability effects
            if 'draw' in effect_text.lower() and 'card' in effect_text.lower():
                # Card drawing abilities
                import re
                draw_match = re.search(r'draw (\d+)', effect_text.lower())
                if draw_match:
                    cards_to_draw = int(draw_match.group(1))
                    player = self.players[player_id]
                    # In a real implementation, this would draw from deck
                    result['effects_applied'].append(f"Drew {cards_to_draw} cards")
                    self.logger.info(f"Ability {ability_name}: Player {player_id} draws {cards_to_draw} cards")
            
            elif 'energy' in effect_text.lower():
                # Energy-related abilities
                if 'attach' in effect_text.lower():
                    # Energy attachment abilities
                    result['effects_applied'].append("Energy attachment effect")
                    self.logger.info(f"Ability {ability_name}: Energy attachment triggered")
            
            elif 'damage' in effect_text.lower():
                # Damage-related abilities
                if 'prevent' in effect_text.lower() or 'reduce' in effect_text.lower():
                    result['effects_applied'].append("Damage prevention/reduction effect")
                    self.logger.info(f"Ability {ability_name}: Damage modification triggered")
            
            # Generic ability execution
            if not result['effects_applied']:
                result['effects_applied'].append(f"Generic ability effect: {ability_name}")
                self.logger.info(f"Triggered generic ability: {ability_name}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ability execution failed: {e}")
            return None
    
    def _handle_knockout(self, attacker_id: int, defender_id: int):
        """Handle Pokemon knockout and trigger forced Pokemon selection"""
        try:
            attacker = self.players[attacker_id]
            defender = self.players[defender_id]
            
            # Ensure the active Pokemon is actually knocked out
            if not defender.active_pokemon or not defender.active_pokemon.is_knocked_out():
                self.logger.warning(f"_handle_knockout called but Pokemon not actually knocked out")
                return
            
            # Trigger knockout abilities before removing Pokemon
            self._trigger_abilities('on_knockout', {
                'knocked_out_pokemon': defender.active_pokemon,
                'attacker_pokemon': attacker.active_pokemon,
                'attacker_id': attacker_id,
                'defender_id': defender_id
            })
            
            # Award prize points
            points_awarded = 2 if defender.active_pokemon.is_ex_pokemon() else 1
            attacker.prize_points += points_awarded
            
            # Log knockout with descriptive text
            pokemon_name = defender.active_pokemon.card.name
            self._log_pokemon_knockout(defender_id, pokemon_name)
                
            self.logger.info(f"Pokemon KO: Player {attacker_id} scored {points_awarded} points, now has {attacker.prize_points} points")
                
            # Remove knocked out Pokemon from active position
            defender.active_pokemon = None
            
            # CRITICAL: Check win condition immediately after prize points awarded
            if attacker.prize_points >= self.max_prize_points:
                self.logger.info(f"PRIZE POINTS WIN: Player {attacker_id} reaches {attacker.prize_points} points (max: {self.max_prize_points})")
                self._end_battle_winner(attacker_id, "prize_points")
                self.logger.info(f"Battle ended with winner: {self.winner}, is_tie: {self.is_tie}")
                return
            
            # Check if defender can select a replacement Pokemon
            if defender.can_continue_battle():
                # Trigger forced Pokemon selection phase
                self.phase = GamePhase.FORCED_POKEMON_SELECTION
                self.forced_selection_player = defender_id
                # Current player remains the same (attacker) until Pokemon selection is complete
                self.logger.info(f"Pokemon KO: Player {defender_id} must select new active Pokemon before turn continues")
                
                # Log available replacement options for debugging
                options = defender.get_pokemon_selection_options()
                bench_count = len(options['bench_options'])
                hand_count = len(options['hand_options'])
                self.logger.debug(f"Player {defender_id} replacement options: {bench_count} bench, {hand_count} hand")
            else:
                # Defender cannot continue - attacker wins
                self._end_battle_winner(attacker_id, "opponent_unable")
                return
            
        except Exception as e:
            self.logger.error(f"Knockout handling failed: {e}")
            # In case of error, try to end the battle safely
            self._end_battle_winner(attacker_id, "error_during_knockout")
    
    def _end_battle_winner(self, winner_id: int, reason: str):
        """End battle with a winner"""
        if self.winner is not None or self.is_tie:
            self.logger.warning(f"Attempted to set winner {winner_id} ({reason}) but battle already ended: winner={self.winner}, tie={self.is_tie}")
            return
        
        self.winner = winner_id
        self.is_tie = False
        self.end_reason = reason
        self.phase = GamePhase.BATTLE_END
        
        # Log prize points for debugging
        p0_points = self.players[0].prize_points if len(self.players) > 0 else 0
        p1_points = self.players[1].prize_points if len(self.players) > 1 else 0
        self.logger.info(f"🏆 BATTLE ENDED: Player {winner_id} wins ({reason}) - Points: P0={p0_points}, P1={p1_points}")
    
    def _end_battle_tie(self, reason: str):
        """End battle in a tie"""
        if self.winner is not None or self.is_tie:
            self.logger.warning(f"Attempted to set tie ({reason}) but battle already ended: winner={self.winner}, tie={self.is_tie}")
            return
        
        self.winner = None
        self.is_tie = True
        self.end_reason = reason
        self.phase = GamePhase.BATTLE_END
        
        # Log prize points for debugging
        p0_points = self.players[0].prize_points if len(self.players) > 0 else 0
        p1_points = self.players[1].prize_points if len(self.players) > 1 else 0
        self.logger.info(f"🤝 BATTLE ENDED IN TIE ({reason}) - Points: P0={p0_points}, P1={p1_points}")
    
    def _log_action(self, action: BattleAction):
        """Log an action to turn log with descriptive text"""
        descriptive_text = self._generate_descriptive_log(action)
        
        log_entry = {
            "turn": self.turn_number,
            "player": action.player_id,
            "action": action.action_type.value,
            "details": action.details,
            "descriptive_text": descriptive_text,
            "game_state": self.get_current_state_snapshot(),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.turn_log.append(log_entry)
    
    def _generate_descriptive_log(self, action: BattleAction) -> str:
        """Generate human-readable description of an action"""
        player_name = f"Player {action.player_id + 1}"
        player = self.players[action.player_id]
        
        try:
            if action.action_type == ActionType.ATTACK:
                # Get attack name using the same helper method used in validation/execution
                attack, attack_name = self._get_attack_from_action(player, action)
                if not attack_name:
                    attack_name = 'Unknown Attack'
                target_info = ""
                
                # Get attacker info
                if player.active_pokemon:
                    attacker = player.active_pokemon.card.name
                    
                    # Get target info
                    target_player_id = action.details.get('target_player_id')
                    if target_player_id is not None:
                        target_player = self.players[target_player_id]
                        if target_player.active_pokemon:
                            target_info = f" against {target_player.active_pokemon.card.name}"
                    
                    damage = action.details.get('final_damage', action.details.get('damage', 0))
                    
                    # Build detailed attack description
                    attack_text = f"{player_name}'s {attacker} used {attack_name}{target_info}"
                    
                    # Add damage info
                    if damage > 0:
                        attack_text += f" for {damage} damage"
                    
                    # Add coin flip results
                    coin_results = action.details.get('coin_results', [])
                    if coin_results:
                        heads = coin_results.count('heads')
                        tails = coin_results.count('tails')
                        attack_text += f" 🪙({heads}H/{tails}T)"
                    
                    # Add status effects
                    status_effects = action.details.get('status_effects', [])
                    if status_effects:
                        attack_text += f" 💫{', '.join(status_effects)}"
                    
                    # Add additional effects
                    additional_effects = action.details.get('additional_effects', [])
                    if additional_effects:
                        attack_text += f" ✨{', '.join(additional_effects)}"
                    
                    attack_text += "!"
                    return attack_text
                        
                return f"{player_name} used {attack_name}!"
                
            elif action.action_type == ActionType.ATTACH_ENERGY:
                energy_type = action.details.get('energy_type', 'Energy')
                if player.active_pokemon:
                    pokemon_name = player.active_pokemon.card.name
                    return f"{player_name} attached {energy_type} energy to {pokemon_name}"
                return f"{player_name} attached {energy_type} energy"
                
            elif action.action_type == ActionType.PLAY_POKEMON:
                card_name = action.details.get('card_name', 'Pokemon')
                position = action.details.get('position', 'unknown')
                if position == 'active':
                    return f"{player_name} played {card_name} as their Active Pokémon!"
                elif position == 'bench':
                    return f"{player_name} played {card_name} to their Bench"
                return f"{player_name} played {card_name}"
                
            elif action.action_type == ActionType.RETREAT:
                if player.active_pokemon:
                    retreating_pokemon = player.active_pokemon.card.name
                    bench_index = action.details.get('bench_index', 0)
                    if bench_index < len(player.bench) and player.bench[bench_index]:
                        new_active = player.bench[bench_index].card.name
                        return f"{player_name} retreated {retreating_pokemon} and brought up {new_active}!"
                    return f"{player_name} retreated {retreating_pokemon}!"
                return f"{player_name} retreated their Active Pokémon!"
                
            elif action.action_type == ActionType.USE_ABILITY:
                ability_name = action.details.get('ability_name', 'Unknown Ability')
                if player.active_pokemon:
                    pokemon_name = player.active_pokemon.card.name
                    return f"{player_name}'s {pokemon_name} used ability: {ability_name}!"
                return f"{player_name} used ability: {ability_name}!"
                
            elif action.action_type == ActionType.SELECT_ACTIVE:
                card_name = action.details.get('card_name', 'Pokemon')
                return f"{player_name} selected {card_name} as their new Active Pokémon!"
                
            elif action.action_type == ActionType.PLAY_FROM_HAND:
                card_name = action.details.get('card_name', 'Pokemon')
                return f"{player_name} played {card_name} from hand as Active Pokémon!"
                
            else:
                # Default fallback
                return f"{player_name} performed {action.action_type.value.replace('_', ' ').title()}"
                
        except Exception as e:
            # Fallback in case of any errors
            return f"{player_name} performed {action.action_type.value.replace('_', ' ').title()}"
    
    def _log_turn_start(self):
        """Log start of turn"""
        player_name = f"Player {self.current_player + 1}"
        current_player = self.players[self.current_player]
        
        # Generate descriptive turn start text
        descriptive_text = f"🎯 **TURN {self.turn_number}** - {player_name}'s turn begins!"
        
        # Add hand size info
        hand_size = len(current_player.hand) if current_player.hand else 0
        descriptive_text += f" (Hand: {hand_size} cards)"
        
        # Add active Pokemon info
        if current_player.active_pokemon:
            active_name = current_player.active_pokemon.card.name
            active_hp = f"{current_player.active_pokemon.current_hp}/{current_player.active_pokemon.card.hp}"
            descriptive_text += f" | Active: {active_name} ({active_hp} HP)"
        
        log_entry = {
            "turn": self.turn_number,
            "player": self.current_player,
            "action": "turn_start",
            "details": {},
            "descriptive_text": descriptive_text,
            "game_state": self.get_current_state_snapshot(),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.turn_log.append(log_entry)
    
    def _log_turn_end(self):
        """Log end of turn"""
        player_name = f"Player {self.current_player + 1}"
        descriptive_text = f"✅ {player_name} ends their turn"
        
        log_entry = {
            "turn": self.turn_number,
            "player": self.current_player,
            "action": "turn_end",
            "details": {},
            "descriptive_text": descriptive_text,
            "game_state": self.get_current_state_snapshot(),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.turn_log.append(log_entry)
    
    def _log_card_draw(self, player_id: int, cards_drawn: int = 1):
        """Log card drawing"""
        player_name = f"Player {player_id + 1}"
        if cards_drawn == 1:
            descriptive_text = f"{player_name} drew a card"
        else:
            descriptive_text = f"{player_name} drew {cards_drawn} cards"
            
        log_entry = {
            "turn": self.turn_number,
            "player": player_id,
            "action": "draw_card",
            "details": {"cards_drawn": cards_drawn},
            "descriptive_text": descriptive_text,
            "game_state": self.get_current_state_snapshot(),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.turn_log.append(log_entry)
    
    def _log_pokemon_knockout(self, player_id: int, pokemon_name: str):
        """Log when a Pokemon is knocked out"""
        player_name = f"Player {player_id + 1}"
        descriptive_text = f"💀 {player_name}'s {pokemon_name} was knocked out!"
        
        log_entry = {
            "turn": self.turn_number,
            "player": player_id,
            "action": "pokemon_knockout",
            "details": {"pokemon_name": pokemon_name},
            "descriptive_text": descriptive_text,
            "game_state": self.get_current_state_snapshot(),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.turn_log.append(log_entry)
    
    def _initialize_effect_engine(self):
        """Initialize the advanced effect system with all cards in play"""
        try:
            # Collect all BattleCards from all players
            all_battle_cards = []
            
            for player in self.players:
                # Convert all cards in deck to BattleCards
                for card in player.deck.cards:
                    try:
                        battle_card = self.card_bridge.convert_to_battle_card(card)
                        all_battle_cards.append(battle_card)
                    except Exception as e:
                        self.logger.warning(f"Failed to convert card {card.name}: {e}")
            
            # Initialize effect engine with all cards
            self.effect_engine = AdvancedEffectEngine(
                battle_cards=all_battle_cards,
                logger=self.logger,
                rng_seed=self.rng_seed
            )
            
            # Register effects for all cards currently in play
            for player in self.players:
                if player.active_pokemon:
                    try:
                        battle_card = self.card_bridge.convert_to_battle_card(player.active_pokemon.card)
                        self.effect_engine.register_card_effects(battle_card)
                    except Exception as e:
                        self.logger.warning(f"Failed to register effects for {player.active_pokemon.card.name}: {e}")
                
                for pokemon in player.bench:
                    if pokemon:
                        try:
                            battle_card = self.card_bridge.convert_to_battle_card(pokemon.card)
                            self.effect_engine.register_card_effects(battle_card)
                        except Exception as e:
                            self.logger.warning(f"Failed to register effects for {pokemon.card.name}: {e}")
            
            # Update effect engine with current battle state
            self.effect_engine.update_battle_state(self.turn_number, self.current_player)
            
            self.logger.info(f"Effect engine initialized with {len(all_battle_cards)} cards")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize effect engine: {e}")
            # Continue battle without effect engine
            self.effect_engine = None