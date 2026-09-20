"""
app.py — Main Flask Application
==================================
This is the entry point for Vouchly.

What this file does:
1. Creates the Flask app.
2. Loads configuration from config.py.
3. Registers all Blueprints (auth, spaces, testimonials, analytics, widgets).
4. Sets up the database connection and indexes.
5. Registers error handlers (404, 500).
6. Registers page routes (the Jinja2-rendered HTML pages).
7. Adds profile/settings API routes.

How to run:
    python app.py
or:
    flask run

The app will be available at http://localhost:5000
"""

import os
from datetime import datetime

from bson import ObjectId
from flask import Flask, render_template, request, jsonify, g, redirect, url_for, make_response, current_app
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from database import get_db, close_db, init_db
from auth import auth_bp, login_required
from spaces import spaces_bp, public_bp
from testimonials import testimonials_bp
from analytics import analytics_bp
from widgets import widgets_bp, generate_embed_code
from utils import (
    success_response, error_response,
    is_valid_email, validate_password_strength,
    save_uploaded_image, serialize_doc, utcnow
)


def create_app(config_object=None):
    """
    Flask application factory.
    Creates and configures the Flask app.

    Using a factory function (instead of a global app) makes testing easier
    because tests can create fresh app instances with different configs.
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_object:
        app.config.from_object(config_object)

    # ── CORS ──────────────────────────────────────
    # Allow the widget endpoint to be called from any origin
    # (needed for embeds on external websites)
    CORS(app, resources={
        r"/api/public/widgets/*": {"origins": "*"},
        r"/widget/*": {"origins": "*"},
    }, supports_credentials=False)

    # ── Rate Limiting ─────────────────────────────
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
    )

    # Apply stricter limits to auth endpoints
    limiter.limit("10 per minute")(auth_bp)

    # ── Blueprints ────────────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(spaces_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(testimonials_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(widgets_bp)

    # ── Database teardown ─────────────────────────
    app.teardown_appcontext(close_db)

    # ── Initialize indexes ────────────────────────
    init_db(app)

    # ── Upload folder ─────────────────────────────
    upload_dir = os.path.join(app.root_path, app.config["UPLOAD_FOLDER"])
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(os.path.join(upload_dir, "logos"), exist_ok=True)
    os.makedirs(os.path.join(upload_dir, "avatars"), exist_ok=True)

    # ── Jinja2 context processor ──────────────────
    @app.context_processor
    def inject_globals():
        """Make these variables available in every template."""
        owner_info = None
        token = request.cookies.get("access_token")
        if token:
            from auth import decode_access_token
            payload, err = decode_access_token(token)
            if not err and payload and "sub" in payload:
                try:
                    db = get_db()
                    owner = db.owners.find_one({"_id": ObjectId(payload["sub"])})
                    if owner and owner.get("is_active", True) and owner.get("email_verified", False):
                        name = owner.get("full_name", "Owner")
                        owner_info = {
                            "id": str(owner["_id"]),
                            "full_name": name,
                            "email": owner.get("email", ""),
                            "initial": (name[:1] or "O").upper(),
                            "first_name": name.split()[0] if name else "Owner",
                        }
                except Exception:
                    pass

        return {
            "app_name": "Vouchly",
            "current_year": datetime.now().year,
            "current_owner": owner_info,
        }

    # ──────────────────────────────────────────────
    # Page Routes (Jinja2-rendered HTML pages)
    # ──────────────────────────────────────────────

    @app.route("/")
    def landing():
        """Landing page — shown to everyone."""
        return render_template("landing.html")

    @app.route("/login")
    def login_page():
        return render_template("login.html")

    @app.route("/signup")
    def signup_page():
        return render_template("signup.html")

    @app.route("/verification-pending")
    def verification_pending_page():
        email = request.args.get("email", "")
        verify_link = request.args.get("verify_link", "")
        email_error = request.args.get("email_error", "")
        is_dev = current_app.config.get("FLASK_ENV") == "development" or current_app.config.get("DEV_EMAIL_SIMULATE")
        return render_template(
            "verification_pending.html",
            email=email,
            verify_link=verify_link if (is_dev or email_error) else "",
            email_error=email_error,
            is_dev=is_dev
        )

    @app.route("/verify-email")
    @app.route("/verify-email/<token>")
    def verify_email_page(token=None):
        if not token:
            token = request.args.get("token", "")
        return render_template("verify_email.html", token=token)

    @app.route("/forgot-password")
    def forgot_password_page():
        return render_template("forgot_password.html")

    @app.route("/reset-password")
    def reset_password_page():
        token = request.args.get("token", "")
        return render_template("reset_password.html", token=token)

    @app.route("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/spaces")
    def spaces_page():
        return render_template("spaces.html")

    @app.route("/spaces/new")
    def create_space_page():
        return render_template("create_space.html")

    @app.route("/spaces/<space_id>/edit")
    def edit_space_page(space_id):
        return render_template("edit_space.html", space_id=space_id)

    @app.route("/testimonials")
    def testimonials_page():
        return render_template("testimonials.html")

    @app.route("/testimonials/<testimonial_id>")
    def testimonial_detail_page(testimonial_id):
        return render_template("testimonial_detail.html", testimonial_id=testimonial_id)

    @app.route("/analytics")
    def analytics_page():
        return render_template("analytics.html")

    @app.route("/embed")
    def embed_page():
        return render_template("embed_generator.html")

    @app.route("/settings")
    def settings_page():
        return render_template("settings.html")

    @app.route("/profile")
    def profile_page():
        return render_template("profile.html")

    # ── Public pages ──────────────────────────────

    @app.route("/collect/<slug>")
    def collection_page(slug):
        """Public testimonial collection form."""
        return render_template("collection.html", slug=slug)

    @app.route("/wall/<slug>")
    def wall_page(slug):
        """Public Wall of Love."""
        return render_template("wall_of_love.html", slug=slug)

    # ──────────────────────────────────────────────
    # Profile & Settings API Routes
    # ──────────────────────────────────────────────

    @app.route("/api/profile", methods=["GET"])
    @login_required
    def get_profile():
        """GET /api/profile — Return current owner's full profile."""
        owner = g.current_owner
        data = {
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
        return jsonify(success_response(data)[0]), 200

    @app.route("/api/profile", methods=["PATCH"])
    @login_required
    def update_profile():
        """
        PATCH /api/profile
        Update owner's profile information.

        Accepts multipart/form-data (for logo upload) or JSON.
        """
        owner = g.current_owner
        owner_id = owner["_id"]
        db = get_db()

        if request.content_type and "multipart" in request.content_type:
            data = request.form
            logo_file = request.files.get("logo")
        else:
            data = request.get_json() or {}
            logo_file = None

        update_fields = {}

        if "full_name" in data:
            name = data["full_name"].strip()
            if not name:
                return jsonify(error_response("Full name cannot be empty.", 400)[0]), 400
            update_fields["full_name"] = name[:100]

        if "business_name" in data:
            update_fields["business_name"] = data["business_name"].strip()[:100]

        if "brand_color" in data:
            update_fields["brand_color"] = data["brand_color"].strip()[:20]

        if "theme_preference" in data:
            theme = data["theme_preference"]
            if theme in ("light", "dark"):
                update_fields["theme_preference"] = theme

        if logo_file and logo_file.filename:
            logo_path, upload_error = save_uploaded_image(logo_file, subfolder="logos")
            if upload_error:
                return jsonify(error_response(upload_error, 400)[0]), 400
            update_fields["logo"] = logo_path

        if not update_fields:
            return jsonify(error_response("No fields to update.", 400)[0]), 400

        update_fields["updated_at"] = utcnow()
        db.owners.update_one({"_id": owner_id}, {"$set": update_fields})

        updated = db.owners.find_one({"_id": owner_id})
        response_data = {
            "id": str(updated["_id"]),
            "full_name": updated["full_name"],
            "email": updated["email"],
            "business_name": updated.get("business_name", ""),
            "logo": updated.get("logo", ""),
            "brand_color": updated.get("brand_color", "#B89A5A"),
            "theme_preference": updated.get("theme_preference", "light"),
        }
        return jsonify(success_response(response_data, "Profile updated successfully.")[0]), 200

    @app.route("/api/profile/change-password", methods=["POST"])
    @login_required
    def change_password():
        """
        POST /api/profile/change-password
        Change the current owner's password.

        Requires the current password to be correct first.
        """
        owner = g.current_owner
        data = request.get_json() or {}

        current_password = data.get("current_password", "")
        new_password = data.get("new_password", "")
        confirm_password = data.get("confirm_password", "")

        if not current_password:
            return jsonify(error_response("Current password is required.", 400)[0]), 400

        if not check_password_hash(owner["password_hash"], current_password):
            return jsonify(error_response("Current password is incorrect.", 400)[0]), 400

        ok, reason = validate_password_strength(new_password)
        if not ok:
            return jsonify(error_response(reason, 400)[0]), 400

        if new_password != confirm_password:
            return jsonify(error_response("New passwords do not match.", 400)[0]), 400

        db = get_db()
        new_hash = generate_password_hash(new_password)
        db.owners.update_one(
            {"_id": owner["_id"]},
            {"$set": {"password_hash": new_hash, "updated_at": utcnow()}}
        )

        return jsonify(success_response(message="Password changed successfully.")[0]), 200

    @app.route("/api/embed/generate", methods=["POST"])
    @login_required
    def generate_embed():
        """
        POST /api/embed/generate
        Generate embed code snippets for a widget configuration.
        """
        data = request.get_json() or {}
        slug = data.get("slug", "").strip()
        if not slug:
            return jsonify(error_response("Space slug is required.", 400)[0]), 400

        # Verify ownership
        db = get_db()
        space = db.spaces.find_one({"slug": slug, "owner_id": g.current_owner["_id"]})
        if not space:
            return jsonify(error_response("Space not found.", 404)[0]), 404

        from widgets import validate_widget_config
        config = validate_widget_config(data.get("config", {}))
        base_url = app.config["APP_BASE_URL"]
        embed_code = generate_embed_code(slug, config, base_url)

        return jsonify(success_response(embed_code)[0]), 200

    # ──────────────────────────────────────────────
    # Error Handlers
    # ──────────────────────────────────────────────

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify(error_response("The requested resource was not found.", 404)[0]), 404
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        if request.path.startswith("/api/"):
            return jsonify(error_response("An internal server error occurred.", 500)[0]), 500
        return render_template("500.html"), 500

    @app.errorhandler(413)
    def file_too_large(e):
        return jsonify(error_response(
            f"File too large. Maximum size is {app.config['MAX_UPLOAD_SIZE_MB']}MB.",
            413
        )[0]), 413

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify(error_response("Too many requests. Please slow down.", 429)[0]), 429

    return app


# ──────────────────────────────────────────────
# Run the app
# ──────────────────────────────────────────────

if __name__ == "__main__":
    app = create_app()
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=app.config["DEBUG"]
    )
