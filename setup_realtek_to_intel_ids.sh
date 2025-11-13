
#!/bin/bash
################################################################################
# Setup: Realtek → Intel IDS Pipeline
################################################################################
# This script sets up packet flow from Realtek NIC to Intel NIC
# and runs DPDK-based IDS on the Intel NIC
#
# Architecture:
#   Realtek enp5s0 (192.168.100.1) → Intel enp1s0 (DPDK IDS)
#   
# Requirements: Physical cable between enp5s0 and enp1s0
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# NIC Configuration
REALTEK_NIC="enp5s0"           # Source NIC (packet sender)
REALTEK_IP="192.168.100.1/24"  # IP for Realtek
INTEL_NIC="enp1s0"             # Target NIC (DPDK IDS)
INTEL_PCI="0000:01:00.0"       # Intel PCI address
MANAGEMENT_NIC="enp3s0"        # Keep for SSH/management

echo -e "${BOLD}${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║                                                           ║${NC}"
echo -e "${BOLD}${CYAN}║     Realtek → Intel IDS Setup (DPDK Mode)                 ║${NC}"
echo -e "${BOLD}${CYAN}║                                                           ║${NC}"
echo -e "${BOLD}${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}\n"

# Check root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Configuration:${NC}"
echo -e "  Packet Source:  ${REALTEK_NIC} (Realtek, kernel mode)"
echo -e "  Packet Target:  ${INTEL_NIC} (Intel 10G, DPDK mode)"
echo -e "  Management:     ${MANAGEMENT_NIC} (Realtek, untouched)"
echo -e "  Physical Link:  ${REALTEK_NIC} <--cable--> ${INTEL_NIC}"
echo ""

# Step 1: Load vfio-pci module
echo -e "${CYAN}[1/6]${NC} Loading DPDK kernel modules..."
modprobe vfio-pci 2>/dev/null || echo "  vfio-pci already loaded"
echo -e "${GREEN}✓ vfio-pci ready${NC}\n"

# Step 2: Configure Realtek NIC (keep in kernel)
echo -e "${CYAN}[2/6]${NC} Configuring Realtek NIC ${REALTEK_NIC} (packet sender)..."
ip link set dev ${REALTEK_NIC} down 2>/dev/null || true
ip addr flush dev ${REALTEK_NIC} 2>/dev/null || true
ip addr add ${REALTEK_IP} dev ${REALTEK_NIC}
ip link set dev ${REALTEK_NIC} up
ip link set dev ${REALTEK_NIC} promisc on
echo -e "${GREEN}✓ ${REALTEK_NIC} configured: ${REALTEK_IP}${NC}\n"

# Step 3: Prepare Intel NIC for DPDK binding
echo -e "${CYAN}[3/6]${NC} Preparing Intel NIC ${INTEL_NIC} for DPDK..."
ip link set dev ${INTEL_NIC} down 2>/dev/null || true
ip addr flush dev ${INTEL_NIC} 2>/dev/null || true
echo -e "${GREEN}✓ ${INTEL_NIC} prepared (kernel driver will be unbound)${NC}\n"

# Step 4: Bind Intel NIC to DPDK
echo -e "${CYAN}[4/6]${NC} Binding Intel NIC to DPDK (vfio-pci)..."
if dpdk-devbind.py --bind=vfio-pci ${INTEL_PCI}; then
    echo -e "${GREEN}✓ Intel NIC bound to DPDK${NC}\n"
else
    echo -e "${RED}❌ Failed to bind Intel NIC to DPDK${NC}"
    echo "  Check: dpdk-devbind.py --status"
    exit 1
fi

# Step 5: Verify DPDK binding
echo -e "${CYAN}[5/6]${NC} Verifying DPDK status..."
dpdk-devbind.py --status | grep -A 2 "Network devices using DPDK" || true
echo ""

# Step 6: Setup hugepages
echo -e "${CYAN}[6/6]${NC} Configuring hugepages..."
mkdir -p /mnt/huge
if ! mount | grep -q /mnt/huge; then
    mount -t hugetlbfs nodev /mnt/huge
fi
echo 2048 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
echo -e "${GREEN}✓ Hugepages configured (2048 MB)${NC}\n"

# Summary
echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}Setup Complete!${NC}\n"
echo -e "${BOLD}Network Configuration:${NC}"
ip addr show ${REALTEK_NIC} | grep -E "inet |link/ether" | sed 's/^/  /'
echo ""
echo -e "${BOLD}DPDK Binding:${NC}"
dpdk-devbind.py --status 2>/dev/null | grep "drv=" | sed 's/^/  /' || echo "  (check manually)"
echo ""
echo -e "${BOLD}Next Steps:${NC}"
echo -e "  ${CYAN}1. Physically connect ${REALTEK_NIC} <--> ${INTEL_NIC} with cable${NC}"
echo -e "  ${CYAN}2. Start IDS pipeline:${NC}"
echo -e "     sudo ./run_realtime_engine_dpdk.sh test"
echo -e "  ${CYAN}3. Send test traffic from another terminal:${NC}"
echo -e "     sudo tcpreplay --intf1=${REALTEK_NIC} dpdk_suricata_ml_pipeline/pcap_samples/mixed_traffic_sample.pcap"
echo -e "  ${CYAN}4. Monitor IDS logs:${NC}"
echo -e "     tail -f logs/feature_engine.log"
echo ""
echo -e "${BOLD}Restore Original State:${NC}"
echo -e "  sudo ./run_realtime_engine_dpdk.sh stop"
echo -e "  sudo dpdk-devbind.py --bind=ixgbe ${INTEL_PCI}"
echo -e "  sudo ip link set dev ${INTEL_NIC} up"
echo ""
echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}\n"
