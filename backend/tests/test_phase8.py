import os
from types import SimpleNamespace

os.environ["SLIDEMIND_SKIP_AUTOAPP"] = "1"

import pytest

from app import create_app
from database import db
from models import Presentation, PresentationVersion, Slide, User
from services import google_auth, slides
from tests.test_phase5 import KEY, FakeDrive, FakeSlidesAPI
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


def create_deck(user_id, count=3, published=False):
    p = Presentation(user_id=user_id, title="Pitch Deck",
                     google_presentation_id="gid123" if published else None,
                     google_url="https://docs.google.com/presentation/d/gid123/edit" if published else None)
    db.session.add(p)
    db.session.flush()
    for i in range(1, count + 1):
        s = Slide(presentation_id=p.id, position=i, title=f"Slide {i}",
                  content={"layout": "title_bullets", "bullets": [{"text": f"Point {i}.1", "source_ids": []}]},
                  speaker_notes=f"Notes for slide {i}")
        db.session.add(s)
    db.session.commit()
    return p


def test_edit_slide_content_and_notes(app):
    client = app.test_client()
    headers = login(client, "edit@test.com")
    with app.app_context():
        u = User.query.filter_by(email="edit@test.com").first()
        p = create_deck(u.id, count=3)
        pid = p.id

    r = client.post("/api/presentation/edit", json={
        "presentation_id": pid,
        "action": "edit_slide",
        "slide_position": 2,
        "title": "Updated Market Size",
        "bullets": ["$50B TAM by 2030", "Rapidly growing segment"],
        "speaker_notes": "Emphasize market compound growth rate.",
        "layout": "two_column",
    }, headers=headers)

    assert r.status_code == 200
    data = r.get_json()["data"]
    assert data["slide_count"] == 3
    s2 = data["slides"][1]
    assert s2["title"] == "Updated Market Size"
    assert len(s2["content"]["bullets"]) == 2
    assert s2["speaker_notes"] == "Emphasize market compound growth rate."
    assert s2["content"]["layout"] == "two_column"

    # Verify version snapshot
    with app.app_context():
        versions = PresentationVersion.query.filter_by(presentation_id=pid).all()
        assert len(versions) == 1
        assert "edit: edit_slide" in versions[0].reason


def test_add_and_delete_slide(app):
    client = app.test_client()
    headers = login(client, "add_del@test.com")
    with app.app_context():
        u = User.query.filter_by(email="add_del@test.com").first()
        p = create_deck(u.id, count=2)
        pid = p.id

    # Add slide at position 2
    r_add = client.post("/api/presentation/edit", json={
        "presentation_id": pid,
        "action": "add_slide",
        "slide_position": 2,
        "title": "Middle Slide",
        "bullets": ["Inserted bullet"],
        "speaker_notes": "Speaking notes for middle slide",
    }, headers=headers)
    assert r_add.status_code == 200
    assert r_add.get_json()["data"]["slide_count"] == 3
    assert r_add.get_json()["data"]["slides"][1]["title"] == "Middle Slide"

    # Delete slide at position 1
    r_del = client.post("/api/presentation/edit", json={
        "presentation_id": pid,
        "action": "delete_slide",
        "slide_position": 1,
    }, headers=headers)
    assert r_del.status_code == 200
    assert r_del.get_json()["data"]["slide_count"] == 2
    assert r_del.get_json()["data"]["slides"][0]["title"] == "Middle Slide"


def test_cannot_delete_last_slide(app):
    client = app.test_client()
    headers = login(client, "last_slide@test.com")
    with app.app_context():
        u = User.query.filter_by(email="last_slide@test.com").first()
        p = create_deck(u.id, count=1)
        pid = p.id

    r = client.post("/api/presentation/edit", json={
        "presentation_id": pid,
        "action": "delete_slide",
        "slide_position": 1,
    }, headers=headers)
    assert r.status_code == 400
    assert "Cannot delete the last slide" in r.get_json()["error"]["message"]


def test_update_presentation_title(app):
    client = app.test_client()
    headers = login(client, "title@test.com")
    with app.app_context():
        u = User.query.filter_by(email="title@test.com").first()
        p = create_deck(u.id, count=2)
        pid = p.id

    r = client.post("/api/presentation/edit", json={
        "presentation_id": pid,
        "action": "update_title",
        "title": "New Strategic Roadmap",
    }, headers=headers)
    assert r.status_code == 200
    assert r.get_json()["data"]["title"] == "New Strategic Roadmap"


def test_sync_to_google_slides_when_published(app, monkeypatch):
    client = app.test_client()
    headers = login(client, "sync_user@test.com")

    fake_slides = FakeSlidesAPI()
    fake_svc = slides.Services(slides=fake_slides, drive=FakeDrive())
    monkeypatch.setattr(slides, "build_services", lambda creds: fake_svc)
    monkeypatch.setattr(google_auth, "credentials_for", lambda u: SimpleNamespace())
    monkeypatch.setattr(google_auth, "is_connected", lambda u: True)

    with app.app_context():
        u = User.query.filter_by(email="sync_user@test.com").first()
        p = create_deck(u.id, count=2, published=True)
        pid = p.id

    r = client.post("/api/presentation/edit", json={
        "presentation_id": pid,
        "action": "edit_slide",
        "slide_position": 1,
        "title": "New Headline",
        "sync": True,
    }, headers=headers)

    assert r.status_code == 200
    data = r.get_json()["data"]
    assert data["google_sync"]["synced"] is True

    # Also test manual sync endpoint /api/presentation/<pid>/sync
    r_sync = client.post(f"/api/presentation/{pid}/sync", headers=headers)
    assert r_sync.status_code == 200
    assert r_sync.get_json()["data"]["sync"]["synced"] is True
