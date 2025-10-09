#!/bin/bash

################################################################################
# AF_PACKET Mode - IDS Pipeline Runner
################################################################################
# This script runs the complete IDS+ML pipeline using AF_PACKET mode
# Compatible with ANY network interface including USB adapters
# No DPDK required - uses standard Linux AF_PACKET sockets
#
# Usage: sudo ./run_afpacket_mode.sh [option]
#
# Architecture:
#   Network Interface (AF_PACKET) → Suricata → Kafka → ML Consumer
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/config/ids_config.yaml"
PIPELINE_SCRIPTS="${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/scripts"
PIPELINE_CONFIG="${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/config/pipeline.conf"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo -e "${BOLD}${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║                                                               ║${NC}"
    echo -e "${BOLD}${BLUE}║        IDS Pipeline - AF_PACKET Mode (USB Compatible)        ║${NC}"
    echo -e "${BOLD}${BLUE}║                                                               ║${NC}"
    echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${CYAN}📝 Mode: AF_PACKET (Works with any network interface)${NC}"
    echo -e "${CYAN}🔧 No DPDK required - Standard Linux packet capture${NC}"
    echo
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}❌ This script must be run as root (sudo)${NC}"
        exit 1
    fi
}

load_config() {
    if [ ! -f "$PIPELINE_CONFIG" ]; then
        echo -e "${RED}❌ Configuration file not found: $PIPELINE_CONFIG${NC}"
        exit 1
    fi
    source "$PIPELINE_CONFIG"
    echo -e "${GREEN}✓ Configuration loaded${NC}"
}

check_dependencies() {
    echo -e "${BLUE}Checking dependencies...${NC}"
    
    local missing_deps=()
    
    # Check Suricata
    if ! command -v suricata &> /dev/null; then
        missing_deps+=("suricata")
    fi
    
    # Check Kafka
    if ! command -v kafka-server-start.sh &> /dev/null && [ ! -f "/usr/local/kafka/bin/kafka-server-start.sh" ]; then
        missing_deps+=("kafka")
    fi
    
    # Check tcpreplay
    if ! command -v tcpreplay &> /dev/null; then
        missing_deps+=("tcpreplay")
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo -e "${RED}❌ Missing dependencies: ${missing_deps[*]}${NC}"
        echo -e "${YELLOW}Please install missing dependencies before continuing${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ All dependencies installed${NC}"
}

check_interface() {
    if [ -z "$NETWORK_INTERFACE" ]; then
        echo -e "${RED}❌ NETWORK_INTERFACE not configured${NC}"
        echo -e "${YELLOW}Edit $PIPELINE_CONFIG and set NETWORK_INTERFACE${NC}"
        exit 1
    fi
    
    if ! ip link show "$NETWORK_INTERFACE" > /dev/null 2>&1; then
        echo -e "${RED}❌ Network interface not found: $NETWORK_INTERFACE${NC}"
        echo
        echo -e "${YELLOW}Available interfaces:${NC}"
        ip link show | grep -E '^[0-9]+:' | awk '{print "  - " $2}' | sed 's/:$//'
        exit 1
    fi
    
    echo -e "${GREEN}✓ Network interface available: $NETWORK_INTERFACE${NC}"
}

start_kafka() {
    echo -e "\n${BOLD}${CYAN}═══ Starting Kafka ═══${NC}"
    
    if pgrep -f "kafka.Kafka" > /dev/null; then
        echo -e "${YELLOW}⚠️  Kafka already running${NC}"
        return 0
    fi
    
    bash "${PIPELINE_SCRIPTS}/02_setup_kafka.sh"
    sleep 3
    
    if pgrep -f "kafka.Kafka" > /dev/null; then
        echo -e "${GREEN}✓ Kafka started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start Kafka${NC}"
        exit 1
    fi
}

start_suricata() {
    echo -e "\n${BOLD}${CYAN}═══ Starting Suricata (AF_PACKET Mode) ═══${NC}"
    
    if pgrep -f "suricata.*--af-packet" > /dev/null; then
        echo -e "${YELLOW}⚠️  Suricata already running${NC}"
        return 0
    fi
    
    bash "${PIPELINE_SCRIPTS}/03_start_suricata_afpacket.sh"
    sleep 3
    
    if pgrep -f "suricata.*--af-packet" > /dev/null; then
        echo -e "${GREEN}✓ Suricata started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start Suricata${NC}"
        exit 1
    fi
}

start_kafka_bridge() {
    echo -e "\n${BOLD}${CYAN}═══ Starting Suricata → Kafka Bridge ═══${NC}"
    
    if pgrep -f "suricata_kafka_bridge.py" > /dev/null; then
        echo -e "${YELLOW}⚠️  Kafka bridge already running${NC}"
        return 0
    fi
    
    bash "${PIPELINE_SCRIPTS}/06_start_kafka_bridge.sh"
    sleep 2
    
    if pgrep -f "suricata_kafka_bridge.py" > /dev/null; then
        echo -e "${GREEN}✓ Kafka bridge started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start Kafka bridge${NC}"
        exit 1
    fi
}

start_ml_consumer() {
    echo -e "\n${BOLD}${CYAN}═══ Starting ML Consumer ═══${NC}"
    
    if pgrep -f "ml_kafka_consumer.py" > /dev/null; then
        echo -e "${YELLOW}⚠️  ML consumer already running${NC}"
        return 0
    fi
    
    bash "${PIPELINE_SCRIPTS}/04_start_ml_consumer.sh" &
    sleep 3
    
    if pgrep -f "ml_kafka_consumer.py" > /dev/null; then
        echo -e "${GREEN}✓ ML consumer started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start ML consumer${NC}"
        exit 1
    fi
}

show_status() {
    echo -e "\n${BOLD}${CYAN}═══ System Status ═══${NC}\n"
    
    # Kafka status
    if pgrep -f "kafka.Kafka" > /dev/null; then
        echo -e "${GREEN}✓ Kafka:${NC} Running"
    else
        echo -e "${RED}✗ Kafka:${NC} Not running"
    fi
    
    # Suricata status
    if pgrep -f "suricata.*--af-packet" > /dev/null; then
        echo -e "${GREEN}✓ Suricata (AF_PACKET):${NC} Running"
        SURICATA_PID=$(pgrep -f "suricata.*--af-packet")
        echo -e "  ${CYAN}PID:${NC} $SURICATA_PID"
        echo -e "  ${CYAN}Interface:${NC} $NETWORK_INTERFACE"
    else
        echo -e "${RED}✗ Suricata:${NC} Not running"
    fi
    
    # Kafka bridge status
    if pgrep -f "suricata_kafka_bridge.py" > /dev/null; then
        echo -e "${GREEN}✓ Kafka Bridge:${NC} Running"
    else
        echo -e "${RED}✗ Kafka Bridge:${NC} Not running"
    fi
    
    # ML consumer status
    if pgrep -f "ml_kafka_consumer.py" > /dev/null; then
        echo -e "${GREEN}✓ ML Consumer:${NC} Running"
    else
        echo -e "${RED}✗ ML Consumer:${NC} Not running"
    fi
    
    # Network interface status
    echo -e "\n${CYAN}Network Interface ($NETWORK_INTERFACE):${NC}"
    if ip link show "$NETWORK_INTERFACE" | grep -q "UP"; then
        echo -e "${GREEN}✓ Interface UP${NC}"
    else
        echo -e "${RED}✗ Interface DOWN${NC}"
    fi
    
    # Check promiscuous mode
    if ip link show "$NETWORK_INTERFACE" | grep -q "PROMISC"; then
        echo -e "${GREEN}✓ Promiscuous mode enabled${NC}"
    else
        echo -e "${YELLOW}⚠️  Promiscuous mode not enabled${NC}"
    fi
}

stop_all() {
    echo -e "\n${BOLD}${CYAN}═══ Stopping All Services ═══${NC}\n"
    
    # Stop ML consumer
    if pgrep -f "ml_kafka_consumer.py" > /dev/null; then
        echo -e "${BLUE}Stopping ML consumer...${NC}"
        pkill -f "ml_kafka_consumer.py" && echo -e "${GREEN}✓ ML consumer stopped${NC}"
    fi
    
    # Stop Kafka bridge
    if pgrep -f "suricata_kafka_bridge.py" > /dev/null; then
        echo -e "${BLUE}Stopping Kafka bridge...${NC}"
        pkill -f "suricata_kafka_bridge.py" && echo -e "${GREEN}✓ Kafka bridge stopped${NC}"
    fi
    
    # Stop Suricata
    if pgrep -f "suricata" > /dev/null; then
        echo -e "${BLUE}Stopping Suricata...${NC}"
        pkill -f "suricata" && echo -e "${GREEN}✓ Suricata stopped${NC}"
        sleep 2
    fi
    
    # Stop Kafka
    if pgrep -f "kafka.Kafka" > /dev/null; then
        echo -e "${BLUE}Stopping Kafka...${NC}"
        bash "${PIPELINE_SCRIPTS}/stop_all.sh"
        echo -e "${GREEN}✓ Kafka stopped${NC}"
    fi
    
    echo -e "\n${GREEN}All services stopped${NC}"
}

replay_traffic() {
    echo -e "\n${BOLD}${CYAN}═══ Traffic Replay ═══${NC}\n"
    bash "${PIPELINE_SCRIPTS}/05_replay_traffic.sh"
}

view_logs() {
    echo -e "\n${BOLD}${CYAN}═══ Log Viewer ═══${NC}\n"
    echo -e "${YELLOW}Select log to view:${NC}"
    echo -e "  ${GREEN}1${NC}) Suricata logs"
    echo -e "  ${GREEN}2${NC}) ML consumer logs"
    echo -e "  ${GREEN}3${NC}) Kafka bridge logs"
    echo -e "  ${GREEN}4${NC}) All logs (tail -f)"
    echo
    read -p "Enter choice [1-4]: " log_choice
    
    case $log_choice in
        1)
            tail -f /var/log/suricata/suricata.log 2>/dev/null || echo -e "${RED}Log file not found${NC}"
            ;;
        2)
            tail -f "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log" 2>/dev/null || echo -e "${RED}Log file not found${NC}"
            ;;
        3)
            tail -f "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/logs/kafka_bridge.log" 2>/dev/null || echo -e "${RED}Log file not found${NC}"
            ;;
        4)
            tail -f /var/log/suricata/suricata.log \
                    "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log" \
                    "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/logs/kafka_bridge.log" 2>/dev/null || echo -e "${RED}Some log files not found${NC}"
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            ;;
    esac
}

setup_external_capture() {
    echo -e "\n${BOLD}${CYAN}═══ External Traffic Capture Setup ═══${NC}\n"
    bash "${PIPELINE_SCRIPTS}/00_setup_external_capture.sh"
}

show_menu() {
    echo -e "\n${BOLD}${MAGENTA}═══════════════════ MENU ═══════════════════${NC}"
    echo -e "  ${GREEN}1${NC}) ${BOLD}Start Complete Pipeline${NC} (Kafka + Suricata + ML)"
    echo -e "  ${GREEN}2${NC}) Start Kafka Only"
    echo -e "  ${GREEN}3${NC}) Start Suricata Only (AF_PACKET)"
    echo -e "  ${GREEN}4${NC}) Start ML Consumer Only"
    echo -e "  ${GREEN}5${NC}) Start Kafka Bridge Only"
    echo -e "  ${GREEN}6${NC}) Replay Traffic (PCAP)"
    echo -e "  ${GREEN}7${NC}) Check Status"
    echo -e "  ${GREEN}8${NC}) View Logs"
    echo -e "  ${GREEN}9${NC}) Setup External Capture 🌐"
    echo -e "  ${GREEN}10${NC}) Stop All Services"
    echo -e "  ${RED}0${NC}) Exit"
    echo -e "${BOLD}${MAGENTA}═══════════════════════════════════════════${NC}\n"
}

################################################################################
# Main Logic
################################################################################

main() {
    print_header
    check_root
    load_config
    check_dependencies
    check_interface
    
    # If argument provided, execute directly
    if [ $# -gt 0 ]; then
        case $1 in
            start|1)
                start_kafka
                start_suricata
                start_kafka_bridge
                start_ml_consumer
                echo -e "\n${GREEN}${BOLD}✓ Complete pipeline started!${NC}"
                show_status
                ;;
            kafka|2)
                start_kafka
                ;;
            suricata|3)
                start_suricata
                ;;
            ml|4)
                start_ml_consumer
                ;;
            bridge|5)
                start_kafka_bridge
                ;;
            replay|6)
                replay_traffic
                ;;
            status|7)
                show_status
                ;;
            logs|8)
                view_logs
                ;;
            setup|9)
                setup_external_capture
                ;;
            stop|10)
                stop_all
                ;;
            *)
                echo -e "${RED}Invalid option${NC}"
                exit 1
                ;;
        esac
        exit 0
    fi
    
    # Interactive menu
    while true; do
        show_menu
        read -p "Enter choice [0-10]: " choice
        
        case $choice in
            1)
                start_kafka
                start_suricata
                start_kafka_bridge
                start_ml_consumer
                echo -e "\n${GREEN}${BOLD}✓ Complete pipeline started!${NC}"
                show_status
                ;;
            2)
                start_kafka
                ;;
            3)
                start_suricata
                ;;
            4)
                start_ml_consumer
                ;;
            5)
                start_kafka_bridge
                ;;
            6)
                replay_traffic
                ;;
            7)
                show_status
                ;;
            8)
                view_logs
                ;;
            9)
                setup_external_capture
                ;;
            10)
                stop_all
                ;;
            0)
                echo -e "\n${CYAN}Exiting...${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid choice. Please enter 0-10${NC}"
                ;;
        esac
        
        echo
        read -p "Press Enter to continue..."
    done
}

# Run main
main "$@"
