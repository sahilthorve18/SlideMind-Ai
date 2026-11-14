import os

os.environ["SLIDEMIND_SKIP_AUTOAPP"] = "1"

import pytest

from app import create_app
from database import db
from routes import conversations as conv_routes
from services import gemini


@pytest.fixture()
def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "DEV_LOGIN_ENABLED": True,
                      "RATELIMIT_ENABLED": False, "GEMINI_API_KEY": "test-key"})
    with app.test_client() as c:
        yield c
    with app.app_context():
        db.drop_all()


def login(client):
    r = client.post("/api/auth/dev-login", json={"email": "a@example.com"})
    return {"Authorization": "Bearer " + r.get_json()["data"]["token"]}


def test_chat_persists_reply_and_passes_history(client, monkeypatch):
    seen = []
    monkeypatch.setattr(conv_routes, "run_agent", lambda history, ctx, active=None, **kw: (seen.append(list(history)) or f"reply-{len(history)}"))
    h = login(client)
    r1 = client.post("/api/chat", json={"message": "Plan a deck"}, headers=h).get_json()["data"]
    assert r1["reply"] == "reply-1"
    cid = r1["conversation_id"]
    r2 = client.post("/api/chat", json={"message": "10 slides", "conversation_id": cid}, headers=h).get_json()["data"]
    assert r2["reply"] == "reply-3"  # user, assistant, user
    assert [m["role"] for m in seen[1]] == ["user", "assistant", "user"]
    conv = client.get(f"/api/conversations/{cid}", headers=h).get_json()["data"]
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant", "user", "assistant"]
    assert conv["title"] == "Plan a deck"


def test_upstream_failure_returns_502_and_no_fake_reply(client, monkeypatch):
    def boom(history, ctx, active=None, **kw):
        raise gemini.GeminiError("The AI service returned an error.")
    monkeypatch.setattr(conv_routes, "run_agent", boom)
    h = login(client)
    r = client.post("/api/chat", json={"message": "hello"}, headers=h)
    assert r.status_code == 502
    hist = client.get("/api/history", headers=h).get_json()["data"]
    conv = client.get(f"/api/conversations/{hist[0]['id']}", headers=h).get_json()["data"]
    assert [m["role"] for m in conv["messages"]] == ["user"]


def test_build_contents_maps_roles(client):
    with client.application.app_context():
        c = gemini.build_contents([{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}])
    assert [x.role for x in c] == ["user", "model"]
