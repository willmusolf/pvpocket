import os
import json
import base64
import requests
import firebase_admin
from firebase_admin import firestore
from google.cloud import run_v2
import hashlib

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

def _generate_sets_hash(website_sets):
    """Generate a hash of all set data for efficient change detection."""
    # Sort sets for consistent hashing
    sorted_sets = sorted(website_sets, key=lambda x: x[1])  # Sort by set code
    
    # Create a simple string representation of all sets
    sets_string = "|".join([f"{name}:{code}" for name, code in sorted_sets])
    
    # Generate SHA256 hash
    return hashlib.sha256(sets_string.encode()).hexdigest()[:16]  # First 16 chars sufficient

def _check_limitless_sets_efficient():
    """Ultra-efficient set checker using hash-based change detection with redundant methods."""
    print("🔍 Enhanced check: Scanning LimitlessTCG for changes...")
    try:
        # 1. Get current website data (FREE - no Firestore ops)
        website_sets = get_card_sets()  # Returns [(name, code), ...]
        current_hash = _generate_sets_hash(website_sets)
        
        # 2. Get stored state (single Firestore read)
        config_ref = db.collection("internal_config").document("sets_hash_tracker")
        doc = config_ref.get()
        stored_data = doc.to_dict() if doc.exists else {}
        stored_hash = stored_data.get("sets_hash", "")
        stored_sets = stored_data.get("known_sets", [])
        stored_count = stored_data.get("sets_count", 0)
        
        print(f"   Current hash: {current_hash}")
        print(f"   Stored hash:  {stored_hash}")
        print(f"   Current sets: {len(website_sets)}, Stored: {stored_count}")
        
        # 3. Multi-layer change detection
        changes_detected = False
        change_reasons = []
        
        # Primary: Hash comparison (most efficient)
        if current_hash != stored_hash:
            changes_detected = True
            change_reasons.append(f"Hash changed: {stored_hash[:8]}... → {current_hash[:8]}...")
        
        # Secondary: Set count comparison (fast fallback)
        if len(website_sets) != stored_count:
            changes_detected = True
            change_reasons.append(f"Set count changed: {stored_count} → {len(website_sets)}")
        
        # Tertiary: New set detection (comprehensive fallback)
        current_set_codes = [code for name, code in website_sets]
        stored_set_codes = [item.get('code', '') for item in stored_sets]
        new_set_codes = [code for code in current_set_codes if code not in stored_set_codes]
        
        if new_set_codes:
            changes_detected = True
            change_reasons.append(f"New sets detected: {', '.join(new_set_codes)}")
        
        if not changes_detected:
            print("✅ No changes detected - skipping expensive operations")
            return
        
        # 4. Changes detected! Perform detailed analysis
        print("🚨 Changes detected - performing detailed analysis...")
        for reason in change_reasons:
            print(f"   📝 {reason}")
        
        # Analyze new sets in detail
        new_sets_info = []
        current_set_counts = {}
        
        for set_name, set_code in website_sets:
            cards_in_set = get_cards_from_set(set_code)
            current_card_count = len(cards_in_set)
            current_set_counts[set_code] = current_card_count
            
            # Check if this is a completely new set
            if set_code in new_set_codes:
                new_sets_info.append((set_name, set_code, current_card_count))
                print(f"  📦 NEW SET: {set_name} ({set_code}) - {current_card_count} cards")
        
        # Log what changed
        if not new_sets_info and changes_detected:
            print(f"  📊 Existing sets updated (card count changes or other modifications)")
        
        # 5. Trigger scraping and update state (single write operation)
        print("🚀 Triggering scraper...")
        _trigger_cloud_run_job("scrape_sets")
        
        # Store comprehensive state for next comparison
        updated_known_sets = [
            {"name": name, "code": code, "card_count": current_set_counts.get(code, 0)}
            for name, code in website_sets
        ]
        
        config_ref.set({
            "sets_hash": current_hash,
            "last_changed": db.SERVER_TIMESTAMP,
            "sets_count": len(website_sets),
            "known_sets": updated_known_sets,
            "change_reasons": change_reasons,
            "change_summary": f"Detected changes: {'; '.join(change_reasons[:2])}",
            "new_sets_count": len(new_sets_info),
            "check_method": "enhanced_multi_layer",
            "last_successful_check": db.SERVER_TIMESTAMP
        })
        
        # Send detailed alert about changes detected
        if new_sets_info:
            new_set_names = [f"{name} ({code})" for name, code, _ in new_sets_info]
            _send_automation_alert(
                f"🎉 NEW SETS DETECTED: {', '.join(new_set_names)} - Scraping triggered",
                "NEW_SETS"
            )
        
        _send_success_notification(
            f"Change detection successful - {len(new_sets_info)} new sets found",
            {
                "new_sets": [f"{name} ({code})" for name, code, _ in new_sets_info],
                "total_sets": len(website_sets),
                "change_reasons": change_reasons
            }
        )
        
        print(f"✅ Enhanced check complete - {len(new_sets_info)} new sets processed")
        
    except Exception as e:
        print(f"❌ ERROR: Enhanced sets check failed: {e}")
        # Send alert for automation failures
        try:
            _send_automation_alert(f"Set detection failed: {e}")
        except:
            pass  # Don't fail on alert failure

# Keep old function for backward compatibility but mark deprecated
def _check_limitless_sets():
    print("⚠️  DEPRECATED: Using old inefficient checker method")
    _check_limitless_sets_efficient()
        
def _generate_drive_hash(all_folders, folder_file_counts):
    """Generate hash of all folder states for efficient change detection."""
    # Create sorted list of folder_name:file_count pairs
    folder_data = []
    for folder in sorted(all_folders, key=lambda x: x.get("name", "")):
        folder_name = folder.get("name", "")
        file_count = folder_file_counts.get(folder_name, 0)
        folder_data.append(f"{folder_name}:{file_count}")
    
    # Generate hash from combined data
    combined_data = "|".join(folder_data)
    return hashlib.sha256(combined_data.encode()).hexdigest()[:16]

def _check_google_drive_efficient():
    """Ultra-efficient Google Drive checker using hash-based change detection."""
    print("🔍 Efficient check: Scanning Google Drive for changes...")
    try:
        # 1. Get folder list from Drive (Google API call - free)
        all_folders = []
        page_token = None
        while True:
            query = f"'{GOOGLE_DRIVE_ROOT_FOLDER_ID}' in parents and trashed=false and mimeType = 'application/vnd.google-apps.folder'"
            response = drive_service.files().list(q=query, pageToken=page_token, fields="nextPageToken, files(id, name)").execute()
            all_folders.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        
        # 2. Get file counts for folders (Google API calls - free)  
        current_folder_file_counts = {}
        for folder in all_folders:
            folder_id = folder.get("id")
            folder_name = folder.get("name")
            
            # Count files efficiently
            file_count = 0
            page_token_files = None
            while True:
                query_files = f"'{folder_id}' in parents and trashed=false"
                response_files = drive_service.files().list(
                    q=query_files, 
                    pageToken=page_token_files, 
                    pageSize=1000, 
                    fields="nextPageToken, files(id)"
                ).execute()
                file_count += len(response_files.get("files", []))
                page_token_files = response_files.get("nextPageToken")
                if not page_token_files:
                    break
            
            current_folder_file_counts[folder_name] = file_count
        
        # 3. Generate current state hash (FREE)
        current_hash = _generate_drive_hash(all_folders, current_folder_file_counts)
        
        # 4. Single Firestore read to get stored hash
        config_ref = db.collection("internal_config").document("drive_hash_tracker")
        doc = config_ref.get()
        stored_hash = doc.to_dict().get("drive_hash", "") if doc.exists else ""
        
        print(f"   Current hash: {current_hash}")
        print(f"   Stored hash:  {stored_hash}")
        
        # 5. Compare hashes (FREE)
        if current_hash == stored_hash:
            print("✅ No changes detected in Google Drive")
            return
        
        # 6. Changes detected! Log details and trigger job
        print("🚨 Drive changes detected!")
        folder_count = len(all_folders)
        total_files = sum(current_folder_file_counts.values())
        print(f"   📁 Total folders: {folder_count}")
        print(f"   📄 Total files: {total_files}")
        
        print("🚀 Triggering image scraper...")
        _trigger_cloud_run_job("scrape_images")
        
        # 7. Single atomic write to update hash
        config_ref.set({
            "drive_hash": current_hash,
            "last_changed": db.SERVER_TIMESTAMP,
            "folder_count": folder_count,
            "total_files": total_files,
            "change_summary": f"Hash changed from {stored_hash[:8]}... to {current_hash[:8]}..."
        })
        
        print("✅ Efficient Drive check complete")
        
    except HttpError as e:
        print(f"❌ ERROR: Google Drive API error: {e}")
    except Exception as e:
        print(f"❌ ERROR: Efficient Drive check failed: {e}")

# Keep old function for backward compatibility but mark deprecated  
def _check_google_drive():
    print("⚠️  DEPRECATED: Using old inefficient Drive checker method")
    _check_google_drive_efficient()

# --- Main Entry Point for the Function ---
def pvpocket_checker(request):
    """Ultra-efficient checker that minimizes Firestore operations."""
    _initialize_clients_if_needed()
    
    envelope = request.get_json(silent=True) or request.args
    check_type = envelope.get("CHECK_TYPE")

    print("🚀 Starting ultra-efficient checker...")
    start_time = db.SERVER_TIMESTAMP
    
    if check_type == "limitless_sets":
        _check_limitless_sets_efficient()
    elif check_type == "google_drive":
        _check_google_drive_efficient()
    else:
        # If no specific type is requested, run all checks by default.
        print("📋 No CHECK_TYPE specified, running all efficient checks.")
        _check_limitless_sets_efficient()
        _check_google_drive_efficient()
    
    print("✅ All efficient checks complete!")
    return "Efficient checks complete - minimal Firestore usage", 200


def _send_automation_alert(message: str, alert_type: str = "ERROR"):
    """Send alert for automation failures or successes."""
    try:
        print(f"🚨 {alert_type}: {message}")
        # Store alert in Firestore for monitoring dashboard
        alert_doc = {
            "type": alert_type,
            "message": message,
            "timestamp": db.SERVER_TIMESTAMP,
            "component": "change_detection",
            "severity": "high" if alert_type == "ERROR" else "medium"
        }
        db.collection("internal_config").document("alerts").collection("automation_alerts").add(alert_doc)
    except Exception as e:
        print(f"Failed to send alert: {e}")

def _send_success_notification(message: str, details: dict = None):
    """Send success notification with details."""
    try:
        print(f"✅ SUCCESS: {message}")
        success_doc = {
            "type": "SUCCESS", 
            "message": message,
            "details": details or {},
            "timestamp": db.SERVER_TIMESTAMP,
            "component": "change_detection"
        }
        db.collection("internal_config").document("alerts").collection("automation_alerts").add(success_doc)
    except Exception as e:
        print(f"Failed to log success: {e}")