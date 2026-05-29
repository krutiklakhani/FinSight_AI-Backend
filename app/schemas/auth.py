"""
Auth Pydantic v2 schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model that automatically converts snake_case fields to camelCase in JSON serialization/validation."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class UserCreate(BaseModel):
    """Payload for user registration."""
    # Allow both snake_case and camelCase payloads for registration
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)


class UserLogin(BaseModel):
    """Payload for user login."""

    email: EmailStr
    password: str


class UserResponse(CamelModel):
    """Public representation of a user."""

    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    role: str
    created_at: datetime


class TokenResponse(CamelModel):
    """JWT token pair returned on login / refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(CamelModel):
    """Payload for token refresh requests."""

    refresh_token: str


class TokenPayload(BaseModel):
    """Decoded JWT payload."""

    sub: str
    exp: int
    type: str
