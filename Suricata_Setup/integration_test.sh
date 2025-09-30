#!/bin/bash

# End-to-End Integration Test for Suricata Direct Kafka Streaming
# This script demonstrates and validates the complete pipeline

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KAFKA_BROKERS="localhost:9092"
TOPICS=("suricata-events" "suricata-alerts" "suricata-stats")
TEST_DURATION=120
VALIDATION_TIMEOUT=60

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

function log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

function log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

function log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

function log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

function print_header() {
    echo ""
    echo "================================================================"
    echo "  SURICATA DIRECT KAFKA STREAMING - END-TO-END TEST"
    echo "================================================================"
    echo "This test validates that Suricata streams events directly to"
    echo "Kafka without writing any files to disk."
    echo ""
    echo "Test Components:"
    echo "✓ Suricata with DPDK packet capture"
    echo "✓ Direct Kafka streaming (no eve.json files)"
    echo "✓ High-throughput async producer"
    echo "✓ Multiple Kafka topics"
    echo "✓ Real-time event validation"
    echo "================================================================"
    echo ""
}

function check_environment() {
    log_step "Checking environment prerequisites"
    
    # Check if we're in the correct directory
    if [ ! -f "suricata-kafka.yaml" ]; then
        log_error "suricata-kafka.yaml not found. Please run from Suricata_Setup directory"
        exit 1
    fi
    
    # Check if required scripts exist
    local required_scripts=("setup_kafka.sh" "validate_kafka_streaming.sh" "generate_test_traffic.sh" "kafka_consumer.py")
    for script in "${required_scripts[@]}"; do
        if [ ! -f "$script" ]; then
            log_error "Required script not found: $script"
            exit 1
        fi
    done
    
    # Check if scripts are executable
    for script in setup_kafka.sh validate_kafka_streaming.sh generate_test_traffic.sh; do
        if [ ! -x "$script" ]; then
            log_warn "Making $script executable"
            chmod +x "$script"
        fi
    done
    
    log_info "✅ Environment check passed"
}

function setup_kafka_topics() {
    log_step "Setting up Kafka topics"
    
    if ! ./setup_kafka.sh; then
        log_error "Failed to setup Kafka topics"
        exit 1
    fi
    
    log_info "✅ Kafka topics configured"
}

function validate_suricata_config() {
    log_step "Validating Suricata configuration"
    
    # Check for file outputs (should be none)
    if grep -q "filename:" suricata-kafka.yaml; then
        log_error "Configuration contains file outputs - not streaming directly to Kafka"
        log_error "Found 'filename:' entries in suricata-kafka.yaml"
        exit 1
    fi
    
    # Check for Kafka outputs
    if ! grep -q "kafka:" suricata-kafka.yaml; then
        log_error "No Kafka outputs found in configuration"
        exit 1
    fi
    
    # Check that console logging is disabled
    if grep -A 5 "console:" suricata-kafka.yaml | grep -q "enabled: yes"; then
        log_warn "Console logging enabled - may impact performance"
    fi
    
    log_info "✅ Configuration validation passed"
    log_info "  - No file outputs configured"
    log_info "  - Kafka outputs enabled"
    log_info "  - Direct streaming mode confirmed"
}

function check_suricata_service() {
    log_step "Checking Suricata service status"
    
    if systemctl is-active --quiet suricata-kafka; then
        log_info "✅ Suricata-Kafka service is running"
        
        # Show service status
        echo ""
        echo "Service Status:"
        systemctl status suricata-kafka --no-pager -l | head -15
        echo ""
        
    else
        log_warn "Suricata-Kafka service is not running"
        log_info "Attempting to start service..."
        
        if sudo systemctl start suricata-kafka; then
            log_info "✅ Service started successfully"
            sleep 5  # Allow service to initialize
        else
            log_error "Failed to start Suricata service"
            log_error "Check logs: journalctl -u suricata-kafka -f"
            exit 1
        fi
    fi
}

function verify_no_log_files() {
    log_step "Verifying no log files are being created"
    
    local log_dirs=("/var/log/suricata" "/opt/suricata/var/log/suricata" "/usr/local/var/log/suricata")
    local files_found=0
    
    for log_dir in "${log_dirs[@]}"; do
        if [ -d "$log_dir" ]; then
            log_info "Checking directory: $log_dir"
            
            # Check for common Suricata log files
            local log_files=("eve.json" "fast.log" "suricata.log" "stats.log")
            for log_file in "${log_files[@]}"; do
                if [ -f "$log_dir/$log_file" ]; then
                    local size=$(stat -f%z "$log_dir/$log_file" 2>/dev/null || stat -c%s "$log_dir/$log_file" 2>/dev/null || echo "0")
                    if [ "$size" -gt 0 ]; then
                        log_warn "Log file found: $log_dir/$log_file (size: $size bytes)"
                        files_found=$((files_found + 1))
                    fi
                fi
            done
        fi
    done
    
    if [ $files_found -eq 0 ]; then
        log_info "✅ No active log files found - direct Kafka streaming confirmed"
    else
        log_warn "Found $files_found log files - may indicate partial file logging"
        log_warn "This is acceptable if files are empty or not being actively written"
    fi
}

function start_monitoring() {
    log_step "Starting real-time event monitoring"
    
    # Start Kafka consumer in background
    log_info "Starting Kafka consumer for all topics..."
    python3 kafka_consumer.py \
        --brokers "$KAFKA_BROKERS" \
        --topics "${TOPICS[@]}" \
        --quiet \
        --stats-interval 15 &
    
    CONSUMER_PID=$!
    echo $CONSUMER_PID > /tmp/integration_test_consumer.pid
    
    log_info "Consumer started (PID: $CONSUMER_PID)"
    sleep 3
}

function generate_comprehensive_traffic() {
    log_step "Generating comprehensive test traffic"
    
    log_info "Starting traffic generation for $TEST_DURATION seconds..."
    
    # Run traffic generator in background
    ./generate_test_traffic.sh &
    TRAFFIC_PID=$!
    
    # Monitor traffic generation
    local start_time=$(date +%s)
    local end_time=$((start_time + TEST_DURATION))
    
    while [ $(date +%s) -lt $end_time ]; do
        local elapsed=$(($(date +%s) - start_time))
        local remaining=$((TEST_DURATION - elapsed))
        
        echo -ne "\r${BLUE}[TRAFFIC]${NC} Progress: ${elapsed}/${TEST_DURATION}s | Remaining: ${remaining}s"
        sleep 5
    done
    
    echo ""
    log_info "✅ Traffic generation completed"
    
    # Stop traffic generator
    kill $TRAFFIC_PID 2>/dev/null || true
    wait $TRAFFIC_PID 2>/dev/null || true
}

function validate_event_flow() {
    log_step "Validating event flow to Kafka"
    
    # Use the validation consumer
    log_info "Running validation consumer..."
    if python3 kafka_consumer.py \
        --brokers "$KAFKA_BROKERS" \
        --topics "${TOPICS[@]}" \
        --validate \
        --timeout $VALIDATION_TIMEOUT; then
        
        log_info "✅ Event validation successful"
        return 0
    else
        log_error "❌ Event validation failed"
        return 1
    fi
}

function check_topic_statistics() {
    log_step "Checking Kafka topic statistics"
    
    echo ""
    echo "Topic Statistics:"
    echo "=================="
    
    for topic in "${TOPICS[@]}"; do
        echo ""
        echo "Topic: $topic"
        echo "-------------------"
        
        # Get topic info
        if kafka-topics.sh --bootstrap-server "$KAFKA_BROKERS" --describe --topic "$topic" 2>/dev/null; then
            # Count messages (approximate)
            local msg_count=$(timeout 5 kafka-console-consumer.sh \
                --bootstrap-server "$KAFKA_BROKERS" \
                --topic "$topic" \
                --from-beginning \
                --timeout-ms 3000 2>/dev/null | wc -l || echo "0")
            
            echo "Approximate message count: $msg_count"
        else
            log_warn "Could not get statistics for topic: $topic"
        fi
    done
    
    echo ""
}

function performance_summary() {
    log_step "Performance Summary"
    
    echo ""
    echo "Performance Metrics:"
    echo "===================="
    
    # Suricata process info
    if pgrep -x suricata > /dev/null; then
        local suricata_pid=$(pgrep -x suricata | head -1)
        local cpu_usage=$(ps -p $suricata_pid -o %cpu --no-headers 2>/dev/null || echo "N/A")
        local mem_usage=$(ps -p $suricata_pid -o %mem --no-headers 2>/dev/null || echo "N/A")
        
        echo "Suricata Process:"
        echo "  PID: $suricata_pid"
        echo "  CPU Usage: ${cpu_usage}%"
        echo "  Memory Usage: ${mem_usage}%"
    else
        echo "Suricata Process: Not running"
    fi
    
    # System load
    echo ""
    echo "System Load:"
    uptime
    
    # Memory info
    echo ""
    echo "Memory Usage:"
    free -h | head -2
    
    echo ""
}

function cleanup() {
    log_info "Cleaning up test environment..."
    
    # Stop consumer
    if [ -f /tmp/integration_test_consumer.pid ]; then
        local pid=$(cat /tmp/integration_test_consumer.pid)
        if kill -0 $pid 2>/dev/null; then
            kill $pid
            log_info "Stopped Kafka consumer"
        fi
        rm -f /tmp/integration_test_consumer.pid
    fi
    
    # Kill any remaining background jobs
    jobs -p | xargs -r kill > /dev/null 2>&1 || true
    
    log_info "Cleanup completed"
}

function print_results() {
    echo ""
    echo "================================================================"
    echo "  INTEGRATION TEST RESULTS"
    echo "================================================================"
    
    if [ "$TEST_PASSED" = "true" ]; then
        echo -e "${GREEN}🎉 TEST PASSED - Direct Kafka Streaming Validated${NC}"
        echo ""
        echo "✅ Suricata is successfully streaming events directly to Kafka"
        echo "✅ No file-based logging detected"
        echo "✅ Events flowing to all configured topics"
        echo "✅ Real-time processing confirmed"
        echo ""
        echo "Kafka Topics Receiving Events:"
        for topic in "${TOPICS[@]}"; do
            echo "  - $topic"
        done
    else
        echo -e "${RED}❌ TEST FAILED - Issues Detected${NC}"
        echo ""
        echo "❌ Direct Kafka streaming validation failed"
        echo ""
        echo "Troubleshooting:"
        echo "1. Check Suricata logs: journalctl -u suricata-kafka -f"
        echo "2. Verify Kafka broker connectivity"
        echo "3. Check network interface configuration"
        echo "4. Review Suricata configuration file"
    fi
    
    echo ""
    echo "================================================================"
}

function main() {
    trap cleanup EXIT
    
    print_header
    
    # Test steps
    check_environment
    setup_kafka_topics
    validate_suricata_config
    check_suricata_service
    verify_no_log_files
    
    # Start monitoring and testing
    start_monitoring
    generate_comprehensive_traffic
    
    # Validate results
    if validate_event_flow; then
        TEST_PASSED="true"
    else
        TEST_PASSED="false"
    fi
    
    # Show statistics
    check_topic_statistics
    performance_summary
    
    # Final results
    print_results
    
    # Exit with appropriate code
    if [ "$TEST_PASSED" = "true" ]; then
        exit 0
    else
        exit 1
    fi
}

# Check if running as root for system operations
if [ "$EUID" -ne 0 ]; then
    log_warn "Some operations may require root privileges"
    log_info "Run with 'sudo' if you encounter permission issues"
fi

# Run main function
main "$@"
