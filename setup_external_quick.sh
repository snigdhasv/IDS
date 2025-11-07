#!/bin/bash
# Quick External Device Setup - IDS Device
# Run this script on your IDS system to configure the USB adapter

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   IDS DEVICE - EXTERNAL CAPTURE QUICK SETUP                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo

# Step 1: Configure USB adapter
echo "📡 Step 1: Configuring USB Ethernet adapter..."
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
sudo bash 00_setup_external_capture.sh

echo
echo "✓ Interface configured: enx00e04c36074c → 192.168.100.1/24"
echo

# Step 2: Start monitoring in background
echo "👁️  Step 2: Starting packet monitor (Ctrl+C to stop)..."
echo "   Press Ctrl+C after you verify packets are captured..."
echo
sudo tcpdump -i enx00e04c36074c -n -c 20

echo
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   SETUP COMPLETE - NEXT STEPS                              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo
echo "1. 🔌 Connect Ethernet cable to external device"
echo
echo "2. 🖥️  On EXTERNAL device, run:"
echo "   sudo ip link set eth0 up"
echo "   sudo ip addr add 192.168.100.2/24 dev eth0"
echo "   ping 192.168.100.1"
echo
echo "3. 🚀 Start IDS pipeline:"
echo "   cd /home/sujay/Programming/IDS"
echo "   sudo ./run_afpacket_mode.sh"
echo "   (Select option 1 - Start All)"
echo
echo "4. 📊 Monitor with dashboard:"
echo "   cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline"
echo "   python3 scripts/metrics_dashboard.py"
echo
echo "5. 📦 On EXTERNAL device, replay traffic:"
echo "   sudo tcpreplay -i eth0 --mbps 10 capture.pcap"
echo
echo "📖 Full guide: EXTERNAL_DEVICE_SETUP_GUIDE.md"
