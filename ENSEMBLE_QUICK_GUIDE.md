# 🎯 IDS Ensemble - Quick Reference Guide

## How to Run the Ensemble IDS

### Start Everything
```bash
cd /home/s-ujay/Programming/IDS
sudo ./run_realtime_engine.sh start
```

This automatically starts:
1. Kafka (message queue)
2. Suricata (signature-based IDS)
3. Suricata-Kafka bridge
4. **Feature Engine** (extracts 65 CICIDS features from packets)
5. **Ensemble ML Consumer** (5 models voting for predictions)

### Stop Everything
```bash
sudo ./run_realtime_engine.sh stop
```

### Restart (stop + start)
```bash
sudo ./run_realtime_engine.sh restart
```

## What is the Ensemble?

The **Ensemble ML Consumer** uses **5 trained models** voting together:

1. **Random Forest** - Tree-based, robust
2. **Decision Tree** - Fast, interpretable  
3. **LightGBM** - Gradient boosting, accurate
4. **KNN** - Instance-based learning
5. **Logistic Regression** - Linear, baseline

### How Voting Works:
- All 5 models predict independently
- **Majority wins** (3/5, 4/5, or 5/5)
- **Confidence thresholds**:
  - Attacks need **80%+ agreement** (4 or 5 models)
  - Attacks need **50%+ confidence**
  - Low-confidence attacks → Reclassified as BENIGN

## Monitor Predictions

### Watch ML Consumer (predictions)
```bash
tail -f logs/ml_consumer.log
```

### Watch Feature Engine (packet capture)
```bash
tail -f logs/feature_engine.log
```

### Filter for Attacks Only
```bash
grep "🚨" logs/ml_consumer.log | tail -20
```

### Filter for High-Confidence Predictions
```bash
grep "Agreement: [89][0-9]\|Agreement: 100" logs/ml_consumer.log
```

## Current Architecture

```
Internet Traffic
      ↓
  NIC (enp0s1)
      ↓
  AF_PACKET Fanout (cluster_id=99)
      ↓
      ├──→ Suricata (signature detection)
      │         ↓
      │    Kafka "suricata-alerts"
      │
      └──→ Feature Engine (65 CICIDS features)
                ↓
           Kafka "ml-features"
                ↓
        Ensemble ML Consumer (5 models)
                ↓
           Attack Alerts!
```

## Performance Stats

### With Ensemble:
- **Max Confidence**: 84% (5/5 models agree)
- **False Positive Reduction**: High (requires 4/5 agreement)
- **Detection**: Bot, DoS, Heartbleed, etc.

### Normal Traffic:
- GitHub, Google, Microsoft → **BENIGN** (correctly classified)
- Low-confidence "attacks" (20-40%) → **Rejected** → BENIGN

## Logs Explained

### ✓ BENIGN Prediction
```
✓ BENIGN | Confidence: 84.0% | Agreement: 100.0% (5/5) | Flow: 140.82.114.21:443-192.168.101.87:41486
```
- All 5 models agreed it's BENIGN
- 84% ensemble confidence
- This is high-quality normal traffic

### 🚨 Attack Detection (would need 80%+ agreement now)
```
🚨 DoS Hulk | Confidence: 92.5% | Agreement: 100.0% (5/5) | Flow: 192.168.1.10:45123-192.168.1.1:80
```
- All 5 models flagged as DoS Hulk attack
- 92.5% confidence
- This is a real attack!

### ⚠️ Rejected Low-Confidence
```
⚠️  Low-confidence Bot rejected (conf: 27.8%, agreement: 60.0%) → Reclassified as BENIGN: flow_id
```
- Only 3/5 models said "Bot"
- Confidence too low (27.8% < 50%)
- Automatically reclassified as BENIGN

## Testing with CICIDS Dataset

To test with real attack traffic:
```bash
sudo tcpreplay -i enp0s1 dpdk_suricata_ml_pipeline/dataset/Wednesday-workingHours.pcap
```

Then watch for high-confidence attack detections!

## Troubleshooting

### No predictions showing?
1. Check if consumer is running: `ps aux | grep ensemble_consumer`
2. Check Kafka: `sudo systemctl status kafka`
3. Check feature engine: `tail logs/feature_engine.log`
4. Generate traffic: `curl http://example.com`
5. Wait 12 seconds (10s flow timeout + 2s processing)

### Too many warnings in log?
The warnings are now suppressed. If still showing, restart:
```bash
sudo ./run_realtime_engine.sh restart
```

### Want to use single model instead?
Edit `run_realtime_engine.sh` line 91:
```bash
# Change this:
python3 -u realtime_ensemble_consumer.py ...

# To this:
python3 -u realtime_ml_consumer.py ...
```

## Files Summary

- **run_realtime_engine.sh** - Master control script
- **realtime_feature_engine.py** - Extracts 65 CICIDS features from packets
- **realtime_ensemble_consumer.py** - 5-model ensemble with voting
- **realtime_ml_consumer.py** - Single model (original)
- **feature_selector.py** - Selects 34 best features for PCA models
- **model_loader.py** - Loads ML models

## Quick Stats

```bash
# Count total predictions
wc -l logs/ml_consumer.log

# Count attacks detected
grep -c "🚨" logs/ml_consumer.log

# Count benign flows
grep -c "✓ BENIGN" logs/ml_consumer.log

# Show last 10 predictions
grep -E "🚨|✓ BENIGN.*Agreement" logs/ml_consumer.log | tail -10
```

## What's Next?

1. **Dashboard**: Create Grafana or Next.js dashboard for visualization
2. **Alerting**: Send email/Slack notifications for high-confidence attacks
3. **Storage**: Save predictions to database for analysis
4. **Fine-tuning**: Adjust confidence thresholds based on your network

---

**Status**: ✅ **OPERATIONAL**  
**Mode**: Ensemble (5 models)  
**Real-time**: Yes (12s detection latency)  
**False Positives**: Low (80% agreement threshold)
