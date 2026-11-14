import os

os.environ["SLIDEMIND_SKIP_AUTOAPP"] = "1"

import pytest

from app import create_app
from database import db
from models import Presentation, Slide, User
from tests.test_phase5 import KEY
from tests.test_phase6 import login


def make_app(**extra):
    cfg = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "DEV_LOGIN_ENABLED": True,
        "RATELIMIT_ENABLED": False,
        "GEMINI_API_KEY": "k",
        "JOBS_INLINE": True,
        "TOKEN_ENCRYPTION_KEY": KEY,
    }
    cfg.update(extra)
    return create_app(cfg)


@pytest.fixture()
def app():
    a = make_app()
    yield a
    with a.app_context():
        db.drop_all()


def test_health_check_endpoint(app):
    client = app.test_client()
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["data"]["status"] == "healthy"


def test_cors_headers_configuration(app):
    client = app.test_client()
    r = client.options("/api/health", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert r.status_code == 200
    assert "Access-Control-Allow-Origin" in r.headers


def test_end_to_end_presentation_lifecycle(app):
    """Verifies complete presentation lifecycle: dev-login -> presentation -> intelligence -> edit -> rehearsal."""
    client = app.test_client()
    headers = login(client, "e2e@test.com")

    # 1. Create presentation in database
    with app.app_context():
        u = User.query.filter_by(email="e2e@test.com").first()
        p = Presentation(user_id=u.id, title="E2E Product Launch", settings={"duration_minutes": 5, "theme": "corporate"})
        db.session.add(p)
        db.session.flush()

        s1 = Slide(presentation_id=p.id, position=1, title="Introduction",
                   content={"layout": "title_bullets", "bullets": [{"text": "Welcome to our revolutionary AI platform"}]},
                   speaker_notes="Introduce the overarching vision.")
        s2 = Slide(presentation_id=p.id, position=2, title="Traction & Metrics",
                   content={"layout": "title_bullets", "bullets": [{"text": "100k active users and 45% month over month growth"}]},
                   speaker_notes="Deep dive into customer retention and growth trajectory.")
        s3 = Slide(presentation_id=p.id, position=3, title="Conclusion & Ask",
                   content={"layout": "title_bullets", "bullets": [{"text": "Raising Series A to scale infrastructure"}]},
                   speaker_notes="Close with a strong call to action.")
        db.session.add_all([s1, s2, s3])
        db.session.commit()
        pid = p.id

    # 2. Query Presentation details
    r_get = client.get(f"/api/presentation/{pid}", headers=headers)
    assert r_get.status_code == 200
    assert r_get.get_json()["data"]["title"] == "E2E Product Launch"
    assert len(r_get.get_json()["data"]["slides"]) == 3

    # 3. Query Presentation Intelligence Report
    r_intel = client.get(f"/api/presentation/{pid}/intelligence", headers=headers)
    assert r_intel.status_code == 200
    intel_data = r_intel.get_json()["data"]
    assert "overall_score" in intel_data
    assert intel_data["overall_score"] > 0
    assert len(intel_data["pacing_timeline"]) == 3

    # 4. Apply direct presentation edit
    r_edit = client.post("/api/presentation/edit", json={
        "presentation_id": pid,
        "action": "edit_slide",
        "slide_position": 2,
        "title": "Traction & Unit Economics",
        "bullets": ["100k active users", "50% gross margin"],
    }, headers=headers)
    assert r_edit.status_code == 200
    assert r_edit.get_json()["data"]["slides"][1]["title"] == "Traction & Unit Economics"

    # 5. Run Rehearsal analysis
    r_reh = client.post("/api/rehearsal", json={
        "presentation_id": pid,
        "slide_position": 1,
        "transcript": "Hello everyone and welcome to our product launch. Today we demonstrate how AI accelerates presentation design.",
        "duration_seconds": 15,
    }, headers=headers)
    assert r_reh.status_code == 200
    reh_data = r_reh.get_json()["data"]
    assert reh_data["wpm"] > 0
    assert "coaching_tips" in reh_data
