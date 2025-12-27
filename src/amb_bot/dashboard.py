"""Terminal UI Dashboard for AMB Bot monitoring."""
import json
from datetime import datetime
from pathlib import Path
from typing import List

from rich.console import Console
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn
from rich.table import Table
from textual.app import ComposeResult, RenderResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static
from textual.widget import Widget

from .budget import BudgetTracker


class StatusBar(Static):
    """Top status bar showing bot status and time."""
    
    status = reactive("IDLE")
    market_status = reactive("CLOSED")
    
    def render(self) -> str:
        status_icon = "🟢" if self.status == "RUNNING" else "🟡" if self.status == "IDLE" else "🔴"
        market_icon = "📈" if self.market_status == "OPEN" else "🌙"
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"{status_icon} {self.status:15} | {market_icon} {self.market_status:10} | {time_str}"


class BudgetWidget(Static):
    """Budget display with progress bar."""
    
    monthly_budget = reactive(200.0)
    spent = reactive(0.0)
    
    def render(self) -> RenderResult:
        remaining = max(0, self.monthly_budget - self.spent)
        percentage = (self.spent / self.monthly_budget * 100) if self.monthly_budget > 0 else 0
        
        # Progress bar
        bar_length = 30
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        content = f"""
┌─ BUDGET ({datetime.now().strftime('%B %Y')} ────────────────┐
│ Total:     {self.monthly_budget:8.2f}€                  │
│ Spent:     {self.spent:8.2f}€  [{bar}] {percentage:5.1f}%  │
│ Remaining: {remaining:8.2f}€                  │
└──────────────────────────────────────┘
"""
        return content


class PositionsWidget(Static):
    """Display open positions table."""
    
    positions = reactive({})
    
    def render(self) -> RenderResult:
        if not self.positions:
            return "📭 No open positions"
        
        table = Table(title="📊 OPEN POSITIONS")
        table.add_column("Symbol", style="cyan")
        table.add_column("Qty", justify="right", style="magenta")
        table.add_column("Avg Price", justify="right")
        table.add_column("Current", justify="right")
        table.add_column("P&L", justify="right")
        table.add_column("P&L %", justify="right")
        
        for symbol, pos in self.positions.items():
            qty = pos.get("qty", 0)
            avg_price = pos.get("avg_price", 0)
            current_price = pos.get("current_price", avg_price)
            pnl = (current_price - avg_price) * qty
            pnl_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
            
            pnl_color = "green" if pnl >= 0 else "red"
            pnl_str = f"[{pnl_color}]{pnl:+.2f}€[/{pnl_color}]"
            pnl_pct_str = f"[{pnl_color}]{pnl_pct:+.1f}%[/{pnl_color}]"
            
            table.add_row(
                symbol,
                f"{qty:.4f}",
                f"{avg_price:.2f}€",
                f"{current_price:.2f}€",
                pnl_str,
                pnl_pct_str
            )
        
        console = Console()
        with console.capture() as capture:
            console.print(table)
        return capture.getvalue()


class TradeHistoryWidget(Static):
    """Display recent trades."""
    
    trades = reactive([])
    
    def render(self) -> RenderResult:
        if not self.trades:
            return "📭 No recent trades"
        
        table = Table(title="📜 RECENT TRADES (Last 10)", max_width=60)
        table.add_column("Time", style="dim")
        table.add_column("Type", style="cyan")
        table.add_column("Symbol", style="magenta")
        table.add_column("Qty", justify="right")
        table.add_column("Price", justify="right")
        
        for trade in self.trades[-10:]:
            timestamp = trade.get("timestamp", "")
            if "T" in timestamp:
                timestamp = timestamp.split("T")[1][:5]  # HH:MM
            
            side = trade.get("side", "").upper()
            side_icon = "🟢" if side == "BUY" else "🔴"
            trade_type = trade.get("type", "")
            
            table.add_row(
                timestamp,
                f"{side_icon} {side}",
                trade.get("symbol", ""),
                f"{trade.get('qty', 0):.4f}",
                f"{trade.get('price', 0):.2f}€"
            )
        
        console = Console()
        with console.capture() as capture:
            console.print(table)
        return capture.getvalue()


class OpportunitiesWidget(Static):
    """Display pending opportunities."""
    
    opportunities = reactive([])
    
    def render(self) -> RenderResult:
        if not self.opportunities:
            return "⭐ Scanning for opportunities..."
        
        table = Table(title="🎯 DETECTED OPPORTUNITIES (Next 5)")
        table.add_column("Symbol", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Confidence", justify="right")
        table.add_column("Reason", no_wrap=True)
        
        for opp in self.opportunities[:5]:
            confidence = opp.get("confidence", 0) * 100
            confidence_bar = "█" * int(confidence / 10) + "░" * (10 - int(confidence / 10))
            
            table.add_row(
                opp.get("symbol", ""),
                opp.get("type", "").replace("_", " "),
                f"{confidence_bar} {confidence:.0f}%",
                opp.get("reason", "")[:40]
            )
        
        console = Console()
        with console.capture() as capture:
            console.print(table)
        return capture.getvalue()


class Dashboard(Widget):
    """Main dashboard container."""
    
    def compose(self) -> ComposeResult:
        yield StatusBar(id="status_bar")
        yield BudgetWidget(id="budget")
        yield PositionsWidget(id="positions")
        yield TradeHistoryWidget(id="history")
        yield OpportunitiesWidget(id="opportunities")
    
    def update_status(self, status: str, market_status: str = None) -> None:
        """Update status bar."""
        self.query_one(StatusBar).status = status
        if market_status:
            self.query_one(StatusBar).market_status = market_status
    
    def update_budget(self, budget_tracker: BudgetTracker) -> None:
        """Update budget display."""
        widget = self.query_one(BudgetWidget)
        widget.monthly_budget = budget_tracker.monthly_budget
        widget.spent = budget_tracker.monthly_spent
    
    def update_positions(self, positions: dict) -> None:
        """Update positions table."""
        self.query_one(PositionsWidget).positions = positions
    
    def update_trades(self, trades: List) -> None:
        """Update trade history."""
        self.query_one(TradeHistoryWidget).trades = trades
    
    def update_opportunities(self, opportunities: List) -> None:
        """Update opportunities display."""
        self.query_one(OpportunitiesWidget).opportunities = opportunities


def load_budget_data() -> dict:
    """Load latest budget data."""
    data_file = Path("data/budget_tracker.json")
    if data_file.exists():
        try:
            with data_file.open("r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def format_positions_from_budget(trades: List) -> dict:
    """Build positions dict from trade history."""
    positions = {}
    for trade in trades:
        symbol = trade.get("symbol", "")
        if symbol not in positions:
            positions[symbol] = {
                "qty": 0,
                "avg_price": 0,
                "total_cost": 0
            }
        
        side = trade.get("side", "").lower()
        qty = trade.get("qty", 0)
        price = trade.get("price", 0)
        
        if side == "buy":
            pos = positions[symbol]
            total_cost = pos["total_cost"] + qty * price
            total_qty = pos["qty"] + qty
            pos["total_cost"] = total_cost
            pos["qty"] = total_qty
            pos["avg_price"] = total_cost / total_qty if total_qty > 0 else 0
        elif side == "sell":
            pos = positions[symbol]
            pos["qty"] -= qty
    
    # Remove zero positions
    return {k: v for k, v in positions.items() if v["qty"] > 0}
