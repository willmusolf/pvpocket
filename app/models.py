# app/models.py
from flask_login import UserMixin, LoginManager
from flask import current_app  # For load_user to access app.config

# --- Flask-Login Setup ---
login_manager = LoginManager()
# Configure login view and messages here or in create_app after init_app
login_manager.login_view = (
    "auth.login_prompt_page"  # Default if not overridden in create_app
)
login_manager.login_message = "Please sign in with Google to access this page."
login_manager.login_message_category = "info"


class User(UserMixin):  # UserMixin provides default implementations for Flask-Login
    def __init__(self, user_id, username, email=None, data=None):
        self.id = user_id  # Flask-Login expects this to be 'id'
        self.username = username
        self.email = email
        # Ensure data is always a dict, even if None is passed
        self.data = data if data is not None else {}


# In app/models.py (or app/__init__.py if defined there)
@login_manager.user_loader
def load_user(user_id_from_session):  # Changed name for clarity
    print(
        f"[LOAD_USER_DEBUG] load_user called with user_id_from_session: '{user_id_from_session}' (type: {type(user_id_from_session)})"
    )

    users_data = current_app.config.get("users", {})
    # Ensure user_id_from_session is used as a string key if your users_dict keys are strings
    user_info = users_data.get(str(user_id_from_session))

    if user_info:
        print(f"[LOAD_USER_DEBUG] User info found: {user_info}")
        # Ensure you are instantiating your defined User class
        user_instance = User(
            user_id=str(user_id_from_session),  # Pass the original ID
            username=user_info.get("username"),
            email=user_info.get("email"),
            data=user_info,
        )
        print(
            f"[LOAD_USER_DEBUG] Returning User instance: ID={user_instance.id}, Username={user_instance.username}"
        )
        return user_instance
    else:
        print(
            f"[LOAD_USER_DEBUG] User ID '{user_id_from_session}' NOT found in users_data."
        )
        return None
