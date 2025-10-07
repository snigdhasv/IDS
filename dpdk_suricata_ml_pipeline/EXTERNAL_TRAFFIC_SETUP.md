#!/bin/bash

# Setup USB adapter to receive traffic from external device
# This configures the interface for passive monitoring

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
echo -e "${BOLD}${BLUE}║  External Traffic Capture Setup                ║${NC}"
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

# Configuration
CAPTURE_INTERFACE="$NETWORK_INTERFACE"
CAPTURE_IP="192.168.100.1"      # IP for your IDS system
CAPTURE_NETMASK="255.255.255.0"
CAPTURE_NETWORK="192.168.100.0/24"

echo -e "${CYAN}Configuration:${NC}"
echo -e "  Interface: $CAPTURE_INTERFACE"
echo -e "  IP Address: $CAPTURE_IP"
echo -e "  Network: $CAPTURE_NETWORK"
echo

# Check if interface exists
if ! ip link show "$CAPTURE_INTERFACE" > /dev/null 2>&1; then
    echo -e "${RED}❌ Interface $CAPTURE_INTERFACE not found${NC}"
    echo "Available interfaces:"
    ip link show | grep -E '^[0-9]+:' | awk '{print $2}' | sed 's/:$//'
    exit 1
fi

# Bring interface up
echo -e "${BLUE}Step 1: Bringing interface up...${NC}"
ip link set "$CAPTURE_INTERFACE" up
sleep 1
echo -e "${GREEN}✓ Interface is up${NC}"

# Assign static IP
echo -e "\n${BLUE}Step 2: Assigning static IP...${NC}"
ip addr flush dev "$CAPTURE_INTERFACE" 2>/dev/null || true
ip addr add "$CAPTURE_IP/$CAPTURE_NETMASK" dev "$CAPTURE_INTERFACE"
echo -e "${GREEN}✓ IP configured: $CAPTURE_IP${NC}"

# Disable reverse path filtering (important for IDS)
echo -e "\n${BLUE}Step 3: Configuring kernel parameters for IDS...${NC}"
echo 0 > /proc/sys/net/ipv4/conf/"$CAPTURE_INTERFACE"/rp_filter
echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter
echo -e "${GREEN}✓ Reverse path filtering disabled${NC}"

# Enable promiscuous mode
echo -e "\n${BLUE}Step 4: Enabling promiscuous mode...${NC}"
ip link set "$CAPTURE_INTERFACE" promisc on
echo -e "${GREEN}✓ Promiscuous mode enabled${NC}"

# Optimize receive buffer
echo -e "\n${BLUE}Step 5: Optimizing network buffers...${NC}"
ethtool -G "$CAPTURE_INTERFACE" rx 4096 2>/dev/null || echo -e "${YELLOW}⚠️  Could not increase RX ring buffer (may not be supported)${NC}"
echo -e "${GREEN}✓ Network optimizations applied${NC}"

# Disable offloading features for accurate packet capture
echo -e "\n${BLUE}Step 6: Disabling offload features...${NC}"
ethtool -K "$CAPTURE_INTERFACE" gro off 2>/dev/null || true
ethtool -K "$CAPTURE_INTERFACE" lro off 2>/dev/null || true
ethtool -K "$CAPTURE_INTERFACE" gso off 2>/dev/null || true
ethtool -K "$CAPTURE_INTERFACE" tso off 2>/dev/null || true
echo -e "${GREEN}✓ Offload features disabled${NC}"

# Show final configuration
echo -e "\n${BOLD}${GREEN}Interface Configuration:${NC}"
ip addr show "$CAPTURE_INTERFACE"
echo

echo -e "\n${BOLD}${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  Interface Ready for External Traffic          ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo

echo -e "${BOLD}${CYAN}Next Steps:${NC}"
echo -e "1. Connect external device to USB adapter via Ethernet cable"
echo -e "2. Configure external device with IP: ${CYAN}192.168.100.2${NC} (or DHCP)"
echo -e "3. Start Suricata: ${CYAN}sudo ./03_start_suricata_afpacket.sh${NC}"
echo -e "4. Start external PCAP replay on the other device"
echo -e "5. Monitor traffic: ${CYAN}tcpdump -i $CAPTURE_INTERFACE${NC}"
echo

echo -e "${BOLD}${YELLOW}External Device Configuration:${NC}"
echo -e "  IP: 192.168.100.2"
echo -e "  Netmask: 255.255.255.0"
echo -e "  Gateway: 192.168.100.1 (optional)"
echo -e "  Target: 192.168.100.1 or any IP in 192.168.100.0/24"
echo

echo -e "${BOLD}${YELLOW}Test Connectivity:${NC}"
echo -e "  From this system: ${CYAN}ping 192.168.100.2${NC}"
echo -e "  From external device: ${CYAN}ping 192.168.100.1${NC}"
echo

echo -e "${GREEN}✓ Setup complete!${NC}"
