"""
Broker Pydantic v2 schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model that automatically converts snake_case fields to camelCase in JSON serialization/validation."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class BrokerConnectRequest(BaseModel):
    """Payload to connect a broker account."""

    broker_name: str
    credentials: dict[str, Any]


class BrokerConnectionResponse(CamelModel):
    """Public representation of a broker connection."""

    id: uuid.UUID
    broker_name: str
    broker_user_id: str | None = None
    is_active: bool
    last_synced_at: datetime | None = None
    created_at: datetime


class BrokerStatus(CamelModel):
    """Quick status check for a broker."""

    broker_name: str
    is_connected: bool
    last_synced_at: datetime | None = None
