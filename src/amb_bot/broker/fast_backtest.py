import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .base import BrokerClient, OrderResult, Position, Quote


class FastBacktestBroker(BrokerClient):
    """Offline fast backtesting broker with synthetic price/volume.

    - No network calls, fully deterministic per symbol.
    - Generates daily prices via geometric Brownian motion.
    - Simulates order fills with small slippage.
    """

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        initial_cash: float = 10000.0,
        monthly_budget: float = 200.0,
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.current_date = start_date
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.monthly_budget = monthly_budget
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Dict] = []
        self.portfolio_history: List[Dict] = []
        self._price_cache: Dict[str, List[Dict]] = {}

    async def connect(self) -> None:  # no-op for offline
        return None

    async def disconnect(self) -> None:  # no-op for offline
        return None

    def _generate_series(self, symbol: str) -> List[Dict]:
        if symbol in self._price_cache:
            return self._price_cache[symbol]

        days_total = max(365, (self.end_date - self.start_date).days + 60)
        # Deterministic seed per symbol
        seed = abs(hash(symbol)) % (2**32)
        rng = random.Random(seed)

        # Parameters for GBM
        start_price = max(20.0, (rng.random() * 180.0) + 20.0)
        mu = 0.08  # annual drift ~8%
        sigma = 0.25  # annual volatility ~25%
        dt = 1.0 / 252.0

        series: List[Dict] = []
        price = start_price
        date = self.start_date - timedelta(days=days_total)
        for _ in range(days_total * 2):  # generate ample history
            # GBM step
            z = rng.gauss(0, 1)
            price *= math.exp((mu - 0.5 * sigma * sigma) * dt + sigma * math.sqrt(dt) * z)
            price = max(1.0, price)
            volume = max(1000, int(rng.lognormvariate(2.0, 1.0)))
            series.append({"date": date.date(), "close": price, "volume": volume})
            date += timedelta(days=1)

        self._price_cache[symbol] = series
        return series

    def advance_date(self, days: int = 30) -> None:
        self.current_date += timedelta(days=days)

    async def fetch_quote(self, symbol: str) -> Quote:
        series = self._generate_series(symbol)
        # find closest <= current_date
        chosen = None
        for bar in series:
            if bar["date"] <= self.current_date.date():
                chosen = bar
        if not chosen:
            return Quote(symbol=symbol, price=0.0, volume=0.0)
        return Quote(symbol=symbol, price=chosen["close"], volume=float(chosen["volume"]))

    async def fetch_historical(self, symbol: str, days: int = 60) -> List[float]:
        series = self._generate_series(symbol)
        cutoff = self.current_date.date() - timedelta(days=days)
        prices = [bar["close"] for bar in series if cutoff <= bar["date"] <= self.current_date.date()]
        return prices[-days:] if prices else []

    async def fetch_volume_history(self, symbol: str, days: int = 20) -> List[float]:
        series = self._generate_series(symbol)
        cutoff = self.current_date.date() - timedelta(days=days)
        volumes = [float(bar["volume"]) for bar in series if cutoff <= bar["date"] <= self.current_date.date()]
        return volumes[-days:] if volumes else []

    async def place_order(self, symbol: str, qty: float, side: str, limit_price: Optional[float] = None) -> OrderResult:
        quote = await self.fetch_quote(symbol)
        if not quote.price or quote.price <= 0:
            return OrderResult(symbol=symbol, qty=0, side=side, price=0.0)
        fill_price = limit_price if limit_price else quote.price
        slippage = 0.001
        if side.lower() == "buy":
            fill_price *= (1 + slippage)
            cost = fill_price * qty
            if cost > self.cash:
                qty = self.cash / fill_price
                cost = fill_price * qty
            if qty > 0:
                self.cash -= cost
                if symbol in self.positions:
                    pos = self.positions[symbol]
                    new_qty = pos.qty + qty
                    new_avg = (pos.avg_price * pos.qty + fill_price * qty) / new_qty
                    self.positions[symbol] = Position(symbol=symbol, qty=new_qty, avg_price=new_avg)
                else:
                    self.positions[symbol] = Position(symbol=symbol, qty=qty, avg_price=fill_price)
                self.trade_history.append({
                    "date": self.current_date,
                    "symbol": symbol,
                    "side": "buy",
                    "qty": qty,
                    "price": fill_price,
                    "value": cost,
                })
        else:
            fill_price *= (1 - slippage)
            if symbol not in self.positions:
                return OrderResult(symbol=symbol, qty=0, side=side, price=0.0)
            pos = self.positions[symbol]
            qty = min(qty, pos.qty)
            if qty > 0:
                proceeds = fill_price * qty
                self.cash += proceeds
                remaining_qty = pos.qty - qty
                if remaining_qty > 0:
                    self.positions[symbol] = Position(symbol=symbol, qty=remaining_qty, avg_price=pos.avg_price)
                else:
                    del self.positions[symbol]
                self.trade_history.append({
                    "date": self.current_date,
                    "symbol": symbol,
                    "side": "sell",
                    "qty": qty,
                    "price": fill_price,
                    "value": proceeds,
                    "pnl": (fill_price - pos.avg_price) * qty,
                })
        return OrderResult(symbol=symbol, qty=qty, side=side, price=fill_price)

    async def list_positions(self) -> List[Position]:
        return list(self.positions.values())

    async def close_position(self, symbol: str, qty: Optional[float] = None) -> OrderResult:
        if symbol not in self.positions:
            return OrderResult(symbol=symbol, qty=0, side="sell", price=0.0)
        pos = self.positions[symbol]
        qty_to_sell = qty if qty is not None else pos.qty
        return await self.place_order(symbol, qty_to_sell, side="sell")

    async def get_portfolio_value(self) -> float:
        total = self.cash
        for symbol, pos in self.positions.items():
            quote = await self.fetch_quote(symbol)
            if quote.price > 0:
                total += quote.price * pos.qty
        return total

    def record_portfolio_snapshot(self) -> None:
        self.portfolio_history.append({
            "date": self.current_date,
            "cash": self.cash,
            "positions": dict(self.positions),
        })
