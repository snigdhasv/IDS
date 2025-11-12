# DPDK Realtime Engine - Quick Start Guide

## TL;DR - Get Running in 5 Minutes

### Prerequisites Check
```bash
# 1. Do you have a DPDK-compatible NIC?
lspci | grep -i ethernet
# Should show: Intel 1G/10G/40G or Broadcom or Mellanox (NOT USB adapter)

# 2. Is Suricata compiled with DPDK?
suricata --build-info | grep DPDK
# Should show: DPDK support: yes
```

### Quick Start

```bash
# 1. Bind interface to DPDK (MUST do this first!)
cd /home/ifscr/SE_02_2025/IDS
sudo ./dpdk_suricata_ml_pipeline/scripts/01_bind_interface.sh
# Follow prompts, select vfio-pci driver

# 2. Start the pipeline
sudo ./run_realtime_engine_dpdk.sh start

# 3. Verify it's working
sudo ./run_realtime_engine_dpdk.sh status

# 4. Watch it run
tail -f logs/feature_engine.log

# 5. Stop when done
sudo ./run_realtime_engine_dpdk.sh stop
```

---

## Detailed Setup

### Step 1: Verify Prerequisites

```bash
# Check NIC
lspci | grep -i ethernet
# DPDK-compatible examples:
# - 01:00.0 Ethernet controller: Intel Corporation 82599ES 10-Gigabit SFI/SFP+
# - 02:00.0 Ethernet controller: Mellanox Technologies ConnectX-5
# 
# NOT compatible:
# - USB Ethernet adapters (don't appear in lspci, use AF_PACKET instead)

# Check Suricata DPDK support
suricata --build-info | grep DPDK
# Output should show: DPDK support: yes

# Check current interface status
ip link show enp2s0  # or whatever your interface is
```

### Step 2: Configure pipeline.conf

Already done for you! But verify:

```bash
cat dpdk_suricata_ml_pipeline/config/pipeline.conf | grep NETWORK_INTERFACE
# Should show: NETWORK_INTERFACE="enp2s0"
```

If your interface is different:
```bash
ip link show | grep "^[0-9]:" | awk '{print $2}' | sed 's/:$//'
# Use output to update NETWORK_INTERFACE in config/pipeline.conf
```

### Step 3: Bind Interface to DPDK

**⚠️ WARNING: Interface will go OFFLINE!**

```bash
# Run the binding script
sudo ./dpdk_suricata_ml_pipeline/scripts/01_bind_interface.sh

# Script will:
# - Detect your interface (enp2s0)
# - Get its PCI address (e.g., 0000:02:00.0)
# - Load vfio-pci kernel module
# - Bind interface from kernel driver to DPDK
# - Interface disappears from 'ip link show'
# - Interface now visible in 'dpdk-devbind.py --status'

# Verify binding
dpdk-devbind.py --status | grep DPDK
# Output example:
# Network devices using DPDK-compatible driver
# 0000:02:00.0 'Intel 82599ES' drv=vfio-pci
```

### Step 4: Start the Pipeline

```bash
# Start everything with one command
sudo ./run_realtime_engine_dpdk.sh start

# Output will show:
# ✓ Kafka ready
# ✓ Suricata DPDK started (PID: 12345)
# ✓ Feature Engine started (PID: 12346)
# ✓ ML Consumer started (PID: 12347)
```

### Step 5: Monitor

```bash
# Check status anytime
sudo ./run_realtime_engine_dpdk.sh status

# Watch logs
tail -f logs/feature_engine.log
tail -f logs/ml_consumer.log
tail -f /var/log/suricata/suricata.log

# Monitor Kafka
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
    --topic suricata-alerts --max-messages 5
```

---

## Testing the Pipeline

### Generate Test Traffic

```bash
# Use PCAP files in dpdk_suricata_ml_pipeline/pcap_samples/
# Option 1: Replay from external device (recommended)
# On external device:
sudo tcpreplay -i eth0 --mbps 100 attack_traffic.pcap

# Option 2: Replay locally (if supported)
tcpreplay -i enp2s0 attack_traffic.pcap
# Note: May not work after DPDK binding (interface offline)
```

### Verify Feature Detection

```bash
# Watch for attacks in feature engine
tail -f logs/feature_engine.log | grep -i "attack\|alert"

# Or check Kafka
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
    --topic ml-features | jq '.prediction' | grep -i attack
```

---

## Comparison: AF_PACKET vs DPDK

| Metric | AF_PACKET | DPDK |
|--------|-----------|------|
| **Script** | `./run_realtime_engine.sh` | `./run_realtime_engine_dpdk.sh` |
| **Speed** | 100-500 Mbps | 1-10+ Gbps |
| **Latency** | 1-10 ms | Microseconds |
| **Setup** | Simple | Complex (binding) |
| **Interface Status** | UP (online) | DOWN (offline) |
| **Best For** | Testing, dev | Production |

### When to Use What

**Use AF_PACKET if:**
- USB Ethernet adapter (doesn't support DPDK)
- Testing/learning
- Traffic is low-moderate (~100 Mbps)
- You need interface for SSH/other networking

**Use DPDK if:**
- High-speed network (1+ Gbps)
- Production IDS deployment
- Dedicated capture NIC (not needed for other use)
- Minimizing latency critical
- Intel 1G/10G/40G, Broadcom, or Mellanox NIC

---

## Troubleshooting

### Issue: "No DPDK devices found"

```bash
# Check if interface is actually bound
dpdk-devbind.py --status

# If not showing DPDK devices:
# 1. Run the binding script: ./01_bind_interface.sh
# 2. Verify interface is DPDK-compatible: lspci | grep -i ethernet
```

### Issue: "Feature Engine failed to start"

```bash
# Check error in log
cat logs/feature_engine.log | tail -20

# Common issues:
# 1. Suricata DPDK not running: ps aux | grep suricata
# 2. Wrong PCI address: dpdk-devbind.py --status
# 3. Python DPDK bindings missing: pip install python-dpdk
```

### Issue: "Permission denied"

```bash
# All DPDK operations need root
sudo ./run_realtime_engine_dpdk.sh start
sudo ./run_realtime_engine_dpdk.sh status
```

### Issue: "Interface disappeared and can't SSH"

**Don't panic!** The interface is just bound to DPDK. You can still access the system if you have:
- Physical console access
- Other network interfaces
- SSH on a different interface

To restore:
```bash
# If you can get access to a terminal:
sudo ./run_realtime_engine_dpdk.sh stop
# Choose 'y' to unbind when prompted

# Or manually:
sudo ./dpdk_suricata_ml_pipeline/scripts/unbind_interface.sh
# Interface will come back online
```

---

## Advanced: Tuning for Performance

### CPU Performance Tuning

```bash
# Edit pipeline.conf
DPDK_CORES="0,1"  # Use specific cores (isolated from kernel is better)
DPDK_HUGEPAGES="2048"  # 2GB for high-speed capture
```

### Latency vs Throughput Tradeoff

```bash
# Lower latency (real-time attack detection):
realtime_feature_engine.py --timeout 5 --dpdk

# Higher throughput (batch processing):
realtime_feature_engine.py --timeout 30 --dpdk
```

### Monitor Performance

```bash
# Real-time metrics
watch -n 1 'tail -1 logs/feature_engine.log | jq'

# CPU usage of DPDK processes
top -p $(pgrep -f "suricata|feature_engine" | tr '\n' ',')

# Packet drop statistics
dpdk-app --stats  # If available
```

---

## Stopping & Cleanup

### Clean Stop

```bash
# Stop pipeline gracefully
sudo ./run_realtime_engine_dpdk.sh stop

# Choose options:
# - Stop Kafka? Usually 'n' (may be shared)
# - Unbind DPDK? Usually 'y' (restore interface)
```

### Manual Cleanup

```bash
# Stop all processes
pkill -f "suricata"
pkill -f "feature_engine"
pkill -f "ml_consumer"
pkill -f "kafka"

# Restore interface (unbind DPDK)
sudo ./dpdk_suricata_ml_pipeline/scripts/unbind_interface.sh

# Verify interface is back online
ip link show enp2s0
# Should show: <BROADCAST,MULTICAST,UP>
```

---

## Log Files

```bash
logs/
├── feature_engine.log      # DPDK packet capture & feature extraction
├── ml_consumer.log          # ML inference with predictions
├── metrics_dashboard.log    # Optional metrics web UI
└── suricata/
    └── suricata.log         # Suricata DPDK alerts
```

## Kafka Topics

```bash
# Raw Suricata alerts (from DPDK capture)
suricata-alerts

# Extracted CICIDS features (from Feature Engine)
ml-features

# ML predictions with threat scores
ml-predictions
```

## Next Steps

1. **Verify Performance**: Compare throughput/latency between AF_PACKET and DPDK
2. **Test with Real Traffic**: Use `tcpreplay` to send attack traffic
3. **Integrate with SIEM**: Send ml-predictions to your monitoring system
4. **Tune Parameters**: Adjust timeout, cores, burst size for your hardware
5. **Monitor in Production**: Set up alerts for high threat scores

---

## Support & Documentation

- **Detailed comparison**: See `REALTIME_ENGINE_COMPARISON.md`
- **Implementation details**: See `DPDK_FEATURE_ENGINE_IMPLEMENTATION.md`
- **DPDK scripts**: `dpdk_suricata_ml_pipeline/scripts/`
- **Feature engine code**: `dpdk_suricata_ml_pipeline/src/realtime_feature_engine.py`

---

## Summary

```bash
# The complete workflow:

# 1. Setup (once)
sudo ./dpdk_suricata_ml_pipeline/scripts/01_bind_interface.sh

# 2. Start (whenever you need IDS)
sudo ./run_realtime_engine_dpdk.sh start

# 3. Monitor (watch in real-time)
tail -f logs/feature_engine.log

# 4. Stop (when done)
sudo ./run_realtime_engine_dpdk.sh stop
```

**That's it!** You now have a high-performance DPDK-based IDS with real-time CICIDS feature extraction and ML predictions.
