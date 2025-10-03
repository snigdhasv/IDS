# 🔄 Pipeline Modes Comparison

**Quick Guide**: Choose the right mode for your needs

---

## 📊 Mode Comparison Table

| Feature | Test Mode (PCAP) | Production Mode (DPDK) |
|---------|------------------|------------------------|
| **Traffic Source** | PCAP files (tcpreplay) | External device/network |
| **Network Interface** | Any interface (lo, eth0) | Dedicated DPDK-bound NIC |
| **Suricata Mode** | AF_PACKET | DPDK |
| **Performance** | Limited (< 1 Gbps) | High (1-10+ Gbps) |
| **Setup Complexity** | Simple (3 steps) | Advanced (6 steps) |
| **Interface Status** | Stays online | Taken offline |
| **Network Access** | Not affected | Interface unavailable to OS |
| **Use Case** | Development, testing, demos | Production monitoring |
| **Requires Physical Device** | No | Yes (or port mirror) |
| **Packet Drops** | Possible at high rates | Minimal with proper tuning |
| **ML Processing** | ALL flows | ALL flows |
| **Guide** | `QUICKSTART.md` | `PRODUCTION_DPDK_GUIDE.md` |

---

## 🎯 When to Use Each Mode

### ✅ Use Test Mode (PCAP) When:

- 🧪 **Testing the pipeline** for the first time
- 📚 **Learning** how the system works
- 🐛 **Debugging** ML models or features
- 📊 **Analyzing** specific PCAP files
- 💻 **Demonstrating** the system (no external hardware needed)
- 🔬 **Developing** new features or models
- ⚠️ **You only have one network interface** and need to stay connected

**Advantages:**
- ✅ No risk of losing network connectivity
- ✅ Repeatable (same PCAP every time)
- ✅ Quick setup (< 5 minutes)
- ✅ No special hardware needed
- ✅ Can test with known attack patterns

**Limitations:**
- ⚠️ Limited to replay speed
- ⚠️ Not real-time traffic
- ⚠️ Cannot detect live attacks

---

### ✅ Use Production Mode (DPDK) When:

- 🏢 **Monitoring production networks**
- 🚨 **Real-time threat detection** is critical
- ⚡ **High throughput** required (> 1 Gbps)
- 🌐 **Live traffic analysis** needed
- 🔍 **Actual attack detection** in real network
- 📈 **Performance is critical** (minimal latency)
- 🛡️ **Security monitoring** for organization

**Advantages:**
- ✅ Real-time detection
- ✅ High performance (up to 10+ Gbps)
- ✅ Zero-copy packet capture
- ✅ Minimal packet drops
- ✅ Suitable for production deployment

**Requirements:**
- ⚠️ Dedicated network interface (will be taken offline)
- ⚠️ External traffic source (device, mirror port, TAP)
- ⚠️ DPDK compatible NIC
- ⚠️ Backup access method (console, IPMI, second NIC)
- ⚠️ More complex setup

---

## 🚀 Quick Start Commands

### Test Mode (PCAP Replay)

```bash
# 1. Start Kafka
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
./02_setup_kafka.sh

# 2. Start ML Consumer (new terminal)
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline
source ../venv/bin/activate
python src/ml_kafka_consumer.py --config config/pipeline.conf

# 3. Replay traffic
./scripts/05_replay_traffic.sh
```

**Guide**: `QUICKSTART.md`

---

### Production Mode (DPDK)

```bash
# 1. Start Kafka
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
./02_setup_kafka.sh

# 2. Bind interface to DPDK
sudo ./01_bind_interface.sh  # ⚠️ Takes interface offline!

# 3. Start Suricata DPDK
sudo ./03_start_suricata.sh

# 4. Start ML Consumer (new terminal)
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline
source ../venv/bin/activate
python src/ml_kafka_consumer.py --config config/pipeline.conf

# 5. Send traffic from external device
# (Configure external laptop/router to send traffic)

# 6. Monitor predictions
# (Watch ML consumer output and Kafka topics)
```

**Guide**: `PRODUCTION_DPDK_GUIDE.md`

---

## 🔧 Configuration Differences

### Test Mode Configuration

```bash
# config/pipeline.conf

# Can use any interface
NETWORK_INTERFACE="lo"  # or "eth0" (won't be bound)

# Suricata runs in AF_PACKET mode (not DPDK)
# No need to bind interface

# PCAP replay settings
PCAP_REPLAY_INTERFACE="lo"
PCAP_REPLAY_SPEED="10"  # Mbps
```

### Production Mode Configuration

```bash
# config/pipeline.conf

# Use dedicated monitoring interface
NETWORK_INTERFACE="eth1"  # ⚠️ Will be taken offline!

# DPDK settings
DPDK_DRIVER="vfio-pci"
DPDK_HUGEPAGES="2048"
DPDK_CORES="0,1"

# Suricata DPDK settings
SURICATA_CORES="2"
SURICATA_HOME_NET="192.168.0.0/16"  # ← Update to your network
```

---

## 📈 Performance Comparison

### Test Mode (PCAP)

| Metric | Typical Value |
|--------|---------------|
| **Throughput** | 10-100 Mbps (replay speed) |
| **Packet Capture** | tcpreplay → Suricata AF_PACKET |
| **Latency** | 50-200ms per flow |
| **Packet Drops** | 5-10% at high rates |
| **CPU Usage** | 40-60% |
| **Memory** | 2-4 GB |

### Production Mode (DPDK)

| Metric | Typical Value |
|--------|---------------|
| **Throughput** | 1-10+ Gbps |
| **Packet Capture** | DPDK zero-copy |
| **Latency** | < 50ms per flow |
| **Packet Drops** | < 1% (with tuning) |
| **CPU Usage** | 60-80% |
| **Memory** | 4-8 GB (includes hugepages) |

---

## 🎓 Pipeline Components (Both Modes)

Both modes use the same core components:

```
Traffic Source → Suricata → Kafka → ML Engine → Predictions
```

### Common Components:

1. **Kafka Message Broker**
   - Topics: `suricata-alerts`, `ml-predictions`
   - Same in both modes

2. **ML Inference Engine**
   - Flow-based feature extraction (65 features)
   - Random Forest / LightGBM models
   - Same in both modes

3. **Alert Processing**
   - Combined signature + ML detection
   - Threat scoring
   - Same in both modes

### Differences:

| Component | Test Mode | Production Mode |
|-----------|-----------|-----------------|
| **Traffic Ingestion** | tcpreplay (PCAP files) | DPDK (live network) |
| **Suricata Capture** | AF_PACKET mode | DPDK mode |
| **Network Interface** | Normal OS driver | DPDK driver (vfio-pci) |

---

## 🔄 Switching Between Modes

### From Test Mode → Production Mode

```bash
# 1. Stop test mode
pkill -f ml_kafka_consumer.py
# Kafka can keep running

# 2. Configure production settings
nano config/pipeline.conf
# Update NETWORK_INTERFACE, SURICATA_HOME_NET, etc.

# 3. Bind interface to DPDK
sudo ./scripts/01_bind_interface.sh

# 4. Start Suricata DPDK
sudo ./scripts/03_start_suricata.sh

# 5. Start ML consumer
python src/ml_kafka_consumer.py --config config/pipeline.conf

# 6. Send live traffic
```

### From Production Mode → Test Mode

```bash
# 1. Stop production mode
sudo ./scripts/stop_all.sh

# 2. Unbind DPDK interface
sudo ./scripts/unbind_interface.sh

# 3. Restart Kafka (if stopped)
./scripts/02_setup_kafka.sh

# 4. Start ML consumer
python src/ml_kafka_consumer.py --config config/pipeline.conf

# 5. Replay PCAP
./scripts/05_replay_traffic.sh
```

---

## ✅ Recommendations

### For Learning / Development:
**Use Test Mode**
- ✅ Start with `QUICKSTART.md`
- ✅ Test with sample PCAPs
- ✅ Understand the pipeline flow
- ✅ Experiment with ML models
- ✅ Then move to production when ready

### For Production Deployment:
**Use Production Mode**
- ✅ Read `PRODUCTION_DPDK_GUIDE.md` thoroughly
- ✅ Test in safe environment first
- ✅ Ensure backup access to system
- ✅ Use dedicated monitoring interface
- ✅ Configure proper network ranges
- ✅ Tune for your traffic volume

### For Development/Testing with Real Traffic:
**Hybrid Approach**
- ✅ Capture live traffic to PCAP
- ✅ Analyze offline with test mode
- ✅ Iterate on models/features
- ✅ Deploy to production when validated

---

## 📚 Documentation Map

```
START_HERE.md
    ├─ For Testing
    │   └─ QUICKSTART.md ⚡
    │       └─ 5-minute PCAP setup
    │
    ├─ For Production
    │   └─ PRODUCTION_DPDK_GUIDE.md 🚀
    │       └─ Complete DPDK setup
    │
    ├─ For Details
    │   └─ RUNTIME_GUIDE.md 📖
    │       └─ Step-by-step execution
    │
    └─ For Troubleshooting
        └─ Each guide has troubleshooting section
```

---

## 🎯 Decision Tree

```
Do you need to monitor real network traffic?
│
├─ NO → Use Test Mode (PCAP)
│   └─ Read: QUICKSTART.md
│
└─ YES → Do you have a dedicated network interface?
    │
    ├─ NO → Use Test Mode (capture PCAPs first)
    │   └─ Or get port mirroring / TAP
    │
    └─ YES → Do you have backup access (console/IPMI)?
        │
        ├─ NO → Use Test Mode (too risky!)
        │
        └─ YES → Use Production Mode (DPDK)
            └─ Read: PRODUCTION_DPDK_GUIDE.md
```

---

## 🔑 Key Takeaways

1. **Both modes use the same ML pipeline** - flow-based detection for ALL traffic
2. **Test mode is safer and easier** - great for learning
3. **Production mode is more powerful** - necessary for real deployments
4. **You can switch between modes** - test first, then deploy
5. **ML works identically in both modes** - same features, same models
6. **Choose based on your needs** - testing vs. production monitoring

---

**Need More Help?**
- Test Mode: `QUICKSTART.md`
- Production Mode: `PRODUCTION_DPDK_GUIDE.md`
- General Info: `RUNTIME_GUIDE.md`
- Overview: `START_HERE.md`

---

**Happy Intrusion Detecting! 🛡️**
