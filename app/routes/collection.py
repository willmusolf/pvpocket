from flask import Blueprint, render_template, current_app, session, redirect, url_for, flash
import os
import json
from .auth import is_logged_in, get_current_user

collection_bp = Blueprint('collection_bp', __name__)
@collection_bp.route('/collection')
def view_collection():
    """View all decks in the user's collection."""
    # Check if user is logged in
    if not is_logged_in():
        flash('Please log in to view your collection.', 'warning')
        return redirect(url_for('auth.login'))
    
    # Get meta stats from app config
    meta_stats = current_app.config.get('meta_stats', {})
    
    # Get current user
    username = session.get('username')
    
    decks = []
    if os.path.exists('decks'):
        for filename in os.listdir('decks'):
            if filename.endswith('.json'):
                try:
                    with open(f'decks/{filename}', 'r') as f:
                        deck_data = json.load(f)
                        
                        # Skip decks that don't belong to the current user
                        # Changed this line to check both 'owner' and if owner field doesn't exist
                        if 'owner' in deck_data and deck_data.get('owner') != username:
                            continue
                        
                        # Get win rate from meta stats if available
                        win_rate = None
                        deck_name = deck_data.get('name')
                        if deck_name in meta_stats.get("decks", {}):
                            stats = meta_stats["decks"][deck_name]
                            if stats.get("total_battles", 0) > 0:
                                win_rate = (stats["wins"] / stats["total_battles"]) * 100
                        
                        # Get cover card if available
                        cover_card = None
                        cover_card_image_url = None
                        cover_card_display_image_path = None
                        if 'cover_card_id' in deck_data and deck_data['cover_card_id']:
                            card_collection = current_app.config['card_collection']
                            cover_card = card_collection.get_card_by_id(deck_data['cover_card_id'])
                            if cover_card:
                                # Add the image URL and display_image_path to the cover card
                                cover_card_image_url = cover_card.image_url
                                cover_card_display_image_path = cover_card.display_image_path
                        
                        decks.append({
                            'name': deck_name,
                            'filename': filename,
                            'types': deck_data.get('deck_types', []),
                            'card_count': len(deck_data.get('cards', [])),
                            'win_rate': round(win_rate, 1) if win_rate is not None else None,
                            'cover_card': {
                                'name': cover_card.name if cover_card else "No Cover",
                                'image_url': cover_card_image_url if cover_card_image_url else None,
                                'display_image_path': cover_card_display_image_path if cover_card_display_image_path else None
                            } if cover_card else None
                        })
                except Exception as e:
                    print(f"Error loading deck {filename}: {e}")
    
    # Add debug information
    print(f"Found {len(decks)} decks for user {username}")
    
    return render_template(
        'collection.html', 
        decks=decks,
        user_logged_in=is_logged_in(),
        username=username
    )