#!/bin/bash
###############################################################################
# 🔌 IB Gateway Systemd Service Manager for AMB Bot
#
# This script creates a systemd service to auto-start IB Gateway on VPS reboot
# 
# Usage:
#   sudo bash setup_gateway_service.sh
###############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

GATEWAY_USER="gateway"
GATEWAY_HOME="/home/$GATEWAY_USER"
DEPLOY_PATH="/opt/amb-bot"

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   🔌 IB Gateway - Systemd Service Setup${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
   echo -e "${RED}❌ This script must be run as root (sudo)${NC}"
   exit 1
fi

# Step 1: Create gateway user if doesn't exist
echo -e "\n${BLUE}[1/4]${NC} Setting up gateway user..."
if ! id "$GATEWAY_USER" &>/dev/null; then
    useradd -m -s /bin/bash $GATEWAY_USER
    echo -e "${GREEN}✅ Created user: $GATEWAY_USER${NC}"
else
    echo -e "${YELLOW}⚠️  User $GATEWAY_USER already exists${NC}"
fi

# Step 2: Download and install IB Gateway
echo -e "\n${BLUE}[2/4]${NC} Installing IB Gateway..."
GATEWAY_DIR="$GATEWAY_HOME/ibgateway"
mkdir -p $GATEWAY_DIR

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" = "aarch64" ]; then
    GATEWAY_URL="https://download2.interactivebrokers.com/installers/ibgateway/latest-standalone/ibgateway-latest-standalone-linux-aarch64.sh"
    echo "Detected: ARM64 (Raspberry Pi)"
else
    GATEWAY_URL="https://download2.interactivebrokers.com/installers/ibgateway/latest-standalone/ibgateway-latest-standalone-linux-x64.sh"
    echo "Detected: x86_64"
fi

echo "Downloading IB Gateway..."
wget -q "$GATEWAY_URL" -O "$GATEWAY_DIR/ibgateway-installer.sh"
chmod +x "$GATEWAY_DIR/ibgateway-installer.sh"

# Install silently (requires user to configure later)
echo "⚠️  IB Gateway installer downloaded"
echo "   User must install manually and configure IBKR credentials"

# Step 3: Create systemd service file
echo -e "\n${BLUE}[3/4]${NC} Creating systemd service file..."

cat > /etc/systemd/system/ibgateway.service << 'EOF'
[Unit]
Description=Interactive Brokers Gateway for AMB Bot
After=network.target
Wants=network-online.target

[Service]
Type=forking
User=gateway
Group=gateway
WorkingDirectory=/home/gateway/ibgateway

# Launch IB Gateway with display manager (Xvfb for headless)
ExecStartPre=/usr/bin/Xvfb :99 -screen 0 1024x768x24
ExecStart=/home/gateway/ibgateway/bin/ibgateway /home/gateway/ibgateway_config.ini
ExecStop=/bin/bash -c 'pkill -f "ibgateway" || true'

Restart=on-failure
RestartSec=30
StartLimitInterval=300
StartLimitBurst=5

# Permissions
PrivateTmp=false
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo -e "${GREEN}✅ Systemd service created${NC}"

# Step 4: Create config template
echo -e "\n${BLUE}[4/4]${NC} Creating IB Gateway configuration template..."

cat > "$GATEWAY_HOME/ibgateway_config.ini" << 'EOF'
[Configuration]
ibserver=127.0.0.1
ibserverport=4002
TZ=UTC
ReadOnly=no
Accept Incoming=No
Store Session=yes
EOF

chown $GATEWAY_USER:$GATEWAY_USER "$GATEWAY_HOME/ibgateway_config.ini"
chmod 600 "$GATEWAY_HOME/ibgateway_config.ini"

# Final instructions
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   ✅ Setup Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo "📋 Manual Steps Required:"
echo "   1. Install IB Gateway (as $GATEWAY_USER):"
echo "      ${YELLOW}sudo -u $GATEWAY_USER $GATEWAY_DIR/ibgateway-installer.sh${NC}"
echo ""
echo "   2. Configure IB Gateway:"
echo "      • Start the GUI installer"
echo "      • Login with your IBKR username/password"
echo "      • Enable API: Global Configuration → API → Settings"
echo "      • Change port to 4002 (paper trading)"
echo "      • Save and exit"
echo ""
echo "   3. Update config file:"
echo "      ${YELLOW}nano $GATEWAY_HOME/ibgateway_config.ini${NC}"
echo ""
echo "   4. Test manual start:"
echo "      ${YELLOW}systemctl start ibgateway${NC}"
echo "      ${YELLOW}systemctl status ibgateway${NC}"
echo ""
echo "   5. Enable auto-start:"
echo "      ${YELLOW}systemctl enable ibgateway${NC}"
echo ""
echo "⚠️  Note: X11 display server (Xvfb) required for headless mode"
echo "   Install if needed: ${YELLOW}apt install -y xvfb${NC}"
echo ""
echo "📞 Test IBKR Connection:"
echo "   ${YELLOW}$DEPLOY_PATH/test_ibkr_connection.py${NC}"
echo ""
