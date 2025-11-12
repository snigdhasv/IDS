#!/bin/bash

################################################################################
# End-to-End DPDK PCAP Replay + IDS Testing
################################################################################
# Complete workflow:
#   1. Start DPDK pipeline (Kafka, Suricata, Feature Engine, ML Consumer)
#   2. Replay PCAP traffic through X520 NIC
#   3. Capture IDS predictions to CSV
#   4. Calculate accuracy metrics
#
# Usage:
#   sudo bash test_dpdk_replay.sh [start|stop|status]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="${SCRIPT_DIR}/venv"
LOGS_DIR="${SCRIPT_DIR}/logs"
RESULTS_DIR="${SCRIPT_DIR}/test_results"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Test configuration
PCAP_DIR="${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/pcap_samples"
PCAP_FILES=("normal_traffic.pcap" "dos_traffic_sample.pcap" "mixed_traffic_sample.pcap")

check_root() {
    if [ "$EUID" -ne 0 ]; then 
        echo -e "${RED}[!] Please run as root (sudo)${NC}"
        exit 1
    fi
}

print_header() {
    clear
    echo -e "${MAGENTA}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║     End-to-End DPDK PCAP Replay + IDS Accuracy Testing       ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
}

init_env() {
    mkdir -p "$LOGS_DIR" "$RESULTS_DIR"
    
    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${YELLOW}[!] Python venv not found at $VENV_PATH${NC}"
        echo -e "    Creating venv..."
        python3 -m venv "$VENV_PATH"
        source "${VENV_PATH}/bin/activate"
        pip install -q scapy kafka-python numpy pandas scikit-learn
        deactivate
    fi
}

start_pipeline() {
    echo -e "${BLUE}[1/3] Starting DPDK Pipeline...${NC}\n"
    
    # Start with run_realtime_engine_dpdk.sh
    if [ -f "${SCRIPT_DIR}/run_realtime_engine_dpdk.sh" ]; then
        bash "${SCRIPT_DIR}/run_realtime_engine_dpdk.sh" start
    else
        echo -e "${YELLOW}[!] run_realtime_engine_dpdk.sh not found${NC}"
        exit 1
    fi
    
    # Wait for services to stabilize
    echo -e "\n${CYAN}[*] Waiting for services to stabilize...${NC}"
    sleep 5
}

run_pcap_replay() {
    echo -e "\n${BLUE}[2/3] Replaying PCAP Traffic...${NC}\n"
    
    source "${VENV_PATH}/bin/activate"
    
    test_num=0
    for pcap_file in "${PCAP_FILES[@]}"; do
        test_num=$((test_num + 1))
        pcap_path="${PCAP_DIR}/${pcap_file}"
        
        if [ ! -f "$pcap_path" ]; then
            echo -e "${YELLOW}[!] PCAP not found: $pcap_path${NC}"
            continue
        fi
        
        echo -e "${CYAN}[*] Test ${test_num}: Replaying $pcap_file${NC}"
        
        # Replay and capture ground truth
        csv_output="${RESULTS_DIR}/${pcap_file%.pcap}_packets.csv"
        
        python3 "${SCRIPT_DIR}/dpdk_pcap_replay.py" \
            "$pcap_path" \
            --repeat 1 \
            --csv "$csv_output" \
            --rate 100000  # 100k pkt/s
        
        # Wait for ML Consumer to process
        echo -e "${CYAN}    Waiting for predictions...${NC}"
        sleep 3
        
        echo -e "${GREEN}[+] Packets captured: $csv_output${NC}\n"
    done
    
    deactivate
}

collect_predictions() {
    echo -e "\n${BLUE}[3/3] Collecting ML Predictions...${NC}\n"
    
    # Copy prediction log
    if [ -f "${LOGS_DIR}/ml_consumer.log" ]; then
        cp "${LOGS_DIR}/ml_consumer.log" "${RESULTS_DIR}/ml_predictions.log"
        echo -e "${GREEN}[+] Predictions saved: ${RESULTS_DIR}/ml_predictions.log${NC}\n"
    fi
}

stop_pipeline() {
    echo -e "${YELLOW}[*] Stopping DPDK Pipeline...${NC}\n"
    
    if [ -f "${SCRIPT_DIR}/run_realtime_engine_dpdk.sh" ]; then
        bash "${SCRIPT_DIR}/run_realtime_engine_dpdk.sh" stop
    fi
    
    sleep 2
    echo -e "${GREEN}[+] Pipeline stopped${NC}\n"
}

show_results() {
    echo -e "${MAGENTA}╔═══════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║  Test Results Summary                         ║${NC}"
    echo -e "${MAGENTA}╚═══════════════════════════════════════════════╝${NC}\n"
    
    echo -e "${CYAN}Results Directory: ${RESULTS_DIR}${NC}\n"
    
    echo -e "${GREEN}Generated Files:${NC}"
    ls -lh "${RESULTS_DIR}"/ 2>/dev/null | tail -n +2 | awk '{print "  • " $9 " (" $5 ")"}'
    echo
    
    echo -e "${GREEN}Next Steps:${NC}"
    echo -e "  1. Compare ground truth (CSV) with predictions (log)"
    echo -e "  2. Calculate accuracy metrics"
    echo -e "  3. Analyze false positives/negatives"
    echo
    
    echo -e "${CYAN}Calculate accuracy:${NC}"
    echo -e "  python3 calculate_accuracy_metrics.py \\"
    echo -e "    --packets ${RESULTS_DIR}/*_packets.csv \\"
    echo -e "    --predictions ${RESULTS_DIR}/ml_predictions.log"
    echo
}

main() {
    check_root
    print_header
    init_env
    
    case "${1:-help}" in
        start)
            start_pipeline
            run_pcap_replay
            collect_predictions
            show_results
            ;;
        
        stop)
            stop_pipeline
            ;;
        
        status)
            bash "${SCRIPT_DIR}/run_realtime_engine_dpdk.sh" status
            ;;
        
        *)
            echo -e "${BOLD}Usage:${NC}"
            echo -e "  ${CYAN}sudo bash $0 start${NC}    - Start pipeline, replay PCAP, collect results"
            echo -e "  ${CYAN}sudo bash $0 stop${NC}     - Stop pipeline"
            echo -e "  ${CYAN}sudo bash $0 status${NC}   - Show service status"
            echo
            echo -e "${BOLD}What it does:${NC}"
            echo -e "  1. Starts Kafka, Suricata DPDK, Feature Engine, ML Consumer"
            echo -e "  2. Replays PCAP files through X520 NIC (simulates real traffic)"
            echo -e "  3. Captures ground truth packet data to CSV"
            echo -e "  4. Collects IDS predictions from ML Consumer"
            echo -e "  5. Saves results for accuracy analysis"
            echo
            exit 1
            ;;
    esac
}

main "$@"
