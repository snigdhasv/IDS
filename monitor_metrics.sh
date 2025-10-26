#!/bin/bash
#
# Monitor Metrics for Running IDS Pipeline
#
# Use this script to monitor metrics when your IDS pipeline is already running.
# This works with both DPDK and AF_PACKET modes.
#
# Usage:
#   ./monitor_metrics.sh              # Launch dashboard
#   ./monitor_metrics.sh --tail       # Tail metrics file
#   ./monitor_metrics.sh --files      # Show metrics files
#   ./monitor_metrics.sh --status     # Check if metrics are being generated
#

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
METRICS_DIR="${SCRIPT_DIR}/logs/metrics"
DASHBOARD="${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/scripts/metrics_dashboard.py"

print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              IDS Pipeline Metrics Monitor                      ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_pipeline_running() {
    local components_running=0
    local components_total=2
    
    echo -e "${CYAN}Checking pipeline status...${NC}"
    
    if pgrep -f "suricata_kafka_bridge" > /dev/null; then
        echo -e "${GREEN}✓ Kafka Bridge is running${NC}"
        ((components_running++))
    else
        echo -e "${YELLOW}⚠️  Kafka Bridge not running${NC}"
    fi
    
    # Check for either single model or ensemble consumer
    if pgrep -f "two_model_consumer" > /dev/null; then
        echo -e "${GREEN}✓ ML Consumer (Two-Model Ensemble) is running${NC}"
        ((components_running++))
    elif pgrep -f "ml_kafka_consumer" > /dev/null; then
        echo -e "${GREEN}✓ ML Consumer (Single Model) is running${NC}"
        ((components_running++))
    else
        echo -e "${YELLOW}⚠️  ML Consumer not running${NC}"
    fi
    
    if [ $components_running -eq 0 ]; then
        echo -e "\n${RED}❌ No pipeline components are running!${NC}"
        echo -e "${YELLOW}Metrics are only generated when the pipeline is running.${NC}"
        echo -e "${YELLOW}Start your pipeline first with: sudo ./run_afpacket_mode.sh${NC}"
        echo ""
        return 1
    elif [ $components_running -lt $components_total ]; then
        echo -e "\n${YELLOW}⚠️  Only $components_running/$components_total components running${NC}"
        echo -e "${YELLOW}For full metrics, ensure both Bridge and ML Consumer are running.${NC}"
        echo ""
    else
        echo -e "\n${GREEN}✓ All pipeline components running!${NC}"
        echo ""
    fi
    
    return 0
}

check_metrics_files() {
    if [ ! -d "$METRICS_DIR" ]; then
        echo -e "${RED}❌ Metrics directory not found: $METRICS_DIR${NC}"
        echo -e "${YELLOW}Metrics directory will be created when pipeline starts logging.${NC}"
        return 1
    fi
    
    local metrics_files=$(find "$METRICS_DIR" -name "metrics_*.jsonl" -type f 2>/dev/null | wc -l)
    
    if [ $metrics_files -eq 0 ]; then
        echo -e "${YELLOW}⚠️  No metrics files found yet${NC}"
        echo -e "${YELLOW}Metrics will appear once the pipeline processes events.${NC}"
        echo -e "${YELLOW}If pipeline is running, wait a few seconds and try again.${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ Found $metrics_files metrics file(s)${NC}"
    return 0
}

show_metrics_files() {
    echo -e "${CYAN}Metrics files:${NC}"
    if [ -d "$METRICS_DIR" ]; then
        ls -lh "$METRICS_DIR"/*.jsonl 2>/dev/null || echo -e "${YELLOW}No .jsonl files found${NC}"
        ls -lh "$METRICS_DIR"/*.csv 2>/dev/null || echo -e "${YELLOW}No .csv files found${NC}"
    else
        echo -e "${YELLOW}Metrics directory not found yet${NC}"
    fi
}

show_status() {
    print_header
    
    # Check pipeline
    check_pipeline_running
    
    # Check metrics files
    echo -e "${CYAN}Checking metrics files...${NC}"
    check_metrics_files
    
    if [ -d "$METRICS_DIR" ]; then
        echo ""
        show_metrics_files
        
        # Show latest metrics file stats
        local latest_file=$(ls -t "$METRICS_DIR"/metrics_*.jsonl 2>/dev/null | head -1)
        if [ -n "$latest_file" ]; then
            echo ""
            echo -e "${CYAN}Latest metrics file:${NC} $(basename "$latest_file")"
            echo -e "${CYAN}File size:${NC} $(du -h "$latest_file" | cut -f1)"
            echo -e "${CYAN}Line count:${NC} $(wc -l < "$latest_file") metrics"
            echo -e "${CYAN}Last modified:${NC} $(stat -c %y "$latest_file" | cut -d'.' -f1)"
        fi
    fi
    
    echo ""
}

tail_metrics() {
    print_header
    
    if ! check_pipeline_running; then
        exit 1
    fi
    
    if ! check_metrics_files; then
        echo -e "\n${YELLOW}Waiting for metrics to be generated...${NC}"
        echo -e "${YELLOW}(Press Ctrl+C to exit)${NC}\n"
    fi
    
    # Create metrics dir if it doesn't exist
    mkdir -p "$METRICS_DIR"
    
    # Get today's metrics file
    local today=$(date +%Y%m%d)
    local metrics_file="${METRICS_DIR}/metrics_${today}.jsonl"
    
    if [ -f "$metrics_file" ]; then
        echo -e "${CYAN}Tailing: $(basename "$metrics_file")${NC}"
        echo -e "${YELLOW}(Press Ctrl+C to exit)${NC}\n"
        
        # Check if jq is available
        if command -v jq &> /dev/null; then
            tail -f "$metrics_file" | jq '.'
        else
            echo -e "${YELLOW}Note: Install 'jq' for pretty-printed JSON${NC}\n"
            tail -f "$metrics_file"
        fi
    else
        echo -e "${YELLOW}Metrics file not found: $(basename "$metrics_file")${NC}"
        echo -e "${YELLOW}Waiting for metrics to be generated...${NC}\n"
        
        # Wait for file to be created
        until [ -f "$metrics_file" ]; do
            sleep 2
        done
        
        echo -e "${GREEN}Metrics file created! Starting tail...${NC}\n"
        if command -v jq &> /dev/null; then
            tail -f "$metrics_file" | jq '.'
        else
            tail -f "$metrics_file"
        fi
    fi
}

launch_dashboard() {
    print_header
    
    if ! check_pipeline_running; then
        echo ""
        read -p "Pipeline not fully running. Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    if [ ! -f "$DASHBOARD" ]; then
        echo -e "${RED}❌ Dashboard script not found: $DASHBOARD${NC}"
        exit 1
    fi
    
    if ! check_metrics_files; then
        echo -e "\n${YELLOW}No metrics files found yet.${NC}"
        echo -e "${YELLOW}Dashboard will show data once metrics are generated.${NC}"
        echo ""
        read -p "Launch dashboard anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    echo -e "${GREEN}Launching metrics dashboard...${NC}"
    echo -e "${YELLOW}(Press Ctrl+C to exit dashboard)${NC}\n"
    sleep 1
    
    # Launch dashboard
    "$DASHBOARD"
}

show_help() {
    cat << EOF
${BLUE}╔════════════════════════════════════════════════════════════════╗
║              IDS Pipeline Metrics Monitor                      ║
╚════════════════════════════════════════════════════════════════╝${NC}

Monitor metrics for your running IDS pipeline (DPDK or AF_PACKET mode).

${CYAN}USAGE:${NC}
    ./monitor_metrics.sh [OPTION]

${CYAN}OPTIONS:${NC}
    ${GREEN}(no option)${NC}     Launch interactive metrics dashboard (default)
    ${GREEN}--dashboard${NC}     Launch interactive metrics dashboard
    ${GREEN}--tail${NC}          Tail metrics file in real-time (raw JSON)
    ${GREEN}--status${NC}        Check pipeline status and show metrics files
    ${GREEN}--files${NC}         List all metrics files
    ${GREEN}--help${NC}          Show this help message

${CYAN}EXAMPLES:${NC}
    # Launch dashboard (most common)
    ./monitor_metrics.sh

    # Check if metrics are being generated
    ./monitor_metrics.sh --status

    # View raw metrics in real-time
    ./monitor_metrics.sh --tail

    # List all metrics files
    ./monitor_metrics.sh --files

${CYAN}PREREQUISITES:${NC}
    Your IDS pipeline must be running first!
    
    ${YELLOW}Terminal 1:${NC} sudo ./run_afpacket_mode.sh
    ${YELLOW}Terminal 2:${NC} ./monitor_metrics.sh

${CYAN}WHAT YOU'LL SEE:${NC}
    📊 Latency metrics (P50/P95/P99)
    🚀 Throughput (events/sec)
    🤖 ML inference performance
    ⚠️  Errors and warnings
    💻 System resource usage

${CYAN}METRICS LOCATION:${NC}
    logs/metrics/metrics_YYYYMMDD.jsonl
    logs/metrics/metrics_YYYYMMDD.csv

EOF
}

################################################################################
# Main
################################################################################

main() {
    case "${1:-}" in
        --dashboard)
            launch_dashboard
            ;;
        --tail)
            tail_metrics
            ;;
        --status)
            show_status
            ;;
        --files)
            show_metrics_files
            ;;
        --help|-h)
            show_help
            ;;
        "")
            # Default: launch dashboard
            launch_dashboard
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo -e "Use --help for usage information"
            exit 1
            ;;
    esac
}

main "$@"
