"""
Stadium Card System for Pokemon TCG Pocket Battle Simulator

Handles Stadium cards that provide field-wide continuous effects that persist
until replaced by another Stadium card or removed by specific effects.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Import core components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class StadiumEffectType(Enum):
    """Types of Stadium effects"""
    DAMAGE_MODIFICATION = "damage_mod"      # Modify attack damage
    ENERGY_MODIFICATION = "energy_mod"      # Modify energy costs/generation
    STATUS_MODIFICATION = "status_mod"      # Affect status conditions
    DRAW_MODIFICATION = "draw_mod"          # Modify card draw
    HEALING_MODIFICATION = "healing_mod"    # Modify healing effects
    POKEMON_STAT_MOD = "stat_mod"          # Modify Pokemon stats (HP, retreat cost)
    TURN_STRUCTURE_MOD = "turn_mod"        # Modify turn structure/limitations
    SPECIAL_RULE = "special"               # Unique stadium rules


@dataclass
class StadiumEffect:
    """Represents a single Stadium card effect"""
    effect_type: StadiumEffectType
    target: str  # "all", "player", "opponent", "pokemon_type", etc.
    parameters: Dict[str, Any]
    condition: Optional[str] = None  # Condition for effect to apply
    description: str = ""


@dataclass
class ActiveStadium:
    """Represents the currently active Stadium card"""
    card_id: str
    card_name: str
    played_by_player: int  # Which player played this Stadium
    turn_played: int
    effects: List[StadiumEffect]
    
    # State tracking
    effect_counters: Dict[str, int] = None  # For effects with limited uses
    
    def __post_init__(self):
        if self.effect_counters is None:
            self.effect_counters = {}


class StadiumManager:
    """Manages Stadium card effects and field-wide modifications"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Current active Stadium
        self.active_stadium: Optional[ActiveStadium] = None
        
        # Effect modification tracking
        self.persistent_effects: List[Dict[str, Any]] = []
        
        # Stadium effect registry (built-in Stadium cards)
        self.stadium_registry = self._build_stadium_registry()
        
        self.logger.debug("Stadium Manager initialized")
    
    def _build_stadium_registry(self) -> Dict[str, List[StadiumEffect]]:
        """Build registry of known Stadium card effects"""
        registry = {}
        
        # Power Plant - Increases Electric-type attack damage
        registry["Power Plant"] = [
            StadiumEffect(
                effect_type=StadiumEffectType.DAMAGE_MODIFICATION,
                target="electric_pokemon",
                parameters={"damage_bonus": 10, "energy_type": "Lightning"},
                description="Electric-type Pokemon attacks do +10 damage"
            )
        ]
        
        # Pokemon Center - Heal all Pokemon between turns
        registry["Pokemon Center"] = [
            StadiumEffect(
                effect_type=StadiumEffectType.HEALING_MODIFICATION,
                target="all_pokemon",
                parameters={"heal_amount": 20, "timing": "between_turns"},
                description="Heal 20 damage from all Pokemon between turns"
            )
        ]
        
        # Viridian Forest - Extra energy attachment
        registry["Viridian Forest"] = [
            StadiumEffect(
                effect_type=StadiumEffectType.ENERGY_MODIFICATION,
                target="all_players",
                parameters={"extra_energy_per_turn": 1},
                condition="once_per_turn",
                description="Each player may attach 1 additional energy per turn"
            )
        ]
        
        # Old Cemetery - Discard pile manipulation
        registry["Old Cemetery"] = [
            StadiumEffect(
                effect_type=StadiumEffectType.SPECIAL_RULE,
                target="all_players", 
                parameters={"discard_benefit": True},
                description="Players may return Pokemon from discard pile to hand"
            )
        ]
        
        # Fighting Dojo - Reduce Fighting Pokemon retreat costs
        registry["Fighting Dojo"] = [
            StadiumEffect(
                effect_type=StadiumEffectType.POKEMON_STAT_MOD,
                target="fighting_pokemon",
                parameters={"retreat_cost_reduction": 1, "energy_type": "Fighting"},
                description="Fighting-type Pokemon have -1 retreat cost"
            )
        ]
        
        # Trainer School - Extra card draw
        registry["Trainer School"] = [
            StadiumEffect(
                effect_type=StadiumEffectType.DRAW_MODIFICATION,
                target="all_players",
                parameters={"extra_cards": 1},
                condition="once_per_turn",
                description="Each player may draw 1 extra card per turn"
            )
        ]
        
        # Rough Seas - Water/Lightning status immunity
        registry["Rough Seas"] = [
            StadiumEffect(
                effect_type=StadiumEffectType.STATUS_MODIFICATION,
                target="water_lightning_pokemon",
                parameters={"status_immunity": ["burn", "poison"], "energy_types": ["Water", "Lightning"]},
                description="Water and Lightning Pokemon can't be burned or poisoned"
            )
        ]
        
        return registry
    
    def play_stadium_card(self, card, player_id: int, turn_number: int) -> Tuple[bool, str]:
        """
        Play a Stadium card, replacing any existing Stadium
        
        Args:
            card: Stadium card being played
            player_id: Player playing the Stadium
            turn_number: Current turn number
            
        Returns:
            (success, message)
        """
        try:
            # Check if card is a Stadium
            if not self._is_stadium_card(card):
                return False, f"{card.name} is not a Stadium card"
            
            # Get Stadium effects
            effects = self._parse_stadium_effects(card)
            if not effects:
                self.logger.warning(f"Stadium {card.name} has no recognized effects")
            
            # Replace existing Stadium if present
            old_stadium = None
            if self.active_stadium:
                old_stadium = self.active_stadium
                self._deactivate_stadium()
            
            # Activate new Stadium
            self.active_stadium = ActiveStadium(
                card_id=card.id,
                card_name=card.name,
                played_by_player=player_id,
                turn_played=turn_number,
                effects=effects
            )
            
            # Apply immediate effects
            self._apply_stadium_effects()
            
            message = f"Stadium {card.name} is now in play"
            if old_stadium:
                message += f" (replaced {old_stadium.card_name})"
            
            self.logger.info(f"Player {player_id} played Stadium: {card.name}")
            return True, message
            
        except Exception as e:
            self.logger.error(f"Failed to play Stadium {card.name}: {e}")
            return False, f"Stadium play failed: {e}"
    
    def _is_stadium_card(self, card) -> bool:
        """Check if a card is a Stadium card"""
        card_type = card.card_type.lower()
        return 'stadium' in card_type or card.name in self.stadium_registry
    
    def _parse_stadium_effects(self, card) -> List[StadiumEffect]:
        """Parse Stadium effects from card data"""
        # Check registry first
        if card.name in self.stadium_registry:
            return self.stadium_registry[card.name]
        
        # Parse from card abilities/text (simplified)
        effects = []
        
        for ability in card.abilities or []:
            effect_text = ability.get('effect_text', '').lower()
            parsed_effect = self._parse_stadium_text(effect_text, card.name)
            if parsed_effect:
                effects.append(parsed_effect)
        
        return effects
    
    def _parse_stadium_text(self, text: str, card_name: str) -> Optional[StadiumEffect]:
        """Parse Stadium effect from text (basic implementation)"""
        text_lower = text.lower()
        
        # Damage modification patterns
        if 'damage' in text_lower and ('+' in text_lower or 'bonus' in text_lower):
            import re
            damage_match = re.search(r'\+(\d+)\s*damage', text_lower)
            if damage_match:
                bonus = int(damage_match.group(1))
                return StadiumEffect(
                    effect_type=StadiumEffectType.DAMAGE_MODIFICATION,
                    target="all_pokemon",
                    parameters={"damage_bonus": bonus},
                    description=f"All attacks do +{bonus} damage"
                )
        
        # Healing patterns
        if 'heal' in text_lower:
            heal_match = re.search(r'heal\s*(\d+)', text_lower)
            if heal_match:
                heal_amount = int(heal_match.group(1))
                return StadiumEffect(
                    effect_type=StadiumEffectType.HEALING_MODIFICATION,
                    target="all_pokemon",
                    parameters={"heal_amount": heal_amount, "timing": "between_turns"},
                    description=f"Heal {heal_amount} damage between turns"
                )
        
        # Energy patterns
        if 'energy' in text_lower and 'attach' in text_lower:
            return StadiumEffect(
                effect_type=StadiumEffectType.ENERGY_MODIFICATION,
                target="all_players",
                parameters={"extra_energy_per_turn": 1},
                condition="once_per_turn",
                description="May attach 1 extra energy per turn"
            )
        
        # Status condition patterns
        if any(status in text_lower for status in ['burn', 'poison', 'paralyze', 'sleep']):
            return StadiumEffect(
                effect_type=StadiumEffectType.STATUS_MODIFICATION,
                target="all_pokemon",
                parameters={"status_protection": True},
                description="Modified status condition rules"
            )
        
        return None
    
    def _apply_stadium_effects(self):
        """Apply Stadium effects when Stadium becomes active"""
        if not self.active_stadium:
            return
        
        for effect in self.active_stadium.effects:
            # Most Stadium effects are continuous and don't need immediate application
            # They're checked when relevant game events occur
            self.logger.debug(f"Stadium effect active: {effect.description}")
    
    def _deactivate_stadium(self):
        """Deactivate current Stadium and remove its effects"""
        if not self.active_stadium:
            return
        
        old_name = self.active_stadium.card_name
        self.active_stadium = None
        
        # Clear any persistent modifications
        self.persistent_effects.clear()
        
        self.logger.debug(f"Stadium {old_name} deactivated")
    
    def modify_attack_damage(self, base_damage: int, attacking_pokemon, defending_pokemon, 
                           attack_data: Dict[str, Any]) -> int:
        """
        Apply Stadium damage modifications to an attack
        
        Args:
            base_damage: Base attack damage
            attacking_pokemon: Pokemon performing attack
            defending_pokemon: Pokemon receiving damage
            attack_data: Attack information
            
        Returns:
            Modified damage amount
        """
        if not self.active_stadium:
            return base_damage
        
        modified_damage = base_damage
        
        for effect in self.active_stadium.effects:
            if effect.effect_type != StadiumEffectType.DAMAGE_MODIFICATION:
                continue
            
            # Check if effect applies to this attack
            if self._effect_applies_to_pokemon(effect, attacking_pokemon):
                bonus = effect.parameters.get('damage_bonus', 0)
                modified_damage += bonus
                
                self.logger.debug(f"Stadium {self.active_stadium.card_name}: +{bonus} damage to {attacking_pokemon.card.name}'s attack")
        
        return modified_damage
    
    def modify_healing(self, base_healing: int, target_pokemon, healing_source: str) -> int:
        """
        Apply Stadium healing modifications
        
        Args:
            base_healing: Base healing amount
            target_pokemon: Pokemon being healed
            healing_source: Source of healing ("attack", "ability", "between_turns", etc.)
            
        Returns:
            Modified healing amount
        """
        if not self.active_stadium:
            return base_healing
        
        modified_healing = base_healing
        
        for effect in self.active_stadium.effects:
            if effect.effect_type != StadiumEffectType.HEALING_MODIFICATION:
                continue
            
            # Check timing
            timing = effect.parameters.get('timing', 'any')
            if timing != 'any' and timing != healing_source:
                continue
            
            # Check if effect applies
            if self._effect_applies_to_pokemon(effect, target_pokemon):
                heal_bonus = effect.parameters.get('heal_amount', 0)
                modified_healing += heal_bonus
                
                self.logger.debug(f"Stadium {self.active_stadium.card_name}: +{heal_bonus} healing to {target_pokemon.card.name}")
        
        return modified_healing
    
    def check_status_immunity(self, pokemon, status_condition: str) -> bool:
        """
        Check if Stadium provides immunity to a status condition
        
        Args:
            pokemon: Pokemon that would receive status condition
            status_condition: Status condition being applied ("burn", "poison", etc.)
            
        Returns:
            True if Pokemon is immune due to Stadium effect
        """
        if not self.active_stadium:
            return False
        
        for effect in self.active_stadium.effects:
            if effect.effect_type != StadiumEffectType.STATUS_MODIFICATION:
                continue
            
            if self._effect_applies_to_pokemon(effect, pokemon):
                immunities = effect.parameters.get('status_immunity', [])
                if status_condition in immunities:
                    self.logger.debug(f"Stadium {self.active_stadium.card_name}: {pokemon.card.name} immune to {status_condition}")
                    return True
        
        return False
    
    def modify_retreat_cost(self, base_cost: int, pokemon) -> int:
        """
        Apply Stadium retreat cost modifications
        
        Args:
            base_cost: Base retreat cost
            pokemon: Pokemon attempting to retreat
            
        Returns:
            Modified retreat cost
        """
        if not self.active_stadium:
            return base_cost
        
        modified_cost = base_cost
        
        for effect in self.active_stadium.effects:
            if effect.effect_type != StadiumEffectType.POKEMON_STAT_MOD:
                continue
            
            if self._effect_applies_to_pokemon(effect, pokemon):
                cost_reduction = effect.parameters.get('retreat_cost_reduction', 0)
                modified_cost = max(0, modified_cost - cost_reduction)
                
                self.logger.debug(f"Stadium {self.active_stadium.card_name}: -{cost_reduction} retreat cost for {pokemon.card.name}")
        
        return modified_cost
    
    def can_attach_extra_energy(self, player_id: int) -> bool:
        """
        Check if Stadium allows extra energy attachment this turn
        
        Args:
            player_id: Player attempting extra energy attachment
            
        Returns:
            True if extra energy attachment is allowed
        """
        if not self.active_stadium:
            return False
        
        for effect in self.active_stadium.effects:
            if effect.effect_type != StadiumEffectType.ENERGY_MODIFICATION:
                continue
            
            if effect.target in ["all_players", f"player_{player_id}"]:
                extra_energy = effect.parameters.get('extra_energy_per_turn', 0)
                if extra_energy > 0:
                    # Check if already used this turn (simplified)
                    effect_key = f"extra_energy_p{player_id}"
                    if effect_key not in self.active_stadium.effect_counters:
                        self.active_stadium.effect_counters[effect_key] = 0
                    
                    if self.active_stadium.effect_counters[effect_key] < extra_energy:
                        return True
        
        return False
    
    def use_extra_energy(self, player_id: int) -> bool:
        """
        Mark that player used extra energy attachment this turn
        
        Args:
            player_id: Player using extra energy
            
        Returns:
            True if successfully marked
        """
        if not self.active_stadium:
            return False
        
        for effect in self.active_stadium.effects:
            if effect.effect_type == StadiumEffectType.ENERGY_MODIFICATION:
                effect_key = f"extra_energy_p{player_id}"
                if effect_key not in self.active_stadium.effect_counters:
                    self.active_stadium.effect_counters[effect_key] = 0
                
                self.active_stadium.effect_counters[effect_key] += 1
                return True
        
        return False
    
    def reset_turn_counters(self, turn_number: int):
        """Reset per-turn effect counters"""
        if self.active_stadium:
            # Reset counters that are per-turn
            keys_to_reset = []
            for key in self.active_stadium.effect_counters:
                if 'per_turn' in key or 'extra_energy' in key:
                    keys_to_reset.append(key)
            
            for key in keys_to_reset:
                self.active_stadium.effect_counters[key] = 0
    
    def process_between_turns_effects(self, all_pokemon: List) -> List[str]:
        """
        Process Stadium effects that occur between turns
        
        Args:
            all_pokemon: List of all Pokemon in play
            
        Returns:
            List of effect descriptions that occurred
        """
        effects_applied = []
        
        if not self.active_stadium:
            return effects_applied
        
        for effect in self.active_stadium.effects:
            if effect.effect_type == StadiumEffectType.HEALING_MODIFICATION:
                timing = effect.parameters.get('timing', 'any')
                if timing == 'between_turns':
                    heal_amount = effect.parameters.get('heal_amount', 0)
                    
                    for pokemon in all_pokemon:
                        if pokemon and not pokemon.is_knocked_out():
                            if self._effect_applies_to_pokemon(effect, pokemon):
                                actual_healed = pokemon.heal(heal_amount)
                                if actual_healed > 0:
                                    effects_applied.append(
                                        f"Stadium {self.active_stadium.card_name}: {pokemon.card.name} healed {actual_healed} HP"
                                    )
        
        return effects_applied
    
    def _effect_applies_to_pokemon(self, effect: StadiumEffect, pokemon) -> bool:
        """Check if a Stadium effect applies to a specific Pokemon"""
        target = effect.target
        
        if target == "all_pokemon" or target == "all":
            return True
        
        # Energy type targeting
        if "pokemon" in target and hasattr(pokemon, 'card'):
            pokemon_type = pokemon.card.energy_type
            
            if target == "electric_pokemon" and pokemon_type == "Lightning":
                return True
            elif target == "fighting_pokemon" and pokemon_type == "Fighting":
                return True
            elif target == "water_lightning_pokemon" and pokemon_type in ["Water", "Lightning"]:
                return True
            
            # Check for specific energy type in effect parameters
            effect_energy_type = effect.parameters.get('energy_type')
            if effect_energy_type and pokemon_type == effect_energy_type:
                return True
            
            # Check for multiple energy types
            effect_energy_types = effect.parameters.get('energy_types', [])
            if effect_energy_types and pokemon_type in effect_energy_types:
                return True
        
        return False
    
    def get_active_stadium_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently active Stadium"""
        if not self.active_stadium:
            return None
        
        return {
            "name": self.active_stadium.card_name,
            "played_by": self.active_stadium.played_by_player,
            "turn_played": self.active_stadium.turn_played,
            "effects": [
                {
                    "type": effect.effect_type.value,
                    "target": effect.target,
                    "description": effect.description,
                    "parameters": effect.parameters
                }
                for effect in self.active_stadium.effects
            ]
        }
    
    def has_active_stadium(self) -> bool:
        """Check if there's an active Stadium"""
        return self.active_stadium is not None
    
    def get_stadium_name(self) -> Optional[str]:
        """Get name of active Stadium"""
        return self.active_stadium.card_name if self.active_stadium else None
    
    def __str__(self) -> str:
        if self.active_stadium:
            return f"StadiumManager(active: {self.active_stadium.card_name})"
        else:
            return "StadiumManager(no active stadium)"