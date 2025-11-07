# External Device Setup Guide - Step by Step

Complete guide to set up external traffic capture between your IDS system and a second device for PCAP replay testing.

---

## 📋 Prerequisites

### Hardware Required
- **IDS Device**: Your current system (sujay-950QED)
- **External Device**: Second laptop/PC for traffic generation
- **USB Ethernet Adapter**: Already connected (`enx00e04c36074c`)
- **Ethernet Cable**: To connect both devices

### Software Required
- **IDS Device**: Already installed ✅
  - Suricata, Kafka, Python environment
  - tcpdump, tcpreplay
  
- **External Device**: Needs installation
  - tcpreplay (for PCAP replay)
  - Optional: hping3, scapy, netcat

---

## 🔧 Part 1: IDS Device Setup (Your Current System)

### Step 1: Configure Network Interface

Connect the USB Ethernet adapter and run the setup script:

```bash
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
sudo bash 00_setup_external_capture.sh
```

**What this does:**
- Assigns IP `192.168.100.1/24` to `enx00e04c36074c`
- Enables promiscuous mode for packet capture
- Disables offload features (GRO, LRO, TSO)
- Optimizes network buffers
- Configures firewall rules

**Expected Output:**
```
✓ Interface is up
✓ IP configured: 192.168.100.1/24
✓ Promiscuous mode enabled
✓ Interface Ready for External Traffic
```

### Step 2: Verify Interface Configuration

```bash
# Check IP address
ip addr show enx00e04c36074c

# Should show: inet 192.168.100.1/24
```

### Step 3: Start IDS Pipeline

Option A - Using run_afpacket_mode.sh (recommended):
```bash
cd /home/sujay/Programming/IDS
sudo ./run_afpacket_mode.sh
```
Then select:
- Option `1` - Start All Components
- Or start individually with options 2-8

Option B - Using quick start script:
```bash
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
sudo bash quick_start.sh
```
Select option `1` for AF_PACKET mode

### Step 4: Verify Pipeline is Running

```bash
# Check Suricata
ps aux | grep suricata | grep -v grep

# Check Kafka Bridge
ps aux | grep suricata_kafka_bridge | grep -v grep

# Check ML Consumer
ps aux | grep two_model_consumer | grep -v grep

# Monitor live capture (in separate terminal)
sudo tcpdump -i enx00e04c36074c -n
```

---

## 🖥️ Part 2: External Device Setup (Second Computer)

### Step 1: Physical Connection

1. **Connect** the Ethernet cable between:
   - IDS Device USB adapter (`enx00e04c36074c`)
   - External device's Ethernet port

2. **Identify** the network interface on external device:
```bash
ip link show
# Look for interface like: eth0, enp3s0, eno1, etc.
```

### Step 2: Configure Static IP

**Replace `eth0` with your actual interface name!**

```bash
# Bring interface up
sudo ip link set eth0 up

# Assign static IP
sudo ip addr add 192.168.100.2/24 dev eth0

# Verify configuration
ip addr show eth0
# Should show: inet 192.168.100.2/24
```

### Step 3: Install Traffic Generation Tools

**On Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y tcpreplay hping3 netcat-openbsd
```

**On Fedora/RHEL:**
```bash
sudo dnf install -y tcpreplay hping3 nmap-ncat
```

**On Arch:**
```bash
sudo pacman -S tcpreplay hping nmap
```

### Step 4: Test Connectivity

```bash
# Ping IDS device
ping -c 4 192.168.100.1

# Expected output: 64 bytes from 192.168.100.1: icmp_seq=1 ttl=64 time=X ms
```

---

## 🧪 Part 3: Testing Traffic Capture

### On IDS Device (Terminal 1)

Start monitoring interface:
```bash
sudo tcpdump -i enx00e04c36074c -n -v
```

### On External Device (Terminal 1)

Send test traffic:
```bash
# Simple ping test
ping 192.168.100.1

# TCP SYN flood test
sudo hping3 -S 192.168.100.1 -p 80 -c 10

# Generate random traffic
ping -c 100 -i 0.1 192.168.100.1
```

### Verify on IDS Device

You should see:
1. **In tcpdump**: Packets appearing in real-time
2. **In Suricata logs**: Events being logged
   ```bash
   tail -f /var/log/suricata/eve.json | grep flow
   ```
3. **In Dashboard**: Events and ML predictions
   ```bash
   cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline
   python3 scripts/metrics_dashboard.py
   ```

---

## 📦 Part 4: PCAP Replay Testing

### Option A: Generate Test PCAP on IDS Device

Create a simple test PCAP:
```bash
cd /home/sujay/Programming/IDS

# Capture some traffic
sudo timeout 30 tcpdump -i wlo1 -w test_traffic.pcap -c 1000

# Or use existing notebooks to generate attack traffic
```

### Option B: Download Public Dataset

On external device:
```bash
# Download sample PCAP (example)
wget https://www.malware-traffic-analysis.net/2024/01/01/2024-01-01-traffic.pcap

# Or use your own PCAP files
```

### Transfer PCAP to External Device (if needed)

**From IDS device:**
```bash
# Copy file via USB drive, or use network transfer:
scp test_traffic.pcap user@192.168.100.2:/tmp/
```

### Replay PCAP from External Device

**Replace `eth0` with your interface and adjust path!**

```bash
# Basic replay at normal speed
sudo tcpreplay -i eth0 your_capture.pcap

# Replay at 10 Mbps
sudo tcpreplay -i eth0 --mbps 10 your_capture.pcap

# Replay at maximum speed
sudo tcpreplay -i eth0 -t your_capture.pcap

# Replay in loop
sudo tcpreplay -i eth0 --loop 5 your_capture.pcap

# Replay with rate limiting
sudo tcpreplay -i eth0 --pps 1000 your_capture.pcap
```

---

## 📊 Part 5: Monitor ML Predictions

### On IDS Device

**Terminal 1 - Dashboard:**
```bash
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline
python3 scripts/metrics_dashboard.py
```

**Terminal 2 - Metrics Log:**
```bash
tail -f logs/metrics/metrics_$(date +%Y%m%d).jsonl
```

**Terminal 3 - ML Predictions:**
```bash
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
python3 -c "
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'ml-predictions',
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

print('🔍 Listening for ML predictions...')
for message in consumer:
    pred = message.value
    print(f'Prediction: {pred[\"prediction\"]} | Confidence: {pred[\"confidence\"]:.2f} | Models: {pred[\"model_names\"]}')
"
```

---

## 🔍 Troubleshooting

### IDS Device - No Packets Captured

```bash
# Check interface is UP
ip link show enx00e04c36074c

# Check promiscuous mode enabled
ip link show enx00e04c36074c | grep PROMISC

# Check firewall
sudo ufw status
sudo iptables -L -v -n

# Verify Suricata is listening
sudo netstat -tuln | grep 9092  # Kafka
ps aux | grep suricata
```

### External Device - Cannot Ping IDS

```bash
# Check interface is UP
ip link show eth0

# Check IP assigned
ip addr show eth0

# Check routing
ip route

# Check cable connection
ethtool eth0 | grep "Link detected"
```

### No ML Predictions Appearing

```bash
# Check consumer is running
ps aux | grep two_model_consumer

# Check Kafka topics
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic suricata-events --from-beginning --max-messages 1

# Restart consumer
sudo pkill -f two_model_consumer
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
bash 06_start_two_model_consumer.sh
```

---

## 📝 Quick Command Reference

### IDS Device Commands

```bash
# Setup interface
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
sudo bash 00_setup_external_capture.sh

# Start pipeline
cd /home/sujay/Programming/IDS
sudo ./run_afpacket_mode.sh

# Monitor capture
sudo tcpdump -i enx00e04c36074c -n

# View dashboard
cd /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline
python3 scripts/metrics_dashboard.py

# Check logs
tail -f /var/log/suricata/eve.json
tail -f logs/metrics/metrics_$(date +%Y%m%d).jsonl
```

### External Device Commands

```bash
# Configure IP (replace eth0!)
sudo ip link set eth0 up
sudo ip addr add 192.168.100.2/24 dev eth0

# Test connectivity
ping 192.168.100.1

# Replay PCAP (replace eth0 and filename!)
sudo tcpreplay -i eth0 --mbps 10 capture.pcap

# Generate attack traffic
sudo hping3 -S 192.168.100.1 -p 80 --flood -c 1000
```

---

## ✅ Success Checklist

- [ ] USB adapter shows IP 192.168.100.1/24
- [ ] External device shows IP 192.168.100.2/24  
- [ ] Ping works between devices
- [ ] tcpdump shows packets on IDS device
- [ ] Suricata logs show events in eve.json
- [ ] Dashboard shows throughput and events
- [ ] ML predictions appear in metrics log
- [ ] PCAP replay generates traffic successfully

---

## 🎯 Next Steps After Setup

1. **Test with Real Attack PCAPs**: Use CICIDS2017/2018 samples
2. **Generate Custom Attacks**: Use scripts in `tests/` folder
3. **Monitor Performance**: Track latency and throughput
4. **Tune Models**: Compare different ensemble configurations
5. **Export Results**: Analyze metrics for research/reporting

---

## 📚 Additional Resources

- `USB_ADAPTER_GUIDE.md` - USB adapter configuration details
- `EXTERNAL_TRAFFIC_GUIDE.md` - Extended traffic capture guide
- `ENSEMBLE_GUIDE.md` - ML model ensemble documentation
- `PERFORMANCE_METRICS_GUIDE.md` - Metrics and monitoring

For help: Check logs in `dpdk_suricata_ml_pipeline/logs/`
