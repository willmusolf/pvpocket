# main.py

import os
from flask import Flask, request
from firebase_admin import firestore
import requests
import hashlib

# Import your checker logic from the scraper script
from scraping.scraper import get_card_sets, get_drive_service, GOOGLE_DRIVE_FOLDER_ID

# Initialize Flask app
app = Flask(__name__)

# --- Re-initialize clients needed for the function ---
# Note: Firebase is initialized by the gunicorn server environment
db = firestore.client()
run_client = None  # We will initialize this only when needed to avoid import issues


# --- Helper Functions ---
def _trigger_cloud_run_job(job_type_to_run: str):
    # Late import and initialization to ensure it works in the server context
    from google.cloud import run_v2

    global run_client
    if run_client is None:
        run_client = run_v2.JobsClient()

    project_id = os.environ.get("GCP_PROJECT_ID", "pvpocket-dd286")
    region = os.environ.get("GCP_REGION", "us-central1")
    job_name = "pvpocket-job"

    print(f"Change detected. Triggering '{job_name}' with JOB_TYPE={job_type_to_run}.")
    job_path = run_client.job_path(project_id, region, job_name)

    overrides = run_v2.RunJobRequest.Overrides(
        container_overrides=[
            run_v2.RunJobRequest.Overrides.ContainerOverride(
                env=[{"name": "JOB_TYPE", "value": job_type_to_run}]
            )
        ]
    )
    request = run_v2.RunJobRequest(name=job_path, overrides=overrides)
    run_client.run_job(request=request)
    print("Job triggered successfully.")


# In main.py, replace the _check_limitless_sets function


def _check_limitless_sets():
    print("Checking for new sets on Limitless TCG...")
    try:
        config_ref = db.collection("internal_config").document("sets_tracker")

        website_set_codes = {s[1] for s in get_card_sets()}
        if not website_set_codes:
            print(
                "Warning: Received empty set list from get_card_sets(). Aborting check."
            )
            return

        known_set_codes = set(config_ref.get().to_dict().get("known_codes", []))

        if website_set_codes != known_set_codes:
            _trigger_cloud_run_job("scrape_sets")
            config_ref.set({"known_codes": list(website_set_codes)})
        else:
            print("No new sets found.")

    except Exception as e:
        # If any error occurs, log it instead of crashing the function
        print(f"ERROR: An exception occurred while checking sets: {e}")


def _check_google_drive():
    print("Checking for new images in Google Drive...")
    config_ref = db.collection("internal_config").document("drive_tracker")
    drive_service = get_drive_service()
    query = f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed=false"
    files = (
        drive_service.files()
        .list(q=query, fields="files(id, name)")
        .execute()
        .get("files", [])
    )
    current_file_count = len(files)
    known_file_count = config_ref.get().to_dict().get("file_count", 0)
    if current_file_count != known_file_count:
        _trigger_cloud_run_job("migrate_images")
        config_ref.set({"file_count": current_file_count})


def _check_icon_page():
    print("Checking for updates on icon source page...")
    config_ref = db.collection("internal_config").document("icon_page_tracker")
    url = (
        "https://thedigitalcrowns.com/all-icons-and-how-to-get-them-pokemon-tcg-pocket/"
    )
    response = requests.get(url, timeout=15)
    current_hash = hashlib.sha256(response.content).hexdigest()
    known_hash = config_ref.get().to_dict().get("page_hash", "")
    if current_hash != known_hash:
        _trigger_cloud_run_job("scrape_icons")
        config_ref.set({"page_hash": current_hash})

@app.route("/", methods=["POST"])
def main(request):
    """Cloud Function entry point. Handles both scheduled and direct triggers."""
    envelope = request.get_json()
    if not envelope:
        print("ERROR: Invalid request, no JSON body received.")
        return "ERROR: Invalid request.", 400

    data = {}
    # This block handles data from both a real scheduler run and a manual test run
    if "data" in envelope:
        payload = envelope["data"]
        if isinstance(payload, str):
            # This is a real scheduler run, data is a base64 string
            import base64
            import json

            data = json.loads(base64.b64decode(payload).decode("utf-8"))
        elif isinstance(payload, dict):
            # This is a test run ("Force run"), data is already a dict
            data = payload
    else:
        # This is a direct test call (e.g. from gcloud functions call)
        data = envelope

    check_type = data.get("CHECK_TYPE")
    print(f"--- Running checker for: {check_type} ---")

    if check_type == "limitless_sets":
        _check_limitless_sets()
    elif check_type == "google_drive":
        _check_google_drive()
    elif check_type == "icon_page":
        _check_icon_page()
    else:
        print(f"ERROR: Unknown CHECK_TYPE '{check_type}'.")
        return f"ERROR: Unknown CHECK_TYPE '{check_type}'.", 400

    return "Check complete.", 200
