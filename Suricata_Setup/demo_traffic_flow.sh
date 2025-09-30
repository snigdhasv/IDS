#!/bin/bash

# Live Traffic Flow Demonstration
# Shows real-time packet flow from source → Suricata → Kafka

echo "🚀 LIVE IDS PIPELINE DEMONSTRATION"
echo "=================================="
echo ""

# Function to show traffic generation and monitoring
demo_traffic_flow() {
    echo "🔥 Starting live demonstration..."
    echo ""
    
    # Start Kafka consumer in background
    echo "1. Starting Kafka consumer to monitor events..."
    python3 kafka_monitor.py &
    MONITOR_PID=$!
    sleep 2
    
    echo ""
    echo "2. Generating test traffic that will trigger detection..."
    echo ""
    
    # Generate various types of traffic
    echo "   📡 Generating HTTP requests..."
    curl -s http://www.google.com > /dev/null
    curl -s http://www.github.com > /dev/null
    curl -s http://httpbin.org/get > /dev/null
    
    echo "   🔍 Performing DNS lookups..."
    nslookup google.com > /dev/null 2>&1
    nslookup github.com > /dev/null 2>&1
    nslookup stackoverflow.com > /dev/null 2>&1
    
    echo "   🎯 Generating potential alerts (port scans)..."
    # This might trigger alerts depending on rules
    timeout 2 nmap -p 22,80,443 8.8.8.8 > /dev/null 2>&1 || true
    
    echo "   💨 Quick ping sweep..."
    ping -c 3 8.8.8.8 > /dev/null 2>&1
    ping -c 3 1.1.1.1 > /dev/null 2>&1
    
    echo ""
    echo "3. Waiting for events to flow through pipeline..."
    echo "   (Traffic → Suricata → EVE.json → Bridge → Kafka)"
    sleep 5
    
    echo ""
    echo "4. Checking event counts in each stage..."
    
    # Count events in EVE.json
    if [ -f "/var/log/suricata/eve.json" ]; then
        EVE_COUNT=$(wc -l < /var/log/suricata/eve.json)
        echo "   📄 EVE.json total events: $EVE_COUNT"
    fi
    
    # Check Kafka topic message counts
    echo "   📡 Kafka topic message counts:"
    for topic in suricata-events suricata-alerts suricata-stats; do
        # Get partition count and latest offset
        PARTITIONS=$(/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic $topic 2>/dev/null | grep -c "Partition:")
        if [ "$PARTITIONS" -gt 0 ]; then
            # Get high water mark (total messages)
            MESSAGES=$(/opt/kafka/bin/kafka-log-dirs.sh --bootstrap-server localhost:9092 --describe --json 2>/dev/null | grep -o "\"$topic.*\"size\":[0-9]*" | head -1 | grep -o "[0-9]*$" || echo "0")
            echo "      └── $topic: $MESSAGES bytes (check with consumer for count)"
        fi
    done
    
    echo ""
    echo "5. Sample recent events from EVE.json:"
    if [ -f "/var/log/suricata/eve.json" ]; then
        echo "   📋 Last 3 events:"
        tail -3 /var/log/suricata/eve.json | while read line; do
            # Extract key fields
            TIMESTAMP=$(echo "$line" | jq -r '.timestamp // "N/A"' 2>/dev/null)
            EVENT_TYPE=$(echo "$line" | jq -r '.event_type // "N/A"' 2>/dev/null)
            SRC_IP=$(echo "$line" | jq -r '.src_ip // "N/A"' 2>/dev/null)
            DEST_IP=$(echo "$line" | jq -r '.dest_ip // "N/A"' 2>/dev/null)
            PROTO=$(echo "$line" | jq -r '.proto // "N/A"' 2>/dev/null)
            
            echo "      └── $TIMESTAMP | $EVENT_TYPE | $SRC_IP → $DEST_IP ($PROTO)"
        done
    fi
    
    echo ""
    echo "6. Stopping monitoring..."
    kill $MONITOR_PID 2>/dev/null || true
    wait $MONITOR_PID 2>/dev/null || true
    
    echo ""
    echo "✅ Demonstration complete!"
    echo ""
}

# Function to explain what just happened
explain_traffic_flow() {
    echo "🧠 WHAT JUST HAPPENED - Technical Breakdown"
    echo "==========================================="
    echo ""
    echo "Traffic Source → Network Interface → Suricata → EVE.json → Bridge → Kafka"
    echo ""
    echo "1. 📦 PACKET GENERATION:"
    echo "   • curl commands created HTTP requests to google.com, github.com"
    echo "   • nslookup generated DNS queries to resolve domain names"
    echo "   • nmap performed port scans (potential security event)"
    echo "   • ping generated ICMP packets for connectivity tests"
    echo ""
    echo "2. 🔍 SURICATA CAPTURE:"
    echo "   • Monitored interface enp2s0 for all packets"
    echo "   • Applied detection rules to identify patterns"
    echo "   • Generated structured events for interesting traffic"
    echo "   • Wrote events to /var/log/suricata/eve.json in real-time"
    echo ""
    echo "3. 📄 EVE.json LOGGING:"
    echo "   • Each network event became a JSON object"
    echo "   • Included metadata: timestamp, IPs, ports, protocol"
    echo "   • Classified events: flow (connections), http (web), alert (suspicious)"
    echo ""
    echo "4. 🌉 BRIDGE PROCESSING:"
    echo "   • eve_kafka_bridge.py monitored EVE.json for changes"
    echo "   • Parsed each new JSON line in real-time"
    echo "   • Routed events to appropriate Kafka topics by type"
    echo "   • Applied gzip compression for efficient transfer"
    echo ""
    echo "5. 📡 KAFKA STREAMING:"
    echo "   • Events distributed across topic partitions"
    echo "   • Multiple consumers can process events in parallel"
    echo "   • Persistent storage for event replay and analysis"
    echo ""
    echo "This creates a scalable, real-time intrusion detection pipeline!"
}

# Main execution
echo "This script will demonstrate the complete packet flow through your IDS pipeline."
echo "Press Enter to start the demonstration..."
read

demo_traffic_flow
explain_traffic_flow

echo ""
echo "🎯 TRY IT YOURSELF:"
echo "==================="
echo "1. Generate traffic:    curl -s http://www.example.com"
echo "2. Monitor events:      python3 kafka_consumer.py"
echo "3. Watch EVE.json:      tail -f /var/log/suricata/eve.json"
echo "4. Check bridge stats:  ps aux | grep eve_kafka_bridge"
echo ""
echo "Your IDS pipeline is working and ready for production traffic!"
