# How to Monitor Metrics When AF_PACKET Mode is Running

## Quick Answer

If you already have `run_afpacket_mode.sh` running in one terminal, simply open a second terminal and run:

```bash
cd /home/sujay/Programming/IDS
./monitor_metrics.sh
```

This will launch the metrics dashboard showing real-time performance statistics.

---

## Detailed Setup

### Scenario: AF_PACKET Mode Already Running

**Terminal 1** - Your IDS Pipeline (already running):
```bash
cd /home/sujay/Programming/IDS
sudo ./run_afpacket_mode.sh
# Select option 1: Start Complete Pipeline
# This starts: Kafka → Suricata → Bridge → ML Consumer
```

**Terminal 2** - Monitor Metrics:
```bash
cd /home/sujay/Programming/IDS
./monitor_metrics.sh
```

That's it! The dashboard will show live metrics.

---

## Monitor Script Options

```bash
# Default: Launch dashboard
./monitor_metrics.sh

# Check if metrics are being generated
./monitor_metrics.sh --status

# View raw metrics in real-time (JSON format)
./monitor_metrics.sh --tail

# List all metrics files
./monitor_metrics.sh --files

# Show help
./monitor_metrics.sh --help
```

---

## What Each Option Does

### 1. Dashboard (Default)
```bash
./monitor_metrics.sh
# or
./monitor_metrics.sh --dashboard
```

**Shows:**
```
╔═══════════════════════════════════════════════════════════════╗
║              IDS Pipeline Metrics Dashboard                   ║
╚═══════════════════════════════════════════════════════════════╝

📊 LATENCY METRICS
─────────────────────────────────────────────────────────────────
Component: ml_consumer | Operation: ml_inference
  Mean:   12.3 ms
  P50:    11.2 ms
  P95:    18.9 ms
  P99:    25.7 ms

🚀 THROUGHPUT METRICS
─────────────────────────────────────────────────────────────────
  Events/sec:       82.5
  Total Events:     1,234

🤖 ML METRICS
─────────────────────────────────────────────────────────────────
  Prediction Distribution:
    BENIGN:    890 (89%)
    DoS:        78 (8%)
    PortScan:   32 (3%)

[Refreshes every 5 seconds]
```

### 2. Status Check
```bash
./monitor_metrics.sh --status
```

**Shows:**
- ✓ Which pipeline components are running
- ✓ Metrics files location and size
- ✓ Latest metrics timestamp
- ⚠️ Warnings if components are missing

**Example output:**
```
Checking pipeline status...
✓ Kafka Bridge is running
✓ ML Consumer is running

✓ All pipeline components running!

Checking metrics files...
✓ Found 1 metrics file(s)

Metrics files:
-rw-rw-r-- 1 sujay sujay 145K Oct 26 15:30 metrics_20251026.jsonl
-rw-rw-r-- 1 sujay sujay  89K Oct 26 15:30 metrics_20251026.csv

Latest metrics file: metrics_20251026.jsonl
File size: 145K
Line count: 3456 metrics
Last modified: 2025-10-26 15:30:45
```

### 3. Tail Metrics
```bash
./monitor_metrics.sh --tail
```

**Shows:** Raw JSON metrics in real-time (useful for debugging)

**Example output:**
```
Tailing: metrics_20251026.jsonl
(Press Ctrl+C to exit)

{
  "timestamp": 1729959045.123,
  "metric_type": "latency",
  "component": "ml_consumer",
  "operation": "ml_inference",
  "latency_ms": 12.345
}
{
  "timestamp": 1729959045.456,
  "metric_type": "throughput",
  "component": "ml_consumer",
  "events_count": 100,
  "events_per_second": 82.5
}
```

### 4. List Files
```bash
./monitor_metrics.sh --files
```

**Shows:** All metrics files in `logs/metrics/` directory

---

## Complete Workflow Example

### Step-by-Step: Monitoring an Already Running Pipeline

**Step 1: Check if pipeline is running**
```bash
./monitor_metrics.sh --status
```

If you see:
- ✓ Components running → Good! Proceed to Step 2
- ⚠️ Components missing → Start them with `run_afpacket_mode.sh`

**Step 2: Launch dashboard**
```bash
./monitor_metrics.sh
```

**Step 3: Watch metrics update**
- Dashboard refreshes every 5 seconds
- Shows real-time performance
- Press Ctrl+C to exit

**Step 4: Analyze historical data (optional)**
```bash
# View raw data
cat logs/metrics/metrics_$(date +%Y%m%d).jsonl | jq '.'

# Open in spreadsheet
libreoffice logs/metrics/metrics_$(date +%Y%m%d).csv
```

---

## Terminal Layout Recommendation

### 2-Terminal Setup (Simple)
```
┌─────────────────────────────┬─────────────────────────────┐
│   Terminal 1: Pipeline      │   Terminal 2: Dashboard     │
│                              │                             │
│   $ sudo ./run_afpacket_    │   $ ./monitor_metrics.sh    │
│     mode.sh                  │                             │
│                              │   📊 Metrics Dashboard      │
│   [INFO] Processing...      │   ─────────────────────     │
│   [INFO] Prediction: BENIGN │   Latency: 12ms (P95)      │
│                              │   Throughput: 82 evt/s      │
└─────────────────────────────┴─────────────────────────────┘
```

### 3-Terminal Setup (Advanced)
```
┌───────────────────┬──────────────────┬──────────────────┐
│ Terminal 1:       │ Terminal 2:      │ Terminal 3:      │
│ Pipeline          │ Dashboard        │ Logs             │
│                   │                  │                  │
│ $ sudo ./run_     │ $ ./monitor_     │ $ tail -f logs/  │
│   afpacket_mode   │   metrics.sh     │   ml/*.log       │
│                   │                  │                  │
│ [Running...]      │ 📊 Dashboard     │ [INFO] Events... │
└───────────────────┴──────────────────┴──────────────────┘
```

---

## Troubleshooting

### Problem: Dashboard shows "No metrics files found"

**Cause:** Pipeline hasn't generated metrics yet

**Solution:**
```bash
# 1. Check if pipeline is running
./monitor_metrics.sh --status

# 2. If components are running, wait 10-30 seconds
#    Metrics are flushed every 30 seconds

# 3. Check again
./monitor_metrics.sh --status

# 4. If still no metrics, check if MetricsLogger is enabled in code
grep -r "MetricsLogger" dpdk_suricata_ml_pipeline/src/
```

### Problem: "Pipeline not running" warning

**Cause:** `run_afpacket_mode.sh` not started yet

**Solution:**
```bash
# Terminal 1: Start pipeline first
sudo ./run_afpacket_mode.sh
# Select option 1: Start Complete Pipeline

# Terminal 2: Then monitor
./monitor_metrics.sh
```

### Problem: Dashboard shows stale data

**Cause:** Pipeline stopped, dashboard reading old files

**Solution:**
```bash
# Check if pipeline is still running
ps aux | grep -E 'suricata|bridge|consumer'

# If not running, restart:
sudo ./run_afpacket_mode.sh
```

---

## Integration with DPDK Mode

The monitoring script works **identically** with DPDK mode:

**Terminal 1** - DPDK Pipeline:
```bash
sudo ./run_dpdk_mode.sh
```

**Terminal 2** - Monitor (same command):
```bash
./monitor_metrics.sh
```

The script auto-detects which mode is running and displays appropriate metrics.

---

## Key Metrics to Watch

### For AF_PACKET Mode

**Good Performance:**
- **P95 Latency**: < 100ms end-to-end
- **Throughput**: 50-200 events/sec
- **CPU**: 50-80%
- **Confidence**: > 0.8

**Warning Signs:**
- P99 > 500ms → Investigate bottlenecks
- Throughput < 10/s → Check for errors
- Many errors → Check logs
- Low confidence < 0.5 → Model quality issue

---

## Quick Reference

```bash
# Most common usage
./monitor_metrics.sh                    # Launch dashboard

# Check if working
./monitor_metrics.sh --status          # Status check

# Debug
./monitor_metrics.sh --tail            # Raw metrics
tail -f logs/ml/ml_consumer.log        # ML consumer logs

# Analysis
cat logs/metrics/metrics_*.jsonl | jq '.'              # Pretty JSON
libreoffice logs/metrics/metrics_$(date +%Y%m%d).csv  # Spreadsheet
```

---

## Summary

**Simple answer:** Open a second terminal and run `./monitor_metrics.sh`

**What it does:**
- ✓ Checks if pipeline is running
- ✓ Verifies metrics are being generated
- ✓ Launches real-time dashboard
- ✓ Updates every 5 seconds
- ✓ Works with both AF_PACKET and DPDK modes

**Files created:**
- `monitor_metrics.sh` - Monitoring script (executable)
- `logs/metrics/metrics_YYYYMMDD.jsonl` - Metrics data
- `logs/metrics/metrics_YYYYMMDD.csv` - Spreadsheet format
