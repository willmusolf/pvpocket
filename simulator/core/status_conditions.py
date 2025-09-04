"""
Status Condition System for Pokemon TCG Pocket Battle Simulator
Handles status effects like Burn, Poison, Sleep, Paralysis, and Confusion.
"""

from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
import logging
import random
from dataclasses import dataclass


class StatusCondition(Enum):
    """Possible status conditions in Pokemon TCG Pocket"""
    BURNED = "burned"
    POISONED = "poisoned" 
    ASLEEP = "asleep"
    PARALYZED = "paralyzed"
    CONFUSED = "confused"


@dataclass
class StatusEffect:
    """Represents an active status condition on a Pokemon"""
    condition: StatusCondition
    turns_remaining: Optional[int] = None  # None = indefinite until removed
    damage_per_turn: int = 0
    applied_turn: int = 0
    metadata: Dict = None  # For additional effect data
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StatusManager:
    """Manages status conditions for Pokemon in battle"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Status condition rules
        self.status_rules = {
            StatusCondition.BURNED: {
                'damage_per_turn': 20,
                'blocks_actions': [],
                'removal_chance': 0.0,  # Burn doesn't automatically remove
                'description': 'Takes 20 damage between turns'
            },
            StatusCondition.POISONED: {
                'damage_per_turn': 10,
                'blocks_actions': [],
                'removal_chance': 0.0,  # Poison doesn't automatically remove
                'description': 'Takes 10 damage between turns'
            },
            StatusCondition.ASLEEP: {
                'damage_per_turn': 0,
                'blocks_actions': ['attack', 'retreat'],
                'removal_chance': 0.5,  # 50% chance to wake up each turn
                'description': 'Cannot attack or retreat, 50% chance to wake up each turn'
            },
            StatusCondition.PARALYZED: {
                'damage_per_turn': 0,
                'blocks_actions': ['attack', 'retreat'],
                'removal_chance': 1.0,  # Paralysis removes automatically after one turn
                'description': 'Cannot attack or retreat this turn, removes automatically'
            },
            StatusCondition.CONFUSED: {
                'damage_per_turn': 0,
                'blocks_actions': [],
                'removal_chance': 0.0,  # Confusion persists until manually removed
                'description': 'Must flip coin to attack, takes 30 damage on tails'
            }
        }
    
    def apply_status_condition(self, pokemon_instance, condition: StatusCondition, 
                             current_turn: int, metadata: Dict = None) -> Tuple[bool, str]:
        """Apply a status condition to a Pokemon"""
        if metadata is None:
            metadata = {}
        
        # Check if Pokemon already has this condition
        if hasattr(pokemon_instance, 'status_conditions'):
            for existing_status in pokemon_instance.status_conditions:
                if existing_status.condition == condition:
                    return False, f"Pokemon already has {condition.value} condition"
        
        # Create status effect
        status_effect = StatusEffect(
            condition=condition,
            applied_turn=current_turn,
            damage_per_turn=self.status_rules[condition]['damage_per_turn'],
            metadata=metadata
        )
        
        # Initialize status conditions list if needed
        if not hasattr(pokemon_instance, 'status_conditions'):
            pokemon_instance.status_conditions = []
        
        pokemon_instance.status_conditions.append(status_effect)
        
        pokemon_name = getattr(pokemon_instance, 'name', getattr(pokemon_instance, 'card', {}).name if hasattr(getattr(pokemon_instance, 'card', {}), 'name') else 'Pokemon')
        self.logger.info(f"{pokemon_name} is now {condition.value}")
        return True, f"Applied {condition.value} to {pokemon_name}"
    
    def remove_status_condition(self, pokemon_instance, condition: StatusCondition) -> Tuple[bool, str]:
        """Remove a specific status condition from a Pokemon"""
        if not hasattr(pokemon_instance, 'status_conditions'):
            return False, f"Pokemon doesn't have {condition.value} condition"
        
        # Find and remove the condition
        for i, status_effect in enumerate(pokemon_instance.status_conditions):
            if status_effect.condition == condition:
                del pokemon_instance.status_conditions[i]
                pokemon_name = getattr(pokemon_instance, 'name', getattr(pokemon_instance, 'card', {}).name if hasattr(getattr(pokemon_instance, 'card', {}), 'name') else 'Pokemon')
                self.logger.info(f"{pokemon_name} is no longer {condition.value}")
                return True, f"Removed {condition.value} from {pokemon_name}"
        
        return False, f"Pokemon doesn't have {condition.value} condition"
    
    def clear_all_status_conditions(self, pokemon_instance) -> List[StatusCondition]:
        """Remove all status conditions from a Pokemon"""
        removed_conditions = []
        
        if hasattr(pokemon_instance, 'status_conditions'):
            for status_effect in pokemon_instance.status_conditions:
                removed_conditions.append(status_effect.condition)
            pokemon_instance.status_conditions = []
            
            if removed_conditions:
                pokemon_name = getattr(pokemon_instance, 'name', getattr(pokemon_instance, 'card', {}).name if hasattr(getattr(pokemon_instance, 'card', {}), 'name') else 'Pokemon')
                self.logger.info(f"Cleared all status conditions from {pokemon_name}")
        
        return removed_conditions
    
    def has_status_condition(self, pokemon_instance, condition: StatusCondition) -> bool:
        """Check if Pokemon has a specific status condition"""
        if not hasattr(pokemon_instance, 'status_conditions'):
            return False
        
        return any(status.condition == condition for status in pokemon_instance.status_conditions)
    
    def has_any_status_condition(self, pokemon_instance) -> bool:
        """Check if Pokemon has any status condition"""
        return hasattr(pokemon_instance, 'status_conditions') and len(pokemon_instance.status_conditions) > 0
    
    def get_status_conditions(self, pokemon_instance) -> List[StatusCondition]:
        """Get all status conditions affecting a Pokemon"""
        if not hasattr(pokemon_instance, 'status_conditions'):
            return []
        
        return [status.condition for status in pokemon_instance.status_conditions]
    
    def process_between_turns_effects(self, pokemon_instance, current_turn: int) -> List[Dict]:
        """Process status condition effects that happen between turns"""
        effects_applied = []
        
        if not hasattr(pokemon_instance, 'status_conditions'):
            return effects_applied
        
        conditions_to_remove = []
        
        for status_effect in pokemon_instance.status_conditions:
            condition = status_effect.condition
            rules = self.status_rules[condition]
            
            # Apply damage if any
            if status_effect.damage_per_turn > 0:
                pokemon_instance.take_damage(status_effect.damage_per_turn)
                effects_applied.append({
                    'type': 'status_damage',
                    'condition': condition.value,
                    'damage': status_effect.damage_per_turn,
                    'remaining_hp': pokemon_instance.current_hp
                })
                pokemon_name = getattr(pokemon_instance, 'name', getattr(pokemon_instance, 'card', {}).name if hasattr(getattr(pokemon_instance, 'card', {}), 'name') else 'Pokemon')
                self.logger.info(f"{pokemon_name} took {status_effect.damage_per_turn} damage from {condition.value}")
            
            # Check for automatic removal
            removal_chance = rules['removal_chance']
            if removal_chance > 0:
                if removal_chance >= 1.0 or random.random() < removal_chance:
                    conditions_to_remove.append(condition)
                    effects_applied.append({
                        'type': 'status_removed',
                        'condition': condition.value,
                        'reason': 'automatic'
                    })
        
        # Remove conditions that were cleared
        for condition in conditions_to_remove:
            self.remove_status_condition(pokemon_instance, condition)
        
        return effects_applied
    
    def can_perform_action(self, pokemon_instance, action: str) -> Tuple[bool, str]:
        """Check if Pokemon can perform an action given its status conditions"""
        if not hasattr(pokemon_instance, 'status_conditions'):
            return True, "No status conditions blocking action"
        
        blocked_actions = set()
        blocking_conditions = []
        
        for status_effect in pokemon_instance.status_conditions:
            condition = status_effect.condition
            rules = self.status_rules[condition]
            
            for blocked_action in rules['blocks_actions']:
                if blocked_action == action:
                    blocked_actions.add(blocked_action)
                    blocking_conditions.append(condition.value)
        
        if blocked_actions:
            return False, f"Action '{action}' blocked by: {', '.join(blocking_conditions)}"
        
        return True, "Action allowed"
    
    def handle_confused_attack(self, pokemon_instance) -> Tuple[bool, str, int]:
        """Handle confusion mechanics when attacking"""
        if not self.has_status_condition(pokemon_instance, StatusCondition.CONFUSED):
            return True, "Not confused", 0
        
        # Flip coin for confusion
        coin_flip = random.choice([True, False])  # True = heads, False = tails
        
        if coin_flip:
            # Heads - attack succeeds
            pokemon_name = getattr(pokemon_instance, 'name', getattr(pokemon_instance, 'card', {}).name if hasattr(getattr(pokemon_instance, 'card', {}), 'name') else 'Pokemon')
            self.logger.info(f"{pokemon_name} flipped heads - attack succeeds despite confusion")
            return True, "Confusion overcome - attack succeeds", 0
        else:
            # Tails - Pokemon damages itself
            confusion_damage = 30
            pokemon_instance.take_damage(confusion_damage)
            pokemon_name = getattr(pokemon_instance, 'name', getattr(pokemon_instance, 'card', {}).name if hasattr(getattr(pokemon_instance, 'card', {}), 'name') else 'Pokemon')
            self.logger.info(f"{pokemon_name} flipped tails - confused and hurt itself for {confusion_damage} damage")
            return False, f"Confused - hurt itself for {confusion_damage} damage", confusion_damage
    
    def apply_random_status_condition(self, pokemon_instance, current_turn: int, 
                                    exclude_conditions: Set[StatusCondition] = None) -> Tuple[bool, str]:
        """Apply a random status condition (for effects like Alolan Muk ex)"""
        if exclude_conditions is None:
            exclude_conditions = set()
        
        # Get existing conditions to exclude
        existing_conditions = set(self.get_status_conditions(pokemon_instance))
        exclude_conditions.update(existing_conditions)
        
        # Available conditions to apply
        all_conditions = set(StatusCondition)
        available_conditions = list(all_conditions - exclude_conditions)
        
        if not available_conditions:
            return False, "No available status conditions to apply"
        
        # Choose random condition
        chosen_condition = random.choice(available_conditions)
        
        success, message = self.apply_status_condition(pokemon_instance, chosen_condition, current_turn)
        if success:
            pokemon_name = getattr(pokemon_instance, 'name', getattr(pokemon_instance, 'card', {}).name if hasattr(getattr(pokemon_instance, 'card', {}), 'name') else 'Pokemon')
            self.logger.info(f"Randomly applied {chosen_condition.value} to {pokemon_name}")
        
        return success, message
    
    def get_status_description(self, pokemon_instance) -> str:
        """Get a human-readable description of all status conditions"""
        if not hasattr(pokemon_instance, 'status_conditions') or not pokemon_instance.status_conditions:
            return "No status conditions"
        
        descriptions = []
        for status_effect in pokemon_instance.status_conditions:
            condition = status_effect.condition
            rule_desc = self.status_rules[condition]['description']
            descriptions.append(f"{condition.value.title()}: {rule_desc}")
        
        return "; ".join(descriptions)


def create_status_effect_from_text(effect_text: str) -> Optional[StatusCondition]:
    """Parse status condition from effect text"""
    text_lower = effect_text.lower()
    
    # Map text patterns to status conditions
    status_patterns = {
        'burned': StatusCondition.BURNED,
        'burn': StatusCondition.BURNED,
        'poisoned': StatusCondition.POISONED,
        'poison': StatusCondition.POISONED,
        'asleep': StatusCondition.ASLEEP,
        'sleep': StatusCondition.ASLEEP,
        'paralyzed': StatusCondition.PARALYZED,
        'paralysis': StatusCondition.PARALYZED,
        'confused': StatusCondition.CONFUSED,
        'confusion': StatusCondition.CONFUSED,
    }
    
    for pattern, condition in status_patterns.items():
        if pattern in text_lower:
            return condition
    
    return None


def get_special_condition_check_bonus(pokemon_instance) -> int:
    """Get damage bonus for attacks that check for special conditions"""
    if not hasattr(pokemon_instance, 'status_conditions'):
        return 0
    
    # If Pokemon has any status condition, return the bonus
    if pokemon_instance.status_conditions:
        return 60  # Common bonus amount for "special condition" effects
    
    return 0