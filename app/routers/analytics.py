"""
Analytics router – allocation, risk, performance, predictions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.analytics import (
    PerformanceMetrics,
    PredictionResponse,
    RiskMetrics,
    SectorAllocation,
)
from app.services.analytics_service import (
    get_performance_metrics,
    get_predictions,
    get_risk_metrics,
    get_sector_allocation,
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/allocation", response_model=SectorAllocation)
async def allocation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SectorAllocation:
    """Sector-wise allocation breakdown."""
    return await get_sector_allocation(db, current_user.id)


@router.get("/risk", response_model=RiskMetrics)
async def risk(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RiskMetrics:
    """Portfolio risk indicators."""
    return await get_risk_metrics(db, current_user.id)


@router.get("/performance", response_model=PerformanceMetrics)
async def performance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PerformanceMetrics:
    """Historical performance metrics."""
    return await get_performance_metrics(db, current_user.id)


@router.get("/predictions", response_model=list[PredictionResponse])
async def predictions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PredictionResponse]:
    """ML-generated predictions for the user's portfolio."""
    return await get_predictions(db, current_user.id)
