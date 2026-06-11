"""
Application configuration loaded from environment variables.

All secrets and connection strings are pulled from a .env file via
pydantic-settings.  Sensitive values (ENCRYPTION_KEY, SECRET_KEY) must
never be committed to version control.
"""

from __future__ import annotations

from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import json

# Locate .env file - looks in project root (parent of backend/)
# Works from both project root and backend directory
_config_dir = Path(__file__).parent
_backend_dir = _config_dir.parent.parent
_project_root = _backend_dir.parent if _backend_dir.name == "backend" else _backend_dir

_env_file = _project_root / ".env"

# If .env not found in project root, try current directory
if not _env_file.exists() and Path(".env").exists():
    _env_file = Path(".env").resolve()

# Explicitly load .env file with expanded env vars support
# Do not override environment variables supplied by the shell/runtime.
load_dotenv(_env_file, override=False)


class Settings(BaseSettings):
    """Central configuration for FinSight AI backend."""

    model_config = SettingsConfigDict(
        env_file=str(_env_file),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Project ──────────────────────────────────────────────────────────
    PROJECT_NAME: str = "FinSight AI"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        if isinstance(value, str):
            normalised = value.strip().lower()
            if normalised in {"1", "true", "yes", "on", "debug"}:
                return True
            if normalised in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value

    # ── Database (PostgreSQL + asyncpg) ──────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/finsight"

    # ── Redis ────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Auth / JWT ───────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Fernet encryption key (for broker tokens at rest) ────────────────
    ENCRYPTION_KEY: str = "change-me-generate-with-Fernet.generate_key"

    # ── Zerodha Kite Connect ─────────────────────────────────────────────
    KITE_API_KEY: str = ""
    KITE_API_SECRET: str = ""
    KITE_REDIRECT_URI: str = "https://finsight-ai-backend-b37j.onrender.com/api/v1/broker/callback/zerodha"
    FRONTEND_URL: str = "https://fin-sight-ai-frontend.vercel.app"

    # ── Angel One SmartAPI ───────────────────────────────────────────────
    ANGEL_API_KEY: str = ""
    ANGEL_CLIENT_ID: str = ""

    # ── Binance ──────────────────────────────────────────────────────────
    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "https://fin-sight-ai-frontend.vercel.app",
        "https://fin-sight-ai-frontend-1hafyqt9d.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [i.strip() for i in v.split(",")]
        return v

    # ── Celery ───────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"


settings = Settings()
