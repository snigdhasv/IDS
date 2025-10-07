# 🎯 SETUP COMPLETE: External Traffic Capture Ready!

## What You Asked For

> "Instead of replaying traffic using AF_PACKET here, I want to be able to use the traffic being replayed on another external device using a PCAP replay application and connect through USB adapter that's bound to AF_PACKET and rest of the IDS pipeline works from this traffic from USB adapter."

## ✅ What I've Created

### New Scripts
1. **`scripts/00_setup_external_capture.sh`** - Configures your USB adapter to receive external traffic
2. Updated **`scripts/quick_start.sh`** - Added option 9 for external capture setup

### New Documentation
1. **`EXTERNAL_TRAFFIC_GUIDE.md`** - Complete guide with all details
2. **`NETWORK_TOPOLOGY.md`** - Visual diagrams of the setup
3. **`EXTERNAL_TRAFFIC_SETUP.md`** - Technical reference
4. Updated **`config/pipeline.conf`** - Added external capture notes

---

## 🚀 How to Use It

### On Your IDS System (This Laptop)

```bash
cd ~/Programming/IDS/dpdk_suricata_ml_pipeline/scripts

# Step 1: Configure USB adapter for external traffic
sudo ./00_setup_external_capture.sh

# Step 2: Start the IDS pipeline
sudo ./quick_start.sh
# Select option 1: Start Complete Pipeline

# Step 3: Monitor in separate terminals
# Terminal 2: Watch packets
sudo tcpdump -i enx00e04c36074c -n

# Terminal 3: Watch alerts
tail -f logs/suricata/eve.json | jq 'select(.event_type=="alert")'

# Terminal 4: Watch ML predictions
tail -f logs/ml/consumer.log
```

### On Your External Device (e.g., Kali Linux, Raspberry Pi, Another PC)

```bash
# Step 1: Configure network
sudo ip addr add 192.168.100.2/24 dev eth0
sudo ip link set eth0 up

# Step 2: Test connectivity
ping 192.168.100.1

# Step 3: Replay your PCAPs
sudo tcpreplay -i eth0 -K --mbps 10 /path/to/attack.pcap

# Or use other tools:
# - scapy: sendp(packets, iface='eth0')
# - hping3: sudo hping3 -S 192.168.100.1 -p 80 --flood
# - nmap: sudo nmap -sS 192.168.100.1
```

---

## 🌐 Network Configuration

```
┌──────────────────────┐         ┌──────────────────────┐
│  External Device     │ Cable   │   Your IDS System    │
│  (PCAP Replay)       │═══════▶│   (This Laptop)      │
│                      │         │                      │
│  IP: 192.168.100.2   │         │  IP: 192.168.100.1   │
│  Interface: eth0     │         │  Interface:          │
│                      │         │  enx00e04c36074c     │
│  Tools:              │         │                      │
│  • tcpreplay         │         │  Components:         │
│  • scapy             │         │  • Suricata (IDS)    │
│  • hping3            │         │  • Kafka (Bus)       │
│  • metasploit        │         │  • ML (Detection)    │
└──────────────────────┘         └──────────────────────┘
```

---

## 📋 What This Setup Does

### Old Way (Local Replay - Not What You Wanted)
```
Same System: PCAP → USB Adapter → Suricata
❌ Everything on one device
❌ Less realistic testing
```

### New Way (External Traffic - What You Wanted!)
```
External Device: tcpreplay → [Cable] → USB Adapter → Suricata → ML
✅ Separate attack generator
✅ Realistic traffic flow
✅ Any PCAP replay tool works
✅ Can use multiple external devices
```

---

## 🎮 Complete Workflow

### 1. Physical Setup
- Connect Ethernet cable from external device to your USB adapter
- Ensure cable is good and shows "Link detected: yes"

### 2. IDS System Setup (One-Time)
```bash
cd ~/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
sudo ./00_setup_external_capture.sh
```

This configures:
- ✅ USB adapter IP: 192.168.100.1/24
- ✅ Promiscuous mode (captures all traffic)
- ✅ Optimized buffers
- ✅ Disabled offload features

### 3. External Device Setup (One-Time per Device)
```bash
# On external device
sudo ip addr add 192.168.100.2/24 dev eth0
sudo ip link set eth0 up
ping 192.168.100.1  # Should work!
```

### 4. Start IDS Pipeline (Each Session)
```bash
cd ~/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
sudo ./quick_start.sh
# Select: 1 (Start Complete Pipeline)
```

### 5. Replay Traffic (From External Device)
```bash
# On external device
sudo tcpreplay -i eth0 -K --mbps 10 capture.pcap
```

### 6. Watch Detection (On IDS System)
```bash
# Live alerts with pretty JSON
tail -f logs/suricata/eve.json | jq 'select(.event_type=="alert")'

# ML predictions
tail -f logs/ml/consumer.log | grep -i "attack"

# Statistics
suricatasc -c dump-counters
```

---

## 🔍 Verification Steps

### Check USB Adapter Configuration
```bash
ip addr show enx00e04c36074c
# Should show:
# - PROMISC flag
# - inet 192.168.100.1/24
```

### Check Connectivity
```bash
# From IDS system
ping 192.168.100.2

# From external device
ping 192.168.100.1

# Both should work!
```

### Check Traffic is Flowing
```bash
# On IDS system
sudo tcpdump -i enx00e04c36074c -n -c 10
# Should see packets when external device sends traffic
```

### Check Pipeline is Working
```bash
# Suricata running?
ps aux | grep suricata

# Kafka running?
ps aux | grep kafka

# ML consumer running?
ps aux | grep ml_kafka_consumer

# All should show processes
```

---

## 📚 Documentation Reference

| Document | Purpose |
|----------|---------|
| **EXTERNAL_TRAFFIC_GUIDE.md** | Complete step-by-step guide |
| **NETWORK_TOPOLOGY.md** | Visual diagrams and examples |
| **AF_PACKET_QUICK_START.md** | AF_PACKET mode basics |
| **USB_ADAPTER_GUIDE.md** | Why DPDK doesn't work |

---

## 🎓 Example: Using Kali Linux as External Device

### On Kali Linux
```bash
# Configure network
sudo ip addr add 192.168.100.2/24 dev eth0
sudo ip link set eth0 up

# Test connection
ping 192.168.100.1

# Install tools if needed
sudo apt install tcpreplay scapy hping3

# Replay attack PCAP
sudo tcpreplay -i eth0 -K --mbps 10 /usr/share/pcaps/attack.pcap

# Or generate live attacks
sudo hping3 -S 192.168.100.1 -p 80 --flood

# Or use scapy
python3 << EOF
from scapy.all import *
target = "192.168.100.1"
packet = IP(dst=target)/TCP(dport=80, flags="S")
send(packet, iface="eth0", count=100)
EOF
```

### On Your IDS System
```bash
# Watch detections in real-time!
tail -f logs/suricata/eve.json | jq 'select(.event_type=="alert") | {timestamp: .timestamp, alert: .alert.signature}'

# You'll see alerts for the attacks from Kali!
```

---

## 💡 Pro Tips

### Tip 1: Use Multiple External Devices
```bash
# Device 1: 192.168.100.2 (DDoS attacks)
# Device 2: 192.168.100.3 (Port scans)
# Device 3: 192.168.100.4 (Web exploits)
# All send traffic to your IDS simultaneously!
```

### Tip 2: Replay at Different Speeds
```bash
# Slow and steady (10 Mbps)
sudo tcpreplay -i eth0 -K --mbps 10 capture.pcap

# As fast as possible
sudo tcpreplay -i eth0 -t capture.pcap

# Loop 100 times
sudo tcpreplay -i eth0 --loop 100 capture.pcap
```

### Tip 3: Target Different IPs
```bash
# Your IDS will see traffic to ANY IP
# The external device can target:
# - 192.168.100.1 (the IDS itself)
# - 192.168.100.50 (simulated server)
# - 8.8.8.8 (external IP - will be routed if configured)
# - Any IP in your PCAP
```

### Tip 4: Use PCAP Datasets
```bash
# Your project already has datasets
# CICIDS2017, CICIDS2018 in notebooks/
# Extract PCAPs from these and replay them!
```

---

## 🐛 Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| Can't ping external device | Check cable, check IP config on both sides |
| No traffic in tcpdump | Ensure promiscuous mode, check firewall |
| Suricata not detecting | Check suricata.log, verify interface in config |
| ML not predicting | Check Kafka connection, verify model loaded |
| High packet loss | Reduce replay speed on external device |

---

## ✅ Summary

You now have:

✅ **Script to configure USB adapter for external traffic**
   - `sudo ./00_setup_external_capture.sh`

✅ **Network configured as 192.168.100.0/24**
   - IDS: 192.168.100.1
   - External: 192.168.100.2+

✅ **Complete documentation**
   - EXTERNAL_TRAFFIC_GUIDE.md (detailed)
   - NETWORK_TOPOLOGY.md (visual)

✅ **Updated pipeline scripts**
   - quick_start.sh has new option 9

✅ **Works with ANY PCAP replay tool**
   - tcpreplay, scapy, hping3, metasploit, etc.

✅ **Separates attack generation from detection**
   - External device: Generate attacks
   - Your laptop: Detect and classify

---

## 🚀 Next Steps

1. **Run the setup**:
   ```bash
   cd ~/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
   sudo ./00_setup_external_capture.sh
   ```

2. **Connect your external device** via Ethernet cable

3. **Configure external device**: IP 192.168.100.2/24

4. **Start the pipeline**:
   ```bash
   sudo ./quick_start.sh  # Option 1
   ```

5. **Replay traffic** from external device

6. **Watch the magic happen!** 🎉

---

**You're all set to capture and analyze external traffic!**

See `EXTERNAL_TRAFFIC_GUIDE.md` for complete details.
