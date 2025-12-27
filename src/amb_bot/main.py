import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from .backtest_utils import calculate_performance_metrics, print_backtest_results
from .broker.base import BrokerClient
from .broker.paper import PaperBroker
from .budget import BudgetTracker, Trade
from .config import get_settings
from .indicators import calculate_sma
from .opportunities import scan_opportunities
from .strategy import Strategy

app = typer.Typer(help="AMB DCA bot - Continuous market monitoring")
console = Console()


def get_broker(settings) -> BrokerClient:
    """Factory to create broker client based on config."""
    if settings.broker_type.lower() == "ibkr":
        from .broker.ibkr import IBKRClient
        return IBKRClient(
            host=settings.ibkr_host,
            port=settings.ibkr_port,
            client_id=settings.ibkr_client_id
        )
    else:
        return PaperBroker()


def is_market_open(settings) -> bool:
    """Check if current time is within trading hours."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    return settings.trading_start_hour_utc <= hour < settings.trading_end_hour_utc


async def scan_and_trade(broker: BrokerClient, settings, budget_tracker: BudgetTracker) -> int:
    """Scan for opportunities and execute trades. Returns number of trades."""
    logger = logging.getLogger(__name__)
    trades_executed = 0
    
    available_budget = budget_tracker.get_available_budget()
    if available_budget < 10:
        logger.info("💤 Insufficient budget remaining this month")
        return 0
    
    logger.info(f"🔍 Scanning {len(settings.universe)} stocks for opportunities...")
    
    for symbol in settings.universe:
        try:
            # Fetch data
            quote = await broker.fetch_quote(symbol)
            prices = await broker.fetch_historical(symbol, days=60)
            volumes = await broker.fetch_volume_history(symbol, days=20)
            
            if len(prices) < 50:
                continue
            
            sma_20 = calculate_sma(prices, 20)
            sma_50 = calculate_sma(prices, 50)
            
            # Scan opportunities
            opportunities = scan_opportunities(
                symbol,
                quote.price,
                prices,
                volumes,
                sma_20,
                sma_50,
                available_budget
            )
            
            for opp in opportunities:
                if opp.confidence < settings.min_confidence:
                    continue
                
                if not budget_tracker.can_trade(opp.suggested_allocation):
                    logger.info(f"⏭️  Skipping {symbol} {opp.type}: insufficient budget")
                    continue
                
                # Execute trade
                qty = round(opp.suggested_allocation / quote.price, 4)
                limit_price = round(quote.price * (1 + settings.limit_order_buffer), 2)
                
                logger.info(f"🎯 Opportunity: {symbol} {opp.type} (confidence: {opp.confidence:.1%}) - {opp.reason}")
                
                result = await broker.place_order(
                    symbol,
                    qty,
                    side="buy",
                    limit_price=limit_price if settings.use_limit_orders else None
                )
                
                if result.qty > 0:
                    trade = Trade(
                        timestamp=datetime.now().isoformat(),
                        symbol=symbol,
                        side="buy",
                        qty=result.qty,
                        price=result.price,
                        amount=result.qty * result.price,
                        type=opp.type
                    )
                    budget_tracker.record_trade(trade)
                    trades_executed += 1
                    logger.info(f"✅ Executed {symbol} {opp.type}: {result.qty} @ {result.price}")
                else:
                    logger.warning(f"⚠️  {symbol} order not filled (limit not reached)")
                
                # Update available budget
                available_budget = budget_tracker.get_available_budget()
                if available_budget < 10:
                    logger.info("💤 Budget exhausted for this month")
                    return trades_executed
        
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
    
    return trades_executed


async def run_once() -> None:
    settings = get_settings()
    # Speed overrides to avoid long sleeps
    settings.time_slicing_enabled = False
    settings.time_slicing_delay_minutes = 0
    # Enable short-term strategy for simulator runs
    settings.short_term_mode_enabled = True
    logging.basicConfig(level=settings.log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    broker = get_broker(settings)
    
    # Connect if IBKR
    if hasattr(broker, 'connect'):
        await broker.connect()
    
    strategy = Strategy(settings)
    results = await strategy.execute(broker)
    
    # Disconnect if IBKR
    if hasattr(broker, 'disconnect'):
        await broker.disconnect()
    
    if not results:
        rprint("[yellow]No actions taken.[/yellow]")
        return
    rprint("[green]Orders executed:[/green]")
    for res in results:
        rprint(f"{res.side.upper()} {res.qty} {res.symbol} @ {res.price}")


async def run_continuous() -> None:
    """Run bot in continuous monitoring mode."""
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    broker = get_broker(settings)
    budget_tracker = BudgetTracker(settings.monthly_budget)
    strategy = Strategy(settings)
    
    # Connect if IBKR
    if hasattr(broker, 'connect'):
        await broker.connect()
    
    logger.info("🚀 Starting continuous monitoring mode")
    logger.info(f"📊 Check interval: {settings.check_interval_minutes} minutes")
    logger.info(f"⏰ Trading hours: {settings.trading_start_hour_utc:02d}:00 - {settings.trading_end_hour_utc:02d}:00 UTC")
    
    # Show budget status
    summary = budget_tracker.get_month_summary()
    logger.info(f"💰 Budget: {summary['spent']:.2f}€ / {summary['budget']:.2f}€ (remaining: {summary['remaining']:.2f}€)")
    
    iteration = 0
    try:
        while True:
            iteration += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"🔄 Scan #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Check if market is open
            if not is_market_open(settings):
                logger.info("🌙 Market closed - waiting...")
                await asyncio.sleep(settings.check_interval_minutes * 60)
                continue
            
            # Check for stop-loss / take-profit exits
            logger.info("📉 Checking existing positions for exits...")
            exit_results = []
            exits = await strategy.plan_exits(broker)
            for dec in exits:
                result = await broker.place_order(dec.symbol, dec.qty, side="sell")
                if result.qty > 0:
                    trade = Trade(
                        timestamp=datetime.now().isoformat(),
                        symbol=dec.symbol,
                        side="sell",
                        qty=result.qty,
                        price=result.price,
                        amount=result.qty * result.price,
                        type="stop_loss" if "stop" in dec.reason.lower() else "take_profit"
                    )
                    budget_tracker.record_trade(trade)
                    exit_results.append(result)
                    logger.info(f"🔴 Exit {dec.symbol}: {result.qty} @ {result.price} ({dec.reason})")
            
            # Scan for new opportunities
            trades = await scan_and_trade(broker, settings, budget_tracker)
            
            if trades == 0 and len(exit_results) == 0:
                logger.info("✨ No opportunities found")
            
            # Wait until next check
            logger.info(f"⏳ Sleeping for {settings.check_interval_minutes} minutes...")
            await asyncio.sleep(settings.check_interval_minutes * 60)
    
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down continuous mode...")
    finally:
        if hasattr(broker, 'disconnect'):
            await broker.disconnect()
        
        # Show final summary
        summary = budget_tracker.get_month_summary()
        table = Table(title=f"Month Summary: {summary['month']}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("Budget", f"{summary['budget']:.2f}€")
        table.add_row("Spent", f"{summary['spent']:.2f}€")
        table.add_row("Remaining", f"{summary['remaining']:.2f}€")
        table.add_row("Trades", str(summary['trades_count']))
        table.add_row("Buys", str(summary['buys']))
        table.add_row("Sells", str(summary['sells']))
        console.print(table)


@app.command()
def once() -> None:
    """Run a single DCA + risk pass (one-time execution)."""
    asyncio.run(run_once())


@app.command()
def watch() -> None:
    """Run in continuous monitoring mode (24/7 opportunity scanner)."""
    asyncio.run(run_continuous())


@app.command()
def simulate(cycles: int = 6) -> None:
    """Simulate N monthly cycles with the paper broker (faster than backtest)."""
    console.print(f"[cyan]🚀 Running {cycles} simulation cycles...[/cyan]\n")
    
    async def _loop() -> None:
        for i in range(1, cycles + 1):
            console.print(f"[yellow]📆 Cycle {i}/{cycles}[/yellow]")
            await run_once()
            console.print()
    
    asyncio.run(_loop())
    console.print(f"[green]✅ Simulation complete![/green]")


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
def dashboard() -> None:
    """Show interactive TUI dashboard for monitoring."""
    from .tui import AMBDashboardApp
    
    app = AMBDashboardApp()
    app.run_interactive()


@app.command()
def backtest(
    months: int = typer.Option(12, "--months", "-m", help="Number of months to backtest"),
    start_date: Optional[str] = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    initial_cash: float = typer.Option(10000.0, "--initial-cash", help="Initial cash balance"),
) -> None:
    """Run backtest on historical data."""
    asyncio.run(run_backtest(months, start_date, initial_cash))


async def run_backtest(months: int, start_date_str: Optional[str], initial_cash: float) -> None:
    """Execute backtest simulation."""
    from .broker.backtest import BacktestBroker
    
    settings = get_settings()
    # Disable time slicing in backtests to avoid long sleeps between batches
    settings.time_slicing_enabled = False
    settings.time_slicing_delay_minutes = 0
    settings.time_slicing_batches = 1
    
    # Determine date range
    if start_date_str:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    else:
        # Default: start N months ago
        start_date = datetime.now() - timedelta(days=months * 30)
    
    end_date = start_date + timedelta(days=months * 30)
    
    console.print(f"[cyan]🔙 Starting backtest from {start_date.date()} to {end_date.date()}[/cyan]")
    console.print(f"[cyan]💰 Initial capital: ${initial_cash:,.2f}[/cyan]")
    console.print(f"[cyan]📅 Monthly budget: ${settings.monthly_budget}[/cyan]\n")
    
    # Create backtest broker
    broker = BacktestBroker(
        start_date=start_date,
        end_date=end_date,
        initial_cash=initial_cash,
        ibkr_host=settings.ibkr_host,
        ibkr_port=settings.ibkr_port,
    )
    
    await broker.connect()
    console.print("[green]✅ Connected to IBKR for historical data[/green]")
    
    # Preload all tickers in parallel
    await broker.preload_all_tickers(settings.universe)
    # Filter universe to symbols that have data at the start date (skip pre-IPO)
    available_universe = [s for s in settings.universe if broker.has_data_on_or_before(s, start_date)]
    skipped = set(settings.universe) - set(available_universe)
    missing_preload = getattr(broker, "missing_symbols", [])
    if skipped:
        console.print(f"[red]⚠️ {len(skipped)} symboles sans données à la date de départ : {', '.join(sorted(skipped))}[/red]")
    if missing_preload:
        console.print(f"[red]⚠️ Données historiques manquantes lors du preload pour : {', '.join(sorted(missing_preload))}[/red]")
    settings.universe = available_universe
    console.print()
    
    strategy = Strategy(settings)
    
    # Run simulation month by month
    month_count = 0
    while broker.current_date < end_date:
        month_count += 1
        month_start = broker.current_date
        month_end = min(month_start + timedelta(days=30), end_date)
        console.print(f"[yellow]📆 Month {month_count}: {month_start.date()}[/yellow]")
        
        # Inject monthly DCA budget into cash before running the strategy
        broker.cash += settings.monthly_budget
        
        # Execute strategy for this month
        try:
            results = await strategy.execute(broker)
            
            if results:
                console.print(f"  [green]✅ Executed {len(results)} orders[/green]")
            else:
                console.print(f"  [dim]No trades this month[/dim]")
            
            # Record portfolio snapshot
            broker.record_portfolio_snapshot()
            
        except Exception as e:
            console.print(f"  [red]Error: {e}[/red]")
        
        # Walk through the rest of the month day-by-day to catch stop-loss / take-profit triggers
        day_cursor = month_start + timedelta(days=1)
        while day_cursor < month_end:
            broker.current_date = day_cursor
            day_decisions = []
            day_decisions.extend(await strategy.plan_exits(broker))
            day_decisions.extend(await strategy.plan_rebalance(broker))

            day_results = []
            for dec in day_decisions:
                res = await broker.place_order(dec.symbol, dec.qty, side="sell")
                if res.qty > 0:
                    day_results.append(res)

            if day_results:
                console.print(f"  [blue]🔔 Mid-month exits {day_cursor.date()}: {len(day_results)}[/blue]")

            broker.record_portfolio_snapshot()
            day_cursor += timedelta(days=1)

        # Advance to next month boundary
        broker.current_date = month_end
        broker.record_portfolio_snapshot()
    
    await broker.disconnect()
    
    # Calculate final portfolio value
    final_value = await broker.get_portfolio_value()
    
    # Calculate performance metrics
    metrics = calculate_performance_metrics(
        initial_value=initial_cash,
        final_value=final_value,
        portfolio_history=broker.portfolio_history,
        trade_history=broker.trade_history,
        monthly_budget=settings.monthly_budget,
        months=months,
    )
    
    # Print results
    print_backtest_results(
        start_date=start_date,
        end_date=end_date,
        metrics=metrics,
        trade_history=broker.trade_history,
        elo_ratings=strategy.elo_ratings,
    )



if __name__ == "__main__":
    app()
