# app/models.py
from flask_login import UserMixin, LoginManager
from flask import current_app
from .cache_manager import cache_manager

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
    """Loads a user from cache first, then Firestore if needed."""
    if not user_id_from_session:
        return None
        
    user_id_str = str(user_id_from_session)
    
    # Try to get from Redis cache first
    try:
        cached_user_data = cache_manager.get_user_data(user_id_str)
        if cached_user_data:
            return User(user_id=user_id_str, data=cached_user_data)
    except Exception as e:
        # Only log cache errors in debug mode
        if current_app and current_app.debug:
            print(f"[LOAD_USER_CACHE] Error loading user from cache: {e}", flush=True)
    
    # Fallback to Firestore if not in cache
    db = current_app.config.get("FIRESTORE_DB")
    if not db:
        # Only log critical errors in debug mode
        if current_app and current_app.debug:
            print(
                "[LOAD_USER_FIRESTORE] Firestore client not available in app.config.",
                flush=True,
            )
        return None

    try:
        user_doc_ref = db.collection("users").document(user_id_str)
        user_doc = user_doc_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            # Cache the user data for future requests (30 minute TTL)
            cache_manager.set_user_data(user_id_str, user_data, ttl_minutes=30)
            return User(user_id=user_id_str, data=user_data)
        else:
            # Only log user not found in debug mode
            if current_app and current_app.debug:
                print(
                    f"[LOAD_USER_FIRESTORE] User '{user_id_str}' not found in Firestore.",
                    flush=True,
                )
            return None
    except Exception as e:
        # Only log Firestore errors in debug mode
        if current_app and current_app.debug:
            print(
                f"Error loading user {user_id_from_session} from Firestore: {e}", flush=True
            )
        return None
