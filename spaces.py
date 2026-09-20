"""
spaces.py — Space Management Module
=====================================
Handles all routes for creating and managing testimonial collection spaces.

A "space" is a branded testimonial collection page that owners create.
Each space has a unique slug (e.g., /collect/acme-corp) and can be
customised with logos, colors, welcome messages, and custom questions.

Routes (Blueprint prefix: /api/spaces):
  GET    /api/spaces                       — List all spaces for the current owner
  POST   /api/spaces                       — Create a new space
  GET    /api/spaces/<space_id>            — Get a single space
  PATCH  /api/spaces/<space_id>            — Update a space
  DELETE /api/spaces/<space_id>            — Delete a space

Public routes (Blueprint prefix: /api/public):
  GET    /api/public/spaces/<slug>         — Get space info for the collection page
"""

from datetime import datetime, timezone

from bson import ObjectId
from flask import Blueprint, request, jsonify, g, current_app

from auth import login_required
from database import get_db
from utils import (
    success_response, error_response,
    is_valid_object_id, serialize_doc,
    is_valid_slug, sanitize_slug,
    save_uploaded_image, utcnow,
    create_notification
)

spaces_bp = Blueprint("spaces", __name__)
public_bp = Blueprint("public", __name__, url_prefix="/api/public")


# ─────────────────────────────────────────────
# Helper: Verify space ownership
# ─────────────────────────────────────────────

def get_owned_space(space_id, owner_id):
    """
    Fetch a space and verify it belongs to the current owner.

    Returns (space_doc, None) if found and owned.
    Returns (None, "error message") if not found or not owned.

    Why: We never trust the owner_id from the browser.
    We always check ownership on the server.
    """
    if not is_valid_object_id(space_id):
        return None, "Invalid space ID."

    db = get_db()
    space = db.spaces.find_one({
        "_id": ObjectId(space_id),
        "owner_id": ObjectId(owner_id)  # Must also match the logged-in owner
    })

    if not space:
        return None, "Space not found or you don't have permission to access it."

    return space, None


# ─────────────────────────────────────────────
# Authenticated Space Routes
# ─────────────────────────────────────────────

@spaces_bp.route("/api/spaces", methods=["GET"])
@login_required
def list_spaces():
    """
    GET /api/spaces
    Return all spaces belonging to the logged-in owner.

    Query params:
      - page (default: 1)
      - per_page (default: 20)
    """
    owner_id = g.current_owner["_id"]
    db = get_db()

    spaces = list(db.spaces.find({"owner_id": owner_id}).sort("created_at", -1))

    # Add testimonial counts for each space
    result = []
    for space in spaces:
        space_id = space["_id"]
        total = db.testimonials.count_documents({"space_id": space_id})
        pending = db.testimonials.count_documents({"space_id": space_id, "status": "pending"})
        approved = db.testimonials.count_documents({"space_id": space_id, "status": "approved"})

        s = serialize_doc(space)
        s["testimonial_counts"] = {"total": total, "pending": pending, "approved": approved}
        result.append(s)

    return jsonify(success_response({"spaces": result, "total": len(result)})[0]), 200


@spaces_bp.route("/api/spaces", methods=["POST"])
@login_required
def create_space():
    """
    POST /api/spaces
    Create a new testimonial collection space.

    Accepts multipart/form-data (because of file upload) or JSON.

    Form fields:
      - name (required): Human-readable space name
      - slug (required): URL-safe identifier (e.g. "acme-corp")
      - business_name: Optional business name
      - welcome_heading: Heading shown on the collection form
      - description: Subheading/description on the collection form
      - thank_you_message: Message shown after submission
      - brand_color: Hex color e.g. "#B89A5A"
      - enable_star_rating: "true"/"false"
      - require_avatar: "true"/"false"
      - custom_questions: JSON string of question objects
      - logo: File upload
    """
    owner = g.current_owner
    owner_id = owner["_id"]
    db = get_db()

    # Support both JSON and multipart form data
    if request.content_type and "multipart" in request.content_type:
        data = request.form
        logo_file = request.files.get("logo")
    else:
        data = request.get_json() or {}
        logo_file = None

    # --- Required field validation ---
    name = data.get("name", "").strip()
    slug = data.get("slug", "").strip().lower()

    errors = {}
    if not name:
        errors["name"] = "Space name is required."
    if not slug:
        errors["slug"] = "A URL slug is required."
    elif not is_valid_slug(slug):
        errors["slug"] = "Slug must be 3–60 characters: lowercase letters, numbers, and hyphens only."

    if errors:
        return jsonify(error_response("Please fix the errors below.", 400, errors)[0]), 400

    # --- Check slug uniqueness ---
    existing = db.spaces.find_one({"slug": slug})
    if existing:
        return jsonify(error_response(
            "This slug is already taken. Please choose a different one.",
            409,
            {"slug": "Slug already in use."}
        )[0]), 409

    # --- Handle logo upload ---
    logo_path = ""
    if logo_file and logo_file.filename:
        logo_path, upload_error = save_uploaded_image(logo_file, subfolder="logos")
        if upload_error:
            return jsonify(error_response(upload_error, 400)[0]), 400

    # --- Parse custom questions ---
    import json
    custom_questions = []
    raw_questions = data.get("custom_questions", "[]")
    try:
        if isinstance(raw_questions, str):
            custom_questions = json.loads(raw_questions)
        elif isinstance(raw_questions, list):
            custom_questions = raw_questions
    except (json.JSONDecodeError, TypeError):
        custom_questions = []

    # Validate each question has a label
    validated_questions = []
    for q in custom_questions:
        if isinstance(q, dict) and q.get("label", "").strip():
            validated_questions.append({
                "label": q["label"].strip(),
                "required": bool(q.get("required", False)),
                "type": q.get("type", "text"),
            })

    # --- Build the space document ---
    now = utcnow()
    space_doc = {
        "owner_id": owner_id,
        "name": name,
        "slug": slug,
        "business_name": data.get("business_name", owner.get("business_name", "")).strip(),
        "logo": logo_path,
        "brand_color": data.get("brand_color", "#B89A5A").strip(),
        "welcome_heading": data.get("welcome_heading", f"Share your experience with {name}").strip(),
        "description": data.get("description", "We'd love to hear your feedback.").strip(),
        "thank_you_message": data.get("thank_you_message", "Thank you for your testimonial!").strip(),
        "require_avatar": str(data.get("require_avatar", "false")).lower() in ("true", "on", "1"),
        "enable_star_rating": str(data.get("enable_star_rating", "true")).lower() not in ("false", "off", "0"),
        "custom_questions": validated_questions,
        "theme_settings": {
            "background_color": data.get("background_color", "#F8F6F0"),
            "text_color": data.get("text_color", "#111111"),
        },
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    result = db.spaces.insert_one(space_doc)

    # Create a notification for the owner
    create_notification(db, str(owner_id), "Space Created", f"Your space '{name}' is live at /collect/{slug}", "success")

    space_doc["_id"] = result.inserted_id
    return jsonify(success_response(
        serialize_doc(space_doc),
        "Space created successfully!",
        201
    )[0]), 201


@spaces_bp.route("/api/spaces/<space_id>", methods=["GET"])
@login_required
def get_space(space_id):
    """
    GET /api/spaces/<space_id>
    Get details of a single space (owner must own it).
    """
    owner_id = str(g.current_owner["_id"])
    space, error = get_owned_space(space_id, owner_id)
    if error:
        return jsonify(error_response(error, 404)[0]), 404

    db = get_db()
    total = db.testimonials.count_documents({"space_id": space["_id"]})
    pending = db.testimonials.count_documents({"space_id": space["_id"], "status": "pending"})
    approved = db.testimonials.count_documents({"space_id": space["_id"], "status": "approved"})

    data = serialize_doc(space)
    data["testimonial_counts"] = {"total": total, "pending": pending, "approved": approved}
    return jsonify(success_response(data)[0]), 200


@spaces_bp.route("/api/spaces/<space_id>", methods=["PATCH"])
@login_required
def update_space(space_id):
    """
    PATCH /api/spaces/<space_id>
    Update a space's settings and branding.
    """
    owner_id = str(g.current_owner["_id"])
    space, error = get_owned_space(space_id, owner_id)
    if error:
        return jsonify(error_response(error, 404)[0]), 404

    # Support both JSON and multipart (for logo upload)
    if request.content_type and "multipart" in request.content_type:
        data = request.form
        logo_file = request.files.get("logo")
    else:
        data = request.get_json() or {}
        logo_file = None

    db = get_db()
    update_fields = {}

    # Only update fields that were actually sent
    if "name" in data:
        name = data["name"].strip()
        if not name:
            return jsonify(error_response("Space name cannot be empty.", 400)[0]), 400
        update_fields["name"] = name

    if "slug" in data:
        new_slug = data["slug"].strip().lower()
        if not is_valid_slug(new_slug):
            return jsonify(error_response(
                "Invalid slug format.",
                400,
                {"slug": "Slug must be 3–60 characters: lowercase letters, numbers, and hyphens only."}
            )[0]), 400
        # Check if new slug is taken by a DIFFERENT space
        existing = db.spaces.find_one({"slug": new_slug, "_id": {"$ne": space["_id"]}})
        if existing:
            return jsonify(error_response("This slug is already taken.", 409)[0]), 409
        update_fields["slug"] = new_slug

    for field in ["business_name", "brand_color", "welcome_heading", "description", "thank_you_message"]:
        if field in data:
            update_fields[field] = data[field].strip()

    if "require_avatar" in data:
        update_fields["require_avatar"] = str(data["require_avatar"]).lower() in ("true", "on", "1")

    if "enable_star_rating" in data:
        update_fields["enable_star_rating"] = str(data["enable_star_rating"]).lower() not in ("false", "off", "0")

    if "is_active" in data:
        update_fields["is_active"] = str(data["is_active"]).lower() in ("true", "on", "1")

    if "custom_questions" in data:
        import json
        raw = data["custom_questions"]
        try:
            questions = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            questions = []
        validated = []
        for q in questions:
            if isinstance(q, dict) and q.get("label", "").strip():
                validated.append({
                    "label": q["label"].strip(),
                    "required": bool(q.get("required", False)),
                    "type": q.get("type", "text"),
                })
        update_fields["custom_questions"] = validated

    # Handle logo upload
    if logo_file and logo_file.filename:
        logo_path, upload_error = save_uploaded_image(logo_file, subfolder="logos")
        if upload_error:
            return jsonify(error_response(upload_error, 400)[0]), 400
        update_fields["logo"] = logo_path

    if not update_fields:
        return jsonify(error_response("No fields to update.", 400)[0]), 400

    update_fields["updated_at"] = utcnow()
    db.spaces.update_one({"_id": space["_id"]}, {"$set": update_fields})

    updated_space = db.spaces.find_one({"_id": space["_id"]})
    return jsonify(success_response(serialize_doc(updated_space), "Space updated successfully.")[0]), 200


@spaces_bp.route("/api/spaces/<space_id>", methods=["DELETE"])
@login_required
def delete_space(space_id):
    """
    DELETE /api/spaces/<space_id>
    Delete a space and all its testimonials.

    This is a permanent action. We warn the user in the frontend
    before calling this route.
    """
    owner_id = str(g.current_owner["_id"])
    space, error = get_owned_space(space_id, owner_id)
    if error:
        return jsonify(error_response(error, 404)[0]), 404

    db = get_db()
    space_oid = space["_id"]

    # Delete all testimonials belonging to this space
    db.testimonials.delete_many({"space_id": space_oid})

    # Delete the space itself
    db.spaces.delete_one({"_id": space_oid})

    return jsonify(success_response(message=f"Space '{space['name']}' and all its testimonials have been deleted.")[0]), 200


# ─────────────────────────────────────────────
# Public Space Route (no authentication needed)
# ─────────────────────────────────────────────

@public_bp.route("/spaces/<slug>", methods=["GET"])
def get_public_space(slug):
    """
    GET /api/public/spaces/<slug>
    Return space info for the public collection page.

    IMPORTANT: This endpoint must NEVER return:
    - The owner's email or personal info
    - Any testimonial content (just the space settings)
    - Internal IDs that could be used to access private data

    The collection form uses this to load the space's branding and questions.
    """
    db = get_db()
    slug_norm = slug.strip().lower() if slug else ""
    space = db.spaces.find_one({"slug": slug_norm, "is_active": True})

    if not space:
        return jsonify(error_response("Space not found or is no longer accepting testimonials.", 404)[0]), 404

    # Return only the fields needed to render the public collection form
    public_data = {
        "name": space["name"],
        "slug": space["slug"],
        "business_name": space.get("business_name", ""),
        "logo": space.get("logo", ""),
        "brand_color": space.get("brand_color", "#B89A5A"),
        "welcome_heading": space.get("welcome_heading", ""),
        "description": space.get("description", ""),
        "thank_you_message": space.get("thank_you_message", ""),
        "require_avatar": space.get("require_avatar", False),
        "enable_star_rating": space.get("enable_star_rating", True),
        "custom_questions": space.get("custom_questions", []),
    }

    return jsonify(success_response(public_data)[0]), 200
