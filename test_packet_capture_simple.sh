#!/bin/bash
################################################################################
# Simple Packet Capture Test (Without DPDK Complexity)
################################################################################
# Tests packet flow from Realtek to Intel using standard Linux tools
#
# This script temporarily unbinds the Intel NIC from DPDK to allow
# standard packet capture tools (tcpdump) to work.
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

INTEL_NIC="enp1s0"
INTEL_PCI="0000:01:00.0"
REALTEK_NIC="enp5s0"

echo -e "${BOLD}${CYAN}Simple Packet Capture Test${NC}\n"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}This test will:${NC}"
echo -e "  1. Unbind Intel NIC from DPDK (temporarily)"
echo -e "  2. Bring up Intel NIC in kernel mode"
echo -e "  3. Run tcpdump to capture packets"
echo -e "  4. You send packets from Realtek NIC"
echo -e "  5. Verify packets are received"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

# Step 1: Unbind from DPDK
echo -e "\n${CYAN}[1/4]${NC} Unbinding Intel NIC from DPDK..."
if dpdk-devbind.py --status | grep "0000:01:00.0" | grep -q "drv=vfio-pci"; then
    echo "  Unbinding from vfio-pci..."
    dpdk-devbind.py --unbind ${INTEL_PCI}
    sleep 1
    echo "  Binding to ixgbe..."
    dpdk-devbind.py --bind=ixgbe ${INTEL_PCI}
    sleep 2
    echo -e "${GREEN}✓ Unbound from vfio-pci, bound to ixgbe${NC}"
elif dpdk-devbind.py --status | grep "0000:01:00.0" | grep -q "drv=ixgbe"; then
    echo -e "${GREEN}✓ Already using kernel driver (ixgbe)${NC}"
else
    echo -e "${YELLOW}⚠️  Unknown driver state${NC}"
    dpdk-devbind.py --status | grep "0000:01:00.0"
fi

# Wait for interface to appear
echo "  Waiting for interface to appear..."
sleep 2

# Step 2: Bring up interface
echo -e "\n${CYAN}[2/4]${NC} Bringing up Intel NIC..."
ip link set dev ${INTEL_NIC} up
ip link set dev ${INTEL_NIC} promisc on
sleep 2
echo -e "${GREEN}✓ ${INTEL_NIC} is UP and in promiscuous mode${NC}"

# Step 3: Start tcpdump
echo -e "\n${CYAN}[3/4]${NC} Starting packet capture on ${INTEL_NIC}..."
echo -e "${YELLOW}Waiting for packets... (Ctrl+C to stop)${NC}\n"
echo -e "${BOLD}In another terminal, run:${NC}"
echo -e "  ${GREEN}sudo tcpreplay --intf1=${REALTEK_NIC} dpdk_suricata_ml_pipeline/pcap_samples/normal_traffic.pcap${NC}"
echo -e "\n${CYAN}Capturing...${NC}\n"

# Capture packets (will show them on screen)
tcpdump -i ${INTEL_NIC} -c 100 -n -v

echo -e "\n${GREEN}✓ Capture complete!${NC}"

# Step 4: Ask about rebinding
echo -e "\n${CYAN}[4/4]${NC} Cleanup..."
echo ""
read -p "Rebind Intel NIC to DPDK? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ip link set dev ${INTEL_NIC} down
    dpdk-devbind.py --bind=vfio-pci ${INTEL_PCI}
    echo -e "${GREEN}✓ Intel NIC rebound to DPDK (vfio-pci)${NC}"
else
    echo -e "${YELLOW}⚠️  Intel NIC still using kernel driver (ixgbe)${NC}"
    echo -e "   Rebind manually: sudo dpdk-devbind.py --bind=vfio-pci ${INTEL_PCI}"
fi

echo -e "\n${GREEN}✓ Test complete!${NC}\n"
