import re
import requests
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import secretmanager

from dotenv import load_dotenv


# --- Firebase Initialization ---
if not firebase_admin._apps:
    try:
        project_id = os.environ.get("GCP_PROJECT_ID")
        secret_name = os.environ.get("FIREBASE_SECRET_NAME")

        if project_id and secret_name:
            print("Post-processor: Initializing Firebase from Google Secret Manager...")
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})

            secret_payload = response.payload.data.decode("UTF-8")
            cred_dict = json.loads(secret_payload)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print(
                "Post-processor: Firebase initialized successfully from Secret Manager."
            )
        else:
            print(
                "Post-processor: Secret Manager config not found, attempting default credentials."
            )
            firebase_admin.initialize_app()
            print(
                "Post-processor: Firebase initialized with Application Default Credentials."
            )

        db_firestore = firestore.client()

    except Exception as e:
        print(
            f"CRITICAL ERROR: Failed to initialize Firebase Admin SDK for post-processor: {e}"
        )
        db_firestore = None


# --- Card Data Processing Rules & Helper Functions ---

CUSTOM_RARITY_OVERRIDES = {
    "A2b": ("97", "110"),
    "A3": ("210", "237"),
    "A3a": ("89", "102"),
    "A3b": ("93", "106"),
}

ULTRA_BEAST_DEFINITIONS = {
    "A3a": [
        "6",
        "7",
        "8",
        "9",
        "20",
        "42",
        "43",
        "44",
        "45",
        "53",
        "62",
        "71",
        "72",
        "75",
        "76",
        "79",
        "86",
        "88",
        "103",
    ],
    "P-A": ("75", "82"),
}

SHINY_CARD_TYPE_DEFINITIONS = {
    "P-A": ("83", "92"),
}


def determine_final_rarity(set_code, card_number_str, initial_rarity_str):
    """Converts standard star rarity to shiny star rarity based on defined ranges."""
    final_rarity = initial_rarity_str
    if set_code in CUSTOM_RARITY_OVERRIDES:
        override_rule = CUSTOM_RARITY_OVERRIDES[set_code]
        if isinstance(override_rule, tuple) and len(override_rule) == 2:
            start_num_str, end_num_str = override_rule
            try:
                current_card_num_int = int(re.sub(r"\D", "", str(card_number_str)))
                if int(start_num_str) <= current_card_num_int <= int(end_num_str):
                    num_stars = str(initial_rarity_str or "").count("☆")
                    if num_stars > 0:
                        final_rarity = "✵" * num_stars
            except ValueError:
                print(
                    f"Warning: Could not parse card numbers for shiny range check: Set {set_code}, Card {card_number_str}, Range {override_rule}"
                )
    return final_rarity


def modify_card_type_for_ultra_beast(set_code, card_number_str, current_card_type):
    """Appends ' (Ultra Beast)' to the card_type for specific cards."""
    new_card_type = current_card_type
    if current_card_type is None:
        return current_card_type
    if set_code in ULTRA_BEAST_DEFINITIONS:
        override_rule = ULTRA_BEAST_DEFINITIONS[set_code]
        if isinstance(override_rule, tuple) and len(override_rule) == 2:
            start_num_str, end_num_str = override_rule
            try:
                current_card_num_int = int(re.sub(r"\D", "", str(card_number_str)))
                if int(start_num_str) <= current_card_num_int <= int(end_num_str):
                    if " (Ultra Beast)" not in new_card_type:
                        new_card_type += " (Ultra Beast)"
            except ValueError:
                print(
                    f"Warning: Could not parse card numbers for Ultra Beast card_type check: Set {set_code}, Card {card_number_str}, Range {override_rule}"
                )
        elif isinstance(override_rule, list):
            if card_number_str in override_rule:
                if " (Ultra Beast)" not in new_card_type:
                    new_card_type += " (Ultra Beast)"
    return new_card_type


def modify_card_type_for_shiny(set_code, card_number_str, current_card_type):
    """Appends ' (Shiny)' to the card_type for specific card ranges."""
    new_card_type = current_card_type
    if current_card_type is None:
        return current_card_type

    if set_code in SHINY_CARD_TYPE_DEFINITIONS:
        override_rule = SHINY_CARD_TYPE_DEFINITIONS[set_code]
        if isinstance(override_rule, tuple) and len(override_rule) == 2:
            start_num_str, end_num_str = override_rule
            try:
                current_card_num_int = int(re.sub(r"\D", "", str(card_number_str)))
                if int(start_num_str) <= current_card_num_int <= int(end_num_str):
                    if " (Shiny)" not in new_card_type:
                        new_card_type += " (Shiny)"
            except ValueError:
                print(
                    f"Warning: Could not parse card numbers for Shiny card_type check: Set {set_code}, Card {card_number_str}, Range {override_rule}"
                )
    return new_card_type


def get_cards_from_firestore():
    if not db_firestore:
        print("Firestore client not initialized. Cannot fetch cards.")
        return []
    print("Fetching all cards from Firestore for processing...")
    cards_to_process = []
    try:
        sets_collection_ref = db_firestore.collection("cards")
        for set_doc in sets_collection_ref.stream():
            cards_subcollection_ref = set_doc.reference.collection("set_cards")
            for card_doc in cards_subcollection_ref.stream():
                card_data = card_doc.to_dict()
                if card_data and all(
                    k in card_data for k in ["set_code", "card_number_str", "card_type"]
                ):
                    cards_to_process.append(
                        {
                            "set_doc_id": set_doc.id,
                            "card_doc_id": card_doc.id,
                            **card_data,
                        }
                    )
    except Exception as e:
        print(f"Error fetching cards from Firestore: {e}", exc_info=True)
    return cards_to_process


def update_card_in_firestore(set_doc_id, card_doc_id, updates):
    if not db_firestore:
        return False
    try:
        card_ref = (
            db_firestore.collection("cards")
            .document(set_doc_id)
            .collection("set_cards")
            .document(card_doc_id)
        )
        card_ref.update(updates)
        return True
    except Exception as e:
        print(f"Firestore error updating card {set_doc_id}/{card_doc_id}: {e}")
        return False


def trigger_cache_refresh():
    load_dotenv()
    base_url = os.getenv("WEBSITE_URL", "http://127.0.0.1:5001")
    refresh_key = os.getenv("REFRESH_SECRET_KEY")

    if not refresh_key:
        print(
            "ERROR: REFRESH_SECRET_KEY not found in environment. Cannot trigger refresh."
        )
        return

    refresh_url = f"{base_url}/api/refresh-cards"
    headers = {"X-Refresh-Key": refresh_key}

    print(f"Scraping complete. Triggering cache refresh at {refresh_url}...")
    try:
        response = requests.post(refresh_url, headers=headers, timeout=60)
        if response.status_code == 200:
            print("SUCCESS: Cache refresh triggered successfully.")
            print(response.json())
        else:
            print(
                f"ERROR: Failed to trigger cache refresh. Status Code: {response.status_code}"
            )
            print(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(
            f"CRITICAL ERROR: Could not connect to the application to refresh cache: {e}"
        )
        print("The website will show old data until it is restarted manually.")


def main_post_process():
    if not db_firestore:
        print("Exiting: Firestore client failed to initialize.")
        return

    # Part 1: Update Firestore document data (rarity, etc.)
    print("\n--- Starting Card Data Post-Processing ---")
    all_cards_from_fs = get_cards_from_firestore()
    if not all_cards_from_fs:
        print("No cards found in Firestore. Skipping data post-processing.")
    else:
        rarity_update_counter, card_type_update_counter = 0, 0
        print(f"Checking {len(all_cards_from_fs)} cards for potential data updates...")
        for card_entry in all_cards_from_fs:
            updates_to_make = {}
            target_rarity = determine_final_rarity(
                card_entry["set_code"],
                card_entry["card_number_str"],
                card_entry.get("rarity", ""),
            )
            if target_rarity != card_entry.get("rarity", ""):
                updates_to_make["rarity"] = target_rarity

            card_type_after_ub = modify_card_type_for_ultra_beast(
                card_entry["set_code"],
                card_entry["card_number_str"],
                card_entry.get("card_type"),
            )
            final_card_type = modify_card_type_for_shiny(
                card_entry["set_code"],
                card_entry["card_number_str"],
                card_type_after_ub,
            )
            if final_card_type != card_entry.get("card_type"):
                updates_to_make["card_type"] = final_card_type

            if updates_to_make:
                if update_card_in_firestore(
                    card_entry["set_doc_id"], card_entry["card_doc_id"], updates_to_make
                ):
                    if "rarity" in updates_to_make:
                        rarity_update_counter += 1
                    if "card_type" in updates_to_make:
                        card_type_update_counter += 1
        print(
            f"Rarity updates: {rarity_update_counter}. Card Type updates: {card_type_update_counter}."
        )

    # Part 2: Update Set Document Card Counts
    print("\nStarting to update set documents with card counts...")
    if all_cards_from_fs:
        unique_set_doc_ids = {entry["set_doc_id"] for entry in all_cards_from_fs}
        set_count_update_success, set_count_update_failure = 0, 0
        for set_id in unique_set_doc_ids:
            try:
                aggregation_query = (
                    db_firestore.collection("cards")
                    .document(set_id)
                    .collection("set_cards")
                    .count()
                )
                count_in_set = aggregation_query.get()[0][0].value
                db_firestore.collection("cards").document(set_id).update(
                    {"card_count": count_in_set}
                )
                set_count_update_success += 1
            except Exception as e_count_update:
                print(
                    f"  FAILURE: Could not update card_count for set '{set_id}': {e_count_update}"
                )
                set_count_update_failure += 1
        print(
            f"Set card count update complete. {set_count_update_success} set(s) updated, {set_count_update_failure} failed."
        )

    print("\n\n✅ All post-processing tasks are complete.")

    trigger_cache_refresh()
    print("Cache refreshed.")


if __name__ == "__main__":
    main_post_process()
