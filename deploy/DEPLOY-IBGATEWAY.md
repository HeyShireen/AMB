# Déploiement d'IB Gateway sans Docker

## Étape 1 : Copier les fichiers sur le serveur

```bash
# Depuis votre machine locale
scp deploy/install-ibgateway-standalone.sh amb@vps-b53afda3:/home/amb/apps/AMB/AMB/deploy/
scp deploy/ibc-config-template.ini amb@vps-b53afda3:/home/amb/apps/AMB/AMB/deploy/
scp deploy/start-ibgateway-ibc.sh amb@vps-b53afda3:/home/amb/apps/AMB/AMB/deploy/
scp deploy/ibgateway-standalone.service amb@vps-b53afda3:/home/amb/apps/AMB/AMB/deploy/
```

## Étape 2 : Sur le serveur, installer IB Gateway + IBC

```bash
cd /home/amb/apps/AMB/AMB/deploy
chmod +x install-ibgateway-standalone.sh
./install-ibgateway-standalone.sh
```

## Étape 3 : Configurer IBC avec vos credentials IBKR

```bash
# Créer le répertoire de config
mkdir -p ~/.config/ibgateway

# Copier le template et éditer
cp ibc-config-template.ini ~/.config/ibgateway/ibc-config.ini
nano ~/.config/ibgateway/ibc-config.ini
```

**Modifiez ces lignes :**
- `IbLoginId=VOTRE_USERNAME_IBKR` → votre username IBKR
- `Password=VOTRE_PASSWORD_IBKR` → votre mot de passe
- `TradingMode=paper` → laissez "paper" pour le compte de simulation

**Sécurisez le fichier :**
```bash
chmod 600 ~/.config/ibgateway/ibc-config.ini
```

## Étape 4 : Configurer le service systemd

```bash
chmod +x start-ibgateway-ibc.sh
sudo cp ibgateway-standalone.service /etc/systemd/system/
sudo systemctl daemon-reload
```

## Étape 5 : Démarrer IB Gateway

```bash
sudo systemctl start ibgateway-standalone
sudo systemctl status ibgateway-standalone
```

**Vérifier les logs :**
```bash
sudo journalctl -u ibgateway-standalone -f
```

## Étape 6 : Tester la connexion

```bash
cd /home/amb/apps/AMB/AMB
source .venv/bin/activate
python test_ibkr_connection.py
```

## Étape 7 : Activer le démarrage automatique

```bash
sudo systemctl enable ibgateway-standalone
```

## Dépannage

### Le service ne démarre pas
```bash
# Vérifier les logs
sudo journalctl -u ibgateway-standalone -n 50

# Tester le script manuellement
cd /home/amb/apps/AMB/AMB/deploy
./start-ibgateway-ibc.sh
```

### Le port 4002 n'est pas accessible
```bash
# Vérifier que le processus écoute
ss -tlnp | grep 4002

# Vérifier les processus Java
ps aux | grep java
```

### Réinitialiser complètement
```bash
sudo systemctl stop ibgateway-standalone
pkill -9 -f java
pkill -9 -f Xvfb
sudo rm -rf /tmp/ibc-logs/*
sudo systemctl start ibgateway-standalone
```

## Commandes utiles

```bash
# Statut
sudo systemctl status ibgateway-standalone

# Arrêter
sudo systemctl stop ibgateway-standalone

# Redémarrer
sudo systemctl restart ibgateway-standalone

# Logs en temps réel
sudo journalctl -u ibgateway-standalone -f

# Désactiver le démarrage auto
sudo systemctl disable ibgateway-standalone
```
