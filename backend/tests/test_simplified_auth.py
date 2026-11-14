import os

os.environ["SLIDEMIND_SKIP_AUTOAPP"] = "1"

import pytest
from app import create_app
from database import db


@pytest.fixture
def client():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "RATELIMIT_ENABLED": False,
        "DEV_LOGIN_ENABLED": True,
        "GEMINI_API_KEY": "",
    })
    with app.test_client() as cl:
        yield cl
    with app.app_context():
        db.drop_all()


def test_guest_login_flow(client):
    res = client.post("/api/auth/guest-login")
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert "token" in data["data"]
    user = data["data"]["user"]
    assert "guest_" in user["email"]
    assert "Guest Explorer" in user["name"]


def test_email_login_flow(client):
    res = client.post("/api/auth/email-login", json={"email": "friend.alex@example.com"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert "token" in data["data"]
    user = data["data"]["user"]
    assert user["email"] == "friend.alex@example.com"
    assert user["name"] == "Friend Alex"


def test_email_login_does_not_take_over_existing_account(client):
    first = client.post("/api/auth/email-login", json={"email": "friend.alex@example.com"})
    assert first.status_code == 200
    again = client.post("/api/auth/email-login", json={"email": "friend.alex@example.com"})
    assert again.status_code == 403
    assert again.get_json()["error"]["code"] == "account_exists"
    assert "token" not in again.get_json().get("data", {})
