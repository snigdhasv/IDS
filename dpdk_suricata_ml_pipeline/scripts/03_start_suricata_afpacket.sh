#!/bin/bash

# Start Suricata in AF_PACKET mode with Kafka output
# Works with ANY network interface including USB adapters!

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/pipeline.conf"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║  Suricata AF_PACKET Mode Start Script          ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo

# Check root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}❌ This script must be run as root${NC}"
    exit 1
fi

# Load configuration
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo -e "${RED}❌ Configuration file not found: $CONFIG_FILE${NC}"
    exit 1
fi

# Check if Suricata is installed
if ! command -v suricata &> /dev/null; then
    echo -e "${RED}❌ Suricata not installed${NC}"
    exit 1
fi

# Check if interface exists
if ! ip link show "$NETWORK_INTERFACE" > /dev/null 2>&1; then
    echo -e "${RED}❌ Interface $NETWORK_INTERFACE not found${NC}"
    echo "Available interfaces:"
    ip link show | grep -E '^[0-9]+:' | awk '{print $2}' | sed 's/:$//'
    exit 1
fi

# Check if interface is up
if ! ip link show "$NETWORK_INTERFACE" | grep -q "UP"; then
    echo -e "${YELLOW}⚠️  Interface $NETWORK_INTERFACE is down. Bringing it up...${NC}"
    ip link set "$NETWORK_INTERFACE" up
    sleep 2
fi

# Enable promiscuous mode (required for packet capture)
echo -e "${BLUE}Enabling promiscuous mode on $NETWORK_INTERFACE...${NC}"
ip link set "$NETWORK_INTERFACE" promisc on
if ip link show "$NETWORK_INTERFACE" | grep -q "PROMISC"; then
    echo -e "${GREEN}✓ Promiscuous mode enabled${NC}"
else
    echo -e "${YELLOW}⚠️  Could not enable promiscuous mode (Suricata will enable it)${NC}"
fi

# Create log directory if it doesn't exist
mkdir -p "$SURICATA_LOG_DIR"

# Check if Suricata is already running
PID_FILE="/var/run/suricata.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Suricata is already running${NC}"
        echo -e "${CYAN}Current PID:${NC} $PID"
        echo
        echo -e "${BOLD}Process Info:${NC}"
        ps aux | grep -E "^root.*$PID.*suricata"
        echo
        echo -e "${GREEN}✓ Suricata is already running - no action needed${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠️  Stale PID file found, removing...${NC}"
        rm -f "$PID_FILE"
    fi
fi

# Use default Suricata config
AFPACKET_CONFIG="/etc/suricata/suricata.yaml"
if [ ! -f "$AFPACKET_CONFIG" ]; then
    echo -e "${RED}❌ Suricata config not found: $AFPACKET_CONFIG${NC}"
    exit 1
fi

# Display configuration
echo -e "${CYAN}Configuration:${NC}"
echo -e "  Interface: $NETWORK_INTERFACE"
echo -e "  Config: $AFPACKET_CONFIG"
echo -e "  Log Directory: $SURICATA_LOG_DIR"
echo -e "  HOME_NET: $SURICATA_HOME_NET"
echo -e "  Worker Threads: $SURICATA_CORES"
echo

# Start Suricata in AF_PACKET mode
echo -e "${BLUE}Starting Suricata in AF_PACKET mode...${NC}"

suricata -c "$AFPACKET_CONFIG" \
    --af-packet="$NETWORK_INTERFACE" \
    -l "$SURICATA_LOG_DIR" \
    --set vars.address-groups.HOME_NET="$SURICATA_HOME_NET" \
    --set vars.address-groups.EXTERNAL_NET="$SURICATA_EXTERNAL_NET" \
    --set af-packet.0.threads="$SURICATA_CORES" \
    --set af-packet.0.cluster-type=cluster_flow \
    --set outputs.5.eve-log.enabled=yes \
    --set outputs.5.eve-log.filetype=regular \
    --set outputs.5.eve-log.filename=eve.json \
    -D

# Wait for Suricata to fully initialize
echo -e "${CYAN}Waiting for Suricata to initialize (daemon fork)...${NC}"

# Wait for PID file to be created (daemon fork completes)
RETRY_COUNT=0
MAX_RETRIES=15
PID_FILE="/var/run/suricata.pid"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if [ -f "$PID_FILE" ]; then
        # PID file exists, verify process is actually running
        PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
            # Process is running, wait a bit more for full initialization
            sleep 2
            # Verify still running after 2 seconds
            if ps -p "$PID" > /dev/null 2>&1; then
                echo -e "${GREEN}✓ Suricata daemon initialized successfully${NC}"
                break
            fi
        fi
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo -e "${YELLOW}  Waiting for daemon to fork... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
        sleep 1
    fi
done

# Final check if Suricata started successfully
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
fi

if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Suricata started successfully!${NC}"
    echo -e "${CYAN}PID:${NC} $PID"
    echo
    
    # Show running info
    echo -e "${BOLD}Process Info:${NC}"
    ps aux | grep "[s]uricata" | grep -v grep
    echo
    
    echo -e "${BOLD}Log Files:${NC}"
    echo -e "  EVE JSON: ${CYAN}$SURICATA_LOG_DIR/eve.json${NC}"
    echo -e "  Fast Log: ${CYAN}$SURICATA_LOG_DIR/fast.log${NC}"
    echo -e "  Stats: ${CYAN}$SURICATA_LOG_DIR/stats.log${NC}"
    echo
    
    echo -e "${BOLD}Monitor Logs:${NC}"
    echo -e "  tail -f $SURICATA_LOG_DIR/eve.json | jq ."
    echo -e "  tail -f $SURICATA_LOG_DIR/fast.log"
    echo
    
    echo -e "${BOLD}Check Status:${NC}"
    echo -e "  ps aux | grep suricata"
    echo -e "  suricatasc -c dump-counters"
    echo
    
    echo -e "${GREEN}✓ Suricata is running in AF_PACKET mode on $NETWORK_INTERFACE${NC}"
    echo -e "${YELLOW}Note: AF_PACKET mode works with USB and all network adapters!${NC}"
else
    echo -e "${RED}❌ Failed to start Suricata${NC}"
    echo "Check the logs:"
    echo "  tail -50 $SURICATA_LOG_DIR/suricata.log"
    exit 1
fi

echo
echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  Suricata Started Successfully                 ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════╝${NC}"
