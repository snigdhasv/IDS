# 🎯 PCAP Replay with IDS - Quick Reference

## ✅ Setup Complete!

Your system is configured for replaying CICIDS2017 PCAP files to your IDS pipeline.

---

## 📋 Hardware Configuration

- **Replay NIC:** Realtek (`enp5s0`) - Sends packets
- **Capture NIC:** Intel 82599ES (`enp1s0` / `01:00.0`) - Receives via DPDK
- **Connection:** Direct cable between `enp5s0` ↔ `enp1s0`
- **Internet NIC:** Realtek (`enp3s0`) - Keep for internet access

---

## 🚀 Quick Start Options

### Option 1: Complete Automated Pipeline
```bash
cd ~/SE_02_2025/IDS
sudo ./run_ids_with_replay.sh
```
This will:
1. Setup DPDK
2. Let you choose IDS mode (DPDK/AF_PACKET)
3. Start the IDS
4. Replay the PCAP
5. Show you where to find results

---

### Option 2: Manual Control (Step-by-step)

#### Step 1: Setup DPDK
```bash
cd ~/SE_02_2025/IDS
sudo ./setup_dpdk_capture.sh
```

#### Step 2: Start IDS (Choose ONE)

**Option A - Full DPDK Pipeline:**
```bash
sudo ./run_realtime_engine_dpdk.sh start
```

**Option B - AF_PACKET Pipeline:**
```bash
sudo ./run_realtime_engine.sh start
```

**Option C - Just Feature Engine:**
```bash
cd dpdk_suricata_ml_pipeline/src
source ../venv/bin/activate
python3 dpdk_feature_engine.py
```

#### Step 3: Replay PCAP
```bash
# Use the fixed Wednesday PCAP (8.4 GB, no MTU issues)
sudo tcpreplay --intf1=enp5s0 --mbps=100 --stats=30 /home/ifscr/Downloads/Wednesday-fixed.pcap

# Or use the script to replay all
sudo ./fix_and_replay_pcaps.sh
```

#### Step 4: Monitor Results

**Watch Feature Extraction:**
```bash
tail -f logs/feature_engine.log
```

**Watch ML Predictions:**
```bash
tail -f logs/ml_consumer.log
```

**Watch Suricata Alerts:**
```bash
tail -f /var/log/suricata/suricata.log
```

**Real-time Kafka Output:**
```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic ml-predictions
```

---

## 📁 PCAP Files

Located in `/home/ifscr/Downloads/`:
- ✅ `Wednesday-fixed.pcap` (8.4 GB) - Ready to use!
- ⚠️ `Monday-WorkingHours.pcap` (11 GB) - Needs fixing
- ⚠️ `Tuesday-WorkingHours.pcap` (11 GB) - Needs fixing
- ⚠️ `Thursday-WorkingHours.pcap` (7.8 GB) - Needs fixing
- ⚠️ `Friday-WorkingHours.pcap` (8.3 GB) - Needs fixing

**To fix other PCAPs:**
```bash
cd ~/SE_02_2025/IDS
sudo ./fix_and_replay_pcaps.sh
```

This will:
1. Use `tcprewrite` to fix MTU issues
2. Store fixed versions in `/home/ifscr/Downloads/fixed_pcaps/`
3. Replay them automatically

---

## 🧪 Testing Mode (Just testpmd)

If you just want to test packet reception without the full IDS:

```bash
# 1. Setup DPDK
sudo ./setup_dpdk_capture.sh

# 2. Start testpmd
sudo dpdk-testpmd -l 0-1 -n 4 -- -i --port-topology=chained

# 3. In testpmd:
set promisc all on
start

# 4. In another terminal, replay:
sudo tcpreplay --intf1=enp5s0 --mbps=100 /home/ifscr/Downloads/Wednesday-fixed.pcap

# 5. Check stats in testpmd:
show port stats all
```

---

## 🛠️ Scripts Created

All scripts are in `/home/ifscr/SE_02_2025/IDS/`:

1. **`setup_dpdk_capture.sh`** - Bind Intel NIC to DPDK
2. **`replay_pcaps.sh`** - Simple replay script
3. **`fix_and_replay_pcaps.sh`** - Fix MTU issues & replay all
4. **`run_ids_with_replay.sh`** - Complete automated pipeline
5. **`test_replay_complete.sh`** - Guided test mode

---

## ⚙️ Key Settings

**Replay Speed:** 100 Mbps (adjust in scripts)
- Lower for stability: `--mbps=50`
- Higher for speed: `--mbps=200` or `--topspeed`

**Stats Display:** Every 30 seconds
- Change with `--stats=10` for updates every 10 seconds

**DPDK Cores:** Using cores 0-1
- Adjust in testpmd: `-l 0-3` for more cores

---

## 🔧 Troubleshooting

**Problem: No packets in testpmd**
```bash
# Check you're using the right NIC (enp5s0, NOT enp3s0)
ip link show enp5s0

# Verify DPDK binding
sudo dpdk-devbind.py --status | grep DPDK
```

**Problem: "Message too long" errors**
```bash
# Use the Wednesday-fixed.pcap or run fix script
sudo ./fix_and_replay_pcaps.sh
```

**Problem: testpmd won't start - "Cannot create lock"**
```bash
# Kill old testpmd
sudo pkill -9 testpmd
sleep 2
# Then restart
```

**Problem: Intel NIC not bound to DPDK**
```bash
sudo ./setup_dpdk_capture.sh
```

---

## 📊 Expected Results

For Wednesday-fixed.pcap (8.4 GB):
- **Packets:** ~5-10 million packets
- **Duration:** ~10-15 minutes at 100 Mbps
- **Features:** Thousands of flows extracted
- **Predictions:** ML model will classify as BENIGN/Attack

---

## 🎯 Next Steps

1. **Test with testpmd first** - Verify packet flow works
2. **Run IDS with Wednesday-fixed.pcap** - Get ML predictions
3. **Fix other PCAPs** - Process Monday through Friday
4. **Analyze results** - Check logs for attack classifications

---

## 🆘 Need Help?

Check these logs:
- DPDK binding: `sudo dpdk-devbind.py --status`
- testpmd stats: `show port stats all`
- Feature Engine: `tail -f logs/feature_engine.log`
- ML Consumer: `tail -f logs/ml_consumer.log`

---

**Created:** 2025-11-12  
**System:** Intel 82599ES + Realtek NICs with direct cable connection
