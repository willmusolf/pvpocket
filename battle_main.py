#!/usr/bin/env python3
"""
Pokemon TCG Pocket Battle Simulator - Demo Entry Point

Demonstrates the battle simulator with AI vs AI battles.
Can be used for testing, development, and showcasing the system.
"""

import argparse
import json
import logging
import random
import sys
import time
import os
from typing import List, Dict, Any

# Import existing models
from Card import Card, CardCollection
from Deck import Deck

# Import battle simulator
from simulator.core.game import GameState, BattleResult
from simulator.core.rules import BattleRules, RulesEngine
from simulator.ai.rule_based import RuleBasedAI

# Import real card integration
from simulator.core.card_bridge import load_real_card_collection, create_battle_deck_from_real_cards, BattleCard


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Setup logging for the battle simulator"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    return logging.getLogger(__name__)


def create_real_card_collection(logger: logging.Logger = None) -> List[BattleCard]:
    """Load real cards from the database for battle simulation"""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    # Set up environment for Firebase emulator
    os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
    
    try:
        battle_cards = load_real_card_collection(logger)
        if battle_cards:
            logger.info(f"Successfully loaded {len(battle_cards)} real battle cards")
            return battle_cards
        else:
            logger.warning("No real cards loaded, falling back to sample cards")
            return create_sample_battle_cards()
    except Exception as e:
        logger.error(f"Failed to load real cards: {e}, using sample cards")
        return create_sample_battle_cards()


def create_sample_battle_cards() -> List[BattleCard]:
    """Create sample battle cards as fallback"""
    return [
        BattleCard(
            id=1, name="Charmander", card_type="Basic Pokémon", energy_type="Fire", hp=60,
            attacks=[{"name": "Scratch", "cost": [], "damage": 10, "effect_text": "", "parsed_effects": []}],
            weakness="Water", retreat_cost=1, evolution_stage=0
        ),
        BattleCard(
            id=2, name="Squirtle", card_type="Basic Pokémon", energy_type="Water", hp=60,
            attacks=[{"name": "Bubble", "cost": ["Water"], "damage": 10, "effect_text": "", "parsed_effects": []}],
            weakness="Lightning", retreat_cost=1, evolution_stage=0
        ),
        BattleCard(
            id=3, name="Bulbasaur", card_type="Basic Pokémon", energy_type="Grass", hp=60,
            attacks=[{"name": "Tackle", "cost": [], "damage": 10, "effect_text": "", "parsed_effects": []}],
            weakness="Fire", retreat_cost=1, evolution_stage=0
        ),
        BattleCard(
            id=4, name="Pikachu", card_type="Basic Pokémon", energy_type="Lightning", hp=60,
            attacks=[{"name": "Thunder Shock", "cost": ["Lightning"], "damage": 20, "effect_text": "", "parsed_effects": []}],
            weakness="Fighting", retreat_cost=1, evolution_stage=0
        ),
        BattleCard(
            id=5, name="Rattata", card_type="Basic Pokémon", energy_type="Colorless", hp=40,
            attacks=[{"name": "Quick Attack", "cost": [], "damage": 10, "effect_text": "", "parsed_effects": []}],
            weakness=None, retreat_cost=1, evolution_stage=0
        ),
        BattleCard(
            id=6, name="Meowth", card_type="Basic Pokémon", energy_type="Colorless", hp=50,
            attacks=[{"name": "Scratch", "cost": [], "damage": 10, "effect_text": "", "parsed_effects": []}],
            weakness="Fighting", retreat_cost=1, evolution_stage=0
        )
    ]


def create_sample_card_collection() -> CardCollection:
    """Create a sample collection for demo purposes (legacy function)"""
    collection = CardCollection()
    
    # Create sample Basic Pokemon cards
    sample_cards = [
        # Fire type Basic Pokemon
        Card(
            id=1, name="Charmander", energy_type="Fire", card_type="Basic Pokémon", hp=60,
            attacks=[{"name": "Scratch", "cost": [], "damage": "10", "effect": ""}],
            weakness="Water", retreat_cost=1
        ),
        Card(
            id=2, name="Growlithe", energy_type="Fire", card_type="Basic Pokémon", hp=70,
            attacks=[{"name": "Bite", "cost": ["F"], "damage": "20", "effect": ""}],
            weakness="Water", retreat_cost=1
        ),
        
        # Water type Basic Pokemon
        Card(
            id=3, name="Squirtle", energy_type="Water", card_type="Basic Pokémon", hp=60,
            attacks=[{"name": "Bubble", "cost": ["W"], "damage": "10", "effect": ""}],
            weakness="Lightning", retreat_cost=1
        ),
        Card(
            id=4, name="Psyduck", energy_type="Water", card_type="Basic Pokémon", hp=70,
            attacks=[{"name": "Water Gun", "cost": ["W", "C"], "damage": "20", "effect": ""}],
            weakness="Lightning", retreat_cost=2
        ),
        
        # Grass type Basic Pokemon
        Card(
            id=5, name="Bulbasaur", energy_type="Grass", card_type="Basic Pokémon", hp=60,
            attacks=[{"name": "Tackle", "cost": [], "damage": "10", "effect": ""}],
            weakness="Fire", retreat_cost=1
        ),
        Card(
            id=6, name="Oddish", energy_type="Grass", card_type="Basic Pokémon", hp=50,
            attacks=[{"name": "Absorb", "cost": ["G"], "damage": "10", "effect": "Heal 10"}],
            weakness="Fire", retreat_cost=1
        ),
        
        # Lightning type Basic Pokemon  
        Card(
            id=7, name="Pikachu", energy_type="Lightning", card_type="Basic Pokémon", hp=60,
            attacks=[{"name": "Thunder Shock", "cost": ["L"], "damage": "20", "effect": ""}],
            weakness="Fighting", retreat_cost=1
        ),
        Card(
            id=8, name="Magnemite", energy_type="Lightning", card_type="Basic Pokémon", hp=50,
            attacks=[{"name": "Thunder Wave", "cost": ["L"], "damage": "10", "effect": ""}],
            weakness="Fighting", retreat_cost=1
        ),
        
        # Colorless Basic Pokemon (with zero-cost attacks for testing)
        Card(
            id=9, name="Rattata", energy_type="Colorless", card_type="Basic Pokémon", hp=40,
            attacks=[{"name": "Quick Attack", "cost": [], "damage": "10", "effect": ""}],
            weakness=None, retreat_cost=1
        ),
        Card(
            id=10, name="Meowth", energy_type="Colorless", card_type="Basic Pokémon", hp=50,
            attacks=[{"name": "Scratch", "cost": [], "damage": "10", "effect": ""}],
            weakness="Fighting", retreat_cost=1
        ),
        
        # Trainer cards
        Card(
            id=11, name="Professor Oak", energy_type="", card_type="Trainer - Supporter",
            attacks=[], weakness=None, retreat_cost=None
        ),
        Card(
            id=12, name="Potion", energy_type="", card_type="Trainer - Item",
            attacks=[], weakness=None, retreat_cost=None
        )
    ]
    
    for card in sample_cards:
        collection.add_card(card)
        
    return collection


def create_sample_deck(collection: CardCollection, deck_type: str = "fire") -> Deck:
    """Create a sample deck for testing"""
    deck = Deck(f"Sample {deck_type.title()} Deck")
    
    if deck_type == "fire":
        # Fire deck composition
        cards_to_add = [
            (1, 2),   # 2x Charmander
            (2, 2),   # 2x Growlithe
            (9, 2),   # 2x Rattata (colorless)
            (10, 2),  # 2x Meowth (colorless)
            (11, 2),  # 2x Professor Oak 
            (12, 2),  # 2x Potion
            (5, 2),   # 2x Bulbasaur (filler)
            (6, 2),   # 2x Oddish (filler)
            (7, 2),   # 2x Pikachu (filler)
            (8, 2)    # 2x Magnemite (filler)
        ]
        deck.deck_types = ["Fire"]
        
    elif deck_type == "water":
        # Water deck composition
        cards_to_add = [
            (3, 2),   # 2x Squirtle
            (4, 2),   # 2x Psyduck
            (9, 2),   # 2x Rattata (colorless)
            (10, 2),  # 2x Meowth (colorless)
            (11, 2),  # 2x Professor Oak
            (12, 2),  # 2x Potion
            (1, 2),   # 2x Charmander (filler)
            (2, 2),   # 2x Growlithe (filler)
            (5, 2),   # 2x Bulbasaur (filler)
            (6, 2)    # 2x Oddish (filler)
        ]
        deck.deck_types = ["Water"]
        
    elif deck_type == "grass":
        # Grass deck composition
        cards_to_add = [
            (5, 2),   # 2x Bulbasaur
            (6, 2),   # 2x Oddish
            (9, 2),   # 2x Rattata (colorless)
            (10, 2),  # 2x Meowth (colorless)
            (11, 2),  # 2x Professor Oak
            (12, 2),  # 2x Potion
            (1, 2),   # 2x Charmander (filler)
            (3, 2),   # 2x Squirtle (filler)
            (7, 2),   # 2x Pikachu (filler)
            (8, 2)    # 2x Magnemite (filler)
        ]
        deck.deck_types = ["Grass"]
        
    elif deck_type == "lightning":
        # Lightning deck composition
        cards_to_add = [
            (7, 2),   # 2x Pikachu
            (8, 2),   # 2x Magnemite
            (9, 2),   # 2x Rattata (colorless)
            (10, 2),  # 2x Meowth (colorless)
            (11, 2),  # 2x Professor Oak
            (12, 2),  # 2x Potion
            (1, 2),   # 2x Charmander (filler)
            (3, 2),   # 2x Squirtle (filler)
            (5, 2),   # 2x Bulbasaur (filler)
            (6, 2)    # 2x Oddish (filler)
        ]
        deck.deck_types = ["Lightning"]
        
    elif deck_type == "mixed":
        # Mixed deck composition
        cards_to_add = [
            (1, 1),   # 1x Charmander
            (3, 1),   # 1x Squirtle
            (5, 1),   # 1x Bulbasaur
            (7, 1),   # 1x Pikachu
            (9, 2),   # 2x Rattata
            (10, 2),  # 2x Meowth
            (11, 6),  # 6x Professor Oak
            (12, 6)   # 6x Potion
        ]
        deck.deck_types = ["Fire", "Water", "Grass", "Lightning"]
        
    else:  # Default to colorless
        cards_to_add = [
            (9, 4),   # 4x Rattata
            (10, 4),  # 4x Meowth
            (11, 6),  # 6x Professor Oak
            (12, 6)   # 6x Potion
        ]
        deck.deck_types = ["Colorless"]
    
    # Add cards to deck
    for card_id, count in cards_to_add:
        card = collection.get_card_by_id(card_id)
        if card:
            for _ in range(count):
                if len(deck.cards) < 20:  # Ensure exactly 20 cards
                    deck.add_card(card)
    
    return deck


def create_real_card_deck(battle_cards: List[BattleCard], deck_type: str = "fire") -> Deck:
    """Create a deck using real battle cards"""
    deck = Deck(f"Real {deck_type.title()} Deck")
    
    # Filter Pokemon cards by type
    pokemon_cards = [
        card for card in battle_cards 
        if 'Pokémon' in card.card_type and 
        card.energy_type.lower() == deck_type.lower()
    ]
    
    # Get Basic Pokemon for deck foundation
    basic_pokemon = [card for card in pokemon_cards if card.evolution_stage == 0]
    
    # Fallback to any Basic Pokemon if not enough of the target type
    if len(basic_pokemon) < 5:
        all_basics = [
            card for card in battle_cards 
            if 'Pokémon' in card.card_type and 
            card.evolution_stage == 0
        ]
        # Add different types to fill out the deck
        for card in all_basics:
            if card not in basic_pokemon:
                basic_pokemon.append(card)
                if len(basic_pokemon) >= 10:
                    break
    
    # Ensure we have at least some cards
    if not basic_pokemon:
        # Fallback to sample cards if no real cards available
        logger = logging.getLogger(__name__)
        logger.warning("No Basic Pokemon found in real cards, using sample cards")
        return create_sample_deck(create_sample_card_collection(), deck_type)
    
    # Create deck with exactly 20 cards
    deck_cards = []
    card_names = {}  # Track count by name for 2-copy limit
    
    # Add Basic Pokemon first (ensure at least 1)
    for basic_card in basic_pokemon:
        if len(deck_cards) >= 20:
            break
            
        card_name = basic_card.name
        if card_names.get(card_name, 0) < 2:  # 2-copy limit
            # Convert BattleCard back to Card for Deck compatibility
            card = Card(
                id=basic_card.id,
                name=basic_card.name,
                energy_type=basic_card.energy_type,
                card_type=basic_card.card_type,
                hp=basic_card.hp,
                attacks=[
                    {
                        'name': attack['name'],
                        'cost': attack['cost'],
                        'damage': str(attack['damage']),
                        'effect': attack['effect_text']
                    }
                    for attack in basic_card.attacks
                ],
                weakness=basic_card.weakness,
                retreat_cost=basic_card.retreat_cost,
                firebase_image_url=basic_card.firebase_image_url,
                rarity=basic_card.rarity,
                set_name=basic_card.set_name
            )
            deck_cards.append(card)
            card_names[card_name] = card_names.get(card_name, 0) + 1
    
    # Fill remaining slots by adding second copies
    while len(deck_cards) < 20:
        added_card = False
        for basic_card in basic_pokemon:
            if len(deck_cards) >= 20:
                break
                
            card_name = basic_card.name
            if card_names.get(card_name, 0) < 2:  # Can add second copy
                card = Card(
                    id=basic_card.id,
                    name=basic_card.name,
                    energy_type=basic_card.energy_type,
                    card_type=basic_card.card_type,
                    hp=basic_card.hp,
                    attacks=[
                        {
                            'name': attack['name'],
                            'cost': attack['cost'],
                            'damage': str(attack['damage']),
                            'effect': attack['effect_text']
                        }
                        for attack in basic_card.attacks
                    ],
                    weakness=basic_card.weakness,
                    retreat_cost=basic_card.retreat_cost,
                    firebase_image_url=basic_card.firebase_image_url,
                    rarity=basic_card.rarity,
                    set_name=basic_card.set_name
                )
                deck_cards.append(card)
                card_names[card_name] = card_names.get(card_name, 0) + 1
                added_card = True
        
        # If we can't add any more cards (all at 2-copy limit), break
        if not added_card:
            break
    
    # If still not 20 cards, pad with duplicates (ignore 2-copy rule for testing)
    while len(deck_cards) < 20 and basic_pokemon:
        source_card = basic_pokemon[len(deck_cards) % len(basic_pokemon)]
        card = Card(
            id=source_card.id,
            name=f"{source_card.name}_extra_{len(deck_cards)}",  # Make name unique
            energy_type=source_card.energy_type,
            card_type=source_card.card_type,
            hp=source_card.hp,
            attacks=[
                {
                    'name': attack['name'],
                    'cost': attack['cost'],
                    'damage': str(attack['damage']),
                    'effect': attack['effect_text']
                }
                for attack in source_card.attacks
            ],
            weakness=source_card.weakness,
            retreat_cost=source_card.retreat_cost
        )
        deck_cards.append(card)
    
    # Add cards to deck
    for card in deck_cards:
        deck.add_card(card)
    
    # Set deck types for energy generation
    deck.deck_types = [deck_type.title()]
    
    logger = logging.getLogger(__name__)
    logger.info(f"Created {deck_type} deck with {len(deck.cards)} cards from {len(basic_pokemon)} available basic Pokemon")
    
    return deck


def run_single_battle(deck1: Deck, 
                     deck2: Deck, 
                     battle_id: str = None,
                     rng_seed: int = None,
                     debug: bool = False,
                     logger: logging.Logger = None) -> BattleResult:
    """Run a single battle between two decks"""
    
    if logger is None:
        logger = logging.getLogger(__name__)
    
    try:
        # Initialize game state
        game_state = GameState(
            player_decks=[deck1, deck2],
            battle_id=battle_id or f"demo_battle_{int(time.time())}",
            rng_seed=rng_seed,
            logger=logger
        )
        
        # Initialize AI players
        ai_players = [
            RuleBasedAI(player_id=0, logger=logger, rng_seed=rng_seed),
            RuleBasedAI(player_id=1, logger=logger, rng_seed=rng_seed)
        ]
        
        # Set different strategies for variety
        ai_players[0].set_strategy("balanced")
        ai_players[1].set_strategy("aggro")
        
        # Start the battle
        if not game_state.start_battle():
            logger.error("Failed to start battle")
            return None
            
        logger.info(f"Battle {game_state.battle_id} started!")
        
        # Battle loop
        turn_count = 0
        max_actions_per_turn = 10  # Prevent infinite loops
        
        while not game_state.is_battle_over() and turn_count < 1000:
            # Determine which player should act based on game phase
            from simulator.core.game import GamePhase
            if game_state.phase == GamePhase.FORCED_POKEMON_SELECTION:
                # During forced selection, only the forced_selection_player can act
                acting_player = game_state.forced_selection_player
            else:
                # Normal turn - current player acts
                acting_player = game_state.current_player
                
            ai_player = ai_players[acting_player]
            
            if debug:
                phase_info = f" ({game_state.phase.value})" if hasattr(game_state, 'phase') else ""
                if game_state.phase == GamePhase.FORCED_POKEMON_SELECTION:
                    logger.info(f"\n--- Turn {game_state.turn_number}, Player {acting_player} FORCED SELECTION{phase_info} ---")
                else:
                    logger.info(f"\n--- Turn {game_state.turn_number}, Player {acting_player}{phase_info} ---")
                logger.info(f"Player {acting_player}: {game_state.players[acting_player]}")
                logger.info(f"Player {1-acting_player}: {game_state.players[1-acting_player]}")
            
            actions_this_turn = 0
            
            # Player takes actions until they end turn or battle ends or acting player changes
            initial_acting_player = acting_player
            while (acting_player == initial_acting_player and 
                   not game_state.is_battle_over() and 
                   actions_this_turn < max_actions_per_turn):
                
                # AI chooses action
                action = ai_player.choose_action(game_state)
                
                if action is None:
                    logger.warning(f"AI Player {acting_player} returned no action, ending turn")
                    action = ai_player._create_end_turn_action()
                
                if debug:
                    logger.info(f"Player {acting_player} chose action: {action.action_type.value} with details: {action.details}")
                
                # Execute action
                success = game_state.execute_action(action)
                
                if not success:
                    logger.warning(f"Action failed for player {acting_player}: {action.action_type.value}")
                    # Force end turn on failed action to prevent infinite loops
                    end_turn_action = ai_player._create_end_turn_action()
                    game_state.execute_action(end_turn_action)
                    break
                
                actions_this_turn += 1
                
                # Re-determine acting player after each action (phase might have changed)
                new_acting_player = game_state.forced_selection_player if game_state.phase == GamePhase.FORCED_POKEMON_SELECTION else game_state.current_player
                if new_acting_player != acting_player:
                    acting_player = new_acting_player
                    ai_player = ai_players[acting_player]
            
            # Only increment turn count for completed turns, not forced selections
            if game_state.phase != GamePhase.FORCED_POKEMON_SELECTION:
                turn_count += 1
            
            # Safety check for infinite loops
            if actions_this_turn >= max_actions_per_turn:
                logger.warning(f"Turn action limit reached for player {acting_player}")
        
        # Get battle result
        result = game_state.get_battle_result()
        
        # Log result
        if result.is_tie:
            logger.info(f"Battle ended in a tie after {result.total_turns} turns ({result.end_reason})")
        else:
            logger.info(f"Player {result.winner} wins after {result.total_turns} turns ({result.end_reason})")
            logger.info(f"Final scores: {result.final_scores}")
        
        logger.info(f"Battle duration: {result.duration_seconds:.3f} seconds")
        
        return result
        
    except Exception as e:
        logger.error(f"Battle failed: {e}")
        return None


def run_multiple_battles(num_battles: int = 10,
                        deck_types: List[str] = None,
                        rng_seed: int = None,
                        logger: logging.Logger = None) -> List[BattleResult]:
    """Run multiple battles for analysis"""
    
    if logger is None:
        logger = logging.getLogger(__name__)
    
    if deck_types is None:
        deck_types = ["fire", "water"]
    
    # Create card collection
    collection = create_sample_card_collection()
    
    results = []
    
    for i in range(num_battles):
        # Create decks
        deck1 = create_sample_deck(collection, deck_types[0])
        deck2 = create_sample_deck(collection, deck_types[1])
        
        # Use different seed for each battle
        battle_seed = (rng_seed + i) if rng_seed else None
        
        logger.info(f"\n=== Battle {i+1}/{num_battles} ===")
        
        result = run_single_battle(
            deck1=deck1,
            deck2=deck2,
            battle_id=f"multi_battle_{i+1}",
            rng_seed=battle_seed,
            debug=False,
            logger=logger
        )
        
        if result:
            results.append(result)
    
    # Analyze results
    if results:
        analyze_battle_results(results, deck_types, logger)
    
    return results


def run_multiple_real_card_battles(battle_cards: List[BattleCard],
                                  num_battles: int = 10,
                                  deck_types: List[str] = None,
                                  rng_seed: int = None,
                                  logger: logging.Logger = None) -> List[BattleResult]:
    """Run multiple battles using real cards for analysis"""
    
    if logger is None:
        logger = logging.getLogger(__name__)
    
    if deck_types is None:
        deck_types = ["fire", "water"]
    
    results = []
    
    for i in range(num_battles):
        # Create decks using real cards
        deck1 = create_real_card_deck(battle_cards, deck_types[0])
        deck2 = create_real_card_deck(battle_cards, deck_types[1])
        
        # Use different seed for each battle
        battle_seed = (rng_seed + i) if rng_seed else None
        
        logger.info(f"\n=== Battle {i+1}/{num_battles} (Real Cards) ===")
        
        result = run_single_battle(
            deck1=deck1,
            deck2=deck2,
            battle_id=f"real_battle_{i+1}",
            rng_seed=battle_seed,
            debug=False,
            logger=logger
        )
        
        if result:
            results.append(result)
    
    # Analyze results
    if results:
        analyze_battle_results(results, deck_types, logger)
    
    return results


def analyze_battle_results(results: List[BattleResult], 
                          deck_types: List[str],
                          logger: logging.Logger):
    """Analyze and report on battle results"""
    
    total_battles = len(results)
    
    if total_battles == 0:
        logger.info("No battles to analyze")
        return
    
    # Win statistics
    player_0_wins = sum(1 for r in results if r.winner == 0)
    player_1_wins = sum(1 for r in results if r.winner == 1)
    ties = sum(1 for r in results if r.is_tie)
    
    # Duration statistics
    durations = [r.duration_seconds for r in results]
    avg_duration = sum(durations) / len(durations)
    min_duration = min(durations)
    max_duration = max(durations)
    
    # Turn statistics
    turns = [r.total_turns for r in results]
    avg_turns = sum(turns) / len(turns)
    min_turns = min(turns)
    max_turns = max(turns)
    
    # End reason statistics
    end_reasons = {}
    for result in results:
        end_reasons[result.end_reason] = end_reasons.get(result.end_reason, 0) + 1
    
    # Report
    logger.info(f"\n=== BATTLE ANALYSIS ({total_battles} battles) ===")
    logger.info(f"Deck Types: {deck_types[0]} vs {deck_types[1]}")
    logger.info(f"")
    logger.info(f"Win Statistics:")
    logger.info(f"  Player 0 ({deck_types[0]}): {player_0_wins}/{total_battles} ({player_0_wins/total_battles*100:.1f}%)")
    logger.info(f"  Player 1 ({deck_types[1]}): {player_1_wins}/{total_battles} ({player_1_wins/total_battles*100:.1f}%)")
    logger.info(f"  Ties: {ties}/{total_battles} ({ties/total_battles*100:.1f}%)")
    logger.info(f"")
    logger.info(f"Duration Statistics:")
    logger.info(f"  Average: {avg_duration:.3f}s")
    logger.info(f"  Range: {min_duration:.3f}s - {max_duration:.3f}s")
    logger.info(f"")
    logger.info(f"Turn Statistics:")
    logger.info(f"  Average: {avg_turns:.1f}")
    logger.info(f"  Range: {min_turns} - {max_turns}")
    logger.info(f"")
    logger.info(f"End Reasons:")
    for reason, count in end_reasons.items():
        logger.info(f"  {reason}: {count}/{total_battles} ({count/total_battles*100:.1f}%)")


def main():
    """Main entry point for battle simulator demo"""
    
    parser = argparse.ArgumentParser(description="Pokemon TCG Pocket Battle Simulator Demo")
    parser.add_argument("--battles", "-b", type=int, default=1,
                       help="Number of battles to run (default: 1)")
    parser.add_argument("--deck1", type=str, default="fire",
                       choices=["fire", "water", "grass", "lightning", "mixed", "colorless"],
                       help="Player 1 deck type (default: fire)")
    parser.add_argument("--deck2", type=str, default="water", 
                       choices=["fire", "water", "grass", "lightning", "mixed", "colorless"],
                       help="Player 2 deck type (default: water)")
    parser.add_argument("--seed", "-s", type=int, default=None,
                       help="Random seed for reproducible battles")
    parser.add_argument("--debug", "-d", action="store_true",
                       help="Enable debug logging and detailed output")
    parser.add_argument("--log-level", type=str, default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level (default: INFO)")
    parser.add_argument("--output", "-o", type=str, default=None,
                       help="Output file for battle results (JSON format)")
    parser.add_argument("--use-sample-cards", action="store_true",
                       help="Use sample cards instead of real card database")
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_level)
    
    logger.info("Pokemon TCG Pocket Battle Simulator Demo")
    logger.info("=" * 50)
    
    if args.seed:
        logger.info(f"Using random seed: {args.seed}")
        random.seed(args.seed)
    
    # Choose card source
    if args.use_sample_cards:
        # Use sample cards (legacy mode)
        collection = create_sample_card_collection()
        logger.info(f"Using sample collection with {len(collection)} cards")
        
        # Create decks using sample cards
        deck1 = create_sample_deck(collection, args.deck1)
        deck2 = create_sample_deck(collection, args.deck2)
    else:
        # Use real cards (default mode)
        battle_cards = create_real_card_collection(logger)
        logger.info(f"Using real card collection with {len(battle_cards)} cards")
        
        # Create decks using real cards
        deck1 = create_real_card_deck(battle_cards, args.deck1)
        deck2 = create_real_card_deck(battle_cards, args.deck2)
    
    try:
        if args.battles == 1:
            # Single battle mode
            logger.info(f"Created decks: {args.deck1} vs {args.deck2}")
            
            result = run_single_battle(
                deck1=deck1,
                deck2=deck2,
                rng_seed=args.seed,
                debug=args.debug,
                logger=logger
            )
            
            if result and args.output:
                with open(args.output, 'w') as f:
                    json.dump(result.to_dict(), f, indent=2)
                logger.info(f"Battle result saved to {args.output}")
                
        else:
            # Multiple battles mode
            if args.use_sample_cards:
                results = run_multiple_battles(
                    num_battles=args.battles,
                    deck_types=[args.deck1, args.deck2],
                    rng_seed=args.seed,
                    logger=logger
                )
            else:
                results = run_multiple_real_card_battles(
                    battle_cards=battle_cards,
                    num_battles=args.battles,
                    deck_types=[args.deck1, args.deck2],
                    rng_seed=args.seed,
                    logger=logger
                )
            
            if results and args.output:
                results_data = [r.to_dict() for r in results]
                with open(args.output, 'w') as f:
                    json.dump(results_data, f, indent=2)
                logger.info(f"Battle results saved to {args.output}")
    
    except KeyboardInterrupt:
        logger.info("\nBattle simulation interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Battle simulation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()