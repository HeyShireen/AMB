#!/bin/bash
set -e

echo "==================================="
echo "Installation d'IB Gateway + IBC"
echo "==================================="

# Variables de configuration
IB_VERSION="10.30"
IBC_VERSION="3.18.0"
INSTALL_BASE="/opt/ibgateway"
IBC_DIR="/opt/ibc"
USER="amb"

# 1. Installer les dépendances Java et X11
echo "[1/6] Installation des dépendances..."
sudo dnf install -y java-17-openjdk xorg-x11-server-Xvfb wget unzip socat

# 2. Créer les répertoires
echo "[2/6] Création des répertoires..."
sudo mkdir -p $INSTALL_BASE
sudo mkdir -p $IBC_DIR
sudo chown -R $USER:$USER $INSTALL_BASE $IBC_DIR

# 3. Télécharger et installer IB Gateway
echo "[3/6] Téléchargement d'IB Gateway..."
cd /tmp
wget -q --show-progress \
  "https://download2.interactivebrokers.com/installers/ibgateway/latest-standalone/ibgateway-latest-standalone-linux-x64.sh" \
  -O ibgateway-installer.sh

chmod +x ibgateway-installer.sh

echo "[4/6] Installation d'IB Gateway (mode silencieux)..."
# Installation en mode silencieux
sudo -u $USER ./ibgateway-installer.sh -q -dir $INSTALL_BASE

# 4. Télécharger et installer IBC
echo "[5/6] Installation d'IBC..."
cd /tmp
wget -q --show-progress \
  "https://github.com/IbcAlpha/IBC/releases/download/${IBC_VERSION}/IBCLinux-${IBC_VERSION}.zip" \
  -O ibc.zip

unzip -q ibc.zip -d $IBC_DIR
sudo chown -R $USER:$USER $IBC_DIR
chmod +x $IBC_DIR/*.sh
chmod +x $IBC_DIR/scripts/*.sh 2>/dev/null || true

# 5. Configuration finale
echo "[6/6] Configuration finale..."

# Créer le répertoire de configuration
mkdir -p ~/.config/ibgateway

echo ""
echo "==================================="
echo "✓ Installation terminée !"
echo "==================================="
echo "IB Gateway: $INSTALL_BASE"
echo "IBC: $IBC_DIR"
echo ""
echo "Prochaines étapes:"
echo "1. Configurer IBC avec vos credentials IBKR"
echo "2. Démarrer le service systemd"
echo ""
