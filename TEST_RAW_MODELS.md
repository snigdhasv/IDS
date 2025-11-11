# Testing Raw Feature Models with CICIDS PCAP Replay

## ✅ Setup Complete

The pipeline has been updated to use the new **raw feature models** (trained without PCA on all 78 CICIDS features):

### Models Loaded (99%+ Accuracy)
1. **Random Forest**: 99.47%
2. **Decision Tree**: 99.16%
3. **LightGBM**: 99.88% (BEST)
4. **KNN**: 98.60%
5. **Logistic Regression**: 96.81%

### Key Changes Made
- ✅ Updated `ENSEMBLE_MODELS` list to use `*_raw.joblib` models
- ✅ Removed `feature_selector` dependency (no longer needed)
- ✅ Using **all 78 CICIDS features** instead of 34 PCA features
- ✅ Added scaler loading (`scaler_2017_raw.joblib`)
- ✅ Features are now scaled before inference (matches training)

---

## 🧪 Testing with CICIDS PCAP Replay

### Step 1: Start the Pipeline

```bash
cd /home/s-ujay/Programming/IDS
sudo ./run_realtime_engine.sh restart
```

**What to check:**
- All 5 components start successfully
- Console shows: `✓ Loaded 5/5 models for ensemble`
- Console shows: `✓ Loaded feature scaler from scaler_2017_raw.joblib`

### Step 2: Monitor ML Predictions

Open a new terminal and watch the ML consumer logs:

```bash
tail -f /home/s-ujay/Programming/IDS/logs/ml_consumer.log
```

**Expected output:**
- Benign traffic: Mostly silent (only summary every 100 flows)
- Attack traffic: `🚨 <ATTACK_TYPE> | Confidence: 95.3% | Agreement: 100.0% (5/5) | Flow: ...`

### Step 3: Replay CICIDS PCAP

Find a CICIDS2017 PCAP file and replay it to your NIC:

```bash
# Example: Wednesday morning workday traffic (has DoS Slowloris attacks)
cd /path/to/cicids/pcaps
sudo tcpreplay -i enp0s1 Wednesday-workingHours.pcap
```

**Available CICIDS2017 Days:**
- **Monday**: Benign only
- **Tuesday**: Benign + FTP-Patator + SSH-Patator
- **Wednesday**: Benign + DoS Slowloris + DoS Hulk + DoS GoldenEye + Heartbleed
- **Thursday Morning**: Benign + Web Attack (Brute Force, XSS, SQL Injection)
- **Thursday Afternoon**: Benign + Infiltration
- **Friday Morning**: Benign + Bot
- **Friday Afternoon**: Benign + PortScan + DDoS

### Step 4: Validate Predictions

While replaying, you should see:

1. **Attack Detection in Logs:**
   ```
   🚨 DoS Slowloris | Confidence: 98.2% | Agreement: 100.0% (5/5) | Votes: {'DoS Slowloris': 5} | Flow: 192.168.10.8:49876→192.168.10.50:80
   ```

2. **Check IP Addresses:**
   - Victim IPs: `192.168.10.x` (should appear in attack flows)
   - Attacker IPs: Check CICIDS documentation for attack source IPs

3. **Filter Attack Predictions:**
   ```bash
   grep "🚨" /home/s-ujay/Programming/IDS/logs/ml_consumer.log | tail -20
   ```

---

## 📊 Validating Accuracy Against Ground Truth

To check if predictions match the actual labels from CICIDS CSV:

### Method 1: Manual Comparison

1. **Extract predictions from logs:**
   ```bash
   grep "🚨" logs/ml_consumer.log > predictions.txt
   ```

2. **Load corresponding CSV file** (e.g., `Wednesday-workingHours.pcap.csv`)

3. **Match by flow 5-tuple:**
   - Source IP:Port
   - Destination IP:Port
   - Protocol
   - Compare prediction vs. CSV `Label` column

### Method 2: Automated Testing (TODO)

Create a script that:
1. Replays PCAP
2. Collects predictions
3. Loads CSV ground truth
4. Matches flows by 5-tuple
5. Calculates metrics:
   - True Positives (TP)
   - False Positives (FP)
   - True Negatives (TN)
   - False Negatives (FN)
   - Accuracy = (TP + TN) / Total
   - Precision = TP / (TP + FP)
   - Recall = TP / (TP + FN)
   - F1-Score = 2 * (Precision * Recall) / (Precision + Recall)

---

## 🔍 Troubleshooting

### Issue: No attack predictions at all

**Check 1: Feature extraction working?**
```bash
# Should show 78 features per flow
tail -f logs/feature_engine.log | grep "features:"
```

**Check 2: Models loaded correctly?**
```bash
# Should show: "✓ Loaded 5/5 models for ensemble"
grep "Loaded" logs/ml_consumer.log
```

**Check 3: Kafka messages flowing?**
```bash
# Should show flow messages
kafka-console-consumer --bootstrap-server localhost:9092 --topic ml-features --from-beginning | head -5
```

### Issue: All predictions are BENIGN

**Possibility 1: PCAP is from Monday (all benign)**
- Solution: Use Tuesday-Friday PCAPs with attacks

**Possibility 2: Feature values out of range**
- Check: `tail -f logs/ml_consumer.log` for any warnings
- Solution: Ensure scaler is loaded correctly

**Possibility 3: Wrong NIC capturing traffic**
- Check: `sudo tcpdump -i enp0s1 -n` shows CICIDS IPs (192.168.10.x)
- Solution: Verify bridge and AF_PACKET fanout working

### Issue: Low confidence predictions

**Expected behavior:**
- Ensemble confidence scaled to 90%+ for strong predictions
- If confidence < 90%, check:
  1. Model agreement (should be 4-5/5 for strong predictions)
  2. Feature quality (check for NaN/Inf values)

---

## 📈 Expected Performance

Based on training results:

| Metric | Expected Value |
|--------|----------------|
| **Attack Detection Rate** | 99%+ (high recall) |
| **False Positive Rate** | <1% (high precision) |
| **Ensemble Confidence** | 90-99% for attacks |
| **Model Agreement** | 80-100% (4-5/5 models) |

### Known Limitations

1. **Minority Attack Classes**: Some rare attacks (e.g., Infiltration, Heartbleed) may have lower detection due to class imbalance
2. **Cross-Day Generalization**: Models trained on 2017 data may need retraining for 2018+ datasets
3. **Flow Timeout**: 10-second timeout may split long-lived flows

---

## 🚀 Next Steps

1. **Test with Wednesday PCAP** (DoS attacks - easiest to detect)
2. **Validate high detection rate** (should see many `🚨` alerts)
3. **Create automated accuracy testing script**
4. **Install Suricata rules** for hybrid detection:
   ```bash
   sudo suricata-update
   sudo systemctl restart suricata
   ```
5. **Compare ML predictions vs. Suricata alerts**
6. **Test with 2018 dataset** (retrain if needed)

---

## 📝 Notes

- **Feature Order**: Python 3.7+ dicts maintain insertion order, so features are consistent
- **Scaling**: Models were trained on StandardScaler-normalized features
- **Threshold**: Attack detection requires 60% model agreement + 40% confidence
- **Logging**: Only attack predictions are logged; benign traffic is silent

Good luck with testing! 🎯
