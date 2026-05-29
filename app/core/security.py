"""
Security helpers – JWT tokens, password hashing, Fernet encryption.

* Broker access-tokens are encrypted with Fernet before DB storage.
* JWTs carry a ``type`` claim (``access`` | ``refresh``).
* Passwords are hashed with bcrypt via passlib.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Password hashing ────────────────────────────────────────────────────

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return _pwd_ctx.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify *plain_password* against a bcrypt *hashed_password*."""
    return _pwd_ctx.verify(plain_password, hashed_password)


# ── JWT tokens ───────────────────────────────────────────────────────────


def create_access_token(data: dict) -> str:
    """Create a short-lived JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a long-lived JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Raises ``JWTError`` on invalid / expired tokens.
    """
    try:
        payload: dict = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        raise


# ── Fernet encryption (broker tokens at rest) ───────────────────────────

_fernet = Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_token(token: str) -> str:
    """Encrypt a plaintext broker token for safe DB storage."""
    return _fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a stored broker token back to plaintext."""
    return _fernet.decrypt(encrypted_token.encode()).decode()


# ── OAuth helpers ────────────────────────────────────────────────────────


def generate_state() -> str:
    """Generate a cryptographically-secure random state string for OAuth flows."""
    return secrets.token_urlsafe(32)
