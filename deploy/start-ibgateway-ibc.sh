#!/bin/bash
# Script de démarrage d'IB Gateway avec IBC

set -e

# Variables
IBC_DIR="/opt/ibc"
GATEWAY_DIR="/opt/ibgateway"
CONFIG_FILE="/home/amb/.config/ibgateway/ibc-config.ini"
DISPLAY=:99

# Vérifier que le fichier de configuration existe
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERREUR: Fichier de configuration manquant: $CONFIG_FILE"
    echo "Copiez ibc-config-template.ini vers $CONFIG_FILE et ajoutez vos credentials"
    exit 1
fi

# Démarrer Xvfb (serveur X virtuel) en arrière-plan si pas déjà lancé
if ! pgrep -x "Xvfb" > /dev/null; then
    echo "Démarrage du serveur X virtuel (Xvfb)..."
    Xvfb $DISPLAY -screen 0 1024x768x24 &
    XVFB_PID=$!
    sleep 2
fi

# Export des variables d'environnement
export DISPLAY=$DISPLAY
export TWS_MAJOR_VRSN=10.30
export IBC_INI=$CONFIG_FILE
export TWS_PATH=$GATEWAY_DIR
export IBC_PATH=$IBC_DIR
export LOG_PATH=/tmp/ibc-logs
export JAVA_PATH=/usr/bin/java

# Créer le répertoire de logs
mkdir -p $LOG_PATH

# Lancer IB Gateway via IBC
echo "Démarrage d'IB Gateway..."
cd $IBC_DIR
./gatewaystart.sh -inline &

# Attendre que Gateway soit prêt
echo "Attente de l'initialisation de Gateway (peut prendre 1-2 minutes)..."
sleep 60

# Vérifier que le port API est accessible
if nc -z localhost 4002 2>/dev/null; then
    echo "✓ IB Gateway démarré avec succès sur le port 4002"
else
    echo "⚠ IB Gateway démarré mais le port 4002 n'est pas encore accessible"
    echo "  Vérifiez les logs dans $LOG_PATH"
fi

# Garder le script actif (pour systemd)
wait
