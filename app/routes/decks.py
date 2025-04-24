from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, session
import os
import json
from .auth import is_logged_in, get_current_user
from Deck import Deck
import os
import json
import random
import time
from .auth import is_logged_in, get_current_user

decks_bp = Blueprint('decks', __name__)

@decks_bp.route('/decks')
def list_decks():
    """List all saved decks and provide deck building interface."""
    # Get meta stats from app config
    meta_stats = current_app.config.get('meta_stats', {})
    
    # Get card collection for search functionality
    card_collection = current_app.config.get('card_collection')
    
    # Load user and public decks
    decks = []
    if os.path.exists('decks'):
        for filename in os.listdir('decks'):
            if filename.endswith('.json'):
                try:
                    with open(f'decks/{filename}', 'r') as f:
                        deck_data = json.load(f)
                        
                        # Get win rate from meta stats if available
                        win_rate = None
                        deck_name = deck_data.get('name')
                        if meta_stats and deck_name in meta_stats.get("decks", {}):
                            stats = meta_stats["decks"][deck_name]
                            if stats["total_battles"] > 0:
                                win_rate = (stats["wins"] / stats["total_battles"]) * 100
                        
                        decks.append({
                            'name': deck_name,
                            'filename': filename,
                            'types': deck_data.get('deck_types', []),
                            'card_count': len(deck_data.get('cards', [])),
                            'win_rate': round(win_rate, 1) if win_rate is not None else None,
                            'owner': deck_data.get('owner', 'Unknown')
                        })
                except Exception as e:
                    print(f"Error loading deck {filename}: {e}")
    
    # Filter decks based on ownership if user is logged in
    current_user = get_current_user()
    if current_user:
        user_decks = [deck for deck in decks if deck['owner'] == current_user['username']]
        public_decks = [deck for deck in decks if deck['owner'] != current_user['username']]
    else:
        user_decks = []
        public_decks = decks
    
    return render_template(
        'decks.html', 
        user_decks=user_decks,
        public_decks=public_decks,
        user_logged_in=is_logged_in(),
        username=session.get('username')
    )

# API Routes for Deck Building

@decks_bp.route('/api/cards', methods=['GET'])
def get_all_cards():
    """API endpoint to get all cards with optional filtering."""
    # Get card collection from app config
    card_collection = current_app.config['card_collection']
    
    try:
        # Get filter parameters from query string
        set_code = request.args.get('set_code')
        energy_type = request.args.get('energy_type')
        card_type = request.args.get('card_type')
        name = request.args.get('name')
        
        # Apply filters
        filtered_cards = card_collection.cards
        
        if set_code:
            filtered_cards = [card for card in filtered_cards if card.set_code == set_code]
        
        if energy_type:
            filtered_cards = [card for card in filtered_cards if card.energy_type == energy_type]
        
        if card_type:
            filtered_cards = [card for card in filtered_cards if card_type in card.card_type]
        
        if name:
            filtered_cards = [card for card in filtered_cards if name.lower() in card.name.lower()]
        
        # Convert to dictionaries for JSON response and add display_image_path
        card_dicts = []
        for card in filtered_cards:
            card_dict = card.to_dict()
            # Add display_image_path to the card dictionary
            card_dict['display_image_path'] = card.display_image_path
            card_dicts.append(card_dict)
        
        return jsonify({"cards": card_dicts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@decks_bp.route('/api/decks/<filename>', methods=['GET'])
def get_deck(filename):
    """API endpoint to get a specific deck."""
    # Get card collection from app config
    card_collection = current_app.config['card_collection']
    
    try:
        # Load the deck
        deck = Deck.load_from_json(f'decks/{filename}', card_collection)
        
        # Convert to dictionary for JSON response
        card_dicts = []
        for card in deck.cards:
            card_dict = card.to_dict()
            # Add display_image_path to the card dictionary
            card_dict['display_image_path'] = card.display_image_path
            card_dicts.append(card_dict)
            
        deck_dict = {
            'id': filename,
            'name': deck.name,
            'deck_types': deck.deck_types,
            'cards': card_dicts
        }
        
        return jsonify(deck_dict)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@decks_bp.route('/api/decks', methods=['POST'])
def create_deck():
    """API endpoint to create a new deck."""
    if not is_logged_in():
        return jsonify({"success": False, "error": "You must be logged in to create decks"}), 401
    
    try:
        # Get deck data from request
        deck_data = request.json
        card_collection = current_app.config['card_collection']
        
        # Validate deck
        if not deck_data.get('name'):
            return jsonify({"success": False, "error": "Deck must have a name"}), 400
        
        # Create a new deck
        new_deck = Deck(deck_data.get('name'))
        
        # Add cards to the deck if provided
        if deck_data.get('cards'):
            for card_data in deck_data.get('cards'):
                card_id = card_data.get('id')
                if card_id:
                    card = card_collection.get_card_by_id(card_id)
                    if card:
                        new_deck.add_card(card)
        
        # Use the provided deck_types if available
        if 'deck_types' in deck_data and isinstance(deck_data['deck_types'], list):
            new_deck.set_deck_types(deck_data['deck_types'])
        else:
            # Fall back to auto-detection if no types provided
            new_deck.set_deck_types(new_deck.determine_deck_types())
        
        # Add owner information
        current_user = get_current_user()
        new_deck.owner = current_user['username']
        
        # Generate a unique filename
        deck_id = f"deck_{int(time.time())}_{random.randint(1000, 9999)}"
        filename = f"{deck_id}.json"
        
        # Save the deck
        os.makedirs('decks', exist_ok=True)
        new_deck.save_to_json(f'decks/{filename}')
        
        return jsonify({
            "success": True, 
            "message": "Deck created successfully",
            "filename": filename
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@decks_bp.route('/api/decks/<filename>', methods=['PUT'])
def update_deck(filename):
    """API endpoint to update an existing deck."""
    if not is_logged_in():
        return jsonify({"success": False, "error": "You must be logged in to update decks"}), 401
    
    try:
        # Get deck data from request
        deck_data = request.json
        card_collection = current_app.config['card_collection']
        
        # Validate deck
        if not deck_data.get('name'):
            return jsonify({"success": False, "error": "Deck must have a name"}), 400
        
        # Check ownership
        try:
            existing_deck = Deck.load_from_json(f'decks/{filename}', card_collection)
            current_user = get_current_user()
            if hasattr(existing_deck, 'owner') and existing_deck.owner != current_user['username']:
                return jsonify({"success": False, "error": "You can only update your own decks"}), 403
        except Exception as e:
            return jsonify({"success": False, "error": f"Deck not found: {str(e)}"}), 404
        
        # Create updated deck
        updated_deck = Deck(deck_data.get('name'))
        
        # Add cards
        for card_data in deck_data.get('cards', []):
            card_id = card_data.get('id')
            if card_id:
                card = card_collection.get_card_by_id(card_id)
                if card:
                    updated_deck.add_card(card)
        
        # Use the provided deck_types instead of automatically determining them
        if 'deck_types' in deck_data and isinstance(deck_data['deck_types'], list):
            updated_deck.set_deck_types(deck_data['deck_types'])
        else:
            # Fall back to auto-detection if no types provided
            updated_deck.set_deck_types(updated_deck.determine_deck_types())
            
        updated_deck.owner = current_user['username']
        
        # Save the updated deck
        updated_deck.save_to_json(f'decks/{filename}')
        
        return jsonify({
            "success": True, 
            "message": "Deck updated successfully",
            "filename": filename
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@decks_bp.route('/delete_deck')
def delete_deck():
    """Delete a deck from the user's collection."""
    # Check if user is logged in
    if not is_logged_in():
        flash('Please log in to delete decks.', 'warning')
        return redirect(url_for('auth.login'))
    
    # Get filename from query parameters
    filename = request.args.get('filename')
    if not filename:
        flash('No deck specified.', 'danger')
        return redirect(url_for('collection_bp.view_collection'))
    
    # Check if the file exists
    deck_path = os.path.join('decks', filename)
    if not os.path.exists(deck_path):
        flash('Deck not found.', 'danger')
        return redirect(url_for('collection_bp.view_collection'))
    
    # Check if the user owns this deck
    username = session.get('username')
    try:
        with open(deck_path, 'r') as f:
            deck_data = json.load(f)
            # Only allow deletion if user owns deck or if no owner is specified
            if 'owner' in deck_data and deck_data['owner'] != username:
                flash('You do not have permission to delete this deck.', 'danger')
                return redirect(url_for('collection_bp.view_collection'))
    except Exception as e:
        flash(f'Error checking deck ownership: {e}', 'danger')
        return redirect(url_for('collection_bp.view_collection'))
    
    # Delete the deck file
    try:
        os.remove(deck_path)
    except Exception as e:
        flash(f'Error deleting deck: {e}', 'danger')
    
    return redirect(url_for('collection_bp.view_collection'))