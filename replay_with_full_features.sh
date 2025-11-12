#!/bin/bash
#
# PCAP Replay with Full Feature Extraction
# Uses enp5s0 (replay NIC) for both sending AND capturing
# This allows AF_PACKET feature extraction with all CICIDS65 features
#

PCAP_FILE="/home/ifscr/Downloads/Wednesday-fixed.pcap"
REPLAY_INTERFACE="enp5s0"
CAPTURE_INTERFACE="enp5s0"  # Same NIC - capture what we're sending
REPLAY_SPEED="100"
IDS_DIR="/home/ifscr/SE_02_2025/IDS"

echo "=========================================="
echo "🚀 PCAP Replay with Full Feature Extraction"
echo "=========================================="
echo ""
echo "Strategy: Use enp5s0 for BOTH replay and capture"
echo "  - tcpreplay sends from enp5s0"
echo "  - AF_PACKET feature engine captures on enp5s0"
echo "  - Extracts all CICIDS65 features"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (sudo)"
    exit 1
fi

# Step 1: Start Kafka
echo "Step 1: Starting Kafka..."
echo "=========================================="
if ! netstat -tuln 2>/dev/null | grep -q ":9092"; then
    cd "$IDS_DIR"
    if [ -f "dpdk_suricata_ml_pipeline/scripts/02_setup_kafka.sh" ]; then
        bash dpdk_suricata_ml_pipeline/scripts/02_setup_kafka.sh
        sleep 5
    else
        echo "⚠️  Kafka setup script not found. Make sure Kafka is running manually."
    fi
fi

if netstat -tuln 2>/dev/null | grep -q ":9092"; then
    echo "✅ Kafka is running on port 9092"
else
    echo "❌ Kafka is not running. Start it manually."
    exit 1
fi
echo ""

# Step 2: Start Feature Engine on enp5s0
echo "Step 2: Starting Feature Engine..."
echo "=========================================="
cd "$IDS_DIR/dpdk_suricata_ml_pipeline/src"
source "$IDS_DIR/venv/bin/activate"

# Kill any existing feature engine
pkill -f "realtime_feature_engine.py" 2>/dev/null

# Start feature engine in background
python3 -u realtime_feature_engine.py -i "$CAPTURE_INTERFACE" --timeout 10 \
    > "$IDS_DIR/logs/feature_engine.log" 2>&1 &
FEATURE_PID=$!

sleep 3

if kill -0 $FEATURE_PID 2>/dev/null; then
    echo "✅ Feature Engine started (PID: $FEATURE_PID)"
    echo "   Interface: $CAPTURE_INTERFACE"
    echo "   Log: $IDS_DIR/logs/feature_engine.log"
else
    echo "❌ Feature Engine failed to start"
    exit 1
fi
echo ""

# Step 3: Start ML Consumer
echo "Step 3: Starting ML Consumer..."
echo "=========================================="

# Kill any existing ML consumer
pkill -f "realtime_ensemble_consumer" 2>/dev/null

python3 -u realtime_ensemble_consumer_with_csv.py \
    > "$IDS_DIR/logs/ml_consumer.log" 2>&1 &
ML_PID=$!

sleep 3

if kill -0 $ML_PID 2>/dev/null; then
    echo "✅ ML Consumer started (PID: $ML_PID)"
    echo "   Log: $IDS_DIR/logs/ml_consumer.log"
else
    echo "⚠️  ML Consumer failed (may need models)"
fi
echo ""

deactivate
cd "$IDS_DIR"

# Step 4: Replay PCAP
echo "Step 4: Starting PCAP Replay..."
echo "=========================================="
echo "PCAP: $PCAP_FILE"
echo "Interface: $REPLAY_INTERFACE"
echo "Speed: ${REPLAY_SPEED} Mbps"
echo ""
read -p "Press ENTER to start replay..."

echo ""
echo "🎬 Replay started at: $(date)"
echo ""

# Run replay
tcpreplay --intf1="$REPLAY_INTERFACE" --mbps="$REPLAY_SPEED" --stats=30 "$PCAP_FILE"

REPLAY_EXIT=$?

echo ""
echo "✅ Replay Complete!"
echo "=========================================="
echo "Finished at: $(date)"
echo "Exit code: $REPLAY_EXIT"
echo ""

# Give feature engine time to process last packets
echo "⏳ Waiting 30 seconds for feature processing..."
sleep 30

# Step 5: Show Results
echo ""
echo "📊 Results"
echo "=========================================="
echo ""

echo "Feature Engine Log (last 20 lines):"
tail -20 "$IDS_DIR/logs/feature_engine.log"
echo ""

if [ -f "$IDS_DIR/logs/ml_consumer.log" ]; then
    echo "ML Consumer Log (last 20 lines):"
    tail -20 "$IDS_DIR/logs/ml_consumer.log"
    echo ""
fi

if [ -f "$IDS_DIR/logs/ml_predictions.csv" ]; then
    echo "ML Predictions (last 10):"
    tail -10 "$IDS_DIR/logs/ml_predictions.csv"
    echo ""
    
    echo "Prediction Summary:"
    cut -d',' -f2 "$IDS_DIR/logs/ml_predictions.csv" | tail -n +2 | sort | uniq -c
    echo ""
fi

# Step 6: Cleanup
echo "📋 Cleanup"
echo "=========================================="
read -p "Stop Feature Engine and ML Consumer? [y/N]: " stop_choice

if [[ $stop_choice =~ ^[Yy]$ ]]; then
    kill $FEATURE_PID 2>/dev/null && echo "✓ Feature Engine stopped"
    kill $ML_PID 2>/dev/null && echo "✓ ML Consumer stopped"
fi

echo ""
echo "🎉 Complete!"
echo ""
echo "Full logs available at:"
echo "  - Feature Engine: $IDS_DIR/logs/feature_engine.log"
echo "  - ML Consumer: $IDS_DIR/logs/ml_consumer.log"
echo "  - Predictions CSV: $IDS_DIR/logs/ml_predictions.csv"
echo ""
