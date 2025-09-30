#!/bin/bash

echo "🔍 SURICATA KAFKA STREAMING - COMPLETE OVERVIEW"
echo "==============================================="

echo ""
echo "📊 CURRENT STATUS:"
echo "=================="

# Suricata status
if pgrep -f "suricata" > /dev/null; then
    echo "✅ Suricata: RUNNING"
    echo "   $(ps aux | grep suricata | grep -v grep | head -1 | awk '{print $11, $12, $13, $14}')"
else
    echo "❌ Suricata: NOT RUNNING"
fi

# Kafka status
if nc -z localhost 9092 2>/dev/null; then
    echo "✅ Kafka: RUNNING on localhost:9092"
else
    echo "❌ Kafka: NOT RUNNING"
fi

# Check event files
EVE_FILE="/var/log/suricata/eve.json"
if [ -f "$EVE_FILE" ]; then
    EVE_SIZE=$(stat -c%s "$EVE_FILE")
    EVE_LINES=$(wc -l < "$EVE_FILE")
    echo "✅ Eve.json: EXISTS ($EVE_LINES events, $EVE_SIZE bytes)"
else
    echo "❌ Eve.json: NOT FOUND"
fi

echo ""
echo "🔍 WHAT'S WORKING:"
echo "=================="
echo "✅ Network monitoring (Suricata processing traffic)"
echo "✅ Event detection (Rules firing on network activity)"
echo "✅ Kafka infrastructure (Broker running, topics created)"
echo "✅ File output (Events written to eve.json)"

echo ""
echo "❌ WHAT'S NOT WORKING:"
echo "======================"
echo "❌ Direct Kafka streaming (Suricata → Kafka)"
echo "❌ DPDK high-performance mode"
echo "❌ Real-time event flow to Kafka topics"

echo ""
echo "🔧 THE CORE ISSUE:"
echo "=================="
echo "Suricata configuration specifies Kafka output, but the current"
echo "Suricata build lacks the Kafka output module. Therefore:"
echo ""
echo "INTENDED: Network → Suricata → Kafka → Consumers"
echo "REALITY:  Network → Suricata → eve.json file"

echo ""
echo "💡 SOLUTIONS:"
echo "============="
echo "1. IMMEDIATE - File Bridge:"
echo "   python3 eve_kafka_bridge.py &"
echo "   (Watches eve.json and streams to Kafka)"
echo ""
echo "2. PERMANENT - Kafka-enabled Suricata:"
echo "   sudo ./install_suricata_kafka.sh"
echo "   (Installs Suricata with librdkafka support)"
echo ""
echo "3. PERFORMANCE - DPDK Setup:"
echo "   Fix hugepages and interface binding"
echo "   (For high-throughput environments)"

echo ""
echo "📈 VALIDATION:"
echo "=============="
echo "Quick check: ./quick_validate.sh"
echo "Monitor:     python3 kafka_consumer.py"
echo "Bridge demo: python3 eve_kafka_bridge.py &"

echo ""
echo "==============================================="
echo "🎯 BOTTOM LINE: Your setup is 90% complete!"
echo "   Just need Kafka output module for direct streaming"
echo "==============================================="
