# Intel X520 DPDK Setup Guide

## X520 Compatibility Overview

✅ **FULLY COMPATIBLE** with DPDK 23.11.0 and your pipeline

### X520 Specifications
- **Vendor**: Intel
- **Interface Options**: 1-port (SR1), 2-port (DA1), 4-port variants
- **Speed**: 10 Gbps per port
- **DPDK PMD**: ixgbe (excellent support, battle-tested)
- **Driver**: ixgbe (kernel) or igb_uio/vfio-pci (DPDK)

### DPDK 23.11.0 Support Matrix
| Feature | Status |
|---------|--------|
| ixgbe PMD | ✓ Fully supported |
| Vectorized RX/TX | ✓ Supported |
| RSS (multi-queue) | ✓ Enabled |
| Flow Director | ✓ Supported |
| Interrupt Mode | ✓ Supported |
| Poll Mode Driver | ✓ Optimized |

---

## Installation Steps

### 1. Pre-Installation Check

```bash
# Check if X520 detected
lspci | grep -i "ixgbe\|Intel.*Ethernet"

# Example output:
# 02:00.0 Ethernet controller: Intel Corporation 82599ES 10-Gigabit (X520)
# 02:00.1 Ethernet controller: Intel Corporation 82599ES 10-Gigabit (X520)
```

### 2. Load ixgbe Kernel Driver (if not already loaded)

```bash
# Load the ixgbe driver
modprobe ixgbe

# Verify
lsmod | grep ixgbe
```

### 3. Identify Your X520 Interfaces

```bash
# List network interfaces
ip link show

# Or with ethtool
ethtool -i eth0
# Look for: driver: ixgbe
```

### 4. Bind to DPDK

You have two options:

#### **Option A: UIO (Legacy, simpler)**
```bash
# Load UIO driver
modprobe uio
insmod /lib/modules/$(uname -r)/kernel/drivers/uio/igb_uio.ko

# Bind X520 to igb_uio
dpdk-devbind.py -b igb_uio 0000:02:00.0
dpdk-devbind.py -b igb_uio 0000:02:00.1  # if dual-port

# Verify
dpdk-devbind.py --status | grep igb_uio
```

#### **Option B: VFIO (Modern, recommended)**
```bash
# Enable IOMMU (if not already)
# Edit /etc/default/grub and add: intel_iommu=on
# Then run: sudo update-grub && sudo reboot

# Enable VFIO
modprobe vfio
modprobe vfio_pci

# Bind X520
dpdk-devbind.py -b vfio-pci 0000:02:00.0
dpdk-devbind.py -b vfio-pci 0000:02:00.1

# Verify
dpdk-devbind.py --status | grep vfio-pci
```

### 5. Configure Pipeline for X520

Edit `/home/ifscr/SE_02_2025/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf`:

```ini
# Network interface (X520 port 0)
NETWORK_INTERFACE=eth0
INTERFACE_PCI_ADDRESS=0000:02:00.0

# Optional: if using dual-port, second port
# SECONDARY_INTERFACE_PCI=0000:02:00.1

# DPDK Settings (optimized for X520)
DPDK_COREMASK=0x0F          # Cores 0-3 (adjust for your CPU)
DPDK_MEMPOOL_SIZE=262144    # 256K buffers
DPDK_BURST_SIZE=32          # RX/TX burst size

# Suricata DPDK specific
SURICATA_DPDK_WORKERS=2     # Worker threads
SURICATA_QUEUE_SIZE=2048    # Packet queue size
```

### 6. Verify Setup

```bash
# Check DPDK binding
sudo dpdk-devbind.py --status

# Test DPDK app (simple packet count)
cd /home/ifscr/SE_02_2025/IDS
source venv/bin/activate
python3 -c "from dpdk_suricata_ml_pipeline.src.dpdk_utils import check_dpdk; check_dpdk('0000:02:00.0')"
```

---

## Expected Performance with X520

| Metric | Expected |
|--------|----------|
| **Throughput** | 10 Gbps line rate (both ports if dual) |
| **Packets/sec** | ~14.88 Mpps per port (64-byte frames) |
| **Latency** | Sub-microsecond (kernel bypass) |
| **CPU Usage** | <10% per core (zero-copy) |
| **Feature Extraction Rate** | 1-10 Gbps with full CICIDS65 calculation |

---

## Running the Pipeline on X520

```bash
# Start complete DPDK pipeline
sudo bash /home/ifscr/SE_02_2025/IDS/run_realtime_engine_dpdk.sh start

# Check status
sudo bash /home/ifscr/SE_02_2025/IDS/run_realtime_engine_dpdk.sh status

# Monitor in real-time
tail -f /home/ifscr/SE_02_2025/IDS/logs/feature_engine.log
tail -f /home/ifscr/SE_02_2025/IDS/logs/ml_consumer.log
```

---

## Troubleshooting X520 Issues

### **Issue: Device not detected**
```bash
# Check if X520 kernel driver is loaded
lsmod | grep ixgbe
# If not, load it
sudo modprobe ixgbe
```

### **Issue: Binding fails (permission denied)**
```bash
# Make sure you're running as root
sudo su -
dpdk-devbind.py -b igb_uio 0000:02:00.0
```

### **Issue: VFIO binding fails (IOMMU not enabled)**
```bash
# Enable IOMMU in BIOS (Intel: VT-d)
# Edit /etc/default/grub:
# GRUB_CMDLINE_LINUX="... intel_iommu=on iommu=pt"
# Then:
sudo update-grub
sudo reboot
```

### **Issue: Low throughput (<1 Gbps)**
```bash
# Check RSS is enabled
ethtool -n eth0 rx-flow-hash tcp4

# Verify core assignment (should use multiple cores)
# Edit pipeline.conf and set:
DPDK_COREMASK=0x0F  # or wider mask

# Check for packet drops
cat /proc/net/dev | grep eth0
```

### **Issue: High latency variance**
```bash
# Disable CPU frequency scaling
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Disable power management
sudo systemctl stop cpupower.service
```

---

## Next Steps: Testing with PCAP Replay

Once X520 is bound and pipeline starts successfully:

```bash
# See: PCAP_REPLAY_GUIDE.md
# This will replay CICIDS dataset through X520 for accuracy testing
bash replay_pcap_for_testing.sh dataset.pcap
```

---

## Reference: X520 Linux Driver Info

```bash
# View detailed X520 info
lspci -vv -s 02:00.0

# Monitor interface stats
watch -n 1 'ethtool -S eth0 | grep -E "rx|tx|drops"'

# View DPDK port info
dpdk-devbind.py --status
```

---

## Architecture with X520

```
┌─────────────────────────────────────┐
│      Intel X520 (10 Gbps)           │
│  PCI: 0000:02:00.0, 0000:02:00.1   │
└──────────────┬──────────────────────┘
               │
          DPDK PMD
          (ixgbe)
               │
     ┌─────────┴──────────┐
     │                    │
  Suricata            Feature Engine
  (alerts)            (CICIDS65 features)
     │                    │
     └──────────┬─────────┘
                │
              Kafka
                │
         ML Consumer
         (ensemble voting)
                │
            CSV Logs
            (accuracy calc)
```

---

## Validation Checklist

- [ ] X520 recognized by `lspci`
- [ ] ixgbe driver loaded: `lsmod | grep ixgbe`
- [ ] X520 interfaces visible: `ip link show`
- [ ] DPDK binding successful: `dpdk-devbind.py --status`
- [ ] Suricata compiled with DPDK: `suricata --build-info | grep DPDK`
- [ ] Pipeline starts without errors: `sudo bash run_realtime_engine_dpdk.sh start`
- [ ] Kafka topics created: `kafka-topics.sh --list`
- [ ] Feature engine log shows packets: `tail -f logs/feature_engine.log`
- [ ] ML consumer shows predictions: `tail -f logs/ml_consumer.log`

---

**Ready to test accuracy with PCAP replay? See `PCAP_REPLAY_GUIDE.md`**
