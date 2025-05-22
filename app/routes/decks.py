from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, session
import os
import json
from Deck import Deck
import random
import time
from .auth import is_logged_in, get_current_user_data
import uuid

decks_bp = Blueprint('decks', __name__)

@decks_bp.route('/decks')
def list_decks():
    """List all saved decks and provide deck building interface."""
    # Get meta stats from app config
    meta_stats = current_app.config.get('meta_stats', {})

    # Get card collection for search functionality
    card_collection = current_app.config.get('card_collection')

    # Load user and public decks
    decks = []
    if os.path.exists('decks'):
        for filename in os.listdir('decks'):
            if filename.endswith('.json'):
                try:
                    with open(f'decks/{filename}', 'r') as f:
                        deck_data = json.load(f)

                        # Get win rate from meta stats if available
                        win_rate = None
                        deck_name = deck_data.get('name')
                        if meta_stats and deck_name in meta_stats.get("decks", {}):
                            stats = meta_stats["decks"][deck_name]
                            if stats["total_battles"] > 0:
                                win_rate = (stats["wins"] / stats["total_battles"]) * 100

                        decks.append({
                            'name': deck_name,
                            'filename': filename,
                            'types': deck_data.get('deck_types', []),
                            'card_count': len(deck_data.get('cards', [])),
                            'win_rate': round(win_rate, 1) if win_rate is not None else None,
                            'owner': deck_data.get('owner', 'Unknown')
                        })
                except Exception as e:
                    print(f"Error loading deck {filename}: {e}")

    # Filter decks based on ownership if user is logged in
    current_user = get_current_user_data()
    if current_user:
        user_decks = [deck for deck in decks if deck['owner'] == current_user['username']]
        public_decks = [deck for deck in decks if deck['owner'] != current_user['username']]
    else:
        user_decks = []
        public_decks = decks

    return render_template(
        'decks.html', 
        user_decks=user_decks,
        public_decks=public_decks,
        user_logged_in=is_logged_in(),
        username=session.get('username')
    )

# API Routes for Deck Building

@decks_bp.route('/api/cards', methods=['GET'])
def get_all_cards():
    """API endpoint to get all cards with optional filtering."""
    # Get card collection from app config
    card_collection = current_app.config['card_collection']

    try:
        # Get filter parameters from query string
        set_code = request.args.get('set_code')
        energy_type = request.args.get('energy_type')
        card_type = request.args.get('card_type')
        name = request.args.get('name')

        # Apply filters
        filtered_cards = card_collection.cards

        if set_code:
            filtered_cards = [card for card in filtered_cards if card.set_code == set_code]

        if energy_type:
            filtered_cards = [card for card in filtered_cards if card.energy_type == energy_type]

        if card_type:
            filtered_cards = [card for card in filtered_cards if card_type in card.card_type]

        if name:
            filtered_cards = [card for card in filtered_cards if name.lower() in card.name.lower()]

        # Convert to dictionaries for JSON response and add display_image_path
        card_dicts = []
        for card in filtered_cards:
            card_dict = card.to_dict()
            # Add display_image_path to the card dictionary
            card_dict['display_image_path'] = card.display_image_path
            card_dicts.append(card_dict)

        return jsonify({"cards": card_dicts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# In decks.py
@decks_bp.route("/api/decks/<filename>", methods=["GET"])
def get_deck(filename):
    """API endpoint to get a specific deck."""
    try:
        card_collection = current_app.config["card_collection"]
        # Load the deck object - this sets deck.cover_card
        deck = Deck.load_from_json(f"decks/{filename}", card_collection)

        # Convert card objects to dictionaries
        card_dicts = []
        for card in deck.cards:
            card_dict = card.to_dict()
            card_dict["display_image_path"] = card.display_image_path
            card_dicts.append(card_dict)

        # Build the response dictionary
        deck_dict = {
            "id": filename,
            "name": deck.name,
            "deck_types": deck.deck_types,
            "cards": card_dicts,
            "cover_card_ids": deck.get_cover_card_ids(),  # ++ NEW MULTIPLE ++
        }

        return jsonify(deck_dict)
    except FileNotFoundError:
        return jsonify({"error": "Deck not found"}), 404
    except Exception as e:
        print(f"Error in get_deck for {filename}: {e}")  # Add logging
        return jsonify({"error": str(e)}), 500


@decks_bp.route("/api/decks", methods=["POST"])
def create_deck():
    if not is_logged_in():
        return jsonify({"success": False, "error": "Authentication required"}), 401

    user_id = session.get("user_id")
    current_user_data = get_current_user_data()

    if not user_id or not current_user_data:
        session.clear()
        return jsonify({"success": False, "error": "Invalid session or user data"}), 401

    user_decks_list = current_user_data.get("decks", [])
    MAX_DECKS_PER_USER = 50

    if len(user_decks_list) >= MAX_DECKS_PER_USER:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"You have reached the maximum limit of {MAX_DECKS_PER_USER} decks. Please delete an existing deck to create a new one.",
                }
            ),
            403,
        )

    try:
        deck_data_from_request = request.json  # Renamed for clarity
        if not deck_data_from_request:
            return jsonify({"success": False, "error": "No data received"}), 400

        card_collection = current_app.config.get("card_collection")
        if not card_collection:
            print(
                "CRITICAL: Card Collection not loaded in app config during create_deck"
            )
            raise Exception("Card Collection not loaded in app config")

        deck_name = deck_data_from_request.get("name")
        card_ids_payload = deck_data_from_request.get("cards")  # List of {"id": "..."}
        deck_types_payload = deck_data_from_request.get("deck_types")
        # ++ GET USER'S CHOSEN COVER CARD IDs FROM REQUEST ++
        user_chosen_cover_card_ids = deck_data_from_request.get("cover_card_ids", [])

        if not deck_name or not deck_name.strip():  # Added strip()
            return jsonify({"success": False, "error": "Deck name is required"}), 400

        users = current_app.config["users"]
        decks_dir = "decks"
        if _does_deck_name_exist_for_user(
            current_user_data.get("username"), deck_name.strip(), users, decks_dir
        ):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"A deck named '{deck_name.strip()}' already exists. Please choose a different name.",
                    }
                ),
                400,
            )

        if (
            not card_ids_payload
            or not isinstance(card_ids_payload, list)
            or len(card_ids_payload) == 0
        ):
            return jsonify({"success": False, "error": "Deck must contain cards"}), 400
        if (
            not deck_types_payload
            or not isinstance(deck_types_payload, list)
            or len(deck_types_payload) == 0
        ):
            return (
                jsonify({"success": False, "error": "Deck energy types are required"}),
                400,
            )

        new_deck = Deck(deck_name.strip())  # Create with name
        new_deck.set_deck_types(deck_types_payload)  # Set types

        # Populate cards AFTER deck object is created
        valid_cards_added = []
        for card_data_item in card_ids_payload:
            card_id_str = card_data_item.get("id")
            if card_id_str is not None:  # Check for None
                try:
                    card_object = card_collection.get_card_by_id(
                        int(card_id_str)
                    )  # Assuming IDs are integers
                    if card_object:
                        new_deck.add_card(card_object)
                        valid_cards_added.append(card_object)
                    else:
                        print(
                            f"Warning: Card ID {card_id_str} not found in collection."
                        )
                except ValueError:
                    print(f"Warning: Card ID {card_id_str} is not a valid integer.")
        if not valid_cards_added:
            return (
                jsonify(
                    {"success": False, "error": "No valid cards found for provided IDs"}
                ),
                400,
            )

        # ++ SET USER'S CHOSEN COVER CARDS (NOW THAT new_deck.cards IS POPULATED) ++
        if isinstance(user_chosen_cover_card_ids, list):
            # Ensure IDs are strings for set_cover_card_ids if it expects strings
            cleaned_user_ids = [
                str(cid) for cid in user_chosen_cover_card_ids if cid is not None
            ]
            new_deck.set_cover_card_ids(cleaned_user_ids)
        else:
            new_deck.set_cover_card_ids([])  # Default to empty if bad data

        new_deck.owner = current_user_data.get("username", "Unknown")

        # Generate filename and save deck file (save_to_json will call auto-select if needed)
        deck_id_str = f"deck_{uuid.uuid4()}"
        filename = f"{deck_id_str}.json"
        deck_filepath = os.path.join(decks_dir, filename)
        os.makedirs(decks_dir, exist_ok=True)
        new_deck.save_to_json(
            deck_filepath
        )  # This calls select_cover_card_automatically if len < 3
        print(
            f"Saved new deck file: {deck_filepath} with cover IDs: {new_deck.cover_card_ids}"
        )

        # --- !! UPDATE users.json !! ---
        users = current_app.config["users"] # This is the in-memory dictionary
        save_users = current_app.config["save_users"] # This is the lambda to save it
        user_record_to_update = users.get(user_id)

        if user_record_to_update:
            # Ensure 'decks' key exists and is a list
            if not isinstance(user_record_to_update.get("decks"), list):
                user_record_to_update["decks"] = []
            
            needs_user_save = False # Flag to ensure we only save if a change was made
            if deck_id_str not in user_record_to_update["decks"]:
                user_record_to_update["decks"].append(deck_id_str)
                print(f"Deck ID '{deck_id_str}' appended to user '{user_id}'s deck list (in memory).")
                needs_user_save = True
            else:
                # This indicates a potential issue with UUID generation or state management if a new UUID is already present.
                # However, the deck file itself was created. We should not delete it here.
                # The user record just doesn't need this specific ID re-appended.
                print(f"CRITICAL WARNING: Newly generated Deck ID '{deck_id_str}' was ALREADY in user's deck list for user '{user_id}'. User record not modified by this append. Deck file was saved.")
                # needs_user_save remains False if this was the only potential change.

            if needs_user_save: # Only save if we actually appended a new deck ID
                try:
                    save_users() # This writes the in-memory 'users' dict to users.json
                    print(f"users.json saved. User '{user_record_to_update.get('username')}' now associated with deck '{deck_id_str}'.")
                except Exception as e_save:
                    print(f"ERROR saving users.json after adding deck {deck_id_str}: {e_save}")
                    # If saving users.json fails, the deck file is orphaned regarding this user record.
                    # Attempt to clean up the deck file that was just created.
                    try:
                        os.remove(deck_filepath) 
                        print(f"Cleaned up orphaned deck file: {deck_filepath} due to users.json save error.")
                    except OSError as e_os:
                        print(f"ERROR cleaning up orphaned deck file {deck_filepath}: {e_os}")
                    return jsonify({"success": False, "error": "Failed to update user record after saving deck. Deck file removed."}), 500
            
            # Flash message for deck limit (check after potential append)
            if len(user_record_to_update.get("decks", [])) == MAX_DECKS_PER_USER:
                flash(f"You have now reached the maximum of {MAX_DECKS_PER_USER} decks. You won't be able to create more until you delete some.", "warning")

        else: # user_record_to_update is None (user_id from session not found in users_dict)
            print(f"CRITICAL ERROR: User ID '{user_id}' from session not found in users dictionary during create_deck!")
            try:
                os.remove(deck_filepath) 
                print(f"Cleaned up orphaned deck file: {deck_filepath} due to user lookup failure.")
            except OSError as e_os:
                print(f"ERROR cleaning up deck file {deck_filepath} after user lookup failed: {e_os}")
            return jsonify({"success": False, "error": "User session data mismatch, could not save deck association."}), 500
            
        return jsonify({
            "success": True, 
            "message": "Deck created successfully!", 
            "filename": filename, 
            "deck_id": deck_id_str,
            "cover_card_ids": new_deck.get_cover_card_ids() 
        }), 201

    except Exception as e:
        print(f"Error in create_deck endpoint: {e}")
        import traceback

        traceback.print_exc()
        return (
            jsonify({"success": False, "error": "An internal server error occurred"}),
            500,
        )


@decks_bp.route("/api/decks/<filename>", methods=["PUT"])
def update_deck(filename):
    """API endpoint to update an existing deck."""
    if not is_logged_in():
        return jsonify({"success": False, "error": "Authentication required"}), 401

    user_id = session.get("user_id")
    current_user_data = get_current_user_data()
    if not user_id or not current_user_data:
        session.clear()
        return jsonify({"success": False, "error": "Invalid session or user data"}), 401

    try:
        # Basic filename validation
        if not filename.endswith(".json") or ".." in filename or "/" in filename:
            return jsonify({"success": False, "error": "Invalid filename"}), 400

        deck_id_being_edited = filename.replace(".json", "")

        # --- Ownership Check using users.json ---
        users = current_app.config["users"]
        user_record = users.get(user_id)

        if not user_record or deck_id_being_edited not in user_record.get("decks", []):
            print(
                f"Permission denied: User '{current_user_data.get('username', user_id)}' (ID: {user_id}) attempting to update deck '{deck_id_being_edited}' which they do not own or does not exist in their list."
            )
            deck_filepath_check = os.path.join("decks", filename)
            if not os.path.exists(deck_filepath_check):
                return jsonify({"success": False, "error": "Deck not found"}), 404
            else:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Permission denied to update this deck",
                        }
                    ),
                    403,
                )
        # --- End Ownership Check ---

        deck_data_from_request = request.json
        if not deck_data_from_request:
            return jsonify({"success": False, "error": "No data received"}), 400

        card_collection = current_app.config.get("card_collection")
        if not card_collection:
            print(
                "CRITICAL SERVER ERROR: Card Collection not loaded in app config during update_deck"
            )
            raise Exception("Card Collection not loaded")

        new_deck_name = deck_data_from_request.get("name")
        card_ids_payload = deck_data_from_request.get("cards")
        deck_types_payload = deck_data_from_request.get("deck_types")
        user_chosen_cover_card_ids = deck_data_from_request.get("cover_card_ids", [])

        # Validation of received data
        if not new_deck_name or not new_deck_name.strip():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Deck name is required and cannot be empty",
                    }
                ),
                400,
            )
        if (
            not card_ids_payload
            or not isinstance(card_ids_payload, list)
            or len(card_ids_payload) == 0
        ):
            return jsonify({"success": False, "error": "Deck must contain cards"}), 400
        if (
            not deck_types_payload
            or not isinstance(deck_types_payload, list)
            or len(deck_types_payload) == 0
        ):
            return (
                jsonify({"success": False, "error": "Deck energy types are required"}),
                400,
            )
        if not isinstance(user_chosen_cover_card_ids, list):
            return (
                jsonify({"success": False, "error": "Invalid cover card IDs format"}),
                400,
            )

        # Deck Name Uniqueness Check (excluding the current deck itself)
        decks_dir = "decks"
        if _does_deck_name_exist_for_user(
            current_user_data.get("username"),
            new_deck_name.strip(),
            users,
            decks_dir,
            exclude_deck_id=deck_id_being_edited,
        ):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Another deck named '{new_deck_name.strip()}' already exists. Please choose a different name.",
                    }
                ),
                400,
            )

        # Load the existing deck object to update it
        deck_filepath_to_load_and_save = os.path.join(decks_dir, filename)
        deck_to_update = Deck.load_from_json(
            deck_filepath_to_load_and_save, card_collection
        )

        # Update basic attributes
        deck_to_update.name = new_deck_name.strip()
        deck_to_update.set_deck_types(
            deck_types_payload
        )  # Assumes Deck class handles this

        # Re-populate cards: Clear existing and add new ones
        deck_to_update.cards = []  # Clear existing cards list on the object
        deck_to_update.card_counts = {}  # Reset card counts

        valid_cards_added_to_obj = []
        for card_data_item in card_ids_payload:
            card_id_str = card_data_item.get("id")
            if card_id_str is not None:
                try:
                    card_object = card_collection.get_card_by_id(
                        int(card_id_str)
                    )  # Assuming IDs are integers for lookup
                    if card_object:
                        deck_to_update.add_card(
                            card_object
                        )  # add_card handles MAX_COPIES
                        valid_cards_added_to_obj.append(card_object)
                    else:
                        print(
                            f"Warning: Card ID '{card_id_str}' provided for update not found in master card collection."
                        )
                except ValueError:
                    print(
                        f"Warning: Card ID '{card_id_str}' is not a valid integer during update."
                    )

        if not deck_to_update.cards:  # If deck ended up empty and that's not allowed
            return (
                jsonify(
                    {"success": False, "error": "Deck cannot be empty after update"}
                ),
                400,
            )

        # Set the NEW user-selected cover cards from the request payload
        # This will overwrite what was loaded from the file if the user changed them.
        # Ensure IDs are strings for set_cover_card_ids if it expects strings
        cleaned_user_ids = [
            str(cid) for cid in user_chosen_cover_card_ids if cid is not None
        ]
        deck_to_update.set_cover_card_ids(
            cleaned_user_ids
        )  # This validates against the now-updated deck_to_update.cards

        deck_to_update.owner = current_user_data.get("username")  # Re-affirm owner

        # Save the updated deck object (save_to_json will call select_cover_card_automatically if needed)
        deck_to_update.save_to_json(
            deck_filepath_to_load_and_save
        )  # Overwrite existing file
        print(
            f"Updated deck file: {deck_filepath_to_load_and_save} with final cover IDs: {deck_to_update.get_cover_card_ids()}"
        )

        return jsonify(
            {
                "success": True,
                "message": "Deck updated successfully!",
                "filename": filename,
                "deck_id": deck_id_being_edited,
                "cover_card_ids": deck_to_update.get_cover_card_ids(),  # Return final list
            }
        )

    except (
        FileNotFoundError
    ):  # Should be caught by ownership check if file doesn't exist
        return jsonify({"success": False, "error": "Deck not found to update."}), 404
    except Exception as e:
        print(f"CRITICAL ERROR in update_deck for {filename}: {e}")
        import traceback

        traceback.print_exc()
        return (
            jsonify(
                {
                    "success": False,
                    "error": "An internal server error occurred while updating the deck.",
                }
            ),
            500,
        )


# --- CORRECTED: delete_deck route ---
@decks_bp.route(
    "/delete_deck"
)  # This seems like it should be a DELETE method on /api/decks/<filename>
def delete_deck():  # Renaming suggestion: delete_deck_view or handle_deck_delete
    """Delete a deck file and remove reference from user's list."""
    if not is_logged_in():
        return redirect(
            url_for("auth.login", next=request.url)
        )  # Redirect back to where delete was attempted

    user_id = session.get("user_id")
    current_user_data = get_current_user_data()
    if not user_id or not current_user_data:
        session.clear()
        flash("Session invalid. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    filename = request.args.get("filename")
    if not filename or not filename.endswith(".json") or ".." in filename:
        flash("Invalid or missing deck filename.", "danger")
        # Redirect back to collection or profile, wherever delete is initiated
        return redirect(
            request.referrer or url_for("auth.user_profile")
        )  # Or collection_bp.view_collection

    deck_id = filename.replace(".json", "")  # Extract base ID
    decks_dir = "decks"
    deck_path = os.path.join(decks_dir, filename)

    # --- !! OWNERSHIP CHECK using users.json !! ---
    users = current_app.config["users"]
    save_users = current_app.config["save_users"]
    user_record = users.get(user_id)

    if not user_record or deck_id not in user_record.get("decks", []):
        flash("Deck not found in your collection or permission denied.", "danger")
        return redirect(request.referrer or url_for("auth.user_profile"))
    # --- END OWNERSHIP CHECK ---

    # Proceed with deletion
    # 1. Remove from user's list in users.json
    try:
        user_record["decks"].remove(deck_id)
        save_users()
        print(f"Removed deck ID '{deck_id}' from user '{user_id}' list.")
    except Exception as e_save:
        print(
            f"ERROR saving users.json after removing deck ref for user {user_id}: {e_save}"
        )
        flash("Failed to update user record. Deck file not deleted.", "danger")
        return redirect(request.referrer or url_for("auth.user_profile"))

    # 2. Delete the actual deck file
    if os.path.exists(deck_path):
        try:
            os.remove(deck_path)
            print(f"Deleted deck file: {deck_path}")
        except Exception as e_delete:
            print(
                f"ERROR deleting deck file {deck_path} after removing user ref: {e_delete}"
            )
            # User record was updated, but file deletion failed. What to do?
            # Maybe try adding the deck_id back to the user list? Or just report error.
            flash(
                f"Deck reference removed, but failed to delete file: {e_delete}",
                "warning",
            )
    else:
        # Deck ID was in user list, but file didn't exist. Cleaned up user list anyway.
        flash("Deck file was already missing, removed reference.", "info")

    # Redirect back to the page the user came from (likely profile or collection)
    return redirect(request.referrer or url_for("auth.user_profile"))


# ++ ADD THIS NEW ROUTE AND FUNCTION ++
@decks_bp.route(
    "/decks/copy/<string:original_filename>", methods=["GET"]
)  # Or POST, GET is simpler for a link click
def copy_deck(original_filename):
    if not is_logged_in():
        # Try to redirect back to collection, or login if no referrer
        return redirect(
            request.referrer or url_for("auth.login_prompt_page", next=request.url)
        )

    user_id = session.get("user_id")
    current_user_data = get_current_user_data()
    if not current_user_data:  # Ensure user data is loaded
        return redirect(url_for("auth.login_prompt_page"))

    decks_dir = "decks"
    original_deck_path = os.path.join(decks_dir, original_filename)

    if not os.path.exists(original_deck_path):
        return redirect(
            url_for("collection_bp.view_collection")
        )  # Or wherever your collections page is

    # Ownership Check (important for copying)
    # Assuming original_filename includes '.json', extract ID part
    original_deck_id_part = original_filename.replace(".json", "")
    user_owns_original = original_deck_id_part in current_user_data.get("decks", [])

    # Allow copying of public decks too, or only owned decks?
    # For now, let's assume user must own the deck to copy it directly via this UI,
    # OR if we want to allow copying public decks, this check needs adjustment.
    # For simplicity with current structure, let's assume they are copying THEIR OWN deck from "My Collection"
    if not user_owns_original:
        # Load the original deck to check its owner field if we want to allow copying public decks
        try:
            with open(original_deck_path, "r") as f_orig:
                original_deck_data_for_owner_check = json.load(f_orig)
            if original_deck_data_for_owner_check.get("owner") != current_user_data.get(
                "username"
            ):
                # This logic might need refinement based on public/private deck rules.
                # If only copying from "My Decks", this outer `if not user_owns_original:` should be sufficient.
                return redirect(url_for("collection_bp.view_collection"))
        except Exception:
            return redirect(url_for("collection_bp.view_collection"))

    try:
        with open(original_deck_path, "r") as f_orig:
            original_deck_data = json.load(f_orig)

        # Create data for the new (copied) deck
        new_deck_id_str = f"deck_{uuid.uuid4()}"
        new_filename = f"{new_deck_id_str}.json"

        copied_deck_data = (
            original_deck_data.copy()
        )  # Shallow copy is usually fine for this structure
        copied_deck_data["name"] = (
            f"Copy of {original_deck_data.get('name', 'Unnamed Deck')}"
        )
        copied_deck_data["owner"] = current_user_data.get(
            "username"
        )  # New owner is the current user
        # Ensure 'id' or 'filename' field within the JSON (if any) is updated if your Deck class uses it internally
        # For now, assuming the filename itself is the main ID externally.

        # Save the new deck file
        new_deck_path = os.path.join(decks_dir, new_filename)
        with open(new_deck_path, "w") as f_new:
            json.dump(copied_deck_data, f_new, indent=4)
        print(f"Created copy: {new_filename} from {original_filename}")

        # Add the new deck to the current user's list of decks in users.json
        users = current_app.config["users"]
        save_users = current_app.config["save_users"]
        user_record_to_update = users.get(user_id)

        if user_record_to_update:
            if "decks" not in user_record_to_update or not isinstance(
                user_record_to_update["decks"], list
            ):
                user_record_to_update["decks"] = []
            user_record_to_update["decks"].append(new_deck_id_str)  # Add the ID part
            save_users()
            print(f"Added copied deck '{new_deck_id_str}' to user '{user_id}'")
        else:
            # Should not happen if user is logged in and data is consistent
            os.remove(new_deck_path)  # Clean up copied file if user update fails
            return redirect(url_for("collection_bp.view_collection"))
        # Redirect to the deck builder to edit the new copy
        return redirect(url_for("decks.list_decks", edit=new_filename))

    except FileNotFoundError:  # Should be caught by os.path.exists earlier
        flash("Original deck not found.", "danger")
        return redirect(url_for("collection_bp.view_collection"))
    except Exception as e:
        print(f"Error copying deck {original_filename}: {e}")
        import traceback

        traceback.print_exc()
        flash(f"An error occurred while copying the deck: {e}", "danger")
        return redirect(url_for("collection_bp.view_collection"))


def _does_deck_name_exist_for_user(
    username, deck_name_to_check, users_data, decks_dir, exclude_deck_id=None
):
    """
    Checks if a deck name already exists for a given user.
    - username: The username of the deck owner to check against.
    - deck_name_to_check: The deck name to look for (case-insensitive).
    - users_data: The main dictionary of all users (from app.config['users']).
    - decks_dir: The directory where deck JSON files are stored.
    - exclude_deck_id: A deck ID (e.g., "deck_uuid_string") to exclude from the check (used when updating a deck).
    """
    user_record = None
    for u_id, u_data in users_data.items():
        if u_data.get("username") == username:
            user_record = u_data
            break

    if not user_record:
        return False  # User not found, so name can't exist for them

    user_deck_ids = user_record.get("decks", [])

    for deck_id_in_list in user_deck_ids:
        if exclude_deck_id and deck_id_in_list == exclude_deck_id:
            continue  # Skip the deck currently being edited/renamed

        deck_filename = f"{deck_id_in_list}.json"
        deck_path = os.path.join(decks_dir, deck_filename)
        if os.path.exists(deck_path):
            try:
                with open(deck_path, "r") as f:
                    existing_deck_data = json.load(f)
                if (
                    existing_deck_data.get("name", "").lower()
                    == deck_name_to_check.lower()
                ):
                    return True  # Name exists (case-insensitive)
            except Exception as e:
                print(
                    f"Warning: Could not read deck file {deck_path} during name check: {e}"
                )
                # Decide how to handle: treat as non-existent or raise/log more seriously
    return False
