"""
Smart Card Evaluation System for Pokemon TCG Pocket AI

Provides sophisticated evaluation of Pokemon, trainer cards, and energy for optimal decision making.
Considers attack efficiency, energy curves, strategic value, and situational utility.
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


class CardRole(Enum):
    """Strategic roles for Pokemon cards"""
    EARLY_GAME_ATTACKER = "early_attacker"
    MID_GAME_POWERHOUSE = "mid_game" 
    LATE_GAME_FINISHER = "finisher"
    SETUP_SUPPORT = "support"
    UTILITY = "utility"
    WALL = "wall"


class EvaluationContext(Enum):
    """Context for card evaluation"""
    OPENING_HAND = "opening"
    EARLY_GAME = "early"
    MID_GAME = "mid"
    LATE_GAME = "late"
    BEHIND_ON_PRIZES = "behind"
    AHEAD_ON_PRIZES = "ahead"
    LOW_HP_SITUATION = "low_hp"


@dataclass
class PokemonStats:
    """Analyzed Pokemon statistics"""
    hp_tier: int  # 1-5, higher = better HP
    attack_efficiency: float  # Damage per energy cost
    energy_requirement: int  # Total energy needed for best attack
    retreat_efficiency: float  # 1.0 = free retreat, 0.0 = very expensive
    status_utility: float  # Value from status effects/special abilities
    evolution_potential: float  # Value if this can evolve


@dataclass
class AttackAnalysis:
    """Detailed attack analysis"""
    name: str
    damage: int
    energy_cost: int
    efficiency: float  # damage per energy
    special_effects: List[str]
    situational_value: float  # Extra value from effects
    total_value: float  # Combined damage + situational value


@dataclass
class CardEvaluation:
    """Complete card evaluation result"""
    card_id: str
    card_name: str
    base_value: float  # 0-100 base card strength
    situational_value: float  # -50 to +50 based on current situation
    total_value: float  # Combined value for decision making
    primary_role: CardRole
    recommended_timing: List[EvaluationContext]
    key_strengths: List[str]
    key_weaknesses: List[str]


class SmartCardEvaluator:
    """Advanced card evaluation system for strategic decision making"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # HP tier thresholds for Pokemon evaluation
        self.hp_tiers = {
            1: 0,    # No HP (non-Pokemon)
            2: 60,   # Low HP
            3: 80,   # Medium HP  
            4: 120,  # High HP
            5: 160   # Very high HP
        }
        
        # Energy efficiency thresholds
        self.efficiency_tiers = {
            "excellent": 25,  # 25+ damage per energy
            "good": 20,       # 20-24 damage per energy
            "average": 15,    # 15-19 damage per energy
            "poor": 10,       # 10-14 damage per energy
            "terrible": 0     # <10 damage per energy
        }
        
        # Evaluation weights for different factors
        self.weights = {
            "hp_value": 0.25,
            "attack_efficiency": 0.30,
            "energy_curve": 0.20,
            "utility_effects": 0.15,
            "retreat_cost": 0.10
        }
        
        # Context-specific multipliers
        self.context_multipliers = {
            EvaluationContext.OPENING_HAND: {
                "basic_pokemon": 1.5,  # Basic Pokemon more valuable in opening
                "low_energy_attacks": 1.3,
                "setup_effects": 1.4
            },
            EvaluationContext.EARLY_GAME: {
                "quick_setup": 1.4,
                "low_retreat": 1.2,
                "tempo_effects": 1.3
            },
            EvaluationContext.LATE_GAME: {
                "high_damage": 1.5,
                "game_ending": 1.6,
                "ko_potential": 1.4
            },
            EvaluationContext.BEHIND_ON_PRIZES: {
                "comeback_potential": 1.7,
                "defensive_utility": 1.3,
                "stall_effects": 1.2
            }
        }
    
    def evaluate_pokemon(self, card, game_context: EvaluationContext = EvaluationContext.MID_GAME) -> CardEvaluation:
        """
        Comprehensive Pokemon card evaluation
        
        Args:
            card: Pokemon card to evaluate
            game_context: Current game situation
            
        Returns:
            CardEvaluation with detailed analysis
        """
        try:
            # Analyze basic Pokemon stats
            stats = self._analyze_pokemon_stats(card)
            
            # Evaluate attacks in detail
            attack_analyses = self._analyze_attacks(card)
            
            # Calculate base card value
            base_value = self._calculate_pokemon_base_value(card, stats, attack_analyses)
            
            # Apply situational modifiers
            situational_value = self._calculate_situational_value(
                card, stats, attack_analyses, game_context
            )
            
            # Determine primary role
            primary_role = self._determine_pokemon_role(card, stats, attack_analyses)
            
            # Recommend timing contexts
            timing_contexts = self._recommend_timing(card, stats, attack_analyses, primary_role)
            
            # Identify strengths and weaknesses
            strengths, weaknesses = self._identify_pokemon_traits(card, stats, attack_analyses)
            
            total_value = base_value + situational_value
            
            return CardEvaluation(
                card_id=card.id,
                card_name=card.name,
                base_value=base_value,
                situational_value=situational_value,
                total_value=total_value,
                primary_role=primary_role,
                recommended_timing=timing_contexts,
                key_strengths=strengths,
                key_weaknesses=weaknesses
            )
            
        except Exception as e:
            self.logger.error(f"Pokemon evaluation failed for {card.name}: {e}")
            return self._create_fallback_evaluation(card)
    
    def evaluate_trainer_card(self, card, game_context: EvaluationContext = EvaluationContext.MID_GAME) -> CardEvaluation:
        """
        Evaluate trainer cards (supporters, items, tools)
        
        Args:
            card: Trainer card to evaluate
            game_context: Current game situation
            
        Returns:
            CardEvaluation for the trainer card
        """
        try:
            # Determine trainer type and effects
            trainer_type = self._get_trainer_type(card)
            effects = self._analyze_trainer_effects(card)
            
            # Calculate base value based on effect power
            base_value = self._calculate_trainer_base_value(card, trainer_type, effects)
            
            # Apply context-specific value
            situational_value = self._calculate_trainer_situational_value(
                card, effects, game_context
            )
            
            # Determine role and timing
            role = self._determine_trainer_role(trainer_type, effects)
            timing = self._recommend_trainer_timing(effects, game_context)
            
            # Identify key aspects
            strengths, weaknesses = self._identify_trainer_traits(effects, trainer_type)
            
            return CardEvaluation(
                card_id=card.id,
                card_name=card.name,
                base_value=base_value,
                situational_value=situational_value,
                total_value=base_value + situational_value,
                primary_role=role,
                recommended_timing=timing,
                key_strengths=strengths,
                key_weaknesses=weaknesses
            )
            
        except Exception as e:
            self.logger.error(f"Trainer evaluation failed for {card.name}: {e}")
            return self._create_fallback_evaluation(card)
    
    def _analyze_pokemon_stats(self, card) -> PokemonStats:
        """Analyze Pokemon's core statistics"""
        # HP tier calculation
        hp = card.hp or 0
        hp_tier = 1
        for tier, threshold in sorted(self.hp_tiers.items(), reverse=True):
            if hp >= threshold:
                hp_tier = tier
                break
        
        # Attack efficiency analysis
        best_efficiency = 0.0
        min_energy_for_best = 0
        
        for attack in card.attacks:
            energy_cost = len(attack.get('cost', []))
            damage = self._parse_damage_value(attack.get('damage', '0'))
            
            if energy_cost > 0:
                efficiency = damage / energy_cost
                if efficiency > best_efficiency:
                    best_efficiency = efficiency
                    min_energy_for_best = energy_cost
        
        # Retreat efficiency
        retreat_cost = card.retreat_cost or 0
        retreat_efficiency = max(0.0, (4 - retreat_cost) / 4)  # 0-4 cost scaled to 0-1
        
        # Status utility (simplified - could be expanded)
        status_utility = 0.0
        for attack in card.attacks:
            effect_text = attack.get('effect_text', '').lower()
            if any(status in effect_text for status in ['burn', 'poison', 'paralyze', 'sleep']):
                status_utility += 0.2
            if 'heal' in effect_text:
                status_utility += 0.15
        
        # Evolution potential (simplified)
        evolution_potential = 0.0
        if hasattr(card, 'evolution_stage'):
            if card.evolution_stage == 0:  # Basic
                evolution_potential = 0.3  # Can evolve
            elif card.evolution_stage == 1:  # Stage 1
                evolution_potential = 0.2  # Might evolve further
        
        return PokemonStats(
            hp_tier=hp_tier,
            attack_efficiency=best_efficiency,
            energy_requirement=min_energy_for_best,
            retreat_efficiency=retreat_efficiency,
            status_utility=min(1.0, status_utility),
            evolution_potential=evolution_potential
        )
    
    def _analyze_attacks(self, card) -> List[AttackAnalysis]:
        """Analyze all attacks on a Pokemon"""
        analyses = []
        
        for attack in card.attacks:
            name = attack.get('name', 'Unknown')
            damage = self._parse_damage_value(attack.get('damage', '0'))
            energy_cost = len(attack.get('cost', []))
            
            # Calculate efficiency
            efficiency = damage / max(energy_cost, 1)
            
            # Analyze special effects
            effect_text = attack.get('effect_text', '').lower()
            special_effects = []
            situational_value = 0.0
            
            # Status effects
            if 'burn' in effect_text:
                special_effects.append('Burns opponent')
                situational_value += 15  # 20 damage per turn value
            if 'poison' in effect_text:
                special_effects.append('Poisons opponent')  
                situational_value += 10  # 10 damage per turn value
            if 'paralyze' in effect_text or 'paralyz' in effect_text:
                special_effects.append('Paralyzes opponent')
                situational_value += 20  # Prevents attack
            if 'sleep' in effect_text:
                special_effects.append('Puts opponent to sleep')
                situational_value += 15
            
            # Healing effects
            if 'heal' in effect_text:
                heal_match = self._extract_number_from_text(effect_text, 'heal')
                heal_amount = heal_match or 20  # Default heal amount
                special_effects.append(f'Heals {heal_amount} HP')
                situational_value += heal_amount * 0.5  # Healing worth ~half damage
            
            # Coin flip effects
            if 'flip' in effect_text and 'coin' in effect_text:
                special_effects.append('Coin flip effect')
                situational_value += damage * 0.25  # Expected value reduction for coin flip
            
            # Energy/bench effects
            if 'energy' in effect_text and ('attach' in effect_text or 'search' in effect_text):
                special_effects.append('Energy acceleration')
                situational_value += 25  # Energy acceleration is valuable
            
            total_value = damage + situational_value
            
            analyses.append(AttackAnalysis(
                name=name,
                damage=damage,
                energy_cost=energy_cost,
                efficiency=efficiency,
                special_effects=special_effects,
                situational_value=situational_value,
                total_value=total_value
            ))
        
        return analyses
    
    def _parse_damage_value(self, damage_str: str) -> int:
        """Parse damage value from string (handles '30+', '×', etc.)"""
        if not damage_str or damage_str in ['0', '']:
            return 0
        
        # Extract first number found
        import re
        numbers = re.findall(r'\d+', str(damage_str))
        if numbers:
            return int(numbers[0])
        return 0
    
    def _extract_number_from_text(self, text: str, keyword: str) -> Optional[int]:
        """Extract number associated with a keyword from text"""
        import re
        pattern = rf'{keyword}.*?(\d+)'
        match = re.search(pattern, text)
        return int(match.group(1)) if match else None
    
    def _calculate_pokemon_base_value(self, card, stats: PokemonStats, 
                                    attacks: List[AttackAnalysis]) -> float:
        """Calculate base Pokemon value (0-100)"""
        # HP component
        hp_value = stats.hp_tier * 15  # 15-75 points from HP
        
        # Attack efficiency component
        efficiency_value = 0
        if attacks:
            best_attack = max(attacks, key=lambda a: a.total_value)
            # Scale efficiency to 0-40 points
            efficiency_value = min(40, best_attack.efficiency * 1.5)
        
        # Energy curve component (lower energy = better for tempo)
        energy_value = max(0, 25 - stats.energy_requirement * 5)  # 0-25 points
        
        # Utility components
        retreat_value = stats.retreat_efficiency * 10  # 0-10 points
        status_value = stats.status_utility * 15  # 0-15 points
        evolution_value = stats.evolution_potential * 10  # 0-10 points
        
        base_value = (
            hp_value * self.weights["hp_value"] +
            efficiency_value * self.weights["attack_efficiency"] +
            energy_value * self.weights["energy_curve"] +
            (status_value + evolution_value) * self.weights["utility_effects"] +
            retreat_value * self.weights["retreat_cost"]
        )
        
        return min(100, base_value)
    
    def _calculate_situational_value(self, card, stats: PokemonStats,
                                   attacks: List[AttackAnalysis], 
                                   context: EvaluationContext) -> float:
        """Calculate situational value modifiers (-50 to +50)"""
        situational_value = 0.0
        
        # Get context multipliers
        context_mults = self.context_multipliers.get(context, {})
        
        # Early game bonuses
        if context in [EvaluationContext.OPENING_HAND, EvaluationContext.EARLY_GAME]:
            if hasattr(card, 'is_basic') and card.is_basic:
                situational_value += 15 * context_mults.get("basic_pokemon", 1.0)
            
            if stats.energy_requirement <= 2:
                situational_value += 10 * context_mults.get("low_energy_attacks", 1.0)
            
            if stats.retreat_efficiency > 0.5:
                situational_value += 8 * context_mults.get("low_retreat", 1.0)
        
        # Late game bonuses
        elif context == EvaluationContext.LATE_GAME:
            if attacks and max(attacks, key=lambda a: a.damage).damage >= 80:
                situational_value += 20 * context_mults.get("high_damage", 1.0)
            
            # High HP Pokemon valuable late
            if stats.hp_tier >= 4:
                situational_value += 15
        
        # Behind on prizes - defensive value
        elif context == EvaluationContext.BEHIND_ON_PRIZES:
            if stats.hp_tier >= 4:  # High HP for stalling
                situational_value += 12 * context_mults.get("defensive_utility", 1.0)
            
            if stats.status_utility > 0.3:  # Status effects for disruption
                situational_value += 10 * context_mults.get("stall_effects", 1.0)
        
        # Low HP situation - healing/switching value  
        elif context == EvaluationContext.LOW_HP_SITUATION:
            if any('heal' in effect for attack in attacks for effect in attack.special_effects):
                situational_value += 15
            
            if stats.retreat_efficiency > 0.7:  # Easy retreat
                situational_value += 12
        
        return max(-50, min(50, situational_value))
    
    def _determine_pokemon_role(self, card, stats: PokemonStats, 
                               attacks: List[AttackAnalysis]) -> CardRole:
        """Determine Pokemon's primary strategic role"""
        if not attacks:
            return CardRole.UTILITY
        
        best_attack = max(attacks, key=lambda a: a.total_value)
        
        # Early game attacker - low energy, decent damage
        if stats.energy_requirement <= 2 and best_attack.damage >= 30:
            return CardRole.EARLY_GAME_ATTACKER
        
        # Wall - high HP, low damage
        if stats.hp_tier >= 4 and best_attack.damage <= 60:
            return CardRole.WALL
        
        # Finisher - high damage requirements
        if best_attack.damage >= 100 or stats.energy_requirement >= 4:
            return CardRole.LATE_GAME_FINISHER
        
        # Support - utility effects
        if stats.status_utility > 0.4 or any(len(a.special_effects) >= 2 for a in attacks):
            return CardRole.SETUP_SUPPORT
        
        # Mid-game powerhouse - balanced stats
        if stats.energy_requirement == 3 and best_attack.damage >= 60:
            return CardRole.MID_GAME_POWERHOUSE
        
        return CardRole.UTILITY
    
    def _recommend_timing(self, card, stats: PokemonStats, 
                         attacks: List[AttackAnalysis], 
                         role: CardRole) -> List[EvaluationContext]:
        """Recommend when to use this Pokemon"""
        contexts = []
        
        # Role-based timing
        if role == CardRole.EARLY_GAME_ATTACKER:
            contexts.extend([EvaluationContext.OPENING_HAND, EvaluationContext.EARLY_GAME])
        elif role == CardRole.LATE_GAME_FINISHER:
            contexts.append(EvaluationContext.LATE_GAME)
        elif role == CardRole.MID_GAME_POWERHOUSE:
            contexts.extend([EvaluationContext.MID_GAME, EvaluationContext.LATE_GAME])
        elif role == CardRole.WALL:
            contexts.extend([EvaluationContext.BEHIND_ON_PRIZES, EvaluationContext.LOW_HP_SITUATION])
        elif role == CardRole.SETUP_SUPPORT:
            contexts.extend([EvaluationContext.EARLY_GAME, EvaluationContext.MID_GAME])
        
        # Situational timing
        if hasattr(card, 'is_basic') and card.is_basic:
            contexts.append(EvaluationContext.OPENING_HAND)
        
        if stats.retreat_efficiency > 0.7:
            contexts.append(EvaluationContext.LOW_HP_SITUATION)
        
        return list(set(contexts)) if contexts else [EvaluationContext.MID_GAME]
    
    def _identify_pokemon_traits(self, card, stats: PokemonStats, 
                               attacks: List[AttackAnalysis]) -> Tuple[List[str], List[str]]:
        """Identify key strengths and weaknesses"""
        strengths = []
        weaknesses = []
        
        # HP analysis
        if stats.hp_tier >= 4:
            strengths.append(f"High HP ({card.hp})")
        elif stats.hp_tier <= 2:
            weaknesses.append(f"Low HP ({card.hp})")
        
        # Attack efficiency
        if attacks:
            best_attack = max(attacks, key=lambda a: a.efficiency)
            if best_attack.efficiency >= 20:
                strengths.append(f"Efficient attacks ({best_attack.efficiency:.1f} dmg/energy)")
            elif best_attack.efficiency <= 12:
                weaknesses.append(f"Inefficient attacks ({best_attack.efficiency:.1f} dmg/energy)")
        
        # Energy requirements
        if stats.energy_requirement <= 1:
            strengths.append("Fast setup")
        elif stats.energy_requirement >= 4:
            weaknesses.append("Slow setup")
        
        # Retreat cost
        if stats.retreat_efficiency >= 0.75:
            strengths.append("Low retreat cost")
        elif stats.retreat_efficiency <= 0.25:
            weaknesses.append("High retreat cost")
        
        # Special abilities
        if stats.status_utility > 0.3:
            strengths.append("Useful special effects")
        
        # Evolution potential
        if stats.evolution_potential > 0.2:
            strengths.append("Evolution potential")
        
        return strengths, weaknesses
    
    # Trainer card evaluation methods (simplified for now)
    def _get_trainer_type(self, card) -> str:
        """Determine trainer card type"""
        card_type = card.card_type.lower()
        if 'supporter' in card_type:
            return 'supporter'
        elif 'item' in card_type:
            return 'item'
        elif 'tool' in card_type:
            return 'tool'
        return 'unknown'
    
    def _analyze_trainer_effects(self, card) -> List[str]:
        """Analyze trainer card effects"""
        effects = []
        # This would be expanded with full trainer effect analysis
        for ability in card.abilities or []:
            effect_text = ability.get('effect_text', '').lower()
            if 'draw' in effect_text:
                effects.append('card_draw')
            if 'search' in effect_text:
                effects.append('deck_search')
            if 'heal' in effect_text:
                effects.append('healing')
        return effects
    
    def _calculate_trainer_base_value(self, card, trainer_type: str, effects: List[str]) -> float:
        """Calculate trainer card base value (simplified)"""
        base_value = 30  # Base trainer value
        
        # Add value for each effect type
        for effect in effects:
            if effect == 'card_draw':
                base_value += 25
            elif effect == 'deck_search':
                base_value += 20
            elif effect == 'healing':
                base_value += 15
        
        return min(100, base_value)
    
    def _calculate_trainer_situational_value(self, card, effects: List[str], 
                                          context: EvaluationContext) -> float:
        """Calculate trainer situational value (simplified)"""
        return 0.0  # Placeholder
    
    def _determine_trainer_role(self, trainer_type: str, effects: List[str]) -> CardRole:
        """Determine trainer role (simplified)"""
        return CardRole.UTILITY
    
    def _recommend_trainer_timing(self, effects: List[str], 
                                context: EvaluationContext) -> List[EvaluationContext]:
        """Recommend trainer timing (simplified)"""
        return [EvaluationContext.MID_GAME]
    
    def _identify_trainer_traits(self, effects: List[str], 
                               trainer_type: str) -> Tuple[List[str], List[str]]:
        """Identify trainer strengths/weaknesses (simplified)"""
        return [f"Trainer effects: {', '.join(effects)}"], []
    
    def _create_fallback_evaluation(self, card) -> CardEvaluation:
        """Create fallback evaluation for error cases"""
        return CardEvaluation(
            card_id=card.id,
            card_name=card.name,
            base_value=50.0,
            situational_value=0.0,
            total_value=50.0,
            primary_role=CardRole.UTILITY,
            recommended_timing=[EvaluationContext.MID_GAME],
            key_strengths=["Unknown"],
            key_weaknesses=["Evaluation failed"]
        )