# PCAP Replay & Accuracy Testing Guide

## Overview

This guide walks you through testing your DPDK pipeline accuracy by replaying known datasets (CICIDS2017, CICIDS2018, etc.) and calculating comprehensive accuracy metrics.

**What you'll do:**
1. ✅ Bind X520 to DPDK (one-time setup)
2. 🚀 Start the pipeline with CSV logging enabled
3. 📥 Replay PCAP files through the pipeline
4. 📊 Calculate accuracy metrics from predictions
5. 📈 Analyze per-attack-type performance

---

## Step 1: X520 Setup (One-time)

See `X520_DPDK_SETUP.md` for complete instructions.

Quick validation:
```bash
# Check X520 is bound to DPDK
sudo dpdk-devbind.py --status | grep DPDK

# Expected output:
# 0000:02:00.0 'Intel 82599ES 10-Gigabit' drv=igb_uio unused=
# 0000:02:00.1 'Intel 82599ES 10-Gigabit' drv=igb_uio unused=
```

---

## Step 2: Start Pipeline with CSV Logging

**Option A: With CSV Output (for accuracy testing)**

```bash
# Start the DPDK pipeline
sudo bash /home/ifscr/SE_02_2025/IDS/run_realtime_engine_dpdk.sh start

# In another terminal, start the ML consumer with CSV logging
cd /home/ifscr/SE_02_2025/IDS
source venv/bin/activate
python3 dpdk_suricata_ml_pipeline/src/realtime_ensemble_consumer_with_csv.py \
    --csv-output predictions.csv
```

**Option B: Standard Baseline (without ground truth)**

```bash
# Just run the normal consumer
cd /home/ifscr/SE_02_2025/IDS/dpdk_suricata_ml_pipeline/src
python3 -u realtime_ensemble_consumer.py
```

---

## Step 3: Prepare Ground Truth Labels

You need a CSV file mapping packets/flows to their true labels.

### Format 1: Flow-based (recommended)

```csv
src_ip,dst_ip,src_port,dst_port,label
192.168.1.100,10.0.0.50,12345,80,BENIGN
192.168.1.101,10.0.0.51,12346,443,SSH-Patator
192.168.1.102,10.0.0.52,12347,22,Infiltration
...
```

### Format 2: Simple flow ID

```csv
flow_id,label
flow_001,BENIGN
flow_002,DDoS
flow_003,PortScan
...
```

### Format 3: Network tuple

```csv
src_ip,dst_ip,protocol,label
192.168.1.100,10.0.0.50,TCP,BENIGN
192.168.1.101,10.0.0.51,TCP,SSH-Patator
...
```

**Converting CICIDS CSV to Ground Truth:**

If you have the original CICIDS CSV (with Label column):
```bash
# Extract unique flows and their labels
python3 << 'EOF'
import pandas as pd

# Read original CICIDS dataset
df = pd.read_csv('CICIDS2017.csv')

# Create ground truth CSV
gt = df[['Src IP', 'Dst IP', 'Src Port', 'Dst Port', ' Label']].drop_duplicates()
gt.columns = ['src_ip', 'dst_ip', 'src_port', 'dst_port', 'label']

# Clean label names
gt['label'] = gt['label'].str.strip().str.upper().str.replace('-', '_')

gt.to_csv('cicids2017_groundtruth.csv', index=False)
print(f"Created ground truth for {len(gt)} flows")
EOF
```

---

## Step 4: Replay PCAP File

With Kafka running and ML consumer listening:

```bash
cd /home/ifscr/SE_02_2025/IDS
source venv/bin/activate

# Replay PCAP with ground truth labels
python3 dpdk_suricata_ml_pipeline/src/replay_pcap_for_testing.py \
    --pcap-file /path/to/dataset.pcap \
    --ground-truth cicids2017_groundtruth.csv \
    --max-packets 100000

# If you want to replay at real-time speed (slower):
python3 dpdk_suricata_ml_pipeline/src/replay_pcap_for_testing.py \
    --pcap-file /path/to/dataset.pcap \
    --ground-truth cicids2017_groundtruth.csv \
    --real-time

# Or at 2x speed (faster):
python3 dpdk_suricata_ml_pipeline/src/replay_pcap_for_testing.py \
    --pcap-file /path/to/dataset.pcap \
    --ground-truth cicids2017_groundtruth.csv \
    --speed 2.0
```

**What happens:**
1. Script reads PCAP file
2. Parses each packet (IP, TCP/UDP headers)
3. Extracts flow tuple (src_ip, dst_ip, src_port, dst_port, protocol)
4. Looks up ground truth label
5. Sends packet data to Kafka
6. Feature Engine calculates CICIDS65 features
7. ML Consumer receives features, runs ensemble prediction, writes to CSV

---

## Step 5: Monitor Progress

In separate terminals:

```bash
# Terminal 1: Feature engine logs
tail -f /home/ifscr/SE_02_2025/IDS/logs/feature_engine.log

# Terminal 2: ML consumer logs (with predictions)
tail -f /home/ifscr/SE_02_2025/IDS/logs/ml_consumer.log

# Terminal 3: CSV being written
tail -f predictions.csv | tail -20
```

---

## Step 6: Calculate Accuracy Metrics

Once replay finishes:

```bash
cd /home/ifscr/SE_02_2025/IDS
source venv/bin/activate

# Basic metrics (printed to console)
python3 dpdk_suricata_ml_pipeline/src/calculate_accuracy_metrics.py \
    --predictions predictions.csv

# With JSON report and confusion matrix
python3 dpdk_suricata_ml_pipeline/src/calculate_accuracy_metrics.py \
    --predictions predictions.csv \
    --output metrics_report.json \
    --confusion-matrix confusion_matrix.png
```

---

## Expected Output

### Console Output:
```
======================================================================
ACCURACY METRICS REPORT
======================================================================

📊 OVERALL METRICS:
   Accuracy:     0.9842 (98.42%)
   Precision:    0.9741
   Recall:       0.9823
   F1 Score:     0.9782

📈 PER-CLASS METRICS:

   BENIGN:
      Precision: 0.9923
      Recall:    0.9967
      F1:        0.9945
      Support:   78342

   SSH_PATATOR:
      Precision: 0.9234
      Recall:    0.8567
      F1:        0.8888
      Support:   2345

   DDOS:
      Precision: 0.9156
      Recall:    0.9234
      F1:        0.9195
      Support:   5432

🔢 CONFUSION MATRIX:
    ''         BENIGN    SSH_PATATOR         DDOS
      BENIGN        78120           142          80
  SSH_PATATOR         234          2011         100
        DDOS          123            89        5220

🎯 CONFIDENCE METRICS:
   Mean:      0.9823
   Median:    0.9951
   Stdev:     0.0456
   Min/Max:   0.5123 / 1.0000

   AGREEMENT DISTRIBUTION:
      high (>=0.80)           85436 ( 98.5%)
      medium (0.60-0.80)       1023 (  1.2%)
      low (<0.60)               112 (  0.3%)

======================================================================
```

### JSON Report (metrics_report.json):
```json
{
  "timestamp": "1699526400",
  "total_predictions": 86571,
  "total_with_ground_truth": 86571,
  "basic_metrics": {
    "accuracy": 0.9842,
    "precision": 0.9741,
    "recall": 0.9823,
    "f1": 0.9782,
    "per_class": {
      "BENIGN": {
        "precision": 0.9923,
        "recall": 0.9967,
        "f1": 0.9945,
        "support": 78342
      },
      ...
    },
    "confusion_matrix": {
      "labels": ["BENIGN", "SSH_PATATOR", "DDOS"],
      "matrix": [[78120, 142, 80], ...]
    }
  },
  "confidence_metrics": {
    "confidence": {
      "mean": 0.9823,
      "median": 0.9951,
      "stdev": 0.0456,
      "min": 0.5123,
      "max": 1.0
    },
    "agreement": {
      "mean": 0.9847,
      "median": 1.0,
      "stdev": 0.0321,
      "min": 0.4,
      "max": 1.0
    }
  }
}
```

---

## CSV Prediction Format

The `predictions.csv` file contains one row per prediction with:

| Column | Description |
|--------|-------------|
| timestamp | ISO 8601 timestamp of prediction |
| flow_id | Unique flow identifier |
| ground_truth | True label from PCAP |
| ensemble_prediction | Final prediction (BENIGN/Attack) |
| ensemble_confidence | Confidence score (0-1) |
| agreement_ratio | Fraction of models agreeing (0-1) |
| model_rf_pred | Random Forest prediction |
| model_rf_conf | Random Forest confidence |
| model_dt_pred | Decision Tree prediction |
| model_dt_conf | Decision Tree confidence |
| model_lgb_pred | LightGBM prediction |
| model_lgb_conf | LightGBM confidence |
| model_knn_pred | KNN prediction |
| model_knn_conf | KNN confidence |
| model_lr_pred | Logistic Regression prediction |
| model_lr_conf | Logistic Regression confidence |
| correct | True if prediction matches ground truth |

---

## Troubleshooting

### Issue: "No valid predictions with ground truth found"

**Cause:** Ground truth CSV labels don't match flow information from PCAP.

**Solution:**
1. Check if labels are being populated in predictions.csv
2. Verify ground truth CSV format
3. Check if flow tuple extraction matches (src_ip, dst_ip, src_port, dst_port)

```bash
# Debug: Check what the replayer is sending
python3 dpdk_suricata_ml_pipeline/src/replay_pcap_for_testing.py \
    --pcap-file dataset.pcap \
    --ground-truth labels.csv \
    --max-packets 100
# Look at console output for "With GT: X" count
```

### Issue: Low accuracy (<80%)

**Possible causes:**
1. Feature mismatch between training and real-time
2. Ground truth labels are incorrect
3. PCAP contains different attack patterns than training data

**Debugging:**
```bash
# Check feature vector in realtime_ensemble_consumer_with_csv.py logs
tail -f /home/ifscr/SE_02_2025/IDS/logs/ml_consumer.log | grep -i error

# Compare with CSV predictions
head -50 predictions.csv | tail -20
```

### Issue: "Kafka connection refused"

Make sure Kafka is running:
```bash
# Check if Kafka is listening
netstat -tuln | grep 9092

# If not, start Kafka
sudo bash /home/ifscr/SE_02_2025/IDS/dpdk_suricata_ml_pipeline/scripts/02_setup_kafka.sh
```

---

## Performance Expectations

With X520 (10 Gbps):

| Dataset | Packets | Time (real-time) | Time (10x speed) |
|---------|---------|------------------|------------------|
| CICIDS 1 day | ~2M | 24 hours | 2.4 hours |
| CICIDS 1 week | ~14M | 7 days | 16.8 hours |
| Custom test | ~100k | 10 minutes | 1 minute |

**Tip:** Use `--max-packets 100000` for quick tests.

---

## Example Workflow (Quick Test)

```bash
# Terminal 1: Start pipeline
cd /home/ifscr/SE_02_2025/IDS
sudo bash run_realtime_engine_dpdk.sh start
sleep 5

# Terminal 2: Start ML consumer with CSV
source venv/bin/activate
python3 dpdk_suricata_ml_pipeline/src/realtime_ensemble_consumer_with_csv.py \
    --csv-output test_predictions.csv

# Terminal 3: Replay test PCAP (in background)
source venv/bin/activate
python3 dpdk_suricata_ml_pipeline/src/replay_pcap_for_testing.py \
    --pcap-file test_dataset.pcap \
    --ground-truth test_groundtruth.csv \
    --max-packets 50000 &

# Wait for replay to finish (watch terminal 3)

# Terminal 4: Calculate metrics
source venv/bin/activate
python3 dpdk_suricata_ml_pipeline/src/calculate_accuracy_metrics.py \
    --predictions test_predictions.csv \
    --output test_metrics.json \
    --confusion-matrix test_confusion.png

# View results
cat test_metrics.json | jq '.basic_metrics.accuracy'
```

---

## Next Steps

- [ ] Bind X520 to DPDK (see X520_DPDK_SETUP.md)
- [ ] Prepare ground truth labels for your PCAP
- [ ] Run quick test with --max-packets 10000
- [ ] Verify accuracy is >90%
- [ ] Full dataset replay for production validation
- [ ] Analyze per-attack-type accuracy
- [ ] Check model agreement ratios (should be >95% high confidence)

---

## Reference: CICIDS Labels

Standard attack types in CICIDS datasets:

```
BENIGN
SSH-Patator
FTP-Patator
DoS Hulk
DoS GoldenEye
DoS slowhttptest
DoS Slowloris
Heartbleed
Botnet
PortScan
DDoS
Infiltration
SQL Injection
XSS
```

Make sure your ground truth CSV uses these exact labels (or map them consistently).

---

**Questions or issues?** Check the logs:
```bash
tail -f logs/feature_engine.log
tail -f logs/ml_consumer.log
tail -f /var/log/suricata/suricata.log
```
