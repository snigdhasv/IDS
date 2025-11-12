# X520 DPDK Setup & Accuracy Testing Summary

## ✅ Your Complete Solution

You now have everything to test your ML pipeline on Intel X520 with accuracy metrics. Here's what was created:

### 📚 Documentation Files

1. **X520_DPDK_SETUP.md** - Complete X520 setup guide
   - Hardware compatibility verification (✅ DPDK 23.11.0 fully supports X520)
   - Driver installation (ixgbe)
   - DPDK binding (igb_uio or vfio-pci)
   - Performance expectations

2. **PCAP_REPLAY_ACCURACY_GUIDE.md** - End-to-end testing workflow
   - Step-by-step pipeline startup
   - PCAP replay with ground truth labels
   - Accuracy metrics calculation
   - Troubleshooting guide

### 🐍 Python Scripts

1. **realtime_ensemble_consumer_with_csv.py** - Enhanced ML consumer with CSV logging
   - Logs all predictions with confidence scores
   - Records per-model predictions for voting analysis
   - Includes ground truth comparison
   - Format: timestamp, flow_id, ground_truth, predictions, confidences, correctness

2. **replay_pcap_for_testing.py** - PCAP replay module
   - Extracts packet flows from PCAP files
   - Matches flows to ground truth labels
   - Sends packets to Kafka at controlled speeds
   - Supports real-time playback or fast replay

3. **calculate_accuracy_metrics.py** - Comprehensive metrics calculator
   - Accuracy, Precision, Recall, F1 Score
   - Per-attack-type breakdown
   - Confusion matrix
   - Confidence and agreement analysis
   - Model voting statistics

---

## 🚀 Quick Start (Tomorrow with X520)

### 1. Physical Setup
```bash
# Identify X520 interfaces
lspci | grep -i "ixgbe\|Intel.*Ethernet"

# Bind to DPDK
sudo modprobe ixgbe
sudo insmod /lib/modules/$(uname -r)/kernel/drivers/uio/igb_uio.ko
sudo dpdk-devbind.py -b igb_uio 0000:02:00.0  # Adjust PCI address
sudo dpdk-devbind.py --status  # Verify binding
```

### 2. Start Pipeline
```bash
cd /home/ifscr/SE_02_2025/IDS
sudo bash run_realtime_engine_dpdk.sh start
sleep 5
source venv/bin/activate
```

### 3. Run ML Consumer with CSV Output
```bash
python3 dpdk_suricata_ml_pipeline/src/realtime_ensemble_consumer_with_csv.py \
    --csv-output predictions.csv
```

### 4. Prepare Ground Truth
```bash
# Create ground truth CSV from your dataset
# Format: src_ip, dst_ip, src_port, dst_port, label
# See PCAP_REPLAY_ACCURACY_GUIDE.md for examples
```

### 5. Replay PCAP with Test Data
```bash
python3 dpdk_suricata_ml_pipeline/src/replay_pcap_for_testing.py \
    --pcap-file your_dataset.pcap \
    --ground-truth ground_truth.csv \
    --max-packets 50000  # Start small for testing
```

### 6. Calculate Accuracy
```bash
python3 dpdk_suricata_ml_pipeline/src/calculate_accuracy_metrics.py \
    --predictions predictions.csv \
    --output metrics.json \
    --confusion-matrix confusion_matrix.png
```

### 7. View Results
```bash
cat metrics.json | python3 -m json.tool
# Shows: accuracy, precision, recall, F1, per-class breakdown
```

---

## 📊 What You'll Get

**Sample Output:**
```
ACCURACY METRICS REPORT
======================================================================

📊 OVERALL METRICS:
   Accuracy:     0.9842 (98.42%)
   Precision:    0.9741
   Recall:       0.9823
   F1 Score:     0.9782

📈 PER-CLASS METRICS:
   BENIGN:       Precision: 0.9923, Recall: 0.9967, F1: 0.9945
   DDOS:         Precision: 0.9156, Recall: 0.9234, F1: 0.9195
   SSH_PATATOR:  Precision: 0.9234, Recall: 0.8567, F1: 0.8888

🎯 CONFIDENCE METRICS:
   Mean Confidence: 0.9823
   Agreement Distribution:
      high (>=0.80)     98.5%
      medium (0.60-80)   1.2%
      low (<0.60)        0.3%
```

---

## 🎯 X520 Performance (Expected)

| Metric | Value |
|--------|-------|
| **Throughput** | 10 Gbps line rate |
| **Packets/sec** | 14.88 Mpps (64-byte frames) |
| **Latency** | Sub-microsecond |
| **CPU Usage** | <10% per core |
| **Feature Extraction Rate** | 1-10 Gbps with CICIDS65 |
| **Model Prediction Latency** | <100 μs |

---

## 📂 File Locations

```
/home/ifscr/SE_02_2025/IDS/
├── X520_DPDK_SETUP.md                          # X520 hardware setup
├── PCAP_REPLAY_ACCURACY_GUIDE.md               # Testing workflow
├── dpdk_suricata_ml_pipeline/
│   └── src/
│       ├── realtime_ensemble_consumer_with_csv.py    # ← CSV logging
│       ├── replay_pcap_for_testing.py                # ← PCAP replay
│       └── calculate_accuracy_metrics.py             # ← Metrics calc
├── logs/
│   ├── feature_engine.log                      # Real-time feature extraction
│   ├── ml_consumer.log                         # Predictions
│   └── metrics_dashboard.log
└── predictions.csv                             # Generated during replay
```

---

## ✅ Validation Checklist

Before running on X520, verify:

- [ ] X520 recognized by `lspci | grep -i ixgbe`
- [ ] ixgbe driver installed: `modprobe ixgbe`
- [ ] X520 bound to DPDK: `dpdk-devbind.py --status`
- [ ] Suricata compiled with DPDK: `suricata --build-info | grep DPDK`
- [ ] Pipeline starts: `sudo bash run_realtime_engine_dpdk.sh start`
- [ ] Kafka running: `netstat -tuln | grep 9092`
- [ ] Feature engine logs: `tail -f logs/feature_engine.log`
- [ ] ML consumer runs: `python3 realtime_ensemble_consumer_with_csv.py`
- [ ] PCAP replays: `python3 replay_pcap_for_testing.py --pcap-file test.pcap`
- [ ] Metrics calculate: `python3 calculate_accuracy_metrics.py --predictions predictions.csv`

---

## 🔍 Troubleshooting

### "dpdk-devbind.py not found"
```bash
which dpdk-devbind.py
# If not in PATH, use full path:
sudo /usr/local/bin/dpdk-devbind.py --status
```

### "DPDK support: no" in Suricata
Suricata needs to be compiled with DPDK:
```bash
suricata --build-info | grep DPDK
# If "no", you need to recompile Suricata with DPDK support
```

### Low throughput with X520
1. Check RSS is enabled: `ethtool -n eth0 rx-flow-hash tcp4`
2. Check multiple cores assigned: Edit pipeline.conf DPDK_COREMASK
3. Disable CPU power scaling: `echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`

### "No valid predictions with ground truth found"
1. Check if labels are in predictions.csv: `grep -c "BENIGN\|ATTACK" predictions.csv`
2. Verify ground truth CSV format matches flow extraction
3. Test with small dataset first: `--max-packets 1000`

---

## 📞 Support Resources

1. **DPDK Documentation**: https://doc.dpdk.org/guides/
2. **Suricata DPDK Mode**: https://suricata.readthedocs.io/en/stable/capture-hardware/dpdk.html
3. **Intel X520 Datasheet**: Search for "Intel 82599 10GbE Controller"
4. **scikit-learn Metrics**: https://scikit-learn.org/stable/modules/model_evaluation.html

---

## 🎓 Key Concepts

### What is being tested?
- **Pipeline latency**: Feature extraction + ML inference time
- **Throughput**: Packets processed per second
- **Accuracy**: Prediction correctness vs ground truth
- **Confidence calibration**: Do high-confidence predictions match high accuracy?
- **Model agreement**: Do ensemble models agree? (high = reliable voting)

### Why use ensemble voting?
- **Robustness**: If one model fails, others provide predictions
- **Higher accuracy**: Majority voting > individual models
- **Confidence scores**: Models that agree get higher weight
- **Attack detection**: Different models catch different attack types

### CSV logging workflow
1. Feature Engine extracts CICIDS65 features from packets
2. ML Consumer receives feature vectors
3. **Each model (RF, DT, LGB, KNN, LR) makes a prediction**
4. **Majority voting determines final prediction**
5. **All predictions + confidence logged to CSV**
6. Metrics calculator compares vs ground truth

---

## 📈 Performance Tuning

After initial testing, optimize:

1. **Feature extraction**: Check if bottleneck
   ```bash
   tail -f logs/feature_engine.log | grep "packets processed"
   ```

2. **Model inference**: Check ML consumer latency
   ```bash
   # Add timing to realtime_ensemble_consumer_with_csv.py
   ```

3. **DPDK settings**: Adjust in pipeline.conf
   ```ini
   DPDK_COREMASK=0x0F         # More cores = higher throughput
   DPDK_MEMPOOL_SIZE=262144   # Larger = handle bursts
   DPDK_BURST_SIZE=32         # Larger = lower latency
   ```

4. **Kafka tuning**
   ```bash
   # Adjust batch size, compression, etc
   ```

---

## 🎯 Success Metrics

Aim for:
- ✅ **Accuracy**: >95% on CICIDS datasets
- ✅ **High confidence**: >95% of predictions with >80% agreement
- ✅ **Throughput**: >1 Gbps (10 Gbps line rate possible)
- ✅ **Latency**: <100 ms end-to-end
- ✅ **Per-class accuracy**: >90% for most attack types

---

## 🚀 Next Steps

1. **Install X520** (when available tomorrow)
2. **Follow X520_DPDK_SETUP.md** to bind interface
3. **Test with small PCAP** (--max-packets 10000)
4. **Verify accuracy** is reasonable
5. **Run full dataset** for production validation
6. **Analyze results** - see which attacks have low accuracy
7. **Retrain models** if needed (with low-accuracy attack data)

---

**You're all set!** Everything needed for X520 testing is in place. Just connect the NIC tomorrow and follow the quick start steps. 🎉

Questions? Check the detailed guides:
- X520_DPDK_SETUP.md
- PCAP_REPLAY_ACCURACY_GUIDE.md
