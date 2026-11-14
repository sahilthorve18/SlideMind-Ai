"""Google OAuth 2.0 (authorization-code flow, server side) and credential handling.

Tokens never reach the browser: the callback exchanges the code on the server, stores the
refresh token encrypted, and gives the browser only SlideMind's own session token.
"""
import os
import secrets
from urllib.parse import quote

import requests
from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from database import db
from services import crypto

# Google may return a subset of scopes if the user unticks one; we check grants ourselves.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

SCOPES_IDENTITY = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]
SCOPE_SLIDES = "https://www.googleapis.com/auth/presentations"
SCOPE_DRIVE = "https://www.googleapis.com/auth/drive.file"  # only files this app creates
SCOPES = SCOPES_IDENTITY + [SCOPE_SLIDES, SCOPE_DRIVE]
REQUIRED_FOR_SLIDES = {SCOPE_SLIDES, SCOPE_DRIVE}
STATE_MAX_AGE = 600
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"


class GoogleNotConfigured(Exception):
    pass


class GoogleAuthError(Exception):
    """OAuth failed (bad state, unverified email, token exchange error...)."""


class GoogleAuthExpired(Exception):
    """Stored grant was revoked/expired; the user must reconnect."""


def get_redirect_uri() -> str:
    """Returns the effective Google OAuth redirect URI.
    Uses explicit GOOGLE_REDIRECT_URI if set, otherwise derives from BACKEND_URL or RENDER_EXTERNAL_URL,
    falling back to localhost in development.
    """
    c = current_app.config
    explicit = (c.get("GOOGLE_REDIRECT_URI") or "").strip()
    if explicit:
        return explicit
    backend_url = (os.getenv("BACKEND_URL") or os.getenv("RENDER_EXTERNAL_URL") or c.get("BACKEND_URL") or "").strip()
    if backend_url:
        return f"{backend_url.rstrip('/')}/api/auth/google/callback"
    if c.get("ENV", "development") == "development" or c.get("DEV_LOGIN_ENABLED"):
        return "http://localhost:5000/api/auth/google/callback"
    return ""


def is_configured() -> bool:
    c = current_app.config
    redirect_uri = get_redirect_uri()
    return bool(c.get("GOOGLE_CLIENT_ID") and c.get("GOOGLE_CLIENT_SECRET") and redirect_uri)


def _flow(state=None):
    from google_auth_oauthlib.flow import Flow

    if not is_configured():
        raise GoogleNotConfigured("Google sign-in is not configured on this server.")
    c = current_app.config
    redirect_uri = get_redirect_uri()
    cfg = {"web": {"client_id": c["GOOGLE_CLIENT_ID"], "client_secret": c["GOOGLE_CLIENT_SECRET"],
                   "auth_uri": AUTH_URI, "token_uri": TOKEN_URI, "redirect_uris": [redirect_uri]}}
    # Confidential server-side client: the client secret authenticates the exchange, so PKCE is not used.
    return Flow.from_client_config(cfg, scopes=SCOPES, state=state, redirect_uri=redirect_uri,
                                   autogenerate_code_verifier=False)


# ---- CSRF state: signed, short-lived; the browser also keeps a copy and checks it on return ----

def _state_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="slidemind-oauth-state")


def new_state() -> str:
    return _state_serializer().dumps({"n": secrets.token_urlsafe(16)})


def verify_state(state: str) -> bool:
    try:
        _state_serializer().loads(state or "", max_age=STATE_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def authorization_url() -> tuple[str, str]:
    state = new_state()
    url, _ = _flow().authorization_url(access_type="offline", prompt="consent", include_granted_scopes="true", state=state)
    return url, state


def exchange_code(code: str) -> dict:
    """Server-side code exchange + ID token verification. Returns profile + refresh token + granted scopes."""
    from google.auth.transport import requests as g_requests
    from google.oauth2 import id_token

    flow = _flow()
    client_id = (current_app.config.get("GOOGLE_CLIENT_ID") or "").strip()
    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
        info = id_token.verify_oauth2_token(creds.id_token, g_requests.Request(), client_id)
    except Exception as e:
        current_app.logger.warning("Google code exchange failed: %s: %s", type(e).__name__, e)
        raise GoogleAuthError(f"Google sign-in failed: {e}") from e
    granted = flow.oauth2session.token.get("scope") or creds.scopes or []
    if isinstance(granted, str):
        granted = granted.split()
    return {"sub": info["sub"], "email": (info.get("email") or "").lower(), "email_verified": bool(info.get("email_verified")),
            "name": info.get("name"), "picture": info.get("picture"), "refresh_token": creds.refresh_token,
            "scopes": sorted(set(granted))}


def store_grant(user, refresh_token: str | None, scopes: list[str]):
    if refresh_token:
        user.google_refresh_token_enc = crypto.encrypt(refresh_token)
    user.google_scopes = " ".join(scopes)


def is_connected(user) -> bool:
    """True only if we hold a usable refresh token AND the user granted the Slides + Drive scopes."""
    if not user or not user.google_refresh_token_enc:
        return False
    return REQUIRED_FOR_SLIDES <= set((user.google_scopes or "").split())


def credentials_for(user):
    from google.oauth2.credentials import Credentials

    if not is_connected(user):
        return None
    refresh = crypto.decrypt(user.google_refresh_token_enc)
    if not refresh:
        return None
    c = current_app.config
    return Credentials(token=None, refresh_token=refresh, token_uri=TOKEN_URI, client_id=c["GOOGLE_CLIENT_ID"],
                       client_secret=c["GOOGLE_CLIENT_SECRET"], scopes=(user.google_scopes or "").split())


def disconnect(user, revoke: bool = True):
    """Forget the grant locally and (best effort) revoke it at Google."""
    if revoke and user.google_refresh_token_enc:
        token = crypto.decrypt(user.google_refresh_token_enc)
        if token:
            try:
                requests.post("https://oauth2.googleapis.com/revoke", params={"token": token}, timeout=5)
            except requests.RequestException:
                current_app.logger.warning("Google token revoke request failed")
    user.google_refresh_token_enc = None
    user.google_scopes = None
    db.session.commit()


def frontend_redirect(**fragment) -> str:
    """Tokens travel in the URL *fragment*: never sent to servers or written to access logs."""
    frag = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in fragment.items())
    base_url = (current_app.config.get("FRONTEND_URL") or "http://localhost:5173").rstrip("/")
    return f"{base_url}/#{frag}"
