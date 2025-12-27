#!/bin/bash
###############################################################################
# 📊 AMB Bot - Monitoring Dashboard
#
# Real-time monitoring of AMB Bot on VPS
# Shows: Cron schedule, Latest logs, IBKR connection, Position status
#
# Usage: bash monitor.sh
###############################################################################

set -e

DEPLOY_PATH="/opt/amb-bot"
LOG_DIR="$DEPLOY_PATH/logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

clear

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   📊 AMB Bot - Monitoring Dashboard${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

# 1. Show cron schedule
echo -e "${CYAN}⏰ Cron Schedule:${NC}"
crontab -l 2>/dev/null | grep "amb-bot.main once" || echo "❌ No cron job found"
echo ""

# 2. Show last execution
echo -e "${CYAN}📈 Last Execution:${NC}"
if [ -d "$LOG_DIR" ]; then
    LATEST_LOG=$(ls -t "$LOG_DIR"/cron_* 2>/dev/null | head -1)
    if [ -f "$LATEST_LOG" ]; then
        echo "Log: $(basename $LATEST_LOG)"
        echo "Summary:"
        tail -20 "$LATEST_LOG" | grep -E "Total|Return|Drawdown|Trades|Result" || tail -10 "$LATEST_LOG"
    else
        echo "No logs yet (waiting for first execution)"
    fi
else
    echo "Logs directory not found"
fi
echo ""

# 3. Show next execution
echo -e "${CYAN}⏳ Next Execution:${NC}"
CRON_JOB=$(crontab -l 2>/dev/null | grep "amb-bot.main once" | head -1)
if [ ! -z "$CRON_JOB" ]; then
    # Extract time from cron
    CRON_MIN=$(echo $CRON_JOB | awk '{print $1}')
    CRON_HOUR=$(echo $CRON_JOB | awk '{print $2}')
    CRON_DAY=$(echo $CRON_JOB | awk '{print $3}')
    echo "Scheduled: Day $CRON_DAY at $CRON_HOUR:$CRON_MIN UTC"
    echo "   = 1st of every month @ $(($CRON_HOUR + 1)):$CRON_MIN Paris time"
else
    echo "No cron job configured"
fi
echo ""

# 4. Show system status
echo -e "${CYAN}🖥️  System Status:${NC}"
echo "Memory:"
free -h | grep Mem | awk '{print "  Used: " $3 " / " $2 " (" int($3/$2*100) "%)"}'
echo ""
echo "Disk:"
df -h $DEPLOY_PATH | tail -1 | awk '{print "  Used: " $3 " / " $2 " (" $5 ")"}'
echo ""

# 5. Check IBKR connection
echo -e "${CYAN}🔌 IBKR Connection Test:${NC}"
if python3 -c "
import asyncio
try:
    from ib_insync import IB
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=1, timeout=2)
    print('  ✅ Connected to IB Gateway' if ib.isConnected() else '  ❌ Connection failed')
    ib.disconnect()
except Exception as e:
    print(f'  ❌ Error: {e}')
" 2>/dev/null; then
    true
else
    echo "  ⚠️  ib-insync not available or Gateway not running"
fi
echo ""

# 6. Show configuration
echo -e "${CYAN}⚙️  Configuration:${NC}"
if [ -f "$DEPLOY_PATH/.env" ]; then
    echo "BROKER_TYPE=$(grep BROKER_TYPE $DEPLOY_PATH/.env | cut -d= -f2)"
    echo "MONTHLY_BUDGET=$(grep MONTHLY_BUDGET $DEPLOY_PATH/.env | cut -d= -f2)"
    echo "STOP_LOSS=$(grep STOP_LOSS_PCT $DEPLOY_PATH/.env | cut -d= -f2)"
    echo "TAKE_PROFIT=$(grep TAKE_PROFIT_PCT $DEPLOY_PATH/.env | cut -d= -f2)"
else
    echo "No .env file found"
fi
echo ""

# 7. Show useful commands
echo -e "${CYAN}💡 Quick Commands:${NC}"
echo "  View latest logs:      tail -f $LOG_DIR/*.log"
echo "  Run bot manually:      cd $DEPLOY_PATH && source venv/bin/activate && python -m amb_bot.main once"
echo "  Edit config:           nano $DEPLOY_PATH/.env"
echo "  Check cron status:     systemctl status cron"
echo "  View all logs:         ls -lah $LOG_DIR"
echo "  Monitor live:          watch -n 10 'tail -20 $(ls -t $LOG_DIR/cron_* 2>/dev/null | head -1)'"
echo ""

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "Last update: $(date '+%Y-%m-%d %H:%M:%S UTC')"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
