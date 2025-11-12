# Real-time Feature Engine: DPDK vs AF_PACKET

Comprehensive guide for high-performance CICIDS feature extraction with two architectural approaches.

## Quick Comparison

| Feature | AF_PACKET | DPDK |
|---------|-----------|------|
| **Script** | `run_realtime_engine.sh` | `run_realtime_engine_dpdk.sh` |
| **Throughput** | 100-500 Mbps | 1-10+ Gbps |
| **Latency** | Milliseconds | Microseconds |
| **CPU Overhead** | Moderate (kernel) | Low (zero-copy) |
| **Setup Complexity** | Simple | Complex (requires binding) |
| **Compatibility** | ALL interfaces (including USB) | DPDK-compatible NICs only |
| **Best For** | Testing, dev, low-moderate traffic | Production, high-speed networks |

---

## Architecture Comparison

### AF_PACKET Mode (Traditional)

```
Physical NIC (enp0s1)
    │
    └─ Linux Kernel Network Stack
        │
        ├─ AF_PACKET Socket (cluster_id=99, fanout enabled)
        │
        ├─→ Suricata (IDS signatures)  ──→ Kafka ──→ Alerts
        │   │ Reads: Raw Ethernet frames
        │   │ API: AF_PACKET socket API
        │   │ Mode: cluster_flow fanout
        │
        └─→ Feature Engine (CICIDS65) ──→ Kafka ──→ ML Model
            │ Reads: Same AF_PACKET fanout
            │ Computes: 65-feature vectors
            │ Throughput: ~100-500 Mbps
            │ Latency: Milliseconds

Data Flow:
1. NIC receives packet
2. Kernel copies to ring buffer
3. Both processes read same packets (fanout)
4. Each extracts different data
5. Written to Kafka
```

**Characteristics:**
- ✅ Works with any interface (USB adapters, virtual NICs)
- ✅ Simple setup (no kernel module compilation)
- ✅ Interface remains available for other networking
- ❌ Kernel overhead (context switches, memory copies)
- ❌ Limited to 100-500 Mbps sustained
- ❌ Higher latency (milliseconds)

### DPDK Mode (High-Performance)

```
Physical NIC (bound to DPDK via 01_bind_interface.sh)
    │
    └─ DPDK Userspace Runtime
        │
        ├─ DPDK PMD (Poll Mode Driver)
        │   Kernel: Bypassed entirely
        │   Memory: Zero-copy, DMA direct to userspace
        │   Polling: CPU spins (no interrupts/context switches)
        │
        ├─→ Suricata --dpdk (IDS signatures)  ──→ Kafka ──→ Alerts
        │   │ Reads: Native DPDK packet buffers
        │   │ API: DPDK rte_* functions
        │   │ Mode: PCI address-based capture
        │   │ Throughput: 1-10+ Gbps
        │   │ Latency: Microseconds
        │
        └─→ Feature Engine --dpdk (CICIDS65) ──→ Kafka ──→ ML Model
            │ Reads: Same DPDK packet pool
            │ Computes: 65-feature vectors
            │ Throughput: 1-10+ Gbps
            │ Latency: Microseconds

Data Flow:
1. NIC DMA writes packet directly to userspace memory (zero-copy)
2. DPDK PMD makes available in packet pool
3. Both processes (Suricata, Feature Engine) read from same pool
4. CPU continuously polls (no kernel context switch)
5. Each extracts different data
6. Written to Kafka with minimal latency
```

**Characteristics:**
- ✅ Line-rate capture (1-10+ Gbps)
- ✅ Minimal latency (microseconds)
- ✅ Low CPU overhead (zero-copy, no context switches)
- ✅ Suitable for production IDS
- ❌ Complex setup (kernel module compilation)
- ❌ Interface OFFLINE for normal networking
- ❌ Only DPDK-compatible NICs (Intel, Broadcom, Mellanox)

---

## Feature Engine Implementation Differences

### AF_PACKET Packet Capture

```python
# From realtime_feature_engine.py (AF_PACKET mode)

sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))

# Enable fanout mode to receive same packets as Suricata
fanout_arg = struct.pack('II', CLUSTER_ID, 2)  # cluster_id=99, type=PACKET_FANOUT_CPU
sock.setsockopt(socket.SOL_PACKET, 18, fanout_arg)  # 18 = PACKET_FANOUT

sock.bind((INTERFACE, 0))

# Main loop
while True:
    raw_packet, addr = sock.recvfrom(4096)  # Blocking read
    # Parse Ethernet → IP → TCP/UDP
    # Extract features
    # Publish to Kafka
```

**Key points:**
- AF_PACKET socket API (Linux-specific)
- Blocking recvfrom() call (kernel schedules process)
- Packets already processed by kernel (filtering, reassembly)
- Shared fanout with Suricata (cluster_id=99)
- Moderate throughput (~100-500 Mbps)

### DPDK Packet Capture

```python
# New: realtime_feature_engine.py (DPDK mode, when invoked with --dpdk flag)

from dpdk import DPDK, EAL, Mempool, RxQueue

# Initialize DPDK
eal = EAL(['--proc-type=secondary', '--file-prefix=ids'])
dpdk = DPDK()

# Create mempool for RX packets
mempool = Mempool("rx_pool", 512, 4096)

# Get RX queue from DPDK interface
# interface specified by PCI address (e.g., 0000:02:00.0)
rx_queue = RxQueue(pci_addr=PCI_ADDRESS, queue_id=0, mempool=mempool)

# Main loop
while True:
    # Non-blocking poll
    pkts = rx_queue.rx_burst(burst_size=32)  # Get up to 32 packets
    
    for pkt in pkts:
        # Parse packet from DPDK buffer (zero-copy)
        # Extract features
        # Publish to Kafka
    
    # CPU polls continuously (no blocking, no context switches)
```

**Key points:**
- DPDK EAL (Environment Abstraction Layer)
- Secondary process (primary is Suricata --dpdk)
- Polling model (CPU continuously checks for packets)
- Zero-copy access to packet memory
- Direct DMA from NIC to userspace (kernel-bypass)
- High throughput (1-10+ Gbps)
- Microsecond latency

---

## Setup & Execution

### Prerequisites for DPDK Mode

```bash
# 1. Check if interface is DPDK-compatible
lspci | grep -i ethernet
# Output: 02:00.0 Ethernet controller: Intel Corporation 82599ES 10-Gigabit SFI/SFP+

# 2. Verify Suricata has DPDK support
suricata --build-info | grep DPDK
# Output: DPDK support: yes

# 3. Bind interface to DPDK (MUST run first!)
sudo ./dpdk_suricata_ml_pipeline/scripts/01_bind_interface.sh

# 4. Verify binding
dpdk-devbind.py --status | grep DPDK
# Output: 0000:02:00.0 'Intel 82599ES' drv=vfio-pci
```

### Starting DPDK Pipeline

```bash
# Start the complete high-performance pipeline
sudo ./run_realtime_engine_dpdk.sh start

# Check status
sudo ./run_realtime_engine_dpdk.sh status

# Stop gracefully
sudo ./run_realtime_engine_dpdk.sh stop

# Restart
sudo ./run_realtime_engine_dpdk.sh restart
```

### Monitoring DPDK Pipeline

```bash
# Watch Feature Engine (DPDK mode)
tail -f logs/feature_engine.log

# Watch ML Consumer
tail -f logs/ml_consumer.log

# Watch Suricata DPDK stats
tail -f /var/log/suricata/suricata.log

# Check Kafka topics (with DPDK directly writing)
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
    --topic suricata-alerts --max-messages 10

# Check DPDK interface status
dpdk-devbind.py --status | grep DPDK
```

---

## Performance Tuning

### DPDK Configuration (pipeline.conf)

```bash
# CPU cores for DPDK PMD (should be dedicated, isolated)
DPDK_CORES="0,1"              # E.g., cores 0 and 1

# Memory allocation (huge pages)
DPDK_HUGEPAGES="2048"         # 2GB total
DPDK_MEMORY_CHANNELS="4"      # Match motherboard channels
```

### Feature Engine Tuning

```bash
# Timeout between flow emissions (faster detection = lower latency)
realtime_feature_engine.py --timeout 10  # 10 seconds (real-time)
realtime_feature_engine.py --timeout 30  # 30 seconds (batched)

# Burst size (larger = higher throughput, higher latency)
rx_queue.rx_burst(burst_size=32)  # Default
rx_queue.rx_burst(burst_size=64)  # Higher throughput
```

---

## Troubleshooting

### DPDK-Specific Issues

**Issue: "No DPDK devices found"**
```
Solution:
1. Verify interface is DPDK-compatible: lspci | grep -i ethernet
2. Check binding: dpdk-devbind.py --status
3. If not bound, run: sudo ./01_bind_interface.sh
```

**Issue: "EAL: Cannot open /dev/uio0"**
```
Solution: Load DPDK driver kernel module
sudo modprobe vfio-pci  # or uio_pci_generic
```

**Issue: "Feature Engine fails to start with DPDK"**
```
Solution:
1. Check Suricata DPDK is running: ps aux | grep suricata.*dpdk
2. Verify mempool size (may need more memory)
3. Check logs/feature_engine.log for specific errors
4. Fallback to AF_PACKET: ./run_realtime_engine.sh
```

**Issue: "Permission denied" when binding**
```
Solution:
sudo ./dpdk_suricata_ml_pipeline/scripts/01_bind_interface.sh
# Must run with sudo
```

---

## Migration: AF_PACKET → DPDK

### Step-by-step migration

```bash
# 1. Stop AF_PACKET pipeline (if running)
sudo ./run_realtime_engine.sh stop

# 2. Bind interface to DPDK
sudo ./dpdk_suricata_ml_pipeline/scripts/01_bind_interface.sh
# Answer prompts:
# - Enter interface name (e.g., ens33)
# - Select DPDK driver (vfio-pci recommended)

# 3. Verify binding
dpdk-devbind.py --status | grep DPDK

# 4. Start DPDK pipeline
sudo ./run_realtime_engine_dpdk.sh start

# 5. Monitor performance improvement
tail -f logs/feature_engine.log
# Look for: increased throughput, lower latency
```

### Rollback to AF_PACKET

```bash
# 1. Stop DPDK pipeline
sudo ./run_realtime_engine_dpdk.sh stop

# 2. Unbind interface (during stop, or manually)
sudo ./dpdk_suricata_ml_pipeline/scripts/unbind_interface.sh

# 3. Verify kernel driver is restored
ip link show ens33

# 4. Start AF_PACKET pipeline
sudo ./run_realtime_engine.sh start
```

---

## Architecture Decision Matrix

**Choose AF_PACKET if:**
- Testing/development environment
- USB Ethernet adapter (DPDK incompatible)
- Traffic < 500 Mbps sustained
- Network interface needed for other purposes
- Learning IDS/ML pipeline concepts
- Simple, minimal setup required

**Choose DPDK if:**
- Production deployment
- Network traffic > 500 Mbps (approaching 1+ Gbps)
- Dedicated capture NIC (not needed for other networking)
- Minimizing latency critical (microseconds vs milliseconds)
- Intel 1GbE/10GbE/40GbE, Broadcom, or Mellanox NIC
- Maximum throughput and accuracy required
- Cost of infrastructure supports high-end NICs

---

## Feature Extraction Accuracy

Both AF_PACKET and DPDK modes compute identical CICIDS65 features:

- **Flow Statistics**: Packet counts, byte counts, duration
- **Packet Length Stats**: Mean, std dev, min, max
- **Inter-arrival Times**: Flow-level IAT, forward/backward IAT
- **Protocol Flags**: TCP SYN/ACK/FIN/RST/PSH/URG counts
- **Payload Stats**: Bytes in header, payload correlation

**Difference**: Latency at which features are emitted

- AF_PACKET: ~1-10 second latency (kernel processing + socket blocking)
- DPDK: ~microsecond latency (zero-copy, direct polling)

**Impact on Attack Detection:**
- AF_PACKET: Detects attacks after 1-10 seconds
- DPDK: Detects attacks within microseconds
- Both compute same ML features → same prediction accuracy
- DPDK enables faster response (critical for real-time blocking)

---

## Summary

| Aspect | AF_PACKET | DPDK |
|--------|-----------|------|
| **Speed** | 100-500 Mbps, 1-10ms latency | 1-10+ Gbps, microseconds latency |
| **Accuracy** | Identical CICIDS65 features | Identical CICIDS65 features |
| **Detection Time** | 1-10 seconds | Microseconds |
| **Compatibility** | All interfaces | High-end NICs only |
| **Setup** | Trivial (no binding) | Complex (binding + kernel modules) |
| **Use Case** | Dev/Test | Production High-Speed IDS |

**Recommendation:** Start with AF_PACKET for development and testing. Migrate to DPDK for production deployments with high-speed networks and dedicated capture infrastructure.
