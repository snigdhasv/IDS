#!/bin/bash
#
# Start IDS Pipeline with Metrics Monitoring
# 
# This script starts all components of the IDS pipeline in separate
# terminal windows and displays the metrics dashboard.
#
# Usage: ./start_ids_with_metrics.sh [dpdk|afpacket]
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default to DPDK mode
MODE="${1:-dpdk}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        IDS Pipeline Startup Script with Metrics               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root for Suricata
if [[ $EUID -ne 0 ]] && [[ "$MODE" == "dpdk" || "$MODE" == "afpacket" ]]; then
   echo -e "${YELLOW}⚠️  This script needs sudo privileges to start Suricata${NC}"
   echo -e "${YELLOW}    Re-running with sudo...${NC}"
   sudo "$0" "$@"
   exit $?
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if process is running
is_running() {
    pgrep -f "$1" >/dev/null 2>&1
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down IDS pipeline...${NC}"
    pkill -f suricata 2>/dev/null || true
    pkill -f suricata_kafka_bridge 2>/dev/null || true
    pkill -f ml_kafka_consumer 2>/dev/null || true
    pkill -f metrics_dashboard 2>/dev/null || true
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

trap cleanup EXIT INT TERM

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command_exists python3; then
    echo -e "${RED}✗ Python3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python3 found${NC}"

if ! command_exists suricata; then
    echo -e "${RED}✗ Suricata not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Suricata found${NC}"

if ! command_exists tmux && ! command_exists screen; then
    echo -e "${YELLOW}⚠️  Neither tmux nor screen found. Will run in background.${NC}"
    USE_MULTIPLEXER=false
else
    USE_MULTIPLEXER=true
    if command_exists tmux; then
        MULTIPLEXER="tmux"
    else
        MULTIPLEXER="screen"
    fi
    echo -e "${GREEN}✓ Terminal multiplexer found: $MULTIPLEXER${NC}"
fi

# Create log directories
echo -e "${BLUE}Creating log directories...${NC}"
mkdir -p logs/metrics
mkdir -p logs/ml
mkdir -p logs/bridge
echo -e "${GREEN}✓ Log directories ready${NC}"

# Check if Kafka is running
echo -e "${BLUE}Checking Kafka...${NC}"
if ! netstat -tuln 2>/dev/null | grep -q ':9092' && ! ss -tuln 2>/dev/null | grep -q ':9092'; then
    echo -e "${YELLOW}⚠️  Kafka not detected on port 9092${NC}"
    echo -e "${YELLOW}    Make sure Kafka is running before starting the pipeline${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ Kafka detected${NC}"
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   Starting IDS Pipeline                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to start component in tmux
start_in_tmux() {
    local session=$1
    local window=$2
    local title=$3
    local command=$4
    
    if [ "$window" = "0" ]; then
        tmux new-session -d -s "$session" -n "$title" "$command"
    else
        tmux new-window -t "$session:$window" -n "$title" "$command"
    fi
}

# Function to start component in screen
start_in_screen() {
    local session=$1
    local title=$2
    local command=$3
    
    screen -dmS "$session-$title" bash -c "$command"
}

# Session name
SESSION="ids-pipeline"

if [ "$USE_MULTIPLEXER" = true ]; then
    echo -e "${BLUE}Starting components in $MULTIPLEXER...${NC}"
    
    if [ "$MULTIPLEXER" = "tmux" ]; then
        # Kill existing session if it exists
        tmux kill-session -t "$SESSION" 2>/dev/null || true
        
        # Start Suricata
        echo -e "${GREEN}[1/4] Starting Suricata ($MODE mode)...${NC}"
        if [ "$MODE" = "dpdk" ]; then
            start_in_tmux "$SESSION" 0 "Suricata" "./run_dpdk_mode.sh"
        else
            start_in_tmux "$SESSION" 0 "Suricata" "./run_afpacket_mode.sh"
        fi
        sleep 3
        
        # Start Kafka Bridge
        echo -e "${GREEN}[2/4] Starting Kafka Bridge...${NC}"
        start_in_tmux "$SESSION" 1 "Bridge" "cd dpdk_suricata_ml_pipeline && python3 src/suricata_kafka_bridge.py"
        sleep 2
        
        # Start ML Consumer
        echo -e "${GREEN}[3/4] Starting ML Consumer...${NC}"
        start_in_tmux "$SESSION" 2 "ML-Consumer" "cd dpdk_suricata_ml_pipeline && python3 src/ml_kafka_consumer.py"
        sleep 2
        
        # Start Metrics Dashboard
        echo -e "${GREEN}[4/4] Starting Metrics Dashboard...${NC}"
        start_in_tmux "$SESSION" 3 "Dashboard" "cd dpdk_suricata_ml_pipeline && ./scripts/metrics_dashboard.py"
        
        echo ""
        echo -e "${GREEN}✓ All components started in tmux session: $SESSION${NC}"
        echo ""
        echo -e "${BLUE}To view components:${NC}"
        echo -e "  tmux attach -t $SESSION"
        echo -e "  ${YELLOW}Use Ctrl+B then number (0-3) to switch windows${NC}"
        echo -e "  ${YELLOW}Use Ctrl+B then D to detach${NC}"
        echo ""
        echo -e "${BLUE}Windows:${NC}"
        echo -e "  0: Suricata"
        echo -e "  1: Kafka Bridge"
        echo -e "  2: ML Consumer"
        echo -e "  3: Metrics Dashboard"
        echo ""
        
        # Attach to session (dashboard window)
        sleep 1
        echo -e "${BLUE}Attaching to metrics dashboard...${NC}"
        sleep 2
        tmux select-window -t "$SESSION:3"
        tmux attach -t "$SESSION"
        
    else  # screen
        # Start components in screen
        echo -e "${GREEN}[1/4] Starting Suricata ($MODE mode)...${NC}"
        if [ "$MODE" = "dpdk" ]; then
            start_in_screen "$SESSION" "suricata" "./run_dpdk_mode.sh"
        else
            start_in_screen "$SESSION" "suricata" "./run_afpacket_mode.sh"
        fi
        sleep 3
        
        echo -e "${GREEN}[2/4] Starting Kafka Bridge...${NC}"
        start_in_screen "$SESSION" "bridge" "cd dpdk_suricata_ml_pipeline && python3 src/suricata_kafka_bridge.py"
        sleep 2
        
        echo -e "${GREEN}[3/4] Starting ML Consumer...${NC}"
        start_in_screen "$SESSION" "ml-consumer" "cd dpdk_suricata_ml_pipeline && python3 src/ml_kafka_consumer.py"
        sleep 2
        
        echo -e "${GREEN}[4/4] Starting Metrics Dashboard...${NC}"
        start_in_screen "$SESSION" "dashboard" "cd dpdk_suricata_ml_pipeline && ./scripts/metrics_dashboard.py"
        
        echo ""
        echo -e "${GREEN}✓ All components started in screen sessions${NC}"
        echo ""
        echo -e "${BLUE}To view components:${NC}"
        echo -e "  screen -r $SESSION-suricata"
        echo -e "  screen -r $SESSION-bridge"
        echo -e "  screen -r $SESSION-ml-consumer"
        echo -e "  screen -r $SESSION-dashboard"
        echo ""
        echo -e "${YELLOW}Use Ctrl+A then D to detach${NC}"
        echo ""
        
        # Attach to dashboard
        sleep 1
        echo -e "${BLUE}Attaching to metrics dashboard...${NC}"
        sleep 2
        screen -r "$SESSION-dashboard"
    fi
    
else
    # Run in background without multiplexer
    echo -e "${YELLOW}Running components in background...${NC}"
    
    echo -e "${GREEN}[1/4] Starting Suricata ($MODE mode)...${NC}"
    if [ "$MODE" = "dpdk" ]; then
        nohup ./run_dpdk_mode.sh > logs/suricata_output.log 2>&1 &
    else
        nohup ./run_afpacket_mode.sh > logs/suricata_output.log 2>&1 &
    fi
    sleep 3
    
    echo -e "${GREEN}[2/4] Starting Kafka Bridge...${NC}"
    nohup python3 dpdk_suricata_ml_pipeline/src/suricata_kafka_bridge.py > logs/bridge_output.log 2>&1 &
    sleep 2
    
    echo -e "${GREEN}[3/4] Starting ML Consumer...${NC}"
    nohup python3 dpdk_suricata_ml_pipeline/src/ml_kafka_consumer.py > logs/ml_output.log 2>&1 &
    sleep 2
    
    echo -e "${GREEN}[4/4] Starting Metrics Dashboard...${NC}"
    # Dashboard runs in foreground
    ./dpdk_suricata_ml_pipeline/scripts/metrics_dashboard.py
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   Pipeline Status Check                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

sleep 2

# Check if components are running
echo -e "${BLUE}Checking component status...${NC}"

if is_running "suricata"; then
    echo -e "${GREEN}✓ Suricata is running${NC}"
else
    echo -e "${RED}✗ Suricata not running${NC}"
fi

if is_running "suricata_kafka_bridge"; then
    echo -e "${GREEN}✓ Kafka Bridge is running${NC}"
else
    echo -e "${YELLOW}⚠️  Kafka Bridge not detected${NC}"
fi

if is_running "ml_kafka_consumer"; then
    echo -e "${GREEN}✓ ML Consumer is running${NC}"
else
    echo -e "${YELLOW}⚠️  ML Consumer not detected${NC}"
fi

echo ""
echo -e "${BLUE}Checking metrics files...${NC}"

if [ -d "logs/metrics" ] && [ "$(ls -A logs/metrics/*.jsonl 2>/dev/null)" ]; then
    echo -e "${GREEN}✓ Metrics files exist${NC}"
    ls -lh logs/metrics/*.jsonl 2>/dev/null | tail -3
else
    echo -e "${YELLOW}⚠️  No metrics files yet (give it a few seconds)${NC}"
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                     Useful Commands                           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}View logs:${NC}"
echo -e "  tail -f logs/ml/ml_consumer.log"
echo -e "  tail -f logs/bridge/bridge.log"
echo -e "  tail -f logs/metrics/metrics_*.jsonl | jq '.'"
echo ""
echo -e "${BLUE}Check status:${NC}"
echo -e "  ps aux | grep -E 'suricata|bridge|consumer|dashboard'"
echo ""
echo -e "${BLUE}Stop pipeline:${NC}"
echo -e "  pkill -f suricata"
echo -e "  pkill -f suricata_kafka_bridge"
echo -e "  pkill -f ml_kafka_consumer"
echo -e "  pkill -f metrics_dashboard"
echo ""
echo -e "${BLUE}Test with traffic:${NC}"
echo -e "  python3 tests/test_benign_traffic.py"
echo -e "  python3 tests/test_attack_generator.py"
echo ""

echo -e "${GREEN}IDS Pipeline with Metrics is ready! 🎉${NC}"
