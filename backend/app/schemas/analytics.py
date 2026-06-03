"""
Analytics & prediction Pydantic v2 schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model that automatically converts snake_case fields to camelCase in JSON serialization/validation."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class AllocationItem(CamelModel):
    """A single slice of a portfolio allocation."""

    name: str
    value: float
    percentage: float
    color: str | None = None


class SectorAllocation(CamelModel):
    """Sector-wise allocation breakdown."""

    sectors: list[AllocationItem]


class RiskMetrics(CamelModel):
    """Portfolio-level risk indicators."""

    risk_score: float
    diversification_score: float
    concentration_risk: float
    beta: float
    volatility: float


class PredictionResponse(CamelModel):
    """ML prediction result."""

    id: uuid.UUID
    prediction_type: str
    symbol: str
    predicted_value: float
    confidence: float
    model_version: str
    created_at: datetime


class PerformanceMetrics(CamelModel):
    """Historical performance indicators."""

    total_return: float
    cagr: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
