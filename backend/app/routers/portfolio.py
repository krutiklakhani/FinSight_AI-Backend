"""
Portfolio router – read-only portfolio views.
Supports multiple routing patterns to align with frontend API requests.
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.broker import BrokerConnection
from app.models.user import User
from app.schemas.portfolio import (
    HoldingResponse,
    PortfolioHistory,
    PortfolioSummary,
    PositionResponse,
)
from app.services.auth_service import get_current_user
from app.services.portfolio_service import (
    get_aggregated_portfolio,
    get_all_holdings,
    get_all_positions,
    get_portfolio_history,
    sync_broker_holdings,
)

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get("", response_model=PortfolioSummary)
@router.get("/summary", response_model=PortfolioSummary)
async def portfolio_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioSummary:
    """Aggregated portfolio summary across all brokers."""
    return await get_aggregated_portfolio(db, current_user.id)


@router.get("/holdings", response_model=list[HoldingResponse])
async def portfolio_holdings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HoldingResponse]:
    """All holdings across connected brokers."""
    return await get_all_holdings(db, current_user.id)


@router.get("/positions", response_model=list[PositionResponse])
async def portfolio_positions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PositionResponse]:
    """All open positions across connected brokers."""
    return await get_all_positions(db, current_user.id)


@router.get("/history", response_model=list[PortfolioHistory])
async def portfolio_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PortfolioHistory]:
    """Historical portfolio value snapshots."""
    return await get_portfolio_history(db, current_user.id)


@router.post("/sync")
async def sync_all(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Trigger a full sync across all active broker connections."""
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.is_active.is_(True),
        ),
    )
    connections = result.scalars().all()
    synced = 0
    errors: list[str] = []
    for conn in connections:
        try:
            await sync_broker_holdings(db, current_user.id, conn.id)
            synced += 1
        except Exception as exc:
            errors.append(f"{conn.broker_name.value}: {exc!s}")
    return {"synced": synced, "errors": errors}
