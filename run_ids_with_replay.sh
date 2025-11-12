#!/bin/bash
#
# Complete IDS Pipeline with PCAP Replay
# This script orchestrates PCAP replay with the full IDS pipeline
#

PCAP_FILE="/home/ifscr/Downloads/Wednesday-fixed.pcap"
REPLAY_INTERFACE="enp5s0"
REPLAY_SPEED="100"  # Mbps
IDS_DIR="/home/ifscr/SE_02_2025/IDS"

echo "=========================================="
echo "🚀 Complete IDS Pipeline with PCAP Replay"
echo "=========================================="
echo ""
echo "📋 Configuration:"
echo "  PCAP File: $PCAP_FILE"
echo "  Replay NIC: $REPLAY_INTERFACE"
echo "  Capture NIC: Intel 82599ES (DPDK)"
echo "  Replay Speed: ${REPLAY_SPEED} Mbps"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (sudo)"
    exit 1
fi

echo "Step 1: Setting up DPDK for packet capture..."
echo "=============================================="
modprobe vfio-pci
dpdk-devbind.py --bind=vfio-pci 01:00.0

echo ""
dpdk-devbind.py --status | head -15
echo ""

echo "Step 2: Starting the IDS Pipeline..."
echo "=============================================="
echo ""
echo "Choose IDS mode:"
echo "  1) Full DPDK Pipeline (run_realtime_engine_dpdk.sh)"
echo "  2) AF_PACKET Pipeline (run_realtime_engine.sh)"
echo "  3) Custom DPDK Feature Engine only"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "Starting DPDK Pipeline..."
        cd "$IDS_DIR"
        ./run_realtime_engine_dpdk.sh start
        ;;
    2)
        echo ""
        echo "Starting AF_PACKET Pipeline..."
        cd "$IDS_DIR"
        ./run_realtime_engine.sh start
        ;;
    3)
        echo ""
        echo "Starting Feature Engine only..."
        cd "$IDS_DIR/dpdk_suricata_ml_pipeline/src"
        source ../venv/bin/activate
        python3 dpdk_feature_engine.py &
        FEATURE_PID=$!
        echo "Feature Engine PID: $FEATURE_PID"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "Step 3: Verify IDS is ready..."
echo "=============================================="
echo "Wait 10 seconds for services to start..."
sleep 10

echo ""
echo "Step 4: Start PCAP Replay"
echo "=============================================="
read -p "Press ENTER to start replaying $PCAP_FILE..."

echo ""
echo "🎬 Starting replay..."
echo "Started at: $(date)"
echo ""

# Run the replay
tcpreplay --intf1="$REPLAY_INTERFACE" --mbps="$REPLAY_SPEED" --stats=30 "$PCAP_FILE"

REPLAY_EXIT=$?

echo ""
echo "✅ Replay Complete!"
echo "=============================================="
echo "Finished at: $(date)"
echo "Exit code: $REPLAY_EXIT"
echo ""

echo "📊 Checking IDS Results..."
echo "=============================================="
echo ""
echo "Check these logs for results:"
echo "  - Feature Engine: $IDS_DIR/logs/feature_engine.log"
echo "  - ML Consumer: $IDS_DIR/logs/ml_consumer.log"
echo "  - Suricata: /var/log/suricata/suricata.log"
echo ""
echo "Or use Kafka to see real-time output:"
echo "  kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic ml-predictions"
echo ""

read -p "Do you want to stop the IDS pipeline? [y/N]: " stop_choice
if [[ $stop_choice =~ ^[Yy]$ ]]; then
    echo ""
    echo "Stopping IDS..."
    case $choice in
        1)
            cd "$IDS_DIR"
            ./run_realtime_engine_dpdk.sh stop
            ;;
        2)
            cd "$IDS_DIR"
            ./run_realtime_engine.sh stop
            ;;
        3)
            kill $FEATURE_PID 2>/dev/null
            ;;
    esac
fi

echo ""
echo "🎉 Complete! Check the logs above for analysis results."
