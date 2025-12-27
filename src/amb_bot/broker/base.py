from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Quote:
    symbol: str
    price: float
    volume: Optional[float] = None  # For volume anomaly detection


@dataclass
class Position:
    symbol: str
    qty: float
    avg_price: float


@dataclass
class OrderResult:
    symbol: str
    qty: float
    side: str
    price: float


class BrokerClient(ABC):
    @abstractmethod
    async def fetch_quote(self, symbol: str) -> Quote:
        raise NotImplementedError

    @abstractmethod
    async def fetch_historical(self, symbol: str, days: int = 60) -> List[float]:
        """Fetch historical daily closing prices for trend analysis."""
        raise NotImplementedError

    async def fetch_volume_history(self, symbol: str, days: int = 20) -> List[float]:
        """Fetch historical volume data. Default implementation returns empty list."""
        return []

    @abstractmethod
    async def place_order(self, symbol: str, qty: float, side: str, limit_price: Optional[float] = None) -> OrderResult:
        """Place order. If limit_price is set, uses limit order instead of market order."""
        raise NotImplementedError

    async def place_limit_order(self, symbol: str, qty: float, side: str, limit_price: float) -> OrderResult:
        """Convenience method for limit orders."""
        return await self.place_order(symbol, qty, side, limit_price=limit_price)

    @abstractmethod
    async def list_positions(self) -> List[Position]:
        raise NotImplementedError

    @abstractmethod
    async def close_position(self, symbol: str, qty: Optional[float] = None) -> OrderResult:
        raise NotImplementedError
