#!/bin/bash
echo "🚀 Starting Complete DPDK-IDS Pipeline..."

# Change to correct directory
cd /home/ifscr/SE_02_2025/IDS/Suricata_Setup

# Start Kafka (manual installation)
echo "📡 Starting Kafka..."
cd /home/ifscr/Downloads/kafka_2.13-3.9.1
./bin/zookeeper-server-start.sh -daemon config/zookeeper.properties
sleep 5
./bin/kafka-server-start.sh -daemon config/server.properties
sleep 10

# Setup Kafka topics
echo "📊 Setting up Kafka topics..."
cd /home/ifscr/SE_02_2025/IDS/Suricata_Setup
./setup_kafka.sh

# Start Suricata
echo "🔍 Starting Suricata..."
sudo systemctl start suricata-simple

# Start EVE-Kafka Bridge
echo "🌉 Starting EVE-Kafka Bridge..."
python3 eve_kafka_bridge.py &
BRIDGE_PID=$!
sleep 3

# Validate system
echo "✅ Validating pipeline..."
cd /home/ifscr/SE_02_2025/IDS
sudo python3 realtime_dpdk_pipeline.py --mode validate

echo "🎉 Pipeline startup complete!"
echo "Bridge PID: $BRIDGE_PID (use 'kill $BRIDGE_PID' to stop)"
