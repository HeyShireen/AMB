"""Live monitoring interface for AMB Bot."""
import asyncio
import logging
from datetime import datetime
from typing import List

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .broker.base import BrokerClient, Position
from .config import Settings

logger = logging.getLogger(__name__)


class LiveMonitor:
    """Real-time portfolio monitor with Rich."""
    
    def __init__(self, broker: BrokerClient, settings: Settings):
        self.broker = broker
        self.settings = settings
        self.console = Console()
        self.running = False
    
    def _make_header(self) -> Panel:
        """Create header panel with status."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = Text()
        text.append("🤖 AMB Bot Live Monitor", style="bold cyan")
        text.append(f"\n{now}", style="dim")
        text.append(f"\nBroker: IBKR | Port: {self.settings.ibkr_port}", style="yellow")
        
        return Panel(text, style="cyan", border_style="bold")
    
    def _make_positions_table(self, positions: List[Position], quotes: dict) -> Table:
        """Create positions table with P&L and exit levels."""
        table = Table(title="📊 Open Positions", show_header=True, header_style="bold magenta")
        table.add_column("Symbol", style="cyan", width=10)
        table.add_column("Qty", justify="right", style="white", width=10)
        table.add_column("Avg Price", justify="right", style="white", width=12)
        table.add_column("Current", justify="right", style="white", width=12)
        table.add_column("P&L %", justify="right", width=10)
        table.add_column("Stop -10%", justify="right", style="red", width=12)
        table.add_column("Target +15%", justify="right", style="green", width=12)
        
        if not positions:
            table.add_row("No positions", "", "", "", "", "", "")
            return table
        
        for pos in positions:
            quote = quotes.get(pos.symbol)
            if not quote:
                continue
            
            current_price = quote.price
            pnl_pct = ((current_price - pos.avg_price) / pos.avg_price * 100) if pos.avg_price > 0 else 0
            
            # Calculate exit levels
            stop_loss = pos.avg_price * (1 - self.settings.stop_loss_pct)
            take_profit = pos.avg_price * (1 + self.settings.take_profit_pct)
            
            # Color P&L
            pnl_style = "green" if pnl_pct >= 0 else "red"
            pnl_text = f"{pnl_pct:+.2f}%"
            
            # Highlight if close to exits
            stop_style = "bold red" if current_price <= stop_loss * 1.02 else "red"
            tp_style = "bold green" if current_price >= take_profit * 0.98 else "green"
            
            table.add_row(
                pos.symbol,
                f"{pos.qty:.4f}",
                f"${pos.avg_price:.2f}",
                f"${current_price:.2f}",
                Text(pnl_text, style=pnl_style),
                Text(f"${stop_loss:.2f}", style=stop_style),
                Text(f"${take_profit:.2f}", style=tp_style)
            )
        
        return table
    
    def _make_summary(self, positions: List[Position], quotes: dict) -> Panel:
        """Create portfolio summary panel."""
        total_value = 0.0
        total_cost = 0.0
        
        for pos in positions:
            quote = quotes.get(pos.symbol)
            if quote:
                total_value += pos.qty * quote.price
                total_cost += pos.qty * pos.avg_price
        
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        
        # Build summary text
        summary = Text()
        summary.append("Portfolio Value: ", style="white")
        summary.append(f"${total_value:,.2f}\n", style="bold cyan")
        
        summary.append("Total Cost: ", style="white")
        summary.append(f"${total_cost:,.2f}\n", style="white")
        
        summary.append("Total P&L: ", style="white")
        pnl_style = "bold green" if total_pnl >= 0 else "bold red"
        summary.append(f"${total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)\n", style=pnl_style)
        
        summary.append("Positions: ", style="white")
        summary.append(f"{len(positions)}", style="yellow")
        
        return Panel(summary, title="💰 Summary", border_style="green")
    
    def _make_config_panel(self) -> Panel:
        """Create configuration panel."""
        config = Text()
        config.append(f"Universe: ", style="white")
        config.append(f"{', '.join(self.settings.universe[:5])}", style="cyan")
        if len(self.settings.universe) > 5:
            config.append(f" +{len(self.settings.universe)-5} more", style="dim")
        config.append(f"\n\nMonthly Budget: ", style="white")
        config.append(f"{self.settings.monthly_budget:.0f}€\n", style="yellow")
        config.append(f"Stop-Loss: ", style="white")
        config.append(f"-{self.settings.stop_loss_pct*100:.0f}%\n", style="red")
        config.append(f"Take-Profit: ", style="white")
        config.append(f"+{self.settings.take_profit_pct*100:.0f}%", style="green")
        
        return Panel(config, title="⚙️  Config", border_style="blue")
    
    def _make_layout(self, positions: List[Position], quotes: dict) -> Layout:
        """Create main layout."""
        layout = Layout()
        
        layout.split_column(
            Layout(self._make_header(), size=5),
            Layout(name="body"),
            Layout(name="footer", size=10)
        )
        
        layout["body"].split_row(
            Layout(self._make_positions_table(positions, quotes)),
            Layout(name="right", ratio=1)
        )
        
        layout["right"].split_column(
            Layout(self._make_summary(positions, quotes)),
            Layout(self._make_config_panel())
        )
        
        # Footer
        footer_text = Text()
        footer_text.append("Press ", style="dim")
        footer_text.append("Ctrl+C", style="bold yellow")
        footer_text.append(" to stop monitoring", style="dim")
        layout["footer"] = Panel(footer_text, style="dim")
        
        return layout
    
    async def _fetch_quotes(self, positions: List[Position]) -> dict:
        """Fetch current quotes for all positions."""
        quotes = {}
        for pos in positions:
            try:
                quote = await self.broker.fetch_quote(pos.symbol)
                quotes[pos.symbol] = quote
            except Exception as e:
                logger.error(f"Failed to fetch quote for {pos.symbol}: {e}")
        return quotes
    
    async def run(self, refresh_interval: int = 5):
        """Run live monitor with auto-refresh."""
        self.running = True
        
        # Connect to broker
        if hasattr(self.broker, 'connect'):
            await self.broker.connect()
        
        try:
            with Live(console=self.console, refresh_per_second=0.5, screen=True) as live:
                while self.running:
                    try:
                        # Fetch current positions
                        positions = await self.broker.list_positions()
                        
                        # Fetch quotes
                        quotes = await self._fetch_quotes(positions)
                        
                        # Update display
                        layout = self._make_layout(positions, quotes)
                        live.update(layout)
                        
                        # Wait before next refresh
                        await asyncio.sleep(refresh_interval)
                    
                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        logger.error(f"Monitor error: {e}")
                        await asyncio.sleep(refresh_interval)
        
        finally:
            # Disconnect
            if hasattr(self.broker, 'disconnect'):
                await self.broker.disconnect()
            
            self.console.print("\n[yellow]Monitoring stopped.[/yellow]")
