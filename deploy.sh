#!/bin/bash
###############################################################################
# 🚀 AMB Bot - Vultr Deployment Script
# 
# Usage: 
#   1. Create a fresh Debian 12 VPS on Vultr
#   2. SSH as root: ssh root@your_vps_ip
#   3. Run: curl -sSL https://raw.githubusercontent.com/YOUR_REPO/main/deploy.sh | bash
#   OR
#   4. wget https://raw.githubusercontent.com/YOUR_REPO/main/deploy.sh && bash deploy.sh
#
# This script:
#   - Installs Python 3.11, Poetry, Git, systemd services
#   - Clones the repo and sets up venv
#   - Configures cron for monthly execution (1st of month @ 07:00 UTC)
#   - Sets up IB Gateway for IBKR broker integration
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
REPO="https://github.com/HeyShireen/AMB.git"
DEPLOY_PATH="/opt/amb-bot"
PYTHON_VERSION="3.11"
GATEWAY_USER="gateway"

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   🚀 AMB Bot - Vultr Deployment${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo -e "${RED}Cannot detect OS${NC}"
    exit 1
fi

echo "Detected OS: $OS"

# Step 1: Update system
echo -e "\n${BLUE}[1/7]${NC} Updating system packages..."

if [ "$OS" = "debian" ] || [ "$OS" = "ubuntu" ]; then
    apt update -y
    apt upgrade -y
    apt install -y curl wget git
    
    # Step 2: Install Python 3.11 and dependencies (Debian/Ubuntu)
    echo -e "\n${BLUE}[2/7]${NC} Installing Python ${PYTHON_VERSION} and build tools..."
    apt install -y software-properties-common
    add-apt-repository ppa:deadsnakes/ppa -y
    apt update -y
    apt install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev \
        build-essential libssl-dev libffi-dev
    
    # Set python3.11 as default
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1

elif [ "$OS" = "almalinux" ] || [ "$OS" = "rhel" ] || [ "$OS" = "centos" ]; then
    dnf update -y
    dnf install -y curl wget git
    
    # Step 2: Install Python 3.11 and dependencies (AlmaLinux/RHEL)
    echo -e "\n${BLUE}[2/7]${NC} Installing Python ${PYTHON_VERSION} and build tools..."
    dnf install -y gcc make openssl-devel bzip2-devel libffi-devel zlib-devel
    dnf groupinstall -y "Development Tools"
    
    # Install Python 3.11 from AppStream or compile
    dnf install -y python3.11 python3.11-devel
    
    # Set python3.11 as default
    alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

else
    echo -e "${RED}Unsupported OS: $OS${NC}"
    exit 1
fi

# Step 3: Install Poetry
echo -e "\n${BLUE}[3/7]${NC} Installing Poetry..."
pip3 install --upgrade pip setuptools wheel
pip3 install poetry

# Step 4: Clone repository
echo -e "\n${BLUE}[4/7]${NC} Cloning repository from ${REPO}..."
mkdir -p $(dirname $DEPLOY_PATH)
rm -rf $DEPLOY_PATH  # Clean up if exists
git clone $REPO $DEPLOY_PATH
cd $DEPLOY_PATH

# Step 5: Setup Python environment
echo -e "\n${BLUE}[5/7]${NC} Setting up Python virtual environment..."
python${PYTHON_VERSION} -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    poetry install --no-dev
fi

# Step 6: Create .env file
echo -e "\n${BLUE}[6/7]${NC} Creating .env configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  IMPORTANT: Edit your configuration${NC}"
    echo "nano $DEPLOY_PATH/.env"
    echo ""
    echo "Configure these IBKR settings:"
    echo "  BROKER_TYPE=ibkr"
    echo "  IBKR_HOST=127.0.0.1  (or your home IP if Gateway runs elsewhere)"
    echo "  IBKR_PORT=4002        (Gateway paper trading)"
    echo "  IBKR_CLIENT_ID=1"
    echo ""
    echo "And your strategy:"
    echo "  MONTHLY_BUDGET=200"
    echo "  STOP_LOSS_PCT=0.07"
    echo "  TAKE_PROFIT_PCT=0.25"
else
    echo "✅ .env already exists (skipped)"
fi

# Step 7: Setup Cron job
echo -e "\n${BLUE}[7/7]${NC} Configuring Cron for monthly execution..."

# Cron expression: 0 7 1 * * (1st day of month @ 07:00 UTC)
CRON_JOB="0 7 1 * * cd $DEPLOY_PATH && source venv/bin/activate && python -m amb_bot.main once >> logs/cron_\$(date +\\%Y\\%m\\%d_\\%H\\%M\\%S).log 2>&1"

# Create logs directory
mkdir -p $DEPLOY_PATH/logs
chmod 755 $DEPLOY_PATH/logs

# Add cron (avoid duplicates)
(crontab -l 2>/dev/null | grep -v "amb-bot.main once" ; echo "$CRON_JOB") | crontab -
crontab -l | grep "amb-bot.main once"

# Step 8: Optional - Install IB Gateway (systemd service)
echo -e "\n${YELLOW}[Optional] Installing IB Gateway as systemd service...${NC}"
read -p "Install IB Gateway on this VPS? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating IB Gateway setup..."
    
    # Create gateway user
    if ! id "$GATEWAY_USER" &>/dev/null; then
        useradd -m -s /bin/bash $GATEWAY_USER
        echo -e "${GREEN}✅ Created user: $GATEWAY_USER${NC}"
    fi
    
    # Download IB Gateway
    GATEWAY_DIR="/home/$GATEWAY_USER/ibgateway"
    mkdir -p $GATEWAY_DIR
    
    echo "Downloading IB Gateway (Linux x64)..."
    cd $GATEWAY_DIR
    
    # Check architecture
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ]; then
        GATEWAY_URL="https://download2.interactivebrokers.com/installers/ibgateway/latest-standalone/ibgateway-latest-standalone-linux-aarch64.sh"
    else
        GATEWAY_URL="https://download2.interactivebrokers.com/installers/ibgateway/latest-standalone/ibgateway-latest-standalone-linux-x64.sh"
    fi
    
    wget -q $GATEWAY_URL -O ibgateway-installer.sh
    chmod +x ibgateway-installer.sh
    
    # Create config file
    cat > /home/$GATEWAY_USER/ibgateway_config.ini << 'GATEWAY_CONFIG'
[Configuration]
ibserver=127.0.0.1
ibserverport=4002
ibserverport_paper=4002
TZ=UTC
ReadOnly=no
Accept Incoming=No
GATEWAY_CONFIG
    
    chown -R $GATEWAY_USER:$GATEWAY_USER /home/$GATEWAY_USER/ibgateway
    
    echo -e "${GREEN}✅ IB Gateway downloaded. Manual setup required:${NC}"
    echo "   1. Run installer: /home/$GATEWAY_USER/ibgateway/ibgateway-installer.sh"
    echo "   2. Login with your IBKR credentials"
    echo "   3. Enable API: Global Configuration → API → Settings"
    echo "   4. Start manually or create systemd service"
else
    echo -e "${YELLOW}Skipped IB Gateway installation${NC}"
    echo "Make sure TWS/Gateway is running on your home PC or another server"
fi

# Final checklist
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   ✅ Deployment Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo "📋 Next steps:"
echo "   1. Edit configuration:"
echo "      ${YELLOW}nano $DEPLOY_PATH/.env${NC}"
echo ""
echo "   2. Test the bot manually:"
echo "      ${YELLOW}cd $DEPLOY_PATH && source venv/bin/activate${NC}"
echo "      ${YELLOW}python -m amb_bot.main once${NC}"
echo ""
echo "   3. Check cron schedule:"
echo "      ${YELLOW}crontab -l${NC}"
echo ""
echo "   4. Monitor logs (after next 1st of month):"
echo "      ${YELLOW}tail -f $DEPLOY_PATH/logs/*.log${NC}"
echo ""
echo "   5. If using local TWS/Gateway, configure firewall:"
echo "      Open port 4002 (or 7497 for TWS paper)"
echo ""
echo "⏰ Bot will run automatically on:"
echo "   ${YELLOW}1st of every month @ 07:00 UTC${NC}"
echo ""
echo "📞 Troubleshooting:"
echo "   • Check system logs: ${YELLOW}journalctl -n 50${NC}"
echo "   • Check cron logs: ${YELLOW}grep CRON /var/log/syslog${NC}"
echo "   • Test IBKR connection: ${YELLOW}$DEPLOY_PATH/test_ibkr_connection.py${NC}"
echo ""
