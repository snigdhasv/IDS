# DPDK Testing Quick Reference

## 🚀 Quick Start (5 minutes)

```bash
# 1️⃣  Start the pipeline
sudo bash run_realtime_engine_dpdk.sh start

# 2️⃣  In another terminal: Replay PCAP traffic
python3 dpdk_pcap_replay.py \
  dpdk_suricata_ml_pipeline/pcap_samples/mixed_traffic_sample.pcap \
  --csv results/ground_truth.csv

# 3️⃣  Watch predictions in real-time
tail -f logs/ml_consumer.log

# 4️⃣  Calculate accuracy metrics
python3 calculate_accuracy_metrics.py \
  --packets results/ground_truth.csv \
  --predictions logs/ml_consumer.log \
  --output results/accuracy.json
```

## 📊 Key Commands

### Pipeline Management
```bash
sudo bash run_realtime_engine_dpdk.sh start      # Start all services
sudo bash run_realtime_engine_dpdk.sh stop       # Stop all services
sudo bash run_realtime_engine_dpdk.sh status     # Check status
sudo bash run_realtime_engine_dpdk.sh restart    # Restart
```

### DPDK Management
```bash
# Check DPDK binding
sudo python3 /usr/local/bin/dpdk-devbind.py --status

# Bind X520 to DPDK
sudo python3 /usr/local/bin/dpdk-devbind.py --bind=uio_pci_generic 0000:01:00.0

# Rebind to kernel
sudo python3 /usr/local/bin/dpdk-devbind.py --bind=ixgbe 0000:01:00.0
```

### PCAP Replay
```bash
# Basic replay
python3 dpdk_pcap_replay.py traffic.pcap

# With rate limiting (100k pkt/s)
python3 dpdk_pcap_replay.py traffic.pcap --rate 100000

# Replay multiple times
python3 dpdk_pcap_replay.py traffic.pcap --repeat 5

# Export ground truth to CSV
python3 dpdk_pcap_replay.py traffic.pcap --csv output.csv

# With DPDK mode (if available)
python3 dpdk_pcap_replay.py traffic.pcap --dpdk
```

### Monitoring
```bash
# Watch Feature Engine logs
tail -f logs/feature_engine.log

# Watch ML predictions
tail -f logs/ml_consumer.log

# Watch Suricata
tail -f /var/log/suricata/suricata.log

# Follow all logs with color
tail -f logs/*.log

# Check Kafka topics
kafka-topics.sh --list --bootstrap-server localhost:9092
kafka-console-consumer.sh --topic ml-predictions --bootstrap-server localhost:9092
```

### Accuracy Metrics
```bash
# Full metrics calculation
python3 calculate_accuracy_metrics.py \
  --packets results/*_packets.csv \
  --predictions logs/ml_consumer.log \
  --output results/accuracy.json \
  --detailed results/predictions.csv

# View JSON results
cat results/accuracy.json | jq .

# View accuracy percentage
cat results/accuracy.json | jq '.overall.accuracy * 100'
```

## 📁 File Structure

```
IDS/
├── dpdk_pcap_replay.py                    # PCAP replay tool
├── calculate_accuracy_metrics.py          # Accuracy calculator
├── test_dpdk_replay.sh                    # End-to-end test script
├── DPDK_PCAP_REPLAY_GUIDE.md             # Full documentation
├── dpdk_suricata_ml_pipeline/
│   ├── pcap_samples/
│   │   ├── normal_traffic.pcap
│   │   ├── dos_traffic_sample.pcap
│   │   └── mixed_traffic_sample.pcap
│   ├── scripts/
│   │   ├── 01_bind_interface.sh
│   │   ├── 02_setup_kafka.sh
│   │   ├── 03_start_suricata_dpdk.sh
│   │   └── 04_configure_dpdk_input.sh
│   ├── src/
│   │   ├── realtime_feature_engine.py
│   │   └── realtime_ensemble_consumer.py
│   └── config/
│       └── pipeline.conf
├── logs/
│   ├── feature_engine.log
│   ├── ml_consumer.log
│   └── ...
└── test_results/
    ├── accuracy_report.json
    ├── predictions_detailed.csv
    └── ...
```

## 🎯 Common Workflows

### Test 1: Single PCAP File
```bash
# Start pipeline
sudo bash run_realtime_engine_dpdk.sh start

# Replay once
python3 dpdk_pcap_replay.py traffic.pcap --csv results/gt.csv

# Calculate accuracy
python3 calculate_accuracy_metrics.py \
  --packets results/gt.csv \
  --predictions logs/ml_consumer.log \
  --output results/acc.json

# View results
cat results/acc.json | jq .overall.accuracy
```

### Test 2: Multiple PCAP Files
```bash
# Start once
sudo bash run_realtime_engine_dpdk.sh start

# Replay multiple
for pcap in dpdk_suricata_ml_pipeline/pcap_samples/*.pcap; do
  echo "Replaying $pcap..."
  python3 dpdk_pcap_replay.py "$pcap" --csv "results/$(basename $pcap .pcap).csv"
  sleep 5
done

# Calculate combined accuracy
python3 calculate_accuracy_metrics.py \
  --packets results/*.csv \
  --predictions logs/ml_consumer.log \
  --output results/combined_accuracy.json
```

### Test 3: High-Volume Stress Test
```bash
# Start pipeline
sudo bash run_realtime_engine_dpdk.sh start

# Replay at high rate with repeats
python3 dpdk_pcap_replay.py traffic.pcap \
  --repeat 100 \
  --rate 1000000 \
  --csv results/stress_test.csv

# Monitor CPU/memory
watch -n 1 'top -b -n 1 | head -15'

# Calculate accuracy
python3 calculate_accuracy_metrics.py \
  --packets results/stress_test.csv \
  --predictions logs/ml_consumer.log
```

## 📈 Expected Results

| Metric | Target | Notes |
|--------|--------|-------|
| **Accuracy** | >95% | Overall correctness |
| **Precision** | >95% | False alarm rate |
| **Recall** | >95% | Detection rate |
| **F1-Score** | >95% | Balance metric |
| **Latency** | <100ms | End-to-end prediction time |

## ❌ Troubleshooting

### Pipeline won't start
```bash
# Check DPDK binding
sudo dpdk-devbind.py --status

# Check Kafka
netstat -tuln | grep 9092

# Check services
ps aux | grep suricata
ps aux | grep realtime_feature
ps aux | grep realtime_ensemble
```

### Predictions not appearing
```bash
# Check Feature Engine
tail -f logs/feature_engine.log

# Check ML Consumer
tail -f logs/ml_consumer.log

# Verify Kafka topics
kafka-topics.sh --describe --bootstrap-server localhost:9092
```

### Low accuracy results
1. Check ground truth generation (inspect CSV files)
2. Verify model freshness (retrain if needed)
3. Check feature alignment between replay and training
4. Review false positives/negatives in detailed CSV

### High memory usage
```bash
# Check DPDK hugepages
grep Hugepagesize /proc/meminfo

# Reduce batch size in config
# Or reduce number of parallel workers
```

## 🔧 Configuration Files

### `dpdk_suricata_ml_pipeline/config/pipeline.conf`
- `INTERFACE_PCI_ADDRESS`: X520 PCI address (0000:01:00.0)
- `NETWORK_INTERFACE`: Interface name (enp1s0)
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka broker address
- `FEATURE_COUNT`: Number of features (65 for CICIDS)

### `logs/` Directory
- `feature_engine.log`: CICIDS65 feature extraction
- `ml_consumer.log`: Ensemble predictions
- `metrics_dashboard.log`: Metrics dashboard (optional)

## 📞 Support Commands

```bash
# Show X520 details
lspci | grep -i "82599\|x520"

# Show DPDK status
sudo dpdk-devbind.py --status

# Show Kafka topics
kafka-topics.sh --list --bootstrap-server localhost:9092

# Show pipeline processes
ps aux | grep -E "suricata|realtime_"

# Show Kafka messages
kafka-console-consumer.sh --topic ml-predictions \
  --bootstrap-server localhost:9092 --from-beginning | head -20

# Test connectivity
curl http://localhost:5000  # Metrics dashboard

# Check disk space for logs
du -sh logs/ test_results/
```

## 🎓 Learning Resources

- **DPDK PCAP Replay Guide**: `DPDK_PCAP_REPLAY_GUIDE.md`
- **X520 Setup**: `X520_DPDK_SETUP.md`
- **Pipeline Architecture**: `DPDK_MODE_ARCHITECTURE.md`
- **Feature Engine Docs**: `DPDK_REALTIME_ENGINE_IMPLEMENTATION_SUMMARY.md`

## ✅ Verification Checklist

Before starting tests:
- [ ] X520 is bound to DPDK: `sudo dpdk-devbind.py --status`
- [ ] Kafka is running: `netstat -tuln | grep 9092`
- [ ] PCAP files exist: `ls dpdk_suricata_ml_pipeline/pcap_samples/`
- [ ] Python venv active: `source venv/bin/activate`
- [ ] Suricata has DPDK: `suricata --build-info | grep DPDK`
- [ ] Feature Engine exists: `ls dpdk_suricata_ml_pipeline/src/realtime_feature_engine.py`
