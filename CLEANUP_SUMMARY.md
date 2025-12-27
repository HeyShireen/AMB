# 🧹 Nettoyage AMB Bot - Résumé

## ✅ Nettoyage Complété

### **Supprimés (inutiles)**
- ❌ `opportunities.py` - Détection de dips/breakouts (non nécessaire pour simple DCA)
- ❌ `dashboard.py` - Interface TUI Textual  
- ❌ `tui.py` - Interface TUI (terminal UI)
- ❌ `backtest_utils.py` - Utilitaires de backtest avancés
- ❌ `indicators.py` - Calculs d'indicateurs complexes
- ❌ `PaperBroker` - Broker simulé (on utilise IBKR API uniquement)
- ❌ `scan_and_trade()` - Logique opportunités complexe
- ❌ Commandes CLI: `watch`, `dashboard`, `backtest`
- ❌ Dépendances: `textual`, `click`, `httpx`

### **Simplifié (core business logic)**

#### `strategy.py` (de 582 → 181 lignes)
**Avant:** ELO ratings, Glicko-2, market regime detection, exploration, multi-factor scoring, league system
**Après:** Simple DCA pure + 10% SL / 15% TP

```python
plan_entries()    # DCA equal allocation across universe
plan_exits()      # Stop-loss à -10%, Take-profit à +15%
execute()         # Exits d'abord, puis entries
```

#### `main.py` (de 557 → 190 lignes)
**Avant:** watch, dashboard, backtest, scan_and_trade complexe
**Après:** 3 commandes simples

```
amb-bot once      # Single DCA + exits (idéal pour cron)
amb-bot simulate  # N cycles avec IBKR paper
amb-bot status    # Budget status
```

#### `pyproject.toml`
- ✂️ Supprimer: `textual`, `click`, `httpx`
- ✅ Garder: `ib-insync`, `typer`, `rich`, `pydantic`

### **Gardé (Core)**
- ✅ `broker/base.py` - Interface abstraite
- ✅ `broker/ibkr.py` - IBKR API client (seul broker supporté)
- ✅ `broker/backtest.py` - Backtest sur données IBKR (garder pour tests)
- ✅ `config.py` - Settings YAML + env
- ✅ `budget.py` - Suivi budget mensuel

## 🎯 Configuration pour Test Paper Trading

```bash
# Port 7497 = TWS Paper Trading (défaut)
export IBKR_HOST=127.0.0.1
export IBKR_PORT=7497

# Univers minimal
export UNIVERSE=AAPL,MSFT,GOOGL

# Budget
export MONTHLY_BUDGET=200

# SL/TP (configuré dans defaults.yaml)
stop_loss_pct: 0.10
take_profit_pct: 0.15
```

## 🚀 Commandes de Test

```bash
# Installation dépendances
poetry install

# Test unique (DCA + exits une fois)
poetry run amb-bot once

# Simulation N cycles
poetry run amb-bot simulate --cycles 6

# Voir budget
poetry run amb-bot status
```

## 📊 Architecture Finale

```
AMB/
├── src/amb_bot/
│   ├── broker/
│   │   ├── base.py          # Interface broker
│   │   ├── ibkr.py          # IBKR API (seul broker)
│   │   └── backtest.py       # Backtest sur IBKR data
│   ├── main.py              # CLI: once, simulate, status
│   ├── strategy.py          # DCA simple + 10% SL / 15% TP
│   ├── config.py            # Settings
│   ├── budget.py            # Budget tracking
│   └── __init__.py
├── config/
│   └── defaults.yaml        # Defaults: universe, params
├── pyproject.toml          # Deps (lightened)
└── README.md               # Docs
```

## 🔄 Flux d'Exécution (once)

1. **Connexion** → IBKR (port 7497 = paper)
2. **Phase 1: Exits** → Check stop-loss (-10%) / take-profit (+15%)
3. **Phase 2: Entries** → DCA: split monthly budget equally across universe
4. **Déconnexion** → Close IBKR connection

## ✨ Améliorations

- **Code épuré** : 582 → 181 lignes dans strategy.py
- **Dépendances allégées** : -5 dépendances inutiles
- **API-only** : Pas de simulation locale, IBKR API pour tous les tests
- **Simple & maintenable** : DCA pur + exits basiques
- **Ready for production** : Cron-friendly avec `amb-bot once`

## ⚠️ Notes

- **Paper trading**: Connectez-vous à IBKR TWS/Gateway en mode paper (port 7497)
- **Production**: Changez simplement le port à 7496 (live) quand prêt
- **Backtest**: Nécessite IBKR Gateway connecté pour données historiques

---

**Date**: 27 décembre 2025  
**Status**: ✅ Ready for official paper trading test
