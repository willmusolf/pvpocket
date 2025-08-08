import requests
from bs4 import BeautifulSoup
import time
import re
import os
from urllib.parse import urlparse
from typing import Optional, List, Dict, Any
import io
import google.auth

# GCP and Firebase libraries will be initialized in the main job runner
from firebase_admin import firestore, storage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

try:
    # This style works when run as part of the cloud job
    from .post_processor import main_post_process
except ImportError:
    # This style works when run as a standalone script locally
    from post_processor import main_post_process


# --- Configuration ---
# These constants remain as they are specific to the scraper's logic
GOOGLE_DRIVE_FOLDER_ID = "1-JIeAcBXoRn1r_SFgoqO8ZG2KPp2ss9U"
GDRIVE_CREDENTIALS_PATH = (
    "credentials.json"  # Ensure this file is in your project root or accessible
)
STORAGE_BASE_PATH = "high_res_cards"
SCRAPE_ONLY_NEW_CARDS = True


# --- Helper Functions (Sanitize, Clean Text, etc.) ---
# These functions are used by the scraper and remain unchanged.
def sanitize_for_firestore_id(text: str) -> str:
    if not text:
        return "unknown"
    text = text.replace(" ", "_")
    text = re.sub(r"[\[\]*~/.:\'()\"]", "", text)
    text = text.replace("/", "_")
    text = text.replace("-", "_")
    if not text:
        return "sanitized_empty"
    max_len = 100
    if len(text) > max_len:
        text = text[:max_len]
    return text


def clean_rules_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    cleaned_text = text.replace("<br>", "\n")
    cleaned_text = re.sub(r"\[\s*(.*?)\s*\]", r"[\1]", cleaned_text)
    cleaned_text = re.sub(r"\s*\n\s*(\[[A-Za-z]+\])", r" \1", cleaned_text)
    cleaned_text = re.sub(r"(\[[A-Za-z]+\])\s*\n\s*", r"\1 ", cleaned_text)
    cleaned_text = re.sub(r"(?<!\s)(\[[A-Za-z]+\])", r" \1", cleaned_text)
    cleaned_text = re.sub(r"(\[[A-Za-z]+\])(?!\s)", r"\1 ", cleaned_text)
    cleaned_text = re.sub(r"\n+", "\n", cleaned_text)
    cleaned_text = re.sub(r"[ \t]+", " ", cleaned_text)
    cleaned_text = cleaned_text.strip()
    if not cleaned_text:
        return None
    lines = cleaned_text.splitlines()
    processed_lines = [line.strip() for line in lines if line.strip()]
    if not processed_lines:
        return None
    final_text = "\n".join(processed_lines)
    final_text = re.sub(r":\n([^\n])", r": \1", final_text)
    final_text = re.sub(r":\n$", ":", final_text)
    return final_text if final_text else None


# --- Core Scraping and Data Handling Functions ---


def upload_image_to_firebase_storage(
    image_url_source: str,
    set_code: str,
    card_number_str: str,
    original_set_name_from_scrape: str,
) -> Optional[str]:
    if not image_url_source:
        return None
    try:
        bucket_storage = storage.bucket()
        folder_base_name = re.sub(
            r"\s*\([A-Za-z0-9\-]+\)\s*$", "", original_set_name_from_scrape
        ).strip()
        if not folder_base_name:
            folder_base_name = set_code

        safe_set_folder = (
            folder_base_name.lower()
            .replace(" ", "-")
            .replace("'", "")
            .replace(":", "")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
        )
        parsed_source_url = urlparse(image_url_source)
        source_path = parsed_source_url.path
        ext = os.path.splitext(source_path)[1]
        if not ext or ext.lower() not in [".png", ".jpg", ".jpeg", ".webp"]:
            if ".png" in image_url_source.lower():
                ext = ".png"
            elif ".webp" in image_url_source.lower():
                ext = ".webp"
            elif (
                ".jpg" in image_url_source.lower()
                or ".jpeg" in image_url_source.lower()
            ):
                ext = ".jpg"
            else:
                ext = ".webp"

        destination_blob_name = f"cards/{safe_set_folder}/{card_number_str}"
        blob = bucket_storage.blob(destination_blob_name)
        response = requests.get(image_url_source, stream=True, timeout=20)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "application/octet-stream")
        if "image/png" in content_type:
            content_type = "image/png"
        elif "image/jpeg" in content_type:
            content_type = "image/jpeg"
        elif "image/webp" in content_type:
            content_type = "image/webp"
        else:
            if ext == ".png":
                content_type = "image/png"
            elif ext == ".jpg" or ext == ".jpeg":
                content_type = "image/jpeg"
            elif ext == ".webp":
                content_type = "image/webp"
        blob.upload_from_string(response.content, content_type=content_type)
        blob.make_public()
        return blob.public_url
    except requests.RequestException:
        return None
    except Exception:
        return None


def get_current_max_card_id(db: firestore.client) -> int:
    print("Determining current maximum global card ID from Firestore...")
    max_id_found = 0
    try:
        sets_collection_ref = db.collection("cards")
        set_docs_stream = sets_collection_ref.stream()
        for set_doc in set_docs_stream:
            cards_subcollection_ref = set_doc.reference.collection("set_cards")
            id_query = (
                cards_subcollection_ref.order_by(
                    "id", direction=firestore.Query.DESCENDING
                )
                .limit(1)
                .stream()
            )
            for card_doc_snapshot in id_query:
                if card_doc_snapshot.exists and "id" in card_doc_snapshot.to_dict():
                    current_card_id = card_doc_snapshot.to_dict()["id"]
                    if (
                        isinstance(current_card_id, int)
                        and current_card_id > max_id_found
                    ):
                        max_id_found = current_card_id
        print(f"Current maximum global card ID found in Firestore: {max_id_found}")
        return max_id_found
    except Exception as e:
        print(f"Error determining max global card ID: {e}. Starting IDs from 0.")
        return 0


def get_current_max_set_release_order(db: firestore.client) -> int:
    """Get the highest release_order value from all sets in Firestore."""
    print("Determining current maximum set release_order from Firestore...")
    max_order = 0
    try:
        sets_query = (
            db.collection("cards")
            .order_by("release_order", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        for set_doc in sets_query:
            if set_doc.exists:
                set_data = set_doc.to_dict()
                current_order = set_data.get("release_order", 0)
                if isinstance(current_order, int) and current_order > max_order:
                    max_order = current_order
        print(f"Current maximum set release_order found: {max_order}")
        return max_order
    except Exception as e:
        # If release_order field doesn't exist yet, that's ok
        print(f"Note: release_order field may not exist yet. Starting from 0.")
        return 0


def save_card_to_firestore(
    card_data_dict: Dict[str, Any], id_counter: int
) -> tuple[bool, int]:
    db_firestore = firestore.client()
    if (
        not card_data_dict
        or not card_data_dict.get("set_code")
        or not card_data_dict.get("card_number_str")
        or not card_data_dict.get("name")
        or not card_data_dict.get("set_name")
    ):
        print(f"Error: Insufficient data. Card data: {card_data_dict}")
        return False, id_counter

    set_name_original = card_data_dict["set_name"]
    card_name_original = card_data_dict["name"]
    set_code = card_data_dict["set_code"]
    card_number_str_val = card_data_dict["card_number_str"]
    original_image_url = card_data_dict.get("original_image_url")
    raw_set_name_for_image_path = card_data_dict.get("raw_set_name_for_image_path")

    sanitized_set_name_for_doc_id = sanitize_for_firestore_id(set_name_original)
    sanitized_card_name_for_doc_id = sanitize_for_firestore_id(card_name_original)
    card_doc_id = (
        f"{sanitized_card_name_for_doc_id}_{set_code}_{card_number_str_val}".replace(
            "/", "_"
        )
    )

    set_doc_ref = db_firestore.collection("cards").document(
        sanitized_set_name_for_doc_id
    )
    card_specific_ref = set_doc_ref.collection("set_cards").document(card_doc_id)
    full_card_path = f"cards/{sanitized_set_name_for_doc_id}/set_cards/{card_doc_id}"

    try:
        existing_card_doc_snapshot = card_specific_ref.get()

        if SCRAPE_ONLY_NEW_CARDS and existing_card_doc_snapshot.exists:
            return False, id_counter

        if not existing_card_doc_snapshot.exists or not SCRAPE_ONLY_NEW_CARDS:
            if original_image_url and raw_set_name_for_image_path:
                card_data_dict["firebase_image_url"] = upload_image_to_firebase_storage(
                    original_image_url,
                    set_code,
                    card_number_str_val,
                    raw_set_name_for_image_path,
                )
            elif "firebase_image_url" not in card_data_dict:
                card_data_dict["firebase_image_url"] = None

        card_data_dict.pop("raw_set_name_for_image_path", None)

        if not existing_card_doc_snapshot.exists:
            id_counter += 1
            assigned_id = id_counter
            card_data_dict["id"] = assigned_id

            # Check if this set already has a release_order
            existing_set = set_doc_ref.get()
            if existing_set.exists and "release_order" in existing_set.to_dict():
                # Set already has release_order, just update name/code
                set_doc_data = {"set_name": set_name_original, "set_code": set_code}
            else:
                # New set or missing release_order - assign the next highest number
                db_firestore = firestore.client()
                max_order = get_current_max_set_release_order(db_firestore)
                set_doc_data = {
                    "set_name": set_name_original, 
                    "set_code": set_code,
                    "release_order": max_order + 1
                }
                print(f"Assigning release_order {max_order + 1} to new set: {set_name_original}")
            set_doc_ref.set(set_doc_data, merge=True)
            card_specific_ref.set(card_data_dict)
            print(
                f"CREATED: {card_name_original} ({set_code} {card_number_str_val}) ID: {assigned_id}"
            )
            return True, id_counter
        else:
            if "id" in card_data_dict:
                del card_data_dict["id"]
            # Check if this set already has a release_order
            existing_set = set_doc_ref.get()
            if existing_set.exists and "release_order" in existing_set.to_dict():
                # Set already has release_order, just update name/code
                set_doc_data = {"set_name": set_name_original, "set_code": set_code}
            else:
                # New set or missing release_order - assign the next highest number
                db_firestore = firestore.client()
                max_order = get_current_max_set_release_order(db_firestore)
                set_doc_data = {
                    "set_name": set_name_original, 
                    "set_code": set_code,
                    "release_order": max_order + 1
                }
                print(f"Assigning release_order {max_order + 1} to new set: {set_name_original}")
            set_doc_ref.set(set_doc_data, merge=True)
            card_specific_ref.set(card_data_dict, merge=True)
            print(f"UPDATED: {card_name_original} ({set_code} {card_number_str_val})")
            return True, id_counter
    except Exception as e:
        print(f"Error saving/updating {full_card_path}: {e}")
        return False, id_counter


def get_card_sets() -> list:
    url = "https://pocket.limitlesstcg.com/cards"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching card sets: {e}")
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    sets = []
    for link_tag in soup.select("a[href^='/cards/']"):
        href = link_tag["href"]
        if href.count("/") == 2:
            set_code = href.split("/")[-1]
            set_name = " ".join(link_tag.text.split()).strip()
            if (
                not set_name
                or set_name.isspace()
                or re.match(r"^\d{1,2} \w{3,} \d{2}$", set_name)
                or set_name.isdigit()
            ):
                continue
            sets.append((set_name, set_code))
    return sets


def get_cards_from_set(set_code: str) -> list:
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
        if href.count("/") == 3:
            card_number = href.split("/")[-1]
            card_numbers.append(card_number)
    return card_numbers


def scrape_card_details(
    set_code: str, card_number_str_arg: str
) -> Optional[Dict[str, Any]]:
    url = f"https://pocket.limitlesstcg.com/cards/{set_code}/{card_number_str_arg}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching details URL for {set_code}-{card_number_str_arg}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    card_data = {}
    try:
        name_element = soup.select_one(".card-text .card-text-name")
        if not name_element:
            return None
        card_data["name"] = " ".join(name_element.text.split()).strip()

        set_name_el = soup.select_one(".prints-current-details span.text-lg")
        raw_set_name_for_image_path = "unknown-set"
        if set_name_el:
            raw_set_name_for_image_path = " ".join(set_name_el.text.split()).strip()
            card_data["set_name"] = re.sub(
                r"\s*\([A-Za-z0-9\-]+\)\s*$", "", raw_set_name_for_image_path
            ).strip()
            if not card_data["set_name"]:
                card_data["set_name"] = set_code
        else:
            card_data["set_name"] = "Unknown Set"

        card_data["set_code"] = set_code
        card_data["card_number_str"] = card_number_str_arg
        card_data["raw_set_name_for_image_path"] = raw_set_name_for_image_path
        card_data["firebase_image_url"] = None
        card_type_el = soup.select_one(".card-text .card-text-type")
        card_data["card_type"] = (
            " ".join(card_type_el.text.split()).strip()
            if card_type_el
            else "Unknown Type"
        )
        energy_type_val, hp_val = "", None
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
                    energy_type_val = etype
                    break
            hp_match = re.search(r"(\d+)\s*HP", title_text)
            if hp_match:
                hp_val = int(hp_match.group(1))
        card_data["energy_type"], card_data["hp"] = energy_type_val, hp_val
        rarity_val, pack_val = "", ""
        rarity_pack_el = soup.select_one(".prints-current-details span:not(.text-lg)")
        if rarity_pack_el:
            parts = rarity_pack_el.get_text("·", strip=True).split("·")
            if len(parts) >= 2:
                rarity_val = parts[1].strip()
            if len(parts) >= 3:
                pack_text = parts[2].strip()
                pack_val = (
                    re.sub(r"(?i)\s*pack\s*", "", pack_text)
                    if "pack" in pack_text.lower()
                    else pack_text
                )
        card_data["rarity"], card_data["pack"] = rarity_val, pack_val
        weakness_val, retreat_cost_val = None, None
        if "Pokémon" in card_data["card_type"]:
            wrr_el = soup.select_one(".card-text-wrr")
            if wrr_el:
                wrr_text = wrr_el.get_text()
                weak_match = re.search(
                    r"Weakness:\s*([A-Za-z]+(?:[\s×x+]\d+)?)", wrr_text
                )
                if weak_match:
                    weakness_val = weak_match.group(1).strip()
                retreat_match = re.search(r"Retreat:\s*(\d+)", wrr_text)
                if retreat_match:
                    retreat_cost_val = int(retreat_match.group(1))
        card_data["weakness"], card_data["retreat_cost"] = (
            weakness_val,
            retreat_cost_val,
        )
        artist_el = soup.select_one(".card-text-artist")
        illustrator_val = None
        if artist_el:
            artist_text = artist_el.text.strip()
            if "Illustrated by" in artist_text:
                parts = artist_text.split("Illustrated by", 1)
                if len(parts) > 1:
                    illustrator_val = parts[1].strip()
            elif "illustrator:" in artist_text.lower():
                parts = re.split(
                    r"illustrator:", artist_text, maxsplit=1, flags=re.IGNORECASE
                )
                if len(parts) > 1:
                    illustrator_val = parts[1].strip().title()
            else:
                illustrator_val = artist_text
            if illustrator_val:
                illustrator_val = " ".join(illustrator_val.split())
        card_data["illustrator"] = illustrator_val
        flavor_el = soup.select_one(".card-text-flavor")
        card_data["flavor_text"] = (
            clean_rules_text(flavor_el.get_text()) if flavor_el else None
        )

        img_el = soup.select_one(".card-image img")
        image_url = img_el["src"] if img_el and img_el.has_attr("src") else ""
        card_data["original_image_url"] = image_url

        scraped_attacks_data, scraped_abilities_list_of_dicts = [], []
        if "Pokémon" in card_data["card_type"]:
            ability_elements = soup.select(".card-text-ability")
            for ab_el in ability_elements:
                raw_ability_text_block = ab_el.get_text(separator="\n").strip()
                cleaned_ability_block = clean_rules_text(raw_ability_text_block)
                if cleaned_ability_block:
                    ability_obj = {"name": "", "text": cleaned_ability_block}
                    lines = cleaned_ability_block.split("\n", 1)
                    first_line = lines[0].strip()
                    if first_line.lower().startswith("ability:"):
                        ability_obj["name"] = first_line[len("Ability:") :].strip()
                        ability_obj["text"] = lines[1].strip() if len(lines) > 1 else ""
                    scraped_abilities_list_of_dicts.append(ability_obj)
            attack_elements = soup.select(".card-text-attack")
            for idx, atk_el in enumerate(attack_elements):
                atk_name, atk_dmg, atk_costs, atk_effect_raw_text = "", "0", [], ""
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
                if not atk_costs and atk_name:
                    cost_name_match = re.match(r"^([A-Z]+)\s+(.*)", atk_name)
                    if cost_name_match:
                        atk_costs.extend(list(cost_name_match.group(1)))
                        atk_name = cost_name_match.group(2).strip()
                if not atk_name and info_el:
                    atk_name = info_el.get_text(strip=True).split(" ")[0]
                effect_el = atk_el.select_one(".card-text-attack-effect")
                if effect_el:
                    atk_effect_raw_text = effect_el.get_text(separator="\n")
                scraped_attacks_data.append(
                    {
                        "name": atk_name if atk_name else f"Attack {idx + 1}",
                        "cost": atk_costs,
                        "damage": atk_dmg,
                        "effect": clean_rules_text(atk_effect_raw_text),
                    }
                )
        elif "Trainer" in card_data["card_type"] or (
            "Energy" in card_data["card_type"]
            and "Basic" not in card_data["card_type"]
            and card_data["name"]
            and "Basic" not in card_data["name"]
        ):
            main_text_div = soup.select_one(".card-text")
            if main_text_div:
                artist_div_to_remove = main_text_div.select_one(".card-text-artist")
                if artist_div_to_remove:
                    artist_div_to_remove.decompose()
                sections = main_text_div.select(":scope > div.card-text-section")
                trainer_rules_text_parts = []
                for sec in sections:
                    if not (
                        sec.select_one(
                            ".card-text-title, .card-text-type, .card-text-wrr, .card-text-flavor, .card-text-attack, .card-text-ability"
                        )
                    ):
                        raw_section_text = sec.get_text(separator="\n")
                        cleaned_section_text = clean_rules_text(raw_section_text)
                        if cleaned_section_text:
                            trainer_rules_text_parts.append(cleaned_section_text)
                if trainer_rules_text_parts:
                    scraped_abilities_list_of_dicts.append(
                        {"name": "", "text": "\n".join(trainer_rules_text_parts)}
                    )
        card_data["attacks"] = scraped_attacks_data
        card_data["abilities"] = scraped_abilities_list_of_dicts
        return card_data
    except Exception as e:
        print(
            f"Error during card detail scrape for {set_code}-{card_number_str_arg}: {e}"
        )
        return None


def generate_set_map_from_firestore(db_client):
    print("Generating set map from Firestore 'cards' collection...")
    if not db_client:
        return None
    final_set_map = {}
    try:
        sets_ref = db_client.collection("cards").stream()
        for set_doc in sets_ref:
            set_data = set_doc.to_dict()
            set_code, set_name = set_data.get("set_code"), set_data.get("set_name")
            if set_code and set_name:
                folder_base_name = re.sub(
                    r"\s*\([A-Za-z0-9\-]+\)\s*$", "", set_name
                ).strip()
                safe_folder_name = (
                    folder_base_name.lower()
                    .replace(" ", "-")
                    .replace("'", "")
                    .replace(":", "")
                    .replace(",", "")
                    .replace("(", "")
                    .replace(")", "")
                )
                safe_folder_name = safe_folder_name.replace(f"-{set_code.lower()}", "")
                final_set_map[set_code] = safe_folder_name
        print(
            f"✅ Successfully generated map for {len(final_set_map)} sets from Firestore."
        )
        return final_set_map
    except Exception as e:
        print(f"❌ Error reading from Firestore to generate set map: {e}")
        return None


def get_drive_service():
    """Authenticates with Google Drive using the application's default credentials."""
    import google.auth
    from googleapiclient.discovery import build

    print("Authenticating to Google Drive using the default service account...")
    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
    
    # This automatically finds the service account credentials in the cloud
    creds, _ = google.auth.default(scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


# --- Main Logic Functions for Jobs ---


def run_set_scrape_and_post_process():
    """
    Main job for scraping new sets from LimitlessTCG, saving them,
    and then running the post-processor to apply special rules.
    """
    db = firestore.client()

    print("--- Starting Set Scrape & Post-Process Job ---")
    if SCRAPE_ONLY_NEW_CARDS:
        print("Scraping only new cards (will not update existing cards).")
    else:
        print("WARNING: Will add new cards and update existing ones.")

    current_global_card_id_counter = get_current_max_card_id(db)
    print(f"Starting global card ID counter at: {current_global_card_id_counter}")

    card_sets = get_card_sets()
    total_saved_or_updated_cards = 0

    for set_name_from_list, set_code in card_sets:
        print(f"\nProcessing Set: {set_name_from_list} ({set_code})")
        cards_in_current_set_numbers = get_cards_from_set(set_code)

        if not cards_in_current_set_numbers:
            print(f"No cards found for set {set_code}. Skipping.")
            continue

        # High-speed set check
        website_card_count = len(cards_in_current_set_numbers)
        firestore_card_count = 0
        
        # Special handling for promo set - always process to catch new cards
        if set_code == "P-A":
            print(f"⚡ Promo set (P-A) detected - always processing to catch new cards...")
            firestore_card_count = 0  # Force processing
        else:
            try:
                # Get the correct set document path
                sanitized_set_name = sanitize_for_firestore_id(set_name_from_list)
                set_doc_ref = db.collection("cards").document(sanitized_set_name)
                set_document = set_doc_ref.get()
                
                if set_document.exists:
                    firestore_card_count = set_document.to_dict().get("card_count", 0)
                    print(f"Found set document '{sanitized_set_name}' with {firestore_card_count} cards")
                else:
                    print(f"Set document '{sanitized_set_name}' not found - will process all cards")
            except Exception as e:
                print(f"Warning: Could not query Firestore for set count check: {e}")

        if firestore_card_count > 0 and firestore_card_count >= website_card_count:
            print(
                f"✅ Set is complete ({firestore_card_count}/{website_card_count} cards). Skipping."
            )
            continue

        print(
            f"Set has {firestore_card_count}/{website_card_count} cards. Proceeding..."
        )

        for i, card_num_str in enumerate(cards_in_current_set_numbers):
            time.sleep(0.1)  # Be kind to the server
            card_details_dict = scrape_card_details(set_code, card_num_str)

            if card_details_dict:
                saved, new_counter = save_card_to_firestore(
                    card_details_dict, current_global_card_id_counter
                )
                if saved:
                    total_saved_or_updated_cards += 1
                    current_global_card_id_counter = new_counter

    print(
        f"\nWEBSITE SCRAPING FINISHED. Total cards saved/updated: {total_saved_or_updated_cards}"
    )

    # After scraping, immediately run the post-processor
    print("\n========================================================")
    print("RUNNING POST-PROCESSING...")
    print("========================================================")
    main_post_process()


def run_image_migration():
    """
    Main job for migrating high-resolution images from Google Drive
    to Firebase Storage.
    """
    print("\n--- Starting High-Resolution Image Migration Job ---")
    db_client = firestore.client()
    bucket_client = storage.bucket()
    set_code_to_folder_map = generate_set_map_from_firestore(db_client)
    if not set_code_to_folder_map:
        print("❌ Image Scrape Aborted: Could not generate set map from Firestore.")
        return

    # Manual patch for promo set
    set_code_to_folder_map["P-A"] = "promo-a"

    try:
        drive_service = get_drive_service()
    except Exception as e:
        print(f"❌ CRITICAL Error initializing Google Drive service: {e}")
        return

    print(f"Fetching folders from Google Drive root '{GOOGLE_DRIVE_FOLDER_ID}'...")
    query = f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed=false and mimeType = 'application/vnd.google-apps.folder'"
    drive_folders = (
        drive_service.files()
        .list(q=query, pageSize=1000, fields="files(id, name)")
        .execute()
        .get("files", [])
    )

    total_uploaded, total_warnings, total_failures = 0, 0, 0

    for drive_folder in drive_folders:
        drive_folder_name, folder_id = drive_folder.get("name"), drive_folder.get("id")
        print(f"\nProcessing Drive folder: '{drive_folder_name}'...")

        firebase_folder_name_to_find = drive_folder_name.lower().replace(" ", "-")
        corresponding_set_code = next(
            (
                code
                for code, name in set_code_to_folder_map.items()
                if name in firebase_folder_name_to_find
            ),
            None,
        )

        if not corresponding_set_code:
            print(
                f"  ⚠️ Warning: No matching set for Drive folder '{drive_folder_name}'. Skipping."
            )
            total_warnings += 1
            continue

        firebase_set_folder_path = (
            f"{STORAGE_BASE_PATH}/{set_code_to_folder_map[corresponding_set_code]}/"
        )
        blobs_in_set = list(bucket_client.list_blobs(prefix=firebase_set_folder_path))
        files_in_drive_folder = (
            drive_service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed=false",
                pageSize=1000,
                fields="files(id, name)",
            )
            .execute()
            .get("files", [])
        )

        if files_in_drive_folder and len(blobs_in_set) >= len(files_in_drive_folder):
            print(
                f"  ✅ Set '{corresponding_set_code}' appears complete ({len(blobs_in_set)} images exist). Skipping folder."
            )
            continue

        print(
            f"  -> Found {len(files_in_drive_folder)} files in Drive. Checking against {len(blobs_in_set)} in Storage."
        )

        filename_prefix_to_match = corresponding_set_code.lower()
        if corresponding_set_code == "P-A":
            filename_prefix_to_match = "promo-a"

        dynamic_filename_regex = re.compile(
            f"^{re.escape(filename_prefix_to_match)}-(\\d+)\\..+", re.IGNORECASE
        )

        for file_item in files_in_drive_folder:
            file_name, file_id = file_item.get("name"), file_item.get("id")
            match = dynamic_filename_regex.match(file_name)

            if not match:
                total_warnings += 1
                continue

            card_number_str = str(int(match.group(1)))
            destination_blob_name = f"{STORAGE_BASE_PATH}/{set_code_to_folder_map[corresponding_set_code]}/{card_number_str}"
            blob = bucket_client.blob(destination_blob_name)

            if blob.exists():
                continue

            try:
                request = drive_service.files().get_media(fileId=file_id)
                file_content = io.BytesIO()
                downloader = MediaIoBaseDownload(file_content, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()

                file_content.seek(0)
                blob.upload_from_file(file_content, content_type="image/png")
                blob.make_public()
                total_uploaded += 1
                print(f"    -> Uploaded '{file_name}'")

            except Exception as e:
                print(f"    -> ❌ FAILED to process/upload '{file_name}': {e}")
                total_failures += 1

    print("\n" + "=" * 40)
    print("      HIGH-RES IMAGE SCRAPE SUMMARY")
    print("=" * 40)
    print(f"✅ New Images Uploaded: {total_uploaded}")
    print(f"⚠️ Warnings/Skipped:    {total_warnings}")
    print(f"❌ Upload Failures:       {total_failures}")
    print("=" * 40)

if __name__ == "__main__":
    import sys
    import os
    from dotenv import load_dotenv

    # Load environment variables from .env file
    load_dotenv()

    # This block of code only runs when you execute scraper.py directly
    print("Running scraper.py as a standalone script...")

    # This is a standard Python trick to allow the script to find the shared_utils.py file
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_root)

    from shared_utils import initialize_firebase

    # Check for a command-line argument
    if len(sys.argv) < 2:
        print("Usage: python3 scraping/scraper.py [sets|images]")
        sys.exit(1)

    choice = sys.argv[1]

    print(f"Running scraper.py as a standalone script for: {choice}")

    # Initialize Firebase before running any function
    initialize_firebase()

    if choice == "sets":
        run_set_scrape_and_post_process()
    elif choice == "images":
        run_image_migration()
    else:
        print(f"Error: Invalid choice '{choice}'. Please use 'sets' or 'images'.")
        sys.exit(1)

    print("\nStandalone script finished.")
