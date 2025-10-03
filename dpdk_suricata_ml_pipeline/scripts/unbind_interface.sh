#!/bin/bash

# Script to unbind DPDK interface and restore to original driver

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/pipeline.conf"
BACKUP_DIR="${SCRIPT_DIR}/../logs/interface_backup"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║  DPDK Interface Unbinding Script               ║${NC}"
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

# Find most recent backup
if [ -d "$BACKUP_DIR" ]; then
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/backup_*.conf 2>/dev/null | head -n1)
    if [ -n "$LATEST_BACKUP" ]; then
        echo -e "${GREEN}✓ Found backup: $LATEST_BACKUP${NC}"
        source "$LATEST_BACKUP"
    fi
fi

# Check if dpdk-devbind.py exists
DEVBIND=$(which dpdk-devbind.py 2>/dev/null || echo "/usr/local/bin/dpdk-devbind.py")
if [ ! -f "$DEVBIND" ] && [ ! -x "$DEVBIND" ]; then
    echo -e "${RED}❌ dpdk-devbind.py not found${NC}"
    exit 1
fi

# Auto-detect PCI if not set
if [ -z "$INTERFACE_PCI_ADDRESS" ]; then
    echo -e "${YELLOW}No PCI address configured, showing all DPDK devices:${NC}"
    "$DEVBIND" --status | grep -A 10 "Network devices using DPDK"
    echo
    read -p "Enter PCI address to unbind (e.g., 0000:02:00.0): " INTERFACE_PCI_ADDRESS
fi

# Get original driver if not set
if [ -z "$ORIGINAL_DRIVER" ]; then
    echo -e "${YELLOW}Original driver not found in backup${NC}"
    echo "Common drivers: e1000e (Intel), igb (Intel), r8169 (Realtek), bnx2x (Broadcom)"
    read -p "Enter original driver name: " ORIGINAL_DRIVER
fi

echo -e "${CYAN}PCI Address:${NC} $INTERFACE_PCI_ADDRESS"
echo -e "${CYAN}Target Driver:${NC} $ORIGINAL_DRIVER"
echo

# Unbind from DPDK
echo -e "${BLUE}Unbinding from DPDK driver...${NC}"
"$DEVBIND" -u "$INTERFACE_PCI_ADDRESS"
echo -e "${GREEN}✓ Unbound from DPDK${NC}"

# Bind to original driver
echo -e "\n${BLUE}Binding to original driver ($ORIGINAL_DRIVER)...${NC}"
"$DEVBIND" -b "$ORIGINAL_DRIVER" "$INTERFACE_PCI_ADDRESS"
echo -e "${GREEN}✓ Bound to $ORIGINAL_DRIVER${NC}"

# Wait for interface to appear
sleep 2

# Bring interface up
if [ -n "$NETWORK_INTERFACE" ]; then
    echo -e "\n${BLUE}Bringing interface up...${NC}"
    ip link set "$NETWORK_INTERFACE" up
    echo -e "${GREEN}✓ Interface $NETWORK_INTERFACE is up${NC}"
    
    # Show interface status
    echo -e "\n${BOLD}Interface Status:${NC}"
    ip addr show "$NETWORK_INTERFACE"
fi

echo -e "\n${BOLD}${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  Interface Restored Successfully               ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo

echo -e "${GREEN}✓ Done! Network interface restored.${NC}"
