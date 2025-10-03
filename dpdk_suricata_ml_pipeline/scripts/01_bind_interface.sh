#!/bin/bash

# Script to bind network interface to DPDK
# WARNING: This will take the interface offline!

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
echo -e "${BOLD}${BLUE}║  DPDK Interface Binding Script                 ║${NC}"
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
    echo -e "${GREEN}✓ Configuration loaded${NC}"
else
    echo -e "${RED}❌ Configuration file not found: $CONFIG_FILE${NC}"
    exit 1
fi

# Check if dpdk-devbind.py exists
DEVBIND=$(which dpdk-devbind.py 2>/dev/null || echo "/usr/local/bin/dpdk-devbind.py")
if [ ! -f "$DEVBIND" ] && [ ! -x "$DEVBIND" ]; then
    echo -e "${RED}❌ dpdk-devbind.py not found. Is DPDK installed?${NC}"
    exit 1
fi

# Function to get PCI address
get_pci_address() {
    local iface=$1
    local pci=$(ethtool -i "$iface" 2>/dev/null | grep "bus-info" | awk '{print $2}')
    if [ -z "$pci" ]; then
        pci=$(ls -l /sys/class/net/"$iface"/device 2>/dev/null | awk -F'/' '{print $(NF)}')
    fi
    echo "$pci"
}

# Function to get current driver
get_current_driver() {
    local iface=$1
    ethtool -i "$iface" 2>/dev/null | grep "driver:" | awk '{print $2}'
}

# Check interface exists
if ! ip link show "$NETWORK_INTERFACE" > /dev/null 2>&1; then
    echo -e "${RED}❌ Interface $NETWORK_INTERFACE not found${NC}"
    echo "Available interfaces:"
    ip link show | grep -E '^[0-9]+:' | awk '{print $2}' | sed 's/:$//'
    exit 1
fi

# Get PCI address
if [ -z "$INTERFACE_PCI_ADDRESS" ]; then
    INTERFACE_PCI_ADDRESS=$(get_pci_address "$NETWORK_INTERFACE")
    if [ -z "$INTERFACE_PCI_ADDRESS" ]; then
        echo -e "${RED}❌ Could not determine PCI address for $NETWORK_INTERFACE${NC}"
        exit 1
    fi
fi

# Get current driver
CURRENT_DRIVER=$(get_current_driver "$NETWORK_INTERFACE")

echo -e "${CYAN}Interface:${NC} $NETWORK_INTERFACE"
echo -e "${CYAN}PCI Address:${NC} $INTERFACE_PCI_ADDRESS"
echo -e "${CYAN}Current Driver:${NC} $CURRENT_DRIVER"
echo -e "${CYAN}Target Driver:${NC} $DPDK_DRIVER"
echo

# Check if already bound to DPDK
if [ "$CURRENT_DRIVER" == "$DPDK_DRIVER" ]; then
    echo -e "${GREEN}✓ Interface already bound to $DPDK_DRIVER${NC}"
    exit 0
fi

# Warning
echo -e "${BOLD}${YELLOW}⚠️  WARNING ⚠️${NC}"
echo -e "${YELLOW}This will bind $NETWORK_INTERFACE to DPDK driver.${NC}"
echo -e "${YELLOW}The interface will be taken OFFLINE and unavailable for normal use!${NC}"
echo -e "${YELLOW}Network connectivity will be lost if this is your primary interface.${NC}"
echo

read -p "Continue? (type 'yes' to proceed): " -r
if [[ ! $REPLY == "yes" ]]; then
    echo "Aborted."
    exit 0
fi

# Backup current configuration
BACKUP_DIR="${SCRIPT_DIR}/../logs/interface_backup"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

if [ "$BACKUP_INTERFACE_CONFIG" == "true" ]; then
    echo -e "\n${BLUE}Backing up interface configuration...${NC}"
    {
        echo "INTERFACE=$NETWORK_INTERFACE"
        echo "PCI_ADDRESS=$INTERFACE_PCI_ADDRESS"
        echo "ORIGINAL_DRIVER=$CURRENT_DRIVER"
        echo "TIMESTAMP=$TIMESTAMP"
        ip addr show "$NETWORK_INTERFACE"
    } > "$BACKUP_DIR/backup_${TIMESTAMP}.conf"
    echo -e "${GREEN}✓ Backup saved to: $BACKUP_DIR/backup_${TIMESTAMP}.conf${NC}"
fi

# Take interface down
echo -e "\n${BLUE}Taking interface down...${NC}"
ip link set "$NETWORK_INTERFACE" down

# Load required kernel modules
echo -e "\n${BLUE}Loading kernel modules...${NC}"

case "$DPDK_DRIVER" in
    vfio-pci)
        modprobe vfio-pci
        echo -e "${GREEN}✓ Loaded vfio-pci${NC}"
        
        # Enable unsafe NOIOMMU mode if IOMMU is not available
        if [ ! -d "/sys/kernel/iommu_groups" ] || [ -z "$(ls -A /sys/kernel/iommu_groups 2>/dev/null)" ]; then
            echo -e "${YELLOW}⚠️  IOMMU not available, enabling NOIOMMU mode${NC}"
            modprobe vfio enable_unsafe_noiommu_mode=1 2>/dev/null || true
            echo 1 > /sys/module/vfio/parameters/enable_unsafe_noiommu_mode 2>/dev/null || true
        fi
        ;;
    uio_pci_generic)
        modprobe uio
        modprobe uio_pci_generic
        echo -e "${GREEN}✓ Loaded uio_pci_generic${NC}"
        ;;
    igb_uio)
        if [ ! -f "/lib/modules/$(uname -r)/extra/dpdk/igb_uio.ko" ]; then
            echo -e "${RED}❌ igb_uio module not found. Build DPDK with igb_uio support.${NC}"
            exit 1
        fi
        insmod "/lib/modules/$(uname -r)/extra/dpdk/igb_uio.ko"
        echo -e "${GREEN}✓ Loaded igb_uio${NC}"
        ;;
    *)
        echo -e "${RED}❌ Unknown driver: $DPDK_DRIVER${NC}"
        exit 1
        ;;
esac

# Unbind from current driver
echo -e "\n${BLUE}Unbinding from current driver...${NC}"
"$DEVBIND" -u "$INTERFACE_PCI_ADDRESS"
echo -e "${GREEN}✓ Unbound from $CURRENT_DRIVER${NC}"

# Bind to DPDK driver
echo -e "\n${BLUE}Binding to DPDK driver...${NC}"
"$DEVBIND" -b "$DPDK_DRIVER" "$INTERFACE_PCI_ADDRESS"

# Verify binding
sleep 1
BOUND_DRIVER=$(lspci -vvv -s "$INTERFACE_PCI_ADDRESS" 2>/dev/null | grep "Kernel driver in use:" | awk '{print $5}')

if [ "$BOUND_DRIVER" == "$DPDK_DRIVER" ]; then
    echo -e "${GREEN}✓ Successfully bound to $DPDK_DRIVER${NC}"
else
    echo -e "${RED}❌ Binding verification failed${NC}"
    exit 1
fi

# Show status
echo -e "\n${BOLD}${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  Interface Successfully Bound to DPDK          ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo

echo -e "${BOLD}Current DPDK Status:${NC}"
"$DEVBIND" --status

echo -e "\n${BOLD}${YELLOW}Important Notes:${NC}"
echo -e "• Interface $NETWORK_INTERFACE is now offline"
echo -e "• To restore: run ${CYAN}unbind_interface.sh${NC}"
echo -e "• Backup saved: ${CYAN}$BACKUP_DIR/backup_${TIMESTAMP}.conf${NC}"
echo -e "• You can now start Suricata in DPDK mode"
echo

echo -e "${GREEN}✓ Done!${NC}"
