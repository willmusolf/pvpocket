"""
Turn Structure Effects System for Pokemon TCG Pocket Battle Simulator

Handles complex timing restrictions, "once per turn" limitations, triggered abilities,
and turn-based effect tracking for advanced card interactions.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

# Import core components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class EffectTiming(Enum):
    """When effects can be activated"""
    START_OF_TURN = "start_turn"
    END_OF_TURN = "end_turn"
    BETWEEN_TURNS = "between_turns"
    DURING_ATTACK = "during_attack"
    AFTER_ATTACK = "after_attack"
    WHEN_PLAYED = "when_played"
    WHEN_KNOCKED_OUT = "when_ko"
    WHEN_DAMAGED = "when_damaged"
    WHEN_HEALED = "when_healed"
    WHEN_STATUS_APPLIED = "when_status"
    WHEN_EVOLVED = "when_evolved"
    CONTINUOUS = "continuous"
    INSTANT = "instant"


class EffectDuration(Enum):
    """How long effects last"""
    ONCE = "once"                    # Single use
    ONCE_PER_TURN = "once_per_turn"  # Once each turn
    ONCE_PER_GAME = "once_per_game"  # Once for entire game
    UNTIL_END_OF_TURN = "until_eot"  # Until end of current turn
    UNTIL_NEXT_TURN = "until_next"   # Until start of next turn
    PERMANENT = "permanent"          # Lasts entire game
    CONDITIONAL = "conditional"      # Lasts while condition is met


class TriggerCondition(Enum):
    """Conditions that trigger effects"""
    ALWAYS = "always"
    COIN_FLIP_HEADS = "coin_heads"
    COIN_FLIP_TAILS = "coin_tails"
    HP_BELOW_THRESHOLD = "hp_below"
    ENERGY_ATTACHED = "energy_attached"
    STATUS_CONDITION = "has_status"
    POKEMON_TYPE = "pokemon_type"
    OPPONENT_ACTION = "opponent_action"
    SPECIFIC_CARD = "specific_card"


@dataclass
class EffectUsageTracker:
    """Tracks usage of limited effects"""
    effect_id: str
    max_uses_per_turn: int
    max_uses_per_game: int
    
    # Current usage counts
    uses_this_turn: int = 0
    uses_this_game: int = 0
    last_used_turn: int = -1
    
    # Additional restrictions
    can_use_conditions: List[str] = field(default_factory=list)
    disabled_until_turn: int = -1


@dataclass
class TimedEffect:
    """Represents an effect with timing and duration restrictions"""
    effect_id: str
    source_card_id: str
    timing: EffectTiming
    duration: EffectDuration
    source_pokemon: Optional[Any] = None
    trigger_condition: TriggerCondition = TriggerCondition.ALWAYS
    
    # Effect parameters
    effect_type: str = "generic"  # "damage_modification", "status_immunity", etc.
    effect_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Duration tracking
    applied_turn: int = -1
    expires_turn: int = -1
    is_active: bool = True
    
    # Trigger tracking
    trigger_count: int = 0
    max_triggers: int = -1  # -1 = unlimited
    
    # Conditions
    condition_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnState:
    """Complete state for a single turn"""
    turn_number: int
    current_player: int
    
    # Phase tracking
    current_phase: str = "start"  # "start", "main", "attack", "end"
    actions_taken: List[str] = field(default_factory=list)
    
    # Usage tracking
    energy_attached_this_turn: bool = False
    attack_used_this_turn: bool = False
    supporter_played_this_turn: bool = False
    
    # Effect tracking
    active_timed_effects: List[TimedEffect] = field(default_factory=list)
    effect_usage: Dict[str, EffectUsageTracker] = field(default_factory=dict)
    
    # Triggered events this turn
    triggered_events: List[Dict[str, Any]] = field(default_factory=list)


class TurnStructureManager:
    """Manages turn structure, timing restrictions, and effect duration"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Turn tracking
        self.current_turn_state: Optional[TurnState] = None
        self.turn_history: List[TurnState] = []
        self.global_turn_number: int = 0
        
        # Effect management
        self.persistent_effects: Dict[str, TimedEffect] = {}
        self.usage_trackers: Dict[str, EffectUsageTracker] = {}
        
        # Event queue for triggered effects
        self.pending_effects: List[TimedEffect] = []
        self.triggered_abilities: List[Dict[str, Any]] = []
        
        # Built-in effect patterns
        self.effect_patterns = self._build_effect_patterns()
        
        self.logger.debug("Turn Structure Manager initialized")
    
    def _build_effect_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Build common effect patterns with timing restrictions"""
        patterns = {}
        
        # Once per turn abilities
        patterns["draw_card_once_per_turn"] = {
            "timing": EffectTiming.START_OF_TURN,
            "duration": EffectDuration.ONCE_PER_TURN,
            "effect_type": "draw_cards",
            "parameters": {"amount": 1}
        }
        
        patterns["heal_once_per_turn"] = {
            "timing": EffectTiming.BETWEEN_TURNS,
            "duration": EffectDuration.ONCE_PER_TURN,
            "effect_type": "heal",
            "parameters": {"amount": 20}
        }
        
        # Triggered abilities
        patterns["when_damaged_draw"] = {
            "timing": EffectTiming.WHEN_DAMAGED,
            "duration": EffectDuration.ONCE,
            "trigger_condition": TriggerCondition.ALWAYS,
            "effect_type": "draw_cards",
            "parameters": {"amount": 1}
        }
        
        patterns["when_ko_search"] = {
            "timing": EffectTiming.WHEN_KNOCKED_OUT,
            "duration": EffectDuration.ONCE,
            "effect_type": "search_deck",
            "parameters": {"search_type": "pokemon", "amount": 1}
        }
        
        # Continuous effects with conditions
        patterns["type_damage_boost"] = {
            "timing": EffectTiming.CONTINUOUS,
            "duration": EffectDuration.PERMANENT,
            "effect_type": "damage_modification",
            "parameters": {"damage_bonus": 10, "condition": "same_type"}
        }
        
        # Time-limited effects
        patterns["immunity_this_turn"] = {
            "timing": EffectTiming.INSTANT,
            "duration": EffectDuration.UNTIL_END_OF_TURN,
            "effect_type": "status_immunity",
            "parameters": {"immune_to": ["burn", "poison"]}
        }
        
        return patterns
    
    def start_new_turn(self, turn_number: int, player_id: int) -> TurnState:
        """
        Start a new turn and set up tracking
        
        Args:
            turn_number: Global turn number
            player_id: Player whose turn it is
            
        Returns:
            New TurnState for this turn
        """
        # Save previous turn to history
        if self.current_turn_state:
            self.turn_history.append(self.current_turn_state)
        
        # Create new turn state
        self.current_turn_state = TurnState(
            turn_number=turn_number,
            current_player=player_id
        )
        self.global_turn_number = turn_number
        
        # Reset per-turn usage counters
        self._reset_turn_counters()
        
        # Process start-of-turn effects
        self._process_timing_effects(EffectTiming.START_OF_TURN)
        
        # Update continuous effects
        self._update_continuous_effects()
        
        self.logger.debug(f"Started turn {turn_number} for player {player_id}")
        return self.current_turn_state
    
    def end_current_turn(self) -> Optional[TurnState]:
        """
        End the current turn and process end-of-turn effects
        
        Returns:
            Completed TurnState
        """
        if not self.current_turn_state:
            return None
        
        # Process end-of-turn effects
        self._process_timing_effects(EffectTiming.END_OF_TURN)
        
        # Expire timed effects
        self._expire_turn_effects()
        
        # Process between-turns effects (will be applied before next turn starts)
        self._process_timing_effects(EffectTiming.BETWEEN_TURNS)
        
        completed_turn = self.current_turn_state
        self.logger.debug(f"Ended turn {completed_turn.turn_number}")
        
        return completed_turn
    
    def register_timed_effect(self, effect: TimedEffect) -> bool:
        """
        Register a new timed effect
        
        Args:
            effect: TimedEffect to register
            
        Returns:
            True if effect was registered successfully
        """
        try:
            # Check if effect can be used
            if not self._can_use_effect(effect.effect_id):
                return False
            
            # Set timing information
            effect.applied_turn = self.global_turn_number
            
            if effect.duration == EffectDuration.UNTIL_END_OF_TURN:
                effect.expires_turn = self.global_turn_number
            elif effect.duration == EffectDuration.UNTIL_NEXT_TURN:
                effect.expires_turn = self.global_turn_number + 1
            
            # Register effect
            if effect.duration == EffectDuration.PERMANENT:
                self.persistent_effects[effect.effect_id] = effect
            else:
                if self.current_turn_state:
                    self.current_turn_state.active_timed_effects.append(effect)
            
            # Update usage tracking
            self._update_usage_tracking(effect.effect_id)
            
            self.logger.debug(f"Registered timed effect: {effect.effect_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register timed effect {effect.effect_id}: {e}")
            return False
    
    def can_use_ability(self, ability_id: str, card_id: str) -> Tuple[bool, str]:
        """
        Check if an ability can be used right now
        
        Args:
            ability_id: Unique identifier for the ability
            card_id: Card that has the ability
            
        Returns:
            (can_use, reason_if_not)
        """
        # Check usage tracking
        if ability_id in self.usage_trackers:
            tracker = self.usage_trackers[ability_id]
            
            # Check per-turn limit
            if (tracker.max_uses_per_turn > 0 and 
                tracker.uses_this_turn >= tracker.max_uses_per_turn):
                return False, f"Already used {tracker.max_uses_per_turn} times this turn"
            
            # Check per-game limit
            if (tracker.max_uses_per_game > 0 and 
                tracker.uses_this_game >= tracker.max_uses_per_game):
                return False, f"Already used maximum {tracker.max_uses_per_game} times this game"
            
            # Check if disabled
            if tracker.disabled_until_turn > self.global_turn_number:
                return False, f"Disabled until turn {tracker.disabled_until_turn}"
        
        # Check turn-based restrictions
        if not self.current_turn_state:
            return False, "No active turn"
        
        # Check phase restrictions (simplified)
        # This would be expanded with actual phase checking
        
        return True, ""
    
    def use_ability(self, ability_id: str, card_id: str, 
                   effect_parameters: Dict[str, Any]) -> bool:
        """
        Mark ability as used and apply its effects
        
        Args:
            ability_id: Unique identifier for the ability
            card_id: Card that has the ability
            effect_parameters: Parameters for the effect
            
        Returns:
            True if ability was used successfully
        """
        can_use, reason = self.can_use_ability(ability_id, card_id)
        if not can_use:
            self.logger.warning(f"Cannot use ability {ability_id}: {reason}")
            return False
        
        # Create usage tracker if needed
        if ability_id not in self.usage_trackers:
            # Get limitations from effect parameters
            max_per_turn = effect_parameters.get('max_uses_per_turn', -1)
            max_per_game = effect_parameters.get('max_uses_per_game', -1)
            
            self.usage_trackers[ability_id] = EffectUsageTracker(
                effect_id=ability_id,
                max_uses_per_turn=max_per_turn,
                max_uses_per_game=max_per_game
            )
        
        # Update usage counters
        tracker = self.usage_trackers[ability_id]
        tracker.uses_this_turn += 1
        tracker.uses_this_game += 1
        tracker.last_used_turn = self.global_turn_number
        
        # Record action in turn state
        if self.current_turn_state:
            self.current_turn_state.actions_taken.append(f"ability_{ability_id}")
        
        self.logger.debug(f"Used ability {ability_id} (turn usage: {tracker.uses_this_turn})")
        return True
    
    def trigger_event(self, event_type: str, event_data: Dict[str, Any]) -> List[TimedEffect]:
        """
        Trigger event and check for responsive effects
        
        Args:
            event_type: Type of event ("pokemon_damaged", "pokemon_ko", etc.)
            event_data: Data about the event
            
        Returns:
            List of effects that were triggered
        """
        triggered_effects = []
        
        # Check all active effects for triggers
        all_effects = list(self.persistent_effects.values())
        if self.current_turn_state:
            all_effects.extend(self.current_turn_state.active_timed_effects)
        
        for effect in all_effects:
            if self._should_trigger_effect(effect, event_type, event_data):
                # Check if effect can trigger (usage limits, etc.)
                if effect.max_triggers > 0 and effect.trigger_count >= effect.max_triggers:
                    continue
                
                effect.trigger_count += 1
                triggered_effects.append(effect)
                
                # Add to pending effects queue
                self.pending_effects.append(effect)
        
        # Record triggered event
        if self.current_turn_state:
            self.current_turn_state.triggered_events.append({
                "event_type": event_type,
                "event_data": event_data,
                "triggered_effects": [e.effect_id for e in triggered_effects]
            })
        
        self.logger.debug(f"Event {event_type} triggered {len(triggered_effects)} effects")
        return triggered_effects
    
    def process_pending_effects(self) -> List[Dict[str, Any]]:
        """
        Process all pending effects and return their results
        
        Returns:
            List of effect results
        """
        results = []
        
        while self.pending_effects:
            effect = self.pending_effects.pop(0)
            
            try:
                result = self._execute_effect(effect)
                results.append(result)
                
                # Check if effect should be removed after execution
                if effect.duration == EffectDuration.ONCE:
                    self._remove_effect(effect)
                
            except Exception as e:
                self.logger.error(f"Failed to execute pending effect {effect.effect_id}: {e}")
        
        return results
    
    def check_continuous_effect(self, effect_type: str, parameters: Dict[str, Any]) -> Any:
        """
        Check if any continuous effects modify a game mechanic
        
        Args:
            effect_type: Type of effect to check ("damage_modification", etc.)
            parameters: Context parameters
            
        Returns:
            Modification value or None if no effects apply
        """
        modification = None
        
        # Check all active continuous effects
        all_effects = list(self.persistent_effects.values())
        if self.current_turn_state:
            all_effects.extend(self.current_turn_state.active_timed_effects)
        
        for effect in all_effects:
            if (effect.timing == EffectTiming.CONTINUOUS and 
                effect.effect_type == effect_type and 
                effect.is_active):
                
                # Check if effect applies to current context
                if self._effect_applies_to_context(effect, parameters):
                    # Apply modification
                    if effect_type == "damage_modification":
                        bonus = effect.effect_parameters.get('damage_bonus', 0)
                        modification = (modification or 0) + bonus
                    
                    # Add other effect types as needed
        
        return modification
    
    def _reset_turn_counters(self):
        """Reset per-turn usage counters"""
        for tracker in self.usage_trackers.values():
            if tracker.last_used_turn != self.global_turn_number:
                tracker.uses_this_turn = 0
    
    def _process_timing_effects(self, timing: EffectTiming):
        """Process all effects with specific timing"""
        all_effects = list(self.persistent_effects.values())
        if self.current_turn_state:
            all_effects.extend(self.current_turn_state.active_timed_effects)
        
        for effect in all_effects:
            if effect.timing == timing and effect.is_active:
                # Check if effect should trigger
                if self._should_effect_activate(effect):
                    self.pending_effects.append(effect)
    
    def _update_continuous_effects(self):
        """Update status of continuous effects"""
        all_effects = list(self.persistent_effects.values())
        if self.current_turn_state:
            all_effects.extend(self.current_turn_state.active_timed_effects)
        
        for effect in all_effects:
            if effect.timing == EffectTiming.CONTINUOUS:
                # Check if conditions are still met
                if effect.trigger_condition != TriggerCondition.ALWAYS:
                    effect.is_active = self._check_trigger_condition(effect)
    
    def _expire_turn_effects(self):
        """Remove effects that have expired"""
        if not self.current_turn_state:
            return
        
        # Remove expired effects
        active_effects = []
        for effect in self.current_turn_state.active_timed_effects:
            if (effect.expires_turn == -1 or 
                effect.expires_turn > self.global_turn_number):
                active_effects.append(effect)
            else:
                self.logger.debug(f"Expired effect: {effect.effect_id}")
        
        self.current_turn_state.active_timed_effects = active_effects
        
        # Also check persistent effects
        expired_persistent = []
        for effect_id, effect in self.persistent_effects.items():
            if (effect.expires_turn != -1 and 
                effect.expires_turn <= self.global_turn_number):
                expired_persistent.append(effect_id)
        
        for effect_id in expired_persistent:
            del self.persistent_effects[effect_id]
            self.logger.debug(f"Expired persistent effect: {effect_id}")
    
    def _can_use_effect(self, effect_id: str) -> bool:
        """Check if effect can be used based on limitations"""
        if effect_id in self.usage_trackers:
            tracker = self.usage_trackers[effect_id]
            
            # Check turn limit
            if (tracker.max_uses_per_turn > 0 and 
                tracker.uses_this_turn >= tracker.max_uses_per_turn):
                return False
            
            # Check game limit
            if (tracker.max_uses_per_game > 0 and 
                tracker.uses_this_game >= tracker.max_uses_per_game):
                return False
        
        return True
    
    def _update_usage_tracking(self, effect_id: str):
        """Update usage counters for an effect"""
        if effect_id in self.usage_trackers:
            tracker = self.usage_trackers[effect_id]
            tracker.uses_this_turn += 1
            tracker.uses_this_game += 1
            tracker.last_used_turn = self.global_turn_number
    
    def _should_trigger_effect(self, effect: TimedEffect, 
                              event_type: str, event_data: Dict[str, Any]) -> bool:
        """Check if effect should trigger for given event"""
        # Map timing to event types
        timing_events = {
            EffectTiming.WHEN_DAMAGED: ["pokemon_damaged"],
            EffectTiming.WHEN_KNOCKED_OUT: ["pokemon_ko"],
            EffectTiming.WHEN_HEALED: ["pokemon_healed"],
            EffectTiming.WHEN_STATUS_APPLIED: ["status_applied"],
            EffectTiming.WHEN_EVOLVED: ["pokemon_evolved"]
        }
        
        if effect.timing in timing_events:
            if event_type not in timing_events[effect.timing]:
                return False
        else:
            return False
        
        # Check trigger condition
        return self._check_trigger_condition(effect, event_data)
    
    def _should_effect_activate(self, effect: TimedEffect) -> bool:
        """Check if timed effect should activate"""
        # Check usage limits
        if not self._can_use_effect(effect.effect_id):
            return False
        
        # Check trigger condition
        return self._check_trigger_condition(effect)
    
    def _check_trigger_condition(self, effect: TimedEffect, 
                                event_data: Optional[Dict[str, Any]] = None) -> bool:
        """Check if trigger condition is met"""
        if effect.trigger_condition == TriggerCondition.ALWAYS:
            return True
        
        # Implement specific trigger conditions
        if effect.trigger_condition == TriggerCondition.COIN_FLIP_HEADS:
            # This would require coin flip result in event_data
            return event_data and event_data.get('coin_result') == 'heads'
        
        if effect.trigger_condition == TriggerCondition.HP_BELOW_THRESHOLD:
            # Check HP threshold
            threshold = effect.condition_parameters.get('hp_threshold', 50)
            pokemon = effect.source_pokemon
            if pokemon:
                hp_percentage = (pokemon.current_hp / pokemon.max_hp) * 100
                return hp_percentage < threshold
        
        # Add other conditions as needed
        return True
    
    def _effect_applies_to_context(self, effect: TimedEffect, 
                                  context: Dict[str, Any]) -> bool:
        """Check if continuous effect applies to current context"""
        # Check conditions in effect parameters
        conditions = effect.effect_parameters.get('conditions', {})
        
        for condition_type, condition_value in conditions.items():
            if condition_type == "same_type":
                # Check if attacking and target Pokemon are same type
                attacker_type = context.get('attacker_type')
                target_type = context.get('target_type')
                if attacker_type and target_type and attacker_type != target_type:
                    return False
        
        return True
    
    def _execute_effect(self, effect: TimedEffect) -> Dict[str, Any]:
        """Execute a timed effect and return result"""
        result = {
            "effect_id": effect.effect_id,
            "success": True,
            "description": f"Executed {effect.effect_type}",
            "details": {}
        }
        
        try:
            # Execute based on effect type
            if effect.effect_type == "draw_cards":
                amount = effect.effect_parameters.get('amount', 1)
                result["details"]["cards_drawn"] = amount
                result["description"] = f"Drew {amount} cards"
            
            elif effect.effect_type == "heal":
                amount = effect.effect_parameters.get('amount', 0)
                target = effect.source_pokemon
                if target:
                    healed = target.heal(amount)
                    result["details"]["healed_amount"] = healed
                    result["description"] = f"Healed {healed} HP"
            
            elif effect.effect_type == "damage_modification":
                bonus = effect.effect_parameters.get('damage_bonus', 0)
                result["details"]["damage_bonus"] = bonus
                result["description"] = f"Damage modified by {bonus}"
            
            # Add more effect types as needed
            
        except Exception as e:
            result["success"] = False
            result["description"] = f"Effect execution failed: {e}"
            self.logger.error(f"Effect execution failed for {effect.effect_id}: {e}")
        
        return result
    
    def _remove_effect(self, effect: TimedEffect):
        """Remove effect from tracking"""
        # Remove from persistent effects
        if effect.effect_id in self.persistent_effects:
            del self.persistent_effects[effect.effect_id]
        
        # Remove from current turn effects
        if self.current_turn_state:
            self.current_turn_state.active_timed_effects = [
                e for e in self.current_turn_state.active_timed_effects 
                if e.effect_id != effect.effect_id
            ]
    
    def get_turn_summary(self) -> Optional[Dict[str, Any]]:
        """Get summary of current turn state"""
        if not self.current_turn_state:
            return None
        
        return {
            "turn_number": self.current_turn_state.turn_number,
            "current_player": self.current_turn_state.current_player,
            "current_phase": self.current_turn_state.current_phase,
            "actions_taken": len(self.current_turn_state.actions_taken),
            "active_effects": len(self.current_turn_state.active_timed_effects),
            "triggered_events": len(self.current_turn_state.triggered_events),
            "energy_attached": self.current_turn_state.energy_attached_this_turn,
            "attack_used": self.current_turn_state.attack_used_this_turn,
            "supporter_played": self.current_turn_state.supporter_played_this_turn
        }
    
    def get_effect_status(self, effect_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a specific effect"""
        if effect_id in self.usage_trackers:
            tracker = self.usage_trackers[effect_id]
            return {
                "effect_id": effect_id,
                "uses_this_turn": tracker.uses_this_turn,
                "uses_this_game": tracker.uses_this_game,
                "max_per_turn": tracker.max_uses_per_turn,
                "max_per_game": tracker.max_uses_per_game,
                "can_use": self._can_use_effect(effect_id)
            }
        
        return None
    
    def __str__(self) -> str:
        active_effects = len(self.persistent_effects)
        if self.current_turn_state:
            active_effects += len(self.current_turn_state.active_timed_effects)
        
        return f"TurnStructureManager(turn={self.global_turn_number}, effects={active_effects})"