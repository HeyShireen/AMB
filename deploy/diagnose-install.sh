#!/bin/bash
# Diagnostic et installation manuelle d'IB Gateway

set -e

echo "=== Diagnostic IB Gateway ==="
echo ""

# Vérifier les dépendances
echo "[1] Vérification des dépendances..."
for cmd in java wget unzip nc; do
    if command -v $cmd &> /dev/null; then
        echo "  ✓ $cmd trouvé"
    else
        echo "  ✗ $cmd MANQUANT"
    fi
done
echo ""

# Nettoyer les anciennes installations
echo "[2] Nettoyage des anciennes installations..."
sudo rm -rf /opt/ibgateway /opt/ibc
mkdir -p /tmp/ibgateway-install
cd /tmp/ibgateway-install
echo "  Répertoire de travail: $(pwd)"
echo ""

# Télécharger directement depuis la source
echo "[3] Téléchargement d'IB Gateway..."
echo "  URL: https://download2.interactivebrokers.com/installers/ibgateway/stable-standalone/ibgateway-stable-standalone-linux-x64.sh"

# Essayer le téléchargement
if wget --no-verbose --show-progress \
  "https://download2.interactivebrokers.com/installers/ibgateway/stable-standalone/ibgateway-stable-standalone-linux-x64.sh" \
  -O ibgateway.sh 2>&1 | tee download.log; then
    echo "  ✓ Téléchargement réussi"
    ls -lh ibgateway.sh
else
    echo "  ✗ Téléchargement échoué"
    echo "  Contenu du log:"
    cat download.log
    echo ""
    echo "  Essai avec URL alternative..."
    wget --no-verbose --show-progress \
      "https://download2.interactivebrokers.com/installers/ibgateway/latest-standalone/ibgateway-latest-standalone-linux-x64.sh" \
      -O ibgateway.sh 2>&1 | tee download.log
fi

echo ""
echo "[4] Installation d'IB Gateway..."
chmod +x ibgateway.sh
./ibgateway.sh -h 2>&1 | head -20 || true
echo ""

# Installer en mode silencieux
echo "  Lancement du script d'installation..."
sudo ./ibgateway.sh -q -dir /opt/ibgateway 2>&1 | tee install.log || true

# Vérifier l'installation
echo ""
echo "[5] Vérification de l'installation..."
if [ -d "/opt/ibgateway" ]; then
    echo "  ✓ Répertoire /opt/ibgateway créé"
    echo "  Contenu:"
    sudo ls -la /opt/ibgateway/ | head -20
else
    echo "  ✗ Répertoire /opt/ibgateway NON créé"
fi

echo ""
echo "[6] Téléchargement et installation d'IBC..."
cd /tmp/ibgateway-install
wget --no-verbose --show-progress \
  "https://github.com/IbcAlpha/IBC/releases/download/3.18.0/IBCLinux-3.18.0.zip" \
  -O ibc.zip 2>&1 | tee ibc-download.log

if [ -f "ibc.zip" ]; then
    echo "  ✓ IBC téléchargé"
    sudo mkdir -p /opt/ibc
    sudo unzip -q ibc.zip -d /opt/ibc
    sudo chmod +x /opt/ibc/*.sh
    echo "  ✓ IBC installé"
    sudo ls -la /opt/ibc/ | head -20
else
    echo "  ✗ Impossible de télécharger IBC"
fi

echo ""
echo "=== Installation terminée ==="
echo ""
echo "Prochaines étapes:"
echo "1. Vérifier que /opt/ibgateway et /opt/ibc sont créés"
echo "2. Configurer IBC avec vos credentials"
echo "3. Démarrer le service systemd"
echo ""
