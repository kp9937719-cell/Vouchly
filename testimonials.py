"""
testimonials.py — Testimonial Management Module
=================================================
Handles public testimonial submission and owner moderation.

PUBLIC routes (no login needed):
  POST /api/public/spaces/<slug>/testimonials  — Customer submits a testimonial

PRIVATE routes (login required):
  GET    /api/spaces/<space_id>/testimonials           — List testimonials for a space
  GET    /api/testimonials/<id>                        — Get single testimonial
  PATCH  /api/testimonials/<id>                        — Edit testimonial content
  DELETE /api/testimonials/<id>                        — Delete testimonial
  POST   /api/testimonials/<id>/approve                — Approve testimonial
  POST   /api/testimonials/<id>/reject                 — Reject testimonial
  POST   /api/testimonials/<id>/archive                — Archive testimonial
  POST   /api/testimonials/<id>/restore                — Restore to pending
  POST   /api/testimonials/<id>/feature                — Toggle featured status
  POST   /api/testimonials/<id>/like                   — Toggle liked status
"""

import json
from datetime import datetime, timezone

from bson import ObjectId
from flask import Blueprint, request, jsonify, g

from auth import login_required
from database import get_db
from utils import (
    success_response, error_response,
    is_valid_object_id, serialize_doc,
    save_uploaded_image, utcnow,
    get_pagination_params, build_pagination_meta,
    log_moderation_action, create_notification
)

testimonials_bp = Blueprint("testimonials", __name__)


# ─────────────────────────────────────────────
# Helper: Verify testimonial ownership
# ─────────────────────────────────────────────

def get_owned_testimonial(testimonial_id, owner_id):
    """
    Fetch a testimonial and verify it belongs to the current owner.
    Returns (testimonial_doc, None) or (None, "error")
    """
    if not is_valid_object_id(testimonial_id):
        return None, "Invalid testimonial ID."

    db = get_db()
    testimonial = db.testimonials.find_one({
        "_id": ObjectId(testimonial_id),
        "owner_id": ObjectId(owner_id)
    })

    if not testimonial:
        return None, "Testimonial not found or you don't have permission."

    return testimonial, None


def serialize_testimonial_for_owner(t):
    """
    Serialize a testimonial for the owner's private dashboard.
    Includes customer email (only visible to owner).
    """
    return serialize_doc(t)


def serialize_testimonial_public(t):
    """
    Serialize a testimonial for PUBLIC display.
    NEVER includes customer email.
    """
    doc = serialize_doc(t)
    doc.pop("customer_email", None)   # Remove email before sending
    doc.pop("owner_id", None)
    return doc


# ─────────────────────────────────────────────
# Public Testimonial Submission
# ─────────────────────────────────────────────

@testimonials_bp.route("/api/public/spaces/<slug>/testimonials", methods=["POST"])
@testimonials_bp.route("/api/public/<slug>/testimonials", methods=["POST"])
def submit_testimonial(slug):
    """
    POST /api/public/spaces/<slug>/testimonials
    A customer submits a testimonial. No login required.

    What happens:
    1. Find the active space by slug.
    2. Validate the submitted data.
    3. Handle optional avatar upload.
    4. Save the testimonial with status="pending".
    5. Create a notification for the space owner.
    6. Return a success message.

    This is intentionally kept simple so customers can submit easily.
    """
    db = get_db()

    # Find the space
    slug_norm = slug.strip().lower() if slug else ""
    space = db.spaces.find_one({"slug": slug_norm, "is_active": True})
    if not space:
        return jsonify(error_response("This collection page is not active or does not exist.", 404)[0]), 404

    # Support multipart (avatar upload) or JSON
    if request.content_type and "multipart" in request.content_type:
        data = request.form
        avatar_file = request.files.get("avatar")
    else:
        data = request.get_json() or {}
        avatar_file = None

    # --- Validate required fields ---
    errors = {}
    customer_name = data.get("customer_name", "").strip()
    customer_email = data.get("customer_email", "").strip()
    review_text = data.get("review_text", "").strip()

    if not customer_name:
        errors["customer_name"] = "Your name is required."
    if not customer_email:
        errors["customer_email"] = "Your email is required."
    if not review_text:
        errors["review_text"] = "Please write your testimonial."
    elif len(review_text) < 10:
        errors["review_text"] = "Testimonial must be at least 10 characters."
    elif len(review_text) > 2000:
        errors["review_text"] = "Testimonial must be 2000 characters or fewer."

    # --- Validate star rating (only if space has ratings enabled) ---
    rating = None
    if space.get("enable_star_rating"):
        raw_rating = data.get("rating")
        if not raw_rating:
            # Rating is required but was not submitted
            errors["rating"] = "Please select a star rating."
        else:
            try:
                rating = int(raw_rating)
                if not (1 <= rating <= 5):
                    errors["rating"] = "Rating must be between 1 and 5."
            except (ValueError, TypeError):
                errors["rating"] = "Rating must be a number from 1 to 5."

    # --- Validate avatar if required ---
    if space.get("require_avatar") and (not avatar_file or not avatar_file.filename):
        errors["avatar"] = "An avatar photo is required for this space."

    if errors:
        return jsonify(error_response("Please correct the errors below.", 400, errors)[0]), 400

    # --- Handle avatar upload ---
    avatar_path = ""
    if avatar_file and avatar_file.filename:
        avatar_path, upload_error = save_uploaded_image(avatar_file, subfolder="avatars")
        if upload_error:
            return jsonify(error_response(f"Avatar upload failed: {upload_error}", 400)[0]), 400

    # --- Parse custom question answers ---
    custom_answers = []
    raw_answers = data.get("custom_answers", "[]")
    try:
        if isinstance(raw_answers, str):
            answers_list = json.loads(raw_answers)
        else:
            answers_list = raw_answers if isinstance(raw_answers, list) else []
        for a in answers_list:
            if isinstance(a, dict) and a.get("label"):
                custom_answers.append({
                    "label": a["label"][:200],
                    "answer": str(a.get("answer", ""))[:1000],
                })
    except Exception:
        custom_answers = []

    # --- Save testimonial ---
    now = utcnow()
    testimonial_doc = {
        "space_id": space["_id"],
        "owner_id": space["owner_id"],
        "customer_name": customer_name[:100],
        "customer_email": customer_email[:254],
        "company_name": data.get("company_name", "").strip()[:100],
        "company_role": data.get("company_role", "").strip()[:100],
        "rating": rating,
        "review_text": review_text,
        "avatar": avatar_path,
        "custom_answers": custom_answers,
        "status": "pending",           # All testimonials start as Pending
        "is_featured": False,
        "is_liked": False,
        "submitted_at": now,
        "updated_at": now,
        "moderated_at": None,
        "moderated_by": None,
    }

    result = db.testimonials.insert_one(testimonial_doc)

    # --- Notify the owner ---
    owner_id = str(space["owner_id"])
    create_notification(
        db,
        owner_id,
        "New Testimonial",
        f"{customer_name} submitted a testimonial for '{space['name']}'.",
        "info"
    )

    return jsonify(success_response(
        {"testimonial_id": str(result.inserted_id)},
        space.get("thank_you_message", "Thank you for your testimonial!"),
        201
    )[0]), 201


# ─────────────────────────────────────────────
# Owner Testimonial Routes
# ─────────────────────────────────────────────

@testimonials_bp.route("/api/testimonials", methods=["GET"])
@login_required
def list_all_testimonials():
    """
    GET /api/testimonials
    List ALL testimonials owned by the current user across all their spaces.
    Used by the dashboard 'All spaces' view.

    Query params:
      - status: all | pending | approved | rejected | archived
      - space_id: (optional) filter to a specific space
      - search: text search in name, company, review
      - rating: 1-5
      - sort: newest | oldest | rating_high | rating_low
      - page, per_page
    """
    owner_id = g.current_owner["_id"]
    db = get_db()

    # Base filter: only testimonials belonging to this owner
    query = {"owner_id": owner_id}

    # Optional space filter
    space_id_filter = request.args.get("space_id", "").strip()
    if space_id_filter and is_valid_object_id(space_id_filter):
        query["space_id"] = ObjectId(space_id_filter)

    # Status filter
    status_filter = request.args.get("status", "all")
    if status_filter != "all":
        query["status"] = status_filter

    # Rating filter
    rating_filter = request.args.get("rating")
    if rating_filter:
        try:
            query["rating"] = int(rating_filter)
        except ValueError:
            pass

    # Text search
    search = request.args.get("search", "").strip()
    if search:
        query["$or"] = [
            {"customer_name": {"$regex": search, "$options": "i"}},
            {"company_name":  {"$regex": search, "$options": "i"}},
            {"review_text":   {"$regex": search, "$options": "i"}},
        ]

    # Sorting
    sort_by = request.args.get("sort", "newest")
    sort_map = {
        "newest":      [("submitted_at", -1)],
        "oldest":      [("submitted_at",  1)],
        "rating_high": [("rating", -1)],
        "rating_low":  [("rating",  1)],
    }
    sort_order = sort_map.get(sort_by, [("submitted_at", -1)])

    # Tab counts (ignores status/rating filter so all tabs show correct numbers)
    count_base = {"owner_id": owner_id}
    if space_id_filter and is_valid_object_id(space_id_filter):
        count_base["space_id"] = ObjectId(space_id_filter)
    if search:
        count_base["$or"] = query.get("$or", [])

    counts = {
        "all":      db.testimonials.count_documents(count_base),
        "pending":  db.testimonials.count_documents({**count_base, "status": "pending"}),
        "approved": db.testimonials.count_documents({**count_base, "status": "approved"}),
        "rejected": db.testimonials.count_documents({**count_base, "status": "rejected"}),
    }

    # Pagination
    pagination = get_pagination_params(request.args)
    total = db.testimonials.count_documents(query)

    testimonials = list(
        db.testimonials.find(query)
        .sort(sort_order)
        .skip(pagination["skip"])
        .limit(pagination["per_page"])
    )

    result = [serialize_testimonial_for_owner(t) for t in testimonials]
    meta = build_pagination_meta(total, pagination["page"], pagination["per_page"])

    return jsonify(success_response({
        "testimonials": result,
        "pagination": meta,
        "counts": counts,
    })[0]), 200


@testimonials_bp.route("/api/spaces/<space_id>/testimonials", methods=["GET"])
@login_required
def list_testimonials(space_id):
    """
    GET /api/spaces/<space_id>/testimonials
    List testimonials for a space with search, filters, and pagination.

    Query params:
      - status: all | pending | approved | rejected | archived
      - search: text search in name, company, review text
      - rating: 1-5
      - sort: newest (default) | oldest | rating_high | rating_low
      - page, per_page
    """
    if not is_valid_object_id(space_id):
        return jsonify(error_response("Invalid space ID.", 400)[0]), 400

    owner_id = g.current_owner["_id"]
    db = get_db()

    # Verify ownership (owner must own the space)
    space = db.spaces.find_one({"_id": ObjectId(space_id), "owner_id": owner_id})
    if not space:
        return jsonify(error_response("Space not found.", 404)[0]), 404

    # Build MongoDB filter
    query = {"space_id": ObjectId(space_id)}

    status_filter = request.args.get("status", "all")
    if status_filter != "all":
        query["status"] = status_filter

    rating_filter = request.args.get("rating")
    if rating_filter:
        try:
            query["rating"] = int(rating_filter)
        except ValueError:
            pass

    # Text search across multiple fields
    search = request.args.get("search", "").strip()
    if search:
        query["$or"] = [
            {"customer_name": {"$regex": search, "$options": "i"}},
            {"company_name": {"$regex": search, "$options": "i"}},
            {"review_text": {"$regex": search, "$options": "i"}},
        ]

    # Sorting
    sort_by = request.args.get("sort", "newest")
    sort_map = {
        "newest": [("submitted_at", -1)],
        "oldest": [("submitted_at", 1)],
        "rating_high": [("rating", -1)],
        "rating_low": [("rating", 1)],
    }
    sort_order = sort_map.get(sort_by, [("submitted_at", -1)])

    # Tab counts (base query without status/rating filter so all tabs are accurate)
    count_base = {"space_id": ObjectId(space_id)}
    if search:
        count_base["$or"] = query.get("$or", [])

    counts = {
        "all":      db.testimonials.count_documents(count_base),
        "pending":  db.testimonials.count_documents({**count_base, "status": "pending"}),
        "approved": db.testimonials.count_documents({**count_base, "status": "approved"}),
        "rejected": db.testimonials.count_documents({**count_base, "status": "rejected"}),
    }

    # Pagination
    pagination = get_pagination_params(request.args)
    total = db.testimonials.count_documents(query)

    testimonials = list(
        db.testimonials.find(query)
        .sort(sort_order)
        .skip(pagination["skip"])
        .limit(pagination["per_page"])
    )

    result = [serialize_testimonial_for_owner(t) for t in testimonials]
    meta = build_pagination_meta(total, pagination["page"], pagination["per_page"])

    return jsonify(success_response({
        "testimonials": result,
        "pagination": meta,
        "counts": counts,
        "space_name": space["name"],
    })[0]), 200


@testimonials_bp.route("/api/testimonials/<testimonial_id>", methods=["GET"])
@login_required
def get_testimonial(testimonial_id):
    """GET /api/testimonials/<id> — Get a single testimonial (owner only)."""
    owner_id = str(g.current_owner["_id"])
    testimonial, error = get_owned_testimonial(testimonial_id, owner_id)
    if error:
        return jsonify(error_response(error, 404)[0]), 404
    return jsonify(success_response(serialize_testimonial_for_owner(testimonial))[0]), 200


@testimonials_bp.route("/api/testimonials/<testimonial_id>", methods=["PATCH"])
@login_required
def update_testimonial(testimonial_id):
    """
    PATCH /api/testimonials/<id>
    Allow owner to edit limited testimonial fields (e.g. fix a typo).
    Only review_text and customer_name can be edited.
    """
    owner_id = str(g.current_owner["_id"])
    testimonial, error = get_owned_testimonial(testimonial_id, owner_id)
    if error:
        return jsonify(error_response(error, 404)[0]), 404

    data = request.get_json() or {}
    update_fields = {}

    if "review_text" in data:
        text = data["review_text"].strip()
        if len(text) < 10:
            return jsonify(error_response("Review text must be at least 10 characters.", 400)[0]), 400
        update_fields["review_text"] = text[:2000]

    if "customer_name" in data:
        name = data["customer_name"].strip()
        if name:
            update_fields["customer_name"] = name[:100]

    if "company_name" in data:
        update_fields["company_name"] = data["company_name"].strip()[:100]

    if "company_role" in data:
        update_fields["company_role"] = data["company_role"].strip()[:100]

    if not update_fields:
        return jsonify(error_response("No valid fields to update.", 400)[0]), 400

    update_fields["updated_at"] = utcnow()
    db = get_db()
    db.testimonials.update_one({"_id": testimonial["_id"]}, {"$set": update_fields})

    updated = db.testimonials.find_one({"_id": testimonial["_id"]})
    return jsonify(success_response(serialize_testimonial_for_owner(updated), "Testimonial updated.")[0]), 200


@testimonials_bp.route("/api/testimonials/<testimonial_id>", methods=["DELETE"])
@login_required
def delete_testimonial(testimonial_id):
    """DELETE /api/testimonials/<id> — Permanently delete a testimonial."""
    owner_id = str(g.current_owner["_id"])
    testimonial, error = get_owned_testimonial(testimonial_id, owner_id)
    if error:
        return jsonify(error_response(error, 404)[0]), 404

    db = get_db()
    db.testimonials.delete_one({"_id": testimonial["_id"]})

    return jsonify(success_response(message="Testimonial deleted permanently.")[0]), 200


# ─────────────────────────────────────────────
# Moderation Actions
# ─────────────────────────────────────────────

def _change_status(testimonial_id, owner_id, new_status, action_name):
    """
    Internal helper that changes a testimonial's status.
    Used by approve, reject, archive, and restore routes.
    """
    testimonial, error = get_owned_testimonial(testimonial_id, owner_id)
    if error:
        return jsonify(error_response(error, 404)[0]), 404

    db = get_db()
    prev_status = testimonial["status"]
    owner = g.current_owner
    now = utcnow()

    db.testimonials.update_one(
        {"_id": testimonial["_id"]},
        {"$set": {
            "status": new_status,
            "moderated_at": now,
            "moderated_by": owner["_id"],
            "updated_at": now,
        }}
    )

    # Log this moderation action for the audit trail
    log_moderation_action(db, owner_id, testimonial_id, action_name, prev_status, new_status)

    updated = db.testimonials.find_one({"_id": testimonial["_id"]})
    return jsonify(success_response(
        serialize_testimonial_for_owner(updated),
        f"Testimonial {action_name}."
    )[0]), 200


@testimonials_bp.route("/api/testimonials/<testimonial_id>/approve", methods=["POST"])
@login_required
def approve_testimonial(testimonial_id):
    """POST /api/testimonials/<id>/approve — Approve a testimonial (makes it public)."""
    return _change_status(testimonial_id, str(g.current_owner["_id"]), "approved", "approved")


@testimonials_bp.route("/api/testimonials/<testimonial_id>/reject", methods=["POST"])
@login_required
def reject_testimonial(testimonial_id):
    """POST /api/testimonials/<id>/reject — Reject a testimonial."""
    return _change_status(testimonial_id, str(g.current_owner["_id"]), "rejected", "rejected")


@testimonials_bp.route("/api/testimonials/<testimonial_id>/archive", methods=["POST"])
@login_required
def archive_testimonial(testimonial_id):
    """POST /api/testimonials/<id>/archive — Archive a testimonial."""
    return _change_status(testimonial_id, str(g.current_owner["_id"]), "archived", "archived")


@testimonials_bp.route("/api/testimonials/<testimonial_id>/restore", methods=["POST"])
@login_required
def restore_testimonial(testimonial_id):
    """POST /api/testimonials/<id>/restore — Restore to pending."""
    return _change_status(testimonial_id, str(g.current_owner["_id"]), "pending", "restored")


@testimonials_bp.route("/api/testimonials/<testimonial_id>/feature", methods=["POST"])
@login_required
def toggle_feature(testimonial_id):
    """POST /api/testimonials/<id>/feature — Toggle featured status."""
    owner_id = str(g.current_owner["_id"])
    testimonial, error = get_owned_testimonial(testimonial_id, owner_id)
    if error:
        return jsonify(error_response(error, 404)[0]), 404

    db = get_db()
    new_featured = not testimonial.get("is_featured", False)
    db.testimonials.update_one(
        {"_id": testimonial["_id"]},
        {"$set": {"is_featured": new_featured, "updated_at": utcnow()}}
    )

    action = "featured" if new_featured else "unfeatured"
    log_moderation_action(db, owner_id, testimonial_id, action)

    updated = db.testimonials.find_one({"_id": testimonial["_id"]})
    return jsonify(success_response(serialize_testimonial_for_owner(updated), f"Testimonial {action}.")[0]), 200


@testimonials_bp.route("/api/testimonials/<testimonial_id>/like", methods=["POST"])
@login_required
def toggle_like(testimonial_id):
    """POST /api/testimonials/<id>/like — Toggle liked status."""
    owner_id = str(g.current_owner["_id"])
    testimonial, error = get_owned_testimonial(testimonial_id, owner_id)
    if error:
        return jsonify(error_response(error, 404)[0]), 404

    db = get_db()
    new_liked = not testimonial.get("is_liked", False)
    db.testimonials.update_one(
        {"_id": testimonial["_id"]},
        {"$set": {"is_liked": new_liked, "updated_at": utcnow()}}
    )

    updated = db.testimonials.find_one({"_id": testimonial["_id"]})
    action = "liked" if new_liked else "unliked"
    return jsonify(success_response(serialize_testimonial_for_owner(updated), f"Testimonial {action}.")[0]), 200


# ─────────────────────────────────────────────
# Public Wall of Love
# ─────────────────────────────────────────────

@testimonials_bp.route("/api/public/wall/<slug>", methods=["GET"])
def get_public_wall(slug):
    """
    GET /api/public/wall/<slug>
    Return approved testimonials for the public Wall of Love.

    IMPORTANT security rules:
    - Only approved testimonials
    - No customer email addresses
    - Handles inactive spaces
    """
    db = get_db()
    slug_norm = slug.strip().lower() if slug else ""
    space = db.spaces.find_one({"slug": slug_norm})

    if not space:
        return jsonify(error_response("Space not found.", 404)[0]), 404

    if not space.get("is_active"):
        return jsonify(error_response("This Wall of Love is no longer active.", 410)[0]), 410

    # Pagination
    pagination = get_pagination_params(request.args, default_per_page=20)

    query = {"space_id": space["_id"], "status": "approved"}
    total = db.testimonials.count_documents(query)

    testimonials = list(
        db.testimonials.find(query)
        .sort("submitted_at", -1)
        .skip(pagination["skip"])
        .limit(pagination["per_page"])
    )

    # Public serialization — removes customer email
    public_testimonials = [serialize_testimonial_public(t) for t in testimonials]

    space_info = {
        "name": space["name"],
        "business_name": space.get("business_name", ""),
        "logo": space.get("logo", ""),
        "brand_color": space.get("brand_color", "#B89A5A"),
        "enable_star_rating": space.get("enable_star_rating", True),
    }

    return jsonify(success_response({
        "space": space_info,
        "testimonials": public_testimonials,
        "pagination": build_pagination_meta(total, pagination["page"], pagination["per_page"]),
    })[0]), 200
