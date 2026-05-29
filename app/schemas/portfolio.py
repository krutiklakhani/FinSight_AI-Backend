"""
Portfolio Pydantic v2 schemas.
"""

from __future__ import annotations

import uuid
from datetime import date
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model that automatically converts snake_case fields to camelCase in JSON serialization/validation."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class HoldingResponse(CamelModel):
    """A single holding from any broker."""

    id: uuid.UUID
    symbol: str
    exchange: str
    quantity: float
    average_price: float
    current_price: float
    pnl: float
    pnl_percentage: float
    invested_value: float
    current_value: float
    sector: str | None = None
    broker_name: str | None = None
    isin: str | None = None
    instrument_type: str | None = None


class PositionResponse(CamelModel):
    """A single open position from any broker."""

    id: uuid.UUID
    symbol: str
    exchange: str
    quantity: float
    buy_price: float
    sell_price: float
    pnl: float
    product_type: str
    broker_name: str | None = None


class PortfolioSummary(CamelModel):
    """Aggregated portfolio overview across all brokers."""

    total_invested: float
    total_current_value: float
    total_pnl: float
    total_pnl_percentage: float
    holdings_count: int
    day_change: float = 0.0
    day_change_percentage: float = 0.0


class PortfolioHistory(CamelModel):
    """Single data-point in portfolio value history."""

    date: date
    total_value: float
    total_pnl: float
