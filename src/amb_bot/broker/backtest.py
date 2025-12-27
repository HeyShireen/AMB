"""Backtesting broker for historical simulation."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import ib_insync as ib
import logging

# Prevent IB.__del__ from calling disconnect on a closed asyncio loop at shutdown
ib.IB.__del__ = lambda self: None

from .base import BrokerClient, OrderResult, Position, Quote


class BacktestBroker(BrokerClient):
    """Broker for backtesting with historical data."""

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        initial_cash: float = 10000.0,
        ibkr_host: str = "127.0.0.1",
        ibkr_port: int = 4002,
    ) -> None:
        """
        Args:
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_cash: Starting cash balance
            ibkr_host: IBKR host for historical data
            ibkr_port: IBKR port for historical data
        """
        self.start_date = start_date
        self.end_date = end_date
        self.current_date = start_date
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Dict] = []
        self.portfolio_history: List[Dict] = []
        self.logger = logging.getLogger(__name__)
        
        # IBKR connection for historical data
        self.ibkr_host = ibkr_host
        self.ibkr_port = ibkr_port
        self.ib_client = ib.IB()
        # Avoid IB.__del__ calling disconnect on a closed event loop at interpreter shutdown
        self.ib_client.__del__ = lambda: None
        self._historical_cache: Dict[str, List] = {}

    async def connect(self) -> None:
        """Connect to IBKR for historical data."""
        if not self.ib_client.isConnected():
            await self.ib_client.connectAsync(self.ibkr_host, self.ibkr_port, clientId=99)

    async def disconnect(self) -> None:
        """Disconnect from IBKR."""
        if self.ib_client.isConnected():
            self.ib_client.disconnect()

    def advance_date(self, days: int = 30) -> None:
        """Advance simulation date by N days."""
        self.current_date += timedelta(days=days)

    async def _fetch_bars_for_symbol(self, symbol: str) -> tuple[str, List]:
        """Fetch bars for a single symbol (helper for parallelization)."""
        await self.connect()
        
        # Contract mapping for IBKR historical
        if symbol.endswith(".PA"):
            base = symbol.replace(".PA", "")
            contract = ib.Stock(base, "SMART", "EUR", primaryExchange="SBF")
        else:
            contract = ib.Stock(symbol, "SMART", "USD", primaryExchange="NASDAQ")

        try:
            await self.ib_client.qualifyContractsAsync(contract)
        except Exception as exc:
            self.logger.warning(f"Contract qualify failed for {symbol}: {exc}")
            return symbol, []
        
        # Fetch historical data - request up to full window (capped to 3 years to respect IB limits)
        days_total = min((self.end_date - self.start_date).days + 60, 365 * 3)
        duration_str = f"{days_total} D" if days_total < 365 else "3 Y"
        
        try:
            # Pull full window up to simulation end to avoid stale caches when current_date advances
            bars = await self.ib_client.reqHistoricalDataAsync(
                contract,
                endDateTime=self.end_date.strftime("%Y%m%d %H:%M:%S"),
                durationStr=duration_str,
                barSizeSetting="1 day",
                whatToShow="TRADES",
                useRTH=False,
                formatDate=1,
            )
            if not bars:
                self.logger.warning(f"No historical bars for {symbol} ({contract})")
            return symbol, bars if bars else []
        except Exception as e:
            self.logger.warning(f"Failed to fetch bars for {symbol}: {e}")
            return symbol, []

    async def fetch_quote(self, symbol: str) -> Quote:
        """Fetch historical price for current simulation date."""
        await self.connect()
        
        # Get historical data if not cached
        if symbol not in self._historical_cache:
            symbol, bars = await self._fetch_bars_for_symbol(symbol)
            self._historical_cache[symbol] = bars
        
        # Find price for current_date
        bars = self._historical_cache.get(symbol, [])
        for bar in bars:
            # bar.date can be either a string or date object
            if isinstance(bar.date, str):
                bar_date_obj = datetime.strptime(bar.date, "%Y%m%d").date()
            else:
                bar_date_obj = bar.date if isinstance(bar.date, type(self.current_date.date())) else bar.date.date()
            
            if bar_date_obj == self.current_date.date():
                return Quote(symbol=symbol, price=bar.close, volume=bar.volume)
        
        # If exact date not found, use closest previous date
        closest_bar = None
        for bar in bars:
            # bar.date can be either a string or date object
            if isinstance(bar.date, str):
                bar_date_obj = datetime.strptime(bar.date, "%Y%m%d").date()
            else:
                bar_date_obj = bar.date if isinstance(bar.date, type(self.current_date.date())) else bar.date.date()
            
            if bar_date_obj <= self.current_date.date():
                closest_bar = bar
        
        if closest_bar:
            return Quote(symbol=symbol, price=closest_bar.close, volume=closest_bar.volume)
        
        return Quote(symbol=symbol, price=0.0, volume=0.0)

    async def fetch_historical(self, symbol: str, days: int = 60) -> List[float]:
        """Fetch historical prices relative to current simulation date."""
        await self.connect()
        
        if symbol not in self._historical_cache:
            await self.fetch_quote(symbol)  # Populate cache
        
        bars = self._historical_cache.get(symbol, [])
        
        # Get prices for the last N days before current_date
        prices = []
        cutoff_date = self.current_date - timedelta(days=days)
        
        for bar in bars:
            # bar.date can be either a string or date object
            if isinstance(bar.date, str):
                bar_date_obj = datetime.strptime(bar.date, "%Y%m%d").date()
            else:
                bar_date_obj = bar.date if isinstance(bar.date, type(self.current_date.date())) else bar.date.date()
            
            if cutoff_date.date() <= bar_date_obj <= self.current_date.date():
                prices.append(bar.close)
        
        return prices[-days:] if prices else []

    async def fetch_volume_history(self, symbol: str, days: int = 20) -> List[float]:
        """Fetch historical volume relative to current simulation date."""
        await self.connect()
        
        if symbol not in self._historical_cache:
            await self.fetch_quote(symbol)  # Populate cache
        
        bars = self._historical_cache.get(symbol, [])
        
        # Get volumes for the last N days before current_date
        volumes = []
        cutoff_date = self.current_date - timedelta(days=days)
        
        for bar in bars:
            # bar.date can be either a string or date object
            if isinstance(bar.date, str):
                bar_date_obj = datetime.strptime(bar.date, "%Y%m%d").date()
            else:
                bar_date_obj = bar.date if isinstance(bar.date, type(self.current_date.date())) else bar.date.date()
            
            if cutoff_date.date() <= bar_date_obj <= self.current_date.date():
                volumes.append(float(bar.volume))
        
        return volumes[-days:] if volumes else []

    async def place_order(
        self, symbol: str, qty: float, side: str, limit_price: Optional[float] = None
    ) -> OrderResult:
        """Simulate order execution at current date's price."""
        quote = await self.fetch_quote(symbol)
        
        if not quote.price or quote.price <= 0:
            return OrderResult(symbol=symbol, qty=0, side=side, price=0.0)
        
        # Use limit price if provided, otherwise market price
        fill_price = limit_price if limit_price else quote.price
        
        # Simulate slippage (0.1% worse fill)
        slippage = 0.001
        if side.lower() == "buy":
            fill_price *= (1 + slippage)
            cost = fill_price * qty
            
            # Apply commission: 0.05% with 3€ minimum
            commission = max(cost * 0.0005, 3.0)
            total_cost = cost + commission
            
            if total_cost > self.cash:
                # Insufficient funds - reduce qty
                qty = (self.cash - 3.0) / fill_price  # Reserve commission
                cost = fill_price * qty
                commission = max(cost * 0.0005, 3.0)
                total_cost = cost + commission
            
            if qty > 0:
                self.cash -= total_cost
                
                # Update or create position
                if symbol in self.positions:
                    pos = self.positions[symbol]
                    new_qty = pos.qty + qty
                    new_avg = (pos.avg_price * pos.qty + fill_price * qty) / new_qty
                    self.positions[symbol] = Position(symbol=symbol, qty=new_qty, avg_price=new_avg)
                else:
                    self.positions[symbol] = Position(symbol=symbol, qty=qty, avg_price=fill_price)
                
                # Record trade
                self.trade_history.append({
                    "date": self.current_date,
                    "symbol": symbol,
                    "side": "buy",
                    "qty": qty,
                    "price": fill_price,
                    "value": cost,
                })
        else:  # sell
            fill_price *= (1 - slippage)
            
            if symbol not in self.positions:
                return OrderResult(symbol=symbol, qty=0, side=side, price=0.0)
            
            pos = self.positions[symbol]
            qty = min(qty, pos.qty)
            
            if qty > 0:
                proceeds = fill_price * qty
                
                # Apply commission: 0.05% with 3€ minimum
                commission = max(proceeds * 0.0005, 3.0)
                net_proceeds = proceeds - commission
                
                self.cash += net_proceeds
                
                # Update position
                remaining_qty = pos.qty - qty
                if remaining_qty > 0:
                    self.positions[symbol] = Position(
                        symbol=symbol, qty=remaining_qty, avg_price=pos.avg_price
                    )
                else:
                    del self.positions[symbol]
                
                # Record trade
                self.trade_history.append({
                    "date": self.current_date,
                    "symbol": symbol,
                    "side": "sell",
                    "qty": qty,
                    "price": fill_price,
                    "value": proceeds,
                    "pnl": (fill_price - pos.avg_price) * qty - commission,
                })
        
        return OrderResult(symbol=symbol, qty=qty, side=side, price=fill_price)

    async def list_positions(self) -> List[Position]:
        """Return current simulated positions."""
        return list(self.positions.values())

    async def close_position(self, symbol: str, qty: Optional[float] = None) -> OrderResult:
        """Close position (full or partial)."""
        if symbol not in self.positions:
            return OrderResult(symbol=symbol, qty=0, side="sell", price=0.0)
        
        pos = self.positions[symbol]
        qty_to_sell = qty if qty is not None else pos.qty
        return await self.place_order(symbol, qty_to_sell, side="sell")

    async def get_portfolio_value(self) -> float:
        """Calculate total portfolio value (cash + positions)."""
        total = self.cash
        
        for symbol, pos in self.positions.items():
            quote = await self.fetch_quote(symbol)
            if quote.price > 0:
                total += quote.price * pos.qty
        
        return total

    async def preload_all_tickers(self, symbols: List[str]) -> None:
        """Preload historical data for all tickers in parallel."""
        self.logger.info(f"Preloading {len(symbols)} tickers...")
        tasks = [self._fetch_bars_for_symbol(sym) for sym in symbols]
        results: List[Tuple[str, List] | BaseException] = await asyncio.gather(*tasks, return_exceptions=True)

        missing: List[str] = []

        for item in results:
            if isinstance(item, Exception):
                self.logger.warning(f"Preload failed: {item}")
                continue
            if not isinstance(item, tuple) or len(item) != 2:
                self.logger.warning(f"Unexpected preload result: {item}")
                continue
            symbol, bars = item
            if not bars:
                missing.append(symbol)
            self._historical_cache[symbol] = bars

        self.missing_symbols = missing
        if missing:
            self.logger.warning(f"Missing historical data for {len(missing)} symbols: {', '.join(sorted(missing))}")
        self.logger.info(f"✅ Preloaded {len(self._historical_cache)} tickers")

    def record_portfolio_snapshot(self) -> None:
        """Record current portfolio state for performance tracking."""
        self.portfolio_history.append({
            "date": self.current_date,
            "cash": self.cash,
            "positions": dict(self.positions),
        })

    def has_data_on_or_before(self, symbol: str, date: datetime) -> bool:
        """Return True if we have at least one historical bar on or before the given date."""
        bars = self._historical_cache.get(symbol, [])
        if not bars:
            return False
        for bar in bars:
            if isinstance(bar.date, str):
                bar_date_obj = datetime.strptime(bar.date, "%Y%m%d").date()
            else:
                bar_date_obj = bar.date if isinstance(bar.date, type(self.current_date.date())) else bar.date.date()
            if bar_date_obj <= date.date():
                return True
        return False
