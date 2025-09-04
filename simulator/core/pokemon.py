"""
Pokemon battle mechanics for Pokemon TCG Pocket battle simulation

Handles individual Pokemon state, damage, energy attachment, and attacks
"""

import logging
from typing import Dict, List, Optional, Any

# Import existing models
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from Card import Card


class BattlePokemon:
    """Represents a Pokemon in battle with current state"""
    
    def __init__(self, card: Card, logger: Optional[logging.Logger] = None):
        """
        Initialize a Pokemon for battle
        
        Args:
            card: The Card object representing this Pokemon
            logger: Logger for battle events
        """
        # Ensure card has required Pokemon properties
        if not hasattr(card, 'is_pokemon') or not card.is_pokemon:
            # Try to determine if it's a Pokemon from card_type
            if hasattr(card, 'card_type') and 'Pokémon' in card.card_type:
                card.is_pokemon = True
            else:
                raise ValueError(f"Card {card.name} is not a Pokemon")
        
        # Ensure basic Pokemon status
        if not hasattr(card, 'is_basic'):
            if hasattr(card, 'card_type') and 'Basic' in card.card_type:
                card.is_basic = True
            else:
                card.is_basic = False
            
        self.card = card
        self.logger = logger or logging.getLogger(__name__)
        
        # Battle state - handle missing HP gracefully
        hp_value = getattr(card, 'hp', 0)
        if hp_value is None:
            hp_value = 50  # Default HP if not specified
        
        self.current_hp = hp_value
        self.max_hp = hp_value
        self.energy_attached: List[str] = []
        
        # Status effects (for future expansion)
        self.status_effects: List[str] = []
        self.is_asleep = False
        self.is_poisoned = False
        self.is_paralyzed = False
        self.is_confused = False
        
        # Battle history
        self.damage_taken = 0
        self.attacks_used = 0
        
        self.logger.debug(f"Created battle Pokemon: {card.name} with {self.max_hp} HP")
    
    def is_knocked_out(self) -> bool:
        """Check if this Pokemon is knocked out"""
        return self.current_hp <= 0
    
    def is_ex_pokemon(self) -> bool:
        """Check if this is an EX Pokemon (worth 2 prize points)"""
        return "ex" in self.card.name.lower() or getattr(self.card, 'is_ex', False)
    
    def take_damage(self, damage: int) -> int:
        """
        Apply damage to this Pokemon
        
        Args:
            damage: Amount of damage to apply
            
        Returns:
            Actual damage taken (may be less than requested)
        """
        if damage <= 0:
            return 0
            
        actual_damage = min(damage, self.current_hp)
        self.current_hp -= actual_damage
        self.damage_taken += actual_damage
        
        self.logger.info(f"{self.card.name} took {actual_damage} damage, {self.current_hp} HP remaining")
        
        if self.is_knocked_out():
            self.logger.info(f"{self.card.name} was knocked out after taking {actual_damage} damage!")
            
        return actual_damage
    
    def heal(self, amount: int) -> int:
        """
        Heal this Pokemon
        
        Args:
            amount: Amount of HP to restore
            
        Returns:
            Actual HP healed
        """
        if amount <= 0:
            return 0
            
        old_hp = self.current_hp
        self.current_hp = min(self.current_hp + amount, self.max_hp)
        healed = self.current_hp - old_hp
        
        self.logger.debug(f"{self.card.name} healed {healed} HP, now at {self.current_hp} HP")
        return healed
    
    def attach_energy(self, energy_type: str) -> bool:
        """
        Attach energy to this Pokemon
        
        Args:
            energy_type: Type of energy to attach
            
        Returns:
            True if energy attached successfully
        """
        try:
            # Prevent attaching "Colorless" energy - it's not a real energy type
            if energy_type == "Colorless":
                self.logger.error(f"Cannot attach Colorless energy - it's not a valid energy type!")
                return False
                
            # Valid energy types only
            valid_energy_types = ['Fire', 'Water', 'Grass', 'Lightning', 'Psychic', 'Fighting', 'Darkness', 'Metal']
            if energy_type not in valid_energy_types:
                self.logger.warning(f"Unknown energy type: {energy_type}. Allowing attachment but this may cause issues.")
                
            self.energy_attached.append(energy_type)
            self.logger.debug(f"Attached {energy_type} energy to {self.card.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to attach energy to {self.card.name}: {e}")
            return False
    
    def remove_energy(self, energy_type: Optional[str] = None) -> Optional[str]:
        """
        Remove energy from this Pokemon
        
        Args:
            energy_type: Specific energy type to remove (None for any)
            
        Returns:
            Type of energy removed, or None if no energy removed
        """
        if not self.energy_attached:
            return None
            
        if energy_type and energy_type in self.energy_attached:
            self.energy_attached.remove(energy_type)
            self.logger.debug(f"Removed {energy_type} energy from {self.card.name}")
            return energy_type
        elif not energy_type:
            # Remove any energy
            removed = self.energy_attached.pop()
            self.logger.debug(f"Removed {removed} energy from {self.card.name}")
            return removed
            
        return None
    
    def get_energy_count(self, energy_type: Optional[str] = None) -> int:
        """
        Get count of energy attached
        
        Args:
            energy_type: Specific type to count (None for total)
            
        Returns:
            Number of energy of specified type
        """
        if energy_type is None:
            return len(self.energy_attached)
        else:
            return self.energy_attached.count(energy_type)
    
    def can_use_attack(self, attack: Dict[str, Any]) -> bool:
        """
        Check if this Pokemon can use the specified attack
        
        Args:
            attack: Attack dictionary from card data
            
        Returns:
            True if attack can be used
        """
        try:
            if self.is_knocked_out():
                return False
                
            # Get energy cost for attack
            energy_cost = attack.get("cost", [])
            
            # Zero-cost attacks are always usable (empty cost list)
            if not energy_cost:
                return True
                
            # Check if we have enough energy
            energy_available = self.energy_attached.copy()
            
            for required_energy in energy_cost:
                if required_energy == "C" or required_energy == "Colorless":  # Colorless energy - requires ANY energy
                    if energy_available:
                        energy_available.pop()  # Remove any energy to pay for colorless
                    else:
                        return False  # No energy available to pay for colorless
                else:
                    # Need specific energy type - must be exact match
                    if required_energy in energy_available:
                        energy_available.remove(required_energy)
                    else:
                        return False  # Specific energy type not available
                            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to check attack usability for {self.card.name}: {e}")
            return False
    
    def get_usable_attacks(self) -> List[Dict[str, Any]]:
        """
        Get list of attacks this Pokemon can currently use
        
        Returns:
            List of attack dictionaries
        """
        usable_attacks = []
        
        for attack in self.card.attacks:
            if self.can_use_attack(attack):
                usable_attacks.append(attack)
                
        return usable_attacks
    
    def use_attack(self, attack: Dict[str, Any]) -> bool:
        """
        Use an attack (for tracking purposes)
        
        Args:
            attack: Attack being used
            
        Returns:
            True if attack can be used
        """
        if not self.can_use_attack(attack):
            return False
            
        self.attacks_used += 1
        self.logger.debug(f"{self.card.name} used attack: {attack.get('name', 'Unknown')}")
        return True
    
    def calculate_attack_damage(self, attack: Dict[str, Any], target: 'BattlePokemon', weakness_bonus: int = 20) -> int:
        """
        Calculate damage this attack would deal to target
        
        Args:
            attack: Attack being used
            target: Target Pokemon
            weakness_bonus: Bonus damage for weakness
            
        Returns:
            Total damage that would be dealt
        """
        try:
            # Get base damage
            damage_str = attack.get("damage", "0")
            
            # Parse damage value (handle "30+", "×" symbols, etc.)
            base_damage = 0
            if damage_str and damage_str != "0":
                # Extract numeric part
                import re
                numbers = re.findall(r'\d+', str(damage_str))
                if numbers:
                    base_damage = int(numbers[0])
            
            # Apply weakness
            weakness_damage = 0
            if (target.card.weakness and 
                self.card.energy_type and 
                self.card.energy_type == target.card.weakness):
                weakness_damage = weakness_bonus
                
            total_damage = base_damage + weakness_damage
            
            self.logger.debug(f"Attack damage calculation: {base_damage} base + {weakness_damage} weakness = {total_damage}")
            return total_damage
            
        except Exception as e:
            self.logger.error(f"Damage calculation failed: {e}")
            return 0
    
    def get_retreat_cost(self) -> int:
        """Get the energy cost to retreat this Pokemon"""
        return self.card.retreat_cost or 0
    
    def can_retreat(self) -> bool:
        """Check if this Pokemon can retreat (has enough energy and no blocking status)"""
        # Check energy requirements
        retreat_cost = self.get_retreat_cost()
        if len(self.energy_attached) < retreat_cost:
            return False
        
        # Check status conditions that block retreat
        if hasattr(self, 'status_conditions'):
            for status_effect in self.status_conditions:
                if hasattr(status_effect, 'condition'):
                    # Sleep and paralysis block retreat
                    if status_effect.condition.value in ['asleep', 'paralyzed']:
                        return False
        
        return True
    
    def apply_status_effect(self, effect: str) -> bool:
        """
        Apply a status effect to this Pokemon
        
        Args:
            effect: Status effect name
            
        Returns:
            True if effect applied
        """
        if effect not in self.status_effects:
            self.status_effects.append(effect)
            
            # Set specific status flags
            if effect == "asleep":
                self.is_asleep = True
            elif effect == "poisoned":
                self.is_poisoned = True
            elif effect == "paralyzed":
                self.is_paralyzed = True
            elif effect == "confused":
                self.is_confused = True
                
            self.logger.debug(f"{self.card.name} affected by {effect}")
            return True
            
        return False
    
    def remove_status_effect(self, effect: str) -> bool:
        """
        Remove a status effect from this Pokemon
        
        Args:
            effect: Status effect to remove
            
        Returns:
            True if effect removed
        """
        if effect in self.status_effects:
            self.status_effects.remove(effect)
            
            # Clear specific status flags
            if effect == "asleep":
                self.is_asleep = False
            elif effect == "poisoned":
                self.is_poisoned = False
            elif effect == "paralyzed":
                self.is_paralyzed = False
            elif effect == "confused":
                self.is_confused = False
                
            self.logger.debug(f"{self.card.name} recovered from {effect}")
            return True
            
        return False
    
    def clear_all_status_effects(self):
        """Remove all status effects"""
        self.status_effects.clear()
        self.is_asleep = False
        self.is_poisoned = False
        self.is_paralyzed = False
        self.is_confused = False
        self.logger.debug(f"{self.card.name} cleared all status effects")
    
    def is_affected_by_status(self) -> bool:
        """Check if Pokemon has any status effects"""
        return len(self.status_effects) > 0
    
    def get_hp_percentage(self) -> float:
        """Get current HP as percentage of max HP"""
        if self.max_hp <= 0:
            return 0.0
        return (self.current_hp / self.max_hp) * 100.0
    
    def reset_to_full_hp(self):
        """Reset Pokemon to full HP (for testing)"""
        self.current_hp = self.max_hp
        self.damage_taken = 0
        self.clear_all_status_effects()
        self.logger.debug(f"{self.card.name} reset to full HP")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Pokemon state to dictionary for logging"""
        return {
            "card_id": self.card.id,
            "card_name": self.card.name,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "energy_attached": self.energy_attached,
            "status_effects": self.status_effects,
            "is_knocked_out": self.is_knocked_out(),
            "is_ex": self.is_ex_pokemon(),
            "damage_taken": self.damage_taken,
            "attacks_used": self.attacks_used,
            "usable_attacks": [attack.get("name") for attack in self.get_usable_attacks()]
        }
    
    def __str__(self) -> str:
        status = ""
        if self.status_effects:
            status = f" ({', '.join(self.status_effects)})"
            
        energy_str = ""
        if self.energy_attached:
            energy_counts = {}
            for energy in self.energy_attached:
                energy_counts[energy] = energy_counts.get(energy, 0) + 1
            energy_str = f" [{', '.join(f'{count}x{type}' for type, count in energy_counts.items())}]"
            
        return f"{self.card.name}: {self.current_hp}/{self.max_hp} HP{energy_str}{status}"
    
    def __repr__(self) -> str:
        return f"BattlePokemon(card={self.card.name}, hp={self.current_hp}/{self.max_hp}, energy={len(self.energy_attached)})"