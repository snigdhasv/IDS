#!/bin/bash

# Complete Real-time DPDK-IDS System Status
# Shows current status of all integrated components

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

clear

echo -e "${BOLD}${BLUE}🔥 Real-time DPDK-IDS Pipeline Status${NC}"
echo -e "${CYAN}======================================${NC}"
echo

# System Information
echo -e "${BOLD}${YELLOW}📊 System Information${NC}"
echo "Date: $(date)"
echo "Uptime: $(uptime | cut -d',' -f1 | cut -d' ' -f4-)"
echo "Interface: enp2s0"
echo

# Service Status
echo -e "${BOLD}${YELLOW}🔧 Service Status${NC}"

# Check Suricata services
echo -n "Suricata (main): "
if systemctl is-active --quiet suricata; then
    echo -e "${GREEN}✓ Active${NC}"
else
    echo -e "${RED}❌ Inactive${NC}"
fi

echo -n "Suricata (simple): "
if systemctl is-active --quiet suricata-simple; then
    echo -e "${GREEN}✓ Active${NC}"
    SURICATA_PID=$(pgrep -f "suricata.*enp2s0" | head -1)
    if [ ! -z "$SURICATA_PID" ]; then
        echo "  Process: $SURICATA_PID (monitoring enp2s0)"
    fi
else
    echo -e "${RED}❌ Inactive${NC}"
fi

# Check Kafka
echo -n "Kafka: "
if pgrep -f kafka > /dev/null; then
    echo -e "${GREEN}✓ Running${NC}"
    KAFKA_PID=$(pgrep -f kafka | head -1)
    echo "  Process: $KAFKA_PID"
else
    echo -e "${RED}❌ Not running${NC}"
fi

# Check EVE-Kafka Bridge
echo -n "EVE-Kafka Bridge: "
if pgrep -f eve_kafka_bridge > /dev/null; then
    echo -e "${GREEN}✓ Running${NC}"
    BRIDGE_PID=$(pgrep -f eve_kafka_bridge)
    echo "  Process: $BRIDGE_PID"
else
    echo -e "${RED}❌ Not running${NC}"
fi

echo

# File Status
echo -e "${BOLD}${YELLOW}📁 File Status${NC}"

# Check log files
LOG_FILES=("/var/log/suricata/eve.json" "/tmp/suricata/eve.json")
for log_file in "${LOG_FILES[@]}"; do
    if [ -f "$log_file" ]; then
        SIZE=$(du -h "$log_file" | cut -f1)
        MTIME=$(stat -c %Y "$log_file")
        CURRENT=$(date +%s)
        AGE=$((CURRENT - MTIME))
        
        echo -n "$(basename $log_file): "
        if [ $AGE -lt 300 ]; then  # Less than 5 minutes old
            echo -e "${GREEN}✓ Active${NC} (${SIZE}, updated ${AGE}s ago)"
        else
            echo -e "${YELLOW}⚠️  Stale${NC} (${SIZE}, updated ${AGE}s ago)"
        fi
        
        # Show recent event count
        RECENT_EVENTS=$(tail -20 "$log_file" | wc -l)
        echo "  Recent events: $RECENT_EVENTS"
        break
    fi
done

echo

# DPDK Integration Status
echo -e "${BOLD}${YELLOW}🚀 DPDK Integration Status${NC}"

# Check Python dependencies
echo -n "Python Dependencies: "
if python3 -c "import scapy, kafka, psutil" 2>/dev/null; then
    echo -e "${GREEN}✓ Available${NC}"
else
    echo -e "${RED}❌ Missing${NC}"
fi

# Check hugepages
HUGEPAGES_TOTAL=$(cat /proc/meminfo | grep HugePages_Total | awk '{print $2}')
HUGEPAGES_FREE=$(cat /proc/meminfo | grep HugePages_Free | awk '{print $2}')
echo "Hugepages: $HUGEPAGES_FREE/$HUGEPAGES_TOTAL free"

# Check network interface
echo -n "Interface enp2s0: "
if ip link show enp2s0 | grep -q "state UP"; then
    echo -e "${GREEN}✓ UP${NC}"
else
    echo -e "${RED}❌ DOWN${NC}"
fi

echo

# Kafka Topics Status
echo -e "${BOLD}${YELLOW}📡 Kafka Topics Status${NC}"

KAFKA_CMD="/opt/kafka/bin/kafka-topics.sh"
if [ -f "$KAFKA_CMD" ]; then
    TOPICS=("suricata-events" "suricata-alerts" "suricata-stats")
    for topic in "${TOPICS[@]}"; do
        echo -n "$topic: "
        if $KAFKA_CMD --bootstrap-server localhost:9092 --list 2>/dev/null | grep -q $topic; then
            echo -e "${GREEN}✓ Exists${NC}"
        else
            echo -e "${RED}❌ Missing${NC}"
        fi
    done
else
    echo -e "${YELLOW}⚠️  Kafka CLI tools not found${NC}"
fi

echo

# Recent Activity
echo -e "${BOLD}${YELLOW}📈 Recent Activity${NC}"

# Show recent Suricata events
if [ -f "/var/log/suricata/eve.json" ]; then
    EVENTS_LAST_MINUTE=$(find /var/log/suricata/eve.json -mmin -1 2>/dev/null | wc -l)
    if [ "$EVENTS_LAST_MINUTE" -gt 0 ]; then
        echo -e "Suricata Events: ${GREEN}Active${NC} (log updated in last minute)"
        
        # Count event types in last 10 lines
        echo "Recent event types:"
        if command -v jq >/dev/null 2>&1; then
            tail -10 /var/log/suricata/eve.json 2>/dev/null | jq -r '.event_type' 2>/dev/null | sort | uniq -c | sed 's/^/  /'
        else
            tail -10 /var/log/suricata/eve.json 2>/dev/null | grep -o '"event_type":"[^"]*"' | sort | uniq -c | sed 's/^/  /'
        fi
    else
        echo -e "Suricata Events: ${YELLOW}⚠️  No recent activity${NC}"
    fi
else
    echo -e "Suricata Events: ${RED}❌ No log file${NC}"
fi

echo

# System Performance
echo -e "${BOLD}${YELLOW}💻 System Performance${NC}"

# CPU and Memory
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
MEM_USAGE=$(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')

echo "CPU Usage: $CPU_USAGE"
echo "Memory Usage: $MEM_USAGE"

# Network I/O for enp2s0
if [ -f "/sys/class/net/enp2s0/statistics/rx_bytes" ]; then
    RX_BYTES=$(cat /sys/class/net/enp2s0/statistics/rx_bytes)
    TX_BYTES=$(cat /sys/class/net/enp2s0/statistics/tx_bytes)
    RX_MB=$((RX_BYTES / 1024 / 1024))
    TX_MB=$((TX_BYTES / 1024 / 1024))
    echo "Network I/O (enp2s0): ↓${RX_MB}MB ↑${TX_MB}MB (total)"
fi

echo

# Available Commands
echo -e "${BOLD}${YELLOW}🎯 Available Commands${NC}"
echo "Generate packets:    sudo python3 /home/ifscr/SE_02_2025/IDS/realtime_dpdk_pipeline.py --mode generate --rate 100"
echo "Monitor events:      python3 /home/ifscr/SE_02_2025/IDS/realtime_ids_monitor.py"
echo "Run demo:            sudo python3 /home/ifscr/SE_02_2025/IDS/realtime_dpdk_pipeline.py --mode demo"
echo "Validate system:     sudo /home/ifscr/SE_02_2025/IDS/validate_complete_pipeline.sh"
echo "Quick validation:    sudo python3 /home/ifscr/SE_02_2025/IDS/realtime_dpdk_pipeline.py --mode validate"

echo

# System Health Score
echo -e "${BOLD}${CYAN}🏆 System Health Score${NC}"

SCORE=0
MAX_SCORE=8

# Check components
systemctl is-active --quiet suricata-simple && ((SCORE++))
pgrep -f kafka > /dev/null && ((SCORE++))
pgrep -f eve_kafka_bridge > /dev/null && ((SCORE++))
[ -f "/var/log/suricata/eve.json" ] && find /var/log/suricata/eve.json -mmin -5 > /dev/null 2>&1 && ((SCORE++))
python3 -c "import scapy, kafka, psutil" 2>/dev/null && ((SCORE++))
ip link show enp2s0 | grep -q "state UP" && ((SCORE++))
[ "$HUGEPAGES_TOTAL" -gt 0 ] && ((SCORE++))
[ -f "/opt/kafka/bin/kafka-topics.sh" ] && ((SCORE++))

PERCENTAGE=$((SCORE * 100 / MAX_SCORE))

if [ $PERCENTAGE -ge 90 ]; then
    echo -e "${GREEN}🎉 EXCELLENT ($SCORE/$MAX_SCORE) - System fully operational${NC}"
elif [ $PERCENTAGE -ge 70 ]; then
    echo -e "${YELLOW}👍 GOOD ($SCORE/$MAX_SCORE) - System mostly functional${NC}"
elif [ $PERCENTAGE -ge 50 ]; then
    echo -e "${YELLOW}⚠️  PARTIAL ($SCORE/$MAX_SCORE) - Some issues need attention${NC}"
else
    echo -e "${RED}❌ POOR ($SCORE/$MAX_SCORE) - System needs significant attention${NC}"
fi

echo
echo -e "${BOLD}Real-time DPDK-IDS Pipeline Status Complete${NC}"
