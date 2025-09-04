"""
Evolution System for Pokemon TCG Pocket Battle Simulator
Handles evolution mechanics, validation, and card transformations.
"""

from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass

# Import card bridge for BattleCard
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from simulator.core.card_bridge import BattleCard


@dataclass
class Evolution:
    """Represents an evolution relationship"""
    evolved_card: BattleCard
    pre_evolution: str  # Name of the card this evolves from
    evolution_stage: int  # 1 = Stage 1, 2 = Stage 2


class EvolutionManager:
    """Manages evolution chains and validation"""
    
    def __init__(self, battle_cards: List[BattleCard], logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.evolution_chains = self._build_evolution_chains(battle_cards)
        self.card_lookup = {card.name: card for card in battle_cards}
        
    def _build_evolution_chains(self, battle_cards: List[BattleCard]) -> Dict[str, List[BattleCard]]:
        """Build evolution chains from battle cards"""
        chains = {}
        
        # Group cards by evolution line
        for card in battle_cards:
            if not card.is_pokemon():
                continue
                
            # Get the base evolution name
            base_name = self._get_base_evolution_name(card)
            if base_name not in chains:
                chains[base_name] = []
            chains[base_name].append(card)
        
        # Sort each chain by evolution stage
        for base_name, cards in chains.items():
            cards.sort(key=lambda c: c.evolution_stage or 0)
            
        self.logger.info(f"Built evolution chains for {len(chains)} different Pokemon lines")
        return chains
    
    def _get_base_evolution_name(self, card: BattleCard) -> str:
        """Get the base Pokemon name for this evolution line"""
        # For now, use simple name-based inference
        # This could be enhanced with actual evolution data
        
        name = card.name.lower()
        
        # Common evolution patterns
        evolution_patterns = {
            # Charmander line
            'charmander': 'charmander',
            'charmeleon': 'charmander', 
            'charizard': 'charmander',
            
            # Squirtle line
            'squirtle': 'squirtle',
            'wartortle': 'squirtle',
            'blastoise': 'squirtle',
            
            # Bulbasaur line
            'bulbasaur': 'bulbasaur',
            'ivysaur': 'bulbasaur',
            'venusaur': 'bulbasaur',
            
            # Caterpie line
            'caterpie': 'caterpie',
            'metapod': 'caterpie',
            'butterfree': 'caterpie',
            
            # Weedle line
            'weedle': 'weedle',
            'kakuna': 'weedle',
            'beedrill': 'weedle',
            
            # Pidgey line
            'pidgey': 'pidgey',
            'pidgeotto': 'pidgey',
            'pidgeot': 'pidgey',
            
            # Rattata line
            'rattata': 'rattata',
            'raticate': 'rattata',
            
            # Spearow line
            'spearow': 'spearow',
            'fearow': 'spearow',
            
            # Ekans line
            'ekans': 'ekans',
            'arbok': 'ekans',
            
            # Pikachu line
            'pichu': 'pichu',
            'pikachu': 'pichu',
            'raichu': 'pichu',
            
            # Sandshrew line
            'sandshrew': 'sandshrew',
            'sandslash': 'sandshrew',
            
            # Nidoran line
            'nidoran': 'nidoran',
            'nidorina': 'nidoran',
            'nidoqueen': 'nidoran',
            'nidorino': 'nidoran',
            'nidoking': 'nidoran',
            
            # Clefairy line
            'cleffa': 'cleffa',
            'clefairy': 'cleffa',
            'clefable': 'cleffa',
            
            # Vulpix line
            'vulpix': 'vulpix',
            'ninetales': 'vulpix',
            
            # Jigglypuff line
            'igglybuff': 'igglybuff',
            'jigglypuff': 'igglybuff',
            'wigglytuff': 'igglybuff',
            
            # Zubat line
            'zubat': 'zubat',
            'golbat': 'zubat',
            'crobat': 'zubat',
            
            # Oddish line
            'oddish': 'oddish',
            'gloom': 'oddish',
            'vileplume': 'oddish',
            'bellossom': 'oddish',
            
            # Paras line
            'paras': 'paras',
            'parasect': 'paras',
            
            # Venonat line
            'venonat': 'venonat',
            'venomoth': 'venonat',
            
            # Diglett line
            'diglett': 'diglett',
            'dugtrio': 'diglett',
            
            # Meowth line
            'meowth': 'meowth',
            'persian': 'meowth',
            
            # Psyduck line
            'psyduck': 'psyduck',
            'golduck': 'psyduck',
            
            # Mankey line
            'mankey': 'mankey',
            'primeape': 'mankey',
            
            # Growlithe line
            'growlithe': 'growlithe',
            'arcanine': 'growlithe',
            
            # Poliwag line
            'poliwag': 'poliwag',
            'poliwhirl': 'poliwag',
            'poliwrath': 'poliwag',
            'politoed': 'poliwag',
            
            # Abra line
            'abra': 'abra',
            'kadabra': 'abra',
            'alakazam': 'abra',
            
            # Machop line
            'machop': 'machop',
            'machoke': 'machop',
            'machamp': 'machop',
            
            # Bellsprout line
            'bellsprout': 'bellsprout',
            'weepinbell': 'bellsprout',
            'victreebel': 'bellsprout',
            
            # Tentacool line
            'tentacool': 'tentacool',
            'tentacruel': 'tentacool',
            
            # Geodude line
            'geodude': 'geodude',
            'graveler': 'geodude',
            'golem': 'geodude',
            
            # Ponyta line
            'ponyta': 'ponyta',
            'rapidash': 'ponyta',
            
            # Slowpoke line
            'slowpoke': 'slowpoke',
            'slowbro': 'slowpoke',
            'slowking': 'slowpoke',
            
            # Magnemite line
            'magnemite': 'magnemite',
            'magneton': 'magnemite',
            'magnezone': 'magnemite',
            
            # Farfetch'd line
            'farfetchd': 'farfetchd',
            
            # Doduo line
            'doduo': 'doduo',
            'dodrio': 'doduo',
            
            # Seel line
            'seel': 'seel',
            'dewgong': 'seel',
            
            # Grimer line
            'grimer': 'grimer',
            'muk': 'grimer',
            
            # Shellder line
            'shellder': 'shellder',
            'cloyster': 'shellder',
            
            # Gastly line
            'gastly': 'gastly',
            'haunter': 'gastly',
            'gengar': 'gastly',
            
            # Onix line
            'onix': 'onix',
            'steelix': 'onix',
            
            # Drowzee line
            'drowzee': 'drowzee',
            'hypno': 'drowzee',
            
            # Krabby line
            'krabby': 'krabby',
            'kingler': 'krabby',
            
            # Voltorb line
            'voltorb': 'voltorb',
            'electrode': 'voltorb',
            
            # Exeggcute line
            'exeggcute': 'exeggcute',
            'exeggutor': 'exeggcute',
            
            # Cubone line
            'cubone': 'cubone',
            'marowak': 'cubone',
            
            # Tyrogue line
            'tyrogue': 'tyrogue',
            'hitmonlee': 'tyrogue',
            'hitmonchan': 'tyrogue',
            'hitmontop': 'tyrogue',
            
            # Lickitung line
            'lickitung': 'lickitung',
            'lickilicky': 'lickitung',
            
            # Koffing line
            'koffing': 'koffing',
            'weezing': 'koffing',
            
            # Rhyhorn line
            'rhyhorn': 'rhyhorn',
            'rhydon': 'rhyhorn',
            'rhyperior': 'rhyhorn',
            
            # Chansey line
            'happiny': 'happiny',
            'chansey': 'happiny',
            'blissey': 'happiny',
            
            # Tangela line
            'tangela': 'tangela',
            'tangrowth': 'tangela',
            
            # Kangaskhan line
            'kangaskhan': 'kangaskhan',
            
            # Horsea line
            'horsea': 'horsea',
            'seadra': 'horsea',
            'kingdra': 'horsea',
            
            # Goldeen line
            'goldeen': 'goldeen',
            'seaking': 'goldeen',
            
            # Staryu line
            'staryu': 'staryu',
            'starmie': 'staryu',
            
            # Mr. Mime line
            'mime jr.': 'mime jr.',
            'mr. mime': 'mime jr.',
            
            # Scyther line
            'scyther': 'scyther',
            'scizor': 'scyther',
            
            # Jynx line
            'smoochum': 'smoochum',
            'jynx': 'smoochum',
            
            # Electabuzz line
            'elekid': 'elekid',
            'electabuzz': 'elekid',
            'electivire': 'elekid',
            
            # Magmar line
            'magby': 'magby',
            'magmar': 'magby',
            'magmortar': 'magby',
            
            # Pinsir line
            'pinsir': 'pinsir',
            
            # Tauros line
            'tauros': 'tauros',
            
            # Magikarp line
            'magikarp': 'magikarp',
            'gyarados': 'magikarp',
            
            # Lapras line
            'lapras': 'lapras',
            
            # Ditto line
            'ditto': 'ditto',
            
            # Eevee line
            'eevee': 'eevee',
            'vaporeon': 'eevee',
            'jolteon': 'eevee',
            'flareon': 'eevee',
            'espeon': 'eevee',
            'umbreon': 'eevee',
            'leafeon': 'eevee',
            'glaceon': 'eevee',
            'sylveon': 'eevee',
            
            # Porygon line
            'porygon': 'porygon',
            'porygon2': 'porygon',
            'porygon-z': 'porygon',
            
            # Omanyte line
            'omanyte': 'omanyte',
            'omastar': 'omanyte',
            
            # Kabuto line
            'kabuto': 'kabuto',
            'kabutops': 'kabuto',
            
            # Aerodactyl line
            'aerodactyl': 'aerodactyl',
            
            # Munchlax line
            'munchlax': 'munchlax',
            'snorlax': 'munchlax',
            
            # Articuno line
            'articuno': 'articuno',
            
            # Zapdos line
            'zapdos': 'zapdos',
            
            # Moltres line
            'moltres': 'moltres',
            
            # Dratini line
            'dratini': 'dratini',
            'dragonair': 'dratini',
            'dragonite': 'dratini',
            
            # Mewtwo line
            'mewtwo': 'mewtwo',
            
            # Mew line
            'mew': 'mew',
        }
        
        # Handle variations and EX cards
        clean_name = name.replace(' ex', '').replace('-ex', '').strip()
        base_name = evolution_patterns.get(clean_name, clean_name)
        
        return base_name
    
    def is_pokemon(self, card: BattleCard) -> bool:
        """Check if card is a Pokemon"""
        return 'Pokémon' in card.card_type
    
    def can_evolve(self, current_card: BattleCard, target_card: BattleCard) -> Tuple[bool, str]:
        """Check if current_card can evolve into target_card"""
        if not self.is_pokemon(current_card) or not self.is_pokemon(target_card):
            return False, "Both cards must be Pokemon"
        
        # Check evolution stages
        current_stage = current_card.evolution_stage or 0
        target_stage = target_card.evolution_stage or 0
        
        if target_stage != current_stage + 1:
            return False, f"Cannot evolve from stage {current_stage} to stage {target_stage}"
        
        # Check evolution line compatibility
        current_base = self._get_base_evolution_name(current_card)
        target_base = self._get_base_evolution_name(target_card)
        
        if current_base != target_base:
            return False, f"Evolution lines don't match: {current_base} vs {target_base}"
        
        # Check if target card specifies what it evolves from
        if target_card.evolves_from and target_card.evolves_from.lower() != current_card.name.lower():
            return False, f"{target_card.name} evolves from {target_card.evolves_from}, not {current_card.name}"
        
        return True, "Evolution is valid"
    
    def get_possible_evolutions(self, current_card: BattleCard) -> List[BattleCard]:
        """Get all possible evolution targets for the current card"""
        possible_evolutions = []
        
        current_base = self._get_base_evolution_name(current_card)
        if current_base in self.evolution_chains:
            chain = self.evolution_chains[current_base]
            
            for card in chain:
                can_evolve, _ = self.can_evolve(current_card, card)
                if can_evolve:
                    possible_evolutions.append(card)
        
        return possible_evolutions
    
    def evolve_pokemon(self, current_card: BattleCard, target_card: BattleCard, 
                      current_damage: int = 0, attached_energy: List[str] = None) -> Tuple[bool, str, Optional[BattleCard]]:
        """Evolve a Pokemon, preserving damage and attached energy"""
        if attached_energy is None:
            attached_energy = []
        
        can_evolve, reason = self.can_evolve(current_card, target_card)
        if not can_evolve:
            return False, reason, None
        
        # Create evolved Pokemon with preserved state
        evolved_card = BattleCard(
            id=target_card.id,
            name=target_card.name,
            card_type=target_card.card_type,
            energy_type=target_card.energy_type,
            hp=target_card.hp,
            attacks=target_card.attacks,
            weakness=target_card.weakness,
            retreat_cost=target_card.retreat_cost,
            evolution_stage=target_card.evolution_stage,
            evolves_from=target_card.evolves_from,
            is_ex=target_card.is_ex,
            abilities=target_card.abilities,
            rarity=target_card.rarity,
            set_name=target_card.set_name
        )
        
        # Note: Damage and energy preservation would be handled by the game state
        # The evolved card itself is just the template
        
        self.logger.info(f"Successfully evolved {current_card.name} into {target_card.name}")
        return True, f"Evolved {current_card.name} into {target_card.name}", evolved_card


def get_evolution_candidates_from_hand(hand_cards: List[BattleCard], 
                                     active_pokemon: BattleCard,
                                     evolution_manager: EvolutionManager) -> List[BattleCard]:
    """Get evolution candidates from hand for the active Pokemon"""
    candidates = []
    
    for card in hand_cards:
        if evolution_manager.is_pokemon(card):
            can_evolve, _ = evolution_manager.can_evolve(active_pokemon, card)
            if can_evolve:
                candidates.append(card)
    
    return candidates


def validate_evolution_rules(pokemon_instance, evolution_card: BattleCard, turn_played: int, current_turn: int) -> Tuple[bool, str]:
    """Validate TCG Pocket evolution rules"""
    
    # Rule 1: Cannot evolve on the same turn the Pokemon was played (unless specified otherwise)
    if turn_played == current_turn:
        # Check for special abilities that allow immediate evolution
        for ability in evolution_card.abilities or []:
            for effect in ability.get('parsed_effects', []):
                if effect.get('type') == 'immediate_evolution':
                    return True, "Immediate evolution allowed by ability"
        
        return False, "Cannot evolve on the same turn the Pokemon was played"
    
    # Rule 2: Can only evolve once per turn per Pokemon (additional rule that could be added)
    # This would need to be tracked in game state
    
    return True, "Evolution rules satisfied"