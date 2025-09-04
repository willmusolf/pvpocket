"""
Rule-based AI for Pokemon TCG Pocket battle simulation

Simple AI that follows basic strategic rules:
1. Place Basic Pokemon if needed
2. Attach energy when possible  
3. Attack with highest damage
4. Handle forced actions (KO replacement)
"""

import logging
import random
from typing import Dict, List, Optional, Any, Tuple

# Import core battle components
from ..core.game import BattleAction, ActionType
from ..core.energy import EnergyManager


class RuleBasedAI:
    """Simple rule-based AI player for battle simulation"""
    
    def __init__(self, 
                 player_id: int,
                 logger: Optional[logging.Logger] = None,
                 rng_seed: Optional[int] = None):
        """
        Initialize AI player
        
        Args:
            player_id: Player ID this AI controls (0 or 1)
            logger: Logger for AI decisions
            rng_seed: Random seed for deterministic behavior
        """
        self.player_id = player_id
        self.logger = logger or logging.getLogger(__name__)
        
        # Random number generator for deterministic decisions
        if rng_seed is not None:
            self.rng = random.Random(rng_seed + player_id)  # Offset by player_id
        else:
            self.rng = random.Random()
            
        # AI configuration
        self.strategy = "balanced"  # Could be "aggro", "control", "balanced"
        self.decision_timeout_ms = 100
        
        # Strategy weights for decision making
        self.weights = {
            "damage_priority": 1.0,
            "energy_efficiency": 0.8, 
            "hp_preservation": 0.6,
            "setup_priority": 0.9
        }
        
        # Action loop prevention
        self.recent_actions = []  # Track last few actions to prevent infinite loops
        self.max_recent_actions = 5  # Track last 5 actions
        self.retreat_attempts_this_turn = 0  # Track retreat attempts per turn
        
        self.logger.debug(f"Initialized rule-based AI for player {player_id}")
    
    def choose_action(self, game_state) -> Optional[BattleAction]:
        """
        Choose the best action for current game state
        
        Args:
            game_state: Current GameState object
            
        Returns:
            BattleAction to take, or None if no valid actions
        """
        try:
            # Import here to avoid circular import
            from ..core.game import GamePhase
            
            player = game_state.players[self.player_id]
            
            # Reset retreat attempts if it's a new turn
            if hasattr(game_state, 'turn_number'):
                current_turn = game_state.turn_number
                if not hasattr(self, '_last_turn') or self._last_turn != current_turn:
                    self.retreat_attempts_this_turn = 0
                    self._last_turn = current_turn
            
            # Priority 0: Handle initial Pokemon placement phase
            if game_state.phase == GamePhase.INITIAL_POKEMON_PLACEMENT and game_state.current_player == self.player_id:
                action = self._choose_initial_pokemon_placement(game_state)
                if action:
                    self.logger.debug(f"AI Player {self.player_id}: Placing initial Pokemon")
                    return self._track_and_return_action(action)
                else:
                    self.logger.error(f"AI Player {self.player_id}: Cannot place initial Pokemon")
                    return None
            
            # Priority 1: Handle forced Pokemon selection after knockout
            if game_state.phase == GamePhase.FORCED_POKEMON_SELECTION and game_state.forced_selection_player == self.player_id:
                action = self._choose_forced_pokemon_selection(game_state)
                if action:
                    self.logger.debug(f"AI Player {self.player_id}: Selecting replacement Pokemon after knockout")
                    return self._track_and_return_action(action)
                else:
                    self.logger.error(f"AI Player {self.player_id}: Cannot select replacement Pokemon")
                    return None
            
            # Priority 1: Check if active Pokemon is sleeping and handle wake up check
            if player.active_pokemon and hasattr(player.active_pokemon, 'status_conditions'):
                for status_effect in player.active_pokemon.status_conditions:
                    if status_effect.condition.value == 'asleep':
                        # Pokemon is asleep - attempt wake up check
                        if game_state.effect_engine and hasattr(game_state.effect_engine, 'status_manager'):
                            # Process sleep wake up check (50% chance)
                            import random
                            if random.random() < 0.5:  # 50% chance to wake up
                                game_state.effect_engine.status_manager.remove_status_condition(
                                    player.active_pokemon, 
                                    status_effect.condition
                                )
                                self.logger.info(f"AI Player {self.player_id}: Active Pokemon woke up from sleep")
                                break  # Pokemon woke up, continue with normal turn
                            else:
                                # Still sleeping - skip turn
                                self.logger.info(f"AI Player {self.player_id}: Active Pokemon still asleep, skipping turn")
                                return self._create_end_turn_action()
            
            # Priority 2: Handle forced actions (place active Pokemon if needed)
            if not player.active_pokemon:
                action = self._choose_pokemon_placement(game_state, "active")
                if action:
                    self.logger.debug(f"AI Player {self.player_id}: Forced to place active Pokemon")
                    return action
                else:
                    # No Pokemon to place - end turn (should trigger loss)
                    return self._create_end_turn_action()
            
            # Priority 3: Place Pokemon if beneficial
            if self._should_place_pokemon(game_state):
                action = self._choose_pokemon_placement(game_state, "bench")
                if action:
                    self.logger.debug(f"AI Player {self.player_id}: Placing Pokemon on bench")
                    return action
            
            # Priority 4: Attach energy if possible and beneficial
            if self._should_attach_energy(game_state):
                action = self._choose_energy_attachment(game_state)
                if action:
                    self.logger.debug(f"AI Player {self.player_id}: Attaching energy")
                    return action
            
            # Priority 5: Attack if possible
            if self._should_attack(game_state):
                action = self._choose_attack(game_state)
                if action:
                    self.logger.debug(f"AI Player {self.player_id}: Attacking")
                    return action
            
            # Priority 6: Retreat if beneficial (but limit attempts)
            if self.retreat_attempts_this_turn < 2 and self._should_retreat(game_state):
                action = self._choose_retreat(game_state)
                if action:
                    self.retreat_attempts_this_turn += 1
                    self.logger.debug(f"AI Player {self.player_id}: Retreating (attempt {self.retreat_attempts_this_turn})")
                    return self._track_and_return_action(action)
            
            # Default: End turn
            self.logger.debug(f"AI Player {self.player_id}: No beneficial actions, ending turn")
            return self._create_end_turn_action()
            
        except Exception as e:
            self.logger.error(f"AI decision failed for player {self.player_id}: {e}")
            # Fallback to end turn
            return self._create_end_turn_action()
    
    def _track_and_return_action(self, action: BattleAction) -> BattleAction:
        """Track action to prevent infinite loops and return it"""
        # Add to recent actions list
        action_key = f"{action.action_type.value}_{action.details}"
        self.recent_actions.append(action_key)
        
        # Keep only recent actions
        if len(self.recent_actions) > self.max_recent_actions:
            self.recent_actions.pop(0)
            
        return action
    
    def _is_repeated_action(self, action: BattleAction) -> bool:
        """Check if this action was recently attempted multiple times"""
        action_key = f"{action.action_type.value}_{action.details}"
        
        # Count how many times this exact action was recently attempted
        recent_count = self.recent_actions.count(action_key)
        
        # If we've tried this exact action 2+ times recently, consider it repeated
        return recent_count >= 2
    
    def _should_place_pokemon(self, game_state) -> bool:
        """Check if AI should place a Pokemon on bench"""
        player = game_state.players[self.player_id]
        
        # Don't place if bench is full
        if player.get_bench_space() <= 0:
            return False
            
        # Place if we have Basic Pokemon in hand
        basic_pokemon = player.get_playable_basic_pokemon()
        if not basic_pokemon:
            return False
            
        # Place if bench is empty (always good to have backup)
        if player.get_bench_pokemon_count() == 0:
            return True
            
        # Place if active Pokemon is low on HP and might be KO'd
        if player.active_pokemon:
            hp_percentage = player.active_pokemon.get_hp_percentage()
            if hp_percentage < 50:  # Less than 50% HP
                return True
                
        return False
    
    def _should_attach_energy(self, game_state) -> bool:
        """Check if AI should attach energy"""
        player = game_state.players[self.player_id]
        
        # Pokemon TCG Pocket rule: Player 1 cannot attach energy on turn 1
        if self.player_id == 0 and game_state.turn_number == 1:
            return False
        
        # Can't attach if already attached this turn
        if not player.can_attach_energy():
            return False
            
        # Always attach energy if possible (simple strategy)
        return True
    
    def _should_attack(self, game_state) -> bool:
        """Check if AI should attack"""
        player = game_state.players[self.player_id]
        opponent = game_state.players[1 - self.player_id]
        
        # Can't attack if already attacked this turn
        if not player.can_attack():
            return False
        
        # Can't attack if no active Pokemon or opponent
        if not player.active_pokemon or not opponent.active_pokemon:
            return False
            
        # Can't attack if no usable attacks
        available_attacks = player.get_available_attacks()
        if not available_attacks:
            return False
            
        # Simple strategy: always attack if possible
        return True
    
    def _should_retreat(self, game_state) -> bool:
        """Check if AI should retreat active Pokemon"""
        player = game_state.players[self.player_id]
        
        # Can't retreat if no Pokemon on bench
        if player.get_bench_pokemon_count() == 0:
            return False
            
        # Can't retreat if active Pokemon can't retreat
        if not player.get_retreatable_pokemon():
            return False
            
        # Don't retreat if we've already tried multiple times this turn
        if self.retreat_attempts_this_turn >= 2:
            return False
            
        # Retreat if active Pokemon is very low on HP
        if player.active_pokemon:
            hp_percentage = player.active_pokemon.get_hp_percentage()
            if hp_percentage < 20:  # Less than 20% HP
                return True
                
        # Retreat if bench has Pokemon with better attacks
        # (Simple heuristic: more energy attached = better)
        active_energy = len(player.active_pokemon.energy_attached)
        for bench_pokemon in player.bench:
            if bench_pokemon and not bench_pokemon.is_knocked_out():
                bench_energy = len(bench_pokemon.energy_attached)
                if bench_energy > active_energy:
                    return True
                    
        return False
    
    def _choose_forced_pokemon_selection(self, game_state) -> Optional[BattleAction]:
        """Choose Pokemon to replace knocked out active Pokemon"""
        from ..core.game import BattleAction, ActionType
        
        player = game_state.players[self.player_id]
        
        # Priority 1: Choose from bench if available
        best_bench_index = -1
        best_bench_score = -1
        
        for i, bench_pokemon in enumerate(player.bench):
            if bench_pokemon and not bench_pokemon.is_knocked_out():
                # Score based on HP, energy, and available attacks
                hp_score = bench_pokemon.current_hp / max(bench_pokemon.max_hp, 1)
                energy_score = len(bench_pokemon.energy_attached) * 0.2
                attack_score = len(bench_pokemon.get_usable_attacks()) * 0.3
                
                total_score = hp_score + energy_score + attack_score
                
                if total_score > best_bench_score:
                    best_bench_score = total_score
                    best_bench_index = i
        
        if best_bench_index >= 0:
            return BattleAction(
                action_type=ActionType.SELECT_ACTIVE_POKEMON,
                player_id=self.player_id,
                details={
                    "selection_type": "bench",
                    "bench_index": best_bench_index
                }
            )
        
        # Priority 2: Choose Basic Pokemon from hand
        basic_pokemon = player.get_playable_basic_pokemon()
        if basic_pokemon:
            # Choose Pokemon with highest HP
            chosen_pokemon = max(basic_pokemon, key=lambda card: card.hp or 0)
            return BattleAction(
                action_type=ActionType.SELECT_ACTIVE_POKEMON,
                player_id=self.player_id,
                details={
                    "selection_type": "hand",
                    "card_id": chosen_pokemon.id
                }
            )
        
        # No valid Pokemon available
        return None
    
    def _choose_initial_pokemon_placement(self, game_state) -> Optional[BattleAction]:
        """Choose initial Pokemon placement (active + optional bench)"""
        player = game_state.players[self.player_id]
        
        # Get Basic Pokemon in hand
        basic_pokemon = [card for card in player.hand if card.is_pokemon and card.is_basic]
        
        if not basic_pokemon:
            self.logger.error(f"AI Player {self.player_id}: No Basic Pokemon in hand for initial placement")
            return None
        
        # Strategy: Place strongest Pokemon as active, weaker ones on bench
        basic_pokemon.sort(key=lambda card: card.hp or 0, reverse=True)
        
        placements = []
        
        # Must place at least one as active
        placements.append({
            "card_id": basic_pokemon[0].id,
            "position": "active"
        })
        
        # Place additional Pokemon on bench if available (up to 3 bench slots)
        for i in range(1, min(len(basic_pokemon), 4)):  # active + 3 bench max
            placements.append({
                "card_id": basic_pokemon[i].id,
                "position": "bench"
            })
        
        self.logger.debug(f"AI Player {self.player_id}: Placing {len(placements)} Pokemon ({placements[0]['position']} + {len(placements)-1} bench)")
        
        return BattleAction(
            action_type=ActionType.INITIAL_POKEMON_PLACEMENT,
            player_id=self.player_id,
            details={"placements": placements}
        )
    
    def _choose_pokemon_placement(self, game_state, position: str) -> Optional[BattleAction]:
        """Choose which Pokemon to place and where"""
        player = game_state.players[self.player_id]
        basic_pokemon = player.get_playable_basic_pokemon()
        
        if not basic_pokemon:
            return None
            
        # Simple strategy: place Pokemon with highest HP first
        chosen_pokemon = max(basic_pokemon, key=lambda card: card.hp or 0)
        
        return BattleAction(
            action_type=ActionType.PLACE_POKEMON,
            player_id=self.player_id,
            details={
                "card_id": chosen_pokemon.id,
                "position": position
            }
        )
    
    def _choose_energy_attachment(self, game_state) -> Optional[BattleAction]:
        """Choose energy type to attach"""
        player = game_state.players[self.player_id]
        
        if not player.active_pokemon:
            return None
            
        # Use energy manager to suggest best energy type
        energy_manager = EnergyManager()
        
        suggested_energy = energy_manager.suggest_energy_attachment(
            deck_types=player.energy_types_available,
            pokemon_energy=player.active_pokemon.energy_attached,
            available_attacks=player.active_pokemon.card.attacks,
            rng=self.rng
        )
        
        if suggested_energy:
            energy_type = energy_manager.energy_type_to_string(suggested_energy)
        else:
            # Fallback to random type from deck
            if player.energy_types_available:
                energy_type = self.rng.choice(player.energy_types_available)
            else:
                energy_type = "Fire"  # Default to Fire, never attach Colorless
        
        return BattleAction(
            action_type=ActionType.ATTACH_ENERGY,
            player_id=self.player_id,
            details={
                "energy_type": energy_type
            }
        )
    
    def _choose_attack(self, game_state) -> Optional[BattleAction]:
        """Choose which attack to use"""
        player = game_state.players[self.player_id]
        opponent = game_state.players[1 - self.player_id]
        
        if not player.active_pokemon or not opponent.active_pokemon:
            return None
            
        available_attacks = player.get_available_attacks()
        if not available_attacks:
            return None
            
        # Choose attack with highest damage
        best_attack = None
        best_damage = -1
        
        for attack in available_attacks:
            # Calculate potential damage
            damage = player.active_pokemon.calculate_attack_damage(
                attack=attack,
                target=opponent.active_pokemon,
                weakness_bonus=game_state.weakness_damage_bonus
            )
            
            if damage > best_damage:
                best_damage = damage
                best_attack = attack
        
        if best_attack:
            return BattleAction(
                action_type=ActionType.ATTACK,
                player_id=self.player_id,
                details={
                    "attack_name": best_attack.get("name", ""),
                    "target": "opponent_active"
                }
            )
            
        return None
    
    def _choose_retreat(self, game_state) -> Optional[BattleAction]:
        """Choose which bench Pokemon to bring active"""
        player = game_state.players[self.player_id]
        
        if not player.get_retreatable_pokemon():
            return None
            
        # Find best bench Pokemon to make active
        best_index = -1
        best_score = -1
        
        for i, bench_pokemon in enumerate(player.bench):
            if bench_pokemon and not bench_pokemon.is_knocked_out():
                # Score based on HP and energy
                hp_score = bench_pokemon.current_hp / max(bench_pokemon.max_hp, 1)
                energy_score = len(bench_pokemon.energy_attached) * 0.1
                attack_score = len(bench_pokemon.get_usable_attacks()) * 0.2
                
                total_score = hp_score + energy_score + attack_score
                
                if total_score > best_score:
                    best_score = total_score
                    best_index = i
        
        if best_index >= 0:
            return BattleAction(
                action_type=ActionType.RETREAT,
                player_id=self.player_id,
                details={
                    "bench_index": best_index
                }
            )
            
        return None
    
    def _create_end_turn_action(self) -> BattleAction:
        """Create end turn action"""
        return BattleAction(
            action_type=ActionType.END_TURN,
            player_id=self.player_id,
            details={}
        )
    
    def handle_forced_choice(self, 
                           choice_type: str, 
                           options: List[Any], 
                           game_state) -> Any:
        """
        Handle forced choices (e.g., choosing new active Pokemon after KO)
        
        Args:
            choice_type: Type of choice required
            options: Available options
            game_state: Current game state
            
        Returns:
            Chosen option
        """
        try:
            if choice_type == "choose_active_pokemon":
                # Choose Pokemon with highest HP
                if options:
                    return max(options, key=lambda pokemon: pokemon.current_hp)
                    
            elif choice_type == "choose_bench_pokemon":
                # Choose Pokemon with most energy
                if options:
                    return max(options, key=lambda pokemon: len(pokemon.energy_attached))
                    
            elif choice_type == "discard_cards":
                # Discard cards with lowest value (simple heuristic)
                if options:
                    # Prefer to discard non-Pokemon cards
                    trainers = [card for card in options if card.is_trainer]
                    if trainers:
                        return self.rng.choice(trainers)
                    else:
                        return self.rng.choice(options)
            
            # Default: random choice
            if options:
                return self.rng.choice(options)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Forced choice handling failed: {e}")
            return options[0] if options else None
    
    def get_strategy_weights(self) -> Dict[str, float]:
        """Get current strategy weights for analysis"""
        return self.weights.copy()
    
    def set_strategy(self, strategy: str, weights: Optional[Dict[str, float]] = None):
        """
        Set AI strategy
        
        Args:
            strategy: Strategy name ("aggro", "control", "balanced")
            weights: Custom weights for decision making
        """
        self.strategy = strategy
        
        if weights:
            self.weights.update(weights)
        else:
            # Default weights for different strategies
            if strategy == "aggro":
                self.weights = {
                    "damage_priority": 1.5,
                    "energy_efficiency": 1.0,
                    "hp_preservation": 0.3,
                    "setup_priority": 0.8
                }
            elif strategy == "control":
                self.weights = {
                    "damage_priority": 0.8,
                    "energy_efficiency": 1.2,
                    "hp_preservation": 1.0,
                    "setup_priority": 1.2
                }
            else:  # balanced
                self.weights = {
                    "damage_priority": 1.0,
                    "energy_efficiency": 0.8,
                    "hp_preservation": 0.6,
                    "setup_priority": 0.9
                }
                
        self.logger.debug(f"AI Player {self.player_id} strategy set to {strategy}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AI state to dictionary for logging"""
        return {
            "player_id": self.player_id,
            "strategy": self.strategy,
            "weights": self.weights,
            "ai_type": "rule_based"
        }
    
    def __str__(self) -> str:
        return f"RuleBasedAI(player={self.player_id}, strategy={self.strategy})"