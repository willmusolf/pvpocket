from flask import Blueprint, render_template, jsonify, request, current_app
from flask_socketio import emit, disconnect, join_room, leave_room
import sys
import os
import io
import contextlib
import logging
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add the project root to the path so we can import battle_main
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from battle_main import run_single_battle, create_sample_card_collection, create_sample_deck, create_real_card_collection, create_real_card_deck
    from simulator.core.game import GameState, BattleAction, ActionType
    from simulator.ai.rule_based import RuleBasedAI
    from simulator.core.card_bridge import load_real_card_collection, create_battle_deck_from_real_cards
    from simulator.core.effect_engine import create_comprehensive_effect_system
except ImportError as e:
    print(f"Could not import battle dependencies: {e}")

battle_bp = Blueprint("battle", __name__)

# In-memory storage for active battles (in production, use Redis)
active_battles: Dict[str, Dict[str, Any]] = {}

# Simple undo system for sandbox mode
battle_undo_stacks: Dict[str, List[Dict[str, Any]]] = {}

# Global reference to SocketIO instance for emitting from HTTP routes
_socketio = None


@battle_bp.route("/battle-simulator")
def battle():
    return render_template("battle_simulator.html")


@battle_bp.route("/api/test-battle")
def test_battle():
    """API endpoint to test advanced Phase 2B battle simulator with real cards"""
    try:
        # Capture battle output
        log_capture_string = io.StringIO()
        
        # Create a simple logger that writes to our string
        logger = logging.getLogger('battle_test')
        logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Add string handler
        ch = logging.StreamHandler(log_capture_string)
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # Try to load real cards first, fallback to sample cards
        try:
            real_cards = load_real_card_collection(logger)
            if real_cards and len(real_cards) > 20:
                deck1 = create_real_card_deck(real_cards, "fire")
                deck2 = create_real_card_deck(real_cards, "water")
                card_type = "real"
                logger.info(f"Using real cards: {len(real_cards)} available")
            else:
                raise ValueError("Not enough real cards available")
        except Exception as e:
            logger.warning(f"Real cards not available ({e}), using sample cards")
            collection = create_sample_card_collection()
            deck1 = create_sample_deck(collection, "fire")
            deck2 = create_sample_deck(collection, "water")
            card_type = "sample"
        
        # Run battle with advanced features
        result = run_single_battle(
            deck1=deck1,
            deck2=deck2,
            battle_id="web_test_battle_advanced",
            rng_seed=42,
            debug=True,
            logger=logger
        )
        
        # Get the captured log
        log_contents = log_capture_string.getvalue()
        
        if result:
            return jsonify({
                "success": True,
                "winner": result.winner if not result.is_tie else "Tie",
                "turns": result.total_turns,
                "duration": f"{result.duration_seconds:.3f}s",
                "final_scores": result.final_scores,
                "end_reason": result.end_reason,
                "battle_log": log_contents,
                "deck_types": ["fire", "water"],
                "card_type": card_type,
                "features": ["status_conditions", "coin_flips", "trainer_cards", "evolution", "real_cards" if card_type == "real" else "sample_cards"]
            })
        else:
            return jsonify({
                "success": False,
                "error": "Battle failed to complete",
                "battle_log": log_contents,
                "card_type": card_type
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "battle_log": f"Error running battle: {e}"
        })


@battle_bp.route("/api/battle/start", methods=["POST"])
def start_battle():
    """Start a new interactive battle for React frontend"""
    try:
        data = request.get_json() or {}
        
        # Get deck types from request
        deck1_type = data.get("deck1_type", "fire")
        deck2_type = data.get("deck2_type", "water")
        battle_mode = data.get("mode", "ai_vs_ai")  # "ai_vs_ai", "human_vs_ai"
        rng_seed = data.get("seed", None)
        
        # Create unique battle ID
        battle_id = str(uuid.uuid4())
        
        # Try to load real cards first, fallback to sample cards
        try:
            real_cards = load_real_card_collection()
            if real_cards and len(real_cards) > 20:
                deck1 = create_real_card_deck(real_cards, deck1_type)
                deck2 = create_real_card_deck(real_cards, deck2_type)
                card_type = "real"
            else:
                raise ValueError("Not enough real cards available")
        except Exception:
            # Fallback to sample cards
            collection = create_sample_card_collection()
            deck1 = create_sample_deck(collection, deck1_type)
            deck2 = create_sample_deck(collection, deck2_type)
            card_type = "sample"
        
        # Create logger for this battle
        logger = logging.getLogger(f'battle_{battle_id}')
        logger.setLevel(logging.INFO)
        
        # Create game state
        game_state = GameState(
            player_decks=[deck1, deck2],
            battle_id=battle_id,
            rng_seed=rng_seed,
            logger=logger
        )
        
        # Start the battle
        if not game_state.start_battle():
            return jsonify({
                "success": False,
                "error": "Failed to start battle"
            })
        
        # Create AI players
        ai_players = [
            RuleBasedAI(player_id=0, logger=logger, rng_seed=rng_seed),
            RuleBasedAI(player_id=1, logger=logger, rng_seed=rng_seed)
        ]
        
        # Store battle state
        active_battles[battle_id] = {
            "game_state": game_state,
            "ai_players": ai_players,
            "mode": battle_mode,
            "deck_types": [deck1_type, deck2_type],
            "card_type": card_type,
            "created_at": time.time(),
            "turn_log": [],
            "features_used": []
        }
        
        return jsonify({
            "success": True,
            "battle_id": battle_id,
            "mode": battle_mode,
            "deck_types": [deck1_type, deck2_type],
            "card_type": card_type,
            "current_state": get_battle_state_dict(game_state)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })


@battle_bp.route("/api/battle/<battle_id>/state")
def get_battle_state(battle_id: str):
    """Get current state of a battle"""
    try:
        if battle_id not in active_battles:
            return jsonify({
                "success": False,
                "error": "Battle not found"
            })
        
        battle_data = active_battles[battle_id]
        game_state = battle_data["game_state"]
        
        return jsonify({
            "success": True,
            "battle_id": battle_id,
            "state": get_battle_state_dict(game_state),
            "is_over": game_state.is_battle_over(),
            "winner": game_state.winner,
            "turn_log": battle_data["turn_log"][-10:]  # Last 10 actions
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })


@battle_bp.route("/api/battle/<battle_id>/step", methods=["POST"])
def execute_battle_step(battle_id: str):
    """Execute the next turn/action in a battle"""
    try:
        if battle_id not in active_battles:
            return jsonify({
                "success": False,
                "error": "Battle not found"
            })
        
        battle_data = active_battles[battle_id]
        game_state = battle_data["game_state"]
        ai_players = battle_data["ai_players"]
        
        if game_state.is_battle_over():
            return jsonify({
                "success": False,
                "error": "Battle is already over"
            })
        
        # Determine which player should act based on game phase
        from simulator.core.game import GamePhase
        if game_state.phase == GamePhase.FORCED_POKEMON_SELECTION:
            # During forced selection, only the forced_selection_player can act
            acting_player = game_state.forced_selection_player
        else:
            # Normal turn - current player acts
            acting_player = game_state.current_player
        
        ai_player = ai_players[acting_player]
        
        # AI chooses action
        action = ai_player.choose_action(game_state)
        
        if action is None:
            action = ai_player._create_end_turn_action()
        
        # Log the action
        action_log = {
            "turn": game_state.turn_number,
            "player": acting_player,  # Use acting_player instead of current_player
            "action": action.action_type.value,
            "details": action.details,
            "timestamp": time.time() * 1000  # Convert to milliseconds for JavaScript
        }
        battle_data["turn_log"].append(action_log)
        
        # Execute action
        success = game_state.execute_action(action)
        
        return jsonify({
            "success": True,
            "action_executed": action.to_dict(),
            "action_success": success,
            "state": get_battle_state_dict(game_state),
            "is_over": game_state.is_battle_over(),
            "winner": game_state.winner,
            "last_action": action_log
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })


@battle_bp.route("/api/battle/<battle_id>/auto-play", methods=["POST"])
def auto_play_battle(battle_id: str):
    """Auto-play battle to completion"""
    try:
        if battle_id not in active_battles:
            return jsonify({
                "success": False,
                "error": "Battle not found"
            })
        
        battle_data = active_battles[battle_id]
        game_state = battle_data["game_state"]
        ai_players = battle_data["ai_players"]
        
        # Import for phase checking
        from simulator.core.game import GamePhase
        
        max_actions = 200  # Safety limit
        actions_taken = 0
        
        while not game_state.is_battle_over() and actions_taken < max_actions:
            # Determine which player should act based on game phase
            if game_state.phase == GamePhase.FORCED_POKEMON_SELECTION:
                # During forced selection, only the forced_selection_player can act
                acting_player = game_state.forced_selection_player
            else:
                # Normal turn - current player acts
                acting_player = game_state.current_player
            
            ai_player = ai_players[acting_player]
            
            # AI chooses action
            action = ai_player.choose_action(game_state)
            
            if action is None:
                action = ai_player._create_end_turn_action()
            
            # Log the action
            action_log = {
                "turn": game_state.turn_number,
                "player": acting_player,  # Use acting_player instead of current_player
                "action": action.action_type.value,
                "details": action.details,
                "timestamp": time.time() * 1000  # Convert to milliseconds for JavaScript
            }
            battle_data["turn_log"].append(action_log)
            
            # Execute action
            success = game_state.execute_action(action)
            actions_taken += 1
            
            # Check if battle ended naturally after this action
            if game_state.is_battle_over():
                current_app.logger.info(f"Battle ended naturally after {actions_taken} actions - Winner: {game_state.winner}, Tie: {game_state.is_tie}")
                break
        
        # Only force tie if we hit action limit AND battle is still not over
        if actions_taken >= max_actions and not game_state.is_battle_over():
            current_app.logger.warning(f"Forcing tie due to action limit: {actions_taken} actions, battle not naturally ended")
            # Force end the battle as a tie due to action limit
            game_state._end_battle_tie("action_limit_reached")
            battle_data["turn_log"].append({
                "turn": game_state.turn_number,
                "player": -1,  # System action
                "action": "force_end_tie",
                "details": {"reason": "Maximum action limit reached", "actions_taken": actions_taken},
                "timestamp": time.time() * 1000  # Convert to milliseconds for JavaScript
            })
        elif game_state.is_battle_over():
            current_app.logger.info(f"Battle completed naturally: Winner={game_state.winner}, Tie={game_state.is_tie}, End reason={game_state.end_reason}")
        
        # Get final result
        result = game_state.get_battle_result()
        
        return jsonify({
            "success": True,
            "result": result.to_dict(),
            "total_actions": actions_taken,
            "final_state": get_battle_state_dict(game_state)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })


@battle_bp.route("/api/battle/<battle_id>/log")
def get_battle_log(battle_id: str):
    """Get complete battle log"""
    try:
        if battle_id not in active_battles:
            return jsonify({
                "success": False,
                "error": "Battle not found"
            })
        
        battle_data = active_battles[battle_id]
        
        return jsonify({
            "success": True,
            "battle_id": battle_id,
            "turn_log": battle_data["turn_log"],
            "deck_types": battle_data["deck_types"],
            "mode": battle_data["mode"]
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })


def get_battle_state_dict(game_state: GameState) -> Dict[str, Any]:
    """Convert game state to dictionary for API"""
    try:
        def serialize_pokemon(pokemon):
            """Helper function to serialize a Pokemon with full card data"""
            if not pokemon:
                return None
            return {
                "card": {
                    "id": getattr(pokemon.card, 'id', 0),
                    "name": pokemon.card.name,
                    "card_type": getattr(pokemon.card, 'card_type', 'Pokemon'),
                    "energy_type": getattr(pokemon.card, 'energy_type', 'Colorless'),
                    "hp": getattr(pokemon.card, 'hp', 0),
                    "attacks": getattr(pokemon.card, 'attacks', []),
                    "abilities": getattr(pokemon.card, 'abilities', []),
                    "weakness": getattr(pokemon.card, 'weakness', None),
                    "retreat_cost": getattr(pokemon.card, 'retreat_cost', 0),
                    "evolution_stage": getattr(pokemon.card, 'evolution_stage', 0),
                    "evolves_from": getattr(pokemon.card, 'evolves_from', None),
                    "is_ex": getattr(pokemon.card, 'is_ex', False),
                    "rarity": getattr(pokemon.card, 'rarity', 'Common'),
                    "set_name": getattr(pokemon.card, 'set_name', 'Unknown'),
                    "firebase_image_url": getattr(pokemon.card, 'firebase_image_url', '')
                },
                "current_hp": pokemon.current_hp,
                "max_hp": pokemon.max_hp,
                "status_conditions": [
                    {
                        "condition": status.condition.value if hasattr(status, 'condition') else str(status),
                        "duration": getattr(status, 'duration', 1)
                    } 
                    for status in getattr(pokemon, 'status_conditions', [])
                ],
                "attached_energy": getattr(pokemon, 'energy_attached', []),
                "damage_taken": getattr(pokemon, 'damage_taken', 0)
            }
        
        return {
            "battle_id": getattr(game_state, 'battle_id', 'unknown'),
            "current_turn": game_state.turn_number,
            "current_player": game_state.current_player,
            "phase": game_state.phase.value,
            "forced_selection_player": getattr(game_state, 'forced_selection_player', None),
            "players": [
                {
                    "player_id": i,
                    "active_pokemon": serialize_pokemon(player.active_pokemon),
                    "bench": [serialize_pokemon(pokemon) for pokemon in player.bench[:3]],  # Limit to 3 bench slots
                    "hand": [
                        {
                            "id": getattr(card, 'id', 0),
                            "name": getattr(card, 'name', 'Unknown'),
                            "card_type": getattr(card, 'card_type', 'Unknown'),
                            "energy_type": getattr(card, 'energy_type', 'Colorless'),
                            "hp": getattr(card, 'hp', None),
                            "attacks": getattr(card, 'attacks', []),
                            "abilities": getattr(card, 'abilities', []),
                            "weakness": getattr(card, 'weakness', None),
                            "retreat_cost": getattr(card, 'retreat_cost', None),
                            "evolution_stage": getattr(card, 'evolution_stage', None),
                            "evolves_from": getattr(card, 'evolves_from', None),
                            "is_ex": getattr(card, 'is_ex', False),
                            "rarity": getattr(card, 'rarity', 'Common'),
                            "set_name": getattr(card, 'set_name', 'Unknown'),
                            "firebase_image_url": getattr(card, 'firebase_image_url', '')
                        } for card in (getattr(player, 'hand', []) or [])
                    ],
                    "deck": [
                        {
                            "id": getattr(card, 'id', 0),
                            "name": getattr(card, 'name', 'Unknown'),
                            "card_type": getattr(card, 'card_type', 'Unknown'),
                            "energy_type": getattr(card, 'energy_type', 'Colorless'),
                            "hp": getattr(card, 'hp', None),
                            "attacks": getattr(card, 'attacks', []),
                            "abilities": getattr(card, 'abilities', []),
                            "weakness": getattr(card, 'weakness', None),
                            "retreat_cost": getattr(card, 'retreat_cost', None),
                            "evolution_stage": getattr(card, 'evolution_stage', None),
                            "evolves_from": getattr(card, 'evolves_from', None),
                            "is_ex": getattr(card, 'is_ex', False),
                            "rarity": getattr(card, 'rarity', 'Common'),
                            "set_name": getattr(card, 'set_name', 'Unknown'),
                            "firebase_image_url": getattr(card, 'firebase_image_url', '')
                        } for card in (getattr(player, 'deck_cards', []) or [])
                    ],
                    "discard": [],
                    "prize_points": player.prize_points,
                    "energy_attached_this_turn": getattr(player, 'energy_attached_this_turn', False),
                    "setup_ready": getattr(player, 'setup_ready', False),
                    "energy_per_turn": getattr(player, 'energy_per_turn', 1)
                }
                for i, player in enumerate(game_state.players)
            ],
            "winner": getattr(game_state, 'winner', None),
            "is_tie": getattr(game_state, 'is_tie', False)
        }
    except Exception as e:
        # Fallback for any missing data
        return {
            "error": f"Failed to serialize game state: {e}",
            "battle_id": getattr(game_state, 'battle_id', 'unknown'),
            "current_turn": getattr(game_state, 'turn_number', 0),
            "current_player": getattr(game_state, 'current_player', 0),
            "phase": "error",
            "players": []
        }


@battle_bp.route("/api/cards/search")
def search_cards():
    """Search for cards by name for testing interface"""
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 10))
        
        if len(query) < 2:
            return jsonify({"success": True, "cards": []})
            
        # Load real cards for searching
        try:
            real_cards = load_real_card_collection()
            if not real_cards:
                raise ValueError("No real cards available")
                
            # Filter cards by name
            matching_cards = []
            for card in real_cards:
                if query.lower() in card.name.lower():
                    card_dict = {
                        "id": card.id,
                        "name": card.name,
                        "energy_type": card.energy_type,
                        "card_type": card.card_type,
                        "hp": card.hp,
                        "attacks": card.attacks,
                        "weakness": card.weakness,
                        "retreat_cost": card.retreat_cost
                    }
                    matching_cards.append(card_dict)
                    
                    if len(matching_cards) >= limit:
                        break
                        
            return jsonify({
                "success": True,
                "cards": matching_cards,
                "total_found": len(matching_cards)
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to search cards: {e}",
                "cards": []
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "cards": []
        })


@battle_bp.route("/api/test-abilities")
def test_abilities():
    """Run comprehensive ability tests"""
    try:
        # Import the test battle features module
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from test_battle_features import BattleFeatureTester
        
        # Run the tests
        tester = BattleFeatureTester()
        results = tester.run_all_tests()
        
        # Calculate summary statistics
        total_tests = 0
        passed_tests = 0
        categories = {}
        
        for category, category_results in results.items():
            category_total = len(category_results)
            category_passed = sum(1 for success in category_results.values() if success)
            total_tests += category_total
            passed_tests += category_passed
            
            categories[category] = {
                "total": category_total,
                "passed": category_passed,
                "success_rate": round((category_passed / category_total * 100) if category_total > 0 else 0)
            }
        
        success_rate = round((passed_tests / total_tests * 100) if total_tests > 0 else 0)
        
        return jsonify({
            "success": True,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": success_rate,
            "categories": categories,
            "detailed_results": results
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Ability tests failed: {e}"
        })


@battle_bp.route("/api/test-features")
def test_features():
    """Run feature validation tests"""
    try:
        # Import and run battle features test
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from test_battle_features import BattleFeatureTester
        
        tester = BattleFeatureTester()
        results = tester.run_all_tests()
        
        return jsonify({
            "success": True,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Feature tests failed: {e}"
        })


# Development Testing Endpoints
@battle_bp.route("/api/dev/cards/search")
def dev_search_cards():
    """Development endpoint to search cards for React testing panel"""
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 20))
        
        if len(query) < 2:
            return jsonify({"success": True, "cards": []})
            
        # Load real cards for searching
        try:
            real_cards = load_real_card_collection()
            if not real_cards:
                raise ValueError("No real cards available")
                
            # Filter cards by name
            matching_cards = []
            for card in real_cards:
                if query.lower() in card.name.lower():
                    # Convert to React-compatible format
                    card_dict = {
                        "id": card.id,
                        "name": card.name,
                        "card_type": card.card_type,
                        "energy_type": card.energy_type,
                        "hp": card.hp,
                        "attacks": card.attacks or [],
                        "abilities": getattr(card, 'abilities', []) or [],
                        "weakness": card.weakness,
                        "retreat_cost": card.retreat_cost,
                        "evolution_stage": getattr(card, 'evolution_stage', None),
                        "evolves_from": getattr(card, 'evolves_from', None),
                        "is_ex": getattr(card, 'is_ex', False),
                        "rarity": getattr(card, 'rarity', 'Common'),
                        "set_name": getattr(card, 'set_name', 'Unknown'),
                        "firebase_image_url": getattr(card, 'firebase_image_url', '')
                    }
                    matching_cards.append(card_dict)
                    
                    if len(matching_cards) >= limit:
                        break
                        
            return jsonify({
                "success": True,
                "cards": matching_cards,
                "total_found": len(matching_cards)
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to search cards: {e}",
                "cards": []
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "cards": []
        })


@battle_bp.route("/api/dev/battle/manipulate", methods=["POST"])
def dev_manipulate_battle():
    """Development endpoint to manipulate battle state for testing"""
    try:
        data = request.get_json()
        action_type = data.get('type')
        
        # Get battle_id from request or use any active battle
        battle_id = data.get('battle_id')
        
        if battle_id and battle_id in active_battles:
            # Use the specific battle requested
            battle_data = active_battles[battle_id]
        elif active_battles:
            # Fallback: use any active battle
            battle_id = list(active_battles.keys())[0]
            battle_data = active_battles[battle_id]
        else:
            return jsonify({
                "success": False,
                "error": "No active battles to manipulate"
            })
        
        game_state = battle_data["game_state"]
        print(f"🎯 SANDBOX: Using battle_id: {battle_id}")
        print(f"🔧 SANDBOX: Action type: {action_type}")
        
        # Sandbox manipulation actions
        if action_type == 'place_card':
            # Place any card in hand/active/bench for either player
            card_id = data.get('card_id')
            player_id = data.get('player_id', data.get('player', 0))  # Support both 'player_id' and 'player'
            position = data.get('position')  # 'hand', 'active', 'bench'
            bench_index = data.get('bench_index', 0)  # For bench placement
            
            # Load the real card by ID
            try:
                real_cards = load_real_card_collection()
                selected_card = None
                for card in real_cards:
                    if card.id == card_id:
                        selected_card = card
                        break
                
                if not selected_card:
                    return jsonify({
                        "success": False,
                        "error": f"Card with ID {card_id} not found"
                    })
                
                player = game_state.players[player_id]
                print(f"🔍 SANDBOX: Targeting Player {player_id} ({['Player 1', 'Player 2'][player_id]}) - Current Active: {getattr(player.active_pokemon.card, 'name', 'None') if player.active_pokemon else 'None'}")
                
                if position == 'hand':
                    # Add to hand
                    player.hand.append(selected_card)
                    message = f"Added {selected_card.name} to Player {player_id}'s hand"
                    
                elif position == 'active':
                    # Replace active Pokemon
                    from simulator.core.pokemon import BattlePokemon
                    battle_pokemon = BattlePokemon(selected_card, game_state.logger)
                    player.active_pokemon = battle_pokemon
                    message = f"Placed {selected_card.name} as Player {player_id}'s active Pokemon"
                    
                elif position == 'bench':
                    # Place on bench
                    from simulator.core.pokemon import BattlePokemon
                    battle_pokemon = BattlePokemon(selected_card, game_state.logger)
                    
                    # Ensure bench has enough slots
                    while len(player.bench) <= bench_index:
                        player.bench.append(None)
                    
                    player.bench[bench_index] = battle_pokemon
                    message = f"Placed {selected_card.name} on Player {player_id}'s bench slot {bench_index}"
                
                else:
                    return jsonify({
                        "success": False,
                        "error": f"Invalid position: {position}"
                    })
                
                # Emit updated game state via WebSocket to notify all clients in this battle room
                if _socketio:
                    print(f"🔄 SANDBOX: Emitting game_state_update via WebSocket after placing {selected_card.name} to room {battle_id}")
                    try:
                        game_state_data = get_battle_state_dict(game_state)
                        print(f"🔄 SANDBOX: Active Pokemon Player 0: {game_state_data.get('players', [{}])[0].get('active_pokemon', {}).get('card', {}).get('name', 'None')}")
                        _socketio.emit('game_state_update', {
                            'game_state': game_state_data,
                            'is_over': game_state.is_battle_over(),
                            'winner': getattr(game_state, 'winner', None)
                        }, room=battle_id)
                        print(f"✅ SANDBOX: Successfully emitted WebSocket update to room {battle_id}")
                    except Exception as e:
                        print(f"❌ SANDBOX: Failed to serialize game state or emit WebSocket: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("❌ SANDBOX: _socketio is None, cannot emit WebSocket update")
                
                return jsonify({
                    "success": True,
                    "message": message,
                    "card": selected_card.name
                })
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": f"Failed to place card: {e}"
                })
                
        elif action_type == 'attach_energy':
            # Add energy to any Pokemon (unlimited in sandbox)
            player_id = data.get('player_id', 0)
            target = data.get('target', 'active')  # 'active' or bench index
            energy_type = data.get('energy_type', 'Fire')
            amount = data.get('amount', 1)
            
            player = game_state.players[player_id]
            target_pokemon = None
            
            if target == 'active':
                target_pokemon = player.active_pokemon
            else:
                # Bench Pokemon by index
                bench_index = int(target)
                if 0 <= bench_index < len(player.bench) and player.bench[bench_index]:
                    target_pokemon = player.bench[bench_index]
            
            if target_pokemon:
                for _ in range(amount):
                    target_pokemon.attach_energy(energy_type)
                
                # Emit updated game state via WebSocket to notify all clients in this battle room
                if _socketio:
                    try:
                        game_state_data = get_battle_state_dict(game_state)
                        _socketio.emit('game_state_update', {
                            'game_state': game_state_data,
                            'is_over': game_state.is_battle_over(),
                            'winner': getattr(game_state, 'winner', None)
                        }, room=battle_id)
                        print(f"✅ SANDBOX: Emitted WebSocket update after energy attachment to room {battle_id}")
                    except Exception as e:
                        print(f"❌ SANDBOX: Failed to emit WebSocket update after energy attachment: {e}")
                
                return jsonify({
                    "success": True,
                    "message": f"Attached {amount}x {energy_type} energy to {target_pokemon.card.name}",
                    "energy_count": len(target_pokemon.energy_attached)
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "No target Pokemon found"
                })
                
        elif action_type == 'set_hp':
            # Set Pokemon HP to specific value
            player_id = data.get('player_id', 0)
            target = data.get('target', 'active')
            new_hp = data.get('hp', 100)
            
            player = game_state.players[player_id]
            target_pokemon = None
            
            if target == 'active':
                target_pokemon = player.active_pokemon
            else:
                # Bench Pokemon by index
                bench_index = int(target)
                if 0 <= bench_index < len(player.bench) and player.bench[bench_index]:
                    target_pokemon = player.bench[bench_index]
            
            if target_pokemon:
                # Clamp HP to valid range
                max_hp = target_pokemon.card.hp
                target_pokemon.current_hp = max(0, min(max_hp, new_hp))
                
                return jsonify({
                    "success": True,
                    "message": f"Set {target_pokemon.card.name} HP to {target_pokemon.current_hp}",
                    "current_hp": target_pokemon.current_hp,
                    "max_hp": max_hp
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "No target Pokemon found"
                })
                
        elif action_type == 'apply_status':
            # Apply status condition to Pokemon
            player_id = data.get('player_id', 0)
            target = data.get('target', 'active')
            status = data.get('status', 'asleep')  # 'asleep', 'burned', 'poisoned', etc.
            
            player = game_state.players[player_id]
            target_pokemon = None
            
            if target == 'active':
                target_pokemon = player.active_pokemon
            else:
                bench_index = int(target)
                if 0 <= bench_index < len(player.bench) and player.bench[bench_index]:
                    target_pokemon = player.bench[bench_index]
            
            if target_pokemon and game_state.effect_engine:
                from simulator.core.status_conditions import StatusCondition
                
                # Map string to status condition
                status_map = {
                    'asleep': StatusCondition.ASLEEP,
                    'burned': StatusCondition.BURNED,
                    'poisoned': StatusCondition.POISONED,
                    'paralyzed': StatusCondition.PARALYZED,
                    'confused': StatusCondition.CONFUSED
                }
                
                if status in status_map:
                    success, message = game_state.effect_engine.status_manager.apply_status_condition(
                        target_pokemon, status_map[status], game_state.turn_number
                    )
                    
                    return jsonify({
                        "success": success,
                        "message": message
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": f"Unknown status condition: {status}"
                    })
            else:
                return jsonify({
                    "success": False,
                    "error": "No target Pokemon found or no effect engine"
                })
                
        elif action_type == 'remove_pokemon':
            # Remove Pokemon from the game
            player_id = data.get('player_id', 0)
            target = data.get('target', 'active')
            
            player = game_state.players[player_id]
            
            if target == 'active':
                if player.active_pokemon:
                    pokemon_name = player.active_pokemon.card.name
                    player.active_pokemon = None
                    message = f"Removed {pokemon_name} from Player {player_id}'s active position"
                else:
                    return jsonify({
                        "success": False,
                        "error": "No active Pokemon to remove"
                    })
            else:
                bench_index = int(target)
                if 0 <= bench_index < len(player.bench) and player.bench[bench_index]:
                    pokemon_name = player.bench[bench_index].card.name
                    player.bench[bench_index] = None
                    message = f"Removed {pokemon_name} from Player {player_id}'s bench slot {bench_index}"
                else:
                    return jsonify({
                        "success": False,
                        "error": f"No Pokemon in bench slot {bench_index}"
                    })
            
            return jsonify({
                "success": True,
                "message": message
            })
            
        elif action_type == 'manipulate_hp':
            # Legacy HP manipulation (for backwards compatibility)
            target = data.get('target', 'active')
            player_id = data.get('player_id', 0)
            hp_change = data.get('hp_change', 0)
            
            player = game_state.players[player_id]
            if target == 'active' and player.active_pokemon:
                new_hp = max(0, min(
                    player.active_pokemon.max_hp,
                    player.active_pokemon.current_hp + hp_change
                ))
                player.active_pokemon.current_hp = new_hp
                
                return jsonify({
                    "success": True,
                    "message": f"Changed {target} Pokemon HP by {hp_change}",
                    "new_hp": new_hp
                })
            
        elif action_type == 'undo_action':
            # Undo the last sandbox action
            if battle_id in battle_undo_stacks and battle_undo_stacks[battle_id]:
                # Get the last saved state
                previous_state = battle_undo_stacks[battle_id].pop()
                
                # Restore game state (simplified - just restore key player data)
                try:
                    for i, saved_player in enumerate(previous_state.get('players', [])):
                        if i < len(game_state.players):
                            player = game_state.players[i]
                            
                            # Restore hand size (simplified)
                            hand_size_diff = len(saved_player.get('hand', [])) - len(player.hand)
                            if hand_size_diff > 0:
                                # Cards were removed, add placeholders
                                for _ in range(hand_size_diff):
                                    player.hand.append(None)  # Placeholder
                            elif hand_size_diff < 0:
                                # Cards were added, remove them
                                player.hand = player.hand[:len(saved_player.get('hand', []))]
                    
                    return jsonify({
                        "success": True,
                        "message": f"Undid last action (stack has {len(battle_undo_stacks[battle_id])} more actions)",
                        "undo_remaining": len(battle_undo_stacks[battle_id])
                    })
                    
                except Exception as e:
                    return jsonify({
                        "success": False,
                        "error": f"Undo failed: {e}"
                    })
            else:
                return jsonify({
                    "success": False,
                    "error": "No actions to undo"
                })
                
        elif action_type == 'clear_undo_stack':
            # Clear the undo stack
            if battle_id in battle_undo_stacks:
                battle_undo_stacks[battle_id] = []
            
            return jsonify({
                "success": True,
                "message": "Undo stack cleared"
            })
            
        elif action_type == 'load_test_card':
            # Legacy card loading (for backwards compatibility)
            card_data = data.get('card')
            if card_data:
                return jsonify({
                    "success": True,
                    "message": f"Test card '{card_data.get('name')}' loaded",
                    "card": card_data
                })
        
        return jsonify({
            "success": False,
            "error": f"Unknown manipulation type: {action_type}"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })


@battle_bp.route("/api/dev/battle/status")
def dev_battle_status():
    """Development endpoint to get current battle status"""
    try:
        status = {
            "active_battles": len(active_battles),
            "battle_list": []
        }
        
        for battle_id, battle_data in active_battles.items():
            game_state = battle_data["game_state"]
            status["battle_list"].append({
                "battle_id": battle_id,
                "mode": battle_data["mode"],
                "card_type": battle_data["card_type"],
                "current_turn": getattr(game_state, 'turn_number', 0),
                "current_player": getattr(game_state, 'current_player', 0),
                "is_over": game_state.is_battle_over() if hasattr(game_state, 'is_battle_over') else False,
                "winner": getattr(game_state, 'winner', None)
            })
        
        return jsonify({
            "success": True,
            "status": status
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })


# WebSocket Event Handlers
def register_battle_websocket_events(socketio):
    """Register WebSocket event handlers for battle simulator"""
    global _socketio
    _socketio = socketio
    
    @socketio.on('connect')
    def on_connect():
        """Handle client connection"""
        print(f"Client connected: {request.sid}")
        emit('connection_confirmed', {'status': 'connected', 'sid': request.sid})
    
    @socketio.on('disconnect')
    def on_disconnect():
        """Handle client disconnection"""
        print(f"Client disconnected: {request.sid}")
        # Clean up any active battles for this client
        battles_to_remove = []
        for battle_id, battle_data in active_battles.items():
            if battle_data.get('client_sid') == request.sid:
                battles_to_remove.append(battle_id)
        
        for battle_id in battles_to_remove:
            del active_battles[battle_id]
            print(f"Cleaned up battle {battle_id} for disconnected client")
    
    @socketio.on('create_battle')
    def handle_create_battle(data):
        """Create a new battle for WebSocket client"""
        try:
            mode = data.get('mode', 'test_battle')
            deck_config = data.get('deck_config', 'default')
            player_mode = data.get('player_mode', 'human_vs_ai')
            player1_deck_type = data.get('player1_deck', 'fire')
            player2_deck_type = data.get('player2_deck', 'water')
            
            # Create unique battle ID
            battle_id = f"ws_{str(uuid.uuid4())[:8]}"
            
            # Try to load real cards first, fallback to sample cards
            try:
                real_cards = load_real_card_collection()
                if real_cards and len(real_cards) > 20:
                    deck1 = create_real_card_deck(real_cards, player1_deck_type)
                    deck2 = create_real_card_deck(real_cards, player2_deck_type)
                    card_type = "real"
                else:
                    raise ValueError("Not enough real cards available")
            except Exception:
                # Fallback to sample cards
                collection = create_sample_card_collection()
                deck1 = create_sample_deck(collection, player1_deck_type)
                deck2 = create_sample_deck(collection, player2_deck_type)
                card_type = "sample"
            
            # Create logger for this battle
            logger = logging.getLogger(f'battle_{battle_id}')
            logger.setLevel(logging.INFO)
            
            # Create game state
            game_state = GameState(
                player_decks=[deck1, deck2],
                battle_id=battle_id,
                rng_seed=None,
                logger=logger
            )
            
            # Start the battle
            if not game_state.start_battle():
                emit('battle_error', {'error': 'Failed to start battle'})
                return
            
            # Create AI players based on player mode
            ai_players = []
            if player_mode == 'ai_vs_ai':
                # Both players are AI
                ai_players = [
                    RuleBasedAI(player_id=0, logger=logger),
                    RuleBasedAI(player_id=1, logger=logger)
                ]
            elif player_mode == 'human_vs_ai':
                # Player 1 is human, Player 2 is AI
                ai_players = [
                    None,  # Human player
                    RuleBasedAI(player_id=1, logger=logger)
                ]
            elif player_mode == 'human_vs_human':
                # Both players are human
                ai_players = [None, None]
            
            # Store battle state
            active_battles[battle_id] = {
                "game_state": game_state,
                "ai_players": ai_players,
                "mode": "manual",
                "player_mode": player_mode,
                "deck_types": [player1_deck_type, player2_deck_type],
                "card_type": card_type,
                "created_at": time.time(),
                "turn_log": [],
                "client_sid": request.sid
            }
            
            # Join battle room
            join_room(battle_id)
            
            emit('battle_created', {
                'battle_id': battle_id,
                'mode': mode,
                'player_mode': player_mode,
                'deck_types': [player1_deck_type, player2_deck_type],
                'card_type': card_type,
                'game_state': get_battle_state_dict(game_state)
            })
            
            # If AI vs AI, start auto-playing immediately
            if player_mode == 'ai_vs_ai':
                # Trigger AI turn processing
                emit('ai_turn_start', {'battle_id': battle_id})
                
                # Also trigger the first AI action immediately
                emit('ai_turn_needed', {
                    'battle_id': battle_id,
                    'current_player': game_state.current_player
                })
            
        except Exception as e:
            emit('battle_error', {'error': str(e)})
    
    @socketio.on('join_battle')
    def handle_join_battle(data):
        """Join an existing battle"""
        battle_id = data.get('battle_id')
        
        if not battle_id or battle_id not in active_battles:
            emit('battle_error', {'error': 'Battle not found'})
            return
        
        join_room(battle_id)
        battle_data = active_battles[battle_id]
        
        emit('battle_joined', {
            'battle_id': battle_id,
            'game_state': get_battle_state_dict(battle_data['game_state'])
        })
    
    @socketio.on('battle_action')
    def handle_battle_action(data):
        """Handle battle action from client"""
        try:
            # Find battle for this client
            battle_id = None
            for bid, battle_data in active_battles.items():
                if battle_data.get('client_sid') == request.sid:
                    battle_id = bid
                    break
            
            if not battle_id:
                emit('battle_error', {'error': 'No active battle found for this client'})
                return
            
            battle_data = active_battles[battle_id]
            game_state = battle_data["game_state"]
            ai_players = battle_data["ai_players"]
            
            if game_state.is_battle_over():
                emit('battle_error', {'error': 'Battle is already over'})
                return
            
            action_type = data.get('type')
            if not action_type:
                emit('battle_error', {'error': 'No action type specified'})
                return
                
            print(f"🎮 BATTLE ACTION: {action_type} from player {data.get('player_id', 0)}")
            
            # Handle different action types
            if action_type == 'use_ability':
                # Handle ability use
                player_id = data.get('player_id', 0)
                ability_data = data.get('data', {})
                ability_index = ability_data.get('ability_index', 0)
                
                from simulator.core.game import BattleAction, ActionType
                action = BattleAction(
                    action_type=ActionType.USE_ABILITY,
                    player_id=player_id,
                    details={'ability_index': ability_index}
                )
                
                success = game_state.execute_action(action)
                print(f"🔍 ACTION RESULT: {action_type} {'✅ SUCCESS' if success else '❌ FAILED'}")
                
                # Get the latest log entries with descriptive text
                recent_logs = game_state.turn_log[-3:] if game_state.turn_log else []
                
                emit('battle_action_result', {
                    'action_type': action_type,
                    'result': success,
                    'player_id': player_id,
                    'log_entries': recent_logs
                })
                
                if not success:
                    emit('battle_error', {'error': f'{action_type} failed to execute'})
                
            elif action_type == 'switch':
                # Handle Pokemon switch
                player_id = data.get('player_id', 0)
                switch_data = data.get('data', {})
                bench_index = switch_data.get('bench_index', 0)
                
                from simulator.core.game import BattleAction, ActionType
                action = BattleAction(
                    action_type=ActionType.SWITCH_POKEMON,
                    player_id=player_id,
                    details={'bench_index': bench_index}
                )
                
                success = game_state.execute_action(action)
                print(f"🔍 ACTION RESULT: {action_type} {'✅ SUCCESS' if success else '❌ FAILED'}")
                
                # Get the latest log entries with descriptive text
                recent_logs = game_state.turn_log[-3:] if game_state.turn_log else []
                
                emit('battle_action_result', {
                    'action_type': action_type,
                    'result': success,
                    'player_id': player_id,
                    'log_entries': recent_logs
                })
                
                if not success:
                    emit('battle_error', {'error': f'{action_type} failed to execute'})
                
            elif action_type == 'pass_turn':
                # End turn
                player_id = data.get('player_id', 0)
                
                from simulator.core.game import BattleAction, ActionType
                action = BattleAction(
                    action_type=ActionType.END_TURN,
                    player_id=player_id,
                    details={}
                )
                
                success = game_state.execute_action(action)
                print(f"🔍 ACTION RESULT: {action_type} {'✅ SUCCESS' if success else '❌ FAILED'}")
                
                # Get the latest log entries with descriptive text
                recent_logs = game_state.turn_log[-3:] if game_state.turn_log else []
                
                emit('battle_action_result', {
                    'action_type': action_type,
                    'result': success,
                    'player_id': player_id,
                    'log_entries': recent_logs
                })
                
                if not success:
                    emit('battle_error', {'error': f'{action_type} failed to execute'})
                
            elif action_type == 'play_pokemon':
                # Place Pokemon from hand
                player_id = data.get('player_id', 0)
                play_data = data.get('data', {})
                hand_index = play_data.get('hand_index', 0)
                target_slot = play_data.get('target_slot', 'active')  # 'active' or bench index
                
                from simulator.core.game import BattleAction, ActionType
                action = BattleAction(
                    action_type=ActionType.PLACE_POKEMON,
                    player_id=player_id,
                    details={
                        'hand_index': hand_index,
                        'target_slot': target_slot
                    }
                )
                
                success = game_state.execute_action(action)
                print(f"🔍 ACTION RESULT: {action_type} {'✅ SUCCESS' if success else '❌ FAILED'}")
                
                # Get the latest log entries with descriptive text
                recent_logs = game_state.turn_log[-3:] if game_state.turn_log else []
                
                emit('battle_action_result', {
                    'action_type': action_type,
                    'result': success,
                    'player_id': player_id,
                    'log_entries': recent_logs
                })
                
                if not success:
                    emit('battle_error', {'error': f'{action_type} failed to execute'})
                
            elif action_type == 'attach_energy':
                # Attach energy from hand to Pokemon
                player_id = data.get('player_id', 0)
                energy_data = data.get('data', {})
                
                # Support both old and new parameter formats
                hand_index = energy_data.get('hand_index', 0)
                
                # New format (from frontend specialist fixes)
                target_player = energy_data.get('target_player')
                target_position = energy_data.get('target_position')
                energy_type = energy_data.get('energy_type')
                
                # Legacy format fallback
                target_pokemon = energy_data.get('target_pokemon', 'active')
                
                # Use new format if available, otherwise use legacy
                if target_player is not None and target_position:
                    target_info = target_position
                    actual_player = target_player
                else:
                    target_info = target_pokemon
                    actual_player = player_id
                
                print(f"🔍 ENERGY ATTACH: Player {player_id} -> Player {actual_player} at {target_info}")
                print(f"🔍 ENERGY DATA: {energy_data}")
                
                from simulator.core.game import BattleAction, ActionType
                action = BattleAction(
                    action_type=ActionType.ATTACH_ENERGY,
                    player_id=actual_player,  # Use the actual target player
                    details={
                        'hand_index': hand_index,
                        'target_pokemon': target_info,
                        'energy_type': energy_type
                    }
                )
                
                success = game_state.execute_action(action)
                print(f"🔍 ACTION RESULT: {action_type} {'✅ SUCCESS' if success else '❌ FAILED'}")
                
                # Get the latest log entries with descriptive text
                recent_logs = game_state.turn_log[-3:] if game_state.turn_log else []
                
                emit('battle_action_result', {
                    'action_type': action_type,
                    'result': success,
                    'player_id': player_id,
                    'log_entries': recent_logs
                })
                
                if not success:
                    emit('battle_error', {'error': f'{action_type} failed to execute'})
                
            elif action_type == 'retreat':
                # Retreat active Pokemon
                player_id = data.get('player_id', 0)
                retreat_data = data.get('data', {})
                replacement_index = retreat_data.get('replacement_index', 0)
                
                from simulator.core.game import BattleAction, ActionType
                action = BattleAction(
                    action_type=ActionType.RETREAT,
                    player_id=player_id,
                    details={'bench_index': replacement_index}
                )
                
                success = game_state.execute_action(action)
                print(f"🔍 ACTION RESULT: {action_type} {'✅ SUCCESS' if success else '❌ FAILED'}")
                
                # Get the latest log entries with descriptive text
                recent_logs = game_state.turn_log[-3:] if game_state.turn_log else []
                
                emit('battle_action_result', {
                    'action_type': action_type,
                    'result': success,
                    'player_id': player_id,
                    'log_entries': recent_logs
                })
                
                if not success:
                    emit('battle_error', {'error': f'{action_type} failed to execute'})
                
            elif action_type == 'setup_ready':
                # Handle player setup ready state
                player_id = data.get('player_id', 0)
                ready_data = data.get('data', {})
                ready_state = ready_data.get('ready', True)
                
                # Update player ready state in game state
                if player_id < len(game_state.players):
                    game_state.players[player_id].setup_ready = ready_state
                    
                    emit('battle_action_result', {
                        'action_type': action_type,
                        'result': True,
                        'player_id': player_id,
                        'log_entries': [{
                            'player': player_id,
                            'action': 'setup_ready',
                            'message': f"Player {player_id + 1} {'ready' if ready_state else 'not ready'}"
                        }]
                    })
                else:
                    emit('battle_action_result', {
                        'action_type': action_type,
                        'result': False,
                        'player_id': player_id,
                        'log_entries': [{
                            'player': player_id,
                            'action': 'setup_ready',
                            'message': 'Invalid player ID'
                        }]
                    })
                
            elif action_type == 'start_game':
                # Handle game start when both players are ready
                player_id = data.get('player_id', 0)
                
                # Check if both players are ready
                all_ready = all(player.setup_ready for player in game_state.players)
                
                # Import GamePhase to check current phase properly
                from simulator.core.game import GamePhase
                
                # Check if we're in a valid phase to start the game
                valid_start_phases = [GamePhase.SETUP, GamePhase.INITIAL_POKEMON_PLACEMENT]
                current_phase_value = game_state.phase
                
                # Handle both enum and string phase values
                if hasattr(current_phase_value, 'value'):
                    current_phase_str = current_phase_value.value
                else:
                    current_phase_str = str(current_phase_value)
                
                is_valid_phase = (current_phase_value in valid_start_phases or 
                                current_phase_str in ['setup', 'initial_pokemon_placement'])
                
                if all_ready and is_valid_phase:
                    # Transition from setup to main game
                    game_state.phase = GamePhase.PLAYER_TURN
                    game_state.turn_number = 1
                    game_state.current_player = 0  # Start with player 0
                    
                    # Log the battle start
                    game_state.turn_log.append({
                        'turn': game_state.turn_number,
                        'player': -1,  # System action
                        'action': 'battle_start',
                        'message': 'Battle started! Both players ready.',
                        'timestamp': time.time() * 1000
                    })
                    
                    emit('battle_action_result', {
                        'action_type': action_type,
                        'result': True,
                        'player_id': player_id,
                        'log_entries': [{
                            'player': -1,  # System action
                            'action': 'battle_start',
                            'message': 'Battle started! Both players ready.'
                        }]
                    })
                else:
                    error_msg = 'Cannot start battle - '
                    if not all_ready:
                        error_msg += 'not all players ready'
                    else:
                        error_msg += f'invalid phase ({current_phase_str})'
                    
                    emit('battle_action_result', {
                        'action_type': action_type,
                        'result': False,
                        'player_id': player_id,
                        'log_entries': [{
                            'player': player_id,
                            'action': 'start_game_failed',
                            'message': error_msg
                        }]
                    })
                
            elif action_type == 'attack':
                # Execute attack using active Pokemon
                player_id = data.get('player_id', 0)
                attack_data = data.get('data', {})
                attack_index = attack_data.get('attack_index', 0)
                
                print(f"🔍 PRE-ACTION: Player {player_id}, Attack Index {attack_index}")
                print(f"🔍 GAME STATE: Phase={game_state.phase}, Current Player={game_state.current_player}")
                if game_state.players[player_id].active_pokemon:
                    active = game_state.players[player_id].active_pokemon
                    print(f"🔍 ACTIVE POKEMON: {active.card.name}, Attacks={len(active.card.attacks)}")
                    if active.card.attacks and attack_index < len(active.card.attacks):
                        attack_info = active.card.attacks[attack_index]
                        print(f"🔍 ATTACK INFO: {attack_info}")
                else:
                    print("🔍 NO ACTIVE POKEMON!")
                
                from simulator.core.game import BattleAction, ActionType
                action = BattleAction(
                    action_type=ActionType.ATTACK,
                    player_id=player_id,
                    details={
                        'attack_index': attack_index
                    }
                )
                
                success = game_state.execute_action(action)
                print(f"🔍 ACTION RESULT: {action_type} {'✅ SUCCESS' if success else '❌ FAILED'}")
                
                # If failed, get validation error
                if not success:
                    is_valid, error = game_state.validate_action(action)
                    print(f"🔍 VALIDATION: {'Valid' if is_valid else 'Invalid'} - {error}")
                
                # Get the latest log entries with descriptive text
                recent_logs = game_state.turn_log[-3:] if game_state.turn_log else []
                
                emit('battle_action_result', {
                    'action_type': action_type,
                    'result': success,
                    'player_id': player_id,
                    'log_entries': recent_logs
                })
                
                if not success:
                    emit('battle_error', {'error': f'{action_type} failed to execute'})
                
            elif action_type == 'draw_card':
                # Handle card draw
                player_id = data.get('player_id', 0)
                
                print(f"🔍 DRAW CARD: Player {player_id}")
                
                # Check if it's the player's turn and they can draw
                if game_state.current_player != player_id:
                    print(f"❌ DRAW FAILED: Not player {player_id}'s turn (current: {game_state.current_player})")
                    emit('battle_error', {'error': f'Not your turn - cannot draw card'})
                    return
                
                # Check if player can draw (has cards left)
                player = game_state.players[player_id]
                if len(player.deck) == 0:
                    print(f"❌ DRAW FAILED: Player {player_id} deck is empty")
                    emit('battle_error', {'error': 'Deck is empty - cannot draw card'})
                    return
                
                # Draw a card
                try:
                    drawn_card = player.draw_card()
                    if drawn_card:
                        print(f"✅ DRAW SUCCESS: Player {player_id} drew {drawn_card.name}")
                        emit('battle_action_result', {
                            'action_type': action_type,
                            'result': True,
                            'player_id': player_id,
                            'log_entries': [{
                                'descriptive_text': f"Player {player_id + 1} drew a card",
                                'details': {'card_name': drawn_card.name}
                            }]
                        })
                    else:
                        print(f"❌ DRAW FAILED: Player {player_id} could not draw card")
                        emit('battle_error', {'error': 'Failed to draw card'})
                except Exception as e:
                    print(f"❌ DRAW ERROR: {e}")
                    emit('battle_error', {'error': f'Draw card failed: {str(e)}'})
                
            elif action_type == 'end_turn':
                # Handle end turn
                player_id = data.get('player_id', 0)
                
                print(f"🔍 END TURN: Player {player_id}")
                
                # Check if it's the player's turn
                if game_state.current_player != player_id:
                    print(f"❌ END TURN FAILED: Not player {player_id}'s turn (current: {game_state.current_player})")
                    emit('battle_error', {'error': f'Not your turn - cannot end turn'})
                    return
                
                # Create end turn action
                from simulator.core.game import BattleAction, ActionType
                action = BattleAction(
                    action_type=ActionType.END_TURN,
                    player_id=player_id,
                    details={}
                )
                
                success = game_state.execute_action(action)
                print(f"🔍 ACTION RESULT: {action_type} {'✅ SUCCESS' if success else '❌ FAILED'}")
                
                if success:
                    recent_logs = game_state.turn_log[-3:] if game_state.turn_log else []
                    emit('battle_action_result', {
                        'action_type': action_type,
                        'result': success,
                        'player_id': player_id,
                        'log_entries': recent_logs
                    })
                else:
                    is_valid, error = game_state.validate_action(action)
                    print(f"🔍 VALIDATION: {'Valid' if is_valid else 'Invalid'} - {error}")
                    emit('battle_error', {'error': f'End turn failed: {error}'})
                
            else:
                # Unknown action type
                print(f"❌ UNKNOWN ACTION TYPE: {action_type}")
                emit('battle_error', {'error': f'Unknown action type: {action_type}'})
                return
                
            # Send updated game state
            emit('game_state_update', {
                'game_state': get_battle_state_dict(game_state),
                'is_over': game_state.is_battle_over(),
                'winner': game_state.winner
            })
            
            # Check if battle is over
            if game_state.is_battle_over():
                emit('battle_ended', {
                    'winner': game_state.winner,
                    'is_tie': getattr(game_state, 'is_tie', False)
                })
            else:
                # Check if we need to trigger AI turn
                battle_data = active_battles[battle_id]
                player_mode = battle_data.get('player_mode', 'human_vs_ai')
                current_player = game_state.current_player
                ai_players = battle_data['ai_players']
                
                # If current player is AI-controlled, trigger AI action after a short delay
                if (current_player < len(ai_players) and 
                    ai_players[current_player] is not None):
                    # Emit AI turn needed event
                    emit('ai_turn_needed', {
                        'battle_id': battle_id,
                        'current_player': current_player
                    })
            
        except Exception as e:
            emit('battle_error', {'error': str(e)})
    
    @socketio.on('set_mode')
    def handle_set_mode(data):
        """Set battle mode (manual/auto_sim)"""
        try:
            # Find battle for this client
            battle_id = None
            for bid, battle_data in active_battles.items():
                if battle_data.get('client_sid') == request.sid:
                    battle_id = bid
                    break
            
            if not battle_id:
                emit('battle_error', {'error': 'No active battle found'})
                return
            
            new_mode = data.get('mode', 'manual')
            speed = data.get('speed', 1)
            
            active_battles[battle_id]['mode'] = new_mode
            
            emit('mode_changed', {
                'mode': new_mode,
                'speed': speed
            })
            
        except Exception as e:
            emit('battle_error', {'error': str(e)})
    
    @socketio.on('request_ai_action')
    def handle_ai_action():
        """Execute AI action for the current player"""
        try:
            # Find battle for this client
            battle_id = None
            for bid, battle_data in active_battles.items():
                if battle_data.get('client_sid') == request.sid:
                    battle_id = bid
                    break
            
            if not battle_id:
                emit('battle_error', {'error': 'No active battle found for this client'})
                return
            
            battle_data = active_battles[battle_id]
            game_state = battle_data["game_state"]
            ai_players = battle_data["ai_players"]
            
            if game_state.is_battle_over():
                emit('battle_error', {'error': 'Battle is already over'})
                return
            
            # Determine which player should act based on game phase
            from simulator.core.game import GamePhase
            if game_state.phase == GamePhase.FORCED_POKEMON_SELECTION:
                acting_player = game_state.forced_selection_player
            else:
                acting_player = game_state.current_player
            
            # Check if current player is AI-controlled
            if (acting_player >= len(ai_players) or 
                ai_players[acting_player] is None):
                emit('battle_error', {'error': 'Current player is not AI-controlled'})
                return
            
            ai_player = ai_players[acting_player]
            
            # AI chooses action
            action = ai_player.choose_action(game_state)
            
            if action is None:
                action = ai_player._create_end_turn_action()
            
            # Log the action
            action_log = {
                "turn": game_state.turn_number,
                "player": acting_player,
                "action": action.action_type.value,
                "details": action.details,
                "timestamp": time.time() * 1000
            }
            battle_data["turn_log"].append(action_log)
            
            # Execute action
            success = game_state.execute_action(action)
            
            # Get the latest log entries with descriptive text
            recent_logs = game_state.turn_log[-3:] if game_state.turn_log else []
            
            emit('battle_action_result', {
                'action_type': 'ai_action',
                'result': success,
                'player_id': acting_player,
                'action': action.to_dict(),
                'log_entries': recent_logs
            })
            
            # Send updated game state
            emit('game_state_update', {
                'game_state': get_battle_state_dict(game_state),
                'is_over': game_state.is_battle_over(),
                'winner': game_state.winner
            })
            
            # Check if battle is over or if another AI turn is needed
            if game_state.is_battle_over():
                emit('battle_ended', {
                    'winner': game_state.winner,
                    'is_tie': getattr(game_state, 'is_tie', False)
                })
            else:
                # Check if we need another AI turn
                current_player = game_state.current_player
                if (current_player < len(ai_players) and 
                    ai_players[current_player] is not None):
                    # Emit next AI turn needed event
                    emit('ai_turn_needed', {
                        'battle_id': battle_id,
                        'current_player': current_player
                    })
            
        except Exception as e:
            emit('battle_error', {'error': str(e)})
