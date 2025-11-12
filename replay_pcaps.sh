#!/bin/bash
#
# PCAP Replay Script for CICIDS2017 Dataset
# Replays traffic from Realtek NIC (enp3s0) to DPDK listener (enp1s0)
#

PCAP_DIR="/home/ifscr/Downloads"
REPLAY_INTERFACE="enp5s0"  # Changed from enp3s0 - this is directly connected to Intel NIC
REPLAY_SPEED="100"  # Mbps - adjust as needed
MTU_SIZE="1500"     # Maximum transmission unit

echo "=========================================="
echo "CICIDS2017 PCAP Replay Script"
echo "=========================================="
echo "Interface: $REPLAY_INTERFACE"
echo "Speed: ${REPLAY_SPEED} Mbps"
echo "MTU: ${MTU_SIZE} bytes"
echo "PCAP Directory: $PCAP_DIR"
echo ""

# Set MTU on the replay interface
echo "Setting MTU to $MTU_SIZE on $REPLAY_INTERFACE..."
ip link set dev $REPLAY_INTERFACE mtu $MTU_SIZE
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo)"
    exit 1
fi

# List available PCAP files
echo "Available PCAP files:"
ls -lh "$PCAP_DIR"/*.pcap
echo ""

# Replay each PCAP file
for pcap_file in "$PCAP_DIR"/*WorkingHours.pcap; do
    if [ -f "$pcap_file" ]; then
        filename=$(basename "$pcap_file")
        echo "=========================================="
        echo "Replaying: $filename"
        echo "Started at: $(date)"
        echo "=========================================="
        
        # Use --maxsleeptime to handle large files better
        # Packets larger than MTU will be skipped but replay continues
        tcpreplay --intf1="$REPLAY_INTERFACE" --mbps="$REPLAY_SPEED" --maxsleeptime=1000 "$pcap_file" 2>&1 | tee -a replay_output.log
        
        exit_code=$?
        echo ""
        echo "Finished: $filename"
        echo "Exit code: $exit_code"
        echo "Completed at: $(date)"
        
        # Show quick stats
        tail -5 replay_output.log
        echo ""
        
        # Brief pause between files
        sleep 2
    fi
done

echo "=========================================="
echo "All PCAP files replayed!"
echo "=========================================="
