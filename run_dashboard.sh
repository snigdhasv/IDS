#!/bin/bash
#
# Launch IDS Traffic Monitoring Dashboard
#
# This script starts the Streamlit web dashboard for monitoring
# IDS pipeline metrics in real-time.
#
# Usage:
#   ./run_dashboard.sh                    # Default metrics directory
#   ./run_dashboard.sh /path/to/metrics   # Custom metrics directory
#

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           IDS Traffic Monitoring Dashboard                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if dashboard.py exists
if [ ! -f "dashboard.py" ]; then
    echo -e "${RED}✗ dashboard.py not found in current directory${NC}"
    exit 1
fi

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo -e "${YELLOW}⚠️  Streamlit not found${NC}"
    echo -e "${BLUE}Installing required packages...${NC}"
    echo ""
    
    # Try to install from requirements.txt
    if [ -f "requirements.txt" ]; then
        echo -e "${BLUE}Installing from requirements.txt...${NC}"
        pip3 install streamlit plotly pandas || {
            echo -e "${RED}✗ Failed to install packages${NC}"
            echo -e "${YELLOW}Please install manually: pip3 install streamlit plotly pandas${NC}"
            exit 1
        }
    else
        echo -e "${BLUE}Installing streamlit, plotly, and pandas...${NC}"
        pip3 install streamlit plotly pandas || {
            echo -e "${RED}✗ Failed to install packages${NC}"
            exit 1
        }
    fi
    
    echo -e "${GREEN}✓ Packages installed successfully${NC}"
    echo ""
fi

# Check metrics directory
METRICS_DIR="${1:-logs/metrics}"

if [ ! -d "$METRICS_DIR" ]; then
    echo -e "${YELLOW}⚠️  Metrics directory not found: $METRICS_DIR${NC}"
    echo -e "${YELLOW}Creating directory...${NC}"
    mkdir -p "$METRICS_DIR"
fi

echo -e "${GREEN}✓ Streamlit found${NC}"
echo -e "${GREEN}✓ Dashboard ready${NC}"
echo ""

# Get today's metrics file
TODAY=$(date +%Y%m%d)
METRICS_FILE="$METRICS_DIR/metrics_${TODAY}.jsonl"

if [ ! -f "$METRICS_FILE" ]; then
    echo -e "${YELLOW}⚠️  No metrics file found: $METRICS_FILE${NC}"
    echo -e "${YELLOW}    Metrics will appear once the IDS pipeline is running.${NC}"
    echo ""
    echo -e "${BLUE}To start the IDS pipeline:${NC}"
    echo -e "  Terminal 1: ${GREEN}sudo ./run_afpacket_mode.sh${NC}  # or ./run_dpdk_mode.sh"
    echo -e "  Terminal 2: ${GREEN}./run_dashboard.sh${NC}"
    echo ""
    read -p "Launch dashboard anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
else
    FILE_SIZE=$(du -h "$METRICS_FILE" | cut -f1)
    LINE_COUNT=$(wc -l < "$METRICS_FILE")
    echo -e "${GREEN}✓ Metrics file found: $METRICS_FILE${NC}"
    echo -e "${BLUE}  Size: $FILE_SIZE | Lines: $LINE_COUNT${NC}"
    echo ""
fi

# Launch dashboard
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   Starting Dashboard                          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}🚀 Launching Streamlit dashboard...${NC}"
echo -e "${BLUE}📊 Monitoring: $METRICS_DIR${NC}"
echo -e "${BLUE}🌐 Dashboard will open in your browser${NC}"
echo ""
echo -e "${YELLOW}Note: Press Ctrl+C to stop the dashboard${NC}"
echo ""

sleep 2

# Launch streamlit with custom metrics directory if provided
if [ "$1" != "" ]; then
    streamlit run dashboard.py -- --metrics-dir "$METRICS_DIR"
else
    streamlit run dashboard.py
fi
