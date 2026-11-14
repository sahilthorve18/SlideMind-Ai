import os

os.environ["SLIDEMIND_SKIP_AUTOAPP"] = "1"

import pytest

from agents import registry
from agents.registry import ToolContext
from app import create_app
from database import db
from models import Presentation, Slide, User
from services import intelligence
from tests.test_phase5 import KEY


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


def login(c, email="user@example.com"):
    r = c.post("/api/auth/dev-login", json={"email": email})
    return {"Authorization": "Bearer " + r.get_json()["data"]["token"]}


def build_sample_deck(user_id, slide_count=4, with_notes=True, sourced=True, layout="title_bullets"):
    p = Presentation(user_id=user_id, title="AI in Healthcare", settings={"duration_minutes": 5, "audience": "executives"})
    db.session.add(p)
    db.session.flush()

    for i in range(1, slide_count + 1):
        if i == 1:
            title = "Introduction: AI in Modern Healthcare"
        elif i == slide_count:
            title = "Summary & Strategic Next Steps"
        else:
            title = f"Clinical Impact Area {i}"

        src_ids = [f"src_{i}"] if sourced else []
        bullets = [
            {"text": f"High ROI automated diagnostics deployment {j}", "source_ids": src_ids}
            for j in range(1, 4)
        ]
        notes = f"Present slide {i} with key strategic metrics on operational efficiency and ROI impact for leadership." if with_notes else ""
        s = Slide(
            presentation_id=p.id,
            position=i,
            title=title,
            content={"layout": layout if i not in (1, slide_count) else "title_bullets", "bullets": bullets},
            speaker_notes=notes,
        )
        db.session.add(s)

    db.session.commit()
    return p


# ---- Intelligence Service Tests ----

def test_empty_presentation_intelligence(app):
    with app.app_context():
        u = User(email="empty@test.com")
        db.session.add(u)
        db.session.commit()
        p = Presentation(user_id=u.id, title="Empty Deck")
        db.session.add(p)
        db.session.commit()

        report = intelligence.analyze_presentation(p)
        assert report["overall_score"] == 0
        assert report["grade"] == "F"
        assert len(report["issues"]) == 1
        assert report["issues"][0]["type"] == "empty_deck"


def test_high_quality_presentation_scores_grade_a(app):
    with app.app_context():
        u = User(email="pro@test.com")
        db.session.add(u)
        db.session.commit()
        p = build_sample_deck(u.id, slide_count=5, with_notes=True, sourced=True)

        report = intelligence.analyze_presentation(p)
        assert report["overall_score"] >= 80
        assert report["grade"] in ("A", "A+")
        assert "pacing" in report["categories"]
        assert "clarity" in report["categories"]
        assert "structure" in report["categories"]
        assert "sourcing" in report["categories"]
        assert report["categories"]["sourcing"]["metrics"]["citation_coverage_pct"] == 100.0


def test_intelligence_pacing_and_duration_analysis(app):
    with app.app_context():
        u = User(email="pace@test.com")
        db.session.add(u)
        db.session.commit()

        # Deck without notes: estimated based on text + dwell
        p = build_sample_deck(u.id, slide_count=4, with_notes=False, sourced=True)
        report = intelligence.analyze_presentation(p, target_duration=10)

        pacing_cat = report["categories"]["pacing"]
        assert pacing_cat["metrics"]["slides_with_notes"] == 0
        assert pacing_cat["metrics"]["total_slides"] == 4
        # Since target is 10 min and 4 slides without notes estimate ~1.5 min, target duration mismatch issue is triggered
        issue_types = {i["type"] for i in report["issues"]}
        assert "target_duration_mismatch" in issue_types

        timeline = report["pacing_timeline"]
        assert len(timeline) == 4
        assert all(t["seconds"] >= 20 for t in timeline)


def test_intelligence_clarity_bullet_overload_and_overflow(app):
    with app.app_context():
        u = User(email="clarity@test.com")
        db.session.add(u)
        db.session.commit()

        p = Presentation(user_id=u.id, title="Clarity Test")
        db.session.add(p)
        db.session.flush()

        # Slide 2 has 8 bullets (overload) and one bullet > 140 chars
        bullets = [{"text": f"Normal bullet {k}", "source_ids": ["s1"]} for k in range(7)]
        bullets.append({"text": "Very long verbose bullet point that exceeds maximum characters " * 3, "source_ids": ["s1"]})

        s1 = Slide(presentation_id=p.id, position=1, title="Intro", content={"bullets": []}, speaker_notes="notes")
        s2 = Slide(presentation_id=p.id, position=2, title="Overloaded Slide", content={"bullets": bullets}, speaker_notes="notes")
        s3 = Slide(presentation_id=p.id, position=3, title="Conclusion", content={"bullets": []}, speaker_notes="notes")
        db.session.add_all([s1, s2, s3])
        db.session.commit()

        report = intelligence.analyze_presentation(p)
        issue_types = {i["type"] for i in report["issues"]}
        assert "bullet_overload" in issue_types
        assert "bullet_length_overflow" in issue_types
        assert report["categories"]["clarity"]["metrics"]["dense_slides_count"] == 1


def test_intelligence_structure_missing_conclusion_and_duplicate_titles(app):
    with app.app_context():
        u = User(email="struct@test.com")
        db.session.add(u)
        db.session.commit()

        p = Presentation(user_id=u.id, title="Structure Test")
        db.session.add(p)
        db.session.flush()

        # Duplicate title on slides 2 and 3, and no concluding slide title
        s1 = Slide(presentation_id=p.id, position=1, title="Introduction", content={"bullets": []}, speaker_notes="n")
        s2 = Slide(presentation_id=p.id, position=2, title="Data Analysis", content={"bullets": [{"text": "pt 1"}]}, speaker_notes="n")
        s3 = Slide(presentation_id=p.id, position=3, title="Data Analysis", content={"bullets": [{"text": "pt 2"}]}, speaker_notes="n")
        s4 = Slide(presentation_id=p.id, position=4, title="Deep Dive Analysis", content={"bullets": [{"text": "pt 3"}]}, speaker_notes="n")
        db.session.add_all([s1, s2, s3, s4])
        db.session.commit()

        report = intelligence.analyze_presentation(p)
        issue_types = {i["type"] for i in report["issues"]}
        assert "duplicate_title" in issue_types
        assert "missing_conclusion" in issue_types
        assert report["categories"]["structure"]["score"] < 80


def test_intelligence_unsourced_charts_and_claims(app):
    with app.app_context():
        u = User(email="source@test.com")
        db.session.add(u)
        db.session.commit()

        p = Presentation(user_id=u.id, title="Sourcing Test")
        db.session.add(p)
        db.session.flush()

        # Unsourced chart and unsourced bullets
        s1 = Slide(presentation_id=p.id, position=1, title="Intro", content={"bullets": []}, speaker_notes="n")
        s2 = Slide(presentation_id=p.id, position=2, title="Metrics",
                   content={"layout": "chart", "bullets": [{"text": "Revenue up 40%"}], "chart": {"type": "bar", "values": [1, 2]}},
                   speaker_notes="n")
        s3 = Slide(presentation_id=p.id, position=3, title="Summary", content={"bullets": []}, speaker_notes="n")
        db.session.add_all([s1, s2, s3])
        db.session.commit()

        report = intelligence.analyze_presentation(p)
        issue_types = {i["type"] for i in report["issues"]}
        assert "unsourced_chart" in issue_types
        assert report["categories"]["sourcing"]["metrics"]["citation_coverage_pct"] == 0.0


def test_auto_fix_presentation(app):
    with app.app_context():
        u = User(email="fix@test.com")
        db.session.add(u)
        db.session.commit()

        p = Presentation(user_id=u.id, title="Fix Test")
        db.session.add(p)
        db.session.flush()

        long_txt = "This is a remarkably long bullet text that should definitely be shortened by the automated intelligence engine trimming function." * 2
        s1 = Slide(presentation_id=p.id, position=1, title="Slide 1", content={"bullets": [{"text": long_txt}]}, speaker_notes="")
        s2 = Slide(presentation_id=p.id, position=2, title="Slide 2", content={"bullets": [{"text": "Normal point"}]}, speaker_notes="")
        db.session.add_all([s1, s2])
        db.session.commit()

        # Test generate_missing_notes
        res = intelligence.auto_fix_presentation(p, "generate_missing_notes")
        assert res["ok"] is True
        assert res["modified_slides"] == 2
        assert len(s1.speaker_notes) > 10
        assert len(s2.speaker_notes) > 10

        # Test trim_overflow
        res2 = intelligence.auto_fix_presentation(p, "trim_overflow")
        assert res2["ok"] is True
        assert res2["modified_slides"] == 1
        assert len(s1.content["bullets"][0]["text"]) <= 140


# ---- API Endpoint Tests ----

def test_get_intelligence_endpoint(app):
    client = app.test_client()
    headers = login(client, "api_intel@test.com")

    # 404 for nonexistent
    r = client.get("/api/presentation/fake-id/intelligence", headers=headers)
    assert r.status_code == 404

    # Build deck
    with app.app_context():
        u = User.query.filter_by(email="api_intel@test.com").first()
        p = build_sample_deck(u.id, slide_count=4)
        pid = p.id

    r = client.get(f"/api/presentation/{pid}/intelligence?target_duration=5&audience=executives", headers=headers)
    assert r.status_code == 200
    data = r.get_json()["data"]
    assert data["presentation_id"] == pid
    assert "overall_score" in data
    assert "grade" in data
    assert "categories" in data
    assert "recommendations" in data
    assert "pacing_timeline" in data


def test_fix_intelligence_endpoint(app):
    client = app.test_client()
    headers = login(client, "fix_endpoint@test.com")

    with app.app_context():
        u = User.query.filter_by(email="fix_endpoint@test.com").first()
        p = build_sample_deck(u.id, slide_count=3, with_notes=False)
        pid = p.id

    # Bad action
    r = client.post(f"/api/presentation/{pid}/intelligence/fix", json={"action_type": "invalid"}, headers=headers)
    assert r.status_code == 400

    # Valid action
    r = client.post(f"/api/presentation/{pid}/intelligence/fix", json={"action_type": "generate_missing_notes"}, headers=headers)
    assert r.status_code == 200
    res = r.get_json()["data"]
    assert res["fix_result"]["ok"] is True
    assert res["fix_result"]["modified_slides"] == 3
    assert res["intelligence"]["categories"]["pacing"]["metrics"]["slides_with_notes"] == 3


def test_verify_presentation_tool_includes_intelligence(app):
    with app.app_context():
        u = User(email="tool_test@test.com")
        db.session.add(u)
        db.session.commit()
        p = build_sample_deck(u.id, slide_count=4)
        ctx = ToolContext(user_id=u.id)

        v = registry.execute("verify_presentation", {"presentation_id": p.id}, ctx)
        assert v["ok"] is True
        assert "overall_score" in v
        assert "grade" in v
        assert "categories" in v
        assert "recommendations" in v
