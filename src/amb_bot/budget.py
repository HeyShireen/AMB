"""Budget tracking for continuous trading."""
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Record of a single trade."""
    timestamp: str
    symbol: str
    side: str
    qty: float
    price: float
    amount: float  # qty * price
    type: str  # "monthly_dca", "dip_buy", "breakout", "stop_loss", "take_profit"


class BudgetTracker:
    """Tracks monthly budget usage and trade history."""
    
    def __init__(self, monthly_budget: float, data_file: Path = None) -> None:
        self.monthly_budget = monthly_budget
        self.data_file = data_file or Path("data/budget_tracker.json")
        self.data_file.parent.mkdir(exist_ok=True)
        
        self.trades: List[Trade] = []
        self.monthly_spent: float = 0.0
        self.current_month: str = ""
        
        self._load()
    
    def _load(self) -> None:
        """Load trade history from disk."""
        if not self.data_file.exists():
            self._reset_month()
            return
        
        try:
            with self.data_file.open("r") as f:
                data = json.load(f)
                self.current_month = data.get("current_month", "")
                self.monthly_spent = data.get("monthly_spent", 0.0)
                self.trades = [Trade(**t) for t in data.get("trades", [])]
            
            # Check if new month
            now_month = datetime.now().strftime("%Y-%m")
            if self.current_month != now_month:
                logger.info(f"📅 New month detected: {now_month}. Resetting budget.")
                self._reset_month()
        except Exception as e:
            logger.error(f"Error loading budget data: {e}")
            self._reset_month()
    
    def _save(self) -> None:
        """Save trade history to disk."""
        try:
            data = {
                "current_month": self.current_month,
                "monthly_spent": self.monthly_spent,
                "trades": [asdict(t) for t in self.trades]
            }
            with self.data_file.open("w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving budget data: {e}")
    
    def _reset_month(self) -> None:
        """Reset for new month (internal use)."""
        self.current_month = datetime.now().strftime("%Y-%m")
        self.monthly_spent = 0.0
        # Keep trades for history, but reset spending
    
    def reset_month(self) -> None:
        """Public method to reset budget for new month (used in backtests)."""
        self._reset_month()
        self._save()
    
    def get_available_budget(self) -> float:
        """Get remaining budget for this month."""
        # Check if new month
        now_month = datetime.now().strftime("%Y-%m")
        if self.current_month != now_month:
            self._reset_month()
            self._save()
        
        return max(0.0, self.monthly_budget - self.monthly_spent)
    
    def can_trade(self, amount: float) -> bool:
        """Check if we have budget for this trade."""
        return self.get_available_budget() >= amount
    
    def record_trade(self, trade: Trade) -> None:
        """Record a trade and update budget."""
        self.trades.append(trade)
        
        if trade.side.lower() == "buy":
            self.monthly_spent += trade.amount
        
        self._save()
        
        remaining = self.get_available_budget()
        logger.info(f"💰 Budget: spent {self.monthly_spent:.2f}€ / {self.monthly_budget:.2f}€ (remaining: {remaining:.2f}€)")
    
    def get_month_summary(self) -> Dict:
        """Get summary of current month's trading."""
        buys = [t for t in self.trades if t.side.lower() == "buy" and t.timestamp.startswith(self.current_month)]
        sells = [t for t in self.trades if t.side.lower() == "sell" and t.timestamp.startswith(self.current_month)]
        
        return {
            "month": self.current_month,
            "budget": self.monthly_budget,
            "spent": self.monthly_spent,
            "remaining": self.get_available_budget(),
            "trades_count": len(buys) + len(sells),
            "buys": len(buys),
            "sells": len(sells),
            "total_bought": sum(t.amount for t in buys),
            "total_sold": sum(t.amount for t in sells)
        }
