from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    current_app,
    flash,
    redirect,
    url_for,
)
from flask_login import login_required, current_user as flask_login_current_user
from firebase_admin import firestore
from Deck import Deck
from ..models import User
from ..services import card_service, url_service
import datetime
from better_profanity import profanity

friends_bp = Blueprint("friends", __name__, url_prefix="/friends")


# Helper function to get user data for display
def _get_user_snapshot(user_id):
    db = current_app.config.get("FIRESTORE_DB")
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()
    if user_doc.exists:
        user_data = user_doc.to_dict()
        return {
            "id": user_doc.id,
            "username": user_data.get("username", "Unknown"),
            "profile_icon": user_data.get("profile_icon", ""),
        }
    return None


@friends_bp.route("/")
@login_required
def friends_page():
    db = current_app.config.get("FIRESTORE_DB")
    user_id = flask_login_current_user.id

    # Fetch current friends
    friends_ref = (
        db.collection("users").document(user_id).collection("friends").stream()
    )
    friends = [_get_user_snapshot(friend.id) for friend in friends_ref]

    # Fetch pending requests (sent and received)
    requests_ref = (
        db.collection("users").document(user_id).collection("friend_requests").stream()
    )
    sent_requests = []
    received_requests = []
    for req in requests_ref:
        req_data = req.to_dict()
        user_info = _get_user_snapshot(req.id)
        if user_info:
            if req_data.get("status") == "sent":
                sent_requests.append(user_info)
            elif req_data.get("status") == "received":
                received_requests.append(user_info)

    return render_template(
        "friends.html",
        friends=friends,
        sent_requests=sent_requests,
        received_requests=received_requests,
    )


@friends_bp.route("/api/friends", methods=["GET"])
@login_required
def get_friends_api():
    """API endpoint to get friends with pagination support."""
    db = current_app.config.get("FIRESTORE_DB")
    user_id = flask_login_current_user.id
    
    try:
        # Get pagination parameters
        try:
            page = max(1, int(request.args.get("page", 1)))
            limit = min(max(1, int(request.args.get("limit", 20))), 100)  # Max 100 friends per page, default 20
        except ValueError:
            return jsonify({"error": "Invalid pagination parameters", "friends": []}), 400
        
        offset = (page - 1) * limit
        
        # Get all friend documents
        friends_ref = (
            db.collection("users").document(user_id).collection("friends").stream()
        )
        
        # Convert to list and sort by friended_at (most recent first)
        all_friends = []
        for friend in friends_ref:
            friend_data = friend.to_dict()
            user_info = _get_user_snapshot(friend.id)
            if user_info:
                user_info['friended_at'] = friend_data.get('friended_at')
                all_friends.append(user_info)
        
        # Sort by friended_at (most recent first), then by username
        all_friends.sort(key=lambda f: (
            f.get('friended_at') or datetime.datetime.min, 
            f.get('username', '').lower()
        ), reverse=True)
        
        # Apply pagination
        total_count = len(all_friends)
        paginated_friends = all_friends[offset:offset + limit]
        has_more = offset + limit < total_count
        
        # Remove friended_at from response (internal field)
        for friend in paginated_friends:
            friend.pop('friended_at', None)
        
        return jsonify({
            "friends": paginated_friends,
            "pagination": {
                "current_page": page,
                "total_count": total_count,
                "has_more": has_more,
                "page_size": limit
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_friends_api for user {user_id}: {e}")
        return jsonify({"error": "An internal error occurred.", "friends": []}), 500


@friends_bp.route("/search", methods=["POST"])
@login_required
def search_users():
    db = current_app.config.get("FIRESTORE_DB")
    query = request.json.get("query", "").strip().lower()

    if not query or len(query) < 3:
        return jsonify({"error": "Search query must be at least 3 characters."}), 400

    users_ref = db.collection("users")
    # This query requires a composite index in Firestore
    query_result = (
        users_ref.where("username_lowercase", ">=", query)
        .where("username_lowercase", "<=", query + "\uf8ff")
        .limit(10)
        .stream()
    )

    current_user_id = flask_login_current_user.id
    results = [
        _get_user_snapshot(doc.id) for doc in query_result if doc.id != current_user_id
    ]

    return jsonify(results)


@friends_bp.route("/request", methods=["POST"])
@login_required
def send_friend_request():
    db = current_app.config.get("FIRESTORE_DB")
    sender_id = flask_login_current_user.id
    recipient_id = request.json.get("recipient_id")

    if not recipient_id or sender_id == recipient_id:
        return jsonify({"error": "Invalid request."}), 400

    try:
        batch = db.batch()

        # Mark as 'sent' for the sender
        sender_req_ref = (
            db.collection("users")
            .document(sender_id)
            .collection("friend_requests")
            .document(recipient_id)
        )
        batch.set(
            sender_req_ref, {"status": "sent", "timestamp": firestore.SERVER_TIMESTAMP}
        )

        # Mark as 'received' for the recipient
        recipient_req_ref = (
            db.collection("users")
            .document(recipient_id)
            .collection("friend_requests")
            .document(sender_id)
        )
        batch.set(
            recipient_req_ref,
            {"status": "received", "timestamp": firestore.SERVER_TIMESTAMP},
        )

        batch.commit()
        return jsonify({"success": True, "message": "Friend request sent."})
    except Exception as e:
        current_app.logger.error(
            f"Error sending friend request from {sender_id} to {recipient_id}: {e}"
        )
        return jsonify({"error": "An unexpected error occurred."}), 500

@friends_bp.route("/accept", methods=["POST"])
@login_required
def accept_friend_request():
    db = current_app.config.get("FIRESTORE_DB")
    current_user_id = flask_login_current_user.id
    sender_id = request.json.get("sender_id")

    if not sender_id:
        return jsonify({"error": "Invalid request. Sender ID missing."}), 400

    @firestore.transactional
    def accept_request_transaction(transaction, current_user_ref, sender_ref):
        # 1. Delete requests from both users
        transaction.delete(
            current_user_ref.collection("friend_requests").document(sender_id)
        )
        transaction.delete(
            sender_ref.collection("friend_requests").document(current_user_id)
        )

        # 2. Add friend documents for both users
        timestamp = firestore.SERVER_TIMESTAMP
        transaction.set(
            current_user_ref.collection("friends").document(sender_id),
            {"friended_at": timestamp},
        )
        transaction.set(
            sender_ref.collection("friends").document(current_user_id),
            {"friended_at": timestamp},
        )

    try:
        transaction = db.transaction()
        current_user_ref = db.collection("users").document(current_user_id)
        sender_ref = db.collection("users").document(sender_id)
        accept_request_transaction(transaction, current_user_ref, sender_ref)

        # Get the new friend's data to return to the frontend
        new_friend_data = _get_user_snapshot(sender_id)
        if new_friend_data:
            return jsonify({
                "success": True, 
                "message": "Friend request accepted.",
                "friend": new_friend_data
            })
        else:
            # This case is unlikely but handled for robustness
            return jsonify({"success": True, "message": "Friend request accepted, but friend data could not be retrieved."})

    except Exception as e:
        current_app.logger.error(f"Error accepting friend request from {sender_id} for user {current_user_id}: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

@friends_bp.route("/remove", methods=["POST"])
@login_required
def remove_friend():
    db = current_app.config.get("FIRESTORE_DB")
    current_user_id = flask_login_current_user.id
    friend_id = request.json.get("friend_id")

    @firestore.transactional
    def remove_friend_transaction(transaction, current_user_ref, friend_ref):
        transaction.delete(current_user_ref.collection("friends").document(friend_id))
        transaction.delete(friend_ref.collection("friends").document(current_user_id))

    transaction = db.transaction()
    current_user_ref = db.collection("users").document(current_user_id)
    friend_ref = db.collection("users").document(friend_id)
    remove_friend_transaction(transaction, current_user_ref, friend_ref)

    return jsonify({"success": True, "message": "Friend removed."})


@friends_bp.route("/decline", methods=["POST"])
@login_required
def decline_friend_request():
    db = current_app.config.get("FIRESTORE_DB")
    current_user_id = flask_login_current_user.id
    sender_id = request.json.get("sender_id")

    # Use a transaction to delete the request from both users' subcollections
    @firestore.transactional
    def decline_request_transaction(transaction, current_user_ref, sender_ref):
        transaction.delete(
            current_user_ref.collection("friend_requests").document(sender_id)
        )
        transaction.delete(
            sender_ref.collection("friend_requests").document(current_user_id)
        )

    transaction = db.transaction()
    current_user_ref = db.collection("users").document(current_user_id)
    sender_ref = db.collection("users").document(sender_id)
    decline_request_transaction(transaction, current_user_ref, sender_ref)

    return jsonify({"success": True, "message": "Friend request declined."})


@friends_bp.route("/<user_id>/decks")
@login_required
def view_friend_decks(user_id):
    """View a friend's public decks."""
    db = current_app.config.get("FIRESTORE_DB")
    current_user_id = flask_login_current_user.id
    
    # Check if user_id is a friend
    friend_doc = db.collection("users").document(current_user_id).collection("friends").document(user_id).get()
    if not friend_doc.exists:
        flash("You can only view decks of your friends.", "error")
        return redirect(url_for("friends.friends_page"))
    
    # Get friend's info
    friend_info = _get_user_snapshot(user_id)
    if not friend_info:
        flash("Friend not found.", "error")
        return redirect(url_for("friends.friends_page"))
    
    # Get friend's public decks
    card_collection = card_service.get_card_collection()
    # Get all public decks for this user
    decks_query = (
        db.collection("decks")
        .where("owner_id", "==", user_id)
        .where("is_public", "==", True)
    )
    
    # Collect all decks first for sorting and pagination
    all_decks = []
    for deck_doc in decks_query.stream():
        try:
            deck = Deck.from_firestore_doc(deck_doc, card_collection)
            
            # Resolve cover cards similar to collection.py with deduplication
            resolved_cover_cards = []
            seen_card_ids = set()
            if deck.cover_card_ids and card_collection:
                for c_id_str in deck.cover_card_ids:
                    if c_id_str and c_id_str not in seen_card_ids:
                        try:
                            card_obj = card_collection.get_card_by_id(int(c_id_str))
                            if card_obj:
                                # Get the correct base URL from the app's central config
                                # Process URL for CDN conversion on server side
                                image_path = getattr(card_obj, "firebase_image_url", None)
                                firebase_image_url = url_service.process_firebase_to_cdn_url(image_path)
                                    
                                resolved_cover_cards.append({
                                    "name": getattr(card_obj, "name", "N/A"),
                                    "firebase_image_url": firebase_image_url,
                                })
                                seen_card_ids.add(c_id_str)
                                # Limit to 3 cover cards maximum
                                if len(resolved_cover_cards) >= 3:
                                    break
                        except (ValueError, TypeError):
                            pass
            
            # Add resolved cover cards to the deck object
            deck.resolved_cover_cards = resolved_cover_cards
            all_decks.append(deck)
        except Exception as e:
            current_app.logger.error(f"Error loading deck {deck_doc.id}: {e}")
    
    # Sort by created_at in memory (most recent first)
    all_decks.sort(key=lambda deck: deck.created_at or datetime.datetime.min, reverse=True)
    
    # For initial page load, show up to 12 decks
    displayed_decks = all_decks[:12]
    
    return render_template(
        "friend_decks.html", 
        friend=friend_info, 
        decks=displayed_decks,
        total_decks=len(all_decks)
    )


@friends_bp.route("/<user_id>/decks/api", methods=["GET"])
@login_required
def get_friend_decks_api(user_id):
    """API endpoint to get friend's public decks with pagination support."""
    db = current_app.config.get("FIRESTORE_DB")
    current_user_id = flask_login_current_user.id
    
    try:
        # Get pagination parameters
        try:
            page = max(1, int(request.args.get("page", 1)))
            limit = min(max(1, int(request.args.get("limit", 12))), 50)  # Max 50 decks per page, default 12
        except ValueError:
            return jsonify({"error": "Invalid pagination parameters", "decks": []}), 400
        
        offset = (page - 1) * limit
        
        # Check if user_id is a friend
        friend_doc = db.collection("users").document(current_user_id).collection("friends").document(user_id).get()
        if not friend_doc.exists:
            return jsonify({"error": "You can only view decks of your friends.", "decks": []}), 403
        
        # Get friend's public decks
        card_collection = card_service.get_card_collection()
        decks_query = (
            db.collection("decks")
            .where("owner_id", "==", user_id)
            .where("is_public", "==", True)
        )
        
        # Collect all decks first for sorting and pagination
        all_decks = []
        for deck_doc in decks_query.stream():
            try:
                deck = Deck.from_firestore_doc(deck_doc, card_collection)
                
                # Resolve cover cards similar to friends.py
                resolved_cover_cards = []
                seen_card_ids = set()
                if deck.cover_card_ids and card_collection:
                    for c_id_str in deck.cover_card_ids:
                        if c_id_str and c_id_str not in seen_card_ids:
                            try:
                                card_obj = card_collection.get_card_by_id(int(c_id_str))
                                if card_obj:
                                    # Get the correct base URL from the app's central config
                                    base_url = current_app.config['ASSET_BASE_URL']
                                    image_path = getattr(card_obj, "firebase_image_url", None)
                                    firebase_image_url = url_service.process_firebase_to_cdn_url(image_path, base_url)
                                        
                                    resolved_cover_cards.append({
                                        "name": getattr(card_obj, "name", "N/A"),
                                        "firebase_image_url": firebase_image_url,
                                    })
                                    seen_card_ids.add(c_id_str)
                                    # Limit to 3 cover cards maximum
                                    if len(resolved_cover_cards) >= 3:
                                        break
                            except (ValueError, TypeError):
                                pass
                
                # Convert deck to JSON-serializable format
                deck_data = {
                    "id": deck.id,
                    "name": deck.name,
                    "deck_types": deck.deck_types,
                    "card_count": len(deck.cards),
                    "description": deck.description or "",
                    "resolved_cover_cards": resolved_cover_cards,
                    "created_at": deck.created_at,
                    "updated_at": deck.updated_at
                }
                all_decks.append(deck_data)
                
            except Exception as e:
                current_app.logger.error(f"Error loading deck {deck_doc.id}: {e}")
        
        # Sort by created_at (most recent first)
        all_decks.sort(key=lambda deck: deck.get("created_at") or datetime.datetime.min, reverse=True)
        
        # Apply pagination
        total_count = len(all_decks)
        paginated_decks = all_decks[offset:offset + limit]
        has_more = offset + limit < total_count
        
        return jsonify({
            "decks": paginated_decks,
            "pagination": {
                "current_page": page,
                "total_count": total_count,
                "has_more": has_more,
                "page_size": limit
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_friend_decks_api for user {user_id}: {e}")
        return jsonify({"error": "An internal error occurred.", "decks": []}), 500


@friends_bp.route("/<user_id>/profile")
@login_required
def view_friend_profile(user_id):
    """View a friend's profile card."""
    db = current_app.config.get("FIRESTORE_DB")
    current_user_id = flask_login_current_user.id
    
    # Check if user_id is a friend
    friend_doc = db.collection("users").document(current_user_id).collection("friends").document(user_id).get()
    if not friend_doc.exists:
        return jsonify({"error": "You can only view profiles of your friends."}), 403
    
    # Get friend's data
    user_doc = db.collection("users").document(user_id).get()
    if not user_doc.exists:
        return jsonify({"error": "User not found."}), 404
    
    friend_user = User(user_id, user_doc.to_dict())
    profile_data = friend_user.get_public_profile_data(is_friend=True)
    
    # Get friend's stats
    decks_count = len(list(db.collection("decks").where("owner_id", "==", user_id).stream()))
    public_decks_count = len(list(db.collection("decks").where("owner_id", "==", user_id).where("is_public", "==", True).stream()))
    
    profile_data.update({
        "user_id": user_id,
        "decks_count": decks_count,
        "public_decks_count": public_decks_count,
    })
    
    return jsonify(profile_data)


@friends_bp.route("/deck/<deck_id>/toggle-privacy", methods=["POST"])
@login_required
def toggle_deck_privacy(deck_id):
    """Toggle privacy of user's own deck."""
    db = current_app.config.get("FIRESTORE_DB")
    current_user_id = flask_login_current_user.id
    card_collection = card_service.get_card_collection()
    
    # Get the deck
    deck_doc = db.collection("decks").document(deck_id).get()
    if not deck_doc.exists:
        return jsonify({"error": "Deck not found."}), 404
    
    deck = Deck.from_firestore_doc(deck_doc, card_collection)
    
    # Check ownership
    if deck.owner_id != current_user_id:
        return jsonify({"error": "You can only modify your own decks."}), 403
    
    # Toggle privacy
    description = request.json.get("description", "").strip()
    
    # Length check for description
    if description and len(description) > 100:
        return jsonify({"error": "Description must be 100 characters or less."}), 400
    
    # Profanity check for description
    if description and profanity.contains_profanity(description):
        return jsonify({"error": "Description contains inappropriate language. Please use appropriate language."}), 400
    
    old_privacy = deck.is_public
    new_privacy = deck.toggle_privacy()
    
    if new_privacy and description:
        deck.description = description
    
    # Save to Firestore - only update privacy-related fields to avoid changing updated_at
    try:
        update_data = {
            "is_public": new_privacy,
            "shared_at": deck.shared_at,
            "description": deck.description
        }
        db.collection("decks").document(deck_id).update(update_data)
        
        action = "made public" if new_privacy else "made private"
        return jsonify({
            "success": True, 
            "message": f"Deck {action} successfully.",
            "is_public": new_privacy
        })
    except Exception as e:
        current_app.logger.error(f"Error updating deck privacy: {e}")
        return jsonify({"error": "Failed to update deck privacy."}), 500
