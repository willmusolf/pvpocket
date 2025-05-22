from flask import Blueprint, render_template, current_app, session
from .auth import is_logged_in
import os
import json

meta_bp = Blueprint('meta', __name__)

@meta_bp.route('/meta')
def meta_rankings():
    """Meta deck rankings page."""
    # Get meta stats from app config
    meta_stats = current_app.config['meta_stats']
    
    # Calculate win rates and sort decks
    ranked_decks = []
    
    for deck_name, stats in meta_stats["decks"].items():
        if stats["total_battles"] >= 3:  # Only include decks with enough battles
            win_rate = (stats["wins"] / stats["total_battles"]) * 100
            
            # Get deck types and other info
            deck_info = {
                "name": deck_name,
                "win_rate": round(win_rate, 1),
                "wins": stats["wins"],
                "losses": stats["losses"],
                "total_battles": stats["total_battles"],
                "avg_turns": round(stats["avg_turns"], 1),
                "types": [],
                "filename": ""
            }
            
            # Find the deck file to get types
            for filename in os.listdir('decks'):
                if filename.endswith('.json'):
                    try:
                        with open(f'decks/{filename}', 'r') as f:
                            deck_data = dict(deck_info)  # Create a copy
                            if deck_data.get('name') == deck_name:
                                deck_info["types"] = deck_data.get('deck_types', [])
                                deck_info["filename"] = filename
                                break
                    except Exception:
                        pass
            
            ranked_decks.append(deck_info)
    
    # Sort by win rate (descending)
    ranked_decks.sort(key=lambda x: x["win_rate"], reverse=True)
    
    # Assign tiers
    for i, deck in enumerate(ranked_decks):
        # Simple tier assignment based on position and win rate
        if i < 3 and deck["win_rate"] > 60:
            deck["tier"] = "S"
        elif i < 8 and deck["win_rate"] > 50:
            deck["tier"] = "A"
        elif deck["win_rate"] > 40:
            deck["tier"] = "B"
        else:
            deck["tier"] = "C"
    
    return render_template(
        'meta_rankings.html',
        ranked_decks=ranked_decks,
        last_updated=meta_stats["last_updated"],
        user_logged_in=is_logged_in(),
        username=session.get('username')
    )

@meta_bp.route('/matchup_analysis/<path:filename>')
def matchup_analysis(filename):
    """Analyze matchups for a specific deck."""
    # Get card collection and meta stats from app config
    card_collection = current_app.config['card_collection']
    meta_stats = current_app.config['meta_stats']
    
    try:
        # Load the deck
        from Deck import Deck
        deck = Deck.load_from_json(f'decks/{filename}', card_collection)
        
        # Get matchup data
        matchups = []
        if deck.name in meta_stats["decks"]:
            deck_stats = meta_stats["decks"][deck.name]
            
            for opponent, result in deck_stats["matchups"].items():
                total = result["wins"] + result["losses"]
                win_rate = (result["wins"] / total) * 100 if total > 0 else 0
                
                # Get opponent deck types
                opponent_types = []
                for opponent_filename in os.listdir('decks'):
                    if opponent_filename.endswith('.json'):
                        try:
                            with open(f'decks/{opponent_filename}', 'r') as f:
                                deck_data = json.load(f)
                                if deck_data.get('name') == opponent:
                                    opponent_types = deck_data.get('deck_types', [])
                                    break
                        except Exception:
                            pass
                
                matchups.append({
                    'opponent': opponent,
                    'wins': result["wins"],
                    'losses': result["losses"],
                    'win_rate': round(win_rate, 1),
                    'total': total,
                    'types': opponent_types,
                })
            
            # Sort by number of matches
            matchups.sort(key=lambda x: x['total'], reverse=True)
        
        return render_template(
            'matchup_analysis.html',
            deck=deck,
            matchups=matchups,
            user_logged_in=is_logged_in(),
            username=session.get('username')
        )
    except Exception as e:
        return render_template('error.html', error=str(e))

@meta_bp.route('/deck/analyze/<path:filename>')
def analyze_deck(filename):
    """Analyze a deck's strengths and weaknesses."""
    # Get card collection and meta stats from app config
    card_collection = current_app.config['card_collection']
    meta_stats = current_app.config['meta_stats']
    
    try:
        # Load the deck
        from Deck import Deck
        deck = Deck.load_from_json(f'decks/{filename}', card_collection)
        
        # Calculate various statistics and metrics
        pokemon_count = deck.get_pokemon_count()
        trainer_count = deck.get_trainer_count()
        type_breakdown = deck.get_type_breakdown()
        evolution_counts = deck.get_evolution_counts()
        
        # Analyze consistency metrics
        basic_pokemon_count = evolution_counts.get("Basic", 0)
        consistency_score = 0
        
        # More basic Pokémon = better consistency
        if basic_pokemon_count >= 10:
            consistency_score += 5
        elif basic_pokemon_count >= 8:
            consistency_score += 4
        elif basic_pokemon_count >= 6:
            consistency_score += 3
        elif basic_pokemon_count >= 4:
            consistency_score += 2
        else:
            consistency_score += 1
        
        # Calculate card type balance score
        if 7 <= pokemon_count <= 12 and 8 <= trainer_count <= 13:
            balance_score = 5  # Balanced deck
        elif 5 <= pokemon_count <= 14 and 6 <= trainer_count <= 15:
            balance_score = 4  # Reasonably balanced
        else:
            balance_score = 2  # Unbalanced
        
        # Get meta performance
        meta_data = None
        win_rate = 0
        tier = "Unranked"
        if deck.name in meta_stats["decks"]:
            meta_data = meta_stats["decks"][deck.name]
            if meta_data["total_battles"] > 0:
                win_rate = (meta_data["wins"] / meta_data["total_battles"]) * 100
                
                # Assign tier based on win rate
                if win_rate > 60:
                    tier = "S"
                elif win_rate > 50:
                    tier = "A"
                elif win_rate > 40:
                    tier = "B"
                else:
                    tier = "C"
        
        # Calculate overall power score
        power_score = (consistency_score + balance_score) / 2
        if meta_data and meta_data["total_battles"] >= 5:
            # Incorporate win rate if we have enough data
            power_score = (power_score * 0.5) + (win_rate / 20)
        
        return render_template(
            'deck_analysis.html',
            deck=deck,
            pokemon_count=pokemon_count,
            trainer_count=trainer_count,
            type_breakdown=type_breakdown,
            evolution_counts=evolution_counts,
            consistency_score=consistency_score,
            balance_score=balance_score,
            win_rate=round(win_rate, 1) if win_rate else None,
            power_score=round(power_score, 1),
            tier=tier,
            meta_data=meta_data,
            user_logged_in=is_logged_in(),
            username=session.get('username')
        )
    except Exception as e:
        return render_template('error.html', error=str(e))