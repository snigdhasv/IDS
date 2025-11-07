#!/bin/bash
# Quick External Device Setup - EXTERNAL DEVICE
# Run this script on your SECOND device (the one sending traffic)

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   EXTERNAL DEVICE - QUICK SETUP                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo

# Detect network interfaces
echo "📡 Detecting network interfaces..."
INTERFACES=$(ip link show | grep -E '^[0-9]+:' | awk '{print $2}' | sed 's/:$//' | grep -v 'lo')

echo "Available interfaces:"
echo "$INTERFACES"
echo

# Prompt for interface
read -p "Enter interface name (e.g., eth0, enp3s0): " IFACE

if [ -z "$IFACE" ]; then
    echo "❌ No interface specified!"
    exit 1
fi

# Check if interface exists
if ! ip link show "$IFACE" > /dev/null 2>&1; then
    echo "❌ Interface $IFACE not found!"
    exit 1
fi

echo
echo "🔧 Configuring interface $IFACE..."

# Bring up interface
sudo ip link set "$IFACE" up
sleep 1

# Assign IP
sudo ip addr flush dev "$IFACE" 2>/dev/null || true
sudo ip addr add 192.168.100.2/24 dev "$IFACE"

echo "✓ Interface configured: $IFACE → 192.168.100.2/24"
echo

# Test connectivity
echo "🔍 Testing connectivity to IDS device..."
if ping -c 3 -W 2 192.168.100.1 > /dev/null 2>&1; then
    echo "✓ Connection successful! IDS device is reachable."
else
    echo "⚠️  Cannot reach IDS device (192.168.100.1)"
    echo "   Make sure:"
    echo "   1. Ethernet cable is connected"
    echo "   2. IDS device setup script has run"
    echo "   3. USB adapter is plugged in on IDS device"
fi

echo
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   SETUP COMPLETE - TRAFFIC GENERATION                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo
echo "📦 Install traffic tools (if not already installed):"
echo "   sudo apt install tcpreplay hping3 netcat-openbsd"
echo
echo "🧪 Test traffic generation:"
echo "   # Simple ping"
echo "   ping 192.168.100.1"
echo
echo "   # TCP SYN flood"
echo "   sudo hping3 -S 192.168.100.1 -p 80 -c 100"
echo
echo "   # PCAP replay (replace YOUR_FILE.pcap)"
echo "   sudo tcpreplay -i $IFACE --mbps 10 YOUR_FILE.pcap"
echo
echo "   # High-speed replay"
echo "   sudo tcpreplay -i $IFACE -t YOUR_FILE.pcap"
echo
echo "   # Loop replay"
echo "   sudo tcpreplay -i $IFACE --loop 10 YOUR_FILE.pcap"
echo
echo "📊 Monitor on IDS device:"
echo "   python3 scripts/metrics_dashboard.py"
