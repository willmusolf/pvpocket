from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, session
import os
from Deck import Deck
import random
import time
from .auth import is_logged_in, get_current_user_data, profanity_check
import uuid

from flask import Blueprint, jsonify, current_app, request, session  # Existing imports
from flask_login import (
    current_user as flask_login_current_user,
    login_required,
    )

from firebase_admin import firestore  # For ArrayUnion and SERVER_TIMESTAMP
from typing import Optional  # For type hinting in helper function
import json
import datetime

decks_bp = Blueprint('decks', __name__)

MAX_DECKS_PER_USER = 200


def get_db() -> firestore.client:
    """Helper to get Firestore DB client from app config."""
    db = current_app.config.get("FIRESTORE_DB")
    if not db:
        current_app.logger.critical(
            "Firestore client (FIRESTORE_DB) not available in app config."
        )
        raise Exception("Firestore client not available. Check app initialization.")
    return db


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
def get_all_cards():
    """API endpoint to get all cards from the pre-loaded CardCollection with optional filtering."""
    card_collection = current_app.config.get("card_collection")

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
        name_filter = request.args.get("name")

        # Apply filters to the in-memory list of Card objects
        filtered_card_objects = all_cards_from_collection

        if set_code_filter:
            filtered_card_objects = [
                card
                for card in filtered_card_objects
                if card.set_code == set_code_filter
            ]

        if energy_type_filter:
            filtered_card_objects = [
                card
                for card in filtered_card_objects
                if card.energy_type == energy_type_filter
            ]

        if card_type_filter:
            # Assuming card.card_type is a string like "Pokémon - Basic"
            filtered_card_objects = [
                card
                for card in filtered_card_objects
                if card.card_type and card_type_filter in card.card_type
            ]

        if name_filter:
            filtered_card_objects = [
                card
                for card in filtered_card_objects
                if card.name and name_filter.lower() in card.name.lower()
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
            # Ensure display_image_path is included. If Card.to_dict() doesn't include properties, add it:
            if "display_image_path" not in card_dict:  # Check if it's already there
                card_dict["display_image_path"] = card_obj.display_image_path
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


@decks_bp.route("/api/decks/<string:deck_id>", methods=["GET"])
@login_required
def get_deck(deck_id: str):  # Changed 'filename' to 'deck_id'
    """API endpoint to get a specific deck by its Firestore ID."""
    db = get_db()  # Use your helper to get the Firestore client
    card_collection = current_app.config.get("card_collection")

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

        card_collection = current_app.config.get("card_collection")
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

        card_collection = current_app.config.get("card_collection")
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

    card_collection = current_app.config.get("card_collection")
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
    card_collection = current_app.config.get("card_collection")
    
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
    card_collection = current_app.config.get("card_collection")
    
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
