#!/bin/bash

# Start Suricata-to-Kafka Bridge

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIDGE_SCRIPT="${SCRIPT_DIR}/suricata_kafka_bridge.py"
VENV_PATH="$(dirname "$(dirname "$SCRIPT_DIR")")/venv"
LOG_DIR="${SCRIPT_DIR}/../logs/bridge"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║  Suricata→Kafka Bridge Start Script            ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo

# Create log directory
mkdir -p "$LOG_DIR"

# Check if Suricata is running
if ! ps aux | grep -v grep | grep -q suricata; then
    echo -e "${RED}❌ Suricata is not running${NC}"
    echo "Start Suricata first: ./03_start_suricata_afpacket.sh"
    exit 1
fi
echo -e "${GREEN}✓ Suricata is running${NC}"

# Check if Kafka is running
if ! netstat -tuln 2>/dev/null | grep -q ":9092"; then
    echo -e "${RED}❌ Kafka not running on port 9092${NC}"
    echo "Start Kafka first: ./02_setup_kafka.sh"
    exit 1
fi
echo -e "${GREEN}✓ Kafka is running${NC}"

# Check if bridge is already running
if pgrep -f "suricata_kafka_bridge.py" > /dev/null; then
    echo -e "${YELLOW}⚠️  Bridge already running${NC}"
    read -p "Kill existing process? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "suricata_kafka_bridge.py"
        sleep 2
    else
        echo "Exiting..."
        exit 0
    fi
fi

# Activate virtual environment
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}❌ Virtual environment not found: $VENV_PATH${NC}"
    exit 1
fi

echo -e "${BLUE}Activating virtual environment...${NC}"
source "$VENV_PATH/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Check Python dependencies
echo -e "\n${BLUE}Checking dependencies...${NC}"
python3 -c "import kafka" 2>/dev/null || {
    echo -e "${YELLOW}Installing kafka-python...${NC}"
    pip install kafka-python > /dev/null
}
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Start the bridge
echo -e "\n${BLUE}Starting Suricata→Kafka Bridge...${NC}"
echo -e "${CYAN}Log:${NC} $LOG_DIR/bridge.log"
echo

# Run in background
nohup python3 "$BRIDGE_SCRIPT" > "$LOG_DIR/bridge.log" 2>&1 &
BRIDGE_PID=$!

# Wait a moment and check if it started
sleep 2

if ps -p $BRIDGE_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Bridge started successfully!${NC}"
    echo -e "${CYAN}PID:${NC} $BRIDGE_PID"
    echo
    
    echo -e "${BOLD}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║  Bridge Running                                ║${NC}"
    echo -e "${BOLD}╚════════════════════════════════════════════════╝${NC}"
    echo
    
    echo -e "${BOLD}Status:${NC}"
    echo -e "  Suricata eve.json → Kafka topic: suricata-alerts"
    echo -e "  PID: $BRIDGE_PID"
    echo
    
    echo -e "${BOLD}Monitor:${NC}"
    echo -e "  tail -f $LOG_DIR/bridge.log"
    echo
    
    echo -e "${BOLD}Stop:${NC}"
    echo -e "  pkill -f suricata_kafka_bridge.py"
    echo
    
    echo -e "${GREEN}✓ Done!${NC}"
else
    echo -e "${RED}❌ Bridge failed to start${NC}"
    echo -e "Check logs: tail -f $LOG_DIR/bridge.log"
    exit 1
fi
