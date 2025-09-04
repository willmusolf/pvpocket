"""
Energy system for Pokemon TCG Pocket battle simulation

Handles energy types, attachment rules, and energy generation
"""

import logging
import random
from typing import Dict, List, Optional, Tuple
from enum import Enum


class EnergyType(Enum):
    """Supported energy types in Pokemon TCG Pocket"""
    FIRE = "Fire"
    WATER = "Water"
    GRASS = "Grass"
    LIGHTNING = "Lightning"
    PSYCHIC = "Psychic"
    FIGHTING = "Fighting"
    DARKNESS = "Darkness"
    METAL = "Metal"
    COLORLESS = "Colorless"


# Energy symbol mappings for parsing card data
ENERGY_SYMBOLS = {
    "R": EnergyType.FIRE,
    "W": EnergyType.WATER,
    "G": EnergyType.GRASS,
    "L": EnergyType.LIGHTNING,
    "P": EnergyType.PSYCHIC,
    "F": EnergyType.FIGHTING,
    "D": EnergyType.DARKNESS,
    "M": EnergyType.METAL,
    "C": EnergyType.COLORLESS
}

# Reverse mapping for display
ENERGY_TYPE_TO_SYMBOL = {v: k for k, v in ENERGY_SYMBOLS.items()}


class EnergyManager:
    """Manages energy generation and validation for battle simulation"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize energy manager
        
        Args:
            logger: Logger for energy events
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Energy configuration
        self.energy_per_turn = 1
        self.player_1_no_energy_turn_1 = True
        
        self.logger.debug("Initialized energy manager")
    
    def parse_energy_cost(self, cost_data: List[str]) -> List[EnergyType]:
        """
        Parse energy cost from card data
        
        Args:
            cost_data: List of energy symbols or names
            
        Returns:
            List of EnergyType enums
        """
        parsed_cost = []
        
        try:
            for energy in cost_data:
                if isinstance(energy, str):
                    # Try symbol first
                    if energy in ENERGY_SYMBOLS:
                        parsed_cost.append(ENERGY_SYMBOLS[energy])
                    else:
                        # Try full name
                        for energy_type in EnergyType:
                            if energy_type.value.lower() == energy.lower():
                                parsed_cost.append(energy_type)
                                break
                        else:
                            self.logger.warning(f"Unknown energy type: {energy}")
                            
        except Exception as e:
            self.logger.error(f"Failed to parse energy cost {cost_data}: {e}")
            
        return parsed_cost
    
    def generate_energy_for_turn(self, 
                                deck_types: List[str], 
                                rng: random.Random,
                                turn_number: int,
                                player_id: int) -> Optional[EnergyType]:
        """
        Generate energy for a player's turn
        
        Args:
            deck_types: List of energy types available in deck
            rng: Random number generator
            turn_number: Current turn number
            player_id: Player generating energy (0 or 1)
            
        Returns:
            Energy type generated, or None if no energy allowed
        """
        try:
            # Check if energy attachment is allowed
            if not self.can_attach_energy(turn_number, player_id):
                return None
                
            # No deck types means colorless only
            if not deck_types:
                return EnergyType.COLORLESS
                
            # Single type deck - always generate that type
            if len(deck_types) == 1:
                return self._string_to_energy_type(deck_types[0])
                
            # Multi-type deck - randomly select
            selected_type = rng.choice(deck_types)
            return self._string_to_energy_type(selected_type)
            
        except Exception as e:
            self.logger.error(f"Failed to generate energy: {e}")
            return EnergyType.COLORLESS
    
    def can_attach_energy(self, turn_number: int, player_id: int) -> bool:
        """
        Check if player can attach energy this turn
        
        Args:
            turn_number: Current turn number
            player_id: Player attempting to attach (0 or 1)
            
        Returns:
            True if energy attachment is allowed
        """
        # Player 1 (id=0) cannot attach energy on turn 1
        if self.player_1_no_energy_turn_1 and player_id == 0 and turn_number == 1:
            return False
            
        return True
    
    def validate_energy_cost(self, 
                           required_cost: List[str], 
                           available_energy: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate if available energy can pay for required cost
        
        Args:
            required_cost: List of required energy symbols/types
            available_energy: List of available energy on Pokemon
            
        Returns:
            (can_pay, remaining_energy) tuple
        """
        try:
            # Convert to working lists
            required = required_cost.copy()
            available = available_energy.copy()
            
            # Zero cost is always payable
            if not required:
                return True, available
                
            # Check each required energy
            for needed_energy in required:
                paid = False
                
                if needed_energy == "C" or needed_energy == "Colorless":
                    # Colorless can be paid by any energy
                    if available:
                        available.pop(0)  # Remove any energy
                        paid = True
                else:
                    # Specific energy type required
                    if needed_energy in available:
                        available.remove(needed_energy)
                        paid = True
                    elif available:
                        # Can substitute any energy for specific type
                        available.pop(0)
                        paid = True
                        
                if not paid:
                    return False, available_energy  # Cannot pay cost
                    
            return True, available
            
        except Exception as e:
            self.logger.error(f"Energy validation failed: {e}")
            return False, available_energy
    
    def get_energy_type_priority(self, energy_type: EnergyType) -> int:
        """
        Get priority order for energy types (for AI decision making)
        
        Args:
            energy_type: Energy type to get priority for
            
        Returns:
            Priority value (lower = higher priority)
        """
        priority_map = {
            EnergyType.FIRE: 1,
            EnergyType.WATER: 2,
            EnergyType.GRASS: 3,
            EnergyType.LIGHTNING: 4,
            EnergyType.PSYCHIC: 5,
            EnergyType.FIGHTING: 6,
            EnergyType.DARKNESS: 7,
            EnergyType.METAL: 8,
            EnergyType.COLORLESS: 9
        }
        return priority_map.get(energy_type, 10)
    
    def calculate_energy_efficiency(self, 
                                  pokemon_energy: List[str], 
                                  available_attacks: List[Dict]) -> Dict[str, float]:
        """
        Calculate energy efficiency for available attacks
        
        Args:
            pokemon_energy: Energy attached to Pokemon
            available_attacks: List of possible attacks
            
        Returns:
            Dictionary mapping attack names to efficiency scores
        """
        efficiency_scores = {}
        
        try:
            for attack in available_attacks:
                attack_name = attack.get("name", "Unknown")
                cost = attack.get("cost", [])
                damage = attack.get("damage", "0")
                
                # Parse damage value
                try:
                    import re
                    numbers = re.findall(r'\d+', str(damage))
                    damage_value = int(numbers[0]) if numbers else 0
                except:
                    damage_value = 0
                    
                # Calculate efficiency (damage per energy)
                cost_count = len(cost) if cost else 1  # Avoid division by zero
                efficiency = damage_value / cost_count if cost_count > 0 else damage_value
                
                efficiency_scores[attack_name] = efficiency
                
        except Exception as e:
            self.logger.error(f"Energy efficiency calculation failed: {e}")
            
        return efficiency_scores
    
    def suggest_energy_attachment(self, 
                                deck_types: List[str],
                                pokemon_energy: List[str],
                                available_attacks: List[Dict],
                                rng: random.Random) -> Optional[EnergyType]:
        """
        Suggest best energy type to attach for AI decision making
        
        Args:
            deck_types: Available energy types in deck
            pokemon_energy: Current energy on Pokemon
            available_attacks: Attacks Pokemon can learn
            rng: Random number generator for tie breaking
            
        Returns:
            Suggested energy type to attach
        """
        try:
            if not deck_types:
                return EnergyType.COLORLESS
                
            # Simple strategy: prefer energy types that enable new attacks
            energy_scores = {}
            
            for deck_type in deck_types:
                energy_type = self._string_to_energy_type(deck_type)
                score = 0
                
                # Simulate attaching this energy
                test_energy = pokemon_energy + [deck_type]
                
                # Check how many attacks this would enable
                for attack in available_attacks:
                    cost = attack.get("cost", [])
                    can_pay, _ = self.validate_energy_cost(cost, test_energy)
                    if can_pay:
                        # Weight by attack damage
                        try:
                            import re
                            damage_str = attack.get("damage", "0")
                            numbers = re.findall(r'\d+', str(damage_str))
                            damage = int(numbers[0]) if numbers else 0
                            score += damage
                        except:
                            score += 10  # Default score for enabling attack
                            
                energy_scores[energy_type] = score
                
            # Select energy type with highest score
            if energy_scores:
                best_energy = max(energy_scores.items(), key=lambda x: x[1])[0]
                return best_energy
            else:
                # Fallback to random selection
                deck_type = rng.choice(deck_types)
                return self._string_to_energy_type(deck_type)
                
        except Exception as e:
            self.logger.error(f"Energy suggestion failed: {e}")
            return EnergyType.COLORLESS
    
    def get_weakness_matchups(self) -> Dict[EnergyType, EnergyType]:
        """
        Get weakness relationships between energy types
        
        Returns:
            Dictionary mapping attacking type to weak defending type
        """
        # Standard Pokemon TCG weakness relationships
        weakness_chart = {
            EnergyType.FIRE: EnergyType.GRASS,
            EnergyType.WATER: EnergyType.FIRE,
            EnergyType.GRASS: EnergyType.WATER,
            EnergyType.LIGHTNING: EnergyType.WATER,
            EnergyType.PSYCHIC: EnergyType.FIGHTING,
            EnergyType.FIGHTING: EnergyType.PSYCHIC,
            EnergyType.DARKNESS: EnergyType.PSYCHIC,
            EnergyType.METAL: EnergyType.FIRE
        }
        return weakness_chart
    
    def _string_to_energy_type(self, energy_string: str) -> EnergyType:
        """Convert string to EnergyType enum"""
        # Try direct match first
        for energy_type in EnergyType:
            if energy_type.value.lower() == energy_string.lower():
                return energy_type
                
        # Try symbol match
        if energy_string in ENERGY_SYMBOLS:
            return ENERGY_SYMBOLS[energy_string]
            
        # Default to colorless
        self.logger.warning(f"Unknown energy string: {energy_string}, defaulting to Colorless")
        return EnergyType.COLORLESS
    
    def energy_type_to_string(self, energy_type: EnergyType) -> str:
        """Convert EnergyType enum to string"""
        return energy_type.value
    
    def energy_type_to_symbol(self, energy_type: EnergyType) -> str:
        """Convert EnergyType enum to symbol"""
        return ENERGY_TYPE_TO_SYMBOL.get(energy_type, "C")
    
    def get_all_energy_types(self) -> List[EnergyType]:
        """Get list of all supported energy types"""
        return list(EnergyType)
    
    def get_basic_energy_types(self) -> List[EnergyType]:
        """Get list of basic (non-colorless) energy types"""
        return [e for e in EnergyType if e != EnergyType.COLORLESS]
    
    def is_basic_energy(self, energy_type: EnergyType) -> bool:
        """Check if energy type is basic (not colorless)"""
        return energy_type != EnergyType.COLORLESS
    
    def format_energy_cost(self, cost: List[str]) -> str:
        """
        Format energy cost for display
        
        Args:
            cost: List of energy requirements
            
        Returns:
            Formatted string representation
        """
        if not cost:
            return "Free"
            
        # Count each energy type
        energy_counts = {}
        for energy in cost:
            energy_counts[energy] = energy_counts.get(energy, 0) + 1
            
        # Format as "2R 1W C" etc.
        formatted_parts = []
        for energy_type, count in energy_counts.items():
            if count == 1:
                formatted_parts.append(energy_type)
            else:
                formatted_parts.append(f"{count}{energy_type}")
                
        return " ".join(formatted_parts)
    
    def to_dict(self) -> Dict[str, any]:
        """Convert energy manager state to dictionary"""
        return {
            "energy_per_turn": self.energy_per_turn,
            "player_1_no_energy_turn_1": self.player_1_no_energy_turn_1,
            "supported_types": [e.value for e in EnergyType],
            "weakness_chart": {k.value: v.value for k, v in self.get_weakness_matchups().items()}
        }