from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
    jsonify
)
from urllib.parse import urlparse, urljoin

# No longer need generate_password_hash, check_password_hash if only Google login
# from werkzeug.security import generate_password_hash, check_password_hash
import time  # Keep for user ID generation if not using UUID consistently
from datetime import datetime
import os
import json
import uuid  # <-- **ADD THIS IMPORT**
import re

# Flask-Login and Flask-Dance imports
from flask_login import (
    login_user,
    logout_user,
    current_user as flask_login_current_user,
    login_required,
)  # Removed current_user, use from flask_login
from flask_dance.consumer import oauth_authorized
from flask_dance.contrib.google import (
    google,
)  # This is the proxy to the google blueprint

# Import User class and load_user from __init__.py (or wherever they are defined)
# This assumes User and load_user are accessible, e.g. if __init__ defines them globally
# or if you have a models.py. For simplicity with your current structure:
# from .. import User, load_user # This might cause circular import if auth_bp is imported in __init__ first.
# It's often better to define User and load_user in a separate models.py or directly in __init__.py
# For now, assuming `load_user` is correctly registered with Flask-Login in __init__.py.
# We'll need the User class here if creating new instances.

# --- Temporary User class definition here if not importable, to match __init__.py ---
# --- Ideally, this User class should be in a models.py or in __init__.py and imported ---
from flask_login import UserMixin
from ..models import User


auth_bp = Blueprint("auth", __name__)


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


# app/routes/auth.py
def get_current_user_data():
    from flask_login import current_user

    if current_user.is_authenticated:
        # current_user.id is the app-specific user ID (key in users.json)
        # current_user.data contains the dictionary from users.json
        # (assuming User class in __init__.py correctly populates self.data)
        return current_user.data  # Or fetch fresh from app.config['users'] if needed
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

    # The template will still link to google.login, but we won't pass 'next' in url_for here
    return render_template("login_prompt.html")


# Helper function for username uniqueness check (can be in this file or a utils.py)
def is_username_globally_unique(
    username_to_check, users_data, current_user_id_to_ignore=None
):
    """Checks if a username is unique across all users, optionally ignoring one user."""
    for user_id, user_data in users_data.items():
        if current_user_id_to_ignore and user_id == current_user_id_to_ignore:
            continue
        if user_data.get("username", "").lower() == username_to_check.lower():
            return False  # Username already taken
    return True  # Username is unique


@oauth_authorized.connect_via(google)
def google_authorized(blueprint, token):
    print(
        "--- @oauth_authorized google_authorized SIGNAL HANDLER CALLED --- [TOP OF FUNCTION]",
        flush=True,
    )

    if not token:
        flash("Failed to log in with Google (no token).", "danger")
        print("[AUTH_DEBUG @oauth_authorized] No token received.", flush=True)
        return redirect(url_for("main.index"))

    try:
        resp = blueprint.session.get("/oauth2/v3/userinfo")
        resp.raise_for_status()
        google_user_info = resp.json()
    except Exception as e:
        msg = f"Failed to fetch user info from Google. Error: {e}"
        flash(msg, "danger")
        print(f"[AUTH_DEBUG @oauth_authorized] {msg}", flush=True)
        return redirect(url_for("main.index"))

    print(
        f"[AUTH_DEBUG @oauth_authorized] Google user info fetched: {google_user_info}",
        flush=True,
    )

    google_id = str(google_user_info.get("sub"))
    email = google_user_info.get("email")

    if not email:
        flash("Could not retrieve a verified email from Google.", "danger")
        print("[AUTH_DEBUG @oauth_authorized] No email from Google.", flush=True)
        return redirect(url_for("auth.login_prompt_page"))

    users_dict = current_app.config["users"]
    save_users_func = current_app.config["save_users"]
    user_app_id = None
    user_dict_data = None
    needs_saving_users_json = False
    is_new_user_creation = False  # Flag to track if we just created the user

    # 1. Find by Google ID
    for uid, u_data in users_dict.items():
        if u_data.get("google_id") == google_id:
            user_app_id = uid
            user_dict_data = u_data
            print(
                f"[AUTH_DEBUG @oauth_authorized] Found user by Google ID: {uid}",
                flush=True,
            )
            break

    # 2. If not found, find by email and link
    if not user_app_id:
        for uid, u_data in users_dict.items():
            if u_data.get("email") == email:
                user_app_id = uid
                user_dict_data = u_data
                if not user_dict_data.get("google_id"):
                    user_dict_data["google_id"] = google_id
                    needs_saving_users_json = True
                    print(
                        f"[AUTH_DEBUG @oauth_authorized] Linking Google ID to existing user {uid}",
                        flush=True,
                    )
                break

    # 3. If still not found, create new user
    if not user_app_id:
        is_new_user_creation = True
        user_app_id = str(uuid.uuid4())
        user_dict_data = {
            "username": "",  # Initially empty, user must set it
            "email": email,
            "google_id": google_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "decks": [],
            "username_set": False,  # New flag
        }
        users_dict[user_app_id] = user_dict_data
        needs_saving_users_json = True
        print(
            f"[AUTH_DEBUG @oauth_authorized] Creating new user. App ID: {user_app_id}",
            flush=True,
        )

    if needs_saving_users_json:
        try:
            save_users_func()
            print("[AUTH_DEBUG @oauth_authorized] Users data saved.", flush=True)
        except Exception as e_save:
            flash("Critical error: Could not save user data.", "danger")
            print(
                f"[AUTH_DEBUG @oauth_authorized] Error saving users_dict: {e_save}",
                flush=True,
            )
            return redirect(url_for("main.index"))

    # 5. Log in the user with Flask-Login
    if user_dict_data and user_app_id:
        # Note: User object's username might be empty if it's a brand new user
        user_instance_to_login = User(
            user_id=user_app_id,
            username=user_dict_data.get("username"),  # Will be "" for new users here
            email=user_dict_data.get("email"),
            data=user_dict_data,
        )
        login_user(user_instance_to_login, remember=True)
        # session["user_id"] and session["username"] will be set based on user_instance_to_login
        # If username is "", session["username"] will be ""
        session["user_id"] = user_instance_to_login.id
        session["username"] = user_instance_to_login.username
        print(
            f"[AUTH_DEBUG @oauth_authorized] User '{user_instance_to_login.username}' (ID: {user_app_id}) logged in with Flask-Login.",
            flush=True,
        )
    else:
        flash(
            "User identification or creation failed after Google authentication.",
            "danger",
        )
        print(
            "[AUTH_DEBUG @oauth_authorized] ERROR: user_dict_data or user_app_id was None before login_user.",
            flush=True,
        )
        return redirect(url_for("auth.login_prompt_page"))

    # 6. Determine final redirect URL (original intended page)
    final_next_url_after_setup = None
    next_url_from_flask_dance = session.pop(f"{blueprint.name}_next_url", None)
    print(
        f"[AUTH_DEBUG @oauth_authorized] Popped '{blueprint.name}_next_url': '{next_url_from_flask_dance}'",
        flush=True,
    )

    if next_url_from_flask_dance and is_safe_url(next_url_from_flask_dance):
        final_next_url_after_setup = next_url_from_flask_dance
    else:
        if next_url_from_flask_dance:
            print(
                f"[AUTH_DEBUG @oauth_authorized] Flask-Dance next_url ('{next_url_from_flask_dance}') was unsafe.",
                flush=True,
            )
        custom_next_url = session.pop("custom_login_next_url", None)
        print(
            f"[AUTH_DEBUG @oauth_authorized] Popped 'custom_login_next_url': '{custom_next_url}'",
            flush=True,
        )
        if custom_next_url and is_safe_url(custom_next_url):
            final_next_url_after_setup = custom_next_url
        elif custom_next_url:
            print(
                f"[AUTH_DEBUG @oauth_authorized] Custom_login_next_url ('{custom_next_url}') was unsafe.",
                flush=True,
            )

    if not final_next_url_after_setup or final_next_url_after_setup == url_for(
        "main.index"
    ):
        # If no specific 'next' URL was found, or if it was just the main index,
        # redirect to the user's profile page by default after login.
        final_next_url_after_setup = url_for("auth.user_profile_and_settings")
    print(
        f"[AUTH_DEBUG @oauth_authorized] Determined next URL after setup: {final_next_url_after_setup}",
        flush=True,
    )

    # 7. Check if username needs to be set
    if not user_dict_data.get("username_set"):
        flash(
            "Welcome! Please choose your username to complete your registration.",
            "info",
        )
        return redirect(
            url_for("auth.set_username_page", next=final_next_url_after_setup)
        )  # Pass the determined next URL
    else:
        flash(f"Successfully signed in as {user_dict_data.get('username')}!", "success")
        print(
            f"[AUTH_DEBUG @oauth_authorized] Redirecting to: {final_next_url_after_setup}",
            flush=True,
        )
        return redirect(final_next_url_after_setup)


# ++ NEW ROUTE FOR SETTING USERNAME ++
@auth_bp.route("/set-username", methods=["GET", "POST"])
@login_required
def set_username_page():
    user_id = str(flask_login_current_user.id)
    users_dict = current_app.config["users"]
    user_record = users_dict.get(user_id)

    if not user_record:  # Should not happen if @login_required
        flash("User not found. Please log in again.", "danger")
        logout_user()
        return redirect(url_for("auth.login_prompt_page"))

    # If username is already set, redirect away from this page
    if user_record.get("username_set"):
        flash("Your username is already set.", "info")
        return redirect(url_for("main.index"))  # Or user_profile_and_settings

    next_url_on_success = request.args.get(
        "next", url_for("main.index")
    )  # Get 'next' from GET param for rendering form
    if not is_safe_url(next_url_on_success):  # Validate 'next' from GET
        next_url_on_success = url_for("main.index")

    if request.method == "POST":
        new_username = request.form.get("new_username", "").strip()
        # 'next_url_on_success' will be submitted via a hidden field in the form
        next_url_from_form = request.form.get("next_url", url_for("main.index"))
        if not is_safe_url(next_url_from_form):  # Validate 'next' from POST
            next_url_from_form = url_for("main.index")

        # Validation logic (same as your profile page, plus global uniqueness)
        error_occurred = False
        if not new_username:
            flash("Username cannot be empty.", "danger")
            error_occurred = True
        elif len(new_username) < 3 or len(new_username) > 20:
            flash("Username must be 3-20 characters.", "danger")
            error_occurred = True
        elif " " in new_username:
            flash("Username cannot contain spaces.", "danger")
            error_occurred = True
        elif not re.match(r"^[a-zA-Z0-9_]+$", new_username):
            flash(
                "Username can only contain letters, numbers, and underscores.", "danger"
            )
            error_occurred = True
        elif not is_username_globally_unique(
            new_username, users_dict
        ):  # Global uniqueness check
            flash("That username is already taken. Please choose another.", "danger")
            error_occurred = True

        if error_occurred:
            return render_template(
                "set_username.html",
                title="Set Your Username",
                next_url=next_url_from_form,
                current_username_value=new_username,
            )

        # If valid and unique:
        user_record["username"] = new_username
        user_record["username_set"] = True
        try:
            current_app.config["save_users"]()
            # Update session and current_user proxy immediately
            session["username"] = new_username
            if hasattr(flask_login_current_user, "username"):
                flask_login_current_user.username = new_username
            # Update the User object associated with flask_login_current_user if its data is stale
            # This might require re-fetching or directly updating the .data attribute if your User class uses it.
            # For simplicity, we assume login_manager.user_loader will provide fresh User object on next request.
            # The current User object in flask_login_current_user might still hold the old username ("") until next full load.
            # To fix immediately:
            if hasattr(flask_login_current_user, "data"):
                flask_login_current_user.data["username"] = new_username
                flask_login_current_user.data["username_set"] = True
            print(
                f"Username for {user_id} set to '{new_username}'. Redirecting to '{next_url_from_form}'."
            )
            return redirect(next_url_from_form)
        except Exception as e:
            flash(
                "An error occurred while saving your username. Please try again.",
                "danger",
            )
            print(f"Error saving username for {user_id}: {e}")
            user_record["username_set"] = False  # Revert flag on error
            user_record["username"] = ""  # Revert username
            return render_template(
                "set_username.html",
                title="Set Your Username",
                next_url=next_url_from_form,
                current_username_value=new_username,
            )

    # For GET request
    return render_template(
        "set_username.html",
        title="Choose Your Username",
        next_url=next_url_on_success,
        current_username_value="",
    )

@auth_bp.route("/logout")
def logout():
    origin_url = request.referrer or request.headers.get("Referer")

    logout_user() 

    session.pop("user_id", None)
    session.pop("username", None)
    session.pop("google_oauth_token", None) 

    is_safe = is_safe_url(origin_url)
    if origin_url and is_safe:
        return redirect(origin_url)
    return redirect(url_for("main.index"))


# --- COMBINED User Profile & Settings Page ---
@auth_bp.route("/user/profile", methods=["GET", "POST"])
@login_required
def user_profile_and_settings():  # Ensure this matches url_for calls, or use explicit endpoint name
    users_dict = current_app.config["users"]
    # Ensure user_id from Flask-Login is a string if keys in users_dict are strings
    user_record = users_dict.get(str(flask_login_current_user.id))

    if not user_record:
        logout_user()
        return redirect(url_for("auth.login_prompt_page"))

    if request.method == "POST":
        new_username_form = request.form.get("new_username", "").strip()
        max_username_len = 20
        min_username_len = 3
        error_occurred = False

        # --- Username Validation Logic (same as before) ---
        if not new_username_form:
            error_occurred = True
        elif len(new_username_form) < min_username_len:
            error_occurred = True
        elif len(new_username_form) > max_username_len:
            error_occurred = True
        elif " " in new_username_form:
            error_occurred = True
        elif not re.match(r"^[a-zA-Z0-9_]+$", new_username_form):
            error_occurred = True
        else:
            is_unique_or_same = True
            if new_username_form.lower() != user_record.get("username", "").lower():
                for uid, u_data in users_dict.items():
                    if (
                        uid != str(flask_login_current_user.id)
                        and u_data.get("username", "").lower()
                        == new_username_form.lower()
                    ):
                        is_unique_or_same = False
                        break
            if not is_unique_or_same:
                flash(
                    "That username is already taken. Please choose another.", "danger"
                )
                error_occurred = True
        # --- End Validation ---

        if not error_occurred:
            old_username = user_record.get("username")
            user_record["username"] = new_username_form  # Update the dict

            try:
                current_app.config["save_users"]()
                session["username"] = (
                    new_username_form  # Update app-specific session key
                )
                flask_login_current_user.username = (
                    new_username_form  # Update proxy for current request
                )
                flash(
                    f"Username successfully changed to '{new_username_form}'.",
                    "success",
                )

                # --- PRG PATTERN: Redirect after successful POST ---
                return redirect(
                    url_for("auth.user_profile_and_settings")
                )  # Or 'auth.user_profile' if you named it that
                # --- END PRG ---
            except Exception as e:
                flash("An error occurred while saving your new username.", "danger")
                user_record["username"] = old_username  # Revert on error
                session["username"] = old_username
                if hasattr(
                    flask_login_current_user, "username"
                ):  # Check before assigning
                    flask_login_current_user.username = old_username
        # If error_occurred is True, or if save failed without redirect,
        # we will fall through to the GET request rendering logic below,
        # which will re-render the form with flashed messages and POSTed values.

    # --- Logic for GET request (or if POST had errors and didn't redirect) ---
    # Fetch Decks and Battles data (same as before)
    user_decks_details = []
    decks_dir = "decks"
    meta_stats = current_app.config.get("meta_stats", {})
    for deck_id in user_record.get("decks", []):
        filename = f"{deck_id}.json"
        deck_path = os.path.join(decks_dir, filename)
        if os.path.exists(deck_path):
            try:
                with open(deck_path, "r") as f:
                    deck_data = json.load(f)
                win_rate = None
                deck_name = deck_data.get("name", "Unnamed Deck")
                if deck_name and deck_name in meta_stats.get("decks", {}):
                    stats = meta_stats["decks"][deck_name]
                    if stats.get("total_battles", 0) > 0:
                        win_rate = (stats.get("wins", 0) / stats["total_battles"]) * 100
                user_decks_details.append(
                    {
                        "name": deck_name,
                        "filename": filename,
                        "deck_id": deck_id,
                        "types": deck_data.get("deck_types", []),
                        "card_count": len(deck_data.get("cards", [])),
                        "win_rate": (
                            round(win_rate, 1) if win_rate is not None else None
                        ),
                        # 'cover_card': deck_data.get('cover_card_id') # Resolve to details if needed
                    }
                )
            except Exception as e:
                print(f"Error loading deck {filename} for profile: {e}")
        else:
            print(
                f"Deck file {filename} for user {user_record.get('username')} not found."
            )

    battle_history = current_app.config.get("battle_history", [])
    user_battles = []
    if user_record.get("username"):
        for battle in battle_history:
            if battle.get("player1") == user_record.get("username") or battle.get(
                "player2"
            ) == user_record.get("username"):
                user_battles.append(battle)

    return render_template(
        "profile.html",  # Your combined template name
        user_info=user_record,  # Pass the user's data dictionary
        decks=user_decks_details,
        battles=user_battles,
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
@login_required  # Ensure user is logged in to delete their own account
def delete_account():
    user_id_to_delete = str(flask_login_current_user.id)
    username_to_delete = flask_login_current_user.username  # Or fetch from users_dict

    if not user_id_to_delete:  # Should not happen if @login_required works
        flash("Error: Could not identify user for deletion.", "danger")
        return redirect(url_for("auth.user_profile_and_settings"))

    print(
        f"Attempting to delete account for user ID: {user_id_to_delete}, Username: {username_to_delete}"
    )

    users_dict = current_app.config["users"]
    save_users_func = current_app.config["save_users"]
    decks_dir = "decks"  # Assuming your deck files are in a 'decks' directory

    user_record = users_dict.get(user_id_to_delete)

    if not user_record:
        flash("Error: User record not found. Cannot delete.", "danger")
        # Log this as a serious issue
        print(
            f"CRITICAL: Attempt to delete non-existent user record for ID: {user_id_to_delete}"
        )
        # Log out just in case session is stale, though @login_required should handle
        logout_user()
        return redirect(url_for("main.index"))

    # 1. Delete user's deck files
    decks_owned_by_user = user_record.get("decks", [])
    print(f"User owns {len(decks_owned_by_user)} decks. Preparing to delete files.")
    for deck_id_str in decks_owned_by_user:
        deck_filename = f"{deck_id_str}.json"
        deck_path = os.path.join(decks_dir, deck_filename)
        if os.path.exists(deck_path):
            try:
                os.remove(deck_path)
                print(f"Deleted deck file: {deck_path}")
            except Exception as e:
                print(f"Error deleting deck file {deck_path}: {e}")
                # Decide if you want to halt deletion or just log and continue
                # For now, we'll log and continue to remove user record
        else:
            print(f"Deck file {deck_path} not found, but was listed for user.")

    # 2. Delete user entry from users.json (or user database)
    if user_id_to_delete in users_dict:
        del users_dict[user_id_to_delete]
        print(f"Removed user record for ID: {user_id_to_delete} from users_dict.")
    else:
        # Should have been caught by user_record check, but defensive
        print(
            f"Warning: User ID {user_id_to_delete} not in users_dict at final deletion stage."
        )

    # 3. Save the updated users.json
    try:
        save_users_func()
        print("users.json saved after deleting user.")
    except Exception as e:
        # This is problematic: user record might be gone from memory but not saved as deleted.
        # Or deck files deleted but user record deletion not persisted.
        # Needs careful thought for production (e.g., transactions, backup, restore user record to memory)
        print(
            f"CRITICAL ERROR: Failed to save users.json after deleting user record for ID: {user_id_to_delete}. Error: {e}"
        )
        flash(
            "A critical error occurred during account deletion. Please contact support.",
            "danger",
        )
        # Don't log the user out yet if the save failed, their session might still be valid for a broken state.
        return redirect(url_for("auth.user_profile_and_settings"))

    # 4. Log the user out
    logout_user()  # Clears Flask-Login session
    session.clear()  # Clear any remaining app-specific session data as well

    flash(
        "Your account and all associated data have been permanently deleted.", "success"
    )
    print(
        f"Account deletion successful for user ID: {user_id_to_delete}, Username: {username_to_delete}. User logged out."
    )
    return redirect(url_for("main.index"))  # Redirect to homepage
