"""
tests/conftest.py — Pytest Fixtures
=======================================
Provides:
  - app: A Flask test app with an in-memory-style test MongoDB database
  - client: A Flask test client (simulates HTTP requests)
  - auth_headers: Headers with a valid JWT for authenticated test requests

HOW TO RUN:
    cd "c:\\job project\\vouchly"
    pytest tests/ -v

Make sure to have a MONGO_URI pointing to a local MongoDB for tests.
Or set TEST_MONGO_URI in environment.
"""

import os
import sys
import pytest

# Ensure root project directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from database import get_db


# ── Test configuration ──────────────────────────────────────
class TestConfig:
    TESTING        = True
    DEBUG          = False
    SECRET_KEY     = "test-secret-key-for-testing-only"
    JWT_ACCESS_SECRET = "test-jwt-access-secret"
    JWT_REFRESH_SECRET = "test-jwt-refresh-secret"
    MONGO_URI      = os.environ.get("TEST_MONGO_URI", "mongodb://localhost:27017/")
    MONGO_DB_NAME  = "vouchly_test"
    UPLOAD_FOLDER  = "static/uploads"
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    MAX_UPLOAD_SIZE_MB = 5
    JWT_ACCESS_EXPIRES_MINUTES  = 60
    JWT_REFRESH_EXPIRES_DAYS    = 7
    COOKIE_SECURE   = False
    COOKIE_SAMESITE = "Lax"
    RATELIMIT_ENABLED = False
    DEV_EMAIL_SIMULATE = True
    APP_BASE_URL = "http://localhost:5000"


@pytest.fixture(scope="session")
def app():
    """Create a Flask app configured for testing."""
    application = create_app(TestConfig)
    yield application


@pytest.fixture(scope="function")
def client(app):
    """A test client for making HTTP requests to the app."""
    return app.test_client()


@pytest.fixture(scope="function", autouse=True)
def clean_db(app):
    """
    Clean the test database before each test function.
    This ensures tests are independent and don't pollute each other.
    """
    with app.app_context():
        db = get_db()
        # Drop all test collections before each test
        db.owners.drop()
        db.spaces.drop()
        db.testimonials.drop()
        db.refresh_tokens.drop()
        db.email_verification_tokens.drop()
        db.password_reset_tokens.drop()
        db.notifications.drop()
        db.moderation_logs.drop()
        db.widget_configurations.drop()
    yield


# ── Helper: Create and log in a test user ──────────────────

def create_and_login(client, email="test@vouchly.com", password="TestPass123!"):
    """
    Create a user, manually verify their email, then log in.
    Returns the client after setting cookies.
    """
    # Sign up
    client.post(
        "/api/auth/signup",
        json={"full_name": "Test Owner", "email": email, "password": password},
        content_type="application/json",
    )

    # Manually verify email in DB (simulate clicking the link)
    from app import create_app as _create_app
    from database import get_db as _get_db
    with client.application.app_context():
        db = _get_db()
        db.owners.update_one({"email": email}, {"$set": {"email_verified": True}})

    # Log in
    res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        content_type="application/json",
    )
    return res


@pytest.fixture(scope="function")
def logged_in_client(app):
    """
    A test client already logged in with a verified account.
    Cookies are set automatically (Flask test client handles cookie jars).
    """
    c = app.test_client()
    create_and_login(c)
    return c
