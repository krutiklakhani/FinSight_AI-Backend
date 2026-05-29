"""
Unit tests for portfolio analytics and risk calculations.
"""

from __future__ import annotations

import math
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.portfolio import Holding, PortfolioSnapshot
from app.schemas.analytics import SectorAllocation
from app.services.analytics_service import (
    get_performance_metrics,
    get_risk_metrics,
    get_sector_allocation,
)


@pytest.mark.asyncio
async def test_get_sector_allocation() -> None:
    """Test sector allocation calculations and color assignments."""
    # Arrange
    user_id = uuid.uuid4()
    mock_db = AsyncMock()

    # Create mock holdings
    h1 = Holding(
        id=uuid.uuid4(),
        user_id=user_id,
        symbol="RELIANCE",
        sector="Energy",
        current_value=100000.0,
    )
    h2 = Holding(
        id=uuid.uuid4(),
        user_id=user_id,
        symbol="TCS",
        sector="Technology",
        current_value=150000.0,
    )
    h3 = Holding(
        id=uuid.uuid4(),
        user_id=user_id,
        symbol="INFY",
        sector="Technology",
        current_value=50000.0,
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [h1, h2, h3]
    mock_db.execute.return_value = mock_result

    # Act
    res = await get_sector_allocation(mock_db, user_id)

    # Assert
    assert isinstance(res, SectorAllocation)
    assert len(res.sectors) == 2  # Energy and Technology

    # Check Technology sector details (150k + 50k = 200k out of 300k total = 66.67%)
    tech = next(s for s in res.sectors if s.name == "Technology")
    assert tech.value == 200000.0
    assert math.isclose(tech.percentage, 66.67, abs_tol=0.01)

    # Check Energy sector details (100k out of 300k total = 33.33%)
    energy = next(s for s in res.sectors if s.name == "Energy")
    assert energy.value == 100000.0
    assert math.isclose(energy.percentage, 33.33, abs_tol=0.01)


@pytest.mark.asyncio
async def test_get_risk_metrics_diversified() -> None:
    """Test Herfindahl-Hirschman Index (HHI) concentration risk and diversification score."""
    # Arrange
    user_id = uuid.uuid4()
    mock_db = AsyncMock()

    # 4 equally weighted holdings (weights = 0.25 each)
    # HHI = 4 * (0.25^2) = 0.25
    # min_hhi = 1/4 = 0.25
    # diversification = (1 - 0.25) / (1 - 0.25) * 100 = 100%
    holdings = [
        Holding(
            id=uuid.uuid4(),
            user_id=user_id,
            symbol=f"SYM_{i}",
            current_value=25000.0,
            pnl_percentage=10.0,
        )
        for i in range(4)
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = holdings
    mock_db.execute.return_value = mock_result

    # Act
    res = await get_risk_metrics(mock_db, user_id)

    # Assert
    assert res.concentration_risk == 25.0  # HHI * 100
    assert res.diversification_score == 100.0
    assert res.volatility == 0.0  # All holdings have exact same pnl_pct


@pytest.mark.asyncio
async def test_get_performance_metrics_cagr() -> None:
    """Test CAGR and Sharpe ratio calculations from portfolio snapshots."""
    # Arrange
    user_id = uuid.uuid4()
    mock_db = AsyncMock()

    # Create 2 snapshots, 365 days apart
    # Value grows from 100,000 to 120,000 (growth = 1.2, years = 1.0)
    # Expected CAGR = (1.2^(1/1) - 1) * 100 = 20.0%
    s1 = PortfolioSnapshot(
        user_id=user_id,
        total_invested=100000.0,
        total_current_value=100000.0,
        total_pnl=0.0,
        total_pnl_percentage=0.0,
        snapshot_date=date(2025, 1, 1),
    )
    s2 = PortfolioSnapshot(
        user_id=user_id,
        total_invested=100000.0,
        total_current_value=120000.0,
        total_pnl=20000.0,
        total_pnl_percentage=20.0,
        snapshot_date=date(2026, 1, 1),
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [s1, s2]
    mock_db.execute.return_value = mock_result

    # Act
    res = await get_performance_metrics(mock_db, user_id)

    # Assert
    assert res.total_return == 20.0
    assert math.isclose(res.cagr, 20.0, abs_tol=0.1)
    assert res.max_drawdown == 0.0  # Kept rising
