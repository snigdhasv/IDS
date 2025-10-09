#!/bin/bash

# Quick Start Script for AF_PACKET Mode (USB Adapter Compatible)
# This script runs the complete IDS+ML pipeline without DPDK

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║  IDS Pipeline - AF_PACKET Mode (USB Compatible)      ║${NC}"
echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo

echo -e "${YELLOW}📝 Note: This script uses AF_PACKET mode (not DPDK)${NC}"
echo -e "${YELLOW}   Works with ANY network interface including USB adapters!${NC}"
echo

# Menu
echo -e "${BOLD}Select an option:${NC}"
echo -e "  ${GREEN}1${NC}) Start Complete Pipeline (Kafka + Suricata + ML)"
echo -e "  ${GREEN}2${NC}) Start Kafka Only"
echo -e "  ${GREEN}3${NC}) Start Suricata Only (AF_PACKET mode)"
echo -e "  ${GREEN}4${NC}) Start ML Consumer Only"
echo -e "  ${GREEN}5${NC}) Replay Traffic (PCAP)"
echo -e "  ${GREEN}6${NC}) Check Status"
echo -e "  ${GREEN}7${NC}) Stop All"
echo -e "  ${GREEN}8${NC}) View Logs"
echo -e "  ${CYAN}9${NC}) Setup External Traffic Capture 🌐"
echo -e "  ${RED}0${NC}) Exit"
echo

read -p "Enter choice [0-9]: " choice

case $choice in
    1)
        echo -e "\n${BOLD}${BLUE}Starting Complete Pipeline...${NC}\n"
        
        echo -e "${CYAN}Step 1/4: Starting Kafka...${NC}"
        sudo "${SCRIPT_DIR}/02_setup_kafka.sh"
        sleep 2
        
        echo -e "\n${CYAN}Step 2/4: Starting Suricata (AF_PACKET mode)...${NC}"
        sudo "${SCRIPT_DIR}/03_start_suricata_afpacket.sh"
        sleep 2
        
        echo -e "\n${CYAN}Step 3/4: Starting Suricata→Kafka Bridge...${NC}"
        "${SCRIPT_DIR}/06_start_kafka_bridge.sh"
        sleep 2
        
        echo -e "\n${CYAN}Step 4/4: Starting ML Consumer...${NC}"
        "${SCRIPT_DIR}/04_start_ml_consumer.sh" &
        sleep 2
        
        echo -e "\n${GREEN}✓ Pipeline started successfully!${NC}"
        echo -e "Run ${CYAN}./quick_start.sh${NC} and select option 6 to check status"
        ;;
        
    2)
        echo -e "\n${BOLD}${BLUE}Starting Kafka...${NC}\n"
        sudo "${SCRIPT_DIR}/02_setup_kafka.sh"
        ;;
        
    3)
        echo -e "\n${BOLD}${BLUE}Starting Suricata (AF_PACKET mode)...${NC}\n"
        sudo "${SCRIPT_DIR}/03_start_suricata_afpacket.sh"
        ;;
        
    4)
        echo -e "\n${BOLD}${BLUE}Starting ML Consumer...${NC}\n"
        "${SCRIPT_DIR}/04_start_ml_consumer.sh"
        ;;
        
    5)
        echo -e "\n${BOLD}${BLUE}Replaying Traffic...${NC}\n"
        sudo "${SCRIPT_DIR}/05_replay_traffic.sh"
        ;;
        
    6)
        echo -e "\n${BOLD}${BLUE}System Status:${NC}\n"
        
        echo -e "${CYAN}═══ Kafka Status ═══${NC}"
        if pgrep -f "kafka.Kafka" > /dev/null; then
            echo -e "${GREEN}✓ Kafka is running${NC}"
        else
            echo -e "${RED}✗ Kafka is not running${NC}"
        fi
        
        echo -e "\n${CYAN}═══ Suricata Status ═══${NC}"
        if ps aux | grep -q "[s]uricata.*--af-packet"; then
            echo -e "${GREEN}✓ Suricata is running${NC}"
            ps aux | grep "[s]uricata.*--af-packet"
        else
            echo -e "${RED}✗ Suricata is not running${NC}"
        fi
        
        echo -e "\n${CYAN}═══ Suricata→Kafka Bridge Status ═══${NC}"
        if pgrep -f "suricata_kafka_bridge" > /dev/null; then
            echo -e "${GREEN}✓ Bridge is running${NC}"
            ps aux | grep "[s]uricata_kafka_bridge"
        else
            echo -e "${RED}✗ Bridge is not running${NC}"
        fi
        
        echo -e "\n${CYAN}═══ ML Consumer Status ═══${NC}"
        if pgrep -f "ml_kafka_consumer" > /dev/null; then
            echo -e "${GREEN}✓ ML Consumer is running${NC}"
            ps aux | grep "[m]l_kafka_consumer"
        else
            echo -e "${RED}✗ ML Consumer is not running${NC}"
        fi
        
        echo -e "\n${CYAN}═══ Network Interface Status ═══${NC}"
        ip link show enx00e04c36074c 2>/dev/null || echo -e "${RED}Interface not found${NC}"
        ;;
        
    7)
        echo -e "\n${BOLD}${BLUE}Stopping All Services...${NC}\n"
        sudo "${SCRIPT_DIR}/stop_all.sh"
        ;;
        
    8)
        echo -e "\n${BOLD}${BLUE}Log Files:${NC}\n"
        echo -e "${CYAN}Suricata Logs:${NC}"
        echo -e "  tail -f ../logs/suricata/eve.json | jq ."
        echo -e "  tail -f ../logs/suricata/fast.log"
        echo
        echo -e "${CYAN}ML Logs:${NC}"
        echo -e "  tail -f ../logs/ml/consumer.log"
        echo
        echo -e "Press any key to view live Suricata alerts..."
        read -n 1 -s
        tail -f ../logs/suricata/eve.json 2>/dev/null | jq . || echo "No logs yet"
        ;;
        
    9)
        echo -e "\n${BOLD}${BLUE}Setting up External Traffic Capture...${NC}\n"
        sudo "${SCRIPT_DIR}/00_setup_external_capture.sh"
        echo
        echo -e "${CYAN}Next Steps:${NC}"
        echo -e "1. Connect external device via Ethernet cable to USB adapter"
        echo -e "2. Configure external device: ${CYAN}IP 192.168.100.2/24${NC}"
        echo -e "3. Test: ${CYAN}ping 192.168.100.1${NC} from external device"
        echo -e "4. Start pipeline with option 1"
        echo -e "5. Replay traffic from external device"
        echo
        echo -e "See ${CYAN}EXTERNAL_TRAFFIC_GUIDE.md${NC} for detailed instructions"
        ;;
        
    0)
        echo -e "${GREEN}Goodbye!${NC}"
        exit 0
        ;;
        
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo
echo -e "${BOLD}${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  Operation Complete                                   ║${NC}"
echo -e "${BOLD}${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
