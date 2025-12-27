#!/bin/bash
# AMB Bot - Installation script for OVH VPS (Ubuntu 22.04 / Debian 12)
set -e

echo "🚀 Installing AMB Trading Bot..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+ and dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip git curl

# Create app directory
sudo mkdir -p /opt/amb-bot
sudo chown $USER:$USER /opt/amb-bot

# Clone or copy project
cd /opt/amb-bot

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create logs directory
mkdir -p /opt/amb-bot/logs

# Setup environment file
if [ ! -f /opt/amb-bot/.env ]; then
    cp .env.example .env
    echo "⚠️  Please edit /opt/amb-bot/.env with your IBKR credentials"
fi

# Install systemd service
sudo cp deploy/amb-bot.service /etc/systemd/system/
sudo systemctl daemon-reload

echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit /opt/amb-bot/.env with your IBKR credentials"
echo "2. Start IB Gateway (see deploy/ibgateway-setup.md)"
echo "3. Enable the service: sudo systemctl enable amb-bot"
echo "4. Start the service: sudo systemctl start amb-bot"
echo "5. Check logs: journalctl -u amb-bot -f"
