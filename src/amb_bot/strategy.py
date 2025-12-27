import asyncio
import logging
from typing import Dict, List
import random

from .broker.base import BrokerClient, OrderResult, Position
from .config import Settings
from .indicators import analyze_trend, detect_market_regime

logger = logging.getLogger(__name__)


class Decision:
    def __init__(self, action: str, symbol: str, qty: float, reason: str = "", limit_price: float = 0.0, stop_loss: float | None = None):
        self.action = action
        self.symbol = symbol
        self.qty = qty
        self.reason = reason
        self.limit_price = limit_price
        self.stop_loss = stop_loss


class Strategy:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        # Ratings for all tickers (ELO or Glicko)
        all_tickers = list(settings.universe) + getattr(settings, "exploration_candidates", [])
        self.elo_ratings: Dict[str, float] = {
            sym: getattr(settings, "elo_initial_rating", 1500.0) for sym in all_tickers
        }
        # Glicko-2 specific: rating deviation and volatility
        if getattr(settings, "glicko_enabled", False):
            self.rating_deviations: Dict[str, float] = {
                sym: getattr(settings, "glicko_initial_rd", 350.0) for sym in all_tickers
            }
            self.volatilities: Dict[str, float] = {
                sym: getattr(settings, "glicko_initial_volatility", 0.06) for sym in all_tickers
            }
        else:
            self.rating_deviations = {}
            self.volatilities = {}
        self.last_elo_match = 0  # Track days since last match
        # Mean reversion stop tracking
        self.stop_levels: Dict[str, float] = {}
        # Trailing stop: track highest price since entry
        self.highest_prices: Dict[str, float] = {}
        # Partial take-profit tracking
        self.partial_taken: Dict[str, bool] = {}

    async def refresh_trust_levels(self, broker: BrokerClient) -> None:
        """Legacy hook no-op (exploration removed for mean reversion strategy)."""
        return

    async def run_elo_matches(self, broker: BrokerClient) -> None:
        """Run random rating matches between tickers based on performance."""
        if not getattr(self.settings, "elo_enabled", False):
            return
        
        self.last_elo_match += 1
        if self.last_elo_match < getattr(self.settings, "elo_match_frequency", 5):
            return
        
        self.last_elo_match = 0
        tickers = list(self.elo_ratings.keys())
        
        if len(tickers) < 2:
            return
        
        # Get positions once for all matches
        positions = {pos.symbol: pos for pos in await broker.list_positions()}
        
        # Sort tickers by ELO rating for Swiss pairing (match similar levels)
        sorted_tickers = sorted(tickers, key=lambda t: self.elo_ratings.get(t, self.settings.elo_initial_rating), reverse=True)
        
        # Run multiple matches for better classification
        matches_per_run = getattr(self.settings, "elo_matches_per_run", 1)
        for _ in range(matches_per_run):
            # Swiss pairing: match tickers of similar ELO level (consecutive pairs)
            # Add slight randomization by picking a random starting position
            available = sorted_tickers.copy()
            
            # Pick a random pair from top half to ensure ELO-based matching
            pair_index = random.randint(0, max(0, len(available) // 2 - 1)) * 2
            ticker1 = available[pair_index]
            ticker2 = available[min(pair_index + 1, len(available) - 1)]
            
            # Calculate scores (risk-adjusted by default)
            if getattr(self.settings, "elo_multi_factor_scoring", True):
                score1 = await self._calculate_multi_factor_score(ticker1, positions, broker)
                score2 = await self._calculate_multi_factor_score(ticker2, positions, broker)
            else:
                # Simple P&L scoring (legacy fallback)
                score1 = 0.0
                if ticker1 in positions:
                    pos = positions[ticker1]
                    quote = await broker.fetch_quote(ticker1)
                    score1 = (quote.price - pos.avg_price) / pos.avg_price if pos.avg_price else 0
                
                score2 = 0.0
                if ticker2 in positions:
                    pos = positions[ticker2]
                    quote = await broker.fetch_quote(ticker2)
                    score2 = (quote.price - pos.avg_price) / pos.avg_price if pos.avg_price else 0
            
            # Determine winner (higher score)
            winner, loser = (ticker1, ticker2) if score1 > score2 else (ticker2, ticker1)
            winner_score, loser_score = (score1, score2) if score1 > score2 else (score2, score1)
            
            # Update ratings
            if getattr(self.settings, "glicko_enabled", False):
                self._update_glicko_ratings(winner, loser, winner_score, loser_score)
            else:
                # Simple ELO update
                k = getattr(self.settings, "elo_k_factor", 32.0)
                self.elo_ratings[winner] += k
                self.elo_ratings[loser] -= k
            
            logger.info(f"Rating Match: {winner} beats {loser} (rating: {self.elo_ratings[winner]:.0f} vs {self.elo_ratings[loser]:.0f})")
    
    async def _calculate_multi_factor_score(self, symbol: str, positions: dict, broker: BrokerClient) -> float:
        """Risk-adjusted reliability score for ELO: reward stable, consistent names."""
        score = 0.0

        # P&L component (unrealized) - small weight to avoid overfitting to a single spike
        pnl = 0.0
        if symbol in positions:
            pos = positions[symbol]
            quote = await broker.fetch_quote(symbol)
            pnl = (quote.price - pos.avg_price) / pos.avg_price if pos.avg_price else 0.0
            score += pnl * 0.30

        prices: List[float] = []
        try:
            history = await broker.fetch_historical(symbol, days=90)
            prices = [float(p) for p in history]
        except Exception:
            prices = []

        if len(prices) >= 2:
            # Daily returns
            returns = []
            for i in range(1, len(prices)):
                prev = prices[i - 1]
                curr = prices[i]
                if prev > 0:
                    returns.append((curr - prev) / prev)

            # Sharpe-like ratio
            if returns:
                avg_return = sum(returns) / len(returns)
                variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
                std_return = variance ** 0.5
                annual_return = avg_return * 252
                annual_vol = std_return * 252 ** 0.5
                sharpe = (annual_return - 0.02) / annual_vol if annual_vol > 0 else 0.0
                score += sharpe * 0.30

            # Momentum (20% weight) - medium-term drift
            lookback = min(20, len(prices) - 1)
            base_price = prices[-lookback - 1]
            momentum = (prices[-1] - base_price) / base_price if base_price > 0 else 0.0
            score += momentum * 0.20

            # Max drawdown penalty (20% weight)
            peak = prices[0]
            max_drawdown = 0.0
            for price in prices:
                if price > peak:
                    peak = price
                drawdown = (peak - price) / peak if peak > 0 else 0.0
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            score -= max_drawdown * 0.20

        return score
    
    def _update_glicko_ratings(self, winner: str, loser: str, winner_pnl: float, loser_pnl: float) -> None:
        """Update Glicko-2 ratings after a match."""
        import math
        
        # Glicko-2 constants
        Q = math.log(10) / 400.0
        tau = getattr(self.settings, "glicko_tau", 0.5)
        
        # Get current ratings (convert to Glicko scale: (rating - 1500) / 173.7178)
        r1 = (self.elo_ratings[winner] - 1500) / 173.7178
        r2 = (self.elo_ratings[loser] - 1500) / 173.7178
        rd1 = self.rating_deviations[winner] / 173.7178
        rd2 = self.rating_deviations[loser] / 173.7178
        
        # Expected score
        g_rd2 = 1 / math.sqrt(1 + 3 * Q**2 * rd2**2 / math.pi**2)
        E = 1 / (1 + 10 ** (-g_rd2 * (r1 - r2)))
        
        # Actual score (winner = 1, loser = 0)
        s = 1.0
        
        # Variance
        v = 1 / (Q**2 * g_rd2**2 * E * (1 - E))
        
        # Delta (improvement)
        delta = v * Q * g_rd2 * (s - E)
        
        # Update winner rating
        new_rd1_sq = 1 / (1 / rd1**2 + 1 / v)
        new_r1 = r1 + Q / (1 / rd1**2 + 1 / v) * g_rd2 * (s - E)
        
        # Convert back to ELO scale
        self.elo_ratings[winner] = new_r1 * 173.7178 + 1500
        self.rating_deviations[winner] = math.sqrt(new_rd1_sq) * 173.7178
        
        # Update loser (opposite result)
        g_rd1 = 1 / math.sqrt(1 + 3 * Q**2 * rd1**2 / math.pi**2)
        E_loser = 1 / (1 + 10 ** (-g_rd1 * (r2 - r1)))
        v_loser = 1 / (Q**2 * g_rd1**2 * E_loser * (1 - E_loser))
        new_rd2_sq = 1 / (1 / rd2**2 + 1 / v_loser)
        new_r2 = r2 + Q / (1 / rd2**2 + 1 / v_loser) * g_rd1 * (0 - E_loser)
        
        self.elo_ratings[loser] = new_r2 * 173.7178 + 1500
        self.rating_deviations[loser] = math.sqrt(new_rd2_sq) * 173.7178

    def _compute_indicators(self, prices: List[float]) -> Dict[str, float]:
        """Compute SMA20, Bollinger bands, RSI14, ATR14 (close-only proxy)."""
        if len(prices) < 20:
            return {"sma20": 0, "bb_upper": 0, "bb_lower": 0, "rsi14": 50, "atr14": 0}

        sma20 = sum(prices[-20:]) / 20
        mean = sma20
        variance = sum((p - mean) ** 2 for p in prices[-20:]) / 20
        import math
        std_dev = math.sqrt(variance)
        bb_upper = mean + 2 * std_dev
        bb_lower = mean - 2 * std_dev

        # RSI14 (standard Wilder smoothing)
        changes = [prices[i] - prices[i - 1] for i in range(-14, 0)]
        gains = [c if c > 0 else 0.0 for c in changes]
        losses = [abs(c) if c < 0 else 0.0 for c in changes]
        avg_gain = sum(gains) / len(gains) if gains else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        if avg_loss == 0:
            rsi14 = 100.0
        elif avg_gain == 0:
            rsi14 = 0.0
        else:
            rs = avg_gain / avg_loss
            rsi14 = 100 - (100 / (1 + rs))

        # ATR14 (close-only proxy): use absolute close-to-close changes
        trs = []
        for i in range(1, len(prices)):
            trs.append(abs(prices[i] - prices[i - 1]))
        atr14 = sum(trs[-14:]) / 14 if len(trs) >= 14 else 0.0

        return {
            "sma20": sma20,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "rsi14": rsi14,
            "atr14": atr14,
            "slope20": (prices[-1] - prices[-5]) / prices[-5] if prices[-5] != 0 else 0.0,
        }

    def _is_range(self, indicators: Dict[str, float]) -> bool:
        """Range filter: flat SMA20 (allow up to 3% drift over 5 bars)."""
        slope_flat = abs(indicators.get("slope20", 0.0)) < 0.03  # Allow up to ~3% drift
        atr = indicators.get("atr14", 0.0)
        if atr == 0:
            return False
        return slope_flat

    async def _plan_buys_league_system(self, broker: BrokerClient, base_budget: float, explore_budget: float) -> List[Decision]:
        """Allocate budget using league system: champions (60%), standard (30%), relegation (10%)."""
        # Sort tickers by ELO rating
        sorted_tickers = sorted(
            self.settings.universe,
            key=lambda sym: self.elo_ratings.get(sym, 1500.0),
            reverse=True
        )
        
        # Divide into leagues (top 3, middle, bottom 3)
        champions = sorted_tickers[:3]
        relegation = sorted_tickers[-3:]
        standard = [t for t in sorted_tickers if t not in champions and t not in relegation]
        
        # Allocate budget by league
        champions_budget = base_budget * getattr(self.settings, "elo_league_champions_pct", 0.60)
        standard_budget = base_budget * getattr(self.settings, "elo_league_standard_pct", 0.30)
        relegation_budget = base_budget * getattr(self.settings, "elo_league_relegation_pct", 0.10)
        
        logger.info(f"[League System] Champions: {champions}, Standard: {standard}, Relegation: {relegation}")
        
        decisions: List[Decision] = []
        
        # Allocate to each league
        for symbol, league_budget in [
            *[(c, champions_budget / len(champions)) for c in champions],
            *[(s, standard_budget / len(standard)) for s in standard if standard],
            *[(r, relegation_budget / len(relegation)) for r in relegation]
        ]:
            quote = await broker.fetch_quote(symbol)
            if not quote.price or quote.price <= 0:
                logger.warning(f"⚠️  Skipping {symbol}: No valid price data")
                continue
            
            qty = league_budget / quote.price
            decisions.append(Decision(
                action="buy",
                symbol=symbol,
                qty=qty,
                reason=f"League allocation ({league_budget:.2f}€)",
                limit_price=0.0
            ))
        
        return decisions

    async def _get_market_regime(self, broker: BrokerClient) -> str:
        """Detect market regime using a proxy ticker (SPY or first universe ticker)."""
        if not getattr(self.settings, "market_regime_filter_enabled", False):
            return 'bull'  # Default to bull if filter disabled
        
        # Use first ticker as proxy (could be AAPL, MSFT, etc.)
        proxy_symbol = self.settings.universe[0] if self.settings.universe else None
        if not proxy_symbol:
            return 'bull'
        
        try:
            # Get historical prices for regime detection
            quote = await broker.fetch_quote(proxy_symbol)
            # For backtest broker, we can get historical bars
            if hasattr(broker, '_historical_cache'):
                cache = getattr(broker, '_historical_cache', {})
                if proxy_symbol in cache:
                    bars = cache[proxy_symbol]
                    prices = [float(bar.close) for bar in bars[-250:]]  # Last 250 days
                    regime = detect_market_regime(prices)
                    logger.info(f"📊 Market Regime detected: {regime.upper()} (proxy: {proxy_symbol})")
                    return regime
        except Exception as e:
            logger.warning(f"Failed to detect market regime: {e}")
        
        return 'bull'  # Default to bull on error
    
    async def plan_buys(self, broker: BrokerClient) -> List[Decision]:
        """DCA + momentum-weighted entries: buy top ELO-rated tickers with trend filter."""
        decisions: List[Decision] = []

        # Get available cash for position sizing
        available_cash = getattr(broker, "cash", self.settings.monthly_budget)

        if available_cash < 50:
            return decisions

        # Sort universe by ELO rating (favor higher-rated tickers)
        sorted_universe = sorted(
            self.settings.universe,
            key=lambda s: self.elo_ratings.get(s, 1500.0),
            reverse=True
        )

        if not sorted_universe:
            return decisions

        # If winners_only_mode, limit to top N
        if getattr(self.settings, "elo_winners_only_mode", False):
            winners_count = getattr(self.settings, "elo_winners_count", 5)
            sorted_universe = sorted_universe[:winners_count]
            logger.info(f"🏆 Winners-only mode: focusing on top {winners_count} by ELO")

        open_positions = await broker.list_positions()
        held_symbols = {p.symbol for p in open_positions}

        # Pre-compute portfolio value for concentration check
        portfolio_value = available_cash
        for p in open_positions:
            pq = await broker.fetch_quote(p.symbol)
            portfolio_value += p.qty * pq.price

        # Calculate momentum scores for weighting
        momentum_scores: Dict[str, float] = {}
        valid_symbols: List[str] = []
        
        for symbol in sorted_universe:
            quote = await broker.fetch_quote(symbol)
            price = quote.price
            if price <= 0:
                continue
                
            history = await broker.fetch_historical(symbol, days=30)
            if len(history) < 20:
                continue
            
            indicators = self._compute_indicators(history)
            
            # === TREND FILTERS ===
            # 1. RSI filter: skip if overbought
            rsi = indicators.get("rsi14", 50)
            rsi_overbought = getattr(self.settings, "rsi_overbought", 70)
            if rsi > rsi_overbought:
                logger.debug(f"⏭️ Skipping {symbol}: RSI={rsi:.0f} > {rsi_overbought}")
                continue
            
            # 2. SMA trend filter: price should be above short SMA
            sma20 = indicators.get("sma20", 0)
            if sma20 > 0 and price < sma20 * 0.95:
                logger.debug(f"⏭️ Skipping {symbol}: price below SMA20")
                continue
            
            # 3. Momentum filter: require positive momentum
            momentum_lookback = getattr(self.settings, "momentum_lookback", 20)
            min_momentum = getattr(self.settings, "min_momentum", 0.02)
            if len(history) >= momentum_lookback:
                # Use first price in the lookback window (oldest)
                base_price = history[0] if len(history) <= momentum_lookback else history[-momentum_lookback]
                momentum = (price - base_price) / base_price if base_price > 0 else 0
                if momentum < min_momentum:
                    logger.debug(f"⏭️ Skipping {symbol}: momentum={momentum*100:.1f}% < {min_momentum*100:.0f}%")
                    continue
                momentum_scores[symbol] = max(0.1, momentum)  # Min score 0.1
            else:
                momentum_scores[symbol] = 0.1
            
            # 4. Skip if position is already large (> 15% of portfolio)
            if symbol in held_symbols and portfolio_value > 0:
                pos = next((p for p in open_positions if p.symbol == symbol), None)
                if pos:
                    pos_value = pos.qty * price
                    if pos_value / portfolio_value > 0.15:
                        logger.debug(f"⏭️ Skipping {symbol}: position too large ({pos_value/portfolio_value*100:.0f}%)")
                        continue
            
            valid_symbols.append(symbol)
        
        if not valid_symbols:
            logger.info("📊 No valid entry signals found this period")
            return decisions
        
        # Allocate budget weighted by momentum
        total_momentum = sum(momentum_scores.get(s, 0.1) for s in valid_symbols)
        max_picks = min(getattr(self.settings, "max_positions", 8), len(valid_symbols))
        
        for symbol in valid_symbols[:max_picks]:
            weight = momentum_scores.get(symbol, 0.1) / total_momentum if total_momentum > 0 else 1 / len(valid_symbols)
            budget_for_symbol = available_cash * weight
            
            # Minimum allocation check
            if budget_for_symbol < 20:
                continue
            
            quote = await broker.fetch_quote(symbol)
            price = quote.price
            if price <= 0:
                continue
            
            qty = budget_for_symbol / price
            qty = round(qty, 4)
            if qty <= 0 or qty * price < 15:
                continue

            # ATR-based stop
            history = await broker.fetch_historical(symbol, days=20)
            stop = None
            if len(history) >= 14:
                indicators = self._compute_indicators(history)
                atr = indicators.get("atr14", 0)
                if atr > 0:
                    stop = price - self.settings.atr_stop_multiplier * atr

            decisions.append(Decision(
                action="buy",
                symbol=symbol,
                qty=qty,
                reason=f"momentum_dca (mom={momentum_scores.get(symbol, 0)*100:.1f}%)",
                limit_price=price,
                stop_loss=stop,
            ))
            logger.info(f"📈 Buy signal: {symbol} qty={qty:.4f} @ ${price:.2f} (momentum weight: {weight*100:.1f}%)")

        return decisions

    async def plan_exits(self, broker: BrokerClient) -> List[Decision]:
        """Exit positions based on stop-loss, take-profit, or trailing stop."""
        decisions: List[Decision] = []
        positions = await broker.list_positions()

        for pos in positions:
            quote = await broker.fetch_quote(pos.symbol)
            price = quote.price
            if price <= 0:
                continue

            pnl_pct = (price - pos.avg_price) / pos.avg_price if pos.avg_price > 0 else 0
            
            # Update highest price for trailing stop (track the peak)
            if pos.symbol not in self.highest_prices:
                self.highest_prices[pos.symbol] = max(pos.avg_price, price)
            elif price > self.highest_prices[pos.symbol]:
                self.highest_prices[pos.symbol] = price

            # 1. Full take-profit at configured threshold (default 20%)
            if pnl_pct >= self.settings.take_profit_pct:
                logger.info(f"✅ Take-profit for {pos.symbol}: P&L={pnl_pct*100:.1f}%")
                decisions.append(Decision(action="sell", symbol=pos.symbol, qty=pos.qty, reason="take_profit"))
                self._cleanup_position_tracking(pos.symbol)
                continue

            # 2. Partial take-profit at +10% (sell 50%)
            partial_tp_pct = getattr(self.settings, "partial_take_profit_pct", 0.10)
            partial_tp_frac = getattr(self.settings, "partial_take_profit_frac", 0.5)
            if pnl_pct >= partial_tp_pct and not self.partial_taken.get(pos.symbol, False):
                sell_qty = pos.qty * partial_tp_frac
                logger.info(f"📊 Partial TP for {pos.symbol}: P&L={pnl_pct*100:.1f}%, selling {partial_tp_frac*100:.0f}%")
                decisions.append(Decision(action="sell", symbol=pos.symbol, qty=sell_qty, reason="partial_take_profit"))
                self.partial_taken[pos.symbol] = True
                continue

            # 3. Trailing stop (activate after +8%, trail at 5% from high)
            trailing_enabled = getattr(self.settings, "trailing_stop_enabled", True)
            trailing_activation = getattr(self.settings, "trailing_stop_activation_pct", 0.08)
            trailing_distance = getattr(self.settings, "trailing_stop_distance_pct", 0.05)
            
            if trailing_enabled and pnl_pct >= trailing_activation:
                highest = self.highest_prices.get(pos.symbol, pos.avg_price)
                trailing_stop_price = highest * (1 - trailing_distance)
                if price <= trailing_stop_price:
                    logger.info(f"📉 Trailing stop for {pos.symbol}: Price ${price:.2f} < trailing ${trailing_stop_price:.2f}")
                    decisions.append(Decision(action="sell", symbol=pos.symbol, qty=pos.qty, reason="trailing_stop"))
                    self._cleanup_position_tracking(pos.symbol)
                    continue

            # 4. Stop-loss at configured threshold (default 12%)
            if pnl_pct <= -self.settings.stop_loss_pct:
                logger.info(f"🛑 Stop-loss for {pos.symbol}: P&L={pnl_pct*100:.1f}%")
                decisions.append(Decision(action="sell", symbol=pos.symbol, qty=pos.qty, reason="stop_loss"))
                self._cleanup_position_tracking(pos.symbol)
                continue

        return decisions
    
    def _cleanup_position_tracking(self, symbol: str) -> None:
        """Clean up tracking data when position is closed."""
        self.highest_prices.pop(symbol, None)
        self.partial_taken.pop(symbol, None)
        self.stop_levels.pop(symbol, None)

    async def plan_rebalance(self, broker: BrokerClient) -> List[Decision]:
        """Legacy hook disabled for mean-reversion strategy."""
        return []

    async def execute(self, broker: BrokerClient) -> List[OrderResult]:
        results: List[OrderResult] = []
        await self.run_elo_matches(broker)

        # Exits (stop or TP at SMA20)
        exits = await self.plan_exits(broker)
        for dec in exits:
            results.append(await broker.place_order(dec.symbol, dec.qty, side="sell"))
            self.stop_levels.pop(dec.symbol, None)

        # Entries
        entries = await self.plan_buys(broker)
        for dec in entries:
            result = await broker.place_order(
                dec.symbol,
                dec.qty,
                side="buy",
                limit_price=dec.limit_price if self.settings.use_limit_orders else None
            )
            results.append(result)
            if result.qty > 0 and dec.stop_loss:
                self.stop_levels[dec.symbol] = dec.stop_loss

        return results
