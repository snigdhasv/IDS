#!/bin/bash
################################################################################
# Test DPDK Traffic Reception with Temporary Interface Unbinding
################################################################################
# Temporarily unbinds DPDK interface, sends test traffic, then rebinds
# This allows testing if traffic reaches the NIC before DPDK binding

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PCAP_DIR="${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/pcap_samples"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}Testing DPDK Traffic Reception${NC}\n"

# Check if tcpreplay is available
if ! command -v tcpreplay &> /dev/null; then
    echo -e "${RED}❌ tcpreplay not installed${NC}"
    exit 1
fi

# Check if dpdk-devbind.py is available
DEVBIND="/usr/local/bin/dpdk-devbind.py"
if [ ! -f "$DEVBIND" ]; then
    echo -e "${RED}❌ dpdk-devbind.py not found${NC}"
    exit 1
fi

# Configuration
INTEL_PCI="0000:01:00.0"
KERNEL_DRIVER="ixgbe"
DPDK_DRIVER="vfio-pci"

echo -e "${YELLOW}⚠️  This will temporarily stop DPDK capture for testing${NC}"
read -p "Continue? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

echo -e "\n${CYAN}Step 1: Unbinding interface from DPDK...${NC}"
sudo python3 "$DEVBIND" --unbind "$INTEL_PCI"
sudo python3 "$DEVBIND" --bind="$KERNEL_DRIVER" "$INTEL_PCI"

# Wait for interface to appear
sleep 2
if ! ip link show enp1s0 &>/dev/null; then
    echo -e "${RED}❌ Interface enp1s0 not found after unbinding${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Interface unbound and available${NC}"

echo -e "\n${CYAN}Step 2: Bringing interface up...${NC}"
sudo ip link set enp1s0 up
sudo ip link set enp1s0 promisc on

echo -e "${GREEN}✓ Interface ready${NC}"

echo -e "\n${CYAN}Step 3: Starting tcpdump to monitor traffic...${NC}"
sudo tcpdump -i enp1s0 -c 10 -n &
TCPDUMP_PID=$!

sleep 1

echo -e "\n${CYAN}Step 4: Sending test traffic...${NC}"
if [ -f "${PCAP_DIR}/normal_traffic.pcap" ]; then
    echo -e "${GREEN}→ Sending normal traffic PCAP${NC}"
    sudo tcpreplay --intf1=enp1s0 --mbps=10 "${PCAP_DIR}/normal_traffic.pcap"
else
    echo -e "${YELLOW}⚠️  Normal traffic PCAP not found, using hping3 test${NC}"
    sudo hping3 -S -p 80 -c 5 192.168.1.1 --interface enp1s0 &
    HPING_PID=$!
    sleep 3
    kill $HPING_PID 2>/dev/null || true
fi

echo -e "${GREEN}✓ Traffic sent${NC}"

echo -e "\n${CYAN}Step 5: Waiting for tcpdump to capture packets...${NC}"
sleep 2

# Kill tcpdump
kill $TCPDUMP_PID 2>/dev/null || true

echo -e "\n${CYAN}Step 6: Rebinding interface to DPDK...${NC}"
sudo python3 "$DEVBIND" --unbind "$INTEL_PCI"
sudo python3 "$DEVBIND" --bind="$DPDK_DRIVER" "$INTEL_PCI"

echo -e "${GREEN}✓ Interface rebound to DPDK${NC}"

echo -e "\n${BOLD}${GREEN}Test Complete!${NC}"
echo -e "${CYAN}If tcpdump showed packets, the NIC can receive traffic.${NC}"
echo -e "${CYAN}The DPDK pipeline should work with proper traffic routing.${NC}"