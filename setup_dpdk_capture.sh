#!/bin/bash
#
# DPDK Setup Script - Prepares Intel NIC for packet capture
# Run this before starting testpmd or your IDS
#

echo "=========================================="
echo "DPDK Capture Setup"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo)"
    exit 1
fi

# Load VFIO modules
echo "Loading VFIO kernel modules..."
modprobe vfio
modprobe vfio-pci

# Bring down the Intel NIC
echo "Taking down enp1s0..."
ip link set enp1s0 down

# Bind to DPDK
echo "Binding Intel 82599ES (01:00.0) to DPDK..."
dpdk-devbind.py --bind=vfio-pci 01:00.0

# Verify binding
echo ""
echo "Current NIC status:"
dpdk-devbind.py --status | head -20

echo ""
echo "=========================================="
echo "✓ DPDK setup complete!"
echo "=========================================="
echo ""
echo "You can now run:"
echo "  sudo dpdk-testpmd -l 0-1 -n 4 -- -i --port-topology=chained"
echo ""
echo "Or start your IDS with DPDK capture"
echo ""
