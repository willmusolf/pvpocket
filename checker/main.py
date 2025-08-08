import os
import json
import base64
import requests
import firebase_admin
from firebase_admin import firestore
from google.cloud import run_v2

# New imports for Google Drive API
import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# --- Client Initialization ---
db = None
run_client = None
drive_service = None 

# The main folder in Google Drive where you store all card set folders.
GOOGLE_DRIVE_ROOT_FOLDER_ID = "1-JIeAcBXoRn1r_SFgoqO8ZG2KPp2ss9U"


def _initialize_clients_if_needed():
    """Initializes clients if they haven't been already."""
    global db, run_client, drive_service
    if db is None:
        firebase_admin.initialize_app()
        db = firestore.client()
        run_client = run_v2.JobsClient()
        
        scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        creds, _ = google.auth.default(scopes=scopes)
        drive_service = build("drive", "v3", credentials=creds)


# --- Helper Functions ---
def _trigger_cloud_run_job(job_type_to_run: str):
    project_id = os.environ.get("GCP_PROJECT_ID", "pvpocket-dd286")
    job_name = "pvpocket-job"
    region = "us-central1"
    
    print(f"Change detected. Triggering '{job_name}' with JOB_TYPE={job_type_to_run}.")
    job_path = run_client.job_path(project_id, region, job_name)
    
    overrides = run_v2.RunJobRequest.Overrides(
        container_overrides=[run_v2.RunJobRequest.Overrides.ContainerOverride(
            env=[{"name": "JOB_TYPE", "value": job_type_to_run}]
        )]
    )
    request = run_v2.RunJobRequest(name=job_path, overrides=overrides)
    run_client.run_job(request=request)
    print("Job triggered successfully.")

def get_card_sets():
    url = "https://pocket.limitlesstcg.com/cards"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    from bs4 import BeautifulSoup
    import re
    soup = BeautifulSoup(response.text, "html.parser")
    sets = []
    for link_tag in soup.select("a[href^='/cards/']"):
        href = link_tag["href"]
        if href.count("/") == 2:
            set_code = href.split("/")[-1]
            set_name = " ".join(link_tag.text.split()).strip()
            if (not set_name or set_name.isspace() or re.match(r"^\d{1,2} \w{3,} \d{2}$", set_name) or set_name.isdigit()):
                continue
            sets.append((set_name, set_code))
    return sets

def get_cards_from_set(set_code: str) -> list:
    """Get list of card numbers from a set page."""
    url = f"https://pocket.limitlesstcg.com/cards/{set_code}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        cards_in_set = []
        for link_tag in soup.select(f"a[href^='/cards/{set_code}/']"):
            card_number_str = link_tag["href"].split("/")[-1]
            cards_in_set.append(card_number_str)
        return cards_in_set
    except Exception as e:
        print(f"Error fetching cards from set {set_code}: {e}")
        return []

def _check_limitless_sets():
    print("Checking for new sets and card count changes on LimitlessTCG...")
    try:
        config_ref = db.collection("internal_config").document("sets_tracker")
        website_sets = get_card_sets()  # Returns [(name, code), ...]
        doc = config_ref.get()
        stored_data = doc.to_dict() if doc.exists else {}
        
        known_set_codes = set(stored_data.get("known_codes", []))
        known_set_counts = stored_data.get("set_card_counts", {})
        
        website_set_codes = {s[1] for s in website_sets}
        current_set_counts = {}
        changes_detected = False
        
        # Check each set for new sets or card count changes
        for set_name, set_code in website_sets:
            cards_in_set = get_cards_from_set(set_code)
            current_card_count = len(cards_in_set)
            current_set_counts[set_code] = current_card_count
            
            # Check for new sets
            if set_code not in known_set_codes:
                print(f"  -> NEW SET DETECTED: {set_name} ({set_code}) with {current_card_count} cards")
                changes_detected = True
            else:
                # Check for card count changes in existing sets
                known_card_count = known_set_counts.get(set_code, 0)
                if current_card_count > known_card_count:
                    print(f"  -> CARD COUNT INCREASE: {set_name} ({set_code}) from {known_card_count} to {current_card_count} cards")
                    changes_detected = True
                elif current_card_count < known_card_count:
                    print(f"  -> CARD COUNT DECREASE: {set_name} ({set_code}) from {known_card_count} to {current_card_count} cards")
                    changes_detected = True
        
        # Special focus on promo set
        promo_count = current_set_counts.get("P-A", 0)
        known_promo_count = known_set_counts.get("P-A", 0)
        if promo_count != known_promo_count:
            print(f"  -> PROMO SET CHANGE: P-A cards changed from {known_promo_count} to {promo_count}")
            changes_detected = True
            
        if changes_detected:
            print("Changes detected - triggering scraping job...")
            _trigger_cloud_run_job("scrape_sets")
            # Update stored data
            config_ref.set({
                "known_codes": list(website_set_codes),
                "set_card_counts": current_set_counts,
                "last_checked": db.SERVER_TIMESTAMP
            })
        else:
            print("No changes detected in sets or card counts.")
    except Exception as e:
        print(f"ERROR: An exception occurred while checking sets: {e}")
        
def _check_google_drive():
    """
    Checks each folder in Google Drive against a stored map of file counts
    in Firestore. Triggers a job if any folder's file count has changed.
    """
    print("Running intelligent Drive check (v3)...")
    try:
        # 1. Get the last known state of all folders from Firestore
        config_ref = db.collection("internal_config").document("drive_tracker")
        doc = config_ref.get()
        known_folder_states = doc.to_dict() if doc.exists else {}

        # 2. Get the current list of all set folders from Drive
        all_folders = []
        page_token = None
        while True:
            query = f"'{GOOGLE_DRIVE_ROOT_FOLDER_ID}' in parents and trashed=false and mimeType = 'application/vnd.google-apps.folder'"
            response = drive_service.files().list(q=query, pageToken=page_token, fields="nextPageToken, files(id, name)").execute()
            all_folders.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        
        # 3. Check each folder for changes and build the new state
        should_trigger_job = False
        current_folder_states = {}

        for folder in all_folders:
            folder_id = folder.get("id")
            folder_name = folder.get("name")
            
            # Count files in the current folder (with pagination)
            file_count = 0
            page_token_files = None
            while True:
                query_files = f"'{folder_id}' in parents and trashed=false"
                response_files = drive_service.files().list(q=query_files, pageToken=page_token_files, pageSize=1000, fields="nextPageToken, files(id)").execute()
                file_count += len(response_files.get("files", []))
                page_token_files = response_files.get("nextPageToken")
                if not page_token_files:
                    break
            
            # Record the current state
            current_folder_states[folder_name] = {"file_count": file_count}
            
            # Compare with the known state
            last_known_count = known_folder_states.get(folder_name, {}).get("file_count", -1) # Use -1 to detect new folders
            if file_count != last_known_count:
                print(f"  -> CHANGE DETECTED in folder '{folder_name}': count changed from {last_known_count} to {file_count}.")
                should_trigger_job = True

        # Also check if a folder was deleted
        if len(known_folder_states) != len(current_folder_states):
             print(f"  -> CHANGE DETECTED: Number of folders changed from {len(known_folder_states)} to {len(current_folder_states)}.")
             should_trigger_job = True

        # 4. Trigger job and update Firestore if any change was found
        if should_trigger_job:
            _trigger_cloud_run_job("scrape_images")
            config_ref.set(current_folder_states)
        else:
            print("No changes found in any Drive folders.")

    except HttpError as e:
        print(f"ERROR: A Google Drive API error occurred: {e}")
    except Exception as e:
        print(f"ERROR: An exception occurred while checking Google Drive: {e}")

# --- Main Entry Point for the Function ---
def pvpocket_checker(request):
    """This is the function that Cloud Scheduler will trigger."""
    _initialize_clients_if_needed()
    
    envelope = request.get_json(silent=True) or request.args
    check_type = envelope.get("CHECK_TYPE")

    if check_type == "limitless_sets":
        _check_limitless_sets()
    elif check_type == "google_drive":
        _check_google_drive()
    else:
        # If no specific type is requested, run all checks by default.
        print("No CHECK_TYPE specified, running all default checks.")
        _check_limitless_sets()
        _check_google_drive()
    
    return "Checks complete.", 200