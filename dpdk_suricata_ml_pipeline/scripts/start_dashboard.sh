#!/bin/bash
# Start the metrics dashboard in the background

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Kill any existing dashboard process
pkill -f "python3.*metrics_dashboard.py" 2>/dev/null

# Start the dashboard
echo "Starting metrics dashboard..."
nohup python3 metrics_dashboard.py > /tmp/metrics_dashboard.log 2>&1 &
DASHBOARD_PID=$!

# Wait a moment for it to start
sleep 2

# Check if it's running
if ps -p $DASHBOARD_PID > /dev/null; then
    echo "✓ Metrics dashboard started (PID: $DASHBOARD_PID)"
    echo "  Access at: http://localhost:5000"
    echo "  Logs: /tmp/metrics_dashboard.log"
else
    echo "✗ Failed to start dashboard"
    echo "Check logs: /tmp/metrics_dashboard.log"
    exit 1
fi
