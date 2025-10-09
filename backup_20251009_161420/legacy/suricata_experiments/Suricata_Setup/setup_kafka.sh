#!/bin/bash

# Kafka Setup Script for Suricata Integration
# This script sets up Kafka topics and validates the configuration

set -e

echo "=== Kafka Setup for Suricata Integration ==="

# Configuration
KAFKA_HOME="/home/ifscr/Downloads/kafka_2.13-3.9.1"
KAFKA_BROKERS="localhost:9092"
ZOOKEEPER_HOST="localhost:2181"

# Auto-detect Kafka installation if not found
if [ ! -f "$KAFKA_HOME/bin/kafka-topics.sh" ]; then
    echo "Auto-detecting Kafka installation..."
    KAFKA_TOPICS_PATH=$(which kafka-topics.sh 2>/dev/null || find /usr /opt /home -name "kafka-topics.sh" 2>/dev/null | head -1)
    if [ -n "$KAFKA_TOPICS_PATH" ]; then
        KAFKA_HOME=$(dirname "$(dirname "$KAFKA_TOPICS_PATH")")
        echo "Found Kafka at: $KAFKA_HOME"
    else
        echo "❌ Kafka installation not found!"
        echo "Please install Kafka or update KAFKA_HOME in this script"
        exit 1
    fi
fi

# Topics configuration
EVENTS_TOPIC="suricata-events"
ALERTS_TOPIC="suricata-alerts"
STATS_TOPIC="suricata-stats"

# Topic settings
PARTITIONS=4
REPLICATION_FACTOR=1
RETENTION_MS=604800000  # 7 days
SEGMENT_MS=86400000     # 1 day

function check_kafka_running() {
    echo "Checking if Kafka is running..."
    if ! nc -z localhost 9092; then
        echo "❌ Kafka is not running on localhost:9092"
        echo "Please start Kafka first:"
        echo "  1. Start Zookeeper: sudo systemctl start zookeeper"
        echo "  2. Start Kafka: sudo systemctl start kafka"
        exit 1
    fi
    echo "✅ Kafka is running"
}

function create_topics() {
    echo "Creating Kafka topics for Suricata..."
    
    # Create main events topic
    echo "Creating topic: $EVENTS_TOPIC"
    $KAFKA_HOME/bin/kafka-topics.sh --create \
        --bootstrap-server $KAFKA_BROKERS \
        --topic $EVENTS_TOPIC \
        --partitions $PARTITIONS \
        --replication-factor $REPLICATION_FACTOR \
        --config retention.ms=$RETENTION_MS \
        --config segment.ms=$SEGMENT_MS \
        --config compression.type=snappy \
        --config cleanup.policy=delete \
        --config max.message.bytes=1048576 \
        --if-not-exists
    
    # Create alerts topic (higher priority)
    echo "Creating topic: $ALERTS_TOPIC"
    $KAFKA_HOME/bin/kafka-topics.sh --create \
        --bootstrap-server $KAFKA_BROKERS \
        --topic $ALERTS_TOPIC \
        --partitions $PARTITIONS \
        --replication-factor $REPLICATION_FACTOR \
        --config retention.ms=$RETENTION_MS \
        --config segment.ms=$SEGMENT_MS \
        --config compression.type=snappy \
        --config cleanup.policy=delete \
        --config min.insync.replicas=1 \
        --if-not-exists
    
    # Create stats topic
    echo "Creating topic: $STATS_TOPIC"
    $KAFKA_HOME/bin/kafka-topics.sh --create \
        --bootstrap-server $KAFKA_BROKERS \
        --topic $STATS_TOPIC \
        --partitions 2 \
        --replication-factor $REPLICATION_FACTOR \
        --config retention.ms=$RETENTION_MS \
        --config segment.ms=$SEGMENT_MS \
        --config compression.type=gzip \
        --config cleanup.policy=delete \
        --if-not-exists
    
    echo "✅ Topics created successfully"
}

function list_topics() {
    echo "Listing Kafka topics..."
    $KAFKA_HOME/bin/kafka-topics.sh --list --bootstrap-server $KAFKA_BROKERS
}

function describe_topics() {
    echo "Describing Suricata topics..."
    
    echo "=== $EVENTS_TOPIC ==="
    $KAFKA_HOME/bin/kafka-topics.sh --describe \
        --bootstrap-server $KAFKA_BROKERS \
        --topic $EVENTS_TOPIC
    
    echo "=== $ALERTS_TOPIC ==="
    $KAFKA_HOME/bin/kafka-topics.sh --describe \
        --bootstrap-server $KAFKA_BROKERS \
        --topic $ALERTS_TOPIC
    
    echo "=== $STATS_TOPIC ==="
    $KAFKA_HOME/bin/kafka-topics.sh --describe \
        --bootstrap-server $KAFKA_BROKERS \
        --topic $STATS_TOPIC
}

function test_producer() {
    echo "Testing Kafka producer..."
    echo '{"test": "message", "timestamp": "'$(date -Iseconds)'", "event_type": "test"}' | \
    $KAFKA_HOME/bin/kafka-console-producer.sh \
        --bootstrap-server $KAFKA_BROKERS \
        --topic $EVENTS_TOPIC
    echo "✅ Test message sent to $EVENTS_TOPIC"
}

function show_consumer_commands() {
    echo "=== Kafka Consumer Commands ==="
    echo "To consume Suricata events:"
    echo "  $KAFKA_HOME/bin/kafka-console-consumer.sh --bootstrap-server $KAFKA_BROKERS --topic $EVENTS_TOPIC --from-beginning"
    echo ""
    echo "To consume alerts only:"
    echo "  $KAFKA_HOME/bin/kafka-console-consumer.sh --bootstrap-server $KAFKA_BROKERS --topic $ALERTS_TOPIC --from-beginning"
    echo ""
    echo "To consume stats:"
    echo "  $KAFKA_HOME/bin/kafka-console-consumer.sh --bootstrap-server $KAFKA_BROKERS --topic $STATS_TOPIC --from-beginning"
}

# Main execution
case "${1:-setup}" in
    "setup")
        check_kafka_running
        create_topics
        list_topics
        describe_topics
        test_producer
        show_consumer_commands
        ;;
    "list")
        list_topics
        ;;
    "describe")
        describe_topics
        ;;
    "test")
        test_producer
        ;;
    "consumer-commands")
        show_consumer_commands
        ;;
    "cleanup")
        echo "Deleting Suricata topics..."
        $KAFKA_HOME/bin/kafka-topics.sh --delete --bootstrap-server $KAFKA_BROKERS --topic $EVENTS_TOPIC
        $KAFKA_HOME/bin/kafka-topics.sh --delete --bootstrap-server $KAFKA_BROKERS --topic $ALERTS_TOPIC
        $KAFKA_HOME/bin/kafka-topics.sh --delete --bootstrap-server $KAFKA_BROKERS --topic $STATS_TOPIC
        echo "✅ Topics deleted"
        ;;
    *)
        echo "Usage: $0 {setup|list|describe|test|consumer-commands|cleanup}"
        echo ""
        echo "Commands:"
        echo "  setup              - Create topics and test setup"
        echo "  list               - List all topics"
        echo "  describe           - Describe Suricata topics"
        echo "  test               - Send test message"
        echo "  consumer-commands  - Show consumer commands"
        echo "  cleanup            - Delete Suricata topics"
        exit 1
        ;;
esac

echo "=== Kafka setup complete ==="
