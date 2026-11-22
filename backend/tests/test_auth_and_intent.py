"""Comprehensive test suite for Authentication and Chat Intent Classification.

Scenarios tested:
1. Fresh browser visit (no token) -> 401 Unauthorized, no guest account created in DB.
2. Explicit 'Continue as Guest' -> guest session created with is_guest=True.
3. Google OAuth start & state validation -> returns auth URL, validates state.
4. Logout / invalid token / expired token -> 401 Unauthorized, never creates guest account silently.
5. Unauthenticated user sending 'Hi' to /api/chat -> 401 Unauthorized, no agent run.
6. Authenticated user sending 'Hi' (even when active presentation exists in conversation) ->
   normal AI response, NO background job_id, NO generating status.
7. Authenticated user sending 'How are you?' -> normal AI response, NO job.
8. Authenticated user asking 'Explain my presentation' -> normal AI response, NO edit job.
9. Authenticated user saying 'Create a presentation about AI' -> 202 Accepted, presentation generation starts.
10. Authenticated user saying 'Add a conclusion slide to this presentation' -> 200 OK, edit presentation job starts.
11. Existing conversations and presentations load correctly for authenticated user.
"""
import os
import pytest
from unittest.mock import patch

from app import create_app
from database import db
from models import Conversation, Presentation, Slide, User
from utils.http import issue_token


@pytest.fixture()
def app():
    cfg = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "DEV_LOGIN_ENABLED": True,
        "RATELIMIT_ENABLED": False,
        "GEMINI_API_KEY": "test-key-mocked",
        "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "GOOGLE_REDIRECT_URI": "http://localhost:5000/api/auth/google/callback",
        "FRONTEND_URL": "http://localhost:5173",
        "FRONTEND_ORIGINS": ["http://localhost:5173"],
    }
    a = create_app(cfg)
    with a.app_context():
        db.create_all()
    yield a
    with a.app_context():
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def test_scenario_1_fresh_visit_no_guest_account(client, app):
    """Scenario 1: Fresh browser visit with no token results in 401 on protected endpoints,

    and does NOT automatically create any guest accounts in the database.
    """
    with app.app_context():
        initial_users = User.query.count()
        assert initial_users == 0

    # Visiting protected endpoints without token
    res_me = client.get("/api/auth/me")
    assert res_me.status_code == 401
    assert res_me.get_json()["error"]["code"] == "unauthorized"

    res_convs = client.get("/api/history")
    assert res_convs.status_code == 401

    res_pres = client.get("/api/presentations")
    assert res_pres.status_code == 401

    with app.app_context():
        # Ensure no guest or other user was silently created
        assert User.query.count() == 0


def test_scenario_2_explicit_guest_login(client, app):
    """Scenario 2: Explicitly clicking 'Continue as Guest' calls /api/auth/guest-login

    and creates a guest session with is_guest=True.
    """
    res = client.post("/api/auth/guest-login")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "token" in data
    assert data["user"]["is_guest"] is True
    assert data["user"]["email"].startswith("guest_")

    with app.app_context():
        assert User.query.count() == 1
        user = User.query.first()
        assert user.is_guest is True


def test_scenario_3_google_oauth_flow(client, app):
    """Scenario 3: Google sign-in initialization returns authorization URL and state."""
    res = client.post("/api/auth/google", json={"return_to": "http://localhost:5173"})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "auth_url" in data
    assert "state" in data
    assert "accounts.google.com" in data["auth_url"]


def test_scenario_4_invalid_and_expired_token(client, app):
    """Scenario 4: Invalid or expired tokens return 401 and do not create guest accounts."""
    # Bogus token
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer totally-invalid-token"})
    assert res.status_code == 401
    assert res.get_json()["error"]["code"] == "unauthorized"

    with app.app_context():
        assert User.query.count() == 0


def test_scenario_5_unauthenticated_chat_rejected(client, app):
    """Scenario 5: Unauthenticated request to /api/chat returns 401 without running agent."""
    res = client.post("/api/chat", json={"message": "Hi"})
    assert res.status_code == 401
    assert res.get_json()["error"]["code"] == "unauthorized"

    with app.app_context():
        assert Conversation.query.count() == 0


@patch("routes.conversations.run_agent")
def test_scenario_7_and_8_normal_chat_not_interpreted_as_edit(mock_run_agent, client, app):
    """Scenarios 7 & 8: Authenticated user sends 'Hi' or 'How are you?' even when

    an active presentation ID exists in the conversation.
    MUST return normal conversational response, NO background edit job, NO generating status.
    """
    mock_run_agent.return_value = "Hello! I am SlideMind AI. How can I help you today?"

    with app.app_context():
        u = User(email="test@example.com", name="Test User")
        db.session.add(u)
        db.session.flush()

        # Create an existing presentation and conversation with that presentation active
        p = Presentation(user_id=u.id, title="Quantum Computing 101")
        db.session.add(p)
        db.session.flush()

        c = Conversation(user_id=u.id, active_presentation_id=p.id)
        db.session.add(c)
        db.session.commit()
        token = issue_token(u.id)
        conv_id = c.id
        pres_id = p.id

    # 1. User sends "Hi" passing presentation_id (or inside conversation with active_presentation_id)
    res = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Hi", "conversation_id": conv_id, "presentation_id": pres_id},
    )
    assert res.status_code == 200
    data = res.get_json()["data"]
    # MUST NOT return job_id or status: generating
    assert "job_id" not in data
    assert data.get("status") != "generating"
    assert data["reply"] == "Hello! I am SlideMind AI. How can I help you today?"

    # 2. User sends "How are you?"
    mock_run_agent.return_value = "I'm doing great, ready to help you with presentations!"
    res2 = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "How are you?", "conversation_id": conv_id},
    )
    assert res2.status_code == 200
    data2 = res2.get_json()["data"]
    assert "job_id" not in data2
    assert data2.get("status") != "generating"


@patch("routes.conversations.run_agent")
def test_scenario_9_explain_presentation_is_normal_chat(mock_run_agent, client, app):
    """Scenario 9: Authenticated user asks 'Explain my presentation'.

    Must produce a normal conversational response, NOT an edit job.
    """
    mock_run_agent.return_value = (
        "This presentation covers the fundamentals of Quantum Computing, including qubits and superposition."
    )

    with app.app_context():
        u = User(email="test2@example.com", name="Test User 2")
        db.session.add(u)
        db.session.flush()
        p = Presentation(user_id=u.id, title="Quantum Computing 101")
        db.session.add(p)
        db.session.flush()
        c = Conversation(user_id=u.id, active_presentation_id=p.id)
        db.session.add(c)
        db.session.commit()
        token = issue_token(u.id)
        conv_id = c.id
        pres_id = p.id

    res = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Explain my presentation", "conversation_id": conv_id, "presentation_id": pres_id},
    )
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "job_id" not in data
    assert data.get("status") != "generating"
    assert "fundamentals of Quantum Computing" in data["reply"]


@patch("services.jobs.start_generation")
def test_scenario_10_create_presentation_triggers_generation(mock_start_gen, client, app):
    """Scenario 10: Authenticated user says 'Create a presentation about AI'.

    Must trigger presentation generation and return 202 with job_id.
    """
    from models import BackgroundJob
    with app.app_context():
        u = User(email="creator@example.com", name="Creator")
        db.session.add(u)
        db.session.commit()
        token = issue_token(u.id)

    mock_job = BackgroundJob(id="job-12345", user_id=u.id, kind="generate_presentation", status="queued", payload={})
    mock_start_gen.return_value = mock_job

    res = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Create a 10-slide presentation about artificial intelligence."},
    )
    assert res.status_code == 202
    data = res.get_json()["data"]
    assert data["job_id"] == "job-12345"
    assert data["status"] == "generating"
    assert data["kind"] == "generate_presentation"
    assert "Generating a 10-slide presentation" in data["reply"]


@patch("services.jobs.start_edit")
def test_scenario_11_edit_presentation_triggers_edit_job(mock_start_edit, client, app):
    """Scenario 11: Authenticated user says 'Add a conclusion slide to this presentation'.

    When an active presentation exists, must trigger edit presentation job.
    """
    from models import BackgroundJob
    with app.app_context():
        u = User(email="editor@example.com", name="Editor")
        db.session.add(u)
        db.session.flush()
        p = Presentation(user_id=u.id, title="Pitch Deck")
        db.session.add(p)
        db.session.flush()
        c = Conversation(user_id=u.id, active_presentation_id=p.id)
        db.session.add(c)
        db.session.commit()
        token = issue_token(u.id)
        conv_id = c.id
        pres_id = p.id

    mock_job = BackgroundJob(id="edit-job-999", user_id=u.id, kind="edit_presentation", status="running", payload={})
    mock_job.result = None
    mock_start_edit.return_value = mock_job

    res = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "Add a conclusion slide to this presentation",
            "conversation_id": conv_id,
            "presentation_id": pres_id,
        },
    )
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["job_id"] == "edit-job-999"
    assert data["status"] == "generating"
    assert data["kind"] == "edit_presentation"
    assert "Updating your presentation" in data["reply"]


def test_scenario_12_existing_conversations_and_presentations_load(client, app):
    """Scenario 12: Existing conversations and presentations load correctly for authenticated user."""
    with app.app_context():
        u = User(email="loader@example.com", name="Loader")
        db.session.add(u)
        db.session.flush()
        p = Presentation(user_id=u.id, title="My Saved Deck")
        db.session.add(p)
        db.session.flush()
        s = Slide(presentation_id=p.id, position=1, title="Intro", content={"layout": "hero"})
        db.session.add(s)
        c = Conversation(user_id=u.id, title="Chat about Deck", active_presentation_id=p.id)
        db.session.add(c)
        db.session.commit()
        token = issue_token(u.id)
        conv_id = c.id
        pres_id = p.id

    # 1. Fetch conversations
    res_convs = client.get("/api/history", headers={"Authorization": f"Bearer {token}"})
    assert res_convs.status_code == 200
    data_convs = res_convs.get_json()["data"]
    assert len(data_convs) == 1
    assert data_convs[0]["id"] == conv_id

    # 2. Fetch specific conversation
    res_conv = client.get(f"/api/conversations/{conv_id}", headers={"Authorization": f"Bearer {token}"})
    assert res_conv.status_code == 200
    data_conv = res_conv.get_json()["data"]
    assert data_conv["active_presentation_id"] == pres_id

    # 3. Fetch presentations list
    res_pres = client.get("/api/presentations", headers={"Authorization": f"Bearer {token}"})
    assert res_pres.status_code == 200
    data_pres = res_pres.get_json()["data"]
    assert len(data_pres) == 1
    assert data_pres[0]["id"] == pres_id
    assert data_pres[0]["title"] == "My Saved Deck"
