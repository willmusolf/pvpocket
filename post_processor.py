import sqlite3
import re  # Needed for re.sub in determine_final_rarity

# post_processor.py

CUSTOM_RARITY_OVERRIDES = {
    "A2b": ("97", "110"),  # For set A2b, cards 97-110 (inclusive)
    "A3": ("210", "237"),  # For set A3, cards 210-237 (inclusive)
    # You can add other specific non-range overrides here if needed, for example:
    # "PROMO1": {"001": "P"}
}


def determine_final_rarity(set_code, card_number_str, initial_rarity_str):
    final_rarity = initial_rarity_str  # Default to original if no rules apply or conditions aren't met

    if set_code in CUSTOM_RARITY_OVERRIDES:
        override_rule = CUSTOM_RARITY_OVERRIDES[set_code]

        if isinstance(override_rule, tuple) and len(override_rule) == 2:  # Shiny range
            start_num_str, end_num_str = override_rule
            try:
                # Ensure card_number_str is treated as a string for re.sub
                current_card_num_int = int(re.sub(r"\D", "", str(card_number_str)))
                start_num_int = int(start_num_str)
                end_num_int = int(end_num_str)

                if start_num_int <= current_card_num_int <= end_num_int:
                    # Ensure initial_rarity_str is a string for .count()
                    num_stars = str(
                        initial_rarity_str if initial_rarity_str is not None else ""
                    ).count("☆")
                    if num_stars > 0:
                        new_shiny_rarity = "✵" * num_stars
                        final_rarity = new_shiny_rarity
            except ValueError:
                # This might happen if card_number or range numbers aren't parseable
                # Or if re.sub results in an empty string that can't be int()'ed
                print(
                    f"Warning: Could not parse card numbers for shiny range check: Set {set_code}, Card {card_number_str}, Range {override_rule}"
                )
                # In case of error, final_rarity remains initial_rarity_str
                pass

        elif isinstance(
            override_rule, dict
        ):  # Specific override map (e.g., for promos)
            if card_number_str in override_rule:
                final_rarity = override_rule[card_number_str]

    return final_rarity


def get_cards_for_rarity_update(db_path="pokemon_cards.db"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Access columns by name
    cursor = conn.cursor()
    # Fetch id, set_code, card_number, and current rarity for all cards
    cursor.execute("SELECT id, set_code, card_number, rarity FROM cards")
    cards = cursor.fetchall()
    conn.close()
    return cards


def update_card_rarity_in_db(db_path, card_id, new_rarity):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE cards SET rarity = ? WHERE id = ?", (new_rarity, card_id)
        )
        conn.commit()
        return cursor.rowcount > 0  # True if a row was updated
    except sqlite3.Error as e:
        print(f"Database error updating rarity for card ID {card_id}: {e}")
        return False
    finally:
        conn.close()


def main_post_process():
    print("Starting post-processing to update card rarities...")
    db_path = "pokemon_cards.db"

    all_cards_from_db = get_cards_for_rarity_update(db_path)

    if not all_cards_from_db:
        print("No cards found in the database. Nothing to post-process.")
        return

    update_counter = 0
    print(f"Checking {len(all_cards_from_db)} cards for potential rarity updates...")

    for card_row in all_cards_from_db:
        card_id = card_row["id"]
        set_code = card_row["set_code"]
        card_number = card_row["card_number"]  # This is card_number_str
        current_db_rarity = card_row["rarity"]

        # initial_rarity_str for determine_final_rarity should be the current DB rarity
        # Ensure it's a string, even if None from DB, for .count()
        rarity_to_check = current_db_rarity if current_db_rarity is not None else ""

        target_rarity = determine_final_rarity(set_code, card_number, rarity_to_check)

        # Only update if the target_rarity is different from what's currently in the DB
        if target_rarity != current_db_rarity:
            if update_card_rarity_in_db(db_path, card_id, target_rarity):
                print(
                    f"  SUCCESS: Updated card ID {card_id} ({set_code}-{card_number}). Rarity: '{current_db_rarity}' -> '{target_rarity}'"
                )
                update_counter += 1
            else:
                print(
                    f"  FAILURE: Could not update card ID {card_id} ({set_code}-{card_number}) in DB."
                )

    print(
        f"\nRarity post-processing complete. {update_counter} card(s) were updated in the database."
    )


if __name__ == "__main__":
    main_post_process()
