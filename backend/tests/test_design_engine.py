"""Tests for SlideMind Next-Generation Presentation Design Engine.

Covers:
- 10+ Premium design systems
- Design intelligence planning and pacing
- Layout specification and visual assets
- Google Slides API rich element creation
- Automated design quality audit and auto-correct
- Native PPTX and PDF export engines
- Single slide regeneration and direct download endpoints
"""
import io
import pytest

from app import create_app
from database import db
from models import Presentation, Slide, User
from services import design_auditor, design_intelligence, design_systems, exporter, slides
from utils.http import issue_token


@pytest.fixture()
def app():
    a = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "DEV_LOGIN_ENABLED": True,
        "RATELIMIT_ENABLED": False,
        "GEMINI_API_KEY": "test-key",
    })
    with a.app_context():
        db.create_all()
        yield a
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user_and_deck(app):
    with app.app_context():
        u = User(email="designer@slidemind.ai")
        db.session.add(u)
        db.session.commit()

        p = Presentation(user_id=u.id, title="Quantum Computing 2026", settings={"theme": "dark_technology"})
        db.session.add(p)
        db.session.flush()

        layouts = ["full_bleed_hero", "problem_solution", "cards_hierarchy", "stats_kpi", "conclusion_cta"]
        for i, l in enumerate(layouts, start=1):
            s = Slide(
                presentation_id=p.id,
                position=i,
                title=f"Quantum Milestone {i}",
                content={"layout": l, "bullets": [{"text": f"Crucial quantum metric {i}.1 with 99.8% fidelity", "source_ids": []}]},
                speaker_notes=f"Discuss quantum advancement stage {i}.",
            )
            db.session.add(s)
        db.session.commit()
        uid = u.id
        pid = p.id
        token = issue_token(u.id)
    return uid, pid, {"Authorization": f"Bearer {token}"}


# 1. Premium Design Systems Test
def test_design_systems_palette_and_compatibility():
    systems = design_systems.list_design_systems()
    assert len(systems) >= 10

    expected_ids = [
        "swiss_minimal", "apple_keynote", "startup_pitch", "dark_technology", "editorial_magazine",
        "corporate_premium", "education_modern", "data_storytelling", "creative_agency", "futuristic_ai"
    ]
    found_ids = {s["id"] for s in systems}
    for eid in expected_ids:
        assert eid in found_ids

    # Test resolution and fallback
    ds = design_systems.get_design_system("futuristic_ai")
    assert ds.name == "Futuristic AI" and ds.dark_mode is True

    # Legacy fallback
    legacy = design_systems.get_design_system("modern_light")
    assert legacy.id == "swiss_minimal"


# 2. Design Intelligence Planning & Layout Pacing
def test_design_intelligence_planning_generates_diverse_pacing():
    plan = design_intelligence.generate_design_plan("Renewable Energy Revolution", audience="investors", slide_count=5)
    assert plan["presentation_title"]
    assert len(plan["slides"]) == 5
    assert plan["slides"][0]["layout"] == "full_bleed_hero"
    assert plan["slides"][-1]["layout"] in ("conclusion_cta", "quote_testimonial")

    layouts = [s["layout"] for s in plan["slides"]]
    # Ensure layout variety (not all identical)
    assert len(set(layouts)) >= 3


# 3. Visual Assets Specification & Layout Enrichment


# 4. Google Slides API Rich Element Builders
def test_google_slides_rich_elements():
    # Test image requests
    im_reqs = slides.image_requests("slide_123", "https://images.unsplash.com/sample.jpg", 1.0, 1.5, 6.0, 4.0)
    assert len(im_reqs) == 1
    assert "createImage" in im_reqs[0]
    assert im_reqs[0]["createImage"]["url"] == "https://images.unsplash.com/sample.jpg"

    # Test shape card container
    sh_reqs, sid = slides.shape_card_requests("slide_123", 1.0, 1.0, 4.0, 3.0, (1.0, 1.0, 1.0), (0.2, 0.2, 0.2))
    assert len(sh_reqs) == 2
    assert "createShape" in sh_reqs[0]
    assert sh_reqs[0]["createShape"]["shapeType"] == "ROUNDED_RECTANGLE"


# 5. Automated Design Quality Auditor & Auto-Remediation
def test_design_auditor_and_auto_correct(app, user_and_deck):
    uid, pid, h = user_and_deck
    with app.app_context():
        p_db = db.session.get(Presentation, pid)
        audit = design_auditor.audit_presentation_design(p_db)
        assert "score" in audit and "grade" in audit
        assert audit["score"] >= 70

        # Auto-correct should optimize layouts and enrich visuals
        res = design_auditor.auto_correct_presentation_design(p_db)
        assert res["presentation_id"] == pid
        assert res["audit_after"]["score"] >= 80


# 6. Native PPTX & PDF Export Engines
def test_native_pptx_and_pdf_exports(app, user_and_deck):
    uid, pid, h = user_and_deck
    with app.app_context():
        p_db = db.session.get(Presentation, pid)

        # PPTX Export
        pptx_bytes = exporter.export_pptx(p_db)
        assert isinstance(pptx_bytes, bytes)
        assert len(pptx_bytes) > 1000
        assert pptx_bytes[:4] == b"PK\x03\x04"  # standard ZIP / PPTX header

        # PDF Export
        pdf_bytes = exporter.export_pdf(p_db)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 500
        assert pdf_bytes[:4] == b"%PDF"


# 7. Presentation Download Route (PPTX and PDF)
def test_download_presentation_endpoint(client, user_and_deck):
    uid, pid, h = user_and_deck
    # Download PPTX
    r_pptx = client.get(f"/api/presentation/{pid}/download?format=pptx", headers=h)
    assert r_pptx.status_code == 200
    assert r_pptx.headers["Content-Type"] == slides.EXPORT_MIMES["pptx"]
    assert r_pptx.data[:4] == b"PK\x03\x04"

    # Download PDF
    r_pdf = client.get(f"/api/presentation/{pid}/download?format=pdf", headers=h)
    assert r_pdf.status_code == 200
    assert r_pdf.headers["Content-Type"] == "application/pdf"
    assert r_pdf.data[:4] == b"%PDF"


# 8. Single Slide Regeneration Route
def test_single_slide_regeneration_endpoint(client, user_and_deck):
    uid, pid, h = user_and_deck
    # Regenerate slide 2 with split_screen layout
    r = client.post(
        f"/api/presentation/{pid}/slide/2/regenerate",
        json={"instructions": "Focus on high-level architecture", "layout": "split_screen"},
        headers=h,
    )
    assert r.status_code == 200
    data = r.get_json()["data"]
    assert data["slide"]["position"] == 2
    assert data["slide"]["content"]["layout"] == "split_screen"
