# scraping/download_icons.py

import requests
from bs4 import BeautifulSoup
import time
import os

# Firebase is initialized by the main run_job.py script.
# We just need to import the storage module to use it.
from firebase_admin import storage

# --- Configuration ---
WEBPAGE_URL = (
    "https://thedigitalcrowns.com/all-icons-and-how-to-get-them-pokemon-tcg-pocket/"
)
PROFILE_ICONS_STORAGE_FOLDER = "profile_icons"


# --- Main Job Function ---
def run_icon_scrape():
    """
    Scrapes icon URLs and uploads them to Firebase Storage.
    This is the main entry point for the icon scraping job.
    """
    # Get the storage bucket client inside the function
    bucket_storage = storage.bucket()

    print(f"\n--- Starting Profile Icon Scrape from: {WEBPAGE_URL} ---")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        }
        response = requests.get(WEBPAGE_URL, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the webpage {WEBPAGE_URL}: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    figure_block = soup.find("figure", class_="wp-block-table")

    if not figure_block:
        print(
            "Error: Could not find the specific figure block containing the icons table."
        )
        return

    icon_table = figure_block.find("table", class_="has-fixed-layout")
    if not icon_table:
        print("Error: Could not find the icons table on the webpage.")
        return

    icon_data = []
    for row in icon_table.find_all("tr")[1:]:
        td_elements = row.find_all("td")
        if len(td_elements) > 0:
            icon_td = td_elements[0]
            img_tag = icon_td.find("img", {"data-lazy-src": True})
            label_text = ""
            for content in icon_td.contents:
                if content.name is None and str(content).strip():
                    label_text = str(content).strip()
                    break
            if img_tag and img_tag.get("data-lazy-src"):
                image_url = img_tag["data-lazy-src"]
                icon_data.append({"url": image_url, "label": label_text})

    if not icon_data:
        print("No icons found on the webpage with 'data-lazy-src' attribute.")
        return

    icon_data.reverse()
    uploaded_count, skipped_count, failed_count = 0, 0, 0

    for i, icon in enumerate(icon_data):
        original_url = icon["url"]
        icon_label = icon["label"]
        destination_filename = f"_{i + 1}.png"
        destination_blob_path = f"{PROFILE_ICONS_STORAGE_FOLDER}/{destination_filename}"
        blob = bucket_storage.blob(destination_blob_path)

        if blob.exists():
            skipped_count += 1
            continue

        print(f"Downloading and uploading {destination_filename} ({icon_label})...")
        try:
            img_response = requests.get(original_url, stream=True, timeout=10)
            img_response.raise_for_status()
            content_type = img_response.headers.get("content-type", "image/png")
            if "image/" not in content_type:
                content_type = "image/png"

            blob.upload_from_string(img_response.content, content_type=content_type)
            blob.make_public()
            uploaded_count += 1
            print(f"Successfully uploaded {destination_filename} for {icon_label}.")
        except requests.exceptions.RequestException as e:
            print(f"Failed to download {original_url} for {icon_label}: {e}")
            failed_count += 1
        except Exception as e:
            print(f"Failed to upload {destination_filename} for {icon_label}: {e}")
            failed_count += 1
        time.sleep(0.1)

    print("\n--- Profile Icon Scrape Summary ---")
    print(f"New Icons Uploaded: {uploaded_count}")
    print(f"Icons Skipped (Already Exist): {skipped_count}")
    print(f"Icons Failed to Process: {failed_count}")
    print("-----------------------------------")


if __name__ == "__main__":
    from shared_utils import initialize_firebase

    print("Running download_icons.py as a standalone script for local testing...")
    initialize_firebase()
    run_icon_scrape()
    print("\nScript finished.")
