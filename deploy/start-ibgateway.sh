#!/bin/bash
# Start Xvfb in background, then launch IBC

# Kill any existing Xvfb on display :1
pkill -f "Xvfb :1" || true

# Start Xvfb in background
/usr/bin/Xvfb :1 -screen 0 1024x768x24 &
XVFB_PID=$!

# Give Xvfb time to start
sleep 2

# Set display for IBC
export DISPLAY=:1

# Launch IBC (this will block and run the gateway)
exec /opt/ibc/scripts/ibcstart.sh -g
