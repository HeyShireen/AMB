import random
from typing import Dict, List, Optional

from .base import BrokerClient, OrderResult, Position, Quote


class PaperBroker(BrokerClient):
    def __init__(self) -> None:
        self.positions: Dict[str, Position] = {}

    async def fetch_quote(self, symbol: str) -> Quote:
        price = round(random.uniform(50, 250), 2)
        volume = round(random.uniform(500000, 5000000), 0)  # Simulated volume
        return Quote(symbol=symbol, price=price, volume=volume)

    async def fetch_historical(self, symbol: str, days: int = 60) -> List[float]:
        """Generate fake historical prices with upward trend."""
        base = random.uniform(50, 200)
        prices = []
        for i in range(days):
            drift = i * 0.5  # Slight upward trend
            noise = random.uniform(-5, 5)
            prices.append(round(base + drift + noise, 2))
        return prices

    async def fetch_volume_history(self, symbol: str, days: int = 20) -> List[float]:
        """Generate fake historical volume."""
        base_volume = random.uniform(1000000, 3000000)
        return [round(base_volume * random.uniform(0.7, 1.3), 0) for _ in range(days)]

    async def place_order(self, symbol: str, qty: float, side: str, limit_price: Optional[float] = None) -> OrderResult:
        quote = await self.fetch_quote(symbol)
        
        # Simulate limit order rejection if price exceeds limit
        if limit_price and side.lower() == "buy" and quote.price > limit_price:
            return OrderResult(symbol=symbol, qty=0, side=side, price=0.0)  # Order not filled
        if limit_price and side.lower() == "sell" and quote.price < limit_price:
            return OrderResult(symbol=symbol, qty=0, side=side, price=0.0)  # Order not filled
        
        execution_price = limit_price if limit_price else quote.price
        
        if side.lower() == "buy":
            pos = self.positions.get(symbol)
            if pos:
                total_cost = pos.avg_price * pos.qty + execution_price * qty
                total_qty = pos.qty + qty
                new_avg = total_cost / total_qty
                self.positions[symbol] = Position(symbol=symbol, qty=total_qty, avg_price=new_avg)
            else:
                self.positions[symbol] = Position(symbol=symbol, qty=qty, avg_price=execution_price)
        else:
            pos = self.positions.get(symbol)
            if pos:
                remaining = max(pos.qty - qty, 0)
                if remaining == 0:
                    self.positions.pop(symbol, None)
                else:
                    self.positions[symbol] = Position(symbol=symbol, qty=remaining, avg_price=pos.avg_price)
        return OrderResult(symbol=symbol, qty=qty, side=side, price=execution_price)

    async def list_positions(self) -> List[Position]:
        return list(self.positions.values())

    async def close_position(self, symbol: str, qty: Optional[float] = None) -> OrderResult:
        pos = self.positions.get(symbol)
        if not pos:
            return OrderResult(symbol=symbol, qty=0, side="sell", price=0.0)
        qty_to_sell = pos.qty if qty is None else min(qty, pos.qty)
        return await self.place_order(symbol, qty_to_sell, side="sell")
