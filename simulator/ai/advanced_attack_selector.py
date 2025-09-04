"""
Advanced Attack Selection Algorithm for Pokemon TCG Pocket AI

Intelligently selects optimal attacks considering damage, effects, energy efficiency,
game state, win conditions, and strategic positioning.
"""

import logging
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Import core components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from simulator.ai.board_evaluator import ThreatLevel, GamePhase


class AttackStrategy(Enum):
    """Attack strategy types"""
    MAXIMIZE_DAMAGE = "max_damage"
    SECURE_KO = "secure_ko"
    SETUP_EFFECTS = "setup"
    STATUS_DISRUPTION = "disrupt"
    TEMPO_CONTROL = "tempo"
    CONSERVATIVE = "conservative"
    DESPERATE = "desperate"


@dataclass
class AttackOption:
    """Represents an attack option with full analysis"""
    attack_dict: Dict[str, Any]  # Original attack data
    name: str
    base_damage: int
    effective_damage: int  # After weakness/resistance
    energy_cost: int
    
    # Strategic values
    ko_probability: float  # 0.0 to 1.0
    tempo_value: float  # How much tempo this gains/loses
    setup_value: float  # Value of setup effects
    disruption_value: float  # Value of disrupting opponent
    
    # Risk assessment
    energy_efficiency: float  # Damage per energy
    opportunity_cost: float  # Cost of not doing other actions
    
    # Effects analysis
    status_effects: List[str]
    special_effects: List[str]
    coin_flip_effects: List[str]
    
    # Overall scoring
    total_score: float


@dataclass
class AttackContext:
    """Context for attack selection"""
    my_pokemon: Any  # BattlePokemon attacking
    target_pokemon: Any  # BattlePokemon being attacked
    game_state: Any  # Current GameState
    board_evaluation: Any  # BoardEvaluationResult
    my_player_id: int
    
    # Strategic context
    current_strategy: AttackStrategy
    prize_pressure: ThreatLevel
    turn_number: int
    game_phase: GamePhase


class AdvancedAttackSelector:
    """Sophisticated attack selection with multi-factor analysis"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Scoring weights for different factors
        self.base_weights = {
            "damage": 0.35,
            "ko_potential": 0.25,
            "energy_efficiency": 0.15,
            "status_effects": 0.12,
            "tempo_value": 0.08,
            "setup_value": 0.05
        }
        
        # Strategy-specific weight modifications
        self.strategy_weights = {
            AttackStrategy.MAXIMIZE_DAMAGE: {
                "damage": 1.5,
                "ko_potential": 1.3,
                "energy_efficiency": 0.8
            },
            AttackStrategy.SECURE_KO: {
                "ko_potential": 2.0,
                "damage": 1.2,
                "energy_efficiency": 0.7
            },
            AttackStrategy.STATUS_DISRUPTION: {
                "status_effects": 2.0,
                "damage": 0.8,
                "tempo_value": 1.3
            },
            AttackStrategy.SETUP_EFFECTS: {
                "setup_value": 2.5,
                "damage": 0.6,
                "tempo_value": 1.2
            },
            AttackStrategy.TEMPO_CONTROL: {
                "tempo_value": 1.8,
                "energy_efficiency": 1.4,
                "damage": 0.9
            },
            AttackStrategy.CONSERVATIVE: {
                "energy_efficiency": 1.5,
                "ko_potential": 0.7,
                "status_effects": 1.2
            }
        }
        
        # Phase-specific considerations
        self.phase_modifiers = {
            GamePhase.EARLY_GAME: {
                "setup_value": 1.4,
                "energy_efficiency": 1.3,
                "ko_potential": 0.8
            },
            GamePhase.MID_GAME: {
                "damage": 1.1,
                "tempo_value": 1.2,
                "ko_potential": 1.1
            },
            GamePhase.LATE_GAME: {
                "ko_potential": 1.5,
                "damage": 1.3,
                "setup_value": 0.7
            }
        }
    
    def select_best_attack(self, context: AttackContext) -> Optional[AttackOption]:
        """
        Select the optimal attack given current context
        
        Args:
            context: AttackContext with all relevant information
            
        Returns:
            AttackOption representing the best choice, or None if no attacks available
        """
        try:
            # Get available attacks
            available_attacks = self._get_available_attacks(context)
            if not available_attacks:
                self.logger.debug("No attacks available")
                return None
            
            # Analyze each attack option
            attack_options = []
            for attack in available_attacks:
                option = self._analyze_attack_option(attack, context)
                if option:
                    attack_options.append(option)
            
            if not attack_options:
                self.logger.debug("No viable attack options")
                return None
            
            # Score and rank attacks
            scored_attacks = self._score_attacks(attack_options, context)
            
            # Select best attack
            best_attack = max(scored_attacks, key=lambda a: a.total_score)
            
            self.logger.debug(f"Selected attack: {best_attack.name} (score: {best_attack.total_score:.2f})")
            return best_attack
            
        except Exception as e:
            self.logger.error(f"Attack selection failed: {e}")
            # Fallback to simple highest damage
            return self._fallback_attack_selection(context)
    
    def _get_available_attacks(self, context: AttackContext) -> List[Dict[str, Any]]:
        """Get list of available attacks for the current Pokemon"""
        if not context.my_pokemon or context.my_pokemon.is_knocked_out():
            return []
        
        # Use existing method from BattlePokemon
        return context.my_pokemon.get_usable_attacks()
    
    def _analyze_attack_option(self, attack: Dict[str, Any], context: AttackContext) -> Optional[AttackOption]:
        """Perform comprehensive analysis of a single attack option"""
        try:
            name = attack.get('name', 'Unknown')
            
            # Basic damage calculations
            base_damage = self._parse_damage_value(attack.get('damage', '0'))
            effective_damage = self._calculate_effective_damage(attack, context)
            energy_cost = len(attack.get('cost', []))
            
            # KO probability calculation
            ko_prob = self._calculate_ko_probability(effective_damage, context.target_pokemon)
            
            # Energy efficiency
            efficiency = effective_damage / max(energy_cost, 1)
            
            # Analyze effects
            status_effects, special_effects, coin_effects = self._analyze_attack_effects(attack)
            
            # Strategic value calculations
            tempo_value = self._calculate_tempo_value(attack, effective_damage, context)
            setup_value = self._calculate_setup_value(special_effects, context)
            disruption_value = self._calculate_disruption_value(status_effects, context)
            
            # Opportunity cost
            opportunity_cost = self._calculate_opportunity_cost(energy_cost, context)
            
            return AttackOption(
                attack_dict=attack,
                name=name,
                base_damage=base_damage,
                effective_damage=effective_damage,
                energy_cost=energy_cost,
                ko_probability=ko_prob,
                tempo_value=tempo_value,
                setup_value=setup_value,
                disruption_value=disruption_value,
                energy_efficiency=efficiency,
                opportunity_cost=opportunity_cost,
                status_effects=status_effects,
                special_effects=special_effects,
                coin_flip_effects=coin_effects,
                total_score=0.0  # Will be calculated later
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze attack {attack.get('name', 'Unknown')}: {e}")
            return None
    
    def _parse_damage_value(self, damage_str: str) -> int:
        """Parse damage value from attack string"""
        if not damage_str or damage_str in ['0', '']:
            return 0
        
        import re
        numbers = re.findall(r'\d+', str(damage_str))
        if numbers:
            return int(numbers[0])
        return 0
    
    def _calculate_effective_damage(self, attack: Dict[str, Any], context: AttackContext) -> int:
        """Calculate damage after weakness/resistance"""
        base_damage = self._parse_damage_value(attack.get('damage', '0'))
        
        if not context.target_pokemon:
            return base_damage
        
        # Use existing damage calculation method
        return context.my_pokemon.calculate_attack_damage(
            attack, context.target_pokemon
        )
    
    def _calculate_ko_probability(self, damage: int, target_pokemon) -> float:
        """Calculate probability this attack will KO the target"""
        if not target_pokemon or damage <= 0:
            return 0.0
        
        current_hp = target_pokemon.current_hp
        if damage >= current_hp:
            return 1.0  # Guaranteed KO
        
        # For attacks with randomness (coin flips), adjust probability
        # This is simplified - could be expanded with actual coin flip analysis
        damage_ratio = damage / current_hp
        
        if damage_ratio >= 0.8:
            return 0.9  # Very likely KO with slight variance
        elif damage_ratio >= 0.6:
            return 0.7  # Good KO chance
        elif damage_ratio >= 0.4:
            return 0.4  # Moderate chance
        else:
            return damage_ratio * 0.3  # Low but scaling chance
    
    def _analyze_attack_effects(self, attack: Dict[str, Any]) -> Tuple[List[str], List[str], List[str]]:
        """Analyze attack effects and categorize them"""
        effect_text = attack.get('effect_text', '').lower()
        
        status_effects = []
        special_effects = []
        coin_effects = []
        
        # Status conditions
        if 'burn' in effect_text:
            status_effects.append('burn')
        if 'poison' in effect_text:
            status_effects.append('poison')
        if 'paralyze' in effect_text or 'paralyz' in effect_text:
            status_effects.append('paralyze')
        if 'sleep' in effect_text:
            status_effects.append('sleep')
        if 'confus' in effect_text:
            status_effects.append('confuse')
        
        # Special effects
        if 'heal' in effect_text:
            special_effects.append('heal_self')
        if 'draw' in effect_text and 'card' in effect_text:
            special_effects.append('draw_cards')
        if 'search' in effect_text:
            special_effects.append('deck_search')
        if 'energy' in effect_text and 'attach' in effect_text:
            special_effects.append('energy_acceleration')
        if 'discard' in effect_text and 'energy' in effect_text:
            special_effects.append('energy_removal')
        
        # Coin flip effects
        if 'flip' in effect_text and 'coin' in effect_text:
            if 'heads' in effect_text:
                coin_effects.append('coin_bonus')
            else:
                coin_effects.append('coin_effect')
        
        return status_effects, special_effects, coin_effects
    
    def _calculate_tempo_value(self, attack: Dict[str, Any], damage: int, context: AttackContext) -> float:
        """Calculate tempo advantage/disadvantage of this attack"""
        tempo_value = 0.0
        
        # Damage tempo - how much board presence this affects
        if context.target_pokemon:
            hp_percentage_damage = damage / context.target_pokemon.max_hp
            tempo_value += hp_percentage_damage * 30  # Scale to meaningful range
        
        # Energy cost tempo impact
        energy_cost = len(attack.get('cost', []))
        if energy_cost <= 1:
            tempo_value += 10  # Fast attacks gain tempo
        elif energy_cost >= 3:
            tempo_value -= 5  # Expensive attacks lose tempo
        
        # Status effect tempo
        effect_text = attack.get('effect_text', '').lower()
        if 'paralyze' in effect_text:
            tempo_value += 20  # Prevents opponent's turn
        elif 'sleep' in effect_text:
            tempo_value += 15  # Likely prevents opponent's turn
        elif 'burn' in effect_text or 'poison' in effect_text:
            tempo_value += 8  # Ongoing damage
        
        # Energy manipulation tempo
        if 'energy' in effect_text:
            if 'attach' in effect_text:
                tempo_value += 15  # Energy acceleration
            elif 'discard' in effect_text:
                tempo_value += 12  # Slow opponent down
        
        return tempo_value
    
    def _calculate_setup_value(self, special_effects: List[str], context: AttackContext) -> float:
        """Calculate value of setup effects"""
        setup_value = 0.0
        
        for effect in special_effects:
            if effect == 'draw_cards':
                setup_value += 20  # Card advantage
            elif effect == 'deck_search':
                setup_value += 25  # Deck thinning + selection
            elif effect == 'energy_acceleration':
                setup_value += 30  # Speed up future turns
            elif effect == 'heal_self':
                # Healing value depends on current HP
                if context.my_pokemon:
                    hp_ratio = context.my_pokemon.current_hp / context.my_pokemon.max_hp
                    if hp_ratio < 0.5:
                        setup_value += 25  # High value when low HP
                    else:
                        setup_value += 10  # Lower value when healthy
        
        # Early game setup is more valuable
        if context.game_phase == GamePhase.EARLY_GAME:
            setup_value *= 1.3
        elif context.game_phase == GamePhase.LATE_GAME:
            setup_value *= 0.7
        
        return setup_value
    
    def _calculate_disruption_value(self, status_effects: List[str], context: AttackContext) -> float:
        """Calculate value of disrupting opponent"""
        disruption_value = 0.0
        
        for effect in status_effects:
            if effect == 'paralyze':
                disruption_value += 30  # Prevents next attack
            elif effect == 'sleep':
                disruption_value += 25  # Likely prevents next attack  
            elif effect == 'burn':
                disruption_value += 15  # 20 damage per turn
            elif effect == 'poison':
                disruption_value += 12  # 10 damage per turn
            elif effect == 'confuse':
                disruption_value += 18  # 50% chance to hurt self
        
        # Disruption more valuable when behind
        if context.prize_pressure in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            disruption_value *= 1.4
        
        # Less valuable if opponent likely to switch out
        if context.target_pokemon and len(context.target_pokemon.energy_attached) == 0:
            disruption_value *= 0.7  # Easy to retreat
        
        return disruption_value
    
    def _calculate_opportunity_cost(self, energy_cost: int, context: AttackContext) -> float:
        """Calculate opportunity cost of using this attack"""
        opportunity_cost = 0.0
        
        # High energy attacks have opportunity cost
        if energy_cost >= 3:
            opportunity_cost += 10  # Could have done multiple smaller actions
        
        # If we could KO with a cheaper attack, expensive overkill has cost
        if context.target_pokemon:
            remaining_hp = context.target_pokemon.current_hp
            if energy_cost >= 2 and remaining_hp <= 30:
                opportunity_cost += 15  # Overkill with expensive attack
        
        # Late game opportunity costs are higher (less time to recover)
        if context.game_phase == GamePhase.LATE_GAME:
            opportunity_cost *= 1.2
        
        return opportunity_cost
    
    def _score_attacks(self, attack_options: List[AttackOption], context: AttackContext) -> List[AttackOption]:
        """Score all attack options based on current strategy and context"""
        # Get active weights for current strategy
        active_weights = self.base_weights.copy()
        
        # Apply strategy modifications
        strategy_mods = self.strategy_weights.get(context.current_strategy, {})
        for factor, modifier in strategy_mods.items():
            if factor in active_weights:
                active_weights[factor] *= modifier
        
        # Apply phase modifications
        phase_mods = self.phase_modifiers.get(context.game_phase, {})
        for factor, modifier in phase_mods.items():
            if factor in active_weights:
                active_weights[factor] *= modifier
        
        # Score each attack
        for attack in attack_options:
            score = 0.0
            
            # Damage component
            damage_score = min(100, attack.effective_damage * 1.2)  # Scale damage
            score += damage_score * active_weights["damage"]
            
            # KO potential component  
            ko_score = attack.ko_probability * 100
            score += ko_score * active_weights["ko_potential"]
            
            # Energy efficiency component
            efficiency_score = min(80, attack.energy_efficiency * 3)  # Scale efficiency
            score += efficiency_score * active_weights["energy_efficiency"]
            
            # Status effects component
            status_score = attack.disruption_value
            score += status_score * active_weights["status_effects"]
            
            # Tempo component
            tempo_score = max(0, attack.tempo_value)  # Only positive tempo
            score += tempo_score * active_weights["tempo_value"]
            
            # Setup component
            setup_score = attack.setup_value
            score += setup_score * active_weights["setup_value"]
            
            # Apply opportunity cost penalty
            score -= attack.opportunity_cost
            
            # Situational bonuses/penalties
            score = self._apply_situational_modifiers(score, attack, context)
            
            attack.total_score = score
        
        return attack_options
    
    def _apply_situational_modifiers(self, base_score: float, attack: AttackOption, context: AttackContext) -> float:
        """Apply situational modifiers based on game state"""
        modified_score = base_score
        
        # Desperate situations - prioritize any KO chance
        if context.prize_pressure == ThreatLevel.CRITICAL:
            if attack.ko_probability > 0.5:
                modified_score *= 1.5
        
        # When ahead, prioritize safe/efficient attacks
        if (context.board_evaluation and 
            hasattr(context.board_evaluation, 'position_score') and 
            context.board_evaluation.position_score > 50):
            if attack.energy_efficiency > 15:
                modified_score *= 1.2
        
        # Coin flip penalties in crucial situations
        if (context.prize_pressure >= ThreatLevel.HIGH and 
            attack.coin_flip_effects and 
            attack.ko_probability < 1.0):
            modified_score *= 0.8  # Reduce coin flip reliability when critical
        
        # Low HP - prioritize finishing opponent or defensive options
        if (context.my_pokemon and 
            context.my_pokemon.current_hp < context.my_pokemon.max_hp * 0.3):
            if attack.ko_probability > 0.7:
                modified_score *= 1.3  # Go for the win
            elif 'heal_self' in attack.special_effects:
                modified_score *= 1.2  # Survive longer
        
        return modified_score
    
    def _determine_attack_strategy(self, context: AttackContext) -> AttackStrategy:
        """Determine optimal attack strategy based on context"""
        # Critical situations
        if context.prize_pressure == ThreatLevel.CRITICAL:
            return AttackStrategy.DESPERATE
        
        # Can secure a KO
        if (context.board_evaluation and 
            hasattr(context.board_evaluation.threat_assessment, 'i_can_ko_next_turn') and
            context.board_evaluation.threat_assessment.i_can_ko_next_turn):
            return AttackStrategy.SECURE_KO
        
        # Early game
        if context.game_phase == GamePhase.EARLY_GAME:
            return AttackStrategy.SETUP_EFFECTS
        
        # Late game
        if context.game_phase == GamePhase.LATE_GAME:
            return AttackStrategy.MAXIMIZE_DAMAGE
        
        # When behind
        if (context.board_evaluation and 
            hasattr(context.board_evaluation, 'position_score') and
            context.board_evaluation.position_score < -30):
            return AttackStrategy.STATUS_DISRUPTION
        
        # Default balanced approach
        return AttackStrategy.TEMPO_CONTROL
    
    def _fallback_attack_selection(self, context: AttackContext) -> Optional[AttackOption]:
        """Fallback to simple attack selection if advanced analysis fails"""
        available_attacks = self._get_available_attacks(context)
        if not available_attacks:
            return None
        
        # Simple: pick highest damage attack
        best_attack = max(available_attacks, key=lambda a: self._parse_damage_value(a.get('damage', '0')))
        
        return AttackOption(
            attack_dict=best_attack,
            name=best_attack.get('name', 'Unknown'),
            base_damage=self._parse_damage_value(best_attack.get('damage', '0')),
            effective_damage=self._parse_damage_value(best_attack.get('damage', '0')),
            energy_cost=len(best_attack.get('cost', [])),
            ko_probability=0.5,
            tempo_value=0.0,
            setup_value=0.0,
            disruption_value=0.0,
            energy_efficiency=0.0,
            opportunity_cost=0.0,
            status_effects=[],
            special_effects=[],
            coin_flip_effects=[],
            total_score=100.0
        )