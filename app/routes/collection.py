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
            card_collection = current_app.config.get("card_collection")
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

            # 3. Create a temporary deck object to get card/type data
            temp_deck_obj = Deck.from_firestore_doc(original_deck_doc, card_collection)
            
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
                "card_ids": [str(card.id) for card in temp_deck_obj.cards],
                "deck_types": temp_deck_obj.deck_types,
                "is_public": False,
                "description": original_deck_data.get("description", ""),
                "cover_card_ids": original_deck_data.get("cover_card_ids", []), # Force-set from original
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
    API endpoint to fetch, process, and return all of a user's decks as JSON.
    This uses the original, reliable one-by-one fetch method.
    """
    db = current_app.config.get("FIRESTORE_DB")
    if not db:
        return jsonify({"error": "Database service unavailable.", "decks": []}), 503

    try:
        current_user_app_id = str(flask_login_current_user.id)
        user_doc_ref = db.collection("users").document(current_user_app_id)
        user_doc = user_doc_ref.get()

        if not user_doc.exists:
            return jsonify({"error": "User not found", "decks": []}), 404

        user_deck_ids = user_doc.to_dict().get("deck_ids", [])
        if not user_deck_ids:
            return jsonify({"decks": []})

        # Use a single batch request to fetch all deck documents at once.
        deck_refs = [
            db.collection("decks").document(deck_id)
            for deck_id in user_deck_ids
            if deck_id
        ]
        deck_docs = db.get_all(deck_refs)

        user_decks_details = []
        card_collection_obj = current_app.config.get("card_collection")
        meta_stats = current_app.config.get("meta_stats", {})

        for deck_doc in deck_docs:
            if not deck_doc.exists:
                continue

            deck_data = deck_doc.to_dict()
            deck_id_str = deck_doc.id

            win_rate = None
            deck_name = deck_data.get("name", f"Deck {deck_id_str[:8]}...")
            if deck_name and meta_stats.get("decks", {}).get(deck_name):
                stats = meta_stats["decks"][deck_name]
                if stats.get("total_battles", 0) > 0:
                    win_rate = (stats.get("wins", 0) / stats["total_battles"]) * 100

            resolved_cover_cards = []
            cover_card_ids_from_db = deck_data.get("cover_card_ids", [])
            if card_collection_obj and isinstance(cover_card_ids_from_db, list):
                for c_id_str in cover_card_ids_from_db:
                    if c_id_str:
                        try:
                            card_obj = card_collection_obj.get_card_by_id(int(c_id_str))
                            if card_obj:
                                resolved_cover_cards.append(
                                    {
                                        "name": getattr(card_obj, "name", "N/A"),
                                        "display_image_path": getattr(
                                            card_obj, "display_image_path", None
                                        ),
                                    }
                                )
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

        default_time = datetime.min.replace(tzinfo=timezone.utc)
        user_decks_details.sort(
            key=lambda deck: deck.get("updated_at", default_time), reverse=True
        )

        return jsonify(decks=user_decks_details)

    except Exception as e:
        print(
            f"Error in get_user_decks_api for {flask_login_current_user.id}: {e}",
            flush=True,
        )
        import traceback

        traceback.print_exc()
        return jsonify({"error": "An internal error occurred.", "decks": []}), 500