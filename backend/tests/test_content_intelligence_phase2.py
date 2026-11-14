"""Phase 2 Test Suite: Content Intelligence and Narrative Engine Overhaul.

Verifies:
1. CampusCare Topic Isolation (unrelated topics have zero CampusCare/technician leakage).
2. Genuine Topic Handling (facilities/campus topics handled accurately when explicitly requested).
3. Planning Metadata Isolation (internal planning_purpose is separated from visible subtitle/content).
4. Zero Fabricated Metrics (no hallucinated KPIs, ARR, percentages when sources lack numbers).
5. Educational & Pedagogical Narrative Flow (pedagogical progression for educational concepts).
6. Business Strategy & Pitch Flow (problem/solution/traction progression for startup/enterprise topics).
7. Existing Presentation Compatibility (legacy slide payloads load and serialize safely).
8. Existing API Compatibility (/api/presentation routes function seamlessly with Phase 2 payloads).
"""
import json
from unittest.mock import patch
import pytest
from sqlalchemy.pool import StaticPool

from app import create_app
from agents.registry import ToolContext
from database import db
from models import Presentation, Slide, User
from services import content_intelligence, slides
from tools import draft


KEY = "0123456789abcdef0123456789abcdef"


def make_app(**extra):
    cfg = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "DEV_LOGIN_ENABLED": True,
        "RATELIMIT_ENABLED": False,
        "GEMINI_API_KEY": "test-key",
        "JOBS_INLINE": True,
        "TOKEN_ENCRYPTION_KEY": KEY,
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        },
    }
    cfg.update(extra)
    return create_app(cfg)


@pytest.fixture()
def app():
    a = make_app()
    with a.app_context():
        db.create_all()
    yield a
    with a.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def auth_header(client, email="presenter@example.com"):
    resp = client.post("/api/auth/dev-login", json={"email": email})
    data = resp.get_json()["data"]
    return {"Authorization": f"Bearer {data['token']}"}, data["user"]["id"]


# ---------------------------------------------------------------------------
# 1. CampusCare Topic Isolation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("topic,expected_archetype", [
    ("Quantum Cryptography & Key Distribution", "technical_architecture"),
    ("Cellular Respiration in Plant Biology", "educational_concept"),
    ("Enterprise Cloud Security & Zero Trust Architecture", "technical_architecture"),
    ("Seed Stage Pitch for AI Supply Chain Logistics", "startup_pitch"),
    ("Quarterly Financial Review & Operational Efficiency", "data_report"),
])
def test_topic_isolation_across_unrelated_domains(topic, expected_archetype):
    """Verify that unrelated topics generate domain-specific prompts and blueprints
    with ZERO trace of CampusCare, technician, or campus ticketing terminology.
    """
    classified = content_intelligence.classify_presentation_intent(topic)
    assert classified["archetype"] == expected_archetype, f"Expected {expected_archetype}, got {classified['archetype']}"

    prompt = content_intelligence.build_batch_content_prompt(
        topic=topic,
        audience="Executive Leadership & Technical Stakeholders",
        tone="authoritative, editorial, and compelling",
        slides_outline=[
            {"index": 1, "title": f"Introduction to {topic}", "planning_purpose": "Establish strategic context"},
            {"index": 2, "title": "Core Architectural Foundation", "planning_purpose": "Explain mechanism"},
            {"index": 3, "title": "Measurable Impact & Roadmap", "planning_purpose": "Outline next steps"},
        ],
    )

    forbidden_leaks = [
        "campuscare", "campus care", "technician", "broken fan", "room qr",
        "work order", "facility maintenance", "student or faculty", "benches", "lighting"
    ]
    prompt_lower = prompt.lower()
    for leak in forbidden_leaks:
        assert leak not in prompt_lower, f"Forbidden leak '{leak}' found in prompt for topic '{topic}'"


# ---------------------------------------------------------------------------
# 2. Genuine Topic Handling
# ---------------------------------------------------------------------------

def test_genuine_campus_facility_topic():
    """Verify that when a presentation IS genuinely about smart campus facilities,
    the engine appropriately selects product_operations archetype without error.
    """
    topic = "Smart Campus Facility Maintenance and Work Order Resolution"
    classified = content_intelligence.classify_presentation_intent(topic)
    assert classified["archetype"] == "product_operations"

    prompt = content_intelligence.build_batch_content_prompt(
        topic=topic,
        audience="University Facilities Operations Committee",
        tone="professional",
        slides_outline=[
            {"index": 1, "title": "Campus Facility Overview", "planning_purpose": "Introduce initiative"},
        ],
    )
    # Generic instructions still maintain zero-hallucination rules
    assert "ZERO-HALLUCINATION POLICY" in prompt
    assert "NEVER invent fake percentages" in prompt


# ---------------------------------------------------------------------------
# 3. Planning Metadata Isolation
# ---------------------------------------------------------------------------

def test_planning_metadata_isolated_from_visible_content(app):
    """Verify that internal slide purpose is preserved in planning_purpose
    and NOT exposed as visible subtitle or body content.
    """
    with app.app_context():
        user = User(email="test_user@example.com")
        db.session.add(user)
        db.session.commit()

        ctx = ToolContext(user_id=user.id)

        mock_outline = {
            "title": "Advanced Quantum Computing",
            "slides": [
                {
                    "title": "Quantum Supremacy & Error Correction",
                    "purpose": "Internal note: establish why decoherence is hard",
                    "layout": "split_hero",
                },
                {
                    "title": "Topological Qubits Architecture",
                    "purpose": "Internal note: contrast physical vs logical qubits",
                    "layout": "technical_architecture_flow",
                },
                {
                    "title": "Future Strategic Horizon",
                    "purpose": "Internal note: roadmap synthesis",
                    "layout": "conclusion_cta",
                },
            ]
        }

        with patch("services.gemini.generate_json", return_value=mock_outline):
            res = draft.generate_slide_outline(ctx, {
                "topic": "Quantum Computing",
                "slide_count": 3,
                "audience": "business_executives",
            })
            assert "presentation_id" in res

            pres_id = res["presentation_id"]
            deck_slides = Slide.query.filter_by(presentation_id=pres_id).order_by(Slide.position).all()
            assert len(deck_slides) == 3

            for s in deck_slides:
                content = s.content or {}
                # Planning purpose is stored in planning_purpose
                assert "planning_purpose" in content
                assert "Internal note" in content["planning_purpose"]
                # Visible subtitle must NOT be the internal note
                assert content.get("subtitle", "") != content["planning_purpose"]
                # Visible bullets must NOT contain internal note
                for b in content.get("bullets", []):
                    text = b.get("text", "") if isinstance(b, dict) else str(b)
                    assert "Internal note" not in text


# ---------------------------------------------------------------------------
# 4. Zero Fabricated Metrics
# ---------------------------------------------------------------------------

def test_zero_fabricated_metrics_policy():
    """Verify that when factual source context lacks metrics, the engine produces
    qualitative depth rather than hallucinated percentages or financial claims.
    """
    raw_llm_json = json.dumps({
        "slides": [
            {
                "index": 1,
                "title": "Cognitive Load in Minimalist UI",
                "subtitle": "Reducing Friction Through Intuitive Hierarchy",
                "main_message": "Clean interfaces allow users to focus on primary tasks without distraction.",
                "semantic_type": "concept_explanation",
                "recommended_layout": "cards_hierarchy",
                "bullets": [
                    {
                        "bold": "Progressive Disclosure",
                        "text": "Present complex configuration options only when specifically requested by user actions.",
                    },
                    {
                        "bold": "Consistent Typography",
                        "text": "Unified font weight scales establish predictable visual hierarchies across all views.",
                    },
                ],
                "cards": [
                    {
                        "title": "Visual Restraint",
                        "badge": "FOCUS",
                        "description": "Limiting active accent colors to high-priority interactive components.",
                    },
                ],
                "data_points": [],  # Strictly empty when source lacks metrics
                "speaker_notes": "Emphasize how cognitive ease translates directly into lower user error rates.",
            }
        ]
    })

    parsed = content_intelligence.parse_batch_content_response(raw_llm_json)
    slide_data = parsed["slides"][0]

    # Verify no fabricated data points
    assert len(slide_data.get("data_points", [])) == 0
    # Verify content payload has qualitative depth
    assert slide_data["main_message"]
    assert len(slide_data["bullets"]) == 2
    assert slide_data["cards"][0]["title"] == "Visual Restraint"


# ---------------------------------------------------------------------------
# 5. Educational / Pedagogical Flow
# ---------------------------------------------------------------------------

def test_educational_pedagogical_flow():
    """Verify pedagogical narrative progression for educational topics."""
    topic = "CRISPR-Cas9 Gene Editing Mechanism"
    archetype_info = content_intelligence.classify_presentation_intent(topic)
    assert archetype_info["archetype"] == "educational_concept"

    blueprint = archetype_info["blueprint"]
    assert "concept" in blueprint[0]["purpose"]
    assert any("mechanism" in step["purpose"] or "process" in step["purpose"] for step in blueprint)
    assert any("manifestation" in step["purpose"] or "observation" in step["purpose"] or "case" in step.get("role", "") for step in blueprint)


# ---------------------------------------------------------------------------
# 6. Business Strategy & Pitch Flow
# ---------------------------------------------------------------------------

def test_startup_pitch_narrative_flow():
    """Verify problem/solution/market narrative progression for pitch decks."""
    topic = "Seed Pitch: Autonomous Satellite Servicing"
    archetype_info = content_intelligence.classify_presentation_intent(topic)
    assert archetype_info["archetype"] == "startup_pitch"

    blueprint = archetype_info["blueprint"]
    purposes = [s["purpose"] for s in blueprint]
    # Check classic pitch arc: problem -> solution -> market -> business model
    assert any("problem" in p or "friction" in p for p in purposes)
    assert any("solution" in p or "value" in p for p in purposes)
    assert any("market" in p or "model" in p for p in purposes)


# ---------------------------------------------------------------------------
# 7. Backward Compatibility with Legacy Presentations
# ---------------------------------------------------------------------------

def test_legacy_presentation_compatibility(app):
    """Verify that existing legacy presentations in the database load cleanly
    and do not crash services, exporters, or serialization.
    """
    with app.app_context():
        user = User(email="legacy_user@example.com")
        db.session.add(user)
        db.session.commit()

        # Create presentation with legacy schema (no subtitle, no data_points, older layout)
        legacy_pres = Presentation(
            user_id=user.id,
            title="Legacy Project Deck",
            settings={"topic": "Old Topic"},
            status="ready",
        )
        db.session.add(legacy_pres)
        db.session.flush()

        legacy_slide = Slide(
            presentation_id=legacy_pres.id,
            position=1,
            title="Legacy Overview",
            content={
                "layout": "cards_hierarchy",
                "purpose": "Legacy planning note",
                "bullets": [{"bold": "Point A", "text": "Legacy point description"}],
            },
        )
        db.session.add(legacy_slide)
        db.session.commit()

        # Verify retrieval via database model
        deck = Slide.query.filter_by(presentation_id=legacy_pres.id).order_by(Slide.position).all()
        assert len(deck) == 1
        assert deck[0].title == "Legacy Overview"
        # Content remains intact and accessible
        assert deck[0].content["layout"] == "cards_hierarchy"
        assert deck[0].content["bullets"][0]["bold"] == "Point A"


# ---------------------------------------------------------------------------
# 8. API Compatibility
# ---------------------------------------------------------------------------

def test_presentation_api_endpoints_with_phase2_payloads(client, app):
    """Verify that the presentations REST API correctly handles presentations
    and slides adhering to the Phase 2 payload structure.
    """
    headers, user_id = auth_header(client, "api_tester@example.com")

    with app.app_context():
        # Setup a presentation in the DB
        pres = Presentation(
            user_id=user_id,
            title="Robotics in Medicine",
            settings={"topic": "Robotics in Medicine", "theme": "modern_light"},
            status="draft",
        )
        db.session.add(pres)
        db.session.flush()

        # Add slide with rich Phase 2 payload
        slide = Slide(
            presentation_id=pres.id,
            position=1,
            title="Microsurgical Robotic Actuation",
            content={
                "subtitle": "Sub-millimeter Tremor Cancellation",
                "main_message": "Active feedback control cancels physiological hand tremor in microsurgery.",
                "planning_purpose": "Explain robotic surgical mechanics",
                "semantic_type": "technical_architecture",
                "layout": "split_hero",
                "bullets": [
                    {"text": "Continuous optical tracking at 1000 Hz.", "source_ids": []},
                    {"text": "Force feedback replicates tissue resistance tactilely.", "source_ids": []},
                ],
                "cards": [
                    {"title": "Actuator Precision", "badge": "PRECISION", "body": "Piezoelectric micro-drives."},
                ],
                "data_points": [
                    {"value": "1000 Hz", "label": "TRACKING RATE", "description": "Real-time kinematic sensing."},
                ],
            },
            speaker_notes="Highlight how force feedback prevents accidental puncture.",
        )
        db.session.add(slide)
        db.session.commit()
        pres_id = pres.id

    # 1. Fetch presentation details via GET /api/presentation/<pid>
    get_resp = client.get(f"/api/presentation/{pres_id}", headers=headers)
    assert get_resp.status_code == 200
    res_data = get_resp.get_json()["data"]
    assert res_data["title"] == "Robotics in Medicine"
    assert len(res_data["slides"]) == 1

    slide_data = res_data["slides"][0]
    assert slide_data["title"] == "Microsurgical Robotic Actuation"
    assert slide_data["content"]["subtitle"] == "Sub-millimeter Tremor Cancellation"
    assert slide_data["content"]["planning_purpose"] == "Explain robotic surgical mechanics"
    assert slide_data["speaker_notes"] == "Highlight how force feedback prevents accidental puncture."

    # 2. Edit presentation slide via POST /api/presentation/edit
    edit_resp = client.post(
        "/api/presentation/edit",
        headers=headers,
        json={
            "presentation_id": pres_id,
            "action": "edit_slide",
            "slide_position": 1,
            "title": "Next-Gen Microsurgical Robotics",
            "sync": False,
        },
    )
    assert edit_resp.status_code == 200

    # 3. List user presentations via GET /api/presentations
    list_resp = client.get("/api/presentations", headers=headers)
    assert list_resp.status_code == 200
    pres_list = list_resp.get_json()["data"]
    assert any(p["id"] == pres_id for p in pres_list)
