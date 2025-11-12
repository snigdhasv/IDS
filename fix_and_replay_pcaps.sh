#!/bin/bash
#
# PCAP Fix and Replay Script for CICIDS2017 Dataset
# This script uses tcprewrite to truncate oversized packets before replay
#

PCAP_DIR="/home/ifscr/Downloads"
FIXED_PCAP_DIR="/home/ifscr/Downloads/fixed_pcaps"
REPLAY_INTERFACE="enp5s0"  # Changed from enp3s0 - this is directly connected to Intel NIC
REPLAY_SPEED="100"  # Mbps
MAX_MTU="1500"

echo "=========================================="
echo "CICIDS2017 PCAP Fix & Replay Script"
echo "=========================================="
echo "Source Directory: $PCAP_DIR"
echo "Fixed PCAP Directory: $FIXED_PCAP_DIR"
echo "Interface: $REPLAY_INTERFACE"
echo "Speed: ${REPLAY_SPEED} Mbps"
echo "Max MTU: ${MAX_MTU} bytes"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo)"
    exit 1
fi

# Create directory for fixed PCAPs
mkdir -p "$FIXED_PCAP_DIR"

# Process and replay each PCAP file
for pcap_file in "$PCAP_DIR"/*WorkingHours.pcap; do
    if [ -f "$pcap_file" ]; then
        filename=$(basename "$pcap_file")
        fixed_file="$FIXED_PCAP_DIR/fixed_${filename}"
        
        echo "=========================================="
        echo "Processing: $filename"
        echo "=========================================="
        
        # Check if fixed version already exists
        if [ -f "$fixed_file" ]; then
            echo "Fixed version already exists: $fixed_file"
            echo "Skipping tcprewrite..."
        else
            echo "Fixing oversized packets with tcprewrite..."
            echo "This may take a while for large files..."
            
            # Use tcprewrite to truncate packets to MTU size
            tcprewrite --mtu=$MAX_MTU --mtu-trunc --infile="$pcap_file" --outfile="$fixed_file"
            
            if [ $? -eq 0 ]; then
                echo "✓ Successfully created: $fixed_file"
            else
                echo "✗ Failed to create fixed PCAP. Skipping replay."
                continue
            fi
        fi
        
        echo ""
        echo "Replaying: $filename"
        echo "Started at: $(date)"
        echo "----------------------------------------"
        
        # Replay the fixed PCAP
        tcpreplay --intf1="$REPLAY_INTERFACE" --mbps="$REPLAY_SPEED" "$fixed_file"
        
        exit_code=$?
        echo ""
        echo "Finished: $filename"
        echo "Exit code: $exit_code"
        echo "Completed at: $(date)"
        echo ""
        
        # Brief pause between files
        sleep 2
    fi
done

echo "=========================================="
echo "All PCAP files processed and replayed!"
echo "=========================================="
echo "Fixed PCAPs are stored in: $FIXED_PCAP_DIR"
