"""Structured responses, validation helpers and auth."""
from functools import wraps

from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from database import db
from models import User

TOKEN_MAX_AGE = 60 * 60 * 24 * 7


def ok(data=None, status=200):
    return jsonify({"ok": True, "data": data}), status


def fail(code: str, message: str, status=400, details=None):
    body = {"ok": False, "error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


def not_implemented(feature: str, phase: int):
    return fail("not_implemented", f"{feature} is not available yet (planned for Phase {phase}).", 501)


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="slidemind-auth")


def issue_token(user_id: str) -> str:
    return _serializer().dumps({"uid": user_id})


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        token = None
        if header.startswith("Bearer "):
            token = header[7:].strip()
        elif "sm_token" in request.cookies:
            token = request.cookies.get("sm_token")

        if not token:
            return fail("unauthorized", "Missing credentials.", 401)
        try:
            payload = _serializer().loads(token, max_age=TOKEN_MAX_AGE)
        except (BadSignature, SignatureExpired):
            return fail("unauthorized", "Invalid or expired session.", 401)
        db.session.expire_all()
        user = db.session.get(User, payload.get("uid"))
        if not user:
            return fail("unauthorized", "Unknown user.", 401)
        g.user = user
        return fn(*args, **kwargs)

    return wrapper


def json_body(required: dict):
    """Validate a JSON body. `required` maps field -> expected type (or tuple of types).
    Returns (data, error_response)."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, fail("invalid_request", "Expected a JSON object body.")
    for field, typ in required.items():
        if field not in data or not isinstance(data[field], typ):
            return None, fail("invalid_request", f"Field '{field}' is missing or invalid.")
    return data, None


def clean_text(value: str, max_len: int = 8000) -> str:
    """Strip control characters and cap length. Rendering escapes happen on the client."""
    value = "".join(ch for ch in value if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    return value.strip()[:max_len]
