# 🔧 Troubleshooting Guide: DPDK Feature Engine Issues

## ❌ Problems You Encountered

When running `sudo ./run_realtime_engine_dpdk.sh test`, you saw:

1. **Kafka Connection Refused** - `ECONNREFUSED` on port 9092
2. **PyDPDK Not Installed** - Fallback to Scapy mode
3. **Reading from Suricata EVE** - Not capturing from DPDK interface directly

## ✅ Solutions & Workarounds

### Solution 1: Start Kafka First (REQUIRED)

```bash
# Start Kafka before starting the feature engine
bash dpdk_suricata_ml_pipeline/scripts/02_setup_kafka.sh &

# Wait 5 seconds for Kafka to start
sleep 5

# Verify Kafka is running
sudo netstat -tuln | grep 9092
# Should show: tcp6  0  0 127.0.0.1:9092  :::*  LISTEN
```

**Status**: ✅ **Kafka is now running!**

### Solution 2: Use Standard Packet Capture (Recommended for Testing)

The `dpdk_feature_engine.py` requires **PyDPDK** (complex to install). For initial testing, use standard tools:

#### Option A: Simple Packet Capture Test
```bash
# This script temporarily unbinds Intel NIC from DPDK
# and uses tcpdump to verify packet flow
sudo ./test_packet_capture_simple.sh
```

Then in another terminal:
```bash
sudo tcpreplay --intf1=enp5s0 dpdk_suricata_ml_pipeline/pcap_samples/normal_traffic.pcap
```

####Option B: Use AF_PACKET Feature Engine (No DPDK)
```bash
# Edit the script to use realtime_feature_engine.py instead
# This uses AF_PACKET (same as Suricata AF_PACKET mode)

cd dpdk_suricata_ml_pipeline/src
source ../../venv/bin/activate

# First unbind from DPDK
sudo dpdk-devbind.py --bind=ixgbe 0000:01:00.0
sudo ip link set dev enp1s0 up

# Run AF_PACKET feature engine
python3 realtime_feature_engine.py
```

### Solution 3: Install PyDPDK (Advanced - Not Recommended)

PyDPDK installation is complex and requires:
- DPDK development headers
- Cython
- Specific DPDK version compatibility

**Skip this unless absolutely needed.**

## 🎯 Recommended Workflow (Step-by-Step)

### For Quick Testing Without DPDK Complexity:

```bash
# Terminal 1: Setup NICs (but use kernel drivers)
sudo ./setup_realtek_to_intel_ids.sh

# Then unbind Intel from DPDK for now
sudo dpdk-devbind.py --bind=ixgbe 0000:01:00.0
sudo ip link set dev enp1s0 up
sudo ip link set dev enp1s0 promisc on

# Start Kafka
bash dpdk_suricata_ml_pipeline/scripts/02_setup_kafka.sh &
sleep 5

# Start simple packet capture
sudo tcpdump -i enp1s0 -n
```

```bash
# Terminal 2: Send packets
sudo tcpreplay --intf1=enp5s0 --mbps=10 \
    dpdk_suricata_ml_pipeline/pcap_samples/mixed_traffic_sample.pcap
```

You should see packets in tcpdump!

### For Full IDS Pipeline (Suricata + ML):

```bash
# Use AF_PACKET mode instead of DPDK mode
cd dpdk_suricata_ml_pipeline/scripts

# Start Kafka
bash 02_setup_kafka.sh &
sleep 5

# Start Suricata in AF_PACKET mode (not DPDK)
sudo bash 03_start_suricata_afpacket.sh

# Start feature engine (AF_PACKET mode)
cd ../src
source ../../venv/bin/activate
python3 realtime_feature_engine.py &

# Start ML consumer
python3 realtime_ml_consumer.py &
```

## 📊 What Each Mode Does

| Mode | Packet Capture | Performance | Complexity | Status |
|------|----------------|-------------|------------|--------|
| **DPDK** | Direct hardware (PMD) | 10+ Gbps | Very High | ❌ Requires PyDPDK |
| **AF_PACKET** | Kernel socket + fanout | 1-5 Gbps | Medium | ✅ Works out of box |
| **Scapy** | Standard pcap | < 1 Gbps | Low | ✅ Works (slow) |
| **tcpdump** | libpcap | 1-2 Gbps | Low | ✅ For testing only |

## 🔍 Current Status Check

```bash
# Check Kafka
sudo netstat -tuln | grep 9092
# ✅ Should show port 9092 LISTEN

# Check DPDK binding
dpdk-devbind.py --status
# Shows if Intel NIC is bound to vfio-pci or ixgbe

# Check network interfaces
ip -brief link show
# enp1s0 - Intel (target for IDS)
# enp5s0 - Realtek (packet sender)
# enp3s0 - Realtek (management)

# Check if processes are running
pgrep -a kafka
pgrep -a suricata
pgrep -a python | grep feature
```

## 🚀 Quick Commands to Run Now

### Option 1: Simple Packet Flow Test (No ML, just verify connectivity)

```bash
# Terminal 1
sudo ./test_packet_capture_simple.sh
```

```bash
# Terminal 2 (when prompted)
sudo tcpreplay --intf1=enp5s0 dpdk_suricata_ml_pipeline/pcap_samples/normal_traffic.pcap
```

### Option 2: Full Pipeline with AF_PACKET (Not DPDK)

```bash
# Unbind from DPDK first
sudo dpdk-devbind.py --bind=ixgbe 0000:01:00.0
sudo ip link set dev enp1s0 up

# Start Suricata AF_PACKET mode
sudo bash dpdk_suricata_ml_pipeline/scripts/03_start_suricata_afpacket.sh

# Send traffic
sudo tcpreplay --intf1=enp5s0 --loop=5 dpdk_suricata_ml_pipeline/pcap_samples/mixed_traffic_sample.pcap

# Check Suricata logs
tail -f /var/log/suricata/fast.log
```

## ⚠️ Why DPDK Mode Failed

1. **PyDPDK Missing**: The feature engine code tries to `import dpdk` but PyDPDK is not installed
2. **Fallback Mode**: When PyDPDK fails, it falls back to reading Suricata's eve.json file
3. **No Active Flows**: Suricata wasn't running, so eve.json had no new data
4. **Kafka Down**: Without Kafka, features can't be sent to ML consumer anyway

## ✅ Solutions Applied

1. ✅ **Kafka started** - Running on port 9092
2. ✅ **Created simple test script** - `test_packet_capture_simple.sh`
3. ✅ **Created send traffic script** - `send_test_traffic.sh`
4. ✅ **Updated docs** - This troubleshooting guide

## 📝 Next Steps

Choose your path:

**Path A: Quick Test (Recommended)**
1. Run: `sudo ./test_packet_capture_simple.sh`
2. Verify packets flow from Realtek to Intel
3. Once confirmed, proceed to full pipeline

**Path B: Full IDS with AF_PACKET**
1. Unbind Intel from DPDK: `sudo dpdk-devbind.py --bind=ixgbe 0000:01:00.0`
2. Start Suricata: `sudo bash dpdk_suricata_ml_pipeline/scripts/03_start_suricata_afpacket.sh`
3. Start ML consumer: `cd dpdk_suricata_ml_pipeline/src && python3 realtime_ml_consumer.py`
4. Send traffic: `./send_test_traffic.sh`

**Path C: Install PyDPDK (Advanced)**
- Not recommended unless you need true 10+ Gbps throughput
- Requires building DPDK from source with Python bindings

## 🆘 Still Having Issues?

```bash
# Check all logs
tail -f logs/feature_engine.log
tail -f logs/ml_consumer.log
tail -f /var/log/suricata/suricata.log

# Verify cable connection
ethtool enp5s0 | grep "Link detected"
ethtool enp1s0 | grep "Link detected"

# Test with ping (after unbinding from DPDK)
sudo ip addr add 192.168.100.2/24 dev enp1s0
ping -c 3 192.168.100.1  # Should reach Realtek NIC
```

---

**TL;DR**: Kafka is now running. For testing, use `test_packet_capture_simple.sh` or run Suricata in AF_PACKET mode instead of DPDK mode. PyDPDK is not required for the pipeline to work!
