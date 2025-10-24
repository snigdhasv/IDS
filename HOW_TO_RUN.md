# 🚀 How to Run the IDS Pipeline - Complete Guide

## 📋 Table of Contents
- [System Requirements](#system-requirements)
- [Quick Start (5 minutes)](#quick-start-5-minutes)
- [Detailed Setup](#detailed-setup)
- [Running the Pipeline](#running-the-pipeline)
- [Testing & Verification](#testing--verification)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

### Hardware
- **CPU**: 2+ cores minimum (4+ recommended)
- **RAM**: 4GB minimum (8GB recommended)
- **Storage**: 20GB free space (for logs and data)
- **Network Interface**: Any for AF_PACKET, DPDK-compatible for DPDK mode

### Software
- **OS**: Linux (Ubuntu 18.04+, CentOS 7+, Debian 10+)
- **Python**: 3.8 or higher
- **Suricata**: 5.0 or higher
- **Kafka**: 2.8 or higher
- **Docker** (optional, for containerized setup)

### Network Access
- Internet access for downloading dependencies
- Root/sudo privileges required

---

## Quick Start (5 minutes)

### For AF_PACKET Mode (Recommended for Most Users)

```bash
# 1. Navigate to the IDS directory
cd /home/sujay/Programming/IDS

# 2. Make scripts executable (if not already)
chmod +x run_afpacket_mode.sh
chmod +x dpdk_suricata_ml_pipeline/scripts/*.sh

# 3. Run the interactive menu
sudo ./run_afpacket_mode.sh

# 4. Select option 1 (Start Complete Pipeline)
# This starts:
#   - Kafka broker
#   - Suricata IDS (AF_PACKET mode)
#   - Kafka bridge
#   - ML consumer

# 5. Check status
sudo ./run_afpacket_mode.sh status

# 6. View logs
sudo ./run_afpacket_mode.sh logs
```

That's it! The pipeline is now running! ✅

---

## Detailed Setup

### Step 1: Prerequisites Installation

#### Ubuntu/Debian
```bash
# Update package list
sudo apt update

# Install required packages
sudo apt install -y \
    build-essential \
    git \
    curl \
    wget \
    python3 \
    python3-pip \
    python3-dev \
    libssl-dev \
    libffi-dev \
    pkg-config

# Install Suricata
sudo apt install -y suricata

# Verify Suricata installation
suricata --version
```

#### CentOS/RHEL
```bash
# Install required packages
sudo yum groupinstall -y "Development Tools"
sudo yum install -y \
    git \
    curl \
    wget \
    python3 \
    python3-pip \
    python3-devel \
    openssl-devel \
    libffi-devel \
    pkgconfig

# Install Suricata (from EPEL)
sudo yum install -y epel-release
sudo yum install -y suricata
```

### Step 2: Install Python Dependencies

```bash
# Navigate to IDS directory
cd /home/sujay/Programming/IDS

# Install Python packages
pip install -r requirements.txt

# Verify installations
python3 -c "import kafka, sklearn, numpy; print('✓ All packages installed')"
```

### Step 3: Install & Setup Kafka

```bash
# Download Kafka
wget https://archive.apache.org/dist/kafka/3.0.0/kafka_2.13-3.0.0.tgz

# Extract
tar -xzf kafka_2.13-3.0.0.tgz
sudo mv kafka_2.13-3.0.0 /usr/local/kafka

# Add to PATH
echo 'export PATH=$PATH:/usr/local/kafka/bin' >> ~/.bashrc
source ~/.bashrc

# Verify
kafka-broker-api-versions.sh --bootstrap-server localhost:9092 2>/dev/null && echo "✓ Kafka ready" || echo "⚠️ Kafka not running yet"
```

### Step 4: Configure Network Interface

```bash
# List available network interfaces
ip link show

# Find your interface name (e.g., eth0, enp3s0, enx00e04c36074c)
# Edit the configuration file
nano /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf

# Change this line:
# NETWORK_INTERFACE="enx00e04c36074c"  ← Replace with YOUR interface name

# Save and exit (Ctrl+X, Y, Enter)
```

### Step 5: Verify Configuration

```bash
# Check if your interface exists
ip link show YOUR_INTERFACE

# Should show output like:
# 3: YOUR_INTERFACE: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500

# If not UP, bring it up:
sudo ip link set YOUR_INTERFACE up
```

---

## Running the Pipeline

### Option 1: AF_PACKET Mode (Easy)

#### Interactive Menu
```bash
cd /home/sujay/Programming/IDS
sudo ./run_afpacket_mode.sh

# Menu options:
# 1) Start Complete Pipeline
# 2) Start Kafka Only
# 3) Start Suricata Only
# 4) Start ML Consumer Only
# 5) Start Kafka Bridge Only
# 6) Replay Traffic (PCAP)
# 7) Check Status
# 8) View Logs
# 9) Setup External Capture
# 10) Stop All Services
# 0) Exit
```

#### Direct Commands
```bash
# Start everything
sudo ./run_afpacket_mode.sh start

# Start individual components
sudo ./run_afpacket_mode.sh kafka
sudo ./run_afpacket_mode.sh suricata
sudo ./run_afpacket_mode.sh ml
sudo ./run_afpacket_mode.sh bridge

# Check status
sudo ./run_afpacket_mode.sh status

# View logs
sudo ./run_afpacket_mode.sh logs

# Stop all
sudo ./run_afpacket_mode.sh stop
```

### Option 2: DPDK Mode (Advanced)

#### Prerequisites for DPDK
```bash
# Check if DPDK-compatible NIC is available
lspci | grep -i "ethernet\|network"

# You need Intel X710, Mellanox ConnectX, or similar

# Configure hugepages
echo 1024 > /proc/sys/vm/nr_hugepages
mkdir -p /mnt/huge
mount -t hugetlbfs nodev /mnt/huge

# Install DPDK
sudo apt install -y dpdk dpdk-dev
```

#### Run DPDK Pipeline
```bash
cd /home/sujay/Programming/IDS
sudo ./run_dpdk_mode.sh

# Menu options:
# 1) Start Complete Pipeline (includes binding)
# 2) Start Kafka Only
# 3) Start Suricata Only
# 4) Start ML Consumer Only
# 5) Start Kafka Bridge Only
# 6) Bind Interface to DPDK
# 7) Unbind Interface from DPDK
# 8) Check Status
# 9) View Logs
# 10) Show DPDK Info
# 11) Stop All Services
# 0) Exit

# Direct commands
sudo ./run_dpdk_mode.sh start
sudo ./run_dpdk_mode.sh status
sudo ./run_dpdk_mode.sh stop
```

---

## Testing & Verification

### Test 1: Verify All Services Running

```bash
# Check Kafka
ps aux | grep kafka | grep -v grep

# Check Suricata
ps aux | grep suricata | grep -v grep

# Check ML Consumer
ps aux | grep ml_kafka_consumer | grep -v grep

# Check Kafka Bridge
ps aux | grep suricata_kafka_bridge | grep -v grep
```

### Test 2: Generate Test Traffic

```bash
# Create test traffic
cd /home/sujay/Programming/IDS/tests

# Option A: Benign traffic
python3 test_benign_traffic.py

# Option B: Attack traffic
python3 test_attack_generator.py

# Option C: DPDK-specific test
python3 test_dpdk_scapy_integration.py

# Option D: ML classification test
python3 test_ml_classifications.py
```

### Test 3: Verify ML Predictions

```bash
# Check if ML predictions are being generated
python3 << 'EOF'
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'ml-predictions',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='latest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

print("Listening for ML predictions...")
print("(This will block. Press Ctrl+C to exit)")

for message in consumer:
    print(f"\nPrediction: {json.dumps(message.value, indent=2)}")
    break  # Exit after first message

consumer.close()
EOF
```

### Test 4: Check Suricata Alerts

```bash
# View Suricata EVE JSON logs
tail -f /var/log/suricata/eve.json

# Filter for alerts only
tail -f /var/log/suricata/eve.json | grep '"event_type":"alert"'
```

---

## Troubleshooting

### Issue 1: "Permission denied" when running script

**Solution:**
```bash
# Make script executable
chmod +x /home/sujay/Programming/IDS/run_afpacket_mode.sh
chmod +x /home/sujay/Programming/IDS/run_dpdk_mode.sh

# Ensure you're using sudo
sudo ./run_afpacket_mode.sh
```

### Issue 2: "Network interface not found"

**Solution:**
```bash
# List all interfaces
ip link show

# Edit config file
nano /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf

# Update NETWORK_INTERFACE to match your interface

# Bring interface up if needed
sudo ip link set YOUR_INTERFACE up
```

### Issue 3: "Kafka not running"

**Solution:**
```bash
# Start Kafka manually
cd /usr/local/kafka
bin/kafka-server-start.sh config/server.properties &

# Or restart using the script
sudo ./run_afpacket_mode.sh kafka

# Check if it's running
ps aux | grep kafka
```

### Issue 4: "Suricata not installed" or "DPDK support missing"

**Solution:**
```bash
# Check Suricata version
suricata --version

# Check DPDK support (if needed)
suricata --build-info | grep DPDK

# If DPDK support missing, rebuild Suricata with DPDK:
# (This is complex - see PRODUCTION_DPDK_GUIDE.md)
```

### Issue 5: "Port 9092 already in use"

**Solution:**
```bash
# Find process using port
sudo lsof -i :9092

# Kill the process
sudo kill -9 <PID>

# Or change Kafka port in config:
nano /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf
# Edit: KAFKA_BOOTSTRAP_SERVERS="localhost:9093"
```

### Issue 6: High CPU usage or packet loss

**Solution for AF_PACKET:**
```bash
# Increase number of Suricata threads
# Edit pipeline.conf and increase SURICATA_CORES
# Then restart Suricata

# Increase network buffer sizes
sudo ethtool -G YOUR_INTERFACE rx 4096
sudo ethtool -G YOUR_INTERFACE tx 4096

# Disable CPU power management
echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

**Solution for DPDK:**
```bash
# Increase hugepages
echo 2048 > /proc/sys/vm/nr_hugepages

# Isolate CPU cores (add to /etc/default/grub):
GRUB_CMDLINE_LINUX="isolcpus=2,3,4,5"
sudo update-grub
sudo reboot

# Use higher memory channels
# Edit pipeline.conf: DPDK_MEMORY_CHANNELS="4"
```

### Issue 7: "No alerts being generated"

**Solution:**
```bash
# Check if Suricata rules are loaded
sudo tail -f /var/log/suricata/suricata.log | grep -i "rule"

# Check if traffic is being captured
sudo tcpdump -i YOUR_INTERFACE -c 10

# Verify Kafka bridge is running
ps aux | grep suricata_kafka_bridge

# Check Kafka topics
kafka-topics.sh --bootstrap-server localhost:9092 --list

# Check if messages are in Kafka
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
    --topic suricata-alerts --from-beginning
```

---

## Workflow Example: Step by Step

### Complete Example: Start to Alert

```bash
# ============================================
# STEP 1: Navigate to project
# ============================================
cd /home/sujay/Programming/IDS
ls -la

# ============================================
# STEP 2: Configure interface
# ============================================
ip link show                          # Find your interface
nano dpdk_suricata_ml_pipeline/config/pipeline.conf
# Change: NETWORK_INTERFACE="eth0"   (or your interface)
# Save: Ctrl+X, Y, Enter

# ============================================
# STEP 3: Start the pipeline
# ============================================
sudo ./run_afpacket_mode.sh           # Interactive menu
# Select: 1 (Start Complete Pipeline)
# Wait 10 seconds for all components to start

# ============================================
# STEP 4: Verify everything is running
# ============================================
sudo ./run_afpacket_mode.sh status
# You should see:
# ✓ Kafka: Running
# ✓ Suricata (AF_PACKET): Running
# ✓ Kafka Bridge: Running
# ✓ ML Consumer: Running

# ============================================
# STEP 5: Generate test traffic
# ============================================
cd tests/
python3 test_attack_generator.py      # Generate attack traffic
# Or in another terminal:
# python3 test_benign_traffic.py

# ============================================
# STEP 6: View alerts in real-time
# ============================================
# Terminal 1: Suricata alerts
tail -f /var/log/suricata/eve.json | grep alert

# Terminal 2: ML predictions
cd .. && python3 << 'EOF'
from kafka import KafkaConsumer
import json
consumer = KafkaConsumer('ml-predictions', 
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='latest')
for msg in consumer:
    print(json.dumps(json.loads(msg.value), indent=2))
EOF

# ============================================
# STEP 7: Stop when done
# ============================================
sudo ./run_afpacket_mode.sh stop
```

---

## Performance Tuning

### For Better Detection Accuracy
```bash
# Lower confidence threshold (more alerts)
nano dpdk_suricata_ml_pipeline/config/pipeline.conf
# Change: ML_CONFIDENCE_THRESHOLD="0.5"  # was 0.7

# Enable more Suricata rules
# Edit Suricata config to enable all threat rules
```

### For Better Performance
```bash
# Increase batch size
nano dpdk_suricata_ml_pipeline/config/pipeline.conf
# Change: ML_BATCH_SIZE="500"  # was 100

# Disable detailed logging
# Change: LOG_LEVEL="WARNING"   # was INFO

# Use DPDK mode (if hardware supports)
sudo ./run_dpdk_mode.sh start
```

---

## Advanced Usage

### Using with External Attacks
```bash
# Setup to receive traffic from external device
sudo ./run_afpacket_mode.sh setup  # option 9

# On external device (e.g., your laptop):
# Configure IP: 192.168.100.2/24
# Capture packets and send to: 192.168.100.1

# See EXTERNAL_TRAFFIC_GUIDE.md for details
```

### Replaying PCAP Files
```bash
# Replay captured traffic
sudo ./run_afpacket_mode.sh replay  # option 6

# Or manually
tcpreplay -i YOUR_INTERFACE traffic_sample.pcap
```

### Custom Attack Testing
```bash
# Generate specific attacks
cd tests/

# DDoS attack
python3 test_attack_generator.py ddos

# Port scan
python3 test_attack_generator.py portscan

# Bot traffic
python3 test_attack_generator.py botnet
```

---

## Next Steps

After running successfully:

1. ✅ Read `PIPELINE_ARCHITECTURE.md` - Understand how it works
2. ✅ Read `NEXT_STEPS.md` - See what's next
3. ✅ Setup dashboard - Add Kibana/Grafana for visualization
4. ✅ Tune for your environment - Adjust thresholds and rules
5. ✅ Deploy to production - Consider containerization with Docker

---

## Getting Help

**Script not working?**
- Check: `sudo ./run_afpacket_mode.sh status`
- Logs: `sudo ./run_afpacket_mode.sh logs`
- Troubleshooting: See section above

**Questions about architecture?**
- Read: `PIPELINE_ARCHITECTURE.md`
- Review: `QUICKSTART.md`
- Check: `README.md`

**Ideas for improvements?**
- See: `NEXT_STEPS.md`
- Contribute: Create GitHub issue

---

**Happy threat hunting! 🔐🚀**

For detailed architecture info, see `PIPELINE_ARCHITECTURE.md`
For project roadmap, see `NEXT_STEPS.md`
