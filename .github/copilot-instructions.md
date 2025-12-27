# AMB Investment Bot - Project Setup Complete

## Setup Checklist
- [x] Verify that the copilot-instructions.md file in the .github directory is created. (Done: file added)
- [x] Clarify Project Requirements (Python 3.11 CLI bot; EU/US equities; 200€/mo DCA; 10% SL/15% TP; Linux hosting; IBKR broker)
- [x] Scaffold the Project (Done: Python scaffolding with Poetry, src/tests, config, CLI entrypoint)
- [x] Customize the Project (Done: paper broker + IBKR client, strategy with 10% SL / 15% TP, CLI commands)
- [x] Install Required Extensions (None needed)
- [x] Compile the Project (Deps installed including ib-insync)
- [x] Create and Run Task (Added VS Code tasks for pytest and one-off run)
- [x] Documentation Complete (README with IBKR setup, production checklist, next steps)

## Project Overview
**AMB Bot** is a Python 3.11+ automated DCA (Dollar-Cost Averaging) investment bot for EU/US equities.

### Features
- Monthly 200€ budget split across configurable universe (AAPL, MSFT, GOOGL, etc.)
- 10% stop-loss and 15% take-profit guards on all positions
- Two broker implementations:
  - `PaperBroker`: Simulated broker for testing
  - `IBKRClient`: Interactive Brokers via ib-insync (TWS/Gateway API)
- CLI via Typer: `amb-bot once` or `amb-bot simulate --cycles N`
- Config via YAML + environment variables

### Tech Stack
- Python 3.11+, Poetry for deps
- pydantic for config, typer+rich for CLI
- ib-insync for IBKR API
- pytest for testing

### Run Commands
```bash
# Install dependencies
poetry install

# Test with paper broker
poetry run amb-bot once

# Use IBKR (requires TWS/Gateway running)
BROKER_TYPE=ibkr IBKR_PORT=7497 poetry run amb-bot once
```

### Project Structure
```
AMB/
├── src/amb_bot/
│   ├── broker/
│   │   ├── base.py       # Abstract broker interface
│   │   ├── paper.py      # Simulated broker
│   │   └── ibkr.py       # Interactive Brokers client
│   ├── config.py         # Settings (YAML + env)
│   ├── strategy.py       # DCA + stop/take logic
│   └── main.py           # CLI entrypoint
├── tests/                # Unit tests
├── config/
│   └── defaults.yaml     # Default strategy params
├── .env.example          # Environment template
├── pyproject.toml        # Poetry dependencies
└── README.md             # Full setup guide
```

## Next Actions for User
1. Complete IBKR account setup and download TWS/IB Gateway
2. Enable API access in TWS settings (port 7497 for paper)
3. Test with paper trading: `BROKER_TYPE=ibkr IBKR_PORT=7497 poetry run amb-bot once`
4. Deploy to Linux host with monthly cron: `0 7 1 * * cd /path/to/AMB && poetry run amb-bot once`

## Development Notes
- Broker interface is async-first (all methods use `async`/`await`)
- IBKR requires TWS/Gateway running locally or remotely
- Strategy runs exits first (stop/take), then entries (DCA)
- Config merges YAML defaults with env overrides
