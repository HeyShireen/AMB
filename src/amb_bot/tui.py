"""Textual TUI App for AMB Bot Dashboard."""
from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Button
from textual.binding import Binding

from .dashboard import Dashboard, load_budget_data, format_positions_from_budget
from .budget import BudgetTracker


class AMBDashboardApp:
    """Dashboard UI for AMB Bot monitoring (non-Textual version for compatibility)."""
    
    def __init__(self) -> None:
        self.budget_tracker = BudgetTracker(200.0)
        self.running = True
    
    def refresh_display(self) -> None:
        """Refresh all dashboard data."""
        import os
        os.system("clear" if os.name == "posix" else "cls")
        
        print("\n" + "="*70)
        print("  🤖 AMB INVESTMENT BOT - DASHBOARD")
        print("="*70)
        
        # Status bar
        now = datetime.now()
        hour = now.hour
        market_open = 14 <= hour < 21  # UTC hours
        market_icon = "📈 OPEN" if market_open else "🌙 CLOSED"
        print(f"\n⏰ {now.strftime('%Y-%m-%d %H:%M:%S UTC')}  |  {market_icon}\n")
        
        # Budget section
        self.print_budget()
        
        # Positions section
        self.print_positions()
        
        # Trade history section
        self.print_trade_history()
        
        # Opportunities section
        self.print_opportunities()
        
        # Footer
        print("\n" + "-"*70)
        print("Commands: [R]efresh  [S]ettings  [Q]uit  [W]atch mode")
        print("="*70 + "\n")
    
    def print_budget(self) -> None:
        """Print budget widget."""
        summary = self.budget_tracker.get_month_summary()
        spent = summary['spent']
        budget = summary['budget']
        remaining = summary['remaining']
        pct = (spent / budget * 100) if budget > 0 else 0
        
        bar_len = 40
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        
        print(f"💰 BUDGET ({summary['month']})")
        print(f"   Total:     {budget:8.2f}€")
        print(f"   Spent:     {spent:8.2f}€  [{bar}] {pct:5.1f}%")
        print(f"   Remaining: {remaining:8.2f}€\n")
    
    def print_positions(self) -> None:
        """Print open positions."""
        budget_data = load_budget_data()
        trades = budget_data.get('trades', [])
        positions = format_positions_from_budget(trades)
        
        if not positions:
            print("📭 No open positions\n")
            return
        
        print("📊 OPEN POSITIONS")
        print(f"{'Symbol':<10} {'Qty':<12} {'Avg Price':<12} {'P&L $':<12} {'P&L %':<10}")
        print("-" * 70)
        
        for symbol, pos in positions.items():
            qty = pos.get('qty', 0)
            avg_price = pos.get('avg_price', 0)
            # In real scenario, would fetch current price
            current_price = avg_price  # Placeholder
            pnl = (current_price - avg_price) * qty
            pnl_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
            
            pnl_color = "🟢" if pnl >= 0 else "🔴"
            print(f"{symbol:<10} {qty:>11.4f} {avg_price:>11.2f}€ {pnl:>11.2f}€ {pnl_color} {pnl_pct:>8.1f}%")
        
        print()
    
    def print_trade_history(self) -> None:
        """Print recent trades."""
        budget_data = load_budget_data()
        trades = budget_data.get('trades', [])
        
        if not trades:
            print("📭 No recent trades\n")
            return
        
        print("📜 RECENT TRADES (Last 10)")
        print(f"{'Time':<10} {'Type':<10} {'Symbol':<10} {'Qty':<12} {'Price':<10}")
        print("-" * 70)
        
        for trade in trades[-10:]:
            timestamp = trade.get('timestamp', '')
            if 'T' in timestamp:
                timestamp = timestamp.split('T')[1][:5]
            
            side = trade.get('side', '').upper()
            side_icon = "🟢" if side == "BUY" else "🔴"
            
            print(f"{timestamp:<10} {side_icon} {side:<8} {trade.get('symbol', ''):<10} "
                  f"{trade.get('qty', 0):>11.4f} {trade.get('price', 0):>9.2f}€")
        
        print()
    
    def print_opportunities(self) -> None:
        """Print detected opportunities (placeholder)."""
        print("🎯 DETECTED OPPORTUNITIES")
        print("   ⭐ Scanning for opportunities...")
        print()
    
    def run_interactive(self) -> None:
        """Run interactive dashboard."""
        while self.running:
            self.refresh_display()
            
            try:
                cmd = input("Command: ").strip().upper()
                
                if cmd == 'Q':
                    print("👋 Goodbye!")
                    self.running = False
                elif cmd == 'R':
                    continue
                elif cmd == 'S':
                    print("⚙️  Settings not yet implemented")
                elif cmd == 'W':
                    print("🔗 Use: poetry run amb-bot watch")
                else:
                    print(f"Unknown command: {cmd}")
            except KeyboardInterrupt:
                print("\n👋 Interrupted!")
                self.running = False
            except Exception as e:
                print(f"Error: {e}")
