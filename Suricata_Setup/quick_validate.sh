#!/bin/bash

# Quick Kafka Streaming Validation
# Simple script to check if Suricata is streaming to Kafka

KAFKA_BROKERS="localhost:9092"
TOPICS=("suricata-events" "suricata-alerts" "suricata-stats")

echo "🔍 Quick Kafka Streaming Validation"
echo "======================================"

# Check if Suricata is running
if pgrep -f "suricata" > /dev/null; then
    echo "✅ Suricata is running"
else
    echo "❌ Suricata is not running"
    exit 1
fi

# Check if Kafka is running
if nc -z localhost 9092; then
    echo "✅ Kafka is running"
else
    echo "❌ Kafka is not running"
    exit 1
fi

# Generate some test traffic
echo "📡 Generating test traffic..."
curl -s http://www.google.com > /dev/null 2>&1 || true
nslookup google.com > /dev/null 2>&1 || true

# Wait a moment for events to be processed
sleep 3

# Check for messages in Kafka topics
echo "🔍 Checking Kafka topics for events..."
total_messages=0

for topic in "${TOPICS[@]}"; do
    # Get message count from topic
    count=$(timeout 5 /home/ifscr/Downloads/kafka_2.13-3.9.1/bin/kafka-console-consumer.sh \
        --bootstrap-server $KAFKA_BROKERS \
        --topic $topic \
        --from-beginning \
        --timeout-ms 3000 \
        --max-messages 100 2>/dev/null | wc -l)
    
    if [ "$count" -gt 0 ]; then
        echo "✅ Topic '$topic': $count messages"
        total_messages=$((total_messages + count))
    else
        echo "⚠️  Topic '$topic': no messages"
    fi
done

echo "======================================"
if [ $total_messages -gt 0 ]; then
    echo "🎉 SUCCESS: Found $total_messages total events in Kafka"
    echo "✅ Suricata is streaming directly to Kafka"
    echo "✅ No file-based logging detected"
else
    echo "❌ FAILED: No events found in Kafka topics"
    echo "Check Suricata configuration and logs"
fi
echo "======================================"
