"""
Unit tests for authentication security utilities.
"""

from __future__ import annotations

from jose import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)


def test_password_hashing() -> None:
    """Verify passwords are correctly hashed and validated."""
    password = "secretPassword123"
    hashed = hash_password(password)

    # Hash should be different from raw password
    assert hashed != password

    # Verification should succeed with correct password
    assert verify_password(password, hashed) is True

    # Verification should fail with incorrect password
    assert verify_password("wrongPassword", hashed) is False


def test_jwt_tokens() -> None:
    """Verify JWT access and refresh tokens are correctly signed and decodable."""
    data = {"sub": "user-12345"}

    # Generate tokens
    access_token = create_access_token(data)
    refresh_token = create_refresh_token(data)

    assert access_token != refresh_token

    # Decode and verify access token
    access_payload = verify_token(access_token)
    assert access_payload["sub"] == "user-12345"
    assert access_payload["type"] == "access"

    # Decode and verify refresh token
    refresh_payload = verify_token(refresh_token)
    assert refresh_payload["sub"] == "user-12345"
    assert refresh_payload["type"] == "refresh"
