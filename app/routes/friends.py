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

    transaction = db.transaction()
    current_user_ref = db.collection("users").document(current_user_id)
    sender_ref = db.collection("users").document(sender_id)
    accept_request_transaction(transaction, current_user_ref, sender_ref)

    return jsonify({"success": True, "message": "Friend request accepted."})


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
