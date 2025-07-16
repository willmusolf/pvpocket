import re
import requests
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import secretmanager

from dotenv import load_dotenv


# --- Card Data Processing Rules & Helper Functions ---

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


def get_sortable_card_number(card_number_str: str) -> int:
    """Extracts a numeric value from a card number string for sorting."""
    # This will handle '123/165' and 'sv045' by stripping non-digits
    numeric_part = re.sub(r"\D", "", str(card_number_str))
    return int(numeric_part) if numeric_part else 0


def get_cards_grouped_by_set():
    """
    Fetches all cards from Firestore and groups them by set.
    Returns a dictionary like: {'set_code': [card_list]}
    """
    if not db_firestore:
        print("Firestore client not initialized. Cannot fetch cards.")
        return {}

    print("Fetching and grouping all cards by set from Firestore...")
    sets_data = {}
    try:
        sets_collection_ref = db_firestore.collection("cards").stream()
        for set_doc in sets_collection_ref:
            set_code = set_doc.to_dict().get("set_code")
            if not set_code:
                continue

            card_list = []
            cards_subcollection_ref = set_doc.reference.collection("set_cards").stream()
            for card_doc in cards_subcollection_ref:
                card_data = card_doc.to_dict()
                if card_data:
                    # Ensure all necessary keys are present before adding
                    if all(
                        k in card_data
                        for k in ["card_number_str", "rarity", "card_type"]
                    ):
                        card_list.append(
                            {
                                "set_doc_id": set_doc.id,
                                "card_doc_id": card_doc.id,
                                **card_data,
                            }
                        )
            if card_list:
                sets_data[set_code] = card_list
    except Exception as e:
        print(f"Error fetching cards from Firestore: {e}", exc_info=True)

    print(f"Found and grouped {len(sets_data)} sets.")
    return sets_data


def main_post_process():
    """
    Main post-processing function. Applies automated shiny logic for most sets,
    a special rule for the P-A set, handles Ultra Beasts, and updates set counts.
    """
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
            
    if not db_firestore:
        print("Exiting: Firestore client failed to initialize.")
        return

    all_sets = get_cards_grouped_by_set()
    if not all_sets:
        print("No sets found to process.")
        return

    print("\n--- Starting Card Data Post-Processing ---")
    total_updates_made = 0

    # Part 1: Process each set for shiny and ultra beast updates
    for set_code, cards in all_sets.items():
        print(f"\nProcessing set: {set_code} ({len(cards)} cards)")

        sorted_cards = sorted(
            cards, key=lambda c: get_sortable_card_number(c["card_number_str"])
        )

        # Find the marker card indices for the automated shiny logic
        last_three_star_index = -1
        first_crown_rare_index = len(sorted_cards)
        for i, card in enumerate(sorted_cards):
            rarity = card.get("rarity", "")
            if "☆☆☆" in rarity:
                last_three_star_index = i
            if "♛" in rarity and i < first_crown_rare_index:
                first_crown_rare_index = i

        shiny_start_index = last_three_star_index + 1

        # Now iterate through all cards to apply all rules
        for i, card in enumerate(sorted_cards):
            updates_to_make = {}

            # Start with the original card type
            final_card_type = card.get("card_type")

            # Rule 1: Apply the hardcoded shiny logic (affects P-A set)
            final_card_type = modify_card_type_for_shiny(
                card["set_code"], card["card_number_str"], final_card_type
            )

            # Rule 2: Apply the new automated shiny logic
            if (
                last_three_star_index != -1
                and i >= shiny_start_index
                and i < first_crown_rare_index
            ):
                if " (Shiny)" not in final_card_type:
                    final_card_type += " (Shiny)"

                # Also update its rarity symbol to the shiny version
                num_stars = str(card.get("rarity", "")).count("☆")
                if num_stars > 0:
                    updates_to_make["rarity"] = "✵" * num_stars

            # Rule 3: Apply Ultra Beast logic
            final_card_type = modify_card_type_for_ultra_beast(
                card["set_code"], card["card_number_str"], final_card_type
            )

            # Check if the card type has changed after all rules
            if final_card_type != card.get("card_type"):
                updates_to_make["card_type"] = final_card_type

            # If there are any updates, write them to Firestore
            if updates_to_make:
                print(
                    f"  -> UPDATING {card.get('name')} ({card.get('set_code')} {card.get('card_number_str')}): {updates_to_make}"
                )
                if update_card_in_firestore(
                    card["set_doc_id"], card["card_doc_id"], updates_to_make
                ):
                    total_updates_made += 1

    print(f"\nFinished processing cards. Total updates made: {total_updates_made}")

    # Part 2: Update Set Document Card Counts (Unchanged)
    print("\nStarting to update set documents with card counts...")
    set_count_update_success, set_count_update_failure = 0, 0
    all_set_doc_ids = {
        card["set_doc_id"] for cards in all_sets.values() for card in cards
    }

    for set_id in all_set_doc_ids:
        try:
            count_query = (
                db_firestore.collection("cards")
                .document(set_id)
                .collection("set_cards")
                .count()
            )
            count_result = count_query.get()
            count_in_set = count_result[0][0].value

            db_firestore.collection("cards").document(set_id).update(
                {"card_count": count_in_set}
            )
            set_count_update_success += 1
        except Exception as e:
            print(f"  FAILURE: Could not update card_count for set '{set_id}': {e}")
            set_count_update_failure += 1

    print(
        f"Set card count update complete. {set_count_update_success} set(s) updated, {set_count_update_failure} failed."
    )
    print("\n\n✅ All post-processing tasks are complete.")


if __name__ == "__main__":
    main_post_process()
