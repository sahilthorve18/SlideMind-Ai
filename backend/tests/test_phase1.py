import os

os.environ["SLIDEMIND_SKIP_AUTOAPP"] = "1"

import pytest

from app import create_app
from database import db


@pytest.fixture()
def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "DEV_LOGIN_ENABLED": True,
                      "RATELIMIT_ENABLED": False, "GEMINI_API_KEY": "", "GOOGLE_CLIENT_ID": ""})
    with app.test_client() as c:
        yield c
    with app.app_context():
        db.drop_all()


def login(client, email="a@example.com"):
    r = client.post("/api/auth/dev-login", json={"email": email})
    assert r.status_code == 200
    return {"Authorization": "Bearer " + r.get_json()["data"]["token"]}


def test_health(client):
    assert client.get("/api/health").get_json()["data"]["status"] == "healthy"


def test_auth_required(client):
    assert client.get("/api/history").status_code == 401


def test_conversation_lifecycle_and_isolation(client):
    h1, h2 = login(client), login(client, "b@example.com")
    cid = client.post("/api/conversations", headers=h1).get_json()["data"]["id"]
    assert len(client.get("/api/history", headers=h1).get_json()["data"]) == 1
    assert client.get(f"/api/conversations/{cid}", headers=h2).status_code == 404
    assert client.delete(f"/api/conversations/{cid}", headers=h1).status_code == 200


def test_chat_validates_input(client):
    h = login(client)
    assert client.post("/api/chat", json={"message": "  "}, headers=h).status_code == 400
    assert client.post("/api/chat", json={"message": "hi", "conversation_id": "nope"}, headers=h).status_code == 404


def test_chat_without_api_key_is_honest(client):
    h = login(client)
    r = client.post("/api/chat", json={"message": "hello"}, headers=h)
    assert r.status_code == 503
    assert r.get_json()["error"]["code"] == "ai_not_configured"


def test_unimplemented_endpoints_are_honest(client):
    # Google sign-in is real as of Phase 5: unconfigured servers say so instead of faking it
    r = client.post("/api/auth/google")
    assert r.status_code == 503 and r.get_json()["error"]["code"] == "google_not_configured"
    h = login(client)
    r = client.post("/api/research", json={"query": "climate trends"}, headers=h)
    assert r.status_code == 503
    assert r.get_json()["error"]["code"] == "ai_not_configured"
