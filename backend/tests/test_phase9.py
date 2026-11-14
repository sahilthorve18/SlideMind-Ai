import os
from types import SimpleNamespace

os.environ["SLIDEMIND_SKIP_AUTOAPP"] = "1"

import pytest

from app import create_app
from database import db
from models import Presentation, Slide, User
from services import gemini, rehearsal
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


def create_deck(user_id):
    p = Presentation(user_id=user_id, title="Pitch Practice", settings={"duration_minutes": 3})
    db.session.add(p)
    db.session.flush()

    s1 = Slide(
        presentation_id=p.id,
        position=1,
        title="Introduction & Vision",
        content={"bullets": [{"text": "Disrupting renewable energy markets with high density battery storage"}]},
        speaker_notes="Welcome the audience and highlight the market transition to clean grid infrastructure.",
    )
    s2 = Slide(
        presentation_id=p.id,
        position=2,
        title="Business Model & Unit Economics",
        content={"bullets": [{"text": "Recurring SaaS subscription revenue with 80% gross margins"}]},
        speaker_notes="Walk through our customer acquisition strategy and recurring revenue expansion.",
    )
    db.session.add_all([s1, s2])
    db.session.commit()
    return p


# ---- Service Unit Tests ----

def test_rehearsal_pacing_and_wpm():
    # 65 words in 30 seconds = 130 WPM (conversational)
    sample_text = "Today we are looking at our core product strategy and how renewable storage transforms utility grids. " * 4
    res = rehearsal.analyze_slide_rehearsal(
        slide_title="Energy Grid",
        bullets=["Renewable energy storage"],
        speaker_notes="Explain the grid storage transformation",
        transcript=sample_text,
        duration_seconds=30,
    )
    assert 120 <= res["wpm"] <= 150
    assert res["pace_status"] == "conversational"
    assert res["pace_score"] == 100


def test_rehearsal_filler_words_detection():
    transcript_with_fillers = "Um so like basically we think that uh you know the revenue is actually growing rapidly."
    res = rehearsal.analyze_slide_rehearsal(
        slide_title="Revenue",
        bullets=["Revenue growth"],
        speaker_notes="Highlight revenue",
        transcript=transcript_with_fillers,
        duration_seconds=15,
    )
    assert res["total_fillers"] >= 4
    assert "um" in res["filler_breakdown"]
    assert "like" in res["filler_breakdown"]
    assert res["filler_score"] < 90
    assert any("filler" in tip.lower() for tip in res["coaching_tips"])


def test_rehearsal_concept_coverage():
    bullets = ["Customer acquisition cost decreased by 40% year over year", "Enterprise retention rate stands at 95%"]
    notes = "Explain customer acquisition cost and net retention rate trends"

    # Transcript covers CAC and retention
    good_transcript = "Our customer acquisition cost has decreased significantly by 40% and our enterprise retention is at 95%."
    res_good = rehearsal.analyze_slide_rehearsal("Metrics", bullets, notes, good_transcript, 20)
    assert res_good["coverage_pct"] >= 50

    # Irrelevant transcript
    bad_transcript = "Let us talk about the weather outside and completely unrelated topics."
    res_bad = rehearsal.analyze_slide_rehearsal("Metrics", bullets, notes, bad_transcript, 20)
    assert res_bad["coverage_pct"] < 30


# ---- Rehearsal Endpoint Tests ----

def test_practice_slide_endpoint(app):
    client = app.test_client()
    headers = login(client, "rehearse@test.com")
    with app.app_context():
        u = User.query.filter_by(email="rehearse@test.com").first()
        p = create_deck(u.id)
        pid = p.id

    r = client.post("/api/rehearsal", json={
        "presentation_id": pid,
        "slide_position": 1,
        "transcript": "Welcome everyone. Today we are introducing our high density battery storage for utility grids.",
        "duration_seconds": 15,
    }, headers=headers)

    assert r.status_code == 200
    data = r.get_json()["data"]
    assert data["slide_title"] == "Introduction & Vision"
    assert "wpm" in data
    assert "pace_status" in data
    assert "coaching_tips" in data
    assert "overall_score" in data


def test_practice_deck_endpoint(app):
    client = app.test_client()
    headers = login(client, "deck_rehearse@test.com")
    with app.app_context():
        u = User.query.filter_by(email="deck_rehearse@test.com").first()
        p = create_deck(u.id)
        pid = p.id

    runs = [
        {
            "slide_position": 1,
            "transcript": "Welcome everyone. We are disrupting the clean energy market with storage technology.",
            "duration_seconds": 25,
        },
        {
            "slide_position": 2,
            "transcript": "Our business model relies on high margin recurring subscription software.",
            "duration_seconds": 30,
        },
    ]

    r = client.post("/api/rehearsal/deck", json={"presentation_id": pid, "runs": runs}, headers=headers)
    assert r.status_code == 200
    data = r.get_json()["data"]
    assert data["slide_count"] == 2
    assert "overall_score" in data
    assert "grade" in data
    assert "total_minutes" in data
    assert "summary_tips" in data
    assert len(data["slide_results"]) == 2

