#!/bin/bash

# Complete ML-Enhanced DPDK-Suricata-Kafka IDS Pipeline
# Integrates DPDK packet generation, Suricata rule-based detection, 
# Random Forest ML predictions, and real-time Kafka streaming

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
INTERFACE="enp2s0"
KAFKA_BROKER="localhost:9092"
ML_MODEL_PATH="/home/ifscr/SE_02_2025/IDS/src/ML_Model/intrusion_detection_model.joblib"
DURATION=300  # 5 minutes default
PACKET_RATE=100
ML_ENABLED=true

echo -e "${BOLD}${BLUE}🧠 ML-Enhanced DPDK-IDS Pipeline${NC}"
echo -e "${CYAN}=====================================+========${NC}"
echo "Architecture: DPDK → Suricata → ML → Kafka → Analytics"
echo

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}🔍 Checking system prerequisites...${NC}"
    
    # Root privileges
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}❌ Root privileges required for packet injection${NC}"
        echo "Please run: sudo $0"
        exit 1
    fi
    echo -e "${GREEN}✓ Root privileges confirmed${NC}"
    
    # Python dependencies
    python3 -c "import scapy, kafka, joblib, sklearn, numpy, pandas" 2>/dev/null || {
        echo -e "${RED}❌ Missing Python dependencies${NC}"
        echo "Installing required packages..."
        pip3 install scapy kafka-python joblib scikit-learn numpy pandas psutil watchdog python-snappy
    }
    echo -e "${GREEN}✓ Python dependencies available${NC}"
    
    # ML Model
    if [ ! -f "$ML_MODEL_PATH" ]; then
        echo -e "${RED}❌ ML model not found at $ML_MODEL_PATH${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ ML model found ($(du -h $ML_MODEL_PATH | cut -f1))${NC}"
    
    # Network interface
    if ! ip link show $INTERFACE > /dev/null 2>&1; then
        echo -e "${RED}❌ Interface $INTERFACE not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Interface $INTERFACE available${NC}"
    
    echo
}

# Function to start Kafka infrastructure
start_kafka() {
    echo -e "${YELLOW}📡 Starting Kafka infrastructure...${NC}"
    
    # Check if Kafka is already running
    if pgrep -f kafka > /dev/null; then
        echo -e "${GREEN}✓ Kafka already running${NC}"
        return 0
    fi
    
    # Try systemd first
    if systemctl start kafka 2>/dev/null; then
        echo -e "${GREEN}✓ Kafka started via systemd${NC}"
        sleep 5
    else
        # Try manual Kafka installation
        KAFKA_HOME="/home/ifscr/Downloads/kafka_2.13-3.9.1"
        if [ -d "$KAFKA_HOME" ]; then
            echo "Starting Kafka manually..."
            cd "$KAFKA_HOME"
            
            # Start Zookeeper
            ./bin/zookeeper-server-start.sh -daemon config/zookeeper.properties
            sleep 5
            
            # Start Kafka
            ./bin/kafka-server-start.sh -daemon config/server.properties
            sleep 10
            
            echo -e "${GREEN}✓ Kafka started manually${NC}"
        else
            echo -e "${RED}❌ Cannot start Kafka${NC}"
            exit 1
        fi
    fi
    
    # Setup topics
    cd /home/ifscr/SE_02_2025/IDS/Suricata_Setup
    ./setup_kafka.sh
    
    # Create ML-enhanced alerts topic
    KAFKA_CMD="/opt/kafka/bin/kafka-topics.sh"
    if [ -f "$KAFKA_CMD" ]; then
        $KAFKA_CMD --bootstrap-server $KAFKA_BROKER --create --if-not-exists --topic ml-enhanced-alerts --partitions 1 --replication-factor 1 2>/dev/null
        echo -e "${GREEN}✓ ML-enhanced alerts topic created${NC}"
    fi
    
    echo
}

# Function to start Suricata
start_suricata() {
    echo -e "${YELLOW}🔍 Starting Suricata IDS...${NC}"
    
    # Check if already running
    if systemctl is-active --quiet suricata-simple; then
        echo -e "${GREEN}✓ Suricata-simple already running${NC}"
    else
        systemctl start suricata-simple
        sleep 3
        if systemctl is-active --quiet suricata-simple; then
            echo -e "${GREEN}✓ Suricata-simple started${NC}"
        else
            echo -e "${RED}❌ Failed to start Suricata${NC}"
            exit 1
        fi
    fi
    
    # Verify log output
    if [ -f "/var/log/suricata/eve.json" ]; then
        echo -e "${GREEN}✓ Suricata logging to eve.json${NC}"
    else
        echo -e "${YELLOW}⚠️  Creating Suricata log directory${NC}"
        mkdir -p /var/log/suricata
        chown suricata:suricata /var/log/suricata
        chmod 755 /var/log/suricata
    fi
    
    echo
}

# Function to start EVE-Kafka bridge
start_bridge() {
    echo -e "${YELLOW}🌉 Starting EVE-Kafka bridge...${NC}"
    
    # Check if already running
    if pgrep -f eve_kafka_bridge > /dev/null; then
        echo -e "${GREEN}✓ EVE-Kafka bridge already running${NC}"
    else
        cd /home/ifscr/SE_02_2025/IDS/Suricata_Setup
        python3 eve_kafka_bridge.py &
        BRIDGE_PID=$!
        sleep 3
        
        if kill -0 $BRIDGE_PID 2>/dev/null; then
            echo -e "${GREEN}✓ EVE-Kafka bridge started (PID: $BRIDGE_PID)${NC}"
        else
            echo -e "${RED}❌ Failed to start EVE-Kafka bridge${NC}"
            exit 1
        fi
    fi
    
    echo
}

# Function to start ML processing
start_ml_pipeline() {
    echo -e "${YELLOW}🧠 Starting ML-Enhanced Processing...${NC}"
    
    cd /home/ifscr/SE_02_2025/IDS
    python3 ml_enhanced_ids_pipeline.py &
    ML_PID=$!
    sleep 5
    
    if kill -0 $ML_PID 2>/dev/null; then
        echo -e "${GREEN}✓ ML pipeline started (PID: $ML_PID)${NC}"
        echo "  Processing Kafka events with Random Forest model"
        echo "  Combining rule-based + ML-based threat detection"
    else
        echo -e "${RED}❌ Failed to start ML pipeline${NC}"
        exit 1
    fi
    
    echo
}

# Function to start packet generation
start_packet_generation() {
    echo -e "${YELLOW}🚀 Starting DPDK packet generation...${NC}"
    echo "Rate: $PACKET_RATE pps, Duration: $DURATION seconds"
    
    cd /home/ifscr/SE_02_2025/IDS
    # Use advanced attack generator for sophisticated ML model testing
    python3 advanced_attack_generator.py --attack-type mixed --rate $PACKET_RATE --interface $INTERFACE &
    PACKET_PID=$!
    
    echo -e "${GREEN}✓ Packet generation started (PID: $PACKET_PID)${NC}"
    echo
}

# Function to monitor the pipeline
monitor_pipeline() {
    echo -e "${YELLOW}📊 Starting pipeline monitoring...${NC}"
    
    # Start monitoring in background
    cd /home/ifscr/SE_02_2025/IDS
    python3 realtime_ids_monitor.py &
    MONITOR_PID=$!
    
    echo -e "${GREEN}✓ Real-time monitoring started (PID: $MONITOR_PID)${NC}"
    echo "  Dashboard showing: Events, Alerts, ML predictions, System performance"
    echo
    
    # Monitor ML-enhanced alerts
    echo -e "${CYAN}🔍 Monitoring ML-Enhanced alerts...${NC}"
    timeout $DURATION python3 -c "
from kafka import KafkaConsumer
import json
import time

consumer = KafkaConsumer(
    'ml-enhanced-alerts',
    bootstrap_servers=['$KAFKA_BROKER'],
    auto_offset_reset='latest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

print('Listening for ML-enhanced alerts...')
alert_count = 0

for message in consumer:
    alert = message.value
    alert_count += 1
    
    threat_level = alert['combined_assessment']['threat_level']
    src_ip = alert['src_ip']
    dest_ip = alert['dest_ip']
    description = alert['combined_assessment']['description']
    score = alert['combined_assessment']['combined_score']
    
    color_code = ''
    if threat_level == 'CRITICAL':
        color_code = '\033[91m'  # Red
    elif threat_level == 'HIGH':
        color_code = '\033[93m'  # Yellow
    else:
        color_code = '\033[92m'  # Green
    
    print(f'{color_code}🚨 {threat_level} ALERT #{alert_count}:\033[0m')
    print(f'  Source: {src_ip} → Destination: {dest_ip}')
    print(f'  Threat Score: {score:.1f}/100')
    print(f'  Description: {description}')
    print(f'  ML Prediction: {alert[\"ml_detection\"][\"predicted_attack\"]} (confidence: {alert[\"ml_detection\"][\"confidence\"]:.2f})')
    print()
    
    if alert_count >= 50:  # Limit output
        break

print(f'Total ML-enhanced alerts: {alert_count}')
" &
    ALERT_MONITOR_PID=$!
}

# Function to show real-time dashboard
show_dashboard() {
    echo -e "${BOLD}${MAGENTA}📺 Real-time Pipeline Dashboard${NC}"
    echo -e "${MAGENTA}================================${NC}"
    
    # Show system status every 10 seconds
    for i in $(seq 1 $((DURATION/10))); do
        echo -e "\n${CYAN}📊 Pipeline Status (Update $i)${NC}"
        echo "Time: $(date '+%H:%M:%S')"
        
        # Service status
        echo -n "Suricata: "
        systemctl is-active --quiet suricata-simple && echo -e "${GREEN}✓ Active${NC}" || echo -e "${RED}❌ Inactive${NC}"
        
        echo -n "Kafka: "
        pgrep -f kafka > /dev/null && echo -e "${GREEN}✓ Running${NC}" || echo -e "${RED}❌ Not running${NC}"
        
        echo -n "ML Pipeline: "
        kill -0 $ML_PID 2>/dev/null && echo -e "${GREEN}✓ Processing${NC}" || echo -e "${RED}❌ Stopped${NC}"
        
        echo -n "Packet Generation: "
        kill -0 $PACKET_PID 2>/dev/null && echo -e "${GREEN}✓ Generating${NC}" || echo -e "${YELLOW}⏹️ Completed${NC}"
        
        # Event counts
        if [ -f "/var/log/suricata/eve.json" ]; then
            RECENT_EVENTS=$(tail -100 /var/log/suricata/eve.json 2>/dev/null | wc -l)
            echo "Recent Suricata events: $RECENT_EVENTS"
        fi
        
        # System performance
        CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
        MEM_USAGE=$(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')
        echo "System: CPU ${CPU_USAGE}, Memory ${MEM_USAGE}"
        
        sleep 10
    done
}

# Function to stop all processes
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up processes...${NC}"
    
    # Stop background processes
    [ ! -z "$PACKET_PID" ] && kill $PACKET_PID 2>/dev/null || true
    [ ! -z "$ML_PID" ] && kill $ML_PID 2>/dev/null || true
    [ ! -z "$MONITOR_PID" ] && kill $MONITOR_PID 2>/dev/null || true
    [ ! -z "$ALERT_MONITOR_PID" ] && kill $ALERT_MONITOR_PID 2>/dev/null || true
    
    echo -e "${GREEN}✓ Cleanup completed${NC}"
}

# Function to show final results
show_results() {
    echo -e "\n${BOLD}${BLUE}📊 ML-Enhanced IDS Pipeline Results${NC}"
    echo -e "${BLUE}====================================${NC}"
    
    # Suricata events
    if [ -f "/var/log/suricata/eve.json" ]; then
        TOTAL_EVENTS=$(wc -l < /var/log/suricata/eve.json)
        ALERTS=$(grep '"event_type":"alert"' /var/log/suricata/eve.json | wc -l)
        FLOWS=$(grep '"event_type":"flow"' /var/log/suricata/eve.json | wc -l)
        HTTP_EVENTS=$(grep '"event_type":"http"' /var/log/suricata/eve.json | wc -l)
        
        echo -e "${GREEN}📈 Suricata Detection Results:${NC}"
        echo "  Total events: $TOTAL_EVENTS"
        echo "  Security alerts: $ALERTS"
        echo "  Network flows: $FLOWS"
        echo "  HTTP events: $HTTP_EVENTS"
    fi
    
    echo
    echo -e "${MAGENTA}🧠 ML Enhancement Benefits:${NC}"
    echo "  ✓ Combined rule-based + ML detection"
    echo "  ✓ Unknown threat pattern recognition"
    echo "  ✓ Confidence scoring for alerts"
    echo "  ✓ Advanced feature extraction"
    echo "  ✓ Real-time inference on streaming data"
    
    echo
    echo -e "${CYAN}🎯 Next Steps:${NC}"
    echo "  • Analyze ML-enhanced alerts: kafka_consumer.py --topic ml-enhanced-alerts"
    echo "  • Tune ML model thresholds based on results"
    echo "  • Add custom features for your network environment"
    echo "  • Deploy to production with scaling"
    
    echo
    echo -e "${BOLD}🎉 ML-Enhanced IDS Pipeline Complete!${NC}"
}

# Main execution function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --duration)
                DURATION="$2"
                shift 2
                ;;
            --rate)
                PACKET_RATE="$2"
                shift 2
                ;;
            --no-ml)
                ML_ENABLED=false
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --duration SECONDS    Duration of packet generation (default: 300)"
                echo "  --rate PPS           Packet generation rate (default: 100)"
                echo "  --no-ml              Disable ML processing"
                echo "  --help               Show this help"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Trap for cleanup
    trap cleanup EXIT
    
    echo "Configuration:"
    echo "  Duration: $DURATION seconds"
    echo "  Packet rate: $PACKET_RATE pps"
    echo "  ML processing: $ML_ENABLED"
    echo "  Interface: $INTERFACE"
    echo
    
    # Execute pipeline stages
    check_prerequisites
    start_kafka
    start_suricata
    start_bridge
    
    if [ "$ML_ENABLED" = true ]; then
        start_ml_pipeline
    fi
    
    start_packet_generation
    monitor_pipeline
    
    # Show dashboard in foreground
    show_dashboard
    
    # Wait for completion
    wait $PACKET_PID 2>/dev/null
    sleep 10  # Allow processing to complete
    
    show_results
}

# Execute main function
main "$@"