"""
Zerodha Kite Connect v3 – read-only integration with simulator mode.
"""

from __future__ import annotations

import logging
from typing import Any

from kiteconnect import KiteConnect

from app.core.config import settings
from app.integrations.base import BaseBroker

logger = logging.getLogger(__name__)


class ZerodhaClient(BaseBroker):
    """Kite Connect v3 wrapper (read-only) with simulator fallback."""

    def __init__(self, access_token: str | None = None, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.KITE_API_KEY or "your-kite-api-key"
        self._kite = KiteConnect(api_key=self.api_key)
        self.access_token = access_token
        if access_token:
            self._kite.set_access_token(access_token)
            
    def _is_simulator(self) -> bool:
        mock_keys = {"your-kite-api-key", "kite_sim_key", "SIMULATOR"}
        return (
            self.api_key in mock_keys
            or (self.access_token is not None and self.access_token.startswith("mock"))
        )

    # ── OAuth flow helpers ───────────────────────────────────────────────

    def get_login_url(self) -> str:
        """Return the Kite login URL for the user to authorise the app."""
        if self._is_simulator():
            return "https://fin-sight-ai-frontend.vercel.app/profile?broker=zerodha&status=callback&request_token=mock_zerodha_token"
        return self._kite.login_url()

    async def handle_callback(self, request_token: str) -> str:
        """Exchange a *request_token* from the OAuth callback for an access token."""
        if self._is_simulator() or request_token.startswith("mock"):
            return "mock_zerodha_access_token"
        data = self._kite.generate_session(
            request_token,
            api_secret=settings.KITE_API_SECRET,
        )
        access_token: str = data["access_token"]
        self._kite.set_access_token(access_token)
        return access_token

    # ── Read-only data methods ───────────────────────────────────────────

    async def get_holdings(self) -> list[dict[str, Any]]:
        """Fetch long-term equity holdings."""
        if self._is_simulator():
            return [
                {
                    "symbol": "RELIANCE",
                    "exchange": "NSE",
                    "isin": "INE002A01018",
                    "quantity": 50.0,
                    "average_price": 2340.0,
                    "current_price": 2567.85,
                    "pnl": 11392.5,
                    "pnl_percentage": 9.74,
                    "invested_value": 117000.0,
                    "current_value": 128392.5,
                    "sector": "Energy",
                    "instrument_type": "EQ",
                },
                {
                    "symbol": "TCS",
                    "exchange": "NSE",
                    "isin": "INE467B01029",
                    "quantity": 30.0,
                    "average_price": 3456.0,
                    "current_price": 3789.45,
                    "pnl": 10003.5,
                    "pnl_percentage": 9.65,
                    "invested_value": 103680.0,
                    "current_value": 113683.5,
                    "sector": "IT",
                    "instrument_type": "EQ",
                },
                {
                    "symbol": "INFY",
                    "exchange": "NSE",
                    "isin": "INE009A01021",
                    "quantity": 60.0,
                    "average_price": 1456.0,
                    "current_price": 1523.7,
                    "pnl": 4062.0,
                    "pnl_percentage": 4.65,
                    "invested_value": 87360.0,
                    "current_value": 91422.0,
                    "sector": "IT",
                    "instrument_type": "EQ",
                },
                {
                    "symbol": "WIPRO",
                    "exchange": "NSE",
                    "isin": "INE075A01022",
                    "quantity": 120.0,
                    "average_price": 412.0,
                    "current_price": 387.6,
                    "pnl": -2928.0,
                    "pnl_percentage": -5.92,
                    "invested_value": 49440.0,
                    "current_value": 46512.0,
                    "sector": "IT",
                    "instrument_type": "EQ",
                },
                {
                    "symbol": "BHARTIARTL",
                    "exchange": "NSE",
                    "isin": "INE397D01024",
                    "quantity": 45.0,
                    "average_price": 876.0,
                    "current_price": 1145.2,
                    "pnl": 12114.0,
                    "pnl_percentage": 30.73,
                    "invested_value": 39420.0,
                    "current_value": 51534.0,
                    "sector": "Telecom",
                    "instrument_type": "EQ",
                },
                {
                    "symbol": "TATAMOTORS",
                    "exchange": "NSE",
                    "isin": "INE155A01022",
                    "quantity": 70.0,
                    "average_price": 623.0,
                    "current_price": 578.4,
                    "pnl": -3122.0,
                    "pnl_percentage": -7.15,
                    "invested_value": 43610.0,
                    "current_value": 40488.0,
                    "sector": "Auto",
                    "instrument_type": "EQ",
                },
                {
                    "symbol": "ADANIENT",
                    "exchange": "NSE",
                    "isin": "INE423A01024",
                    "quantity": 25.0,
                    "average_price": 2890.0,
                    "current_price": 3156.7,
                    "pnl": 6667.5,
                    "pnl_percentage": 9.23,
                    "invested_value": 72250.0,
                    "current_value": 78917.5,
                    "sector": "Infrastructure",
                    "instrument_type": "EQ",
                }
            ]
        try:
            holdings = self._kite.holdings()
            return [
                {
                    "symbol": h["tradingsymbol"],
                    "exchange": h["exchange"],
                    "isin": h.get("isin", ""),
                    "quantity": h["quantity"],
                    "average_price": h["average_price"],
                    "current_price": h["last_price"],
                    "pnl": h["pnl"],
                    "pnl_percentage": (
                        (h["pnl"] / (h["average_price"] * h["quantity"]) * 100)
                        if h["average_price"] and h["quantity"]
                        else 0.0
                    ),
                    "invested_value": h["average_price"] * h["quantity"],
                    "current_value": h["last_price"] * h["quantity"],
                    "instrument_type": h.get("instrument_type", "EQ"),
                }
                for h in holdings
            ]
        except Exception:
            logger.exception("Zerodha get_holdings failed")
            raise

    async def get_positions(self) -> list[dict[str, Any]]:
        """Fetch intraday + day positions."""
        if self._is_simulator():
            return [
                {
                    "symbol": "ITC",
                    "exchange": "NSE",
                    "quantity": 100.0,
                    "buy_price": 420.0,
                    "sell_price": 435.2,
                    "pnl": 1520.0,
                    "product_type": "MIS",
                }
            ]
        try:
            positions = self._kite.positions()
            result: list[dict[str, Any]] = []
            for pos in positions.get("net", []):
                result.append(
                    {
                        "symbol": pos["tradingsymbol"],
                        "exchange": pos["exchange"],
                        "quantity": pos["quantity"],
                        "buy_price": pos["average_price"],
                        "sell_price": pos["last_price"],
                        "pnl": pos["pnl"],
                        "product_type": pos["product"],
                    },
                )
            return result
        except Exception:
            logger.exception("Zerodha get_positions failed")
            raise

    async def get_funds(self) -> dict[str, Any]:
        """Fetch margin / fund details."""
        if self._is_simulator():
            return {
                "available_cash": 150000.0,
                "used_margin": 45000.0,
                "total_balance": 195000.0,
            }
        try:
            margins = self._kite.margins()
            equity = margins.get("equity", {})
            return {
                "available_cash": equity.get("available", {}).get("cash", 0),
                "used_margin": equity.get("utilised", {}).get("debits", 0),
                "total_balance": equity.get("net", 0),
            }
        except Exception:
            logger.exception("Zerodha get_funds failed")
            raise

    async def get_profile(self) -> dict[str, Any]:
        """Fetch user profile from Kite."""
        if self._is_simulator():
            return {
                "broker_user_id": "MOCK_ZR1234",
                "user_name": "John Doe (Simulated)",
                "email": "johndoe@example.com",
                "broker": "zerodha",
            }
        try:
            profile = self._kite.profile()
            return {
                "broker_user_id": profile.get("user_id", ""),
                "user_name": profile.get("user_name", ""),
                "email": profile.get("email", ""),
                "broker": "zerodha",
            }
        except Exception:
            logger.exception("Zerodha get_profile failed")
            raise
