#!/bin/bash
#
# Complete PCAP Replay Test with DPDK
# This script sets up DPDK, starts testpmd, and replays a PCAP file
#

REPLAY_INTERFACE="enp5s0"  # Changed from enp3s0 - this is directly connected to Intel NIC
PCAP_FILE="/home/ifscr/Downloads/Wednesday-fixed.pcap"
REPLAY_SPEED="100"  # Mbps

echo "=========================================="
echo "Complete DPDK Replay Test Setup"
echo "=========================================="
echo "Replay NIC: $REPLAY_INTERFACE"
echo "PCAP File: $PCAP_FILE"
echo "Speed: ${REPLAY_SPEED} Mbps"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo)"
    exit 1
fi

# Step 1: Setup DPDK
echo "Step 1: Setting up DPDK..."
modprobe vfio
modprobe vfio-pci
ip link set enp1s0 down
dpdk-devbind.py --bind=vfio-pci 01:00.0

echo ""
echo "DPDK binding status:"
dpdk-devbind.py --status | head -15
echo ""

# Step 2: Instructions for testpmd
echo "=========================================="
echo "Step 2: Start testpmd in ANOTHER terminal"
echo "=========================================="
echo ""
echo "Run this command in a separate terminal:"
echo ""
echo "  sudo dpdk-testpmd -l 0-1 -n 4 -- -i --port-topology=chained"
echo ""
echo "Then in testpmd prompt, run:"
echo "  set promisc all on"
echo "  start"
echo ""
read -p "Press ENTER when testpmd is running and configured..."

# Step 3: Replay PCAP
echo ""
echo "=========================================="
echo "Step 3: Replaying PCAP file..."
echo "=========================================="
echo ""
echo "Starting replay at: $(date)"
echo ""

tcpreplay --intf1="$REPLAY_INTERFACE" --mbps="$REPLAY_SPEED" --stats=30 "$PCAP_FILE"

echo ""
echo "=========================================="
echo "Replay complete!"
echo "=========================================="
echo "Finished at: $(date)"
echo ""
echo "Check testpmd stats with: show port stats all"
echo ""
