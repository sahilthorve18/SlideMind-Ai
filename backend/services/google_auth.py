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
if os.getenv("FLASK_ENV") == "development" or os.getenv("DEV_LOGIN_ENABLED", "").lower() in ("true", "1"):
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

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


def _clean_str(val: str | None) -> str:
    """Strips all leading/trailing whitespace, internal newlines/carriage returns, and quotes."""
    if not val:
        return ""
    return "".join(str(val).split()).strip("\"'")


def get_redirect_uri() -> str:
    """Returns the effective Google OAuth redirect URI.
    Uses explicit GOOGLE_REDIRECT_URI if set, otherwise derives from BACKEND_URL or RENDER_EXTERNAL_URL,
    falling back to localhost in development.
    """
    c = current_app.config
    explicit = _clean_str(c.get("GOOGLE_REDIRECT_URI"))
    if explicit:
        return explicit
    backend_url = _clean_str(os.getenv("BACKEND_URL") or os.getenv("RENDER_EXTERNAL_URL") or c.get("BACKEND_URL"))
    if backend_url:
        return f"{backend_url.rstrip('/')}/api/auth/google/callback"
    if c.get("ENV", "development") == "development" or c.get("DEV_LOGIN_ENABLED"):
        return "http://localhost:5000/api/auth/google/callback"
    return ""


def is_configured() -> bool:
    c = current_app.config
    redirect_uri = get_redirect_uri()
    client_id = _clean_str(c.get("GOOGLE_CLIENT_ID"))
    client_secret = _clean_str(c.get("GOOGLE_CLIENT_SECRET"))
    return bool(client_id and client_secret and redirect_uri)


def _flow(state=None):
    from google_auth_oauthlib.flow import Flow

    if not is_configured():
        raise GoogleNotConfigured("Google sign-in is not configured on this server.")
    c = current_app.config
    redirect_uri = get_redirect_uri()
    client_id = _clean_str(c.get("GOOGLE_CLIENT_ID"))
    client_secret = _clean_str(c.get("GOOGLE_CLIENT_SECRET"))
    cfg = {"web": {"client_id": client_id, "client_secret": client_secret,
                   "auth_uri": AUTH_URI, "token_uri": TOKEN_URI, "redirect_uris": [redirect_uri]}}
    # Confidential server-side client: the client secret authenticates the exchange, so PKCE is not used.
    return Flow.from_client_config(cfg, scopes=SCOPES, state=state, redirect_uri=redirect_uri,
                                   autogenerate_code_verifier=False)


# ---- CSRF state: signed, short-lived; the browser also keeps a copy and checks it on return ----

def is_safe_return_url(url: str | None) -> bool:
    """Validates if return_to belongs to known dev origins, Vercel preview/production, or configured FRONTEND_URL."""
    if not url:
        return False
    import re
    clean = _clean_str(url).rstrip("/")
    if clean in ("http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"):
        return True
    cfg_frontend = _clean_str(current_app.config.get("FRONTEND_URL")).rstrip("/")
    if cfg_frontend and clean == cfg_frontend:
        return True
    for origin in current_app.config.get("FRONTEND_ORIGINS", []):
        if clean == _clean_str(origin).rstrip("/"):
            return True
    if re.match(r"^https:\/\/[\w\-]+(\.vercel\.app|\.onrender\.com)$", clean):
        return True
    return False


def _state_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="slidemind-oauth-state")


def new_state(return_to: str | None = None) -> str:
    payload = {"n": secrets.token_urlsafe(16)}
    if return_to and is_safe_return_url(return_to):
        payload["r"] = _clean_str(return_to).rstrip("/")
    return _state_serializer().dumps(payload)


def verify_state(state: str) -> bool:
    try:
        _state_serializer().loads(state or "", max_age=STATE_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def get_state_return_to(state: str) -> str | None:
    try:
        data = _state_serializer().loads(state or "", max_age=STATE_MAX_AGE)
        if isinstance(data, dict):
            r = data.get("r")
            if is_safe_return_url(r):
                return r
    except Exception:
        pass
    return None


def authorization_url(return_to: str | None = None) -> tuple[str, str]:
    state = new_state(return_to=return_to)
    url, _ = _flow().authorization_url(access_type="offline", prompt="consent", include_granted_scopes="true", state=state)
    return url, state


def _mask_secret(val: str) -> str:
    if not val:
        return "<EMPTY>"
    val = _clean_str(val)
    if len(val) <= 8:
        return f"{val[:2]}*** (len {len(val)})"
    return f"{val[:4]}...{val[-4:]} (len {len(val)})"


def exchange_code(code: str) -> dict:
    """Server-side code exchange with dual verification: ID token verification with graceful
    fallback to the authoritative Google UserInfo API. Returns profile + refresh token + granted scopes."""
    from google.auth.transport import requests as g_requests
    from google.oauth2 import id_token

    flow = _flow()
    c = current_app.config
    client_id = _clean_str(c.get("GOOGLE_CLIENT_ID"))
    client_secret = _clean_str(c.get("GOOGLE_CLIENT_SECRET"))
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        err_str = str(e)
        if "invalid_client" in err_str or "client secret" in err_str.lower():
            hint = f"GOOGLE_CLIENT_SECRET in Render ({_mask_secret(client_secret)}) is invalid for Client ID {_mask_secret(client_id)}. Update GOOGLE_CLIENT_SECRET in Render Environment with the secret from Google Cloud Console."
            current_app.logger.error("OAuth client secret mismatch: %s. %s", e, hint)
            raise GoogleAuthError(hint) from e
        current_app.logger.warning("Google flow.fetch_token failed: %s: %s", type(e).__name__, e)
        raise GoogleAuthError(f"Token exchange failed ({type(e).__name__}): {e}") from e

    creds = flow.credentials
    info = None

    # Step 1: Attempt ID token verification if id_token is provided
    id_tok = getattr(creds, "id_token", None)
    if not id_tok and hasattr(flow, "oauth2session") and flow.oauth2session.token:
        id_tok = flow.oauth2session.token.get("id_token")

    if id_tok:
        try:
            info = id_token.verify_oauth2_token(
                id_tok,
                g_requests.Request(),
                audience=client_id or None,
                clock_skew_in_seconds=60,
            )
        except Exception as e:
            current_app.logger.warning("ID token verification failed (%s: %s), falling back to Google UserInfo endpoint.", type(e).__name__, e)

    # Step 2: Resilient fallback — fetch profile directly from Google's UserInfo API using the bearer access token
    if not info or not info.get("email"):
        try:
            userinfo_res = flow.oauth2session.get("https://www.googleapis.com/oauth2/v3/userinfo", timeout=10)
            if userinfo_res.ok:
                info = userinfo_res.json()
            else:
                current_app.logger.warning("Google userinfo endpoint responded with status %s: %s", userinfo_res.status_code, userinfo_res.text)
        except Exception as e:
            current_app.logger.warning("Google userinfo request failed: %s", e)

    if not info or not info.get("sub"):
        raise GoogleAuthError("Could not retrieve verified profile from Google.")

    granted = flow.oauth2session.token.get("scope") or creds.scopes or []
    if isinstance(granted, str):
        granted = granted.split()

    email = (info.get("email") or "").strip().lower()
    email_verified = info.get("email_verified")
    if email_verified is None:
        email_verified = True

    return {
        "sub": str(info["sub"]),
        "email": email,
        "email_verified": bool(email_verified),
        "name": info.get("name") or (email.split("@")[0].title() if email else "User"),
        "picture": info.get("picture"),
        "refresh_token": creds.refresh_token,
        "scopes": sorted(set(granted)),
    }


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
    client_id = _clean_str(c.get("GOOGLE_CLIENT_ID"))
    client_secret = _clean_str(c.get("GOOGLE_CLIENT_SECRET"))
    return Credentials(token=None, refresh_token=refresh, token_uri=TOKEN_URI, client_id=client_id,
                       client_secret=client_secret, scopes=(user.google_scopes or "").split())


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


def frontend_redirect(return_to: str | None = None, **fragment) -> str:
    """Tokens travel in the URL *fragment*: never sent to servers or written to access logs."""
    frag = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in fragment.items())
    base_url = None
    if return_to and is_safe_return_url(return_to):
        base_url = _clean_str(return_to).rstrip("/")
    if not base_url:
        base_url = _clean_str(current_app.config.get("FRONTEND_URL") or "http://localhost:5173").rstrip("/")
    return f"{base_url}/#{frag}"
