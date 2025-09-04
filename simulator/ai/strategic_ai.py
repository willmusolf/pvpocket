"""
Strategic AI for Pokemon TCG Pocket Battle Simulation

Enhanced AI that integrates board evaluation, card evaluation, and advanced attack selection
for sophisticated decision making that rivals human-level strategic thinking.
"""

import logging
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Import existing components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ..core.game import BattleAction, ActionType, GamePhase
from ..core.energy import EnergyManager
from .board_evaluator import StrategicBoardEvaluator, GamePhase as BoardGamePhase, ThreatLevel
from .card_evaluator import SmartCardEvaluator, EvaluationContext, CardRole
from .advanced_attack_selector import (
    AdvancedAttackSelector, AttackContext, AttackStrategy, 
    AttackOption, GamePhase as AttackGamePhase
)


class AIPersonality(Enum):
    """AI personality types with different strategic focuses"""
    AGGRESSIVE = "aggressive"    # High-risk, high-reward plays
    BALANCED = "balanced"        # Adaptive, situational play
    CONSERVATIVE = "conservative"  # Safe, efficient plays
    CONTROL = "control"          # Long-term advantage focus
    COMBO = "combo"             # Setup-focused for specific win conditions


@dataclass
class DecisionContext:
    """Complete context for AI decision making"""
    game_state: Any
    board_evaluation: Any
    my_player_id: int
    personality: AIPersonality
    
    # Strategic priorities (0.0 to 2.0)
    aggression_level: float
    risk_tolerance: float
    setup_priority: float
    tempo_priority: float


class StrategicAI:
    """
    Advanced AI that uses strategic evaluation for all decisions.
    Significantly more intelligent than the basic RuleBasedAI.
    """
    
    def __init__(self, 
                 player_id: int,
                 personality: AIPersonality = AIPersonality.BALANCED,
                 logger: Optional[logging.Logger] = None,
                 rng_seed: Optional[int] = None):
        """
        Initialize strategic AI
        
        Args:
            player_id: Player ID this AI controls
            personality: AI personality type
            logger: Logger for AI decisions
            rng_seed: Random seed for deterministic behavior
        """
        self.player_id = player_id
        self.personality = personality
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize strategic components
        self.board_evaluator = StrategicBoardEvaluator(logger)
        self.card_evaluator = SmartCardEvaluator(logger)  
        self.attack_selector = AdvancedAttackSelector(logger)
        self.energy_manager = EnergyManager()
        
        # Random number generator
        if rng_seed is not None:
            self.rng = random.Random(rng_seed + player_id)
        else:
            self.rng = random.Random()
        
        # Personality-specific parameters
        self.personality_params = self._initialize_personality_params(personality)
        
        # Decision tracking
        self.recent_decisions = []
        self.turn_number = 0
        self.decisions_this_turn = 0
        
        self.logger.info(f"Initialized Strategic AI (Player {player_id}, {personality.value})")
    
    def _initialize_personality_params(self, personality: AIPersonality) -> Dict[str, float]:
        """Initialize personality-specific parameters"""
        if personality == AIPersonality.AGGRESSIVE:
            return {
                "aggression_level": 1.6,
                "risk_tolerance": 1.8,
                "setup_priority": 0.7,
                "tempo_priority": 1.5,
                "ko_focus": 1.4
            }
        elif personality == AIPersonality.CONSERVATIVE:
            return {
                "aggression_level": 0.6,
                "risk_tolerance": 0.4,
                "setup_priority": 1.3,
                "tempo_priority": 0.8,
                "ko_focus": 0.9
            }
        elif personality == AIPersonality.CONTROL:
            return {
                "aggression_level": 0.8,
                "risk_tolerance": 0.7,
                "setup_priority": 1.6,
                "tempo_priority": 1.0,
                "ko_focus": 1.1
            }
        elif personality == AIPersonality.COMBO:
            return {
                "aggression_level": 0.9,
                "risk_tolerance": 1.2,
                "setup_priority": 1.8,
                "tempo_priority": 0.6,
                "ko_focus": 1.3
            }
        else:  # BALANCED
            return {
                "aggression_level": 1.0,
                "risk_tolerance": 1.0,
                "setup_priority": 1.0,
                "tempo_priority": 1.0,
                "ko_focus": 1.0
            }
    
    def choose_action(self, game_state) -> Optional[BattleAction]:
        """
        Choose optimal action using strategic evaluation
        
        Args:
            game_state: Current GameState object
            
        Returns:
            BattleAction to take, or None if no valid actions
        """
        try:
            # Track turn changes
            if game_state.turn_number != self.turn_number:
                self.turn_number = game_state.turn_number
                self.decisions_this_turn = 0
            
            self.decisions_this_turn += 1
            
            # Evaluate current board position
            board_eval = self.board_evaluator.evaluate_position(game_state)
            
            # Create decision context
            context = DecisionContext(
                game_state=game_state,
                board_evaluation=board_eval,
                my_player_id=self.player_id,
                personality=self.personality,
                **self.personality_params
            )
            
            # Handle initial Pokemon placement first
            from ..core.game import GamePhase as CoreGamePhase
            if (hasattr(game_state, 'phase') and 
                game_state.phase == CoreGamePhase.INITIAL_POKEMON_PLACEMENT and
                game_state.current_player == self.player_id):
                action = self._choose_initial_pokemon_placement(context)
                if action:
                    self.logger.info(f"Strategic AI: Initial Pokemon placement")
                    return self._track_decision(action, "initial_placement")
            
            # Handle forced selections
            if (hasattr(game_state, 'phase') and 
                game_state.phase == CoreGamePhase.FORCED_POKEMON_SELECTION and
                game_state.forced_selection_player == self.player_id):
                action = self._choose_forced_pokemon_selection(context)
                if action:
                    self.logger.info(f"Strategic AI: Forced Pokemon selection")
                    return self._track_decision(action, "forced_selection")
            
            # Strategic action selection based on board evaluation
            action = self._choose_strategic_action(context)
            
            if action:
                action_desc = f"{action.action_type.value} (strategy: {board_eval.recommended_strategy})"
                self.logger.debug(f"Strategic AI Player {self.player_id}: {action_desc}")
                return self._track_decision(action, action.action_type.value)
            
            # Fallback to end turn
            self.logger.debug(f"Strategic AI Player {self.player_id}: No strategic actions, ending turn")
            return self._create_end_turn_action()
            
        except Exception as e:
            self.logger.error(f"Strategic AI decision failed for player {self.player_id}: {e}")
            # Fallback to basic action
            return self._fallback_action_selection(game_state)
    
    def _choose_strategic_action(self, context: DecisionContext) -> Optional[BattleAction]:
        """Choose action based on strategic evaluation and recommended strategy"""
        game_state = context.game_state
        board_eval = context.board_evaluation
        strategy = board_eval.recommended_strategy
        
        # Get current player state
        player = game_state.players[self.player_id]
        
        # Priority 1: Handle critical threats
        if board_eval.threat_assessment.immediate_ko_threat:
            return self._handle_critical_threat(context)
        
        # Priority 2: Take winning opportunities
        if board_eval.threat_assessment.i_can_ko_next_turn:
            return self._execute_winning_opportunity(context)
        
        # Priority 3: Ensure we have an active Pokemon
        if not player.active_pokemon:
            return self._place_emergency_active_pokemon(context)
        
        # Strategic action based on recommended strategy
        if strategy == "aggressive":
            return self._execute_aggressive_strategy(context)
        elif strategy == "defensive":
            return self._execute_defensive_strategy(context)
        elif strategy == "setup_focused":
            return self._execute_setup_strategy(context)
        elif strategy == "press_advantage":
            return self._execute_advantage_strategy(context)
        elif strategy == "stabilize_board":
            return self._execute_stabilization_strategy(context)
        elif strategy == "close_out":
            return self._execute_closeout_strategy(context)
        elif strategy == "comeback_attempt":
            return self._execute_comeback_strategy(context)
        else:  # balanced or other
            return self._execute_balanced_strategy(context)
    
    def _handle_critical_threat(self, context: DecisionContext) -> Optional[BattleAction]:
        """Handle immediate KO threats"""
        # Priority: Retreat if possible to avoid KO
        retreat_action = self._attempt_strategic_retreat(context)
        if retreat_action:
            return retreat_action
        
        # If can't retreat, try to attack back for revenge KO
        attack_action = self._attempt_strategic_attack(context)
        if attack_action:
            return attack_action
        
        # Last resort: any other action that might help
        return self._attempt_utility_action(context)
    
    def _execute_winning_opportunity(self, context: DecisionContext) -> Optional[BattleAction]:
        """Execute when we can secure a KO"""
        # Focus purely on securing the KO
        attack_context = self._create_attack_context(context, AttackStrategy.SECURE_KO)
        best_attack = self.attack_selector.select_best_attack(attack_context)
        
        if best_attack:
            return self._create_attack_action(best_attack)
        
        # Fallback to any attack if strategic selector fails
        return self._attempt_strategic_attack(context)
    
    def _execute_aggressive_strategy(self, context: DecisionContext) -> Optional[BattleAction]:
        """Execute aggressive strategy - prioritize damage and pressure"""
        # 1. Attack if possible with aggressive strategy
        attack_action = self._attempt_strategic_attack(context, AttackStrategy.MAXIMIZE_DAMAGE)
        if attack_action:
            return attack_action
        
        # 2. Place Pokemon to maintain pressure
        place_action = self._attempt_strategic_pokemon_placement(context)
        if place_action:
            return place_action
        
        # 3. Energy attachment for faster setup
        energy_action = self._attempt_strategic_energy_attachment(context)
        if energy_action:
            return energy_action
        
        return None
    
    def _execute_defensive_strategy(self, context: DecisionContext) -> Optional[BattleAction]:
        """Execute defensive strategy - prioritize survival and board control"""
        # 1. Try to retreat to a safer Pokemon
        retreat_action = self._attempt_strategic_retreat(context)
        if retreat_action:
            return retreat_action
        
        # 2. Attack with disruption focus
        attack_action = self._attempt_strategic_attack(context, AttackStrategy.STATUS_DISRUPTION)
        if attack_action:
            return attack_action
        
        # 3. Build board presence
        place_action = self._attempt_strategic_pokemon_placement(context)
        if place_action:
            return place_action
        
        # 4. Conservative energy attachment
        energy_action = self._attempt_strategic_energy_attachment(context)
        return energy_action
    
    def _execute_setup_strategy(self, context: DecisionContext) -> Optional[BattleAction]:
        """Execute setup-focused strategy"""
        # 1. Place Pokemon for future plays
        place_action = self._attempt_strategic_pokemon_placement(context)
        if place_action:
            return place_action
        
        # 2. Energy attachment for setup
        energy_action = self._attempt_strategic_energy_attachment(context)
        if energy_action:
            return energy_action
        
        # 3. Attack with setup effects
        attack_action = self._attempt_strategic_attack(context, AttackStrategy.SETUP_EFFECTS)
        return attack_action
    
    def _execute_balanced_strategy(self, context: DecisionContext) -> Optional[BattleAction]:
        """Execute balanced strategy - adaptive decision making"""
        game_state = context.game_state
        player = game_state.players[self.player_id]
        
        # Evaluate what's most needed right now
        priorities = self._evaluate_action_priorities(context)
        
        # Execute highest priority action
        for priority_action in sorted(priorities, key=lambda x: x[1], reverse=True):
            action_type, score = priority_action
            
            if action_type == "attack":
                action = self._attempt_strategic_attack(context, AttackStrategy.TEMPO_CONTROL)
            elif action_type == "place_pokemon":
                action = self._attempt_strategic_pokemon_placement(context)
            elif action_type == "attach_energy":
                action = self._attempt_strategic_energy_attachment(context)
            elif action_type == "retreat":
                action = self._attempt_strategic_retreat(context)
            else:
                continue
            
            if action:
                return action
        
        return None
    
    def _evaluate_action_priorities(self, context: DecisionContext) -> List[Tuple[str, float]]:
        """Evaluate priority scores for different action types"""
        priorities = []
        game_state = context.game_state
        player = game_state.players[self.player_id]
        
        # Attack priority
        if player.active_pokemon and player.can_attack():
            attack_score = 50.0
            # Boost if opponent is low HP
            opponent = game_state.players[1 - self.player_id]
            if opponent.active_pokemon:
                hp_ratio = opponent.active_pokemon.current_hp / opponent.active_pokemon.max_hp
                if hp_ratio < 0.5:
                    attack_score += 30
            priorities.append(("attack", attack_score))
        
        # Pokemon placement priority
        if player.get_bench_space() > 0 and player.get_playable_basic_pokemon():
            place_score = 30.0
            # Boost if we have no bench
            if player.get_bench_pokemon_count() == 0:
                place_score += 40
            # Boost early game
            if game_state.turn_number <= 5:
                place_score += 20
            priorities.append(("place_pokemon", place_score))
        
        # Energy attachment priority
        if player.can_attach_energy():
            energy_score = 35.0
            # Boost if active Pokemon needs energy
            if player.active_pokemon:
                usable_attacks = player.active_pokemon.get_usable_attacks()
                total_attacks = len(player.active_pokemon.card.attacks)
                if len(usable_attacks) < total_attacks:
                    energy_score += 25
            priorities.append(("attach_energy", energy_score))
        
        # Retreat priority
        if player.active_pokemon and player.get_retreatable_pokemon():
            retreat_score = 20.0
            # Boost if active Pokemon is low HP
            if player.active_pokemon:
                hp_ratio = player.active_pokemon.current_hp / player.active_pokemon.max_hp
                if hp_ratio < 0.3:
                    retreat_score += 40
            priorities.append(("retreat", retreat_score))
        
        return priorities
    
    def _attempt_strategic_attack(self, context: DecisionContext, 
                                strategy: AttackStrategy = AttackStrategy.TEMPO_CONTROL) -> Optional[BattleAction]:
        """Attempt to make an attack using strategic selection"""
        game_state = context.game_state
        player = game_state.players[self.player_id]
        opponent = game_state.players[1 - self.player_id]
        
        if not player.can_attack() or not player.active_pokemon or not opponent.active_pokemon:
            return None
        
        # Create attack context
        attack_context = self._create_attack_context(context, strategy)
        
        # Select best attack
        best_attack = self.attack_selector.select_best_attack(attack_context)
        
        if best_attack:
            return self._create_attack_action(best_attack)
        
        return None
    
    def _create_attack_context(self, context: DecisionContext, strategy: AttackStrategy) -> AttackContext:
        """Create attack context for the advanced attack selector"""
        game_state = context.game_state
        player = game_state.players[self.player_id]
        opponent = game_state.players[1 - self.player_id]
        
        # Map game phases
        game_phase = AttackGamePhase.MID_GAME
        if game_state.turn_number <= 5:
            game_phase = AttackGamePhase.EARLY_GAME
        elif game_state.turn_number >= 16:
            game_phase = AttackGamePhase.LATE_GAME
        
        return AttackContext(
            my_pokemon=player.active_pokemon,
            target_pokemon=opponent.active_pokemon,
            game_state=game_state,
            board_evaluation=context.board_evaluation,
            my_player_id=self.player_id,
            current_strategy=strategy,
            prize_pressure=context.board_evaluation.threat_assessment.prize_point_pressure,
            turn_number=game_state.turn_number,
            game_phase=game_phase
        )
    
    def _create_attack_action(self, attack_option: AttackOption) -> BattleAction:
        """Create attack action from AttackOption"""
        return BattleAction(
            action_type=ActionType.ATTACK,
            player_id=self.player_id,
            details={
                "attack_name": attack_option.name,
                "target": "opponent_active"
            }
        )
    
    def _attempt_strategic_pokemon_placement(self, context: DecisionContext) -> Optional[BattleAction]:
        """Attempt strategic Pokemon placement"""
        game_state = context.game_state
        player = game_state.players[self.player_id]
        
        if player.get_bench_space() <= 0:
            return None
        
        basic_pokemon = player.get_playable_basic_pokemon()
        if not basic_pokemon:
            return None
        
        # Use card evaluator to choose best Pokemon
        best_pokemon = None
        best_score = -1
        
        # Determine evaluation context
        eval_context = EvaluationContext.MID_GAME
        if game_state.turn_number <= 5:
            eval_context = EvaluationContext.EARLY_GAME
        elif game_state.turn_number >= 16:
            eval_context = EvaluationContext.LATE_GAME
        
        for pokemon_card in basic_pokemon:
            evaluation = self.card_evaluator.evaluate_pokemon(pokemon_card, eval_context)
            if evaluation.total_value > best_score:
                best_score = evaluation.total_value
                best_pokemon = pokemon_card
        
        if best_pokemon:
            # Decide position based on board state
            position = "bench"
            if not player.active_pokemon:
                position = "active"
            
            return BattleAction(
                action_type=ActionType.PLACE_POKEMON,
                player_id=self.player_id,
                details={
                    "card_id": best_pokemon.id,
                    "position": position
                }
            )
        
        return None
    
    def _attempt_strategic_energy_attachment(self, context: DecisionContext) -> Optional[BattleAction]:
        """Attempt strategic energy attachment"""
        game_state = context.game_state
        player = game_state.players[self.player_id]
        
        if not player.can_attach_energy() or not player.active_pokemon:
            return None
        
        # Use energy manager for optimal energy selection
        suggested_energy = self.energy_manager.suggest_energy_attachment(
            deck_types=player.energy_types_available,
            pokemon_energy=player.active_pokemon.energy_attached,
            available_attacks=player.active_pokemon.card.attacks,
            rng=self.rng
        )
        
        if suggested_energy:
            energy_type = self.energy_manager.energy_type_to_string(suggested_energy)
        else:
            # Fallback to deck types
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
    
    def _attempt_strategic_retreat(self, context: DecisionContext) -> Optional[BattleAction]:
        """Attempt strategic retreat"""
        game_state = context.game_state
        player = game_state.players[self.player_id]
        
        if not player.get_retreatable_pokemon() or player.get_bench_pokemon_count() == 0:
            return None
        
        # Evaluate if retreating is beneficial
        current_hp_ratio = player.active_pokemon.current_hp / player.active_pokemon.max_hp
        
        # Find best bench Pokemon to bring active
        best_bench_index = -1
        best_score = -1
        
        for i, bench_pokemon in enumerate(player.bench):
            if bench_pokemon and not bench_pokemon.is_knocked_out():
                # Score based on HP, energy, and usable attacks
                hp_score = bench_pokemon.current_hp / bench_pokemon.max_hp
                energy_score = len(bench_pokemon.energy_attached) * 0.1
                attack_score = len(bench_pokemon.get_usable_attacks()) * 0.2
                
                total_score = hp_score + energy_score + attack_score
                
                if total_score > best_score:
                    best_score = total_score
                    best_bench_index = i
        
        # Only retreat if bench Pokemon is significantly better or we're in danger
        retreat_threshold = 1.3  # Bench Pokemon should be 30% better
        if current_hp_ratio < 0.3:  # Low HP - retreat more readily
            retreat_threshold = 1.0
        
        if best_bench_index >= 0 and (best_score > retreat_threshold or current_hp_ratio < 0.3):
            return BattleAction(
                action_type=ActionType.RETREAT,
                player_id=self.player_id,
                details={
                    "bench_index": best_bench_index
                }
            )
        
        return None
    
    def _attempt_utility_action(self, context: DecisionContext) -> Optional[BattleAction]:
        """Attempt utility actions when other strategies aren't available"""
        # Try basic energy attachment
        energy_action = self._attempt_strategic_energy_attachment(context)
        if energy_action:
            return energy_action
        
        # Try placing Pokemon
        place_action = self._attempt_strategic_pokemon_placement(context)
        if place_action:
            return place_action
        
        return None
    
    # Implement other strategy methods with similar intelligence...
    def _execute_advantage_strategy(self, context: DecisionContext) -> Optional[BattleAction]:
        """Execute when we have advantage - press it"""
        return self._execute_aggressive_strategy(context)  # Similar to aggressive
    
    def _execute_stabilization_strategy(self, context: DecisionContext) -> Optional[BattleAction]:
        """Execute when we need to stabilize"""
        return self._execute_defensive_strategy(context)  # Similar to defensive
    
    def _execute_closeout_strategy(self, context: DecisionContext) -> Optional[BattleAction]:
        """Execute when we're close to winning"""
        return self._execute_aggressive_strategy(context)  # Focus on closing out
    
    def _execute_comeback_strategy(self, context: DecisionContext) -> Optional[BattleAction]:
        """Execute when we're behind and need comeback"""
        return self._execute_defensive_strategy(context)  # Focus on survival/disruption
    
    def _place_emergency_active_pokemon(self, context: DecisionContext) -> Optional[BattleAction]:
        """Emergency Pokemon placement when we have no active"""
        game_state = context.game_state
        player = game_state.players[self.player_id]
        
        # Try bench first
        for i, bench_pokemon in enumerate(player.bench):
            if bench_pokemon and not bench_pokemon.is_knocked_out():
                return BattleAction(
                    action_type=ActionType.SELECT_ACTIVE_POKEMON,
                    player_id=self.player_id,
                    details={
                        "selection_type": "bench",
                        "bench_index": i
                    }
                )
        
        # Try basic Pokemon from hand
        basic_pokemon = player.get_playable_basic_pokemon()
        if basic_pokemon:
            chosen = max(basic_pokemon, key=lambda card: card.hp or 0)
            return BattleAction(
                action_type=ActionType.SELECT_ACTIVE_POKEMON,
                player_id=self.player_id,
                details={
                    "selection_type": "hand",
                    "card_id": chosen.id
                }
            )
        
        return None
    
    def _choose_forced_pokemon_selection(self, context: DecisionContext) -> Optional[BattleAction]:
        """Choose Pokemon replacement after knockout"""
        game_state = context.game_state
        player = game_state.players[self.player_id]
        
        # Evaluate all available options
        best_option = None
        best_score = -1
        
        # Check bench Pokemon
        for i, bench_pokemon in enumerate(player.bench):
            if bench_pokemon and not bench_pokemon.is_knocked_out():
                evaluation = self.card_evaluator.evaluate_pokemon(
                    bench_pokemon.card, EvaluationContext.LATE_GAME
                )
                score = evaluation.total_value
                
                # Adjust score based on current state
                hp_ratio = bench_pokemon.current_hp / bench_pokemon.max_hp
                score *= hp_ratio  # Prefer healthier Pokemon
                
                if score > best_score:
                    best_score = score
                    best_option = ("bench", i)
        
        # Check hand for Basic Pokemon
        basic_pokemon = player.get_playable_basic_pokemon()
        for pokemon_card in basic_pokemon:
            evaluation = self.card_evaluator.evaluate_pokemon(
                pokemon_card, EvaluationContext.LATE_GAME
            )
            score = evaluation.total_value * 1.1  # Slight bonus for fresh Pokemon
            
            if score > best_score:
                best_score = score
                best_option = ("hand", pokemon_card.id)
        
        if best_option:
            selection_type, identifier = best_option
            if selection_type == "bench":
                return BattleAction(
                    action_type=ActionType.SELECT_ACTIVE_POKEMON,
                    player_id=self.player_id,
                    details={
                        "selection_type": "bench",
                        "bench_index": identifier
                    }
                )
            else:  # hand
                return BattleAction(
                    action_type=ActionType.SELECT_ACTIVE_POKEMON,
                    player_id=self.player_id,
                    details={
                        "selection_type": "hand",
                        "card_id": identifier
                    }
                )
        
        return None
    
    def _choose_initial_pokemon_placement(self, context: DecisionContext) -> Optional[BattleAction]:
        """Choose initial Pokemon placement using strategic evaluation"""
        game_state = context.game_state
        player = game_state.players[self.player_id]
        
        # Get Basic Pokemon in hand
        basic_pokemon = [card for card in player.hand if card.is_pokemon and card.is_basic]
        
        if not basic_pokemon:
            self.logger.error(f"Strategic AI Player {self.player_id}: No Basic Pokemon for initial placement")
            return None
        
        # Evaluate each Pokemon for different roles
        pokemon_evaluations = []
        for pokemon in basic_pokemon:
            eval_result = self.card_evaluator.evaluate_pokemon(
                pokemon, EvaluationContext.EARLY_GAME
            )
            pokemon_evaluations.append((pokemon, eval_result))
        
        # Sort by strategic value
        pokemon_evaluations.sort(key=lambda x: x[1].total_value, reverse=True)
        
        # Strategic placement decisions
        placements = []
        
        # Choose best Pokemon as active
        active_pokemon = pokemon_evaluations[0][0]
        placements.append({
            "card_id": active_pokemon.id,
            "position": "active"
        })
        
        # Place additional Pokemon on bench strategically
        remaining_pokemon = pokemon_evaluations[1:]
        
        # Personality-based bench selection
        bench_count = 0
        max_bench = 3
        
        if context.personality == AIPersonality.AGGRESSIVE:
            # Aggressive: Place attackers on bench
            max_bench = 2  # Save hand space for energy/trainers
        elif context.personality == AIPersonality.CONSERVATIVE:
            # Conservative: Place all available Pokemon for safety
            max_bench = min(len(remaining_pokemon), 3)
        else:  # BALANCED, CONTROL, COMBO
            # Balanced approach: Place 1-2 based on strategic value
            max_bench = min(2, len(remaining_pokemon))
        
        for i, (pokemon, evaluation) in enumerate(remaining_pokemon[:max_bench]):
            # Only place if strategic value is high enough
            if evaluation.total_value > 0.6:  # Threshold for bench placement
                placements.append({
                    "card_id": pokemon.id,
                    "position": "bench"
                })
                bench_count += 1
        
        self.logger.info(
            f"Strategic AI Player {self.player_id}: Placing {active_pokemon.name} active + {bench_count} bench " +
            f"(personality: {context.personality.value})"
        )
        
        return BattleAction(
            action_type=ActionType.INITIAL_POKEMON_PLACEMENT,
            player_id=self.player_id,
            details={"placements": placements}
        )
    
    def _track_decision(self, action: BattleAction, decision_type: str) -> BattleAction:
        """Track decision for analysis and loop prevention"""
        decision_key = f"{decision_type}_{action.details}"
        self.recent_decisions.append(decision_key)
        
        # Keep only recent decisions
        if len(self.recent_decisions) > 10:
            self.recent_decisions.pop(0)
        
        return action
    
    def _create_end_turn_action(self) -> BattleAction:
        """Create end turn action"""
        return BattleAction(
            action_type=ActionType.END_TURN,
            player_id=self.player_id,
            details={}
        )
    
    def _fallback_action_selection(self, game_state) -> Optional[BattleAction]:
        """Fallback to basic action selection if strategic analysis fails"""
        from .rule_based import RuleBasedAI
        
        fallback_ai = RuleBasedAI(self.player_id, self.logger)
        return fallback_ai.choose_action(game_state)
    
    # Public interface methods
    def set_personality(self, personality: AIPersonality):
        """Change AI personality and recalculate parameters"""
        self.personality = personality
        self.personality_params = self._initialize_personality_params(personality)
        self.logger.info(f"Strategic AI Player {self.player_id} personality changed to {personality.value}")
    
    def get_decision_analysis(self) -> Dict[str, Any]:
        """Get analysis of recent decisions for debugging"""
        return {
            "player_id": self.player_id,
            "personality": self.personality.value,
            "parameters": self.personality_params,
            "recent_decisions": self.recent_decisions[-5:],  # Last 5 decisions
            "decisions_this_turn": self.decisions_this_turn,
            "turn_number": self.turn_number
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AI state to dictionary for logging"""
        return {
            "player_id": self.player_id,
            "ai_type": "strategic",
            "personality": self.personality.value,
            "parameters": self.personality_params,
            "turn_number": self.turn_number,
            "decisions_this_turn": self.decisions_this_turn
        }
    
    def __str__(self) -> str:
        return f"StrategicAI(player={self.player_id}, personality={self.personality.value})"