"""Opportunity detection for continuous monitoring."""
import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Opportunity:
    """Detected trading opportunity."""
    symbol: str
    type: str  # "dip_buy", "breakout", "monthly_dca"
    confidence: float  # 0.0 to 1.0
    reason: str
    suggested_allocation: float  # Amount in base currency


def detect_price_dip(current_price: float, sma_20: float, sma_50: float) -> Optional[Opportunity]:
    """
    Detect buying opportunity when price dips below moving averages.
    
    Buy signal: Price touches or crosses below SMA20 while SMA20 > SMA50 (still in uptrend).
    """
    if sma_20 <= sma_50:
        return None  # Not in uptrend
    
    # Price 2-5% below SMA20 = good dip
    dip_pct = (sma_20 - current_price) / sma_20
    
    if 0.02 <= dip_pct <= 0.05:
        confidence = min(1.0, dip_pct * 20)  # 2% = 0.4, 5% = 1.0
        return Opportunity(
            symbol="",
            type="dip_buy",
            confidence=confidence,
            reason=f"Price dip {dip_pct*100:.1f}% below SMA20 in uptrend",
            suggested_allocation=0.0  # Will be set by strategy
        )
    
    return None


def detect_breakout(prices: List[float], volumes: List[float]) -> Optional[Opportunity]:
    """
    Detect breakout: price breaks above resistance with high volume.
    
    Signals:
    - Price breaks 20-day high
    - Volume > 1.5x average
    """
    if len(prices) < 21 or len(volumes) < 20:
        return None
    
    current_price = prices[-1]
    recent_high = max(prices[-21:-1])  # Last 20 days (excluding today)
    current_volume = volumes[-1]
    avg_volume = sum(volumes[-20:]) / 20
    
    if current_price > recent_high * 1.02 and current_volume > avg_volume * 1.5:
        confidence = min(1.0, (current_volume / avg_volume - 1) / 2)
        return Opportunity(
            symbol="",
            type="breakout",
            confidence=confidence,
            reason=f"Breakout above 20-day high with {current_volume/avg_volume:.1f}x volume",
            suggested_allocation=0.0
        )
    
    return None


def scan_opportunities(
    symbol: str,
    current_price: float,
    prices: List[float],
    volumes: List[float],
    sma_20: float,
    sma_50: float,
    budget_available: float
) -> List[Opportunity]:
    """
    Scan for all types of opportunities.
    
    Returns list of detected opportunities sorted by confidence.
    """
    opportunities: List[Opportunity] = []
    
    # Check for dip
    dip_opp = detect_price_dip(current_price, sma_20, sma_50)
    if dip_opp:
        dip_opp.symbol = symbol
        # Allocate 10-20% of remaining budget based on confidence
        dip_opp.suggested_allocation = budget_available * 0.1 * (1 + dip_opp.confidence)
        opportunities.append(dip_opp)
    
    # Check for breakout
    breakout_opp = detect_breakout(prices, volumes)
    if breakout_opp:
        breakout_opp.symbol = symbol
        # Allocate 5-15% of budget for breakouts (more aggressive)
        breakout_opp.suggested_allocation = budget_available * 0.05 * (1 + breakout_opp.confidence * 2)
        opportunities.append(breakout_opp)
    
    # Sort by confidence
    opportunities.sort(key=lambda x: x.confidence, reverse=True)
    
    return opportunities
