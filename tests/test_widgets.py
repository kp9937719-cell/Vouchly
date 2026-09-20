"""
tests/test_widgets.py — Widget & Embed Tests
==============================================
"""


def create_space_and_approve(client, owner_client, slug):
    """Create a space, submit a testimonial, and approve it."""
    owner_client.post("/api/spaces", json={"name": "Widget Space", "slug": slug})
    client.post(f"/api/public/{slug}/testimonials", json={
        "customer_name":  "Widget Fan",
        "customer_email": "fan@example.com",
        "review_text":    "Embedding this is so easy!",
    })
    # Approve the testimonial
    res = owner_client.get(f"/api/spaces")
    spaces = res.get_json()["data"]["spaces"]
    space_id = spaces[0]["id"]
    t_res = owner_client.get(f"/api/spaces/{space_id}/testimonials")
    items = t_res.get_json()["data"]["testimonials"]
    if items:
        owner_client.post(f"/api/testimonials/{items[0]['id']}/approve")
    return space_id


def test_public_widget_endpoint(logged_in_client, client):
    """The public widget endpoint should return approved testimonials."""
    create_space_and_approve(client, logged_in_client, "widget-slug")

    res = client.get("/api/public/widgets/widget-slug")
    data = res.get_json()
    assert res.status_code == 200
    assert data["success"] is True
    assert len(data["data"]["testimonials"]) == 1
    # Email must not be present
    for t in data["data"]["testimonials"]:
        assert "email" not in t


def test_public_widget_no_pending(logged_in_client, client):
    """Widget endpoint should NOT return pending testimonials."""
    owner_client = logged_in_client
    owner_client.post("/api/spaces", json={"name": "No Pending Space", "slug": "no-pending-wg"})

    # Submit but do NOT approve
    client.post("/api/public/no-pending-wg/testimonials", json={
        "customer_name":  "Not Yet",
        "customer_email": "pending@example.com",
        "review_text":    "Still waiting to be approved.",
    })

    res = client.get("/api/public/widgets/no-pending-wg")
    data = res.get_json()
    assert data["success"] is True
    assert len(data["data"]["testimonials"]) == 0


def test_widget_config_save_and_load(logged_in_client):
    """Owners should be able to save and retrieve widget configurations."""
    logged_in_client.post("/api/spaces", json={"name": "Config Space", "slug": "config-space-wg"})
    res = logged_in_client.get("/api/spaces")
    space_id = res.get_json()["data"]["spaces"][0]["id"]

    # Save config
    config = {
        "layout": "carousel",
        "theme":  "dark",
        "count":  10,
        "show_ratings": True,
        "show_avatars": False,
        "show_company": True,
        "brand_color":  "#FF0000",
    }
    save_res = logged_in_client.post(
        f"/api/spaces/{space_id}/widget-config",
        json=config,
    )
    assert save_res.status_code == 200
    assert save_res.get_json()["data"]["config"]["layout"] == "carousel"
    assert save_res.get_json()["data"]["config"]["theme"]  == "dark"

    # Load config
    load_res = logged_in_client.get(f"/api/spaces/{space_id}/widget-config")
    assert load_res.status_code == 200
    loaded = load_res.get_json()["data"]["config"]
    assert loaded["layout"] == "carousel"
    assert loaded["show_avatars"] is False


def test_widget_page_renders(logged_in_client, client):
    """GET /widget/<slug> should render the embeddable HTML page."""
    create_space_and_approve(client, logged_in_client, "widget-page-slug")

    res = client.get("/widget/widget-page-slug?layout=grid&theme=light&count=6")
    assert res.status_code == 200
    # Should return HTML
    assert b"widget" in res.data.lower() or b"html" in res.data.lower()
    # Should not leak emails
    assert b"fan@example.com" not in res.data


def test_embed_generate_requires_auth(client):
    """Embed code generation should require authentication."""
    res = client.post("/api/embed/generate", json={
        "slug": "some-slug",
        "config": {"layout": "grid"},
    })
    assert res.status_code == 401
