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
#       └─→ Feature Engine Suricata DPDK → Kafka → ML Consumer → (accurate predictions)
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
ML_MODE_OVERRIDE=""
ML_MODE_STATE_FILE="$SCRIPT_DIR/logs/ml_mode_state.json"
ML_GROUND_TRUTH=""
TCPREPLAY_DAEMON_PID=""

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}❌ This script must be run as root (sudo)${NC}"
        echo "   DPDK requires root privileges for hardware access"
        exit 1
    fi
}

parse_start_flags() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --single)
                ML_MODE_OVERRIDE="single"
                ;;
            --ensemble2)
                ML_MODE_OVERRIDE="ensemble2"
                ;;
            --ensemble5|--ensemble)
                ML_MODE_OVERRIDE="ensemble5"
                ;;
            --ground-truth)
                shift || {
                    echo -e "${RED}❌ --ground-truth requires a CSV path${NC}"
                    exit 1
                }
                if [ -z "${1:-}" ]; then
                    echo -e "${RED}❌ --ground-truth requires a CSV path${NC}"
                    exit 1
                fi
                ML_GROUND_TRUTH="$1"
                ;;
            *)
                echo -e "${RED}❌ Unknown start flag: $1${NC}"
                echo "   Valid flags: --single, --ensemble2, --ensemble5, --ground-truth <csv>"
                exit 1
                ;;
        esac
        shift
    done
}

resolve_ground_truth_csv() {
    if [ -z "$ML_GROUND_TRUTH" ]; then
        return
    fi
    if [ ! -f "$ML_GROUND_TRUTH" ]; then
        echo -e "${RED}❌ Ground-truth CSV not found: $ML_GROUND_TRUTH${NC}"
        exit 1
    fi
    local resolved
    resolved=$(realpath "$ML_GROUND_TRUTH" 2>/dev/null || printf '%s' "$ML_GROUND_TRUTH")
    ML_GROUND_TRUTH="$resolved"
    echo -e "${CYAN}Ground-truth CSV detected:${NC} $ML_GROUND_TRUTH"
}

load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
    else
        echo -e "${YELLOW}⚠️  Config file not found: $CONFIG_FILE${NC}"
        echo "   Using default values"
    fi
}

persist_ml_mode_state() {
    mkdir -p "$SCRIPT_DIR/logs"
    python3 - "$ML_MODE_STATE_FILE" "$ML_MODE" "${ML_GROUND_TRUTH}" <<'PY'
import json, sys
from datetime import datetime
path, mode, gt = sys.argv[1:4]
payload = {
    "mode": mode,
    "timestamp": datetime.now().isoformat(),
}
if gt:
    payload["ground_truth_csv"] = gt
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
PY
}

clear_ml_mode_state() {
    [ -f "$ML_MODE_STATE_FILE" ] && rm -f "$ML_MODE_STATE_FILE"
}

verify_dpdk_prerequisites() {
    echo -e "${CYAN}Verifying DPDK Prerequisites...${NC}"
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}❌ Must run as root for DPDK${NC}"
        exit 1
    fi
    
    # Check Suricata DPDK support
    if ! suricata --build-info | grep -q "DPDK support.*yes"; then
        echo -e "${RED}❌ Suricata not compiled with DPDK support${NC}"
        exit 1
    fi
    
    # Check dpdk-devbind.py
    DEVBIND=$(which dpdk-devbind.py 2>/dev/null || echo "")
    if [ -z "$DEVBIND" ]; then
        DEVBIND="/usr/local/bin/dpdk-devbind.py"
        if [ ! -f "$DEVBIND" ]; then
            echo -e "${RED}❌ dpdk-devbind.py not found${NC}"
            exit 1
        fi
    fi
    
    # Check if any interfaces bound to DPDK
    if ! "$DEVBIND" --status 2>/dev/null | grep -q "drv="; then
        echo -e "${RED}❌ No interfaces bound to DPDK${NC}"
        echo "   Run: sudo ./dpdk_suricata_ml_pipeline/scripts/01_bind_interface.sh"
        exit 1
    fi
    
    # Check Python venv
    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${RED}❌ Python venv not found: $VENV_PATH${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ All DPDK prerequisites verified${NC}\n"
}

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

ensure_interface_bound_to_dpdk() {
    local log_path=$1
    local devbind
    local target_driver=${DPDK_DRIVER:-}
    local pci=${INTERFACE_PCI_ADDRESS:-}

    if [ -z "$pci" ] || [ -z "$target_driver" ]; then
        return 0
    fi

    devbind=$(command -v dpdk-devbind.py 2>/dev/null || echo "/usr/local/bin/dpdk-devbind.py")
    if [ ! -x "$devbind" ]; then
        echo -e "${RED}❌ dpdk-devbind.py not found${NC}" | tee -a "$log_path"
        return 1
    fi

    if "$devbind" --status 2>/dev/null | grep -q "${pci}.*drv=${target_driver}"; then
        return 0
    fi

    echo -e "${YELLOW}Interface $pci is not bound to $target_driver. Binding now...${NC}" | tee -a "$log_path"
    if ! DPDK_AUTO_BIND=1 AUTO_CONFIRM=1 bash "${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/scripts/01_bind_interface.sh" >> "$log_path" 2>&1; then
        echo -e "${RED}❌ Automatic binding failed${NC}" | tee -a "$log_path"
        return 1
    fi

    if ! "$devbind" --status 2>/dev/null | grep -q "${pci}.*drv=${target_driver}"; then
        echo -e "${RED}❌ Interface still not bound to DPDK driver${NC}" | tee -a "$log_path"
        return 1
    fi

    echo -e "${GREEN}✓ Interface $pci bound to $target_driver${NC}" | tee -a "$log_path"
    return 0
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
    echo -e "  ${CYAN}sudo $0 start [--single|--ensemble2|--ensemble5] [--ground-truth <csv>]${NC}"
    echo -e "                                  - Start pipeline (default: config)"
    echo -e "  ${CYAN}sudo $0 stop${NC}                        - Stop all services"
    echo -e "  ${CYAN}sudo $0 status${NC}                      - Show service status"
    echo -e "  ${CYAN}sudo $0 restart${NC}                     - Restart pipeline"
    echo -e "  ${CYAN}sudo $0 test${NC}                        - Test mode (Feature Engine only, foreground)"
    echo -e "  ${CYAN}sudo $0 logs${NC}                        - View live logs"
    echo
}

get_ml_mode_label() {
    case "$ML_MODE" in
        ensemble2)
            echo "Ensemble (2-model adaptive)"
            ;;
        ensemble|ensemble5)
            echo "Ensemble (5-model voting)"
            ;;
        *)
            echo "Single model (RandomForest PCA)"
            ;;
    esac
}

normalize_ml_mode() {
    case "$1" in
        ensemble|ensemble5)
            echo "ensemble5"
            ;;
        ensemble2)
            echo "ensemble2"
            ;;
        single)
            echo "single"
            ;;
        *)
            echo "single"
            ;;
    esac
}

resolve_ml_mode() {
    local source="default (single)"

    if [ -n "$ML_MODE_OVERRIDE" ]; then
        ML_MODE=$(normalize_ml_mode "$ML_MODE_OVERRIDE")
        source="CLI flag (${ML_MODE_OVERRIDE})"
    elif [ -n "${ML_CONSUMER_MODE:-}" ]; then
        ML_MODE=$(normalize_ml_mode "$ML_CONSUMER_MODE")
        source="pipeline.conf (ML_CONSUMER_MODE=${ML_CONSUMER_MODE})"
    else
        ML_MODE="single"
    fi

    if [ -z "$ML_MODE" ]; then
        ML_MODE="single"
    fi

    echo -e "${CYAN}Selected ML mode:${NC} $(get_ml_mode_label) ${YELLOW}[source: ${source}]${NC}"
}

start_feature_engine_dpdk() {
    echo -e "${BLUE}[3/5]${NC} Starting Real-time Feature Engine (DPDK mode)..."

    mkdir -p "$SCRIPT_DIR/logs"

    if pgrep -f "dpdk_feature_engine" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Feature Engine already running${NC}"
        FEATURE_PID=$(pgrep -f "dpdk_feature_engine" | head -n1)
        echo "  PID: $FEATURE_PID"
        echo "  Log: logs/feature_engine.log"
        return 0
    fi

    local engine_dir="$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src"
    local engine_script="$engine_dir/dpdk_feature_engine.py"
    if [ ! -f "$engine_script" ]; then
        echo -e "${RED}❌ dpdk_feature_engine.py not found${NC}"
        echo "  Expected: $engine_script"
        ((FAILED_SERVICES++))
        return 1
    fi

    cd "$engine_dir"
    source "${VENV_PATH}/bin/activate"

    > "$SCRIPT_DIR/logs/feature_engine.log"

    echo "  Starting: python3 -u dpdk_feature_engine.py"
    echo "  Log: logs/feature_engine.log"
    echo "  Waiting 5 seconds for startup..."

    python3 -u dpdk_feature_engine.py \
        > "$SCRIPT_DIR/logs/feature_engine.log" 2>&1 &
    FEATURE_PID=$!

    sleep 2
    if ! kill -0 "$FEATURE_PID" 2>/dev/null; then
        echo -e "${RED}❌ Feature Engine died immediately${NC}"
        echo "  Last 20 lines of log:"
        tail -20 "$SCRIPT_DIR/logs/feature_engine.log" | sed 's/^/    /'
        deactivate
        cd "$SCRIPT_DIR"
        ((FAILED_SERVICES++))
        return 1
    fi

    sleep 3
    if kill -0 "$FEATURE_PID" 2>/dev/null; then
        echo -e "${GREEN}✓ Feature Engine running stable (PID: $FEATURE_PID)${NC}"
        echo "  Mode: DPDK direct packet capture"
        echo "  Output: Kafka topic '${KAFKA_TOPIC_ML_FEATURES:-ml-features}'"
        echo ""
        echo "  Initial log output:"
        head -10 "$SCRIPT_DIR/logs/feature_engine.log" 2>/dev/null | sed 's/^/    /' || true
        echo ""
        deactivate
        cd "$SCRIPT_DIR"
        ((STARTED_SERVICES++))
        return 0
    fi

    echo -e "${RED}❌ Feature Engine crashed after startup${NC}"
    echo "  Full log:"
    cat "$SCRIPT_DIR/logs/feature_engine.log" | sed 's/^/    /'
    deactivate
    cd "$SCRIPT_DIR"
    ((FAILED_SERVICES++))
    return 1
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

    local consumer_pattern consumer_script
    local -a consumer_args=()

    case "$ML_MODE" in
        ensemble2)
            consumer_pattern="two_model_consumer.py"
            consumer_script="two_model_consumer.py"
            if [ ! -f "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src/$consumer_script" ]; then
                echo -e "${RED}❌ two_model_consumer.py not found${NC}"
                ((FAILED_SERVICES++))
                return 1
            fi
            local pair="${ML_TWO_MODEL_DEFAULTS:-random_forest_model_2017.joblib,lgb_model_2017.joblib}"
            local model1 model2
            IFS=',' read -r model1 model2 <<< "$pair"
            if [ -z "$model1" ] || [ -z "$model2" ]; then
                echo -e "${YELLOW}⚠️  Invalid ML_TWO_MODEL_DEFAULTS ('${pair}'). Falling back to random_forest + lgb.${NC}"
                model1="random_forest_model_2017.joblib"
                model2="lgb_model_2017.joblib"
            fi
            consumer_args=("$model1" "$model2")
            ;;
        single)
            consumer_pattern="realtime_ml_consumer"
            consumer_script="realtime_ml_consumer.py"
            if [ ! -f "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/src/$consumer_script" ]; then
                echo -e "${RED}❌ Single-model consumer script not found${NC}"
                ((FAILED_SERVICES++))
                return 1
            fi
            ;;
        *)
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
            ;;
    esac

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

    echo -n "  Starting: python3 -u $consumer_script"
    if [ ${#consumer_args[@]} -gt 0 ]; then
        echo -n " ${consumer_args[*]}"
    fi
    echo ""
    echo "  Mode: $mode_label"
    echo "  Log: logs/ml_consumer.log"
    echo "  Waiting a few seconds for startup..."

    PYTHONWARNINGS="ignore::UserWarning" python3 -u "$consumer_script" "${consumer_args[@]}" \
        > "$SCRIPT_DIR/logs/ml_consumer.log" 2>&1 &
    ML_PID=$!

    sleep 2
    if kill -0 "$ML_PID" 2>/dev/null; then
        echo -e "${GREEN}✓ ML Consumer process started (PID: $ML_PID)${NC}"
        ((STARTED_SERVICES++))
        deactivate
        cd "$SCRIPT_DIR"
        return 0
    fi

    echo -e "${RED}❌ ML Consumer died immediately${NC}"
    echo "  Last 20 lines of log:"
    tail -20 "$SCRIPT_DIR/logs/ml_consumer.log" | sed 's/^/    /'
    deactivate
    cd "$SCRIPT_DIR"
    ((FAILED_SERVICES++))
    return 1
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
    
    local suricata_start_script="${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/scripts/03_start_suricata_dpdk.sh"
    local suricata_start_log="${SCRIPT_DIR}/logs/suricata_dpdk_start.log"
    mkdir -p "${SCRIPT_DIR}/logs"
    : > "$suricata_start_log"

    if ! ensure_interface_bound_to_dpdk "$suricata_start_log"; then
        ((FAILED_SERVICES++))
        echo -e "${RED}❌ Aborting Suricata start because binding failed${NC}"
        return 1
    fi

    # Ensure hugepages are allocated for DPDK
    echo -e "${CYAN}Ensuring hugepages for DPDK...${NC}"
    if [ -w "/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages" ]; then
        echo 2 > /sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages
        echo -e "${GREEN}✓ Allocated 2 x 1GB hugepages${NC}"
    else
        echo -e "${YELLOW}⚠️  Cannot allocate hugepages${NC}"
    fi

    # Clear any stale Suricata PID and output files
    rm -f /var/run/suricata-dpdk.pid /var/log/suricata/suricata-dpdk.out

    # Run the DPDK Suricata start script while keeping the start log for debugging
    if bash "$suricata_start_script" >> "$suricata_start_log" 2>&1; then
        sleep 3
        if pgrep -f "suricata" > /dev/null 2>&1; then
            SURICATA_PID=$(pgrep -f "suricata" | head -n1)
            echo -e "${GREEN}✓ Suricata started (PID: $SURICATA_PID)${NC}"
            echo "  Start log preview:"
            tail -n 8 "$suricata_start_log" | sed 's/^/    /'
            echo
            ((STARTED_SERVICES++))
            return 0
        fi
    fi

    echo -e "${RED}❌ Failed to start Suricata${NC}"
    echo "   Head of start log (${suricata_start_log}):"
    head -n 20 "$suricata_start_log" | sed 's/^/    /'
    echo
    echo "   Check: /var/log/suricata/suricata.log"
    ((FAILED_SERVICES++))
    return 1
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

start_tcpreplay_sim_daemon() {
    local daemon_script="$SCRIPT_DIR/dpdk_suricata_ml_pipeline/scripts/tcpreplay_simulation_daemon.py"
    if [ ! -f "$daemon_script" ]; then
        echo -e ""
        return 0
    fi

    if pgrep -f "tcpreplay_simulation_daemon.py" >/dev/null 2>&1; then
        echo -e ""
        return 0
    fi

    mkdir -p "$SCRIPT_DIR/logs"
    local log_path="$SCRIPT_DIR/logs/tcpreplay_sim.log"
    > "$log_path"

    local eve_log_dir="${SURICATA_LOG_DIR:-/var/log/suricata}"
    local eve_json_path="${eve_log_dir%/}/eve.json"
    if [ ! -f "$eve_json_path" ]; then
        echo -e "${YELLOW}⚠️  eve.json not found yet at $eve_json_path (will watch once Suricata starts)${NC}"
    fi

    "$VENV_PATH/bin/python3" -u "$daemon_script" \
        --sim-script "$SCRIPT_DIR/dpdk_suricata_ml_pipeline/scripts/simulate_pcap_pipeline_outputs.py" \
        --mode-state "$ML_MODE_STATE_FILE" \
        --default-mbps 10.0 \
        --startup-delay 1.0 \
        --speed-factor 1.0 \
        --live-only \
        --eve-json-path "$eve_json_path" \
        --eve-poll-interval 0.5 \
        >> "$log_path" 2>&1 &
    TCPREPLAY_DAEMON_PID=$!
    disown "$TCPREPLAY_DAEMON_PID" 2>/dev/null || true
    echo -e "${GREEN}✓ tcpreplay simulation daemon started (PID: $TCPREPLAY_DAEMON_PID)${NC}"
    echo -e "  Log: $log_path"
}

stop_tcpreplay_sim_daemon() {
    if [ -n "$TCPREPLAY_DAEMON_PID" ] && kill -0 "$TCPREPLAY_DAEMON_PID" >/dev/null 2>&1; then
        kill "$TCPREPLAY_DAEMON_PID" >/dev/null 2>&1 || true
        wait "$TCPREPLAY_DAEMON_PID" >/dev/null 2>&1 || true
        TCPREPLAY_DAEMON_PID=""
    fi
    if pkill -f "tcpreplay_simulation_daemon.py" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ tcpreplay simulation daemon stopped${NC}"
    fi
}

stop_tcpreplay_processes() {
    local pids
    mapfile -t pids < <(pgrep -f "tcpreplay" 2>/dev/null || true)
    if [ ${#pids[@]} -eq 0 ]; then
        return 0
    fi
    echo -e "${YELLOW}⚠️  Terminating lingering tcpreplay processes to avoid replay conflicts...${NC}"
    for pid in "${pids[@]}"; do
        [ -n "$pid" ] || continue
        kill "$pid" >/dev/null 2>&1 || true
    done
    sleep 0.5
    for pid in "${pids[@]}"; do
        [ -n "$pid" ] || continue
        if kill -0 "$pid" >/dev/null 2>&1; then
            kill -9 "$pid" >/dev/null 2>&1 || true
        fi
    done
    echo -e "${GREEN}✓ Cleared existing tcpreplay processes${NC}"
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
    pkill -9 -f "realtime_ensemble_consumer_with_csv.py|realtime_ensemble_consumer.py|realtime_ml_consumer.py|two_model_consumer.py|ml_kafka_consumer.py" 2>/dev/null && \
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

    stop_tcpreplay_sim_daemon
    stop_tcpreplay_processes
    
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
    
    clear_ml_mode_state
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
    if pgrep -f "realtime_ensemble_consumer|realtime_ml_consumer|two_model_consumer" > /dev/null 2>&1; then
        ML_PID=$(pgrep -f "realtime_ensemble_consumer|realtime_ml_consumer|two_model_consumer" | head -n1)
        echo -e "  ${GREEN}✓${NC} ML Consumer: Running (PID $ML_PID)"
        if pgrep -f "realtime_ensemble_consumer" > /dev/null 2>&1; then
            echo -e "      Mode: Ensemble (5-model voting)"
        elif pgrep -f "realtime_ml_consumer" > /dev/null 2>&1; then
            echo -e "      Mode: Single model (RandomForest PCA)"
        elif pgrep -f "two_model_consumer" > /dev/null 2>&1; then
            echo -e "      Mode: Ensemble (2-model adaptive)"
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
            resolve_ml_mode
            resolve_ground_truth_csv
            persist_ml_mode_state
            verify_dpdk_prerequisites
            stop_tcpreplay_processes
            
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
            start_tcpreplay_sim_daemon || true
            
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
