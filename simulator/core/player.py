"""
Player state management for Pokemon TCG Pocket battle simulation

Handles individual player state including hand, bench, active Pokemon,
and player-specific game mechanics.
"""

import logging
import random
from typing import Dict, List, Optional, Any, Tuple

# Import existing models
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from Card import Card
from Deck import Deck


class PlayerState:
    """Manages the state of a single player in battle"""
    
    def __init__(self, 
                 player_id: int, 
                 deck: Deck,
                 rng: random.Random,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize player state
        
        Args:
            player_id: Player identifier (0 or 1)
            deck: Player's deck (must be valid 20-card deck)
            rng: Random number generator for consistent behavior
            logger: Logger for events
        """
        self.player_id = player_id
        self.deck = deck
        self.rng = rng
        self.logger = logger or logging.getLogger(__name__)
        
        # Game state
        self.hand: List[Card] = []
        self.bench: List[Optional['BattlePokemon']] = [None] * 3  # Max 3 bench slots
        self.active_pokemon: Optional['BattlePokemon'] = None
        self.prize_points = 0
        
        # Turn state
        self.energy_attached_this_turn = False
        self.attacked_this_turn = False
        self.energy_types_available: List[str] = deck.deck_types.copy()
        self.energy_per_turn = 1
        self.setup_ready = False  # Whether player is ready for battle start
        
        # Configuration
        self.max_hand_size = 10
        self.max_bench_size = 3
        
        # Deck management
        self.deck_cards = deck.cards.copy()
        self.rng.shuffle(self.deck_cards)  # Shuffle deck for drawing
        
        self.logger.debug(f"Initialized player {player_id} with {len(self.deck_cards)} cards")
    
    def setup_initial_state(self) -> bool:
        """
        Setup initial game state for this player
        - Draw starting hand with at least 1 Basic Pokemon
        - Place 1 Basic Pokemon as active
        
        Returns:
            True if setup successful
        """
        try:
            # Draw initial hand (ensuring at least 1 Basic Pokemon)
            attempts = 0
            max_attempts = 10
            
            while attempts < max_attempts:
                self.hand = []
                
                # Draw 5 cards for starting hand
                for _ in range(5):
                    if len(self.deck_cards) > 0:
                        self.hand.append(self.deck_cards.pop())
                
                # Check if hand contains Basic Pokemon
                basic_pokemon = [card for card in self.hand if card.is_pokemon and card.is_basic]
                
                if basic_pokemon:
                    # DON'T auto-place Pokemon - just ensure Basic Pokemon exists
                    # Pokemon placement happens in separate pre-turn phase
                    self.logger.info(f"Player {self.player_id} drew 5 cards with {len(basic_pokemon)} Basic Pokemon")
                    return True
                else:
                    # Reshuffle and try again (simulates mulligan rule)
                    self.deck_cards.extend(self.hand)
                    self.rng.shuffle(self.deck_cards)
                    attempts += 1
                    
            self.logger.error(f"Player {self.player_id} failed to get Basic Pokemon after {max_attempts} attempts")
            return False
            
        except Exception as e:
            self.logger.error(f"Setup failed for player {self.player_id}: {e}")
            return False
    
    def can_continue_battle(self) -> bool:
        """
        Check if player can continue the battle
        
        Returns:
            True if player has at least one Pokemon that can be active
        """
        # Check if has active Pokemon
        if self.active_pokemon and not self.active_pokemon.is_knocked_out():
            return True
            
        # Check if has Pokemon on bench that can become active
        for bench_pokemon in self.bench:
            if bench_pokemon is not None and not bench_pokemon.is_knocked_out():
                return True
                
        # Check if has Basic Pokemon in hand that can be played
        for card in self.hand:
            if card.is_pokemon and card.is_basic:
                return True
                
        return False
    
    def get_active_pokemon_hp(self) -> int:
        """Get current HP of active Pokemon"""
        if self.active_pokemon:
            return self.active_pokemon.current_hp
        return 0
    
    def get_bench_pokemon_count(self) -> int:
        """Get number of Pokemon on bench"""
        return len([p for p in self.bench if p is not None])
    
    def get_bench_space(self) -> int:
        """Get number of available bench slots"""
        return self.max_bench_size - self.get_bench_pokemon_count()
    
    def can_attach_energy(self) -> bool:
        """Check if player can attach energy this turn"""
        return (not self.energy_attached_this_turn and 
                self.active_pokemon is not None and
                len(self.energy_types_available) > 0)
    
    def can_attack(self) -> bool:
        """Check if player can attack this turn"""
        return (not self.attacked_this_turn and 
                self.active_pokemon is not None and
                not self.active_pokemon.is_knocked_out())
    
    def get_available_attacks(self) -> List[Dict[str, Any]]:
        """
        Get list of attacks the active Pokemon can use
        
        Returns:
            List of attack dictionaries with energy requirements met
        """
        if not self.active_pokemon:
            return []
            
        available_attacks = []
        
        for attack in self.active_pokemon.card.attacks:
            if self.active_pokemon.can_use_attack(attack):
                available_attacks.append(attack)
                
        return available_attacks
    
    def get_playable_basic_pokemon(self) -> List[Card]:
        """Get Basic Pokemon in hand that can be played"""
        playable = []
        
        for card in self.hand:
            if card.is_pokemon and card.is_basic:
                # Can play if active slot empty or bench has space
                if not self.active_pokemon or self.get_bench_space() > 0:
                    playable.append(card)
                    
        return playable
    
    def get_retreatable_pokemon(self) -> bool:
        """Check if active Pokemon can retreat"""
        if not self.active_pokemon:
            return False
            
        # Need Pokemon on bench to retreat to
        if self.get_bench_pokemon_count() == 0:
            return False
            
        # Check energy requirement for retreat
        retreat_cost = self.active_pokemon.card.retreat_cost or 0
        energy_count = len(self.active_pokemon.energy_attached)
        
        return energy_count >= retreat_cost
    
    def get_available_bench_pokemon(self) -> List[Tuple[int, 'BattlePokemon']]:
        """
        Get list of available bench Pokemon that can become active
        
        Returns:
            List of (index, pokemon) tuples for valid bench Pokemon
        """
        available = []
        for i, bench_pokemon in enumerate(self.bench):
            if bench_pokemon is not None and not bench_pokemon.is_knocked_out():
                available.append((i, bench_pokemon))
        return available
    
    def get_pokemon_selection_options(self) -> Dict[str, Any]:
        """
        Get all available Pokemon options for forced selection after knockout
        
        Returns:
            Dictionary with bench and hand options
        """
        return {
            "bench_options": self.get_available_bench_pokemon(),
            "hand_options": self.get_playable_basic_pokemon()
        }
    
    def draw_card(self) -> Optional[Card]:
        """
        Draw a card from deck to hand
        
        Returns:
            Card drawn or None if deck empty or hand full
        """
        try:
            if len(self.hand) >= self.max_hand_size:
                self.logger.warning(f"Player {self.player_id} hand full, cannot draw")
                return None
                
            if len(self.deck_cards) == 0:
                self.logger.warning(f"Player {self.player_id} deck empty, cannot draw")
                return None
                
            card = self.deck_cards.pop()
            self.hand.append(card)
            
            self.logger.debug(f"Player {self.player_id} drew {card.name}")
            return card
            
        except Exception as e:
            self.logger.error(f"Draw failed for player {self.player_id}: {e}")
            return None
    
    def place_pokemon_active(self, card: Card) -> bool:
        """
        Place a Basic Pokemon as active
        
        Args:
            card: Basic Pokemon card from hand
            
        Returns:
            True if placed successfully
        """
        try:
            if not card.is_pokemon or not card.is_basic:
                return False
                
            if card not in self.hand:
                return False
                
            if self.active_pokemon is not None:
                return False
                
            # Remove from hand and place as active
            self.hand.remove(card)
            
            from .pokemon import BattlePokemon
            self.active_pokemon = BattlePokemon(card)
            
            self.logger.debug(f"Player {self.player_id} placed {card.name} as active")
            return True
            
        except Exception as e:
            self.logger.error(f"Place active failed for player {self.player_id}: {e}")
            return False
    
    def place_pokemon_bench(self, card: Card) -> bool:
        """
        Place a Basic Pokemon on bench
        
        Args:
            card: Basic Pokemon card from hand
            
        Returns:
            True if placed successfully
        """
        try:
            if not card.is_pokemon or not card.is_basic:
                return False
                
            if card not in self.hand:
                return False
                
            if self.get_bench_space() <= 0:
                return False
                
            # Find empty bench slot
            bench_index = None
            for i in range(self.max_bench_size):
                if self.bench[i] is None:
                    bench_index = i
                    break
                    
            if bench_index is None:
                return False
                
            # Remove from hand and place on bench
            self.hand.remove(card)
            
            from .pokemon import BattlePokemon
            self.bench[bench_index] = BattlePokemon(card)
            
            self.logger.debug(f"Player {self.player_id} placed {card.name} on bench")
            return True
            
        except Exception as e:
            self.logger.error(f"Place bench failed for player {self.player_id}: {e}")
            return False
    
    def attach_energy_to_active(self, energy_type: Optional[str] = None) -> bool:
        """
        Attach energy to active Pokemon
        
        Args:
            energy_type: Type of energy to attach (auto-selected if None)
            
        Returns:
            True if attached successfully
        """
        try:
            if not self.can_attach_energy():
                return False
                
            # Auto-select energy type if not specified
            if energy_type is None:
                if self.energy_types_available:
                    energy_type = self.rng.choice(self.energy_types_available)
                else:
                    energy_type = "Fire"  # Default to Fire, never attach Colorless
                    
            # Attach energy
            self.active_pokemon.energy_attached.append(energy_type)
            self.energy_attached_this_turn = True
            
            self.logger.debug(f"Player {self.player_id} attached {energy_type} energy to active Pokemon")
            return True
            
        except Exception as e:
            self.logger.error(f"Energy attachment failed for player {self.player_id}: {e}")
            return False
    
    def retreat_active_pokemon(self, bench_index: int) -> bool:
        """
        Retreat active Pokemon for one on bench
        
        Args:
            bench_index: Index of bench Pokemon to make active
            
        Returns:
            True if retreat successful
        """
        try:
            if not self.get_retreatable_pokemon():
                return False
                
            if bench_index < 0 or bench_index >= self.max_bench_size:
                return False
                
            if self.bench[bench_index] is None:
                return False
                
            # Pay retreat cost (remove energy)
            retreat_cost = self.active_pokemon.card.retreat_cost or 0
            for _ in range(retreat_cost):
                if self.active_pokemon.energy_attached:
                    self.active_pokemon.energy_attached.pop()
                    
            # Swap active and bench Pokemon
            old_active = self.active_pokemon
            self.active_pokemon = self.bench[bench_index]
            
            # Put old active on bench if there's space
            if self.get_bench_space() > 0:
                self.bench[bench_index] = old_active
            else:
                # No space on bench - this shouldn't happen in normal play
                self.logger.warning(f"Player {self.player_id} retreat with no bench space")
                self.bench[bench_index] = old_active
                
            self.logger.debug(f"Player {self.player_id} retreated active Pokemon")
            return True
            
        except Exception as e:
            self.logger.error(f"Retreat failed for player {self.player_id}: {e}")
            return False
    
    def handle_active_pokemon_knockout(self) -> bool:
        """
        Handle when active Pokemon is knocked out
        Must choose new active Pokemon from bench
        
        Returns:
            True if new active Pokemon chosen successfully
        """
        try:
            if self.active_pokemon and not self.active_pokemon.is_knocked_out():
                return True  # Active Pokemon not knocked out
                
            # Remove knocked out Pokemon
            self.active_pokemon = None
            
            # Look for Pokemon on bench to make active
            for i in range(self.max_bench_size):
                if self.bench[i] is not None and not self.bench[i].is_knocked_out():
                    self.active_pokemon = self.bench[i]
                    self.bench[i] = None
                    self.logger.debug(f"Player {self.player_id} promoted bench Pokemon to active")
                    return True
                    
            # No Pokemon on bench, try to play Basic from hand
            basic_pokemon = self.get_playable_basic_pokemon()
            if basic_pokemon:
                # Auto-play first Basic Pokemon
                return self.place_pokemon_active(basic_pokemon[0])
                
            self.logger.warning(f"Player {self.player_id} has no Pokemon to make active")
            return False
            
        except Exception as e:
            self.logger.error(f"Knockout handling failed for player {self.player_id}: {e}")
            return False
    
    def reset_turn_state(self):
        """Reset turn-based state at start of turn"""
        self.energy_attached_this_turn = False
        self.attacked_this_turn = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert player state to dictionary for logging"""
        return {
            "player_id": self.player_id,
            "hand_size": len(self.hand),
            "deck_size": len(self.deck_cards),
            "active_pokemon": self.active_pokemon.to_dict() if self.active_pokemon else None,
            "bench_count": self.get_bench_pokemon_count(),
            "bench": [p.to_dict() if p else None for p in self.bench],
            "prize_points": self.prize_points,
            "energy_attached_this_turn": self.energy_attached_this_turn,
            "energy_types_available": self.energy_types_available
        }
    
    def __str__(self) -> str:
        active_name = self.active_pokemon.card.name if self.active_pokemon else "None"
        return (f"Player {self.player_id}: Active={active_name}, "
                f"Bench={self.get_bench_pokemon_count()}/3, "
                f"Hand={len(self.hand)}, Points={self.prize_points}")