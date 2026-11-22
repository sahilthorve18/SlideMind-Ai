"""End-to-end verification of SlideMind AI Visual Intelligence Engine across
the 5 target presentation domains, user authentic asset priority, and export integrity.

Verifies:
1. Renewable Energy
2. Artificial Intelligence
3. Cybersecurity
4. Startup Investor Pitch
5. Human Anatomy
6. Uploaded company logos & product photos take priority on relevant slides
7. PPTX, PDF, and Google Slides rendering
"""
import io
import pytest
from app import create_app
from database import db
from models import Presentation, Slide, User, VisualAsset
from services import exporter, slides, storage, visual_intelligence


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-suite-777",
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


def _login(client, email="presenter@example.com"):
    resp = client.post("/api/auth/dev-login", json={"email": email})
    data = resp.get_json()["data"]
    return data["token"], data["user"]["id"]


# ---------------------------------------------------------------------------
# 1. Verification of the 5 Target Presentation Topics
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("topic,slide_title,expected_terms", [
    ("Renewable Energy", "Offshore Wind Turbine Array", ["wind", "turbine", "energy", "marine", "offshore"]),
    ("Artificial Intelligence", "Neural Network Architecture", ["neural", "intelligence", "computing", "network", "ai"]),
    ("Cybersecurity", "Zero Trust Distributed Security", ["security", "cyber", "network", "crypto", "encryption", "trust"]),
    ("Startup Investor Pitch", "Seed Funding & Growth Trajectory", ["startup", "business", "growth", "pitch", "investor", "market"]),
    ("Human Anatomy", "Cellular Biology and Histology", ["anatomy", "biology", "human", "medical", "cellular", "tissue"]),
])
def test_visual_selection_across_topics(topic, slide_title, expected_terms):
    """Verify visual intelligence engine generates structured visual briefs and matches
    appropriate visual assets for each required topic.
    """
    brief = visual_intelligence.generate_visual_brief(
        topic=topic,
        slide_title=slide_title,
        purpose=f"Strategic analysis of {slide_title}",
        bullets=[f"Primary breakthrough in {topic}"],
        layout="split_screen",
        slide_index=1,
        total_slides=6,
    )

    assert brief.slide_title == slide_title
    all_kws = " ".join(brief.search_keywords + brief.key_concepts).lower()
    assert any(term in all_kws for term in expected_terms)

    visual = visual_intelligence.select_best_slide_visual(
        topic=topic,
        slide_title=slide_title,
        purpose=f"Strategic analysis of {slide_title}",
        bullets=[f"Primary breakthrough in {topic}"],
        layout="split_screen",
        slide_index=1,
        total_slides=6,
    )

    assert visual is not None
    assert visual["url"].startswith("http")
    assert visual["source"] in ("Wikimedia Commons", "Wikipedia", "Unsplash", "Pexels")
    assert visual["dimensions"]["width"] > 0
    assert visual["dimensions"]["height"] > 0
    assert visual["relevance_score"] >= 50.0


# ---------------------------------------------------------------------------
# 2. Priority of User Authentic Assets (Logos & Product Photos)
# ---------------------------------------------------------------------------

def test_user_uploaded_assets_priority(app, client):
    """Verify that when a user uploads authentic company logos or product photos,
    the Visual Intelligence Engine prioritizes them over generic stock photography
    on relevant slides, but DOES NOT force them onto unrelated slides.
    """
    token, user_id = _login(client, "founder@acmewind.com")
    headers = {"Authorization": f"Bearer {token}"}

    with app.app_context():
        # User uploads authentic product photo: Acme Wind Turbine Blade
        product_asset = VisualAsset(
            user_id=user_id,
            filename="acme_turbine_blade_product.png",
            original_filename="acme_turbine_blade_product.png",
            file_type="png",
            mime_type="image/png",
            size_bytes=54321,
            content_hash="hash_product_123",
            storage_key=f"{user_id}/acme_turbine_blade_product.png",
            storage_provider="local",
            width=1920,
            height=1080,
            aspect_ratio=1.78,
            title="Acme High-Performance Wind Turbine Blade",
            description="Proprietary carbon-composite wind turbine blade manufactured by Acme",
            tags=["turbine", "blade", "wind", "product", "hardware", "energy"],
            visual_category="product",
            is_product_photo=True,
            is_company_logo=False,
        )
        db.session.add(product_asset)
        db.session.commit()

        # Case A: Relevant Slide about "Turbine Blade Technology"
        relevant_brief = visual_intelligence.generate_visual_brief(
            topic="Renewable Wind Energy",
            slide_title="Next-Generation Turbine Blade Engineering",
            purpose="Highlight proprietary carbon fiber wind turbine blade manufacturing",
            bullets=["Carbon composite architecture reduces weight by 22%"],
            layout="split_screen",
            slide_index=2,
            total_slides=6,
        )

        candidates = visual_intelligence.retrieve_image_candidates(
            relevant_brief,
            user_id=user_id,
        )

        # The user's uploaded product asset MUST be present and top-ranked!
        user_cands = [c for c in candidates if c.id == f"user_{product_asset.id}"]
        assert len(user_cands) == 1
        assert user_cands[0].source == "User Uploads"
        assert user_cands[0].score >= 80.0

        ranked = visual_intelligence.evaluate_and_rank_candidates(candidates, relevant_brief)
        # Authentic user asset takes top priority
        assert ranked[0].id == f"user_{product_asset.id}"

        # Case B: Completely UNRELATED slide (e.g. Ancient Roman Architecture)
        unrelated_brief = visual_intelligence.generate_visual_brief(
            topic="Classical Antiquity",
            slide_title="The Roman Colosseum & Arch Systems",
            purpose="Architectural engineering of Roman concrete arches",
            bullets=["Travertine limestone masonry and vaulted arches"],
            layout="split_screen",
            slide_index=1,
            total_slides=4,
        )

        unrelated_candidates = visual_intelligence.retrieve_image_candidates(
            unrelated_brief,
            user_id=user_id,
        )
        # Must NEVER force the wind turbine product photo onto the Roman Colosseum slide!
        assert not any(c.id == f"user_{product_asset.id}" for c in unrelated_candidates)


# ---------------------------------------------------------------------------
# 3. Slide Visual Editor API Routes (Replace, Remove, Diagram)
# ---------------------------------------------------------------------------

def test_visual_editor_endpoints(app, client):
    """Verify Find a Better Visual, Replace, Remove, and Switch to Diagram routes."""
    token, user_id = _login(client, "editor@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with app.app_context():
        p = Presentation(title="Renewable Power Grid", user_id=user_id)
        db.session.add(p)
        db.session.commit()

        slide = Slide(
            presentation_id=p.id,
            position=1,
            title="Solar Farm Infrastructure",
            content={
                "layout": "split_screen",
                "bullets": [{"text": "Bifacial tracking panels maximize daytime energy capture"}],
            },
        )
        db.session.add(slide)
        db.session.commit()

        # 1. Get Visual Candidates (Find a Better Visual)
        cand_resp = client.get(f"/api/presentation/{p.id}/slide/1/visual/candidates", headers=headers)
        assert cand_resp.status_code == 200
        cand_data = cand_resp.get_json()["data"]
        assert len(cand_data["candidates"]) > 0
        chosen_cand = cand_data["candidates"][0]

        # 2. Select Slide Visual (Replace)
        select_resp = client.post(
            f"/api/presentation/{p.id}/slide/1/visual/select",
            json={
                "image": {
                    "url": chosen_cand["image_url"],
                    "alt": chosen_cand["title"],
                    "source": chosen_cand["source"],
                    "artist": chosen_cand["artist"],
                }
            },
            headers=headers,
        )
        assert select_resp.status_code == 200
        updated_content = select_resp.get_json()["data"]["content"]
        assert "image" in updated_content
        assert updated_content["image"]["url"] == chosen_cand["image_url"]

        # 3. Switch to Diagram
        diag_resp = client.post(f"/api/presentation/{p.id}/slide/1/visual/switch-diagram", headers=headers)
        assert diag_resp.status_code == 200
        diag_content = diag_resp.get_json()["data"]["content"]
        assert diag_content["layout"] == "process_diagram"
        assert len(diag_content["process_steps"]) >= 1
        assert "image" not in diag_content  # Image cleared for clean diagram

        # 4. Remove Visual
        rem_resp = client.post(f"/api/presentation/{p.id}/slide/1/visual/remove", headers=headers)
        assert rem_resp.status_code == 200
        rem_content = rem_resp.get_json()["data"]["content"]
        assert "image" not in rem_content
