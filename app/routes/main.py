from flask import (
    Blueprint,
    render_template,
    current_app,
) 
from flask_login import (
    current_user as flask_login_current_user,
)
main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    db = current_app.config.get("FIRESTORE_DB")  # Get Firestore client

    # Get card collection from app config (still from CardCollection loaded in memory)
    card_collection = current_app.config.get("card_collection", [])
    total_cards = len(card_collection)

    # --- Get Total Users from Firestore ---
    total_users = 0
    if db:
        try:
            # WARNING: Streaming all documents just to count can be inefficient for very large collections.
            # Consider a distributed counter for production if user numbers are huge.
            users_query = (
                db.collection("users").select([]).stream()
            )  # select([]) fetches only IDs, more efficient
            total_users = len(list(users_query))
        except Exception as e:
            current_app.logger.error(f"Error counting users from Firestore: {e}")
            # Fallback or set to a placeholder if count fails
            total_users = "N/A"
    else:
        total_users = "N/A"  # DB not available

    # --- Get Total Decks from Firestore ---
    total_decks = 0
    if db:
        try:
            # Same warning as for users regarding counting large collections.
            decks_query = db.collection("decks").select([]).stream()
            total_decks = len(list(decks_query))
        except Exception as e:
            current_app.logger.error(f"Error counting decks from Firestore: {e}")
            total_decks = "N/A"
    else:
        total_decks = "N/A"  # DB not available

    battle_history = current_app.config.get("battle_history", [])
    total_battles = len(battle_history)
    recent_battles = battle_history[-5:] if battle_history else []
    # TODO: Migrate battle_history to Firestore and update fetching here.

    meta_stats = current_app.config.get("meta_stats", {"decks": {}})
    top_decks_data = []
    if db:
        for deck_name, stats in meta_stats.get("decks", {}).items():
            if (
                stats.get("total_battles", 0) >= 5
            ):
                win_rate = (stats.get("wins", 0) / stats["total_battles"]) * 100

                deck_types_from_fs = []
                try:
                    deck_query_by_name = (
                        db.collection("decks")
                        .where("name", "==", deck_name)
                        .limit(1)
                        .stream()
                    )
                    for deck_doc_found in deck_query_by_name:
                        deck_data_fs = deck_doc_found.to_dict()
                        deck_types_from_fs = deck_data_fs.get("deck_types", [])
                        break
                except Exception as e_deck_type:
                    current_app.logger.error(
                        f"Error fetching types for deck '{deck_name}' from Firestore: {e_deck_type}"
                    )

                top_decks_data.append(
                    {
                        "name": deck_name,
                        "win_rate": round(win_rate, 1),
                        "types": deck_types_from_fs,
                    }
                )
    else:
        for deck_name, stats in meta_stats.get("decks", {}).items():
            if stats.get("total_battles", 0) >= 5:
                win_rate = (stats.get("wins", 0) / stats["total_battles"]) * 100
                top_decks_data.append(
                    {"name": deck_name, "win_rate": round(win_rate, 1), "types": []}
                )

    top_decks_data.sort(key=lambda x: x.get("win_rate", 0), reverse=True)
    top_decks_data = top_decks_data[:5]

    return render_template(
        "main_index.html",
        total_cards=total_cards,
        total_users=total_users,
        total_decks=total_decks,
        total_battles=total_battles,
        recent_battles=recent_battles,
        top_decks=top_decks_data,
        user_logged_in=flask_login_current_user.is_authenticated,
        username=(
            flask_login_current_user.username
            if flask_login_current_user.is_authenticated
            else None
        ),
    )