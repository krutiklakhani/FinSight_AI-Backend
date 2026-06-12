"""
Binance API – read-only integration with simulator mode.
"""

from __future__ import annotations

import logging
from typing import Any

from binance import AsyncClient as BinanceAsyncClient

from app.core.config import settings
from app.integrations.base import BaseBroker

logger = logging.getLogger(__name__)


class BinanceClient(BaseBroker):
    """Binance async wrapper (read-only) with simulator fallback."""

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.BINANCE_API_KEY or "your-binance-api-key"
        self.api_secret = api_secret or settings.BINANCE_API_SECRET or "your-binance-api-secret"
        self._client: BinanceAsyncClient | None = None

    def _is_simulator(self) -> bool:
        return (
            self.api_key == "your-binance-api-key"
            or self.api_key.startswith("mock")
            or self.api_key == "SIMULATOR"
        )

    async def _ensure_client(self) -> BinanceAsyncClient:
        """Lazily initialise the async Binance client."""
        if self._client is None and not self._is_simulator():
            self._client = await BinanceAsyncClient.create(
                self.api_key,
                self.api_secret,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._client is not None:
            await self._client.close_connection()
            self._client = None

    # ── Read-only data methods ───────────────────────────────────────────

    async def get_holdings(self) -> list[dict[str, Any]]:
        """Return non-zero spot-wallet balances as 'holdings'."""
        if self._is_simulator():
            return [
                {
                    "symbol": "BTC",
                    "exchange": "BINANCE",
                    "isin": None,
                    "quantity": 0.5,
                    "average_price": 3200000.0,
                    "current_price": 3450000.0,
                    "pnl": 125000.0,
                    "pnl_percentage": 7.81,
                    "invested_value": 1600000.0,
                    "current_value": 1725000.0,
                    "sector": "Crypto",
                    "instrument_type": "CRYPTO",
                },
                {
                    "symbol": "ETH",
                    "exchange": "BINANCE",
                    "isin": None,
                    "quantity": 5.0,
                    "average_price": 195000.0,
                    "current_price": 218000.0,
                    "pnl": 115000.0,
                    "pnl_percentage": 11.79,
                    "invested_value": 975000.0,
                    "current_value": 1090000.0,
                    "sector": "Crypto",
                    "instrument_type": "CRYPTO",
                }
            ]
            
        try:
            client = await self._ensure_client()
            account = await client.get_account()
            balances = account.get("balances", [])
            holdings: list[dict[str, Any]] = []
            for b in balances:
                free = float(b.get("free", 0))
                locked = float(b.get("locked", 0))
                qty = free + locked
                if qty <= 0:
                    continue
                asset = b["asset"]
                # Attempt to get current price in USDT
                current_price = 0.0
                if asset != "USDT":
                    try:
                        ticker = await client.get_symbol_ticker(
                            symbol=f"{asset}USDT",
                        )
                        current_price = float(ticker.get("price", 0))
                    except Exception:
                        current_price = 0.0
                else:
                    current_price = 1.0

                holdings.append(
                    {
                        "symbol": asset,
                        "exchange": "BINANCE",
                        "isin": None,
                        "quantity": qty,
                        "average_price": 0.0,  # Binance doesn't expose cost basis
                        "current_price": current_price,
                        "pnl": 0.0,
                        "pnl_percentage": 0.0,
                        "invested_value": 0.0,
                        "current_value": qty * current_price,
                        "instrument_type": "CRYPTO",
                    },
                )
            return holdings
        except Exception:
            logger.exception("Binance get_holdings failed")
            raise

    async def get_positions(self) -> list[dict[str, Any]]:
        """Return open orders as 'positions'."""
        if self._is_simulator():
            return []
        try:
            client = await self._ensure_client()
            open_orders = await client.get_open_orders()
            return [
                {
                    "symbol": o["symbol"],
                    "exchange": "BINANCE",
                    "quantity": float(o.get("origQty", 0)),
                    "buy_price": float(o.get("price", 0)),
                    "sell_price": 0.0,
                    "pnl": 0.0,
                    "product_type": o.get("type", "LIMIT"),
                }
                for o in open_orders
            ]
        except Exception:
            logger.exception("Binance get_positions failed")
            raise

    async def get_funds(self) -> dict[str, Any]:
        """Aggregate USDT / BTC balances as a fund summary."""
        if self._is_simulator():
            return {
                "available_cash": 1250.0,
                "btc_balance": 0.5,
                "total_balance": 25000.0,
            }
        try:
            client = await self._ensure_client()
            account = await client.get_account()
            balances = {
                b["asset"]: float(b["free"]) + float(b["locked"])
                for b in account.get("balances", [])
            }
            return {
                "available_cash": balances.get("USDT", 0),
                "btc_balance": balances.get("BTC", 0),
                "total_balance": balances.get("USDT", 0),
            }
        except Exception:
            logger.exception("Binance get_funds failed")
            raise

    async def get_profile(self) -> dict[str, Any]:
        """Fetch account info as a profile."""
        if self._is_simulator():
            return {
                "broker_user_id": "MOCK_BI9876",
                "user_name": "Crypto Investor (Simulated)",
                "email": "crypto@example.com",
                "broker": "binance",
                "can_trade": True,
                "can_withdraw": False,
                "account_type": "SPOT",
            }
        try:
            client = await self._ensure_client()
            info = await client.get_account()
            return {
                "broker_user_id": str(info.get("uid", "")),
                "user_name": "",
                "email": "",
                "broker": "binance",
                "can_trade": info.get("canTrade", False),
                "can_withdraw": info.get("canWithdraw", False),
                "account_type": info.get("accountType", ""),
            }
        except Exception:
            logger.exception("Binance get_profile failed")
            raise
