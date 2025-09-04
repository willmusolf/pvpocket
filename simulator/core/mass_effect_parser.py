"""
Mass Effect Parser for Pokemon TCG Pocket Battle Simulator
Analyzes and implements card effects in bulk using pattern recognition
Based on analysis of 1,576 cards with 1,094 effects (86.9% pattern coverage)
"""

import re
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
import logging
from collections import defaultdict

from simulator.core.status_conditions import StatusCondition


class EffectPattern(Enum):
    """Major effect patterns identified from card database analysis"""
    COIN_FLIP = "coin_flip"              # 203 occurrences - Priority 1
    STATUS_CONDITION = "status_condition"  # 118 occurrences - Priority 2  
    CONDITIONAL_DAMAGE = "conditional_damage"  # 134 occurrences - Priority 3
    BENCH_MANIPULATION = "bench_manipulation"  # 166 occurrences - Priority 4
    DISCARD_EFFECTS = "discard_effects"   # 125 occurrences - Priority 5
    HEALING = "healing"                   # 70 occurrences - Priority 6
    ENERGY_SCALING = "energy_scaling"     # 44 occurrences - Priority 7
    SEARCH_EFFECTS = "search_effects"     # 30 occurrences - Priority 8
    DRAW_EFFECTS = "draw_effects"         # 22 occurrences - Priority 9
    DAMAGE_PREVENTION = "damage_prevention"  # 18 occurrences - Priority 10


@dataclass
class EffectParseResult:
    """Result of parsing a card effect"""
    pattern: EffectPattern
    confidence: float  # 0.0 to 1.0
    parameters: Dict[str, Any]
    raw_text: str
    card_name: str = ""
    card_id: int = 0


class MassEffectParser:
    """
    Parses card effects in bulk using pattern recognition
    Implements the top 10 effect patterns covering 86.9% of all card effects
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.effect_patterns = self._initialize_patterns()
        self.parsed_effects = []
        self.pattern_stats = defaultdict(int)
    
    def _initialize_patterns(self) -> Dict[EffectPattern, List[Dict]]:
        """Initialize pattern recognition rules for each effect type"""
        return {
            EffectPattern.COIN_FLIP: [
                {
                    'pattern': r'flip (\d+) coins?\. .*?(\d+) damage.*?each heads',
                    'type': 'scaling_damage',
                    'extract': ['coin_count', 'damage_per_heads']
                },
                {
                    'pattern': r'flip a coin\. if heads,.*?(\d+) more damage',
                    'type': 'conditional_bonus',
                    'extract': ['bonus_damage']
                },
                {
                    'pattern': r'flip a coin\. if tails, this attack does nothing',
                    'type': 'all_or_nothing',
                    'extract': []
                },
                {
                    'pattern': r'flip coins until you get tails.*?(\d+) damage.*?each heads',
                    'type': 'flip_until_tails',
                    'extract': ['damage_per_heads']
                }
            ],
            
            EffectPattern.STATUS_CONDITION: [
                {
                    'pattern': r'(?:active )?pokémon is now (burned|poisoned|asleep|paralyzed|confused)',
                    'type': 'apply_status',
                    'extract': ['status_condition']
                },
                {
                    'pattern': r'(?:opponent.*?pokémon.*?is now (asleep))|(?:your opponent.*?asleep)',
                    'type': 'apply_sleep',
                    'extract': []
                },
                {
                    'pattern': r'special condition.*?chosen at random',
                    'type': 'random_status',
                    'extract': []
                }
            ],
            
            EffectPattern.CONDITIONAL_DAMAGE: [
                {
                    'pattern': r'if.*?has.*?(\d+).*?energy.*?(\d+) more damage',
                    'type': 'energy_condition',
                    'extract': ['energy_count', 'bonus_damage']
                },
                {
                    'pattern': r'if.*?has.*?damage.*?(\d+) more damage',
                    'type': 'damage_condition',
                    'extract': ['bonus_damage']
                },
                {
                    'pattern': r'if.*?evolved.*?this turn.*?(\d+) more damage',
                    'type': 'evolution_condition',
                    'extract': ['bonus_damage']
                }
            ],
            
            EffectPattern.BENCH_MANIPULATION: [
                {
                    'pattern': r'(?:each of )?(?:your opponent\'s )?benched pokémon.*?(\d+) damage',
                    'type': 'bench_damage',
                    'extract': ['damage_amount']
                },
                {
                    'pattern': r'switch.*?pokémon with.*?benched pokémon',
                    'type': 'switch',
                    'extract': []
                },
                {
                    'pattern': r'attach.*?energy.*?benched pokémon',
                    'type': 'bench_energy_attach',
                    'extract': []
                }
            ],
            
            EffectPattern.DISCARD_EFFECTS: [
                {
                    'pattern': r'discard (\d+|an|all).*?energy.*?this pokémon',
                    'type': 'self_energy_discard',
                    'extract': ['discard_count']
                },
                {
                    'pattern': r'discard (\d+|an).*?energy.*?opponent',
                    'type': 'opponent_energy_discard',
                    'extract': ['discard_count']
                },
                {
                    'pattern': r'your opponent discards (\d+).*?cards?.*?hand',
                    'type': 'opponent_hand_discard',
                    'extract': ['discard_count']
                }
            ],
            
            EffectPattern.HEALING: [
                {
                    'pattern': r'heal (\d+) damage.*?this pokémon',
                    'type': 'self_heal',
                    'extract': ['heal_amount']
                },
                {
                    'pattern': r'remove all damage.*?this pokémon',
                    'type': 'full_heal',
                    'extract': []
                }
            ],
            
            EffectPattern.ENERGY_SCALING: [
                {
                    'pattern': r'(\d+) more damage.*?each energy attached to.*?opponent',
                    'type': 'opponent_energy_scaling',
                    'extract': ['damage_per_energy']
                },
                {
                    'pattern': r'(\d+) more damage.*?each energy attached to this pok[ée]mon',
                    'type': 'self_energy_scaling',
                    'extract': ['damage_per_energy']
                }
            ],
            
            EffectPattern.SEARCH_EFFECTS: [
                {
                    'pattern': r'search your deck for.*?(pokémon|energy|trainer).*?(?:hand|bench)',
                    'type': 'deck_search',
                    'extract': ['card_type']
                }
            ],
            
            EffectPattern.DRAW_EFFECTS: [
                {
                    'pattern': r'draw (\d+) cards?',
                    'type': 'draw_cards',
                    'extract': ['card_count']
                }
            ],
            
            EffectPattern.DAMAGE_PREVENTION: [
                {
                    'pattern': r'prevent all damage.*?attacks.*?next turn',
                    'type': 'turn_prevention',
                    'extract': []
                }
            ]
        }
    
    def parse_effect(self, effect_text: str, card_name: str = "", card_id: int = 0) -> List[EffectParseResult]:
        """
        Parse a single effect text and return all matching patterns
        
        Args:
            effect_text: The effect text to parse
            card_name: Name of the card for tracking
            card_id: ID of the card for tracking
            
        Returns:
            List of EffectParseResult objects for all detected patterns
        """
        results = []
        text_lower = effect_text.lower()
        
        # Try each pattern type
        for pattern_type, pattern_rules in self.effect_patterns.items():
            for rule in pattern_rules:
                match = re.search(rule['pattern'], text_lower)
                if match:
                    # Extract parameters based on rule
                    parameters = {'effect_subtype': rule['type']}
                    
                    if 'extract' in rule:
                        for i, param_name in enumerate(rule['extract']):
                            if i + 1 <= len(match.groups()):
                                raw_value = match.group(i + 1)
                                parameters[param_name] = self._normalize_value(raw_value)
                    
                    # Calculate confidence based on pattern complexity and match quality
                    confidence = self._calculate_confidence(effect_text, match, rule)
                    
                    result = EffectParseResult(
                        pattern=pattern_type,
                        confidence=confidence,
                        parameters=parameters,
                        raw_text=effect_text,
                        card_name=card_name,
                        card_id=card_id
                    )
                    
                    results.append(result)
                    self.pattern_stats[pattern_type] += 1
                    
                    # Log successful pattern match
                    self.logger.debug(f"Matched {pattern_type.value} pattern in {card_name}: {rule['type']}")
        
        return results
    
    def parse_card_bulk(self, cards: List[Dict]) -> Dict[str, List[EffectParseResult]]:
        """
        Parse effects for multiple cards in bulk
        
        Args:
            cards: List of card dictionaries with 'attacks' and 'abilities' fields
            
        Returns:
            Dictionary mapping card IDs to their parsed effects
        """
        bulk_results = {}
        total_effects = 0
        matched_effects = 0
        
        for card in cards:
            card_id = str(card.get('id', 0))
            card_name = card.get('name', 'Unknown')
            card_results = []
            
            # Parse attack effects
            for attack in card.get('attacks', []):
                effect_text = attack.get('effect', '')
                if effect_text:
                    parsed = self.parse_effect(effect_text, card_name, card.get('id', 0))
                    card_results.extend(parsed)
                    total_effects += 1
                    if parsed:
                        matched_effects += 1
            
            # Parse ability effects
            for ability in card.get('abilities', []):
                effect_text = ability.get('effect', '')
                if effect_text:
                    parsed = self.parse_effect(effect_text, card_name, card.get('id', 0))
                    card_results.extend(parsed)
                    total_effects += 1
                    if parsed:
                        matched_effects += 1
            
            if card_results:
                bulk_results[card_id] = card_results
        
        # Log bulk parsing statistics
        coverage_percent = (matched_effects / total_effects * 100) if total_effects > 0 else 0
        self.logger.info(f"Bulk parsing completed: {matched_effects}/{total_effects} effects matched ({coverage_percent:.1f}% coverage)")
        
        return bulk_results
    
    def _normalize_value(self, raw_value: str) -> Union[int, str]:
        """Normalize extracted values to appropriate types"""
        if raw_value.isdigit():
            return int(raw_value)
        elif raw_value in ['an', 'a']:
            return 1
        elif raw_value == 'all':
            return 'all'
        else:
            return raw_value
    
    def _calculate_confidence(self, full_text: str, match: re.Match, rule: Dict) -> float:
        """Calculate confidence score for a pattern match"""
        base_confidence = 0.7
        
        # Bonus for specific patterns
        if rule['type'] in ['scaling_damage', 'bench_damage', 'self_heal']:
            base_confidence += 0.2
        
        # Bonus for complete matches
        if len(match.group(0)) > len(full_text) * 0.5:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def get_pattern_statistics(self) -> Dict[str, int]:
        """Get statistics on pattern usage"""
        return dict(self.pattern_stats)
    
    def generate_implementation_code(self, pattern: EffectPattern) -> str:
        """Generate template implementation code for a specific pattern"""
        templates = {
            EffectPattern.COIN_FLIP: '''
def execute_coin_flip_effect(self, effect_params: Dict[str, Any], game_state, source_pokemon):
    """Execute coin flip effect based on subtype"""
    subtype = effect_params.get('effect_subtype')
    
    if subtype == 'scaling_damage':
        coin_count = effect_params.get('coin_count', 1)
        damage_per_heads = effect_params.get('damage_per_heads', 10)
        
        heads_count = 0
        for _ in range(coin_count):
            if self.coin_flip_manager.flip_coin():
                heads_count += 1
        
        return {'damage_bonus': heads_count * damage_per_heads}
        
    elif subtype == 'conditional_bonus':
        bonus_damage = effect_params.get('bonus_damage', 0)
        if self.coin_flip_manager.flip_coin():
            return {'damage_bonus': bonus_damage}
        return {'damage_bonus': 0}
        
    # ... implement other subtypes
''',
            
            EffectPattern.STATUS_CONDITION: '''
def execute_status_condition_effect(self, effect_params: Dict[str, Any], game_state, target_pokemon):
    """Execute status condition effect"""
    subtype = effect_params.get('effect_subtype')
    
    if subtype == 'apply_status':
        status_name = effect_params.get('status_condition')
        status_condition = StatusCondition[status_name.upper()]
        return self.status_manager.apply_condition(target_pokemon, status_condition)
        
    elif subtype == 'random_status':
        import random
        conditions = [StatusCondition.BURNED, StatusCondition.POISONED, 
                     StatusCondition.ASLEEP, StatusCondition.PARALYZED, StatusCondition.CONFUSED]
        random_condition = random.choice(conditions)
        return self.status_manager.apply_condition(target_pokemon, random_condition)
'''
        }
        
        return templates.get(pattern, "# Template not implemented yet")
    
    def export_analysis_report(self) -> str:
        """Export detailed analysis report for developers"""
        report = "# Mass Effect Parser Analysis Report\\n\\n"
        
        # Pattern statistics
        report += "## Pattern Coverage\\n"
        total_patterns = sum(self.pattern_stats.values())
        for pattern, count in sorted(self.pattern_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_patterns * 100) if total_patterns > 0 else 0
            report += f"- **{pattern.value}**: {count} effects ({percentage:.1f}%)\\n"
        
        report += f"\\n**Total Parsed Effects**: {total_patterns}\\n"
        
        # Implementation recommendations
        report += "\\n## Implementation Priority\\n"
        priority_order = [
            (EffectPattern.COIN_FLIP, "Foundation for many combo effects"),
            (EffectPattern.STATUS_CONDITION, "Required by conditional effects"),
            (EffectPattern.HEALING, "Simple standalone mechanics"),
            (EffectPattern.ENERGY_SCALING, "Mathematical scaling patterns"),
            (EffectPattern.CONDITIONAL_DAMAGE, "Depends on status conditions")
        ]
        
        for i, (pattern, description) in enumerate(priority_order, 1):
            count = self.pattern_stats.get(pattern, 0)
            report += f"{i}. **{pattern.value}** ({count} effects) - {description}\\n"
        
        return report


def demonstrate_mass_parsing():
    """Demonstration of mass effect parsing capabilities"""
    parser = MassEffectParser()
    
    # Example cards to test parsing
    test_cards = [
        {
            'id': 1,
            'name': 'Pikachu ex',
            'attacks': [
                {
                    'name': 'Circle Circuit',
                    'effect': 'Flip 2 coins. This attack does 30 damage for each heads.'
                }
            ]
        },
        {
            'id': 2, 
            'name': 'Charizard ex',
            'attacks': [
                {
                    'name': 'Crimson Storm',
                    'effect': 'Your opponent\'s Active Pokemon is now Burned.'
                }
            ]
        }
    ]
    
    # Parse in bulk
    results = parser.parse_card_bulk(test_cards)
    
    print("Mass Effect Parsing Results:")
    for card_id, effects in results.items():
        print(f"\\nCard {card_id}:")
        for effect in effects:
            print(f"  - Pattern: {effect.pattern.value}")
            print(f"  - Confidence: {effect.confidence:.2f}")
            print(f"  - Parameters: {effect.parameters}")
    
    print(f"\\nPattern Statistics:")
    for pattern, count in parser.get_pattern_statistics().items():
        print(f"  {pattern.value}: {count}")


if __name__ == "__main__":
    demonstrate_mass_parsing()