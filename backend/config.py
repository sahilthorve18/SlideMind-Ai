"""Environment-driven configuration. No secrets are hardcoded."""
import os

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))
load_dotenv()  # also load root or ambient .env if present


def _db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        return "sqlite:///slidemind_dev.sqlite3"
    # Render/Heroku style URLs use the legacy scheme.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    ENV = os.getenv("FLASK_ENV", os.getenv("ENV", "development")).lower()
    IS_PROD = ENV in ("production", "prod")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me" if not IS_PROD else "")
    if IS_PROD and (not SECRET_KEY or SECRET_KEY == "dev-only-change-me"):
        raise RuntimeError("CRITICAL SECURITY CONFIGURATION: SECRET_KEY environment variable must be set in production.")

    SQLALCHEMY_DATABASE_URI = _db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    _is_sqlite = _db_url().startswith("sqlite")
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        **({"connect_args": {"timeout": 60}} if _is_sqlite else {"pool_recycle": 280})
    }
    FRONTEND_ORIGINS = [
        o.strip() for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",") if o.strip()
    ]
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "15"))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "120 per minute")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    PLANNER_MODEL = os.getenv("PLANNER_MODEL", "")  # stronger model for storyline + slide specs (falls back to GEMINI_MODEL)
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
    CHAT_HISTORY_LIMIT = int(os.getenv("CHAT_HISTORY_LIMIT", "20"))
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    BACKEND_URL = os.getenv("BACKEND_URL", os.getenv("RENDER_EXTERNAL_URL", "")).rstrip("/")
    # Fernet key for encrypting Google refresh tokens at rest. REQUIRED in production.
    TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")
    DEV_LOGIN_ENABLED = os.getenv("DEV_LOGIN_ENABLED", "false" if IS_PROD else "true").lower() in ("true", "1")
    GUEST_MAX_PRESENTATIONS = int(os.getenv("GUEST_MAX_PRESENTATIONS", "3"))

    # Production secure cookie configuration
    SESSION_COOKIE_SECURE = IS_PROD
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "None" if IS_PROD else "Lax"
    # Persistent storage configuration (local filesystem / S3 / GCS)
    STORAGE_PROVIDER = os.getenv("STORAGE_PROVIDER", "local")
    STORAGE_LOCAL_DIR = os.getenv("STORAGE_LOCAL_DIR", os.path.join(basedir, "persistent_storage"))
    S3_BUCKET = os.getenv("S3_BUCKET", "")
    S3_REGION = os.getenv("S3_REGION", "us-east-1")
    GCS_BUCKET = os.getenv("GCS_BUCKET", "")
