#!/bin/bash

################################################################################
# DPDK Mode - IDS Pipeline Runner
################################################################################
# This script runs the complete IDS+ML pipeline using DPDK mode
# Requires DPDK-compatible NIC (Intel, Mellanox, etc.)
# Provides high-performance packet processing with kernel bypass
#
# Usage: sudo ./run_dpdk_mode.sh [option]
#
# Architecture:
#   Network Interface (DPDK PMD) → Suricata → Kafka → ML Consumer
#
# Requirements:
#   - DPDK-compatible network interface
#   - DPDK libraries installed
#   - Suricata compiled with DPDK support
#   - Hugepages configured
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
    echo -e "${BOLD}${BLUE}║         IDS Pipeline - DPDK Mode (High Performance)          ║${NC}"
    echo -e "${BOLD}${BLUE}║                                                               ║${NC}"
    echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${CYAN}⚡ Mode: DPDK (High-performance packet processing)${NC}"
    echo -e "${CYAN}🚀 Kernel bypass for maximum throughput${NC}"
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
    else
        # Check if Suricata has DPDK support
        if ! suricata --build-info | grep -q "DPDK support.*yes"; then
            echo -e "${RED}❌ Suricata not compiled with DPDK support${NC}"
            echo -e "${YELLOW}Rebuild Suricata with --enable-dpdk flag${NC}"
            exit 1
        fi
    fi
    
    # Check DPDK tools
    if ! command -v dpdk-devbind.py &> /dev/null && [ ! -f "/usr/local/bin/dpdk-devbind.py" ]; then
        missing_deps+=("dpdk-devbind.py")
    fi
    
    # Check Kafka
    if ! command -v kafka-server-start.sh &> /dev/null && [ ! -f "/usr/local/kafka/bin/kafka-server-start.sh" ]; then
        missing_deps+=("kafka")
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

check_hugepages() {
    echo -e "${BLUE}Checking hugepages...${NC}"
    
    local hugepages_free=$(cat /sys/kernel/mm/hugepages/hugepages-2048kB/free_hugepages 2>/dev/null || echo "0")
    local hugepages_total=$(cat /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages 2>/dev/null || echo "0")
    
    if [ "$hugepages_total" -lt 1024 ]; then
        echo -e "${YELLOW}⚠️  Insufficient hugepages configured (${hugepages_total}/1024)${NC}"
        echo -e "${YELLOW}Would you like to configure hugepages now? (y/n)${NC}"
        read -p "> " configure_hp
        
        if [[ $configure_hp =~ ^[Yy]$ ]]; then
            echo 1024 > /proc/sys/vm/nr_hugepages
            mkdir -p /mnt/huge
            mount -t hugetlbfs nodev /mnt/huge 2>/dev/null || true
            echo -e "${GREEN}✓ Hugepages configured${NC}"
        else
            echo -e "${RED}❌ Cannot proceed without hugepages${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ Hugepages configured: ${hugepages_total} (${hugepages_free} free)${NC}"
    fi
}

check_interface() {
    if [ -z "$NETWORK_INTERFACE" ]; then
        echo -e "${RED}❌ NETWORK_INTERFACE not configured${NC}"
        echo -e "${YELLOW}Edit $PIPELINE_CONFIG and set NETWORK_INTERFACE${NC}"
        exit 1
    fi
    
    # Check if interface exists
    if ! ip link show "$NETWORK_INTERFACE" > /dev/null 2>&1; then
        # Maybe it's already bound to DPDK, check by PCI address
        if [ -n "$INTERFACE_PCI_ADDRESS" ]; then
            DEVBIND=$(which dpdk-devbind.py 2>/dev/null || echo "/usr/local/bin/dpdk-devbind.py")
            if ! $DEVBIND --status | grep -q "$INTERFACE_PCI_ADDRESS"; then
                echo -e "${RED}❌ Network interface not found: $NETWORK_INTERFACE${NC}"
                echo -e "${YELLOW}Available interfaces:${NC}"
                ip link show | grep -E '^[0-9]+:' | awk '{print "  - " $2}' | sed 's/:$//'
                exit 1
            fi
        else
            echo -e "${RED}❌ Network interface not found: $NETWORK_INTERFACE${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✓ Network interface available: $NETWORK_INTERFACE${NC}"
}

check_dpdk_binding() {
    DEVBIND=$(which dpdk-devbind.py 2>/dev/null || echo "/usr/local/bin/dpdk-devbind.py")
    
    if [ -z "$INTERFACE_PCI_ADDRESS" ]; then
        # Try to auto-detect PCI address
        INTERFACE_PCI_ADDRESS=$(ethtool -i "$NETWORK_INTERFACE" 2>/dev/null | grep "bus-info" | awk '{print $2}')
        if [ -z "$INTERFACE_PCI_ADDRESS" ]; then
            echo -e "${YELLOW}⚠️  Could not auto-detect PCI address${NC}"
            echo -e "${YELLOW}Please set INTERFACE_PCI_ADDRESS in $PIPELINE_CONFIG${NC}"
            return 1
        fi
    fi
    
    # Check if already bound to DPDK
    if $DEVBIND --status | grep "$INTERFACE_PCI_ADDRESS" | grep -q "drv=$DPDK_DRIVER"; then
        echo -e "${GREEN}✓ Interface already bound to DPDK driver${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Interface not bound to DPDK driver${NC}"
        return 1
    fi
}

bind_interface() {
    echo -e "\n${BOLD}${CYAN}═══ Binding Interface to DPDK ═══${NC}\n"
    
    if check_dpdk_binding; then
        return 0
    fi
    
    echo -e "${BLUE}Binding $NETWORK_INTERFACE to DPDK...${NC}"
    bash "${PIPELINE_SCRIPTS}/01_bind_interface.sh"
    
    if check_dpdk_binding; then
        echo -e "${GREEN}✓ Interface bound successfully${NC}"
    else
        echo -e "${RED}❌ Failed to bind interface${NC}"
        exit 1
    fi
}

unbind_interface() {
    echo -e "\n${BOLD}${CYAN}═══ Unbinding Interface from DPDK ═══${NC}\n"
    
    echo -e "${BLUE}Unbinding $NETWORK_INTERFACE from DPDK...${NC}"
    bash "${PIPELINE_SCRIPTS}/unbind_interface.sh"
    
    echo -e "${GREEN}✓ Interface unbound${NC}"
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
    echo -e "\n${BOLD}${CYAN}═══ Starting Suricata (DPDK Mode) ═══${NC}"
    
    if pgrep suricata > /dev/null; then
        echo -e "${YELLOW}⚠️  Suricata already running${NC}"
        return 0
    fi
    
    # Ensure interface is bound
    if ! check_dpdk_binding; then
        echo -e "${YELLOW}Interface not bound to DPDK. Binding now...${NC}"
        bind_interface
    fi
    
    bash "${PIPELINE_SCRIPTS}/03_start_suricata.sh"
    sleep 3
    
    if pgrep suricata > /dev/null; then
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

    bash "${PIPELINE_SCRIPTS}/04_start_kafka_bridge.sh"
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
    
    bash "${PIPELINE_SCRIPTS}/05_start_ml_consumer.sh" &
    sleep 3
    
    if pgrep -f "ml_kafka_consumer.py" > /dev/null; then
        echo -e "${GREEN}✓ ML consumer started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start ML consumer${NC}"
        exit 1
    fi
}

start_two_model_ensemble() {
    echo -e "\n${BOLD}${CYAN}═══ Starting Two-Model Ensemble Consumer ═══${NC}"
    
    if pgrep -f "two_model_consumer.py" > /dev/null; then
        echo -e "${YELLOW}⚠️  Two-model ensemble already running${NC}"
        return 0
    fi
    
    bash "${PIPELINE_SCRIPTS}/06_start_two_model_consumer.sh"
}

show_status() {
    echo -e "\n${BOLD}${CYAN}═══ System Status ═══${NC}\n"
    
    # DPDK binding status
    echo -e "${CYAN}DPDK Interface Binding:${NC}"
    if check_dpdk_binding; then
        echo -e "${GREEN}✓ Interface bound to DPDK${NC}"
        echo -e "  ${CYAN}Interface:${NC} $NETWORK_INTERFACE"
        echo -e "  ${CYAN}PCI Address:${NC} $INTERFACE_PCI_ADDRESS"
        echo -e "  ${CYAN}Driver:${NC} $DPDK_DRIVER"
    else
        echo -e "${RED}✗ Interface not bound to DPDK${NC}"
    fi
    
    # Hugepages status
    local hugepages_free=$(cat /sys/kernel/mm/hugepages/hugepages-2048kB/free_hugepages 2>/dev/null || echo "0")
    local hugepages_total=$(cat /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages 2>/dev/null || echo "0")
    echo -e "\n${CYAN}Hugepages:${NC}"
    echo -e "  ${CYAN}Total:${NC} $hugepages_total"
    echo -e "  ${CYAN}Free:${NC} $hugepages_free"
    
    # Kafka status
    echo -e "\n${CYAN}Services:${NC}"
    if pgrep -f "kafka.Kafka" > /dev/null; then
        echo -e "${GREEN}✓ Kafka:${NC} Running"
    else
        echo -e "${RED}✗ Kafka:${NC} Not running"
    fi
    
    # Suricata status
    if pgrep suricata > /dev/null; then
        echo -e "${GREEN}✓ Suricata (DPDK):${NC} Running"
        SURICATA_PID=$(pgrep suricata)
        echo -e "  ${CYAN}PID:${NC} $SURICATA_PID"
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
    local ml_running=false
    if pgrep -f "ml_kafka_consumer.py" > /dev/null; then
        echo -e "${GREEN}✓ ML Consumer (Single Model):${NC} Running"
        ml_running=true
    fi
    
    if pgrep -f "two_model_consumer.py" > /dev/null; then
        echo -e "${GREEN}✓ ML Consumer (Two-Model Ensemble):${NC} Running"
        ml_running=true
    fi
    
    if [ "$ml_running" = false ]; then
        echo -e "${RED}✗ ML Consumer:${NC} Not running"
    fi
}

stop_all() {
    echo -e "\n${BOLD}${CYAN}═══ Stopping All Services ═══${NC}\n"
    
    # Stop ML consumers (both single and ensemble)
    if pgrep -f "ml_kafka_consumer.py" > /dev/null; then
        echo -e "${BLUE}Stopping single model ML consumer...${NC}"
        pkill -9 -f "ml_kafka_consumer.py"
        sleep 1
        if ! pgrep -f "ml_kafka_consumer.py" > /dev/null; then
            echo -e "${GREEN}✓ Single model consumer stopped${NC}"
        else
            echo -e "${RED}⚠ Failed to stop single model consumer${NC}"
        fi
    fi
    
    if pgrep -f "two_model_consumer.py" > /dev/null; then
        echo -e "${BLUE}Stopping two-model ensemble consumer...${NC}"
        pkill -9 -f "two_model_consumer.py"
        sleep 1
        if ! pgrep -f "two_model_consumer.py" > /dev/null; then
            echo -e "${GREEN}✓ Two-model ensemble stopped${NC}"
        else
            echo -e "${RED}⚠ Failed to stop ensemble consumer${NC}"
        fi
    fi
    
    # Stop Kafka bridge
    if pgrep -f "suricata_kafka_bridge.py" > /dev/null; then
        echo -e "${BLUE}Stopping Kafka bridge...${NC}"
        pkill -9 -f "suricata_kafka_bridge.py"
        sleep 1
        if ! pgrep -f "suricata_kafka_bridge.py" > /dev/null; then
            echo -e "${GREEN}✓ Kafka bridge stopped${NC}"
        else
            echo -e "${RED}⚠ Failed to stop Kafka bridge${NC}"
        fi
    fi
    
    # Stop Suricata
    if pgrep suricata > /dev/null; then
        echo -e "${BLUE}Stopping Suricata...${NC}"
        pkill suricata
        sleep 2
        if ! pgrep suricata > /dev/null; then
            echo -e "${GREEN}✓ Suricata stopped${NC}"
        else
            echo -e "${RED}⚠ Failed to stop Suricata${NC}"
        fi
    fi
    
    # Stop Kafka
    if pgrep -f "kafka.Kafka" > /dev/null; then
        echo -e "${BLUE}Stopping Kafka...${NC}"
        bash "${PIPELINE_SCRIPTS}/stop_all.sh"
        echo -e "${GREEN}✓ Kafka stopped${NC}"
    fi
    
    # Ask about unbinding interface
    if check_dpdk_binding; then
        echo
        read -p "Unbind interface from DPDK? (y/n): " unbind_choice
        if [[ $unbind_choice =~ ^[Yy]$ ]]; then
            unbind_interface
        fi
    fi
    
    echo -e "\n${GREEN}All services stopped${NC}"
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
            # Detect which consumer is running
            if pgrep -f "two_model_consumer.py" > /dev/null; then
                echo -e "${CYAN}Showing Two-Model Ensemble logs...${NC}"
                tail -f "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/logs/ml/two_model_ensemble.log" 2>/dev/null || echo -e "${RED}Log file not found${NC}"
            elif pgrep -f "ml_kafka_consumer.py" > /dev/null; then
                echo -e "${CYAN}Showing Single Model Consumer logs...${NC}"
                tail -f "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log" 2>/dev/null || echo -e "${RED}Log file not found${NC}"
            else
                # No consumer running, check which log file exists and is newer
                ENSEMBLE_LOG="${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/logs/ml/two_model_ensemble.log"
                SINGLE_LOG="${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log"
                
                if [ -f "$ENSEMBLE_LOG" ] && [ -f "$SINGLE_LOG" ]; then
                    # Show the most recently modified log
                    if [ "$ENSEMBLE_LOG" -nt "$SINGLE_LOG" ]; then
                        echo -e "${CYAN}Showing most recent log (Two-Model Ensemble)...${NC}"
                        tail -f "$ENSEMBLE_LOG"
                    else
                        echo -e "${CYAN}Showing most recent log (Single Model)...${NC}"
                        tail -f "$SINGLE_LOG"
                    fi
                elif [ -f "$ENSEMBLE_LOG" ]; then
                    echo -e "${CYAN}Showing Two-Model Ensemble logs...${NC}"
                    tail -f "$ENSEMBLE_LOG"
                elif [ -f "$SINGLE_LOG" ]; then
                    echo -e "${CYAN}Showing Single Model Consumer logs...${NC}"
                    tail -f "$SINGLE_LOG"
                else
                    echo -e "${RED}No ML consumer log files found${NC}"
                fi
            fi
            ;;
        3)
            tail -f "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/logs/kafka_bridge.log" 2>/dev/null || echo -e "${RED}Log file not found${NC}"
            ;;
        4)
            # Include both consumer logs in "all logs"
            tail -f /var/log/suricata/suricata.log \
                    "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log" \
                    "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/logs/ml/two_model_ensemble.log" \
                    "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/logs/kafka_bridge.log" 2>/dev/null || echo -e "${RED}Some log files not found${NC}"
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            ;;
    esac
}

monitor_metrics() {
    echo -e "\n${BOLD}${CYAN}═══ Metrics Monitor ═══${NC}\n"
    
    # Check if monitor script exists
    MONITOR_SCRIPT="${SCRIPT_DIR}/monitor_metrics.sh"
    if [ ! -f "$MONITOR_SCRIPT" ]; then
        echo -e "${RED}❌ Monitor script not found: $MONITOR_SCRIPT${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Select monitoring mode:${NC}"
    echo -e "  ${GREEN}1${NC}) Live Dashboard (TUI)"
    echo -e "  ${GREEN}2${NC}) System Status"
    echo -e "  ${GREEN}3${NC}) Tail Logs"
    echo -e "  ${GREEN}4${NC}) List Metric Files"
    echo
    read -p "Enter choice [1-4]: " monitor_choice
    
    case $monitor_choice in
        1)
            bash "$MONITOR_SCRIPT" --dashboard
            ;;
        2)
            bash "$MONITOR_SCRIPT" --status
            ;;
        3)
            bash "$MONITOR_SCRIPT" --tail
            ;;
        4)
            bash "$MONITOR_SCRIPT" --files
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            ;;
    esac
}

show_dpdk_info() {
    echo -e "\n${BOLD}${CYAN}═══ DPDK Information ═══${NC}\n"
    
    DEVBIND=$(which dpdk-devbind.py 2>/dev/null || echo "/usr/local/bin/dpdk-devbind.py")
    
    if [ -x "$DEVBIND" ]; then
        $DEVBIND --status
    else
        echo -e "${RED}dpdk-devbind.py not found${NC}"
    fi
}

show_menu() {
    echo -e "\n${BOLD}${MAGENTA}═══════════════════ MENU ═══════════════════${NC}"
    echo -e "  ${GREEN}1${NC}) ${BOLD}Start Complete Pipeline${NC} (Kafka + Suricata + ML)"
    echo -e "  ${GREEN}2${NC}) Start Kafka Only"
    echo -e "  ${GREEN}3${NC}) Start Suricata Only (DPDK)"
    echo -e "  ${GREEN}4${NC}) Start ML Consumer Only"
    echo -e "  ${GREEN}5${NC}) Start Kafka Bridge Only"
    echo -e "  ${GREEN}6${NC}) Bind Interface to DPDK"
    echo -e "  ${GREEN}7${NC}) Unbind Interface from DPDK"
    echo -e "  ${GREEN}8${NC}) Monitor Metrics 📊"
    echo -e "  ${GREEN}9${NC}) Start Two-Model Ensemble 🎯"
    echo -e "  ${GREEN}10${NC}) Check Status"
    echo -e "  ${GREEN}11${NC}) View Logs"
    echo -e "  ${GREEN}12${NC}) Show DPDK Info"
    echo -e "  ${GREEN}13${NC}) Stop All Services"
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
    check_hugepages
    check_interface
    
    # If argument provided, execute directly
    if [ $# -gt 0 ]; then
        case $1 in
            start|1)
                bind_interface
                start_kafka
                start_suricata
                start_kafka_bridge
                
                # Ask which ML consumer to use (if running interactively)
                if [ -t 0 ]; then
                    echo -e "\n${BOLD}${CYAN}═══ Select ML Consumer ═══${NC}"
                    echo -e "  ${GREEN}1${NC}) Single Model (faster, simpler)"
                    echo -e "  ${GREEN}2${NC}) Two-Model Ensemble (more accurate, meta-learner)"
                    echo
                    read -p "Enter choice [1-2]: " ml_choice
                    
                    case $ml_choice in
                        1)
                            start_ml_consumer
                            ;;
                        2)
                            start_two_model_ensemble
                            ;;
                        *)
                            echo -e "${YELLOW}Invalid choice, defaulting to single model${NC}"
                            start_ml_consumer
                            ;;
                    esac
                else
                    # Non-interactive, default to single model
                    start_ml_consumer
                fi
                
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
            bind|6)
                bind_interface
                ;;
            unbind|7)
                unbind_interface
                ;;
            metrics|8)
                monitor_metrics
                ;;
            ensemble|9)
                start_two_model_ensemble
                ;;
            status|10)
                show_status
                ;;
            logs|11)
                view_logs
                ;;
            info|12)
                show_dpdk_info
                ;;
            stop|13)
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
        read -p "Enter choice [0-13]: " choice
        
        case $choice in
            1)
                bind_interface
                start_kafka
                start_suricata
                start_kafka_bridge
                
                # Ask which ML consumer to use
                echo -e "\n${BOLD}${CYAN}═══ Select ML Consumer ═══${NC}"
                echo -e "  ${GREEN}1${NC}) Single Model (faster, simpler)"
                echo -e "  ${GREEN}2${NC}) Two-Model Ensemble (more accurate, meta-learner)"
                echo
                read -p "Enter choice [1-2]: " ml_choice
                
                case $ml_choice in
                    1)
                        start_ml_consumer
                        ;;
                    2)
                        start_two_model_ensemble
                        ;;
                    *)
                        echo -e "${YELLOW}Invalid choice, defaulting to single model${NC}"
                        start_ml_consumer
                        ;;
                esac
                
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
                bind_interface
                ;;
            7)
                unbind_interface
                ;;
            8)
                monitor_metrics
                ;;
            9)
                start_two_model_ensemble
                ;;
            10)
                show_status
                ;;
            11)
                view_logs
                ;;
            12)
                show_dpdk_info
                ;;
            13)
                stop_all
                ;;
            0)
                echo -e "\n${CYAN}Exiting...${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid choice. Please enter 0-13${NC}"
                ;;
        esac
        
        echo
        read -p "Press Enter to continue..."
    done
}

# Run main
main "$@"
