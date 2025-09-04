"""
Optimized Battle Card Cache System
Provides high-performance caching for battle-ready cards at production scale
"""

import logging
import time
from typing import Dict, List, Optional, Set, Tuple
from threading import Lock
import json
from dataclasses import dataclass, asdict
from collections import defaultdict

from simulator.core.card_bridge import CardDataBridge, BattleCard, load_real_card_collection


@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    load_time: float = 0.0
    last_refresh: Optional[float] = None
    
    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests * 100
    
    def to_dict(self) -> dict:
        """Convert to dictionary including computed properties"""
        return {
            'total_requests': self.total_requests,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'load_time': self.load_time,
            'last_refresh': self.last_refresh,
            'hit_rate': self.hit_rate
        }


class BattleCardCache:
    """High-performance cache for battle-ready cards"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Thread-safe cache storage
        self._cache_lock = Lock()
        self._cards_by_id: Dict[int, BattleCard] = {}
        self._cards_by_name: Dict[str, List[BattleCard]] = defaultdict(list)
        self._pokemon_cards: List[BattleCard] = []
        self._trainer_cards: List[BattleCard] = []
        self._basic_pokemon: List[BattleCard] = []
        self._cards_by_energy_type: Dict[str, List[BattleCard]] = defaultdict(list)
        
        # Cache state
        self._is_loaded = False
        self._loading = False
        self.metrics = CacheMetrics()
        
        # Precomputed battle decks for common types
        self._prebuilt_decks: Dict[str, List[BattleCard]] = {}
    
    def load_cards(self, force_refresh: bool = False) -> bool:
        """Load all battle cards into cache"""
        if self._is_loaded and not force_refresh:
            return True
            
        if self._loading:
            # Wait for other thread to finish loading
            while self._loading:
                time.sleep(0.1)
            return self._is_loaded
        
        self._loading = True
        start_time = time.time()
        
        try:
            self.logger.info("Loading battle cards into cache...")
            
            # Load production cards
            battle_cards = load_real_card_collection(self.logger)
            
            if not battle_cards:
                self.logger.error("Failed to load battle cards")
                return False
            
            # Thread-safe cache update
            with self._cache_lock:
                self._clear_cache()
                
                # Index cards by various criteria for fast lookup
                for card in battle_cards:
                    self._cards_by_id[card.id] = card
                    self._cards_by_name[card.name.lower()].append(card)
                    
                    if card.is_pokemon():
                        self._pokemon_cards.append(card)
                        
                        if card.evolution_stage == 0:  # Basic Pokemon
                            self._basic_pokemon.append(card)
                        
                        if card.energy_type:
                            self._cards_by_energy_type[card.energy_type.lower()].append(card)
                    
                    elif card.is_trainer():
                        self._trainer_cards.append(card)
                
                # Precompute common battle decks
                self._build_precomputed_decks()
                
                self._is_loaded = True
                load_time = time.time() - start_time
                self.metrics.load_time = load_time
                self.metrics.last_refresh = time.time()
                
                self.logger.info(f"Loaded {len(battle_cards)} battle cards in {load_time:.2f}s")
                self.logger.info(f"Cache stats: {len(self._pokemon_cards)} Pokemon, {len(self._trainer_cards)} Trainers")
                self.logger.info(f"Basic Pokemon: {len(self._basic_pokemon)}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load battle cards: {e}")
            return False
        finally:
            self._loading = False
    
    def _clear_cache(self):
        """Clear all cached data"""
        self._cards_by_id.clear()
        self._cards_by_name.clear()
        self._pokemon_cards.clear()
        self._trainer_cards.clear()
        self._basic_pokemon.clear()
        self._cards_by_energy_type.clear()
        self._prebuilt_decks.clear()
        self._is_loaded = False
    
    def _build_precomputed_decks(self):
        """Build precomputed decks for common energy types"""
        try:
            energy_types = ['fire', 'water', 'grass', 'lightning', 'psychic', 'fighting', 'darkness', 'metal', 'colorless']
            
            for energy_type in energy_types:
                # Get basic Pokemon of this type
                type_basics = [
                    card for card in self._basic_pokemon 
                    if card.energy_type and card.energy_type.lower() == energy_type
                ]
                
                if len(type_basics) >= 10:  # Need at least 10 for a deck
                    # Create a simple 20-card deck
                    deck_cards = []
                    
                    # Add varied basic Pokemon (up to 2 of each)
                    card_counts = defaultdict(int)
                    for card in type_basics:
                        if card_counts[card.name] < 2 and len(deck_cards) < 20:
                            deck_cards.append(card)
                            card_counts[card.name] += 1
                    
                    # Fill remaining slots with duplicates if needed
                    while len(deck_cards) < 20:
                        for card in type_basics:
                            if card_counts[card.name] < 2:
                                deck_cards.append(card)
                                card_counts[card.name] += 1
                                if len(deck_cards) >= 20:
                                    break
                        break
                    
                    if len(deck_cards) == 20:
                        self._prebuilt_decks[energy_type] = deck_cards
                        self.logger.debug(f"Prebuilt {energy_type} deck with {len(deck_cards)} cards")
            
            self.logger.info(f"Prebuilt {len(self._prebuilt_decks)} battle decks")
            
        except Exception as e:
            self.logger.warning(f"Failed to build precomputed decks: {e}")
    
    def get_card_by_id(self, card_id: int) -> Optional[BattleCard]:
        """Get card by ID with cache metrics"""
        self.metrics.total_requests += 1
        
        if not self._is_loaded:
            self.load_cards()
        
        with self._cache_lock:
            card = self._cards_by_id.get(card_id)
            
            if card:
                self.metrics.cache_hits += 1
            else:
                self.metrics.cache_misses += 1
            
            return card
    
    def get_cards_by_name(self, name: str) -> List[BattleCard]:
        """Get cards by name with cache metrics"""
        self.metrics.total_requests += 1
        
        if not self._is_loaded:
            self.load_cards()
        
        with self._cache_lock:
            cards = self._cards_by_name.get(name.lower(), [])
            
            if cards:
                self.metrics.cache_hits += 1
            else:
                self.metrics.cache_misses += 1
            
            return cards.copy()  # Return copy to prevent external modification
    
    def get_pokemon_cards(self) -> List[BattleCard]:
        """Get all Pokemon cards"""
        if not self._is_loaded:
            self.load_cards()
        
        with self._cache_lock:
            return self._pokemon_cards.copy()
    
    def get_trainer_cards(self) -> List[BattleCard]:
        """Get all trainer cards"""
        if not self._is_loaded:
            self.load_cards()
        
        with self._cache_lock:
            return self._trainer_cards.copy()
    
    def get_basic_pokemon(self) -> List[BattleCard]:
        """Get all basic Pokemon"""
        if not self._is_loaded:
            self.load_cards()
        
        with self._cache_lock:
            return self._basic_pokemon.copy()
    
    def get_cards_by_energy_type(self, energy_type: str) -> List[BattleCard]:
        """Get cards by energy type"""
        self.metrics.total_requests += 1
        
        if not self._is_loaded:
            self.load_cards()
        
        with self._cache_lock:
            cards = self._cards_by_energy_type.get(energy_type.lower(), [])
            
            if cards:
                self.metrics.cache_hits += 1
            else:
                self.metrics.cache_misses += 1
            
            return cards.copy()
    
    def get_prebuilt_deck(self, energy_type: str) -> Optional[List[BattleCard]]:
        """Get a prebuilt battle deck for the given energy type"""
        if not self._is_loaded:
            self.load_cards()
        
        with self._cache_lock:
            return self._prebuilt_decks.get(energy_type.lower())
    
    def get_available_deck_types(self) -> List[str]:
        """Get list of energy types that have prebuilt decks"""
        if not self._is_loaded:
            self.load_cards()
        
        with self._cache_lock:
            return list(self._prebuilt_decks.keys())
    
    def search_cards(self, **filters) -> List[BattleCard]:
        """Search cards with various filters"""
        if not self._is_loaded:
            self.load_cards()
        
        results = []
        
        with self._cache_lock:
            # Start with all cards
            candidates = list(self._cards_by_id.values())
            
            # Apply filters
            if 'energy_type' in filters:
                energy_type = filters['energy_type'].lower()
                candidates = [c for c in candidates if c.energy_type and c.energy_type.lower() == energy_type]
            
            if 'card_type' in filters:
                card_type = filters['card_type'].lower()
                candidates = [c for c in candidates if card_type in c.card_type.lower()]
            
            if 'is_pokemon' in filters and filters['is_pokemon']:
                candidates = [c for c in candidates if c.is_pokemon()]
            
            if 'is_trainer' in filters and filters['is_trainer']:
                candidates = [c for c in candidates if c.is_trainer()]
            
            if 'evolution_stage' in filters:
                stage = filters['evolution_stage']
                candidates = [c for c in candidates if c.evolution_stage == stage]
            
            if 'has_attacks' in filters and filters['has_attacks']:
                candidates = [c for c in candidates if c.attacks and len(c.attacks) > 0]
            
            if 'has_abilities' in filters and filters['has_abilities']:
                candidates = [c for c in candidates if c.abilities and len(c.abilities) > 0]
            
            if 'min_hp' in filters:
                min_hp = filters['min_hp']
                candidates = [c for c in candidates if c.hp and c.hp >= min_hp]
            
            if 'max_hp' in filters:
                max_hp = filters['max_hp']
                candidates = [c for c in candidates if c.hp and c.hp <= max_hp]
            
            results = candidates
        
        return results
    
    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics"""
        with self._cache_lock:
            stats = {
                'loaded': self._is_loaded,
                'total_cards': len(self._cards_by_id),
                'pokemon_cards': len(self._pokemon_cards),
                'trainer_cards': len(self._trainer_cards),
                'basic_pokemon': len(self._basic_pokemon),
                'prebuilt_decks': len(self._prebuilt_decks),
                'energy_types': len(self._cards_by_energy_type),
                'metrics': self.metrics.to_dict()
            }
        
        return stats
    
    def invalidate(self):
        """Invalidate cache and force reload on next access"""
        self.logger.info("Cache invalidated - will reload on next access")
        with self._cache_lock:
            self._clear_cache()


# Global cache instance
_battle_cache = None
_cache_lock = Lock()


def get_battle_cache(logger: Optional[logging.Logger] = None) -> BattleCardCache:
    """Get or create global battle card cache instance"""
    global _battle_cache
    
    if _battle_cache is None:
        with _cache_lock:
            if _battle_cache is None:
                _battle_cache = BattleCardCache(logger)
    
    return _battle_cache


def preload_battle_cache(logger: Optional[logging.Logger] = None) -> bool:
    """Preload the battle card cache (useful for startup)"""
    cache = get_battle_cache(logger)
    return cache.load_cards()


# Convenience functions for easy access
def get_card_by_id(card_id: int) -> Optional[BattleCard]:
    """Get card by ID from global cache"""
    return get_battle_cache().get_card_by_id(card_id)


def get_cards_by_name(name: str) -> List[BattleCard]:
    """Get cards by name from global cache"""
    return get_battle_cache().get_cards_by_name(name)


def get_pokemon_cards() -> List[BattleCard]:
    """Get all Pokemon cards from global cache"""
    return get_battle_cache().get_pokemon_cards()


def get_basic_pokemon() -> List[BattleCard]:
    """Get all basic Pokemon from global cache"""
    return get_battle_cache().get_basic_pokemon()


def get_prebuilt_deck(energy_type: str) -> Optional[List[BattleCard]]:
    """Get prebuilt deck from global cache"""
    return get_battle_cache().get_prebuilt_deck(energy_type)


def search_cards(**filters) -> List[BattleCard]:
    """Search cards with filters from global cache"""
    return get_battle_cache().search_cards(**filters)