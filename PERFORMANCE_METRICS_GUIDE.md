# 📊 ML Performance Metrics Guide

## Overview

The IDS pipeline now includes comprehensive performance monitoring that tracks:
- **Throughput Metrics**: Events/sec, predictions/sec
- **Latency Metrics**: Inference time, feature extraction time, total processing time
- **Accuracy Metrics**: Precision, recall, F1 score, confusion matrix
- **Prediction Distribution**: Attack types detected
- **Confidence Scores**: Model confidence statistics

---

## 🎯 What Metrics Are Tracked

### **1. Throughput Metrics**
| Metric | Description |
|--------|-------------|
| `events_processed` | Total events consumed from Kafka |
| `flows_processed` | Network flows analyzed |
| `ml_predictions` | ML inference operations performed |
| `events_per_sec` | Real-time processing rate |
| `predictions_per_sec` | ML inference rate |

### **2. Latency Metrics** (in milliseconds)
| Metric | Description |
|--------|-------------|
| `inference_time` | Time for ML model prediction (mean, median, P95, P99) |
| `feature_extraction_time` | Time to extract CICIDS2017 features |
| `total_processing_time` | End-to-end flow processing time |

### **3. Accuracy Metrics**
| Metric | Description | Formula |
|--------|-------------|---------|
| `accuracy` | Overall correctness | (TP + TN) / Total |
| `precision` | Positive prediction accuracy | TP / (TP + FP) |
| `recall` | True positive rate | TP / (TP + FN) |
| `f1_score` | Harmonic mean of precision & recall | 2 × (P × R) / (P + R) |
| `false_positive_rate` | False alarm rate | FP / (FP + TN) |

**Confusion Matrix:**
- **True Positive (TP)**: Both ML and Suricata detect threat
- **True Negative (TN)**: Both agree traffic is benign
- **False Positive (FP)**: ML detects threat, Suricata doesn't
- **False Negative (FN)**: Suricata detects threat, ML doesn't

### **4. Prediction Distribution**
- Count and percentage of each attack type predicted
- Visual bar charts in terminal output

### **5. Confidence Scores**
- Mean, median, min, max, standard deviation
- Distribution by confidence range (High ≥90%, Med 70-90%, Low <70%)

---

## 🚀 How to Use

### **Method 1: Real-Time Console Output**

Metrics are automatically displayed every **30 seconds** when the ML consumer is running:

```bash
cd /home/sujay/Programming/IDS

# Start the pipeline
sudo ./run_afpacket_mode.sh start

# Watch the ML consumer terminal - metrics print every 30 seconds
```

**Example Output:**
```
╔════════════════════════════════════════════════════════════════╗
║         ML IDS Performance Metrics (120s runtime)            ║
╚════════════════════════════════════════════════════════════════╝

📊 THROUGHPUT METRICS
  Events processed:      1,245
  Flows processed:       1,100
  ML predictions:        1,100
  Events/sec:            10.38
  Predictions/sec:       9.17

⚡ LATENCY METRICS
  ML Inference Latency:
    Average:   2.450 ms
    Median:    2.320 ms
    P95:       4.100 ms
    P99:       5.230 ms
  Total Processing Latency:
    Average:   3.120 ms
    P95:       5.890 ms

✓ ACCURACY METRICS (ML vs Suricata Agreement)
  True Positives (TP):   45   (ML & Suricata both detect)
  True Negatives (TN):   980  (Both agree benign)
  False Positives (FP):  12   (ML detects, Suricata doesn't)
  False Negatives (FN):  5    (Suricata detects, ML doesn't)
  
  Accuracy:              98.37%
  Precision:             78.95%
  Recall (TPR):          90.00%
  F1 Score:              84.11%

🎯 PREDICTION DISTRIBUTION
  BENIGN               980 (89.1%) ████████████████████████████████████████████
  DDoS                  45 ( 4.1%) ██
  PortScan              30 ( 2.7%) █
  BotNet                25 ( 2.3%) █

📈 CONFIDENCE DISTRIBUTION
  Average Confidence:    87.35%
  High confidence (≥90%): 850
  Med confidence (70-90%): 200
  Low confidence (<70%):  50
```

### **Method 2: Saved Metrics Files**

Metrics are automatically saved to JSON files when the consumer stops:

```bash
# Metrics are saved here:
/home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/performance_metrics_YYYYMMDD_HHMMSS.json

# View latest metrics file
ls -lt /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/performance_metrics_*.json | head -1

# Pretty-print JSON
cat /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/performance_metrics_*.json | jq .
```

**JSON Structure:**
```json
{
  "timestamp": "2025-10-23T14:30:45.123456",
  "runtime_seconds": 120.5,
  "model_name": "random_forest_model_2017.joblib",
  "model_type": "Random Forest",
  "throughput": {
    "events_processed": 1245,
    "flows_processed": 1100,
    "events_per_sec": 10.33,
    "predictions_per_sec": 9.13
  },
  "latency_ms": {
    "inference": {
      "mean": 2.45,
      "median": 2.32,
      "p95": 4.10,
      "p99": 5.23
    },
    "total_processing": {
      "mean": 3.12,
      "p95": 5.89
    }
  },
  "accuracy": {
    "true_positives": 45,
    "true_negatives": 980,
    "false_positives": 12,
    "false_negatives": 5,
    "accuracy_percentage": 98.37,
    "precision_percentage": 78.95,
    "recall_percentage": 90.00,
    "f1_score": 84.11
  },
  "predictions_by_class": {
    "BENIGN": 980,
    "DDoS": 45,
    "PortScan": 30,
    "BotNet": 25
  },
  "confidence_stats": {
    "mean": 0.8735,
    "median": 0.9120,
    "std": 0.1234
  }
}
```

### **Method 3: Real-Time Performance Monitor Script**

Use the dedicated monitoring tool for live dashboard:

```bash
cd /home/sujay/Programming/IDS/tests

# Start real-time monitoring (refreshes every 5 seconds)
python3 monitor_ml_performance.py

# Custom refresh interval (10 seconds)
python3 monitor_ml_performance.py --interval 10

# Generate summary report from all metrics files
python3 monitor_ml_performance.py --report
```

**Monitor Features:**
- ✅ Live updating dashboard (clears screen on refresh)
- ✅ Real-time throughput calculation
- ✅ Color-coded output
- ✅ Visual bar charts
- ✅ Historical trend tracking
- ✅ Automatic latest metrics detection

---

## 📈 Interpreting the Metrics

### **Good Performance Indicators:**

#### Throughput
- ✅ **100+ predictions/sec**: Excellent for most networks
- ✅ **50-100 predictions/sec**: Good for medium traffic
- ⚠️ **<10 predictions/sec**: May indicate low traffic or performance issues

#### Latency
- ✅ **<5ms inference**: Excellent (real-time capable)
- ✅ **5-10ms inference**: Good
- ⚠️ **10-50ms inference**: Acceptable for non-critical
- ❌ **>50ms inference**: Performance issue

#### Accuracy
- ✅ **Accuracy >95%**: Excellent agreement with Suricata
- ✅ **Precision >90%**: Low false alarm rate
- ✅ **Recall >90%**: Catching most threats
- ✅ **F1 Score >85%**: Balanced performance

#### Confidence
- ✅ **Mean confidence >80%**: Model is confident
- ⚠️ **Mean confidence 60-80%**: Some uncertainty
- ❌ **Mean confidence <60%**: May need model retraining

### **Red Flags:**

| Issue | Symptom | Possible Cause |
|-------|---------|----------------|
| Low throughput | <10 predictions/sec | CPU bottleneck, slow model, no traffic |
| High latency | >50ms inference | Large model, CPU overload, memory swapping |
| Low accuracy | <80% | Model mismatch, feature extraction issues |
| High false positives | Precision <70% | Model too sensitive, needs tuning |
| High false negatives | Recall <70% | Model too conservative, missing threats |
| Low confidence | Mean <60% | Model uncertain, needs retraining |

---

## 🔧 Adjusting Performance

### **Improve Throughput:**

```bash
# Edit config
nano /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf

# Increase batch size
ML_BATCH_SIZE="500"  # was 100

# Use faster model
ML_MODEL_PATH="/home/sujay/Programming/IDS/ML Models/lgb_model_2018.joblib"

# Restart
sudo ./run_afpacket_mode.sh stop
sudo ./run_afpacket_mode.sh start
```

### **Improve Accuracy:**

```bash
# Use more accurate model (slower)
ML_MODEL_PATH="/home/sujay/Programming/IDS/ML Models/random_forest_model_2017.joblib"

# Adjust confidence threshold (higher = fewer false positives)
ML_CONFIDENCE_THRESHOLD="0.8"  # was 0.7

# Or lower threshold (catch more threats, more false positives)
ML_CONFIDENCE_THRESHOLD="0.6"
```

### **Reduce Latency:**

```bash
# Use faster model
ML_MODEL_PATH="/home/sujay/Programming/IDS/ML Models/decision_tree_model_2017.joblib"

# Or LightGBM (fast + accurate)
ML_MODEL_PATH="/home/sujay/Programming/IDS/ML Models/lgb_model_2018.joblib"
```

---

## 📊 Analyzing Saved Metrics

### **Compare Multiple Runs:**

```bash
cd /home/sujay/Programming/IDS/tests

# Generate summary report
python3 monitor_ml_performance.py --report
```

**Output:**
```
╔════════════════════════════════════════════════════════════════╗
║           ML IDS Performance Summary Report                    ║
╚════════════════════════════════════════════════════════════════╝

📊 AGGREGATE STATISTICS
  Total sessions: 5
  Total events processed: 12,450
  Total predictions: 11,200

⚡ AVERAGE LATENCY
  Inference: 2.456 ms
  Total:     3.234 ms

✓ ACCURACY TRENDS
  Average accuracy: 97.34%
  Best accuracy:    98.50%
  Worst accuracy:   95.20%

📝 SESSION DETAILS
  Session 1:
    Timestamp: 2025-10-23T14:30:45
    Model: random_forest_model_2017.joblib
    Runtime: 120s
    Events: 1,245
    Accuracy: 98.37%
    Avg latency: 2.450ms
```

### **Export to CSV for Analysis:**

```python
#!/usr/bin/env python3
"""Export metrics to CSV"""
import json
import glob
import csv
from pathlib import Path

metrics_dir = Path('/home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml')
metrics_files = glob.glob(str(metrics_dir / 'performance_metrics_*.json'))

with open('metrics_summary.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Timestamp', 'Model', 'Runtime', 'Predictions', 
                     'Accuracy', 'Precision', 'Recall', 'F1', 
                     'Inference_ms', 'Total_ms'])
    
    for mfile in metrics_files:
        with open(mfile) as jf:
            m = json.load(jf)
            writer.writerow([
                m['timestamp'],
                m['model_name'],
                m['runtime_seconds'],
                m['throughput']['ml_predictions'],
                m['accuracy'].get('accuracy_percentage', 0),
                m['accuracy'].get('precision_percentage', 0),
                m['accuracy'].get('recall_percentage', 0),
                m['accuracy'].get('f1_score', 0),
                m['latency_ms']['inference']['mean'],
                m['latency_ms']['total_processing']['mean']
            ])

print("✓ Exported to metrics_summary.csv")
```

---

## 🎮 Example Workflows

### **Workflow 1: Test Different Models**

```bash
# Test Random Forest
nano /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf
# Set: ML_MODEL_PATH=".../random_forest_model_2017.joblib"
sudo ./run_afpacket_mode.sh start
# ... run for 5 minutes ...
sudo ./run_afpacket_mode.sh stop
# Metrics saved automatically

# Test LightGBM
nano /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf
# Set: ML_MODEL_PATH=".../lgb_model_2018.joblib"
sudo ./run_afpacket_mode.sh start
# ... run for 5 minutes ...
sudo ./run_afpacket_mode.sh stop

# Compare results
cd tests
python3 monitor_ml_performance.py --report
```

### **Workflow 2: Performance Benchmarking**

```bash
# Terminal 1: Start pipeline
cd /home/sujay/Programming/IDS
sudo ./run_afpacket_mode.sh start

# Terminal 2: Generate traffic
cd tests
python3 test_benign_traffic.py  # Run for 2 minutes

# Terminal 3: Monitor performance
cd tests
python3 monitor_ml_performance.py

# After test, check final metrics
cd /home/sujay/Programming/IDS
sudo ./run_afpacket_mode.sh stop
# Metrics saved to logs/ml/performance_metrics_*.json
```

### **Workflow 3: Production Monitoring**

```bash
# Setup cron job to check performance every hour
crontab -e

# Add:
0 * * * * cd /home/sujay/Programming/IDS/tests && python3 monitor_ml_performance.py --report >> /tmp/ml_performance_hourly.log
```

---

## 🐛 Troubleshooting

### **Issue: No metrics displayed**

```bash
# Check if ML consumer is running
ps aux | grep ml_kafka_consumer

# Check logs
tail -f /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log

# Verify metrics directory
ls -la /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/
```

### **Issue: Metrics show 0 events**

```bash
# No traffic being captured
# Check if Kafka has messages:
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
    --topic suricata-alerts --from-beginning --max-messages 10

# Generate test traffic
cd /home/sujay/Programming/IDS/tests
python3 test_benign_traffic.py
```

### **Issue: Low accuracy/high false positives**

```bash
# Check model configuration
grep "ML_MODEL_PATH" /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf

# Try adjusting confidence threshold
nano /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf
# Set: ML_CONFIDENCE_THRESHOLD="0.8"  # Higher = fewer false positives

# Or switch to different model
# Set: ML_MODEL_PATH=".../lgb_model_2018.joblib"
```

---

## 📚 Related Files

- **ML Consumer:** `dpdk_suricata_ml_pipeline/src/ml_kafka_consumer.py` (modified)
- **Monitor Script:** `tests/monitor_ml_performance.py` (new)
- **Metrics Files:** `dpdk_suricata_ml_pipeline/logs/ml/performance_metrics_*.json`
- **Configuration:** `dpdk_suricata_ml_pipeline/config/pipeline.conf`
- **Model Guide:** `MODEL_CONFIGURATION_GUIDE.md`

---

## 🎯 Quick Reference

```bash
# Start pipeline with metrics
sudo ./run_afpacket_mode.sh start

# Real-time monitoring
cd tests && python3 monitor_ml_performance.py

# Generate report
cd tests && python3 monitor_ml_performance.py --report

# View latest metrics
cat dpdk_suricata_ml_pipeline/logs/ml/performance_metrics_*.json | jq .

# Check ML consumer logs
tail -f dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log
```

---

**✅ Your pipeline now has enterprise-grade performance monitoring!**

All metrics are tracked automatically, displayed in real-time, and saved for later analysis. Use the performance monitor script for a beautiful live dashboard! 🚀
