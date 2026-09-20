"""
tests/test_spaces.py — Space CRUD Tests
==========================================
"""

import json
import pytest


# ── CREATE SPACE ───────────────────────────────────────────

def test_create_space_unauthenticated(client):
    """Creating a space without auth should fail."""
    res = client.post("/api/spaces", json={
        "name": "My Space",
        "slug": "my-space",
    })
    assert res.status_code == 401


def test_create_space_success(logged_in_client):
    """An authenticated owner should be able to create a space."""
    res = logged_in_client.post("/api/spaces", json={
        "name": "Test Space",
        "slug": "test-space",
    })
    data = res.get_json()
    assert res.status_code == 201
    assert data["success"] is True
    assert data["data"]["slug"] == "test-space"


def test_create_space_duplicate_slug(logged_in_client):
    """Creating two spaces with the same slug should fail."""
    logged_in_client.post("/api/spaces", json={"name": "Space A", "slug": "my-slug"})
    res = logged_in_client.post("/api/spaces", json={"name": "Space B", "slug": "my-slug"})
    data = res.get_json()
    assert res.status_code == 409
    assert data["success"] is False


def test_create_space_invalid_slug(logged_in_client):
    """Spaces with invalid slugs (special chars) should fail."""
    res = logged_in_client.post("/api/spaces", json={
        "name": "Bad Slug Space",
        "slug": "bad slug!",  # spaces and ! not allowed
    })
    data = res.get_json()
    assert res.status_code in (400, 422)
    assert data["success"] is False


# ── LIST SPACES ────────────────────────────────────────────

def test_list_spaces_empty(logged_in_client):
    """A new owner should have zero spaces."""
    res = logged_in_client.get("/api/spaces")
    data = res.get_json()
    assert res.status_code == 200
    assert data["success"] is True
    assert data["data"]["spaces"] == []


def test_list_spaces_after_creating(logged_in_client):
    """Spaces should appear in the list after creation."""
    logged_in_client.post("/api/spaces", json={"name": "Space 1", "slug": "space-1"})
    logged_in_client.post("/api/spaces", json={"name": "Space 2", "slug": "space-2"})
    res = logged_in_client.get("/api/spaces")
    data = res.get_json()
    assert len(data["data"]["spaces"]) == 2


# ── GET SPACE ──────────────────────────────────────────────

def test_get_space_by_id(logged_in_client):
    """Should be able to fetch a specific space by its ID."""
    create_res = logged_in_client.post("/api/spaces", json={"name": "My Space", "slug": "my-space-x"})
    space_id = create_res.get_json()["data"]["id"]

    res = logged_in_client.get(f"/api/spaces/{space_id}")
    data = res.get_json()
    assert res.status_code == 200
    assert data["data"]["name"] == "My Space"


def test_get_space_wrong_owner(client, logged_in_client):
    """Fetching another owner's space by ID should return 404."""
    # Create space as owner A (logged_in_client)
    create_res = logged_in_client.post("/api/spaces", json={"name": "Owner A Space", "slug": "owner-a-space"})
    space_id = create_res.get_json()["data"]["id"]

    # Create and log in as owner B
    from tests.conftest import create_and_login
    create_and_login(client, email="owner_b@test.com", password="SecurePass123!")

    # Try to access owner A's space as owner B
    res = client.get(f"/api/spaces/{space_id}")
    assert res.status_code == 404


# ── UPDATE SPACE ───────────────────────────────────────────

def test_update_space(logged_in_client):
    """Updating an owned space should succeed."""
    create_res = logged_in_client.post("/api/spaces", json={"name": "Old Name", "slug": "old-slug-u"})
    space_id = create_res.get_json()["data"]["id"]

    res = logged_in_client.patch(f"/api/spaces/{space_id}", json={"name": "New Name"})
    data = res.get_json()
    assert res.status_code == 200
    assert data["data"]["name"] == "New Name"


# ── DELETE SPACE ───────────────────────────────────────────

def test_delete_space(logged_in_client):
    """Deleting an owned space should remove it."""
    create_res = logged_in_client.post("/api/spaces", json={"name": "Delete Me", "slug": "delete-me-slug"})
    space_id = create_res.get_json()["data"]["id"]

    res = logged_in_client.delete(f"/api/spaces/{space_id}")
    assert res.status_code == 200
    assert res.get_json()["success"] is True

    # Verify it's gone
    res2 = logged_in_client.get(f"/api/spaces/{space_id}")
    assert res2.status_code == 404


# ── PUBLIC SPACE ───────────────────────────────────────────

def test_public_space_endpoint(logged_in_client, client):
    """The public space endpoint should return space info without requiring auth."""
    logged_in_client.post("/api/spaces", json={"name": "Public Space", "slug": "pub-space-slug"})

    # Access public endpoint without being logged in
    res = client.get("/api/public/spaces/pub-space-slug")
    data = res.get_json()
    assert res.status_code == 200
    assert data["data"]["slug"] == "pub-space-slug"
    # Should NOT leak owner info
    assert "owner_id" not in str(data["data"])
    assert "owner_email" not in str(data["data"])
