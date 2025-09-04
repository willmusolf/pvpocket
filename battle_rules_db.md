# Pokémon TCG Pocket Battle Rules Database Reference

## Overview
This document defines the minimal, streamlined database structure and runtime configuration for the battle simulator. This is optimized for simulation performance and separate from the full card database.

## Core Database Schema

### Battle Card Data
Minimal card information required for battle simulation:

```python
@dataclass
class BattleCard:
    # Core identification
    id: int                    # Master card ID (links to full Card.py)
    name: str                  # Card name
    
    # Battle mechanics
    card_type: str            # "Basic Pokémon", "Stage 1 Pokémon", "Trainer - Item", etc.
    hp: Optional[int]         # HP for Pokémon cards
    attacks: List[Attack]     # List of attack data
    weakness: Optional[str]   # Weakness type ("Fire", "Water", etc.)
    retreat_cost: Optional[int] # Energy cost to retreat
    
    # Type information
    energy_type: str          # Primary energy type for Pokémon
    is_ex: bool = False      # True for EX Pokémon (2 prize points)
    
    # Evolution data
    evolution_stage: Optional[int]  # 0=Basic, 1=Stage 1, 2=Stage 2
    evolves_from: Optional[str]     # Name of previous evolution
```

### Attack Data Structure
```python
@dataclass
class Attack:
    name: str                 # Attack name
    cost: List[str]          # Energy cost (["Fire", "Fire", "Colorless"])
    damage: int              # Base damage (0 for effect-only attacks)
    effect_text: str         # Human-readable effect description
    effect_id: Optional[str] # Machine-readable effect ID (Phase 2+)
```

### Battle Deck Data
```python
@dataclass
class BattleDeck:
    deck_id: str             # Unique deck identifier
    name: str                # Deck name
    card_ids: List[int]      # List of 20 card IDs
    deck_types: List[str]    # Energy types in deck (["Fire", "Water"])
    strategy_profile: str    # AI strategy ("aggro", "control", "balanced")
```

## Runtime Configuration

### Engine Configuration Singleton
```python
class BattleEngineConfig:
    # Rule constants
    MAX_DECK_SIZE: int = 20
    MAX_HAND_SIZE: int = 10
    MAX_BENCH_SIZE: int = 3
    MAX_CARD_COPIES: int = 2
    MAX_PRIZE_POINTS: int = 3
    MAX_TURNS: int = 100
    
    # Damage modifiers
    WEAKNESS_DAMAGE_BONUS: int = 20
    
    # Energy rules
    ENERGY_PER_TURN: int = 1
    PLAYER_1_NO_ENERGY_TURN_1: bool = True
    
    # Zero-energy attacks
    ALLOW_ZERO_COST_ATTACKS: bool = True
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_TO_FIREBASE: bool = True
    DETAILED_TURN_LOGGING: bool = True
    
    # Performance settings
    BATTLE_TIMEOUT_SECONDS: int = 30
    MAX_CONCURRENT_BATTLES: int = 10
```

## Energy System Reference

### Energy Types
```python
ENERGY_TYPES = {
    "Fire": "R",
    "Water": "W", 
    "Grass": "G",
    "Lightning": "L",
    "Psychic": "P",
    "Fighting": "F",
    "Darkness": "D",
    "Metal": "M",
    "Colorless": "C"
}

ENERGY_SYMBOLS = {v: k for k, v in ENERGY_TYPES.items()}
```

### Multi-Type Energy Generation
```python
def generate_energy_for_turn(deck_types: List[str], rng: random.Random) -> str:
    """Generate random energy type from deck's available types"""
    if not deck_types:
        return "Colorless"
    return rng.choice(deck_types)
```

## Effect System Stubs (Phase 2+)

### Effect Interface
```python
class BattleEffect:
    effect_id: str
    trigger: str              # "on_attack", "on_play", "passive"
    target: str               # "self", "opponent", "active", "bench"
    
    def apply(self, context: BattleContext) -> BattleResult:
        """Apply effect to battle state"""
        pass
```

### Common Effect Stubs
```python
# Placeholder effect IDs for future implementation
EFFECT_REGISTRY = {
    "damage_boost": "Increase attack damage by X",
    "energy_acceleration": "Attach additional energy",
    "status_condition": "Apply status effect (poison, sleep, etc.)",
    "card_draw": "Draw additional cards",
    "healing": "Restore HP to target",
    "retreat_prevention": "Prevent opponent from retreating"
}
```

## Data Import Pipeline

### Nightly Card Import Workflow
```python
def import_cards_for_battle_sim():
    """
    Import cards from main database to battle-optimized format
    Run nightly to sync with scraping updates
    """
    # 1. Load full cards from Firebase/Card.py
    # 2. Extract battle-relevant data
    # 3. Store in optimized battle_cards collection
    # 4. Update deck type mappings
    # 5. Validate all existing battle decks still valid
```

### Battle Card Creation
```python
def card_to_battle_card(card: Card) -> BattleCard:
    """Convert full Card object to BattleCard for simulation"""
    return BattleCard(
        id=card.id,
        name=card.name,
        card_type=card.card_type,
        hp=card.hp,
        attacks=[parse_attack(attack) for attack in card.attacks],
        weakness=card.weakness,
        retreat_cost=card.retreat_cost,
        energy_type=card.energy_type,
        is_ex="ex" in card.name.lower(),
        evolution_stage=card.evolution_stage,
        evolves_from=card.evolves_from
    )
```

## Firebase Collections for Battle Sim

### Collection Structure
```
battle_sim/
  ├── cards/           # BattleCard documents (optimized for simulation)
  ├── decks/           # BattleDeck documents  
  ├── configs/         # Engine configuration
  ├── battle_logs/     # Individual turn logs
  ├── battle_results/  # Battle summaries
  └── meta_analysis/   # Aggregated statistics
```

### Document Examples

#### BattleCard Document
```json
{
  "id": 123,
  "name": "Charizard ex",
  "card_type": "Stage 2 Pokémon",
  "hp": 180,
  "attacks": [
    {
      "name": "Fire Blast",
      "cost": ["Fire", "Fire", "Colorless"],
      "damage": 120,
      "effect_text": "",
      "effect_id": null
    }
  ],
  "weakness": "Water",
  "retreat_cost": 2,
  "energy_type": "Fire",
  "is_ex": true,
  "evolution_stage": 2,
  "evolves_from": "Charmeleon"
}
```

#### Battle Configuration Document
```json
{
  "config_version": "1.0",
  "rules": {
    "weakness_damage_bonus": 20,
    "max_turns": 100,
    "allow_zero_cost_attacks": true
  },
  "ai_settings": {
    "default_strategy": "balanced",
    "decision_timeout_ms": 100
  },
  "logging": {
    "log_level": "INFO",
    "store_turn_details": true
  }
}
```

## Performance Optimizations

### Card Data Caching
```python
class BattleCardCache:
    """In-memory cache of battle cards for fast lookup"""
    
    def __init__(self):
        self._cards_by_id: Dict[int, BattleCard] = {}
        self._cards_by_name: Dict[str, List[BattleCard]] = {}
        
    def load_from_firebase(self) -> None:
        """Load all battle cards into memory cache"""
        pass
        
    def get_card(self, card_id: int) -> Optional[BattleCard]:
        """Fast O(1) card lookup by ID"""
        return self._cards_by_id.get(card_id)
```

### Deck Validation Cache
```python
def validate_deck_for_battle(deck: BattleDeck) -> Tuple[bool, str]:
    """
    Quick deck validation for battle eligibility
    - Exactly 20 cards
    - All cards exist in battle database
    - ≤2 copies of each card name
    - ≥1 Basic Pokémon
    """
    pass
```

## Data Consistency

### Sync Validation
```python
def validate_battle_data_sync():
    """
    Ensure battle database matches main card database
    - Check for missing cards
    - Validate attack data consistency
    - Report discrepancies
    """
    pass
```

### Auto-Update Triggers
- Main card database changes → Battle database update
- New card sets released → Battle card import
- Rule changes → Configuration update
- Schema changes → Migration scripts

## API Integration

### Battle Card Service
```python
class BattleCardService:
    def get_battle_deck(self, deck_id: str) -> BattleDeck:
        """Load deck optimized for battle simulation"""
        pass
        
    def get_battle_cards(self, card_ids: List[int]) -> List[BattleCard]:
        """Batch load battle cards by IDs"""
        pass
        
    def validate_deck_legal(self, deck: BattleDeck) -> bool:
        """Check if deck meets battle requirements"""
        pass
```

---

*Last Updated: [Auto-updated with implementation]*
*Version: 1.0*
*Schema Stability: Stable for Phase 1, extensions planned for Phase 2+*