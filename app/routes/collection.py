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
)
from flask_login import current_user as flask_login_current_user, login_required
from datetime import datetime, timezone

# Removed: import os, json as they are not needed for Firestore reads here
# from .auth import is_logged_in, get_current_user_data # is_logged_in can be replaced by @login_required

# Assuming you might need datetime for handling timestamps if they are strings
# from datetime import datetime # Not needed if using Firestore Timestamps directly
from firebase_admin import (
    firestore,
)  # For firestore.SERVER_TIMESTAMP if needed elsewhere

collection_bp = Blueprint("collection_bp", __name__)


@collection_bp.route("/collection")
@login_required
def view_collection():
    """
    Renders the collection page shell and embeds the necessary URLs and config
    data for the frontend JavaScript to use.
    """
    user_email_for_display = flask_login_current_user.email

    # This dictionary will be converted to JSON and read by our script.
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
