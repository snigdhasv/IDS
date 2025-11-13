# Realtek → Intel IDS Pipeline Guide

## 🎯 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Physical Setup                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Realtek NIC (enp5s0)  ←──[Ethernet Cable]──→  Intel NIC        │
│  ├─ Kernel Mode                                 (enp1s0)         │
│  ├─ IP: 192.168.100.1/24                        ├─ DPDK Mode     │
│  └─ Sends packets via tcpreplay                 ├─ vfio-pci      │
│                                                  └─ IDS/ML        │
│                                                                  │
│  Management NIC (enp3s0) ← Keep for SSH access                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

- ✅ Physical Ethernet cable connecting enp5s0 ↔ enp1s0
- ✅ Root/sudo access
- ✅ DPDK installed (dpdk-devbind.py available)
- ✅ Python venv with ML libraries (`venv/` directory exists)
- ✅ Suricata compiled with DPDK support
- ✅ tcpreplay installed (already verified)

## 🚀 Quick Start (3 Steps)

### Step 1: Setup NICs and DPDK Binding

```bash
# Run the setup script (binds Intel NIC to DPDK, configures Realtek)
sudo ./setup_realtek_to_intel_ids.sh
```

This script:
1. Loads vfio-pci kernel module
2. Configures Realtek NIC (enp5s0) with IP 192.168.100.1/24
3. Binds Intel NIC (enp1s0) to DPDK (vfio-pci driver)
4. Sets up hugepages for DPDK

### Step 2: Start IDS Pipeline

```bash
# Option A: Test mode (feature engine only, foreground - see output)
sudo ./run_realtime_engine_dpdk.sh test

# Option B: Full pipeline (Kafka + Suricata + Feature Engine + ML Consumer)
sudo ./run_realtime_engine_dpdk.sh start
```

**Recommended**: Start with `test` mode to verify packet capture works.

### Step 3: Send Test Traffic

Open a **new terminal** and run:

```bash
# Interactive menu to select traffic type
./send_test_traffic.sh

# Or send specific PCAP directly:
sudo tcpreplay --intf1=enp5s0 --mbps=10 \
    dpdk_suricata_ml_pipeline/pcap_samples/mixed_traffic_sample.pcap
```

## 📊 Monitoring

### Real-time Logs

```bash
# Feature Engine log (packet capture & feature extraction)
tail -f logs/feature_engine.log

# ML Consumer log (predictions)
tail -f logs/ml_consumer.log

# Suricata log (signature alerts)
tail -f /var/log/suricata/suricata.log

# All logs together
sudo ./run_realtime_engine_dpdk.sh logs
```

### Check Pipeline Status

```bash
sudo ./run_realtime_engine_dpdk.sh status
```

### DPDK Binding Status

```bash
dpdk-devbind.py --status
```

## 🛠️ Manual Commands

### Bind/Unbind Intel NIC

```bash
# Bind to DPDK (for IDS)
sudo dpdk-devbind.py --bind=vfio-pci 0000:01:00.0

# Unbind from DPDK (restore kernel driver)
sudo dpdk-devbind.py --bind=ixgbe 0000:01:00.0
sudo ip link set dev enp1s0 up
```

### Send Custom Traffic

```bash
# Send at maximum speed
sudo tcpreplay --intf1=enp5s0 --topspeed your_pcap.pcap

# Send at specific speed (100 Mbps)
sudo tcpreplay --intf1=enp5s0 --mbps=100 your_pcap.pcap

# Loop PCAP 10 times
sudo tcpreplay --intf1=enp5s0 --loop=10 your_pcap.pcap
```

## 🔄 Stop and Restore

### Stop Pipeline

```bash
# Stop all services (keeps DPDK binding)
sudo ./run_realtime_engine_dpdk.sh stop

# The script will ask if you want to:
# - Stop Kafka (y/N)
# - Unbind DPDK interfaces and restore kernel drivers (y/N)
```

### Restore Everything to Original State

```bash
# Unbind Intel NIC from DPDK
sudo dpdk-devbind.py --bind=ixgbe 0000:01:00.0
sudo ip link set dev enp1s0 up

# Remove Realtek IP config
sudo ip addr flush dev enp5s0
sudo ip link set dev enp5s0 promisc off
```

## 🧪 Testing Scenarios

### 1. Normal Traffic Test
```bash
# Terminal 1: Start IDS in test mode
sudo ./run_realtime_engine_dpdk.sh test

# Terminal 2: Send normal traffic
sudo tcpreplay --intf1=enp5s0 \
    dpdk_suricata_ml_pipeline/pcap_samples/normal_traffic.pcap
```

### 2. DoS Attack Detection
```bash
# Terminal 1: Start full pipeline
sudo ./run_realtime_engine_dpdk.sh start

# Terminal 2: Send DoS traffic
sudo tcpreplay --intf1=enp5s0 --mbps=100 \
    dpdk_suricata_ml_pipeline/pcap_samples/dos_traffic_sample.pcap

# Terminal 3: Watch predictions
tail -f logs/ml_consumer.log | grep -i "attack\|dos"
```

### 3. Mixed Traffic Analysis
```bash
# Send mixed benign + attack traffic
sudo tcpreplay --intf1=enp5s0 --loop=5 \
    dpdk_suricata_ml_pipeline/pcap_samples/mixed_traffic_sample.pcap

# View CSV predictions
tail -100 logs/ml_predictions.csv
```

## ⚠️ Troubleshooting

### Intel NIC Not Binding to DPDK

```bash
# Check IOMMU enabled in BIOS/kernel
cat /proc/cmdline | grep iommu

# If not enabled, add to /etc/default/grub:
# GRUB_CMDLINE_LINUX_DEFAULT="intel_iommu=on iommu=pt"
# Then: sudo update-grub && sudo reboot

# Alternative: use uio_pci_generic instead of vfio-pci
sudo modprobe uio_pci_generic
sudo dpdk-devbind.py --bind=uio_pci_generic 0000:01:00.0
```

### Feature Engine Dies Immediately

```bash
# Check the log
cat logs/feature_engine.log

# Common issues:
# 1. No hugepages allocated
echo 2048 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages

# 2. Interface not bound
dpdk-devbind.py --status

# 3. Python venv missing packages
source venv/bin/activate
pip install -r requirements.txt
```

### No Packets Being Captured

```bash
# Verify cable connection
ethtool enp5s0 | grep "Link detected"

# Check DPDK port status in feature engine log
cat logs/feature_engine.log | grep -i "port\|link"

# Try promiscuous mode on Realtek
sudo ip link set dev enp5s0 promisc on

# Send ARP ping to verify connectivity
sudo arping -I enp5s0 192.168.100.2
```

### Kafka Not Starting

```bash
# Start manually
cd dpdk_suricata_ml_pipeline/scripts
sudo ./02_setup_kafka.sh

# Check port
sudo netstat -tuln | grep 9092
```

## 📁 File Locations

- **Scripts**: `/home/ifscr/SE_02_2025/IDS/`
  - `setup_realtek_to_intel_ids.sh` - NIC setup script
  - `send_test_traffic.sh` - Traffic sender
  - `run_realtime_engine_dpdk.sh` - Main pipeline orchestrator

- **Logs**: `/home/ifscr/SE_02_2025/IDS/logs/`
  - `feature_engine.log` - Packet capture & features
  - `ml_consumer.log` - ML predictions
  - `ml_predictions.csv` - Prediction history

- **PCAP Samples**: `dpdk_suricata_ml_pipeline/pcap_samples/`
  - `normal_traffic.pcap` (26KB)
  - `dos_traffic_sample.pcap` (2.8MB)
  - `mixed_traffic_sample.pcap` (8.2MB)

- **Config**: `dpdk_suricata_ml_pipeline/config/pipeline.conf`

## 🎓 Understanding the Flow

1. **Setup Phase**: `setup_realtek_to_intel_ids.sh` configures both NICs
2. **IDS Start**: Feature engine attaches to Intel NIC via DPDK PMD
3. **Packet Send**: tcpreplay sends from Realtek NIC
4. **Physical Layer**: Packets flow through cable to Intel NIC
5. **DPDK Capture**: Feature engine receives packets via DPDK (zero-copy)
6. **Feature Extraction**: CICIDS-style features calculated per flow
7. **Kafka**: Features sent to `ml-features` topic
8. **ML Prediction**: Ensemble model classifies as BENIGN/ATTACK
9. **Output**: Predictions logged to `ml-predictions` topic and CSV

## 🚀 Performance Tips

- **Higher throughput**: Increase `--mbps` in tcpreplay
- **Multiple cores**: Edit `DPDK_CORES="0,1,2,3"` in pipeline.conf
- **Huge batches**: Adjust `ML_BATCH_SIZE` in pipeline.conf
- **Loop traffic**: Use `--loop=N` to repeat PCAP files

## 📞 Need Help?

Check logs first:
```bash
# See what's failing
sudo ./run_realtime_engine_dpdk.sh status

# View specific log
tail -100 logs/feature_engine.log
```

Common log patterns:
- `"Port 0 link UP"` - Good! DPDK captured the interface
- `"Receiving packets..."` - Good! Packets are arriving
- `"Feature vector produced"` - Good! Features extracted
- `"ATTACK detected"` - ML found malicious traffic
