#!/bin/bash

# Visual System Architecture Display
# Shows exactly how packets flow through your IDS pipeline

echo "🔍 IDS PIPELINE ARCHITECTURE - Real-time Packet Flow"
echo "===================================================="
echo ""

echo "📦 PACKET SOURCES"
echo "├── Physical Interface: enp2s0"
echo "├── Test Traffic: curl, nslookup, ping"
echo "├── DPDK Generators: packet_generator.py (future)"
echo "└── Normal OS Traffic: updates, browsing, etc."
echo ""

echo "🔄 PACKET CAPTURE & PROCESSING"
echo "┌─────────────────────────────────────────┐"
echo "│  STEP 1: Network Interface (enp2s0)    │"
echo "│  ├── Receives all network packets       │"
echo "│  ├── Current: AF_PACKET mode            │"
echo "│  └── Future: DPDK mode (10x faster)    │"
echo "└─────────────────────────────────────────┘"
echo "                    │"
echo "                    ▼"
echo "┌─────────────────────────────────────────┐"
echo "│  STEP 2: Suricata IDS Engine           │"
echo "│  ├── Deep Packet Inspection            │"
echo "│  ├── Rule-based Detection              │"
echo "│  ├── Protocol Analysis                 │"
echo "│  └── Event Generation                  │"
echo "└─────────────────────────────────────────┘"
echo "                    │"
echo "                    ▼"
echo "┌─────────────────────────────────────────┐"
echo "│  STEP 3: EVE.json Logging              │"
echo "│  ├── /var/log/suricata/eve.json        │"
echo "│  ├── Structured JSON events            │"
echo "│  ├── Real-time append                  │"
echo "│  └── Event types: alert/flow/http/dns  │"
echo "└─────────────────────────────────────────┘"
echo "                    │"
echo "                    ▼"
echo "┌─────────────────────────────────────────┐"
echo "│  STEP 4: EVE-Kafka Bridge              │"
echo "│  ├── File monitoring (watchdog)        │"
echo "│  ├── Real-time JSON parsing            │"
echo "│  ├── Event type classification         │"
echo "│  └── Kafka topic routing               │"
echo "└─────────────────────────────────────────┘"
echo "                    │"
echo "                    ▼"
echo "┌─────────────────────────────────────────┐"
echo "│  STEP 5: Kafka Topics                  │"
echo "│  ├── suricata-events: General events   │"
echo "│  ├── suricata-alerts: Security alerts  │"
echo "│  ├── suricata-stats: Performance data  │"
echo "│  └── Compression: gzip                 │"
echo "└─────────────────────────────────────────┘"
echo "                    │"
echo "                    ▼"
echo "┌─────────────────────────────────────────┐"
echo "│  STEP 6: Event Consumers               │"
echo "│  ├── kafka_consumer.py                 │"
echo "│  ├── kafka_monitor.py                  │"
echo "│  ├── SIEM integrations                 │"
echo "│  └── ML/AI analysis engines            │"
echo "└─────────────────────────────────────────┘"
echo ""

echo "📊 CURRENT SYSTEM STATUS"
echo "========================"

# Check if Suricata is running
if systemctl is-active --quiet suricata-simple; then
    echo "✅ Suricata: RUNNING (monitoring enp2s0)"
else
    echo "❌ Suricata: STOPPED"
fi

# Check if bridge is running
if pgrep -f "eve_kafka_bridge.py" > /dev/null; then
    echo "✅ EVE-Kafka Bridge: RUNNING"
else
    echo "❌ EVE-Kafka Bridge: STOPPED"
fi

# Check Kafka topics
echo "✅ Kafka Topics:"
/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null | grep suricata | while read topic; do
    echo "   └── $topic"
done

echo ""
echo "🔧 HOW TO GENERATE TEST TRAFFIC"
echo "==============================="
echo "1. Web requests:    curl -s http://www.google.com"
echo "2. DNS queries:     nslookup google.com"
echo "3. Port scans:      nmap -p 80,443 8.8.8.8"
echo "4. Bulk testing:    ./generate_test_traffic.sh"
echo "5. DPDK generator:  python3 DPDK_Packet_Testing/packet_generator.py"
echo ""

echo "🎯 HOW TO MONITOR EVENTS"
echo "========================"
echo "1. Real-time consumer:  python3 kafka_consumer.py"
echo "2. Topic monitor:       python3 kafka_monitor.py"
echo "3. EVE.json direct:     tail -f /var/log/suricata/eve.json"
echo "4. Suricata stats:      tail -f /var/log/suricata/suricata.log"
echo ""

echo "📈 RECENT ACTIVITY"
echo "=================="
if [ -f "/var/log/suricata/eve.json" ]; then
    echo "EVE.json entries (last 5):"
    tail -5 /var/log/suricata/eve.json | jq -r '.timestamp + " | " + .event_type + " | " + (.src_ip // "N/A") + " -> " + (.dest_ip // "N/A")' 2>/dev/null || tail -5 /var/log/suricata/eve.json | head -c 200
    echo "..."
else
    echo "❌ No EVE.json file found"
fi

echo ""
echo "🚀 NEXT STEPS FOR HIGH PERFORMANCE"
echo "=================================="
echo "1. Enable DPDK in Suricata for kernel bypass"
echo "2. Compile Suricata with native Kafka support"
echo "3. Configure DPDK packet generators"
echo "4. Add hardware-accelerated packet capture"
echo "5. Integrate with machine learning pipelines"
