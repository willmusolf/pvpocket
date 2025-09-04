"""
Card Data Bridge - Converts real Card objects to BattleCard format
Handles the integration between the main card database and battle simulator.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Import existing models
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from Card import Card, CardCollection


@dataclass
class BattleCard:
    """Optimized card data structure for battle simulation"""
    # Core identification
    id: int
    name: str
    
    # Battle mechanics
    card_type: str            # "Basic Pokémon", "Stage 1 Pokémon", "Trainer - Item", etc.
    energy_type: str          # Primary energy type for Pokémon
    hp: Optional[int] = None         # HP for Pokémon cards
    attacks: List[Dict[str, Any]] = None  # List of attack data with parsed effects
    weakness: Optional[str] = None   # Weakness type ("Fire", "Water", etc.)
    retreat_cost: Optional[int] = None # Energy cost to retreat
    
    # Evolution data
    evolution_stage: Optional[int] = None  # 0=Basic, 1=Stage 1, 2=Stage 2
    evolves_from: Optional[str] = None     # Name of previous evolution
    
    # Type information
    is_ex: bool = False      # True for EX Pokémon (2 prize points)
    
    # Special abilities
    abilities: List[Dict[str, Any]] = None  # Pokémon abilities with parsed effects
    
    # Visual data
    firebase_image_url: Optional[str] = None  # Card image URL for frontend display
    
    # Additional data
    rarity: str = ""
    set_name: str = ""
    
    def __post_init__(self):
        """Initialize default values after dataclass creation"""
        if self.attacks is None:
            self.attacks = []
        if self.abilities is None:
            self.abilities = []
    
    def is_pokemon(self) -> bool:
        """Check if this card is a Pokemon card"""
        return 'Pokémon' in self.card_type
    
    def is_trainer(self) -> bool:
        """Check if this card is a trainer card"""
        return 'Trainer' in self.card_type
    
    def is_basic_pokemon(self) -> bool:
        """Check if this is a Basic Pokemon"""
        return self.is_pokemon() and 'Basic' in self.card_type
    
    def is_evolution_pokemon(self) -> bool:
        """Check if this is an evolution Pokemon"""
        return self.is_pokemon() and ('Stage 1' in self.card_type or 'Stage 2' in self.card_type)


@dataclass 
class BattleAttack:
    """Battle-optimized attack data"""
    name: str
    cost: List[str]          # Energy cost (["Fire", "Fire", "Colorless"])
    damage: int              # Base damage (0 for effect-only attacks)
    effect_text: str         # Human-readable effect description
    parsed_effects: List[Dict[str, Any]] = None  # Machine-readable effects


class EffectParser:
    """Parses card effect text into structured battle effects"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Common effect patterns for automated parsing
        self.DAMAGE_PATTERNS = [
            (r'(\d+) more damage', lambda m: {'type': 'damage_boost', 'amount': int(m.group(1))}),
            (r'(\d+) additional damage', lambda m: {'type': 'damage_boost', 'amount': int(m.group(1))}),
            (r'does (\d+) damage for each heads', lambda m: {'type': 'coin_flip_damage', 'damage_per_heads': int(m.group(1))}),
            (r'this attack does (\d+) damage', lambda m: {'type': 'fixed_damage', 'damage': int(m.group(1))}),
        ]
        
        self.ENERGY_PATTERNS = [
            (r'discard (\d+) .*?energy', lambda m: {'type': 'discard_energy', 'amount': int(m.group(1))}),
            (r'discard (\d+) \[(\w+)\] energy', lambda m: {'type': 'discard_energy', 'amount': int(m.group(1)), 'energy_type': m.group(2)}),
            (r'attach.*?energy', lambda m: {'type': 'attach_energy'}),
        ]
        
        self.STATUS_PATTERNS = [
            (r'opponent.*?is now (\w+)', lambda m: {'type': 'status_condition', 'condition': m.group(1).lower()}),
            (r'your opponent.*?active.*?(\w+)', lambda m: {'type': 'status_condition', 'condition': m.group(1).lower()}),
        ]
        
        self.CONDITION_PATTERNS = [
            (r'if.*?special condition.*?(\d+) more damage', lambda m: {'type': 'conditional_damage', 'amount': int(m.group(1)), 'condition': 'special_condition'}),
            (r'if (\w+).*?(\d+) more damage', lambda m: {'type': 'conditional_damage', 'amount': int(m.group(2)), 'condition': m.group(1).lower()}),
        ]
        
        self.COIN_PATTERNS = [
            (r'flip (\d+) coins?.*?(\d+) damage for each heads', lambda m: {'type': 'coin_flip_damage', 'count': int(m.group(1)), 'damage_per_heads': int(m.group(2))}),
            (r'flip a coin until.*?tails.*?(\d+) damage for each heads', lambda m: {'type': 'coin_flip_until_tails', 'damage_per_heads': int(m.group(1))}),
            (r'flip a coin.*?if tails.*?does nothing', lambda m: {'type': 'coin_flip_all_or_nothing', 'success_on': 'heads'}),
            (r'flip a coin.*?if heads', lambda m: {'type': 'coin_flip_conditional', 'success_on': 'heads'}),
            (r'flip a coin.*?if tails', lambda m: {'type': 'coin_flip_conditional', 'success_on': 'tails'}),
            (r'flip (\d+) coins?', lambda m: {'type': 'coin_flip', 'count': int(m.group(1))}),
            (r'flip a coin', lambda m: {'type': 'coin_flip', 'count': 1}),
        ]
        
        self.OTHER_PATTERNS = [
            (r'draw (\d+) cards?', lambda m: {'type': 'draw_cards', 'amount': int(m.group(1))}),
            (r'this attack does nothing', lambda m: {'type': 'attack_fails'}),
            (r'heal (\d+) damage', lambda m: {'type': 'heal', 'amount': int(m.group(1))}),
        ]
        
        # Combine all patterns
        self.ALL_PATTERNS = (
            self.DAMAGE_PATTERNS + 
            self.ENERGY_PATTERNS + 
            self.STATUS_PATTERNS + 
            self.CONDITION_PATTERNS + 
            self.COIN_PATTERNS + 
            self.OTHER_PATTERNS
        )
        
    def parse_effect_text(self, effect_text: str) -> List[Dict[str, Any]]:
        """Parse effect text into structured effects"""
        if not effect_text or not effect_text.strip():
            return []
            
        effects = []
        text = effect_text.strip().lower()
        
        # Try each pattern
        for pattern, effect_func in self.ALL_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    effect = effect_func(match)
                    if effect:
                        effects.append(effect)
                except Exception as e:
                    self.logger.warning(f"Failed to parse effect pattern '{pattern}' in text '{effect_text}': {e}")
        
        # If no patterns matched, store as raw text for manual handling
        if not effects and effect_text.strip():
            effects.append({
                'type': 'raw_text',
                'text': effect_text.strip(),
                'requires_manual_implementation': True
            })
            
        return effects


class CardDataBridge:
    """Bridges real Card objects with battle simulator format"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.effect_parser = EffectParser(logger)
        
        # Energy type mapping for consistency
        self.ENERGY_TYPE_MAP = {
            'Fire': 'Fire',
            'Water': 'Water', 
            'Grass': 'Grass',
            'Lightning': 'Lightning',
            'Psychic': 'Psychic',
            'Fighting': 'Fighting',
            'Darkness': 'Darkness',
            'Metal': 'Metal',
            'Colorless': 'Colorless',
            # Handle variations
            'Electric': 'Lightning',
            'Normal': 'Colorless',
        }
        
    def convert_to_battle_card(self, card: Card) -> BattleCard:
        """Convert a Card object to BattleCard format"""
        try:
            # Validate required fields with safe defaults
            card_name = card.name or "Unknown Card"
            card_type = card.card_type or "Unknown"
            
            # Parse evolution info
            evolution_stage = self._get_evolution_stage(card_type)
            evolves_from = self._get_evolves_from(card)
            
            # Parse attacks with effects (handle None case)
            battle_attacks = self._parse_attacks(card.attacks or [])
            
            # Parse abilities with effects (handle None case)
            battle_abilities = self._parse_abilities(card.abilities or [])
            
            # Determine if EX Pokemon - safely handle None
            is_ex = False
            if card_name:
                is_ex = 'ex' in card_name.lower() or 'EX' in card_name
            
            # Map energy type - handle None case
            energy_type = "Colorless"  # Default
            if card.energy_type:
                energy_type = self.ENERGY_TYPE_MAP.get(card.energy_type, card.energy_type)
            
            return BattleCard(
                id=card.id or 0,
                name=card_name,
                card_type=card_type,
                hp=card.hp,
                attacks=battle_attacks,
                weakness=card.weakness,
                retreat_cost=card.retreat_cost,
                energy_type=energy_type,
                is_ex=is_ex,
                evolution_stage=evolution_stage,
                evolves_from=evolves_from,
                abilities=battle_abilities,
                firebase_image_url=getattr(card, 'firebase_image_url', None),
                rarity=card.rarity or "",
                set_name=card.set_name or ""
            )
            
        except Exception as e:
            # Safe handling of error - extract what we can
            safe_name = getattr(card, 'name', None) or "Unknown Card"
            safe_id = getattr(card, 'id', None) or 0
            self.logger.error(f"Failed to convert card {safe_name} (ID: {safe_id}): {e}")
            
            # Return a basic version as fallback with safe defaults
            return BattleCard(
                id=safe_id,
                name=safe_name,
                card_type=getattr(card, 'card_type', None) or "Unknown",
                hp=getattr(card, 'hp', None),
                attacks=[],
                weakness=getattr(card, 'weakness', None),
                retreat_cost=getattr(card, 'retreat_cost', None),
                energy_type=getattr(card, 'energy_type', None) or "Colorless",
                is_ex=False,
                evolution_stage=0,
                abilities=[],
                firebase_image_url=getattr(card, 'firebase_image_url', None),
                rarity=getattr(card, 'rarity', None) or "",
                set_name=getattr(card, 'set_name', None) or ""
            )
    
    def _get_evolution_stage(self, card_type: str) -> Optional[int]:
        """Determine evolution stage from card type"""
        if not card_type:
            return None
            
        card_type_lower = card_type.lower()
        if 'basic' in card_type_lower:
            return 0
        elif 'stage 1' in card_type_lower:
            return 1
        elif 'stage 2' in card_type_lower:
            return 2
        else:
            return None  # Trainer cards, etc.
    
    def _get_evolves_from(self, card: Card) -> Optional[str]:
        """Extract evolution predecessor (this would need to be enhanced with actual data)"""
        # This is a placeholder - in a real implementation, you'd have evolution data
        # For now, we'll implement basic rules
        if hasattr(card, 'evolves_from') and card.evolves_from:
            return card.evolves_from
            
        # Basic inference from names (could be improved with actual evolution data)
        if not card.name:
            return None
        name_lower = card.name.lower()
        
        # Common evolution chains
        evolution_chains = {
            'charmeleon': 'Charmander',
            'charizard': 'Charmeleon',
            'wartortle': 'Squirtle', 
            'blastoise': 'Wartortle',
            'ivysaur': 'Bulbasaur',
            'venusaur': 'Ivysaur',
        }
        
        return evolution_chains.get(name_lower)
    
    def _parse_attacks(self, attacks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse attack data with effect parsing"""
        if not attacks:
            return []
            
        battle_attacks = []
        
        for attack in attacks:
            # Skip None attacks
            if not attack:
                continue
                
            try:
                # Parse energy cost - handle None case
                cost = self._parse_energy_cost(attack.get('cost', []))
                
                # Parse damage - handle None case
                damage = self._parse_damage(attack.get('damage', '0'))
                
                # Parse effects - handle None case
                effect_text = attack.get('effect', '') or ''
                parsed_effects = self.effect_parser.parse_effect_text(effect_text)
                
                battle_attack = {
                    'name': attack.get('name', 'Unknown Attack'),
                    'cost': cost,
                    'damage': damage,
                    'effect_text': effect_text,
                    'parsed_effects': parsed_effects
                }
                
                battle_attacks.append(battle_attack)
                
            except Exception as e:
                self.logger.warning(f"Failed to parse attack {attack}: {e}")
                # Add basic version as fallback
                battle_attacks.append({
                    'name': attack.get('name', 'Unknown Attack'),
                    'cost': [],
                    'damage': 0,
                    'effect_text': attack.get('effect', ''),
                    'parsed_effects': []
                })
        
        return battle_attacks
    
    def _parse_abilities(self, abilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse ability data with effect parsing"""
        if not abilities:
            return []
            
        battle_abilities = []
        
        for ability in abilities:
            # Skip None abilities
            if not ability:
                continue
                
            try:
                # Handle None case for effect text
                effect_text = ability.get('effect', '') or ability.get('effect_text', '') or ''
                parsed_effects = self.effect_parser.parse_effect_text(effect_text)
                
                battle_ability = {
                    'name': ability.get('name', 'Unknown Ability'),
                    'effect_text': effect_text,
                    'parsed_effects': parsed_effects,
                    'type': self._classify_ability_type(effect_text)
                }
                
                battle_abilities.append(battle_ability)
                
            except Exception as e:
                self.logger.warning(f"Failed to parse ability {ability}: {e}")
        
        return battle_abilities
    
    def _classify_ability_type(self, effect_text: str) -> str:
        """Classify ability trigger type"""
        if not effect_text:
            return 'unknown'
            
        text_lower = effect_text.lower()
        
        if 'when you play' in text_lower or 'when this pokémon' in text_lower:
            return 'triggered'
        elif 'once during your turn' in text_lower:
            return 'activated'
        elif 'as long as' in text_lower or 'while' in text_lower:
            return 'passive'
        else:
            return 'unknown'
    
    def _parse_energy_cost(self, cost_data: List[str]) -> List[str]:
        """Parse energy cost into standard format"""
        if not cost_data:
            return []
            
        # Handle different cost formats
        standardized_cost = []
        
        for energy in cost_data:
            # Skip None or empty energy entries
            if not energy:
                continue
                
            # Handle single letter energy codes
            energy_map = {
                'R': 'Fire',     # R = Fire (Red)
                'F': 'Fire',
                'W': 'Water',
                'G': 'Grass',
                'L': 'Lightning',
                'P': 'Psychic',
                'C': 'Colorless',
                'D': 'Darkness',
                'M': 'Metal'
            }
            
            # Convert to string if not already
            energy_str = str(energy)
            
            # Handle multi-character energy costs (like 'RCC' = Fire + Colorless + Colorless)
            if len(energy_str) > 1:
                # Parse each character in the string
                for char in energy_str:
                    if char.upper() in energy_map:
                        standardized_cost.append(energy_map[char.upper()])
                    else:
                        # Default to colorless for unknown
                        standardized_cost.append('Colorless')
            elif energy_str.upper() in energy_map:
                standardized_cost.append(energy_map[energy_str.upper()])
            elif energy_str in self.ENERGY_TYPE_MAP:
                standardized_cost.append(energy_str)
            else:
                # Default to colorless for unknown
                standardized_cost.append('Colorless')
        
        return standardized_cost
    
    def _parse_damage(self, damage_str: str) -> int:
        """Parse damage value from string"""
        if not damage_str:
            return 0
            
        # Extract number from damage string
        damage_match = re.search(r'(\d+)', str(damage_str))
        if damage_match:
            return int(damage_match.group(1))
        else:
            return 0


def load_real_card_collection(logger: Optional[logging.Logger] = None) -> List[BattleCard]:
    """Load real cards from the card service and convert to battle format"""
    if logger is None:
        logger = logging.getLogger(__name__)
        
    try:
        # Import Flask app and get cards from the running service
        import requests
        import time
        
        # Try to get cards from the running Flask app
        try:
            logger.info("Attempting to load cards from running Flask app...")
            response = requests.get('http://localhost:5002/api/cards?limit=100', timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'cards' in data and data['cards']:
                    logger.info(f"Got {len(data['cards'])} cards from Flask API")
                    
                    # Convert to BattleCard format
                    bridge = CardDataBridge(logger)
                    battle_cards = []
                    
                    for card_data in data['cards']:
                        try:
                            # Create Card object from API data
                            card = Card(
                                id=card_data.get('id', 0),
                                name=card_data.get('name', ''),
                                energy_type=card_data.get('energy_type', ''),
                                card_type=card_data.get('card_type', ''),
                                hp=card_data.get('hp'),
                                attacks=card_data.get('attacks', []),
                                weakness=card_data.get('weakness'),
                                retreat_cost=card_data.get('retreat_cost'),
                                abilities=card_data.get('abilities', []),
                                rarity=card_data.get('rarity', ''),
                                set_name=card_data.get('set_name', ''),
                                firebase_image_url=card_data.get('firebase_image_url')
                            )
                            
                            battle_card = bridge.convert_to_battle_card(card)
                            battle_cards.append(battle_card)
                            
                        except Exception as e:
                            logger.warning(f"Failed to convert card {card_data.get('name', 'Unknown')}: {e}")
                    
                    logger.info(f"Successfully loaded {len(battle_cards)} battle cards from Flask API")
                    return battle_cards
                    
        except requests.RequestException as e:
            logger.warning(f"Could not connect to Flask app: {e}")
        
        # Fallback: try direct import (if running in same process)
        try:
            from app.services import CardService
            
            logger.info("Loading real cards from card service...")
            collection = CardService.get_card_collection()
            
            if not collection or not collection.cards:
                logger.warning("No cards found in collection")
                return []
            
            logger.info(f"Got {len(collection.cards)} cards from card service")
            
            # Convert to battle format
            bridge = CardDataBridge(logger)
            battle_cards = []
            
            for card in collection.cards:
                try:
                    battle_card = bridge.convert_to_battle_card(card)
                    battle_cards.append(battle_card)
                except Exception as e:
                    logger.error(f"Failed to convert card {getattr(card, 'name', 'Unknown')}: {e}")
            
            logger.info(f"Successfully loaded {len(battle_cards)} battle cards from card service")
            return battle_cards
            
        except ImportError as e:
            logger.warning(f"Could not import card service: {e}")
            return []
        
    except Exception as e:
        logger.error(f"Failed to load real card collection: {e}")
        return []


def create_battle_deck_from_real_cards(battle_cards: List[BattleCard], 
                                     deck_type: str = "fire", 
                                     logger: Optional[logging.Logger] = None) -> List[BattleCard]:
    """Create a battle deck from real cards of specified type"""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    # Filter cards by type and Pokemon only
    pokemon_cards = [
        card for card in battle_cards 
        if 'Pokémon' in card.card_type and 
        card.energy_type.lower() == deck_type.lower()
    ]
    
    # Filter Basic Pokemon for deck foundation
    basic_pokemon = [card for card in pokemon_cards if card.evolution_stage == 0]
    
    if len(basic_pokemon) < 10:
        logger.warning(f"Not enough {deck_type} Basic Pokemon for deck ({len(basic_pokemon)} found)")
        # Fall back to any Basic Pokemon
        basic_pokemon = [card for card in battle_cards if card.evolution_stage == 0][:10]
    
    # Create deck with 20 cards (simplified for now)
    deck_cards = []
    
    # Add Basic Pokemon (ensure at least 1)
    for i in range(min(10, len(basic_pokemon))):
        deck_cards.append(basic_pokemon[i])
    
    # Fill remaining slots with more basic pokemon or colorless
    while len(deck_cards) < 20 and basic_pokemon:
        deck_cards.append(basic_pokemon[len(deck_cards) % len(basic_pokemon)])
    
    logger.info(f"Created {deck_type} deck with {len(deck_cards)} cards")
    return deck_cards