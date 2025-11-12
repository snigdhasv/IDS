#!/bin/bash

################################################################################
# Configure Suricata & Feature Engine for DPDK Input
################################################################################
# Sets up Suricata and the Feature Engine to capture packets directly from
# the DPDK-bound X520 interface, enabling high-performance packet processing.
#
# This allows the IDS to process replayed PCAP traffic as if it were real
# network packets arriving at 10 Gbps line rate.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IDS_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_FILE="${IDS_DIR}/dpdk_suricata_ml_pipeline/config/pipeline.conf"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  Configure DPDK Input for Suricata & ML IDS    ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}\n"
}

load_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}[!] Config file not found: $CONFIG_FILE${NC}"
        exit 1
    fi
    source "$CONFIG_FILE"
    echo -e "${GREEN}[+] Config loaded${NC}"
}

check_dpdk_binding() {
    echo -e "${CYAN}[*] Checking DPDK binding...${NC}"
    
    DEVBIND="/usr/local/bin/dpdk-devbind.py"
    if [ ! -f "$DEVBIND" ]; then
        echo -e "${RED}[!] dpdk-devbind.py not found${NC}"
        exit 1
    fi
    
    # Check if X520 is bound
    if ! sudo python3 "$DEVBIND" --status | grep -q "drv=uio_pci_generic"; then
        echo -e "${RED}[!] X520 not bound to DPDK${NC}"
        echo -e "${YELLOW}    Run: sudo python3 $DEVBIND --bind=uio_pci_generic 01:00.0${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}[+] X520 bound to DPDK (uio_pci_generic)${NC}\n"
}

configure_suricata_dpdk() {
    echo -e "${CYAN}[*] Configuring Suricata for DPDK...${NC}"
    
    SURICATA_CONF="/etc/suricata/suricata.yaml"
    
    if [ ! -f "$SURICATA_CONF" ]; then
        echo -e "${YELLOW}[!] Suricata config not found at $SURICATA_CONF${NC}"
        echo -e "    Trying alternate locations..."
        
        SURICATA_CONF=$(find /etc -name "suricata.yaml" 2>/dev/null | head -1)
        if [ -z "$SURICATA_CONF" ]; then
            echo -e "${RED}[!] Could not find suricata.yaml${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}[+] Found Suricata config: $SURICATA_CONF${NC}"
    
    # Create backup
    if [ ! -f "${SURICATA_CONF}.dpdk_backup" ]; then
        sudo cp "$SURICATA_CONF" "${SURICATA_CONF}.dpdk_backup"
        echo -e "${GREEN}[+] Backup created: ${SURICATA_CONF}.dpdk_backup${NC}"
    fi
    
    # Ensure DPDK section exists in config
    if ! sudo grep -q "dpdk:" "$SURICATA_CONF"; then
        echo -e "${YELLOW}[!] DPDK config section not found in suricata.yaml${NC}"
        echo -e "    This is expected - Suricata will use command-line DPDK args"
    fi
    
    echo -e "${GREEN}[+] Suricata ready for DPDK mode${NC}\n"
}

configure_feature_engine() {
    echo -e "${CYAN}[*] Configuring Feature Engine for DPDK...${NC}"
    
    FEATURE_ENGINE_CONFIG="${IDS_DIR}/dpdk_suricata_ml_pipeline/config/feature_engine.conf"
    
    if [ ! -f "$FEATURE_ENGINE_CONFIG" ]; then
        echo -e "${YELLOW}[!] Feature Engine config not found, creating...${NC}"
        mkdir -p "$(dirname "$FEATURE_ENGINE_CONFIG")"
        
        cat > "$FEATURE_ENGINE_CONFIG" << 'EOF'
# Feature Engine Configuration

[General]
mode = dpdk
timeout = 10
batch_size = 32

[DPDK]
pci_addr = 0000:01:00.0
rx_queue = 1
tx_queue = 1
mtu = 1500

[Kafka]
bootstrap_servers = localhost:9092
features_topic = ml-features
alerts_topic = suricata-alerts

[Features]
feature_count = 65
normalization = minmax
pca_enabled = false
EOF
        echo -e "${GREEN}[+] Created Feature Engine config${NC}"
    else
        echo -e "${GREEN}[+] Feature Engine config found${NC}"
    fi
    
    echo -e "${GREEN}[+] Feature Engine ready for DPDK mode${NC}\n"
}

show_startup_commands() {
    echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  DPDK Pipeline Configuration Complete          ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}\n"
    
    echo -e "${YELLOW}Next Steps:${NC}\n"
    
    echo -e "${GREEN}1. Start the complete DPDK pipeline:${NC}"
    echo -e "   ${CYAN}sudo bash ${IDS_DIR}/run_realtime_engine_dpdk.sh start${NC}\n"
    
    echo -e "${GREEN}2. In another terminal, replay PCAP traffic:${NC}"
    echo -e "   ${CYAN}python3 ${IDS_DIR}/dpdk_pcap_replay.py /path/to/traffic.pcap${NC}\n"
    
    echo -e "${GREEN}3. Monitor predictions in real-time:${NC}"
    echo -e "   ${CYAN}tail -f ${IDS_DIR}/logs/ml_consumer.log${NC}\n"
    
    echo -e "${GREEN}4. View Kafka topics:${NC}"
    echo -e "   ${CYAN}kafka-topics.sh --list --bootstrap-server localhost:9092${NC}\n"
    
    echo -e "${YELLOW}Architecture:${NC}"
    echo -e "  PCAP Replay (X520 TX)  →  DPDK PMD (kernel bypass)"
    echo -e "                         →  Suricata DPDK (captures + signatures)"
    echo -e "                         →  Feature Engine (CICIDS65)"
    echo -e "                         →  ML Consumer (ensemble predictions)\n"
    
    echo -e "${CYAN}Available PCAP samples:${NC}"
    find "${IDS_DIR}/dpdk_suricata_ml_pipeline/pcap_samples" -name "*.pcap" -exec basename {} \; 2>/dev/null | \
        sed 's/^/  • /'
    echo
}

main() {
    print_header
    
    if [ "$EUID" -eq 0 ]; then
        # Already root, proceed
        load_config
        check_dpdk_binding
        configure_suricata_dpdk
        configure_feature_engine
        show_startup_commands
    else
        # Need to run with sudo for some operations
        echo -e "${CYAN}[*] This script requires sudo for some operations${NC}"
        echo -e "    Running configuration checks...\n"
        
        load_config
        check_dpdk_binding
        
        echo -e "${CYAN}[*] Running Suricata config with sudo...${NC}"
        sudo bash -c "
            SURICATA_CONF='/etc/suricata/suricata.yaml'
            if [ ! -f \"\${SURICATA_CONF}.dpdk_backup\" ]; then
                cp \"\$SURICATA_CONF\" \"\${SURICATA_CONF}.dpdk_backup\"
                echo -e '${GREEN}[+] Backup created${NC}'
            fi
        "
        
        configure_feature_engine
        show_startup_commands
    fi
}

main "$@"
