#!/bin/bash
# Script de démarrage d'IB Gateway

set -e

# Variables
GATEWAY_DIR="/opt/ibgateway"
DISPLAY=:99
LOG_DIR="/tmp/ibgateway-logs"

mkdir -p $LOG_DIR

# Démarrer Xvfb (serveur X virtuel) en arrière-plan si pas déjà lancé
if ! pgrep -x "Xvfb" > /dev/null; then
    echo "Démarrage du serveur X virtuel (Xvfb)..."
    Xvfb $DISPLAY -screen 0 1024x768x24 > $LOG_DIR/xvfb.log 2>&1 &
    XVFB_PID=$!
    sleep 2
fi

# Export des variables d'environnement
export DISPLAY=$DISPLAY
export PATH=$GATEWAY_DIR/bin:$PATH

# Déterminer le répertoire de Gateway
if [ -d "$GATEWAY_DIR/IBJts/ibgateway" ]; then
    GW_HOME="$GATEWAY_DIR/IBJts/ibgateway"
elif [ -d "$GATEWAY_DIR" ]; then
    GW_HOME="$GATEWAY_DIR"
else
    echo "ERREUR: IB Gateway non trouvé dans $GATEWAY_DIR"
    ls -la /opt/ 2>/dev/null || true
    exit 1
fi

echo "Répertoire Gateway: $GW_HOME"

# Chercher le script de démarrage
if [ -f "$GW_HOME/ibgateway" ]; then
    STARTUP_SCRIPT="$GW_HOME/ibgateway"
elif [ -f "$GATEWAY_DIR/ibgateway" ]; then
    STARTUP_SCRIPT="$GATEWAY_DIR/ibgateway"
else
    echo "ERREUR: Script de démarrage ibgateway non trouvé"
    find /opt -name "ibgateway" -type f 2>/dev/null || true
    exit 1
fi

echo "Script de démarrage: $STARTUP_SCRIPT"
echo "Démarrage d'IB Gateway..."

# Lancer IB Gateway
$STARTUP_SCRIPT > $LOG_DIR/gateway.log 2>&1 &
GW_PID=$!

echo "PID: $GW_PID"
echo "Attente de l'initialisation..."
sleep 90

# Vérifier que le port API est accessible
if nc -z localhost 4002 2>/dev/null; then
    echo "✓ IB Gateway démarré avec succès sur le port 4002"
else
    echo "⚠ Vérification du port en cours..."
    # Afficher quelques lignes des logs
    tail -20 $LOG_DIR/gateway.log || true
fi

# Garder le script actif (pour systemd)
wait $GW_PID
