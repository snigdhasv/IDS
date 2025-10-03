#!/bin/bash

# Stop All Pipeline Components

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
echo -e "${BOLD}${BLUE}║  Stop IDS Pipeline                             ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo

# Load configuration
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# Stop ML Consumer
echo -e "${BLUE}Stopping ML Consumer...${NC}"
if pgrep -f "ml_kafka_consumer.py" > /dev/null; then
    pkill -f "ml_kafka_consumer.py"
    sleep 2
    if pgrep -f "ml_kafka_consumer.py" > /dev/null; then
        pkill -9 -f "ml_kafka_consumer.py"
    fi
    echo -e "${GREEN}✓ ML Consumer stopped${NC}"
else
    echo -e "${YELLOW}⚠️  ML Consumer not running${NC}"
fi

# Stop Suricata
echo -e "\n${BLUE}Stopping Suricata...${NC}"
if pgrep -x "suricata" > /dev/null; then
    killall suricata 2>/dev/null || true
    sleep 3
    if pgrep -x "suricata" > /dev/null; then
        killall -9 suricata 2>/dev/null || true
    fi
    echo -e "${GREEN}✓ Suricata stopped${NC}"
else
    echo -e "${YELLOW}⚠️  Suricata not running${NC}"
fi

# Ask about Kafka
echo -e "\n${BLUE}Kafka Management${NC}"
if netstat -tuln 2>/dev/null | grep -q ":9092"; then
    read -p "Stop Kafka? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "/opt/kafka/bin/kafka-server-stop.sh" ]; then
            /opt/kafka/bin/kafka-server-stop.sh
            sleep 3
            /opt/kafka/bin/zookeeper-server-stop.sh
            echo -e "${GREEN}✓ Kafka stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  Kafka stop script not found${NC}"
        fi
    else
        echo -e "${CYAN}Kafka left running${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Kafka not running${NC}"
fi

# Ask about DPDK unbinding
echo -e "\n${BLUE}DPDK Interface Management${NC}"
DEVBIND=$(which dpdk-devbind.py 2>/dev/null || echo "/usr/local/bin/dpdk-devbind.py")
if [ -f "$DEVBIND" ]; then
    DPDK_BOUND=$("$DEVBIND" --status 2>/dev/null | grep -c "drv=vfio-pci\|drv=igb_uio\|drv=uio_pci_generic" || echo "0")
    if [ "$DPDK_BOUND" -gt 0 ]; then
        read -p "Unbind DPDK interfaces? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [ -x "${SCRIPT_DIR}/unbind_interface.sh" ]; then
                "${SCRIPT_DIR}/unbind_interface.sh"
            else
                echo -e "${YELLOW}⚠️  Unbind script not found${NC}"
            fi
        else
            echo -e "${CYAN}DPDK interfaces left bound${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  No DPDK interfaces bound${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  DPDK not installed${NC}"
fi

echo -e "\n${BOLD}${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  Pipeline Stopped                              ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo

echo -e "${BOLD}Status:${NC}"
echo -e "  ML Consumer: ${CYAN}$(pgrep -f 'ml_kafka_consumer.py' > /dev/null && echo 'Running' || echo 'Stopped')${NC}"
echo -e "  Suricata:    ${CYAN}$(pgrep -x 'suricata' > /dev/null && echo 'Running' || echo 'Stopped')${NC}"
echo -e "  Kafka:       ${CYAN}$(netstat -tuln 2>/dev/null | grep -q ':9092' && echo 'Running' || echo 'Stopped')${NC}"
echo -e "  DPDK Bound:  ${CYAN}$DPDK_BOUND interface(s)${NC}"
echo

echo -e "${GREEN}✓ Done!${NC}"
