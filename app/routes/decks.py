from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, session
from Deck import Deck
from .auth import is_logged_in, get_current_user_data, profanity_check
import uuid
from ..services import card_service, database_service, url_service
from ..security import rate_limit_api, rate_limit_api_paginated, rate_limit_heavy
from flask_login import (
    current_user as flask_login_current_user,
    login_required,
    )

from firebase_admin import firestore  # For ArrayUnion and SERVER_TIMESTAMP
from typing import Optional, Dict, List, Set  # For type hinting in helper function
import json
import datetime
import re

decks_bp = Blueprint('decks', __name__)

# Master set release order - used for consistent sorting across the application
# NOTE: When adding new sets, update this order in ALL locations:
# 1. This file (3 places: rarity sort, type sort, set sort)
# 2. templates/decks.html (frontend sorting)
# 3. app/services.py (PRIORITY_SETS for loading)
SET_RELEASE_ORDER = {
    "Eevee Grove": 1,           # Most recent
    "Extradimensional Crisis": 2,
    "Celestial Guardians": 3,
    "Shining Revelry": 4,
    "Triumphant Light": 5,
    "Space-Time Smackdown": 6,
    "Mythical Island": 7,
    "Genetic Apex": 8,           # Oldest set
    "Promo-A": 9,               # Special set - ALWAYS appears last regardless of sort direction
}

MAX_DECKS_PER_USER = 200


# Use shared database service instead of local get_db() function
get_db = database_service.get_db


def parse_search_keywords(search_text: str) -> Dict[str, any]:
    """Parse search text for keywords and return filter parameters.
    
    Args:
        search_text: The raw search text from user input
        
    Returns:
        Dict containing parsed filters and remaining search text
    """
    # Define keyword mappings (from frontend's applyFiltersOLD)
    energy_type_keywords = {
        'grass': 'Grass', 'fire': 'Fire', 'water': 'Water',
        'lightning': 'Lightning', 'electric': 'Lightning', 'psychic': 'Psychic',
        'fighting': 'Fighting', 'darkness': 'Darkness', 'dark': 'Darkness',
        'metal': 'Metal', 'steel': 'Metal', 'dragon': 'Dragon',
        'colorless': 'Colorless', 'normal': 'Colorless'
    }
    
    card_type_keywords = {
        'trainer': 'Trainer', 'pokémon': 'Pokémon', 'pokemon': 'Pokémon'
    }
    
    single_word_stage_keywords = {
        'item': 'Item', 'tool': 'Tool', 'supporter': 'Supporter', 
        'basic': 'Basic', 'ex': 'EX', 'stage1': 'Stage 1', 'stage2': 'Stage 2'
    }
    
    multi_word_stage_keywords = {
        'stage 1': 'Stage 1', 'stage 2': 'Stage 2', 'ultra beast': 'Ultra Beast'
    }
    
    rarity_keywords = {
        'shiny': ['✵', '✵✵'],
        'crown': ['Crown Rare']
    }
    
    set_keywords = {
        'promo': 'Promo-A'
    }
    
    # Special filter keywords
    special_keywords = {
        'noex': 'exclude_ex'
    }
    
    # Initialize result
    result = {
        'energy_types': [],
        'card_type': None,
        'stage_type': None,
        'rarities': [],
        'set_code': None,
        'exclude_ex': False,
        'is_shiny_search': False,
        'remaining_text': ''
    }
    
    if not search_text or not search_text.strip():
        return result
        
    current_search = search_text.lower().strip()
    
    # Collect all potential stage types found in the search
    found_stage_types = []
    
    # Check multi-word keywords first (longer matches take precedence)
    for keyword, filter_value in multi_word_stage_keywords.items():
        if keyword in current_search:
            found_stage_types.append(filter_value)
            current_search = current_search.replace(keyword, '').strip()
    
    # Split remaining text into terms for single-word keyword matching
    terms = current_search.split()
    remaining_terms = []
    
    for term in terms:
        term = term.strip()
        if not term:
            continue
            
        keyword_matched = False
        
        # Check energy type keywords
        if term in energy_type_keywords:
            result['energy_types'].append(energy_type_keywords[term])
            keyword_matched = True
        
        # Check card type keywords
        elif term in card_type_keywords:
            result['card_type'] = card_type_keywords[term]
            keyword_matched = True
            
        # Check stage type keywords
        elif term in single_word_stage_keywords:
            found_stage_types.append(single_word_stage_keywords[term])
            # Don't mark as keyword yet - we'll decide later based on stage type count
            
        # Check rarity keywords
        elif term in rarity_keywords:
            result['rarities'].extend(rarity_keywords[term])
            # Mark if this was specifically a "shiny" search for special handling
            if term == 'shiny':
                result['is_shiny_search'] = True
            keyword_matched = True
            
        # Check set keywords
        elif term in set_keywords:
            result['set_code'] = set_keywords[term]
            keyword_matched = True
            
        # Check special keywords
        elif term in special_keywords:
            if special_keywords[term] == 'exclude_ex':
                result['exclude_ex'] = True
            keyword_matched = True
        
        # If no keyword matched, keep as search text
        if not keyword_matched:
            remaining_terms.append(term)
    
    # Only set stage type filter if exactly one stage type was found
    # If multiple stage types are found, add them back to search text
    if len(found_stage_types) == 1:
        result['stage_type'] = found_stage_types[0]
        # Remove stage type terms from remaining_terms since we're using them as filters
        remaining_terms = [term for term in remaining_terms if term not in single_word_stage_keywords]
    elif len(found_stage_types) > 1:
        # Add stage type terms back to search text for text-based matching
        original_terms = search_text.lower().split()
        stage_terms = []
        
        # Add back multi-word phrases that were found
        for keyword in multi_word_stage_keywords:
            if keyword in search_text.lower():
                stage_terms.append(keyword)
                
        # Add back single-word stage terms that aren't already in remaining_terms
        for term in original_terms:
            if term in single_word_stage_keywords and term not in remaining_terms:
                stage_terms.append(term)
                
        # Add stage terms to remaining terms for text search
        remaining_terms.extend(stage_terms)
    
    # Join remaining terms back into search text
    result['remaining_text'] = ' '.join(remaining_terms).strip()
    
    # Remove duplicates from energy_types and rarities
    result['energy_types'] = list(set(result['energy_types']))
    result['rarities'] = list(set(result['rarities']))
    
    return result


def _does_deck_name_exist_for_user_firestore(
    user_id: str,
    deck_name_to_check: str,
    db: firestore.client,
    exclude_deck_id: Optional[str] = None,
) -> bool:
    """
    Checks if a deck name (case-insensitive) already exists for a given user in Firestore.
    - user_id: The Firestore document ID of the user.
    - deck_name_to_check: The deck name to look for.
    - db: The Firestore client instance.
    - exclude_deck_id: A deck ID (Firestore document ID) to exclude from the check (used when updating a deck).
    """
    decks_ref = db.collection("decks")
    # Assumes your Deck class's to_firestore_dict() saves a 'name_lowercase' field
    query = decks_ref.where("owner_id", "==", user_id).where(
        "name_lowercase", "==", deck_name_to_check.lower()
    )

    docs = query.stream()
    for doc in docs:
        if exclude_deck_id and doc.id == exclude_deck_id:
            continue  # This is the deck being edited, so its own name is fine
        current_app.logger.info(
            f"Deck name '{deck_name_to_check}' (lc: '{deck_name_to_check.lower()}') exists for user '{user_id}' with deck ID '{doc.id}'."
        )
        return True  # Found a deck with this name by this user
    return False


@decks_bp.route("/decks")
def list_decks():
    """
    Lists recently created decks from Firestore.
    """
    db = get_db()
    # Renamed to reflect it's not strictly "public" anymore, but rather a general listing.
    listed_decks_details = []
    meta_stats = current_app.config.get(
        "meta_stats", {}
    )  # meta_stats still loaded from JSON for now

    try:
        # Query for the 50 most recently created decks.
        # This requires an index on 'created_at' for descending order if not automatically created.
        # Firestore usually prompts for index creation if needed.
        decks_query = (
            db.collection("decks")
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(50)  # Fetch up to 50 recent decks
        )

        for deck_doc in decks_query.stream():
            deck_data = deck_doc.to_dict()
            deck_id = deck_doc.id  # Firestore document ID

            win_rate = None
            deck_name_for_stats = deck_data.get("name")
            if (
                meta_stats
                and deck_name_for_stats
                and deck_name_for_stats in meta_stats.get("decks", {})
            ):
                stats = meta_stats["decks"][deck_name_for_stats]
                if stats.get("total_battles", 0) > 0:
                    win_rate = (stats.get("wins", 0) / stats["total_battles"]) * 100

            listed_decks_details.append(  # Changed variable name
                {
                    "name": deck_data.get("name", "Unnamed Deck"),
                    "deck_id": deck_id,
                    "types": deck_data.get("deck_types", []),
                    "card_count": len(deck_data.get("card_ids", [])),
                    "win_rate": round(win_rate, 1) if win_rate is not None else None,
                    "owner_id": deck_data.get("owner_id"),
                    "created_at": deck_data.get("created_at"),
                }
            )

    except Exception as e:
        current_app.logger.error(
            f"Error fetching decks for /decks route: {e}", exc_info=True
        )
        # The flash message is now more generic.
        flash(
            "Could not retrieve decks at this time. Please try again later.",
            "warning",
        )

    # Pass the decks to the template.
    # The template 'decks.html' will use this list.
    # You might want to rename 'public_decks' in your template to something like 'listed_decks'
    # or adjust any surrounding text that implied these were specifically "public".
    return render_template(
        "decks.html",
        # Pass the fetched decks under a suitable name for the template
        listed_decks=listed_decks_details,
    )


# API Routes for Deck Building


@decks_bp.route("/api/cards", methods=["GET"])
@rate_limit_api()
def get_all_cards():
    """API endpoint to get all cards from the pre-loaded CardCollection with optional filtering."""
    # Use get_full_card_collection to ensure all cards are available for search
    card_collection = card_service.get_full_card_collection()

    if not card_collection or not hasattr(card_collection, "cards"):
        current_app.logger.error(
            "CardCollection not found or not initialized in app.config for /api/cards."
        )
        return (
            jsonify(
                {
                    "error": "Card data is currently unavailable. Please try again later.",
                    "success": False,
                }
            ),
            503,
        )

    # Use the cards from the pre-loaded collection
    # The Card objects in card_collection.cards should already have all necessary attributes,
    # including what's needed for display_image_path.
    all_cards_from_collection = card_collection.cards
    current_app.logger.info(
        f"Using {len(all_cards_from_collection)} cards from pre-loaded CardCollection for /api/cards."
    )

    try:
        # Get filter parameters from query string
        set_code_filter = request.args.get("set_code")
        energy_type_filter = request.args.get("energy_type")
        card_type_filter = request.args.get("card_type")
        name_filter = request.args.get("name", "").strip()

        # Parse name_filter for keywords
        parsed_keywords = parse_search_keywords(name_filter) if name_filter else {
            'energy_types': [], 'card_type': None, 'stage_type': None, 
            'rarities': [], 'set_code': None, 'exclude_ex': False, 'remaining_text': ''
        }

        # Apply filters to the in-memory list of Card objects
        filtered_card_objects = all_cards_from_collection

        if set_code_filter:
            filtered_card_objects = [
                card
                for card in filtered_card_objects
                if card.set_code == set_code_filter
            ]

        # Apply keyword-based energy type filter (takes precedence over URL parameter)
        if parsed_keywords['energy_types']:
            # Use the first parsed energy type (multiple energy types not supported in this API)
            filtered_card_objects = [
                card
                for card in filtered_card_objects
                if card.energy_type in parsed_keywords['energy_types']
            ]
        elif energy_type_filter:
            filtered_card_objects = [
                card
                for card in filtered_card_objects
                if card.energy_type == energy_type_filter
            ]

        # Apply keyword-based card type filter (takes precedence over URL parameter)
        if parsed_keywords['card_type']:
            if parsed_keywords['card_type'] == "Pokémon":
                filtered_card_objects = [
                    card
                    for card in filtered_card_objects
                    if card.card_type and "Pokémon" in card.card_type
                ]
            elif parsed_keywords['card_type'] == "Trainer":
                filtered_card_objects = [
                    card
                    for card in filtered_card_objects
                    if card.card_type and "Trainer" in card.card_type
                ]
        elif card_type_filter:
            # Assuming card.card_type is a string like "Pokémon - Basic"
            filtered_card_objects = [
                card
                for card in filtered_card_objects
                if card.card_type and card_type_filter in card.card_type
            ]

        # Apply keyword-based stage type filter
        if parsed_keywords['stage_type']:
            stage_type = parsed_keywords['stage_type']
            if stage_type == "EX":
                # Filter for EX cards (cards ending with " ex" in name or having "pokemon - ex" in card_type)
                filtered_card_objects = [
                    card for card in filtered_card_objects
                    if (card.name and card.name.lower().endswith(' ex') and not card.name.lower().endswith(' - ex (ultra beast)')) or
                       (card.card_type and 'pokemon - ex' in card.card_type.lower())
                ]
            else:
                # For other stage types (Basic, Stage 1, Stage 2, etc.) or trainer types (Item, Supporter, etc.)
                filtered_card_objects = [
                    card for card in filtered_card_objects
                    if card.card_type and stage_type in card.card_type
                ]

        # Apply keyword-based rarity filter
        if parsed_keywords['rarities']:
            if parsed_keywords.get('is_shiny_search', False):
                # Special handling for "shiny" searches: include regular shiny cards plus specific Promo-A cards
                filtered_card_objects = [
                    card for card in filtered_card_objects
                    if (card.rarity in parsed_keywords['rarities']) or  
                       (hasattr(card, 'card_number_str') and card.card_number_str in ['50', '51'] and 
                        getattr(card, 'set_name', None) == 'Promo-A')
                ]
            else:
                filtered_card_objects = [
                    card for card in filtered_card_objects
                    if card.rarity in parsed_keywords['rarities']
                ]

        # Apply keyword-based set filter
        if parsed_keywords['set_code']:
            filtered_card_objects = [
                card for card in filtered_card_objects
                if (hasattr(card, 'set_code') and card.set_code == parsed_keywords['set_code']) or
                   (hasattr(card, 'set_name') and card.set_name == parsed_keywords['set_code'])
            ]

        # Apply remaining text as name filter (after keyword extraction)
        if parsed_keywords['remaining_text']:
            remaining_text = parsed_keywords['remaining_text'].lower()
            filtered_card_objects = [
                card
                for card in filtered_card_objects
                if card.name and remaining_text in card.name.lower()
            ]
        
        # Apply exclude_ex filter if requested
        if parsed_keywords['exclude_ex']:
            filtered_card_objects = [
                card for card in filtered_card_objects
                if not ((card.name and card.name.lower().endswith(' ex')) or
                        (card.card_type and 'pokemon - ex' in card.card_type.lower()))
            ]

        # Convert Card objects to dictionaries for JSON response
        # The Card.to_dict() method should prepare the data correctly.
        # The Card.display_image_path property will be accessed when to_dict() is called if it's part of it,
        # or we add it explicitly if to_dict() doesn't include properties.

        card_dicts = []
        for card_obj in filtered_card_objects:
            card_dict = (
                card_obj.to_dict()
            )  # Card.to_dict() should return all necessary fields
            
            # Process URL for CDN conversion on server side
            card_dict['display_image_path'] = url_service.process_firebase_to_cdn_url(card_obj.display_image_path)
                
            # Generate high-res path from CDN URL
            if card_dict['display_image_path']:
                card_dict['high_res_image_path'] = card_dict['display_image_path'].replace('/cards/', '/high_res_cards/')
                
            card_dicts.append(card_dict)

        current_app.logger.info(
            f"Returning {len(card_dicts)} cards after filtering from CardCollection."
        )
        return jsonify({"cards": card_dicts, "success": True})

    except Exception as e:
        current_app.logger.error(
            f"Error processing cards from CardCollection in /api/cards: {e}",
            exc_info=True,
        )
        return jsonify({"error": "Failed to process card data.", "success": False}), 500


@decks_bp.route("/api/cards/paginated", methods=["GET"])
@rate_limit_api_paginated()
def get_cards_paginated():
    """API endpoint to get cards with pagination and server-side filtering."""
    # Use get_full_card_collection to ensure all cards are available for search
    card_collection = card_service.get_full_card_collection()

    if not card_collection or not hasattr(card_collection, "cards"):
        current_app.logger.error(
            "CardCollection not found or not initialized in app.config for /api/cards/paginated."
        )
        return (
            jsonify(
                {
                    "error": "Card data is currently unavailable. Please try again later.",
                    "success": False,
                }
            ),
            503,
        )

    try:
        # Get pagination parameters
        page = int(request.args.get("page", 1))
        limit = min(int(request.args.get("limit", 20)), 100)  # Max 100 cards per page
        offset = (page - 1) * limit

        # Get filter parameters
        set_code_filter = request.args.get("set_code")
        energy_type_filter = request.args.get("energy_type")
        card_type_filter = request.args.get("card_type")
        stage_type_filter = request.args.get("stage_type")
        rarity_filter = request.args.get("rarity")
        name_filter = request.args.get("name", "").strip()

        # Parse name_filter for keywords
        parsed_keywords = parse_search_keywords(name_filter) if name_filter else {
            'energy_types': [], 'card_type': None, 'stage_type': None, 
            'rarities': [], 'set_code': None, 'exclude_ex': False, 'remaining_text': ''
        }

        # Start with all cards from the collection
        all_cards_from_collection = card_collection.cards
        filtered_card_objects = all_cards_from_collection

        # Apply server-side filters
        # Apply keyword-based set filter first (takes precedence over URL parameter)
        if parsed_keywords['set_code']:
            filtered_card_objects = [
                card for card in filtered_card_objects
                if (hasattr(card, 'set_code') and card.set_code == parsed_keywords['set_code']) or
                   (hasattr(card, 'set_name') and card.set_name == parsed_keywords['set_code'])
            ]
        elif set_code_filter and set_code_filter != "All":
            filtered_card_objects = [
                card for card in filtered_card_objects
                if (hasattr(card, 'set_code') and card.set_code == set_code_filter) or
                   (hasattr(card, 'set_name') and card.set_name == set_code_filter)
            ]

        # Apply keyword-based energy type filter (takes precedence over URL parameter)
        if parsed_keywords['energy_types']:
            filtered_card_objects = [
                card for card in filtered_card_objects
                if hasattr(card, 'energy_type') and card.energy_type in parsed_keywords['energy_types']
            ]
        elif energy_type_filter and energy_type_filter != "All":
            filtered_card_objects = [
                card for card in filtered_card_objects
                if hasattr(card, 'energy_type') and card.energy_type == energy_type_filter
            ]

        # Apply keyword-based card type filter (takes precedence over URL parameter)
        if parsed_keywords['card_type']:
            if parsed_keywords['card_type'] == "Pokémon":
                filtered_card_objects = [
                    card for card in filtered_card_objects
                    if hasattr(card, 'card_type') and card.card_type and "Pokémon" in card.card_type
                ]
            elif parsed_keywords['card_type'] == "Trainer":
                filtered_card_objects = [
                    card for card in filtered_card_objects
                    if hasattr(card, 'card_type') and card.card_type and "Trainer" in card.card_type
                ]
        elif card_type_filter and card_type_filter != "All":
            if card_type_filter == "Pokémon":
                filtered_card_objects = [
                    card for card in filtered_card_objects
                    if hasattr(card, 'card_type') and card.card_type and "Pokémon" in card.card_type
                ]
            elif card_type_filter == "Trainer":
                filtered_card_objects = [
                    card for card in filtered_card_objects
                    if hasattr(card, 'card_type') and card.card_type and "Trainer" in card.card_type
                ]

        # Apply keyword-based stage type filter (takes precedence over URL parameter)
        if parsed_keywords['stage_type']:
            stage_type = parsed_keywords['stage_type']
            if stage_type == "EX":
                # Filter for EX cards (cards ending with " ex" in name or having "pokemon - ex" in card_type)
                filtered_card_objects = [
                    card for card in filtered_card_objects
                    if (card.name and card.name.lower().endswith(' ex') and not card.name.lower().endswith(' - ex (ultra beast)')) or
                       (card.card_type and 'pokemon - ex' in card.card_type.lower())
                ]
            else:
                # For other stage types (Basic, Stage 1, Stage 2, etc.) or trainer types (Item, Supporter, etc.)
                filtered_card_objects = [
                    card for card in filtered_card_objects
                    if card.card_type and stage_type in card.card_type
                ]
        elif stage_type_filter and stage_type_filter != "All":
            if stage_type_filter == "EX":
                # Filter for EX cards (cards ending with " ex" in name or having "pokemon - ex" in card_type)
                filtered_card_objects = [
                    card for card in filtered_card_objects
                    if (card.name and card.name.lower().endswith(' ex') and not card.name.lower().endswith(' - ex (ultra beast)')) or
                       (card.card_type and 'pokemon - ex' in card.card_type.lower())
                ]
            else:
                # For other stage types (Basic, Stage 1, Stage 2, etc.) or trainer types (Item, Supporter, etc.)
                filtered_card_objects = [
                    card for card in filtered_card_objects
                    if card.card_type and stage_type_filter in card.card_type
                ]

        # Apply keyword-based rarity filter (takes precedence over URL parameter)
        if parsed_keywords['rarities']:
            if parsed_keywords.get('is_shiny_search', False):
                current_app.logger.info(f"DEBUG: Shiny search detected in paginated endpoint, looking for Promo-A cards with IDs 50, 51")
                # Special handling for "shiny" searches: include regular shiny cards plus specific Promo-A cards
                promo_cards_found = []
                for card in filtered_card_objects:
                    if hasattr(card, 'card_number_str') and card.card_number_str in ['50', '51'] and getattr(card, 'set_name', None) == 'Promo-A':
                        promo_cards_found.append(f"CardNum:{card.card_number_str}, Name:{card.name}, Set:{card.set_name}")
                
                if promo_cards_found:
                    current_app.logger.info(f"DEBUG: Found Promo-A cards in paginated: {promo_cards_found}")
                else:
                    current_app.logger.info(f"DEBUG: No Promo-A cards with IDs 50,51 found in paginated")
                
                filtered_card_objects = [
                    card for card in filtered_card_objects
                    if (card.rarity in parsed_keywords['rarities']) or  
                       (hasattr(card, 'card_number_str') and card.card_number_str in ['50', '51'] and 
                        getattr(card, 'set_name', None) == 'Promo-A')
                ]
            else:
                filtered_card_objects = [
                    card for card in filtered_card_objects
                    if card.rarity in parsed_keywords['rarities']
                ]
        elif rarity_filter and rarity_filter != "All":
            filtered_card_objects = [
                card for card in filtered_card_objects
                if card.rarity == rarity_filter
            ]

        # Apply remaining text as name filter (after keyword extraction)
        if parsed_keywords['remaining_text']:
            remaining_text = parsed_keywords['remaining_text'].lower()
            search_terms = remaining_text.split()
            
            def card_matches_search_terms(card):
                # Only search in card names for partial matches
                # Card types and energy types are only matched via complete keywords
                card_name = card.name.lower() if card.name else ""
                
                # Check if all search terms are found in the card name
                return all(term in card_name for term in search_terms)
            
            filtered_card_objects = [
                card for card in filtered_card_objects
                if card_matches_search_terms(card)
            ]
        
        # Apply exclude_ex filter if requested
        if parsed_keywords['exclude_ex']:
            filtered_card_objects = [
                card for card in filtered_card_objects
                if not ((card.name and card.name.lower().endswith(' ex')) or
                        (card.card_type and 'pokemon - ex' in card.card_type.lower()))
            ]

        # Get sorting parameters
        sort_type = request.args.get("sort", "name")
        direction = request.args.get("direction", "asc")
        
        # Apply sorting
        if sort_type == "name":
            filtered_card_objects.sort(key=lambda card: card.name.lower() if card.name else "", reverse=(direction == "desc"))
        elif sort_type == "rarity":
            # Define rarity order - matches frontend exactly
            rarity_order = {
                'Crown Rare': 0, '✵✵': 1, '✵': 2,
                '☆☆☆': 3, '☆☆': 4, '☆': 5,
                '◊◊◊◊': 6, '◊◊◊': 7, '◊◊': 8, '◊': 9,
                # Legacy mappings for compatibility
                "Ultra Rare": 1, "♦♦♦♦": 1,
                "Rare": 2, "♦♦♦": 2,
                "Uncommon": 3, "♦♦": 3,
                "Common": 4, "♦": 4
            }
            def rarity_sort_key(card):
                # Primary sort: Rarity
                rarity_priority = rarity_order.get(card.rarity, 99) if card.rarity else 99
                
                # Secondary sort: Most recent set (using same logic as set sorting)
                set_name = card.set_name if card.set_name else ""
                set_priority = SET_RELEASE_ORDER.get(set_name, 999)
                
                # Promo-A should ALWAYS be at the bottom regardless of sort direction
                if set_name == "Promo-A":
                    set_priority = 999  # Make Promo-A always come last
                
                return (rarity_priority, set_priority)
            
            filtered_card_objects.sort(
                key=rarity_sort_key, 
                reverse=(direction == "desc")
            )
        elif sort_type == "type":
            # Sort by card type with sophisticated ordering
            def get_card_sort_key(card):
                if not card.card_type:
                    return (99, "", "")
                
                # Use type order that matches frontend exactly
                type_priority = {
                    'Grass': 0, 'Fire': 1, 'Water': 2, 'Lightning': 3, 
                    'Psychic': 4, 'Fighting': 5, 'Darkness': 6, 'Metal': 7, 
                    'Dragon': 8, 'Colorless': 9, 'Trainer': 10,
                    # Legacy mappings for compatibility
                    'Electric': 3, 'Dark': 6
                }.get(card.energy_type if card.is_pokemon else 'Trainer', 99)
                
                # Stage order that matches frontend exactly
                if card.is_pokemon:
                    stage_priority = {
                        'Stage 2': 0, 'Stage 1': 1, 'Basic': 2, 'Ultra Beast': 6
                    }.get(getattr(card, 'stage', None) or 'Basic', 99)
                elif card.is_trainer:
                    stage_priority = {
                        'Item': 3, 'Supporter': 4, 'Tool': 5
                    }.get(card.trainer_subtype, 99)
                else:
                    stage_priority = 99
                
                # Add set-based secondary sorting (same logic as set sorting)
                set_priority = SET_RELEASE_ORDER.get(card.set_name, 999)
                
                # Handle direction for set sorting (same logic as main set sort)
                # Promo-A should ALWAYS be at the bottom regardless of sort direction
                if card.set_name == "Promo-A":
                    set_priority = 999  # Make Promo-A always come last
                
                return (type_priority, stage_priority, set_priority, 0)
            
            filtered_card_objects.sort(
                key=get_card_sort_key, 
                reverse=(direction == "desc")
            )
        elif sort_type == "set":
            # Sort by set release order (most recent first), then by card number within each set
            def set_sort_key(card):
                set_name = card.set_name if card.set_name else ""
                
                # Get set priority (lower number = more recent)
                set_priority = SET_RELEASE_ORDER.get(set_name, 999)  # Unknown sets go to the end
                
                # Handle direction for set sorting
                if direction == "desc":
                    # For descending: we want oldest set first (Genetic Apex), then newer sets
                    # So we invert the priorities: highest number becomes 1, etc.
                    if set_name != "Promo-A" and set_name in SET_RELEASE_ORDER:
                        max_priority = max(v for k, v in SET_RELEASE_ORDER.items() if k != "Promo-A")
                        set_priority = (max_priority + 1) - set_priority  # Auto-invert based on current max
                    # Promo-A should ALWAYS be at the bottom regardless of sort direction
                    if set_name == "Promo-A":
                        set_priority = 999  # Make Promo-A always come last
                else:
                    # For ascending: keep normal order (Eevee Grove first)
                    # Promo-A should ALWAYS be at the bottom regardless of sort direction
                    if set_name == "Promo-A":
                        set_priority = 999  # Make Promo-A always come last
                
                # Use card_number (integer) if available, otherwise try to extract from card_number_str
                card_num = card.card_number if card.card_number is not None else 0
                if card_num == 0 and hasattr(card, 'card_number_str') and card.card_number_str:
                    try:
                        # Try to extract numeric part from card_number_str (e.g. "123a" -> 123)
                        import re
                        match = re.search(r'(\d+)', str(card.card_number_str))
                        card_num = int(match.group(1)) if match else 0
                    except:
                        card_num = 0
                        
                return (set_priority, card_num)
            
            filtered_card_objects.sort(key=set_sort_key)

        # Calculate pagination metadata
        total_count = len(filtered_card_objects)
        has_more = (offset + limit) < total_count
        
        # Apply pagination
        paginated_cards = filtered_card_objects[offset:offset + limit]

        # Convert Card objects to dictionaries for JSON response
        card_dicts = []
        for card_obj in paginated_cards:
            card_dict = card_obj.to_dict()
            
            # Process URL for CDN conversion on server side
            card_dict['display_image_path'] = url_service.process_firebase_to_cdn_url(card_obj.display_image_path)
                
            # Generate high-res path from CDN URL
            if card_dict['display_image_path']:
                card_dict['high_res_image_path'] = card_dict['display_image_path'].replace('/cards/', '/high_res_cards/')
                
            card_dicts.append(card_dict)

        current_app.logger.info(
            f"Returning page {page} with {len(card_dicts)} cards (total: {total_count}) from CardCollection."
        )

        response = jsonify({
            "cards": card_dicts,
            "success": True,
            "pagination": {
                "current_page": page,
                "total_count": total_count,
                "has_more": has_more,
                "page_size": limit,
                "total_pages": (total_count + limit - 1) // limit
            }
        })
        
        # Add enhanced cache headers for better performance
        response.headers['Cache-Control'] = 'public, max-age=600, s-maxage=1800'  # 10 minutes client, 30 minutes proxy
        cache_key = f"{page}-{limit}-{set_code_filter}-{energy_type_filter}-{card_type_filter}-{stage_type_filter}-{rarity_filter}-{name_filter}-{total_count}"
        response.headers['ETag'] = f'"{hash(cache_key)}"'
        
        # Add rate limiting information to help client-side throttling
        response.headers['X-RateLimit-Limit'] = '1000'
        response.headers['X-RateLimit-Window'] = '60'
        
        return response

    except ValueError as e:
        current_app.logger.warning(f"Invalid pagination parameters in /api/cards/paginated: {e}")
        return jsonify({"error": "Invalid pagination parameters.", "success": False}), 400

    except Exception as e:
        current_app.logger.error(
            f"Error processing paginated cards from CardCollection: {e}",
            exc_info=True,
        )
        return jsonify({"error": "Failed to process paginated card data.", "success": False}), 500


@decks_bp.route("/api/decks/<string:deck_id>", methods=["GET"])
@login_required
def get_deck(deck_id: str):  # Changed 'filename' to 'deck_id'
    """API endpoint to get a specific deck by its Firestore ID."""
    db = get_db()  # Use your helper to get the Firestore client
    card_collection = card_service.get_card_collection()

    if not card_collection:
        current_app.logger.critical(
            "Card Collection not loaded in app config for get_deck API."
        )
        return (
            jsonify({"error": "Server configuration error: Card data unavailable."}),
            500,
        )

    try:
        deck_doc_ref = db.collection("decks").document(deck_id)
        deck_doc = deck_doc_ref.get()

        if not deck_doc.exists:
            return jsonify({"success": False, "error": "Deck not found"}), 404
        
        deck_data = deck_doc.to_dict()
        current_user_id = str(flask_login_current_user.id)
        
        is_owner = deck_data.get("owner_id") == current_user_id
        is_public = deck_data.get("is_public", False) is True

        if not (is_owner or is_public):
            current_app.logger.warning(
                f"User {current_user_id} attempt to access private deck {deck_id} owned by {deck_data.get('owner_id')}."
            )
            return (
                jsonify(
                    {"success": False, "error": "You do not have permission to view this deck."}
                ),
                403, 
            )

        # Use the new method from your Deck class to load from a Firestore document
        deck_obj = Deck.from_firestore_doc(deck_doc, card_collection)

        # Convert card objects in the deck to dictionaries for the JSON response
        card_dicts = []
        for card_in_deck in deck_obj.cards:  # deck_obj.cards contains Card objects
            card_detail_dict = card_in_deck.to_dict()  # Card class's to_dict()
            card_detail_dict["display_image_path"] = card_in_deck.display_image_path
            card_dicts.append(card_detail_dict)

        # Build the response dictionary using attributes from the deck_obj
        response_data = {
            "success": True,
            "deck": {
                "id": deck_obj.id,  # This is the Firestore document ID
                "name": deck_obj.name,
                "deck_types": deck_obj.deck_types,
                "cards": card_dicts,  # List of detailed card dicts
                "cover_card_ids": deck_obj.cover_card_ids,  # List of string card IDs
                "owner_id": deck_obj.owner_id,
                # Optionally include timestamps if they are useful for the client
                "created_at": (
                    deck_obj.created_at.isoformat() if deck_obj.created_at else None
                ),
                "updated_at": (
                    deck_obj.updated_at.isoformat() if deck_obj.updated_at else None
                ),
            },
        }
        return jsonify(response_data)

    # Removed FileNotFoundError as we are not loading from a file system directly for the deck.
    # Other exceptions might occur (e.g., issues with Firestore connection, card_collection).
    except Exception as e:
        current_app.logger.error(
            f"Error in get_deck API for Firestore ID {deck_id}: {e}", exc_info=True
        )
        return (
            jsonify({"success": False, "error": "An internal server error occurred."}),
            500,
        )


@decks_bp.route("/api/decks", methods=["POST"])
@rate_limit_heavy()
@login_required  # Require login to create a deck
def create_deck():
    current_fs_user = flask_login_current_user

    db = get_db()
    user_firestore_id = current_fs_user.id
    user_document_data = current_fs_user.data

    if not user_document_data:
        current_app.logger.error(
            f"User data not found for authenticated user ID: {user_firestore_id}"
        )
        return (
            jsonify(
                {"success": False, "error": "User session error. Please re-login."}
            ),
            401,
        )

    user_deck_ids_list = user_document_data.get("deck_ids", [])


    if len(user_deck_ids_list) >= MAX_DECKS_PER_USER:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"You have reached the maximum limit of {MAX_DECKS_PER_USER} decks.",
                }
            ),
            403,
        )

    try:
        deck_data_from_request = request.json
        if not deck_data_from_request:
            return jsonify({"success": False, "error": "No data received"}), 400

        card_collection = card_service.get_card_collection()
        if not card_collection:
            current_app.logger.critical("Card Collection not loaded during create_deck")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Server configuration error: Card data unavailable.",
                    }
                ),
                500,
            )

        deck_name_from_req = deck_data_from_request.get("name", "").strip()
        # card_ids_payload: list of dicts, e.g., [{"id": "123"}, {"id": "456"}]
        # where "id" is the Card's database ID (from pokemon_cards.db)
        card_ids_payload = deck_data_from_request.get("cards", [])
        deck_types_payload = deck_data_from_request.get("deck_types", [])
        user_chosen_cover_card_ids = deck_data_from_request.get("cover_card_ids", [])

        # --- Validations ---
        if not deck_name_from_req:
            return jsonify({"success": False, "error": "Deck name is required."}), 400
        if not (len(deck_name_from_req) <= 50):
            return (
                jsonify(
                    {"success": False, "error": "Deck name must be less than 50 characters."}
                ),
                400,
            )

        if profanity_check(deck_name_from_req):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Deck name contains inappropriate language. Please choose a different name.",
                    }
                ),
                400,
            )

        if _does_deck_name_exist_for_user_firestore(
            user_firestore_id, deck_name_from_req, db
        ):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"A deck named '{deck_name_from_req}' already exists. Please choose a different name.",
                    }
                ),
                400,
            )

        if (
            not card_ids_payload
            or not isinstance(card_ids_payload, list)
            or not card_ids_payload
        ):
            return jsonify({"success": False, "error": "Deck must contain cards."}), 400
        if (
            not deck_types_payload
            or not isinstance(deck_types_payload, list)
            or not deck_types_payload
        ):  # Ensure it has types
            return (
                jsonify({"success": False, "error": "Deck energy types are required."}),
                400,
            )
        if not isinstance(user_chosen_cover_card_ids, list):  # Basic type check
            return (
                jsonify(
                    {"success": False, "error": "Invalid format for cover card IDs."}
                ),
                400,
            )
        # --- End Validations ---

        # Create Deck object using the modified Deck class
        new_deck_obj = Deck(name=deck_name_from_req, owner_id=user_firestore_id)
        new_deck_obj.set_deck_types(deck_types_payload)

        valid_cards_added_count = 0
        for card_data_item in card_ids_payload:
            card_db_id_str = card_data_item.get("id")
            if card_db_id_str:
                try:
                    card_object_from_collection = card_collection.get_card_by_id(
                        int(card_db_id_str)
                    )
                    if card_object_from_collection:
                        if new_deck_obj.add_card(card_object_from_collection):
                            valid_cards_added_count += 1
                    else:
                        current_app.logger.warning(
                            f"Card ID {card_db_id_str} (payload) not found in master card collection."
                        )
                except ValueError:
                    current_app.logger.warning(
                        f"Invalid card ID format in payload: {card_db_id_str}. Expected int."
                    )

        if valid_cards_added_count == 0:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No valid cards were added. Check card IDs.",
                    }
                ),
                400,
            )

        new_deck_obj.set_cover_card_ids(user_chosen_cover_card_ids)

        # --- Persistence to Firestore ---
        deck_firestore_id = str(uuid.uuid4())
        new_deck_obj.id = deck_firestore_id

        deck_data_to_save_in_firestore = new_deck_obj.to_firestore_dict()

        batch = db.batch()
        deck_doc_ref = db.collection("decks").document(deck_firestore_id)
        batch.set(deck_doc_ref, deck_data_to_save_in_firestore)

        user_doc_ref = db.collection("users").document(user_firestore_id)
        batch.update(
            user_doc_ref, {"deck_ids": firestore.ArrayUnion([deck_firestore_id])}
        )

        batch.commit()

        current_app.logger.info(
            f"Deck '{deck_name_from_req}' (FS ID: {deck_firestore_id}) created for user {user_firestore_id}."
        )

        if (
            hasattr(flask_login_current_user, "data")
            and "deck_ids" in flask_login_current_user.data
        ):
            if deck_firestore_id not in flask_login_current_user.data["deck_ids"]:
                flask_login_current_user.data["deck_ids"].append(deck_firestore_id)
        elif hasattr(flask_login_current_user, "data"):
            flask_login_current_user.data["deck_ids"] = [deck_firestore_id]

        if len(user_deck_ids_list) + 1 == MAX_DECKS_PER_USER:
            session["display_toast_once"] = {
                "message": f"You have now reached the maximum of {MAX_DECKS_PER_USER} decks.",
                "type": "warning",
            }

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Deck created successfully!",
                    "deck_id": deck_firestore_id,
                    "cover_card_ids": new_deck_obj.cover_card_ids,
                }
            ),
            201,
        )

    except Exception as e:
        current_app.logger.error(f"Error in create_deck endpoint: {e}", exc_info=True)
        return (
            jsonify({"success": False, "error": "An internal server error occurred."}),
            500,
        )


@decks_bp.route(
    "/api/decks/<string:deck_id>", methods=["PUT"]
)  # deck_id is now Firestore document ID
@login_required
def update_deck(deck_id: str):
    current_fs_user = flask_login_current_user
    db = get_db()
    user_firestore_id = current_fs_user.id

    try:
        deck_doc_ref = db.collection("decks").document(deck_id)
        deck_doc = deck_doc_ref.get()

        if not deck_doc.exists:
            return jsonify({"success": False, "error": "Deck not found."}), 404

        existing_deck_data = deck_doc.to_dict()
        if existing_deck_data.get("owner_id") != user_firestore_id:
            current_app.logger.warning(
                f"User {user_firestore_id} attempt to update deck {deck_id} owned by {existing_deck_data.get('owner_id')}."
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Permission denied to update this deck.",
                    }
                ),
                403,
            )

        deck_data_from_request = request.json
        if not deck_data_from_request:
            return (
                jsonify({"success": False, "error": "No data received for update."}),
                400,
            )

        card_collection = card_service.get_card_collection()
        if not card_collection:
            current_app.logger.critical("Card Collection not loaded during update_deck")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Server configuration error: Card data unavailable.",
                    }
                ),
                500,
            )

        new_deck_name_from_req = deck_data_from_request.get("name", "").strip()
        card_ids_payload = deck_data_from_request.get("cards", [])
        deck_types_payload = deck_data_from_request.get("deck_types", [])
        user_chosen_cover_card_ids = deck_data_from_request.get("cover_card_ids", [])

        # --- Validations ---
        if not new_deck_name_from_req:
            return (
                jsonify({"success": False, "error": "Deck name cannot be empty."}),
                400,
            )
        if not (len(new_deck_name_from_req) <= 50):
            return (
                jsonify(
                    {"success": False, "error": "Deck name must be less than 50 characters."}
                ),
                400,
            )

        if profanity_check(new_deck_name_from_req):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Deck name contains inappropriate language. Please choose a different name.",
                    }
                ),
                400,
            )

        # Check for name uniqueness, excluding the current deck itself
        if _does_deck_name_exist_for_user_firestore(
            user_firestore_id, new_deck_name_from_req, db, exclude_deck_id=deck_id
        ):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Another deck named '{new_deck_name_from_req}' already exists. Please choose a different name.",
                    }
                ),
                400,
            )

        if (
            not card_ids_payload
            or not isinstance(card_ids_payload, list)
            or not card_ids_payload
        ):
            return jsonify({"success": False, "error": "Deck must contain cards."}), 400
        if (
            not deck_types_payload
            or not isinstance(deck_types_payload, list)
            or not deck_types_payload
        ):
            return (
                jsonify({"success": False, "error": "Deck energy types are required."}),
                400,
            )
        if not isinstance(user_chosen_cover_card_ids, list):
            return (
                jsonify(
                    {"success": False, "error": "Invalid format for cover card IDs."}
                ),
                400,
            )
        # --- End Validations ---

        # Load the existing deck into a Deck object to apply updates
        deck_to_update = Deck.from_firestore_doc(deck_doc, card_collection)

        # Apply changes from the request to the Deck object
        deck_to_update.name = (
            new_deck_name_from_req  # Setter in Deck class updates name_lowercase
        )
        deck_to_update.set_deck_types(deck_types_payload)

        # Repopulate cards: Clear existing and add new ones
        deck_to_update.clear()  # Clears cards, card_counts, and cover_card_ids

        valid_cards_added_count = 0
        for card_data_item in card_ids_payload:
            card_db_id_str = card_data_item.get("id")
            if card_db_id_str:
                try:
                    card_object_from_collection = card_collection.get_card_by_id(
                        int(card_db_id_str)
                    )
                    if card_object_from_collection:
                        if deck_to_update.add_card(card_object_from_collection):
                            valid_cards_added_count += 1
                    else:
                        current_app.logger.warning(
                            f"Update: Card ID {card_db_id_str} not found in collection."
                        )
                except ValueError:
                    current_app.logger.warning(
                        f"Update: Invalid card ID format {card_db_id_str}."
                    )

        if valid_cards_added_count == 0:  # Or if deck_to_update.cards is empty
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Deck cannot be empty after update. No valid cards provided.",
                    }
                ),
                400,
            )

        deck_to_update.set_cover_card_ids(user_chosen_cover_card_ids)
        # select_cover_card_automatically will be called by to_firestore_dict if needed

        # --- Persistence: Update Firestore Document ---
        updated_deck_firestore_data = deck_to_update.to_firestore_dict()

        # Ensure crucial original fields are not accidentally changed by to_firestore_dict
        # owner_id should already be correct on deck_to_update if set by from_firestore_doc and not changed
        # created_at is set to SERVER_TIMESTAMP by to_firestore_dict ONLY if deck_to_update.created_at is None.
        # Since we loaded it from an existing doc, deck_to_update.created_at is a datetime object,
        # so to_firestore_dict will not try to set it again.
        # updated_at will be set to firestore.SERVER_TIMESTAMP by to_firestore_dict().

        deck_doc_ref.update(updated_deck_firestore_data)
        current_app.logger.info(
            f"Deck '{new_deck_name_from_req}' (ID: {deck_id}) updated by user {user_firestore_id}."
        )

        return jsonify(
            {
                "success": True,
                "message": "Deck updated successfully!",
                "deck_id": deck_id,  # The ID of the deck that was updated
                "cover_card_ids": deck_to_update.cover_card_ids,  # Return the final list
            }
        )

    except Exception as e:
        current_app.logger.error(
            f"Error in update_deck for ID {deck_id}: {e}", exc_info=True
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "An internal server error occurred while updating the deck.",
                }
            ),
            500,
        )


@decks_bp.route("/api/decks/<string:deck_id>", methods=["DELETE"])
@login_required
def delete_deck(deck_id: str):
    """API endpoint to delete a deck from Firestore."""
    current_fs_user = flask_login_current_user
    db = get_db()
    user_firestore_id = current_fs_user.id

    try:
        deck_doc_ref = db.collection("decks").document(deck_id)
        deck_doc = deck_doc_ref.get()

        if not deck_doc.exists:
            return jsonify({"success": False, "error": "Deck not found."}), 404

        deck_data = deck_doc.to_dict()
        if deck_data.get("owner_id") != user_firestore_id:
            current_app.logger.warning(
                f"User {user_firestore_id} attempt to delete deck {deck_id} owned by {deck_data.get('owner_id')}."
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Permission denied to delete this deck.",
                    }
                ),
                403,
            )

        # Use a batched write to delete deck and update user's deck_ids atomically
        batch = db.batch()

        # 1. Delete the deck document from the 'decks' collection
        batch.delete(deck_doc_ref)

        # 2. Remove the deck's ID from the user's 'deck_ids' array
        user_doc_ref = db.collection("users").document(user_firestore_id)
        batch.update(user_doc_ref, {"deck_ids": firestore.ArrayRemove([deck_id])})

        batch.commit()

        current_app.logger.info(
            f"Deck (ID: {deck_id}) deleted successfully by user {user_firestore_id}."
        )

        # Update flask_login_current_user.data in session if immediate reflection is needed
        if (
            hasattr(flask_login_current_user, "data")
            and "deck_ids" in flask_login_current_user.data
        ):
            if deck_id in flask_login_current_user.data["deck_ids"]:
                flask_login_current_user.data["deck_ids"].remove(deck_id)

        return jsonify({"success": True, "message": "Deck deleted successfully."}), 200

    except Exception as e:
        current_app.logger.error(
            f"Error deleting deck (ID: {deck_id}): {e}", exc_info=True
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "An internal server error occurred while deleting the deck.",
                }
            ),
            500,
        )


@decks_bp.route("/api/decks/<string:deck_id>/description", methods=["POST"])
@login_required
def update_deck_description(deck_id: str):
    """Update the description of a deck."""
    try:
        db = get_db()
        current_user_id = flask_login_current_user.id
        
        # Get request data
        data = request.get_json()
        description = data.get("description", "").strip()
        
        # Validate description length
        if description and len(description) > 100:
            return jsonify({
                "success": False,
                "error": "Description must be 100 characters or less."
            }), 400
        
        # Profanity check
        if description and profanity_check(description):
            return jsonify({
                "success": False,
                "error": "Description contains inappropriate language."
            }), 400
        
        # Get the deck document
        deck_ref = db.collection("decks").document(deck_id)
        deck_doc = deck_ref.get()
        
        if not deck_doc.exists:
            return jsonify({
                "success": False,
                "error": "Deck not found."
            }), 404
        
        deck_data = deck_doc.to_dict()
        
        # Verify ownership
        if deck_data.get("owner_id") != current_user_id:
            return jsonify({
                "success": False,
                "error": "You can only modify your own decks."
            }), 403
        
        # Update description
        deck_ref.update({
            "description": description
        })
        
        return jsonify({
            "success": True,
            "message": "Description updated successfully."
        }), 200
        
    except Exception as e:
        current_app.logger.error(
            f"Error updating deck description (ID: {deck_id}): {e}", exc_info=True
        )
        return jsonify({
            "success": False,
            "error": "An error occurred while updating the description."
        }), 500


# Change the route and method for copy_deck
@decks_bp.route(
    "/api/decks/<string:original_deck_id>/copy", methods=["POST"]
)  # CHANGED
@login_required
def copy_deck(
    original_deck_id: str,
):  # Function name kept, parameter is original_deck_id
    current_fs_user = flask_login_current_user
    db = get_db()
    user_firestore_id = current_fs_user.id
    user_document_data = current_fs_user.data

    user_deck_ids_list = user_document_data.get("deck_ids", [])
    if len(user_deck_ids_list) >= MAX_DECKS_PER_USER:
        # For an API endpoint, return JSON
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"You have reached the maximum limit of {MAX_DECKS_PER_USER} decks. Cannot create a copy.",
                }
            ),
            403,
        )

    card_collection = card_service.get_card_collection()
    if not card_collection:
        current_app.logger.critical(
            "Card Collection not loaded during copy_deck (Python)"
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Server configuration error: Card data unavailable.",
                }
            ),
            500,
        )

    try:
        original_deck_doc_ref = db.collection("decks").document(original_deck_id)
        original_deck_doc = original_deck_doc_ref.get()

        if not original_deck_doc.exists:
            return (
                jsonify(
                    {"success": False, "error": "Original deck to copy was not found."}
                ),
                404,
            )

        original_deck_data = original_deck_doc.to_dict()

        can_copy_deck = False
        if original_deck_data.get("owner_id") == user_firestore_id:
            can_copy_deck = True
        elif original_deck_data.get("is_public", False) is True:
            can_copy_deck = True

        if not can_copy_deck:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "You do not have permission to copy this deck.",
                    }
                ),
                403,
            )

        copied_deck_obj = Deck.from_firestore_doc(original_deck_doc, card_collection)
        new_deck_firestore_id = str(uuid.uuid4())
        copied_deck_obj.id = new_deck_firestore_id
        copied_deck_obj.owner_id = user_firestore_id
        
        # Explicitly preserve the description from original deck
        original_description = original_deck_data.get("description", "")
        copied_deck_obj.description = original_description
        
        current_app.logger.info(f"Copying deck '{original_deck_data.get('name')}' with description: '{original_description}'")

        original_name = original_deck_data.get("name", "Unnamed Deck")
        new_deck_name = f"Copy of {original_name}"
        temp_new_name = new_deck_name
        copy_count = 1
        while _does_deck_name_exist_for_user_firestore(
            user_firestore_id, temp_new_name, db
        ):
            temp_new_name = f"{new_deck_name} ({copy_count})"
            copy_count += 1
            if copy_count > 10:
                # If too many copies, create with a less ideal name and let user rename
                temp_new_name = f"Copy of {original_name} - {uuid.uuid4().hex[:4]}"
                break
        copied_deck_obj.name = temp_new_name

        copied_deck_obj.created_at = None
        copied_deck_obj.updated_at = None

        if hasattr(copied_deck_obj, "is_public"):  # Assuming Deck class might have this
            copied_deck_obj.is_public = False  # Copies are private by default

        new_deck_data_to_save = copied_deck_obj.to_firestore_dict()
        # If is_public isn't part of to_firestore_dict, and you need it:
        # new_deck_data_to_save['is_public'] = False

        batch = db.batch()
        new_deck_doc_ref = db.collection("decks").document(new_deck_firestore_id)
        batch.set(new_deck_doc_ref, new_deck_data_to_save)
        user_doc_ref = db.collection("users").document(user_firestore_id)
        batch.update(
            user_doc_ref, {"deck_ids": firestore.ArrayUnion([new_deck_firestore_id])}
        )
        batch.commit()

        current_app.logger.info(
            f"Deck {original_deck_id} copied to new deck {new_deck_firestore_id} for user {user_firestore_id}."
        )

        # Update flask_login_current_user.data in session for immediate reflection
        if (
            hasattr(flask_login_current_user, "data")
            and "deck_ids" in flask_login_current_user.data
        ):
            if new_deck_firestore_id not in flask_login_current_user.data["deck_ids"]:
                flask_login_current_user.data["deck_ids"].append(new_deck_firestore_id)
        elif hasattr(flask_login_current_user, "data"):
            flask_login_current_user.data["deck_ids"] = [new_deck_firestore_id]

        # For an API, return JSON
        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Deck '{original_name}' copied successfully as '{copied_deck_obj.name}'.",
                    "new_deck_id": new_deck_firestore_id,
                    "new_deck_name": copied_deck_obj.name,
                    "redirect_url": url_for(
                        "decks.list_decks", edit=new_deck_firestore_id
                    ),  # Suggest where to go
                }
            ),
            201,
        )

    except Exception as e:
        current_app.logger.error(
            f"Error copying deck (original ID: {original_deck_id}): {e}", exc_info=True
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "An internal server error occurred while copying the deck.",
                }
            ),
            500,
        )


@decks_bp.route("/deck/<deck_id>/export/<format>")
@login_required
def export_deck(deck_id, format):
    """Export a deck in various formats (json, text)."""
    db = get_db()
    current_user_id = flask_login_current_user.id
    card_collection = card_service.get_card_collection()
    
    # Get the deck
    deck_doc = db.collection("decks").document(deck_id).get()
    if not deck_doc.exists:
        flash("Deck not found.", "error")
        return redirect(url_for("decks.list_decks"))
    
    deck = Deck.from_firestore_doc(deck_doc, card_collection)
    
    # Check if user can view this deck (owner or public)
    if deck.owner_id != current_user_id and not deck.is_public:
        flash("You don't have permission to export this deck.", "error")
        return redirect(url_for("decks.list_decks"))
    
    if format == "json":
        # Export as JSON
        export_data = {
            "name": deck.name,
            "description": deck.description,
            "deck_types": deck.deck_types,
            "created_at": deck.created_at.isoformat() if deck.created_at else None,
            "is_public": deck.is_public,
            "cards": []
        }
        
        # Group cards by name and count
        card_counts = {}
        for card in deck.cards:
            if card.name not in card_counts:
                card_counts[card.name] = {
                    "count": 0,
                    "card_data": {
                        "id": card.id,
                        "name": card.name,
                        "energy_type": card.energy_type,
                        "card_type": card.card_type,
                        "hp": card.hp,
                        "rarity": card.rarity,
                        "set_name": card.set_name
                    }
                }
            card_counts[card.name]["count"] += 1
        
        for card_name, data in card_counts.items():
            export_data["cards"].append({
                "count": data["count"],
                **data["card_data"]
            })
        
        response = current_app.response_class(
            json.dumps(export_data, indent=2),
            mimetype="application/json"
        )
        response.headers["Content-Disposition"] = f"attachment; filename={deck.name}_deck.json"
        return response
    
    elif format == "text":
        # Export as plain text
        lines = [
            f"=== {deck.name} ===",
            f"Types: {', '.join(deck.deck_types) if deck.deck_types else 'Unspecified'}",
        ]
        
        if deck.description:
            lines.append(f"Description: {deck.description}")
        
        lines.append("")
        
        # Group cards by type
        pokemon = []
        trainers = []
        
        for card in deck.cards:
            if hasattr(card, 'is_pokemon') and card.is_pokemon:
                pokemon.append(card)
            elif hasattr(card, 'is_trainer') and card.is_trainer:
                trainers.append(card)
        
        # Pokemon section
        if pokemon:
            lines.append("Pokemon:")
            pokemon_counts = {}
            for card in pokemon:
                if card.name not in pokemon_counts:
                    pokemon_counts[card.name] = 0
                pokemon_counts[card.name] += 1
            
            for name, count in sorted(pokemon_counts.items()):
                lines.append(f"  {count}x {name}")
            lines.append("")
        
        # Trainers section
        if trainers:
            lines.append("Trainers:")
            trainer_counts = {}
            for card in trainers:
                if card.name not in trainer_counts:
                    trainer_counts[card.name] = 0
                trainer_counts[card.name] += 1
            
            for name, count in sorted(trainer_counts.items()):
                lines.append(f"  {count}x {name}")
            lines.append("")
        
        lines.append(f"Total Cards: {len(deck.cards)}/20")
        
        if deck.created_at:
            lines.append(f"Created: {deck.created_at.strftime('%Y-%m-%d')}")
        
        text_content = "\n".join(lines)
        response = current_app.response_class(
            text_content,
            mimetype="text/plain"
        )
        response.headers["Content-Disposition"] = f"attachment; filename={deck.name}_deck.txt"
        return response
    
    elif format == "image":
        # Export as image - render special template for image capture
        
        # Sort cards: Pokemon first, then trainers, with duplicates grouped together
        pokemon_cards = []
        trainer_cards = []
        
        for card in deck.cards:
            if hasattr(card, 'is_pokemon') and card.is_pokemon:
                pokemon_cards.append(card)
            elif hasattr(card, 'is_trainer') and card.is_trainer:
                trainer_cards.append(card)
        
        # Group cards by name to handle duplicates
        def group_cards_by_name(cards):
            grouped = {}
            for card in cards:
                if card.name not in grouped:
                    grouped[card.name] = []
                grouped[card.name].append(card)
            return grouped
        
        pokemon_grouped = group_cards_by_name(pokemon_cards)
        trainer_grouped = group_cards_by_name(trainer_cards)
        
        # Create ordered list with duplicates adjacent
        ordered_cards = []
        
        # Add pokemon cards (grouped by name)
        for card_name in sorted(pokemon_grouped.keys()):
            ordered_cards.extend(pokemon_grouped[card_name])
        
        # Add trainer cards (grouped by name)
        for card_name in sorted(trainer_grouped.keys()):
            ordered_cards.extend(trainer_grouped[card_name])
        
        # Ensure we have exactly 20 cards (pad if necessary)
        while len(ordered_cards) < 20:
            ordered_cards.append(None)  # Placeholder for empty slots
        
        # Get owner info for creator attribution
        owner_info = None
        if deck.owner_id:
            owner_doc = db.collection("users").document(deck.owner_id).get()
            if owner_doc.exists:
                owner_data = owner_doc.to_dict()
                owner_info = {
                    "username": owner_data.get("username", "Unknown"),
                    "profile_icon": owner_data.get("profile_icon", "")
                }
        
        return render_template(
            "deck_image_export.html",
            deck=deck,
            ordered_cards=ordered_cards,
            deck_types=deck.deck_types,
            owner_info=owner_info,
            config=current_app.config
        )
    
    else:
        flash("Invalid export format.", "error")
        return redirect(url_for("decks.list_decks"))



@decks_bp.route("/deck/<deck_id>/view")
def view_public_deck(deck_id):
    """Public deck viewing page (accessible without login if deck is public)."""
    db = get_db()
    card_collection = card_service.get_card_collection()
    
    # Get the deck
    deck_doc = db.collection("decks").document(deck_id).get()
    if not deck_doc.exists:
        flash("Deck not found.", "error")
        return redirect(url_for("main.index"))
    
    deck = Deck.from_firestore_doc(deck_doc, card_collection)
    
    # Check if deck is public or user is owner
    is_owner = False
    if flask_login_current_user.is_authenticated:
        is_owner = deck.owner_id == flask_login_current_user.id
    
    if not deck.is_public and not is_owner:
        flash("This deck is private.", "error")
        return redirect(url_for("main.index"))
    
    # Get owner info
    owner_info = None
    if deck.owner_id:
        owner_doc = db.collection("users").document(deck.owner_id).get()
        if owner_doc.exists:
            owner_data = owner_doc.to_dict()
            owner_info = {
                "username": owner_data.get("username", "Unknown"),
                "profile_icon": owner_data.get("profile_icon", "")
            }
    
    return render_template(
        "public_deck_view.html",
        deck=deck,
        owner=owner_info,
        is_owner=is_owner
    )
