# 🚀 IDS Pipeline Runtime Guide

**Last Updated**: October 3, 2025  
**Status**: Production Ready

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites Check](#prerequisites-check)
3. [Step-by-Step Execution](#step-by-step-execution)
4. [Monitoring & Verification](#monitoring--verification)
5. [Troubleshooting](#troubleshooting)
6. [Stopping the Pipeline](#stopping-the-pipeline)

---

## 🎯 Quick Start

### For the Impatient:

```bash
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts

# 1. Start Kafka
./02_setup_kafka.sh

# 2. Check status
./status_check.sh

# 3. Activate Python environment and start ML consumer
cd ..
source ../venv/bin/activate
python src/ml_kafka_consumer.py --config config/pipeline.conf

# 4. (In another terminal) Replay traffic
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
./05_replay_traffic.sh
```

**Note**: This assumes Suricata is already configured and running. For first-time setup, follow the detailed steps below.

---

## ✅ Prerequisites Check

### 1. Verify Installation

Run the status check script:

```bash
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
./status_check.sh
```

### 2. Expected Status

✅ **DPDK**: Installed (device binding optional for testing)  
✅ **Hugepages**: Allocated (check `/proc/meminfo`)  
✅ **Kafka**: Ready to start  
✅ **Suricata**: Installed with DPDK support  
✅ **Python venv**: Activated with all packages  
✅ **ML Models**: Available in `/home/sujay/Programming/IDS/ML Models/`

### 3. Check Python Environment

```bash
source /home/sujay/Programming/IDS/venv/bin/activate
python -c "import kafka, pandas, sklearn, joblib; print('✅ All packages available')"
```

### 4. Check ML Models

```bash
ls -lh /home/sujay/Programming/IDS/ML\ Models/
```

Expected output:
- `random_forest_model_2017.joblib` (~2.0 MB)
- `lgb_model_2018.joblib` (~801 KB)

---

## 🏃 Step-by-Step Execution

### Step 1: Start Kafka Broker

Kafka is the message bus between Suricata and the ML engine.

```bash
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
./02_setup_kafka.sh
```

**What this does:**
- Downloads and installs Kafka (if not present)
- Starts Zookeeper (port 2181)
- Starts Kafka broker (port 9092)
- Creates required topics: `suricata-alerts`, `ml-predictions`

**Wait time:** ~30 seconds for Kafka to fully start

**Verification:**
```bash
# Check if Kafka is running
netstat -tuln | grep 9092

# List topics
kafka-topics.sh --list --bootstrap-server localhost:9092
```

Expected topics:
- `suricata-alerts` (input from Suricata)
- `ml-predictions` (output from ML engine)

---

### Step 2: (Optional) Bind Network Interface to DPDK

⚠️ **WARNING:** This takes your network interface offline!

**Only do this if:**
- You have a dedicated NIC for packet capture
- You're using physical traffic (not PCAP replay)
- You won't lose critical network connectivity

```bash
sudo ./01_bind_interface.sh
```

**For testing with PCAP replay, you can skip this step!**

---

### Step 3: Start Suricata IDS

#### Option A: Start Suricata with DPDK (for live traffic)

```bash
sudo ./03_start_suricata.sh
```

**What this does:**
- Starts Suricata in DPDK mode
- Captures packets from DPDK-bound interface
- Logs ALL network flows (not just alerts)
- Sends flows + alerts to Kafka topic `suricata-alerts`

#### Option B: Start Suricata in AF_PACKET mode (for PCAP testing)

If you don't want to bind a network interface:

```bash
# Start Suricata in AF_PACKET mode with Kafka output
sudo suricata -c /usr/local/etc/suricata/suricata.yaml \
              -i lo \
              --set outputs.1.eve-log.enabled=yes \
              --set outputs.1.eve-log.types.0.flow.enabled=yes \
              -v
```

**Verification:**
```bash
# Check Suricata is running
pgrep -a suricata

# Check Suricata logs
tail -f /var/log/suricata/suricata.log

# Check if events are reaching Kafka
kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic suricata-alerts \
    --from-beginning \
    --max-messages 5
```

---

### Step 4: Start ML Inference Consumer

This is the core ML engine that processes network flows.

#### Terminal Window 1: Start ML Consumer

```bash
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline

# Activate virtual environment
source ../venv/bin/activate

# Start ML consumer
python src/ml_kafka_consumer.py --config config/pipeline.conf
```

**What this does:**
- Consumes ALL flow events from Kafka topic `suricata-alerts`
- Extracts 65 CICIDS2017 features from each flow
- Performs real-time ML inference (Random Forest model)
- Correlates ML predictions with Suricata alerts
- Generates enhanced alerts with combined threat scores
- Publishes predictions to `ml-predictions` topic

**Expected output:**
```
🚀 Starting ML Kafka Consumer...
✅ Successfully loaded ML model: random_forest_model_2017.joblib
✅ Model type: RandomForestClassifier
✅ Connected to Kafka broker: localhost:9092
📊 Listening on topic: suricata-alerts
⏳ Waiting for flow events...

[INFO] Processed flow from 192.168.1.10:45123 -> 93.184.216.34:443
       Features extracted: 65/65
       ML Prediction: BENIGN (confidence: 0.98)
       Threat Score: 0.02
```

**Alternative with verbose logging:**

```bash
python src/ml_kafka_consumer.py \
    --config config/pipeline.conf \
    --model-path ../ML\ Models/random_forest_model_2017.joblib \
    --verbose
```

**Using LightGBM model instead:**

```bash
python src/ml_kafka_consumer.py \
    --config config/pipeline.conf \
    --model-path ../ML\ Models/lgb_model_2018.joblib
```

---

### Step 5: Generate/Replay Traffic

Now that everything is running, send some traffic through the pipeline.

#### Option A: Replay PCAP Files (Recommended for Testing)

```bash
# In a new terminal
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
./05_replay_traffic.sh
```

This replays sample PCAP files through the loopback interface.

#### Option B: Use Test Attack Generator

```bash
# Activate venv
source /home/sujay/Programming/IDS/venv/bin/activate

# Generate benign traffic
python tests/test_benign_traffic.py

# Generate attack traffic
python tests/test_attack_generator.py

# Generate various attack patterns
python tests/test_ml_attack_patterns.py
```

#### Option C: Live Traffic Capture

If you bound a physical interface to DPDK:

```bash
# Traffic will automatically flow through DPDK -> Suricata -> Kafka -> ML
# Just use the network normally or run a traffic generator
```

---

## 📊 Monitoring & Verification

### Check Pipeline Status

```bash
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
./status_check.sh
```

### Monitor Real-Time Logs

#### Suricata Logs:
```bash
# Main log
tail -f /var/log/suricata/suricata.log

# Statistics
tail -f /var/log/suricata/stats.log

# Eve log (JSON events)
tail -f /var/log/suricata/eve.json
```

#### ML Consumer Logs:
```bash
tail -f /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log
```

#### Kafka Topics:

**Monitor Suricata alerts (input to ML):**
```bash
kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic suricata-alerts \
    --from-beginning
```

**Monitor ML predictions (output from ML):**
```bash
kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic ml-predictions \
    --from-beginning
```

**Count messages in topics:**
```bash
kafka-run-class.sh kafka.tools.GetOffsetShell \
    --broker-list localhost:9092 \
    --topic suricata-alerts \
    --time -1
```

### Performance Metrics

#### Suricata Stats:
```bash
# Live capture stats
suricatasc -c "dump-counters" | jq .

# Drops, packets processed, etc.
cat /var/log/suricata/stats.log | grep -E "capture.kernel_packets|capture.kernel_drops"
```

#### ML Consumer Metrics:
The ML consumer logs processing metrics:
- Flows processed per second
- Feature extraction time
- Model inference time
- Alert correlation rate

---

## 🐛 Troubleshooting

### Issue 1: Kafka Won't Start

**Symptoms:** Port 9092 not listening, connection refused

**Solutions:**
```bash
# Check if Zookeeper is running first
netstat -tuln | grep 2181

# Kill existing Kafka processes
pkill -9 -f kafka

# Restart Kafka
./02_setup_kafka.sh

# Check logs
tail -f ~/kafka/logs/server.log
```

### Issue 2: Suricata Not Sending Events to Kafka

**Symptoms:** Kafka topic empty, ML consumer waiting

**Solutions:**
```bash
# 1. Verify Suricata eve-kafka output is enabled
grep -A 10 "eve-kafka" /usr/local/etc/suricata/suricata.yaml

# 2. Check Suricata can connect to Kafka
tail -f /var/log/suricata/suricata.log | grep -i kafka

# 3. Verify flow logging is enabled
grep -A 5 "types:" /usr/local/etc/suricata/suricata.yaml | grep flow

# 4. Restart Suricata
sudo pkill suricata
sudo ./03_start_suricata.sh
```

### Issue 3: ML Consumer Crashes or No Output

**Symptoms:** Python script exits, import errors

**Solutions:**
```bash
# 1. Check all Python packages are installed
source /home/sujay/Programming/IDS/venv/bin/activate
pip install -r /home/sujay/Programming/IDS/requirements.txt

# 2. Install missing packages if needed
pip install lightgbm  # If using LightGBM model

# 3. Verify model file exists and is readable
ls -lh /home/sujay/Programming/IDS/ML\ Models/*.joblib
python -c "import joblib; m = joblib.load('/home/sujay/Programming/IDS/ML Models/random_forest_model_2017.joblib'); print('✅ Model loaded')"

# 4. Check Kafka connection
python -c "from kafka import KafkaConsumer; c = KafkaConsumer(bootstrap_servers='localhost:9092'); print('✅ Kafka connected')"

# 5. Run with debug logging
python src/ml_kafka_consumer.py --config config/pipeline.conf --verbose
```

### Issue 4: No Traffic Flowing Through Pipeline

**Symptoms:** All components running, but no events

**Solutions:**
```bash
# 1. Verify Suricata is actually capturing packets
sudo suricatasc -c "capture-stat"

# 2. Check if interface is up (if using DPDK)
dpdk-devbind.py --status

# 3. For PCAP replay, check tcpreplay
tcpreplay --version
ifconfig lo  # Ensure loopback is up

# 4. Generate test traffic
ping -c 10 8.8.8.8  # Generate ICMP traffic
curl http://example.com  # Generate HTTP traffic

# 5. Check Suricata is processing
tail -f /var/log/suricata/stats.log | grep capture.kernel_packets
```

### Issue 5: DPDK Binding Fails

**Symptoms:** Interface won't bind, driver errors

**Solutions:**
```bash
# 1. Check hugepages are allocated
grep Huge /proc/meminfo

# 2. Allocate hugepages if needed
sudo sysctl -w vm.nr_hugepages=512

# 3. Load DPDK kernel modules
sudo modprobe vfio-pci
sudo modprobe uio_pci_generic

# 4. Check interface is not already bound
dpdk-devbind.py --status

# 5. Unbind and rebind
sudo dpdk-devbind.py -u 0000:00:03.0  # Replace with your interface
sudo dpdk-devbind.py -b vfio-pci 0000:00:03.0
```

### Issue 6: Feature Extraction Errors

**Symptoms:** ML consumer logs "Failed to extract features"

**Solutions:**
```bash
# 1. Check Suricata flow events have required fields
kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic suricata-alerts \
    --max-messages 1 | jq .

# 2. Verify flow events (not just alerts)
# Should see: event_type=flow, flow{}, tcp{}, ip{} fields

# 3. Check feature extractor code
python -c "from src.feature_extractor import CICIDS2017FeatureExtractor; print('✅ Feature extractor OK')"

# 4. Test feature extraction manually
python -c "
from src.feature_extractor import CICIDS2017FeatureExtractor
import json
fe = CICIDS2017FeatureExtractor()
# Test with sample event
event = {'event_type': 'flow', 'flow': {'start': '2024-01-01T00:00:00', 'end': '2024-01-01T00:00:10'}}
features = fe.extract(event)
print(f'✅ Extracted {len(features)} features')
"
```

---

## 🛑 Stopping the Pipeline

### Clean Shutdown

```bash
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
./stop_all.sh
```

This will:
1. Stop ML consumer
2. Stop Suricata
3. Stop Kafka and Zookeeper
4. (Optionally) Unbind DPDK interface

### Manual Shutdown

```bash
# Stop ML consumer
pkill -f ml_kafka_consumer.py

# Stop Suricata
sudo pkill suricata

# Stop Kafka
kafka-server-stop.sh

# Stop Zookeeper
zookeeper-server-stop.sh

# Unbind DPDK interface (restore networking)
cd scripts
sudo ./unbind_interface.sh
```

---

## 📈 Performance Tuning

### For High-Throughput Environments:

#### 1. Increase Kafka Throughput
```bash
# Edit kafka config
nano ~/kafka/config/server.properties

# Add/modify:
num.network.threads=8
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
```

#### 2. Tune Suricata Workers
```bash
# Edit suricata config
sudo nano /usr/local/etc/suricata/suricata.yaml

# Increase workers:
workers: 8  # Match CPU cores
```

#### 3. Optimize ML Consumer
```python
# In ml_kafka_consumer.py, increase batch processing:
consumer = KafkaConsumer(
    batch_size=100,  # Process flows in batches
    fetch_min_bytes=1024,
    fetch_max_wait_ms=500
)
```

---

## 🎓 Understanding the Pipeline

### Data Flow Example:

```
1. TCP Packet arrives on eth0
   ↓
2. DPDK captures (zero-copy)
   Packet: SRC=192.168.1.10:45123, DST=93.184.216.34:443, LEN=1500
   ↓
3. Suricata analyzes
   - Signature Check: No match
   - Flow Tracking: Adds to flow state
   - Generates flow event with 65+ fields
   ↓
4. Kafka receives
   Topic: suricata-alerts
   Message: {event_type: "flow", src_ip: "192.168.1.10", ...}
   ↓
5. ML Consumer processes
   - Extracts CICIDS2017 features (65 features)
   - Runs Random Forest model
   - Prediction: BENIGN (0.98 confidence)
   - Threat Score: 0.02/1.0
   ↓
6. Enhanced Alert Generated
   Topic: ml-predictions
   Message: {original_event, ml_prediction: "BENIGN", threat_score: 0.02}
```

### Feature Extraction Details:

The ML engine extracts these feature categories:
- **Flow Stats** (8): Duration, packet counts, byte counts
- **Packet Lengths** (14): Min, max, mean, std (fwd/bwd)
- **Inter-Arrival Times** (9): Mean, std, min, max (flow/fwd/bwd)
- **Flags** (6): SYN, ACK, FIN, PSH, RST, URG counts
- **Header Lengths** (4): Average header lengths
- **Rates** (4): Packets/sec, bytes/sec
- **Protocol** (3): TCP, UDP, ICMP indicators
- **Additional** (17): Idle times, active times, etc.

**Total: 65 features** (CICIDS2017 compatible)

---

## 📝 Quick Reference Commands

```bash
# Status check
./status_check.sh

# Start pipeline
./02_setup_kafka.sh
source ../venv/bin/activate
python src/ml_kafka_consumer.py --config config/pipeline.conf

# Monitor
tail -f /var/log/suricata/stats.log
tail -f logs/ml/ml_consumer.log
kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic ml-predictions

# Stop pipeline
./stop_all.sh
```

---

## 🔗 Additional Resources

- **Setup Guide**: `SETUP_GUIDE.md` - Installation instructions
- **Architecture**: `README.md` - System design and components
- **Flow-Based ML**: `FLOW_BASED_ML_ARCHITECTURE.md` - ML pipeline details
- **Suricata Docs**: https://suricata.io/
- **DPDK Docs**: https://doc.dpdk.org/
- **Kafka Docs**: https://kafka.apache.org/documentation/

---

## ✅ Success Checklist

Before reporting issues, verify:

- [ ] Kafka is running on port 9092
- [ ] Suricata is running and configured with eve-kafka output
- [ ] Flow logging is enabled in Suricata
- [ ] Topics exist: `suricata-alerts`, `ml-predictions`
- [ ] Python venv is activated
- [ ] All Python packages are installed
- [ ] ML model file exists and is readable
- [ ] Traffic is being generated (PCAP replay or live)
- [ ] Suricata is seeing packets (check stats.log)
- [ ] Kafka topic has messages (use console consumer)
- [ ] ML consumer shows "Listening on topic" message

---

**Happy Intrusion Detecting! 🛡️🔍**
