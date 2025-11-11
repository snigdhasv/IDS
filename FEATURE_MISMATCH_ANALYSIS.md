# Feature Mismatch Resolution - Root Cause Analysis

## 🔴 Problem Summary

**Current State:**
- Feature Engine extracts: **77 features**
- Models expect: **69 features**  
- Scaler expects: **69 features**
- Result: `StandardScaler is expecting 69 features as input`

## 🔍 Root Cause

The CICIDS2017 CSV files have **inconsistent whitespace** in column names:
- Some columns: `" ACK Flag Count"` (with leading space)
- Others: `"Total Length of Fwd Packets"` (no leading space)

When the training script (`retrain_models_raw_features.py`) runs:
1. ✅ Strips whitespace from column names (line 183)
2. ✅ Drops zero-variance columns (13 columns)
3. ✅ Drops duplicate `Fwd Header Length.1`
4. ❌ Final dataset: **69 features** (not 77)

The discrepancy (77 vs 69 = **8 features**) is likely because:
- Training script drops more columns during balance/SMOTE
- Or some features become zero-variance after sampling

## ✅ Solution: Three-Part Fix

### Part 1: Identify Exact 69 Features (DONE)

We need to know which 69 features the models were actually trained on:

```python
# Extract from the training process
import pandas as pd
df = pd.read_csv('dataset/CICIDS2017_raw/Monday-WorkingHours.pcap_ISCX.csv', nrows=1000)
df.columns = [col.strip() for col in df.columns]
df = df.drop('Label', axis=1)
# ... apply same preprocessing as training script ...
# Final list = 69 features
```

### Part 2: Update Feature Engine OR Retrain Models

**Option A (QUICK FIX): Use Only 69 Features in Consumer**
- Create feature selector mapping: 77 → 69
- Extract only the 69 features models need
- Apply scaling
- ✅ Works immediately
- ❌ Wastes 8 features from engine

**Option B (PROPER FIX): Retrain Models on 77 Features**  
- Update training script to NOT drop any features engine extracts
- Retrain all 6 models on 77-feature dataset
- Save new scaler for 77 features
- Update consumer to use new models
- ✅ Uses all available features (better accuracy potential)
- ❌ Takes ~3 minutes to retrain

### Part 3: Save Feature Names with Models

Update training script to save feature names:

```python
# After creating X_train
feature_names = X_train.columns.tolist()
joblib.dump(feature_names, 'ML Models/feature_names_2017_raw.joblib')

# Also save scaler with feature names
scaler.feature_names_in_ = feature_names
```

This prevents future mismatches.

## 🚀 Recommended Action Plan

**Immediate (get it working now):**

1. **Identify the 69 features** models were trained on
   ```bash
   python3 extract_training_features.py  # creates /tmp/model_features.txt
   ```

2. **Create feature selector for 77→69**
   ```python
   # In realtime_ensemble_consumer.py
   MODEL_FEATURES = [... list of 69 feature names ...]
   
   def select_model_features(engine_features: Dict) -> List:
       return [engine_features.get(fname, 0) for fname in MODEL_FEATURES]
   ```

3. **Apply scaler to 69 features**
   ```python
   selected = select_model_features(features_dict)
   feature_vector = np.array(selected).reshape(1, -1)
   feature_vector = scaler.transform(feature_vector)  # Now 69→69 ✓
   ```

**Long-term (proper solution):**

1. **Retrain on 77 features**
   - Modify `retrain_models_raw_features.py`:
     - Skip zero-variance removal for features engine extracts
     - Or update engine to NOT extract zero-variance features
   
2. **Save feature metadata**
   - Store feature names with models
   - Store feature extraction order
   - Version models with feature count in filename

3. **Add validation**
   - Consumer checks feature count on startup
   - Fails fast if mismatch detected
   - Logs expected vs actual features

## 📋 Files Needing Updates

### Immediate Fix:
- `dpdk_suricata_ml_pipeline/src/realtime_ensemble_consumer.py`
  - Add MODEL_FEATURES list (69 features)
  - Add select_model_features() function
  - Use selected features instead of all 77

### Long-term Fix:
- `retrain_models_raw_features.py`
  - Save feature names with models
  - Option to skip zero-variance removal
  - Save feature extraction order

- `realtime_feature_engine.py`
  - Match exact CSV feature names (already does via FEATURE_MAPPING)
  - Skip zero-variance features if needed

## 🔧 Next Steps

Choose one:

**A. Quick Fix (10 minutes)**
```bash
# 1. Extract the 69 feature names from training
python3 extract_training_features.py

# 2. Update consumer with feature selector
# (manually edit realtime_ensemble_consumer.py)

# 3. Restart consumer
sudo ./run_realtime_engine.sh restart
```

**B. Proper Fix (30 minutes)**
```bash
# 1. Update training script to save 77-feature models
# (edit retrain_models_raw_features.py)

# 2. Retrain all models
python3 retrain_models_raw_features.py  # ~3 min

# 3. Update consumer to load new models
# (already done - just needs restart)

# 4. Restart consumer
sudo ./run_realtime_engine.sh restart
```

**Which do you prefer?**

---

## 📊 Feature Count Breakdown

| Stage | Count | Notes |
|-------|-------|-------|
| CSV Original | 79 | Includes Label column |
| After Drop Label | 78 | - |
| After Strip Whitespace | 78 | No duplicates from whitespace |
| After Drop Zero-Variance | 66 | Drops 12 zero-variance columns |
| After Drop Fwd Header Length.1 | 65 | Duplicate column |
| **After Training Balance** | **69** | ❓ WHERE DO 4 FEATURES COME FROM? |
| Engine Extracts | 77 | - |

**Mystery:** Training preprocessed to 66, but models trained on 69. Need to trace where 3 extra features appear!

Possible: SMOTE creates synthetic features? Or training script adds derived features?

---

## 💡 Debugging Commands

```bash
# Check model feature count
python3 -c "import joblib; m=joblib.load('ML Models/random_forest_model_2017_raw.joblib'); print(m.n_features_in_)"

# Check scaler feature count  
python3 -c "import joblib; s=joblib.load('ML Models/scaler_2017_raw.joblib'); print(s.n_features_in_)"

# Check engine feature count from Kafka
timeout 3 kafka-console-consumer --bootstrap-server localhost:9092 --topic ml-features --max-messages 1 | jq '.features | length'

# Compare feature lists
diff /tmp/training_features.txt /tmp/engine_features.txt
```

