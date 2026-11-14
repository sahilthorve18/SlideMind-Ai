"""Unit & Integration tests for VisualAsset model, persistent storage service,
and secure asset endpoints (Phase 2).
"""
import io
import time
from PIL import Image
import pytest
from app import create_app
from database import db
from models import User, VisualAsset
from services import storage


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-key-12345",
        "DEV_LOGIN_ENABLED": True,
        "RATELIMIT_ENABLED": False,
        "STORAGE_PROVIDER": "local",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _make_test_image(width=400, height=300, color="blue", fmt="PNG") -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=color)
    img.save(buf, format=fmt)
    return buf.getvalue()


def _login(client, email="designer@example.com"):
    resp = client.post("/api/auth/dev-login", json={"email": email})
    data = resp.get_json()["data"]
    return data["token"], data["user"]["id"]


# ---------------------------------------------------------------------------
# 1. Storage Operations & Pillow Metadata Inspection
# ---------------------------------------------------------------------------

def test_storage_save_read_delete(app):
    img_bytes = _make_test_image(800, 450, color="green")
    storage_key, provider = storage.save_asset_file("user_123", "test_photo.png", img_bytes, "image/png")

    assert provider == "local"
    assert "user_123" in storage_key

    read_bytes = storage.read_asset_file(storage_key, provider)
    assert read_bytes == img_bytes

    info = storage.inspect_image_bytes(img_bytes)
    assert info["width"] == 800
    assert info["height"] == 450
    assert round(info["aspect_ratio"], 2) == 1.78  # 16:9

    deleted = storage.delete_asset_file(storage_key, provider)
    assert deleted is True


# ---------------------------------------------------------------------------
# 2. Cryptographic Signed URL Tokens (HMAC-SHA256)
# ---------------------------------------------------------------------------

def test_signed_asset_tokens(app):
    asset_id = "asset_xyz_789"
    user_id = "user_abc_123"

    token = storage.generate_signed_asset_token(asset_id, user_id, expires_in_seconds=3600)
    assert token and "." in token

    # Valid token passes
    assert storage.verify_signed_asset_token(asset_id, user_id, token) is True

    # Wrong asset_id fails
    assert storage.verify_signed_asset_token("other_asset", user_id, token) is False

    # Wrong user_id fails
    assert storage.verify_signed_asset_token(asset_id, "other_user", token) is False

    # Tampered signature fails
    tampered = token[:-4] + "zzzz"
    assert storage.verify_signed_asset_token(asset_id, user_id, tampered) is False

    # Expired token fails
    expired_token = storage.generate_signed_asset_token(asset_id, user_id, expires_in_seconds=-10)
    assert storage.verify_signed_asset_token(asset_id, user_id, expired_token) is False


# ---------------------------------------------------------------------------
# 3. Visual Tagging & Categorization
# ---------------------------------------------------------------------------

def test_visual_tagging_heuristics(app):
    logo_bytes = _make_test_image(200, 200, color="white")
    logo_meta = storage.extract_visual_metadata_and_tags(
        "company_acme_logo_vector.png",
        logo_bytes,
        {"width": 200, "height": 200, "aspect_ratio": 1.0},
    )
    assert logo_meta["is_logo"] is True
    assert logo_meta["category"] == "logo"
    assert "logo" in logo_meta["tags"]

    product_meta = storage.extract_visual_metadata_and_tags(
        "solar_inverter_product_hardware.png",
        logo_bytes,
        {"width": 1280, "height": 720, "aspect_ratio": 1.78},
    )
    assert product_meta["is_product"] is True
    assert product_meta["category"] == "product"


# ---------------------------------------------------------------------------
# 4. End-to-End Asset Upload, Listing & Security Enforcement
# ---------------------------------------------------------------------------

def test_asset_endpoints_flow(client, app):
    token, user_id = _login(client, "creator@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Upload test image
    img_data = _make_test_image(1280, 720, color="teal")
    upload_resp = client.post(
        "/api/assets/upload",
        data={"file": (io.BytesIO(img_data), "wind_turbine_prototype_product.png", "image/png")},
        content_type="multipart/form-data",
        headers=headers,
    )
    assert upload_resp.status_code == 201
    asset_data = upload_resp.get_json()["data"]
    asset_id = asset_data["id"]

    assert asset_data["width"] == 1280
    assert asset_data["height"] == 720
    assert asset_data["is_product_photo"] is True
    assert "token=" in asset_data["secure_url"]

    # Deduplication test
    dup_resp = client.post(
        "/api/assets/upload",
        data={"file": (io.BytesIO(img_data), "wind_turbine_duplicate.png", "image/png")},
        content_type="multipart/form-data",
        headers=headers,
    )
    assert dup_resp.status_code == 200
    assert dup_resp.get_json()["data"]["duplicate"] is True

    # List assets
    list_resp = client.get("/api/assets", headers=headers)
    assert list_resp.status_code == 200
    assets = list_resp.get_json()["data"]
    assert len(assets) >= 1
    assert any(a["id"] == asset_id for a in assets)

    # Security test: Unauthenticated request without token must fail (401)
    unauth_resp = client.get(f"/api/assets/{asset_id}/view")
    assert unauth_resp.status_code == 401

    # Security test: Other user session without token must fail (401)
    other_token, _ = _login(client, "intruder@example.com")
    forbidden_resp = client.get(f"/api/assets/{asset_id}/view", headers={"Authorization": f"Bearer {other_token}"})
    assert forbidden_resp.status_code == 401

    # Authorized test: Signed token access succeeds
    signed_url = asset_data["secure_url"]
    query_str = signed_url.split("?")[1]
    view_resp = client.get(f"/api/assets/{asset_id}/view?{query_str}")
    assert view_resp.status_code == 200
    assert view_resp.mimetype == "image/png"
    assert view_resp.data == img_data

    # Authorized test: Owner Bearer token succeeds
    owner_view_resp = client.get(f"/api/assets/{asset_id}/view", headers=headers)
    assert owner_view_resp.status_code == 200
    assert owner_view_resp.data == img_data

    # Delete asset
    del_resp = client.delete(f"/api/assets/{asset_id}", headers=headers)
    assert del_resp.status_code == 200

    # Verify deleted
    post_del_resp = client.get(f"/api/assets/{asset_id}/view?{query_str}")
    assert post_del_resp.status_code == 404


def test_slides_image_requests_integration():
    """Verify Google Slides API generator creates createImage requests when an image is present."""
    from services import slides

    slide_dict = {
        "title": "Solar Photovoltaic Tech",
        "bullets": ["High efficiency bifacial cells"],
        "layout": "split_screen",
        "image": {
            "url": "https://example.com/solar_panel.jpg",
            "alt": "Solar panel array",
            "composition": "split_right",
        },
    }

    reqs, ids, nr = slides.slide_requests(1, slide_dict, "modern_light")
    image_ops = [r for r in reqs if "createImage" in r]
    assert len(image_ops) == 1
    assert image_ops[0]["createImage"]["url"] == "https://example.com/solar_panel.jpg"


def test_pptx_and_pdf_image_rendering(app):
    """Verify PPTX and PDF exporter handle split_screen slides with images."""
    from models import Presentation, Slide
    from services import exporter

    with app.app_context():
        user = User(email="exporter@example.com")
        db.session.add(user)
        db.session.commit()

        p = Presentation(title="Renewable Energy Deck", user_id=user.id)
        db.session.add(p)
        db.session.commit()

        s1 = Slide(
            presentation_id=p.id,
            position=1,
            title="Clean Energy Revolution",
            content={"layout": "full_bleed_hero", "bullets": [{"text": "Pioneering the grid of tomorrow"}]},
        )
        s2 = Slide(
            presentation_id=p.id,
            position=2,
            title="Offshore Wind Systems",
            content={
                "layout": "split_screen",
                "bullets": [{"text": "Deepwater turbines harness sustained oceanic winds"}],
                "image": {
                    "url": "https://images.unsplash.com/photo-1466611653911-95081537e5b7?w=800",
                    "alt": "Wind turbine",
                },
            },
        )
        db.session.add_all([s1, s2])
        db.session.commit()

        # PPTX Export
        pptx_bytes = exporter.export_pptx(p)
        assert len(pptx_bytes) > 2000
        assert pptx_bytes[:4] == b"PK\x03\x04"

        # PDF Export
        pdf_bytes = exporter.export_pdf(p)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes[:4] == b"%PDF"

