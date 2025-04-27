import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import csv
import re
import os
from urllib.parse import urlparse

CUSTOM_RARITY_OVERRIDES = {
    "A2b": {  # Shining Revelry
        "97": "✵",
        "98": "✵",
        "99": "✵",
        "100": "✵",
        "101": "✵",
        "102": "✵",
        "103": "✵",
        "104": "✵",
        "105": "✵",
        "106": "✵",
        "107": "✵✵",
        "108": "✵✵",
        "109": "✵✵",
        "110": "✵✵",
    },
    # --- Example: Add future overrides below ---
    # "XYZ": { # Replace with actual set code
    #     "015": "★", # Replace with actual card number and rarity
    #     "025": "★"
    # },
    # "PROMO1": { # Replace with actual promo set code
    #      "001": "P" # Replace with actual card number and promo rarity symbol
    # }
}


# Function to download and save card images locally
# Function to download and save card images locally (Corrected Return Path Logic)
def download_card_image(image_url, set_name, set_code, card_number):
    try:
        # --- Determine Relative Path (for DB/HTML) ---
        # Create a safe directory name from the set name for the relative path
        safe_set_name = (
            set_name.lower().replace(" ", "-").replace("'", "").replace(",", "")
        )

        # Parse URL to get file extension
        parsed_url = urlparse(image_url)
        path = parsed_url.path
        ext = os.path.splitext(path)[1]
        if not ext:
            ext = ".png"  # Default extension if none found

        # Create filename using card number
        filename = f"{card_number}{ext}"

        # Define the desired relative path explicitly - THIS is what should be stored/used by HTML
        relative_path = f"cards/{safe_set_name}/{filename}"

        # --- Determine Full Server Save Path ---
        # Create the actual directory structure on the server where the file will be saved
        # This includes the root 'images' directory.
        base_dir = os.path.join("images", "cards", safe_set_name)
        os.makedirs(base_dir, exist_ok=True)  # Create directories if they don't exist
        full_save_path = os.path.join(
            base_dir, filename
        )  # Full path for saving the file

        # --- Check if file exists on server ---
        if os.path.exists(full_save_path):
            # print(f"Image already exists: {full_save_path}") # Log the full path where it exists
            return relative_path  # <<< Return the RELATIVE path

        # --- Download if needed ---
        print(
            f"Downloading image for {set_name} - {card_number} from {image_url} to {full_save_path}"
        )
        response = requests.get(image_url, stream=True, timeout=15)
        response.raise_for_status()

        # Save to the full server path
        with open(full_save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        # print(f"Downloaded image to {full_save_path}")

        # --- Return the relative path ---
        return relative_path  # <<< Return the RELATIVE path

    except Exception as e:
        print(
            f"Error downloading/saving image for {set_name} - {card_number} ({image_url}): {e}"
        )
        return None  # Return None on error


# Database setup (Resistance column addition REMOVED)
def setup_database():
    conn = sqlite3.connect("pokemon_cards.db")
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(cards)")
    columns = [column[1] for column in cursor.fetchall()]

    if not columns:
        cursor.execute(
            """
            CREATE TABLE cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                set_name TEXT,
                set_code TEXT,
                card_number TEXT,
                card_type TEXT,
                hp INTEGER,
                attacks TEXT,
                weakness TEXT,
                retreat_cost INTEGER,
                illustrator TEXT,
                flavor_text TEXT,
                image_url TEXT
            )
        """
        )
        print("Created base cards table.")
        cursor.execute("PRAGMA table_info(cards)")
        columns = [column[1] for column in cursor.fetchall()]

    # Add columns dynamically if they don't exist (NO resistance here)
    cols_to_add = {
        "energy_type": "TEXT",
        "rarity": "TEXT",
        "pack": "TEXT",
        "local_image_path": "TEXT",
        # 'resistance': 'TEXT' # <<< REMOVED
    }

    for col_name, col_type in cols_to_add.items():
        if col_name not in columns:
            try:
                cursor.execute(f"ALTER TABLE cards ADD COLUMN {col_name} {col_type}")
                print(f"Added {col_name} column to cards table")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"Note: Column {col_name} already exists.")
                else:
                    print(f"Warning during ALTER TABLE for {col_name}: {e}")

    # Clear previous data before fresh scrape
    print("Clearing existing card data from database.")
    cursor.execute("DELETE FROM cards")

    conn.commit()
    conn.close()


# Function to save data to database (Reverted to 16 columns)
def save_to_database(card_data):
    # card_data tuple should now have 16 elements again
    if len(card_data) != 16:
        print(
            f"Error: Expected 16 data fields, but got {len(card_data)} for card {card_data[3]}-{card_data[4]}. Skipping DB save."
        )
        print(f"Data: {card_data}")
        return

    conn = sqlite3.connect("pokemon_cards.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO cards (
                name, energy_type, set_name, set_code, card_number, card_type,
                hp, attacks, weakness, retreat_cost, illustrator,
                flavor_text, image_url, rarity, pack, local_image_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            card_data,
        )  # <<< Back to 16 placeholders
        conn.commit()
    except sqlite3.IntegrityError:
        print(
            f"Card {card_data[3]}-{card_data[4]} likely already exists (IntegrityError). Skipping."
        )
    except Exception as e:
        print(f"Error saving card {card_data[3]}-{card_data[4]} to DB: {e}")
    finally:
        conn.close()


# Function to reset and save data to CSV
def save_to_csv(card_data, write_header=False):
    mode = "w" if write_header else "a"  # 'w' for reset, 'a' for append
    with open("pokemon_cards.csv", mode, newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(
                [
                    "Name",
                    "Energy Type",
                    "Set Name",
                    "Set Code",
                    "Card Number",
                    "Card Type",
                    "HP",
                    "Attacks",
                    "Weakness",
                    "Retreat Cost",
                    "Illustrator",
                    "Flavor Text",
                    "Image URL",
                    "Rarity",
                    "Pack",
                    "Local Image Path",
                ]
            )
        elif card_data:
            writer.writerow(card_data)


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
    for link in soup.select("a[href^='/cards/']"):
        href = link["href"]
        if href.count("/") == 2:
            set_code = href.split("/")[-1]
            set_name = " ".join(link.text.split()).strip()

            if not set_name or set_name.isspace():
                continue
            if re.match(r"^\d{1,2} \w{3,} \d{2}$", set_name):
                continue
            if set_name.isdigit():
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
    cards = []
    for link in soup.select(f"a[href^='/cards/{set_code}/']"):
        href = link["href"]
        if href.count("/") == 3:
            card_number = href.split("/")[-1]
            cards.append(card_number)

    return cards


def scrape_card_details(set_code, card_number): 
    url = f"https://pocket.limitlesstcg.com/cards/{set_code}/{card_number}" 
    try: 
        response = requests.get(url, timeout=10) 
        response.raise_for_status() 
    except requests.RequestException as e: 
        print(f"Error fetching details for card {card_number} from set {set_code}: {e}") 
        return None 
    soup = BeautifulSoup(response.text, "html.parser") 
    try: 
        name = " ".join(soup.select_one(".card-text-name").text.split()).strip() 
        print(f"Scraping card: {name} ({set_code}-{card_number})") 
        # Clean up the set name
        set_name_element = soup.select_one(".prints-current-details span.text-lg") 
        if set_name_element: 
            set_name = re.sub(r'\s+', ' ', set_name_element.text).strip() 
            # Remove the set code in parentheses
            set_name = re.sub(r'\s*\([A-Za-z0-9]+\)\s*$', '', set_name).strip() 
        else: 
            set_name = "Unknown Set" 
        card_type = " ".join(soup.select_one(".card-text-type").text.split()).strip() 
        # Extract energy type from the title text
        energy_type = "" 
        title_element = soup.select_one(".card-text-title") 
        if title_element: 
            full_title_text = title_element.get_text() 
            # Simplest approach: look for "- Type -" pattern in the text
            energy_types = ["Grass", "Fire", "Water", "Lightning", "Psychic",  
                            "Fighting", "Darkness", "Metal", "Colorless", "Dragon", "Fairy"] 
            for type_name in energy_types: 
                pattern = f"- {type_name}" 
                if pattern in full_title_text: 
                    energy_type = type_name 
                    break 

        # Extract rarity and pack from card print details
        rarity = "" 
        pack = "" 
        prints_details = soup.select_one(".prints-current-details span:not(.text-lg)") 
        if prints_details: 
            details_text = prints_details.get_text().strip() 
            # Example: "#1 · ◊◊ · Arceus pack"
            details_parts = details_text.split("·") 
            if len(details_parts) >= 2: 
                rarity = details_parts[1].strip() 
            if len(details_parts) >= 3: 
                pack = details_parts[2].strip() 
                # Remove the word "pack" if present
                if "pack" in pack: 
                    pack = pack.replace("pack", "").strip() 
        # <<< START OF ADDED RARITY OVERRIDE LOGIC >>>
        # Check if there's a custom rarity override defined for this card
        # This uses the CUSTOM_RARITY_OVERRIDES dictionary defined outside this function
        if (
            set_code in CUSTOM_RARITY_OVERRIDES
            and card_number in CUSTOM_RARITY_OVERRIDES[set_code]
        ):
            original_scraped_rarity = rarity  # Store original for logging if needed
            new_rarity = CUSTOM_RARITY_OVERRIDES[set_code][card_number]
            print(
                f"Applying custom rarity override '{new_rarity}' for {set_code}-{card_number} (Original: '{original_scraped_rarity}')"
            )
            rarity = new_rarity  # Apply the override, replacing the scraped value
        # <<< END OF ADDED RARITY OVERRIDE LOGIC >>>
        # Extract HP
        hp = None
        if title_element:
            hp_match = re.search(r"(\d+)\s*HP", title_element.get_text())
            if hp_match:
                hp = int(hp_match.group(1))
        # Extract weakness and retreat cost - only for Pokemon cards
        weakness = None
        retreat_cost = None
        if "Pokémon" in card_type:
            wrr_element = soup.select_one(".card-text-wrr")
            if wrr_element:
                wrr_text = wrr_element.get_text()
                # Extract weakness
                weakness_match = re.search(r"Weakness:\s*([A-Za-z]+)", wrr_text)
                if weakness_match:
                    weakness = weakness_match.group(1).strip()
                # Extract retreat cost
                retreat_match = re.search(r"Retreat:\s*(\d+)", wrr_text)
                if retreat_match:
                    retreat_cost = int(retreat_match.group(1))
        # Extract illustrator
        illustrator = None
        artist_element = soup.select_one(".card-text-artist")
        if artist_element:
            artist_text = artist_element.text.strip()
            if "Illustrated by" in artist_text:
                illustrator = artist_text.split("Illustrated by")[1].strip()
        # Extract flavor text
        flavor_text = None
        flavor_element = soup.select_one(".card-text-flavor")
        if flavor_element:
            flavor_text = flavor_element.text.strip()
        # Get image URL
        image_url = soup.select_one(".card-image img")["src"]
        # Download the image and get local path
        local_image_path = download_card_image(
            image_url, set_name, set_code, card_number
        )
        # Handle attacks for Pokemon cards or effects for Trainer cards
        attacks = []
        # For Pokemon cards, extract attacks
        if "Pokémon" in card_type:
            attack_elements = soup.select(".card-text-attack")
            for attack in attack_elements:
                # Get energy symbols
                energy_costs = attack.select(".ptcg-symbol")
                attack_cost = (
                    [cost.text.strip() for cost in energy_costs] if energy_costs else []
                )
                # Get attack info line
                attack_info = attack.select_one(".card-text-attack-info")
                if not attack_info:
                    continue
                attack_info_text = attack_info.get_text(strip=True)
                # Parse attack name and damage - special handling for energy symbols
                # First, identify energy symbols positions in the text
                energy_positions = []
                for energy in energy_costs:
                    energy_symbol = energy.text.strip()
                    # Find the position in the original HTML
                    energy_html_pos = attack_info_text.find(energy_symbol)
                    if energy_html_pos != -1:
                        energy_positions.append((energy_html_pos, energy_symbol))
                # Clean the attack name and damage
                # Find the last number with optional + or x at the end
                damage_match = re.search(r"(\d+(?:\+|x)?)$", attack_info_text)
                if damage_match:
                    attack_damage = damage_match.group(1)
                    attack_name = attack_info_text[: damage_match.start()].strip()
                    # If the attack name is just 'x', it's likely a parsing error
                    if attack_name.strip() == "x":
                        temp_parts = attack_info_text.split()
                        if len(temp_parts) > 1:
                            attack_name = " ".join(temp_parts[:-1])
                            attack_damage = temp_parts[-1]
                else:
                    # Handle attacks with no damage value
                    attack_damage = "0"
                    attack_name = attack_info_text.strip()
                # Remove energy symbols from the beginning of the name
                # But make sure we're only removing if they are at the start
                for pos, symbol in sorted(energy_positions, key=lambda x: x[0]):
                    if attack_name.startswith(symbol):
                        attack_name = attack_name[len(symbol) :].strip()
                # Get effect text
                attack_effect = attack.select_one(".card-text-attack-effect")
                attack_effect = attack_effect.text.strip() if attack_effect else ""
                attacks.append(
                    {
                        "name": attack_name,
                        "cost": attack_cost,
                        "damage": attack_damage,
                        "effect": attack_effect,
                    }
                )
        # For Trainer cards, extract text description
        elif "Trainer" in card_type: 
            # Find all card text sections that aren't title, type, or artist info
            trainer_text_sections = soup.select(".card-text-section") 
            trainer_effect = "" 
            for section in trainer_text_sections: 
                # Skip title, type, and artist sections
                if section.select_one(".card-text-title") or section.select_one(".card-text-type") or section.select_one(".card-text-artist"): 
                    continue 
                # Get the text content and add it to the effect
                section_text = section.get_text(strip=True) 
                if section_text: 
                    trainer_effect += section_text + " " 
            if trainer_effect: 
                # For trainer cards, we'll represent the effect in the attack array to keep consistent format
                attacks = [{ 
                     "name": "Effect",  
                     "cost": [], 
                     "damage": "", 
                     "effect": trainer_effect.strip()
                 }] 
        # Return card data including the local image path
        return (name, energy_type, set_name, set_code, card_number, card_type, hp, str(attacks), 
                weakness, retreat_cost, illustrator, flavor_text, image_url, rarity, pack, local_image_path) 

    except AttributeError as e: 

        print(f"Error parsing card details for {card_number} in set {set_code}: {e}") 

        return None


# Main function to scrape all data
def main():
    # Create base directory for images
    os.makedirs(os.path.join("images", "cards"), exist_ok=True)

    setup_database()
    save_to_csv([], write_header=True)  # Reset CSV before scraping

    sets = get_card_sets()
    for set_name, set_code in sets:
        for card_number in get_cards_from_set(set_code):
            card_data = scrape_card_details(set_code, card_number)
            # print(card_data)
            if card_data:
                save_to_csv(card_data)
                save_to_database(card_data)
            # time.sleep(1)  # Uncomment to add delay between requests

    print("Scraping complete!")


if __name__ == "__main__":
    main()
