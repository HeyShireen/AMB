#!/bin/bash
# Quick deploy script - syncs local code to OVH VPS
# Usage: ./deploy.sh user@your-vps-ip

set -e

if [ -z "$1" ]; then
    echo "Usage: ./deploy.sh user@host"
    echo "Example: ./deploy.sh amb@123.45.67.89"
    exit 1
fi

TARGET="$1"
REMOTE_DIR="/opt/amb-bot"

echo "🚀 Deploying AMB Bot to $TARGET..."

# Sync code (excluding venv, cache, etc.)
rsync -avz --progress \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    --exclude '.env' \
    --exclude 'logs/' \
    --exclude 'data/' \
    --exclude '.mypy_cache' \
    --exclude '.pytest_cache' \
    --exclude '.ruff_cache' \
    . "$TARGET:$REMOTE_DIR/"

echo "📦 Installing dependencies on remote..."
ssh "$TARGET" "cd $REMOTE_DIR && source .venv/bin/activate && pip install -r requirements.txt"

echo "🔄 Restarting service..."
ssh "$TARGET" "sudo systemctl restart amb-bot.timer"

echo "✅ Deployment complete!"
echo "📋 Check status: ssh $TARGET 'systemctl status amb-bot.timer'"
