"""
Advanced Effect Engine for Pokemon TCG Pocket Battle Simulator
Coordinates all effect systems: status conditions, coin flips, evolution, trainers, etc.
"""

from typing import Dict, List, Optional, Tuple, Any, Union
import logging
from dataclasses import dataclass
from enum import Enum

# Import all our effect systems
from simulator.core.status_conditions import StatusManager, StatusCondition
from simulator.core.coin_flip import CoinFlipManager, parse_coin_flip_effect, execute_coin_flip_effect
from simulator.core.trainer_cards import TrainerCardManager, TrainerType
from simulator.core.evolution import EvolutionManager
from simulator.core.card_bridge import BattleCard
from simulator.core.mass_effect_parser import MassEffectParser, EffectPattern, EffectParseResult
from simulator.core.effect_registry import effect_registry, EffectContext, EffectResult


class EffectTiming(Enum):
    """When effects are triggered"""
    BEFORE_ATTACK = "before_attack"
    DURING_ATTACK = "during_attack" 
    AFTER_ATTACK = "after_attack"
    BETWEEN_TURNS = "between_turns"
    ON_PLAY = "on_play"
    ON_EVOLUTION = "on_evolution"
    ON_KNOCKOUT = "on_knockout"
    PASSIVE = "passive"


class EffectScope(Enum):
    """What the effect targets"""
    SELF = "self"
    OPPONENT = "opponent"
    ACTIVE_POKEMON = "active_pokemon"
    BENCH_POKEMON = "bench_pokemon"
    ALL_POKEMON = "all_pokemon"
    FIELD = "field"


@dataclass
class BattleEffect:
    """A unified battle effect"""
    effect_id: str
    effect_type: str  # "damage", "status", "coin_flip", "trainer", etc.
    timing: EffectTiming
    scope: EffectScope
    parameters: Dict[str, Any]
    source_card: Optional[BattleCard] = None
    description: str = ""
    
    def __post_init__(self):
        if not self.description:
            self.description = f"{self.effect_type} effect from {self.source_card.name if self.source_card else 'unknown'}"


class AdvancedEffectEngine:
    """Coordinates all effect systems for complex card interactions"""
    
    def __init__(self, battle_cards: List[BattleCard], logger: Optional[logging.Logger] = None, rng_seed: Optional[int] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize all subsystems
        self.status_manager = StatusManager(logger)
        self.coin_manager = CoinFlipManager(logger, rng_seed)
        self.trainer_manager = TrainerCardManager(logger)
        self.evolution_manager = EvolutionManager(battle_cards, logger)
        
        # Initialize mass effect parser
        self.mass_parser = MassEffectParser(logger)
        
        # Effect registry for quick lookup
        self.registered_effects = {}
        self.passive_effects = []
        
        # Battle state tracking
        self.current_turn = 0
        self.current_player = 0
        
    def register_card_effects(self, card: BattleCard) -> List[BattleEffect]:
        """Register all effects from a card"""
        effects = []
        
        # Parse attacks for effects
        for attack in card.attacks or []:
            attack_effects = self._parse_attack_effects(attack, card)
            effects.extend(attack_effects)
        
        # Parse abilities for effects
        for ability in card.abilities or []:
            ability_effects = self._parse_ability_effects(ability, card)
            effects.extend(ability_effects)
        
        # Store effects
        self.registered_effects[card.id] = effects
        
        # Track passive effects
        for effect in effects:
            if effect.timing == EffectTiming.PASSIVE:
                self.passive_effects.append(effect)
        
        self.logger.debug(f"Registered {len(effects)} effects for {card.name}")
        return effects
    
    def _parse_attack_effects(self, attack: Dict, card: BattleCard) -> List[BattleEffect]:
        """Parse effects from an attack"""
        effects = []
        effect_text = attack.get('effect_text', '')
        
        if not effect_text:
            return effects
        
        # Check for coin flip effects
        coin_effect = parse_coin_flip_effect(effect_text)
        if coin_effect:
            effects.append(BattleEffect(
                effect_id=f"{card.id}_{attack['name']}_coin",
                effect_type="coin_flip",
                timing=EffectTiming.DURING_ATTACK,
                scope=EffectScope.SELF,
                parameters=coin_effect,
                source_card=card,
                description=f"Coin flip effect from {attack['name']}"
            ))
        
        # Check for status condition effects
        status_effects = self._parse_status_effects(effect_text)
        for status_effect in status_effects:
            effects.append(BattleEffect(
                effect_id=f"{card.id}_{attack['name']}_status",
                effect_type="status_condition",
                timing=EffectTiming.AFTER_ATTACK,
                scope=EffectScope.OPPONENT,
                parameters=status_effect,
                source_card=card,
                description=f"Status effect from {attack['name']}"
            ))
        
        # Check for damage modification effects
        damage_effects = self._parse_damage_effects(effect_text)
        for damage_effect in damage_effects:
            effects.append(BattleEffect(
                effect_id=f"{card.id}_{attack['name']}_damage",
                effect_type="damage_modification",
                timing=EffectTiming.DURING_ATTACK,
                scope=EffectScope.OPPONENT,
                parameters=damage_effect,
                source_card=card,
                description=f"Damage effect from {attack['name']}"
            ))
        
        # Check for energy effects
        energy_effects = self._parse_energy_effects(effect_text)
        for energy_effect in energy_effects:
            effects.append(BattleEffect(
                effect_id=f"{card.id}_{attack['name']}_energy",
                effect_type="energy_manipulation",
                timing=EffectTiming.AFTER_ATTACK,
                scope=EffectScope.SELF,
                parameters=energy_effect,
                source_card=card,
                description=f"Energy effect from {attack['name']}"
            ))
        
        # Check for healing effects
        healing_effects = self._parse_healing_effects(effect_text)
        for healing_effect in healing_effects:
            effects.append(BattleEffect(
                effect_id=f"{card.id}_{attack['name']}_heal",
                effect_type="healing",
                timing=EffectTiming.AFTER_ATTACK,
                scope=EffectScope.SELF,
                parameters=healing_effect,
                source_card=card,
                description=f"Healing effect from {attack['name']}"
            ))
        
        return effects
    
    def _parse_ability_effects(self, ability: Dict, card: BattleCard) -> List[BattleEffect]:
        """Parse effects from an ability"""
        effects = []
        effect_text = ability.get('effect_text', '')
        
        if not effect_text:
            return effects
        
        # Determine ability timing
        timing = self._determine_ability_timing(effect_text)
        
        # Parse various effect types
        # This is where we'd add specific ability parsing logic
        # For now, create a generic ability effect
        effects.append(BattleEffect(
            effect_id=f"{card.id}_{ability['name']}_ability",
            effect_type="ability",
            timing=timing,
            scope=EffectScope.SELF,
            parameters={'text': effect_text},
            source_card=card,
            description=f"Ability: {ability['name']}"
        ))
        
        return effects
    
    def _determine_ability_timing(self, effect_text: str) -> EffectTiming:
        """Determine when an ability triggers"""
        text_lower = effect_text.lower()
        
        if 'when you play' in text_lower or 'when this pokémon' in text_lower:
            return EffectTiming.ON_PLAY
        elif 'once during your turn' in text_lower:
            return EffectTiming.ON_PLAY  # Player-activated
        elif 'between turns' in text_lower:
            return EffectTiming.BETWEEN_TURNS
        elif 'when' in text_lower and 'attack' in text_lower:
            return EffectTiming.BEFORE_ATTACK
        else:
            return EffectTiming.PASSIVE
    
    def _parse_status_effects(self, effect_text: str) -> List[Dict]:
        """Parse status condition effects from text"""
        effects = []
        text_lower = effect_text.lower()
        
        # Map status conditions
        status_mapping = {
            'burned': StatusCondition.BURNED,
            'poisoned': StatusCondition.POISONED,
            'asleep': StatusCondition.ASLEEP,
            'paralyzed': StatusCondition.PARALYZED,
            'confused': StatusCondition.CONFUSED,
        }
        
        for status_text, status_condition in status_mapping.items():
            if status_text in text_lower:
                effects.append({
                    'condition': status_condition,
                    'target': 'opponent'
                })
        
        # Special case: random status condition (like Alolan Muk ex Chemical Panic)
        if ('random' in text_lower and 'special condition' in text_lower) or \
           ('chosen at random' in text_lower and any(status in text_lower for status in ['asleep', 'burned', 'confused', 'paralyzed', 'poisoned'])):
            effects.append({
                'type': 'random_status',
                'target': 'opponent'
            })
        
        return effects
    
    def _parse_damage_effects(self, effect_text: str) -> List[Dict]:
        """Parse damage modification effects"""
        effects = []
        text_lower = effect_text.lower()
        
        import re
        
        # Bench-based damage scaling (like Wishiwashi ex School Storm)
        # Pattern: "This attack does X more damage for each of your Benched [specific Pokemon]"
        bench_scaling_pattern = r'(\d+) more damage for each of your benched (.*?)(?:\.|$)'
        match = re.search(bench_scaling_pattern, text_lower)
        if match:
            damage_per_pokemon = int(match.group(1))
            bench_criteria = match.group(2).strip()
            effects.append({
                'type': 'bench_scaling_damage',
                'damage_per_pokemon': damage_per_pokemon,
                'bench_criteria': bench_criteria,  # e.g., "wishiwashi or wishiwashi ex"
                'target': 'own_bench'
            })

        # Energy-based damage scaling (like Alolan Raichu ex)
        # Pattern: "This attack does X more damage for each Energy attached to your opponent's Active Pokémon"
        energy_scaling_pattern = r'(\d+) more damage for each energy attached to.*?opponent'
        match = re.search(energy_scaling_pattern, text_lower)
        if match:
            effects.append({
                'type': 'energy_scaling_damage',
                'damage_per_energy': int(match.group(1)),
                'target': 'opponent_active'
            })
        
        # Basic Pokemon conditional damage (like Araquanid)
        # Pattern: "If your opponent's Active Pokémon is a Basic Pokemon, this attack does X more damage"
        basic_pokemon_pattern = r'if.*?opponent.*?basic.*?(\d+) more damage'
        match = re.search(basic_pokemon_pattern, text_lower)
        if match:
            effects.append({
                'type': 'conditional_damage',
                'condition': 'opponent_is_basic',
                'bonus': int(match.group(1))
            })
        
        # Special condition damage bonuses (like Absol)
        # Pattern: "If your opponent's Active Pokémon is affected by a Special Condition, this attack does X more damage"
        special_condition_pattern = r'if.*?special condition.*?(\d+) more damage'
        match = re.search(special_condition_pattern, text_lower)
        if match:
            effects.append({
                'type': 'conditional_damage',
                'condition': 'special_condition',
                'bonus': int(match.group(1))
            })
        
        # Fixed damage bonuses (fallback) - only if no other specific damage effect was found
        damage_bonus_pattern = r'(\d+) more damage'
        match = re.search(damage_bonus_pattern, text_lower)
        if match and not any(effect.get('type') in ['conditional_damage', 'energy_scaling_damage', 'bench_scaling_damage'] for effect in effects):
            effects.append({
                'type': 'damage_bonus',
                'amount': int(match.group(1))
            })
        
        return effects
    
    def _parse_energy_effects(self, effect_text: str) -> List[Dict]:
        """Parse energy manipulation effects"""
        effects = []
        text_lower = effect_text.lower()
        
        import re
        
        # Energy acceleration (like Alolan Vulpix Call Forth Cold)
        # Pattern: "Take a [W] Energy from your Energy Zone and attach it to this Pokémon"
        energy_acceleration_pattern = r'take.*?\[([rwglpfdmc])\].*?energy.*?attach.*?to.*?this'
        match = re.search(energy_acceleration_pattern, text_lower)
        if match:
            energy_symbol = match.group(1).upper()
            energy_type_map = {
                'R': 'Fire', 'W': 'Water', 'G': 'Grass', 'L': 'Lightning',
                'P': 'Psychic', 'F': 'Fighting', 'D': 'Darkness', 'M': 'Metal'
                # Note: 'C' (Colorless) is NOT an energy type - it's a cost requirement meaning "any energy"
            }
            energy_type = energy_type_map.get(energy_symbol, 'Fire')  # Default to Fire, never Colorless
            
            effects.append({
                'type': 'attach_energy_from_zone',
                'energy_type': energy_type,
                'amount': 1,
                'target': 'self'
            })
        
        # Energy discard
        discard_pattern = r'discard (\d+) .*?energy'
        match = re.search(discard_pattern, text_lower)
        if match:
            effects.append({
                'type': 'discard_energy',
                'amount': int(match.group(1)),
                'target': 'self'
            })
        
        # Generic energy attachment (fallback) - but only if not a coin flip effect
        elif 'attach' in text_lower and 'energy' in text_lower and 'flip' not in text_lower:
            effects.append({
                'type': 'attach_energy',
                'target': 'self'
            })
        
        return effects
    
    def _parse_healing_effects(self, effect_text: str) -> List[Dict]:
        """Parse healing effects from text"""
        effects = []
        text_lower = effect_text.lower()
        
        import re
        
        # Pattern: "Heal 20 damage from this Pokémon" or "Recover 50 HP"
        heal_pattern = r'heal (\d+) damage|recover (\d+) hp|heal (\d+) hp'
        match = re.search(heal_pattern, text_lower)
        if match:
            # Extract the healing amount from whichever group matched
            heal_amount = int(match.group(1) or match.group(2) or match.group(3))
            effects.append({
                'type': 'heal',
                'amount': heal_amount,
                'target': 'self'  # Most healing effects target self
            })
        
        # Pattern: "Heal all damage from this Pokémon" or "Fully heal this Pokémon"
        full_heal_pattern = r'heal all damage|fully heal|remove all damage'
        if re.search(full_heal_pattern, text_lower):
            effects.append({
                'type': 'full_heal',
                'target': 'self'
            })
        
        # Pattern: "Each of your Pokémon recovers 20 HP" (heal all Pokemon)
        heal_all_pattern = r'each of your.*?recover.*?(\d+)|all.*?your.*?heal.*?(\d+)'
        match_all = re.search(heal_all_pattern, text_lower)
        if match_all:
            heal_amount = int(match_all.group(1) or match_all.group(2))
            effects.append({
                'type': 'heal_all',
                'amount': heal_amount,
                'target': 'all_own'
            })
        
        return effects
    
    def execute_attack_effects(self, attack: Dict, attacking_pokemon, defending_pokemon, 
                             base_damage: int, battle_context: Dict) -> Dict:
        """Execute all effects from an attack using priority-based parsing"""
        result = {
            'final_damage': base_damage,
            'status_effects': [],
            'energy_changes': [],
            'coin_results': [],
            'additional_effects': []
        }
        
        effect_text = attack.get('effect_text', '') or attack.get('effect', '')
        if not effect_text:
            return result
        
        # PRIORITY-BASED EFFECT PARSING SYSTEM
        # Parse all effects first, then sort by priority before execution
        
        all_effects = []
        
        # Priority 1 (Highest): Specific coin flip effects with energy generation
        coin_effect = parse_coin_flip_effect(effect_text)
        if coin_effect:
            all_effects.append({
                'priority': 1,
                'type': 'coin_flip',
                'effect_data': coin_effect,
                'description': 'Coin flip effect (highest priority)'
            })
        
        # Priority 2: Status conditions 
        status_effects = self._parse_status_effects(effect_text)
        for status_effect in status_effects:
            all_effects.append({
                'priority': 2,
                'type': 'status',
                'effect_data': status_effect,
                'description': 'Status condition effect'
            })
        
        # Priority 3: Damage modifications 
        damage_effects = self._parse_damage_effects(effect_text)
        for damage_effect in damage_effects:
            all_effects.append({
                'priority': 3,
                'type': 'damage',
                'effect_data': damage_effect,
                'description': 'Damage modification effect'
            })
        
        # Priority 4: Healing effects
        healing_effects = self._parse_healing_effects(effect_text)
        for healing_effect in healing_effects:
            all_effects.append({
                'priority': 4,
                'type': 'healing',
                'effect_data': healing_effect,
                'description': 'Healing effect'
            })
        
        # Priority 5 (Lowest): Generic energy effects (only if no coin flip energy generation)
        if not coin_effect or not any('energy_generated' in str(coin_effect).lower() for _ in [coin_effect]):
            energy_effects = self._parse_energy_effects(effect_text)
            for energy_effect in energy_effects:
                all_effects.append({
                    'priority': 5,
                    'type': 'energy',
                    'effect_data': energy_effect,
                    'description': 'Generic energy effect (lowest priority)'
                })
        
        # Sort effects by priority (lower number = higher priority)
        all_effects.sort(key=lambda x: x['priority'])
        
        self.logger.debug(f"Processing {len(all_effects)} effects in priority order: {[e['description'] for e in all_effects]}")
        
        # Execute effects in priority order
        for effect in all_effects:
            effect_type = effect['type']
            effect_data = effect['effect_data']
            
            if effect_type == 'coin_flip':
                coin_result = execute_coin_flip_effect(effect_data, self.coin_manager, result['final_damage'], battle_context)
                result['final_damage'] = coin_result['total_damage']
                result['coin_results'] = coin_result['coin_results']
                result['additional_effects'].append(coin_result['description'])
                
                # Handle energy generation from coin flips (like Moltres ex Inferno Dance)
                if 'energy_generated' in coin_result and coin_result['energy_generated'] > 0:
                    energy_type = coin_result.get('energy_type', 'Fire')
                    distribution_target = coin_result.get('distribution_target', 'active')
                    requires_distribution = coin_result.get('requires_distribution', False)
                    
                    if requires_distribution and distribution_target == 'bench':
                        # For Moltres-style effects that distribute to bench Pokemon
                        result['energy_changes'].append({
                            'type': 'distribute_to_bench',
                            'energy_type': energy_type,
                            'amount': coin_result['energy_generated'],
                            'target_filter': energy_type.lower(),  # Only Fire Pokemon for Moltres
                            'requires_ai_choice': True
                        })
                        result['additional_effects'].append(f"Generated {coin_result['energy_generated']} {energy_type} energy to distribute to bench")
                    else:
                        # Simple energy attachment to active Pokemon
                        result['energy_changes'].append({
                            'type': 'attach',
                            'target': distribution_target,
                            'energy_type': energy_type,
                            'amount': coin_result['energy_generated']
                        })
                        result['additional_effects'].append(f"Generated {coin_result['energy_generated']} {energy_type} energy")
            
            elif effect_type == 'status':
                if effect_data.get('type') == 'random_status':
                    success, message = self.status_manager.apply_random_status_condition(
                        defending_pokemon, self.current_turn
                    )
                    if success:
                        result['status_effects'].append(message)
                elif 'condition' in effect_data:
                    success, message = self.status_manager.apply_status_condition(
                        defending_pokemon, effect_data['condition'], self.current_turn
                    )
                    if success:
                        result['status_effects'].append(message)
            
            elif effect_type == 'damage':
                if effect_data.get('type') == 'bench_scaling_damage':
                    # Bench-based damage scaling (like Wishiwashi ex School Storm)
                    damage_per_pokemon = effect_data.get('damage_per_pokemon', 0)
                    bench_criteria = effect_data.get('bench_criteria', '').lower()
                    target = effect_data.get('target', 'own_bench')
                    
                    if target == 'own_bench' and battle_context and battle_context.get('attacker'):
                        attacker = battle_context['attacker']
                        bench_count = 0
                        
                        # Count bench Pokemon that match the criteria
                        if hasattr(attacker, 'bench'):
                            for bench_pokemon in attacker.bench:
                                if bench_pokemon and hasattr(bench_pokemon, 'card'):
                                    pokemon_name = bench_pokemon.card.name.lower()
                                    # Check if this bench Pokemon matches the criteria
                                    # For "wishiwashi or wishiwashi ex", check if name contains either
                                    criteria_parts = bench_criteria.split(' or ')
                                    for part in criteria_parts:
                                        part = part.strip()
                                        if part in pokemon_name:
                                            bench_count += 1
                                            break
                        
                        bonus_damage = bench_count * damage_per_pokemon
                        result['final_damage'] += bonus_damage
                        result['additional_effects'].append(f"Bench scaling: +{bonus_damage} damage ({bench_count} matching bench Pokemon × {damage_per_pokemon})")
                        
                elif effect_data.get('type') == 'energy_scaling_damage':
                    # Energy-based damage scaling (like Alolan Raichu ex)
                    damage_per_energy = effect_data.get('damage_per_energy', 0)
                    target = effect_data.get('target', 'opponent_active')
                    
                    if target == 'opponent_active' and defending_pokemon:
                        energy_count = len(defending_pokemon.energy_attached)
                        bonus_damage = energy_count * damage_per_energy
                        result['final_damage'] += bonus_damage
                        result['additional_effects'].append(f"Energy scaling: +{bonus_damage} damage ({energy_count} energy × {damage_per_energy})")
                        
                elif effect_data.get('type') == 'conditional_damage':
                    condition = effect_data.get('condition')
                    bonus = effect_data.get('bonus', 0)
                    
                    condition_met = False
                    condition_description = ""
                    
                    if condition == 'special_condition':
                        condition_met = self.status_manager.has_any_status_condition(defending_pokemon)
                        condition_description = "special condition"
                        
                    elif condition == 'opponent_is_basic':
                        # Check if defending Pokemon is Basic
                        if defending_pokemon and hasattr(defending_pokemon.card, 'card_type'):
                            condition_met = 'basic' in defending_pokemon.card.card_type.lower()
                            condition_description = "basic Pokemon"
                    
                    if condition_met:
                        result['final_damage'] += bonus
                        result['additional_effects'].append(f"Conditional bonus ({condition_description}): +{bonus} damage")
                        
                elif effect_data.get('type') == 'damage_bonus':
                    # Fixed damage bonus
                    bonus = effect_data.get('amount', 0)
                    result['final_damage'] += bonus
                    result['additional_effects'].append(f"Damage bonus: +{bonus} damage")
            
            elif effect_type == 'healing':
                healing_type = effect_data.get('type')
                target = effect_data.get('target', 'self')
                
                if healing_type == 'heal':
                    heal_amount = effect_data.get('amount', 0)
                    if target == 'self':
                        old_hp = attacking_pokemon.current_hp
                        attacking_pokemon.heal(heal_amount)
                        actual_healed = attacking_pokemon.current_hp - old_hp
                        result['additional_effects'].append(f"Healed {actual_healed} damage from {attacking_pokemon.card.name}")
                        
                elif healing_type == 'full_heal':
                    if target == 'self':
                        old_hp = attacking_pokemon.current_hp
                        attacking_pokemon.current_hp = attacking_pokemon.card.hp
                        actual_healed = attacking_pokemon.current_hp - old_hp
                        result['additional_effects'].append(f"Fully healed {attacking_pokemon.card.name} ({actual_healed} damage removed)")
            
            elif effect_type == 'energy':
                if effect_data.get('type') == 'attach_energy_from_zone':
                    # Energy acceleration (like Alolan Vulpix)
                    energy_type = effect_data.get('energy_type', 'Fire')  # Default to Fire, not Colorless
                    amount = effect_data.get('amount', 1)
                    target = effect_data.get('target', 'self')
                    
                    result['energy_changes'].append({
                        'type': 'attach',
                        'target': 'active' if target == 'self' else target,
                        'energy_type': energy_type,
                        'amount': amount
                    })
                    result['additional_effects'].append(f"Energy acceleration: Attached {amount}x {energy_type} from Energy Zone")
                    
                elif effect_data.get('type') == 'discard_energy':
                    amount = effect_data.get('amount', 0)
                    energy_type = effect_data.get('energy_type', 'any')  # Allow any energy type to be discarded
                    result['energy_changes'].append({
                        'type': 'remove',
                        'target': 'active',
                        'amount': amount,
                        'energy_type': energy_type
                    })
                    result['additional_effects'].append(f"Discard {amount} energy from attacker")
                    
                elif effect_data.get('type') == 'attach_energy':
                    # Generic energy attachment (lowest priority - only executes if no coin flip energy generation)
                    result['energy_changes'].append({
                        'type': 'attach',
                        'target': 'active',
                        'energy_type': 'Fire',  # Default to Fire, never generate Colorless
                        'amount': 1
                    })
                    result['additional_effects'].append("Generic energy attachment effect")
        
        return result
    
    def process_between_turns_effects(self, all_pokemon: List) -> List[Dict]:
        """Process all between-turn effects (like status damage)"""
        all_effects = []
        
        for pokemon in all_pokemon:
            # Process status condition effects
            status_effects = self.status_manager.process_between_turns_effects(pokemon, self.current_turn)
            all_effects.extend(status_effects)
        
        return all_effects
    
    def check_passive_effects(self, trigger: str, context: Dict) -> List[Dict]:
        """Check for passive effects that should trigger"""
        triggered_effects = []
        
        for effect in self.passive_effects:
            # This would contain logic to check if passive effects should trigger
            # based on the current game state and trigger type
            pass
        
        return triggered_effects
    
    def get_all_effects_for_card(self, card: BattleCard) -> List[BattleEffect]:
        """Get all registered effects for a card"""
        return self.registered_effects.get(card.id, [])
    
    def update_battle_state(self, turn: int, player: int):
        """Update the effect engine's battle state"""
        self.current_turn = turn
        self.current_player = player
        self.trainer_manager.reset_turn_limits(turn)
    
    def parse_cards_bulk(self, cards: List[Dict]) -> Dict[str, List[EffectParseResult]]:
        """
        Parse multiple cards using mass effect parser
        Returns comprehensive analysis of effect patterns
        """
        self.logger.info(f"Starting bulk parsing of {len(cards)} cards...")
        
        results = self.mass_parser.parse_card_bulk(cards)
        
        # Generate statistics
        stats = self.mass_parser.get_pattern_statistics()
        total_effects = sum(stats.values())
        
        self.logger.info(f"Mass parsing complete: {total_effects} effects parsed")
        for pattern, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                self.logger.info(f"  {pattern.value}: {count} effects")
        
        return results
    
    def execute_mass_parsed_effect(self, effect_result: EffectParseResult, game_state, source_pokemon, target_pokemon=None) -> Dict[str, Any]:
        """
        Execute an effect that was parsed using the mass effect parser
        Routes to appropriate specialized handlers based on pattern type
        """
        pattern = effect_result.pattern
        params = effect_result.parameters
        
        try:
            if pattern == EffectPattern.COIN_FLIP:
                return self._execute_coin_flip_pattern(params, game_state, source_pokemon)
            
            elif pattern == EffectPattern.STATUS_CONDITION:
                return self._execute_status_condition_pattern(params, game_state, target_pokemon or source_pokemon)
            
            elif pattern == EffectPattern.HEALING:
                return self._execute_healing_pattern(params, game_state, source_pokemon)
            
            elif pattern == EffectPattern.ENERGY_SCALING:
                return self._execute_energy_scaling_pattern(params, game_state, source_pokemon, target_pokemon)
            
            elif pattern == EffectPattern.CONDITIONAL_DAMAGE:
                return self._execute_conditional_damage_pattern(params, game_state, source_pokemon, target_pokemon)
            
            else:
                self.logger.warning(f"Mass parsed effect pattern {pattern.value} not yet implemented")
                return {'not_implemented': True, 'pattern': pattern.value}
                
        except Exception as e:
            self.logger.error(f"Failed to execute mass parsed effect {pattern.value}: {e}")
            return {'error': str(e)}
    
    def _execute_coin_flip_pattern(self, params: Dict[str, Any], game_state, source_pokemon) -> Dict[str, Any]:
        """Execute coin flip effects from mass parser"""
        subtype = params.get('effect_subtype')
        
        if subtype == 'scaling_damage':
            coin_count = params.get('coin_count', 1)
            damage_per_heads = params.get('damage_per_heads', 10)
            
            heads_count = 0
            for _ in range(coin_count):
                if self.coin_manager.flip_coin():
                    heads_count += 1
            
            total_damage = heads_count * damage_per_heads
            self.logger.debug(f"Coin flip scaling: {heads_count} heads = {total_damage} damage")
            return {'damage_bonus': total_damage, 'heads_count': heads_count}
            
        elif subtype == 'conditional_bonus':
            bonus_damage = params.get('bonus_damage', 0)
            if self.coin_manager.flip_coin():
                self.logger.debug(f"Coin flip success: +{bonus_damage} damage")
                return {'damage_bonus': bonus_damage}
            else:
                self.logger.debug("Coin flip failed: no bonus damage")
                return {'damage_bonus': 0}
                
        elif subtype == 'all_or_nothing':
            if self.coin_manager.flip_coin():
                self.logger.debug("Coin flip success: attack proceeds")
                return {'attack_succeeds': True}
            else:
                self.logger.debug("Coin flip failed: attack does nothing")
                return {'attack_succeeds': False, 'damage_bonus': 0}
        
        return {'error': f'Unknown coin flip subtype: {subtype}'}
    
    def _execute_status_condition_pattern(self, params: Dict[str, Any], game_state, target_pokemon) -> Dict[str, Any]:
        """Execute status condition effects from mass parser"""
        subtype = params.get('effect_subtype')
        
        if subtype == 'apply_status':
            status_name = params.get('status_condition', '').upper()
            try:
                status_condition = StatusCondition[status_name]
                success, message = self.status_manager.apply_status_condition(target_pokemon, status_condition, self.current_turn)
                self.logger.debug(f"Applied {status_name} to {target_pokemon.card.name}: {success}")
                return {'status_applied': status_name, 'success': success, 'message': message}
            except KeyError:
                return {'error': f'Unknown status condition: {status_name}'}
                
        elif subtype == 'random_status':
            import random
            conditions = [StatusCondition.BURNED, StatusCondition.POISONED, 
                         StatusCondition.ASLEEP, StatusCondition.PARALYZED, StatusCondition.CONFUSED]
            random_condition = random.choice(conditions)
            success, message = self.status_manager.apply_status_condition(target_pokemon, random_condition, self.current_turn)
            self.logger.debug(f"Applied random status {random_condition.name} to {target_pokemon.card.name}")
            return {'status_applied': random_condition.name, 'success': success, 'message': message, 'random': True}
        
        return {'error': f'Unknown status condition subtype: {subtype}'}
    
    def _execute_healing_pattern(self, params: Dict[str, Any], game_state, source_pokemon) -> Dict[str, Any]:
        """Execute healing effects from mass parser"""
        subtype = params.get('effect_subtype')
        
        if subtype == 'self_heal':
            heal_amount = params.get('heal_amount', 0)
            old_hp = source_pokemon.current_hp
            source_pokemon.heal(heal_amount)
            actual_healed = source_pokemon.current_hp - old_hp
            self.logger.debug(f"Healed {actual_healed} damage from {source_pokemon.card.name}")
            return {'healed_amount': actual_healed}
            
        elif subtype == 'full_heal':
            old_hp = source_pokemon.current_hp
            source_pokemon.current_hp = source_pokemon.card.hp
            actual_healed = source_pokemon.current_hp - old_hp
            self.logger.debug(f"Fully healed {source_pokemon.card.name} ({actual_healed} damage removed)")
            return {'healed_amount': actual_healed, 'full_heal': True}
        
        return {'error': f'Unknown healing subtype: {subtype}'}
    
    def _execute_energy_scaling_pattern(self, params: Dict[str, Any], game_state, source_pokemon, target_pokemon) -> Dict[str, Any]:
        """Execute energy scaling damage effects"""
        subtype = params.get('effect_subtype')
        damage_per_energy = params.get('damage_per_energy', 10)
        
        if subtype == 'opponent_energy_scaling':
            if target_pokemon:
                energy_count = len(target_pokemon.energy_attached)
                bonus_damage = energy_count * damage_per_energy
                self.logger.debug(f"Energy scaling: {energy_count} energy = +{bonus_damage} damage")
                return {'damage_bonus': bonus_damage, 'energy_count': energy_count}
        
        elif subtype == 'self_energy_scaling':
            energy_count = len(source_pokemon.energy_attached)
            bonus_damage = energy_count * damage_per_energy
            self.logger.debug(f"Self energy scaling: {energy_count} energy = +{bonus_damage} damage")
            return {'damage_bonus': bonus_damage, 'energy_count': energy_count}
        
        return {'error': f'Unknown energy scaling subtype: {subtype}'}
    
    def _execute_conditional_damage_pattern(self, params: Dict[str, Any], game_state, source_pokemon, target_pokemon) -> Dict[str, Any]:
        """Execute conditional damage effects"""
        subtype = params.get('effect_subtype')
        
        if subtype == 'energy_condition':
            required_energy = params.get('energy_count', 1)
            bonus_damage = params.get('bonus_damage', 0)
            actual_energy = len(source_pokemon.energy_attached)
            
            if actual_energy >= required_energy:
                self.logger.debug(f"Energy condition met: {actual_energy} >= {required_energy}, +{bonus_damage} damage")
                return {'damage_bonus': bonus_damage, 'condition_met': True}
            else:
                self.logger.debug(f"Energy condition not met: {actual_energy} < {required_energy}")
                return {'damage_bonus': 0, 'condition_met': False}
        
        elif subtype == 'damage_condition':
            bonus_damage = params.get('bonus_damage', 0)
            has_damage = source_pokemon.current_hp < source_pokemon.card.hp
            
            if has_damage:
                self.logger.debug(f"Damage condition met: +{bonus_damage} damage")
                return {'damage_bonus': bonus_damage, 'condition_met': True}
            else:
                self.logger.debug("No damage on Pokemon: condition not met")
                return {'damage_bonus': 0, 'condition_met': False}
        
        return {'error': f'Unknown conditional damage subtype: {subtype}'}
    
    def execute_structured_effect(self, effect_type: str, parameters: Dict[str, Any], 
                                 attacking_pokemon, defending_pokemon = None, 
                                 battle_context: Dict = None) -> EffectResult:
        """
        Execute an effect using the registry system
        
        Args:
            effect_type: The type of effect (matches registry key)
            parameters: Effect parameters
            attacking_pokemon: Source Pokemon
            defending_pokemon: Target Pokemon (if applicable)
            battle_context: Battle state context
        
        Returns:
            EffectResult with outcome
        """
        # Import standard effects to register them
        try:
            import simulator.core.standard_effects
        except ImportError:
            self.logger.warning("Standard effects not available")
        
        # Create effect context
        context = EffectContext(
            source_pokemon=attacking_pokemon,
            target_pokemon=defending_pokemon,
            battle_context=battle_context or {},
            parameters=parameters or {}
        )
        
        # Execute through registry
        return effect_registry.execute(effect_type, context)
    
    def convert_parsed_effect_to_registry(self, effect_data: Dict, 
                                        attacking_pokemon, defending_pokemon = None,
                                        battle_context: Dict = None) -> EffectResult:
        """
        Convert legacy effect data to registry system execution
        
        This provides a bridge between our existing parsing and the new registry system
        """
        effect_type_map = {
            # Damage effects
            'damage_bonus': 'damage_bonus',
            'conditional_damage': 'conditional_damage', 
            'energy_scaling_damage': 'energy_scaling_damage',
            
            # Healing effects
            'heal': 'heal',
            'full_heal': 'full_heal',
            
            # Status effects
            'burn': 'apply_burn',
            'poison': 'apply_poison',
            
            # Coin flip effects
            'flip_for_bonus': 'flip_for_bonus',
            'flip_scaling': 'flip_scaling',
            'flip_variable_count': 'flip_variable_count',
            
            # Energy effects
            'attach_energy': 'attach_energy',
            'discard_energy': 'discard_energy'
        }
        
        # Try to map effect type
        legacy_type = effect_data.get('type')
        registry_type = effect_type_map.get(legacy_type)
        
        if registry_type:
            # Convert parameters to registry format
            parameters = dict(effect_data)  # Copy all parameters
            parameters.pop('type', None)  # Remove type since it's passed separately
            
            return self.execute_structured_effect(
                registry_type, parameters, attacking_pokemon, defending_pokemon, battle_context
            )
        else:
            # Fallback to legacy system
            self.logger.debug(f"Effect type {legacy_type} not in registry, using legacy system")
            return EffectResult(
                success=False,
                description=f"Legacy effect type not mapped: {legacy_type}"
            )
    
    def generate_mass_parsing_report(self, cards: List[Dict]) -> str:
        """Generate a comprehensive report of mass parsing results"""
        results = self.parse_cards_bulk(cards)
        return self.mass_parser.export_analysis_report()


def create_comprehensive_effect_system(battle_cards: List[BattleCard], 
                                     logger: Optional[logging.Logger] = None,
                                     rng_seed: Optional[int] = None) -> AdvancedEffectEngine:
    """Create a complete effect system for the battle simulator"""
    effect_engine = AdvancedEffectEngine(battle_cards, logger, rng_seed)
    
    # Register effects for all cards
    for card in battle_cards:
        effect_engine.register_card_effects(card)
    
    logger.info(f"Created effect system with {len(battle_cards)} cards")
    return effect_engine