"""
widgets.py — Embed Widget Module
===================================
Handles embed code generation and the public widget API.

Routes:
  GET /api/public/widgets/<slug>         — Return approved testimonials for a widget
  GET /api/spaces/<id>/widget-config     — Get saved widget config for a space
  POST /api/spaces/<id>/widget-config    — Save widget config for a space
  GET /widget/<slug>                     — Serve the embeddable widget HTML page

The widget endpoint is public (no login needed) and only returns
approved testimonials — never customer emails or private data.
"""

from bson import ObjectId
from flask import Blueprint, request, jsonify, g, render_template, current_app

from auth import login_required
from database import get_db
from utils import (
    success_response, error_response,
    is_valid_object_id, serialize_doc,
    get_pagination_params, build_pagination_meta, utcnow
)

widgets_bp = Blueprint("widgets", __name__)

# Valid widget configuration options
VALID_LAYOUTS = {"grid", "carousel", "badge"}
VALID_THEMES = {"light", "dark"}
VALID_CARD_STYLES = {"default", "minimal", "bordered"}


def validate_widget_config(config: dict) -> dict:
    """
    Validate and sanitise widget configuration options.
    Returns a clean config dict with safe defaults.
    """
    return {
        "layout": config.get("layout", "grid") if config.get("layout") in VALID_LAYOUTS else "grid",
        "theme": config.get("theme", "light") if config.get("theme") in VALID_THEMES else "light",
        "brand_color": config.get("brand_color", "#B89A5A")[:20],
        "count": max(1, min(50, int(config.get("count", 6) or 6))),
        "show_ratings": bool(config.get("show_ratings", True)),
        "show_avatars": bool(config.get("show_avatars", True)),
        "show_company": bool(config.get("show_company", True)),
        "card_style": config.get("card_style", "default") if config.get("card_style") in VALID_CARD_STYLES else "default",
    }


@widgets_bp.route("/api/public/widgets/<slug>", methods=["GET"])
def get_widget_data(slug):
    """
    GET /api/public/widgets/<slug>
    Return approved testimonials for embedding in external websites.

    Query params mirror widget config:
      - layout: grid | carousel | badge
      - theme: light | dark
      - count: 1-50 (number of testimonials to return)
      - show_ratings: true | false
      - show_avatars: true | false
      - show_company: true | false

    Security: Only approved testimonials. No customer emails.
    CORS is enabled for this endpoint so external sites can call it.
    """
    db = get_db()
    slug_norm = slug.strip().lower() if slug else ""
    space = db.spaces.find_one({"slug": slug_norm, "is_active": True})

    if not space:
        return jsonify(error_response("Space not found or inactive.", 404)[0]), 404

    # Parse and validate query params
    try:
        count = max(1, min(50, int(request.args.get("count", 6))))
    except (ValueError, TypeError):
        count = 6

    query = {"space_id": space["_id"], "status": "approved"}
    testimonials = list(
        db.testimonials.find(query)
        .sort([("is_featured", -1), ("submitted_at", -1)])
        .limit(count)
    )

    public_testimonials = []
    for t in testimonials:
        public_testimonials.append({
            "id": str(t["_id"]),
            "customer_name": t["customer_name"],
            "company_name": t.get("company_name", ""),
            "company_role": t.get("company_role", ""),
            "rating": t.get("rating"),
            "review_text": t["review_text"],
            "avatar": t.get("avatar", ""),
            "is_featured": t.get("is_featured", False),
            "submitted_at": t["submitted_at"].isoformat(),
        })

    space_info = {
        "name": space["name"],
        "business_name": space.get("business_name", ""),
        "brand_color": space.get("brand_color", "#B89A5A"),
        "enable_star_rating": space.get("enable_star_rating", True),
    }

    return jsonify(success_response({
        "space": space_info,
        "testimonials": public_testimonials,
    })[0]), 200


@widgets_bp.route("/api/spaces/<space_id>/widget-config", methods=["GET"])
@login_required
def get_widget_config(space_id):
    """
    GET /api/spaces/<space_id>/widget-config
    Return the saved widget configuration for a space.
    """
    if not is_valid_object_id(space_id):
        return jsonify(error_response("Invalid space ID.", 400)[0]), 400

    owner_id = g.current_owner["_id"]
    db = get_db()

    space = db.spaces.find_one({"_id": ObjectId(space_id), "owner_id": owner_id})
    if not space:
        return jsonify(error_response("Space not found.", 404)[0]), 404

    config_doc = db.widget_configurations.find_one({"space_id": ObjectId(space_id)})

    if not config_doc:
        # Return sensible defaults
        default_config = validate_widget_config({})
        return jsonify(success_response({"config": default_config})[0]), 200

    config = validate_widget_config(config_doc.get("config", {}))
    return jsonify(success_response({"config": config})[0]), 200


@widgets_bp.route("/api/spaces/<space_id>/widget-config", methods=["POST"])
@login_required
def save_widget_config(space_id):
    """
    POST /api/spaces/<space_id>/widget-config
    Save the widget configuration for a space.
    """
    if not is_valid_object_id(space_id):
        return jsonify(error_response("Invalid space ID.", 400)[0]), 400

    owner_id = g.current_owner["_id"]
    db = get_db()

    space = db.spaces.find_one({"_id": ObjectId(space_id), "owner_id": owner_id})
    if not space:
        return jsonify(error_response("Space not found.", 404)[0]), 404

    raw_config = request.get_json() or {}
    clean_config = validate_widget_config(raw_config)

    db.widget_configurations.update_one(
        {"space_id": ObjectId(space_id)},
        {"$set": {
            "space_id": ObjectId(space_id),
            "owner_id": owner_id,
            "config": clean_config,
            "updated_at": utcnow(),
        }},
        upsert=True
    )

    return jsonify(success_response({"config": clean_config}, "Widget configuration saved.")[0]), 200


@widgets_bp.route("/widget/<slug>")
def widget_page(slug):
    """
    GET /widget/<slug>
    Serve a standalone embeddable widget page.

    This is what goes inside an <iframe>. It loads the approved testimonials
    and renders them using the widget.html template.

    Query params:
      - layout, theme, count, show_ratings, show_avatars, show_company, card_style
    """
    db = get_db()
    space = db.spaces.find_one({"slug": slug, "is_active": True})

    if not space:
        return render_template("404.html"), 404

    # Parse widget config from query params
    config = validate_widget_config({
        "layout": request.args.get("layout", "grid"),
        "theme": request.args.get("theme", "light"),
        "brand_color": request.args.get("brand_color", space.get("brand_color", "#B89A5A")),
        "count": request.args.get("count", 6),
        "show_ratings": request.args.get("show_ratings", "true").lower() != "false",
        "show_avatars": request.args.get("show_avatars", "true").lower() != "false",
        "show_company": request.args.get("show_company", "true").lower() != "false",
        "card_style": request.args.get("card_style", "default"),
    })

    testimonials = list(
        db.testimonials.find({"space_id": space["_id"], "status": "approved"})
        .sort([("is_featured", -1), ("submitted_at", -1)])
        .limit(config["count"])
    )

    # Safe public serialization — no emails
    public_testimonials = []
    for t in testimonials:
        public_testimonials.append({
            "id": str(t["_id"]),
            "customer_name": t["customer_name"],
            "company_name": t.get("company_name", ""),
            "company_role": t.get("company_role", ""),
            "rating": t.get("rating"),
            "review_text": t["review_text"],
            "avatar": t.get("avatar", ""),
            "is_featured": t.get("is_featured", False),
        })

    return render_template(
        "widget.html",
        space=space,
        testimonials=public_testimonials,
        config=config,
    )


def generate_embed_code(slug: str, config: dict, base_url: str) -> dict:
    """
    Generate HTML and iframe embed code snippets for a widget.

    The caller passes the slug and configuration.
    This returns both a <script> version and an <iframe> version.

    Why two versions?
    - The iframe version is easiest for non-technical users to paste anywhere.
    - The HTML+script version gives more control.
    """
    # Build query string from config
    params = []
    params.append(f"layout={config.get('layout', 'grid')}")
    params.append(f"theme={config.get('theme', 'light')}")
    params.append(f"count={config.get('count', 6)}")
    params.append(f"show_ratings={'true' if config.get('show_ratings', True) else 'false'}")
    params.append(f"show_avatars={'true' if config.get('show_avatars', True) else 'false'}")
    params.append(f"show_company={'true' if config.get('show_company', True) else 'false'}")
    params.append(f"card_style={config.get('card_style', 'default')}")
    color = config.get("brand_color", "#B89A5A").lstrip("#")
    params.append(f"brand_color=%23{color}")

    query_string = "&".join(params)
    widget_url = f"{base_url}/widget/{slug}?{query_string}"
    api_url = f"{base_url}/api/public/widgets/{slug}?{query_string}"

    iframe_code = (
        f'<iframe\n'
        f'  src="{widget_url}"\n'
        f'  width="100%"\n'
        f'  height="500"\n'
        f'  frameborder="0"\n'
        f'  scrolling="auto"\n'
        f'  title="Vouchly Testimonials Widget"\n'
        f'  loading="lazy"\n'
        f'></iframe>'
    )

    html_code = (
        f'<!-- Vouchly Testimonials Widget -->\n'
        f'<div id="vouchly-widget" data-slug="{slug}" data-api="{api_url}"></div>\n'
        f'<script>\n'
        f'  // Vouchly widget loader\n'
        f'  (function() {{\n'
        f'    var el = document.getElementById("vouchly-widget");\n'
        f'    fetch(el.dataset.api)\n'
        f'      .then(function(r) {{ return r.json(); }})\n'
        f'      .then(function(data) {{\n'
        f'        if (!data.success) return;\n'
        f'        var html = data.data.testimonials.map(function(t) {{\n'
        f'          return \'<div class="pf-card"><p>\' + t.review_text + \'</p><strong>\' + t.customer_name + \'</strong></div>\';\n'
        f'        }}).join("");\n'
        f'        el.innerHTML = \'<div class="pf-grid">\' + html + \'</div>\';\n'
        f'      }});\n'
        f'  }})();\n'
        f'</script>'
    )

    return {"iframe": iframe_code, "html": html_code, "widget_url": widget_url}
