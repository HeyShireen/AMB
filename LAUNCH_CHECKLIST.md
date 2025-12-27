# ✅ Pre-Launch Checklist - AMB Bot on Vultr

## 📋 Avant de Lancer le Deploy

- [ ] **GitHub repo créé et publié** (ou accessible en SSH)
  - [ ] Repo URL: `https://github.com/YOUR_USERNAME/AMB.git`
  - [ ] `.env.example` présent
  - [ ] `requirements.txt` à jour (`pip freeze > requirements.txt`)
  - [ ] Scripts dans le repo:
    - [ ] `deploy.sh`
    - [ ] `setup_gateway_service.sh`
    - [ ] `monitor.sh`
    - [ ] `test_ibkr_connection.py`

- [ ] **IBKR Account Setup** (si pas fait)
  - [ ] Compte créé sur Interactive Brokers
  - [ ] Identifiants username/password disponibles
  - [ ] TWS ou IB Gateway téléchargé
  - [ ] Décidé: Gateway sur VPS ou chez toi?

- [ ] **Vultr Account** 
  - [ ] Compte créé
  - [ ] Moyen de paiement ajouté
  - [ ] 5€ minimum crédité

---

## 🚀 Launch Day Steps

### Step 1: Créer le VPS (5 min)
```
Vultr Dashboard:
  → Deploy New Instance
  → Debian 12 (ou Ubuntu 22.04)
  → Location: Frankfurt / Paris
  → 1GB RAM / 1vCPU / 25GB SSD (2.50€/mois)
  → SSH Key: Generate or import
  → Click Deploy
```

**Résultat**: IP address (e.g., `45.32.123.45`)

- [ ] IP notée

### Step 2: SSH dans le VPS (1 min)
```powershell
# Windows
ssh root@45.32.123.45

# Enter password from Vultr dashboard
```

**Résultat**: `root@amb-bot:~#` prompt

- [ ] Connecté au VPS

### Step 3: Lancer le Deploy Script (10 min)
```bash
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/AMB/main/deploy.sh | bash
```

**Résultat**: Python, venv, dependencies, cron configurés

- [ ] Script complété sans erreurs

### Step 4: Configurer .env (5 min)
```bash
nano /opt/amb-bot/.env
```

Remplir:
```env
BROKER_TYPE=ibkr
IBKR_HOST=127.0.0.1  # ou IP locale si Gateway chez toi
IBKR_PORT=4002       # Gateway paper port
IBKR_CLIENT_ID=1

MONTHLY_BUDGET=200
STOP_LOSS_PCT=0.07
TAKE_PROFIT_PCT=0.25
```

- [ ] `.env` sauvegardé

### Step 5: Configurer IBKR Gateway (10-30 min)

#### Choix A: Gateway sur VPS
```bash
sudo bash /opt/amb-bot/setup_gateway_service.sh
sudo -u gateway /home/gateway/ibgateway/ibgateway-installer.sh
```
- [ ] Gateway installé
- [ ] Credentials IBKR entrés
- [ ] API enabled (Global Conf → API → Settings)
- [ ] Port changé en 4002

#### Choix B: Gateway chez toi
```bash
# Sur ton PC local:
# 1. Lancer TWS ou IB Gateway
# 2. Enable API + add VPS IP to whitelist
# 3. Note ton IP publique
```
- [ ] Gateway tournant
- [ ] Firewall ouvert pour IBKR

### Step 6: Test du Bot (5 min)
```bash
cd /opt/amb-bot
source venv/bin/activate

# Test 1: Bot works
python -m amb_bot.main once

# Test 2: IBKR connection
python -c "from ib_insync import IB; ib = IB(); ib.connect('127.0.0.1', 4002, clientId=1); print('✅ OK' if ib.isConnected() else '❌ FAIL'); ib.disconnect()"

# Test 3: Cron
crontab -l
```

**Résultat**: 
- [ ] Bot exécuté, trades affichés
- [ ] IBKR connecté
- [ ] Cron job visible

### Step 7: Monitoring (2 min)
```bash
bash /opt/amb-bot/monitor.sh
```

Vérifier:
- [ ] Cron scheduled correctly
- [ ] IBKR connection OK
- [ ] Configuration visible

---

## ✨ After Launch (Optional)

### Email Alerts (bonus)
```bash
# Ajouter au crontab pour logs by email
1 8 1 * * mail -s "AMB Report" your@email.com < /opt/amb-bot/logs/cron_$(date +\%Y\%m\%d).log
```

### Slack Notifications (bonus)
Edit `src/amb_bot/main.py`, add at end:
```python
import requests

def send_slack_alert(message):
    webhook = "https://hooks.slack.com/services/YOUR/WEBHOOK"
    requests.post(webhook, json={"text": message})

# After execute, call:
send_slack_alert(f"✅ AMB executed: {trades} trades, P&L: {pnl}")
```

### Backup to GitHub (bonus)
```bash
# Weekly backup cron
@weekly cd /opt/amb-bot && git add -A && git commit -m "Weekly backup" && git push
```

---

## 🔍 Troubleshooting Quick Links

| Issue | Solution |
|-------|----------|
| Bot ne s'exécute pas | `crontab -l` → `sudo systemctl restart cron` |
| IBKR connection fail | `ps aux \| grep gateway` → redémarrer |
| SSH key permission denied | `chmod 600 ~/.ssh/id_ed25519` |
| Git clone fails | Générer SSH key ou utiliser HTTPS token |
| Gateway not starting | `sudo systemctl start ibgateway` → `status` |

---

## 📞 Support

- **Logs**: `/opt/amb-bot/logs/cron_*.log`
- **Config**: `/opt/amb-bot/.env`
- **Cron**: `crontab -l`
- **Status**: `bash /opt/amb-bot/monitor.sh`
- **Manual test**: `cd /opt/amb-bot && source venv/bin/activate && python -m amb_bot.main once`

---

## 🎯 Success Criteria

✅ All boxes checked above = Bot ready for production

**Expected on 1st of next month @ 07:00 UTC**:
1. Bot wakes up
2. Connects to IBKR
3. Executes exits (stop/take)
4. Executes entries (DCA)
5. Saves logs
6. Sleep until next month

**Zero manual intervention needed!** 🚀

---

**Good luck! Questions? Check VULTR_GUIDE.md** 📖
