"""SlideMind AI Flask application factory."""
import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException

from config import Config
from database import db

limiter = Limiter(key_func=get_remote_address)


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["DEV_LOGIN_ENABLED"] = os.getenv("FLASK_ENV") == "development"
    app.config["ENV_IS_PRODUCTION"] = os.getenv("FLASK_ENV") == "production"
    app.config["RATELIMIT_STORAGE_URI"] = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    if overrides:
        app.config.update(overrides)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if app.config.get("ENV_IS_PRODUCTION"):
        secret = app.config.get("SECRET_KEY") or ""
        if secret in ("", "dev-only-change-me"):
            raise RuntimeError("SECRET_KEY must be set to a unique value in production.")
        rate_store = app.config.get("RATELIMIT_STORAGE_URI") or ""
        if rate_store.startswith("memory"):
            logging.warning("RATELIMIT_STORAGE_URI using in-memory store. For multi-worker clusters, configure Redis.")

    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    import re

    # Allowed CORS origins: Local dev + exact Vercel frontend URL + configured origins + regex for Vercel preview deploys
    dev_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
    ]
    cors_origins = list(dev_origins)
    frontend_url = (app.config.get("FRONTEND_URL") or "").rstrip("/")
    if frontend_url and frontend_url not in cors_origins:
        cors_origins.append(frontend_url)
    for origin in app.config.get("FRONTEND_ORIGINS", []):
        o_clean = origin.rstrip("/")
        if o_clean and o_clean not in cors_origins:
            cors_origins.append(o_clean)

    # Dynamically match preview deployments on Vercel and Render for SlideMind
    cors_origins.append(re.compile(r"^https:\/\/(slide-mind-ai|slidemind)[\w\-]*(\.vercel\.app|\.onrender\.com)$"))

    CORS(
        app,
        resources={
            r"/api/*": {"origins": cors_origins},
            r"/healthz": {"origins": "*"},
        },
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        supports_credentials=True,
    )
    db.init_app(app)
    limiter.init_app(app)
    limiter.default_limits = [app.config["RATELIMIT_DEFAULT"]]

    from routes import ALL_BLUEPRINTS
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)

    from routes.auth import export_user_data, delete_user_account
    app.add_url_rule("/api/user/export-data", view_func=export_user_data, methods=["GET"])
    app.add_url_rule("/api/user/delete-account", view_func=delete_user_account, methods=["POST"])

    # Chat triggers paid/limited Gemini calls (and multi-step tool loops): throttle harder than the default.
    limiter.limit(app.config.get("CHAT_RATE_LIMIT", "15 per minute"))(app.view_functions["conversations.chat"])
    limiter.limit(app.config.get("GUEST_RATE_LIMIT", "5 per hour"))(app.view_functions["auth.guest_login"])

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    @app.get("/healthz")
    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "data": {"status": "healthy"}})

    @app.errorhandler(HTTPException)
    def http_error(e):
        return jsonify({"ok": False, "error": {"code": e.name.lower().replace(" ", "_"), "message": e.description}}), e.code

    @app.errorhandler(Exception)
    def unhandled(e):
        app.logger.exception("Unhandled error")
        return jsonify({"ok": False, "error": {"code": "internal_error", "message": "Something went wrong."}}), 500

    with app.app_context():
        import models  # noqa: F401  (register tables)
        if db.engine.dialect.name == "sqlite":
            from sqlalchemy import text
            with db.engine.begin() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.execute(text("PRAGMA busy_timeout=60000"))
        if db.engine.dialect.name == "postgresql":
            from sqlalchemy import text
            with db.engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.create_all()
        from database.schema_guard import add_missing_columns
        add_missing_columns()

    return app


app = create_app() if os.getenv("SLIDEMIND_SKIP_AUTOAPP") != "1" else None

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=os.getenv("FLASK_ENV") == "development", port=5000)
