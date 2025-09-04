"""
Trainer Card System for Pokemon TCG Pocket Battle Simulator
Handles Supporter, Item, and Tool cards based on the real database analysis.
"""

from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
import logging
from dataclasses import dataclass

# Import card bridge for BattleCard
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from simulator.core.card_bridge import BattleCard


class TrainerType(Enum):
    """Types of trainer cards found in the database"""
    SUPPORTER = "supporter"
    ITEM = "item" 
    TOOL = "tool"


@dataclass
class TrainerEffect:
    """Represents a trainer card effect"""
    effect_type: str
    target: str  # "self", "opponent", "both", "field"
    parameters: Dict
    description: str


class TrainerCardManager:
    """Manages trainer card rules and effects"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Track trainer usage per turn (for Supporter limit)
        self.supporters_played_this_turn = []
        self.current_turn = 0
        
        # Trainer card rules based on database analysis
        self.trainer_rules = {
            TrainerType.SUPPORTER: {
                'max_per_turn': 1,  # Traditional TCG rule - confirm with user
                'description': 'Powerful effects, limited to 1 per turn'
            },
            TrainerType.ITEM: {
                'max_per_turn': None,  # Unlimited - confirm with user
                'description': 'Utility effects, can play multiple per turn'
            },
            TrainerType.TOOL: {
                'max_per_turn': None,  # Unlimited attachment - confirm with user  
                'description': 'Attached to Pokemon as equipment'
            }
        }
    
    def get_trainer_type(self, card: BattleCard) -> Optional[TrainerType]:
        """Determine trainer type from card type string"""
        card_type_lower = card.card_type.lower()
        
        if 'supporter' in card_type_lower:
            return TrainerType.SUPPORTER
        elif 'item' in card_type_lower:
            return TrainerType.ITEM
        elif 'tool' in card_type_lower:
            return TrainerType.TOOL
        
        return None
    
    def is_trainer_card(self, card: BattleCard) -> bool:
        """Check if card is a trainer card"""
        return 'trainer' in card.card_type.lower()
    
    def can_play_trainer(self, card: BattleCard, current_turn: int) -> Tuple[bool, str]:
        """Check if trainer card can be played this turn"""
        if not self.is_trainer_card(card):
            return False, "Not a trainer card"
        
        trainer_type = self.get_trainer_type(card)
        if not trainer_type:
            return False, "Unknown trainer type"
        
        # Update current turn if changed
        if current_turn != self.current_turn:
            self.current_turn = current_turn
            self.supporters_played_this_turn = []
        
        # Check Supporter limit
        if trainer_type == TrainerType.SUPPORTER:
            max_supporters = self.trainer_rules[TrainerType.SUPPORTER]['max_per_turn']
            if len(self.supporters_played_this_turn) >= max_supporters:
                return False, f"Already played {max_supporters} Supporter this turn"
        
        return True, f"Can play {trainer_type.value}"
    
    def play_trainer_card(self, card: BattleCard, current_turn: int) -> Tuple[bool, str, List[Dict]]:
        """Play a trainer card and return its effects"""
        can_play, reason = self.can_play_trainer(card, current_turn)
        if not can_play:
            return False, reason, []
        
        trainer_type = self.get_trainer_type(card)
        
        # Track Supporter usage
        if trainer_type == TrainerType.SUPPORTER:
            self.supporters_played_this_turn.append(card.name)
        
        # Parse and execute trainer effects
        effects = self._parse_trainer_effects(card)
        
        self.logger.info(f"Played {trainer_type.value} card: {card.name}")
        return True, f"Successfully played {card.name}", effects
    
    def _parse_trainer_effects(self, card: BattleCard) -> List[Dict]:
        """Parse trainer card effects from abilities"""
        effects = []
        
        for ability in card.abilities or []:
            effect_text = ability.get('effect_text', '')
            if not effect_text:
                continue
            
            # Parse common trainer effects
            parsed_effects = self._parse_trainer_effect_text(effect_text)
            effects.extend(parsed_effects)
        
        return effects
    
    def _parse_trainer_effect_text(self, effect_text: str) -> List[Dict]:
        """Parse specific trainer effect patterns"""
        effects = []
        text_lower = effect_text.lower()
        
        # Common trainer effect patterns (based on typical TCG effects)
        import re
        
        # Draw cards
        draw_pattern = r'draw (\d+) cards?'
        draw_match = re.search(draw_pattern, text_lower)
        if draw_match:
            effects.append({
                'type': 'draw_cards',
                'amount': int(draw_match.group(1)),
                'target': 'self'
            })
        
        # Search deck
        search_pattern = r'search.*?deck.*?(\d+).*?card'
        search_match = re.search(search_pattern, text_lower)
        if search_match:
            effects.append({
                'type': 'search_deck',
                'amount': int(search_match.group(1)),
                'target': 'self'
            })
        
        # Heal Pokemon
        heal_pattern = r'heal (\d+) damage'
        heal_match = re.search(heal_pattern, text_lower)
        if heal_match:
            effects.append({
                'type': 'heal_damage',
                'amount': int(heal_match.group(1)),
                'target': 'pokemon'
            })
        
        # Switch Pokemon
        if 'switch' in text_lower and 'pokemon' in text_lower:
            effects.append({
                'type': 'switch_pokemon',
                'target': 'self'
            })
        
        # Discard cards
        discard_pattern = r'discard (\d+) cards?'
        discard_match = re.search(discard_pattern, text_lower)
        if discard_match:
            effects.append({
                'type': 'discard_cards',
                'amount': int(discard_match.group(1)),
                'target': 'self'
            })
        
        # Energy attachment
        if 'attach' in text_lower and 'energy' in text_lower:
            effects.append({
                'type': 'attach_energy',
                'target': 'pokemon'
            })
        
        # If no specific patterns matched, store as raw text
        if not effects and effect_text.strip():
            effects.append({
                'type': 'raw_trainer_effect',
                'text': effect_text.strip(),
                'requires_manual_implementation': True
            })
        
        return effects
    
    def execute_trainer_effect(self, effect: Dict, battle_context) -> Tuple[bool, str]:
        """Execute a specific trainer effect"""
        effect_type = effect.get('type')
        
        if effect_type == 'draw_cards':
            amount = effect.get('amount', 1)
            # This would be handled by the game state
            return True, f"Draw {amount} cards"
        
        elif effect_type == 'heal_damage':
            amount = effect.get('amount', 0)
            # This would target a Pokemon and heal damage
            return True, f"Heal {amount} damage"
        
        elif effect_type == 'search_deck':
            amount = effect.get('amount', 1)
            # This would let player search deck for cards
            return True, f"Search deck for {amount} cards"
        
        elif effect_type == 'switch_pokemon':
            # This would allow switching active Pokemon
            return True, "Switch Pokemon"
        
        elif effect_type == 'attach_energy':
            # This would allow extra energy attachment
            return True, "Attach energy to Pokemon"
        
        elif effect_type == 'discard_cards':
            amount = effect.get('amount', 1)
            # This would discard cards from hand
            return True, f"Discard {amount} cards"
        
        elif effect_type == 'raw_trainer_effect':
            # Placeholder for effects that need manual implementation
            text = effect.get('text', '')
            return False, f"Manual implementation needed: {text}"
        
        return False, f"Unknown effect type: {effect_type}"
    
    def get_tool_attachments(self, pokemon_instance) -> List[BattleCard]:
        """Get tool cards attached to a Pokemon"""
        if not hasattr(pokemon_instance, 'attached_tools'):
            return []
        return pokemon_instance.attached_tools
    
    def attach_tool(self, pokemon_instance, tool_card: BattleCard) -> Tuple[bool, str]:
        """Attach a tool card to a Pokemon"""
        if self.get_trainer_type(tool_card) != TrainerType.TOOL:
            return False, "Not a tool card"
        
        # Initialize tool attachments if needed
        if not hasattr(pokemon_instance, 'attached_tools'):
            pokemon_instance.attached_tools = []
        
        # Check if already has a tool (limit to 1 tool per Pokemon in most TCG rules)
        if len(pokemon_instance.attached_tools) >= 1:
            return False, "Pokemon already has a tool attached"
        
        pokemon_instance.attached_tools.append(tool_card)
        self.logger.info(f"Attached tool {tool_card.name} to {pokemon_instance.name}")
        return True, f"Attached {tool_card.name}"
    
    def detach_tool(self, pokemon_instance, tool_card: BattleCard) -> Tuple[bool, str]:
        """Detach a tool card from a Pokemon"""
        if not hasattr(pokemon_instance, 'attached_tools'):
            return False, "No tools attached"
        
        if tool_card in pokemon_instance.attached_tools:
            pokemon_instance.attached_tools.remove(tool_card)
            self.logger.info(f"Detached tool {tool_card.name} from {pokemon_instance.name}")
            return True, f"Detached {tool_card.name}"
        
        return False, "Tool not attached to this Pokemon"
    
    def reset_turn_limits(self, turn_number: int):
        """Reset per-turn limits when a new turn starts"""
        if turn_number != self.current_turn:
            self.current_turn = turn_number
            self.supporters_played_this_turn = []
            self.logger.debug(f"Reset trainer limits for turn {turn_number}")


def create_trainer_effects_from_real_cards(trainer_cards: List[BattleCard]) -> Dict[str, List[Dict]]:
    """Create trainer effect database from real cards"""
    trainer_manager = TrainerCardManager()
    trainer_effects = {}
    
    for card in trainer_cards:
        if trainer_manager.is_trainer_card(card):
            effects = trainer_manager._parse_trainer_effects(card)
            trainer_effects[card.name] = effects
    
    return trainer_effects


# Example trainer card database patterns found in your cards:
EXAMPLE_TRAINER_PATTERNS = {
    'supporter_patterns': [
        'Draw cards', 'Search deck', 'Switch Pokemon', 'Heal damage',
        'Remove status conditions', 'Look at opponent hand'
    ],
    'item_patterns': [
        'Heal Pokemon', 'Remove status', 'Energy search', 'Evolution help',
        'Deck manipulation', 'Temporary effects'
    ],
    'tool_patterns': [
        'Increase HP', 'Reduce attack cost', 'Add attack damage',
        'Status condition immunity', 'Special abilities'
    ]
}