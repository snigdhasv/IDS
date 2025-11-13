#!/bin/bash
################################################################################
# Send Test Traffic to IDS
################################################################################
# Sends PCAP traffic from Realtek NIC to Intel NIC for IDS testing
################################################################################

REALTEK_NIC="enp5s0"
PCAP_DIR="dpdk_suricata_ml_pipeline/pcap_samples"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}Sending Test Traffic to IDS${NC}\n"

if [ ! -d "$PCAP_DIR" ]; then
    echo -e "${YELLOW}⚠️  PCAP directory not found${NC}"
    exit 1
fi

if ! command -v tcpreplay &> /dev/null; then
    echo -e "${YELLOW}⚠️  tcpreplay not installed${NC}"
    echo "Install: sudo apt install tcpreplay"
    exit 1
fi

echo -e "${BOLD}Available PCAP files:${NC}"
ls -lh "$PCAP_DIR"/*.pcap | awk '{print "  " $9 " (" $5 ")"}'
echo ""

echo -e "${BOLD}Select traffic type:${NC}"
echo "  1) Normal traffic (26KB)"
echo "  2) DoS attack (2.8MB)"
echo "  3) Mixed traffic (8.2MB)"
echo "  4) All files in sequence"
echo ""
read -p "Choice [1-4]: " choice

case $choice in
    1)
        PCAP="$PCAP_DIR/normal_traffic.pcap"
        ;;
    2)
        PCAP="$PCAP_DIR/dos_traffic_sample.pcap"
        ;;
    3)
        PCAP="$PCAP_DIR/mixed_traffic_sample.pcap"
        ;;
    4)
        echo -e "\n${CYAN}Sending all PCAP files...${NC}\n"
        for pcap in "$PCAP_DIR"/*.pcap; do
            echo -e "${GREEN}→ Sending $(basename $pcap)${NC}"
            sudo tcpreplay --intf1=$REALTEK_NIC --mbps=10 "$pcap"
            echo ""
            sleep 2
        done
        echo -e "${GREEN}✓ All files sent${NC}"
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo -e "\n${CYAN}Sending: $(basename $PCAP)${NC}"
echo -e "Interface: ${REALTEK_NIC}"
echo -e "Speed: 10 Mbps\n"

sudo tcpreplay --intf1=$REALTEK_NIC --mbps=10 "$PCAP"

echo -e "\n${GREEN}✓ Traffic sent successfully${NC}"
echo -e "${CYAN}Check IDS logs:${NC} tail -f logs/feature_engine.log"
