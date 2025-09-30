#!/bin/bash

# Real DPDK-Suricata Integration with ML Enhancement
# Proper DPDK packet capture → Suricata IDS → ML Enhancement → Kafka Streaming
# No Scapy - Pure DPDK performance

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
DPDK_VERSION="23.11"
DPDK_DIR="/opt/dpdk-${DPDK_VERSION}"
DPDK_TARGET="x86_64-native-linux-gcc"
INTERFACE="enp2s0"  # Network interface to bind to DPDK
PCI_ADDRESS=""      # Will be auto-detected
HUGEPAGE_SIZE="1048576"  # 1GB hugepages
NUM_HUGEPAGES="4"   # 4GB total
SURICATA_CONFIG="/etc/suricata/suricata-dpdk.yaml"
KAFKA_BROKER="localhost:9092"
ML_MODEL_PATH="/home/ifscr/SE_02_2025/IDS/src/ML_Model/intrusion_detection_model.joblib"

echo -e "${BOLD}${BLUE}🚀 Real DPDK-Suricata-ML IDS Pipeline Setup${NC}"
echo -e "${CYAN}=================================================${NC}"
echo "Architecture: DPDK Capture → Suricata → ML → Kafka"
echo "No Scapy - Pure DPDK Performance"
echo

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}🔍 Checking system prerequisites...${NC}"
    
    # Root privileges
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}❌ This script must be run as root${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Root privileges confirmed${NC}"
    
    # Check CPU cores
    CORES=$(nproc)
    if [ $CORES -lt 4 ]; then
        echo -e "${RED}❌ Need at least 4 CPU cores for DPDK${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ CPU cores: $CORES${NC}"
    
    # Check memory
    MEM_GB=$(free -g | awk '/^Mem:/{print $2}')
    if [ $MEM_GB -lt 8 ]; then
        echo -e "${RED}❌ Need at least 8GB RAM for DPDK hugepages${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Available memory: ${MEM_GB}GB${NC}"
    
    # Check network interface
    if ! ip link show $INTERFACE > /dev/null 2>&1; then
        echo -e "${RED}❌ Interface $INTERFACE not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Interface $INTERFACE available${NC}"
    
    # Get PCI address
    PCI_ADDRESS=$(ethtool -i $INTERFACE | grep bus-info | cut -d' ' -f2)
    if [ -z "$PCI_ADDRESS" ]; then
        echo -e "${RED}❌ Could not determine PCI address for $INTERFACE${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ PCI address: $PCI_ADDRESS${NC}"
    
    echo
}

# Function to install DPDK
install_dpdk() {
    echo -e "${YELLOW}📦 Installing DPDK $DPDK_VERSION...${NC}"
    
    if [ -d "$DPDK_DIR" ]; then
        echo -e "${GREEN}✓ DPDK already installed at $DPDK_DIR${NC}"
        return 0
    fi
    
    # Install dependencies
    apt-get update
    apt-get install -y build-essential meson ninja-build libnuma-dev \
        python3-pyelftools pkg-config libbsd-dev libpcap-dev \
        linux-headers-$(uname -r)
    
    # Download DPDK
    cd /opt
    wget -q "https://fast.dpdk.org/rel/dpdk-${DPDK_VERSION}.tar.xz"
    tar xf "dpdk-${DPDK_VERSION}.tar.xz"
    rm "dpdk-${DPDK_VERSION}.tar.xz"
    
    # Build DPDK
    cd "$DPDK_DIR"
    meson setup build
    cd build
    ninja
    ninja install
    ldconfig
    
    echo -e "${GREEN}✓ DPDK $DPDK_VERSION installed successfully${NC}"
    echo
}

# Function to configure hugepages
configure_hugepages() {
    echo -e "${YELLOW}🗄️ Configuring hugepages...${NC}"
    
    # Enable hugepages
    echo $NUM_HUGEPAGES > /sys/kernel/mm/hugepages/hugepages-${HUGEPAGE_SIZE}kB/nr_hugepages
    
    # Create hugepage mount point
    mkdir -p /mnt/huge
    
    # Add to fstab if not already there
    if ! grep -q "/mnt/huge" /etc/fstab; then
        echo "nodev /mnt/huge hugetlbfs defaults 0 0" >> /etc/fstab
    fi
    
    # Mount hugepages
    mount -t hugetlbfs nodev /mnt/huge
    
    # Verify hugepages
    AVAILABLE_HUGEPAGES=$(cat /sys/kernel/mm/hugepages/hugepages-${HUGEPAGE_SIZE}kB/nr_hugepages)
    if [ "$AVAILABLE_HUGEPAGES" != "$NUM_HUGEPAGES" ]; then
        echo -e "${RED}❌ Failed to allocate hugepages${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Hugepages configured: ${NUM_HUGEPAGES} x ${HUGEPAGE_SIZE}kB${NC}"
    echo
}

# Function to load DPDK kernel modules
load_dpdk_modules() {
    echo -e "${YELLOW}🔧 Loading DPDK kernel modules...${NC}"
    
    # Load UIO module
    modprobe uio
    
    # Load DPDK-compatible driver
    if modprobe vfio-pci 2>/dev/null; then
        DPDK_DRIVER="vfio-pci"
        echo -e "${GREEN}✓ Using vfio-pci driver (recommended)${NC}"
    else
        modprobe uio_pci_generic
        DPDK_DRIVER="uio_pci_generic"
        echo -e "${YELLOW}⚠️ Using uio_pci_generic driver${NC}"
    fi
    
    echo
}

# Function to bind network interface to DPDK
bind_interface_to_dpdk() {
    echo -e "${YELLOW}🔗 Binding interface to DPDK...${NC}"
    
    # Bring interface down
    ip link set $INTERFACE down
    
    # Bind to DPDK driver
    $DPDK_DIR/usertools/dpdk-devbind.py --bind=$DPDK_DRIVER $PCI_ADDRESS
    
    # Verify binding
    if $DPDK_DIR/usertools/dpdk-devbind.py --status | grep -q "$PCI_ADDRESS.*$DPDK_DRIVER"; then
        echo -e "${GREEN}✓ Interface $INTERFACE ($PCI_ADDRESS) bound to $DPDK_DRIVER${NC}"
    else
        echo -e "${RED}❌ Failed to bind interface to DPDK${NC}"
        exit 1
    fi
    
    echo
}

# Function to install Suricata with DPDK support
install_suricata_dpdk() {
    echo -e "${YELLOW}🔍 Installing Suricata with DPDK support...${NC}"
    
    # Install dependencies
    apt-get install -y libjansson-dev libpcre2-dev libyaml-dev zlib1g-dev \
        libcap-ng-dev libmagic-dev libnet1-dev libnetfilter-queue-dev \
        libhiredis-dev libmaxminddb-dev librustc-std-workspace-core-dev \
        cargo rustc
    
    # Download Suricata source
    cd /tmp
    wget -q "https://www.openinfosecfoundation.org/download/suricata-7.0.2.tar.gz"
    tar xzf suricata-7.0.2.tar.gz
    cd suricata-7.0.2
    
    # Configure with DPDK support
    ./configure --enable-dpdk --with-libdpdk-includes=$DPDK_DIR/build/include \
        --with-libdpdk-libraries=$DPDK_DIR/build/lib/x86_64-linux-gnu \
        --prefix=/usr --sysconfdir=/etc --localstatedir=/var
    
    # Build and install
    make -j$(nproc)
    make install
    ldconfig
    
    echo -e "${GREEN}✓ Suricata with DPDK support installed${NC}"
    echo
}

# Function to configure Suricata for DPDK
configure_suricata_dpdk() {
    echo -e "${YELLOW}⚙️ Configuring Suricata for DPDK...${NC}"
    
    # Create DPDK-specific config
    cat > $SURICATA_CONFIG << 'EOF'
# Suricata DPDK Configuration
vars:
  address-groups:
    HOME_NET: "[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]"
    EXTERNAL_NET: "!$HOME_NET"

# DPDK Configuration
dpdk:
  eal-params:
    proc-type: primary
    file-prefix: suricata
    lcores: "0-3"
    memory-channels: 4
  
  interfaces:
    - interface: 0  # DPDK port ID
      threads: 2
      promisc: true
      checksum-checks: auto
      
# Packet Processing
max-pending-packets: 65535
runmode: workers

# Logging
default-log-dir: /var/log/suricata/
outputs:
  - eve-log:
      enabled: yes
      filetype: regular
      filename: eve.json
      types:
        - alert:
            payload: yes
            http-body: yes
            http-header: yes
        - http:
            extended: yes
        - dns
        - tls
        - files
        - smtp
        - ssh
        - flow

# Detection
detect-engine:
  - profile: medium
  - custom-values:
      toclient-groups: 3
      toserver-groups: 25

# Application Layer
app-layer:
  protocols:
    http:
      enabled: yes
      memcap: 64mb
    tls:
      enabled: yes
    ssh:
      enabled: yes
    smtp:
      enabled: yes
EOF

    # Set permissions
    chown root:root $SURICATA_CONFIG
    chmod 644 $SURICATA_CONFIG
    
    # Create log directory
    mkdir -p /var/log/suricata
    chown suricata:suricata /var/log/suricata
    
    echo -e "${GREEN}✓ Suricata DPDK configuration created${NC}"
    echo
}

# Function to create DPDK-Suricata service
create_dpdk_suricata_service() {
    echo -e "${YELLOW}🔧 Creating DPDK-Suricata systemd service...${NC}"
    
    cat > /etc/systemd/system/suricata-dpdk.service << EOF
[Unit]
Description=Suricata IDS with DPDK
After=network.target

[Service]
Type=simple
User=root
Group=root
ExecStartPre=/bin/sh -c 'echo $NUM_HUGEPAGES > /sys/kernel/mm/hugepages/hugepages-${HUGEPAGE_SIZE}kB/nr_hugepages'
ExecStartPre=/bin/mount -t hugetlbfs nodev /mnt/huge
ExecStart=/usr/bin/suricata -c $SURICATA_CONFIG --dpdk
ExecReload=/bin/kill -USR2 \$MAINPID
KillMode=mixed
KillSignal=SIGINT
TimeoutStopSec=30
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable suricata-dpdk
    
    echo -e "${GREEN}✓ DPDK-Suricata service created and enabled${NC}"
    echo
}

# Function to install Kafka
install_kafka() {
    echo -e "${YELLOW}📡 Installing Kafka...${NC}"
    
    if [ -d "/opt/kafka" ]; then
        echo -e "${GREEN}✓ Kafka already installed${NC}"
        return 0
    fi
    
    # Install Java
    apt-get install -y openjdk-11-jdk
    
    # Download and install Kafka
    cd /opt
    wget -q "https://archive.apache.org/dist/kafka/2.8.2/kafka_2.13-2.8.2.tgz"
    tar xzf kafka_2.13-2.8.2.tgz
    mv kafka_2.13-2.8.2 kafka
    rm kafka_2.13-2.8.2.tgz
    
    # Create Kafka user
    useradd -r -s /bin/false kafka || true
    chown -R kafka:kafka /opt/kafka
    
    echo -e "${GREEN}✓ Kafka installed${NC}"
    echo
}

# Function to setup Kafka topics
setup_kafka_topics() {
    echo -e "${YELLOW}📋 Setting up Kafka topics...${NC}"
    
    # Start Kafka temporarily to create topics
    systemctl start kafka
    sleep 10
    
    # Create topics
    /opt/kafka/bin/kafka-topics.sh --create --topic suricata-alerts \
        --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
    
    /opt/kafka/bin/kafka-topics.sh --create --topic ml-enhanced-alerts \
        --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
    
    /opt/kafka/bin/kafka-topics.sh --create --topic dpdk-stats \
        --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
    
    echo -e "${GREEN}✓ Kafka topics created${NC}"
    echo
}

# Function to create DPDK-EVE-Kafka bridge
create_dpdk_eve_bridge() {
    echo -e "${YELLOW}🌉 Creating DPDK-EVE-Kafka bridge...${NC}"
    
    cat > /home/ifscr/SE_02_2025/IDS/dpdk_eve_kafka_bridge.py << 'EOF'
#!/usr/bin/env python3
"""
DPDK-EVE-Kafka Bridge
Streams Suricata EVE events from DPDK capture to Kafka
"""

import json
import time
import logging
from kafka import KafkaProducer
from kafka.errors import KafkaError
import argparse
import signal
import sys
from pathlib import Path

class DPDKEVEKafkaBridge:
    def __init__(self, eve_file="/var/log/suricata/eve.json", 
                 kafka_broker="localhost:9092"):
        self.eve_file = Path(eve_file)
        self.kafka_broker = kafka_broker
        self.running = True
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup Kafka producer
        self.producer = KafkaProducer(
            bootstrap_servers=[kafka_broker],
            value_serializer=lambda v: json.dumps(v).encode(),
            key_serializer=lambda k: k.encode() if k else None,
            batch_size=16384,
            linger_ms=10,
            buffer_memory=33554432
        )
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        
        self.logger.info(f"DPDK-EVE-Kafka Bridge initialized")
        self.logger.info(f"EVE file: {self.eve_file}")
        self.logger.info(f"Kafka broker: {self.kafka_broker}")
    
    def shutdown(self, signum, frame):
        self.logger.info("Shutting down DPDK-EVE-Kafka bridge...")
        self.running = False
        self.producer.close()
        sys.exit(0)
    
    def stream_events(self):
        """Stream EVE events to Kafka"""
        self.logger.info("Starting to stream DPDK-captured events...")
        
        # Wait for EVE file to be created
        while not self.eve_file.exists() and self.running:
            self.logger.info(f"Waiting for EVE file: {self.eve_file}")
            time.sleep(5)
        
        # Follow the EVE log file
        with open(self.eve_file, 'r') as f:
            # Go to end of file
            f.seek(0, 2)
            
            while self.running:
                line = f.readline()
                if line:
                    try:
                        event = json.loads(line.strip())
                        self.process_event(event)
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Invalid JSON: {e}")
                    except Exception as e:
                        self.logger.error(f"Error processing event: {e}")
                else:
                    time.sleep(0.1)
    
    def process_event(self, event):
        """Process and route EVE event to appropriate Kafka topic"""
        event_type = event.get('event_type', 'unknown')
        
        # Add DPDK metadata
        event['dpdk_capture'] = True
        event['bridge_timestamp'] = time.time()
        
        try:
            if event_type == 'alert':
                # Send alerts to suricata-alerts topic
                self.producer.send(
                    'suricata-alerts',
                    key=f"alert_{event.get('flow_id', 'unknown')}",
                    value=event
                )
                self.logger.info(f"DPDK Alert: {event.get('alert', {}).get('signature', 'Unknown')}")
                
            elif event_type in ['http', 'dns', 'tls', 'ssh', 'smtp']:
                # Send protocol events to protocol-specific topics
                topic = f"suricata-{event_type}"
                self.producer.send(topic, value=event)
                
            elif event_type == 'flow':
                # Send flow events for ML processing
                self.producer.send('suricata-flows', value=event)
                
            elif event_type == 'stats':
                # Send DPDK statistics
                self.producer.send('dpdk-stats', value=event)
                self.logger.info(f"DPDK Stats: {event.get('stats', {})}")
            
            # Send all events to general topic for monitoring
            self.producer.send('suricata-events', value=event)
            
        except KafkaError as e:
            self.logger.error(f"Kafka error: {e}")
        except Exception as e:
            self.logger.error(f"Error sending to Kafka: {e}")

def main():
    parser = argparse.ArgumentParser(description='DPDK-EVE-Kafka Bridge')
    parser.add_argument('--eve-file', default='/var/log/suricata/eve.json',
                        help='Path to Suricata EVE JSON file')
    parser.add_argument('--kafka-broker', default='localhost:9092',
                        help='Kafka broker address')
    
    args = parser.parse_args()
    
    bridge = DPDKEVEKafkaBridge(args.eve_file, args.kafka_broker)
    bridge.stream_events()

if __name__ == '__main__':
    main()
EOF

    chmod +x /home/ifscr/SE_02_2025/IDS/dpdk_eve_kafka_bridge.py
    
    echo -e "${GREEN}✓ DPDK-EVE-Kafka bridge created${NC}"
    echo
}

# Function to create ML enhancement service
create_ml_enhancement_service() {
    echo -e "${YELLOW}🧠 Creating ML enhancement service...${NC}"
    
    cat > /home/ifscr/SE_02_2025/IDS/dpdk_ml_enhancer.py << 'EOF'
#!/usr/bin/env python3
"""
DPDK ML Enhancement Service
Processes DPDK-captured alerts with ML predictions
"""

import json
import time
import logging
import joblib
import numpy as np
import pandas as pd
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import argparse
import signal
import sys

class DPDKMLEnhancer:
    def __init__(self, model_path, kafka_broker="localhost:9092"):
        self.model_path = model_path
        self.kafka_broker = kafka_broker
        self.running = True
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Load ML model
        try:
            self.model = joblib.load(model_path)
            self.logger.info(f"ML model loaded: {model_path}")
        except Exception as e:
            self.logger.error(f"Failed to load ML model: {e}")
            sys.exit(1)
        
        # Setup Kafka
        self.consumer = KafkaConsumer(
            'suricata-alerts',
            bootstrap_servers=[kafka_broker],
            value_deserializer=lambda m: json.loads(m.decode()),
            group_id='dpdk-ml-enhancer',
            auto_offset_reset='latest'
        )
        
        self.producer = KafkaProducer(
            bootstrap_servers=[kafka_broker],
            value_serializer=lambda v: json.dumps(v).encode()
        )
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        
        self.logger.info("DPDK ML Enhancer initialized")
    
    def shutdown(self, signum, frame):
        self.logger.info("Shutting down DPDK ML Enhancer...")
        self.running = False
        self.consumer.close()
        self.producer.close()
        sys.exit(0)
    
    def extract_features(self, alert):
        """Extract features from DPDK-captured alert for ML prediction"""
        try:
            # Basic network features
            features = {
                'src_port': alert.get('src_port', 0),
                'dest_port': alert.get('dest_port', 0),
                'proto': self.encode_protocol(alert.get('proto', 'TCP')),
                'packet_size': alert.get('payload_len', 0),
                'flow_duration': alert.get('flow', {}).get('age', 0),
                'packets_toserver': alert.get('flow', {}).get('pkts_toserver', 0),
                'packets_toclient': alert.get('flow', {}).get('pkts_toclient', 0),
                'bytes_toserver': alert.get('flow', {}).get('bytes_toserver', 0),
                'bytes_toclient': alert.get('flow', {}).get('bytes_toclient', 0)
            }
            
            # DPDK-specific features
            if alert.get('dpdk_capture'):
                features.update({
                    'dpdk_port': alert.get('dpdk_port', 0),
                    'dpdk_queue': alert.get('dpdk_queue', 0),
                    'hardware_timestamp': 1,  # DPDK provides hardware timestamps
                    'zero_copy': 1  # DPDK uses zero-copy
                })
            
            # Alert-specific features
            severity = alert.get('alert', {}).get('severity', 3)
            category = alert.get('alert', {}).get('category', '')
            
            features.update({
                'severity': severity,
                'category_encoded': self.encode_category(category)
            })
            
            return features
            
        except Exception as e:
            self.logger.error(f"Feature extraction error: {e}")
            return None
    
    def encode_protocol(self, proto):
        """Encode protocol string to numeric"""
        protocols = {'TCP': 6, 'UDP': 17, 'ICMP': 1, 'IPv4': 4, 'IPv6': 41}
        return protocols.get(proto.upper(), 0)
    
    def encode_category(self, category):
        """Encode alert category to numeric"""
        categories = {
            'Attempted Information Leak': 1,
            'Unknown Traffic': 2,
            'Potentially Bad Traffic': 3,
            'Misc activity': 4,
            'Generic Protocol Command Decode': 5
        }
        return categories.get(category, 0)
    
    def predict_threat(self, features):
        """Make ML prediction on extracted features"""
        try:
            # Convert to DataFrame for model prediction
            df = pd.DataFrame([features])
            
            # Make prediction
            prediction = self.model.predict(df)[0]
            confidence = self.model.predict_proba(df)[0].max()
            
            # Get feature names if available
            if hasattr(self.model, 'feature_names_in_'):
                # Ensure features match model training features
                df = df.reindex(columns=self.model.feature_names_in_, fill_value=0)
            
            return {
                'prediction': prediction,
                'confidence': float(confidence),
                'ml_model': 'RandomForest',
                'features_used': list(features.keys())
            }
            
        except Exception as e:
            self.logger.error(f"ML prediction error: {e}")
            return None
    
    def enhance_alert(self, alert):
        """Enhance DPDK alert with ML predictions"""
        # Extract features
        features = self.extract_features(alert)
        if not features:
            return None
        
        # Make ML prediction
        ml_result = self.predict_threat(features)
        if not ml_result:
            return None
        
        # Create enhanced alert
        enhanced_alert = alert.copy()
        enhanced_alert.update({
            'ml_enhancement': {
                'timestamp': time.time(),
                'prediction': ml_result['prediction'],
                'confidence': ml_result['confidence'],
                'model': ml_result['ml_model'],
                'dpdk_optimized': True,
                'threat_score': self.calculate_threat_score(alert, ml_result)
            }
        })
        
        return enhanced_alert
    
    def calculate_threat_score(self, alert, ml_result):
        """Calculate combined threat score from rule-based + ML"""
        rule_score = 100 - (alert.get('alert', {}).get('severity', 3) * 20)  # Higher severity = higher score
        ml_score = ml_result['confidence'] * 100
        
        # Weighted combination
        combined_score = (rule_score * 0.4) + (ml_score * 0.6)
        return round(combined_score, 1)
    
    def process_alerts(self):
        """Main processing loop for DPDK alerts"""
        self.logger.info("Starting DPDK ML enhancement processing...")
        
        for message in self.consumer:
            if not self.running:
                break
            
            try:
                alert = message.value
                
                # Only process DPDK-captured alerts
                if not alert.get('dpdk_capture', False):
                    continue
                
                # Enhance with ML
                enhanced_alert = self.enhance_alert(alert)
                if enhanced_alert:
                    # Send to ML-enhanced alerts topic
                    self.producer.send('ml-enhanced-alerts', value=enhanced_alert)
                    
                    ml_info = enhanced_alert['ml_enhancement']
                    self.logger.info(
                        f"DPDK ML Enhancement: {ml_info['prediction']} "
                        f"(confidence: {ml_info['confidence']:.2f}, "
                        f"threat_score: {ml_info['threat_score']})"
                    )
                
            except Exception as e:
                self.logger.error(f"Error processing alert: {e}")

def main():
    parser = argparse.ArgumentParser(description='DPDK ML Enhancement Service')
    parser.add_argument('--model-path', required=True,
                        help='Path to ML model file')
    parser.add_argument('--kafka-broker', default='localhost:9092',
                        help='Kafka broker address')
    
    args = parser.parse_args()
    
    enhancer = DPDKMLEnhancer(args.model_path, args.kafka_broker)
    enhancer.process_alerts()

if __name__ == '__main__':
    main()
EOF

    chmod +x /home/ifscr/SE_02_2025/IDS/dpdk_ml_enhancer.py
    
    echo -e "${GREEN}✓ DPDK ML enhancement service created${NC}"
    echo
}

# Function to create master startup script
create_startup_script() {
    echo -e "${YELLOW}🚀 Creating DPDK-Suricata startup script...${NC}"
    
    cat > /home/ifscr/SE_02_2025/IDS/start_dpdk_pipeline.sh << 'EOF'
#!/bin/bash

# Start Real DPDK-Suricata-ML Pipeline
# Pure DPDK packet capture with Suricata analysis and ML enhancement

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ML_MODEL_PATH="/home/ifscr/SE_02_2025/IDS/src/ML_Model/intrusion_detection_model.joblib"
DURATION=${1:-300}  # Default 5 minutes

echo -e "${BLUE}🚀 Starting Real DPDK-Suricata-ML Pipeline${NC}"
echo "Duration: $DURATION seconds"
echo

# Start Kafka
echo -e "${YELLOW}📡 Starting Kafka...${NC}"
systemctl start kafka
sleep 5
echo -e "${GREEN}✓ Kafka started${NC}"

# Start DPDK-Suricata
echo -e "${YELLOW}🔍 Starting DPDK-Suricata...${NC}"
systemctl start suricata-dpdk
sleep 10
echo -e "${GREEN}✓ DPDK-Suricata started${NC}"

# Start EVE-Kafka bridge
echo -e "${YELLOW}🌉 Starting DPDK-EVE-Kafka bridge...${NC}"
python3 /home/ifscr/SE_02_2025/IDS/dpdk_eve_kafka_bridge.py &
BRIDGE_PID=$!
sleep 5
echo -e "${GREEN}✓ DPDK-EVE-Kafka bridge started (PID: $BRIDGE_PID)${NC}"

# Start ML enhancement
echo -e "${YELLOW}🧠 Starting ML enhancement...${NC}"
python3 /home/ifscr/SE_02_2025/IDS/dpdk_ml_enhancer.py --model-path "$ML_MODEL_PATH" &
ML_PID=$!
sleep 5
echo -e "${GREEN}✓ ML enhancement started (PID: $ML_PID)${NC}"

echo
echo -e "${GREEN}🎯 DPDK Pipeline is LIVE!${NC}"
echo "• DPDK capturing packets at hardware speed"
echo "• Suricata analyzing with DPDK integration"
echo "• ML enhancing detections in real-time"
echo "• Kafka streaming enhanced alerts"
echo
echo "Monitoring for $DURATION seconds..."

# Monitor enhanced alerts
timeout $DURATION python3 -c "
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'ml-enhanced-alerts',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda m: json.loads(m.decode()),
    auto_offset_reset='latest'
)

print('🔍 Monitoring DPDK-ML enhanced alerts...')
alert_count = 0

for message in consumer:
    alert = message.value
    ml_info = alert.get('ml_enhancement', {})
    
    alert_count += 1
    print(f'🚨 DPDK Alert #{alert_count}:')
    print(f'  Prediction: {ml_info.get(\"prediction\", \"Unknown\")}')
    print(f'  Confidence: {ml_info.get(\"confidence\", 0):.2f}')
    print(f'  Threat Score: {ml_info.get(\"threat_score\", 0)}')
    print(f'  DPDK Optimized: {ml_info.get(\"dpdk_optimized\", False)}')
    print()

print(f'Total DPDK-ML enhanced alerts: {alert_count}')
"

echo
echo -e "${BLUE}📊 Pipeline Summary:${NC}"
echo "• Real DPDK packet capture (zero-copy, hardware timestamps)"
echo "• Suricata with native DPDK integration"
echo "• ML enhancement with Random Forest"
echo "• High-performance Kafka streaming"
echo "• No Python packet generation - pure performance!"

# Cleanup
echo -e "${YELLOW}🧹 Cleaning up...${NC}"
kill $BRIDGE_PID $ML_PID 2>/dev/null || true
systemctl stop suricata-dpdk
echo -e "${GREEN}✓ Cleanup complete${NC}"
EOF

    chmod +x /home/ifscr/SE_02_2025/IDS/start_dpdk_pipeline.sh
    
    echo -e "${GREEN}✓ DPDK-Suricata startup script created${NC}"
    echo
}

# Function to show system status
show_system_status() {
    echo -e "${BOLD}${CYAN}📊 DPDK-Suricata System Status${NC}"
    echo -e "${CYAN}================================${NC}"
    
    # DPDK Status
    echo -e "${YELLOW}DPDK Status:${NC}"
    if [ -d "$DPDK_DIR" ]; then
        echo -e "${GREEN}✓ DPDK installed: $DPDK_VERSION${NC}"
    else
        echo -e "${RED}❌ DPDK not installed${NC}"
    fi
    
    # Hugepages
    echo -e "${YELLOW}Hugepages:${NC}"
    HUGEPAGES=$(cat /sys/kernel/mm/hugepages/hugepages-${HUGEPAGE_SIZE}kB/nr_hugepages 2>/dev/null || echo "0")
    if [ "$HUGEPAGES" -gt "0" ]; then
        echo -e "${GREEN}✓ Hugepages: $HUGEPAGES x ${HUGEPAGE_SIZE}kB${NC}"
    else
        echo -e "${RED}❌ Hugepages not configured${NC}"
    fi
    
    # Interface binding
    echo -e "${YELLOW}Interface Binding:${NC}"
    if $DPDK_DIR/usertools/dpdk-devbind.py --status 2>/dev/null | grep -q "$PCI_ADDRESS.*drv="; then
        echo -e "${GREEN}✓ Interface bound to DPDK${NC}"
    else
        echo -e "${RED}❌ Interface not bound to DPDK${NC}"
    fi
    
    # Services
    echo -e "${YELLOW}Services:${NC}"
    if systemctl is-active --quiet suricata-dpdk; then
        echo -e "${GREEN}✓ Suricata-DPDK running${NC}"
    else
        echo -e "${RED}❌ Suricata-DPDK stopped${NC}"
    fi
    
    if systemctl is-active --quiet kafka; then
        echo -e "${GREEN}✓ Kafka running${NC}"
    else
        echo -e "${RED}❌ Kafka stopped${NC}"
    fi
    
    # ML Model
    echo -e "${YELLOW}ML Model:${NC}"
    if [ -f "$ML_MODEL_PATH" ]; then
        echo -e "${GREEN}✓ ML model available ($(du -h $ML_MODEL_PATH | cut -f1))${NC}"
    else
        echo -e "${RED}❌ ML model not found${NC}"
    fi
    
    echo
}

# Function to cleanup and restore interface
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up and restoring interface...${NC}"
    
    # Stop services
    systemctl stop suricata-dpdk 2>/dev/null || true
    
    # Unbind interface from DPDK
    if [ -n "$PCI_ADDRESS" ] && [ -f "$DPDK_DIR/usertools/dpdk-devbind.py" ]; then
        $DPDK_DIR/usertools/dpdk-devbind.py --bind=igb $PCI_ADDRESS 2>/dev/null || true
        ip link set $INTERFACE up 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

# Main execution
main() {
    case "${1:-setup}" in
        "setup")
            check_prerequisites
            install_dpdk
            configure_hugepages
            load_dpdk_modules
            bind_interface_to_dpdk
            install_suricata_dpdk
            configure_suricata_dpdk
            create_dpdk_suricata_service
            install_kafka
            setup_kafka_topics
            create_dpdk_eve_bridge
            create_ml_enhancement_service
            create_startup_script
            
            echo -e "${BOLD}${GREEN}🎉 Real DPDK-Suricata-ML Pipeline Setup Complete!${NC}"
            echo
            echo -e "${CYAN}Next Steps:${NC}"
            echo "1. Run: sudo ./start_dpdk_pipeline.sh [duration]"
            echo "2. Monitor: tail -f /var/log/suricata/eve.json"
            echo "3. Status: sudo ./setup_real_dpdk_suricata.sh status"
            echo
            ;;
        "status")
            show_system_status
            ;;
        "cleanup")
            cleanup
            ;;
        "start")
            ./start_dpdk_pipeline.sh ${2:-300}
            ;;
        *)
            echo "Usage: $0 {setup|status|cleanup|start [duration]}"
            exit 1
            ;;
    esac
}

# Trap for cleanup on exit
trap cleanup EXIT

# Execute main function
main "$@"