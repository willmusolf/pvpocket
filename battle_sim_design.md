# Pokémon TCG Pocket Battle Simulator Design

## Overview
This document describes the architecture, core mechanics, and implementation plan for a comprehensive Pokémon TCG Pocket battle simulator integrated with the existing Pokemon TCG Pocket web application.

## Core Rules & Mechanics

### Deck Rules
- **Deck Size**: Exactly 20 cards
- **Card Copies**: Maximum 2 copies of any card with the same name
- **Starting Hand**: Must contain at least 1 Basic Pokémon (no mulligans)
- **Valid Deck**: Must contain at least 1 Basic Pokémon

### Battle Setup
- **Hand Size**: Maximum 10 cards
- **Bench Size**: Maximum 3 Pokémon
- **Energy**: 1 energy attachment per turn
- **Multi-color Decks**: Energy type selected randomly from deck types each turn
- **Zero Energy Attacks**: Legal and require no energy cost

### Turn Structure
1. **Player 1 Turn 1 Restriction**: Cannot attach energy unless card effect allows
2. **Energy Attachment**: 1 per turn, type based on deck types (random for multi-type)
3. **Attack Phase**: Choose attack, calculate damage, apply effects
4. **Knockout Handling**: If Pokemon is knocked out, defending player must immediately select replacement
5. **End Turn**: Check win conditions, switch active player

### Damage & Combat
- **Weakness**: +20 damage (configurable)
- **Attack Damage**: Based on card attack values
- **KO System**: Pokémon with HP ≤ 0 are knocked out
- **Prize Points**: 1 point per KO, 2 points for EX Pokémon
- **Forced Replacement**: When active Pokemon is knocked out, player must immediately choose replacement from bench or hand

### Win/Tie Conditions
- **Win**: First player to reach 3 prize points
- **Tie**: Both players unable to continue (no bench Pokémon available)
- **Turn Limit**: 100 turns maximum (tie if reached)

## System Architecture

### Package Structure
```
/simulator/
  __init__.py
  /core/
    __init__.py
    game.py        # Main game loop and state management
    player.py      # Player state and actions
    pokemon.py     # Pokémon battle mechanics
    energy.py      # Energy system and type management
    rules.py       # Rule enforcement and validation
  /ai/
    __init__.py
    rule_based.py  # Phase 1 rule-based AI
  /tests/
    __init__.py
    test_game.py   # Game mechanics tests
    test_rules.py  # Rule enforcement tests
    test_ai.py     # AI behavior tests
main.py           # Demo battle entry point
```

## Core Components

### GameState Class
```python
class GameState:
    # Game tracking
    turn_number: int
    current_player: int  # 0 or 1
    winner: Optional[int]
    is_tie: bool
    
    # Player states
    players: List[PlayerState]
    
    # Game configuration
    config: RulesConfig
    
    # Logging
    turn_log: List[Dict]
    rng_seed: Optional[int]
```

### PlayerState Class
```python
class PlayerState:
    # Identity
    player_id: int
    deck: Deck
    
    # Game state
    hand: List[Card]
    bench: List[Optional[BattlePokemon]]  # Max 3, None = empty slot
    active_pokemon: Optional[BattlePokemon]
    prize_points: int
    
    # Turn state
    energy_attached_this_turn: bool
    energy_types_available: List[str]
```

### BattlePokemon Class
```python
class BattlePokemon:
    # Card reference
    card: Card
    
    # Battle state
    current_hp: int
    max_hp: int
    energy_attached: List[str]
    
    # Status effects (future expansion)
    status_effects: List[str]
```

### RulesConfig Class
```python
class RulesConfig:
    # Configurable rules
    weakness_damage_bonus: int = 20
    max_hand_size: int = 10
    max_bench_size: int = 3
    max_deck_size: int = 20
    max_card_copies: int = 2
    max_prize_points: int = 3
    max_turns: int = 100
    
    # Energy rules
    energy_per_turn: int = 1
    player_1_no_energy_turn_1: bool = True
```

## Game Flow

### Initialization
1. Validate both decks (20 cards, ≤2 copies, ≥1 Basic)
2. Shuffle decks with optional seed for reproducibility
3. Draw starting hands (ensure ≥1 Basic Pokémon)
4. Each player places 1 Basic Pokémon as Active
5. Initialize game state and logging

### Turn Sequence
1. **Start of Turn**
   - Check if player can continue (has Active Pokémon)
   - Log turn start
   
2. **Energy Phase**
   - Attach 1 energy if allowed (not Player 1 Turn 1)
   - For multi-type decks, randomly select energy type
   
3. **Action Phase**
   - AI or player selects action (attack, play card, etc.)
   - For Phase 1: AI always attacks if possible
   
4. **Attack Resolution**
   - Validate attack requirements (energy cost)
   - Calculate damage (base + weakness bonus)
   - Apply damage, check for KO
   - If KO occurs, trigger forced Pokemon selection
   - Award prize points for KO
   
5. **Forced Pokemon Selection** (if knockout occurred)
   - Game enters FORCED_POKEMON_SELECTION phase
   - Defending player must choose replacement Pokemon
   - Options: Pokemon from bench or Basic Pokemon from hand
   - Turn continues after selection is made
   
6. **End of Turn**
   - Check win conditions
   - Switch to next player (only if no forced selection pending)
   - Increment turn counter

### Win Condition Checking
1. **Prize Points**: Player reaches 3 points
2. **No Active Pokémon**: Opponent cannot continue
3. **Turn Limit**: 100 turns reached (declare tie)
4. **Both Unable**: Both players cannot continue (tie)

## AI Implementation (Phase 1)

### Rule-Based AI Strategy
```python
class RuleBasedAI:
    def choose_action(self, game_state: GameState, player_id: int) -> Action:
        # Priority order:
        # 1. Place Basic Pokémon if active slot empty
        # 2. Attach energy if available
        # 3. Attack with highest damage possible
        # 4. End turn if no valid actions
```

### AI Decision Logic
1. **Forced Pokemon Selection**: When active Pokemon is knocked out, choose replacement with highest HP/energy score
2. **Pokémon Placement**: Always place Basic Pokémon if active slot is empty
3. **Energy Attachment**: Attach to Active Pokémon if available
4. **Attack Selection**: Choose attack that deals most damage to opponent
5. **Target Selection**: Always target opponent's Active Pokémon

## Logging System

### Turn Logging (JSONL Format)
```json
{
  "turn": 1,
  "player": 0,
  "action": "attach_energy",
  "details": {"energy_type": "Fire", "target": "active"},
  "game_state": {
    "player_0_active_hp": 60,
    "player_1_active_hp": 70,
    "player_0_bench_count": 1,
    "player_1_bench_count": 2
  }
}
```

### Battle Summary
```json
{
  "battle_id": "uuid",
  "winner": 0,
  "is_tie": false,
  "total_turns": 15,
  "final_scores": [3, 1],
  "duration_seconds": 0.045,
  "deck_types": [["Fire"], ["Water", "Lightning"]],
  "rng_seed": 12345
}
```

## Integration Points

### Flask Application
- **Route**: `/api/battle-sim` for battle endpoints
- **Admin Dashboard**: Battle statistics and configuration
- **Database**: Store battle logs and AI configurations in Firebase

### Existing Models
- **Card.py**: Use attack data, HP, weakness, energy types
- **Deck.py**: Use deck validation and card management
- **shared_utils.py**: Firebase integration for logging

### Testing Integration
- **Test Framework**: Integrate with existing `./scripts/run_tests.sh`
- **Coverage**: Include in existing coverage reporting
- **CI/CD**: Add to existing GitHub Actions workflow

## Performance Considerations

### Battle Speed
- **Target**: <100ms per battle for meta analysis
- **Optimization**: Minimal object creation, efficient state updates
- **Caching**: Pre-calculate attack costs and damage values

### Scalability
- **Batch Processing**: Run multiple battles in parallel
- **Memory Management**: Clear battle logs after storage
- **Firebase Limits**: Batch write battle results

## React UI Development (Current Phase)

### Overview
**Status**: ✅ Production Card Database Complete (1,576 cards) | 🚧 React UI Development In Progress

The battle simulator backend is fully operational with comprehensive card effect parsing (86.9% coverage, 1,108+ effects). Now developing an interactive React-based UI for visual testing and gameplay.

### React UI Architecture

#### Component Structure
```
/frontend/
  src/
    components/
      battle/
        BattleField.jsx          # Main game field layout
        PokemonCard.jsx          # Individual card display
        GameControls.jsx         # Attack/action buttons
        EffectDisplay.jsx        # Visual effect feedback  
        BattleLog.jsx           # Real-time event logging
    hooks/
      useBattleWebSocket.js    # Real-time battle state
      useCardEffects.js        # Effect visualization
    services/
      battleAPI.js             # Flask backend integration
```

#### Key Features
- **Dual Mode Operation**: Toggle between AI vs AI auto-sim and manual player control
- **Visual Effect Testing**: Real-time feedback for card effects, damage, status conditions
- **Engine Debugging**: Live display of effect parsing → execution → damage calculation
- **Responsive Design**: Mobile-first approach inspired by official Pokemon TCG Pocket

#### Technical Stack
- **React 18** with TypeScript and functional components
- **WebSocket/Socket.io** for real-time battle state synchronization
- **CSS Modules** for component-scoped styling
- **Vite** for development and build tooling

### Current Development Focus

#### Phase 1: Engine Bug Fixes & React Foundation
**Priority Issues to Resolve**:
- **Pikachu ex Circle Circuit**: Coin flip damage scaling not executing correctly
- **Effect Pipeline**: Ensure parsed effects properly trigger damage modifications
- **Status Condition Visual Feedback**: Make burn/poison damage clearly visible

#### Phase 2: Interactive Battle Interface
**UI Components**:
- Clean battle field layout matching official game aesthetic
- Player area (bottom): Active Pokemon + 3 bench slots with HP/status indicators
- Opponent area (top): Mirror layout with turn indicators
- Real-time battle log showing all effect triggers and calculations

#### Phase 3: Advanced Testing Tools
**Debugging Features**:
- Card state inspector (current HP, status, energy, effects)
- Effect execution tracer (parsed vs executed vs results)
- Quick test scenarios for specific card interactions
- Battle replay system for reproducing bugs

### Integration with Existing Systems

#### Flask Backend Extensions
- **WebSocket Support**: Real-time battle state updates via Socket.io
- **Enhanced Logging**: Detailed effect execution logs for UI debugging
- **Battle API Endpoints**: 
  - `POST /api/battle/create` - Initialize new battle
  - `POST /api/battle/action` - Submit player moves
  - `GET /api/battle/state` - Current battle state

#### Production Card Integration
- **Battle Card Cache**: Utilizes existing optimized caching system
- **Effect Engine**: Leverages mass effect parser with 86.9% coverage
- **Card Conversion**: Uses CardDataBridge for production data compatibility

### Testing Strategy via UI

#### Visual Testing Approach
**Philosophy**: Use interactive gameplay to validate engine correctness rather than isolated unit tests

**Testing Process**:
1. **Load Production Cards**: All 1,576 cards available for testing
2. **Visual Effect Verification**: Immediately see when effects work/fail
3. **Real-time Debugging**: Battle log shows exact effect execution
4. **Systematic Card Testing**: Test problematic cards through actual gameplay

#### Recent Fixes & Improvements ✅
- **Coin Flip Effects**: Pikachu ex Circle Circuit damage scaling FIXED - now properly scales with bench Pokemon count
- **Status Conditions**: Burn/poison damage working correctly - applied after attacks, processed between turns
- **Energy Scaling**: Damage bonuses based on attached energy WORKING
- **Healing Effects**: HP recovery mechanics IMPLEMENTED and working
- **Effect Registry System**: NEW - Modular effect handler system with decorator pattern
- **Comprehensive Effect Execution**: All parsed effects now execute properly in battles

### Next Phase: Complete Battle Engine (Priority Focus)

**⚠️ Focus: Engine Completeness Before AI Development**
The current priority is making the battle engine 100% correct and fully playable with all Pokemon TCG Pocket rules and effects implemented properly.

### Core Engine Completion Tasks

#### Phase A: Common Card Effects (Immediate Priority)
- **Basic Damage Effects**: Ensure all simple damage calculations work correctly
- **Energy Requirements**: Verify energy cost calculations for all common cards
- **Simple Status Effects**: Burn, poison, paralysis, sleep, confusion timing
- **Common Healing**: Basic heal amounts and full heal effects
- **Retreat Mechanics**: Energy cost, status condition blocking
- **Weakness/Resistance**: Verify +20 weakness damage applies correctly

#### Phase B: Intermediate Effects (Short Term)
- **Trainer Cards**: Item effects, supporter effects, tool cards
- **Evolution Mechanics**: Proper evolution chains and timing
- **Energy Manipulation**: Energy acceleration, discard, search effects
- **Deck/Hand Manipulation**: Draw effects, search effects, discard effects
- **Multi-Target Effects**: Bench damage, heal all effects
- **Conditional Effects**: "If opponent has X" type conditions

#### Phase C: Advanced Effects (Medium Term)
- **Stadium Cards**: Field-wide effects and timing
- **Complex Interactions**: Multiple effects triggering simultaneously
- **Replacement Effects**: "Instead" effects and prevention
- **Continuous Effects**: Passive abilities and ongoing effects
- **Turn Structure Effects**: "Once per turn" limitations and tracking

### Battle System Validation

#### Rule Completeness Checklist
- [ ] **Turn 1 Restrictions**: Player 1 cannot attack/energy attach turn 1 (verify exact rules)
- [ ] **Energy Attachment**: 1 per turn, correct type generation for multi-type decks
- [ ] **Attack Resolution**: Damage calculation → weakness → status → healing → KO check
- [ ] **Forced Replacement**: When active Pokemon KO'd, must select replacement immediately
- [ ] **Win Conditions**: 3 prize points, opponent unable to continue, 100 turn limit
- [ ] **Status Timing**: Applied after attacks, processed between turns
- [ ] **Hand/Bench Limits**: 10 card hand limit, 3 bench Pokemon limit

#### Common Card Testing Priority
1. **Basic Pokemon**: Pikachu, Charmander, Squirtle - simple attacks and HP
2. **Evolution Lines**: Charizard line, Blastoise line - evolution mechanics
3. **Trainer Items**: Professor's Research, Pokeball, Potion - basic effects
4. **Energy Cards**: Basic energy attachment and generation
5. **Status Inducers**: Cards that cause burn, poison, paralysis
6. **Healing Cards**: Cards with simple heal effects

### Future Expansion (Later Phases)

#### Advanced Battle Features (After Engine Complete)
- **Battle Animations**: Visual effect feedback in React UI
- **Replay System**: Save and replay battles for debugging
- **Performance Optimization**: <50ms per battle for rapid testing
- **Tournament Mode**: Multiple battle series

#### AI Development (Final Phase)
- **Basic AI**: Simple rule-based decision making
- **Strategic AI**: Deck archetype awareness
- **Meta Analysis**: Automated deck optimization
- **Learning AI**: Advanced strategic development

## Configuration Management

### Environment Variables
```bash
BATTLE_SIM_LOG_LEVEL=INFO
BATTLE_SIM_FIREBASE_LOGGING=true
BATTLE_SIM_RNG_SEED=null
BATTLE_SIM_WEAKNESS_DAMAGE=20
```

### Firebase Collections
```
battle_logs/        # Individual battle turn logs
battle_results/     # Battle summaries and outcomes
ai_configs/         # AI strategy configurations
meta_analysis/      # Large-scale simulation results
```

## Error Handling

### Battle Interruption
- **Invalid State**: Save battle state, log error, graceful exit
- **Timeout**: Declare tie if battle exceeds time limit
- **AI Errors**: Fallback to random valid action

### Data Validation
- **Deck Validation**: Ensure legal decks before battle
- **Action Validation**: Verify all AI actions are legal
- **State Consistency**: Validate game state after each action

## Testing Strategy

### Unit Tests
- **Core Mechanics**: Energy attachment, damage calculation, KO detection
- **Rule Enforcement**: Hand limits, bench limits, deck validation
- **AI Behavior**: Verify AI makes legal and reasonable decisions

### Integration Tests
- **Full Battles**: Complete AI vs AI battles
- **Edge Cases**: Tie conditions, turn limits, unusual scenarios
- **Performance**: Battle speed benchmarks

### Security Tests
- **Input Validation**: Prevent malformed deck data
- **AI Safety**: Ensure AI cannot make illegal moves
- **Resource Limits**: Prevent infinite loops or excessive memory use

## Documentation Maintenance

### Living Documentation
- **Update on Changes**: Modify this document when rules or architecture change
- **Version Control**: Track document changes with code changes
- **Examples**: Maintain working examples of all public APIs

### Code Documentation
- **Docstrings**: Comprehensive documentation for all public methods
- **Type Hints**: Full type annotations for better IDE support
- **Comments**: Explain complex game logic and edge cases

---

*Last Updated: [Auto-updated by implementation]*
*Version: 1.0*
*Status: Phase 1 Implementation*