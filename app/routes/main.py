from flask import Blueprint, render_template, current_app, session
import os
import json

main_bp = Blueprint('main', __name__)

def is_logged_in():
    """Check if user is logged in."""
    return 'user_id' in session

@main_bp.route('/')
def index():
    """Main homepage with paths to all features."""
    # Get card collection from app config
    card_collection = current_app.config['card_collection']
    battle_history = current_app.config['battle_history']
    meta_stats = current_app.config['meta_stats']
    
    # Get statistics for the homepage
    total_cards = len(card_collection)
    
    # Count total decks
    total_decks = 0
    if os.path.exists('decks'):
        total_decks = len([f for f in os.listdir('decks') if f.endswith('.json')])
    
    # Get battle count
    total_battles = len(battle_history)
    
    # Get recent battles
    recent_battles = battle_history[-5:] if battle_history else []
    
    # Get top decks by win rate
    top_decks = []
    for deck_name, stats in meta_stats["decks"].items():
        if stats["total_battles"] >= 5:  # Only include decks with enough battles
            win_rate = (stats["wins"] / stats["total_battles"]) * 100
            
            # Get deck types
            deck_types = []
            for filename in os.listdir('decks'):
                if filename.endswith('.json'):
                    try:
                        with open(f'decks/{filename}', 'r') as f:
                            deck_data = json.load(f)
                            if deck_data.get('name') == deck_name:
                                deck_types = deck_data.get('deck_types', [])
                                break
                    except Exception:
                        pass
            
            top_decks.append({
                "name": deck_name,
                "win_rate": round(win_rate, 1),
                "types": deck_types
            })
    
    # Sort by win rate (descending)
    top_decks.sort(key=lambda x: x["win_rate"], reverse=True)
    top_decks = top_decks[:5]  # Top 5 decks
    
    return render_template(
        'main_index.html',
        total_cards=total_cards,
        total_decks=total_decks,
        total_battles=total_battles,
        recent_battles=recent_battles,
        top_decks=top_decks,
        user_logged_in=is_logged_in(),
        username=session.get('username')
    )