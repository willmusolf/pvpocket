# app/routes/collection.py

from flask import (
    Blueprint,
    render_template,
    current_app,
    session,
    redirect,
    url_for,
    request,
    jsonify,
    flash,
)
from flask_login import current_user as flask_login_current_user, login_required
from datetime import datetime, timezone

import uuid
from typing import Optional
from Deck import Deck
from ..services import card_service, database_service, url_service

from firebase_admin import (
    firestore,
)

collection_bp = Blueprint("collection_bp", __name__)

# --- HELPERS (adapted from your decks.py) ---
MAX_DECKS_PER_USER = 200

# Use shared database service instead of local get_db() function
get_db = database_service.get_db

def _does_deck_name_exist_for_user_firestore(
    user_id: str,
    deck_name_to_check: str,
    db: firestore.client,
    exclude_deck_id: Optional[str] = None,
) -> bool:
    """Checks if a deck name (case-insensitive) already exists for a given user."""
    decks_ref = db.collection("decks")
    query = decks_ref.where("owner_id", "==", user_id).where(
        "name_lowercase", "==", deck_name_to_check.lower()
    )
    for doc in query.stream():
        if exclude_deck_id and doc.id == exclude_deck_id:
            continue
        return True
    return False

def passes_filters(deck_data: dict, search_text: str, energy_types: list, privacy_filter: str, card_collection_obj=None) -> bool:
    """Check if a deck passes the given filters."""
    # Privacy filter
    if privacy_filter == "public" and not deck_data.get("is_public", False):
        return False
    elif privacy_filter == "private" and deck_data.get("is_public", False):
        return False
    
    # Energy type filter
    if energy_types:
        deck_types = deck_data.get("deck_types", [])
        # Require exact match - same length and all selected types present
        if len(deck_types) != len(energy_types) or not all(energy_type in deck_types for energy_type in energy_types):
            return False
    
    # Search text filter (applied to deck name and Pokemon names in deck)
    if search_text:
        search_text_lower = search_text.lower()
        
        # First check deck name
        deck_name = deck_data.get("name", "").lower()
        if search_text_lower in deck_name:
            return True
        
        # If not found in deck name, search through Pokemon names in the deck
        if card_collection_obj:
            card_ids = deck_data.get("card_ids", [])
            for card_id_str in card_ids:
                try:
                    card_obj = card_collection_obj.get_card_by_id(int(card_id_str))
                    if card_obj:
                        card_name = getattr(card_obj, "name", "").lower()
                        if search_text_lower in card_name:
                            return True
                except (ValueError, TypeError):
                    continue
        
        # If search text wasn't found in deck name or Pokemon names, filter out this deck
        return False
    
    return True
# --- END HELPERS ---


@collection_bp.route("/collection")
@login_required
def view_collection():
    """
    Renders the collection page.
    If 'copy_from_friend_deck' is in the request, it copies the deck
    and redirects. Otherwise, it renders the collection.
    """
    deck_id_to_copy = request.args.get("copy_from_friend_deck")
    if deck_id_to_copy:
        try:
            db = get_db()
            card_collection = card_service.get_card_collection()
            current_user_id = flask_login_current_user.id

            # 1. Check user's deck limit
            user_doc = db.collection("users").document(current_user_id).get()
            user_deck_ids = user_doc.to_dict().get("deck_ids", [])
            if len(user_deck_ids) >= MAX_DECKS_PER_USER:
                session['display_toast_once'] = {"message": "Max decks reached. Cannot create copy.", "type": "error"}
                return redirect(url_for("collection_bp.view_collection"))

            # 2. Fetch the original deck and validate
            original_deck_doc = db.collection("decks").document(deck_id_to_copy).get()
            if not original_deck_doc.exists:
                session['display_toast_once'] = {"message": "Deck to copy was not found.", "type": "error"}
                return redirect(url_for("collection_bp.view_collection"))

            original_deck_data = original_deck_doc.to_dict()
            if not original_deck_data.get("is_public", False):
                session['display_toast_once'] = {"message": "You can only copy public decks.", "type": "error"}
                return redirect(url_for("collection_bp.view_collection"))

            # 3. Extract data directly from original deck without creating temp object
            original_card_ids = original_deck_data.get("card_ids", [])
            original_deck_types = original_deck_data.get("deck_types", [])
            original_cover_card_ids = original_deck_data.get("cover_card_ids", [])
            
            # 4. Find a unique name for the copy
            original_name = original_deck_data.get("name", "Unnamed Deck")
            base_new_name = f"Copy of {original_name}"
            new_deck_name = base_new_name
            copy_count = 1
            while _does_deck_name_exist_for_user_firestore(current_user_id, new_deck_name, db):
                new_deck_name = f"{base_new_name} ({copy_count})"
                copy_count += 1

            # 5. Manually construct the dictionary for the new deck
            new_deck_id = str(uuid.uuid4())
            data_to_save = {
                "name": new_deck_name,
                "name_lowercase": new_deck_name.lower(),
                "owner_id": current_user_id,
                "card_ids": original_card_ids,  # Copy directly from original
                "deck_types": original_deck_types,  # Copy directly from original
                "is_public": False,
                "description": original_deck_data.get("description", ""),
                "cover_card_ids": original_cover_card_ids,  # Copy directly from original without auto-selection
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
                "shared_at": None,
            }

            # 6. Save the new deck data to Firestore
            batch = db.batch()
            new_deck_ref = db.collection("decks").document(new_deck_id)
            batch.set(new_deck_ref, data_to_save)

            user_ref = db.collection("users").document(current_user_id)
            batch.update(user_ref, {"deck_ids": firestore.ArrayUnion([new_deck_id])})
            batch.commit()

            session['display_toast_once'] = {"message": f"Copied '{original_name}' to your collection.", "type": "success"}
            return redirect(url_for("collection_bp.view_collection"))

        except Exception as e:
            current_app.logger.error(f"Error copying deck {deck_id_to_copy}: {e}", exc_info=True)
            session['display_toast_once'] = {"message": "Error copying deck.", "type": "error"}
            return redirect(url_for("collection_bp.view_collection"))
    # --- END DECK COPYING LOGIC ---

    # Original function logic for just viewing the collection
    user_email_for_display = flask_login_current_user.email
    page_data = {
        "api_url": url_for("collection_bp.get_user_decks_api"),
        "deck_builder_url": url_for("decks.list_decks"),
        "battle_sim_url": url_for("battle.battle"),
        "energy_icon_urls": current_app.config.get("ENERGY_ICON_URLS", {}),
    }
    return render_template(
        "collection.html", email=user_email_for_display, page_data=page_data
    )


@collection_bp.route("/api/my-decks")
@login_required
def get_user_decks_api():
    """
    API endpoint to fetch, process, and return user's decks as JSON with pagination support.
    """
    db = current_app.config.get("FIRESTORE_DB")
    if not db:
        return jsonify({"error": "Database service unavailable.", "decks": []}), 503

    try:
        # Get pagination parameters
        try:
            page = max(1, int(request.args.get("page", 1)))
            limit = min(max(1, int(request.args.get("limit", 12))), 50)  # Max 50 decks per page, default 12
        except ValueError:
            return jsonify({"error": "Invalid pagination parameters", "decks": []}), 400
        
        offset = (page - 1) * limit
        
        # Get filter parameters
        search_text = request.args.get("search", "").strip().lower()
        energy_types = request.args.getlist("energy_types")  # Can have multiple
        privacy_filter = request.args.get("privacy", "all")  # all, public, private

        current_user_app_id = str(flask_login_current_user.id)
        user_doc_ref = db.collection("users").document(current_user_app_id)
        user_doc = user_doc_ref.get()

        if not user_doc.exists:
            return jsonify({"error": "User not found", "decks": [], "pagination": {"has_more": False}}), 404

        user_deck_ids = user_doc.to_dict().get("deck_ids", [])
        if not user_deck_ids:
            return jsonify({"decks": [], "pagination": {"current_page": page, "total_count": 0, "has_more": False}})

        # Get all deck documents first to sort by updated_at
        deck_refs = [
            db.collection("decks").document(deck_id)
            for deck_id in user_deck_ids
            if deck_id
        ]
        all_deck_docs = db.get_all(deck_refs)

        # Get card collection for Pokemon name searching
        card_collection_obj = card_service.get_card_collection()
        
        # Sort all decks by updated_at (most recent first) and apply filters
        valid_decks = []
        for deck_doc in all_deck_docs:
            if deck_doc.exists:
                deck_data = deck_doc.to_dict()
                
                # Apply server-side filtering (now includes Pokemon name search)
                if not passes_filters(deck_data, search_text, energy_types, privacy_filter, card_collection_obj):
                    continue
                    
                valid_decks.append((deck_doc, deck_data))

        default_time = datetime.min.replace(tzinfo=timezone.utc)
        valid_decks.sort(
            key=lambda item: item[1].get("updated_at", default_time), reverse=True
        )

        # Apply pagination after sorting
        total_count = len(valid_decks)
        paginated_decks = valid_decks[offset:offset + limit]
        has_more = offset + limit < total_count

        user_decks_details = []
        meta_stats = current_app.config.get("meta_stats", {})

        for deck_doc, deck_data in paginated_decks:
            deck_id_str = deck_doc.id

            win_rate = None
            deck_name = deck_data.get("name", f"Deck {deck_id_str[:8]}...")
            if deck_name and meta_stats.get("decks", {}).get(deck_name):
                stats = meta_stats["decks"][deck_name]
                if stats.get("total_battles", 0) > 0:
                    win_rate = (stats.get("wins", 0) / stats["total_battles"]) * 100

            resolved_cover_cards = []
            cover_card_ids_from_db = deck_data.get("cover_card_ids", [])
            seen_card_ids = set()
            if card_collection_obj and isinstance(cover_card_ids_from_db, list):
                for c_id_str in cover_card_ids_from_db:
                    if c_id_str and c_id_str not in seen_card_ids:
                        try:
                            card_obj = card_collection_obj.get_card_by_id(int(c_id_str))
                            if card_obj:
                                # Process URL for CDN conversion on server side
                                image_path = getattr(card_obj, "display_image_path", None)
                                display_image_url = url_service.process_firebase_to_cdn_url(image_path)
                                    
                                resolved_cover_cards.append(
                                    {
                                        "name": getattr(card_obj, "name", "N/A"),
                                        "display_image_path": display_image_url,
                                    }
                                )
                                seen_card_ids.add(c_id_str)
                                # Limit to 3 cover cards maximum
                                if len(resolved_cover_cards) >= 3:
                                    break
                        except (ValueError, TypeError):
                            pass

            user_decks_details.append(
                {
                    "name": deck_name,
                    "deck_id": deck_id_str,
                    "types": deck_data.get("deck_types", []),
                    "card_count": len(deck_data.get("card_ids", [])),
                    "win_rate": (round(win_rate, 1) if win_rate is not None else None),
                    "resolved_cover_cards": resolved_cover_cards,
                    "updated_at": deck_data.get("updated_at"),
                    "is_public": deck_data.get("is_public", False),
                    "description": deck_data.get("description", ""),
                }
            )

        return jsonify({
            "decks": user_decks_details,
            "pagination": {
                "current_page": page,
                "total_count": total_count,
                "has_more": has_more,
                "page_size": limit
            }
        })

    except Exception as e:
        print(
            f"Error in get_user_decks_api for {flask_login_current_user.id}: {e}",
            flush=True,
        )
        import traceback

        traceback.print_exc()
        return jsonify({"error": "An internal error occurred.", "decks": []}), 500