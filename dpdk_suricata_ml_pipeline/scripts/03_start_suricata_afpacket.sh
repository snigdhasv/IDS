#!/bin/bash

# Start Suricata in AF_PACKET mode with Kafka output
# Works with ANY network interface including USB adapters!

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/pipeline.conf"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║  Suricata AF_PACKET Mode Start Script          ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo
#!/bin/bash
# Check root
echo "Suricata AF_PACKET mode is disabled—it is no longer used in this DPDK-only pipeline."
echo "Use the DPDK pipeline via run_realtime_engine_dpdk.sh and ensure enp1s0 is bound before starting."
exit 1
fi
