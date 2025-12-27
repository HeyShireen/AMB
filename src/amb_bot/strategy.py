"""Simplified DCA Strategy with 10% Stop-Loss and 15% Take-Profit."""
import logging
from typing import Dict, List

from .broker.base import BrokerClient, OrderResult, Position
from .config import Settings

logger = logging.getLogger(__name__)


class Decision:
    """Trade decision representation."""
    def __init__(self, action: str, symbol: str, qty: float, reason: str = ""):
        self.action = action
        self.symbol = symbol
        self.qty = qty
        self.reason = reason


class Strategy:
    """Simple DCA strategy with stop-loss and take-profit."""
    
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.highest_prices: Dict[str, float] = {}  # Track peak price for trailing stop

    async def plan_exits(self, broker: BrokerClient) -> List[Decision]:
        """
        Exit positions based on:
        - Stop-loss at 10% loss
        - Take-profit at 15% gain
        """
        decisions: List[Decision] = []
        positions = await broker.list_positions()

        for pos in positions:
            quote = await broker.fetch_quote(pos.symbol)
            price = quote.price
            if price <= 0:
                continue

            # Calculate P&L percentage
            pnl_pct = (price - pos.avg_price) / pos.avg_price if pos.avg_price > 0 else 0
            
            # Update highest price for reference
            if pos.symbol not in self.highest_prices:
                self.highest_prices[pos.symbol] = max(pos.avg_price, price)
            elif price > self.highest_prices[pos.symbol]:
                self.highest_prices[pos.symbol] = price

            # Stop-loss: exit if down 10%
            if pnl_pct <= -self.settings.stop_loss_pct:
                logger.info(f"🛑 Stop-loss for {pos.symbol}: P&L={pnl_pct*100:.1f}%")
                decisions.append(Decision(
                    action="sell",
                    symbol=pos.symbol,
                    qty=pos.qty,
                    reason=f"stop_loss (P&L: {pnl_pct*100:.1f}%)"
                ))
                self.highest_prices.pop(pos.symbol, None)
                continue

            # Take-profit: exit if up 15%
            if pnl_pct >= self.settings.take_profit_pct:
                logger.info(f"✅ Take-profit for {pos.symbol}: P&L={pnl_pct*100:.1f}%")
                decisions.append(Decision(
                    action="sell",
                    symbol=pos.symbol,
                    qty=pos.qty,
                    reason=f"take_profit (P&L: {pnl_pct*100:.1f}%)"
                ))
                self.highest_prices.pop(pos.symbol, None)
                continue

        return decisions

    async def plan_entries(self, broker: BrokerClient, budget_available: float) -> List[Decision]:
        """
        Simple DCA: allocate monthly budget equally across universe.
        
        For each symbol, buy an equal share of the monthly allocation.
        """
        decisions: List[Decision] = []

        if budget_available < 50:
            logger.info(f"⏭️  Insufficient budget: {budget_available:.2f}€")
            return decisions

        universe = self.settings.universe
        if not universe:
            logger.warning("❌ Empty universe - no symbols to trade")
            return decisions

        # Equal allocation: split budget across universe
        per_symbol_budget = budget_available / len(universe)
        logger.info(f"💰 DCA: {budget_available:.2f}€ → {len(universe)} symbols × {per_symbol_budget:.2f}€ each")

        for symbol in universe:
            try:
                quote = await broker.fetch_quote(symbol)
                if not quote.price or quote.price <= 0:
                    logger.warning(f"⚠️  Skipping {symbol}: invalid price {quote.price}")
                    continue

                # Calculate quantity to buy
                qty = per_symbol_budget / quote.price
                qty = round(qty, 4)

                if qty <= 0 or qty * quote.price < 10:
                    logger.debug(f"⏭️  {symbol}: allocation too small ({qty * quote.price:.2f}€)")
                    continue

                decisions.append(Decision(
                    action="buy",
                    symbol=symbol,
                    qty=qty,
                    reason=f"monthly_dca ({per_symbol_budget:.2f}€ / {quote.price:.2f}$)"
                ))
                logger.info(f"📈 DCA buy {symbol}: {qty:.4f} @ ${quote.price:.2f}")

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue

        return decisions

    async def execute(self, broker: BrokerClient) -> List[OrderResult]:
        """
        Execute strategy:
        1. Plan and execute exits (stop-loss / take-profit)
        2. Plan and execute entries (DCA)
        """
        results: List[OrderResult] = []
        logger.info("=" * 60)
        logger.info("🚀 Executing DCA strategy")
        logger.info("=" * 60)

        # Phase 1: Exits
        logger.info("\n📉 Phase 1: Processing exits (stop-loss / take-profit)...")
        exits = await self.plan_exits(broker)
        for dec in exits:
            try:
                result = await broker.place_order(dec.symbol, dec.qty, side="sell")
                if result.qty > 0:
                    logger.info(f"   ✓ Sold {result.qty:.4f} {dec.symbol} @ ${result.price:.2f}")
                    results.append(result)
            except Exception as e:
                logger.error(f"   ✗ Failed to sell {dec.symbol}: {e}")

        if not exits:
            logger.info("   ✓ No exits needed")

        # Phase 2: Entries (DCA)
        logger.info("\n📈 Phase 2: Processing entries (DCA)...")
        
        # Get available budget
        portfolio = await broker.get_portfolio()
        budget_available = portfolio.cash if hasattr(portfolio, 'cash') else self.settings.monthly_budget
        logger.info(f"   Available budget: {budget_available:.2f}€")

        entries = await self.plan_entries(broker, budget_available)
        for dec in entries:
            try:
                result = await broker.place_order(dec.symbol, dec.qty, side="buy")
                if result.qty > 0:
                    logger.info(f"   ✓ Bought {result.qty:.4f} {dec.symbol} @ ${result.price:.2f}")
                    results.append(result)
            except Exception as e:
                logger.error(f"   ✗ Failed to buy {dec.symbol}: {e}")

        if not entries:
            logger.info("   ✓ No entries needed")

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ Execution complete: {len(results)} trades executed")
        logger.info("=" * 60)

        return results
