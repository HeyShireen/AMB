"""
AMB DCA Bot - Simplified CLI for IBKR paper trading and testing.

Simple commands:
  amb-bot once       : Run single DCA + exit check (for cron jobs)
  amb-bot simulate N : Run N monthly cycles with IBKR paper
  amb-bot monitor    : Live monitoring with real-time P&L and positions
"""
import asyncio
import logging
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from .broker.base import BrokerClient
from .config import get_settings
from .strategy_clean import Strategy
from .budget import BudgetTracker, Trade

app = typer.Typer(help="AMB DCA Bot - Monthly DCA with 10% SL / 15% TP")
console = Console()


def get_broker(settings) -> BrokerClient:
    """Factory to create IBKR broker client."""
    from .broker.ibkr import IBKRClient
    return IBKRClient(
        host=settings.ibkr_host,
        port=settings.ibkr_port,
        client_id=settings.ibkr_client_id
    )


async def run_once() -> None:
    """Execute a single DCA cycle with exit checks."""
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    broker = get_broker(settings)
    strategy = Strategy(settings)

    # Connect if IBKR
    if hasattr(broker, 'connect'):
        await broker.connect()

    try:
        # Execute strategy (exits + entries)
        results = await strategy.execute(broker)

        # Display summary
        if results:
            console.print("\n[green]✅ Trades Executed:[/green]")
            table = Table(title="Order Summary")
            table.add_column("Symbol", style="cyan")
            table.add_column("Side", style="magenta")
            table.add_column("Qty", style="yellow")
            table.add_column("Price", style="green")

            for res in results:
                table.add_row(res.symbol, res.side.upper(), f"{res.qty:.4f}", f"${res.price:.2f}")

            console.print(table)
        else:
            console.print("[yellow]ℹ️  No actions taken.[/yellow]")

    finally:
        # Disconnect if IBKR
        if hasattr(broker, 'disconnect'):
            await broker.disconnect()


async def run_simulate(cycles: int) -> None:
    """Run N monthly simulation cycles with paper broker."""
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    console.print(f"\n[cyan]🚀 Running {cycles} simulation cycles with paper broker...[/cyan]\n")

    strategy = Strategy(settings)
    budget_tracker = BudgetTracker(settings.monthly_budget)
    total_trades = 0

    for cycle in range(1, cycles + 1):
        console.print(f"\n[yellow]{'='*60}[/yellow]")
        console.print(f"[yellow]📆 Cycle {cycle}/{cycles} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/yellow]")
        console.print(f"[yellow]{'='*60}[/yellow]")

        broker = get_broker(settings)
        
        # Connect if IBKR
        if hasattr(broker, 'connect'):
            await broker.connect()

        try:
            # Execute strategy
            results = await strategy.execute(broker)
            total_trades += len(results)

            # Track trades in budget
            for res in results:
                trade = Trade(
                    timestamp=datetime.now().isoformat(),
                    symbol=res.symbol,
                    side=res.side,
                    qty=res.qty,
                    price=res.price,
                    amount=res.qty * res.price,
                    type="dca_entry" if res.side == "buy" else "dca_exit"
                )
                budget_tracker.record_trade(trade)

            # Show cycle summary
            summary = budget_tracker.get_month_summary()
            table = Table(title=f"Cycle {cycle} Summary")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="magenta")

            table.add_row("Budget", f"{summary['budget']:.2f}€")
            table.add_row("Spent", f"{summary['spent']:.2f}€")
            table.add_row("Remaining", f"{summary['remaining']:.2f}€")
            table.add_row("Trades", str(summary['trades_count']))
            table.add_row("Buys", str(summary['buys']))
            table.add_row("Sells", str(summary['sells']))

            console.print(table)

        finally:
            # Disconnect if IBKR
            if hasattr(broker, 'disconnect'):
                await broker.disconnect()

        # Reset budget for next cycle
        budget_tracker.reset_month()

    # Final summary
    console.print(f"\n[cyan]{'='*60}[/cyan]")
    console.print(f"[green]✅ Simulation complete![/green]")
    console.print(f"[cyan]   Total trades: {total_trades}[/cyan]")
    console.print(f"[cyan]{'='*60}[/cyan]\n")


@app.command()
def once() -> None:
    """Run a single DCA + risk pass (one-time execution, ideal for cron)."""
    asyncio.run(run_once())


@app.command()
def simulate(cycles: int = typer.Option(6, "--cycles", "-c", help="Number of monthly cycles")) -> None:
    """Simulate N monthly cycles with paper broker (faster than backtest)."""
    asyncio.run(run_simulate(cycles))


@app.command()
def status() -> None:
    """Show current budget status and trade history."""
    settings = get_settings()
    budget_tracker = BudgetTracker(settings.monthly_budget)
    summary = budget_tracker.get_month_summary()

    table = Table(title=f"📊 Budget Status - {summary['month']}")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")

    table.add_row("Monthly Budget", f"{summary['budget']:.2f}€")
    table.add_row("Spent", f"{summary['spent']:.2f}€")
    table.add_row("Remaining", f"{summary['remaining']:.2f}€")
    table.add_row("Usage", f"{(summary['spent']/summary['budget']*100):.1f}%")
    table.add_row("", "")
    table.add_row("Total Trades", str(summary['trades_count']))
    table.add_row("Buys", str(summary['buys']))
    table.add_row("Sells", str(summary['sells']))
    table.add_row("Total Bought", f"{summary['total_bought']:.2f}€")
    table.add_row("Total Sold", f"{summary['total_sold']:.2f}€")

    console.print(table)


@app.command()
def monitor(
    refresh: int = typer.Option(5, "--refresh", "-r", help="Refresh interval in seconds")
) -> None:
    """Live monitoring with real-time P&L and positions."""
    async def _monitor():
        from .monitor import LiveMonitor
        
        settings = get_settings()
        logging.basicConfig(
            level=logging.WARNING,  # Reduce noise in monitor
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        broker = get_broker(settings)
        monitor_instance = LiveMonitor(broker, settings)
        
        console.print("[cyan]🔄 Starting live monitor...[/cyan]")
        console.print(f"[dim]Refreshing every {refresh} seconds. Press Ctrl+C to stop.[/dim]\n")
        
        await monitor_instance.run(refresh_interval=refresh)
    
    asyncio.run(_monitor())


if __name__ == "__main__":
    app()
