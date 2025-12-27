"""Technical indicators for trend analysis."""
from typing import List, Tuple


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """
    Calculate Relative Strength Index (RSI).
    
    Args:
        prices: List of historical prices (most recent last)
        period: RSI period (default 14)
    
    Returns:
        RSI value (0-100). >70 = overbought, <30 = oversold
    """
    if len(prices) < period + 1:
        return 50.0  # Neutral if insufficient data
    
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_sma(prices: List[float], period: int) -> float:
    """
    Calculate Simple Moving Average.
    
    Args:
        prices: List of historical prices
        period: Number of periods
    
    Returns:
        SMA value
    """
    if len(prices) < period:
        return sum(prices) / len(prices)
    return sum(prices[-period:]) / period


def detect_market_regime(prices: List[float], short_period: int = 50, long_period: int = 200) -> str:
    """
    Detect market regime based on moving averages.
    
    Args:
        prices: List of historical prices (most recent last)
        short_period: Short MA period (default 50)
        long_period: Long MA period (default 200)
    
    Returns:
        'bull': Price > MA200 and MA50 > MA200
        'bear': Price < MA200 and MA50 < MA200
        'sideways': Otherwise (mixed signals)
    """
    if len(prices) < long_period:
        return 'sideways'  # Not enough data, stay neutral
    
    current_price = prices[-1]
    sma_short = calculate_sma(prices, short_period)
    sma_long = calculate_sma(prices, long_period)
    
    if current_price > sma_long and sma_short > sma_long:
        return 'bull'
    elif current_price < sma_long and sma_short < sma_long:
        return 'bear'
    else:
        return 'sideways'


def is_uptrend(prices: List[float], short_period: int = 20, long_period: int = 50) -> bool:
    """
    Check if stock is in uptrend using moving averages.
    
    Args:
        prices: Historical prices
        short_period: Short MA period (default 20)
        long_period: Long MA period (default 50)
    
    Returns:
        True if short MA > long MA (golden cross = uptrend)
    """
    if len(prices) < long_period:
        return True  # Insufficient data, allow buy
    
    sma_short = calculate_sma(prices, short_period)
    sma_long = calculate_sma(prices, long_period)
    
    return sma_short > sma_long


def detect_volume_anomaly(current_volume: float, historical_volumes: List[float], threshold: float = 3.0) -> Tuple[bool, str]:
    """
    Detect abnormal volume spikes that might indicate manipulation.
    
    Args:
        current_volume: Today's volume
        historical_volumes: Past volumes (e.g., 20 days)
        threshold: Multiplier for anomaly (3.0 = 3x average)
    
    Returns:
        (is_anomaly, reason) tuple
    """
    if len(historical_volumes) < 5:
        return False, "Insufficient volume data"
    
    avg_volume = sum(historical_volumes) / len(historical_volumes)
    
    if avg_volume == 0:
        return False, "No historical volume"
    
    ratio = current_volume / avg_volume
    
    if ratio > threshold:
        return True, f"Volume spike {ratio:.1f}x average (possible manipulation)"
    
    return False, f"Normal volume ({ratio:.1f}x avg)"


def analyze_trend(
    prices: List[float],
    current_volume: float = 0,
    historical_volumes: List[float] | None = None,
    short_period: int = 20,
    long_period: int = 50,
    rsi_period: int = 14,
    rsi_overbought: float = 75.0,
    price_above_sma_factor: float = 0.95,
    volume_threshold: float = 3.0,
) -> Tuple[bool, str]:
    """
    Comprehensive trend analysis with volume anomaly detection.
    
    Args:
        prices: Historical prices (oldest first, newest last)
        current_volume: Today's volume (optional)
        historical_volumes: Historical volumes (optional)
    
    Returns:
        (should_buy, reason) tuple
    """
    if len(prices) < max(long_period, rsi_period, 30):
        return True, "Insufficient data for analysis"
    
    current_price = prices[-1]
    rsi = calculate_rsi(prices, period=rsi_period)
    uptrend = is_uptrend(prices, short_period=short_period, long_period=long_period)
    sma_short = calculate_sma(prices, short_period)
    
    # Volume anomaly check
    if current_volume > 0 and historical_volumes:
        is_anomaly, volume_msg = detect_volume_anomaly(current_volume, historical_volumes, threshold=volume_threshold)
        if is_anomaly:
            return False, volume_msg
    
    # Filter conditions
    if rsi > rsi_overbought:
        return False, f"Overbought (RSI={rsi:.1f})"
    
    if not uptrend:
        return False, "Downtrend (SMAshort < SMAlong)"
    
    if current_price < sma_short * price_above_sma_factor:
        return False, f"Price below SMA(short) threshold"
    
    return True, f"Uptrend confirmed (RSI={rsi:.1f})"
