# app/routes/collection.py
from flask import (
    Blueprint,
    render_template,
    current_app,
    session,
    redirect,
    url_for,
    request,
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
@login_required  # Use Flask-Login's decorator
def view_collection():
    db = current_app.config.get("FIRESTORE_DB")
    if not db:
        session["display_toast_once"] = {
            "message": "Database service unavailable.",
            "type": "error",
        }
        return redirect(url_for("main.index"))

    current_user_app_id = str(flask_login_current_user.id)  # From Flask-Login
    user_email_for_display = flask_login_current_user.email  # From User object

    user_decks_details = []
    meta_stats = current_app.config.get("meta_stats", {})
    card_collection_obj = current_app.config.get("card_collection")

    try:
        user_doc_ref = db.collection("users").document(current_user_app_id)
        user_doc = user_doc_ref.get()

        if user_doc.exists:
            user_data_from_firestore = user_doc.to_dict()
            # Key in Firestore for user's deck list should be 'deck_ids'
            user_deck_ids_in_firestore = user_data_from_firestore.get("deck_ids", [])

            print(
                f"Loading collection for user ID '{current_user_app_id}'. Deck IDs from Firestore: {user_deck_ids_in_firestore}",
                flush=True,
            )

            for deck_id_str in user_deck_ids_in_firestore:
                if not deck_id_str:
                    continue  # Skip if an empty string somehow got into the array

                deck_doc_ref = db.collection("decks").document(deck_id_str)
                deck_doc = deck_doc_ref.get()

                if deck_doc.exists:
                    deck_data = deck_doc.to_dict()

                    win_rate = None
                    deck_name = deck_data.get("name", f"Deck {deck_id_str[:8]}...")
                    if deck_name and meta_stats.get("decks", {}).get(deck_name):
                        stats = meta_stats["decks"][deck_name]
                        if stats.get("total_battles", 0) > 0:
                            win_rate = (
                                stats.get("wins", 0) / stats["total_battles"]
                            ) * 100

                    resolved_cover_cards = []
                    cover_card_ids_from_db = deck_data.get("cover_card_ids", [])
                    if card_collection_obj and isinstance(cover_card_ids_from_db, list):
                        for c_id_str in cover_card_ids_from_db:
                            if c_id_str:
                                try:
                                    card_id_for_lookup = int(
                                        c_id_str
                                    )
                                    cover_card_obj = card_collection_obj.get_card_by_id(
                                        card_id_for_lookup
                                    )
                                    if cover_card_obj:
                                        resolved_cover_cards.append(
                                            {
                                                "name": getattr(
                                                    cover_card_obj, "name", "N/A"
                                                ),
                                                "display_image_path": getattr(
                                                    cover_card_obj,
                                                    "display_image_path",
                                                    None,
                                                ),
                                            }
                                        )
                                except ValueError:
                                    print(
                                        f"Invalid cover card ID '{c_id_str}' in deck '{deck_id_str}'.",
                                        flush=True,
                                    )

                    created_at_val = deck_data.get("created_at")
                    created_at_display = None
                    if created_at_val:
                        if hasattr(
                            created_at_val, "strftime"
                        ): 
                            created_at_display = created_at_val.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        else:
                            created_at_display = str(created_at_val)

                    updated_at_val = deck_data.get("updated_at") # Get updated_at timestamp

                    user_decks_details.append(
                        {
                            "name": deck_name,
                            "deck_id": deck_id_str, 
                            "types": deck_data.get("deck_types", []),
                            "card_count": len(deck_data.get("card_ids", [])),
                            "win_rate": (
                                round(win_rate, 1) if win_rate is not None else None
                            ),
                            "resolved_cover_cards": resolved_cover_cards,
                            "created_at": created_at_display, # For display
                            "firestore_created_at_obj": created_at_val, # Raw created_at for sorting fallback
                            "firestore_updated_at_obj": updated_at_val, # Raw updated_at for primary sorting
                        }
                    )
                else:
                    print(
                        f"Deck doc '{deck_id_str}' (listed for user) not found in 'decks' collection.",
                        flush=True,
                    )
        else:
            print(
                f"User document for ID '{current_user_app_id}' not found. Cannot load collection.",
                flush=True,
            )

        if user_decks_details:
            # Ensure datetime objects for proper comparison, import datetime and timezone if not already
            # from datetime import datetime, timezone # Add to top of file if missing
            default_old_timestamp = datetime.min.replace(
                tzinfo=timezone.utc
            )  # Requires timezone import

            user_decks_details.sort(
                key=lambda deck: (
                    deck.get("firestore_updated_at_obj") or default_old_timestamp,
                    deck.get("firestore_created_at_obj") or default_old_timestamp,
                ),
                reverse=True,  # True for newest (most recent updated_at or created_at) first
            )
            # Clean up temporary sort keys if they were added only for sorting
            for deck_detail in user_decks_details:
                deck_detail.pop("firestore_created_at_obj", None)
                deck_detail.pop("firestore_updated_at_obj", None)

    except Exception as e:
        print(
            f"Error fetching user collection for {current_user_app_id}: {e}", flush=True
        )
        import traceback

        traceback.print_exc()
        session["display_toast_once"] = {
            "message": "Error loading your deck collection.",
            "type": "error",
        }

    return render_template(
        "collection.html",
        decks=user_decks_details,
        email=user_email_for_display,
    )
