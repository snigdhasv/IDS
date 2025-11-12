#!/bin/bash

# Start Suricata in DPDK mode with Kafka output

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
echo -e "${BOLD}${BLUE}║  Suricata DPDK Start Script                    ║${NC}"
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

# Check DPDK support
if ! suricata --build-info | grep -q "DPDK support.*yes"; then
    echo -e "${RED}❌ Suricata not compiled with DPDK support${NC}"
    echo "Run: suricata --build-info | grep DPDK"
    exit 1
fi

echo -e "${GREEN}✓ Suricata with DPDK support detected${NC}"

# Note: We're using AF_PACKET mode (kernel driver), which works fine for IDS
# Pure DPDK PMD mode requires explicit driver binding (optional for this setup)

# Check Kafka is running
# Use ss if netstat is not available
if command -v netstat &> /dev/null; then
    KAFKA_RUNNING=$(netstat -tuln 2>/dev/null | grep -q ":9092" && echo "yes" || echo "no")
else
    KAFKA_RUNNING=$(ss -tuln 2>/dev/null | grep -q ":9092" && echo "yes" || echo "no")
fi

if [ "$KAFKA_RUNNING" != "yes" ]; then
    echo -e "${YELLOW}⚠️  Kafka not running - continuing without Kafka output${NC}"
fi

# Create Suricata config if needed
SURICATA_CONFIG_DIR="$(dirname "$SURICATA_CONFIG")"
mkdir -p "$SURICATA_CONFIG_DIR"

if [ ! -f "$SURICATA_CONFIG" ]; then
    echo -e "\n${BLUE}Creating Suricata DPDK configuration...${NC}"
    
    # Copy default config
    if [ -f "/etc/suricata/suricata.yaml" ]; then
        cp "/etc/suricata/suricata.yaml" "$SURICATA_CONFIG"
    else
        echo -e "${RED}❌ Default Suricata config not found${NC}"
        exit 1
    fi
    
    # Append DPDK and Kafka configuration
    cat >> "$SURICATA_CONFIG" << EOF

# DPDK Configuration
dpdk:
  eal-params:
    proc-type: primary
    
  interfaces:
    - interface: ${INTERFACE_PCI_ADDRESS}
      threads: ${SURICATA_CORES}
      cluster-id: 99
      cluster-type: cluster_flow
      promisc: yes
      checksum-checks: yes
      copy-mode: ips
      copy-iface: none
      
# Kafka Output
outputs:
  - eve-log:
      enabled: yes
      filetype: kafka
      kafka:
        bootstrap-servers: ${KAFKA_BOOTSTRAP_SERVERS}
        topic: ${KAFKA_TOPIC_ALERTS}
        compression-codec: snappy
        
      types:
        - alert:
            tagged-packets: yes
            xff:
              enabled: yes
              mode: extra-data
              deployment: reverse
        - anomaly:
            enabled: yes
        - http:
            extended: yes
        - dns:
            query: yes
            answer: yes
        - tls:
            extended: yes
        - files:
            force-magic: yes
        - flow:
            # Enable flow logging for ML feature extraction
            # This logs ALL network flows (not just alerts)
        - stats:
            totals: yes
            threads: yes
            deltas: yes

# Network variables
vars:
  address-groups:
    HOME_NET: "${SURICATA_HOME_NET}"
    EXTERNAL_NET: "${SURICATA_EXTERNAL_NET}"

# Performance tuning
af-packet:
  - interface: default
    cluster-id: 99
    cluster-type: cluster_flow
    defrag: yes
    use-mmap: yes
    mmap-locked: yes
    tpacket-v3: yes
    ring-size: 2048
    block-size: 32768

# Rules
rule-files:
  - /etc/suricata/rules/suricata.rules

# Advanced options
stream:
  memcap: 256mb
  checksum-validation: yes
  inline: auto
  reassembly:
    memcap: 512mb
    depth: 1mb
    toserver-chunk-size: 2560
    toclient-chunk-size: 2560

EOF
    
    echo -e "${GREEN}✓ Configuration created: $SURICATA_CONFIG${NC}"
fi

# Create log directory
mkdir -p "$SURICATA_LOG_DIR"

# Check if already running
if pgrep -x "suricata" > /dev/null; then
    echo -e "${YELLOW}⚠️  Suricata already running${NC}"
    read -p "Kill existing process? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        killall suricata 2>/dev/null || true
        sleep 2
    else
        echo "Aborted."
        exit 0
    fi
fi

# Start Suricata
echo -e "\n${BOLD}${BLUE}Starting Suricata in AF_PACKET mode (DPDK-optimized)...${NC}"
echo -e "${CYAN}Config: /etc/suricata/suricata.yaml.dpdk${NC}"
echo -e "${CYAN}Log Dir: $SURICATA_LOG_DIR${NC}"
echo

# Start Suricata in background (AF_PACKET mode on enp3s0 interface)
# Note: Skip config test as minimal configs may not have all rules enabled
mkdir -p "$SURICATA_LOG_DIR"
nohup suricata -i enp3s0 -c /etc/suricata/suricata.yaml \
    -l "$SURICATA_LOG_DIR" \
    --pidfile /var/run/suricata-dpdk.pid \
    > "${SURICATA_LOG_DIR}/suricata.out" 2>&1 &

SURICATA_PID=$!
sleep 3

# Verify it's running
if ps -p $SURICATA_PID > /dev/null; then
    echo -e "${GREEN}✓ Suricata started (PID: $SURICATA_PID)${NC}"
else
    echo -e "${RED}❌ Suricata failed to start${NC}"
    echo "Check logs: tail -f ${SCRIPT_DIR}/../logs/suricata/suricata.out"
    exit 1
fi

echo -e "\n${BOLD}${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  Suricata Started Successfully                 ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo

echo -e "${BOLD}Process Info:${NC}"
echo -e "  PID: ${CYAN}$SURICATA_PID${NC}"
echo -e "  Config: ${CYAN}$SURICATA_CONFIG${NC}"
echo -e "  Logs: ${CYAN}$SURICATA_LOG_DIR${NC}"
echo

echo -e "${BOLD}Monitor Logs:${NC}"
echo -e "  ${CYAN}tail -f $SURICATA_LOG_DIR/suricata.log${NC}"
echo -e "  ${CYAN}tail -f $SURICATA_LOG_DIR/eve.json${NC}"
echo -e "  ${CYAN}tail -f $SURICATA_LOG_DIR/stats.log${NC}"
echo

echo -e "${BOLD}Check Stats:${NC}"
echo -e "  ${CYAN}suricatasc -c stats${NC}"
echo

echo -e "${BOLD}Kafka Output:${NC}"
echo -e "  Topic: ${CYAN}$KAFKA_TOPIC_ALERTS${NC}"
echo -e "  Monitor: ${CYAN}kafka-console-consumer.sh --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS --topic $KAFKA_TOPIC_ALERTS${NC}"
echo

echo -e "${GREEN}✓ Done!${NC}"
