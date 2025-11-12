#!/bin/bash
# Start AF_PACKET Feature Engine with correct interface

cd /home/ifscr/SE_02_2025/IDS/dpdk_suricata_ml_pipeline/src

echo "🚀 Starting AF_PACKET Feature Engine (enp2s0)..."
echo ""

# Source venv and run
source /home/ifscr/SE_02_2025/IDS/venv/bin/activate
python3 -u realtime_feature_engine.py -i enp2s0 --timeout 10
