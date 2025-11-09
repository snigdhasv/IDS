# Dashboard Metrics Display Fix

**Date**: November 9, 2025  
**Issue**: Dashboard showing "Waiting for metrics" even though metrics file exists

---

## Problem

The Streamlit dashboard was displaying:
```
Monitoring: logs/metrics
Waiting for: metrics_20251109.jsonl
```

Even though the metrics file existed and was being actively written to.

---

## Root Cause

**Path Mismatch**: The dashboard was looking in the wrong directory.

- **Dashboard expected**: `/home/sujay/Programming/IDS/logs/metrics/`
- **Metrics actually in**: `/home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/logs/metrics/`

The `logs/metrics/` directory exists but is empty. The actual metrics are in `dpdk_suricata_ml_pipeline/logs/metrics/`.

---

## Solution

Fixed the `get_metrics_directory()` function in `dashboard.py`:

```python
# OLD - WRONG:
def get_metrics_directory():
    script_dir = Path(__file__).parent
    return script_dir / 'logs' / 'metrics'  # ❌ Wrong path

# NEW - FIXED:
def get_metrics_directory():
    script_dir = Path(__file__).parent
    return script_dir / 'dpdk_suricata_ml_pipeline' / 'logs' / 'metrics'  # ✅ Correct path
```

---

## Verification

```bash
# Check metrics file exists and is active
ls -lh /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/logs/metrics/metrics_20251109.jsonl
# Output: 64K file with 312+ lines

# Check file is being updated
tail -f /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/logs/metrics/metrics_20251109.jsonl
# Should see new lines appearing every ~15 seconds
```

---

## Current Status

✅ **Metrics File**: Active and updating
- Location: `dpdk_suricata_ml_pipeline/logs/metrics/metrics_20251109.jsonl`
- Size: 64KB
- Lines: 312+
- Last update: Within last 30 seconds
- Component: `ensemble_consumer` (throughput metrics)

✅ **Dashboard**: Now pointing to correct directory
- Will auto-refresh every 5 seconds (default)
- Will show last 10 minutes of data (default)

---

## What You Should See Now

After refreshing the dashboard (or waiting for auto-refresh):

1. **Overview Section**:
   - Total Events Processed
   - ML Predictions count
   - Average Latency
   - Total Errors

2. **Throughput Section**:
   - Time series chart showing events/second
   - Table showing ensemble_consumer throughput

3. **Other Sections** (if data available):
   - Latency metrics
   - ML predictions distribution
   - System resources
   - Errors/warnings

---

## If Dashboard Still Shows "Waiting"

Possible reasons:

1. **Dashboard hasn't auto-refreshed yet**
   - Click the "🔄 Refresh Now" button
   - Or wait 5 seconds for auto-refresh

2. **Time window too narrow**
   - Use sidebar slider to increase "Data lookback window" to 60 minutes
   - This will show all metrics from the last hour

3. **Need to restart dashboard**
   ```bash
   # Stop the dashboard (Ctrl+C in terminal)
   # Restart it
   streamlit run dashboard.py --server.port 8502
   ```

---

## Monitoring in Real-Time

To verify metrics are flowing:

```bash
# Watch metrics file grow
watch -n 1 'ls -lh /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/logs/metrics/metrics_20251109.jsonl'

# See latest metrics in real-time
tail -f /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/logs/metrics/metrics_20251109.jsonl | jq .

# Count metrics by type
cat /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/logs/metrics/metrics_20251109.jsonl | \
  jq -r .type | sort | uniq -c
```

---

## Dashboard Configuration

Access via sidebar:
- **Auto-refresh interval**: 1-60 seconds (default: 5s)
- **Data lookback window**: 1-60 minutes (default: 10m)

Adjust these if you want:
- More frequent updates → decrease refresh interval
- More historical data → increase lookback window

---

**Status**: ✅ Fixed - Dashboard now points to correct metrics directory
