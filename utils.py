"""
utils.py — Shared Helper Functions
====================================
This file contains reusable functions used across the entire application.

Think of it as a "toolbox" — short, focused functions that avoid
repeating the same code in multiple route files.

Contents:
- JSON response helpers (success_response, error_response)
- MongoDB ObjectId validation
- File upload validation and saving (Pillow + Werkzeug)
- Slug validation
- Email format validation
- Password strength validation
- Pagination helper
- Notification creator
- Moderation log writer
"""

import os
import re
import secrets
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from bson import ObjectId
from flask import current_app
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError


# ─────────────────────────────────────────────
# Email Sender
# ─────────────────────────────────────────────

def send_email(to_email: str, subject: str, html_body: str, text_body: str = "") -> tuple[bool, str]:
    """
    Send an email via Gmail SMTP (TLS on port 587).

    Reads MAIL_* settings from the Flask app config (which loads from .env).
    Falls back to printing to the console if DEV_EMAIL_SIMULATE is True or
    if MAIL_USERNAME / MAIL_PASSWORD are not configured.

    Returns:
        (True, "")          on success
        (False, "reason")   on failure
    """
    cfg = current_app.config

    # ── Development simulation mode ──────────────────────────────────────────
    if cfg.get("DEV_EMAIL_SIMULATE") or not cfg.get("MAIL_USERNAME") or not cfg.get("MAIL_PASSWORD"):
        print("\n" + "=" * 60)
        print("[EMAIL SIMULATION — no real email sent]")
        print(f"  To      : {to_email}")
        print(f"  Subject : {subject}")
        print(f"  Body    :\n{text_body or html_body}")
        print("=" * 60 + "\n")
        return True, ""

    # ── Real SMTP delivery ────────────────────────────────────────────────────
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = cfg.get("MAIL_DEFAULT_SENDER") or cfg["MAIL_USERNAME"]
        msg["To"]      = to_email

        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"]) as server:
            if cfg.get("MAIL_USE_TLS", True):
                server.starttls()
            server.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
            server.sendmail(cfg["MAIL_USERNAME"], to_email, msg.as_string())

        return True, ""

    except smtplib.SMTPAuthenticationError:
        err = "SMTP authentication failed. Check MAIL_USERNAME and MAIL_PASSWORD in .env"
        print(f"[EMAIL ERROR] {err}")
        return False, err
    except Exception as exc:
        err = f"Failed to send email: {exc}"
        print(f"[EMAIL ERROR] {err}")
        return False, err


# ─────────────────────────────────────────────
# Response Helpers
# ─────────────────────────────────────────────

def success_response(data=None, message="Success", status=200):
    """
    Return a consistent JSON success response.

    Example:
        return success_response({"user": {...}}, "Logged in", 200)
    """
    body = {"success": True, "message": message}
    if data is not None:
        body["data"] = data
    return body, status


def error_response(message="An error occurred", status=400, errors=None):
    """
    Return a consistent JSON error response.

    Example:
        return error_response("Email already exists", 409)
    """
    body = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    return body, status


# ─────────────────────────────────────────────
# MongoDB Helpers
# ─────────────────────────────────────────────

def is_valid_object_id(oid_str):
    """
    Check whether a string is a valid MongoDB ObjectId.
    Prevents database errors from malformed IDs in URLs.
    """
    try:
        ObjectId(oid_str)
        return True
    except Exception:
        return False


def serialize_doc(doc):
    """
    Convert a MongoDB document to a JSON-serialisable dict.
    Converts ObjectId fields to strings and datetime to ISO strings.
    """
    if doc is None:
        return None
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, list):
            result[key] = [serialize_doc(v) if isinstance(v, dict) else
                           str(v) if isinstance(v, ObjectId) else v
                           for v in value]
        elif isinstance(value, dict):
            result[key] = serialize_doc(value)
        else:
            result[key] = value
    if "_id" in result and "id" not in result:
        result["id"] = result["_id"]
    return result


# ─────────────────────────────────────────────
# Validation Helpers
# ─────────────────────────────────────────────

def is_valid_email(email):
    """Simple email format validation using a regex."""
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.match(pattern, email.strip()))


def validate_password_strength(password):
    """
    Check password strength.
    Returns (True, None) if strong enough, or (False, "reason") if not.

    Rules:
    - At least 8 characters
    - Contains a letter
    - Contains a number
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    return True, None


def is_valid_slug(slug):
    """
    Validate a URL slug.
    Allowed: lowercase letters, numbers, hyphens. No spaces. 3–60 chars.
    """
    pattern = r"^[a-z0-9][a-z0-9\-]{1,58}[a-z0-9]$"
    return bool(re.match(pattern, slug))


def sanitize_slug(text):
    """
    Convert a plain text name to a URL-safe slug.
    Example: "Acme Corp!" → "acme-corp"
    """
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9\s\-]", "", slug)   # remove special chars
    slug = re.sub(r"[\s\-]+", "-", slug)           # collapse spaces/hyphens
    slug = slug.strip("-")
    return slug[:60]


# ─────────────────────────────────────────────
# File Upload Helpers
# ─────────────────────────────────────────────

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename):
    """Check if a filename has an allowed image extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_image(file_storage, subfolder="general"):
    """
    Validate and save an uploaded image file.

    What this does:
    1. Checks the file extension is allowed.
    2. Opens the file with Pillow to confirm it is a real image (not a renamed .exe).
    3. Generates a safe, unique filename.
    4. Saves it to static/uploads/<subfolder>/.
    5. Returns the relative path to store in MongoDB.

    Returns:
        (relative_path, None) on success
        (None, "error message") on failure
    """
    if not file_storage or file_storage.filename == "":
        return None, "No file provided."

    if not allowed_file(file_storage.filename):
        return None, f"File type not allowed. Use: {', '.join(ALLOWED_EXTENSIONS)}"

    # Validate it's a real image using Pillow
    try:
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream)
        img.verify()  # Raises an exception if not a valid image
    except (UnidentifiedImageError, Exception):
        return None, "Uploaded file is not a valid image."

    # Generate a safe, unique filename
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    safe_name = secure_filename(unique_name)

    # Ensure the upload directory exists
    upload_dir = os.path.join(
        current_app.root_path,
        current_app.config["UPLOAD_FOLDER"],
        subfolder
    )
    os.makedirs(upload_dir, exist_ok=True)

    # Save the file (re-open stream since verify() closes it)
    file_storage.stream.seek(0)
    save_path = os.path.join(upload_dir, safe_name)
    file_storage.save(save_path)

    # Return relative path suitable for serving as a static URL
    relative_path = f"{current_app.config['UPLOAD_FOLDER']}/{subfolder}/{safe_name}"
    return relative_path, None


# ─────────────────────────────────────────────
# Pagination Helper
# ─────────────────────────────────────────────

def get_pagination_params(request_args, default_per_page=10):
    """
    Extract and validate pagination parameters from a request's query string.

    Returns a dict with 'page', 'per_page', and 'skip' (how many docs to skip).
    """
    try:
        page = max(1, int(request_args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        per_page = max(1, min(100, int(request_args.get("per_page", default_per_page))))
    except (ValueError, TypeError):
        per_page = default_per_page

    skip = (page - 1) * per_page
    return {"page": page, "per_page": per_page, "skip": skip}


def build_pagination_meta(total, page, per_page):
    """Build a pagination metadata dict to include in API responses."""
    total_pages = (total + per_page - 1) // per_page  # ceiling division
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


# ─────────────────────────────────────────────
# Activity / Notifications
# ─────────────────────────────────────────────

def log_moderation_action(db, owner_id, testimonial_id, action, prev_status=None, new_status=None):
    """
    Write an entry to the moderation_logs collection.

    Called after every approve / reject / archive / restore / feature action.
    This creates an audit trail so owners can see what happened and when.
    """
    db.moderation_logs.insert_one({
        "owner_id": ObjectId(owner_id),
        "testimonial_id": ObjectId(testimonial_id),
        "action": action,              # e.g. "approved", "rejected", "featured"
        "prev_status": prev_status,
        "new_status": new_status,
        "created_at": datetime.now(timezone.utc),
    })


def create_notification(db, owner_id, title, message, notification_type="info"):
    """
    Insert a notification for a specific owner.

    These appear in the dashboard notification bell icon.
    Types: "info", "success", "warning", "error"
    """
    db.notifications.insert_one({
        "owner_id": ObjectId(owner_id),
        "title": title,
        "message": message,
        "type": notification_type,
        "is_read": False,
        "created_at": datetime.now(timezone.utc),
    })


# ─────────────────────────────────────────────
# Token Generators
# ─────────────────────────────────────────────

def generate_secure_token(length=32):
    """Generate a cryptographically secure random URL-safe token string."""
    return secrets.token_urlsafe(length)


# ─────────────────────────────────────────────
# Date Helpers
# ─────────────────────────────────────────────

def utcnow():
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)
