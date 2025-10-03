#!/bin/bash

# Check Pipeline Status

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║  IDS Pipeline Status Check                     ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo

# Check DPDK
echo -e "${BOLD}${CYAN}▶ DPDK Status${NC}"
echo -e "${CYAN}$(printf '─%.0s' {1..50})${NC}"
if command -v dpdk-devbind.py &> /dev/null; then
    DPDK_DEVICES=$(dpdk-devbind.py --status 2>/dev/null | grep -A 5 "Network devices using DPDK" | grep -c "drv=" || echo "0")
    if [ "$DPDK_DEVICES" -gt 0 ]; then
        echo -e "${GREEN}✓ DPDK installed and $DPDK_DEVICES device(s) bound${NC}"
        dpdk-devbind.py --status 2>/dev/null | grep -A 10 "Network devices using DPDK"
    else
        echo -e "${YELLOW}⚠️  DPDK installed but no devices bound${NC}"
    fi
else
    echo -e "${RED}✗ DPDK not installed${NC}"
fi

# Check Hugepages
HUGEPAGES=$(grep -E "HugePages_Total|HugePages_Free" /proc/meminfo)
echo -e "\nHugepages:"
echo "$HUGEPAGES"
echo

# Check Kafka
echo -e "${BOLD}${CYAN}▶ Kafka Status${NC}"
echo -e "${CYAN}$(printf '─%.0s' {1..50})${NC}"
if netstat -tuln 2>/dev/null | grep -q ":9092"; then
    echo -e "${GREEN}✓ Kafka running on port 9092${NC}"
    
    # Check topics
    if command -v kafka-topics.sh &> /dev/null; then
        echo -e "\nTopics:"
        kafka-topics.sh --list --bootstrap-server localhost:9092 2>/dev/null | sed 's/^/  /'
    fi
else
    echo -e "${RED}✗ Kafka not running on port 9092${NC}"
fi
echo

# Check Suricata
echo -e "${BOLD}${CYAN}▶ Suricata Status${NC}"
echo -e "${CYAN}$(printf '─%.0s' {1..50})${NC}"
if pgrep -x "suricata" > /dev/null; then
    SURICATA_PID=$(pgrep -x "suricata")
    echo -e "${GREEN}✓ Suricata running (PID: $SURICATA_PID)${NC}"
    
    # Check DPDK support
    if suricata --build-info 2>/dev/null | grep -q "DPDK support.*yes"; then
        echo -e "${GREEN}✓ DPDK support enabled${NC}"
    else
        echo -e "${YELLOW}⚠️  DPDK support not enabled${NC}"
    fi
    
    # Recent stats
    if [ -f "/var/log/suricata/stats.log" ]; then
        echo -e "\nRecent stats (last 5 lines):"
        tail -n 5 /var/log/suricata/stats.log | sed 's/^/  /'
    fi
else
    echo -e "${RED}✗ Suricata not running${NC}"
fi
echo

# Check ML Consumer
echo -e "${BOLD}${CYAN}▶ ML Consumer Status${NC}"
echo -e "${CYAN}$(printf '─%.0s' {1..50})${NC}"
if pgrep -f "ml_kafka_consumer.py" > /dev/null; then
    ML_PID=$(pgrep -f "ml_kafka_consumer.py")
    echo -e "${GREEN}✓ ML Consumer running (PID: $ML_PID)${NC}"
    
    # Check recent log
    if [ -f "${SCRIPT_DIR}/../logs/ml/ml_consumer.log" ]; then
        echo -e "\nRecent activity (last 5 lines):"
        tail -n 5 "${SCRIPT_DIR}/../logs/ml/ml_consumer.log" | sed 's/^/  /'
    fi
else
    echo -e "${RED}✗ ML Consumer not running${NC}"
fi
echo

# System Resources
echo -e "${BOLD}${CYAN}▶ System Resources${NC}"
echo -e "${CYAN}$(printf '─%.0s' {1..50})${NC}"
echo -e "CPU Usage:"
top -bn1 | grep "Cpu(s)" | sed 's/^/  /'
echo -e "\nMemory Usage:"
free -h | grep -E "Mem:|Swap:" | sed 's/^/  /'
echo -e "\nDisk Usage:"
df -h / | tail -n 1 | awk '{print "  Used: "$3" / "$2" ("$5")"}'
echo

# Summary
echo -e "${BOLD}${CYAN}▶ Pipeline Summary${NC}"
echo -e "${CYAN}$(printf '─%.0s' {1..50})${NC}"

COMPONENTS_UP=0
COMPONENTS_TOTAL=4

# Count running components
if [ "$DPDK_DEVICES" -gt 0 ]; then ((COMPONENTS_UP++)); fi
if netstat -tuln 2>/dev/null | grep -q ":9092"; then ((COMPONENTS_UP++)); fi
if pgrep -x "suricata" > /dev/null; then ((COMPONENTS_UP++)); fi
if pgrep -f "ml_kafka_consumer.py" > /dev/null; then ((COMPONENTS_UP++)); fi

if [ $COMPONENTS_UP -eq $COMPONENTS_TOTAL ]; then
    echo -e "${BOLD}${GREEN}✓ Full pipeline operational ($COMPONENTS_UP/$COMPONENTS_TOTAL components)${NC}"
elif [ $COMPONENTS_UP -gt 0 ]; then
    echo -e "${BOLD}${YELLOW}⚠️  Partial pipeline ($COMPONENTS_UP/$COMPONENTS_TOTAL components running)${NC}"
else
    echo -e "${BOLD}${RED}✗ Pipeline not running (0/$COMPONENTS_TOTAL components)${NC}"
fi

echo
echo -e "${BOLD}Quick Actions:${NC}"
echo -e "  Start all: ${CYAN}./scripts/start_all.sh${NC}"
echo -e "  Stop all:  ${CYAN}sudo ./scripts/stop_all.sh${NC}"
echo -e "  Logs:      ${CYAN}./scripts/view_logs.sh${NC}"
echo
