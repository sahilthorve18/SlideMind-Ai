from flask import Blueprint, current_app, g, redirect, request
from sqlalchemy.exc import IntegrityError

from database import db
from models import User
from services import google_auth
from services.google_auth import GoogleAuthError, GoogleNotConfigured
from utils.http import fail, issue_token, json_body, ok, require_auth

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _user_dict(u: User):
    return {"id": u.id, "email": u.email, "name": u.name, "avatar_url": u.avatar_url,
            "google_connected": google_auth.is_connected(u)}


@bp.post("/google")
def google_start():
    """Returns the Google consent URL. The browser stores `state` and compares it when it comes back."""
    try:
        url, state = google_auth.authorization_url()
    except GoogleNotConfigured:
        return fail("google_not_configured", "Google sign-in is not configured on this server.", 503)
    return ok({"auth_url": url, "state": state})


@bp.get("/google/callback")
def google_callback():
    """Google redirects the browser here. We exchange the code server-side, keep Google's tokens
    (encrypted), and send the browser back with our session token in the URL fragment and secure cookie."""
    if request.args.get("error"):
        error_type = request.args.get("error")
        current_app.logger.warning("Google OAuth error from provider: %s", error_type)
        return redirect(google_auth.frontend_redirect(error="google_denied"))
    state, code = request.args.get("state", ""), request.args.get("code", "")
    if not code or not google_auth.verify_state(state):
        current_app.logger.warning("Google OAuth callback rejected: missing code or invalid state")
        return redirect(google_auth.frontend_redirect(error="invalid_state"))
    try:
        info = google_auth.exchange_code(code)
    except GoogleNotConfigured:
        current_app.logger.warning("Google OAuth code exchange attempted while unconfigured")
        return redirect(google_auth.frontend_redirect(error="google_not_configured"))
    except GoogleAuthError:
        current_app.logger.warning("Google OAuth exchange failed")
        return redirect(google_auth.frontend_redirect(error="google_failed"))
    except Exception as e:
        current_app.logger.exception("Unexpected error exchanging Google OAuth code: %s", e)
        return redirect(google_auth.frontend_redirect(error="google_failed"))

    if not info.get("email") or not info.get("email_verified"):
        return redirect(google_auth.frontend_redirect(error="email_unverified"))

    try:
        user = User.query.filter_by(google_sub=info["sub"]).first() or User.query.filter_by(email=info["email"]).first()
        if not user:
            user = User(email=info["email"])
            db.session.add(user)
        user.google_sub = info["sub"]
        user.name = user.name or info["name"]
        user.avatar_url = user.avatar_url or info["picture"]
        google_auth.store_grant(user, info["refresh_token"], info["scopes"])
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Database error persisting Google OAuth user: %s", e)
        return redirect(google_auth.frontend_redirect(error="google_failed"))

    token = issue_token(user.id)
    resp = redirect(google_auth.frontend_redirect(token=token, state=state))
    is_prod = current_app.config.get("ENV_IS_PRODUCTION", False)
    resp.set_cookie(
        "sm_token",
        token,
        max_age=60 * 60 * 24 * 7,
        secure=is_prod,
        httponly=False,
        samesite="None" if is_prod else "Lax",
    )
    return resp


@bp.post("/google/disconnect")
@require_auth
def google_disconnect():
    google_auth.disconnect(g.user)
    resp, status = ok(_user_dict(g.user))
    resp.delete_cookie("sm_token")
    return resp, status


@bp.post("/dev-login")
def dev_login():
    """Development-only login. Disabled outside FLASK_ENV=development."""
    if not current_app.config.get("DEV_LOGIN_ENABLED"):
        return fail("not_found", "Not found.", 404)
    data, err = json_body({"email": str})
    if err:
        return err
    email = data["email"].strip().lower()[:255]
    if "@" not in email:
        return fail("invalid_request", "A valid email is required.")
    user = User.query.filter_by(email=email).first()
    if not user:
        name_part = email.split("@")[0].replace(".", " ").replace("_", " ").title()
        user = User(email=email, name=name_part)
        db.session.add(user)
        db.session.commit()
    return ok({"token": issue_token(user.id), "user": _user_dict(user)})


@bp.post("/email-login")
def email_login():
    """Create an account for an email that has never been used.

    Knowing an email is not enough to enter an existing account. Returning
    visitors keep the session already stored in their browser, or use Google.
    """
    data, err = json_body({"email": str})
    if err:
        return err
    email = data["email"].strip().lower()[:255]
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        return fail("invalid_request", "A valid email address is required.")
    if User.query.filter_by(email=email).first():
        return fail(
            "account_exists",
            "This email already has an account. Open SlideMind in the browser where you signed in, or continue with Google.",
            403,
        )
    name_part = email.split("@")[0].replace(".", " ").title()
    user = User(email=email, name=name_part)
    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail(
            "account_exists",
            "This email already has an account. Open SlideMind in the browser where you signed in, or continue with Google.",
            403,
        )
    return ok({"token": issue_token(user.id), "user": _user_dict(user)})


@bp.post("/guest-login")
def guest_login():
    """1-Click instant guest pass so anyone can try SlideMind AI immediately."""
    import uuid

    guest_id = uuid.uuid4().hex[:6]
    email = f"guest_{guest_id}@slidemind.ai"
    user = User(email=email, name=f"Guest Explorer #{guest_id}")
    db.session.add(user)
    db.session.commit()
    return ok({"token": issue_token(user.id), "user": _user_dict(user)})


@bp.get("/me")
@require_auth
def me():
    return ok(_user_dict(g.user))


@bp.get("/export-data")
@require_auth
def export_user_data():
    """GDPR Article 20: Right to data portability. Exports all user data as JSON."""
    from datetime import datetime, timezone
    from models import Conversation, Document, Presentation

    presentations = [
        {
            "id": p.id,
            "title": p.title,
            "settings": p.settings,
            "slides": [
                {
                    "position": s.position,
                    "title": s.title,
                    "content": s.content,
                    "speaker_notes": s.speaker_notes,
                }
                for s in p.slides
            ],
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in Presentation.query.filter_by(user_id=g.user.id).all()
    ]
    conversations = [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "messages": [
                {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat() if m.created_at else None}
                for m in c.messages
            ]
        }
        for c in Conversation.query.filter_by(user_id=g.user.id).all()
    ]
    docs = [
        {"id": d.id, "filename": d.filename, "file_type": d.file_type, "page_count": d.page_count}
        for d in Document.query.filter_by(user_id=g.user.id).all()
    ]
    return ok({
        "user": _user_dict(g.user),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "presentations": presentations,
        "conversations": conversations,
        "documents": docs,
    })


@bp.post("/delete-account")
@require_auth
def delete_user_account():
    """GDPR Article 17: Right to erasure. Permanently deletes account and cascades all associated data."""
    from models import BackgroundJob, Conversation, Document, Presentation, VisualAsset
    uid = g.user.id

    for p in Presentation.query.filter_by(user_id=uid).all():
        db.session.delete(p)

    for c in Conversation.query.filter_by(user_id=uid).all():
        db.session.delete(c)

    for d in Document.query.filter_by(user_id=uid).all():
        db.session.delete(d)

    for j in BackgroundJob.query.filter_by(user_id=uid).all():
        db.session.delete(j)

    for v in VisualAsset.query.filter_by(user_id=uid).all():
        db.session.delete(v)

    db.session.delete(g.user)
    db.session.commit()
    return ok({"deleted": True, "message": "Account and all associated data have been permanently deleted."})
