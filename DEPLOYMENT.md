# 🚀 Déploiement H24 - AMB Bot (Budget: 2.5-5€/mois)

## Option 1: **VPS Linux + Cron** (Recommandé) ✨
**Coût**: 2.5-5€/mois | **Maintenance**: Très facile | **Perfs**: Excellentes

### Étape 1: Choisir un VPS
| Fournisseur | RAM | CPU | Prix/mois | Lien |
|-------------|-----|-----|-----------|------|
| **Vultr** | 1GB | 1 | 2.50€ | https://www.vultr.com |
| **Linode** | 1GB | 1 | 5€ | https://www.linode.com |
| **Hetzner** | 1GB | 1 | 3€ | https://www.hetzner.com |
| **DigitalOcean** | 512MB | 1 | 4€ | https://www.digitalocean.com |

**Recommandation**: Vultr (payment method PayPal OK)

### Étape 2: Configuration initiale du VPS
```bash
# SSH dans ton VPS (depuis ton PC ou terminal)
ssh root@your_vps_ip

# Mise à jour
apt update && apt upgrade -y

# Installation dépendances Python
apt install -y python3.11 python3.11-venv python3-pip git curl wget

# Clone ton repo (créer SSH key sur GitHub ou utiliser HTTPS)
cd /opt
git clone https://github.com/ton_username/AMB.git
cd AMB

# Créer venv
python3.11 -m venv venv
source venv/bin/activate

# Installer dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
# OU avec Poetry:
pip install poetry
poetry install --no-dev
```

### Étape 3: Configuration `.env` sur VPS
```bash
# Copier le .env template
cp .env.example .env
nano .env

# Remplir avec tes vraies clés:
BROKER_TYPE=ibkr
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
IBKR_CLIENT_ID=1
INITIAL_CASH=10000
MONTHLY_BUDGET=200
```

### Étape 4: Configuration Cron (Exécution mensuelle automatique)
```bash
# Ouvrir crontab
crontab -e

# Ajouter cette ligne (exécute le 1er de chaque mois à 07h00 UTC):
0 7 1 * * cd /opt/AMB && /opt/AMB/venv/bin/python -m amb_bot.main once >> /opt/AMB/logs/cron_$(date +\%Y\%m\%d).log 2>&1

# Créer le dossier logs
mkdir -p /opt/AMB/logs

# Vérifier la crontab
crontab -l
```

### Étape 5: **IMPORTANT - Gérer IBKR Gateway**
Tu as **2 choix**:

#### **Option A: IB Gateway sur VPS** (Recommandé)
```bash
# 1. Télécharger IB Gateway (Linux)
cd /opt
wget https://download2.interactivebrokers.com/installers/ibgateway/latest-standalone/ibgateway-latest-standalone-linux-x64.sh
chmod +x ibgateway-latest-standalone-linux-x64.sh

# 2. Installer
./ibgateway-latest-standalone-linux-x64.sh

# 3. Créer script de démarrage automatique
cat > /opt/AMB/start_gateway.sh << 'EOF'
#!/bin/bash
# Lance IB Gateway en arrière-plan chaque jour à 06:55 (avant le bot)
export DISPLAY=:99
nohup /root/ibgateway/bin/ibgateway /opt/AMB/ibgateway_config.ini > /opt/AMB/logs/gateway.log 2>&1 &
EOF
chmod +x /opt/AMB/start_gateway.sh

# 4. Ajouter au crontab (avant le bot):
55 6 1 * * /opt/AMB/start_gateway.sh
0 7 1 * * cd /opt/AMB && /opt/AMB/venv/bin/python -m amb_bot.main once >> /opt/AMB/logs/cron.log 2>&1
```

#### **Option B: IB Gateway sur ton PC local** (Simple)
```bash
# 1. Laisse TWS/Gateway tournant chez toi
# 2. Configure l'accès distant dans IB Gateway:
#    - Global Configuration → API
#    - Trusted IP: x.x.x.x (l'IP publique de ton VPS)

# 3. Dans .env du VPS:
IBKR_HOST=your_home_ip_or_ddns
IBKR_PORT=4002  # Gateway port
```

### Étape 6: Monitoring et Logs
```bash
# Voir les logs du dernier run
tail -f /opt/AMB/logs/cron*.log

# Vérifier si cron s'est exécuté
grep CRON /var/log/syslog

# Test du bot manuellement
cd /opt/AMB
source venv/bin/activate
python -m amb_bot.main once
```

---

## Option 2: **Raspberry Pi chez toi** 🍓
**Coût**: 60€ (Raspberry Pi 5 avec alim) + 0€/mois | **Maintenance**: Moyenne

### Étape 1: Hardware
```
- Raspberry Pi 5 (8GB): 70€
- SD card 128GB: 15€
- Alimentation: 10€
Total: ~100€ one-time
```

### Étape 2: OS
```bash
# Flasher Raspberry Pi OS (Lite 64-bit)
# https://www.raspberrypi.com/software/

# SSH et config initiale (même que VPS mais plus facile)
```

### Étape 3: IBKR Gateway natif
```bash
# Installer directement sur Pi
wget https://download2.interactivebrokers.com/installers/ibgateway/latest-standalone/ibgateway-latest-standalone-linux-aarch64.sh
chmod +x ibgateway-latest-standalone-linux-aarch64.sh
./ibgateway-latest-standalone-linux-aarch64.sh
```

---

## Option 3: **Replit / AWS Lambda** (Gratuit, limité)
**⚠️ Non recommandé** car:
- Timeout after 15min (Lambda)
- Cold starts
- IBKR Gateway pas facile à intégrer

---

## 🔑 Checklist Production

- [ ] VPS créé et SSH accessible
- [ ] Python 3.11+ et Poetry/pip installés
- [ ] Code cloné et `.env` configuré
- [ ] `requirements.txt` ou `poetry.lock` à jour
- [ ] IBKR Gateway/TWS testé (connection test)
- [ ] Cron job configuré (1er du mois à 07h00)
- [ ] Dossier `/logs` créé et writable
- [ ] Test: `poetry run amb-bot once` exécuté avec succès
- [ ] Logs affichent "Order placed" ou "Position updated"
- [ ] VPS reboot test: assurer que Gateway redémarre auto

---

## 📊 Coûts estimés

| Option | Setup | Mensuel | Notes |
|--------|-------|---------|-------|
| **VPS Vultr** | 0€ | 2.5€ | ✅ Best value |
| **Linode** | 0€ | 5€ | Fiable |
| **Raspberry Pi** | 100€ | 0€ | DIY, mais électricité +5€ |
| **Heroku** | 0€ | 7€ (dyno) | Pas bon pour cron |

---

## 🚨 Troubleshooting

### Bot ne s'exécute pas?
```bash
# Vérifier crontab
crontab -l

# Voir logs système
tail -20 /var/log/syslog | grep CRON

# Test manuel
cd /opt/AMB && source venv/bin/activate
python -m amb_bot.main once
```

### Connection IBKR échoue?
```bash
# Vérifier si Gateway tourne
ps aux | grep ibgateway

# Tester la connection
python -c "
from ib_insync import *
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)
print('Connected!' if ib.isConnected() else 'Failed')
ib.disconnect()
"
```

### Git pull du code échoue?
```bash
# Ajouter SSH key GitHub
ssh-keygen -t ed25519 -C "your@email.com"
cat ~/.ssh/id_ed25519.pub  # Ajouter à GitHub Settings

# Ou utiliser HTTPS avec token:
git clone https://your_token@github.com/username/repo.git
```

---

## 📝 Script de déploiement automatisé
```bash
#!/bin/bash
# deploy.sh - Deploy AMB bot on fresh VPS

set -e

echo "🚀 Déploiement AMB Bot..."

# Vars
REPO="https://github.com/your_username/AMB.git"
DEPLOY_PATH="/opt/AMB"
PYTHON_VERSION="3.11"

# 1. Update system
apt update && apt upgrade -y
apt install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv git curl

# 2. Clone repo
mkdir -p $(dirname $DEPLOY_PATH)
git clone $REPO $DEPLOY_PATH
cd $DEPLOY_PATH

# 3. Setup venv
python${PYTHON_VERSION} -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Create .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Edit .env with your credentials!"
fi

# 5. Create logs dir
mkdir -p logs

# 6. Setup cron
CRON_JOB="0 7 1 * * cd $DEPLOY_PATH && source venv/bin/activate && python -m amb_bot.main once >> logs/cron_\$(date +\%Y\%m\%d).log 2>&1"
(crontab -l 2>/dev/null | grep -v "amb-bot" ; echo "$CRON_JOB") | crontab -

echo "✅ Déploiement réussi!"
echo "📋 Checklist:"
echo "  1. SSH dans le VPS: ssh root@your_ip"
echo "  2. Edit .env: nano $DEPLOY_PATH/.env"
echo "  3. Test: cd $DEPLOY_PATH && source venv/bin/activate && python -m amb_bot.main once"
echo "  4. Vérifier logs: tail -f $DEPLOY_PATH/logs/*.log"
```

Sauvegarde ce script et exécute: `bash deploy.sh`

---

**Quelle option tu préfères?** VPS ou Raspberry Pi? Je vais t'aider à te mettre en place! 🎯
