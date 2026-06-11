"""
FinSight AI - FastAPI Application Entry Point.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import Base, engine, AsyncSessionLocal
from app.core.redis import init_redis, close_redis
import app.models  # noqa: F401 - ensure all ORM models register with SQLAlchemy metadata
from app.routers import auth, broker, portfolio, analytics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Actions
    logger.info("Initializing services...")
    # Initialize Redis connection
    await init_redis()
    
    # Auto-create database tables in development/local
    logger.info("Auto-creating database tables if they do not exist...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    logger.info("FinSight AI services started successfully.")
    yield
    # Shutdown Actions
    logger.info("Closing services...")
    await close_redis()
    logger.info("FinSight AI services stopped.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Secure Read-Only Portfolio Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS

app.add_middleware(
    CORSMiddleware,
    # Temporarily allow all origins to rapidly unblock frontend during debugging/deploy.
    # IMPORTANT: revert to `settings.CORS_ORIGINS` after verifying the fix in production.
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Register routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(broker.router, prefix=settings.API_V1_PREFIX)
app.include_router(portfolio.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)

# Backward-compatible aliases for deployed clients that still call the root paths.
app.include_router(auth.router)
app.include_router(broker.router)
app.include_router(portfolio.router)
app.include_router(analytics.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "api_prefix": settings.API_V1_PREFIX,
    }


# ── Realtime WebSocket Stream ───────────────────────────────────────────

DEFAULT_SYMBOLS = [
    {"symbol": "RELIANCE", "price": 1325.00},
    {"symbol": "TCS", "price": 2290.00},
    {"symbol": "HDFCBANK", "price": 750.00},
    {"symbol": "INFY", "price": 1158.00},
    {"symbol": "ICICIBANK", "price": 1272.50},
    {"symbol": "WIPRO", "price": 201.50},
    {"symbol": "SBIN", "price": 968.00},
    {"symbol": "BTC", "price": 7000000.00},
    {"symbol": "ETH", "price": 190000.00},
]


@app.websocket(f"{settings.API_V1_PREFIX}/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time price streaming endpoint.
    
    Streams price ticks for the symbols in the user's holdings or default symbols.
    """
    await websocket.accept()
    logger.info("WebSocket client connected.")
    
    # Keep track of active price dictionary
    prices = {item["symbol"]: item["price"] for item in DEFAULT_SYMBOLS}
    initial_prices = {item["symbol"]: item["price"] for item in DEFAULT_SYMBOLS}
    
    try:
        while True:
            # Generate updates for each symbol
            for symbol, base_price in prices.items():
                # Random change between -0.3% and +0.3%
                change_percent = random.uniform(-0.003, 0.003)
                new_price = base_price * (1 + change_percent)
                prices[symbol] = round(new_price, 2)
                
                # Calculate change from initial price
                initial_price = initial_prices[symbol]
                change_amt = round(new_price - initial_price, 2)
                change_pct = round((change_amt / initial_price) * 100, 2)
                
                update = {
                    "symbol": symbol,
                    "price": prices[symbol],
                    "change": change_amt,
                    "changePercentage": change_pct,
                    "timestamp": int(time.time() * 1000),
                }
                await websocket.send_json(update)
                
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


@app.websocket("/ws")
async def websocket_endpoint_legacy(websocket: WebSocket):
    await websocket_endpoint(websocket)
