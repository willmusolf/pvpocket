# app/models.py
from flask_login import UserMixin, LoginManager
from flask import current_app

login_manager = LoginManager()
login_manager.login_view = "auth.login_prompt_page"
login_manager.login_message = "Please sign in with Google to access this page."
login_manager.login_message_category = "info"


class User(UserMixin):
    def __init__(self, user_id, data=None): 
        self.id = str(user_id)
        self.data = data if data is not None else {} 

        self.username = self.data.get("username", "")
        self.email = self.data.get("email", "")
        self.google_id = self.data.get("google_id", "")
        self.username_set = self.data.get("username_set", False)
        
        # Privacy settings
        self.email_visible_to_friends = self.data.get("email_visible_to_friends", False)
        self.profile_public = self.data.get("profile_public", True)

    def get_public_profile_data(self, is_friend=False):
        """Returns sanitized profile data for public viewing."""
        profile_data = {
            "username": self.username,
            "profile_icon": self.data.get("profile_icon", ""),
            "created_at": self.data.get("created_at"),
        }
        
        # Only include email if user allows friends to see it and viewer is a friend
        if is_friend and self.email_visible_to_friends:
            profile_data["email"] = self.email
            
        return profile_data


@login_manager.user_loader
def load_user(user_id_from_session):
    """Loads a user from Firestore given their user_id."""
    db = current_app.config.get("FIRESTORE_DB")
    if not db:
        print(
            "[LOAD_USER_FIRESTORE] Firestore client not available in app.config.",
            flush=True,
        )
        return None

    try:
        user_id_str = str(user_id_from_session)
        user_doc_ref = db.collection("users").document(user_id_str)
        user_doc = user_doc_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            return User(user_id=user_id_str, data=user_data)
        else:
            print(
                f"[LOAD_USER_FIRESTORE] User '{user_id_str}' not found in Firestore.",
                flush=True,
            )
            return None
    except Exception as e:
        print(
            f"Error loading user {user_id_from_session} from Firestore: {e}", flush=True
        )
        return None
