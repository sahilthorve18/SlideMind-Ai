"""Verification suite for Render Keep-Alive, Health Endpoints, and Production Google OAuth."""
import os
import pytest
from cryptography.fernet import Fernet
from urllib.parse import parse_qs, urlparse

from app import create_app
from database import db
from models import User
from services import google_auth
from services.google_auth import SCOPES
from utils.http import issue_token

KEY = Fernet.generate_key().decode()


@pytest.fixture()
def app():
    cfg = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "DEV_LOGIN_ENABLED": True,
        "RATELIMIT_ENABLED": False,
        "GEMINI_API_KEY": "dummy",
        "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "GOOGLE_REDIRECT_URI": "https://slidemind-ai-backend.onrender.com/api/auth/google/callback",
        "FRONTEND_URL": "https://slidemind-ai.vercel.app",
        "FRONTEND_ORIGINS": ["https://slidemind-ai.vercel.app", "http://localhost:5173"],
        "TOKEN_ENCRYPTION_KEY": KEY,
    }
    a = create_app(cfg)
    yield a
    with a.app_context():
        db.drop_all()


def test_health_endpoints_return_200_without_auth(app):
    """Both /api/health and /healthz must return 200 OK with no auth or exposed secrets."""
    with app.test_client() as c:
        for path in ("/api/health", "/healthz"):
            res = c.get(path)
            assert res.status_code == 200
            data = res.get_json()
            assert data["ok"] is True
            assert data["data"]["status"] == "healthy"
            # Ensure no credentials/secrets leaked
            assert "secret" not in str(data).lower()
            assert "database" not in str(data).lower()


def test_cors_allows_vercel_and_dev_origins_without_wildcard_credentials(app):
    """Exact Vercel origins and dev origins must receive specific Access-Control-Allow-Origin, not '*'."""
    with app.test_client() as c:
        # Vercel production origin
        res = c.get("/api/health", headers={"Origin": "https://slidemind-ai.vercel.app"})
        assert res.headers.get("Access-Control-Allow-Origin") == "https://slidemind-ai.vercel.app"
        assert res.headers.get("Access-Control-Allow-Credentials") == "true"

        # Local development origin
        res_dev = c.get("/api/health", headers={"Origin": "http://localhost:5173"})
        assert res_dev.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
        assert res_dev.headers.get("Access-Control-Allow-Credentials") == "true"

        # Vercel preview branch deployment
        res_preview = c.get("/api/health", headers={"Origin": "https://slidemind-git-feature.vercel.app"})
        assert res_preview.headers.get("Access-Control-Allow-Origin") == "https://slidemind-git-feature.vercel.app"


def test_redirect_uri_derivation_logic(app):
    """Verifies that redirect URI derivation works via explicit URI, BACKEND_URL, or localhost."""
    with app.app_context():
        # 1. Explicit
        assert google_auth.get_redirect_uri() == "https://slidemind-ai-backend.onrender.com/api/auth/google/callback"

        # 2. Derived from BACKEND_URL when explicit is blank
        old = app.config["GOOGLE_REDIRECT_URI"]
        app.config["GOOGLE_REDIRECT_URI"] = ""
        app.config["BACKEND_URL"] = "https://custom-backend.onrender.com"
        assert google_auth.get_redirect_uri() == "https://custom-backend.onrender.com/api/auth/google/callback"

        # 3. Development fallback
        app.config["BACKEND_URL"] = ""
        app.config["DEV_LOGIN_ENABLED"] = True
        assert google_auth.get_redirect_uri() == "http://localhost:5000/api/auth/google/callback"
        app.config["GOOGLE_REDIRECT_URI"] = old


def test_google_callback_success_sets_cookie_and_redirects(app, monkeypatch):
    """Successful callback redirects to Vercel FRONTEND_URL fragment and sets secure sm_token cookie."""
    mock_info = {
        "sub": "google-user-123",
        "email": "user@example.com",
        "email_verified": True,
        "name": "Test User",
        "picture": "https://lh3.googleusercontent.com/photo.jpg",
        "refresh_token": "mock-refresh-token",
        "scopes": sorted(SCOPES),
    }
    monkeypatch.setattr(google_auth, "exchange_code", lambda code: mock_info)

    with app.test_client() as c:
        start_res = c.post("/api/auth/google").get_json()["data"]
        state = start_res["state"]

        res = c.get(f"/api/auth/google/callback?code=mock_code&state={state}")
        assert res.status_code == 302
        location = res.headers["Location"]
        assert location.startswith("https://slidemind-ai.vercel.app/#")

        # Verify fragment contents
        parsed = urlparse(location)
        fragment = {k: v[0] for k, v in parse_qs(parsed.fragment).items()}
        assert "token" in fragment
        assert fragment["state"] == state

        # Verify cookie is set
        set_cookie = res.headers.get("Set-Cookie", "")
        assert "sm_token=" in set_cookie


def test_google_callback_gracefully_handles_errors(app):
    """Failed, cancelled, or expired OAuth attempts must redirect gracefully without crashing."""
    with app.test_client() as c:
        # 1. User denied consent
        res_denied = c.get("/api/auth/google/callback?error=access_denied")
        assert res_denied.status_code == 302
        assert "error=google_denied" in res_denied.headers["Location"]

        # 2. Invalid or expired state
        res_bad_state = c.get("/api/auth/google/callback?code=abc&state=badstate")
        assert res_bad_state.status_code == 302
        assert "error=invalid_state" in res_bad_state.headers["Location"]

        # 3. Missing code
        res_missing_code = c.get("/api/auth/google/callback?state=xyz")
        assert res_missing_code.status_code == 302
        assert "error=invalid_state" in res_missing_code.headers["Location"]


def test_auth_via_cookie_when_bearer_header_absent(app):
    """require_auth must authenticate users via sm_token cookie when Authorization header is absent."""
    with app.app_context():
        user = User(email="cookie_user@example.com", name="Cookie Tester")
        db.session.add(user)
        db.session.commit()
        token = issue_token(user.id)

    with app.test_client() as c:
        # Without cookie or header -> 401
        res_no_auth = c.get("/api/auth/me")
        assert res_no_auth.status_code == 401

        # With sm_token cookie
        c.set_cookie("sm_token", token)
        res_with_cookie = c.get("/api/auth/me")
        assert res_with_cookie.status_code == 200
        data = res_with_cookie.get_json()["data"]
        assert data["email"] == "cookie_user@example.com"
