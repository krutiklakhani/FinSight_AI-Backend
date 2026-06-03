"""
Abstract base class for read-only broker integrations.

All broker clients MUST inherit from ``BaseBroker`` and implement the
four read-only methods.  **No trade-execution methods are permitted.**
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseBroker(ABC):
    """Read-only broker interface.

    Concrete subclasses provide integration with a specific brokerage
    API (Zerodha Kite, Angel One SmartAPI, Binance, etc.).
    """

    @abstractmethod
    async def get_holdings(self) -> list[dict]:
        """Fetch the user's current long-term holdings."""
        ...

    @abstractmethod
    async def get_positions(self) -> list[dict]:
        """Fetch intraday / open positions."""
        ...

    @abstractmethod
    async def get_funds(self) -> dict:
        """Fetch available margin / fund balances."""
        ...

    @abstractmethod
    async def get_profile(self) -> dict:
        """Fetch the broker account profile / identity."""
        ...
