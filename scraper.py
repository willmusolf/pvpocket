import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import re
import os
from urllib.parse import urlparse
from typing import Optional

# This constant remains to control scraping behavior for the database
SCRAPE_ONLY_NEW_CARDS = True


# --- HELPER FUNCTION for cleaning rule text ---
def clean_rules_text(text: Optional[str]) -> Optional[str]:  # Allow None input
    if not text:
        return None

    # Replace <br> tags with newlines (if they exist, though site uses divs/newlines more)
    cleaned_text = text.replace("<br>", "\n")

    # --- More aggressive cleaning around brackets and symbols ---
    # Remove any whitespace immediately inside brackets: "[ P ]" -> "[P]"
    cleaned_text = re.sub(r"\[\s*(.*?)\s*\]", r"[\1]", cleaned_text)

    # Remove newlines and excessive whitespace BEFORE a bracketed symbol, add a single space
    cleaned_text = re.sub(r"\s*\n\s*(\[[A-Za-z]+\])", r" \1", cleaned_text)

    # Remove newlines and excessive whitespace AFTER a bracketed symbol, add a single space
    cleaned_text = re.sub(r"(\[[A-Za-z]+\])\s*\n\s*", r"\1 ", cleaned_text)

    # Ensure a single space before and after bracketed symbols if they are adjacent to non-whitespace
    # This is a fallback in case the above didn't cover all cases.
    cleaned_text = re.sub(r"(?<!\s)(\[[A-Za-z]+\])", r" \1", cleaned_text)
    cleaned_text = re.sub(r"(\[[A-Za-z]+\])(?!\s)", r"\1 ", cleaned_text)
    # --- End aggressive cleaning ---

    # Normalize multiple newlines into single newlines
    cleaned_text = re.sub(r"\n+", "\n", cleaned_text)

    # Collapse multiple spaces/tabs anywhere into a single space
    cleaned_text = re.sub(r"[ \t]+", " ", cleaned_text)

    # Trim leading/trailing whitespace from the whole block
    cleaned_text = cleaned_text.strip()

    # If text becomes empty after stripping, return None
    if not cleaned_text:
        return None

    lines = cleaned_text.splitlines()
    processed_lines = []

    for line in lines:
        # Trim leading/trailing whitespace from each line
        current_line = line.strip()

        if not current_line:  # Skip empty lines after trimming
            continue

        # Append the cleaned line
        processed_lines.append(current_line)

    if not processed_lines:
        return None

    # Join lines with a single newline. This preserves intended line breaks.
    final_text = "\n".join(processed_lines)

    # Post-processing: Ensure single space after colon if followed by text on the next line
    # This handles cases like "Ability:\nSome description" -> "Ability: Some description"
    final_text = re.sub(
        r":\n([^\n])", r": \1", final_text
    )  # Colon followed by newline and then non-newline char
    final_text = re.sub(
        r":\n$", ":", final_text
    )  # Colon followed by newline at the end

    return final_text if final_text else None


# Function to download and save card images locally
def download_card_image(image_url, set_name, set_code, card_number):
    try:
        safe_set_name = (
            set_name.lower().replace(" ", "-").replace("'", "").replace(",", "")
        )
        parsed_url = urlparse(image_url)
        path = parsed_url.path
        ext = os.path.splitext(path)[1]
        if not ext:  # Default extension if not found in URL
            ext = (
                ".png"
                if ".png" in image_url.lower()
                else ".webp" if ".webp" in image_url.lower() else ".jpg"
            )
            if not ext.startswith("."):
                ext = "." + ext

        filename = f"{card_number}{ext}"

        # Path to be stored in DB (relative to the 'images' static folder)
        db_relative_path = os.path.join("cards", safe_set_name, filename).replace(
            "\\", "/"
        )

        # Full path for saving the file locally
        base_dir_for_saving = os.path.join("images", "cards", safe_set_name)
        os.makedirs(base_dir_for_saving, exist_ok=True)
        full_save_path = os.path.join(base_dir_for_saving, filename)

        if os.path.exists(full_save_path):
            return db_relative_path  # Already exists

        print(
            f"Downloading image for {set_name} - {card_number} from {image_url} to {full_save_path}"
        )
        response = requests.get(image_url, stream=True, timeout=15)
        response.raise_for_status()
        with open(full_save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return db_relative_path
    except Exception as e:
        print(
            f"Error downloading/saving image for {set_name} - {card_number} ({image_url}): {e}"
        )
        return None


# Database setup
def setup_database():
    conn = sqlite3.connect("pokemon_cards.db")
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(cards)")
    existing_columns_info = cursor.fetchall()
    existing_column_names = [col_info[1] for col_info in existing_columns_info]

    # Define the ideal schema with columns in the desired order
    # Changed 'effects' to 'abilities' and moved it before 'attacks'
    ideal_schema_ordered = [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("name", "TEXT"),
        ("energy_type", "TEXT"),
        ("set_name", "TEXT"),
        ("set_code", "TEXT"),
        ("card_number", "TEXT"),
        ("card_type", "TEXT"),
        ("hp", "INTEGER"),
        ("abilities", "TEXT"),  # Changed from 'effects' and moved here
        ("attacks", "TEXT"),
        ("weakness", "TEXT"),
        ("retreat_cost", "INTEGER"),
        ("illustrator", "TEXT"),
        ("flavor_text", "TEXT"),
        ("image_url", "TEXT"),
        ("rarity", "TEXT"),
        ("pack", "TEXT"),
        ("local_image_path", "TEXT"),
    ]

    if not existing_column_names:  # Table doesn't exist, create it
        cols_definitions = ", ".join(
            [f"'{col_name}' {col_type}" for col_name, col_type in ideal_schema_ordered]
        )
        # Note: UNIQUE constraint handled separately for clarity in CREATE statement
        create_table_sql = f"""
            CREATE TABLE cards (
                {cols_definitions},
                UNIQUE(set_code, card_number)
            )
        """
        cursor.execute(create_table_sql)
        print("Created 'cards' table with columns in specified order.")
        # Update existing_columns list after creation
        cursor.execute("PRAGMA table_info(cards)")
        existing_column_names = [col[1] for col in cursor.fetchall()]
    else:  # Table exists, check for and add missing columns from the ideal_schema
        for col_name, col_type in ideal_schema_ordered:
            # Handle renaming 'effects' to 'abilities' if 'effects' exists but 'abilities' doesn't
            if (
                col_name == "abilities"
                and "effects" in existing_column_names
                and "abilities" not in existing_column_names
            ):
                try:
                    cursor.execute(
                        "ALTER TABLE cards RENAME COLUMN effects TO abilities"
                    )
                    print("Renamed column 'effects' to 'abilities'.")
                except sqlite3.OperationalError as e:
                    print(f"Warning during RENAME COLUMN effects to abilities: {e}")
            elif (
                col_name not in existing_column_names
                and col_name != "id"
                and col_name
                != "effects"  # Don't try to add 'effects' if we're renaming it
            ):  # 'id' is special
                try:
                    cursor.execute(
                        f"ALTER TABLE cards ADD COLUMN '{col_name}' {col_type}"
                    )
                    print(f"Added missing column '{col_name}' to 'cards' table.")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        # This case should ideally not be hit if existing_column_names is accurate
                        print(
                            f"Note: Column '{col_name}' was marked missing but already exists."
                        )
                    else:
                        print(f"Warning during ALTER TABLE for '{col_name}': {e}")

    if not SCRAPE_ONLY_NEW_CARDS:
        print("Clearing ALL existing card data from 'cards' table (full scrape mode).")
        cursor.execute("DELETE FROM cards")
    else:
        print(
            "Scraping only new cards. Existing data in 'cards' table will be preserved."
        )

    conn.commit()
    conn.close()


# Function to save data to database
def save_to_database(card_data):
    # Updated expected fields count and column names/order
    expected_fields = 17  # name, energy_type, set_name, set_code, card_number, card_type, hp, abilities, attacks, weakness, retreat_cost, illustrator, flavor_text, image_url, rarity, pack, local_image_path
    if len(card_data) != expected_fields:
        print(
            f"Error: Expected {expected_fields} data fields, but got {len(card_data)} for card {card_data[3]}-{card_data[4]}. Skipping DB save."
        )  # card_data[3] is set_code, card_data[4] is card_number
        print(f"Data: {card_data}")
        return

    conn = sqlite3.connect("pokemon_cards.db")
    cursor = conn.cursor()
    try:
        # Order of columns in INSERT must match the order in card_data tuple
        # Updated column names and order to reflect 'abilities' before 'attacks'
        cursor.execute(
            """
            INSERT INTO cards (
                name, energy_type, set_name, set_code, card_number, card_type,
                hp, abilities, attacks, weakness, retreat_cost, illustrator,
                flavor_text, image_url, rarity, pack, local_image_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            card_data,
        )
        conn.commit()
    except sqlite3.IntegrityError:  # Handles UNIQUE constraint violation
        print(
            f"Card {card_data[3]}-{card_data[4]} likely already exists (IntegrityError). Skipping."
        )
    except Exception as e:
        print(f"Error saving card {card_data[3]}-{card_data[4]} to DB: {e}")
    finally:
        conn.close()


# Function to get all sets
def get_card_sets():
    url = "https://pocket.limitlesstcg.com/cards"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching card sets: {e}")
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    sets = []
    for link_tag in soup.select("a[href^='/cards/']"):  # Iterate over <a> tags
        href = link_tag["href"]
        if href.count("/") == 2:  # Format /cards/SET_CODE
            set_code = href.split("/")[-1]
            set_name = " ".join(
                link_tag.text.split()
            ).strip()  # Cleaned set name from link text
            # Basic filters for invalid set names
            if (
                not set_name
                or set_name.isspace()
                or re.match(r"^\d{1,2} \w{3,} \d{2}$", set_name)
                or set_name.isdigit()
            ):
                continue
            print(f"Extracted set: {set_name} ({set_code})")
            sets.append((set_name, set_code))
    return sets


# Function to get all cards from a set
def get_cards_from_set(set_code):
    url = f"https://pocket.limitlesstcg.com/cards/{set_code}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching cards from set {set_code}: {e}")
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    card_numbers = []
    for link_tag in soup.select(f"a[href^='/cards/{set_code}/']"):
        href = link_tag["href"]
        if href.count("/") == 3:  # Format /cards/SET_CODE/CARD_NUMBER
            card_number = href.split("/")[-1]
            card_numbers.append(card_number)
    return card_numbers


# Function to check if card exists in DB
def card_exists_in_db(set_code, card_number):
    conn = sqlite3.connect("pokemon_cards.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM cards WHERE set_code = ? AND card_number = ?",
        (set_code, card_number),
    )
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def scrape_card_details(set_code, card_number):
    url = f"https://pocket.limitlesstcg.com/cards/{set_code}/{card_number}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching details for {set_code}-{card_number}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    try:
        name_element = soup.select_one(
            ".card-text .card-text-name"
        )  # More specific to avoid other names
        if not name_element:
            print(f"Could not find name for {set_code}-{card_number}. Skipping.")
            return None
        name = " ".join(name_element.text.split()).strip()
        print(f"Scraping card: {name} ({set_code}-{card_number})")

        set_name_el = soup.select_one(".prints-current-details span.text-lg")
        set_name = (
            re.sub(
                r"\s*\([A-Za-z0-9\-]+\)\s*$",
                "",
                re.sub(r"\s+", " ", set_name_el.text).strip(),
            )
            if set_name_el
            else "Unknown Set"
        )

        card_type_el = soup.select_one(".card-text .card-text-type")
        card_type = (
            " ".join(card_type_el.text.split()).strip()
            if card_type_el
            else "Unknown Type"
        )

        energy_type = ""
        title_el = soup.select_one(".card-text .card-text-title")
        if title_el:
            title_text = title_el.get_text()
            pkmn_energies = [
                "Grass",
                "Fire",
                "Water",
                "Lightning",
                "Psychic",
                "Fighting",
                "Darkness",
                "Metal",
                "Colorless",
                "Dragon",
                "Fairy",
            ]
            for etype in pkmn_energies:
                if f"- {etype}" in title_text:
                    energy_type = etype
                    break
            hp_match = re.search(r"(\d+)\s*HP", title_text)
            hp = int(hp_match.group(1)) if hp_match else None
        else:
            hp = None

        rarity_pack_el = soup.select_one(".prints-current-details span:not(.text-lg)")
        rarity, pack = "", ""
        if rarity_pack_el:
            parts = rarity_pack_el.get_text("·", strip=True).split("·")
            if len(parts) >= 2:
                rarity = parts[1].strip()  # Assuming rarity is second part
            if len(parts) >= 3:
                pack_text = parts[2].strip()
                pack = (
                    re.sub(r"(?i)\s*pack\s*", "", pack_text)
                    if "pack" in pack_text.lower()
                    else pack_text
                )

        weakness, retreat_cost = None, None
        if "Pokémon" in card_type:
            wrr_el = soup.select_one(".card-text-wrr")
            if wrr_el:
                wrr_text = wrr_el.get_text()
                weak_match = re.search(
                    r"Weakness:\s*([A-Za-z]+(?:[\s×x+]\d+)?)", wrr_text
                )
                if weak_match:
                    weakness = weak_match.group(1).strip()
                retreat_match = re.search(r"Retreat:\s*(\d+)", wrr_text)
                if retreat_match:
                    retreat_cost = int(retreat_match.group(1))

        artist_el = soup.select_one(".card-text-artist")
        illustrator = None  # Initialize illustrator
        if artist_el:
            artist_text = artist_el.text.strip()  # Get the full text once
            if "Illustrated by" in artist_text:
                # Split by "Illustrated by" and take the second part
                parts = artist_text.split("Illustrated by", 1)
                if len(parts) > 1:
                    illustrator = parts[1].strip()
            elif (
                "illustrator:" in artist_text.lower()
            ):  # Check lowercase for "illustrator:"
                # Split by "illustrator:" (case-insensitive due to .lower())
                parts = re.split(
                    r"illustrator:", artist_text, maxsplit=1, flags=re.IGNORECASE
                )
                if len(parts) > 1:
                    illustrator = (
                        parts[1].strip().title()
                    )  # .title() to capitalize words
            else:
                # If no specific prefix, assume the whole text is the illustrator's name
                illustrator = artist_text

            # Further clean up common extraneous details if any (e.g. trailing set info if not caught by selectors)
            # For now, the above logic should be safer.
            if illustrator:  # Ensure illustrator is not empty after stripping
                illustrator = " ".join(illustrator.split())  # Normalize spaces

        flavor_el = soup.select_one(".card-text-flavor")
        flavor_text = (
            clean_rules_text(flavor_el.get_text()) if flavor_el else None
        )  # Also clean flavor text

        img_el = soup.select_one(".card-image img")
        image_url_val = img_el["src"] if img_el and img_el.has_attr("src") else ""
        local_image_path = (
            download_card_image(image_url_val, set_name, set_code, card_number)
            if image_url_val
            else None
        )

        attacks_data = []
        abilities_list = []  # Renamed from effects_list

        if "Pokémon" in card_type:
            # Scrape Abilities
            ability_elements = soup.select(
                ".card-text-ability"
            )  # Common class for abilities
            for ab_el in ability_elements:
                raw_ability_text = ab_el.get_text(separator="\n")
                cleaned_ability_text = clean_rules_text(raw_ability_text)
                if cleaned_ability_text:
                    abilities_list.append(cleaned_ability_text)

            # Scrape Attacks
            attack_elements = soup.select(".card-text-attack")
            for idx, atk_el in enumerate(attack_elements):
                atk_name, atk_dmg, atk_costs, atk_effect_raw = "", "0", [], ""

                cost_spans = atk_el.select(
                    ".card-text-attack-info span.ptcg-symbol, .card-text-attack-cost span.ptcg-symbol"
                )
                for cs in cost_spans:
                    atk_costs.append(cs.get("aria-label", cs.text.strip()))

                info_el = atk_el.select_one(".card-text-attack-info")
                current_info_text = ""
                if info_el:
                    text_parts = [
                        node.strip()
                        for node in info_el.find_all(string=True, recursive=False)
                        if node.strip()
                    ]
                    current_info_text = " ".join(text_parts).strip()
                    dmg_match = re.search(
                        r"((?:\d+\+?)|(?:[xX×]\d+)|(?:\d+x))$", current_info_text
                    )
                    if dmg_match:
                        atk_dmg = dmg_match.group(1)
                        atk_name = current_info_text[: dmg_match.start()].strip()
                    else:
                        atk_name = current_info_text

                if not atk_costs and atk_name:  # Minimal fix for costs in name
                    cost_name_match = re.match(r"^([A-Z]+)\s+(.*)", atk_name)
                    if cost_name_match:
                        atk_costs.extend(list(cost_name_match.group(1)))
                        atk_name = cost_name_match.group(2).strip()

                if not atk_name and info_el:  # Fallback for attack name
                    atk_name = info_el.get_text(strip=True).split(" ")[0]

                effect_el = atk_el.select_one(".card-text-attack-effect")
                if effect_el:
                    atk_effect_raw = effect_el.get_text(separator="\n")

                attacks_data.append(
                    {
                        "name": atk_name if atk_name else f"Attack {idx + 1}",
                        "cost": atk_costs,
                        "damage": atk_dmg,
                        "effect": clean_rules_text(
                            atk_effect_raw
                        ),  # Clean attack effect text
                    }
                )
        elif "Trainer" in card_type or (
            "Energy" in card_type
            and "Basic" not in card_type
            and name
            and "Basic" not in name
        ):
            main_text_div = soup.select_one(".card-text")
            if main_text_div:
                # Explicitly remove the artist element if it exists within the main text div
                # This prevents "Illustrated by" from being scraped with the rules text.
                artist_div_to_remove = main_text_div.select_one(".card-text-artist")
                if artist_div_to_remove:
                    artist_div_to_remove.decompose()  # Remove the element from the soup

                # Now scrape the remaining text sections
                sections = main_text_div.select(":scope > div.card-text-section")
                for sec in sections:
                    # Skip sections that are known meta-data containers or attacks/abilities
                    # (The artist element is already removed)
                    if not (
                        sec.select_one(
                            ".card-text-title, .card-text-type, .card-text-wrr, .card-text-flavor, .card-text-attack, .card-text-ability"
                        )
                    ):
                        raw_section_text = sec.get_text(
                            separator="\n"
                        )  # Keep original newlines for context
                        cleaned_section_text = clean_rules_text(raw_section_text)
                        if cleaned_section_text:
                            # No need for the "illustrated by" filter here as the element is removed
                            abilities_list.append(
                                cleaned_section_text
                            )  # Append to abilities_list

        # Join the collected abilities/effects text.
        # For Trainer/Energy, this is the main rules text.
        # For Pokémon, this is the ability text(s).
        # Join with newline.
        final_abilities_text = "\n".join(abilities_list) if abilities_list else None

        # Ensure the order here matches the INSERT statement and ideal_schema_ordered
        return (
            name,
            energy_type,
            set_name,
            set_code,
            card_number,
            card_type,
            hp,
            final_abilities_text,  # Changed from final_effects_text and moved before attacks
            str(attacks_data),
            weakness,
            retreat_cost,
            illustrator,
            flavor_text,
            image_url_val,
            rarity,
            pack,
            local_image_path,
        )
    except Exception as e:
        print(
            f"Error parsing card details for {set_code}-{card_number} (URL: {url}): {e}"
        )
        import traceback

        traceback.print_exc()
        return None


# Main function
def main():
    os.makedirs(os.path.join("images", "cards"), exist_ok=True)
    setup_database()
    card_sets = get_card_sets()
    total_scraped = 0
    for set_n, set_c in card_sets:
        print(f"\nProcessing Set: {set_n} ({set_c})")
        scraped_in_set = 0
        for card_num_str in get_cards_from_set(set_c):
            if SCRAPE_ONLY_NEW_CARDS and card_exists_in_db(set_c, card_num_str):
                continue
            card_details_tuple = scrape_card_details(set_c, card_num_str)
            if card_details_tuple:
                save_to_database(card_details_tuple)
                scraped_in_set += 1
            # time.sleep(0.05) # Optional delay
        print(
            f"Finished set {set_n}. Scraped {scraped_in_set} new card(s)."
            if scraped_in_set > 0
            else f"Finished set {set_n}. No new cards to add."
        )
        total_scraped += scraped_in_set
    print(f"\nScraping complete! Total new cards added: {total_scraped}")


if __name__ == "__main__":
    main()