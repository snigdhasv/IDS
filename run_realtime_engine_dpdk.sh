#!/bin/bash

################################################################################
# Real-time Feature Engine Starter - DPDK Mode
################################################################################
# Starts the complete high-performance pipeline with accurate CICIDS feature
# extraction using DPDK (Data Plane Development Kit):
#   1. Kafka (message broker)
#   2. Suricata in DPDK mode (high-speed alerts/signatures via PMD)
#   3. Feature Engine (accurate CICIDS features via DPDK packet capture)
#   4. ML Consumer (Ensemble predictions with high confidence)
#
# REQUIREMENTS:
#   - Network interface bound to DPDK (run 01_bind_interface.sh first)
#   - Suricata compiled with DPDK support
#   - Python venv with required ML libraries
#   - Root/sudo access
#
# ARCHITECTURE:
#   NIC (PCI bound to DPDK)
#       │
#       ├─→ Suricata DPDK PMD → Kafka → (alerts/signatures - 1-10 Gbps)
#       │
#       └─→ Feature Engine DPDK → Kafka → ML Consumer → (accurate predictions)
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/config/pipeline.conf"
VENV_PATH="${SCRIPT_DIR}/venv"
PIPELINE_USER="${SUDO_USER:-$(whoami)}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# Counters for status tracking
STARTED_SERVICES=0
FAILED_SERVICES=0
ML_MODE="single"

get_kafka_host_port() {
    # Use first bootstrap server entry
    local bootstrap=${KAFKA_BOOTSTRAP_SERVERS%%,*}
    local host=${bootstrap%%:*}
    local port=${bootstrap##*:}

    if [ "$host" = "$bootstrap" ]; then
        port="9092"
    fi
    printf "%s %s" "$host" "$port"
}

wait_for_tcp_port() {
    local host=$1
    local port=$2
    local retries=${3:-20}
    local interval=${4:-1}
    local attempt=1

    while [ $attempt -le $retries ]; do
        if bash -c "cat < /dev/null > /dev/tcp/$host/$port" >/dev/null 2>&1; then
            return 0
        fi
        sleep "$interval"
        attempt=$((attempt + 1))
    done
    return 1
}

print_header() {
    clear
    echo -e "${BOLD}${MAGENTA}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║   Real-time CICIDS Feature Extraction Pipeline (DPDK)         ║"
    echo "║         High-Performance Packet Capture & ML Pipeline         ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
}

print_usage() {
    print_header
    echo -e "${BOLD}Real-time CICIDS Feature Extraction Pipeline (DPDK Mode)${NC}\n"
    echo -e "${BOLD}Usage:${NC}"
    echo -e "  ${CYAN}sudo $0 start [--single|--ensemble]${NC}  - Start pipeline (default: single model)"
    echo -e "  ${CYAN}sudo $0 stop${NC}                        - Stop all services"
    echo -e "  ${CYAN}sudo $0 status${NC}                      - Show service status"
    echo -e "  ${CYAN}sudo $0 restart${NC}                     - Restart pipeline"
    echo -e "  ${CYAN}sudo $0 test${NC}                        - Test mode (Feature Engine only, foreground)"
    echo -e "  ${CYAN}sudo $0 logs${NC}                        - View live logs"
    echo
}

get_ml_mode_label() {
    if [ "$ML_MODE" = "ensemble" ]; then
        echo "Ensemble (5-model voting)"
    else
        echo "Single model (RandomForest PCA)"
    fi
}

parse_start_flags() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --ensemble)
                ML_MODE="ensemble"
                ;;
            --single)
                ML_MODE="single"
                ;;
            --help|-h)
                print_usage
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Unknown start option: $1${NC}"
                exit 1
                ;;
        esac
        shift
    done
}

check_root() {
    if [ "$EUID" -ne 0 ]; then 
        echo -e "${RED}❌ Please run as root (sudo)${NC}"
        exit 1
    fi
}

load_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}❌ Config file not found: $CONFIG_FILE${NC}"
        exit 1
    fi
    source "$CONFIG_FILE"
    : "${KAFKA_TOPIC_ML_FEATURES:=ml-features}"
    echo -e "${GREEN}✓ Config loaded: $CONFIG_FILE${NC}"
}

verify_dpdk_prerequisites() {
    echo -e "${CYAN}Verifying DPDK prerequisites...${NC}\n"
    
    if ! command -v suricata &> /dev/null; then
        echo -e "${RED}❌ Suricata not installed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Suricata found${NC}"
    
    if ! suricata --build-info | grep -q "DPDK support.*yes"; then
        echo -e "${RED}❌ Suricata not compiled with DPDK support${NC}"
        echo "   Run: suricata --build-info | grep DPDK"
        exit 1
    fi
    echo -e "${GREEN}✓ Suricata compiled with DPDK support${NC}"
    
    DEVBIND=$(which dpdk-devbind.py 2>/dev/null || echo "")
    if [ -z "$DEVBIND" ]; then
        DEVBIND="/usr/local/bin/dpdk-devbind.py"
        if [ ! -f "$DEVBIND" ]; then
            echo -e "${RED}❌ dpdk-devbind.py not found${NC}"
            exit 1
        fi
    fi
    echo -e "${GREEN}✓ dpdk-devbind found: $DEVBIND${NC}"
    
    if ! "$DEVBIND" --status 2>/dev/null | grep -q "drv="; then
        echo -e "${RED}❌ No interfaces bound to DPDK${NC}"
        echo "   Run: sudo ./dpdk_suricata_ml_pipeline/scripts/01_bind_interface.sh"
        exit 1
    fi
    echo -e "${GREEN}✓ DPDK interfaces bound${NC}"
    
    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${RED}❌ Python venv not found: $VENV_PATH${NC}"
        echo "   Run: python3 -m venv venv"
        exit 1
    fi
    echo -e "${GREEN}✓ Python venv found${NC}\n"
}

stop_afpacket_suricata_instances() {
    local suricata_pids
    mapfile -t suricata_pids < <(pgrep -f "suricata" 2>/dev/null || true)
    local stopped=0
    for pid in "${suricata_pids[@]}"; do
        [ -z "$pid" ] && continue
        if [ ! -r "/proc/$pid/cmdline" ]; then
            continue
        fi
        local cmdline
        cmdline=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)
        if [[ "$cmdline" == *"--dpdk"* ]]; then
            continue
        fi
        echo -e "${YELLOW}⏹️  Stopping legacy AF_PACKET Suricata (PID: $pid)...${NC}"
        kill "$pid" >/dev/null 2>&1 || true
        sleep 0.2
        kill -0 "$pid" >/dev/null 2>&1 && kill -9 "$pid" >/dev/null 2>&1 || true
        stopped=1
    done

    if [ $stopped -gt 0 ]; then
        echo -e "${GREEN}✓ Legacy AF_PACKET Suricata instances cleared${NC}"
        local bind_script="$SCRIPT_DIR/dpdk_suricata_ml_pipeline/scripts/01_bind_interface.sh"
        if [ -x "$bind_script" ]; then
            echo -e "${CYAN}Rebinding interface to the DPDK driver...${NC}"
            bash "$bind_script" >/dev/null 2>&1 || true
        fi
        sleep 1
    fi
}

print_process_details() {
    local title="$1"
    local pattern="$2"
    local lines
    lines=$(pgrep -af "$pattern" 2>/dev/null || true)
    if [ -z "$lines" ]; then
        echo -e "  ${YELLOW}○${NC} $title: not running"
        return
    fi
    echo -e "  ${GREEN}✓${NC} $title:"
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        local pid=${line%% *}
        local cmd=${line#* }
        [ -z "$pid" ] && continue
        echo "    PID: $pid"
        echo "    Cmd: $cmd"
        if [[ "$cmd" == *"--dpdk"* ]]; then
            echo "    Mode: DPDK"
        elif [[ "$cmd" == *"--af-packet"* ]]; then
            echo "    Mode: AF_PACKET (legacy)"
        fi
        echo ""
    done <<< "$lines"
}

locate_kafka_console_consumer() {
    local -a candidates=()
    if [ -n "${KAFKA_HOME:-}" ]; then
        candidates+=("$KAFKA_HOME/bin/kafka-console-consumer.sh")
    fi
    candidates+=("$(command -v kafka-console-consumer.sh 2>/dev/null || true)")
    candidates+=("/opt/kafka/bin/kafka-console-consumer.sh" "/usr/bin/kafka-console-consumer.sh" "/usr/local/kafka/bin/kafka-console-consumer.sh")
    for candidate in "${candidates[@]}"; do
        [ -n "$candidate" ] || continue
        if [ -x "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

show_feature_topic_sample() {
    local consumer
    local topic="${KAFKA_TOPIC_ML_FEATURES:-ml-features}"
    consumer=$(locate_kafka_console_consumer)
    echo -e "${BLUE}Sampling Kafka topic '$topic' (ml-features)...${NC}"
    if [ -z "$consumer" ]; then
        echo -e "  ${YELLOW}Kafka console consumer not found; install Kafka or set KAFKA_HOME.${NC}"
        echo ""
        return
    fi
    echo "  Using: $consumer"
    if ! "$consumer" --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
        --topic "$topic" --from-beginning --max-messages 1 --timeout-ms 5000; then
        echo -e "  ${YELLOW}Unable to read from the topic (Kafka may be offline or the topic is empty).${NC}"
    fi
    echo ""
}

display_runtime_proof() {
    echo -e "${BOLD}${CYAN}DPDK Runtime Proof (Processes + Kafka sample)${NC}\n"
    print_process_details "Suricata" "suricata"
    print_process_details "Feature Engine" "dpdk_feature_engine"
    print_process_details "ML Consumers" "realtime_ensemble_consumer|realtime_ml_consumer"
    print_process_details "Suricata ML Consumer" "ml_kafka_consumer.py"
    show_feature_topic_sample
}

start_kafka() {
    echo -e "${BLUE}[1/5]${NC} Starting Kafka..."
    
    # Check if Kafka already running
    if netstat -tuln 2>/dev/null | grep -q ":9092"; then
        echo -e "${YELLOW}⚠️  Kafka already running on port 9092${NC}"
        return 0
    fi
    
    # Try to start with script if available
    if [ -f "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/scripts/02_setup_kafka.sh" ]; then
        bash "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/scripts/02_setup_kafka.sh" > /dev/null 2>&1 || true
    fi
    
    sleep 2
    
    if netstat -tuln 2>/dev/null | grep -q ":9092"; then
        echo -e "${GREEN}✓ Kafka ready on port 9092${NC}\n"
        ((STARTED_SERVICES++))
        return 0
    else
        echo -e "${YELLOW}⚠️  Could not verify Kafka startup (may still be starting)${NC}\n"
        return 0
    fi
}

start_suricata_dpdk() {
    echo -e "${BLUE}[2/5]${NC} Starting Suricata in DPDK mode..."
    
    # Check if already running
    if pgrep -f "suricata" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Suricata already running${NC}"
        return 0
    fi
    
    # Run the DPDK Suricata start script
    if bash "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/scripts/03_start_suricata_dpdk.sh" > /dev/null 2>&1; then
        sleep 3
        if pgrep -f "suricata" > /dev/null 2>&1; then
            SURICATA_PID=$(pgrep -f "suricata" | head -n1)
            echo -e "${GREEN}✓ Suricata started (PID: $SURICATA_PID)${NC}\n"
            ((STARTED_SERVICES++))
            return 0
        fi
    fi
    
    echo -e "${RED}❌ Failed to start Suricata${NC}"
    echo "   Check: /var/log/suricata/suricata.log"
    ((FAILED_SERVICES++))
    return 1
}

start_feature_engine_dpdk() {
    echo -e "${BLUE}[3/5]${NC} Starting Real-time Feature Engine (DPDK mode)..."
    
    # Create logs directory if it doesn't exist
    mkdir -p "$SCRIPT_DIR/logs"
    
    # Check if already running
    if pgrep -f "dpdk_feature_engine" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Feature Engine already running${NC}"
        FEATURE_PID=$(pgrep -f "dpdk_feature_engine" | head -n1)
        echo "  PID: $FEATURE_PID"
        echo "  Log: logs/feature_engine.log"
        return 0
    fi
    
    # Check if source file exists
    if [ ! -f "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src/dpdk_feature_engine.py" ]; then
        echo -e "${RED}❌ dpdk_feature_engine.py not found${NC}"
        echo "  Expected: $SCRIPT_DIR/dpdk_suricata_ml_pipeline/src/dpdk_feature_engine.py"
        ((FAILED_SERVICES++))
        return 1
    fi
    
    cd "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src"
    source "${VENV_PATH}/bin/activate"
    
    # Clear old log
    > "$SCRIPT_DIR/logs/feature_engine.log"
    
    # Show what we're doing
    echo "  Starting: python3 -u dpdk_feature_engine.py"
    echo "  Log: logs/feature_engine.log"
    echo "  Waiting 5 seconds for startup..."
    
    # Use DPDK-based feature extraction (direct DPDK packet capture)
    python3 -u dpdk_feature_engine.py \
        > "$SCRIPT_DIR/logs/feature_engine.log" 2>&1 &
    FEATURE_PID=$!
    
    # Wait and check multiple times
    sleep 2
    if kill -0 $FEATURE_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Feature Engine process started (PID: $FEATURE_PID)${NC}"
    else
        echo -e "${RED}❌ Feature Engine died immediately${NC}"
        echo "  Last 20 lines of log:"
        tail -20 "$SCRIPT_DIR/logs/feature_engine.log" | sed 's/^/    /'
        deactivate
        cd "$SCRIPT_DIR"
        ((FAILED_SERVICES++))
        return 1
    fi
    
    sleep 3
    if kill -0 $FEATURE_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Feature Engine running stable (PID: $FEATURE_PID)${NC}"
        echo "  Mode: DPDK direct packet capture"
        echo "  Output: Kafka topic '${KAFKA_TOPIC_ML_FEATURES:-ml-features}'"
        echo ""
        
        # Show first few log lines
        echo "  Initial log output:"
        head -10 "$SCRIPT_DIR/logs/feature_engine.log" 2>/dev/null | sed 's/^/    /' || true
        echo ""
        
        deactivate
        cd "$SCRIPT_DIR"
        ((STARTED_SERVICES++))
        return 0
    else
        echo -e "${RED}❌ Feature Engine crashed after startup${NC}"
        echo "  Full log:"
        cat "$SCRIPT_DIR/logs/feature_engine.log" | sed 's/^/    /'
        deactivate
        cd "$SCRIPT_DIR"
        ((FAILED_SERVICES++))
        return 1
    fi
}

start_ml_consumer() {
        local mode_label
        mode_label="$(get_ml_mode_label)"
        echo -e "${BLUE}[4/5]${NC} Starting ML Consumer (${mode_label})..."
    
    mkdir -p "$SCRIPT_DIR/logs"

    local metrics_dir="$SCRIPT_DIR/dpdk_suricata_ml_pipeline/logs/metrics"
    mkdir -p "$metrics_dir"
    chown -R "$PIPELINE_USER:$PIPELINE_USER" "$metrics_dir" >/dev/null 2>&1 || true
    chmod 775 "$metrics_dir" >/dev/null 2>&1 || true

        read -r kafka_host kafka_port <<< "$(get_kafka_host_port)"
        if ! wait_for_tcp_port "$kafka_host" "$kafka_port" 60 1; then
            echo -e "${RED}❌ Kafka did not become available on ${kafka_host}:${kafka_port}${NC}"
            ((FAILED_SERVICES++))
            return 1
        fi

        local consumer_pattern consumer_script consumer_path
        if [ "$ML_MODE" = "ensemble" ]; then
            consumer_pattern="realtime_ensemble_consumer"
            if [ -f "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src/realtime_ensemble_consumer_with_csv.py" ]; then
                consumer_script="realtime_ensemble_consumer_with_csv.py"
            elif [ -f "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src/realtime_ensemble_consumer.py" ]; then
                consumer_script="realtime_ensemble_consumer.py"
            else
                echo -e "${RED}❌ Ensemble consumer script not found${NC}"
                ((FAILED_SERVICES++))
                return 1
            fi
        else
            consumer_pattern="realtime_ml_consumer"
            consumer_script="realtime_ml_consumer.py"
            if [ ! -f "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src/$consumer_script" ]; then
                echo -e "${RED}❌ Single-model consumer script not found${NC}"
                ((FAILED_SERVICES++))
                return 1
            fi
        fi
        consumer_path="$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src/$consumer_script"

        if pgrep -f "$consumer_pattern" > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  ML Consumer already running (${mode_label})${NC}"
            ML_PID=$(pgrep -f "$consumer_pattern" | head -n1)
            echo "  PID: $ML_PID"
            echo "  Log: logs/ml_consumer.log"
            return 0
        fi

        cd "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src"
        source "${VENV_PATH}/bin/activate"

        > "$SCRIPT_DIR/logs/ml_consumer.log"

        echo "  Starting: python3 -u $consumer_script"
        echo "  Mode: $mode_label"
        echo "  Log: logs/ml_consumer.log"
        echo "  Waiting 5 seconds for startup..."

        PYTHONWARNINGS="ignore::UserWarning" python3 -u "$consumer_script" \
            > "$SCRIPT_DIR/logs/ml_consumer.log" 2>&1 &
        ML_PID=$!

        sleep 2
    echo -e "${BLUE}[3/5]${NC} Starting Real-time Feature Engine (DPDK mode)..."
    
    # Create logs directory if it doesn't exist
    mkdir -p "$SCRIPT_DIR/logs"
    
    # Check if already running
    if pgrep -f "dpdk_feature_engine" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Feature Engine already running${NC}"
        FEATURE_PID=$(pgrep -f "dpdk_feature_engine" | head -n1)
        echo "  PID: $FEATURE_PID"
        echo "  Log: logs/feature_engine.log"
        return 0
    fi
    
    # Check if source file exists
    if [ ! -f "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src/dpdk_feature_engine.py" ]; then
        echo -e "${RED}❌ dpdk_feature_engine.py not found${NC}"
        echo "  Expected: $SCRIPT_DIR/dpdk_suricata_ml_pipeline/src/dpdk_feature_engine.py"
        ((FAILED_SERVICES++))
        return 1
    fi
    
    cd "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src"
    source "${VENV_PATH}/bin/activate"
    
    # Clear old log
    > "$SCRIPT_DIR/logs/feature_engine.log"
    
    # Show what we're doing
    echo "  Starting: python3 -u dpdk_feature_engine.py"
    echo "  Log: logs/feature_engine.log"
    echo "  Waiting 5 seconds for startup..."
    
    # Use DPDK-based feature extraction (direct DPDK packet capture)
    python3 -u dpdk_feature_engine.py \
        > "$SCRIPT_DIR/logs/feature_engine.log" 2>&1 &
    FEATURE_PID=$!
    
    # Wait and check multiple times
    sleep 2
    if kill -0 $FEATURE_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Feature Engine process started (PID: $FEATURE_PID)${NC}"
    else
        echo -e "${RED}❌ Feature Engine died immediately${NC}"
        echo "  Last 20 lines of log:"
        tail -20 "$SCRIPT_DIR/logs/feature_engine.log" | sed 's/^/    /'
        deactivate
        cd "$SCRIPT_DIR"
        ((FAILED_SERVICES++))
        return 1
    fi
    
    sleep 3
    if kill -0 $FEATURE_PID 2>/dev/null; then
    echo -e "${GREEN}✓ Feature Engine running stable (PID: $FEATURE_PID)${NC}"
    echo "  Mode: DPDK direct packet capture"
    echo "  Output: Kafka topic '${KAFKA_TOPIC_ML_FEATURES:-ml-features}'"
        echo ""
        
        # Show first few log lines
        echo "  Initial log output:"
        head -10 "$SCRIPT_DIR/logs/feature_engine.log" 2>/dev/null | sed 's/^/    /' || true
        echo ""
        
        deactivate
        cd "$SCRIPT_DIR"
        ((STARTED_SERVICES++))
        return 0
    else
        echo -e "${RED}❌ Feature Engine crashed after startup${NC}"
        echo "  Full log:"
        cat "$SCRIPT_DIR/logs/feature_engine.log" | sed 's/^/    /'
        deactivate
        cd "$SCRIPT_DIR"
        ((FAILED_SERVICES++))
        return 1
    fi
}

start_ml_consumer() {
    echo -e "${BLUE}[4/5]${NC} Starting Ensemble ML Consumer..."
    
    # Create logs directory
    mkdir -p "$SCRIPT_DIR/logs"

    read -r kafka_host kafka_port <<< "$(get_kafka_host_port)"
    if ! wait_for_tcp_port "$kafka_host" "$kafka_port" 60 1; then
        echo -e "${RED}❌ Kafka did not become available on ${kafka_host}:${kafka_port}${NC}"
        ((FAILED_SERVICES++))
        return 1
    fi
    
    # Check if already running
    if pgrep -f "realtime_ensemble_consumer" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  ML Consumer already running${NC}"
        ML_PID=$(pgrep -f "realtime_ensemble_consumer" | head -n1)
        echo "  PID: $ML_PID"
        echo "  Log: logs/ml_consumer.log"
        return 0
    fi
    
    # Check if source file exists
    if [ ! -f "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src/realtime_ensemble_consumer_with_csv.py" ]; then
        echo -e "${YELLOW}⚠️  realtime_ensemble_consumer_with_csv.py not found${NC}"
        echo "  Trying alternate ML consumer..."
        
        # Try alternate consumer
        if [ -f "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src/realtime_ml_consumer.py" ]; then
            CONSUMER_SCRIPT="realtime_ml_consumer.py"
        else
            echo -e "${RED}❌ No ML consumer found${NC}"
            ((FAILED_SERVICES++))
            return 1
        fi
    else
        CONSUMER_SCRIPT="realtime_ensemble_consumer_with_csv.py"
    fi
    
    cd "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src"
    source "${VENV_PATH}/bin/activate"
    
    # Clear old log
    > "$SCRIPT_DIR/logs/ml_consumer.log"
    
    echo "  Starting: python3 $CONSUMER_SCRIPT"
    echo "  Log: logs/ml_consumer.log"
    echo "  Waiting 5 seconds for startup..."
    
    # Use ensemble consumer with CSV logging for accuracy metrics
    PYTHONWARNINGS="ignore::UserWarning" python3 -u "$CONSUMER_SCRIPT" \
        > "$SCRIPT_DIR/logs/ml_consumer.log" 2>&1 &
    ML_PID=$!
    
    # Wait and check
    sleep 2
    if kill -0 $ML_PID 2>/dev/null; then
        echo -e "${GREEN}✓ ML Consumer process started (PID: $ML_PID)${NC}"
    else
        echo -e "${RED}❌ ML Consumer died immediately${NC}"
        echo "  Last 20 lines of log:"
        tail -20 "$SCRIPT_DIR/logs/ml_consumer.log" | sed 's/^/    /'
        deactivate
        cd "$SCRIPT_DIR"
        ((FAILED_SERVICES++))
        return 1
    fi
    
    sleep 3
    if kill -0 $ML_PID 2>/dev/null; then
    echo -e "${GREEN}✓ ML Consumer running stable (PID: $ML_PID)${NC}"
    echo "  Input: Kafka topic '${KAFKA_TOPIC_ML_FEATURES:-ml-features}'"
        echo "  Output: Kafka topic 'ml-predictions'"
        if [ -f "$SCRIPT_DIR/logs/ml_predictions.csv" ]; then
            echo "  CSV: logs/ml_predictions.csv"
        fi
        echo ""
        
        # Show first few log lines
        echo "  Initial log output:"
        head -10 "$SCRIPT_DIR/logs/ml_consumer.log" 2>/dev/null | sed 's/^/    /' || true
        echo ""
        
        deactivate
        cd "$SCRIPT_DIR"
        ((STARTED_SERVICES++))
        return 0
    else
        echo -e "${RED}❌ ML Consumer crashed after startup${NC}"
        echo "  Full log:"
        cat "$SCRIPT_DIR/logs/ml_consumer.log" | sed 's/^/    /'
        deactivate
        cd "$SCRIPT_DIR"
        ((FAILED_SERVICES++))
        return 1
    fi
}

start_suricata_ml_consumer() {
    echo -e "${BLUE}[4b/5]${NC} Starting Suricata ML Consumer (alerts → predictions)..."

    mkdir -p "$SCRIPT_DIR/logs"

    if pgrep -f "ml_kafka_consumer.py" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Suricata ML Consumer already running${NC}"
        SML_PID=$(pgrep -f "ml_kafka_consumer.py" | head -n1)
        echo "  PID: $SML_PID"
        echo "  Log: logs/suricata_ml_consumer.log"
        return 0
    fi

    if [ ! -f "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src/ml_kafka_consumer.py" ]; then
        echo -e "${YELLOW}⚠️  ml_kafka_consumer.py not found${NC}"
        return 0
    fi

    cd "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src"
    source "${VENV_PATH}/bin/activate"

    > "$SCRIPT_DIR/logs/suricata_ml_consumer.log"

    echo "  Starting: python3 ml_kafka_consumer.py"
    echo "  Log: logs/suricata_ml_consumer.log"

    PYTHONWARNINGS="ignore::UserWarning" python3 -u ml_kafka_consumer.py \
        > "$SCRIPT_DIR/logs/suricata_ml_consumer.log" 2>&1 &
    SML_PID=$!

    sleep 2
    if kill -0 $SML_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Suricata ML Consumer started (PID: $SML_PID)${NC}"
    else
        echo -e "${RED}❌ Suricata ML Consumer died immediately${NC}"
        tail -20 "$SCRIPT_DIR/logs/suricata_ml_consumer.log" | sed 's/^/    /'
        deactivate
        cd "$SCRIPT_DIR"
        return 1
    fi

    sleep 3
    if kill -0 $SML_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Suricata ML Consumer running stable (PID: $SML_PID)${NC}"
        echo "  Input: Kafka topic 'suricata-alerts'"
        echo "  Output: Kafka topic 'ml-predictions'"
        echo ""
        echo "  Initial log output:"
        head -10 "$SCRIPT_DIR/logs/suricata_ml_consumer.log" 2>/dev/null | sed 's/^/    /' || true
        echo ""
        deactivate
        cd "$SCRIPT_DIR"
        ((STARTED_SERVICES++))
        return 0
    else
        echo -e "${RED}❌ Suricata ML Consumer crashed after startup${NC}"
        cat "$SCRIPT_DIR/logs/suricata_ml_consumer.log" | sed 's/^/    /'
        deactivate
        cd "$SCRIPT_DIR"
        return 1
    fi
}

start_metrics_dashboard() {
    echo -e "${BLUE}[5/5]${NC} Starting Metrics Dashboard (optional)..."
    
    # Check if already running
    if pgrep -f "metrics_dashboard.py" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Metrics Dashboard already running${NC}"
        return 0
    fi
    
    cd "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/scripts"
    source "${VENV_PATH}/bin/activate"
    
    # Run in background, suppress errors if Flask/Plotly not available
    python3 -u metrics_dashboard.py \
        > "$SCRIPT_DIR/logs/metrics_dashboard.log" 2>&1 &
    DASHBOARD_PID=$!
    deactivate
    cd "$SCRIPT_DIR"
    
    sleep 2
    if kill -0 $DASHBOARD_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Metrics Dashboard started (PID: $DASHBOARD_PID)${NC}"
        echo "  Log: logs/metrics_dashboard.log"
        echo "  URL: http://localhost:5000"
        echo ""
        ((STARTED_SERVICES++))
        return 0
    else
        echo -e "${YELLOW}⚠️  Metrics Dashboard not available (optional)${NC}\n"
        return 0
    fi
}

show_summary() {
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}Pipeline Summary${NC}\n"
    
    echo -e "  ${GREEN}✓ Services started: $STARTED_SERVICES${NC}"
    if [ $FAILED_SERVICES -gt 0 ]; then
        echo -e "  ${RED}✗ Services failed: $FAILED_SERVICES${NC}"
    fi
    echo
    
    echo -e "${BOLD}Architecture (DPDK Mode):${NC}"
    echo -e "  ${MAGENTA}NIC (${NETWORK_INTERFACE} @ PCI ${INTERFACE_PCI_ADDRESS})${NC}"
    echo -e "       │"
    echo -e "       ├─ DPDK PMD (kernel bypass, zero-copy)"
    echo -e "       │"
    echo -e "       ├─→ ${YELLOW}Suricata${NC} → Kafka"
    echo -e "       │   (signature-based alerts, 1-10 Gbps)"
    echo -e "       │"
    echo -e "       └─→ ${GREEN}Feature Engine${NC} → Kafka"
    echo -e "           (accurate CICIDS65 features)"
    echo -e "               │"
    echo -e "               └→ ${BLUE}ML Consumer${NC}"
    echo -e "                   (ensemble predictions, threat scores)"
    echo -e "\n  ${BOLD}ML Mode:${NC} $(get_ml_mode_label)"
    echo
    
    echo -e "${BOLD}Performance Characteristics:${NC}"
    echo -e "  Throughput:  1-10+ Gbps (hardware-limited)"
    echo -e "  Latency:     Microseconds (kernel bypass)"
    echo -e "  CPU:         Low overhead (zero-copy, no context switches)"
    echo -e "  Accuracy:    High (CICIDS65 feature extraction in real-time)"
    echo
    
    echo -e "${BOLD}Monitoring:${NC}"
    echo -e "  Feature Engine: tail -f logs/feature_engine.log"
    echo -e "  ML Consumer:    tail -f logs/ml_consumer.log"
    echo -e "  Suricata:       tail -f /var/log/suricata/suricata.log"
    
    if netstat -tuln 2>/dev/null | grep -q ":5000"; then
        echo -e "  Metrics:        http://localhost:5000"
    fi
    echo
    
    echo -e "${BOLD}Kafka Topics:${NC}"
    if command -v kafka-topics.sh &> /dev/null; then
        echo -e "  ${CYAN}suricata-alerts${NC} (Suricata signatures & alerts)"
    echo -e "  ${CYAN}${KAFKA_TOPIC_ML_FEATURES:-ml-features}${NC} (CICIDS feature vectors)"
        echo -e "  ${CYAN}ml-predictions${NC} (ML predictions with confidence scores)"
    fi
    echo
    
    echo -e "${BOLD}Stop the pipeline:${NC}"
    echo -e "  sudo $0 stop"
    echo
    
    echo -e "${BOLD}View interface binding:${NC}"
    echo -e "  dpdk-devbind.py --status | grep DPDK"
    echo
    
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}\n"
    
    if [ $FAILED_SERVICES -gt 0 ]; then
        return 1
    fi
    return 0
}

stop_all() {
    echo -e "${YELLOW}Stopping all DPDK pipeline services...${NC}\n"
    
    # Stop in reverse order (ML Consumer → Feature Engine → Suricata → Kafka)
    
    # ML Consumers (both single and ensemble)
    pkill -9 -f "realtime_ensemble_consumer_with_csv.py|realtime_ensemble_consumer.py|realtime_ml_consumer.py|ml_kafka_consumer.py" 2>/dev/null && \
        echo -e "${GREEN}✓ ML Consumer stopped${NC}" || true
    
    # Feature Engine (DPDK)
    pkill -9 -f "dpdk_feature_engine.py" 2>/dev/null && \
        echo -e "${GREEN}✓ Feature Engine stopped${NC}" || true
    
    # Suricata DPDK
    pkill -9 -f "suricata.*--dpdk" 2>/dev/null && \
        echo -e "${GREEN}✓ Suricata DPDK stopped${NC}" || true
    
    # Metrics Dashboard
    pkill -f "metrics_dashboard.py" 2>/dev/null && \
        echo -e "${GREEN}✓ Metrics Dashboard stopped${NC}" || true
    
    # Ask about Kafka
    echo -e "\n${CYAN}Kafka Management:${NC}"
    if pgrep -f "kafka.Kafka|zookeeper" > /dev/null 2>&1; then
        read -p "Stop Kafka and Zookeeper? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            pkill -f "kafka.Kafka|zookeeper" 2>/dev/null && \
                echo -e "${GREEN}✓ Kafka stopped${NC}" || true
        else
            echo -e "${YELLOW}⚠️  Kafka still running${NC}"
        fi
    fi
    
    # Ask about DPDK unbinding
    echo -e "\n${CYAN}DPDK Interface Management:${NC}"
    DEVBIND=$(which dpdk-devbind.py 2>/dev/null || echo "/usr/local/bin/dpdk-devbind.py")
    if [ -f "$DEVBIND" ] && "$DEVBIND" --status 2>/dev/null | grep -q "drv="; then
        read -p "Unbind DPDK interfaces and restore kernel drivers? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            bash "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/scripts/unbind_interface.sh" && \
                echo -e "${GREEN}✓ DPDK interfaces unbound${NC}" || true
        else
            echo -e "${YELLOW}⚠️  Interfaces still bound to DPDK${NC}"
        fi
    fi
    
    echo -e "\n${GREEN}✓ All services stopped${NC}\n"
}

show_status() {
    echo -e "${BOLD}${CYAN}Pipeline Status (DPDK Mode):${NC}\n"
    
    # Kafka
    if netstat -tuln 2>/dev/null | grep -q ":9092"; then
        echo -e "  ${GREEN}✓${NC} Kafka: Running (port 9092)"
    else
        echo -e "  ${RED}✗${NC} Kafka: Stopped"
    fi
    
    # Suricata DPDK
    if pgrep -f "suricata" > /dev/null 2>&1; then
        SURICATA_PID=$(pgrep -f "suricata" | head -n1)
        echo -e "  ${GREEN}✓${NC} Suricata: Running (PID $SURICATA_PID)"
    else
        echo -e "  ${RED}✗${NC} Suricata: Stopped"
    fi
    
    # Feature Engine
    if pgrep -f "dpdk_feature_engine" > /dev/null 2>&1; then
        FEATURE_PID=$(pgrep -f "dpdk_feature_engine" | head -n1)
        echo -e "  ${GREEN}✓${NC} Feature Engine: Running (PID $FEATURE_PID)"
    else
        echo -e "  ${RED}✗${NC} Feature Engine: Stopped"
    fi
    
    # ML Consumer
    if pgrep -f "realtime_ensemble_consumer|realtime_ml_consumer" > /dev/null 2>&1; then
        ML_PID=$(pgrep -f "realtime_ensemble_consumer|realtime_ml_consumer" | head -n1)
        echo -e "  ${GREEN}✓${NC} ML Consumer: Running (PID $ML_PID)"
        if pgrep -f "realtime_ensemble_consumer" > /dev/null 2>&1; then
            echo -e "      Mode: Ensemble (5-model voting)"
        elif pgrep -f "realtime_ml_consumer" > /dev/null 2>&1; then
            echo -e "      Mode: Single model (RandomForest PCA)"
        fi
    else
        echo -e "  ${RED}✗${NC} ML Consumer: Stopped"
    fi

    # Suricata ML Consumer
    if pgrep -f "ml_kafka_consumer.py" > /dev/null 2>&1; then
        SML_PID=$(pgrep -f "ml_kafka_consumer.py" | head -n1)
        echo -e "  ${GREEN}✓${NC} Suricata ML Consumer: Running (PID $SML_PID)"
    else
        echo -e "  ${YELLOW}○${NC} Suricata ML Consumer: Stopped (optional)"
    fi
    
    # Metrics Dashboard
    if pgrep -f "metrics_dashboard" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Metrics Dashboard: Running (http://localhost:5000)"
    else
        echo -e "  ${YELLOW}○${NC} Metrics Dashboard: Stopped (optional)"
    fi
    
    # DPDK binding
    DEVBIND=$(which dpdk-devbind.py 2>/dev/null || echo "/usr/local/bin/dpdk-devbind.py")
    if [ -f "$DEVBIND" ]; then
    DPDK_COUNT=$("$DEVBIND" --status 2>/dev/null | awk '/drv=/ && $0 !~ /if=/ {count++} END {print count+0}' || echo 0)
        if [ $DPDK_COUNT -gt 0 ]; then
            echo -e "  ${GREEN}✓${NC} DPDK: $DPDK_COUNT interface(s) bound"
        else
            echo -e "  ${YELLOW}⚠${NC} DPDK: No interfaces bound"
        fi
    fi
    
    echo
}

main() {
    check_root

    local action
    if [ $# -gt 0 ]; then
        action="$1"
        shift
    else
        action="start"
    fi
    
    case "$action" in
        start)
            parse_start_flags "$@"
            print_header
            stop_afpacket_suricata_instances
            load_config
            verify_dpdk_prerequisites
            
            echo -e "${CYAN}Starting Complete DPDK Pipeline...${NC}"
            echo -e "  ML Mode: $(get_ml_mode_label)\n"
            
            if ! start_kafka; then
                echo -e "${RED}Aborting pipeline because Kafka is unavailable.${NC}"
                show_summary
                exit 1
            fi

            if ! start_suricata_dpdk; then
                echo -e "${RED}Aborting pipeline because Suricata failed to start.${NC}"
                show_summary
                exit 1
            fi

            if ! start_feature_engine_dpdk; then
                echo -e "${RED}Aborting pipeline because the Feature Engine failed to start.${NC}"
                show_summary
                exit 1
            fi

            if ! start_ml_consumer; then
                echo -e "${RED}Aborting pipeline because the ML Consumer failed to start.${NC}"
                show_summary
                exit 1
            fi

            start_suricata_ml_consumer || true
            start_metrics_dashboard || true
            
            show_summary
            ;;
        
        stop)
            if [ $# -gt 0 ]; then
                echo -e "${YELLOW}Ignoring unsupported options for stop: $*${NC}"
            fi
            stop_all
            ;;
        
        status)
            if [ $# -gt 0 ]; then
                echo -e "${RED}❌ status does not accept options${NC}"
                exit 1
            fi
            show_status
            ;;
        
        restart)
            echo -e "${YELLOW}Restarting DPDK pipeline...${NC}\n"
            stop_all
            sleep 3
            exec "$0" start "$@"
            ;;
        
        test|debug)
            if [ $# -gt 0 ]; then
                echo -e "${RED}❌ test/debug does not accept options${NC}"
                exit 1
            fi
            print_header
            echo -e "${CYAN}🧪 TEST MODE - Feature Engine Only${NC}\n"
            check_root
            load_config
            
            echo -e "${YELLOW}This mode starts ONLY the Feature Engine for debugging${NC}"
            echo -e "No Kafka, Suricata, or ML Consumer will be started\n"
            
            echo "Checking DPDK binding..."
            dpdk-devbind.py --status | grep -A 2 "DPDK-compatible"
            echo ""
            
            mkdir -p "$SCRIPT_DIR/logs"
            
            cd "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src"
            if [ ! -f "dpdk_feature_engine.py" ]; then
                echo -e "${RED}❌ dpdk_feature_engine.py not found${NC}"
                exit 1
            fi
            
            echo "Starting Feature Engine in foreground (Ctrl+C to stop)..."
            echo "Log will be displayed here AND saved to logs/feature_engine.log"
            echo ""
            
            source "${VENV_PATH}/bin/activate"
            python3 -u dpdk_feature_engine.py 2>&1 | tee "$SCRIPT_DIR/logs/feature_engine.log"
            ;;

        proof)
            print_header
            load_config
            display_runtime_proof
            ;;
        
        logs)
            if [ $# -gt 0 ]; then
                echo -e "${RED}❌ logs does not accept options${NC}"
                exit 1
            fi
            print_header
            echo -e "${CYAN}📋 Live Logs${NC}\n"
            echo "Choose log to view:"
            echo "  1) Feature Engine"
            echo "  2) ML Consumer"
            echo "  3) Suricata"
            echo "  4) All (split screen)"
            echo ""
            read -p "Choice [1-4]: " log_choice
            
            case $log_choice in
                1) tail -f "$SCRIPT_DIR/logs/feature_engine.log" ;;
                2) tail -f "$SCRIPT_DIR/logs/ml_consumer.log" ;;
                3) tail -f /var/log/suricata/suricata.log ;;
                4) 
                    echo "Opening all logs (Ctrl+C to exit)..."
                    tail -f "$SCRIPT_DIR/logs"/*.log /var/log/suricata/suricata.log 2>/dev/null
                    ;;
                *) echo "Invalid choice" ;;
            esac
            ;;
        
        *)
            print_usage
            exit 1
            ;;
    esac
}

main "$@"
