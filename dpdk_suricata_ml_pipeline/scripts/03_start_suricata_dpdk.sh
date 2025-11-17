#!/bin/bash

# Start Suricata in DPDK mode with Kafka output

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/pipeline.conf"
PID_FILE="/var/run/suricata-dpdk.pid"

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

ensure_dpdk_binding() {
    local devbind="$(command -v dpdk-devbind.py 2>/dev/null || echo "/usr/local/bin/dpdk-devbind.py")"
    if [ ! -x "$devbind" ]; then
        echo -e "${RED}❌ dpdk-devbind.py not found${NC}"
        exit 1
    fi

    if ! "$devbind" --status 2>/dev/null | grep -q "${INTERFACE_PCI_ADDRESS}.*drv="; then
        echo -e "${RED}❌ Interface ${INTERFACE_PCI_ADDRESS} is not bound to a DPDK driver${NC}"
        echo -e "    Use scripts/01_bind_interface.sh before starting Suricata"
        exit 1
    fi
    echo -e "${GREEN}✓ Interface ${INTERFACE_PCI_ADDRESS} bound to DPDK${NC}"
}

ensure_hugepages() {
    local hp_1g="/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages"
    local hp_2m="/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages"
    local target_mb="${DPDK_HUGEPAGES:-2048}"

    # Ensure the configured value is a positive integer
    if ! [[ "$target_mb" =~ ^[0-9]+$ ]] || [ "$target_mb" -le 0 ]; then
        target_mb="2048"
    fi

    local page_file=""
    local page_mb=""
    local page_label=""

    if [ -w "$hp_2m" ]; then
        page_file="$hp_2m"
        page_mb=2
        page_label="2MB"
    elif [ -w "$hp_1g" ]; then
        page_file="$hp_1g"
        page_mb=1024
        page_label="1GB"
    fi

    if [ -z "$page_file" ]; then
        echo -e "${YELLOW}⚠️  Unable to configure hugepages automatically${NC}"
        return
    fi

    local target_pages=$(( (target_mb + page_mb - 1) / page_mb ))
    if [ "$target_pages" -lt 1 ]; then
        target_pages=1
    fi

    local current
    current=$(cat "$page_file" 2>/dev/null || echo 0)
    if [ "${current:-0}" -lt "$target_pages" ]; then
        echo "$target_pages" > "$page_file"
    fi

    local configured_mb=$(( target_pages * page_mb ))
    echo -e "${GREEN}✓ HugePages (${page_label}) available: $(cat "$page_file") (~${configured_mb}MB reserved, config asked for ${target_mb}MB)${NC}"
}

ensure_rule_file() {
    local rule_dir="/etc/suricata/rules"
    local rule_file="${rule_dir}/dpdk-minimal.rules"
    mkdir -p "$rule_dir"
    if [ ! -f "$rule_file" ]; then
        cat > "$rule_file" <<'EOF'
alert icmp any any -> any any (msg:"DPDK test rule"; sid:9000001; rev:1;)
EOF
        echo -e "${GREEN}✓ Created ${rule_file}${NC}"
    fi
}

ensure_suricata_config() {
    local config_dir="$(dirname "$SURICATA_CONFIG")"
    mkdir -p "$config_dir"
    if [ -f "$SURICATA_CONFIG" ]; then
        return
    fi

    cat > "$SURICATA_CONFIG" <<EOF
%YAML 1.1
---
# Auto-generated DPDK Suricata config
vars:
  address-groups:
    HOME_NET: "${SURICATA_HOME_NET}"
    EXTERNAL_NET: "${SURICATA_EXTERNAL_NET}"

threading:
  set-cpu-affinity: yes
  cpu-affinity:
    - management-cpu-set:
        cpu: [ 0 ]
    - receive-cpu-set:
        cpu: [ 1, 2 ]
    - worker-cpu-set:
        cpu: [ 3, 4 ]

stats:
    enabled: yes
    interval: 10

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
      copy-mode: none
      copy-iface: none

outputs:
  - eve-log:
      enabled: yes
      filetype: regular
      filename: /var/log/suricata/eve.json
      types:
        - alert
        - flow
        - dns
        - tls
        - stats
        - packet

default-rule-path: /etc/suricata/rules
rule-files:
  - dpdk-minimal.rules

stream:
  memcap: 64mb
  checksum-validation: yes

logging:
  default-log-level: info
  outputs:
    - file:
        enabled: yes
        filename: /var/log/suricata/suricata.log
EOF
    echo -e "${GREEN}✓ Generated ${SURICATA_CONFIG}${NC}"
}

wait_for_port() {
    local port=$1
    if command -v netstat &> /dev/null; then
        netstat -tuln 2>/dev/null | grep -q ":${port}" && return 0
    else
        ss -tuln 2>/dev/null | grep -q ":${port}" && return 0
    fi
    return 1
}

# Check if Suricata is installed
if ! command -v suricata &> /dev/null; then
    echo -e "${RED}❌ Suricata not installed${NC}"
    exit 1
fi

if ! suricata --build-info | grep -q "DPDK support.*yes"; then
    echo -e "${RED}❌ Suricata not compiled with DPDK support${NC}"
    exit 1
fi

ensure_dpdk_binding
ensure_hugepages
ensure_rule_file
ensure_suricata_config

# Check Kafka (optional)
if ! wait_for_port 9092; then
    echo -e "${YELLOW}⚠️  Kafka not running on port 9092 - continuing${NC}"
else
    echo -e "${GREEN}✓ Kafka detected on port 9092${NC}"
fi

mkdir -p "$SURICATA_LOG_DIR"

if pgrep -f "suricata.*--dpdk" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Suricata (DPDK) already running${NC}"
    read -p "Kill existing process? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "suricata.*--dpdk" 2>/dev/null || true
        sleep 2
    else
        echo "Aborted."
        exit 0
    fi
fi

if [[ -f "$PID_FILE" ]]; then
    PID_FROM_FILE=$(cat "$PID_FILE" 2>/dev/null || true)
    if [[ -n "$PID_FROM_FILE" ]] && kill -0 "$PID_FROM_FILE" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  PID file $PID_FILE indicates Suricata is still running (PID: $PID_FROM_FILE)${NC}"
        echo -e "    Use scripts/stop_all.sh or stop the process before restarting."
        exit 1
    fi
    echo -e "${YELLOW}⚠️  Removing stale PID file: $PID_FILE${NC}"
    rm -f "$PID_FILE" 2>/dev/null || true
fi

LOG_OUT="${SURICATA_LOG_DIR}/suricata-dpdk.out"
echo -e "\n${BOLD}${BLUE}Starting Suricata in DPDK mode...${NC}"
echo -e "  Config: ${SURICATA_CONFIG}"
echo -e "  Logs:   ${SURICATA_LOG_DIR}"
echo -e "  PCI:    ${INTERFACE_PCI_ADDRESS}"

nohup suricata --dpdk -c "$SURICATA_CONFIG" -l "$SURICATA_LOG_DIR" \
    --pidfile "$PID_FILE" \
    > "$LOG_OUT" 2>&1 &

SURICATA_PID=$!
sleep 3

if kill -0 $SURICATA_PID 2>/dev/null; then
    echo -e "${GREEN}✓ Suricata started (PID: $SURICATA_PID)${NC}"
else
    echo -e "${RED}❌ Suricata failed to start${NC}"
    echo "  Check log: tail -n 50 $LOG_OUT"
    exit 1
fi

echo -e "\n${BOLD}${GREEN}Suricata DPDK is running${NC}"
echo -e "  eve.json : /var/log/suricata/eve.json"
echo -e "  monitor  : tail -f $LOG_OUT"
echo -e "  stats    : suricatasc -c stats"
