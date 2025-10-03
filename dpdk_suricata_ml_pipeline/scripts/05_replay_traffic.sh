#!/bin/bash

# Replay PCAP Traffic to DPDK Interface

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
echo -e "${BOLD}${BLUE}║  PCAP Traffic Replay Script                    ║${NC}"
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
    echo -e "${YELLOW}⚠️  Using default configuration${NC}"
    NETWORK_INTERFACE="eth0"
    PCAP_REPLAY_SPEED="10"
    PCAP_LOOP_COUNT="1"
fi

# Check for PCAP file argument
if [ $# -lt 1 ]; then
    echo -e "${RED}❌ No PCAP file specified${NC}"
    echo "Usage: $0 <pcap_file> [options]"
    echo
    echo "Options:"
    echo "  -s, --speed <mbps>     Replay speed in Mbps (default: $PCAP_REPLAY_SPEED)"
    echo "  -l, --loop <count>     Number of times to loop (default: $PCAP_LOOP_COUNT)"
    echo "  -i, --interface <if>   Interface to replay on (default: $NETWORK_INTERFACE)"
    echo
    echo "Examples:"
    echo "  $0 ../pcap_samples/attack.pcap"
    echo "  $0 capture.pcap -s 100 -l 5"
    echo "  $0 traffic.pcap -i eth1"
    exit 1
fi

PCAP_FILE="$1"
shift

# Parse additional arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--speed)
            PCAP_REPLAY_SPEED="$2"
            shift 2
            ;;
        -l|--loop)
            PCAP_LOOP_COUNT="$2"
            shift 2
            ;;
        -i|--interface)
            NETWORK_INTERFACE="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check PCAP file exists
if [ ! -f "$PCAP_FILE" ]; then
    echo -e "${RED}❌ PCAP file not found: $PCAP_FILE${NC}"
    exit 1
fi

# Get PCAP info
PCAP_SIZE=$(du -h "$PCAP_FILE" | awk '{print $1}')
PCAP_PACKETS=$(capinfos -c "$PCAP_FILE" 2>/dev/null | grep "Number of packets" | awk '{print $NF}' || echo "Unknown")

echo -e "${CYAN}PCAP File:${NC} $PCAP_FILE"
echo -e "${CYAN}Size:${NC} $PCAP_SIZE"
echo -e "${CYAN}Packets:${NC} $PCAP_PACKETS"
echo -e "${CYAN}Interface:${NC} $NETWORK_INTERFACE"
echo -e "${CYAN}Speed:${NC} ${PCAP_REPLAY_SPEED} Mbps"
echo -e "${CYAN}Loop Count:${NC} $PCAP_LOOP_COUNT"
echo

# Check interface exists
if ! ip link show "$NETWORK_INTERFACE" > /dev/null 2>&1; then
    echo -e "${RED}❌ Interface $NETWORK_INTERFACE not found${NC}"
    echo "Available interfaces:"
    ip link show | grep -E '^[0-9]+:' | awk '{print $2}' | sed 's/:$//'
    exit 1
fi

# Check if tcpreplay is installed
if ! command -v tcpreplay &> /dev/null; then
    echo -e "${YELLOW}tcpreplay not found. Installing...${NC}"
    apt-get update -qq
    apt-get install -y tcpreplay
    echo -e "${GREEN}✓ tcpreplay installed${NC}"
fi

# Check if interface is bound to DPDK
DEVBIND=$(which dpdk-devbind.py 2>/dev/null || echo "/usr/local/bin/dpdk-devbind.py")
IS_DPDK_BOUND=false

if [ -f "$DEVBIND" ]; then
    if "$DEVBIND" --status 2>/dev/null | grep -q "$NETWORK_INTERFACE.*drv=vfio-pci\|drv=igb_uio\|drv=uio_pci_generic"; then
        IS_DPDK_BOUND=true
    fi
fi

if [ "$IS_DPDK_BOUND" = true ]; then
    echo -e "${YELLOW}⚠️  WARNING: Interface appears to be bound to DPDK${NC}"
    echo -e "${YELLOW}tcpreplay may not work with DPDK-bound interfaces${NC}"
    echo -e "${YELLOW}Consider:"
    echo -e "  1. Unbind interface: ./unbind_interface.sh"
    echo -e "  2. Use another interface for replay"
    echo -e "  3. Send traffic from external system${NC}"
    echo
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# Warning
echo -e "${BOLD}${YELLOW}⚠️  WARNING ⚠️${NC}"
echo -e "${YELLOW}This will replay network traffic to $NETWORK_INTERFACE${NC}"
echo -e "${YELLOW}Make sure Suricata is running to capture the traffic!${NC}"
echo

read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Replay traffic
echo -e "\n${BOLD}${BLUE}Starting traffic replay...${NC}"
echo

# Build tcpreplay command
TCPREPLAY_CMD="tcpreplay"
TCPREPLAY_CMD="$TCPREPLAY_CMD -i $NETWORK_INTERFACE"

if [ "$PCAP_REPLAY_SPEED" != "0" ]; then
    TCPREPLAY_CMD="$TCPREPLAY_CMD -M ${PCAP_REPLAY_SPEED}"
else
    TCPREPLAY_CMD="$TCPREPLAY_CMD -t"  # Top speed
fi

if [ "$PCAP_LOOP_COUNT" != "1" ]; then
    TCPREPLAY_CMD="$TCPREPLAY_CMD -l $PCAP_LOOP_COUNT"
fi

TCPREPLAY_CMD="$TCPREPLAY_CMD --stats=1"  # Print stats every second
TCPREPLAY_CMD="$TCPREPLAY_CMD $PCAP_FILE"

echo -e "${CYAN}Command: $TCPREPLAY_CMD${NC}"
echo

# Execute replay
$TCPREPLAY_CMD

REPLAY_STATUS=$?

if [ $REPLAY_STATUS -eq 0 ]; then
    echo -e "\n${GREEN}✓ Traffic replay completed successfully${NC}"
else
    echo -e "\n${RED}❌ Traffic replay failed (exit code: $REPLAY_STATUS)${NC}"
    exit $REPLAY_STATUS
fi

echo -e "\n${BOLD}${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  Traffic Replay Complete                       ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo

echo -e "${BOLD}Next Steps:${NC}"
echo -e "  1. Check Suricata logs: ${CYAN}tail -f /var/log/suricata/eve.json${NC}"
echo -e "  2. Monitor Kafka alerts: ${CYAN}kafka-console-consumer.sh --topic suricata-alerts${NC}"
echo -e "  3. Check ML predictions: ${CYAN}tail -f ../logs/ml/ml_consumer.log${NC}"
echo

echo -e "${GREEN}✓ Done!${NC}"
