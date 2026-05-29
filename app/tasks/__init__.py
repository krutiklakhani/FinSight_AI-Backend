"""
Celery Background Tasks Configuration.

Defines the Celery application and background tasks for FinSight AI.
Uses an event loop runner to execute asynchronous DB operations.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.broker import BrokerConnection
from app.models.portfolio import Holding
from app.models.prediction import Prediction
from app.services.portfolio_service import sync_broker_holdings, create_snapshot
from app.ml.models import get_predictions_for_symbols

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    "finsight",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery settings
celery_app.conf.update(
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
)

# Alias for command launcher `celery -A app.tasks`
app = celery_app

# Helper to run async functions in Celery worker thread
def run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        return asyncio.get_event_loop().run_until_complete(coro)


# ── Periodic task definitions ──────────────────────────────────────────


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Sync all connected broker holdings every 30 minutes
    sender.add_periodic_task(
        1800.0,
        sync_all_active_brokers.s(),
        name="Sync active broker holdings (30m)",
    )
    
    # Run ML model training & predictions daily at 00:00 AM IST
    sender.add_periodic_task(
        crontab(hour=0, minute=0),
        generate_ml_predictions_task.s(),
        name="Generate ML Volatility and Trend predictions (Daily)",
    )

    # Take a daily snapshot of all portfolios at 11:50 PM IST
    sender.add_periodic_task(
        crontab(hour=23, minute=50),
        take_daily_portfolio_snapshots.s(),
        name="Take daily portfolio value snapshots (Daily)",
    )


# ── Background Tasks ──────────────────────────────────────────────────


@celery_app.task
def sync_all_active_brokers():
    """Background task to sync all connected, active broker accounts."""
    logger.info("Executing periodic broker sync task...")
    
    async def _sync():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(BrokerConnection).where(BrokerConnection.is_active == True)
            )
            connections = result.scalars().all()
            logger.info(f"Found {len(connections)} active broker connections to sync.")
            for conn in connections:
                try:
                    logger.info(f"Syncing connection {conn.id} for user {conn.user_id}")
                    await sync_broker_holdings(db, conn.user_id, conn.id)
                    await db.commit()
                except Exception as e:
                    logger.error(f"Error syncing connection {conn.id}: {e}")
                    await db.rollback()

    run_async(_sync())
    logger.info("Broker sync task finished.")


@celery_app.task
def generate_ml_predictions_task():
    """Run trained ML models on users' holdings and store results in DB."""
    logger.info("Executing ML predictions task...")
    
    async def _predict():
        async with AsyncSessionLocal() as db:
            # Fetch all users
            users_res = await db.execute(select(User))
            users = users_res.scalars().all()
            
            for user in users:
                # Fetch symbols in user holdings
                holdings_res = await db.execute(
                    select(Holding.symbol).where(Holding.user_id == user.id).distinct()
                )
                symbols = [h for h in holdings_res.scalars().all()]
                
                # Default to some major indexes/assets if they have no holdings
                if not symbols:
                    symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "BTC", "ETH"]
                    
                # Generate predictions
                predictions_list = get_predictions_for_symbols(symbols)
                
                for p_dict in predictions_list:
                    # Map to SQLAlchemy object
                    prediction = Prediction(
                        id=p_dict["id"],
                        user_id=user.id,
                        prediction_type=p_dict["prediction_type"],
                        symbol=p_dict["symbol"],
                        predicted_value=p_dict["predicted_value"],
                        confidence=p_dict["confidence"],
                        model_version=p_dict["model_version"],
                        created_at=p_dict["created_at"],
                    )
                    db.add(prediction)
            
            await db.commit()

    run_async(_predict())
    logger.info("ML predictions task finished.")


@celery_app.task
def take_daily_portfolio_snapshots():
    """Take daily portfolio value snapshots for historical charting."""
    logger.info("Executing daily portfolio snapshot task...")
    
    async def _snapshot():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.is_active == True))
            users = result.scalars().all()
            for user in users:
                try:
                    logger.info(f"Generating portfolio snapshot for user {user.id}")
                    await create_snapshot(db, user.id)
                    await db.commit()
                except Exception as e:
                    logger.error(f"Error snapshotting portfolio for user {user.id}: {e}")
                    await db.rollback()

    run_async(_snapshot())
    logger.info("Portfolio snapshot task finished.")
