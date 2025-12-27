# 🚀 Déploiement AMB Bot sur OVH

## 1. Choisir un VPS OVH

### Recommandation : VPS Starter ou Essential
- **VPS Starter** (~3.50€/mois) : 1 vCPU, 2GB RAM, 20GB SSD
- **VPS Essential** (~6€/mois) : 2 vCPU, 4GB RAM, 40GB SSD ✅ Recommandé

👉 [Commander un VPS OVH](https://www.ovhcloud.com/fr/vps/)

### Configuration
- **OS** : Ubuntu 22.04 LTS ou Debian 12
- **Localisation** : Gravelines (France) ou Francfort (Allemagne)
- **Options** : Backup automatique (optionnel)

---

## 2. Connexion au VPS

```bash
# Depuis votre terminal Windows (PowerShell)
ssh root@VOTRE_IP_VPS

# Créer un utilisateur dédié
adduser amb
usermod -aG sudo amb

# Se reconnecter avec le nouvel utilisateur
exit
ssh amb@VOTRE_IP_VPS
```

---

## 3. Installation du Bot

```bash
# Cloner le projet
cd /opt
sudo git clone https://github.com/VOTRE_REPO/AMB.git amb-bot
sudo chown -R amb:amb /opt/amb-bot
cd /opt/amb-bot

# Lancer l'installation
chmod +x deploy/install.sh
./deploy/install.sh
```

---

## 4. Configuration

### Fichier .env
```bash
nano /opt/amb-bot/.env
```

```env
# Broker
BROKER_TYPE=ibkr
IBKR_HOST=127.0.0.1
IBKR_PORT=4001
IBKR_CLIENT_ID=1

# Strategy
MONTHLY_BUDGET=200
STOP_LOSS_PCT=0.07
TAKE_PROFIT_PCT=0.25

# Timezone
TZ=Europe/Paris
```

---

## 5. IB Gateway (IBKR API)

### Option A : IB Gateway + IBC (Headless - Recommandé)

```bash
# Installer les dépendances
sudo apt install -y openjdk-11-jre xvfb

# Télécharger IB Gateway
cd /opt
wget https://download2.interactivebrokers.com/installers/ibgateway/stable-standalone/ibgateway-stable-standalone-linux-x64.sh
chmod +x ibgateway-stable-standalone-linux-x64.sh
sudo ./ibgateway-stable-standalone-linux-x64.sh -q

# Installer IBC (automatise la connexion)
wget https://github.com/IbcAlpha/IBC/releases/download/3.18.0/IBCLinux-3.18.0.zip
unzip IBCLinux-3.18.0.zip -d /opt/ibc

# Configurer IBC
nano /opt/ibc/config.ini
```

**config.ini** :
```ini
IbLoginId=VOTRE_LOGIN_IBKR
IbPassword=VOTRE_PASSWORD
TradingMode=paper  # ou 'live' pour le réel
IbDir=/opt/ibgateway
AcceptIncomingConnectionAction=accept
AcceptNonBrokerageAccountWarning=yes
```

### Service IB Gateway
```bash
sudo nano /etc/systemd/system/ibgateway.service
```

```ini
[Unit]
Description=IB Gateway
After=network.target

[Service]
Type=simple
User=amb
Environment="DISPLAY=:1"
ExecStartPre=/usr/bin/Xvfb :1 -screen 0 1024x768x24 &
ExecStart=/opt/ibc/scripts/ibcstart.sh -g
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable ibgateway
sudo systemctl start ibgateway
```

---

## 6. Démarrer le Bot

### Exécution manuelle (test)
```bash
cd /opt/amb-bot
source .venv/bin/activate
python -m amb_bot.main once
```

### Timer mensuel (production)
```bash
# Activer le timer systemd
sudo cp deploy/amb-bot.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable amb-bot.timer
sudo systemctl start amb-bot.timer

# Vérifier le prochain run
systemctl list-timers amb-bot.timer
```

### Ou via Cron (alternative)
```bash
crontab -e
```
```cron
# Exécuter le 1er de chaque mois à 8h00
0 8 1 * * cd /opt/amb-bot && /opt/amb-bot/.venv/bin/python -m amb_bot.main once >> /opt/amb-bot/logs/cron.log 2>&1
```

---

## 7. Monitoring

### Logs
```bash
# Logs du bot
tail -f /opt/amb-bot/logs/amb-bot.log

# Logs systemd
journalctl -u amb-bot -f
journalctl -u ibgateway -f
```

### Alertes (optionnel)
Ajoutez un webhook Discord/Telegram dans le bot pour recevoir les notifications de trades.

---

## 8. Sécurité

```bash
# Firewall
sudo ufw allow ssh
sudo ufw enable

# Mises à jour automatiques
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 📊 Coûts estimés

| Élément | Coût mensuel |
|---------|-------------|
| VPS OVH Essential | ~6€ |
| Commissions IBKR | ~10-20€ (selon volume) |
| **Total** | **~16-26€/mois** |

---

## ⚠️ Checklist avant production

- [ ] VPS OVH commandé et accessible
- [ ] Compte IBKR avec API activée
- [ ] IB Gateway configuré et connecté
- [ ] `.env` configuré avec credentials
- [ ] Test avec `python -m amb_bot.main once`
- [ ] Timer/Cron activé
- [ ] Backup automatique OVH activé
