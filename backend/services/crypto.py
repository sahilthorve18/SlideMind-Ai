"""Encryption of secrets at rest (Google refresh tokens)."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


def _fernet() -> Fernet:
    key = current_app.config.get("TOKEN_ENCRYPTION_KEY")
    if key:
        return Fernet(key.encode())
    if current_app.config.get("ENV_IS_PRODUCTION"):
        raise RuntimeError("TOKEN_ENCRYPTION_KEY must be set in production.")
    # Development convenience only: derive a key from SECRET_KEY.
    digest = hashlib.sha256(current_app.config["SECRET_KEY"].encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return None  # key rotated or data corrupted: treat as not connected
