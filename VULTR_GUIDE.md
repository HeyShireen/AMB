# 🚀 Guide Complet: Déployer AMB Bot sur Vultr

## 1️⃣ Créer ton VPS Vultr

### Étape 1: Inscription
1. Créer compte: https://www.vultr.com
2. Ajouter moyen de paiement (PayPal OK)
3. Créditer le compte (~5€)

### Étape 2: Créer une instance
1. Cliquer **"Deploy New Instance"**
2. Choisir:
   - **Location**: Frankfurt (EU) ou Paris si disponible
   - **OS**: **Debian 12** (mieux supporté)
   - **Plan**: **Cloud Compute Regular**
     - **1 GB RAM** / **1 vCPU** / **25 GB SSD** = **2.50€/mois** ✅
3. SSH Key: Générer ou importer ta clé (optionnel, utiliser password sinon)
4. Hostname: `amb-bot`
5. Cliquer **Deploy** (5 secondes)

### Étape 3: Récupérer l'IP
```
Vultr Dashboard → Instances → amb-bot → IPv4 Address
Exemple: 45.32.123.45
```

---

## 2️⃣ SSH dans le VPS

### Depuis Windows (PowerShell):
```powershell
ssh root@45.32.123.45
# Entrer le password fourni par Vultr (ou clé SSH)
```

### Depuis Mac/Linux:
```bash
ssh root@45.32.123.45
```

**Succès** = Tu vois: `root@amb-bot:~#`

---

## 3️⃣ Déployer avec Script Auto

Une fois connecté au VPS:

```bash
# Télécharger le script de déploiement
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/AMB/main/deploy.sh | bash

# OU
wget https://raw.githubusercontent.com/YOUR_USERNAME/AMB/main/deploy.sh
bash deploy.sh
```

### ⚠️ REMPLACE dans le script:
Avant de lancer, ouvre le script et change:
```bash
REPO="https://github.com/YOUR_USERNAME/AMB.git"
```

Le script va:
- ✅ Installer Python 3.11, Poetry
- ✅ Cloner ton repo
- ✅ Installer les dépendances
- ✅ Créer `.env` (tu dois le configurer après)
- ✅ Configurer Cron pour exécuter le 1er du mois à 07h00 UTC
- ✅ Optionnellement installer IB Gateway

---

## 4️⃣ Configuration du `.env`

Après le déploiement:

```bash
nano /opt/amb-bot/.env
```

Remplis avec tes vraies données:
```env
BROKER_TYPE=ibkr
IBKR_HOST=127.0.0.1    # Si Gateway sur VPS
IBKR_HOST=your.home.ip # Si Gateway chez toi
IBKR_PORT=4002         # Gateway port
IBKR_CLIENT_ID=1

MONTHLY_BUDGET=200
STOP_LOSS_PCT=0.07
TAKE_PROFIT_PCT=0.25
```

Sauvegarde: `Ctrl+X` → `Y` → `Enter`

---

## 5️⃣ Options pour IBKR Gateway

### Option A: Gateway sur VPS (Recommandé si tu as pas besoin de TWS)

```bash
# Lancer le script de setup
sudo bash /opt/amb-bot/setup_gateway_service.sh

# Installer IB Gateway (mode interactif)
sudo -u gateway /home/gateway/ibgateway/ibgateway-installer.sh

# Lancer le service
sudo systemctl start ibgateway
sudo systemctl enable ibgateway  # Auto-start au reboot

# Vérifier status
sudo systemctl status ibgateway
```

**Avantage**: Tout sur VPS, pas besoin d'internet chez toi
**Inconvénient**: Dois configurer IB Gateway une fois

### Option B: Gateway chez toi (Plus simple)

1. **Laisse TWS/Gateway tournant** sur ton PC
2. **Dans `.env` du VPS**:
   ```env
   IBKR_HOST=your_home_ip
   IBKR_PORT=4002
   ```
3. **Ouvre le firewall** IB Gateway:
   - IB Gateway → Settings → API → Add IP whitelist
   - Ajoute l'IP publique du VPS Vultr

**Avantage**: Pas de configuration complexe
**Inconvénient**: Dois laisser ton PC allumé ou avoir Gateway ailleurs

---

## 6️⃣ Test du Déploiement

### Test 1: Vérifier que tout est installé
```bash
cd /opt/amb-bot
source venv/bin/activate
python -m amb_bot.main --version  # Doit afficher la version
```

### Test 2: Lancer le bot manuellement
```bash
cd /opt/amb-bot
source venv/bin/activate
python -m amb_bot.main once
# Doit afficher les positions et exécuter les trades
```

### Test 3: Vérifier la connexion IBKR
```bash
python -c "
from ib_insync import IB
ib = IB()
ib.connect('127.0.0.1', 4002, clientId=1)
print('✅ Connecté!' if ib.isConnected() else '❌ Erreur')
ib.disconnect()
"
```

### Test 4: Vérifier le Cron
```bash
crontab -l
# Doit afficher: 0 7 1 * * cd /opt/amb-bot && source venv/bin/activate && python -m amb_bot.main once >> logs/cron_...
```

---

## 7️⃣ Monitoring

### Dashboard en temps réel
```bash
bash /opt/amb-bot/monitor.sh
```

Affiche:
- Cron schedule
- Dernier résultat d'exécution
- Status IBKR
- Recommandations

### Voir les logs
```bash
# Logs des exécutions mensuelles
tail -f /opt/amb-bot/logs/cron_*.log

# Logs système (cron)
sudo grep CRON /var/log/syslog

# Logs continus
watch -n 5 "tail -20 /opt/amb-bot/logs/*.log"
```

---

## 8️⃣ Checklist de Production

- [ ] VPS Vultr créé
- [ ] SSH connecté
- [ ] Script deploy.sh lancé
- [ ] `.env` configuré avec vraies clés IBKR
- [ ] Test manuel: `python -m amb_bot.main once` ✅
- [ ] IBKR Gateway testé (Option A ou B)
- [ ] Cron job visible: `crontab -l`
- [ ] Logs directory créé: `/opt/amb-bot/logs`
- [ ] Dashboard monitoring fonctionne
- [ ] Reboot test: `sudo reboot` puis attendre 2min

---

## 9️⃣ Dépannage

### Bot ne s'exécute pas?
```bash
# 1. Vérifier cron
sudo service cron status
sudo systemctl restart cron

# 2. Vérifier logs système
sudo tail -50 /var/log/syslog | grep CRON

# 3. Test manuel
cd /opt/amb-bot && source venv/bin/activate
python -m amb_bot.main once
```

### IBKR connection échoue?
```bash
# Vérifier Gateway tourne
ps aux | grep ibgateway

# Tester la connection
python -c "
from ib_insync import IB
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=1, timeout=5)
    print('OK' if ib.isConnected() else 'FAIL')
    ib.disconnect()
except Exception as e:
    print(f'ERROR: {e}')
"

# Si error:
#  - Vérifier IBKR_HOST/IBKR_PORT dans .env
#  - Redémarrer Gateway: systemctl restart ibgateway
#  - Vérifier firewall: ufw allow 4002
```

### Git push ne fonctionne pas sur VPS?
```bash
# Générer SSH key
ssh-keygen -t ed25519 -C "your@email.com"
cat ~/.ssh/id_ed25519.pub  # Copier dans GitHub → Settings → SSH Keys

# Ou utiliser HTTPS token:
git config --global credential.helper store
# Puis pull/push avec ton token perso GitHub
```

---

## 🔟 Logs et Monitoring Continu

### Afficher les 10 derniers logs
```bash
ls -lah /opt/amb-bot/logs/cron_*.log | tail -10
```

### Archiver les vieux logs (optionnel)
```bash
# Ajouter au crontab (nettoyage monthly)
@monthly find /opt/amb-bot/logs -name "cron_*.log" -mtime +30 -delete
```

### Envoyer les logs par email (optionnel)
```bash
# Edit crontab:
crontab -e

# Ajouter (après le bot):
1 8 1 * * mail -s "AMB Bot Report" your@email.com < /opt/amb-bot/logs/cron_$(date +\%Y\%m\%d).log
```

---

## 📊 Performance Expected

| Metric | Value |
|--------|-------|
| VPS Cost | 2.50€/mois |
| Uptime | 99.9%+ |
| Latency to IBKR | <50ms |
| RAM Usage | ~200MB |
| Disk Usage | ~2GB |
| Execution Time | ~1-2 min |

---

## 🎯 C'est fait!

Ton bot tourne maintenant **H24** sur Vultr pour seulement **2.50€/mois**. 🚀

**Le 1er de chaque mois à 07h00 UTC**, le bot va:
1. Se connecter à IBKR
2. Analyser les positions
3. Déclencher les stops/takes
4. DCA acheter les top 3 tickers
5. Sauvegarder les logs

Aucune action manuelle nécessaire! ✅

---

## Questions?

- Dashboard: `bash /opt/amb-bot/monitor.sh`
- Logs: `tail -f /opt/amb-bot/logs/cron_*.log`
- Slack/Email alerts (futur): À configurer dans `main.py`
