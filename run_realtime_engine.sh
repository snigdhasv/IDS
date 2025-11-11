#!/bin/bash

################################################################################
# Real-time Feature Engine Starter
################################################################################
# Starts the complete pipeline with accurate CICIDS feature extraction:
#   1. Suricata (alerts/signatures) 
#   2. Feature Engine (accurate CICIDS features via AF_PACKET fanout)
#   3. ML Consumer (high-confidence predictions)
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="${SCRIPT_DIR}/venv"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
    clear
    echo -e "${BOLD}${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║      Real-time CICIDS Feature Extraction Pipeline            ║"
    echo "║           With AF_PACKET Fanout Architecture                 ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then 
        echo -e "${RED}❌ Please run as root (sudo)${NC}"
        exit 1
    fi
}

start_all() {
    print_header
    
    echo -e "${CYAN}Starting Complete Pipeline...${NC}\n"
    
    # 1. Start Kafka
    echo -e "${BLUE}[1/5]${NC} Starting Kafka..."
    ./run_afpacket_mode.sh kafka > /dev/null 2>&1
    echo -e "${GREEN}✓ Kafka ready${NC}\n"
    sleep 3
    
    # 2. Start Suricata
    echo -e "${BLUE}[2/5]${NC} Starting Suricata (alerts/signatures)..."
    ./run_afpacket_mode.sh suricata > /dev/null 2>&1
    echo -e "${GREEN}✓ Suricata ready${NC}\n"
    sleep 2
    
    # 3. Start Kafka bridge (for Suricata alerts)
    echo -e "${BLUE}[3/5]${NC} Starting Suricata-Kafka bridge..."
    ./run_afpacket_mode.sh bridge > /dev/null 2>&1
    echo -e "${GREEN}✓ Bridge ready${NC}\n"
    sleep 2
    
    # 4. Start Feature Engine (accurate CICIDS features)
    echo -e "${BLUE}[4/5]${NC} Starting Real-time Feature Engine..."
    cd dpdk_suricata_ml_pipeline/src
    source "${VENV_PATH}/bin/activate"
    
    # Use 10-second timeout for faster attack detection in real-time
    python3 -u realtime_feature_engine.py --timeout 10 > ../../logs/feature_engine.log 2>&1 &
    FEATURE_PID=$!
    deactivate
    cd "${SCRIPT_DIR}"
    
    sleep 3
    if kill -0 $FEATURE_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Feature Engine started (PID: $FEATURE_PID)${NC}"
        echo "  Log: logs/feature_engine.log"
    else
        echo -e "${RED}❌ Feature Engine failed to start${NC}"
        exit 1
    fi
    echo
    
    # 5. Start ML Consumer (predictions) - ENSEMBLE MODE
    echo -e "${BLUE}[5/5]${NC} Starting Ensemble ML Consumer..."
    cd dpdk_suricata_ml_pipeline/src
    source "${VENV_PATH}/bin/activate"
    
    # Suppress sklearn warnings by filtering stderr
    PYTHONWARNINGS="ignore::UserWarning" python3 -u realtime_ensemble_consumer.py > ../../logs/ml_consumer.log 2>&1 &
    ML_PID=$!
    deactivate
    cd "${SCRIPT_DIR}"
    
    sleep 3
    if kill -0 $ML_PID 2>/dev/null; then
        echo -e "${GREEN}✓ ML Consumer started (PID: $ML_PID)${NC}"
        echo "  Log: logs/ml_consumer.log"
    else
        echo -e "${RED}❌ ML Consumer failed to start${NC}"
        exit 1
    fi
    echo
    
    # Show status
    echo -e "${BOLD}${GREEN}✓ Pipeline Started Successfully!${NC}\n"
    
    echo -e "${BOLD}Architecture:${NC}"
    echo -e "  ${CYAN}NIC (enp0s1)${NC}"
    echo -e "       │"
    echo -e "       ├─ AF_PACKET fanout (cluster_id=99)"
    echo -e "       │"
    echo -e "       ├─→ ${YELLOW}Suricata${NC} → Kafka → (alerts/signatures)"
    echo -e "       │"
    echo -e "       └─→ ${GREEN}Feature Engine${NC} → Kafka → ${BLUE}ML Consumer${NC} → (accurate predictions)"
    echo
    
    echo -e "${BOLD}Monitoring:${NC}"
    echo -e "  Feature Engine: tail -f logs/feature_engine.log"
    echo -e "  ML Consumer:    tail -f logs/ml_consumer.log"
    echo -e "  Suricata:       tail -f /var/log/suricata/suricata.log"
    echo
    
    echo -e "${BOLD}Stop:${NC}"
    echo -e "  sudo $0 stop"
    echo
}

stop_all() {
    echo -e "${YELLOW}Stopping all services...${NC}\n"
    
    # Stop ML Consumer (both single and ensemble) - force kill
    pkill -9 -f "realtime_ml_consumer.py\|realtime_ensemble_consumer.py" && echo -e "${GREEN}✓ ML Consumer stopped${NC}" || true
    
    # Stop Feature Engine - force kill
    pkill -9 -f "realtime_feature_engine.py" && echo -e "${GREEN}✓ Feature Engine stopped${NC}" || true
    
    # Stop Suricata pipeline (kill processes directly to avoid interactive menu)
    echo -e "${GREEN}✓ Stopping Suricata pipeline...${NC}"
    pkill -f "suricata_kafka_bridge" || true
    pkill -f "suricata.*-c /etc/suricata" || true
    
    # Stop Kafka
    docker stop kafka zookeeper 2>/dev/null || true
    
    echo -e "\n${GREEN}✓ All services stopped${NC}"
}

show_status() {
    echo -e "${BOLD}${CYAN}Pipeline Status:${NC}\n"
    
    # Check Kafka
    if pgrep -f "kafka.Kafka" > /dev/null; then
        echo -e "  ${GREEN}✓${NC} Kafka: Running"
    else
        echo -e "  ${RED}✗${NC} Kafka: Stopped"
    fi
    
    # Check Suricata
    if pgrep -f "suricata" > /dev/null; then
        echo -e "  ${GREEN}✓${NC} Suricata: Running"
    else
        echo -e "  ${RED}✗${NC} Suricata: Stopped"
    fi
    
    # Check Bridge
    if pgrep -f "suricata_kafka_bridge" > /dev/null; then
        echo -e "  ${GREEN}✓${NC} Kafka Bridge: Running"
    else
        echo -e "  ${RED}✗${NC} Kafka Bridge: Stopped"
    fi
    
    # Check Feature Engine
    if pgrep -f "realtime_feature_engine" > /dev/null; then
        echo -e "  ${GREEN}✓${NC} Feature Engine: Running"
    else
        echo -e "  ${RED}✗${NC} Feature Engine: Stopped"
    fi
    
    # Check ML Consumer
    if pgrep -f "realtime_ml_consumer" > /dev/null; then
        echo -e "  ${GREEN}✓${NC} ML Consumer: Running"
    else
        echo -e "  ${RED}✗${NC} ML Consumer: Stopped"
    fi
    
    echo
}

main() {
    check_root
    
    case "${1:-}" in
        start)
            start_all
            ;;
        stop)
            stop_all
            ;;
        status)
            show_status
            ;;
        restart)
            stop_all
            sleep 2
            start_all
            ;;
        *)
            print_header
            echo -e "${BOLD}Usage:${NC}"
            echo -e "  sudo $0 start   - Start complete pipeline"
            echo -e "  sudo $0 stop    - Stop all services"
            echo -e "  sudo $0 status  - Show service status"
            echo -e "  sudo $0 restart - Restart pipeline"
            echo
            exit 1
            ;;
    esac
}

main "$@"
