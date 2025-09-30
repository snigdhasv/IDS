#!/bin/bash

# Complete DPDK-Suricata-Kafka Pipeline Validation
# This script validates the entire real-time IDS pipeline end-to-end

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
INTERFACE="enp2s0"
KAFKA_BROKER="localhost:9092"
TEST_DURATION=30
PACKET_RATE=50

echo -e "${BOLD}${BLUE}🔬 Complete DPDK-IDS Pipeline Validation${NC}"
echo -e "${CYAN}================================================${NC}"

# Function to check if service is running
check_service() {
    local service=$1
    if systemctl is-active --quiet $service; then
        echo -e "${GREEN}✓ $service is running${NC}"
        return 0
    else
        echo -e "${RED}❌ $service is not running${NC}"
        return 1
    fi
}

# Function to check process by name
check_process() {
    local process=$1
    if pgrep -f $process > /dev/null; then
        echo -e "${GREEN}✓ $process is running${NC}"
        return 0
    else
        echo -e "${RED}❌ $process is not running${NC}"
        return 1
    fi
}

# Phase 1: System Prerequisites
echo -e "\n${YELLOW}Phase 1: System Prerequisites${NC}"
echo "Checking system requirements..."

# Check root privileges for packet injection
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}❌ Root privileges required for packet injection${NC}"
    echo "Please run: sudo $0"
    exit 1
fi
echo -e "${GREEN}✓ Root privileges confirmed${NC}"

# Check network interface
if ip link show $INTERFACE > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Interface $INTERFACE available${NC}"
else
    echo -e "${RED}❌ Interface $INTERFACE not found${NC}"
    exit 1
fi

# Check Python dependencies
echo "Checking Python dependencies..."
python3 -c "import scapy, kafka, psutil" 2>/dev/null && echo -e "${GREEN}✓ Python dependencies available${NC}" || {
    echo -e "${RED}❌ Missing Python dependencies${NC}"
    echo "Install with: pip install scapy kafka-python psutil"
    exit 1
}

# Phase 2: Service Status
echo -e "\n${YELLOW}Phase 2: Service Status Check${NC}"

# Check Suricata (try both main and custom services)
SURICATA_RUNNING=false
if check_service suricata; then
    SURICATA_RUNNING=true
    SURICATA_SERVICE="suricata"
elif check_service suricata-simple; then
    SURICATA_RUNNING=true
    SURICATA_SERVICE="suricata-simple"
    echo -e "${GREEN}✓ suricata-simple is running${NC}"
elif check_service suricata-kafka; then
    SURICATA_RUNNING=true
    SURICATA_SERVICE="suricata-kafka"
    echo -e "${GREEN}✓ suricata-kafka is running${NC}"
fi

if [ "$SURICATA_RUNNING" = true ]; then
    # Get Suricata process info
    SURICATA_PID=$(pgrep -f suricata | head -1)
    if [ ! -z "$SURICATA_PID" ]; then
        echo "  Process ID: $SURICATA_PID"
        echo "  Memory usage: $(ps -p $SURICATA_PID -o %mem --no-headers | tr -d ' ')%"
        echo "  CPU usage: $(ps -p $SURICATA_PID -o %cpu --no-headers | tr -d ' ')%"
    fi
else
    echo -e "${RED}❌ No Suricata service is running${NC}"
    echo -e "${YELLOW}⚠️  Available services: suricata, suricata-simple, suricata-kafka${NC}"
fi

# Check Kafka (may be running manually)
if ! check_service kafka; then
    if check_process kafka; then
        echo -e "${GREEN}✓ Kafka process detected (manual installation)${NC}"
    else
        echo -e "${YELLOW}⚠️  Kafka not detected. Starting if available...${NC}"
        # Try to start Kafka if installed via our setup script
        if [ -f "/opt/kafka/bin/kafka-server-start.sh" ]; then
            echo "Attempting to start Kafka..."
            cd /opt/kafka
            nohup bin/kafka-server-start.sh config/server.properties > /dev/null 2>&1 &
            sleep 5
        fi
    fi
fi

# Phase 3: Configuration Validation
echo -e "\n${YELLOW}Phase 3: Configuration Validation${NC}"

# Check Suricata configuration
SURICATA_CONFIG="/etc/suricata/suricata.yaml"
if [ -f "$SURICATA_CONFIG" ]; then
    echo -e "${GREEN}✓ Suricata config found${NC}"
    
    # Check if interface is configured
    if grep -q "interface: $INTERFACE" $SURICATA_CONFIG; then
        echo -e "${GREEN}✓ Interface $INTERFACE configured in Suricata${NC}"
    else
        echo -e "${YELLOW}⚠️  Interface $INTERFACE not found in main config${NC}"
        # Check our custom configs
        if [ -f "/home/ifscr/SE_02_2025/IDS/Suricata_Setup/suricata-simple.yaml" ]; then
            if grep -q "interface: $INTERFACE" /home/ifscr/SE_02_2025/IDS/Suricata_Setup/suricata-simple.yaml; then
                echo -e "${GREEN}✓ Interface found in custom config${NC}"
            fi
        fi
    fi
else
    echo -e "${RED}❌ Suricata config not found${NC}"
fi

# Check Suricata log directory
LOG_PATHS=("/var/log/suricata/eve.json" "/tmp/suricata/eve.json")
ACTIVE_LOG=""
for log_path in "${LOG_PATHS[@]}"; do
    if [ -f "$log_path" ]; then
        # Check if file was modified recently (within last 5 minutes)
        if [ $(find "$log_path" -mmin -5 2>/dev/null | wc -l) -gt 0 ]; then
            echo -e "${GREEN}✓ Active Suricata log: $log_path${NC}"
            ACTIVE_LOG="$log_path"
            break
        else
            echo -e "${YELLOW}⚠️  Suricata log exists but not recently updated: $log_path${NC}"
        fi
    fi
done

if [ -z "$ACTIVE_LOG" ]; then
    echo -e "${RED}❌ No active Suricata log found${NC}"
fi

# Phase 4: Kafka Topic Validation
echo -e "\n${YELLOW}Phase 4: Kafka Topic Validation${NC}"

# Check if Kafka topics exist
KAFKA_CMD="/opt/kafka/bin/kafka-topics.sh"
if [ -f "$KAFKA_CMD" ]; then
    echo "Checking Kafka topics..."
    
    TOPICS=("suricata-events" "suricata-alerts" "suricata-stats")
    for topic in "${TOPICS[@]}"; do
        if $KAFKA_CMD --bootstrap-server $KAFKA_BROKER --list | grep -q $topic; then
            echo -e "${GREEN}✓ Topic $topic exists${NC}"
        else
            echo -e "${YELLOW}⚠️  Creating topic $topic...${NC}"
            $KAFKA_CMD --bootstrap-server $KAFKA_BROKER --create --topic $topic --partitions 1 --replication-factor 1 2>/dev/null || echo -e "${RED}❌ Failed to create $topic${NC}"
        fi
    done
else
    echo -e "${YELLOW}⚠️  Kafka command-line tools not found at expected location${NC}"
fi

# Phase 5: Real-time Pipeline Test
echo -e "\n${YELLOW}Phase 5: Real-time Pipeline Test${NC}"

echo "Starting comprehensive pipeline test..."
echo "Duration: ${TEST_DURATION}s, Packet rate: ${PACKET_RATE} pps"

# Start Kafka monitoring in background
echo "Starting Kafka event monitoring..."
python3 -c "
import sys
sys.path.append('/home/ifscr/SE_02_2025/IDS/Suricata_Setup')
import kafka_consumer
" > /tmp/kafka_monitor.log 2>&1 &
KAFKA_MONITOR_PID=$!

# Give monitoring time to start
sleep 3

# Start packet generation
echo "Starting packet generation..."
python3 /home/ifscr/SE_02_2025/IDS/realtime_dpdk_pipeline.py --mode generate --duration $TEST_DURATION --rate $PACKET_RATE &
PACKET_GEN_PID=$!

# Monitor for specified duration
echo "Monitoring pipeline for ${TEST_DURATION} seconds..."
for i in $(seq 1 $TEST_DURATION); do
    echo -ne "\rProgress: [$i/$TEST_DURATION] "
    # Show dots for visual progress
    printf "%0.s." $(seq 1 $((i * 50 / TEST_DURATION)))
    sleep 1
done
echo

# Stop background processes
kill $PACKET_GEN_PID 2>/dev/null || true
kill $KAFKA_MONITOR_PID 2>/dev/null || true

# Phase 6: Results Analysis
echo -e "\n${YELLOW}Phase 6: Results Analysis${NC}"

# Check Suricata logs for new events
if [ ! -z "$ACTIVE_LOG" ]; then
    echo "Analyzing Suricata events..."
    
    # Count recent events (last 2 minutes)
    RECENT_EVENTS=$(find "$ACTIVE_LOG" -mmin -2 -exec wc -l {} \; 2>/dev/null | head -1 | awk '{print $1}')
    if [ ! -z "$RECENT_EVENTS" ] && [ "$RECENT_EVENTS" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $RECENT_EVENTS recent events in Suricata log${NC}"
        
        # Show sample events
        echo "Sample recent events:"
        tail -5 "$ACTIVE_LOG" | while read line; do
            EVENT_TYPE=$(echo "$line" | python3 -c "import sys, json; print(json.load(sys.stdin).get('event_type', 'unknown'))" 2>/dev/null || echo "unknown")
            echo "  - Event type: $EVENT_TYPE"
        done
    else
        echo -e "${YELLOW}⚠️  No recent events found in Suricata log${NC}"
    fi
fi

# Check Kafka monitoring results
if [ -f "/tmp/kafka_monitor.log" ]; then
    KAFKA_EVENTS=$(grep -c "event_type" /tmp/kafka_monitor.log 2>/dev/null || echo "0")
    if [ ! -z "$KAFKA_EVENTS" ] && [ "$KAFKA_EVENTS" -gt 0 ]; then
        echo -e "${GREEN}✓ Detected $KAFKA_EVENTS events in Kafka stream${NC}"
    else
        echo -e "${YELLOW}⚠️  No events detected in Kafka stream${NC}"
    fi
    rm -f /tmp/kafka_monitor.log
fi

# System performance check
echo -e "\n${YELLOW}System Performance Summary:${NC}"
echo "CPU usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')"
echo "Memory usage: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
echo "Network interface status:"
ip -s link show $INTERFACE | grep -A 2 "RX:\|TX:"

# Phase 7: Integration Validation
echo -e "\n${YELLOW}Phase 7: Integration Status${NC}"

INTEGRATION_SCORE=0
MAX_SCORE=8

# Check each component
echo "Component status:"
# Check any Suricata service
if systemctl is-active --quiet suricata || systemctl is-active --quiet suricata-simple || systemctl is-active --quiet suricata-kafka; then
    echo -e "${GREEN}✓ Suricata active${NC}"; ((INTEGRATION_SCORE++))
else
    echo -e "${RED}❌ Suricata inactive${NC}"
fi

pgrep -f kafka > /dev/null && { echo -e "${GREEN}✓ Kafka running${NC}"; ((INTEGRATION_SCORE++)); } || echo -e "${RED}❌ Kafka not running${NC}"

[ ! -z "$ACTIVE_LOG" ] && { echo -e "${GREEN}✓ Suricata logging active${NC}"; ((INTEGRATION_SCORE++)); } || echo -e "${RED}❌ No active Suricata log${NC}"

python3 -c "from scapy.all import Ether, IP, TCP; print('Packet injection capable')" > /dev/null 2>&1 && { echo -e "${GREEN}✓ Packet injection capable${NC}"; ((INTEGRATION_SCORE++)); } || echo -e "${RED}❌ Packet injection failed${NC}"

# Test Kafka connectivity
timeout 5 python3 -c "
from kafka import KafkaConsumer
consumer = KafkaConsumer(bootstrap_servers=['$KAFKA_BROKER'])
consumer.close()
" 2>/dev/null && { echo -e "${GREEN}✓ Kafka connectivity${NC}"; ((INTEGRATION_SCORE++)); } || echo -e "${RED}❌ Kafka not accessible${NC}"

# Check if EVE-Kafka bridge is running
if [ -f "/home/ifscr/SE_02_2025/IDS/Suricata_Setup/eve_kafka_bridge.py" ]; then
    pgrep -f eve_kafka_bridge > /dev/null && { echo -e "${GREEN}✓ EVE-Kafka bridge active${NC}"; ((INTEGRATION_SCORE++)); } || echo -e "${YELLOW}⚠️  EVE-Kafka bridge not running${NC}"
fi

# Check hugepages (for DPDK)
HUGEPAGES=$(cat /proc/meminfo | grep HugePages_Total | awk '{print $2}')
[ "$HUGEPAGES" -gt 0 ] && { echo -e "${GREEN}✓ Hugepages configured ($HUGEPAGES pages)${NC}"; ((INTEGRATION_SCORE++)); } || echo -e "${YELLOW}⚠️  No hugepages configured${NC}"

# Interface monitoring
ip link show $INTERFACE | grep -q "state UP" && { echo -e "${GREEN}✓ Network interface UP${NC}"; ((INTEGRATION_SCORE++)); } || echo -e "${RED}❌ Network interface DOWN${NC}"

# Final Results
echo -e "\n${BOLD}${CYAN}📊 Validation Results${NC}"
echo -e "${CYAN}=====================${NC}"

PERCENTAGE=$((INTEGRATION_SCORE * 100 / MAX_SCORE))

if [ $PERCENTAGE -ge 90 ]; then
    echo -e "${GREEN}🎉 EXCELLENT: Pipeline fully operational ($INTEGRATION_SCORE/$MAX_SCORE components)${NC}"
elif [ $PERCENTAGE -ge 70 ]; then
    echo -e "${YELLOW}👍 GOOD: Pipeline mostly functional ($INTEGRATION_SCORE/$MAX_SCORE components)${NC}"
elif [ $PERCENTAGE -ge 50 ]; then
    echo -e "${YELLOW}⚠️  PARTIAL: Pipeline partially functional ($INTEGRATION_SCORE/$MAX_SCORE components)${NC}"
else
    echo -e "${RED}❌ POOR: Pipeline needs attention ($INTEGRATION_SCORE/$MAX_SCORE components)${NC}"
fi

echo -e "\n${BOLD}Next Steps:${NC}"
if [ $PERCENTAGE -ge 90 ]; then
    echo "• Start continuous monitoring: python3 /home/ifscr/SE_02_2025/IDS/realtime_ids_monitor.py"
    echo "• Run full demo: python3 /home/ifscr/SE_02_2025/IDS/realtime_dpdk_pipeline.py --mode demo"
    echo "• Scale up packet generation: increase --rate parameter"
elif [ $PERCENTAGE -ge 70 ]; then
    echo "• Check missing components and restart services"
    echo "• Verify Kafka topics: /home/ifscr/SE_02_2025/IDS/Suricata_Setup/setup_kafka.sh"
    echo "• Test with reduced load first"
else
    echo "• Review system setup: /home/ifscr/SE_02_2025/IDS/setup_realtime_dpdk.sh"
    echo "• Check service logs: journalctl -u suricata -f"
    echo "• Verify network interface configuration"
fi

echo -e "\n${CYAN}Pipeline validation completed!${NC}"
