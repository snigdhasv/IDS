# DPDK PCAP Replay + IDS Accuracy Testing Guide

## Overview

This guide walks you through testing your IDS with DPDK-based PCAP replay, simulating real network traffic arriving at line rate (10 Gbps) through your X520 NIC.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DPDK PCAP Replay Pipeline                     │
└─────────────────────────────────────────────────────────────────┘

       PCAP Files
         ↓
    ┌─────────────┐
    │   Scapy     │  Reads packets from PCAP
    └─────────────┘
         ↓
    ┌─────────────────────────────────┐
    │ X520 NIC (Bound to DPDK)        │  PCI: 0000:01:00.0
    │ uio_pci_generic driver          │  10 Gbps Ethernet
    └─────────────────────────────────┘
         ↓
    ┌─────────────────────────────────┐
    │ Suricata (DPDK mode)            │  Capture + Signature Detection
    └─────────────────────────────────┘
         ↓
    ┌─────────────────────────────────┐
    │ Feature Engine (DPDK)           │  CICIDS65 Feature Extraction
    └─────────────────────────────────┘
         ↓
    ┌─────────────────────────────────┐
    │ ML Consumer (Ensemble)          │  Threat Classification
    └─────────────────────────────────┘
         ↓
    ┌─────────────────────────────────┐
    │ Accuracy Metrics                │  Compare Predictions vs Ground Truth
    └─────────────────────────────────┘
```

## Prerequisites

✅ **Completed Setup:**
- X520 NIC detected at PCI `0000:01:00.0`
- X520 bound to DPDK (`uio_pci_generic`)
- DPDK 23.11.0 installed
- Suricata 7.0.11 with DPDK support
- Kafka running on port 9092
- Python venv configured

## Step 1: Configure DPDK Input

Configure Suricata and Feature Engine to read from the DPDK-bound X520:

```bash
bash /home/ifscr/SE_02_2025/IDS/dpdk_suricata_ml_pipeline/scripts/04_configure_dpdk_input.sh
```

**What it does:**
- Verifies X520 binding
- Configures Suricata YAML for DPDK
- Sets up Feature Engine for DPDK input
- Creates required config files

## Step 2: Replay PCAP Traffic

### Option A: Manual Replay (Recommended for first test)

Start the pipeline first:

```bash
sudo bash /home/ifscr/SE_02_2025/IDS/run_realtime_engine_dpdk.sh start
```

In another terminal, replay PCAP:

```bash
python3 /home/ifscr/SE_02_2025/IDS/dpdk_pcap_replay.py \
  /home/ifscr/SE_02_2025/IDS/dpdk_suricata_ml_pipeline/pcap_samples/mixed_traffic_sample.pcap \
  --repeat 1 \
  --csv test_results/ground_truth.csv
```

Monitor predictions in real-time:

```bash
tail -f /home/ifscr/SE_02_2025/IDS/logs/ml_consumer.log
```

### Option B: Automated End-to-End Test

Run complete test with single command:

```bash
sudo bash /home/ifscr/SE_02_2025/IDS/test_dpdk_replay.sh start
```

This automatically:
1. Starts DPDK pipeline
2. Replays all PCAP samples
3. Captures ground truth
4. Collects predictions
5. Generates results in `test_results/`

## Step 3: Calculate Accuracy Metrics

After replay completes, calculate accuracy:

```bash
python3 /home/ifscr/SE_02_2025/IDS/calculate_accuracy_metrics.py \
  --packets test_results/*_packets.csv \
  --predictions test_results/ml_predictions.log \
  --output test_results/accuracy_report.json \
  --detailed test_results/predictions_detailed.csv
```

### Output Files

- `accuracy_report.json` - Full metrics in JSON format
- `predictions_detailed.csv` - Per-packet predictions vs ground truth
- Console output - Formatted accuracy report

### Metrics Calculated

| Metric | Description |
|--------|-------------|
| **Accuracy** | Percentage of correct predictions |
| **Precision** | % of predicted attacks that were correct |
| **Recall** | % of actual attacks detected |
| **F1-Score** | Harmonic mean of precision and recall |
| **Confusion Matrix** | TP, TN, FP, FN breakdown |
| **Confidence** | Model confidence statistics |

## Example Workflow

### Complete Test in 5 Steps

```bash
# 1. Configure DPDK input
bash dpdk_suricata_ml_pipeline/scripts/04_configure_dpdk_input.sh

# 2. Start pipeline
sudo bash run_realtime_engine_dpdk.sh start

# 3. Replay PCAP (wait ~30 seconds)
python3 dpdk_pcap_replay.py dpdk_suricata_ml_pipeline/pcap_samples/mixed_traffic_sample.pcap \
  --csv results/ground_truth.csv

# 4. Monitor predictions (in another terminal)
tail -f logs/ml_consumer.log

# 5. Calculate accuracy after replay finishes
python3 calculate_accuracy_metrics.py \
  --packets results/ground_truth.csv \
  --predictions logs/ml_consumer.log \
  --output results/accuracy.json
```

## Understanding the Results

### Sample Accuracy Report Output

```
======================================================================
IDS ACCURACY METRICS REPORT
======================================================================

DATASET SUMMARY
----------------------------------------------------------------------
Total samples analyzed:     10,000
Ground truth distribution:  {'BENIGN': 7000, 'ATTACK': 3000}
Prediction distribution:    {'BENIGN': 6950, 'ATTACK': 3050}

OVERALL PERFORMANCE
----------------------------------------------------------------------
Accuracy:                   97.45%
Correct predictions:        9,745
Incorrect predictions:      255

BENIGN CLASS METRICS
----------------------------------------------------------------------
Precision:                  99.29%
Recall:                     97.86%
F1-Score:                   98.56%

ATTACK CLASS METRICS
----------------------------------------------------------------------
Precision:                  94.46%
Recall:                     97.33%
F1-Score:                   95.88%

CONFUSION MATRIX
----------------------------------------------------------------------
                    Predicted BENIGN  Predicted ATTACK
Actual BENIGN                6850              150
Actual ATTACK                 80              2920
```

### Interpreting Metrics

- **High Accuracy (>95%)**: Good overall performance
- **High Recall (>95%)**: Detecting most real attacks (fewer false negatives)
- **High Precision (>95%)**: Few false alarms (fewer false positives)
- **Balanced F1-Score**: Good balance between precision and recall

## Available PCAP Samples

Located at: `dpdk_suricata_ml_pipeline/pcap_samples/`

| File | Description | Size |
|------|-------------|------|
| `normal_traffic.pcap` | Benign network traffic | ~5 MB |
| `dos_traffic_sample.pcap` | DoS attack traffic | ~3 MB |
| `mixed_traffic_sample.pcap` | Mixed benign + attack | ~8 MB |

### Using Custom PCAP Files

Add your own PCAP files and replay:

```bash
python3 dpdk_pcap_replay.py /path/to/your/traffic.pcap \
  --csv results/your_test.csv \
  --repeat 3 \
  --rate 50000
```

## DPDK Binding Management

### Check Current Binding

```bash
sudo python3 /usr/local/bin/dpdk-devbind.py --status
```

Expected output:
```
Network devices using DPDK-compatible driver
============================================
0000:01:00.0 '82599ES 10-Gigabit SFI/SFP+ Network Connection' drv=uio_pci_generic
```

### Rebind to Kernel (if needed)

```bash
sudo python3 /usr/local/bin/dpdk-devbind.py --bind=ixgbe 0000:01:00.0
```

Then restore network:
```bash
sudo ip link set enp1s0 up
sudo dhclient enp1s0
```

## Troubleshooting

### Issue: "No DPDK interfaces bound"
**Solution:** Bind X520 to DPDK:
```bash
sudo python3 /usr/local/bin/dpdk-devbind.py --bind=uio_pci_generic 0000:01:00.0
```

### Issue: "Permission denied" errors
**Solution:** Run with sudo:
```bash
sudo bash test_dpdk_replay.sh start
```

### Issue: Kafka not running
**Solution:** Start Kafka:
```bash
bash dpdk_suricata_ml_pipeline/scripts/02_setup_kafka.sh
```

### Issue: ML predictions not appearing
**Solution:** Check pipeline status:
```bash
sudo bash run_realtime_engine_dpdk.sh status
```

Verify Feature Engine is running:
```bash
tail -f logs/feature_engine.log
```

## Performance Expectations

| Metric | Value | Notes |
|--------|-------|-------|
| Replay Speed | 100k-1M pkt/s | Limited by host CPU, not X520 |
| Detection Latency | <100ms | End-to-end time for prediction |
| Throughput | Up to 10 Gbps | X520 hardware limit |
| CPU Usage | 20-30% | Per core, for packet processing |
| Memory | 2-4 GB | DPDK hugepages + ML models |

## Advanced: Custom Ground Truth Labels

To use custom attack labels instead of file-based inference:

1. Create a `labels.json`:
```json
{
  "normal_traffic.pcap": "BENIGN",
  "dos_traffic_sample.pcap": "ATTACK",
  "suspicious.pcap": "ATTACK"
}
```

2. Modify `calculate_accuracy_metrics.py` to load labels:
```python
with open('labels.json', 'r') as f:
    label_map = json.load(f)
    # Use label_map[pcap_filename] as ground truth
```

## Next Steps

1. **Run baseline tests** with provided PCAP samples
2. **Use your own PCAP files** for validation
3. **Fine-tune thresholds** based on accuracy metrics
4. **Monitor false positives** and adjust rules
5. **Deploy with confidence** when accuracy meets your SLA

## Files Created

| File | Purpose |
|------|---------|
| `dpdk_pcap_replay.py` | PCAP replay engine |
| `test_dpdk_replay.sh` | End-to-end test orchestrator |
| `calculate_accuracy_metrics.py` | Accuracy calculation |
| `dpdk_suricata_ml_pipeline/scripts/04_configure_dpdk_input.sh` | DPDK config |
| `test_results/` | Output directory |

## Support

For issues or questions:
- Check logs: `logs/feature_engine.log`, `logs/ml_consumer.log`
- Verify DPDK binding: `sudo dpdk-devbind.py --status`
- Check Kafka: `kafka-topics.sh --list --bootstrap-server localhost:9092`
- Run status check: `sudo bash run_realtime_engine_dpdk.sh status`
