"""
Coin Flip System for Pokemon TCG Pocket Battle Simulator
Handles coin flip mechanics that are common in many card effects.
"""

import random
from typing import List, Tuple, Dict, Optional
import logging
from enum import Enum


class CoinResult(Enum):
    """Coin flip results"""
    HEADS = "heads"
    TAILS = "tails"


class CoinFlipManager:
    """Manages coin flip mechanics for battles"""
    
    def __init__(self, logger: Optional[logging.Logger] = None, rng_seed: Optional[int] = None):
        self.logger = logger or logging.getLogger(__name__)
        if rng_seed is not None:
            random.seed(rng_seed)
    
    def flip_coin(self) -> CoinResult:
        """Flip a single coin"""
        result = CoinResult.HEADS if random.random() < 0.5 else CoinResult.TAILS
        self.logger.debug(f"Coin flip result: {result.value}")
        return result
    
    def flip_multiple_coins(self, count: int) -> List[CoinResult]:
        """Flip multiple coins"""
        results = [self.flip_coin() for _ in range(count)]
        heads_count = sum(1 for r in results if r == CoinResult.HEADS)
        tails_count = count - heads_count
        
        self.logger.info(f"Flipped {count} coins: {heads_count} heads, {tails_count} tails")
        return results
    
    def flip_until_tails(self, max_flips: int = 10) -> Tuple[List[CoinResult], int]:
        """Flip coins until tails (for effects like 'flip until tails')"""
        results = []
        heads_count = 0
        
        for _ in range(max_flips):
            result = self.flip_coin()
            results.append(result)
            
            if result == CoinResult.HEADS:
                heads_count += 1
            else:  # TAILS
                break
        
        self.logger.info(f"Flipped until tails: {heads_count} heads before tails")
        return results, heads_count
    
    def calculate_coin_flip_damage(self, base_damage: int, damage_per_heads: int, 
                                 flip_count: int) -> Tuple[int, List[CoinResult]]:
        """Calculate damage based on coin flips"""
        results = self.flip_multiple_coins(flip_count)
        heads_count = sum(1 for r in results if r == CoinResult.HEADS)
        
        total_damage = base_damage + (heads_count * damage_per_heads)
        
        self.logger.info(f"Coin flip damage: {base_damage} base + ({heads_count} heads × {damage_per_heads}) = {total_damage}")
        return total_damage, results
    
    def check_coin_flip_success(self, required_heads: int = 1) -> Tuple[bool, List[CoinResult]]:
        """Check if coin flip(s) meet success criteria"""
        results = self.flip_multiple_coins(required_heads)
        heads_count = sum(1 for r in results if r == CoinResult.HEADS)
        
        success = heads_count >= required_heads
        self.logger.info(f"Coin flip success check: needed {required_heads} heads, got {heads_count} - {'SUCCESS' if success else 'FAILED'}")
        
        return success, results


def parse_coin_flip_effect(effect_text: str) -> Optional[Dict]:
    """Parse coin flip mechanics from effect text"""
    text_lower = effect_text.lower()
    
    # Pattern: "Flip X coins. This attack does Y damage for each heads"
    import re
    
    # Energy attachment based on coin flips (like Moltres ex Inferno Dance) - CHECK THIS FIRST
    # Pattern: "Flip 3 coins. Take an amount of [R] Energy from your Energy Zone equal to the number of heads"
    pattern_energy = r'flip (\d+) coins?.*?energy.*?equal to the number of heads'
    match_energy = re.search(pattern_energy, text_lower)
    if match_energy:
        coin_count = int(match_energy.group(1))
        
        # Check if it's specifically bench distribution (like Moltres)
        distribution_target = 'self'  # Default
        energy_type = 'Fire'  # Default - assume Fire for Moltres
        
        if 'bench' in text_lower:
            distribution_target = 'bench'
        
        # Determine energy type from card text - NEVER generate "Colorless"
        if '[r]' in text_lower or 'fire' in text_lower:
            energy_type = 'Fire'
        elif '[w]' in text_lower or 'water' in text_lower:
            energy_type = 'Water'
        elif '[g]' in text_lower or 'grass' in text_lower:
            energy_type = 'Grass'
        elif '[l]' in text_lower or 'lightning' in text_lower:
            energy_type = 'Lightning'
        elif '[p]' in text_lower or 'psychic' in text_lower:
            energy_type = 'Psychic'
        elif '[f]' in text_lower or 'fighting' in text_lower:
            energy_type = 'Fighting'
        elif '[d]' in text_lower or 'darkness' in text_lower:
            energy_type = 'Darkness'
        elif '[m]' in text_lower or 'metal' in text_lower:
            energy_type = 'Metal'
        # Note: Never generate "Colorless" energy - it doesn't exist as an attachment
        
        return {
            'type': 'coin_flip_energy_generation',
            'coin_count': coin_count,
            'energy_per_heads': 1,
            'energy_type': energy_type,
            'distribution_target': distribution_target
        }
    
    # Variable count based on bench Pokemon (like Pikachu ex Circle Circuit)
    # Pattern: "Flip a coin for each of your Benched Pokémon. This attack does X more damage for each heads"
    pattern_bench = r'flip a coin for each.*?bench.*?(\d+).*?damage for each heads'
    match_bench = re.search(pattern_bench, text_lower)
    if match_bench:
        damage_per_heads = int(match_bench.group(1))
        return {
            'type': 'coin_flip_variable_count',
            'count_source': 'bench_pokemon',
            'damage_per_heads': damage_per_heads,
            'base_damage': 0
        }
    
    # Multiple coins with damage per heads (fixed count)
    pattern1 = r'flip (\d+) coins?.*?(\d+) damage for each heads'
    match1 = re.search(pattern1, text_lower)
    if match1:
        coin_count = int(match1.group(1))
        damage_per_heads = int(match1.group(2))
        return {
            'type': 'coin_flip_damage',
            'coin_count': coin_count,
            'damage_per_heads': damage_per_heads,
            'base_damage': 0
        }
    
    # Pattern: "Flip a coin until you get tails. This attack does X damage for each heads"  
    pattern2 = r'flip a coin until.*?tails.*?(\d+) damage for each heads'
    match2 = re.search(pattern2, text_lower)
    if match2:
        damage_per_heads = int(match2.group(1))
        return {
            'type': 'coin_flip_until_tails',
            'damage_per_heads': damage_per_heads,
            'base_damage': 0
        }
    
    # Pattern: "Flip a coin. If tails, this attack does nothing"
    pattern3 = r'flip a coin.*?if tails.*?does nothing'
    if re.search(pattern3, text_lower):
        return {
            'type': 'coin_flip_all_or_nothing',
            'success_on': 'heads'
        }
    
    # Pattern: "Flip a coin. If heads, [effect]"
    pattern4 = r'flip a coin.*?if heads'
    if re.search(pattern4, text_lower):
        return {
            'type': 'coin_flip_conditional',
            'success_on': 'heads',
            'success_effect': 'parsed_separately'
        }
    
    # Pattern: "Flip a coin. If tails, [effect]"  
    pattern5 = r'flip a coin.*?if tails'
    if re.search(pattern5, text_lower):
        return {
            'type': 'coin_flip_conditional',
            'success_on': 'tails',
            'success_effect': 'parsed_separately'
        }
    
    # Simple coin flip
    pattern6 = r'flip a coin'
    if re.search(pattern6, text_lower):
        return {
            'type': 'coin_flip_simple',
            'coin_count': 1
        }
    
    # Multiple coin flip (generic fallback)
    pattern7 = r'flip (\d+) coins'
    match7 = re.search(pattern7, text_lower)
    if match7:
        coin_count = int(match7.group(1))
        return {
            'type': 'coin_flip_multiple',
            'coin_count': coin_count
        }
    
    return None


def execute_coin_flip_effect(effect_data: Dict, coin_manager: CoinFlipManager, 
                           base_attack_damage: int = 0, battle_context: Dict = None) -> Dict:
    """Execute a coin flip effect and return results"""
    effect_type = effect_data.get('type')
    results = {
        'success': False,
        'total_damage': base_attack_damage,
        'coin_results': [],
        'description': ''
    }
    
    if effect_type == 'coin_flip_damage':
        coin_count = effect_data.get('coin_count', 1)
        damage_per_heads = effect_data.get('damage_per_heads', 0)
        
        total_damage, coin_results = coin_manager.calculate_coin_flip_damage(
            base_attack_damage, damage_per_heads, coin_count
        )
        
        heads_count = sum(1 for r in coin_results if r == CoinResult.HEADS)
        
        results.update({
            'success': True,
            'total_damage': total_damage,
            'coin_results': [r.value for r in coin_results],
            'description': f'Flipped {coin_count} coins, got {heads_count} heads for {total_damage} total damage'
        })
    
    elif effect_type == 'coin_flip_variable_count':
        # Handle variable count based on bench Pokemon (like Pikachu ex Circle Circuit)
        count_source = effect_data.get('count_source', 'bench_pokemon')
        damage_per_heads = effect_data.get('damage_per_heads', 0)
        
        # Determine coin count based on source
        coin_count = 0
        if battle_context and count_source == 'bench_pokemon':
            attacker = battle_context.get('attacker')
            if attacker and hasattr(attacker, 'bench'):
                # Count non-None Pokemon on bench
                coin_count = sum(1 for pokemon in attacker.bench if pokemon is not None)
        
        if coin_count > 0:
            total_damage, coin_results = coin_manager.calculate_coin_flip_damage(
                base_attack_damage, damage_per_heads, coin_count
            )
            heads_count = sum(1 for r in coin_results if r == CoinResult.HEADS)
            
            results.update({
                'success': True,
                'total_damage': total_damage,
                'coin_results': [r.value for r in coin_results],
                'description': f'Flipped {coin_count} coins (one for each bench Pokemon), got {heads_count} heads for {total_damage} total damage'
            })
        else:
            # No bench Pokemon, no coins to flip
            results.update({
                'success': True,
                'total_damage': base_attack_damage,
                'coin_results': [],
                'description': f'No bench Pokemon, no coins flipped, {base_attack_damage} base damage'
            })
    
    elif effect_type == 'coin_flip_until_tails':
        damage_per_heads = effect_data.get('damage_per_heads', 0)
        
        coin_results, heads_count = coin_manager.flip_until_tails()
        total_damage = base_attack_damage + (heads_count * damage_per_heads)
        
        results.update({
            'success': True,
            'total_damage': total_damage,
            'coin_results': [r.value for r in coin_results],
            'description': f'Flipped until tails, got {heads_count} heads for {total_damage} total damage'
        })
    
    elif effect_type == 'coin_flip_all_or_nothing':
        success_on = effect_data.get('success_on', 'heads')
        coin_result = coin_manager.flip_coin()
        
        success = (coin_result.value == success_on)
        final_damage = base_attack_damage if success else 0
        
        results.update({
            'success': success,
            'total_damage': final_damage,
            'coin_results': [coin_result.value],
            'description': f'Flipped {coin_result.value} - {"SUCCESS" if success else "FAILED"}, {final_damage} damage'
        })
    
    elif effect_type == 'coin_flip_conditional':
        success_on = effect_data.get('success_on', 'heads')
        coin_result = coin_manager.flip_coin()
        
        success = (coin_result.value == success_on)
        
        results.update({
            'success': success,
            'total_damage': base_attack_damage,
            'coin_results': [coin_result.value],
            'description': f'Flipped {coin_result.value} - condition {"MET" if success else "NOT MET"}'
        })
    
    elif effect_type == 'coin_flip_energy_generation':
        coin_count = effect_data.get('coin_count', 1)
        energy_per_heads = effect_data.get('energy_per_heads', 1)
        coin_results = coin_manager.flip_multiple_coins(coin_count)
        
        heads_count = sum(1 for r in coin_results if r == CoinResult.HEADS)
        energy_generated = heads_count * energy_per_heads
        
        results.update({
            'success': True,
            'total_damage': base_attack_damage,
            'coin_results': [r.value for r in coin_results],
            'description': f'Flipped {coin_count} coins, got {heads_count} heads - generated {energy_generated} energy',
            'energy_generated': energy_generated,
            'requires_distribution': True,  # Flag to indicate this needs energy distribution
            'energy_type': effect_data.get('energy_type', 'Fire'),  # Type of energy to distribute
            'distribution_target': effect_data.get('distribution_target', 'bench')  # Where to distribute
        })
    
    elif effect_type in ['coin_flip_simple', 'coin_flip_multiple']:
        coin_count = effect_data.get('coin_count', 1)
        coin_results = coin_manager.flip_multiple_coins(coin_count)
        
        heads_count = sum(1 for r in coin_results if r == CoinResult.HEADS)
        
        results.update({
            'success': True,
            'total_damage': base_attack_damage,
            'coin_results': [r.value for r in coin_results],
            'description': f'Flipped {coin_count} coins, got {heads_count} heads'
        })
    
    return results


# Example usage patterns for common effects from your database:

def handle_iron_head_attack(coin_manager: CoinFlipManager, base_damage: int = 70) -> Dict:
    """Handle 'Flip a coin until you get tails. This attack does 70 damage for each heads.'"""
    effect_data = {
        'type': 'coin_flip_until_tails',
        'damage_per_heads': base_damage
    }
    return execute_coin_flip_effect(effect_data, coin_manager, 0, None)


def handle_tropical_hammer_attack(coin_manager: CoinFlipManager, base_damage: int) -> Dict:
    """Handle 'Flip a coin. If tails, this attack does nothing.'"""
    effect_data = {
        'type': 'coin_flip_all_or_nothing',
        'success_on': 'heads'
    }
    return execute_coin_flip_effect(effect_data, coin_manager, base_damage, None)


def handle_burning_bonemerang_attack(coin_manager: CoinFlipManager) -> Dict:
    """Handle 'Flip 2 coins. This attack does 70 damage for each heads.'"""
    effect_data = {
        'type': 'coin_flip_damage',
        'coin_count': 2,
        'damage_per_heads': 70
    }
    return execute_coin_flip_effect(effect_data, coin_manager, 0, None)