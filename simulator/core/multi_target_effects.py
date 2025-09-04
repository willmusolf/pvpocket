"""
Multi-Target Effects System for Pokemon TCG Pocket Battle Simulator

Handles attacks and abilities that can target multiple Pokemon simultaneously,
including bench damage, area healing, mass status effects, and selective targeting.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import random

# Import core components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TargetScope(Enum):
    """Scope of multi-target effects"""
    ALL_OPPONENT_POKEMON = "all_opponent"
    ALL_MY_POKEMON = "all_mine"
    ALL_POKEMON = "all_pokemon"
    OPPONENT_BENCH = "opponent_bench"
    MY_BENCH = "my_bench"
    ALL_BENCH = "all_bench"
    SELECTIVE_OPPONENT = "selective_opponent"
    SELECTIVE_MY = "selective_my"
    ACTIVE_AND_BENCH = "active_and_bench"


class EffectDistribution(Enum):
    """How effects are distributed among targets"""
    EQUAL_TO_ALL = "equal"        # Same effect to all targets
    SPLIT_TOTAL = "split"         # Split total effect among targets
    SELECTIVE_CHOOSE = "choose"   # Choose specific targets
    RANDOM_TARGETS = "random"     # Randomly select from available targets
    DIMINISHING = "diminishing"   # Reduced effect for each additional target


@dataclass
class TargetCriteria:
    """Criteria for selecting targets"""
    energy_type: Optional[str] = None      # Target specific energy types
    min_hp: Optional[int] = None           # Minimum HP to target
    max_hp: Optional[int] = None           # Maximum HP to target
    has_status: Optional[str] = None       # Must have specific status
    no_status: Optional[str] = None        # Must not have specific status
    evolution_stage: Optional[int] = None   # Target specific evolution stages
    has_energy: Optional[bool] = None       # Must have energy attached
    is_damaged: Optional[bool] = None       # Must be damaged/undamaged


@dataclass
class MultiTargetEffect:
    """Represents a multi-target effect"""
    effect_type: str  # "damage", "heal", "status", "energy_manipulation"
    scope: TargetScope
    distribution: EffectDistribution
    base_amount: int  # Base damage/healing amount
    
    # Targeting
    max_targets: Optional[int] = None      # Maximum number of targets
    target_criteria: Optional[TargetCriteria] = None
    
    # Effect parameters
    status_condition: Optional[str] = None  # For status effects
    energy_changes: Optional[Dict[str, int]] = None  # Energy manipulation
    special_parameters: Optional[Dict[str, Any]] = None
    
    # Randomization
    coin_flips: int = 0                    # Number of coin flips involved
    success_condition: Optional[str] = None # "all_heads", "any_heads", etc.


@dataclass
class TargetResult:
    """Result of applying effect to a single target"""
    target_pokemon: Any  # BattlePokemon
    target_location: str  # "active", "bench_0", "bench_1", etc.
    effect_applied: bool
    amount_applied: int  # Damage dealt, healing applied, etc.
    status_applied: Optional[str] = None
    details: str = ""


@dataclass
class MultiTargetResult:
    """Complete result of a multi-target effect"""
    success: bool
    total_targets: int
    successful_targets: int
    target_results: List[TargetResult]
    coin_flip_results: List[bool] = None
    description: str = ""


class MultiTargetEffectManager:
    """Manages multi-target effects execution and resolution"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Effect type handlers
        self.effect_handlers = {
            "damage": self._apply_damage_effect,
            "heal": self._apply_healing_effect,
            "status": self._apply_status_effect,
            "energy_manipulation": self._apply_energy_effect,
            "special": self._apply_special_effect
        }
        
        # Common multi-target effect patterns
        self.effect_patterns = self._build_effect_patterns()
        
        self.logger.debug("Multi-Target Effect Manager initialized")
    
    def _build_effect_patterns(self) -> Dict[str, MultiTargetEffect]:
        """Build common multi-target effect patterns"""
        patterns = {}
        
        # Bench damage attacks (common in TCG)
        patterns["bench_damage_20"] = MultiTargetEffect(
            effect_type="damage",
            scope=TargetScope.OPPONENT_BENCH,
            distribution=EffectDistribution.EQUAL_TO_ALL,
            base_amount=20,
            special_parameters={"ignore_weakness": True}
        )
        
        patterns["bench_damage_10"] = MultiTargetEffect(
            effect_type="damage",
            scope=TargetScope.OPPONENT_BENCH,
            distribution=EffectDistribution.EQUAL_TO_ALL,
            base_amount=10,
            special_parameters={"ignore_weakness": True}
        )
        
        # Area healing effects
        patterns["heal_all_mine"] = MultiTargetEffect(
            effect_type="heal",
            scope=TargetScope.ALL_MY_POKEMON,
            distribution=EffectDistribution.EQUAL_TO_ALL,
            base_amount=30
        )
        
        patterns["heal_bench"] = MultiTargetEffect(
            effect_type="heal",
            scope=TargetScope.MY_BENCH,
            distribution=EffectDistribution.EQUAL_TO_ALL,
            base_amount=20
        )
        
        # Mass status effects
        patterns["poison_all_opponent"] = MultiTargetEffect(
            effect_type="status",
            scope=TargetScope.ALL_OPPONENT_POKEMON,
            distribution=EffectDistribution.EQUAL_TO_ALL,
            base_amount=0,
            status_condition="poison"
        )
        
        patterns["burn_bench"] = MultiTargetEffect(
            effect_type="status",
            scope=TargetScope.OPPONENT_BENCH,
            distribution=EffectDistribution.EQUAL_TO_ALL,
            base_amount=0,
            status_condition="burn"
        )
        
        # Selective targeting (coin flip based)
        patterns["selective_bench_damage"] = MultiTargetEffect(
            effect_type="damage",
            scope=TargetScope.OPPONENT_BENCH,
            distribution=EffectDistribution.RANDOM_TARGETS,
            base_amount=30,
            coin_flips=3,
            success_condition="per_target",
            special_parameters={"one_flip_per_target": True}
        )
        
        # Energy manipulation
        patterns["energy_removal"] = MultiTargetEffect(
            effect_type="energy_manipulation",
            scope=TargetScope.ALL_OPPONENT_POKEMON,
            distribution=EffectDistribution.SELECTIVE_CHOOSE,
            base_amount=1,
            max_targets=2,
            energy_changes={"remove": 1}
        )
        
        return patterns
    
    def execute_multi_target_effect(self, 
                                   effect: MultiTargetEffect,
                                   source_pokemon,
                                   battle_context: Dict[str, Any]) -> MultiTargetResult:
        """
        Execute a multi-target effect
        
        Args:
            effect: MultiTargetEffect to execute
            source_pokemon: Pokemon using the effect
            battle_context: Current battle state context
            
        Returns:
            MultiTargetResult with complete execution details
        """
        try:
            # Get all potential targets
            potential_targets = self._get_potential_targets(effect.scope, source_pokemon, battle_context)
            
            if not potential_targets:
                return MultiTargetResult(
                    success=False,
                    total_targets=0,
                    successful_targets=0,
                    target_results=[],
                    description="No valid targets available"
                )
            
            # Apply targeting criteria
            filtered_targets = self._apply_target_criteria(potential_targets, effect.target_criteria)
            
            # Handle coin flips if required
            coin_results = []
            if effect.coin_flips > 0:
                coin_results = self._handle_coin_flips(effect, filtered_targets)
                
                # Filter targets based on coin flip results
                if effect.success_condition:
                    filtered_targets = self._filter_by_coin_results(
                        filtered_targets, coin_results, effect.success_condition
                    )
            
            # Limit number of targets
            final_targets = self._select_final_targets(filtered_targets, effect)
            
            if not final_targets:
                return MultiTargetResult(
                    success=False,
                    total_targets=0,
                    successful_targets=0,
                    target_results=[],
                    coin_flip_results=coin_results,
                    description="No targets remain after filtering"
                )
            
            # Calculate effect amounts per target
            target_amounts = self._calculate_target_amounts(final_targets, effect)
            
            # Apply effects to each target
            target_results = []
            successful_count = 0
            
            for i, (target_pokemon, location) in enumerate(final_targets):
                amount = target_amounts[i] if i < len(target_amounts) else effect.base_amount
                
                result = self._apply_effect_to_target(
                    effect, target_pokemon, location, amount, battle_context
                )
                
                target_results.append(result)
                if result.effect_applied:
                    successful_count += 1
            
            # Generate description
            description = self._generate_effect_description(effect, target_results, coin_results)
            
            return MultiTargetResult(
                success=successful_count > 0,
                total_targets=len(final_targets),
                successful_targets=successful_count,
                target_results=target_results,
                coin_flip_results=coin_results,
                description=description
            )
            
        except Exception as e:
            self.logger.error(f"Multi-target effect execution failed: {e}")
            return MultiTargetResult(
                success=False,
                total_targets=0,
                successful_targets=0,
                target_results=[],
                description=f"Effect execution failed: {e}"
            )
    
    def _get_potential_targets(self, scope: TargetScope, source_pokemon, 
                              battle_context: Dict[str, Any]) -> List[Tuple[Any, str]]:
        """Get all potential targets based on scope"""
        targets = []
        
        # Extract player information from battle context
        my_player = battle_context.get('attacker')
        opponent_player = battle_context.get('defender')
        
        if not my_player or not opponent_player:
            self.logger.warning("Missing player context for multi-target effect")
            return targets
        
        # Add targets based on scope
        if scope in [TargetScope.ALL_OPPONENT_POKEMON, TargetScope.OPPONENT_BENCH, 
                    TargetScope.SELECTIVE_OPPONENT, TargetScope.ACTIVE_AND_BENCH]:
            # Opponent's active Pokemon
            if scope != TargetScope.OPPONENT_BENCH and opponent_player.active_pokemon:
                targets.append((opponent_player.active_pokemon, "active"))
            
            # Opponent's bench
            if scope != TargetScope.ACTIVE_AND_BENCH or scope == TargetScope.OPPONENT_BENCH:
                for i, bench_pokemon in enumerate(opponent_player.bench):
                    if bench_pokemon and not bench_pokemon.is_knocked_out():
                        targets.append((bench_pokemon, f"bench_{i}"))
        
        if scope in [TargetScope.ALL_MY_POKEMON, TargetScope.MY_BENCH, TargetScope.SELECTIVE_MY]:
            # My active Pokemon
            if scope != TargetScope.MY_BENCH and my_player.active_pokemon:
                targets.append((my_player.active_pokemon, "active"))
            
            # My bench
            if scope != TargetScope.SELECTIVE_MY or scope == TargetScope.MY_BENCH:
                for i, bench_pokemon in enumerate(my_player.bench):
                    if bench_pokemon and not bench_pokemon.is_knocked_out():
                        targets.append((bench_pokemon, f"bench_{i}"))
        
        if scope in [TargetScope.ALL_POKEMON, TargetScope.ALL_BENCH]:
            # All Pokemon
            if scope == TargetScope.ALL_POKEMON:
                if my_player.active_pokemon:
                    targets.append((my_player.active_pokemon, "my_active"))
                if opponent_player.active_pokemon:
                    targets.append((opponent_player.active_pokemon, "opponent_active"))
            
            # All bench Pokemon
            for i, bench_pokemon in enumerate(my_player.bench):
                if bench_pokemon and not bench_pokemon.is_knocked_out():
                    targets.append((bench_pokemon, f"my_bench_{i}"))
            
            for i, bench_pokemon in enumerate(opponent_player.bench):
                if bench_pokemon and not bench_pokemon.is_knocked_out():
                    targets.append((bench_pokemon, f"opponent_bench_{i}"))
        
        return targets
    
    def _apply_target_criteria(self, targets: List[Tuple[Any, str]], 
                              criteria: Optional[TargetCriteria]) -> List[Tuple[Any, str]]:
        """Filter targets based on criteria"""
        if not criteria:
            return targets
        
        filtered = []
        
        for pokemon, location in targets:
            # Check energy type
            if criteria.energy_type and pokemon.card.energy_type != criteria.energy_type:
                continue
            
            # Check HP ranges
            if criteria.min_hp and pokemon.current_hp < criteria.min_hp:
                continue
            if criteria.max_hp and pokemon.current_hp > criteria.max_hp:
                continue
            
            # Check damage status
            if criteria.is_damaged is not None:
                is_damaged = pokemon.current_hp < pokemon.max_hp
                if criteria.is_damaged != is_damaged:
                    continue
            
            # Check energy attachment
            if criteria.has_energy is not None:
                has_energy = len(pokemon.energy_attached) > 0
                if criteria.has_energy != has_energy:
                    continue
            
            # Check status conditions
            if criteria.has_status:
                if not any(status.condition.value == criteria.has_status 
                          for status in getattr(pokemon, 'status_conditions', [])):
                    continue
            
            if criteria.no_status:
                if any(status.condition.value == criteria.no_status 
                      for status in getattr(pokemon, 'status_conditions', [])):
                    continue
            
            # Check evolution stage
            if criteria.evolution_stage is not None:
                card_stage = getattr(pokemon.card, 'evolution_stage', 0)
                if card_stage != criteria.evolution_stage:
                    continue
            
            filtered.append((pokemon, location))
        
        return filtered
    
    def _handle_coin_flips(self, effect: MultiTargetEffect, 
                          targets: List[Tuple[Any, str]]) -> List[bool]:
        """Handle coin flips for effects"""
        results = []
        
        if effect.special_parameters and effect.special_parameters.get('one_flip_per_target'):
            # One coin flip per target
            for _ in targets[:effect.coin_flips]:
                results.append(random.choice([True, False]))
        else:
            # Standard coin flips
            for _ in range(effect.coin_flips):
                results.append(random.choice([True, False]))
        
        return results
    
    def _filter_by_coin_results(self, targets: List[Tuple[Any, str]], 
                               coin_results: List[bool], 
                               success_condition: str) -> List[Tuple[Any, str]]:
        """Filter targets based on coin flip results"""
        if success_condition == "all_heads":
            if not all(coin_results):
                return []  # No targets if not all heads
        
        elif success_condition == "any_heads":
            if not any(coin_results):
                return []  # No targets if no heads
        
        elif success_condition == "per_target":
            # One coin per target, only successful flips get targeted
            filtered = []
            for i, (pokemon, location) in enumerate(targets):
                if i < len(coin_results) and coin_results[i]:
                    filtered.append((pokemon, location))
            return filtered
        
        return targets
    
    def _select_final_targets(self, targets: List[Tuple[Any, str]], 
                             effect: MultiTargetEffect) -> List[Tuple[Any, str]]:
        """Select final targets based on effect parameters"""
        if effect.max_targets and len(targets) > effect.max_targets:
            if effect.distribution == EffectDistribution.RANDOM_TARGETS:
                return random.sample(targets, effect.max_targets)
            else:
                return targets[:effect.max_targets]  # Take first N targets
        
        return targets
    
    def _calculate_target_amounts(self, targets: List[Tuple[Any, str]], 
                                 effect: MultiTargetEffect) -> List[int]:
        """Calculate effect amount for each target"""
        amounts = []
        
        if effect.distribution == EffectDistribution.EQUAL_TO_ALL:
            amounts = [effect.base_amount] * len(targets)
        
        elif effect.distribution == EffectDistribution.SPLIT_TOTAL:
            if targets:
                amount_per_target = effect.base_amount // len(targets)
                amounts = [amount_per_target] * len(targets)
        
        elif effect.distribution == EffectDistribution.DIMINISHING:
            for i in range(len(targets)):
                # Reduce by 10% for each additional target
                multiplier = max(0.1, 1.0 - (i * 0.1))
                amounts.append(int(effect.base_amount * multiplier))
        
        else:
            # Default to equal amounts
            amounts = [effect.base_amount] * len(targets)
        
        return amounts
    
    def _apply_effect_to_target(self, effect: MultiTargetEffect, target_pokemon, 
                               location: str, amount: int, 
                               battle_context: Dict[str, Any]) -> TargetResult:
        """Apply effect to a single target"""
        handler = self.effect_handlers.get(effect.effect_type)
        if not handler:
            return TargetResult(
                target_pokemon=target_pokemon,
                target_location=location,
                effect_applied=False,
                amount_applied=0,
                details=f"Unknown effect type: {effect.effect_type}"
            )
        
        return handler(effect, target_pokemon, location, amount, battle_context)
    
    def _apply_damage_effect(self, effect: MultiTargetEffect, target_pokemon, 
                            location: str, amount: int, 
                            battle_context: Dict[str, Any]) -> TargetResult:
        """Apply damage effect to target"""
        try:
            # Check for special damage rules
            ignore_weakness = (effect.special_parameters and 
                             effect.special_parameters.get('ignore_weakness', False))
            
            actual_damage = amount
            if not ignore_weakness:
                # Apply weakness (simplified)
                source_pokemon = battle_context.get('source_pokemon')
                if (source_pokemon and target_pokemon.card.weakness and 
                    source_pokemon.card.energy_type == target_pokemon.card.weakness):
                    actual_damage += 20  # Standard weakness bonus
            
            damage_dealt = target_pokemon.take_damage(actual_damage)
            
            return TargetResult(
                target_pokemon=target_pokemon,
                target_location=location,
                effect_applied=damage_dealt > 0,
                amount_applied=damage_dealt,
                details=f"{damage_dealt} damage dealt"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to apply damage to {target_pokemon.card.name}: {e}")
            return TargetResult(
                target_pokemon=target_pokemon,
                target_location=location,
                effect_applied=False,
                amount_applied=0,
                details=f"Damage application failed: {e}"
            )
    
    def _apply_healing_effect(self, effect: MultiTargetEffect, target_pokemon, 
                             location: str, amount: int, 
                             battle_context: Dict[str, Any]) -> TargetResult:
        """Apply healing effect to target"""
        try:
            healed_amount = target_pokemon.heal(amount)
            
            return TargetResult(
                target_pokemon=target_pokemon,
                target_location=location,
                effect_applied=healed_amount > 0,
                amount_applied=healed_amount,
                details=f"{healed_amount} HP healed"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to heal {target_pokemon.card.name}: {e}")
            return TargetResult(
                target_pokemon=target_pokemon,
                target_location=location,
                effect_applied=False,
                amount_applied=0,
                details=f"Healing failed: {e}"
            )
    
    def _apply_status_effect(self, effect: MultiTargetEffect, target_pokemon, 
                            location: str, amount: int, 
                            battle_context: Dict[str, Any]) -> TargetResult:
        """Apply status effect to target"""
        try:
            status_condition = effect.status_condition
            if not status_condition:
                return TargetResult(
                    target_pokemon=target_pokemon,
                    target_location=location,
                    effect_applied=False,
                    amount_applied=0,
                    details="No status condition specified"
                )
            
            success = target_pokemon.apply_status_effect(status_condition)
            
            return TargetResult(
                target_pokemon=target_pokemon,
                target_location=location,
                effect_applied=success,
                amount_applied=1 if success else 0,
                status_applied=status_condition if success else None,
                details=f"{status_condition} applied" if success else f"{status_condition} failed"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to apply status to {target_pokemon.card.name}: {e}")
            return TargetResult(
                target_pokemon=target_pokemon,
                target_location=location,
                effect_applied=False,
                amount_applied=0,
                details=f"Status application failed: {e}"
            )
    
    def _apply_energy_effect(self, effect: MultiTargetEffect, target_pokemon, 
                            location: str, amount: int, 
                            battle_context: Dict[str, Any]) -> TargetResult:
        """Apply energy manipulation effect to target"""
        try:
            energy_changes = effect.energy_changes or {}
            
            if 'remove' in energy_changes:
                remove_count = energy_changes['remove']
                removed_energy = []
                for _ in range(min(remove_count, len(target_pokemon.energy_attached))):
                    if target_pokemon.energy_attached:
                        removed = target_pokemon.remove_energy()
                        if removed:
                            removed_energy.append(removed)
                
                return TargetResult(
                    target_pokemon=target_pokemon,
                    target_location=location,
                    effect_applied=len(removed_energy) > 0,
                    amount_applied=len(removed_energy),
                    details=f"Removed {len(removed_energy)} energy"
                )
            
            elif 'add' in energy_changes:
                add_count = energy_changes['add']
                energy_type = energy_changes.get('energy_type', 'Fire')  # Default to Fire, not Colorless
                
                for _ in range(add_count):
                    target_pokemon.attach_energy(energy_type)
                
                return TargetResult(
                    target_pokemon=target_pokemon,
                    target_location=location,
                    effect_applied=True,
                    amount_applied=add_count,
                    details=f"Added {add_count} {energy_type} energy"
                )
            
            return TargetResult(
                target_pokemon=target_pokemon,
                target_location=location,
                effect_applied=False,
                amount_applied=0,
                details="No energy changes specified"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to manipulate energy for {target_pokemon.card.name}: {e}")
            return TargetResult(
                target_pokemon=target_pokemon,
                target_location=location,
                effect_applied=False,
                amount_applied=0,
                details=f"Energy manipulation failed: {e}"
            )
    
    def _apply_special_effect(self, effect: MultiTargetEffect, target_pokemon, 
                             location: str, amount: int, 
                             battle_context: Dict[str, Any]) -> TargetResult:
        """Apply special effect to target (placeholder)"""
        return TargetResult(
            target_pokemon=target_pokemon,
            target_location=location,
            effect_applied=True,
            amount_applied=amount,
            details="Special effect applied"
        )
    
    def _generate_effect_description(self, effect: MultiTargetEffect, 
                                    results: List[TargetResult],
                                    coin_results: List[bool]) -> str:
        """Generate human-readable description of effect results"""
        if not results:
            return "No targets affected"
        
        successful = [r for r in results if r.effect_applied]
        
        if effect.effect_type == "damage":
            total_damage = sum(r.amount_applied for r in successful)
            return f"Multi-target attack: {len(successful)} Pokemon took {total_damage} total damage"
        
        elif effect.effect_type == "heal":
            total_healed = sum(r.amount_applied for r in successful)
            return f"Area heal: {len(successful)} Pokemon healed {total_healed} total HP"
        
        elif effect.effect_type == "status":
            status_name = effect.status_condition or "status"
            return f"Mass {status_name}: {len(successful)} Pokemon affected"
        
        elif effect.effect_type == "energy_manipulation":
            return f"Energy manipulation: {len(successful)} Pokemon affected"
        
        return f"Multi-target effect: {len(successful)}/{len(results)} targets affected"
    
    def parse_multi_target_from_text(self, effect_text: str) -> Optional[MultiTargetEffect]:
        """Parse multi-target effect from attack/ability text"""
        text_lower = effect_text.lower()
        
        # Bench damage patterns
        if 'bench' in text_lower and 'damage' in text_lower:
            import re
            damage_match = re.search(r'(\d+)\s*damage.*bench', text_lower)
            if damage_match:
                damage_amount = int(damage_match.group(1))
                
                if 'opponent' in text_lower or 'defending' in text_lower:
                    scope = TargetScope.OPPONENT_BENCH
                else:
                    scope = TargetScope.ALL_BENCH
                
                return MultiTargetEffect(
                    effect_type="damage",
                    scope=scope,
                    distribution=EffectDistribution.EQUAL_TO_ALL,
                    base_amount=damage_amount,
                    special_parameters={"ignore_weakness": True}
                )
        
        # Heal all patterns
        if 'heal' in text_lower and ('all' in text_lower or 'each' in text_lower):
            heal_match = re.search(r'heal\s*(\d+)', text_lower)
            if heal_match:
                heal_amount = int(heal_match.group(1))
                
                scope = TargetScope.ALL_MY_POKEMON
                if 'opponent' in text_lower:
                    scope = TargetScope.ALL_OPPONENT_POKEMON
                elif 'bench' in text_lower:
                    scope = TargetScope.MY_BENCH
                
                return MultiTargetEffect(
                    effect_type="heal",
                    scope=scope,
                    distribution=EffectDistribution.EQUAL_TO_ALL,
                    base_amount=heal_amount
                )
        
        # Mass status effects
        for status in ['poison', 'burn', 'paralyze', 'sleep', 'confus']:
            if status in text_lower and ('all' in text_lower or 'each' in text_lower):
                scope = TargetScope.ALL_OPPONENT_POKEMON
                if 'bench' in text_lower:
                    scope = TargetScope.OPPONENT_BENCH
                
                return MultiTargetEffect(
                    effect_type="status",
                    scope=scope,
                    distribution=EffectDistribution.EQUAL_TO_ALL,
                    base_amount=0,
                    status_condition=status.replace('confus', 'confusion')
                )
        
        return None
    
    def get_pattern_effect(self, pattern_name: str) -> Optional[MultiTargetEffect]:
        """Get a predefined effect pattern"""
        return self.effect_patterns.get(pattern_name)