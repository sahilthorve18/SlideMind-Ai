"""Tests for production launch readiness:
- GDPR Data Export & Deletion
- Guest Presentation Limit enforcement
- Production SECRET_KEY protection
"""
import pytest
from app import create_app
from database import db
from models import Conversation, Document, Message, Presentation, Slide, User


@pytest.fixture
def app():
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-launch-readiness-key",
        "GUEST_MAX_PRESENTATIONS": 3,
        "DEV_LOGIN_ENABLED": True,
        "GEMINI_API_KEY": "fake-key-for-test",
        "STORAGE_PROVIDER": "local",
    }
    app = create_app(test_config)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_gdpr_export_and_delete(client, app):
    # 1. Sign up a user
    r = client.post("/api/auth/email-login", json={"email": "gdpr.tester@example.com"})
    assert r.status_code == 200
    token = r.get_json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    with app.app_context():
        user = User.query.filter_by(email="gdpr.tester@example.com").first()
        assert user is not None
        # Add conversation, presentation, document
        c = Conversation(user_id=user.id, title="Test GDPR Chat")
        db.session.add(c)
        db.session.flush()
        db.session.add(Message(conversation_id=c.id, role="user", content="Hello"))

        p = Presentation(user_id=user.id, title="Test GDPR Deck", settings={"theme": "linear_dark"}, status="draft")
        db.session.add(p)
        db.session.flush()
        db.session.add(Slide(presentation_id=p.id, position=1, title="Slide 1", content={"bullets": []}))

        d = Document(user_id=user.id, filename="notes.txt", file_type="txt", size_bytes=100, content_hash="hash123", status="indexed")
        db.session.add(d)
        db.session.commit()

    # 2. Test export-data endpoint
    res = client.get("/api/user/export-data", headers=headers)
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["user"]["email"] == "gdpr.tester@example.com"
    assert len(data["conversations"]) == 1
    assert len(data["presentations"]) == 1
    assert len(data["documents"]) == 1

    # Also test /api/auth/export-data alias
    res_alias = client.get("/api/auth/export-data", headers=headers)
    assert res_alias.status_code == 200

    # 3. Test delete-account endpoint
    del_res = client.post("/api/user/delete-account", headers=headers)
    assert del_res.status_code == 200
    assert del_res.get_json()["data"]["deleted"] is True

    # 4. Verify in DB that all user records were wiped
    with app.app_context():
        assert User.query.filter_by(email="gdpr.tester@example.com").first() is None
        assert Conversation.query.filter_by(title="Test GDPR Chat").first() is None
        assert Presentation.query.filter_by(title="Test GDPR Deck").first() is None
        assert Document.query.filter_by(filename="notes.txt").first() is None


def test_guest_presentation_limit(client, app):
    # 1. Login as guest
    r = client.post("/api/auth/guest-login")
    assert r.status_code == 200
    guest_data = r.get_json()["data"]
    token = guest_data["token"]
    headers = {"Authorization": f"Bearer {token}"}

    with app.app_context():
        user = User.query.filter_by(id=guest_data["user"]["id"]).first()
        assert user.is_guest is True

        # Pre-populate 3 presentations (reaching limit of 3)
        for i in range(3):
            p = Presentation(user_id=user.id, title=f"Guest Deck {i+1}", settings={}, status="draft")
            db.session.add(p)
        db.session.commit()

    # 2. Attempt to create 4th presentation via /api/presentation/create
    payload = {
        "topic": "The 4th presentation",
        "slide_count": 5,
        "audience": "college_students",
        "theme": "linear_dark",
    }
    res = client.post("/api/presentation/create", json=payload, headers=headers)
    assert res.status_code == 403
    body = res.get_json()
    assert body["error"]["code"] == "guest_limit_reached"

    # 3. Attempt to create 4th presentation via /api/chat
    chat_payload = {
        "message": "Create a 5 slide deck on Quantum Computing",
    }
    chat_res = client.post("/api/chat", json=chat_payload, headers=headers)
    assert chat_res.status_code == 403
    chat_body = chat_res.get_json()
    assert chat_body["error"]["code"] == "guest_limit_reached"


def test_production_secret_key_protection(monkeypatch):
    import importlib
    import config

    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "dev-only-change-me")

    try:
        with pytest.raises(RuntimeError) as exc_info:
            importlib.reload(config)
        assert "SECRET_KEY" in str(exc_info.value)
    finally:
        monkeypatch.setenv("ENV", "development")
        monkeypatch.setenv("FLASK_ENV", "development")
        monkeypatch.setenv("SECRET_KEY", "dev-only-change-me")
        importlib.reload(config)
