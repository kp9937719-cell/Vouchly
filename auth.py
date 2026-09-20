"""
auth.py — Authentication Module
=================================
Handles all authentication routes and JWT helpers.

Routes (registered as a Flask Blueprint with prefix /api/auth):
  POST /signup          — Create a new owner account
  POST /login           — Login and receive JWT cookies
  POST /logout          — Clear cookies and revoke refresh token
  POST /refresh         — Get a new access token using refresh token
  POST /verify-email    — Verify email using a token
  POST /resend-verification — Send a new verification email
  POST /forgot-password — Request a password reset email
  POST /reset-password  — Submit new password with reset token
  GET  /me              — Get current authenticated owner info

JWT Strategy:
  - Access token: 15 minutes, stored in HttpOnly cookie "access_token"
  - Refresh token: 7 days, stored in HttpOnly cookie "refresh_token"
  - On refresh: rotate the refresh token (old one is revoked)
  - On logout: revoke the refresh token
"""

import jwt
import secrets
from datetime import datetime, timezone, timedelta
from functools import wraps

from bson import ObjectId
from flask import (
    Blueprint, request, jsonify, make_response,
    current_app, g, url_for
)
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db
from utils import (
    success_response, error_response,
    is_valid_email, validate_password_strength,
    generate_secure_token, serialize_doc, utcnow,
    create_notification
)

# Create the auth Blueprint — all routes will be /api/auth/...
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ─────────────────────────────────────────────
# JWT Helper Functions
# ─────────────────────────────────────────────

def create_access_token(owner_id: str) -> str:
    """
    Create a short-lived JWT access token (15 minutes).

    The token payload contains:
    - sub: the owner's MongoDB _id as a string
    - iat: when the token was issued
    - exp: when the token expires
    - type: "access" (so we can reject refresh tokens used as access tokens)
    """
    expiry = utcnow() + timedelta(minutes=current_app.config["JWT_ACCESS_EXPIRES_MINUTES"])
    payload = {
        "sub": str(owner_id),
        "iat": utcnow(),
        "exp": expiry,
        "type": "access",
    }
    token = jwt.encode(payload, current_app.config["JWT_ACCESS_SECRET"], algorithm="HS256")
    return token


def create_refresh_token(owner_id: str) -> str:
    """
    Create a long-lived JWT refresh token (7 days).

    Unlike the access token, the refresh token is also stored in MongoDB
    so it can be revoked on logout or rotation.
    """
    expiry = utcnow() + timedelta(days=current_app.config["JWT_REFRESH_EXPIRES_DAYS"])
    payload = {
        "sub": str(owner_id),
        "iat": utcnow(),
        "exp": expiry,
        "type": "refresh",
    }
    token = jwt.encode(payload, current_app.config["JWT_REFRESH_SECRET"], algorithm="HS256")
    return token


def store_refresh_token(db, owner_id: str, token: str):
    """Save a new refresh token to MongoDB so it can be revoked later."""
    expiry = utcnow() + timedelta(days=current_app.config["JWT_REFRESH_EXPIRES_DAYS"])
    db.refresh_tokens.insert_one({
        "owner_id": ObjectId(owner_id),
        "token": token,
        "is_revoked": False,
        "created_at": utcnow(),
        "expires_at": expiry,   # MongoDB TTL index will auto-delete after this
    })


def revoke_refresh_token(db, token: str):
    """Mark a refresh token as revoked in MongoDB."""
    db.refresh_tokens.update_one(
        {"token": token},
        {"$set": {"is_revoked": True}}
    )


def decode_access_token(token: str):
    """
    Decode and validate an access token.
    Returns (payload_dict, None) on success or (None, "error message") on failure.
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_ACCESS_SECRET"],
            algorithms=["HS256"]
        )
        if payload.get("type") != "access":
            return None, "Invalid token type."
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "Access token has expired."
    except jwt.InvalidTokenError:
        return None, "Invalid access token."


def decode_refresh_token(token: str):
    """
    Decode and validate a refresh token.
    Returns (payload_dict, None) on success or (None, "error message") on failure.
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_REFRESH_SECRET"],
            algorithms=["HS256"]
        )
        if payload.get("type") != "refresh":
            return None, "Invalid token type."
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "Refresh token has expired."
    except jwt.InvalidTokenError:
        return None, "Invalid refresh token."


def set_auth_cookies(response, access_token: str, refresh_token: str):
    """
    Set both JWT tokens as HttpOnly cookies on a response object.

    HttpOnly: JavaScript cannot read these cookies (protects against XSS).
    Secure: Only sent over HTTPS (enabled in production via COOKIE_SECURE).
    SameSite: Prevents CSRF in most browsers.
    """
    secure = current_app.config["COOKIE_SECURE"]
    samesite = current_app.config["COOKIE_SAMESITE"]

    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=current_app.config["JWT_ACCESS_EXPIRES_MINUTES"] * 60,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=current_app.config["JWT_REFRESH_EXPIRES_DAYS"] * 86400,
    )


def clear_auth_cookies(response):
    """Remove both JWT cookies by setting them to empty with immediate expiry."""
    response.set_cookie("access_token", "", expires=0, httponly=True)
    response.set_cookie("refresh_token", "", expires=0, httponly=True)


# ─────────────────────────────────────────────
# Authentication Decorator
# ─────────────────────────────────────────────

def login_required(f):
    """
    Decorator that protects routes requiring authentication.

    What it does:
    1. Reads the access_token cookie.
    2. Decodes and validates the JWT.
    3. Looks up the owner in MongoDB.
    4. Stores the owner in Flask's 'g' object so the route can use it.

    If the token is missing or invalid, returns 401 Unauthorized.

    Usage:
        @auth_bp.route("/protected")
        @login_required
        def protected_route():
            owner = g.current_owner
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get("access_token")

        if not token:
            return jsonify(error_response("Authentication required. Please log in.", 401)[0]), 401

        payload, error = decode_access_token(token)
        if error:
            return jsonify(error_response(error, 401)[0]), 401

        db = get_db()
        owner = db.owners.find_one({"_id": ObjectId(payload["sub"])})

        if not owner:
            return jsonify(error_response("Owner account not found.", 401)[0]), 401

        if not owner.get("is_active", True):
            return jsonify(error_response("Account is deactivated.", 403)[0]), 403

        if not owner.get("email_verified", False):
            return jsonify(error_response("Email verification is required. Please verify your email.", 403)[0]), 403

        # Make the owner available inside route functions as g.current_owner
        g.current_owner = owner
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# Email Verification Token Helpers (itsdangerous)
# ─────────────────────────────────────────────

def get_verification_serializer():
    """
    Return a URLSafeTimedSerializer initialized with the application's SECRET_KEY
    and dedicated salt.
    """
    from itsdangerous import URLSafeTimedSerializer
    secret_key = current_app.config.get("SECRET_KEY", "dev-secret-change-in-production")
    salt = current_app.config.get("EMAIL_VERIFICATION_SALT", "vouchly-email-verification-salt")
    return URLSafeTimedSerializer(secret_key, salt=salt)


def generate_verification_token(email: str) -> str:
    """
    Generate a cryptographic signed time-stamped token for the given normalized email.
    Uses itsdangerous URLSafeTimedSerializer with dedicated salt and secret.
    """
    normalized_email = email.strip().lower()
    serializer = get_verification_serializer()
    return serializer.dumps(normalized_email)


def verify_verification_token(token: str, max_age: int = None):
    """
    Validate an itsdangerous verification token.
    Returns:
      (email, None) if token is valid and within max_age.
      (None, "expired") if signature is valid but token has expired.
      (None, "invalid") if signature is invalid or tampered with.
    """
    from itsdangerous import SignatureExpired, BadTimeSignature, BadSignature

    if not token or not isinstance(token, str):
        return None, "invalid"

    if max_age is None:
        max_age = current_app.config.get("EMAIL_VERIFICATION_MAX_AGE", 3600)

    serializer = get_verification_serializer()
    try:
        email = serializer.loads(token, max_age=max_age)
        return email.strip().lower(), None
    except SignatureExpired:
        return None, "expired"
    except (BadTimeSignature, BadSignature, Exception):
        return None, "invalid"


def log_development_verification_link(email: str, verify_url: str):
    """
    Print the verification simulation link to the terminal in development mode.
    Clearly notes that NO external email was sent.
    """
    if current_app.config.get("FLASK_ENV") == "development" or current_app.config.get("DEV_EMAIL_SIMULATE"):
        print("\n" + "="*60)
        print("[DEVELOPMENT EMAIL VERIFICATION SIMULATION]")
        print("Note: No real email was sent (local development mode).")
        print(f"Target Account: {email}")
        print(f"Verification URL: {verify_url}")
        print("="*60 + "\n")


# ─────────────────────────────────────────────
# Auth Routes
# ─────────────────────────────────────────────

@auth_bp.route("/signup", methods=["POST"])
def signup():
    """
    POST /api/auth/signup
    Create a new owner account.

    Expects JSON: { full_name, email, password, confirm_password }
    Returns: JSON success message (owner must verify email)
    """
    data = request.get_json()
    if not data:
        return jsonify(error_response("No data provided.", 400)[0]), 400

    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    # --- Validate required fields ---
    errors = {}
    if not full_name:
        errors["full_name"] = "Full name is required."
    if not email:
        errors["email"] = "Email is required."
    elif not is_valid_email(email):
        errors["email"] = "Please enter a valid email address."
    if not password:
        errors["password"] = "Password is required."
    else:
        ok, reason = validate_password_strength(password)
        if not ok:
            errors["password"] = reason
    if "confirm_password" in data and password != confirm_password:
        errors["confirm_password"] = "Passwords do not match."

    if errors:
        return jsonify(error_response("Please fix the errors below.", 400, errors)[0]), 400

    db = get_db()

    # --- Check for duplicate email ---
    # We use the same generic message whether the email exists or not
    # to avoid leaking which emails are registered (security best practice)
    existing = db.owners.find_one({"email": email})
    if existing:
        return jsonify(error_response(
            "If this email is not already registered, you will receive a verification email shortly.",
            409
        )[0]), 409

    # --- Hash the password (never store plaintext) ---
    password_hash = generate_password_hash(password)

    # --- Create the owner document ---
    now = utcnow()
    owner_doc = {
        "full_name": full_name,
        "email": email,
        "password_hash": password_hash,
        "email_verified": False,
        "verified_at": None,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = db.owners.insert_one(owner_doc)
    owner_id = str(result.inserted_id)

    # --- Generate signed itsdangerous token ---
    token = generate_verification_token(email)

    # Build verification URL
    base_url = current_app.config.get("PUBLIC_BASE_URL") or current_app.config.get("APP_BASE_URL", "http://localhost:5000")
    verify_url = f"{base_url.rstrip('/')}/verify-email/{token}"

    # Log to development console (clearly stating simulation mode)
    log_development_verification_link(email, verify_url)

    is_dev = current_app.config.get("FLASK_ENV") == "development" or current_app.config.get("DEV_EMAIL_SIMULATE")
    resp_data = {
        "owner_id": owner_id,
        "email": email,
    }
    if is_dev:
        resp_data["verify_link"] = verify_url
        resp_data["is_dev"] = True

    return jsonify(success_response(
        resp_data,
        "Your account has been created. Please verify your email address to continue.",
        201
    )[0]), 201


@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
    """
    POST /api/auth/verify-email
    Validate the itsdangerous token and verify the owner's account.

    Expects JSON: { token }
    """
    data = request.get_json()
    token = data.get("token", "").strip() if data else ""

    if not token:
        return jsonify(error_response("Verification token is required.", 400)[0]), 400

    email, err = verify_verification_token(token)

    if err == "expired":
        return jsonify(error_response("This verification link has expired. Please request a new verification link.", 400)[0]), 400
    elif err or not email:
        return jsonify(error_response("Invalid or corrupted verification link.", 400)[0]), 400

    db = get_db()
    owner = db.owners.find_one({"email": email})

    if not owner:
        return jsonify(error_response("No account found associated with this verification link.", 404)[0]), 404

    if owner.get("email_verified", False):
        return jsonify(success_response(
            {"email": email, "already_verified": True},
            "Your email address is already verified. You can sign in immediately."
        )[0]), 200

    now = utcnow()
    db.owners.update_one(
        {"_id": owner["_id"]},
        {"$set": {
            "email_verified": True,
            "verified_at": now,
            "updated_at": now
        }}
    )

    create_notification(db, str(owner["_id"]), "Email Verified", "Your Vouchly account has been verified successfully.", "success")

    return jsonify(success_response(
        {"email": email},
        "Your email has been verified successfully! You can now sign in."
    )[0]), 200


@auth_bp.route("/resend-verification", methods=["POST"])
def resend_verification():
    """
    POST /api/auth/resend-verification
    Generate a new verification token for the requested unverified email.

    Expects JSON: { email }
    """
    data = request.get_json()
    email = data.get("email", "").strip().lower() if data else ""

    if not email or not is_valid_email(email):
        return jsonify(error_response("A valid email address is required.", 400)[0]), 400

    db = get_db()
    owner = db.owners.find_one({"email": email})

    # Always return a safe generic message in production to prevent account enumeration
    is_dev = current_app.config.get("FLASK_ENV") == "development" or current_app.config.get("DEV_EMAIL_SIMULATE")
    generic_msg = "If an unverified account with that email exists, a new verification link has been generated."

    if not owner:
        return jsonify(success_response(message=generic_msg)[0]), 200

    if owner.get("email_verified", False):
        return jsonify(success_response(
            {"already_verified": True},
            "This email address is already verified. Please sign in directly."
        )[0]), 200

    # Generate new itsdangerous token
    token = generate_verification_token(email)
    base_url = current_app.config.get("PUBLIC_BASE_URL") or current_app.config.get("APP_BASE_URL", "http://localhost:5000")
    verify_url = f"{base_url.rstrip('/')}/verify-email/{token}"

    log_development_verification_link(email, verify_url)

    resp_data = {}
    if is_dev:
        resp_data["verify_link"] = verify_url
        resp_data["is_dev"] = True

    return jsonify(success_response(resp_data, message=generic_msg)[0]), 200


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    POST /api/auth/login
    Authenticate an owner and set JWT cookies.

    Expects JSON: { email, password }
    Returns: Owner info + sets access_token and refresh_token cookies
    """
    data = request.get_json()
    if not data:
        return jsonify(error_response("No data provided.", 400)[0]), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify(error_response("Email and password are required.", 400)[0]), 400

    db = get_db()
    owner = db.owners.find_one({"email": email})

    # Use the same error message for wrong email OR wrong password
    invalid_msg = "Invalid email or password."

    if not owner:
        return jsonify(error_response(invalid_msg, 401)[0]), 401

    if not check_password_hash(owner["password_hash"], password):
        return jsonify(error_response(invalid_msg, 401)[0]), 401

    if not owner.get("is_active", True):
        return jsonify(error_response("Your account has been deactivated.", 403)[0]), 403

    if not owner.get("email_verified", False):
        return jsonify(error_response(
            "Your email address has not been verified yet. Please verify your email before logging in.",
            403,
            {"unverified": True, "email": email}
        )[0]), 403

    owner_id = str(owner["_id"])

    # Create tokens
    access_token = create_access_token(owner_id)
    refresh_token = create_refresh_token(owner_id)

    # Store refresh token in MongoDB (so it can be revoked)
    store_refresh_token(db, owner_id, refresh_token)

    # Build response with owner data
    owner_data = {
        "id": owner_id,
        "full_name": owner["full_name"],
        "email": owner["email"],
        "email_verified": owner["email_verified"],
    }

    response = make_response(jsonify(success_response(owner_data, "Logged in successfully.")[0]))
    set_auth_cookies(response, access_token, refresh_token)
    return response, 200


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """
    POST /api/auth/logout
    Log out the current owner.

    What it does:
    1. Reads the refresh token cookie.
    2. Revokes it in MongoDB.
    3. Clears both JWT cookies.
    """
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        db = get_db()
        revoke_refresh_token(db, refresh_token)

    response = make_response(jsonify(success_response(message="Logged out successfully.")[0]))
    clear_auth_cookies(response)
    return response, 200


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    """
    POST /api/auth/refresh
    Issue a new access token using a valid refresh token.

    Refresh Token Rotation:
    - The old refresh token is revoked.
    - A new refresh token is issued.
    - A new access token is issued.
    - This limits the damage if a refresh token is ever stolen.
    """
    token = request.cookies.get("refresh_token")
    if not token:
        return jsonify(error_response("No refresh token provided.", 401)[0]), 401

    payload, error = decode_refresh_token(token)
    if error:
        return jsonify(error_response(error, 401)[0]), 401

    db = get_db()

    # Check the token exists in MongoDB and hasn't been revoked
    stored = db.refresh_tokens.find_one({"token": token})
    if not stored or stored.get("is_revoked"):
        return jsonify(error_response("Refresh token is invalid or has been revoked.", 401)[0]), 401

    owner_id = payload["sub"]

    # Verify the owner still exists
    owner = db.owners.find_one({"_id": ObjectId(owner_id)})
    if not owner:
        return jsonify(error_response("Owner account not found.", 401)[0]), 401

    # Rotate: revoke old, create new
    revoke_refresh_token(db, token)
    new_access_token = create_access_token(owner_id)
    new_refresh_token = create_refresh_token(owner_id)
    store_refresh_token(db, owner_id, new_refresh_token)

    response = make_response(jsonify(success_response(message="Token refreshed.")[0]))
    set_auth_cookies(response, new_access_token, new_refresh_token)
    return response, 200


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """
    POST /api/auth/forgot-password
    Initiate a password reset for an owner.

    Expects JSON: { email }
    """
    data = request.get_json()
    email = data.get("email", "").strip().lower() if data else ""

    # Generic response to avoid leaking whether email exists
    generic_msg = "If an account with that email exists, a password reset link has been sent."

    if not email or not is_valid_email(email):
        return jsonify(success_response(message=generic_msg)[0]), 200

    db = get_db()
    owner = db.owners.find_one({"email": email})

    if not owner:
        return jsonify(success_response(message=generic_msg)[0]), 200

    # Delete old tokens and create a fresh one
    db.password_reset_tokens.delete_many({"owner_id": owner["_id"]})
    token = generate_secure_token()
    now = utcnow()
    db.password_reset_tokens.insert_one({
        "owner_id": owner["_id"],
        "token": token,
        "created_at": now,
        "expires_at": now + timedelta(hours=1),
        "used": False,
    })

    base_url = current_app.config["APP_BASE_URL"]
    reset_link = f"{base_url}/reset-password?token={token}"
    simulate_email(
        to_email=email,
        subject="Reset your Vouchly password",
        body=f"Hi {owner['full_name']},\n\nReset your password here:\n{reset_link}\n\nThis link expires in 1 hour. If you did not request this, ignore this email."
    )

    return jsonify(success_response(message=generic_msg)[0]), 200


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """
    POST /api/auth/reset-password
    Set a new password using a valid reset token.

    Expects JSON: { token, password, confirm_password }
    """
    data = request.get_json()
    if not data:
        return jsonify(error_response("No data provided.", 400)[0]), 400

    token = data.get("token", "").strip()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    if not token:
        return jsonify(error_response("Reset token is required.", 400)[0]), 400

    ok, reason = validate_password_strength(password)
    if not ok:
        return jsonify(error_response(reason, 400)[0]), 400

    if password != confirm_password:
        return jsonify(error_response("Passwords do not match.", 400)[0]), 400

    db = get_db()
    token_doc = db.password_reset_tokens.find_one({"token": token, "used": False})

    if not token_doc:
        return jsonify(error_response("Invalid or expired reset token.", 400)[0]), 400

    if token_doc["expires_at"].replace(tzinfo=timezone.utc) < utcnow():
        return jsonify(error_response("This reset link has expired.", 400)[0]), 400

    # Update the password
    new_hash = generate_password_hash(password)
    db.owners.update_one(
        {"_id": token_doc["owner_id"]},
        {"$set": {"password_hash": new_hash, "updated_at": utcnow()}}
    )

    # Mark the reset token as used
    db.password_reset_tokens.update_one({"token": token}, {"$set": {"used": True}})

    # Revoke all existing refresh tokens for this owner (force re-login everywhere)
    db.refresh_tokens.update_many(
        {"owner_id": token_doc["owner_id"]},
        {"$set": {"is_revoked": True}}
    )

    return jsonify(success_response(message="Password reset successfully. Please log in with your new password.")[0]), 200


@auth_bp.route("/me", methods=["GET"])
@login_required
def get_me():
    """
    GET /api/auth/me
    Return the currently authenticated owner's profile.
    """
    owner = g.current_owner
    owner_data = {
        "id": str(owner["_id"]),
        "full_name": owner["full_name"],
        "email": owner["email"],
        "email_verified": owner.get("email_verified", False),
        "business_name": owner.get("business_name", ""),
        "logo": owner.get("logo", ""),
        "brand_color": owner.get("brand_color", "#B89A5A"),
        "theme_preference": owner.get("theme_preference", "light"),
        "created_at": owner["created_at"].isoformat(),
    }
    return jsonify(success_response(owner_data)[0]), 200
