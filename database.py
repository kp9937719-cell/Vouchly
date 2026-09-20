"""
database.py — MongoDB Connection & Index Setup
================================================
This file handles connecting to MongoDB using PyMongo.

How it works:
1. get_db() returns the database object whenever a route needs it.
2. init_db(app) is called once at startup to create indexes.
3. Indexes speed up queries and enforce uniqueness (e.g. unique emails).

Usage in routes:
    from database import get_db
    db = get_db()
    db.owners.find_one({"email": email})
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from flask import current_app, g


def get_client():
    """Return a PyMongo MongoClient. Creates one per app context."""
    if "mongo_client" not in g:
        g.mongo_client = MongoClient(current_app.config["MONGO_URI"])
    return g.mongo_client


def get_db():
    """Return the Vouchly database object."""
    client = get_client()
    return client[current_app.config["MONGO_DB_NAME"]]


def close_db(e=None):
    """Close the MongoDB connection at the end of the request."""
    client = g.pop("mongo_client", None)
    if client is not None:
        client.close()


def init_db(app):
    """
    Create MongoDB indexes for performance and uniqueness.
    Called once when the Flask app starts.

    Why indexes?
    - Unique index on owner email prevents duplicate accounts.
    - Unique index on space slug ensures public URLs are unique.
    - Other indexes speed up common filter queries.
    """
    with app.app_context():
        db = get_db()

        # ---- owners ----
        # Each owner's email must be unique
        db.owners.create_index([("email", ASCENDING)], unique=True)

        # ---- spaces ----
        # Each space slug must be globally unique (public URLs)
        db.spaces.create_index([("slug", ASCENDING)], unique=True)
        # Find all spaces owned by a specific owner quickly
        db.spaces.create_index([("owner_id", ASCENDING)])

        # ---- testimonials ----
        # Find testimonials for a space quickly
        db.testimonials.create_index([("space_id", ASCENDING)])
        # Filter by owner (to confirm ownership)
        db.testimonials.create_index([("owner_id", ASCENDING)])
        # Filter by status (pending / approved / rejected / archived)
        db.testimonials.create_index([("status", ASCENDING)])
        # Sort by submission date
        db.testimonials.create_index([("submitted_at", DESCENDING)])
        # Combined index for the most common query: space + status
        db.testimonials.create_index(
            [("space_id", ASCENDING), ("status", ASCENDING)]
        )

        # ---- tokens ----
        # Find refresh tokens by their token string quickly
        db.refresh_tokens.create_index([("token", ASCENDING)], unique=True)
        # Expire old tokens automatically (TTL index — MongoDB deletes docs after expires_at)
        db.refresh_tokens.create_index(
            [("expires_at", ASCENDING)], expireAfterSeconds=0
        )

        # Email verification tokens
        db.email_verification_tokens.create_index([("token", ASCENDING)], unique=True)
        db.email_verification_tokens.create_index(
            [("expires_at", ASCENDING)], expireAfterSeconds=0
        )

        # Password reset tokens
        db.password_reset_tokens.create_index([("token", ASCENDING)], unique=True)
        db.password_reset_tokens.create_index(
            [("expires_at", ASCENDING)], expireAfterSeconds=0
        )

        # ---- moderation_logs ----
        db.moderation_logs.create_index([("owner_id", ASCENDING)])
        db.moderation_logs.create_index([("testimonial_id", ASCENDING)])
        db.moderation_logs.create_index([("created_at", DESCENDING)])

        # ---- notifications ----
        db.notifications.create_index([("owner_id", ASCENDING)])
        db.notifications.create_index([("created_at", DESCENDING)])

        print("[OK] MongoDB indexes created successfully.")
