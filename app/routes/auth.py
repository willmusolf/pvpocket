from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    current_app,
    jsonify,
    flash,
)
from urllib.parse import urlparse, urljoin
from datetime import datetime, timezone  # For Firestore Timestamps
import uuid
import re

from flask_login import (
    login_user,
    logout_user,
    current_user as flask_login_current_user,
    login_required,
)
from flask_dance.consumer import oauth_authorized
from flask_dance.contrib.google import google

# Import for Firestore specific types like SERVER_TIMESTAMP or ArrayUnion if needed later
from firebase_admin import firestore

from ..models import User  # Your User class from models.py
from better_profanity import profanity  # Your profanity checker

auth_bp = Blueprint("auth", __name__)


def check_username_requirement():
    """
    Global check that runs before each request to ensure username is set.
    """
    # Skip check for certain routes
    exempt_endpoints = {
        "auth.set_username_page",
        "auth.login_prompt_page",
        "auth.logout",
        "auth.store_intended_redirect",
        "static",  # Allow static files
        "main.index",  # Allow homepage
        # Add other public routes that don't require username
    }

    # Skip if accessing an exempt endpoint
    if request.endpoint in exempt_endpoints:
        return

    # Skip if user is not authenticated
    if not flask_login_current_user.is_authenticated:
        return

    # Check if user needs to set username
    user_data = getattr(flask_login_current_user, "data", {})
    if not user_data.get("username_set", False):
        # Don't redirect if already on set username page
        if request.endpoint == "auth.set_username_page":
            return

        # Store current URL and redirect to username setup
        next_url = request.url
        return redirect(url_for("auth.set_username_page", next=next_url))


def is_safe_url(target):
    if not target:
        print(
            "[IS_SAFE_URL_DEBUG] Target is None or empty, returning False.", flush=True
        )
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    is_internal_host = ref_url.netloc == test_url.netloc
    is_valid_scheme = test_url.scheme in ("http", "https")
    result = is_valid_scheme and is_internal_host
    print(
        f"[IS_SAFE_URL_DEBUG] Target: '{target}', Host URL: '{request.host_url}'",
        flush=True,
    )
    print(f"[IS_SAFE_URL_DEBUG] Ref URL: {ref_url}, Test URL: {test_url}", flush=True)
    print(
        f"[IS_SAFE_URL_DEBUG] Is internal host: {is_internal_host}, Is valid scheme: {is_valid_scheme}, Overall result: {result}",
        flush=True,
    )
    return result


def is_logged_in():
    from flask_login import current_user

    return current_user.is_authenticated


def get_current_user_data():
    if flask_login_current_user.is_authenticated:
        return flask_login_current_user.data  # .data attribute from User class
    return None


@auth_bp.route("/login-prompt")
def login_prompt_page():

    if flask_login_current_user.is_authenticated:
        return redirect(url_for("auth.user_profile_and_settings"))

    next_param = request.args.get("next")
    print(
        f"[AUTH_DEBUG] /login-prompt called. next_param from request.args: '{next_param}'",
        flush=True,
    )

    # Store the 'next' URL in OUR OWN session key, if valid
    if next_param and is_safe_url(next_param):
        session["custom_login_next_url"] = next_param  # Use a distinct session key
        print(
            f"[AUTH_DEBUG] Stored in session['custom_login_next_url']: '{next_param}'",
            flush=True,
        )
    else:
        # If next_param is bad or missing, clear any old one to be safe
        session.pop("custom_login_next_url", None)
        print(
            f"[AUTH_DEBUG] No valid next_param for login_prompt, custom_login_next_url cleared/not set.",
            flush=True,
        )

    return render_template("login_prompt.html")


def is_username_globally_unique(username_to_check, current_user_id_to_ignore=None):
    db = current_app.config.get("FIRESTORE_DB")
    if not db:
        print(
            "is_username_globally_unique: Firestore client not available. Assuming unique for safety.",
            flush=True,
        )
        return True  # Or handle error, but for now, fail open if DB is down

    username_lower = username_to_check.lower()
    # Query for users with the same lowercase username.
    # REQUIRES an index on 'username_lowercase'. Firestore will prompt you to create it.
    query = (
        db.collection("users")
        .where("username_lowercase", "==", username_lower)
        .limit(1)
    )
    docs = query.stream()

    for doc in docs:  # Should be at most one document due to limit(1)
        if doc.id != current_user_id_to_ignore:
            print(f"Username '{username_lower}' taken by user ID: {doc.id}", flush=True)
            return False  # Username taken by someone else
    return True  # Username is unique or taken by the user being ignored


@oauth_authorized.connect_via(google)  # Decorator should already be above your function
def google_authorized(blueprint, token):
    print("--- @oauth_authorized google_authorized (Firestore) ---", flush=True)

    if not token:
        # Using session for toast as flash might not appear after immediate redirect by Flask-Dance
        session["display_toast_once"] = {
            "message": "Failed to log in with Google (no token).",
            "type": "error",
        }
        print("[AUTH_FIRESTORE] No token received.", flush=True)
        return redirect(url_for("main.index"))  # Or auth.login_prompt_page

    try:
        resp = blueprint.session.get("/oauth2/v3/userinfo")
        resp.raise_for_status()  # Raises an exception for bad status codes (4xx or 5xx)
        google_user_info = resp.json()
    except Exception as e:
        msg = "Failed to fetch user info from Google. See logs for detailed error."
        session["display_toast_once"] = {"message": msg, "type": "error"}
        print(f"[AUTH_FIRESTORE] {msg}", flush=True)
        return redirect(url_for("main.index"))  # Or auth.login_prompt_page

    google_id = str(google_user_info.get("sub"))
    email = google_user_info.get("email")
    print(
        f"[AUTH_FIRESTORE] User info fetched for Google ID: {google_id}, Email presence: {email is not None}",
        flush=True,
    )

    if not email:
        session["display_toast_once"] = {
            "message": "Could not retrieve a verified email from Google.",
            "type": "error",
        }
        print("[AUTH_FIRESTORE] No email from Google.", flush=True)
        return redirect(url_for("auth.login_prompt_page"))

    db = current_app.config.get("FIRESTORE_DB")
    if not db:
        print("[AUTH_FIRESTORE] CRITICAL: Firestore client not available!", flush=True)
        session["display_toast_once"] = {
            "message": "Database service unavailable. Please try again later.",
            "type": "error",
        }
        return redirect(url_for("main.index"))

    user_app_id = None
    user_data_for_login = None  # This will hold the dict to create the User object
    users_collection_ref = db.collection("users")

    # 1. Find user by Google ID
    query_google_id = (
        users_collection_ref.where("google_id", "==", google_id).limit(1).stream()
    )
    for user_doc in query_google_id:  # Iterator, will run at most once
        user_app_id = user_doc.id
        user_data_for_login = user_doc.to_dict()
        print(f"[AUTH_FIRESTORE] Found user by Google ID: {user_app_id}", flush=True)
        break

    # 2. If not found by Google ID, find by email and link Google ID
    if not user_app_id:
        query_email = users_collection_ref.where("email", "==", email).limit(1).stream()
        for user_doc in query_email:  # Iterator
            user_app_id = user_doc.id
            user_data_for_login = user_doc.to_dict()
            if not user_data_for_login.get(
                "google_id"
            ):  # Check if google_id is missing or empty
                try:
                    users_collection_ref.document(user_app_id).update(
                        {"google_id": google_id}
                    )
                    user_data_for_login["google_id"] = (
                        google_id  # Update in-memory dict for current login
                    )
                    print(
                        f"[AUTH_FIRESTORE] Linking Google ID to existing user {user_app_id} by email.",
                        flush=True,
                    )
                except Exception as e_update_gid:
                    print(
                        f"[AUTH_FIRESTORE] ERROR linking Google ID for user {user_app_id}: {e_update_gid}",
                        flush=True,
                    )
                    # Continue login with existing data, Google ID linking can be retried or handled
            break

    # 3. If still not found (new user), create a new user document in Firestore
    if not user_app_id:
        user_app_id = str(uuid.uuid4())  # Generate a new unique ID for your app
        user_data_for_login = {
            "email": email,
            "google_id": google_id,
            "username": "",  # User will set this later
            "username_lowercase": "",  # For case-insensitive unique checks
            "created_at": firestore.SERVER_TIMESTAMP,  # Use Firestore server-side timestamp
            "deck_ids": [],  # Initialize as empty array for deck IDs
            "username_set": False,
            "profile_icon": "",
            "username_change_count": 0,
        }
        try:
            users_collection_ref.document(user_app_id).set(user_data_for_login)
            print(
                f"[AUTH_FIRESTORE] Created new user in Firestore. App ID: {user_app_id}",
                flush=True,
            )
        except Exception as e_create:
            print(
                f"[AUTH_FIRESTORE] ERROR creating user {user_app_id} in Firestore: {e_create}",
                flush=True,
            )
            session["display_toast_once"] = {
                "message": "Critical error creating your account. Please try again.",
                "type": "error",
            }
            return redirect(url_for("main.index"))  # Or a more generic error page

    # 4. Log in the user with Flask-Login
    if user_data_for_login and user_app_id:
        # Ensure created_at (if it's a Firestore Timestamp) is handled if User class expects str
        # For User class init: user_data_for_login is passed directly
        user_instance_to_login = User(user_id=user_app_id, data=user_data_for_login)
        login_user(user_instance_to_login, remember=True)
        print(
            f"[AUTH_FIRESTORE] User '{user_instance_to_login.username}' (ID: {user_app_id}) logged in with Flask-Login.",
            flush=True,
        )
    else:
        # This case should ideally not be reached if logic above is correct
        session["display_toast_once"] = {
            "message": "User identification or creation failed after Google authentication.",
            "type": "error",
        }
        print(
            "[AUTH_FIRESTORE] ERROR: user_data_for_login or user_app_id was None before login_user.",
            flush=True,
        )
        return redirect(url_for("auth.login_prompt_page"))

    # 5. Determine final redirect URL (your existing logic for 'next' parameter)
    final_next_url_after_setup = None
    # --- Start of your 'next_url' logic ---
    next_url_from_flask_dance = session.pop(f"{blueprint.name}_next_url", None)
    if next_url_from_flask_dance and is_safe_url(next_url_from_flask_dance):
        final_next_url_after_setup = next_url_from_flask_dance
    else:
        if next_url_from_flask_dance:
            print(
                f"[AUTH_FIRESTORE] Flask-Dance next_url ('{next_url_from_flask_dance}') was unsafe.",
                flush=True,
            )
        custom_next_url = session.pop("custom_login_next_url", None)
        if custom_next_url and is_safe_url(custom_next_url):
            final_next_url_after_setup = custom_next_url
        elif custom_next_url:
            print(
                f"[AUTH_FIRESTORE] Custom_login_next_url ('{custom_next_url}') was unsafe.",
                flush=True,
            )

    if not final_next_url_after_setup or final_next_url_after_setup == url_for(
        "main.index"
    ):
        final_next_url_after_setup = url_for("auth.user_profile_and_settings")
    # --- End of your 'next_url' logic ---
    print(
        f"[AUTH_FIRESTORE] Determined next URL after setup: {final_next_url_after_setup}",
        flush=True,
    )

    # 6. Check if username needs to be set (based on data from Firestore)
    # Use user_data_for_login which is the most up-to-date dict from Firestore or new creation
    if not user_data_for_login.get("username_set"):
        return redirect(
            url_for("auth.set_username_page", next=final_next_url_after_setup)
        )
    else:
        # For existing users who are already set up
        session["display_toast_once"] = {
            "message": f"Successfully signed in as {user_data_for_login.get('username')}!",
            "type": "success",
        }
        print(
            f"[AUTH_FIRESTORE] Redirecting to: {final_next_url_after_setup}", flush=True
        )
        return redirect(final_next_url_after_setup)


def profanity_check(text_to_check: str) -> bool:
    if profanity.contains_profanity(text_to_check):
        return True

    potential_words = re.findall(r"[a-zA-Z]+", text_to_check)

    text_from_parts = " ".join(potential_words)

    if text_from_parts != text_to_check and profanity.contains_profanity(
        text_from_parts
    ):
        return True

    return False


@auth_bp.route("/set-username", methods=["GET", "POST"])
@login_required
def set_username_page():
    db = current_app.config.get("FIRESTORE_DB")
    if not db:
        session["display_toast_once"] = {
            "message": "Database service unavailable.",
            "type": "error",
        }
        return redirect(url_for("main.index"))

    user_id_str = str(flask_login_current_user.id)
    user_doc_ref = db.collection("users").document(user_id_str)

    user_record_snapshot = user_doc_ref.get()
    if not user_record_snapshot.exists:
        logout_user()
        return redirect(
            url_for("auth.login_prompt_page", message="User session error.")
        )
    user_record_data = user_record_snapshot.to_dict()

    if user_record_data.get("username_set"):
        return redirect(url_for("main.index"))

    title = "Set Your Username"
    next_url_on_success = request.form.get(
        "next_url", request.args.get("next", url_for("main.index"))
    )
    if not is_safe_url(next_url_on_success):
        next_url_on_success = url_for("main.index")

    username_error = None
    if request.method == "POST":
        new_username = request.form.get("new_username", "").strip()
        selected_icon = request.form.get("profile_icon")

        if not (3 <= len(new_username) <= 20):
            username_error = "Username must be 3-20 characters long."
        elif not re.match(r"^[a-zA-Z0-9_]+$", new_username):
            username_error = "Username can only contain letters, numbers, and underscores (_). No spaces."
        elif not is_username_globally_unique(
            new_username, current_user_id_to_ignore=user_id_str
        ):
            username_error = "That username is already taken. Please choose another."
        elif profanity_check(new_username):
            username_error = "This username is not allowed due to its content."
        elif not selected_icon or selected_icon not in current_app.config.get(
            "PROFILE_ICON_FILENAMES", []
        ):
            username_error = "Please select a valid profile icon."

        if username_error:
            return render_template(
                "set_username.html",
                title=title,
                next_url=next_url_on_success,
                username_error=username_error,
                current_username_value=new_username,
                profile_icons=current_app.config["PROFILE_ICON_FILENAMES"],
                profile_icon_urls=current_app.config["PROFILE_ICON_URLS"],
            )
        else:
            try:
                update_data = {
                    "username": new_username,
                    "username_lowercase": new_username.lower(),
                    "username_set": True,
                    "profile_icon": selected_icon,
                }
                user_doc_ref.update(update_data)

                session["username"] = new_username
                if hasattr(flask_login_current_user, "username"):
                    flask_login_current_user.username = new_username
                if hasattr(flask_login_current_user, "data"):
                    flask_login_current_user.data.update(update_data)

                session["display_toast_once"] = {
                    "message": "Username successfully set!",
                    "type": "success",
                }
                return redirect(next_url_on_success)
            except Exception as e_update:
                print(
                    f"Error updating username in Firestore for {user_id_str}: {e_update}",
                    flush=True,
                )
                username_error = (
                    "A server error occurred setting username. Please try again."
                )
                return render_template(
                    "set_username.html",
                    title=title,
                    next_url=next_url_on_success,
                    username_error=username_error,
                    current_username_value=new_username,
                    profile_icons=current_app.config["PROFILE_ICON_FILENAMES"],
                    profile_icon_urls=current_app.config["PROFILE_ICON_URLS"],
                )

    return render_template(
        "set_username.html",
        title=title,
        next_url=next_url_on_success,
        username_error=None,
        current_username_value="",
        profile_icons=current_app.config["PROFILE_ICON_FILENAMES"],
        profile_icon_urls=current_app.config["PROFILE_ICON_URLS"],
    )


@auth_bp.route("/logout")
def logout():
    origin_url = request.referrer or request.headers.get("Referer")

    logout_user() 

    session.pop("google_oauth_token", None) 

    is_safe = is_safe_url(origin_url)
    if origin_url and is_safe:
        return redirect(origin_url)
    return redirect(url_for("main.index"))


@auth_bp.route("/user/profile", methods=["GET", "POST"])
@login_required
def user_profile_and_settings():
    db = current_app.config.get("FIRESTORE_DB")
    if not db:
        session["display_toast_once"] = {
            "message": "Database service unavailable.",
            "type": "error",
        }
        return redirect(url_for("main.index"))

    user_id_str = str(flask_login_current_user.id)
    user_doc_ref = db.collection("users").document(user_id_str)

    username_change_error = None
    if request.method == "POST":
        if "update_profile_icon" in request.form:
            new_icon = request.form.get("profile_icon")
            if new_icon and new_icon in current_app.config.get(
                "PROFILE_ICON_FILENAMES", []
            ):
                try:
                    user_doc_ref.update({"profile_icon": new_icon})
                    session["display_toast_once"] = {
                        "message": "Profile icon updated successfully.",
                        "type": "success",
                    }
                    if hasattr(flask_login_current_user, "data"):
                        flask_login_current_user.data["profile_icon"] = new_icon
                    return redirect(url_for("auth.user_profile_and_settings"))
                except Exception as e:
                    current_app.logger.error(
                        f"Error updating profile icon for {user_id_str}: {e}"
                    )
                    flash("Error updating profile icon. Please try again.", "danger")
            else:
                flash("Invalid profile icon selected.", "danger")

        elif "new_username" in request.form:
            new_username_form = request.form.get("new_username", "").strip()

            user_snapshot_for_check = user_doc_ref.get()
            if not user_snapshot_for_check.exists:
                logout_user()
                return redirect(url_for("main.index"))
            user_data_for_check = user_snapshot_for_check.to_dict()

            if user_data_for_check.get("username_change_count", 0) >= 1:
                username_change_error = "You have already changed your username once and cannot change it again."

            if not new_username_form:
                username_change_error = "New username cannot be empty."
            elif len(new_username_form) < 3 or len(new_username_form) > 20:
                username_change_error = "Username must be 3-20 characters long."
            elif not re.match(r"^[a-zA-Z0-9_]+$", new_username_form):
                username_change_error = "Username can only contain letters, numbers, and underscores (_). No spaces."
            elif new_username_form.lower() == user_data_for_check.get(
                "username_lowercase", ""
            ):
                username_change_error = "This is your current username. No change made."
            elif not is_username_globally_unique(
                new_username_form, current_user_id_to_ignore=user_id_str
            ):
                username_change_error = (
                    "That username is already taken. Please choose another."
                )
            elif profanity.contains_profanity(new_username_form):
                username_change_error = "This username contains inappropriate language."

            if not username_change_error:
                try:
                    update_data = {
                        "username": new_username_form,
                        "username_lowercase": new_username_form.lower(),
                        "username_change_count": firestore.Increment(
                            1
                        ),  # Increments the value on the server
                    }
                    user_doc_ref.update(update_data)
                    fresh_user_snapshot = user_doc_ref.get()
                    if fresh_user_snapshot.exists:
                        fresh_user_data = fresh_user_snapshot.to_dict()
                        updated_user_object = User(
                            user_id=user_id_str, data=fresh_user_data
                        )
                        login_user(updated_user_object, remember=True)
                        session["username"] = new_username_form
                    else:
                        logout_user()
                        session.clear()
                        flash(
                            "Could not find your user account after update. You have been logged out.",
                            "error",
                        )
                        return redirect(url_for("auth.login_prompt_page"))

                    session["display_toast_once"] = {
                        "message": f"Username successfully changed to '{new_username_form}'.",
                        "type": "success",
                    }
                    return redirect(url_for("auth.user_profile_and_settings"))
                except Exception as e_update:
                    current_app.logger.error(
                        f"Error updating profile username for {user_id_str}: {e_update}",
                        exc_info=True,
                    )
                    username_change_error = "A server error occurred while saving username. Please try again."

    user_record_snapshot = user_doc_ref.get()
    if not user_record_snapshot.exists:
        current_app.logger.warning(
            f"User document not found for logged-in user ID: {user_id_str}. Logging out."
        )
        logout_user()
        session.clear()
        flash("Your session was invalid. Please log in again.", "warning")
        return redirect(url_for("auth.login_prompt_page"))

    user_record_data = user_record_snapshot.to_dict()
    user_deck_ids = user_record_data.get("deck_ids", [])
    user_battles = []

    return render_template(
        "profile.html",
        user_info=user_record_data,
        decks=user_deck_ids,
        battles=user_battles,
        username_change_error=username_change_error,
    )


@auth_bp.route("/auth/store-intended-redirect", methods=["POST"])
def store_intended_redirect():
    data = request.get_json()
    if not data:
        return jsonify(success=False, error="No data provided."), 400

    next_url = data.get("next_url")
    print(f"[AUTH_DEBUG /auth/store-intended-redirect] Received next_url: '{next_url}'", flush=True)

    if next_url and is_safe_url(next_url):
        session["custom_login_next_url"] = next_url # Use your reliable session key
        print(f"[AUTH_DEBUG /auth/store-intended-redirect] Stored in session['custom_login_next_url']: '{next_url}'", flush=True)
        return jsonify(success=True, message="Intended redirect URL stored.")
    else:
        session.pop("custom_login_next_url", None) # Clear any old or unsafe URL
        print(f"[AUTH_DEBUG /auth/store-intended-redirect] Invalid or no next_url provided. Cleared custom_login_next_url.", flush=True)
        return jsonify(success=False, error="Invalid or unsafe next_url provided."), 400


@auth_bp.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    db = current_app.config.get("FIRESTORE_DB")
    if not db:
        session["display_toast_once"] = {
            "message": "Database service unavailable. Account deletion failed.",
            "type": "error",
        }
        return redirect(url_for("auth.user_profile_and_settings"))

    user_id_to_delete = str(flask_login_current_user.id)
    # username_to_delete = flask_login_current_user.username # Keep if needed for logging

    current_app.logger.info(
        f"Attempting to delete account for user ID: {user_id_to_delete}"
    )

    try:
        # Start a Firestore batch
        batch = db.batch()

        # 1. Fetch the user's document to get their deck_ids
        user_doc_ref = db.collection("users").document(user_id_to_delete)
        user_doc_snapshot = user_doc_ref.get()

        deck_ids_to_delete = []
        if user_doc_snapshot.exists:
            user_data = user_doc_snapshot.to_dict()
            deck_ids_to_delete = user_data.get("deck_ids", [])
            current_app.logger.info(
                f"User {user_id_to_delete} has deck IDs: {deck_ids_to_delete} to be deleted."
            )
        else:
            # User document doesn't exist, but we are in a @login_required route.
            # This is an inconsistent state. Log it. The user will be logged out anyway.
            current_app.logger.warning(
                f"User document for ID {user_id_to_delete} not found during account deletion, though user is logged in."
            )
            # Proceed to logout and clear session. No user or deck docs to delete in Firestore for this ID.
            logout_user()
            session.clear()
            session["display_toast_once"] = {
                "message": "Account data not found. You have been logged out.",
                "type": "warning",
            }
            return redirect(url_for("main.index"))

        # 2. Add delete operations for each deck to the batch
        if deck_ids_to_delete:  # Check if the list is not empty
            for deck_id in deck_ids_to_delete:
                if deck_id and isinstance(deck_id, str):  # Ensure deck_id is valid
                    deck_ref_to_delete = db.collection("decks").document(deck_id)
                    batch.delete(deck_ref_to_delete)
                    current_app.logger.info(
                        f"Added deletion of deck {deck_id} to batch for user {user_id_to_delete}."
                    )
                else:
                    current_app.logger.warning(
                        f"Invalid deck_id '{deck_id}' found for user {user_id_to_delete}, skipping its deletion."
                    )

        # 3. Add delete operation for the user document itself to the batch
        batch.delete(user_doc_ref)
        current_app.logger.info(
            f"Added deletion of user document {user_id_to_delete} to batch."
        )

        # 4. Commit the batch
        batch.commit()
        current_app.logger.info(
            f"Successfully committed batch deletion for user {user_id_to_delete} and their decks."
        )

        # 5. Log out user, clear session, and redirect
        logout_user()  # From flask_login
        session.clear()  # Clear all session data
        session["display_toast_once"] = {  # Set flash message for after redirect
            "message": "Your account and all associated data have been successfully deleted.",
            "type": "default",
        }
        return redirect(url_for("main.index"))

    except Exception as e_delete:
        current_app.logger.error(
            f"Error during account deletion process for user {user_id_to_delete}: {e_delete}",
            exc_info=True,
        )
        session["display_toast_once"] = {
            "message": "An error occurred while trying to delete your account. Please try again or contact support.",
            "type": "error",
        }
        return redirect(url_for("auth.user_profile_and_settings"))
