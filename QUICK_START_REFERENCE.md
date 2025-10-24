# ⚡ Quick Reference Guide

## 🚀 Start in 3 Commands

```bash
cd /home/sujay/Programming/IDS
chmod +x run_afpacket_mode.sh
sudo ./run_afpacket_mode.sh
```

Select option `1` → Pipeline starts! ✅

---

## 📋 Command Cheat Sheet

### Basic Operations

| Task | Command |
|------|---------|
| **Start Pipeline** | `sudo ./run_afpacket_mode.sh start` |
| **Check Status** | `sudo ./run_afpacket_mode.sh status` |
| **View Logs** | `sudo ./run_afpacket_mode.sh logs` |
| **Stop Pipeline** | `sudo ./run_afpacket_mode.sh stop` |
| **Interactive Menu** | `sudo ./run_afpacket_mode.sh` |

### Component Specific

| Task | Command |
|------|---------|
| **Start Only Kafka** | `sudo ./run_afpacket_mode.sh kafka` |
| **Start Only Suricata** | `sudo ./run_afpacket_mode.sh suricata` |
| **Start Only ML Consumer** | `sudo ./run_afpacket_mode.sh ml` |
| **Start Only Kafka Bridge** | `sudo ./run_afpacket_mode.sh bridge` |

### DPDK Mode

| Task | Command |
|------|---------|
| **Start DPDK Pipeline** | `sudo ./run_dpdk_mode.sh start` |
| **Bind Interface** | `sudo ./run_dpdk_mode.sh bind` |
| **Unbind Interface** | `sudo ./run_dpdk_mode.sh unbind` |
| **Check DPDK Status** | `sudo ./run_dpdk_mode.sh info` |

---

## 🔍 Verify Services

### Check if Services are Running

```bash
# Kafka
ps aux | grep kafka | grep -v grep

# Suricata
ps aux | grep suricata | grep -v grep

# ML Consumer
ps aux | grep ml_kafka_consumer | grep -v grep

# Kafka Bridge
ps aux | grep suricata_kafka_bridge | grep -v grep
```

### Quick Status Check

```bash
# AF_PACKET mode
sudo ./run_afpacket_mode.sh status

# DPDK mode
sudo ./run_dpdk_mode.sh status
```

---

## 📊 View Output Data

### Suricata Alerts (Real-time)

```bash
tail -f /var/log/suricata/eve.json
```

### ML Predictions (Real-time)

```bash
python3 << 'EOF'
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'ml-predictions',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='latest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

for message in consumer:
    print(json.dumps(message.value, indent=2))
EOF
```

### Kafka Topics

```bash
# List all topics
kafka-topics.sh --bootstrap-server localhost:9092 --list

# Read messages from suricata-alerts
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
    --topic suricata-alerts --from-beginning

# Read messages from ml-predictions
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
    --topic ml-predictions --from-beginning
```

---

## 🧪 Testing

### Generate Test Traffic

```bash
cd /home/sujay/Programming/IDS/tests

# Benign traffic
python3 test_benign_traffic.py

# Attack traffic
python3 test_attack_generator.py

# ML testing
python3 test_ml_classifications.py

# DPDK testing
python3 test_dpdk_scapy_integration.py
```

---

## ⚙️ Configuration

### Edit Configuration

```bash
nano /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf
```

### Key Settings

| Setting | Location | Default | Purpose |
|---------|----------|---------|---------|
| Network Interface | `NETWORK_INTERFACE` | `enx00e04c36074c` | Packet capture interface |
| Suricata Threads | `SURICATA_CORES` | `2` | Detection threads |
| ML Batch Size | `ML_BATCH_SIZE` | `100` | Batch inference size |
| ML Threshold | `ML_CONFIDENCE_THRESHOLD` | `0.7` | Alert threshold |
| Kafka Servers | `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka location |

---

## 🐛 Common Issues

### Issue: "Permission denied"
```bash
sudo chmod +x /home/sujay/Programming/IDS/run_afpacket_mode.sh
```

### Issue: "Interface not found"
```bash
ip link show  # Find your interface
# Edit: dpdk_suricata_ml_pipeline/config/pipeline.conf
```

### Issue: "Kafka already in use"
```bash
sudo lsof -i :9092  # Find process
sudo kill -9 <PID>  # Kill it
```

### Issue: "No alerts generated"
```bash
# Check Suricata logs
tail -f /var/log/suricata/suricata.log

# Check if traffic is captured
sudo tcpdump -i YOUR_INTERFACE -c 10

# Check Kafka topics
kafka-topics.sh --bootstrap-server localhost:9092 --list
```

### Issue: High CPU usage
```bash
# Increase threads
nano dpdk_suricata_ml_pipeline/config/pipeline.conf
# Set: SURICATA_CORES="4"  (or higher)

# Restart:
sudo ./run_afpacket_mode.sh stop
sudo ./run_afpacket_mode.sh start
```

---

## 📖 Documentation Files

| File | Purpose |
|------|---------|
| `HOW_TO_RUN.md` | Step-by-step setup guide ← **You are here** |
| `PIPELINE_ARCHITECTURE.md` | Technical architecture details |
| `NEXT_STEPS.md` | Project roadmap and future plans |
| `FINAL_SUMMARY.md` | Cleanup report |
| `README.md` | Main documentation |
| `QUICKSTART.md` | Quick setup guide |
| `USB_ADAPTER_GUIDE.md` | USB adapter specific setup |
| `PRODUCTION_DPDK_GUIDE.md` | DPDK production deployment |

---

## 💡 Pro Tips

### 1. Keep Multiple Terminals
```bash
# Terminal 1: Monitor status
watch -n 1 'sudo ./run_afpacket_mode.sh status'

# Terminal 2: View logs
tail -f /var/log/suricata/eve.json

# Terminal 3: Generate test traffic
python3 tests/test_benign_traffic.py

# Terminal 4: Run commands
# available for other tasks
```

### 2. Background Execution
```bash
# Run pipeline in background
nohup sudo ./run_afpacket_mode.sh start > pipeline.log 2>&1 &

# Check log
tail -f pipeline.log

# Stop later
sudo ./run_afpacket_mode.sh stop
```

### 3. Autostart on Boot (Linux)
```bash
# Create systemd service
sudo cat > /etc/systemd/system/ids-pipeline.service << EOF
[Unit]
Description=IDS Pipeline
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/sujay/Programming/IDS
ExecStart=/home/sujay/Programming/IDS/run_afpacket_mode.sh start
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable ids-pipeline.service
sudo systemctl start ids-pipeline.service

# Check status
sudo systemctl status ids-pipeline.service
```

### 4. Docker Deployment (Optional)
```bash
# If containerization desired, add Dockerfile to project
docker build -t ids-pipeline .
docker run -d --net=host ids-pipeline run_afpacket_mode.sh start
```

---

## 🎯 Quick Scenarios

### Scenario 1: Basic Testing
```bash
# Terminal 1
cd /home/sujay/Programming/IDS
sudo ./run_afpacket_mode.sh start

# Terminal 2 (after 10 seconds)
cd /home/sujay/Programming/IDS/tests
python3 test_benign_traffic.py

# Terminal 1
sudo ./run_afpacket_mode.sh logs
# Should see alerts and ML predictions
```

### Scenario 2: Performance Benchmarking
```bash
# Start pipeline
sudo ./run_afpacket_mode.sh start

# Monitor performance
watch -n 1 'ps aux | grep suricata | head -1'

# Generate high-volume traffic
cd tests/
for i in {1..10}; do
  python3 test_attack_generator.py &
done
wait

# Check performance
top -p $(pgrep suricata)
```

### Scenario 3: DPDK Mode Testing
```bash
# If DPDK-compatible hardware available
sudo ./run_dpdk_mode.sh start

# Monitor interface binding
sudo ./run_dpdk_mode.sh info

# Generate traffic
cd tests/
python3 test_dpdk_scapy_integration.py

# Check results
tail -f /var/log/suricata/eve.json
```

---

## 📞 Support

**For detailed setup help:**
- Read: `HOW_TO_RUN.md` (you are here)
- Architecture: `PIPELINE_ARCHITECTURE.md`
- Quick start: `QUICKSTART.md`

**For architecture questions:**
- Read: `PIPELINE_ARCHITECTURE.md`
- Check: `FLOW_BASED_ML_ARCHITECTURE.md`

**For future improvements:**
- See: `NEXT_STEPS.md`

**For troubleshooting:**
- Check issues in: `HOW_TO_RUN.md` (Troubleshooting section)
- View logs: `sudo ./run_afpacket_mode.sh logs`

---

## ✅ Success Checklist

- [ ] Installed dependencies
- [ ] Configured network interface
- [ ] Started pipeline
- [ ] All services running
- [ ] Generated test traffic
- [ ] Received alerts
- [ ] ML predictions working
- [ ] Understand architecture (read PIPELINE_ARCHITECTURE.md)
- [ ] Reviewed next steps (read NEXT_STEPS.md)

---

**You're all set! Start with: `sudo ./run_afpacket_mode.sh start` 🚀**
