"""
tests/test_testimonials.py — Testimonial Submission & Moderation Tests
=========================================================================
"""

import json
import pytest


def create_space(client, name="Test Space", slug="test-space-t"):
    """Helper to create a space and return its ID and slug."""
    res = client.post("/api/spaces", json={"name": name, "slug": slug})
    data = res.get_json()
    return data["data"]["id"], data["data"]["slug"]


# ── PUBLIC SUBMISSION ──────────────────────────────────────

def test_submit_testimonial_success(logged_in_client, client):
    """Anyone should be able to submit a testimonial to a public space."""
    _, slug = create_space(logged_in_client)

    res = client.post(f"/api/public/{slug}/testimonials", json={
        "customer_name":  "Happy Customer",
        "customer_email": "happy@example.com",
        "review_text":    "This product is absolutely amazing!",
    })
    data = res.get_json()
    assert res.status_code == 201
    assert data["success"] is True


def test_submit_testimonial_missing_name(logged_in_client, client):
    """Testimonial without customer name should fail."""
    _, slug = create_space(logged_in_client)
    res = client.post(f"/api/public/{slug}/testimonials", json={
        "customer_email": "test@example.com",
        "review_text":    "Great product!",
    })
    assert res.status_code == 400
    assert res.get_json()["success"] is False


def test_submit_testimonial_missing_review(logged_in_client, client):
    """Testimonial without review text should fail."""
    _, slug = create_space(logged_in_client)
    res = client.post(f"/api/public/{slug}/testimonials", json={
        "customer_name":  "Joe",
        "customer_email": "joe@example.com",
        "review_text":    "",
    })
    assert res.status_code == 400


def test_submit_to_nonexistent_space(client):
    """Submitting to a non-existent space slug should return 404."""
    res = client.post("/api/public/does-not-exist/testimonials", json={
        "customer_name":  "Joe",
        "customer_email": "joe@example.com",
        "review_text":    "Nice!",
    })
    assert res.status_code == 404


def test_submit_starts_as_pending(logged_in_client, client):
    """Newly submitted testimonials should have 'pending' status."""
    space_id, slug = create_space(logged_in_client)

    client.post(f"/api/public/{slug}/testimonials", json={
        "customer_name":  "New Customer",
        "customer_email": "new@example.com",
        "review_text":    "Pending review test.",
    })

    # Fetch testimonials as owner
    res = logged_in_client.get(f"/api/spaces/{space_id}/testimonials?status=pending")
    data = res.get_json()
    assert data["data"]["pagination"]["total"] == 1


# ── MODERATION ─────────────────────────────────────────────

def get_first_testimonial_id(client, space_id):
    """Helper: Get the ID of the first testimonial in a space."""
    res = client.get(f"/api/spaces/{space_id}/testimonials")
    items = res.get_json()["data"]["testimonials"]
    return items[0]["id"] if items else None


def test_approve_testimonial(logged_in_client, client):
    """An owner should be able to approve a pending testimonial."""
    space_id, slug = create_space(logged_in_client)
    client.post(f"/api/public/{slug}/testimonials", json={
        "customer_name":  "Approvable",
        "customer_email": "a@test.com",
        "review_text":    "Please approve me!",
    })

    test_id = get_first_testimonial_id(logged_in_client, space_id)
    res = logged_in_client.post(f"/api/testimonials/{test_id}/approve")
    data = res.get_json()
    assert res.status_code == 200
    assert data["success"] is True

    # Verify it's now approved
    res2 = logged_in_client.get(f"/api/testimonials/{test_id}")
    assert res2.get_json()["data"]["status"] == "approved"


def test_reject_testimonial(logged_in_client, client):
    """An owner should be able to reject a pending testimonial."""
    space_id, slug = create_space(logged_in_client, slug="reject-test-space")
    client.post(f"/api/public/{slug}/testimonials", json={
        "customer_name":  "Rejectable",
        "customer_email": "r@test.com",
        "review_text":    "Please reject me!",
    })

    test_id = get_first_testimonial_id(logged_in_client, space_id)
    res = logged_in_client.post(f"/api/testimonials/{test_id}/reject")
    assert res.status_code == 200
    res2 = logged_in_client.get(f"/api/testimonials/{test_id}")
    assert res2.get_json()["data"]["status"] == "rejected"


def test_feature_approved_testimonial(logged_in_client, client):
    """An approved testimonial should be featureable."""
    space_id, slug = create_space(logged_in_client, slug="feature-test-space")
    client.post(f"/api/public/{slug}/testimonials", json={
        "customer_name":  "Featured",
        "customer_email": "f@test.com",
        "review_text":    "Feature me!",
    })

    test_id = get_first_testimonial_id(logged_in_client, space_id)
    logged_in_client.post(f"/api/testimonials/{test_id}/approve")
    res = logged_in_client.post(f"/api/testimonials/{test_id}/feature")
    assert res.status_code == 200

    res2 = logged_in_client.get(f"/api/testimonials/{test_id}")
    assert res2.get_json()["data"]["is_featured"] is True


# ── PUBLIC WALL ─────────────────────────────────────────────

def test_public_wall_only_shows_approved(logged_in_client, client):
    """The public wall should only return approved testimonials."""
    space_id, slug = create_space(logged_in_client, slug="wall-test-space")

    # Submit 3 testimonials
    for i in range(3):
        client.post(f"/api/public/{slug}/testimonials", json={
            "customer_name":  f"Customer {i}",
            "customer_email": f"c{i}@test.com",
            "review_text":    f"Great stuff {i}",
        })

    # Approve only the first one
    all_res = logged_in_client.get(f"/api/spaces/{space_id}/testimonials")
    test_ids = [t["id"] for t in all_res.get_json()["data"]["testimonials"]]
    logged_in_client.post(f"/api/testimonials/{test_ids[0]}/approve")

    # Public wall should only have 1
    wall_res = client.get(f"/api/public/wall/{slug}")
    wall_data = wall_res.get_json()
    assert wall_data["data"]["pagination"]["total"] == 1


def test_public_wall_hides_customer_email(logged_in_client, client):
    """The public wall should NEVER expose customer emails."""
    space_id, slug = create_space(logged_in_client, slug="email-hide-space")
    client.post(f"/api/public/{slug}/testimonials", json={
        "customer_name":  "Private Email",
        "customer_email": "private@secret.com",
        "review_text":    "Do not expose my email!",
    })

    all_res = logged_in_client.get(f"/api/spaces/{space_id}/testimonials")
    test_id = all_res.get_json()["data"]["testimonials"][0]["id"]
    logged_in_client.post(f"/api/testimonials/{test_id}/approve")

    wall_res = client.get(f"/api/public/wall/{slug}")
    wall_text = wall_res.get_data(as_text=True)
    assert "private@secret.com" not in wall_text
