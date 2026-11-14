"""Encryption of secrets at rest (Google refresh tokens)."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


def _fernet() -> Fernet:
    key = (current_app.config.get("TOKEN_ENCRYPTION_KEY") or "").strip()
    if key:
        try:
            return Fernet(key.encode())
        except Exception:
            current_app.logger.warning("Invalid TOKEN_ENCRYPTION_KEY format, falling back to SECRET_KEY derivation.")
    # Safe deterministic derivation from SECRET_KEY ensures encryption works reliably in all environments
    secret = (current_app.config.get("SECRET_KEY") or "slidemind-default-secret-key").strip()
    digest = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return None  # key rotated or data corrupted: treat as not connected
