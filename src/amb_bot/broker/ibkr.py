import asyncio
from typing import List, Optional

import ib_insync as ib

from .base import BrokerClient, OrderResult, Position, Quote


class IBKRClient(BrokerClient):
    """Interactive Brokers client using ib_insync."""

    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1) -> None:
        """
        Args:
            host: TWS/IB Gateway host (default localhost)
            port: 7497 for TWS paper, 7496 for TWS live, 4002 for Gateway paper, 4001 for Gateway live
            client_id: Unique client ID for this connection
        """
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib_client = ib.IB()

    async def connect(self) -> None:
        """Establish connection to TWS/Gateway. Call before any operations."""
        if not self.ib_client.isConnected():
            await self.ib_client.connectAsync(self.host, self.port, clientId=self.client_id)

    async def disconnect(self) -> None:
        """Close connection."""
        if self.ib_client.isConnected():
            self.ib_client.disconnect()

    async def fetch_quote(self, symbol: str) -> Quote:
        """Fetch latest market price for a symbol."""
        await self.connect()
        contract = ib.Stock(symbol, "SMART", "USD")
        await self.ib_client.qualifyContractsAsync(contract)
        ticker = self.ib_client.reqMktData(contract, "", False, False)
        await asyncio.sleep(2)  # Wait for market data
        self.ib_client.cancelMktData(contract)
        
        price = ticker.marketPrice()
        if price != price:  # NaN check
            price = ticker.close if ticker.close == ticker.close else 0.0
        
        volume = ticker.volume if ticker.volume == ticker.volume else 0.0
        
        return Quote(symbol=symbol, price=price, volume=volume)

    async def fetch_historical(self, symbol: str, days: int = 60) -> List[float]:
        """Fetch historical daily closing prices."""
        await self.connect()
        contract = ib.Stock(symbol, "SMART", "USD")
        await self.ib_client.qualifyContractsAsync(contract)
        
        bars = await self.ib_client.reqHistoricalDataAsync(
            contract,
            endDateTime='',
            durationStr=f'{days} D',
            barSizeSetting='1 day',
            whatToShow='TRADES',
            useRTH=True,
            formatDate=1
        )
        
        return [bar.close for bar in bars]

    async def fetch_volume_history(self, symbol: str, days: int = 20) -> List[float]:
        """Fetch historical volume data."""
        await self.connect()
        contract = ib.Stock(symbol, "SMART", "USD")
        await self.ib_client.qualifyContractsAsync(contract)
        
        bars = await self.ib_client.reqHistoricalDataAsync(
            contract,
            endDateTime='',
            durationStr=f'{days} D',
            barSizeSetting='1 day',
            whatToShow='TRADES',
            useRTH=True,
            formatDate=1
        )
        
        return [float(bar.volume) for bar in bars]

    async def place_order(self, symbol: str, qty: float, side: str, limit_price: Optional[float] = None) -> OrderResult:
        """Place market or limit order."""
        await self.connect()
        contract = ib.Stock(symbol, "SMART", "USD")
        await self.ib_client.qualifyContractsAsync(contract)
        
        action = "BUY" if side.lower() == "buy" else "SELL"
        
        if limit_price:
            order = ib.LimitOrder(action, qty, limit_price)
        else:
            order = ib.MarketOrder(action, qty)
        
        trade = self.ib_client.placeOrder(contract, order)
        await asyncio.sleep(2)  # Wait for fill
        
        fill_price = trade.orderStatus.avgFillPrice if trade.fills else 0.0
        filled_qty = sum(fill.execution.shares for fill in trade.fills) if trade.fills else 0.0
        
        return OrderResult(symbol=symbol, qty=filled_qty, side=side, price=fill_price)

    async def list_positions(self) -> List[Position]:
        """List all open positions."""
        await self.connect()
        positions = self.ib_client.positions()
        
        result: List[Position] = []
        for pos in positions:
            if isinstance(pos.contract, ib.Stock):
                result.append(Position(
                    symbol=pos.contract.symbol,
                    qty=abs(pos.position),
                    avg_price=pos.avgCost / abs(pos.position) if pos.position else 0.0
                ))
        
        return result

    async def close_position(self, symbol: str, qty: Optional[float] = None) -> OrderResult:
        """Close position (full or partial)."""
        await self.connect()
        positions = await self.list_positions()
        
        target_pos = next((p for p in positions if p.symbol == symbol), None)
        if not target_pos:
            return OrderResult(symbol=symbol, qty=0, side="sell", price=0.0)
        
        qty_to_sell = qty if qty is not None else target_pos.qty
        return await self.place_order(symbol, qty_to_sell, side="sell")
