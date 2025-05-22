from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify
from Deck import Deck
from battle_engine import SimpleAI, BattleEngine
import os
import json
import random
from .auth import is_logged_in, get_current_user_data

battle_bp = Blueprint('battle', __name__)

@battle_bp.route('/battle')
def battle():
    """Main battle simulator page."""
    # Get card collection from app config
    card_collection = current_app.config['card_collection']
    
    # Get list of available decks
    decks = []
    if os.path.exists('decks'):
        for filename in os.listdir('decks'):
            if filename.endswith('.json'):
                try:
                    with open(f'decks/{filename}', 'r') as f:
                        deck_data = json.load(f)
                        
                        # Get the cover art URL from the deck
                        cover_art_url = None
                        if 'cover_art_url' in deck_data:
                            cover_art_url = deck_data['cover_art_url']
                        # If no explicit cover art, try to get the first Pokémon card's image
                        elif 'cards' in deck_data and len(deck_data['cards']) > 0:
                            for card_id in deck_data['cards']:
                                card = card_collection.get_card_by_id(card_id)
                                if card and hasattr(card, 'is_pokemon') and card.is_pokemon and hasattr(card, 'image_url') and card.image_url:
                                    cover_art_url = card.image_url
                                    break
                        
                        # Get deck types
                        deck_types = []
                        if 'deck_types' in deck_data:
                            deck_types = deck_data['deck_types']
                        
                        deck_info = {
                            'name': deck_data.get('name', filename[:-5]),
                            'filename': filename,
                            'types': deck_types,
                            'owner': deck_data.get('owner', 'Unknown'),
                            'cover_art_url': cover_art_url
                        }
                        decks.append(deck_info)
                except Exception as e:
                    print(f"Error loading deck {filename}: {e}")
    
    return render_template(
        'battle.html', 
        decks=decks,
        user_logged_in=is_logged_in(),
        username=session.get('username')
    )

@battle_bp.route('/battle/simulate', methods=['POST'])
def simulate_battle():
    """Run a battle simulation between two decks."""
    # Get card collection from app config
    card_collection = current_app.config['card_collection']
    
    try:
        # Handle deck 1
        deck1_filename = request.form.get('deck1')
        if deck1_filename == 'random' or not deck1_filename:
            deck1 = Deck.generate_random_deck(card_collection, "Your Random Deck")
            deck1_filename = None
        else:
            deck1 = Deck.load_from_json(f'decks/{deck1_filename}', card_collection)
        
        # Handle deck 2
        deck2_filename = request.form.get('deck2')
        if deck2_filename == 'random' or not deck2_filename:
            deck2 = Deck.generate_random_deck(card_collection, "AI's Random Deck")
            deck2_filename = None
        else:
            deck2 = Deck.load_from_json(f'decks/{deck2_filename}', card_collection)
        
        max_turns = int(request.form.get('max_turns', 100))
        
        # Create AI players
        ai1 = SimpleAI("Player AI")
        ai2 = SimpleAI("Opponent AI")
        
        # Create and run battle
        battle = BattleEngine(deck1, deck2)
        
        # Set deck names appropriately for the battle display
        if deck1_filename is None:  # Random deck for player
            battle.player1.name = "Your Random Deck"
        else:
            battle.player1.name = deck1.name + " (You)"
            
        if deck2_filename is None:  # Random deck for AI
            battle.player2.name = "AI's Random Deck"
        else:
            battle.player2.name = deck2.name + " (AI)"
        
        # Simulate the game
        result = battle.simulate_game(ai1, ai2, max_turns=max_turns)
        
        return render_template(
            'battle_ongoing.html',
            deck1=deck1,
            deck2=deck2,
            log=result.get('log', []),
            user_logged_in=is_logged_in(),
            username=session.get('username')
        )
    except Exception as e:
        # Log the full error for debugging
        import traceback
        print(f"Battle simulation error: {e}")
        traceback.print_exc()
        
        flash(f"Battle simulation error: {str(e)}", "danger")
        return redirect(url_for('battle.battle'))

@battle_bp.route('/get_random_deck')
def get_random_deck():
    """Generate a random deck."""
    try:
        card_collection = current_app.config['card_collection']
        
        # Only use the name parameter and ignore all filter parameters
        deck_name = request.args.get('name', f'Random Deck {random.randint(1, 1000)}')
        
        # Always generate a regular random deck
        random_deck = Deck.generate_random_deck(card_collection, deck_name)
        
        # Ensure the deck types are limited to 3
        if len(random_deck.deck_types) > 3:
            random_deck.deck_types = random_deck.deck_types[:3]
        
        # Convert the deck to a format suitable for the frontend
        deck_data = {
            'name': random_deck.name,
            'types': random_deck.deck_types,
            'cards': [
                {
                    'id': card.id,
                    'name': card.name,
                    'image_url': card.image_url if hasattr(card, 'image_url') else None,
                    'is_pokemon': card.is_pokemon,
                    'is_trainer': card.is_trainer,
                }
                for card in random_deck.cards
            ],
            'cover_art_url': random_deck.cover_card.image_url if random_deck.cover_card and hasattr(random_deck.cover_card, 'image_url') else None
        }
        
        return jsonify(deck_data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})

# Add additional route for getting deck cards
@battle_bp.route('/get_deck_cards')
def get_deck_cards():
    """Get cards for a specific deck."""
    try:
        card_collection = current_app.config['card_collection']
        
        filename = request.args.get('filename')
        if not filename:
            return jsonify({'error': 'No filename provided'})
        
        deck = Deck.load_from_json(f'decks/{filename}', card_collection)
        
        cards_data = [
            {
                'id': card.id,
                'name': card.name,
                'image_url': card.image_url if hasattr(card, 'image_url') else None,
                'is_pokemon': card.is_pokemon,
                'is_trainer': card.is_trainer,
            }
            for card in deck.cards
        ]
        
        return jsonify({'cards': cards_data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})
