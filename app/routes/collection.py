from flask import (
    Blueprint,
    render_template,
    current_app,
    session,
    redirect,
    url_for,
    flash,
    request
)
import os
import json
from .auth import is_logged_in, get_current_user_data

# Assuming you might need datetime for handling timestamps if they are strings
from datetime import datetime

collection_bp = Blueprint("collection_bp", __name__)


@collection_bp.route("/collection")
def view_collection():
    """Displays the logged-in user's saved decks based on their user record."""
    # Check if user is logged in
    if not is_logged_in():
        flash("Please log in to view your collection.", "warning")
        # Preserve the intended destination when redirecting to login
        return redirect(url_for("auth.login_prompt_page", next=request.url))

    # Get current user data using the helper function
    user_data = get_current_user_data()
    if not user_data:
        # If session is valid but user data is missing (e.g., deleted user)
        session.clear()  # Clear the invalid session
        flash("Your session was invalid. Please log in again.", "warning")
        return redirect(url_for("auth.login_prompt_page"))

    username = user_data.get("username")
    user_deck_ids = user_data.get("decks", [])  # Get the list of IDs from users.json

    print(
        f"Loading collection for user '{username}'. Deck IDs: {user_deck_ids}"
    )  # Debug

    user_decks_details = []
    meta_stats = current_app.config.get("meta_stats", {})
    decks_dir = "decks"
    card_collection = current_app.config.get("card_collection")  # Needed for cover card

    # --- Iterate through the USER'S specific deck ID list ---
    for deck_id in user_deck_ids:
        filename = f"{deck_id}.json"  # Construct filename from the ID
        deck_path = os.path.join(decks_dir, filename)

        if os.path.exists(deck_path):
            try:
                with open(deck_path, "r") as f:
                    deck_data = json.load(f)

                # Get win rate (same logic as before)
                win_rate = None
                deck_name = deck_data.get(
                    "name", f"Deck {deck_id[:8]}..."
                )  # Default name
                if deck_name and deck_name in meta_stats.get("decks", {}):
                    stats = meta_stats["decks"][deck_name]
                    if stats.get("total_battles", 0) > 0:
                        win_rate = (stats.get("wins", 0) / stats["total_battles"]) * 100

                resolved_cover_cards = [] # This will be a list of card objects/dicts
                cover_card_ids_from_file = deck_data.get("cover_card_ids", []) # Expect a list

                if card_collection and isinstance(cover_card_ids_from_file, list):
                    for c_id in cover_card_ids_from_file: # Iterate up to 3 IDs
                        if c_id:  # Ensure ID is not None or empty
                            try:
                                # ++ ATTEMPT TO CONVERT c_id TO INTEGER FOR LOOKUP ++
                                card_id_for_lookup = int(c_id)
                                cover_card_obj = card_collection.get_card_by_id(
                                    card_id_for_lookup
                                )
                            except ValueError:
                                # Handle cases where c_id might not be a valid integer string
                                print(
                                    f"  Warning: Cover card ID '{c_id}' is not a valid integer. Skipping."
                                )
                                cover_card_obj = None

                            if cover_card_obj:
                                card_name_debug = getattr(
                                    cover_card_obj, "name", "NAME_MISSING"
                                )
                                display_path_debug = getattr(
                                    cover_card_obj,
                                    "display_image_path",
                                    "PATH_MISSING_OR_NONE",
                                )
                                print(
                                    f"  Cover ID '{c_id}' (lookup as {card_id_for_lookup}): Name='{card_name_debug}', Display Path='{display_path_debug}'"
                                )
                                resolved_cover_cards.append(
                                    {
                                        "name": card_name_debug,
                                        "display_image_path": (
                                            display_path_debug
                                            if display_path_debug
                                            not in ["PATH_MISSING_OR_NONE", None]
                                            else None
                                        ),
                                    }
                                )
                            else:
                                # This will print if int(c_id) was valid but no card found for that int ID
                                print(
                                    f"  Cover card ID '{c_id}' (lookup as {card_id_for_lookup}) NOT FOUND in card_collection."
                                )
                                # The 'somethings wrong' print can be removed if this is more descriptive
                user_decks_details.append(
                    {
                        "name": deck_name,
                        "filename": filename,  # Pass filename for edit/delete links
                        "deck_id": deck_id,  # Pass base ID
                        "types": deck_data.get("deck_types", []),
                        "card_count": len(deck_data.get("cards", [])),
                        "win_rate": (
                            round(win_rate, 1) if win_rate is not None else None
                        ),
                        "resolved_cover_cards": resolved_cover_cards,
                        "created_at": deck_data.get("created_at"),  # Keep for sorting
                    }
                )
            except Exception as e:
                print(
                    f"Error loading deck file {filename} (listed for user '{username}'): {e}"
                )
                # Optionally add a placeholder for decks that failed to load
        else:
            print(
                f"Deck file {filename} listed for user '{username}' not found on disk."
            )
            # NOTE: Consider adding logic here to automatically clean up this
            # invalid deck_id from the user's list in users.json if desired.
            # This would require calling save_users().

    # --- Sorting Logic (applied to the correctly filtered list) ---
    if user_decks_details:
        try:
            # Sort by 'created_at' string (YYYY-MM-DD HH:MM:SS) or timestamp
            user_decks_details.sort(
                key=lambda deck: deck.get("created_at", "0"), reverse=True
            )
        except TypeError as e:
            print(f"Error sorting decks by created_at: {e}.")

    # Render the collection template, passing only the user's decks
    return render_template(
        "collection.html",
        decks=user_decks_details,  # Pass the correctly loaded & sorted list
        username=username,
        # user_logged_in=True # Not strictly needed if login is required by the route
    )


# Make sure this blueprint is registered in your main app.py or wherever you configure your Flask app
