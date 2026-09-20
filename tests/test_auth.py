"""
tests/test_auth.py — Authentication Tests
============================================
Tests for signup, login, logout, token refresh, and password reset.
"""

import json
import pytest


# ── SIGNUP ──────────────────────────────────────────────────

def test_signup_success(client):
    """A valid signup should create the account."""
    res = client.post("/api/auth/signup", json={
        "full_name": "Alice",
        "email":     "alice@example.com",
        "password":  "SecurePass123!",
    })
    data = res.get_json()
    assert res.status_code == 201
    assert data["success"] is True
    assert "verify" in data["message"].lower() or "created" in data["message"].lower()


def test_signup_duplicate_email(client):
    """Signing up twice with the same email should fail."""
    client.post("/api/auth/signup", json={
        "full_name": "Alice",
        "email":     "alice@example.com",
        "password":  "SecurePass123!",
    })
    res = client.post("/api/auth/signup", json={
        "full_name": "Alice2",
        "email":     "alice@example.com",
        "password":  "SecurePass123!",
    })
    data = res.get_json()
    assert res.status_code == 409
    assert data["success"] is False


def test_signup_invalid_email(client):
    """Signup with an invalid email should fail."""
    res = client.post("/api/auth/signup", json={
        "full_name": "Bob",
        "email":     "not-an-email",
        "password":  "SecurePass123!",
    })
    assert res.status_code == 400
    assert res.get_json()["success"] is False


def test_signup_weak_password(client):
    """Signup with a password that's too short should fail."""
    res = client.post("/api/auth/signup", json={
        "full_name": "Bob",
        "email":     "bob@example.com",
        "password":  "123",
    })
    assert res.status_code == 400


# ── LOGIN ───────────────────────────────────────────────────

def test_login_unverified_email(client):
    """Login should fail if email is not verified."""
    client.post("/api/auth/signup", json={
        "full_name": "Carol",
        "email":     "carol@example.com",
        "password":  "SecurePass123!",
    })
    res = client.post("/api/auth/login", json={
        "email":    "carol@example.com",
        "password": "SecurePass123!",
    })
    data = res.get_json()
    # Should fail with 403 or contain a verification message
    assert not data["success"] or res.status_code == 403


def test_login_success(logged_in_client):
    """Login with verified account should return 200 and set cookies."""
    # The logged_in_client fixture already logs in
    res = logged_in_client.get("/api/auth/me")
    data = res.get_json()
    assert res.status_code == 200
    assert data["success"] is True
    assert "email" in data["data"]


def test_login_wrong_password(client):
    """Login with wrong password should return a generic error."""
    from tests.conftest import create_and_login
    # Create account first
    client.post("/api/auth/signup", json={
        "full_name": "Dave",
        "email":     "dave@example.com",
        "password":  "SecurePass123!",
    })
    # Try wrong password
    res = client.post("/api/auth/login", json={
        "email":    "dave@example.com",
        "password": "WrongPassword",
    })
    data = res.get_json()
    assert res.status_code in (400, 401)
    assert data["success"] is False


def test_login_nonexistent_email(client):
    """Login with a nonexistent email should return the same error as wrong password."""
    res = client.post("/api/auth/login", json={
        "email":    "nobody@example.com",
        "password": "SomePass123!",
    })
    data = res.get_json()
    assert res.status_code in (400, 401)
    assert data["success"] is False


# ── LOGOUT ──────────────────────────────────────────────────

def test_logout(logged_in_client):
    """Logout should clear authentication."""
    res = logged_in_client.post("/api/auth/logout")
    assert res.status_code == 200
    # After logout, /api/auth/me should return 401
    res2 = logged_in_client.get("/api/auth/me")
    assert res2.status_code == 401


# ── GET ME ──────────────────────────────────────────────────

def test_get_me_unauthenticated(client):
    """GET /api/auth/me without auth should return 401."""
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_get_me_authenticated(logged_in_client):
    """GET /api/auth/me with valid cookie should return owner data."""
    res = logged_in_client.get("/api/auth/me")
    data = res.get_json()
    assert res.status_code == 200
    assert data["success"] is True
    assert data["data"]["email"] == "test@vouchly.com"


# ── FORGOT PASSWORD ─────────────────────────────────────────

def test_forgot_password_unknown_email(client):
    """Forgot password with unknown email should return 200 (no enumeration)."""
    res = client.post("/api/auth/forgot-password", json={
        "email": "unknown@example.com"
    })
    # Should return 200 with a generic message regardless
    assert res.status_code == 200


# ── EMAIL VERIFICATION (ITS DANGEROUS SIMULATION) ───────────

def test_token_generation_and_validation(app):
    """Token serializer generates valid signed tokens and detects tampering and expiration."""
    from auth import generate_verification_token, verify_verification_token

    with app.app_context():
        email = "verify-test@example.com"
        token = generate_verification_token(email)
        assert isinstance(token, str)
        assert len(token) > 20

        # Valid verification
        extracted_email, err = verify_verification_token(token)
        assert err is None
        assert extracted_email == email

        # Tampered verification
        tampered_token = token[:-4] + "abcd"
        bad_email, err = verify_verification_token(tampered_token)
        assert bad_email is None
        assert err == "invalid"

        # Expired verification (max_age < 0)
        exp_email, err = verify_verification_token(token, max_age=-1)
        assert exp_email is None
        assert err == "expired"


def test_signup_creates_unverified_owner(client, app):
    """Signup creates owner with email_verified=False and verified_at=None."""
    from database import get_db

    res = client.post("/api/auth/signup", json={
        "full_name": "Unverified User",
        "email":     "unverified@example.com",
        "password":  "SecurePass123!",
    })
    data = res.get_json()
    assert res.status_code == 201
    assert data["success"] is True
    assert "verify_link" in data["data"]

    with app.app_context():
        db = get_db()
        owner = db.owners.find_one({"email": "unverified@example.com"})
        assert owner is not None
        assert owner["email_verified"] is False
        assert owner["verified_at"] is None


def test_login_denied_when_unverified(client):
    """Login is blocked with HTTP 403 when email is unverified."""
    client.post("/api/auth/signup", json={
        "full_name": "Blocked User",
        "email":     "blocked@example.com",
        "password":  "SecurePass123!",
    })

    res = client.post("/api/auth/login", json={
        "email":    "blocked@example.com",
        "password": "SecurePass123!",
    })
    data = res.get_json()
    assert res.status_code == 403
    assert data["success"] is False
    assert data.get("errors", {}).get("unverified") is True


def test_verify_email_endpoint_success_and_login(client, app):
    """Valid verification token marks email_verified=True and enables login."""
    from database import get_db

    # Signup
    res = client.post("/api/auth/signup", json={
        "full_name": "Verifiable User",
        "email":     "verifiable@example.com",
        "password":  "SecurePass123!",
    })
    verify_link = res.get_json()["data"]["verify_link"]
    token = verify_link.split("/verify-email/")[-1]

    # Call verify-email endpoint
    verify_res = client.post("/api/auth/verify-email", json={"token": token})
    verify_data = verify_res.get_json()
    assert verify_res.status_code == 200
    assert verify_data["success"] is True
    assert "verified" in verify_data["message"].lower()

    # Verify DB state
    with app.app_context():
        db = get_db()
        owner = db.owners.find_one({"email": "verifiable@example.com"})
        assert owner["email_verified"] is True
        assert owner["verified_at"] is not None

    # Now login should succeed
    login_res = client.post("/api/auth/login", json={
        "email":    "verifiable@example.com",
        "password": "SecurePass123!",
    })
    assert login_res.status_code == 200
    assert login_res.get_json()["success"] is True


def test_verify_email_already_verified(client):
    """Calling verify-email on an already verified account returns 200 with already_verified."""
    res = client.post("/api/auth/signup", json={
        "full_name": "Double Verify User",
        "email":     "doubleverify@example.com",
        "password":  "SecurePass123!",
    })
    token = res.get_json()["data"]["verify_link"].split("/verify-email/")[-1]

    # First verify
    client.post("/api/auth/verify-email", json={"token": token})

    # Second verify
    res2 = client.post("/api/auth/verify-email", json={"token": token})
    data2 = res2.get_json()
    assert res2.status_code == 200
    assert data2["success"] is True
    assert data2["data"].get("already_verified") is True


def test_verify_email_tampered_token(client):
    """Tampered token returns 400 error."""
    res = client.post("/api/auth/verify-email", json={"token": "totally-bogus-token.12345.xyz"})
    assert res.status_code == 400
    assert res.get_json()["success"] is False


def test_verify_email_expired_token(client, app):
    """Expired token returns 400 error indicating expiration."""
    from auth import generate_verification_token

    with app.app_context():
        token = generate_verification_token("expired-test@example.com")
        # Temporarily set max age to negative to simulate expiration
        app.config["EMAIL_VERIFICATION_MAX_AGE"] = -1

    try:
        res = client.post("/api/auth/verify-email", json={"token": token})
        data = res.get_json()
        assert res.status_code == 400
        assert data["success"] is False
        assert "expired" in data["message"].lower()
    finally:
        app.config["EMAIL_VERIFICATION_MAX_AGE"] = 3600


def test_resend_verification_endpoint(client):
    """Resending verification generates a new link for unverified accounts."""
    client.post("/api/auth/signup", json={
        "full_name": "Resend User",
        "email":     "resend@example.com",
        "password":  "SecurePass123!",
    })

    # Resend
    res = client.post("/api/auth/resend-verification", json={"email": "resend@example.com"})
    data = res.get_json()
    assert res.status_code == 200
    assert data["success"] is True
    assert "verify_link" in data["data"]


def test_resend_verification_nonexistent_email(client):
    """Resending for nonexistent email returns generic 200 without leaking account status."""
    res = client.post("/api/auth/resend-verification", json={"email": "nonexistent@example.com"})
    data = res.get_json()
    assert res.status_code == 200
    assert data["success"] is True
    # In dev mode with nonexistent user, no verify_link should be provided
    assert "verify_link" not in data.get("data", {})


def test_dev_link_hidden_in_production(client, app):
    """In production mode, verify_link is not leaked in JSON response."""
    app.config["FLASK_ENV"] = "production"
    app.config["DEV_EMAIL_SIMULATE"] = False

    try:
        res = client.post("/api/auth/signup", json={
            "full_name": "Prod User",
            "email":     "prod@example.com",
            "password":  "SecurePass123!",
        })
        data = res.get_json()
        assert res.status_code == 201
        assert "verify_link" not in data.get("data", {})
    finally:
        app.config["FLASK_ENV"] = "development"
        app.config["DEV_EMAIL_SIMULATE"] = True


def test_verification_pending_page_renders(client):
    """GET /verification-pending should render 200 without error."""
    res = client.get("/verification-pending?email=test%40example.com&verify_link=http://localhost:5000/verify-email/xyz")
    assert res.status_code == 200
    assert b"Verify Your Email" in res.data
    assert b"test@example.com" in res.data


def test_verify_email_page_renders(client):
    """GET /verify-email and /verify-email/<token> should render 200."""
    res1 = client.get("/verify-email")
    assert res1.status_code == 200
    res2 = client.get("/verify-email/some-test-token")
    assert res2.status_code == 200


