import requests
from bs4 import BeautifulSoup
import time
import os
import re  # For cleaning up text if needed later, though not heavily used for icons themselves
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from a .env file if it exists

import firebase_admin
from firebase_admin import credentials, storage

# --- Configuration ---
# The URL of the webpage containing the icons
WEBPAGE_URL = (
    "https://thedigitalcrowns.com/all-icons-and-how-to-get-them-pokemon-tcg-pocket/"
)

# Your Firebase Storage Bucket Name
# As inferred from your previous Flask app config (e.g., pvpocket-dd286.appspot.com)
FIREBASE_STORAGE_BUCKET_NAME = "pvpocket-dd286.firebasestorage.app"

# The folder within your Firebase Storage bucket where icons will be uploaded
PROFILE_ICONS_STORAGE_FOLDER = "profile_icons"


# --- Firebase Initialization ---
def initialize_firebase():
    """
    Initializes Firebase Admin SDK.
    It attempts to use Application Default Credentials, which is recommended
    for environments like Google Cloud or when GOOGLE_APPLICATION_CREDENTIALS
    environment variable is set locally.
    """
    if not firebase_admin._apps:
        try:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(
                cred, {"storageBucket": FIREBASE_STORAGE_BUCKET_NAME}
            )
            print(
                "Firebase initialized successfully with Application Default Credentials."
            )
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to initialize Firebase Admin SDK: {e}")
            print(
                "Please ensure GOOGLE_APPLICATION_CREDENTIALS environment variable is set"
            )
            print("and points to your Firebase service account key JSON file.")
            exit(1)  # Exit if Firebase cannot be initialized


# Global Firebase Storage bucket client after initialization
bucket_storage = None


# --- Icon Scraping and Upload Logic ---
def scrape_and_upload_profile_icons():
    """
    Scrapes icon URLs from the specified webpage, and uploads them to Firebase Storage,
    only adding new ones if they don't already exist.
    """
    print(f"\n--- Starting Profile Icon Scrape from: {WEBPAGE_URL} ---")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        response = requests.get(WEBPAGE_URL, headers=headers, timeout=15)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
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
    # Iterate through table rows, skipping the header row
    for row in icon_table.find_all("tr")[1:]:
        # Each row should have two <td> elements based on the provided HTML
        td_elements = row.find_all("td")
        if len(td_elements) > 0:
            icon_td = td_elements[0]

            # Find the img tag that has data-lazy-src
            img_tag = icon_td.find("img", {"data-lazy-src": True})

            # The label text is usually immediately after the <noscript> or <img> tag
            # We look for <br>Gladion, so we can split by <br> and take the last part
            label_text = ""
            for content in icon_td.contents:
                if (
                    content.name is None and str(content).strip()
                ):  # It's a NavigableString (text)
                    label_text = str(content).strip()
                    break  # Take the first significant text node

            if img_tag and img_tag.get("data-lazy-src"):
                image_url = img_tag["data-lazy-src"]
                icon_data.append({"url": image_url, "label": label_text})

    if not icon_data:
        print("No icons found on the webpage with 'data-lazy-src' attribute.")
        return

    # You want Giovanni as _1.png, Erika as _2.png, Snorlax as _3.png, etc.
    # Looking at the original HTML, Giovanni is last, Erika second last, Snorlax third last.
    # So, we need to reverse the order of the scraped icons to match your desired numbering.
    icon_data.reverse()

    uploaded_count = 0
    skipped_count = 0
    failed_count = 0

    global bucket_storage  # Use the global bucket client

    for i, icon in enumerate(icon_data):
        original_url = icon["url"]
        icon_label = icon["label"]

        # Construct the destination filename as _1.png, _2.png, etc.
        destination_filename = f"_{i + 1}.png"
        destination_blob_path = f"{PROFILE_ICONS_STORAGE_FOLDER}/{destination_filename}"

        blob = bucket_storage.blob(destination_blob_path)

        if blob.exists():
            print(
                f"Skipping {destination_filename} ({icon_label}): Already exists in Firebase Storage."
            )
            skipped_count += 1
            continue

        print(f"Downloading and uploading {destination_filename} ({icon_label})...")
        try:
            img_response = requests.get(original_url, stream=True, timeout=10)
            img_response.raise_for_status()  # Check for bad HTTP status codes

            # Determine content type (default to image/png as we're saving as .png)
            content_type = img_response.headers.get("content-type", "image/png")
            if "image/" not in content_type:  # Ensure it's an image type
                content_type = "image/png"  # Fallback if header is ambiguous

            # Upload the image content
            blob.upload_from_string(img_response.content, content_type=content_type)
            # Optionally, make the file publicly accessible. Your Flask app's URL structure
            # suggests they are publicly accessible with ?alt=media.
            # If you want a clean public URL, uncomment the next line:
            blob.make_public()
            print(f"Successfully uploaded {destination_filename} for {icon_label}.")
            uploaded_count += 1

        except requests.exceptions.RequestException as e:
            print(f"Failed to download {original_url} for {icon_label}: {e}")
            failed_count += 1
        except Exception as e:
            print(f"Failed to upload {destination_filename} for {icon_label}: {e}")
            failed_count += 1

        time.sleep(0.1)  # Be kind to the server

    print("\n--- Profile Icon Scrape Summary ---")
    print(f"Total Icons Found: {len(icon_data)}")
    print(f"New Icons Uploaded: {uploaded_count}")
    print(f"Icons Skipped (Already Exist): {skipped_count}")
    print(f"Icons Failed to Process: {failed_count}")
    print("-----------------------------------")


if __name__ == "__main__":
    initialize_firebase()
    # Assign the global bucket client after initialization
    bucket_storage = storage.bucket()

    scrape_and_upload_profile_icons()

    print("\nScript finished.")
