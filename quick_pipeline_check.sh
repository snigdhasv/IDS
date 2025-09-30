#!/bin/bash

# Simple DPDK-IDS Pipeline Status Check
# Focuses on the core functionality that's working

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}🔍 DPDK-IDS Pipeline Quick Check${NC}"
echo -e "${BLUE}================================${NC}"
echo

# Check if running as root for packet injection
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}❌ Run with sudo for packet injection tests${NC}"
    echo "Usage: sudo ./quick_pipeline_check.sh"
    exit 1
fi

echo -e "${YELLOW}📋 Core Component Status${NC}"

# 1. Check Suricata services
echo -n "Suricata IDS: "
if systemctl is-active --quiet suricata-simple; then
    echo -e "${GREEN}✓ suricata-simple active${NC}"
    SURICATA_OK=true
elif systemctl is-active --quiet suricata-kafka; then
    echo -e "${GREEN}✓ suricata-kafka active${NC}"
    SURICATA_OK=true
elif systemctl is-active --quiet suricata; then
    echo -e "${GREEN}✓ suricata active${NC}"
    SURICATA_OK=true
else
    echo -e "${RED}❌ No Suricata service active${NC}"
    SURICATA_OK=false
fi

# 2. Check Kafka
echo -n "Kafka: "
if pgrep -f kafka > /dev/null; then
    echo -e "${GREEN}✓ Running${NC}"
    KAFKA_OK=true
else
    echo -e "${RED}❌ Not running${NC}"
    KAFKA_OK=false
fi

# 3. Check EVE-Kafka Bridge
echo -n "EVE-Kafka Bridge: "
if pgrep -f eve_kafka_bridge > /dev/null; then
    echo -e "${GREEN}✓ Running${NC}"
    BRIDGE_OK=true
else
    echo -e "${RED}❌ Not running${NC}"
    BRIDGE_OK=false
fi

# 4. Check Python dependencies
echo -n "Python Dependencies: "
if python3 -c "from scapy.all import Ether, IP, TCP; import kafka; import psutil" 2>/dev/null; then
    echo -e "${GREEN}✓ Available${NC}"
    PYTHON_OK=true
else
    echo -e "${RED}❌ Missing${NC}"
    PYTHON_OK=false
fi

# 5. Check network interface
echo -n "Interface enp2s0: "
if ip link show enp2s0 > /dev/null 2>&1; then
    if ip link show enp2s0 | grep -q "state UP"; then
        echo -e "${GREEN}✓ UP${NC}"
        INTERFACE_OK=true
    else
        echo -e "${YELLOW}⚠️  DOWN${NC}"
        INTERFACE_OK=false
    fi
else
    echo -e "${RED}❌ Not found${NC}"
    INTERFACE_OK=false
fi

# 6. Check Suricata logs
echo -n "Suricata Logging: "
if [ -f "/var/log/suricata/eve.json" ]; then
    # Check if file was updated in last 5 minutes
    if [ $(find /var/log/suricata/eve.json -mmin -5 2>/dev/null | wc -l) -gt 0 ]; then
        echo -e "${GREEN}✓ Active${NC}"
        LOGGING_OK=true
    else
        echo -e "${YELLOW}⚠️  Stale${NC}"
        LOGGING_OK=false
    fi
else
    echo -e "${RED}❌ No log file${NC}"
    LOGGING_OK=false
fi

echo

# Quick functional test if core components are working
if [ "$SURICATA_OK" = true ] && [ "$PYTHON_OK" = true ] && [ "$INTERFACE_OK" = true ]; then
    echo -e "${YELLOW}🧪 Quick Functional Test${NC}"
    
    echo "Generating 3 test packets..."
    python3 -c "
from scapy.all import Ether, IP, TCP, sendp
import time

packets = [
    Ether()/IP(src='10.0.1.100', dst='192.168.1.10')/TCP(sport=12345, dport=80),
    Ether()/IP(src='10.0.1.101', dst='192.168.1.10')/TCP(sport=12346, dport=443),
    Ether()/IP(src='10.0.1.102', dst='8.8.8.8')/TCP(sport=12347, dport=53)
]

for i, pkt in enumerate(packets, 1):
    print(f'  Packet {i}: {pkt[IP].src} → {pkt[IP].dst}')
    sendp(pkt, iface='enp2s0', verbose=0)
    time.sleep(0.5)

print('✓ Test packets sent')
"
    
    echo "Waiting 3 seconds for processing..."
    sleep 3
    
    # Check if new events were generated
    if [ "$LOGGING_OK" = true ]; then
        RECENT_EVENTS=$(tail -10 /var/log/suricata/eve.json 2>/dev/null | wc -l)
        if [ "$RECENT_EVENTS" -gt 0 ]; then
            echo -e "${GREEN}✓ Suricata processing packets (${RECENT_EVENTS} recent events)${NC}"
        else
            echo -e "${YELLOW}⚠️  Check Suricata processing${NC}"
        fi
    fi
    
else
    echo -e "${YELLOW}⚠️  Skipping functional test (core components not ready)${NC}"
fi

echo

# Overall status
COMPONENTS_OK=0
[ "$SURICATA_OK" = true ] && ((COMPONENTS_OK++))
[ "$KAFKA_OK" = true ] && ((COMPONENTS_OK++))
[ "$BRIDGE_OK" = true ] && ((COMPONENTS_OK++))
[ "$PYTHON_OK" = true ] && ((COMPONENTS_OK++))
[ "$INTERFACE_OK" = true ] && ((COMPONENTS_OK++))
[ "$LOGGING_OK" = true ] && ((COMPONENTS_OK++))

echo -e "${BOLD}${BLUE}📊 Overall Status${NC}"
echo -e "Components working: ${COMPONENTS_OK}/6"

if [ $COMPONENTS_OK -eq 6 ]; then
    echo -e "${GREEN}🎉 EXCELLENT - All components operational${NC}"
    echo -e "Ready for: ${BOLD}sudo python3 realtime_dpdk_pipeline.py --mode demo${NC}"
elif [ $COMPONENTS_OK -ge 4 ]; then
    echo -e "${YELLOW}👍 GOOD - Core functionality available${NC}"
    echo -e "Try: ${BOLD}sudo python3 realtime_dpdk_pipeline.py --mode validate${NC}"
else
    echo -e "${RED}❌ NEEDS ATTENTION - Multiple components need fixing${NC}"
fi

echo

# Quick fix suggestions
echo -e "${YELLOW}🔧 Quick Fixes${NC}"
[ "$KAFKA_OK" = false ] && echo "• Start Kafka: cd Suricata_Setup && ./setup_kafka.sh"
[ "$BRIDGE_OK" = false ] && echo "• Start bridge: cd Suricata_Setup && python3 eve_kafka_bridge.py &"
[ "$PYTHON_OK" = false ] && echo "• Install deps: sudo pip3 install scapy kafka-python psutil"
[ "$SURICATA_OK" = false ] && echo "• Start Suricata: sudo systemctl start suricata-simple"

echo
echo -e "${BLUE}Quick validation: ${BOLD}sudo python3 realtime_dpdk_pipeline.py --mode validate${NC}"
