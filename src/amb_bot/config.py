from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "defaults.yaml"


class Settings(BaseSettings):
    base_currency: str = Field("EUR", description="Portfolio base currency")
    monthly_budget: float = Field(200.0, description="Monthly DCA amount in base currency")
    stop_loss_pct: float = Field(0.10, description="Fractional stop-loss (0.10 = 10%)")
    take_profit_pct: float = Field(0.15, description="Fractional take-profit (0.15 = 15%)")
    max_positions: int = Field(10, description="Maximum simultaneous holdings")
    rebalance_enabled: bool = Field(True, description="Enable monthly rebalance rules")
    rebalance_winner_pct: float = Field(0.10, description="P&L threshold to trim winners")
    rebalance_winner_sell_frac: float = Field(0.5, description="Fraction of a winning position to sell when trimming")
    rebalance_loser_pct: float = Field(-0.08, description="P&L threshold to cut losers (keep above stop-loss)")
    exploration_enabled: bool = Field(False, description="Enable exploration sizing with trust levels")
    exploration_budget_pct: float = Field(0.2, description="Fraction of monthly budget reserved for exploration names")
    exploration_max_level: int = Field(3, description="Max trust level for exploration sizing")
    exploration_pnl_up_threshold: float = Field(0.05, description="P&L threshold to level up an exploration name")
    exploration_pnl_down_threshold: float = Field(0.05, description="P&L threshold to level down or pause an exploration name")
    exploration_candidates: List[str] = Field(default_factory=list, description="Exploration tickers (higher risk/less known)")
    elo_enabled: bool = Field(False, description="Enable ranking system for dynamic allocation")
    elo_initial_rating: float = Field(1500.0, description="Initial rating for all tickers")
    elo_k_factor: float = Field(32.0, description="K-factor for ELO rating updates (ignored if glicko_enabled)")
    elo_match_frequency: int = Field(5, description="Number of days between matches")
    elo_matches_per_run: int = Field(1, description="Number of matches to run each time")
    elo_weighted_by_magnitude: bool = Field(False, description="Weight ELO delta by P&L difference magnitude")
    elo_multi_factor_scoring: bool = Field(True, description="Use reliability scoring (P&L + Sharpe + momentum + drawdown)")
    elo_league_system: bool = Field(False, description="Use league-based allocation (champions, standard, relegation)")
    elo_league_champions_pct: float = Field(0.60, description="Budget % for top 3 (champions league)")
    elo_league_standard_pct: float = Field(0.30, description="Budget % for middle tickers")
    elo_league_relegation_pct: float = Field(0.10, description="Budget % for bottom 3 (relegation zone)")
    glicko_enabled: bool = Field(False, description="Use Glicko-2 instead of simple ELO")
    glicko_initial_rd: float = Field(350.0, description="Initial rating deviation (uncertainty)")
    glicko_initial_volatility: float = Field(0.06, description="Initial volatility")
    glicko_tau: float = Field(0.5, description="System constraint for volatility changes")
    elo_winners_only_mode: bool = Field(False, description="Only invest in top N winners by rating")
    elo_winners_count: int = Field(3, description="Number of top winners to invest in when winners_only_mode is True")
    elo_losers_only_mode: bool = Field(False, description="Only invest in bottom N losers by rating (buy the dip)")
    elo_losers_count: int = Field(3, description="Number of bottom losers to invest in when losers_only_mode is True")
    risk_per_trade_pct: float = Field(0.01, description="Risk per trade as fraction of deployable capital")
    atr_stop_multiplier: float = Field(1.5, description="ATR multiplier for stop placement")
    min_position_risk: float = Field(10.0, description="Minimum currency risk per trade to avoid micro positions")
    market_regime_filter_enabled: bool = Field(False, description="Enable market regime detection and allocation adjustment")
    market_regime_bear_allocation: float = Field(0.0, description="Allocation multiplier during bear markets (0.0 = stop buying)")
    market_regime_sideways_allocation: float = Field(0.5, description="Allocation multiplier during sideways markets")
    trend_analysis_enabled: bool = Field(True, description="Enable trend filtering before buys")
    rsi_overbought: float = Field(75, description="Skip buys if RSI above this")
    sma_short: int = Field(20, description="Short SMA period")
    sma_long: int = Field(50, description="Long SMA period")
    use_limit_orders: bool = Field(True, description="Use limit orders (vs market orders)")
    limit_order_buffer: float = Field(0.005, description="Max % above quote for limit orders")
    volume_anomaly_threshold: float = Field(3.0, description="Skip if volume > N x average")
    time_slicing_enabled: bool = Field(True, description="Split orders across time")
    time_slicing_batches: int = Field(3, description="Number of order batches")
    time_slicing_delay_minutes: int = Field(30, description="Minutes between batches")
    continuous_mode_enabled: bool = Field(False, description="Run continuously vs one-off")
    check_interval_minutes: int = Field(15, description="Minutes between opportunity scans")
    trading_start_hour_utc: int = Field(14, description="Market open hour (UTC)")
    trading_end_hour_utc: int = Field(21, description="Market close hour (UTC)")
    detect_dips: bool = Field(True, description="Buy on price dips")
    detect_breakouts: bool = Field(True, description="Buy on breakouts")
    min_confidence: float = Field(0.6, description="Min confidence for opportunity trades")
    universe: List[str] = Field(default_factory=list, description="Tickers eligible for buys")
    cron: str = Field("0 7 1 * *", description="Cron for monthly run")
    timezone: str = Field("Europe/Paris", description="Timezone for scheduling")
    broker_api_key: Optional[str] = Field(
        None,
        description="API key for live broker integrations (set via env BROKER_API_KEY)",
        alias="BROKER_API_KEY",
    )
    broker_api_secret: Optional[str] = Field(
        None,
        description="API secret for live broker integrations (set via env BROKER_API_SECRET)",
        alias="BROKER_API_SECRET",
    )
    broker_base_url: Optional[str] = Field(
        None,
        description="Base URL for live broker APIs (set via env BROKER_BASE_URL)",
        alias="BROKER_BASE_URL",
    )
    broker_type: str = Field("paper", description="Broker: paper or ibkr")
    ibkr_host: str = Field("127.0.0.1", description="IBKR TWS/Gateway host")
    ibkr_port: int = Field(7497, description="IBKR port (7497=TWS paper, 4002=Gateway paper)")
    ibkr_client_id: int = Field(1, description="IBKR client ID")
    log_level: str = Field("INFO", description="Logging level")

    # Short-term simulation overrides
    short_term_mode_enabled: bool = Field(False, description="Use short-term heuristics for simulator")
    short_sma_short: int = Field(5, description="Short-term SMA short period")
    short_sma_long: int = Field(10, description="Short-term SMA long period")
    short_rsi_period: int = Field(7, description="Short-term RSI period")
    short_rsi_overbought: float = Field(70.0, description="Short-term RSI overbought threshold")
    short_price_above_sma_factor: float = Field(0.98, description="Require price >= factor * SMA(short)")
    short_volume_anomaly_threshold: float = Field(4.0, description="Anomaly threshold multiplier for volume")

    model_config = {
        "env_prefix": "",
        "env_file": ".env"
    }

    @field_validator("stop_loss_pct", "take_profit_pct")
    @classmethod
    def validate_pct(cls, v: float) -> float:
        if v <= 0 or v >= 1:
            raise ValueError("percentage must be between 0 and 1")
        return v

    @classmethod
    def load(cls, yaml_path: Path | None = None) -> "Settings":
        yaml_path = yaml_path or DEFAULT_CONFIG
        data = {}
        if yaml_path.exists():
            with yaml_path.open("r", encoding="utf-8") as fh:
                raw_data = yaml.safe_load(fh) or {}
                # Flatten nested structures from YAML
                data = cls._flatten_yaml(raw_data)
        return cls(**data)
    
    @classmethod
    def _flatten_yaml(cls, raw_data: dict) -> dict:
        """Flatten nested YAML structure to match flat Settings fields."""
        data = {}
        for key, value in raw_data.items():
            if key in ("trend_analysis", "protections", "continuous_mode", "rebalance", "logging", "elo", "exploration"):
                # Nested structure - flatten the sub-fields
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if key == "trend_analysis":
                            if sub_key == "enabled":
                                data["trend_analysis_enabled"] = sub_value
                            elif sub_key == "rsi_overbought":
                                data["rsi_overbought"] = sub_value
                            elif sub_key == "sma_short":
                                data["sma_short"] = sub_value
                            elif sub_key == "sma_long":
                                data["sma_long"] = sub_value
                        elif key == "protections":
                            data[sub_key] = sub_value
                        elif key == "continuous_mode":
                            if sub_key == "enabled":
                                data["continuous_mode_enabled"] = sub_value
                            elif sub_key == "check_interval_minutes":
                                data["check_interval_minutes"] = sub_value
                            elif sub_key == "trading_hours":
                                data["trading_start_hour_utc"] = sub_value.get("start_hour_utc", 14)
                                data["trading_end_hour_utc"] = sub_value.get("end_hour_utc", 21)
                            elif sub_key == "opportunities":
                                data["detect_dips"] = sub_value.get("detect_dips", True)
                                data["detect_breakouts"] = sub_value.get("detect_breakouts", True)
                                data["min_confidence"] = sub_value.get("min_confidence", 0.6)
                        elif key == "rebalance":
                            if sub_key == "enabled":
                                data["rebalance_enabled"] = sub_value
                            elif sub_key == "winner_pct":
                                data["rebalance_winner_pct"] = sub_value
                            elif sub_key == "winner_sell_frac":
                                data["rebalance_winner_sell_frac"] = sub_value
                            elif sub_key == "loser_pct":
                                data["rebalance_loser_pct"] = sub_value
                            elif sub_key == "cron":
                                data["cron"] = sub_value
                            elif sub_key == "timezone":
                                data["timezone"] = sub_value
                        elif key == "elo":
                            if sub_key == "enabled":
                                data["elo_enabled"] = sub_value
                            elif sub_key == "initial_rating":
                                data["elo_initial_rating"] = sub_value
                            elif sub_key == "k_factor":
                                data["elo_k_factor"] = sub_value
                            elif sub_key == "match_frequency":
                                data["elo_match_frequency"] = sub_value
                            elif sub_key == "matches_per_run":
                                data["elo_matches_per_run"] = sub_value
                            elif sub_key == "weighted_by_magnitude":
                                data["elo_weighted_by_magnitude"] = sub_value
                            elif sub_key == "multi_factor_scoring":
                                data["elo_multi_factor_scoring"] = sub_value
                            elif sub_key == "league_system":
                                data["elo_league_system"] = sub_value
                            elif sub_key == "league_champions_pct":
                                data["elo_league_champions_pct"] = sub_value
                            elif sub_key == "league_standard_pct":
                                data["elo_league_standard_pct"] = sub_value
                            elif sub_key == "league_relegation_pct":
                                data["elo_league_relegation_pct"] = sub_value
                            elif sub_key == "glicko_enabled":
                                data["glicko_enabled"] = sub_value
                            elif sub_key == "glicko_initial_rd":
                                data["glicko_initial_rd"] = sub_value
                            elif sub_key == "glicko_initial_volatility":
                                data["glicko_initial_volatility"] = sub_value
                            elif sub_key == "glicko_tau":
                                data["glicko_tau"] = sub_value
                            elif sub_key == "winners_only_mode":
                                data["elo_winners_only_mode"] = sub_value
                            elif sub_key == "winners_count":
                                data["elo_winners_count"] = sub_value
                            elif sub_key == "losers_only_mode":
                                data["elo_losers_only_mode"] = sub_value
                            elif sub_key == "losers_count":
                                data["elo_losers_count"] = sub_value
                        elif key == "exploration":
                            if sub_key == "enabled":
                                data["exploration_enabled"] = sub_value
                            elif sub_key == "budget_pct":
                                data["exploration_budget_pct"] = sub_value
                            elif sub_key == "max_level":
                                data["exploration_max_level"] = sub_value
                            elif sub_key == "pnl_up_threshold":
                                data["exploration_pnl_up_threshold"] = sub_value
                            elif sub_key == "pnl_down_threshold":
                                data["exploration_pnl_down_threshold"] = sub_value
                            elif sub_key == "candidates":
                                data["exploration_candidates"] = sub_value
                        elif key == "logging":
                            if sub_key == "level":
                                data["log_level"] = sub_value
            else:
                # Top-level field - copy directly
                data[key] = value
        return data


def get_settings() -> Settings:
    return Settings.load()
