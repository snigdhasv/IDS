#!/bin/bash
################################################################################
# Send Test Traffic to IDS
################################################################################
# Sends PCAP traffic to Intel NIC for IDS testing
################################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REALTEK_NIC="enp5s0"
PCAP_DIR="${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/pcap_samples"
CICIDS_PCAP_DIR="${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/CICIDS2017_real_pcaps"
WEDNESDAY_FIXED_PCAP="${CICIDS_PCAP_DIR}/Wednesday-fixed.pcap"
SIM_SCRIPT="${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/scripts/simulate_pcap_pipeline_outputs.py"
MODE_STATE_FILE="${SCRIPT_DIR}/logs/ml_mode_state.json"
REPLAY_SPEED=10

SIMULATE_ML=1
SIM_DAEMON_ACTIVE=0
SIM_MODE="auto"
SIM_ACCURACY="0.94"
SIM_GROUND_TRUTH=""
CUSTOM_PCAP=""
SIM_SPEED_FACTOR="1.0"
SIM_STARTUP_DELAY="1.0"
SIM_TIMELINE_SECONDS=""
ACTIVE_SIM_PID=""
STATE_MODE=""
STATE_GROUND_TRUTH=""

usage() {
    cat <<EOF
Usage: $0 [options]

Options:
  --pcap <file>           Replay this PCAP (skip menu)
  --speed <mbps>          tcpreplay speed in Mbps (default: ${REPLAY_SPEED})
  --ml-mode <mode|auto>   Simulator mode (single | ensemble2 | ensemble5 | auto)
  --ml-accuracy <float>   Target simulator accuracy (default: ${SIM_ACCURACY})
  --ml-speed-factor <x>   Accelerate or slow simulated timeline (default: ${SIM_SPEED_FACTOR})
    --ml-timeline <sec>     Force simulator to finish within this many seconds
  --ml-start-delay <sec>  Delay before simulator begins streaming (default: ${SIM_STARTUP_DELAY}s)
  --ground-truth <csv>    Provide ground-truth CSV for simulator
  -h, --help              Show this help

Examples:
        $0
    $0 --pcap dpdk_suricata_ml_pipeline/CICIDS2017_real_pcaps/Friday-WorkingHours.pcap
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pcap)
            shift
            CUSTOM_PCAP="$1"
            ;;
        --speed)
            shift
            REPLAY_SPEED="$1"
            ;;
        --ml-mode)
            shift
            SIM_MODE="$1"
            ;;
        --ml-accuracy)
            shift
            SIM_ACCURACY="$1"
            ;;
        --ml-speed-factor)
            shift
            SIM_SPEED_FACTOR="$1"
            ;;
        --ml-timeline)
            shift
            SIM_TIMELINE_SECONDS="$1"
            ;;
        --ml-start-delay)
            shift
            SIM_STARTUP_DELAY="$1"
            ;;
        --ground-truth)
            shift
            SIM_GROUND_TRUTH="$1"
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
    shift || true
done

detect_sim_daemon() {
    if pgrep -f "tcpreplay_simulation_daemon.py" >/dev/null 2>&1; then
        SIM_DAEMON_ACTIVE=1
        SIMULATE_ML=0
    else
        SIM_DAEMON_ACTIVE=0
        SIMULATE_ML=1
    fi
}

detect_sim_daemon

validate_mode() {
    [[ $SIMULATE_ML -eq 1 ]] || return 0
    if [ "$SIM_MODE" = "auto" ]; then
        return
    fi
    case "$SIM_MODE" in
        single|ensemble2|ensemble5)
            ;;
        *)
            echo -e "${YELLOW}⚠️  Invalid --ml-mode '${SIM_MODE}', defaulting to ensemble5${NC}"
            SIM_MODE="ensemble5"
            ;;
    esac
}

ensure_pipeline_ready() {
    [[ $SIMULATE_ML -eq 1 ]] || return 0

    local missing=()
    if ! pgrep -f "suricata.*--dpdk" >/dev/null 2>&1; then
        missing+=("Suricata DPDK")
    fi
    if ! pgrep -f "dpdk_feature_engine.py" >/dev/null 2>&1; then
        missing+=("DPDK feature engine")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Pipeline components not running: ${missing[*]}.${NC}"
        echo "Start the real-time pipeline (run_realtime_engine_dpdk.sh start) before replaying traffic."
        exit 1
    fi
}

load_mode_state_file() {
    STATE_MODE=""
    STATE_GROUND_TRUTH=""
    [[ -f "$MODE_STATE_FILE" ]] || return 0
    mapfile -t __STATE_DATA < <(python3 - "$MODE_STATE_FILE" <<'PY'
import json, sys
mode = ""
gt = ""
try:
    with open(sys.argv[1], 'r', encoding='utf-8') as handle:
        data = json.load(handle)
    mode = (data.get('mode') or '').strip()
    gt = (data.get('ground_truth_csv') or '').strip()
except Exception:
    pass
print(mode)
print(gt)
PY
)
    STATE_MODE="${__STATE_DATA[0]:-}"
    STATE_GROUND_TRUTH="${__STATE_DATA[1]:-}"
    return 0
}

resolve_simulation_mode() {
    [[ $SIMULATE_ML -eq 1 ]] || return 0
    load_mode_state_file
    if [ "$SIM_MODE" != "auto" ]; then
        if [[ -z "$SIM_GROUND_TRUTH" && -n "$STATE_GROUND_TRUTH" ]]; then
            if [ -f "$STATE_GROUND_TRUTH" ]; then
                SIM_GROUND_TRUTH="$STATE_GROUND_TRUTH"
                echo -e "${CYAN}Auto-detected ground truth CSV (${SIM_GROUND_TRUTH}).${NC}"
            else
                echo -e "${YELLOW}⚠️  Ground truth CSV from state file missing: ${STATE_GROUND_TRUTH}.${NC}"
            fi
        fi
        return 0
    fi

    if [ -n "$STATE_MODE" ]; then
        SIM_MODE="$STATE_MODE"
        echo -e "${CYAN}Auto-detected ML mode (${SIM_MODE}) from $(basename "$MODE_STATE_FILE").${NC}"
    fi

    if [ "$SIM_MODE" = "auto" ]; then
        echo -e "${YELLOW}⚠️  Unable to auto-detect ML mode; defaulting to ensemble5.${NC}"
        SIM_MODE="ensemble5"
    fi
    validate_mode

    if [[ -z "$SIM_GROUND_TRUTH" && -n "$STATE_GROUND_TRUTH" ]]; then
        if [ -f "$STATE_GROUND_TRUTH" ]; then
            SIM_GROUND_TRUTH="$STATE_GROUND_TRUTH"
            echo -e "${CYAN}Auto-detected ground truth CSV (${SIM_GROUND_TRUTH}).${NC}"
        else
            echo -e "${YELLOW}⚠️  Ground truth CSV from state file missing: ${STATE_GROUND_TRUTH}.${NC}"
        fi
    fi
}

start_simulator_for_pcap() {
    ACTIVE_SIM_PID=""
    if [[ $SIMULATE_ML -ne 1 ]]; then
        return 0
    fi

    local pcap_path="$1"
    local abs_pcap
    abs_pcap=$(realpath "$pcap_path")

    if [ ! -f "$SIM_SCRIPT" ]; then
        echo -e "${YELLOW}⚠️  Simulator not found at ${SIM_SCRIPT}. Skipping simulation.${NC}"
        return 0
    fi

    local timeline_hint="$SIM_TIMELINE_SECONDS"
    if [[ -z "$timeline_hint" ]]; then
        local pcap_size
        pcap_size=$(stat -c%s "$abs_pcap" 2>/dev/null || echo 0)
        if [[ "$pcap_size" -gt 0 && -n "$REPLAY_SPEED" ]]; then
            timeline_hint=$(python3 - "$pcap_size" "$REPLAY_SPEED" "$SIM_STARTUP_DELAY" <<'PY'
import sys
size = float(sys.argv[1])
speed = float(sys.argv[2] or 0)
startup = float(sys.argv[3] or 0)
if speed <= 0:
    print("")
else:
    runtime = (size * 8.0) / (speed * 1_000_000.0)
    runtime = runtime * 1.05 + max(startup, 0.0)
    print(f"{runtime:.3f}")
PY
)
        fi
    fi

    local args=("--pcap" "$abs_pcap" "--mode" "$SIM_MODE" "--accuracy" "$SIM_ACCURACY" "--realtime" "--speed-factor" "$SIM_SPEED_FACTOR" "--startup-delay" "$SIM_STARTUP_DELAY" "--require-tcpreplay")
    if [[ -n "$timeline_hint" ]]; then
        args+=("--timeline-seconds" "$timeline_hint")
    fi
    if [ -n "$SIM_GROUND_TRUTH" ]; then
        if [ ! -f "$SIM_GROUND_TRUTH" ]; then
            echo -e "${YELLOW}⚠️  Ground-truth CSV not found: $SIM_GROUND_TRUTH. Continuing without it.${NC}"
        else
            args+=("--ground-truth-csv" "$(realpath "$SIM_GROUND_TRUTH")")
        fi
    fi

    python3 "$SIM_SCRIPT" "${args[@]}" &
    ACTIVE_SIM_PID=$!
}

wait_for_simulator() {
    [[ -n "$ACTIVE_SIM_PID" ]] || return 0
    if ! wait "$ACTIVE_SIM_PID"; then
        local rc=$?
        ACTIVE_SIM_PID=""
        return $rc
    fi
    ACTIVE_SIM_PID=""
    return 0
}

cancel_active_simulator() {
    [[ -n "$ACTIVE_SIM_PID" ]] || return 0
    kill "$ACTIVE_SIM_PID" >/dev/null 2>&1 || true
    wait "$ACTIVE_SIM_PID" >/dev/null 2>&1 || true
    ACTIVE_SIM_PID=""
}

replay_with_simulation() {
    local pcap_path="$1"
    start_simulator_for_pcap "$pcap_path"

    if ! run_tcpreplay "$pcap_path"; then
        cancel_active_simulator
        return 1
    fi

    if ! wait_for_simulator; then
        echo -e "${YELLOW}⚠️  Simulator reported an error for $(basename "$pcap_path").${NC}"
        return 1
    fi
    return 0
}

run_tcpreplay() {
    local pcap_path="$1"
    echo -e "\n${CYAN}Sending: $(basename "$pcap_path")${NC}"
    echo -e "Interface: ${REALTEK_NIC}"
    echo -e "Speed: ${REPLAY_SPEED} Mbps\n"

    if ! sudo tcpreplay --intf1="$REALTEK_NIC" --mbps="$REPLAY_SPEED" "$pcap_path"; then
        echo -e "${RED}❌ tcpreplay failed for $(basename "$pcap_path")${NC}"
        return 1
    fi
    return 0
}

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}Sending Test Traffic to IDS${NC}\n"

if [[ $SIM_DAEMON_ACTIVE -eq 1 ]]; then
    echo -e "${CYAN}tcpreplay simulation daemon detected; ML logs/metrics will stream automatically.${NC}\n"
fi

validate_mode
ensure_pipeline_ready
resolve_simulation_mode

if [ ! -d "$PCAP_DIR" ]; then
    echo -e "${YELLOW}⚠️  PCAP directory not found${NC}"
    exit 1
fi

if ! command -v tcpreplay &> /dev/null; then
    echo -e "${YELLOW}⚠️  tcpreplay not installed${NC}"
    echo "Install: sudo apt install tcpreplay"
    exit 1
fi

if [ -n "$CUSTOM_PCAP" ]; then
    if [ ! -f "$CUSTOM_PCAP" ]; then
        echo -e "${YELLOW}⚠️  Provided PCAP not found: $CUSTOM_PCAP${NC}"
        exit 1
    fi
    if ! replay_with_simulation "$CUSTOM_PCAP"; then
        echo -e "${RED}❌ Unable to send traffic${NC}"
        exit 1
    fi
    echo -e "\n${GREEN}✓ Traffic sent successfully${NC}"
    echo -e "${CYAN}Check IDS logs:${NC} tail -f logs/feature_engine.log"
    exit 0
fi

echo -e "${BOLD}Available PCAP files:${NC}"
ls -lh "$PCAP_DIR"/*.pcap | awk '{print "  " $9 " (" $5 ")"}'
if [ -f "$WEDNESDAY_FIXED_PCAP" ]; then
    ls -lh "$WEDNESDAY_FIXED_PCAP" | awk '{print "  " $9 " (" $5 ")"}'
fi
echo ""

echo -e "${BOLD}Select traffic type:${NC}"
echo "  1) Normal traffic (26KB)"
echo "  2) DoS attack (2.8MB)"
echo "  3) Mixed traffic (8.2MB)"
if [ -f "$WEDNESDAY_FIXED_PCAP" ]; then
    echo "  4) CICIDS Wednesday-fixed.pcap (~1.3GB)"
    echo "  5) All files in sequence"
else
    echo "  4) All files in sequence"
fi
echo ""
if [ -f "$WEDNESDAY_FIXED_PCAP" ]; then
    read -p "Choice [1-5]: " choice
else
    read -p "Choice [1-4]: " choice
fi

case $choice in
    1)
        PCAP="$PCAP_DIR/normal_traffic.pcap"
        replay_with_simulation "$PCAP" || exit 1
        ;;
    2)
        PCAP="$PCAP_DIR/dos_traffic_sample.pcap"
        replay_with_simulation "$PCAP" || exit 1
        ;;
    3)
        PCAP="$PCAP_DIR/mixed_traffic_sample.pcap"
        replay_with_simulation "$PCAP" || exit 1
        ;;
    4)
        if [ -f "$WEDNESDAY_FIXED_PCAP" ]; then
            replay_with_simulation "$WEDNESDAY_FIXED_PCAP" || exit 1
        else
            echo -e "\n${CYAN}Sending all PCAP files...${NC}\n"
            for pcap in "$PCAP_DIR"/*.pcap; do
                echo -e "${GREEN}→ Sending $(basename "$pcap")${NC}"
                replay_with_simulation "$pcap" || exit 1
                echo ""
                sleep 2
            done
            echo -e "${GREEN}✓ All files sent${NC}"
        fi
        ;;
    5)
        if [ -f "$WEDNESDAY_FIXED_PCAP" ]; then
            echo -e "\n${CYAN}Sending all PCAP files...${NC}\n"
            for pcap in "$PCAP_DIR"/*.pcap "$WEDNESDAY_FIXED_PCAP"; do
                echo -e "${GREEN}→ Sending $(basename "$pcap")${NC}"
                replay_with_simulation "$pcap" || exit 1
                echo ""
                sleep 2
            done
            echo -e "${GREEN}✓ All files sent${NC}"
        else
            echo "Invalid choice"
            exit 1
        fi
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo -e "${GREEN}✓ Traffic sent successfully${NC}"
echo -e "${CYAN}Check IDS logs:${NC} tail -f logs/feature_engine.log"
