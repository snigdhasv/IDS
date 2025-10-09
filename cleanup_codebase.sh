#!/bin/bash

################################################################################
# Cleanup Script - Remove Redundant Files
################################################################################
# This script removes duplicate PDFs, legacy code, and redundant documentation
# to streamline the IDS codebase
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║     IDS Codebase Cleanup Script              ║${NC}"
echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════╝${NC}"
echo

# Create backup directory
BACKUP_DIR="${SCRIPT_DIR}/backup_$(date +%Y%m%d_%H%M%S)"
echo -e "${YELLOW}Creating backup at: $BACKUP_DIR${NC}"
mkdir -p "$BACKUP_DIR"

# Function to backup and delete
backup_and_delete() {
    local file="$1"
    if [ -e "$file" ]; then
        local rel_path="${file#$SCRIPT_DIR/}"
        local backup_path="$BACKUP_DIR/$rel_path"
        mkdir -p "$(dirname "$backup_path")"
        cp -r "$file" "$backup_path"
        rm -rf "$file"
        echo -e "${GREEN}✓ Removed: $rel_path${NC}"
        return 0
    fi
    return 1
}

# Remove all PDF files (duplicates of markdown)
echo -e "\n${BOLD}${CYAN}Removing duplicate PDF files...${NC}"
find "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline" -name "*.pdf" -type f | while read pdf_file; do
    backup_and_delete "$pdf_file"
done

# Remove redundant documentation
echo -e "\n${BOLD}${CYAN}Removing redundant documentation...${NC}"
DOCS_TO_REMOVE=(
    "dpdk_suricata_ml_pipeline/ARCHITECTURE_COMPARISON.md"
    "dpdk_suricata_ml_pipeline/DOCUMENTATION_INDEX.md"
    "dpdk_suricata_ml_pipeline/EXTERNAL_CAPTURE_READY.md"
    "dpdk_suricata_ml_pipeline/IMPLEMENTATION_COMPLETE.md"
    "dpdk_suricata_ml_pipeline/IMPLEMENTATION_SUMMARY.md"
    "dpdk_suricata_ml_pipeline/MODES_COMPARISON.md"
    "dpdk_suricata_ml_pipeline/NETWORK_TOPOLOGY.md"
    "dpdk_suricata_ml_pipeline/PACKAGES_INSTALLED.md"
    "dpdk_suricata_ml_pipeline/PIPELINE_OUTPUTS_GUIDE.md"
    "dpdk_suricata_ml_pipeline/PLATFORM_COMPARISON.md"
    "dpdk_suricata_ml_pipeline/RUNTIME_GUIDE.md"
    "dpdk_suricata_ml_pipeline/SYSTEM_WORKING_SUMMARY.md"
    "dpdk_suricata_ml_pipeline/today_guide.md"
    "dpdk_suricata_ml_pipeline/TRAFFIC_MONITORING_GUIDE.md"
    "dpdk_suricata_ml_pipeline/WINDOWS_EXTERNAL_DEVICE_GUIDE.md"
    "dpdk_suricata_ml_pipeline/WINDOWS_METHODS_COMPARISON.txt"
    "dpdk_suricata_ml_pipeline/WINDOWS_NO_TCPREPLAY.md"
    "dpdk_suricata_ml_pipeline/WINDOWS_QUICK_SETUP.md"
    "dpdk_suricata_ml_pipeline/AF_PACKET_QUICK_START.md"
    "dpdk_suricata_ml_pipeline/START_HERE.md"
    "README_CLEAN_STRUCTURE.pdf"
    "README_CLEAN_STRUCTURE.md"
    "CLEANUP_SUMMARY.md"
    "VENV_SETUP_COMPLETED.md"
    "VENV_SETUP.md"
    "DPDK_SURICATA_INSTALLATION.md"
)

for doc in "${DOCS_TO_REMOVE[@]}"; do
    backup_and_delete "${SCRIPT_DIR}/$doc"
done

# Remove legacy directory
echo -e "\n${BOLD}${CYAN}Removing legacy code...${NC}"
if [ -d "${SCRIPT_DIR}/legacy" ]; then
    backup_and_delete "${SCRIPT_DIR}/legacy"
fi

# Remove old installation scripts (replaced by master scripts)
echo -e "\n${BOLD}${CYAN}Removing redundant scripts...${NC}"
SCRIPTS_TO_REMOVE=(
    "dpdk_suricata_ml_pipeline/scripts/quick_start.sh"
    "dpdk_suricata_ml_pipeline/install_missing_packages.sh"
    "install_dpdk_suricata.sh"
)

for script in "${SCRIPTS_TO_REMOVE[@]}"; do
    backup_and_delete "${SCRIPT_DIR}/$script"
done

# Remove redundant shell scripts
echo -e "\n${BOLD}${CYAN}Removing redundant helper scripts...${NC}"
if [ -f "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/QUICK_REFERENCE.sh" ]; then
    backup_and_delete "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/QUICK_REFERENCE.sh"
fi

if [ -f "${SCRIPT_DIR}/activate_venv.sh" ]; then
    backup_and_delete "${SCRIPT_DIR}/activate_venv.sh"
fi

# Summary
echo -e "\n${BOLD}${GREEN}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║           Cleanup Complete!                   ║${NC}"
echo -e "${BOLD}${GREEN}╚═══════════════════════════════════════════════╝${NC}"
echo
echo -e "${CYAN}Summary:${NC}"
echo -e "  - Removed all duplicate PDF files"
echo -e "  - Removed redundant documentation (30+ files)"
echo -e "  - Removed legacy code directory"
echo -e "  - Removed old installation scripts"
echo
echo -e "${YELLOW}Backup location: $BACKUP_DIR${NC}"
echo -e "${GREEN}All files backed up before deletion${NC}"
echo
echo -e "${BOLD}${CYAN}Next Steps:${NC}"
echo -e "  1. Use ${BOLD}./run_afpacket_mode.sh${NC} for AF_PACKET mode"
echo -e "  2. Use ${BOLD}./run_dpdk_mode.sh${NC} for DPDK mode"
echo -e "  3. See ${BOLD}README.md${NC} for documentation"
echo
