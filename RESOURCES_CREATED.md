# Complete Resource List - DPDK PCAP Replay + IDS Testing

## 📦 New Files Created

### Core Tools (Executable Python Scripts)

1. **`dpdk_pcap_replay.py`** (13 KB)
   - **Purpose**: High-performance PCAP replay via X520 NIC
   - **Features**:
     - Reads PCAP files using Scapy
     - Injects packets through X520 (DPDK mode or kernel fallback)
     - Configurable rate limiting (pkt/s)
     - Multiple replay passes for stress testing
     - Ground truth CSV export with packet metadata
     - Progress tracking and statistics
   - **Usage**: `python3 dpdk_pcap_replay.py traffic.pcap [--options]`
   - **Options**:
     - `--rate`: Packets per second (0 = unlimited)
     - `--repeat`: Number of replay passes
     - `--csv`: Export ground truth to CSV file
     - `--dpdk`: Use DPDK mode if available
     - `--verbose`: Verbose output

2. **`calculate_accuracy_metrics.py`** (17 KB)
   - **Purpose**: Compare ML predictions against ground truth
   - **Features**:
     - Loads ground truth from PCAP CSV files
     - Loads predictions from ML Consumer logs
     - Matches predictions to ground truth
     - Calculates comprehensive metrics:
       * Accuracy, Precision, Recall, F1-Score
       * Confusion matrix
       * Confidence statistics
     - JSON export for metrics
     - CSV export for detailed per-packet analysis
   - **Usage**: `python3 calculate_accuracy_metrics.py [--options]`
   - **Options**:
     - `--packets`: Ground truth CSV file(s)
     - `--predictions`: ML predictions log file
     - `--output`: JSON output file for metrics
     - `--detailed`: CSV output for per-packet predictions

### Bash Scripts

3. **`test_dpdk_replay.sh`** (6.6 KB)
   - **Purpose**: End-to-end test orchestrator
   - **Workflow**:
     1. Starts complete DPDK pipeline
     2. Replays all available PCAP samples
     3. Captures ground truth packets
     4. Collects ML predictions
     5. Summarizes results
   - **Usage**: `sudo bash test_dpdk_replay.sh [start|stop|status]`
   - **Commands**:
     - `start`: Run complete test cycle
     - `stop`: Stop pipeline
     - `status`: Show service status

4. **`dpdk_suricata_ml_pipeline/scripts/04_configure_dpdk_input.sh`**
   - **Purpose**: Configure Suricata and Feature Engine for DPDK input
   - **Tasks**:
     - Verify X520 binding to DPDK
     - Configure Suricata YAML for DPDK mode
     - Create Feature Engine config
     - Show startup commands
   - **Usage**: `bash dpdk_suricata_ml_pipeline/scripts/04_configure_dpdk_input.sh`

### Documentation Files

5. **`DPDK_PCAP_REPLAY_GUIDE.md`**
   - **Content**: Comprehensive testing guide
   - **Sections**:
     - Architecture overview
     - Prerequisites & setup
     - Step-by-step PCAP replay
     - Accuracy metrics calculation
     - Example workflows
     - Troubleshooting guide
     - Performance expectations
     - Advanced customization

6. **`DPDK_TESTING_QUICK_REFERENCE.md`**
   - **Content**: Quick command reference
   - **Sections**:
     - 5-minute quick start
     - Common commands
     - File structure
     - Testing workflows
     - Expected results
     - Troubleshooting checklist
     - Configuration files
     - Verification checklist

7. **`DPDK_IMPLEMENTATION_STATUS.md`**
   - **Content**: Implementation details and summary
   - **Sections**:
     - Setup completion status
     - Component descriptions
     - Quick start (3 steps)
     - Architecture diagram
     - Data flow
     - Performance metrics
     - Testing scenarios
     - Troubleshooting guide
     - Next steps

8. **`TESTING_WORKFLOW.txt`**
   - **Content**: Visual workflow diagram
   - **Includes**:
     - Step-by-step process diagram
     - Service startup verification
     - PCAP replay process
     - IDS processing pipeline
     - Accuracy calculation flow
     - Metrics output example
     - Command reference

9. **`SETUP_COMPLETE.txt`**
   - **Content**: Setup completion summary
   - **Includes**:
     - What was implemented
     - Quick start (3 steps)
     - System architecture
     - File locations
     - Verification checklist
     - Testing scenarios
     - Expected performance
     - Common commands

## 📁 File Structure

```
/home/ifscr/SE_02_2025/IDS/
├── Core Scripts
│   ├── dpdk_pcap_replay.py                    (13 KB)
│   ├── calculate_accuracy_metrics.py          (17 KB)
│   ├── test_dpdk_replay.sh                    (6.6 KB)
│   │
├── Configuration Scripts
│   └── dpdk_suricata_ml_pipeline/scripts/
│       └── 04_configure_dpdk_input.sh
│
├── Documentation
│   ├── DPDK_PCAP_REPLAY_GUIDE.md              (Complete guide)
│   ├── DPDK_TESTING_QUICK_REFERENCE.md        (Quick reference)
│   ├── DPDK_IMPLEMENTATION_STATUS.md          (Implementation details)
│   ├── TESTING_WORKFLOW.txt                   (Visual workflow)
│   ├── SETUP_COMPLETE.txt                     (Setup summary)
│   └── RESOURCES_CREATED.md                   (This file)
│
├── Available PCAP Samples
│   └── dpdk_suricata_ml_pipeline/pcap_samples/
│       ├── normal_traffic.pcap                (~5 MB)
│       ├── dos_traffic_sample.pcap            (~3 MB)
│       └── mixed_traffic_sample.pcap          (~8 MB)
│
└── Output Directory (Created at runtime)
    └── test_results/
        ├── accuracy_report.json               (Metrics)
        ├── predictions_detailed.csv           (Per-packet analysis)
        └── *_packets.csv                      (Ground truth)
```

## 🎯 Quick Command Reference

### Setup & Configuration
```bash
# Configure DPDK input
bash dpdk_suricata_ml_pipeline/scripts/04_configure_dpdk_input.sh

# Start pipeline
sudo bash run_realtime_engine_dpdk.sh start

# Stop pipeline
sudo bash run_realtime_engine_dpdk.sh stop
```

### Testing
```bash
# Single PCAP replay
python3 dpdk_pcap_replay.py traffic.pcap --csv ground_truth.csv

# Replay with rate limit
python3 dpdk_pcap_replay.py traffic.pcap --rate 100000

# Multiple replays for stress test
python3 dpdk_pcap_replay.py traffic.pcap --repeat 10

# End-to-end automated test
sudo bash test_dpdk_replay.sh start
```

### Metrics & Analysis
```bash
# Calculate accuracy metrics
python3 calculate_accuracy_metrics.py \
  --packets ground_truth.csv \
  --predictions logs/ml_consumer.log \
  --output accuracy.json

# Save detailed per-packet predictions
python3 calculate_accuracy_metrics.py \
  --packets *.csv \
  --predictions logs/ml_consumer.log \
  --detailed predictions.csv
```

### Monitoring
```bash
# Watch Feature Engine logs
tail -f logs/feature_engine.log

# Watch ML Consumer predictions
tail -f logs/ml_consumer.log

# View DPDK binding status
sudo python3 /usr/local/bin/dpdk-devbind.py --status
```

## 🔍 File Descriptions

### dpdk_pcap_replay.py

**Class: `DPDKReplayConfig`**
- Configuration constants for DPDK operation
- NIC PCI address, core mask, memory allocation

**Class: `PCAPReplayEngine`**
- Load and parse PCAP files
- Extract packet features
- Replay via kernel AF_PACKET or DPDK PMD
- Rate limiting and burst handling
- CSV export of ground truth

**Methods**:
- `load_pcap()`: Load PCAP file using Scapy
- `replay_kernel()`: Replay via kernel sockets
- `replay_dpdk()`: Replay via DPDK (if available)
- `export_csv()`: Export ground truth to CSV
- `print_stats()`: Display replay statistics

### calculate_accuracy_metrics.py

**Class: `AccuracyMetricsCalculator`**
- Load ground truth from PCAP CSVs
- Load predictions from ML Consumer logs
- Match predictions to ground truth
- Calculate comprehensive metrics

**Methods**:
- `load_ground_truth()`: Load PCAP CSV files
- `load_predictions()`: Parse ML Consumer log
- `match_predictions_to_ground_truth()`: Align data
- `calculate_metrics()`: Compute accuracy metrics
- `print_report()`: Display formatted report
- `save_json()`: Export metrics to JSON
- `save_detailed_csv()`: Export per-packet predictions

**Metrics Calculated**:
- Accuracy, Precision, Recall, F1-Score
- Confusion Matrix (TP, TN, FP, FN)
- Confidence statistics (mean, std, min, max)
- Per-class metrics (BENIGN, ATTACK)

### test_dpdk_replay.sh

**Functions**:
- `check_root()`: Verify sudo access
- `init_env()`: Initialize Python venv
- `start_pipeline()`: Start DPDK services
- `run_pcap_replay()`: Replay PCAP files
- `collect_predictions()`: Save ML output
- `stop_pipeline()`: Stop all services
- `show_results()`: Display summary

**Operations**:
1. Starts Kafka, Suricata DPDK, Feature Engine, ML Consumer
2. Replays all PCAP samples sequentially
3. Captures ground truth for each sample
4. Collects predictions from ML Consumer
5. Saves all results to test_results/

## 📊 Expected Output Files

### From dpdk_pcap_replay.py

**Console Output**:
```
[*] Loading PCAP: mixed_traffic_sample.pcap
[+] Loaded 10000 packets (5.2 MB)
[*] Starting replay via kernel sockets
[1/1] 10000 packets (5.2 MB) @ 50000 pkt/s

REPLAY STATISTICS
======================================================================
Total packets loaded:   10,000
Total packets sent:     10,000
Total data sent:        5.2 MB
Duration:               0.20 seconds
Packet rate:            50,000 pkt/s
Data rate:              208.0 Mbps
```

**CSV Output** (ground_truth.csv):
```
timestamp,packet_size,src_ip,dst_ip,src_port,dst_port,protocol
2025-11-12T10:30:45.123456,64,192.168.1.100,8.8.8.8,5001,53,UDP
2025-11-12T10:30:45.125432,128,192.168.1.101,8.8.8.8,5002,53,UDP
...
```

### From calculate_accuracy_metrics.py

**Console Output**:
```
IDS ACCURACY METRICS REPORT
======================================================================
Total samples analyzed:     10,000
Accuracy:                   97.45%
Correct predictions:        9,745
Incorrect predictions:      255

BENIGN CLASS METRICS          ATTACK CLASS METRICS
Precision:   99.29%           Precision:   94.46%
Recall:      97.86%           Recall:      97.33%
F1-Score:    98.56%           F1-Score:    95.88%

CONFUSION MATRIX
                    Predicted BENIGN  Predicted ATTACK
Actual BENIGN                6850              150
Actual ATTACK                 80              2920
```

**JSON Output** (accuracy.json):
```json
{
  "timestamp": "2025-11-12T10:45:30.123456",
  "overall": {
    "accuracy": 0.9745,
    "total_correct": 9745,
    "total_incorrect": 255
  },
  "benign_class": {
    "precision": 0.9929,
    "recall": 0.9786,
    "f1_score": 0.9856,
    "true_positives": 2920,
    "false_positives": 80,
    "true_negatives": 6850,
    "false_negatives": 150
  },
  ...
}
```

**CSV Output** (predictions_detailed.csv):
```
index,ground_truth,prediction,confidence,correct,flow
0,BENIGN,BENIGN,0.9824,YES,192.168.1.100:5001 -> 8.8.8.8:53
1,BENIGN,BENIGN,0.9756,YES,192.168.1.101:5002 -> 8.8.8.8:53
2,ATTACK,ATTACK,0.9512,YES,192.168.1.102:5003 -> 10.0.0.1:445
...
```

## 🚀 Usage Workflow

### Workflow 1: Quick Test (5 minutes)
```bash
# 1. Start pipeline
sudo bash run_realtime_engine_dpdk.sh start

# 2. Replay one sample
python3 dpdk_pcap_replay.py \
  dpdk_suricata_ml_pipeline/pcap_samples/normal_traffic.pcap \
  --csv results/gt.csv

# 3. Calculate accuracy
python3 calculate_accuracy_metrics.py \
  --packets results/gt.csv \
  --predictions logs/ml_consumer.log

# 4. Stop pipeline
sudo bash run_realtime_engine_dpdk.sh stop
```

### Workflow 2: Comprehensive Test (30 minutes)
```bash
# 1. Run full test suite
sudo bash test_dpdk_replay.sh start

# 2. Calculate combined accuracy
python3 calculate_accuracy_metrics.py \
  --packets test_results/*_packets.csv \
  --predictions test_results/ml_predictions.log \
  --output test_results/accuracy.json \
  --detailed test_results/predictions.csv

# 3. Analyze results
cat test_results/accuracy.json | jq .
```

### Workflow 3: Stress Test (1+ hour)
```bash
# 1. Start pipeline
sudo bash run_realtime_engine_dpdk.sh start

# 2. Replay with high repeat count
python3 dpdk_pcap_replay.py \
  dpdk_suricata_ml_pipeline/pcap_samples/mixed_traffic_sample.pcap \
  --repeat 100 \
  --rate 1000000 \
  --csv results/stress_test.csv

# 3. Calculate metrics
python3 calculate_accuracy_metrics.py \
  --packets results/stress_test.csv \
  --predictions logs/ml_consumer.log \
  --output results/stress_accuracy.json
```

## 🎓 Learning Path

1. **Start**: Read `SETUP_COMPLETE.txt` for overview
2. **Quick Start**: Follow `DPDK_TESTING_QUICK_REFERENCE.md` 3-step intro
3. **Deep Dive**: Study `DPDK_PCAP_REPLAY_GUIDE.md` for details
4. **Workflow**: View `TESTING_WORKFLOW.txt` for visual process
5. **Debug**: Check `DPDK_IMPLEMENTATION_STATUS.md` for troubleshooting

## 📝 Notes

- All scripts are executable and Python 3.8+ compatible
- Requires: Scapy, numpy, pandas, scikit-learn (will be auto-installed)
- DPDK mode requires: DPDK 23.11.0+ and Suricata with DPDK support
- Tests generate CSV and JSON output for analysis and archiving
- Ground truth inference uses simple heuristics (can be customized)
- Supports both kernel AF_PACKET and DPDK PMD modes

## ✅ Verification

Confirm all resources created:
```bash
ls -lah \
  dpdk_pcap_replay.py \
  calculate_accuracy_metrics.py \
  test_dpdk_replay.sh \
  DPDK_PCAP_REPLAY_GUIDE.md \
  DPDK_TESTING_QUICK_REFERENCE.md \
  DPDK_IMPLEMENTATION_STATUS.md \
  TESTING_WORKFLOW.txt \
  SETUP_COMPLETE.txt
```

All files should exist and be executable/readable.

---

**Created**: November 12, 2025
**Status**: ✅ Complete
**Ready for**: DPDK PCAP Replay Testing & IDS Accuracy Validation
