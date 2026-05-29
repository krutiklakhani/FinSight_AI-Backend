"""
Angel One SmartAPI – read-only integration with simulator mode.
"""

from __future__ import annotations

import logging
from typing import Any

import pyotp
from SmartApi import SmartConnect

from app.core.config import settings
from app.integrations.base import BaseBroker

logger = logging.getLogger(__name__)


class AngelOneClient(BaseBroker):
    """Angel One SmartAPI wrapper (read-only) with simulator fallback."""

    def __init__(self) -> None:
        self.api_key = settings.ANGEL_API_KEY or "your-angel-api-key"
        self._obj = SmartConnect(api_key=self.api_key)
        self._session_data: dict[str, Any] | None = None
        self._is_mock = False

    def _is_simulator(self) -> bool:
        return self.api_key == "your-angel-api-key" or self._is_mock

    async def login(
        self,
        client_id: str,
        password: str,
        totp_secret: str,
    ) -> dict[str, Any]:
        """Authenticate with Angel One using client credentials + TOTP."""
        if client_id.lower().startswith("mock") or self.api_key == "your-angel-api-key":
            self._is_mock = True
            self._session_data = {"jwtToken": "mock_angel_jwt", "refreshToken": "mock_angel_refresh"}
            return {
                "access_token": "mock_angel_access_token",
                "refresh_token": "mock_angel_refresh_token",
                "feed_token": "mock_angel_feed_token",
                "client_id": client_id,
            }
            
        try:
            totp = pyotp.TOTP(totp_secret).now()
            data = self._obj.generateSession(client_id, password, totp)
            if data.get("status"):
                self._session_data = data["data"]
                auth_token = self._session_data["jwtToken"]
                self._obj.setAccessToken(auth_token)
                refresh_token = self._session_data.get("refreshToken", "")
                feed_token = self._obj.getfeedToken()
                return {
                    "access_token": auth_token,
                    "refresh_token": refresh_token,
                    "feed_token": feed_token,
                    "client_id": client_id,
                }
            raise ValueError(data.get("message", "Angel One login failed"))
        except Exception:
            logger.exception("Angel One login failed")
            raise

    # ── Read-only data methods ───────────────────────────────────────────

    async def get_holdings(self) -> list[dict[str, Any]]:
        """Fetch long-term equity holdings."""
        if self._is_simulator():
            return [
                {
                    "symbol": "HDFCBANK",
                    "exchange": "NSE",
                    "isin": "INE040A01034",
                    "quantity": 80,
                    "average_price": 1567.0,
                    "current_price": 1690.3,
                    "pnl": 9864.0,
                    "pnl_percentage": 7.87,
                    "invested_value": 125360.0,
                    "current_value": 135224.0,
                    "sector": "Banking",
                    "instrument_type": "EQ",
                },
                {
                    "symbol": "ICICIBANK",
                    "exchange": "NSE",
                    "isin": "INE090A01021",
                    "quantity": 100,
                    "average_price": 945.0,
                    "current_price": 1023.55,
                    "pnl": 7855.0,
                    "pnl_percentage": 8.31,
                    "invested_value": 94500.0,
                    "current_value": 102355.0,
                    "sector": "Banking",
                    "instrument_type": "EQ",
                },
                {
                    "symbol": "SBIN",
                    "exchange": "NSE",
                    "isin": "INE062A01020",
                    "quantity": 150,
                    "average_price": 567.0,
                    "current_price": 612.85,
                    "pnl": 6877.5,
                    "pnl_percentage": 8.09,
                    "invested_value": 85050.0,
                    "current_value": 91927.5,
                    "sector": "Banking",
                    "instrument_type": "EQ",
                }
            ]
            
        try:
            response = self._obj.holding()
            if not response.get("status"):
                return []
            holdings = response.get("data", []) or []
            return [
                {
                    "symbol": h.get("tradingsymbol", ""),
                    "exchange": h.get("exchange", "NSE"),
                    "isin": h.get("isin", ""),
                    "quantity": int(h.get("quantity", 0)),
                    "average_price": float(h.get("averageprice", 0)),
                    "current_price": float(h.get("ltp", 0)),
                    "pnl": float(h.get("profitandloss", 0)),
                    "pnl_percentage": float(h.get("pnlpercentage", 0)),
                    "invested_value": (
                        float(h.get("averageprice", 0)) * int(h.get("quantity", 0))
                    ),
                    "current_value": (
                        float(h.get("ltp", 0)) * int(h.get("quantity", 0))
                    ),
                    "instrument_type": "EQ",
                }
                for h in holdings
            ]
        except Exception:
            logger.exception("Angel One get_holdings failed")
            raise

    async def get_positions(self) -> list[dict[str, Any]]:
        """Fetch intraday / open positions."""
        if self._is_simulator():
            return [
                {
                    "symbol": "AXISBANK",
                    "exchange": "NSE",
                    "quantity": 50,
                    "buy_price": 1050.0,
                    "sell_price": 1065.5,
                    "pnl": 775.0,
                    "product_type": "INTRADAY",
                }
            ]
            
        try:
            response = self._obj.position()
            if not response.get("status"):
                return []
            positions = response.get("data", []) or []
            return [
                {
                    "symbol": p.get("tradingsymbol", ""),
                    "exchange": p.get("exchange", "NSE"),
                    "quantity": int(p.get("netqty", 0)),
                    "buy_price": float(p.get("avgnetprice", 0)),
                    "sell_price": float(p.get("ltp", 0)),
                    "pnl": float(p.get("pnl", 0)),
                    "product_type": p.get("producttype", "CNC"),
                }
                for p in positions
            ]
        except Exception:
            logger.exception("Angel One get_positions failed")
            raise

    async def get_funds(self) -> dict[str, Any]:
        """Fetch margin / fund details via RMS limits."""
        if self._is_simulator():
            return {
                "available_cash": 245000.0,
                "used_margin": 12000.0,
                "total_balance": 257000.0,
            }
            
        try:
            response = self._obj.rmsLimit()
            if not response.get("status"):
                return {"available_cash": 0, "used_margin": 0, "total_balance": 0}
            data = response.get("data", {}) or {}
            return {
                "available_cash": float(data.get("availablecash", 0)),
                "used_margin": float(data.get("utiliseddebits", 0)),
                "total_balance": float(data.get("net", 0)),
            }
        except Exception:
            logger.exception("Angel One get_funds failed")
            raise

    async def get_profile(self) -> dict[str, Any]:
        """Fetch user profile from Angel One."""
        if self._is_simulator():
            return {
                "broker_user_id": "MOCK_AN1234",
                "user_name": "Jane Smith (Simulated)",
                "email": "janesmith@example.com",
                "broker": "angelone",
            }
            
        try:
            response = self._obj.getProfile(self._obj.refresh_token or "")
            data = response.get("data", {}) or {}
            return {
                "broker_user_id": data.get("clientcode", ""),
                "user_name": data.get("name", ""),
                "email": data.get("email", ""),
                "broker": "angelone",
            }
        except Exception:
            logger.exception("Angel One get_profile failed")
            raise
