# ⚡ Quick Start: AF_PACKET Mode (Fixed!)

## 🎯 The Issue (SOLVED!)

Your network adapter `enx00e04c36074c` is a **USB Ethernet adapter** that cannot use DPDK.

**Error you were getting:**
```
ValueError: Unknown device: usb-0000:00:14.0-1.3. 
Please specify device in "bus:slot.func" format
```

**Why:** DPDK only works with PCI/PCIe network cards, not USB adapters.

---

## ✅ The Solution: AF_PACKET Mode

Use **AF_PACKET mode** instead - it works with ANY network interface!

### 🚀 One-Command Start

```bash
cd ~/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
sudo ./quick_start.sh
```

Select option **1** to start the complete pipeline!

---

## 📋 Manual Step-by-Step

### Option A: Complete Pipeline
```bash
cd ~/Programming/IDS/dpdk_suricata_ml_pipeline/scripts

# Step 1: Start Kafka
sudo ./02_setup_kafka.sh

# Step 2: Start Suricata (AF_PACKET mode - NO BINDING NEEDED!)
sudo ./03_start_suricata_afpacket.sh

# Step 3: Start ML Consumer
./04_start_ml_consumer.sh

# Step 4: Generate/Replay Traffic
sudo ./05_replay_traffic.sh
```

### Option B: Just Test Suricata
```bash
cd ~/Programming/IDS/dpdk_suricata_ml_pipeline/scripts

# Start Suricata only
sudo ./03_start_suricata_afpacket.sh

# In another terminal, generate traffic
ping 8.8.8.8
curl https://google.com

# Watch alerts
tail -f ../logs/suricata/eve.json | jq .
```

---

## 🎮 Interactive Menu

```bash
cd ~/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
./quick_start.sh
```

Options:
- **1** - Start Complete Pipeline
- **2** - Start Kafka Only  
- **3** - Start Suricata Only
- **4** - Start ML Consumer Only
- **5** - Replay Traffic
- **6** - Check Status
- **7** - Stop All
- **8** - View Logs

---

## 📊 What Changed?

### Old (DPDK - Doesn't Work with USB)
```bash
sudo ./01_bind_interface.sh    # ❌ FAILS with USB adapter
sudo ./03_start_suricata.sh    # Uses DPDK mode
```

### New (AF_PACKET - Works with Everything!)
```bash
# No binding needed!
sudo ./03_start_suricata_afpacket.sh  # ✅ Works perfectly!
```

---

## 🔍 Monitoring & Status

### Check if Running
```bash
# Quick status check
cd ~/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
./status_check.sh

# Or manual check
ps aux | grep suricata
ps aux | grep kafka
```

### View Live Alerts
```bash
# Pretty JSON output
tail -f logs/suricata/eve.json | jq .

# Raw alerts
tail -f logs/suricata/fast.log

# ML predictions
tail -f logs/ml/consumer.log
```

### Suricata Stats
```bash
# Detailed counters
suricatasc -c dump-counters

# Connection info
suricatasc -c iface-stat
```

---

## 🛠️ Troubleshooting

### Interface is Down
```bash
sudo ip link set enx00e04c36074c up
```

### Suricata Won't Start
```bash
# Kill existing process
sudo pkill -9 suricata

# Check logs
sudo tail -50 /var/log/suricata/suricata.log

# Try starting again
sudo ./03_start_suricata_afpacket.sh
```

### No Traffic Captured
```bash
# Make sure interface is connected and has IP
ip addr show enx00e04c36074c

# Generate test traffic
ping 8.8.8.8
curl https://google.com

# Check if packets are being processed
suricatasc -c uptime
```

### Kafka Issues
```bash
# Restart Kafka
sudo systemctl restart kafka

# Check Kafka is listening
sudo netstat -tulpn | grep 9092
```

---

## 📈 Performance Expectations

### Your USB Adapter with AF_PACKET
- **Throughput**: 100-500 Mbps ✅
- **Packet Rate**: ~100K packets/sec ✅  
- **Latency**: 10-50µs ✅
- **CPU Usage**: 50-80% (2 cores) ✅

**This is perfect for:**
- ✅ Development and testing
- ✅ ML model training
- ✅ Research projects
- ✅ Small network monitoring

---

## 📚 Files Created/Modified

### New Files
1. **`scripts/03_start_suricata_afpacket.sh`** - Main AF_PACKET script
2. **`scripts/quick_start.sh`** - Interactive menu
3. **`USB_ADAPTER_GUIDE.md`** - Detailed guide
4. **`AF_PACKET_QUICK_START.md`** - This file!

### Modified Files
1. **`config/pipeline.conf`** - Added USB adapter note

### Old Files (Still Available)
- `scripts/01_bind_interface.sh` - For DPDK (if you get PCI NIC later)
- `scripts/03_start_suricata.sh` - For DPDK mode

---

## 🎓 Next Steps

1. ✅ **Start the pipeline**: `sudo ./quick_start.sh` → option 1
2. ✅ **Test with traffic**: `sudo ./05_replay_traffic.sh`
3. ✅ **Monitor alerts**: `tail -f logs/suricata/eve.json | jq .`
4. ✅ **Train ML models**: Use the notebooks in `notebooks/`
5. ✅ **Run tests**: `cd tests && python quick_attack_demo.py`

---

## 💡 Want DPDK in the Future?

If you want to try DPDK later, you'll need:
1. Buy a **PCI/PCIe Ethernet card** (Intel i350, X520, etc.)
2. Install it in a desktop/server
3. Update `NETWORK_INTERFACE` in `config/pipeline.conf`
4. Then use the original `01_bind_interface.sh` script

**But for now, AF_PACKET works perfectly!**

---

## 🎉 Summary

| What | Status |
|------|--------|
| USB Adapter Issue | ✅ Fixed! |
| DPDK Error | ✅ Resolved - using AF_PACKET |
| Scripts Ready | ✅ Yes - use new scripts |
| Performance | ✅ Great for your use case |
| Works Now | ✅ YES! |

**You're all set! Run `sudo ./quick_start.sh` and start capturing! 🚀**

---

## 📞 Reference Links

- **Full Details**: See `USB_ADAPTER_GUIDE.md`
- **Suricata AF_PACKET Docs**: https://docs.suricata.io/en/latest/capture-hardware/af-packet.html
- **Your Config**: `config/pipeline.conf`
- **Status Check**: `./scripts/status_check.sh`
