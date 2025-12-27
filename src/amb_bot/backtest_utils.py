"""Backtesting utilities and performance analysis."""

from datetime import datetime
from typing import Dict, List, Optional

from rich.console import Console
from rich.table import Table


def calculate_performance_metrics(
    initial_value: float,
    final_value: float,
    portfolio_history: List[Dict],
    trade_history: List[Dict],
    monthly_budget: float = 200.0,
    months: int = 12,
) -> Dict:
    """Calculate backtest performance metrics."""
    # Total contributed capital = initial + monthly deposits
    total_contributed = initial_value + (monthly_budget * months)
    
    # Net profit = final value minus what was contributed (deposits shouldn't count as profit)
    net_profit = final_value - total_contributed
    total_return = (net_profit / total_contributed * 100) if total_contributed > 0 else 0.0
    
    # For display: total transaction volume (sum of all buys)
    total_buy_volume = sum(
        trade.get("value", 0) for trade in trade_history if trade.get("side", "").lower() == "buy"
    )
    
    # Calculate max drawdown from portfolio value history
    # Use final_value as a proxy if no detailed history available
    peak = initial_value
    max_drawdown = 0.0
    
    # Build portfolio value series from trade history
    portfolio_values = [initial_value]
    running_value = initial_value
    for trade in trade_history:
        if trade.get("side", "").lower() == "buy":
            # Value decreases by cost (cash goes to stock)
            pass  # Already reflected in position value
        elif "pnl" in trade:
            running_value += trade["pnl"]
            portfolio_values.append(running_value)
    
    # Calculate drawdown from value series
    for value in portfolio_values:
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = ((peak - value) / peak) * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    
    # Cap drawdown at 100%
    max_drawdown = min(max_drawdown, 100.0)
    
    # Trade statistics
    total_trades = len(trade_history)
    buys = sum(1 for t in trade_history if t["side"] == "buy")
    sells = sum(1 for t in trade_history if t["side"] == "sell")
    
    # Calculate realized PnL
    realized_pnl = sum(t.get("pnl", 0) for t in trade_history if "pnl" in t)
    
    # Win rate (for trades with PnL)
    winning_trades = sum(1 for t in trade_history if t.get("pnl", 0) > 0)
    losing_trades = sum(1 for t in trade_history if t.get("pnl", 0) < 0)
    win_rate = (winning_trades / (winning_trades + losing_trades) * 100) if (winning_trades + losing_trades) > 0 else 0
    
    # Trade quality metrics
    total_wins = sum(t.get("pnl", 0) for t in trade_history if t.get("pnl", 0) > 0)
    total_losses = abs(sum(t.get("pnl", 0) for t in trade_history if t.get("pnl", 0) < 0))
    avg_win = total_wins / winning_trades if winning_trades > 0 else 0
    avg_loss = total_losses / losing_trades if losing_trades > 0 else 0
    profit_factor = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0
    win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf') if avg_win > 0 else 0
    
    # Calculate volatility and Sharpe from realized equity curve (uses realized P&L only)
    sharpe_ratio = 0.0
    volatility_annual = 0.0
    equity_curve = [initial_value]
    equity = initial_value
    for trade in trade_history:
        if "pnl" in trade:
            equity += trade["pnl"]
            equity_curve.append(equity)

    # Skip volatility/Sharpe when starting equity is zero to avoid divide-by-zero artifacts
    if len(equity_curve) > 1 and initial_value > 0:
        import math
        returns = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i - 1]
            curr = equity_curve[i]
            if prev > 0:
                returns.append((curr - prev) / prev)
        if returns:
            avg_ret = sum(returns) / len(returns)
            variance = sum((r - avg_ret) ** 2 for r in returns) / len(returns)
            std_dev = math.sqrt(variance)
            # Annualize by trades ~ assume 252 periods if one trade per day; cap to avoid overflow
            volatility_annual = min(std_dev * math.sqrt(252) * 100, 1000.0)
            annual_return = avg_ret * 252
            risk_free_rate = 0.02
            sharpe_ratio = (annual_return - risk_free_rate) / (std_dev * math.sqrt(252)) if std_dev > 0 else 0
    
    return {
        "initial_value": initial_value,
        "final_value": final_value,
        "total_contributed": total_contributed,
        "total_buy_volume": total_buy_volume,
        "net_profit": net_profit,
        "total_return_pct": total_return,
        "max_drawdown_pct": max_drawdown,
        "total_trades": total_trades,
        "buys": buys,
        "sells": sells,
        "realized_pnl": realized_pnl,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate_pct": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "win_loss_ratio": win_loss_ratio,
        "sharpe_ratio": sharpe_ratio,
        "volatility_annual_pct": volatility_annual,
    }


def print_backtest_results(
    start_date: datetime,
    end_date: datetime,
    metrics: Dict,
    trade_history: List[Dict],
    elo_ratings: Optional[Dict[str, float]] = None,
) -> None:
    """Print backtest results in a nice table."""
    console = Console()
    
    # Summary table
    console.print("\n")
    summary = Table(title="📈 Backtest Results", title_style="bold cyan")
    summary.add_column("Metric", style="cyan", no_wrap=True)
    summary.add_column("Value", style="magenta")
    
    summary.add_row("Period", f"{start_date.date()} to {end_date.date()}")
    summary.add_row("Duration", f"{(end_date - start_date).days} days")
    summary.add_row("", "")
    summary.add_row("Initial Capital", f"${metrics['initial_value']:,.2f}")
    summary.add_row("Total Contributed", f"${metrics['total_contributed']:,.2f}")
    summary.add_row("Buy Volume (turnover)", f"${metrics['total_buy_volume']:,.2f}")
    summary.add_row("Final Value", f"${metrics['final_value']:,.2f}")
    summary.add_row("Net Profit", f"${metrics['net_profit']:,.2f}")
    summary.add_row("Total Return", f"{metrics['total_return_pct']:.2f}%")
    summary.add_row("Realized P&L", f"${metrics['realized_pnl']:,.2f}")
    summary.add_row("Max Drawdown", f"{metrics['max_drawdown_pct']:.2f}%")
    summary.add_row("", "")
    summary.add_row("Total Trades", str(metrics['total_trades']))
    summary.add_row("Buys", str(metrics['buys']))
    summary.add_row("Sells", str(metrics['sells']))
    summary.add_row("Winning Trades", str(metrics['winning_trades']))
    summary.add_row("Losing Trades", str(metrics['losing_trades']))
    summary.add_row("Win Rate", f"{metrics['win_rate_pct']:.1f}%")
    summary.add_row("", "")
    summary.add_row("Avg Win", f"${metrics['avg_win']:.2f}")
    summary.add_row("Avg Loss", f"${metrics['avg_loss']:.2f}")
    summary.add_row("Profit Factor", f"{metrics['profit_factor']:.2f}" if metrics['profit_factor'] != float('inf') else "∞")
    summary.add_row("Win/Loss Ratio", f"{metrics['win_loss_ratio']:.2f}" if metrics['win_loss_ratio'] != float('inf') else "∞")
    summary.add_row("", "")
    summary.add_row("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
    summary.add_row("Volatility (Annual)", f"{metrics['volatility_annual_pct']:.2f}%")
    
    console.print(summary)
    
    # Trade history table (last 20 trades)
    if trade_history:
        console.print("\n")
        trades_table = Table(title="📋 Recent Trades (Last 20)", title_style="bold cyan")
        trades_table.add_column("Date", style="cyan")
        trades_table.add_column("Symbol", style="yellow")
        trades_table.add_column("Side", style="green")
        trades_table.add_column("Qty", justify="right")
        trades_table.add_column("Price", justify="right")
        trades_table.add_column("Value", justify="right")
        trades_table.add_column("P&L", justify="right")
        
        for trade in trade_history[-20:]:
            pnl_str = f"${trade.get('pnl', 0):,.2f}" if "pnl" in trade else "-"
            pnl_style = "green" if trade.get('pnl', 0) > 0 else "red" if trade.get('pnl', 0) < 0 else "white"
            
            trades_table.add_row(
                trade['date'].strftime("%Y-%m-%d"),
                trade['symbol'],
                trade['side'].upper(),
                f"{trade['qty']:.4f}",
                f"${trade['price']:.2f}",
                f"${trade['value']:.2f}",
                f"[{pnl_style}]{pnl_str}[/{pnl_style}]"
            )
        
        console.print(trades_table)
    
    # ELO Rankings table
    if elo_ratings:
        console.print("\n")
        elo_table = Table(title="🏆 ELO Rankings", title_style="bold cyan")
        elo_table.add_column("Rank", style="cyan", justify="right")
        elo_table.add_column("Symbol", style="yellow")
        elo_table.add_column("ELO Rating", style="magenta", justify="right")
        
        sorted_elo = sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True)
        for rank, (symbol, rating) in enumerate(sorted_elo, 1):
            elo_table.add_row(str(rank), symbol, f"{rating:.1f}")
        
        console.print(elo_table)
