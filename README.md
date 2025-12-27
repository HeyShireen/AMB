# AMB Investment Bot

Automated DCA bot for EU/US equities with 10% stop-loss and 15% take-profit guards. Targets 200€ monthly deployment, built for Python 3.11 and Linux hosting (works on Windows/macOS for dev).

## Features
- Monthly DCA across a configurable ticker universe
- Stop-loss / take-profit enforcement on open positions
- Pluggable broker client (paper broker included; production broker to be selected)
- CLI via `amb-bot` (Typer) for one-off runs and quick simulations
- Config via YAML + environment variables, `.env` supported

## Quick start
1. Install Poetry (or use your preferred venv tool).
2. Install deps:
   ```bash
   poetry install
   ```
3. Copy env template and adjust values:
   ```bash
   cp .env.example .env
   ```
4. Run once with the paper broker (simulated prices):
   ```bash
   poetry run amb-bot once
   ```
5. **Continuous monitoring mode** (recommended):
   ```bash
   poetry run amb-bot watch
   # Runs 24/7, scans every 15min, trades on opportunities
   # Press Ctrl+C to stop
   ```
6. **Monitor dashboard** (interactive terminal UI):
   ```bash
   poetry run amb-bot dashboard
   # Shows budget, positions, trades, opportunities
   ```
7. Check budget status:
   ```bash
   poetry run amb-bot status
   ```

## Configuration
- Edit `config/defaults.yaml` for default universe, budget, and limits.
- Environment variables (override YAML): see `.env.example` for keys (`BROKER_API_KEY`, `BROKER_API_SECRET`, `BROKER_BASE_URL`, `STOP_LOSS_PCT`, `TAKE_PROFIT_PCT`, etc.).
- Cron-like scheduling is not wired in; run via your host's scheduler (cron/systemd/k8s jobs). Use `CRON_EXPRESSION` as documentation only.

## Broker integration
Two brokers implemented:

### PaperBroker (default)
Simulated broker for testing. No setup required.
```bash
BROKER_TYPE=paper
```

### Interactive Brokers (IBKR)
1. Open IBKR account and complete setup
2. Download and install TWS (Trader Workstation) or IB Gateway
3. Enable API access in TWS/Gateway:
   - Global Configuration → API → Settings
   - Enable "ActiveX and Socket Clients"
   - Note the Socket port (7497 for paper, 7496 for live TWS; 4002/4001 for Gateway)
   - Add trusted IP (127.0.0.1 for local)
4. Start TWS/Gateway and login
5. Configure `.env`:
   ```bash
   BROKER_TYPE=ibkr
   IBKR_HOST=127.0.0.1
   IBKR_PORT=7497  # 7497=TWS paper, 4002=Gateway paper, 7496=TWS live, 4001=Gateway live
   IBKR_CLIENT_ID=1
   ```
6. Run bot while TWS/Gateway is active

**Important**: IBKR requires TWS/IB Gateway running locally. The bot connects via socket API (port 7497/7496/4002/4001).

## Strategy
### Two modes: One-off vs Continuous

**One-off mode** (`amb-bot once`):
- Monthly DCA: Equal-split budget across universe
- Runs once per month (via cron)

**Continuous mode** (`amb-bot watch`) 🆕:
- Runs 24/7, scans every 15 minutes
- Auto-manages monthly 200€ budget
- Trades on detected opportunities

### Entry signals (Continuous mode)
**Monthly DCA allocation**:
- Equal-split when new month starts
- Only if trend filters pass

**Dip buying** 🎯:
- Price drops 2-5% below SMA20 while in uptrend
- Allocates 10-20% of remaining budget based on dip size

**Breakout trading** 🚀:
- Price breaks above 20-day high with 1.5x volume
- Allocates 5-15% of remaining budget

**All entries filtered by**:
- RSI < 75 (avoid overbought)
- SMA20 > SMA50 (uptrend)
- Volume < 3x average (detect manipulation)
- Confidence ≥ 60%

### Exit (Risk management)
- **Stop-loss**: Exit if PnL ≤ -10% (fixed)
- **Take-profit**: Exit if PnL ≥ +15% (fixed)
- Checks every run (monthly by default)

### Anti-bot protections 🛡️
**Limit orders** (default enabled):
- Buys only if price ≤ quote + 0.5%
- Protects against sudden price spikes from HFT manipulation

**Volume anomaly detection**:
- Skips stocks with volume > 3x 20-day average
- Avoids pump & dump schemes

**Time-slicing**:
- Splits orders into 3 batches with 30min delays
- Reduces impact of flash crashes at specific times
- Example: 10 stocks → Batch 1 (3 stocks) @ 7:00, Batch 2 (3) @ 7:30, Batch 3 (4) @ 8:00

### Customization
Edit `config/defaults.yaml`:
```yaml
protections:
  use_limit_orders: false          # Disable for pure market orders
  limit_order_buffer: 0.01         # Allow 1% slippage instead of 0.5%
  volume_anomaly_threshold: 5.0    # More lenient (5x instead of 3x)
  time_slicing_enabled: false      # Execute all at once
  time_slicing_batches: 2          # Only 2 batches
  time_slicing_delay_minutes: 60   # 1 hour between batches
```

## Testing
```bash
poetry run pytest
```

## 🎯 Commands

```bash
# Run once (monthly DCA)
poetry run amb-bot once

# Continuous mode (24/7 opportunity scanner)
poetry run amb-bot watch

# Dashboard (interactive TUI monitoring)
poetry run amb-bot dashboard

# Check budget status
poetry run amb-bot status

# Simulate N monthly cycles
poetry run amb-bot simulate --cycles 3
```

## 📊 Dashboard Features

The TUI dashboard (`poetry run amb-bot dashboard`) shows:

- **Status bar** : Current time, market open/closed, bot status
- **Budget widget** : Monthly budget with progress bar and spent/remaining tracking
- **Positions widget** : All open positions with P&L in € and %
- **Trade history** : Last 10 trades with timestamp, type, qty, price
- **Opportunities widget** : Pending opportunities with confidence scores

## Hosting notes
- Target Linux host (e.g., small VM, container, or serverless cron). Schedule `poetry run amb-bot once` monthly.
- Ensure secrets are injected as env vars; avoid committing `.env`.

## Next steps
1. **IBKR Account**: Complete your Interactive Brokers account setup and fund it
2. **TWS/Gateway**: Download, install, and configure API access (see IBKR section above)
3. **Paper Trading**: Test with `IBKR_PORT=7497` (TWS paper) or `4002` (Gateway paper) first
4. **Production**: Switch to live ports (7496/4001) only after thorough paper testing
5. **Monitoring**: Add alerting (email/Slack/Discord) for trade confirmations and errors
6. **Scheduling**: Set up cron/systemd on Linux to run `amb-bot once` monthly
7. **Persistence**: Consider logging trades to DB/CSV for audit trail (IBKR stores orders)

## Production checklist
- [ ] IBKR account funded and verified
- [ ] TWS/Gateway installed with API enabled
- [ ] Paper trading tested successfully for 1+ month
- [ ] `.env` configured with correct ports and credentials
- [ ] Monthly scheduler configured (cron: `0 7 1 * *`)
- [ ] Monitoring/alerting set up
- [ ] Stop-loss and take-profit percentages validated

## Disclaimer
This code is for educational purposes only and comes with no warranty. Trading involves risk; validate against paper trading before using real funds. Ensure you understand IBKR's API terms and your regulatory obligations.
