"""
Rules engine for Pokemon TCG Pocket battle simulation

Handles rule enforcement, validation, and win condition checking
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

# Import existing models
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from Card import Card
from Deck import Deck


class WinCondition(Enum):
    """Possible ways to win a battle"""
    PRIZE_POINTS = "prize_points"
    OPPONENT_NO_POKEMON = "opponent_no_pokemon"
    TURN_LIMIT = "turn_limit"
    OPPONENT_TIMEOUT = "opponent_timeout"
    BOTH_NO_POKEMON = "both_no_pokemon"  # Results in tie


@dataclass
class BattleRules:
    """Configuration for battle rules"""
    # Deck rules
    max_deck_size: int = 20
    min_deck_size: int = 20
    max_card_copies: int = 2
    require_basic_pokemon: bool = True
    
    # Game rules
    max_hand_size: int = 10
    max_bench_size: int = 3
    max_prize_points: int = 3
    max_turns: int = 100
    
    # Energy rules
    energy_per_turn: int = 1
    player_1_no_energy_turn_1: bool = True
    allow_zero_cost_attacks: bool = True
    
    # Damage rules
    weakness_damage_bonus: int = 20
    
    # Battle timeouts
    max_battle_duration_seconds: int = 300  # 5 minutes
    max_turn_duration_seconds: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rules to dictionary"""
        return {
            "max_deck_size": self.max_deck_size,
            "min_deck_size": self.min_deck_size,
            "max_card_copies": self.max_card_copies,
            "require_basic_pokemon": self.require_basic_pokemon,
            "max_hand_size": self.max_hand_size,
            "max_bench_size": self.max_bench_size,
            "max_prize_points": self.max_prize_points,
            "max_turns": self.max_turns,
            "energy_per_turn": self.energy_per_turn,
            "player_1_no_energy_turn_1": self.player_1_no_energy_turn_1,
            "allow_zero_cost_attacks": self.allow_zero_cost_attacks,
            "weakness_damage_bonus": self.weakness_damage_bonus,
            "max_battle_duration_seconds": self.max_battle_duration_seconds,
            "max_turn_duration_seconds": self.max_turn_duration_seconds
        }


class RulesEngine:
    """Engine for enforcing battle rules and checking win conditions"""
    
    def __init__(self, 
                 rules: Optional[BattleRules] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize rules engine
        
        Args:
            rules: Battle rules configuration
            logger: Logger for rule violations
        """
        self.rules = rules or BattleRules()
        self.logger = logger or logging.getLogger(__name__)
        
        self.logger.debug("Initialized rules engine with standard Pokemon TCG Pocket rules")
    
    def validate_deck(self, deck: Deck) -> Tuple[bool, List[str]]:
        """
        Validate a deck against battle rules
        
        Args:
            deck: Deck to validate
            
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Check deck size
            if len(deck.cards) != self.rules.max_deck_size:
                errors.append(f"Deck must contain exactly {self.rules.max_deck_size} cards, has {len(deck.cards)}")
            
            # Check card copy limits
            card_counts = {}
            for card in deck.cards:
                card_counts[card.name] = card_counts.get(card.name, 0) + 1
                
            for card_name, count in card_counts.items():
                if count > self.rules.max_card_copies:
                    errors.append(f"Too many copies of '{card_name}': {count}/{self.rules.max_card_copies}")
            
            # Check for Basic Pokemon requirement
            if self.rules.require_basic_pokemon:
                has_basic = any(card.is_pokemon and card.is_basic for card in deck.cards)
                if not has_basic:
                    errors.append("Deck must contain at least one Basic Pokémon")
            
            # Additional validation could include:
            # - Evolution line completeness
            # - Energy balance
            # - Trainer card limits
            
        except Exception as e:
            self.logger.error(f"Deck validation failed: {e}")
            errors.append(f"Validation error: {e}")
            
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def validate_hand_size(self, hand_size: int) -> Tuple[bool, str]:
        """
        Validate hand size against rules
        
        Args:
            hand_size: Current hand size
            
        Returns:
            (is_valid, error_message)
        """
        if hand_size > self.rules.max_hand_size:
            return False, f"Hand size {hand_size} exceeds maximum {self.rules.max_hand_size}"
        return True, ""
    
    def validate_bench_size(self, bench_count: int) -> Tuple[bool, str]:
        """
        Validate bench size against rules
        
        Args:
            bench_count: Number of Pokemon on bench
            
        Returns:
            (is_valid, error_message)
        """
        if bench_count > self.rules.max_bench_size:
            return False, f"Bench size {bench_count} exceeds maximum {self.rules.max_bench_size}"
        return True, ""
    
    def can_attach_energy(self, 
                         turn_number: int, 
                         player_id: int, 
                         already_attached: bool) -> Tuple[bool, str]:
        """
        Check if energy attachment is allowed
        
        Args:
            turn_number: Current turn number
            player_id: Player attempting to attach (0 or 1)
            already_attached: Whether energy was already attached this turn
            
        Returns:
            (is_allowed, reason)
        """
        if already_attached:
            return False, "Energy already attached this turn"
            
        # Player 1 restriction on turn 1
        if (self.rules.player_1_no_energy_turn_1 and 
            player_id == 0 and 
            turn_number == 1):
            return False, "Player 1 cannot attach energy on turn 1"
            
        return True, ""
    
    def check_win_condition(self, game_state) -> Tuple[Optional[WinCondition], Optional[int], str]:
        """
        Check for win conditions in current game state
        
        Args:
            game_state: Current GameState object
            
        Returns:
            (win_condition, winner_player_id, reason_description)
            winner_player_id is None for ties
        """
        try:
            # Check prize points victory
            for i, player in enumerate(game_state.players):
                if player.prize_points >= self.rules.max_prize_points:
                    return (WinCondition.PRIZE_POINTS, i, 
                           f"Player {i} reached {self.rules.max_prize_points} prize points")
            
            # Check if players can continue
            players_can_continue = []
            for i, player in enumerate(game_state.players):
                can_continue = player.can_continue_battle()
                players_can_continue.append(can_continue)
                
            unable_count = sum(1 for can_continue in players_can_continue if not can_continue)
            
            if unable_count == 2:
                # Both players cannot continue - tie
                return (WinCondition.BOTH_NO_POKEMON, None, "Both players unable to continue")
            elif unable_count == 1:
                # One player cannot continue - other wins
                winner = players_can_continue.index(True)
                return (WinCondition.OPPONENT_NO_POKEMON, winner, 
                       f"Player {1-winner} unable to continue")
            
            # Check turn limit
            if game_state.turn_number >= self.rules.max_turns:
                return (WinCondition.TURN_LIMIT, None, 
                       f"Turn limit of {self.rules.max_turns} reached")
            
            # No win condition met
            return None, None, ""
            
        except Exception as e:
            self.logger.error(f"Win condition check failed: {e}")
            return None, None, f"Error checking win conditions: {e}"
    
    def validate_attack(self, 
                       attacking_pokemon, 
                       attack: Dict[str, Any], 
                       target_pokemon) -> Tuple[bool, str]:
        """
        Validate an attack action
        
        Args:
            attacking_pokemon: BattlePokemon performing attack
            attack: Attack dictionary
            target_pokemon: BattlePokemon being attacked
            
        Returns:
            (is_valid, error_message)
        """
        try:
            # Check if attacker exists and is not KO'd
            if not attacking_pokemon or attacking_pokemon.is_knocked_out():
                return False, "Attacking Pokémon is knocked out"
                
            # Check if target exists
            if not target_pokemon:
                return False, "No target for attack"
                
            # Check if attack exists on Pokemon
            attack_name = attack.get("name", "")
            pokemon_attacks = [a.get("name", "") for a in attacking_pokemon.card.attacks]
            if attack_name not in pokemon_attacks:
                return False, f"Pokémon does not have attack '{attack_name}'"
                
            # Check energy requirements
            if not attacking_pokemon.can_use_attack(attack):
                return False, f"Insufficient energy for attack '{attack_name}'"
                
            # Check for status conditions that prevent attacking
            if attacking_pokemon.is_asleep:
                return False, "Pokémon is asleep and cannot attack"
            if attacking_pokemon.is_paralyzed:
                return False, "Pokémon is paralyzed and cannot attack"
                
            return True, ""
            
        except Exception as e:
            self.logger.error(f"Attack validation failed: {e}")
            return False, f"Attack validation error: {e}"
    
    def validate_retreat(self, 
                        retreating_pokemon, 
                        replacement_pokemon) -> Tuple[bool, str]:
        """
        Validate a retreat action
        
        Args:
            retreating_pokemon: BattlePokemon attempting to retreat
            replacement_pokemon: BattlePokemon to replace it
            
        Returns:
            (is_valid, error_message)
        """
        try:
            # Check if retreating Pokemon exists and can retreat
            if not retreating_pokemon or retreating_pokemon.is_knocked_out():
                return False, "Cannot retreat knocked out Pokémon"
                
            if retreating_pokemon.is_asleep:
                return False, "Cannot retreat sleeping Pokémon"
            if retreating_pokemon.is_paralyzed:
                return False, "Cannot retreat paralyzed Pokémon"
                
            # Check retreat cost
            if not retreating_pokemon.can_retreat():
                retreat_cost = retreating_pokemon.get_retreat_cost()
                energy_count = len(retreating_pokemon.energy_attached)
                return False, f"Insufficient energy to retreat (need {retreat_cost}, have {energy_count})"
                
            # Check replacement Pokemon
            if not replacement_pokemon or replacement_pokemon.is_knocked_out():
                return False, "Replacement Pokémon is not valid"
                
            return True, ""
            
        except Exception as e:
            self.logger.error(f"Retreat validation failed: {e}")
            return False, f"Retreat validation error: {e}"
    
    def validate_pokemon_placement(self, 
                                 card: Card, 
                                 position: str,
                                 current_bench_count: int,
                                 has_active: bool) -> Tuple[bool, str]:
        """
        Validate Pokemon placement
        
        Args:
            card: Card being placed
            position: "active" or "bench"
            current_bench_count: Current number of Pokemon on bench
            has_active: Whether player already has active Pokemon
            
        Returns:
            (is_valid, error_message)
        """
        try:
            # Check if card is a Pokemon
            if not card.is_pokemon:
                return False, f"'{card.name}' is not a Pokémon"
                
            # Check if Pokemon is Basic (only Basic can be played from hand)
            if not card.is_basic:
                return False, f"'{card.name}' is not a Basic Pokémon"
                
            # Validate position
            if position == "active":
                if has_active:
                    return False, "Active position is already occupied"
            elif position == "bench":
                if current_bench_count >= self.rules.max_bench_size:
                    return False, f"Bench is full ({self.rules.max_bench_size} max)"
            else:
                return False, f"Invalid position: {position}"
                
            # Must place active Pokemon first
            if not has_active and position != "active":
                return False, "Must place active Pokémon first"
                
            return True, ""
            
        except Exception as e:
            self.logger.error(f"Pokemon placement validation failed: {e}")
            return False, f"Placement validation error: {e}"
    
    def calculate_damage(self, 
                        attack: Dict[str, Any],
                        attacking_pokemon,
                        defending_pokemon) -> int:
        """
        Calculate total damage for an attack
        
        Args:
            attack: Attack being used
            attacking_pokemon: Pokemon performing attack
            defending_pokemon: Pokemon receiving damage
            
        Returns:
            Total damage to deal
        """
        try:
            # Get base damage
            damage_str = attack.get("damage", "0")
            
            # Parse damage value
            import re
            base_damage = 0
            if damage_str and str(damage_str) != "0":
                numbers = re.findall(r'\d+', str(damage_str))
                if numbers:
                    base_damage = int(numbers[0])
            
            # Apply weakness
            weakness_damage = 0
            if (defending_pokemon.card.weakness and
                attacking_pokemon.card.energy_type and
                attacking_pokemon.card.energy_type == defending_pokemon.card.weakness):
                weakness_damage = self.rules.weakness_damage_bonus
                
            total_damage = base_damage + weakness_damage
            
            self.logger.debug(f"Damage calculation: {base_damage} base + {weakness_damage} weakness = {total_damage}")
            return max(0, total_damage)  # Damage cannot be negative
            
        except Exception as e:
            self.logger.error(f"Damage calculation failed: {e}")
            return 0
    
    def get_prize_points_for_knockout(self, knocked_out_pokemon) -> int:
        """
        Get prize points awarded for knocking out a Pokemon
        
        Args:
            knocked_out_pokemon: BattlePokemon that was knocked out
            
        Returns:
            Number of prize points to award
        """
        if knocked_out_pokemon.is_ex_pokemon():
            return 2
        else:
            return 1
    
    def enforce_hand_limit(self, hand: List[Card]) -> List[Card]:
        """
        Enforce hand size limit by discarding excess cards
        
        Args:
            hand: Current hand
            
        Returns:
            Hand after enforcing limit
        """
        if len(hand) <= self.rules.max_hand_size:
            return hand
            
        # Keep first max_hand_size cards (in real game, player would choose)
        self.logger.warning(f"Hand size {len(hand)} exceeds limit {self.rules.max_hand_size}, discarding excess")
        return hand[:self.rules.max_hand_size]
    
    def is_legal_game_state(self, game_state) -> Tuple[bool, List[str]]:
        """
        Check if current game state is legal
        
        Args:
            game_state: GameState to validate
            
        Returns:
            (is_legal, list_of_violations)
        """
        violations = []
        
        try:
            for i, player in enumerate(game_state.players):
                # Check hand size
                if len(player.hand) > self.rules.max_hand_size:
                    violations.append(f"Player {i} hand size {len(player.hand)} exceeds limit")
                    
                # Check bench size
                bench_count = player.get_bench_pokemon_count()
                if bench_count > self.rules.max_bench_size:
                    violations.append(f"Player {i} bench size {bench_count} exceeds limit")
                    
                # Check prize points
                if player.prize_points > self.rules.max_prize_points:
                    violations.append(f"Player {i} has {player.prize_points} prize points (max {self.rules.max_prize_points})")
                    
            # Check turn limit
            if game_state.turn_number > self.rules.max_turns:
                violations.append(f"Turn {game_state.turn_number} exceeds limit {self.rules.max_turns}")
                
        except Exception as e:
            self.logger.error(f"Game state validation failed: {e}")
            violations.append(f"Validation error: {e}")
            
        is_legal = len(violations) == 0
        return is_legal, violations
    
    def get_rules_summary(self) -> Dict[str, Any]:
        """Get summary of current rules"""
        return {
            "deck_rules": {
                "deck_size": f"{self.rules.min_deck_size}-{self.rules.max_deck_size}",
                "max_copies": self.rules.max_card_copies,
                "require_basic": self.rules.require_basic_pokemon
            },
            "game_rules": {
                "max_hand_size": self.rules.max_hand_size,
                "max_bench_size": self.rules.max_bench_size,
                "max_prize_points": self.rules.max_prize_points,
                "max_turns": self.rules.max_turns
            },
            "energy_rules": {
                "energy_per_turn": self.rules.energy_per_turn,
                "player_1_restriction": self.rules.player_1_no_energy_turn_1,
                "zero_cost_attacks": self.rules.allow_zero_cost_attacks
            },
            "damage_rules": {
                "weakness_bonus": self.rules.weakness_damage_bonus
            }
        }
    
    def __str__(self) -> str:
        return f"RulesEngine(max_turns={self.rules.max_turns}, max_prize_points={self.rules.max_prize_points})"