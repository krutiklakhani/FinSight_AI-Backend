"""
Async Redis connection pool and caching helpers.

Uses ``redis.asyncio`` (the modern async Redis client, formerly aioredis).
Default cache TTL is 300 s (5 minutes).
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

DEFAULT_TTL: int = 300  # seconds

_pool: aioredis.Redis | None = None


async def init_redis() -> aioredis.Redis:
    """Initialise (or return existing) Redis connection pool."""
    global _pool  # noqa: PLW0603
    if _pool is None:
        _pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _pool


async def close_redis() -> None:
    """Gracefully close the Redis connection pool."""
    global _pool  # noqa: PLW0603
    if _pool is not None:
        await _pool.close()
        _pool = None


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI dependency that yields a Redis client."""
    client = await init_redis()
    yield client


# ── Cache helpers ────────────────────────────────────────────────────────


async def cache_get(key: str) -> Any | None:
    """Return cached value (JSON-decoded) or ``None``."""
    client = await init_redis()
    raw = await client.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


async def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    """Store *value* (JSON-encoded) with an expiry of *ttl* seconds."""
    client = await init_redis()
    serialised = json.dumps(value, default=str)
    await client.set(key, serialised, ex=ttl)


async def cache_delete(key: str) -> None:
    """Remove a cache entry."""
    client = await init_redis()
    await client.delete(key)
