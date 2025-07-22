from flask import (
    Blueprint,
    render_template,
    current_app,
    request,
    jsonify,
    Response,
) 
from flask_login import (
    current_user as flask_login_current_user,
)
import requests
from datetime import datetime

main_bp = Blueprint("main", __name__)


@main_bp.route("/health")
def health_check():
    """Health check endpoint for internal services."""
    try:
        from ..cache_manager import cache_manager
        from ..db_service import db_service
        from ..task_queue import task_queue
        
        health_status = {
            "cache": cache_manager.health_check(),
            "database": db_service.health_check(),
            "task_queue": task_queue.health_check(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        overall_healthy = all(health_status.values())
        status_code = 200 if overall_healthy else 503
        
        return jsonify({
            "status": "healthy" if overall_healthy else "unhealthy",
            "components": health_status
        }), status_code
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "error": str(e)
        }), 500


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


@main_bp.route("/api/proxy-image")
def proxy_image():
    """Proxy for images to handle CORS issues (development) and CDN CORS fallback (production)"""
    try:
        image_url = request.args.get('url')
        if not image_url:
            return jsonify({"error": "No URL provided"}), 400
        
        # Validate URL is from expected domains
        allowed_domains = [
            'storage.googleapis.com',
            'firebasestorage.googleapis.com',
            'cdn.pvpocket.xyz'  # Allow CDN URLs for CORS fallback
        ]
        
        if not any(domain in image_url for domain in allowed_domains):
            return jsonify({"error": "Invalid domain"}), 400
        
        # Fetch from Firebase Storage
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Return the image with CORS headers
        return Response(
            response.content,
            mimetype=response.headers.get('content-type', 'image/png'),
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Cache-Control': 'public, max-age=3600'
            }
        )
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error fetching image: {e}")
        return jsonify({"error": "Failed to fetch image"}), 500
    except Exception as e:
        current_app.logger.error(f"Error in proxy_image: {e}")
        return jsonify({"error": "Internal server error"}), 500


@main_bp.route("/test-scalability-dashboard")
def test_scalability_dashboard():
    """Web-based scalability testing dashboard."""
    return render_template("test_scalability.html")


@main_bp.route("/test-scalability")
def test_scalability():
    """Test endpoint to verify scalability systems are working."""
    try:
        from ..services import card_service
        from ..cache_manager import cache_manager
        from ..db_service import db_service
        
        print("🧪 TESTING SCALABILITY SYSTEMS")
        
        results = {
            "cache_status": "❌ Failed",
            "db_status": "❌ Failed", 
            "card_service_status": "❌ Failed",
            "total_cards": 0
        }
        
        # Test cache
        if cache_manager.health_check():
            results["cache_status"] = "✅ Healthy"
            print("✅ Cache system is working")
        
        # Test database
        if db_service.health_check():
            results["db_status"] = "✅ Healthy"
            print("✅ Database system is working")
        
        # Test card service
        try:
            collection = card_service.get_card_collection()
            results["card_service_status"] = "✅ Working"
            results["total_cards"] = len(collection)
            print(f"✅ Card service loaded {len(collection)} cards")
        except Exception as e:
            print(f"❌ Card service error: {e}")
        
        print("🧪 SCALABILITY TEST COMPLETE")
        return jsonify(results)
        
    except Exception as e:
        print(f"❌ TEST ERROR: {e}")
        return jsonify({"error": str(e)}), 500

