from flask import (
    Blueprint,
    render_template,
    current_app,
    request,
    jsonify,
    Response,
    redirect,
    url_for,
) 
from flask_login import (
    current_user as flask_login_current_user,
)
import requests
from datetime import datetime
from ..services import database_service, card_service

main_bp = Blueprint("main", __name__)


@main_bp.route("/health")
def simple_health_check():
    """Simple public health check endpoint."""
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()}), 200




@main_bp.route("/")
def index():
    db = current_app.config.get("FIRESTORE_DB")  # Get Firestore client

    # Get card collection from cache manager for better performance tracking
    card_collection = card_service.get_card_collection()
    total_cards = len(card_collection) if card_collection else 0

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




@main_bp.route("/test-scalability")
def test_scalability():
    """Test endpoint to verify scalability systems are working."""
    try:
        from ..cache_manager import cache_manager
        from ..db_service import db_service
        
        # Only log scalability tests in development
        if current_app.debug:
            current_app.logger.debug("🧪 TESTING SCALABILITY SYSTEMS")
        
        results = {
            "cache_status": "❌ Failed",
            "db_status": "❌ Failed", 
            "card_service_status": "❌ Failed",
            "total_cards": 0
        }
        
        # Test cache
        if cache_manager.health_check():
            results["cache_status"] = "✅ Healthy"
            if current_app.debug:
                current_app.logger.debug("✅ Cache system is working")
        
        # Test database
        if db_service.health_check():
            results["db_status"] = "✅ Healthy"
            if current_app.debug:
                current_app.logger.debug("✅ Database system is working")
        
        # Test card service
        try:
            collection = card_service.get_card_collection()
            results["card_service_status"] = "✅ Working"
            results["total_cards"] = len(collection)
            if current_app.debug:
                current_app.logger.debug(f"✅ Card service loaded {len(collection)} cards")
        except Exception as e:
            if current_app.debug:
                current_app.logger.debug(f"❌ Card service error: {e}")
        
        if current_app.debug:
            current_app.logger.debug("🧪 SCALABILITY TEST COMPLETE")
        return jsonify(results)
        
    except Exception as e:
        if current_app.debug:
            current_app.logger.debug(f"❌ TEST ERROR: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/dashboard")
def dashboard():
    """Dashboard page."""
    if not flask_login_current_user.is_authenticated:
        return redirect(url_for('auth.login_prompt_page'))
    return render_template("dashboard.html")


@main_bp.route("/profile")
def profile():
    """Profile page."""
    if not flask_login_current_user.is_authenticated:
        return redirect(url_for('auth.login_prompt_page'))
    return render_template("profile.html")


@main_bp.route("/api/profile", methods=["GET"])
def get_profile():
    """Get user profile API."""
    if not flask_login_current_user.is_authenticated:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        db = database_service.get_db()
        user_doc = db.collection("users").document(flask_login_current_user.id).get()
        
        if not user_doc.exists:
            return jsonify({"error": "User not found"}), 404
        
        user_data = user_doc.to_dict()
        # Remove sensitive fields
        safe_data = {k: v for k, v in user_data.items() 
                    if k not in ['password', 'secret_key', 'api_key', 'token']}
        
        return jsonify(safe_data)
    except Exception as e:
        current_app.logger.error(f"Error getting profile: {e}")
        return jsonify({"error": "Internal server error"}), 500


@main_bp.route("/api/profile/update", methods=["POST"])
def update_profile():
    """Update user profile API."""
    if not flask_login_current_user.is_authenticated:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate profile icon URL
        profile_icon = data.get('profile_icon')
        if profile_icon and 'javascript:' in profile_icon.lower():
            return jsonify({"error": "Invalid profile icon URL"}), 400
        
        db = database_service.get_db()
        user_ref = db.collection("users").document(flask_login_current_user.id)
        
        # Only allow certain fields to be updated
        allowed_fields = ['profile_icon', 'display_name']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if update_data:
            user_ref.update(update_data)
            return jsonify({"success": True, "updated": update_data})
        else:
            return jsonify({"error": "No valid fields to update"}), 400
    
    except Exception as e:
        current_app.logger.error(f"Error updating profile: {e}")
        return jsonify({"error": "Internal server error"}), 500


@main_bp.route("/api/search")
def search_api():
    """Global search API."""
    if not flask_login_current_user.is_authenticated:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        query = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'cards')
        
        if not query:
            return jsonify({"results": []})
        
        # Sanitize input
        if '<script>' in query.lower() or 'javascript:' in query.lower():
            return jsonify({"error": "Invalid search query"}), 400
        
        if search_type == 'cards':
            card_collection = card_service.get_card_collection()
            # Simple search implementation
            results = []
            return jsonify({"results": results})
        
        elif search_type == 'users':
            from ..services import database_service
            db = database_service.get_db()
            
            # Search users by username
            users_query = db.collection("users").where("username_lowercase", ">=", query.lower()).limit(10)
            users = []
            for user_doc in users_query.stream():
                user_data = user_doc.to_dict()
                users.append({
                    "id": user_doc.id,
                    "username": user_data.get("username"),
                    "profile_icon": user_data.get("profile_icon")
                })
            return jsonify({"results": users})
        
        else:
            return jsonify({"error": "Invalid search type"}), 400
    
    except Exception as e:
        current_app.logger.error(f"Error in search: {e}")
        return jsonify({"error": "Internal server error"}), 500


@main_bp.route("/api/activity/recent")
def recent_activity():
    """Get recent user activity."""
    if not flask_login_current_user.is_authenticated:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        db = database_service.get_db()
        
        # Get recent activity for user
        activity_query = (db.collection("users")
                         .document(flask_login_current_user.id)
                         .collection("activity")
                         .order_by("timestamp", direction="DESCENDING")
                         .limit(20))
        
        activities = []
        for activity_doc in activity_query.stream():
            activities.append(activity_doc.to_dict())
        
        return jsonify({"activities": activities})
    
    except Exception as e:
        current_app.logger.error(f"Error getting recent activity: {e}")
        return jsonify({"error": "Internal server error"}), 500


@main_bp.route("/api/activity/history")
def activity_history():
    """Get activity history with pagination."""
    if not flask_login_current_user.is_authenticated:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 50)
        
        # Activity history implementation would go here
        return jsonify({"activities": [], "pagination": {"page": page, "has_more": False}})
    
    except Exception as e:
        current_app.logger.error(f"Error getting activity history: {e}")
        return jsonify({"error": "Internal server error"}), 500


@main_bp.route("/api/navbar/user-info")
def navbar_user_info():
    """Get user info for navbar."""
    if not flask_login_current_user.is_authenticated:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        return jsonify({
            "username": getattr(flask_login_current_user, 'username', 'User'),
            "profile_icon": getattr(flask_login_current_user, 'profile_icon', ''),
            "deck_count": len(getattr(flask_login_current_user, 'deck_ids', []))
        })
    
    except Exception as e:
        current_app.logger.error(f"Error getting navbar user info: {e}")
        return jsonify({"error": "Internal server error"}), 500


@main_bp.route("/api/dashboard/recent-decks")
def dashboard_recent_decks():
    """Get recent decks for dashboard."""
    if not flask_login_current_user.is_authenticated:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        db = database_service.get_db()
        
        # Get user's recent decks
        user_data = getattr(flask_login_current_user, 'data', {})
        deck_ids = user_data.get('deck_ids', [])
        
        if not deck_ids:
            return jsonify({"decks": []})
        
        # Get recent decks (limit to 5)
        deck_refs = [db.collection("decks").document(deck_id) for deck_id in deck_ids[:5]]
        deck_docs = db.get_all(deck_refs)
        
        decks = []
        for deck_doc in deck_docs:
            if deck_doc.exists:
                deck_data = deck_doc.to_dict()
                decks.append({
                    "id": deck_doc.id,
                    "name": deck_data.get("name"),
                    "updated_at": deck_data.get("updated_at"),
                    "is_public": deck_data.get("is_public", False)
                })
        
        # Sort by updated_at
        decks.sort(key=lambda x: x.get("updated_at") or datetime.min, reverse=True)
        
        return jsonify({"recent_decks": decks})
    
    except Exception as e:
        current_app.logger.error(f"Error getting recent decks: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Legal and informational pages for Google Ads approval
@main_bp.route("/about")
def about():
    """About page with substantial Pokemon TCG content."""
    db = current_app.config.get("FIRESTORE_DB")
    
    # Get stats for the about page
    total_users = 0
    total_decks = 0
    total_battles = 0
    
    if db:
        try:
            # Get user count
            users_query = db.collection("users").select([]).stream()
            total_users = len(list(users_query))
            
            # Get deck count
            decks_query = db.collection("decks").select([]).stream()
            total_decks = len(list(decks_query))
            
            # Get battle count (if we have it stored)
            try:
                meta_doc = db.collection("internal_config").document("meta_stats").get()
                if meta_doc.exists:
                    meta_stats = meta_doc.to_dict()
                    total_battles = sum(deck_stats.get("total_battles", 0) 
                                      for deck_stats in meta_stats.get("decks", {}).values())
            except Exception as e:
                current_app.logger.error(f"Error getting battle count: {e}")
                total_battles = 0
                
        except Exception as e:
            current_app.logger.error(f"Error getting stats for about page: {e}")
    
    return render_template(
        "about.html",
        total_users=total_users,
        total_decks=total_decks,
        total_battles=total_battles
    )


@main_bp.route("/privacy-policy")
def privacy_policy():
    """Privacy Policy page for legal compliance."""
    return render_template("privacy_policy.html")


@main_bp.route("/terms-of-service")
def terms_of_service():
    """Terms of Service page for legal compliance."""
    return render_template("terms_of_service.html")


@main_bp.route("/faq")
def faq():
    """Frequently Asked Questions page."""
    return render_template("faq.html")


@main_bp.route("/support")
def support():
    """Support contact page."""
    return render_template("support.html")


# Redirect old routes to new ones for SEO
@main_bp.route("/privacy")
def privacy_redirect():
    """Redirect old privacy URL to new one."""
    return redirect(url_for("main.privacy_policy"), code=301)


@main_bp.route("/terms")
def terms_redirect():
    """Redirect old terms URL to new one.""" 
    return redirect(url_for("main.terms_of_service"), code=301)


# Add alias for main index route
@main_bp.route("/home")
def main_index():
    """Alias for the main index page."""
    return redirect(url_for("main.index"), code=301)


@main_bp.route("/api/support", methods=["POST"])
def submit_support_request():
    """Handle support form submissions by storing them in Firestore."""
    try:
        db = current_app.config.get("FIRESTORE_DB")
        if not db:
            current_app.logger.error("Database not available for support ticket")
            return jsonify({"error": "Database not available"}), 500
            
        # Get form data
        data = request.get_json()
        current_app.logger.info(f"Support request received: {data}")
        
        if not data:
            current_app.logger.error("No data provided in support request")
            return jsonify({"error": "No data provided"}), 400
            
        # Check if user is authenticated
        if not flask_login_current_user.is_authenticated:
            current_app.logger.error("Unauthenticated user attempted to submit support request")
            return jsonify({"error": "You must be logged in to submit a support request"}), 401
        
        # Get user's email from their account
        email = flask_login_current_user.email
        if not email:
            current_app.logger.error("User has no email address")
            return jsonify({"error": "Your account must have an email address to submit support requests"}), 400
        
        # Validate required fields (email no longer required from form)
        required_fields = ["name", "subject", "message"]
        for field in required_fields:
            if not data.get(field):
                current_app.logger.error(f"Missing required field in support request: {field}")
                return jsonify({"error": f"Missing required field: {field}"}), 400
            
        # Prepare support ticket data
        support_ticket = {
            "name": data.get("name", "").strip()[:100],  # Limit length
            "email": email[:100],  # Use account email
            "subject": data.get("subject", "").strip()[:200],
            "message": data.get("message", "").strip()[:2000],
            "timestamp": datetime.utcnow(),
            "status": "new",
            "user_id": flask_login_current_user.get_id(),  # User is authenticated
            "ip_address": request.remote_addr
        }
        
        # Store in Firestore
        doc_ref = db.collection("support_tickets").add(support_ticket)
        
        current_app.logger.info(f"Support ticket created: {doc_ref[1].id}")
        
        return jsonify({"success": True, "message": "Support request submitted successfully"}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error submitting support request: {e}")
        return jsonify({"error": "Failed to submit support request"}), 500

