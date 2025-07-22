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
from ..services import card_service

from firebase_admin import (
    firestore,
)

collection_bp = Blueprint("collection_bp", __name__)

# --- HELPERS (adapted from your decks.py) ---
MAX_DECKS_PER_USER = 200

def get_db() -> firestore.client:
    """Helper to get Firestore DB client from app config."""
    db = current_app.config.get("FIRESTORE_DB")
    if not db:
        raise Exception("Firestore client not available. Check app initialization.")
    return db

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

        # Sort all decks by updated_at (most recent first)
        valid_decks = []
        for deck_doc in all_deck_docs:
            if deck_doc.exists:
                deck_data = deck_doc.to_dict()
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
        card_collection_obj = card_service.get_card_collection()
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
                                # Get the correct base URL from the app's central config
                                base_url = current_app.config['ASSET_BASE_URL']
                                
                                # Get the original image path
                                image_path = getattr(card_obj, "display_image_path", None)
                                
                                if image_path:
                                    # If the image path is already a CDN URL, use it as-is
                                    if image_path.startswith('https://cdn.pvpocket.xyz'):
                                        display_image_url = image_path
                                    # If it's already a Firebase URL and we're not using CDN, use it as-is 
                                    elif (image_path.startswith('https://') and 
                                          not base_url.startswith('https://cdn.pvpocket.xyz')):
                                        display_image_url = image_path
                                    # If it's a Firebase URL and we need to convert to CDN
                                    elif (image_path.startswith('https://') and 
                                          base_url.startswith('https://cdn.pvpocket.xyz')):
                                        # Extract relative path from Firebase URLs
                                        relative_path = None
                                        if 'firebasestorage.googleapis.com' in image_path and '/o/' in image_path:
                                            # Extract the path after /o/
                                            path_part = image_path.split('/o/', 1)[1].split('?')[0]
                                            # URL decode the path
                                            from urllib.parse import unquote
                                            relative_path = unquote(path_part)
                                        elif 'storage.googleapis.com' in image_path:
                                            # Extract path from Google Cloud Storage URLs
                                            if 'pvpocket-dd286.firebasestorage.app/' in image_path:
                                                relative_path = image_path.split('pvpocket-dd286.firebasestorage.app/', 1)[1]
                                        
                                        if relative_path:
                                            display_image_url = f"{base_url}/{relative_path}"
                                        else:
                                            display_image_url = image_path
                                    # If it's a relative path, build the URL normally
                                    else:
                                        if base_url.startswith('https://cdn.pvpocket.xyz'):
                                            # For CDN, the path is direct and clean
                                            clean_path = image_path.lstrip('/')
                                            display_image_url = f"{base_url}/{clean_path}"
                                        else: 
                                            # For local development (Firebase), the path needs URL encoding and a suffix
                                            from urllib.parse import quote
                                            clean_path = image_path.lstrip('/')
                                            encoded_path = quote(clean_path, safe='')
                                            display_image_url = f"{base_url}/{encoded_path}?alt=media"
                                else:
                                    display_image_url = image_path
                                    
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