#!/bin/bash

# Validation Script for Suricata Direct Kafka Streaming
# This script validates that Suricata is streaming events directly to Kafka
# without writing any files to disk

set -e

echo "=== Suricata Direct Kafka Streaming Validation ==="

# Configuration
KAFKA_BROKERS="localhost:9092"
TOPICS=("suricata-events" "suricata-alerts" "suricata-stats")
SURICATA_CONFIG="/home/ifscr/SE_02_2025/IDS/Suricata_Setup/suricata-kafka.yaml"
TEST_DURATION=60  # seconds
CONSUMER_TIMEOUT=30  # seconds

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

function log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

function log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

function check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Kafka is running
    if ! nc -z localhost 9092; then
        log_error "Kafka is not running on localhost:9092"
        log_info "Start Kafka with: sudo systemctl start kafka"
        exit 1
    fi
    log_info "✅ Kafka is running"
    
    # Check if topics exist
    for topic in "${TOPICS[@]}"; do
        if kafka-topics.sh --bootstrap-server $KAFKA_BROKERS --list | grep -q "^$topic$"; then
            log_info "✅ Topic '$topic' exists"
        else
            log_error "Topic '$topic' does not exist"
            log_info "Run setup_kafka.sh to create topics"
            exit 1
        fi
    done
    
    # Check if Suricata config exists
    if [ ! -f "$SURICATA_CONFIG" ]; then
        log_error "Suricata config not found: $SURICATA_CONFIG"
        exit 1
    fi
    log_info "✅ Suricata config found"
    
    # Check if Python dependencies are installed
    if ! python3 -c "import kafka" 2>/dev/null; then
        log_warn "kafka-python not installed"
        log_info "Installing kafka-python..."
        pip3 install kafka-python
    fi
    log_info "✅ Python dependencies available"
}

function validate_config() {
    log_info "Validating Suricata configuration for direct Kafka streaming..."
    
    # Check that no file outputs are configured
    if grep -q "filename:" "$SURICATA_CONFIG"; then
        log_error "Configuration contains file outputs - should stream directly to Kafka"
        log_info "Check $SURICATA_CONFIG for 'filename:' entries"
        exit 1
    fi
    log_info "✅ No file outputs configured"
    
    # Check that Kafka outputs are enabled
    if ! grep -q "kafka:" "$SURICATA_CONFIG"; then
        log_error "No Kafka outputs configured"
        exit 1
    fi
    log_info "✅ Kafka outputs configured"
    
    # Check that console logging is disabled
    if grep -A 5 "console:" "$SURICATA_CONFIG" | grep -q "enabled: yes"; then
        log_warn "Console logging is enabled - may impact performance"
    else
        log_info "✅ Console logging disabled"
    fi
    
    # Check DPDK configuration
    if ! grep -q "dpdk:" "$SURICATA_CONFIG"; then
        log_warn "DPDK not configured - using standard packet capture"
    else
        log_info "✅ DPDK configured for high-performance capture"
    fi
}

function start_kafka_consumer() {
    log_info "Starting Kafka consumer to monitor events..."
    
    # Start consumer in background
    python3 kafka_consumer.py \
        --brokers $KAFKA_BROKERS \
        --topics "${TOPICS[0]}" "${TOPICS[1]}" "${TOPICS[2]}" \
        --timeout $CONSUMER_TIMEOUT \
        --validate &
    
    CONSUMER_PID=$!
    echo $CONSUMER_PID > /tmp/kafka_consumer.pid
    
    log_info "Kafka consumer started (PID: $CONSUMER_PID)"
    sleep 2
}

function generate_test_traffic() {
    log_info "Generating test traffic to trigger Suricata events..."
    
    # Generate various types of traffic
    log_info "Generating HTTP traffic..."
    curl -s http://testmyids.com > /dev/null 2>&1 || true
    curl -s http://www.google.com > /dev/null 2>&1 || true
    
    log_info "Generating DNS queries..."
    nslookup google.com > /dev/null 2>&1 || true
    nslookup malware.testcategory.com > /dev/null 2>&1 || true
    
    log_info "Generating network scans (simulated)..."
    # Simulate port scanning
    for port in 22 80 443 3389; do
        timeout 1 nc -z localhost $port > /dev/null 2>&1 || true
    done
    
    log_info "Test traffic generation completed"
}

function check_kafka_messages() {
    log_info "Checking for messages in Kafka topics..."
    
    local messages_found=0
    
    for topic in "${TOPICS[@]}"; do
        log_info "Checking topic: $topic"
        
        # Get message count from topic
        local count=$(kafka-console-consumer.sh \
            --bootstrap-server $KAFKA_BROKERS \
            --topic $topic \
            --from-beginning \
            --timeout-ms 5000 \
            --max-messages 10 2>/dev/null | wc -l)
        
        if [ "$count" -gt 0 ]; then
            log_info "✅ Found $count messages in topic '$topic'"
            messages_found=$((messages_found + count))
        else
            log_warn "No messages found in topic '$topic'"
        fi
    done
    
    if [ $messages_found -gt 0 ]; then
        log_info "✅ Total messages found: $messages_found"
        return 0
    else
        log_error "No messages found in any Kafka topic"
        return 1
    fi
}

function validate_suricata_process() {
    log_info "Checking Suricata process..."
    
    # Check for any Suricata process
    if pgrep -f "suricata" > /dev/null; then
        log_info "✅ Suricata is running"
        
        # Check which service is running
        if systemctl is-active --quiet suricata-kafka; then
            log_info "✅ Suricata running with DPDK + Kafka service"
        elif systemctl is-active --quiet suricata-simple; then
            log_info "✅ Suricata running with simple service (no DPDK)"
            log_warn "Using suricata-simple instead of suricata-kafka"
        else
            log_info "✅ Suricata running (manual start)"
        fi
        
        # Check if current installation supports Kafka
        if ! journalctl -u suricata-simple -n 10 --no-pager | grep -q "kafka"; then
            log_warn "Current Suricata installation may not support Kafka output"
            log_info "Consider running: ./install_suricata_kafka.sh"
        fi
        
        return 0
    else
        log_error "Suricata is not running"
        log_info "Start Suricata with:"
        log_info "  - DPDK version: sudo systemctl start suricata-kafka"
        log_info "  - Simple version: sudo systemctl start suricata-simple"
        return 1
    fi
}

function cleanup() {
    log_info "Cleaning up..."
    
    # Stop consumer if running
    if [ -f /tmp/kafka_consumer.pid ]; then
        local pid=$(cat /tmp/kafka_consumer.pid)
        if kill -0 $pid 2>/dev/null; then
            kill $pid
            log_info "Stopped Kafka consumer"
        fi
        rm -f /tmp/kafka_consumer.pid
    fi
}

function main() {
    trap cleanup EXIT
    
    echo "Starting validation at $(date)"
    echo "========================================"
    
    # Run validation steps
    check_prerequisites
    validate_config
    validate_suricata_process
    
    # Generate test traffic first
    generate_test_traffic
    
    # Wait for events to be processed
    log_info "Waiting for events to be processed..."
    sleep 5
    
    # Check for messages in topics (primary validation method)
    log_info "Checking for events in Kafka topics..."
    if check_kafka_messages; then
        log_info "🎉 VALIDATION SUCCESSFUL!"
        log_info "Suricata is successfully streaming events directly to Kafka"
        echo "========================================"
        echo "✅ No file outputs detected"
        echo "✅ Events flowing to Kafka topics"  
        echo "✅ Direct streaming validated"
        echo "========================================"
        
        # Optional: Start real-time consumer for demonstration
        log_info "Starting real-time consumer for monitoring (optional)..."
        start_kafka_consumer
    else
        log_error "❌ VALIDATION FAILED!"
        log_error "No events detected in Kafka topics"
        echo "========================================"
        echo "Troubleshooting steps:"
        echo "1. Check Suricata logs: journalctl -u suricata-kafka -f"
        echo "2. Verify network interface configuration in $SURICATA_CONFIG"
        echo "3. Check Kafka broker connectivity"
        echo "4. Ensure test traffic reaches Suricata interface"
        echo "========================================"
        exit 1
    fi
}

# Run main function
main "$@"
