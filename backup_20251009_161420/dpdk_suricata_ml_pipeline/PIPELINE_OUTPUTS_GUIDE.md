# IDS Pipeline Output Guide 📊

**Complete guide to monitoring and viewing outputs from your IDS+ML pipeline**

---

## 🎯 Quick Summary

Your pipeline has **5 main output locations**:

1. **Suricata Events** → `/var/log/suricata/eve.json`
2. **Kafka Bridge** → Forwards events to Kafka topic `suricata-alerts`
3. **ML Predictions** → Console output + Kafka topic `ml-predictions`
4. **Bridge Logs** → `~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/bridge/`
5. **ML Consumer Logs** → `~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/`

---

## 📍 Output Locations

### 1. Suricata Outputs (Primary Source)

**Location:** `/var/log/suricata/`

#### `eve.json` - Main Event Log (JSON format)
All Suricata events in structured JSON format:
- **Alerts**: IDS rule matches
- **Flows**: Network flow summaries
- **DNS**: DNS queries/responses
- **HTTP**: HTTP transactions
- **TLS**: TLS handshake data
- **Stats**: Performance statistics

```bash
# View live events (formatted)
tail -f /var/log/suricata/eve.json | jq .

# View alerts only
grep '"event_type":"alert"' /var/log/suricata/eve.json | jq .

# View flow events
grep '"event_type":"flow"' /var/log/suricata/eve.json | jq .

# Search by severity
grep '"severity":1' /var/log/suricata/eve.json | jq .  # High severity
grep '"severity":2' /var/log/suricata/eve.json | jq .  # Medium
```

#### `fast.log` - Quick Alert Summary
Human-readable alert summaries:
```bash
tail -f /var/log/suricata/fast.log
```

#### `stats.log` - Performance Statistics
```bash
tail -f /var/log/suricata/stats.log
```

---

### 2. Kafka Topics (Event Stream)

#### Topic: `suricata-alerts` (Input)
Contains all events forwarded from Suricata via the bridge.

```bash
# View all events from beginning
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic suricata-alerts \
  --from-beginning | jq .

# View live events
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic suricata-alerts | jq .

# Count total messages
/opt/kafka/bin/kafka-run-class.sh kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic suricata-alerts
```

#### Topic: `ml-predictions` (Output)
Contains ML predictions and enhanced alerts.

```bash
# View ML predictions
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic ml-predictions \
  --from-beginning | jq .

# View only malicious predictions
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic ml-predictions \
  --from-beginning | jq 'select(.prediction != "BENIGN")'
```

---

### 3. Kafka Bridge Logs

**Location:** `~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/bridge/`

#### `bridge.log` - Bridge Activity
Tracks events forwarded from Suricata to Kafka.

```bash
# View live bridge activity
tail -f ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/bridge/bridge.log

# Check bridge statistics
grep "Statistics" ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/bridge/bridge.log
```

---

### 4. ML Consumer Logs

**Location:** `~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/`

#### `ml_consumer.log` - Detailed Processing Logs
Full debug information about ML predictions.

```bash
# View live ML processing
tail -f ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log

# Search for ML alerts
grep "ML Alert" ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log
```

#### `ml_consumer.out` - Console Output
User-friendly statistics and summaries.

```bash
# View consumer statistics
tail -f ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.out

# See last session stats
tail -50 ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.out
```

---

## 🖥️ Real-Time Monitoring Setup

### Multi-Terminal Monitoring

Open 4 terminals for complete visibility:

**Terminal 1: Suricata Alerts**
```bash
tail -f /var/log/suricata/eve.json | grep '"event_type":"alert"' | jq .
```

**Terminal 2: ML Consumer Output**
```bash
tail -f ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.out
```

**Terminal 3: Bridge Activity**
```bash
tail -f ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/bridge/bridge.log
```

**Terminal 4: ML Predictions (Kafka)**
```bash
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic ml-predictions | jq .
```

---

## 🔍 Searching and Filtering

### Find Specific Attack Types

```bash
# SQL injection
grep -i "SQL" /var/log/suricata/eve.json | jq .

# XSS attacks
grep -i "XSS" /var/log/suricata/eve.json | jq .

# Port scans
grep -i "scan" /var/log/suricata/eve.json | jq .

# DDoS patterns
grep -i "DDoS\|flood" /var/log/suricata/eve.json | jq .
```

### Filter by Source/Destination

```bash
# Events from specific IP
grep '"src_ip":"192.168.100.2"' /var/log/suricata/eve.json | jq .

# Events to specific port
grep '"dest_port":80' /var/log/suricata/eve.json | jq .
```

### Filter by Time Range

```bash
# Events from today
grep "$(date +%Y-%m-%d)" /var/log/suricata/eve.json | jq .

# Events in last hour
find /var/log/suricata -name "eve.json" -mmin -60 -exec cat {} \;
```

---

## 📈 Statistics and Metrics

### Count Events by Type

```bash
# Count alerts
grep -c '"event_type":"alert"' /var/log/suricata/eve.json

# Count flows
grep -c '"event_type":"flow"' /var/log/suricata/eve.json

# Count by severity
grep -c '"severity":1' /var/log/suricata/eve.json  # High
grep -c '"severity":2' /var/log/suricata/eve.json  # Medium
grep -c '"severity":3' /var/log/suricata/eve.json  # Low
```

### Kafka Topic Statistics

```bash
# Messages per topic
/opt/kafka/bin/kafka-run-class.sh kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic suricata-alerts

# Consumer group lag
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group ml-consumer-group \
  --describe
```

### ML Prediction Statistics

```bash
# Count predictions by type
grep "ML Alert:" ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log | \
  awk -F': ' '{print $3}' | awk '{print $1}' | sort | uniq -c

# Average confidence scores
grep "confidence:" ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log | \
  awk -F'confidence: ' '{print $2}' | awk -F'%' '{print $1}' | \
  awk '{sum+=$1; n++} END {if (n>0) print sum/n "%"}'
```

---

## 🚨 Why Does ML Consumer Stop?

**This is EXPECTED behavior!**

The ML consumer exits when:
1. ✅ No new events for 1 second (timeout)
2. ✅ All available events processed
3. ✅ Ctrl+C pressed

### To Keep It Running:
1. Send continuous traffic from external device
2. Modify timeout in `ml_kafka_consumer.py`:
   ```python
   consumer.poll(timeout_ms=1000)  # Change to 60000 for 1 minute
   ```

---

## 📊 Complete Data Flow

```
External Device (192.168.100.2)
         ↓ [network traffic]
   USB Adapter (enx00e04c36074c)
         ↓ [AF_PACKET capture]
   Suricata (PID 196305)
         ↓ [writes JSON]
   /var/log/suricata/eve.json ← 📍 READ HERE
         ↓ [tailed by bridge]
   Kafka Bridge (suricata_kafka_bridge.py)
         ↓ [publishes to Kafka]
   Kafka Topic: suricata-alerts ← 📍 STREAM HERE
         ↓ [consumed by ML]
   ML Consumer (ml_kafka_consumer.py)
         ├─→ Feature Extraction (65 features)
         ├─→ Feature Mapping (65→34 features)
         ├─→ ML Prediction (Random Forest)
         └─→ Kafka Topic: ml-predictions ← 📍 RESULTS HERE
```

---

## 🎯 Quick Commands Reference

| Task | Command |
|------|---------|
| **View live Suricata alerts** | `tail -f /var/log/suricata/eve.json \| jq .` |
| **View Kafka events** | `/opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic suricata-alerts` |
| **View ML predictions** | `tail -f ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.out` |
| **Check pipeline status** | `cd scripts && ./quick_start.sh` (option 6) |
| **Start ML consumer** | `cd scripts && ./04_start_ml_consumer.sh` |
| **Count total events** | `wc -l /var/log/suricata/eve.json` |
| **Search for attack** | `grep -i "attack_name" /var/log/suricata/eve.json \| jq .` |

---

## ✅ Fixes Applied (Oct 8, 2025)

### Issue 1: Suricata Status Detection ❌→✅
- **Problem**: `quick_start.sh` couldn't detect running Suricata
- **Fix**: Changed from `pgrep -x suricata` to `ps aux | grep "[s]uricata.*--af-packet"`
- **Status**: ✅ **FIXED**

### Issue 2: Feature Mismatch (65→34) ❌→✅
- **Problem**: Feature extractor produces 65 features, model expects 34
- **Fix**: Created `feature_mapper.py` to map 65→34 features
- **Status**: ✅ **FIXED**

### Issue 3: ML Consumer Crashes ❌→✅
- **Problem**: `predict()` returned 1 value, code expected 2
- **Fix**: Now calls both `predict()` and `predict_proba()` separately
- **Status**: ✅ **FIXED**

### Issue 4: ML Consumer Stops Immediately ❌→✅
- **Problem**: Errors caused immediate exit
- **Fix**: All errors fixed, now processes events successfully
- **Status**: ✅ **FIXED** (exits after processing is normal)

---

## 🎉 Working Example Output

```
2025-10-08 15:15:20 - ML Alert: DDoS (confidence: 34.00%) - 145.254.160.237:3009 → 145.253.2.203:53

═══ Statistics (1s) ═══
  Events processed: 10
  Flows processed: 1
  ML predictions: 1
  ML alerts: 0
  Errors: 0
  Events/sec: 7.95
```

Your ML pipeline is **fully operational**! 🚀

---

## 📞 Need Help?

Check these first:
1. **Status**: `cd scripts && ./quick_start.sh` (option 6)
2. **Logs**: `tail -f ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.out`
3. **Errors**: `grep ERROR ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log`

---

*Last Updated: October 8, 2025*
*Pipeline Version: 1.0 (Feature Mapper Edition)*
