"""
Portfolio ORM models: Holding, Position, PortfolioSnapshot.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    broker_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("broker_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    isin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    average_price: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pnl_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    invested_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    instrument_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="holdings")
    broker_connection = relationship("BrokerConnection", back_populates="holdings")

    def __repr__(self) -> str:
        return f"<Holding {self.symbol} qty={self.quantity}>"


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    broker_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("broker_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    buy_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sell_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    product_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="CNC",
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="positions")
    broker_connection = relationship("BrokerConnection", back_populates="positions")

    def __repr__(self) -> str:
        return f"<Position {self.symbol} qty={self.quantity}>"


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    total_invested: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_current_value: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    total_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_pnl_percentage: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    snapshot_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    holdings_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sector_allocation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PortfolioSnapshot {self.snapshot_date} user={self.user_id}>"
