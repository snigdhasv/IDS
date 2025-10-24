# 🎯 ML Model Configuration Guide

## 📍 Current Model Configuration

### **Currently Active Model**
```
Model: Random Forest (2017 CICIDS dataset)
Path: /home/sujay/Programming/IDS/ML Models/random_forest_model_2017.joblib
Type: Random Forest Classifier
Features: 34 features (mapped from 65 CICIDS2017 features)
```

---

## 🗂️ Available Models

Your system has **12 pre-trained models** available in `/home/sujay/Programming/IDS/ML Models/`:

### **2017 Models (CICIDS2017 Dataset)**
| Model Type | Filename | Best For |
|------------|----------|----------|
| **Random Forest** ⭐ | `random_forest_model_2017.joblib` | **Currently Active** - Best overall accuracy |
| Decision Tree | `decision_tree_model_2017.joblib` | Fast inference, interpretable |
| K-Nearest Neighbors | `knn_model_2017.joblib` | Real-time classification |
| LightGBM | `lgb_model_2017.joblib` | High performance, memory efficient |
| Logistic Regression | `lr_model_2017.joblib` | Baseline, very fast |
| Naive Bayes | `nb_model_2017.joblib` | Probabilistic, fast |

### **2018 Models (CICIDS2018 Dataset)**
| Model Type | Filename | Best For |
|------------|----------|----------|
| Random Forest | `random_forest_model_2018.joblib` | Newer attack patterns |
| Decision Tree | `decision_tree_model_2018.joblib` | Fast inference |
| K-Nearest Neighbors | `knn_model_2018.joblib` | Real-time classification |
| LightGBM | `lgb_model_2018.joblib` | High performance |
| Logistic Regression | `lr_model_2018.joblib` | Baseline |
| Naive Bayes | `nb_model_2018.joblib` | Probabilistic |

---

## 🔧 How to Change the Model

### **Method 1: Edit Configuration File (Recommended)**

```bash
# Open the configuration file
nano /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf

# Find this line (around line 40):
ML_MODEL_PATH="/home/sujay/Programming/IDS/ML Models/random_forest_model_2017.joblib"

# Change to your desired model, for example:
ML_MODEL_PATH="/home/sujay/Programming/IDS/ML Models/lgb_model_2018.joblib"

# Save and exit (Ctrl+X, Y, Enter)
```

### **Method 2: Edit the ML Consumer Script Directly**

```bash
# Open the consumer script
nano /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/src/ml_kafka_consumer.py

# Find the _load_config method (around line 114)
# Change this line:
'ml_model_name': 'random_forest_model_2017.joblib',

# To:
'ml_model_name': 'lgb_model_2018.joblib',  # or any other model

# Save and exit
```

### **Method 3: Use Different Model Directory**

If you want to use models from a different location:

```bash
# Edit the model_loader.py to point to a different directory
nano /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/src/model_loader.py

# Find line 33:
self.model_dir = Path(__file__).parent.parent / 'models' / 'ML Models'

# Change to your custom path:
self.model_dir = Path('/path/to/your/custom/models')
```

---

## 🔄 Apply Model Changes

After changing the model configuration, **restart the ML consumer**:

```bash
cd /home/sujay/Programming/IDS

# Stop the pipeline
sudo ./run_afpacket_mode.sh stop

# Start again with new model
sudo ./run_afpacket_mode.sh start

# Or restart just the ML consumer
sudo ./run_afpacket_mode.sh
# Select option 4: Start ML Consumer Only
```

---

## 📊 Model Comparison & Selection Guide

### **When to Use Which Model:**

#### **Random Forest** (Current Default) ⭐
- **Pros:** Best overall accuracy, handles imbalanced data well, robust
- **Cons:** Slower than simpler models, larger memory footprint
- **Use for:** Production environments, highest accuracy needed
- **File:** `random_forest_model_2017.joblib`

#### **LightGBM** 🚀
- **Pros:** Fastest training/inference, memory efficient, high accuracy
- **Cons:** More complex to tune
- **Use for:** High-throughput environments, limited resources
- **File:** `lgb_model_2017.joblib` or `lgb_model_2018.joblib`

#### **Decision Tree** 🌳
- **Pros:** Fast, interpretable, easy to visualize
- **Cons:** Can overfit, less accurate than ensemble methods
- **Use for:** Debugging, understanding decision logic
- **File:** `decision_tree_model_2017.joblib`

#### **K-Nearest Neighbors (KNN)** 🔍
- **Pros:** Simple, no training phase, adapts to new patterns
- **Cons:** Slow on large datasets, memory intensive
- **Use for:** Small-scale deployments, anomaly detection
- **File:** `knn_model_2017.joblib`

#### **Logistic Regression** 📈
- **Pros:** Very fast, minimal memory, good baseline
- **Cons:** Lower accuracy, assumes linear separability
- **Use for:** Quick testing, baseline comparisons
- **File:** `lr_model_2017.joblib`

#### **Naive Bayes** 🎲
- **Pros:** Extremely fast, probabilistic, handles missing data
- **Cons:** Assumes feature independence (rarely true)
- **Use for:** Real-time classification, probabilistic reasoning
- **File:** `nb_model_2017.joblib`

### **2017 vs 2018 Models:**

- **2017 Models:** Trained on CICIDS2017 dataset
  - Attack types: DDoS, DoS, Web attacks, Infiltration, Botnet, Brute Force
  - More stable, well-tested
  - **Recommended for most use cases**

- **2018 Models:** Trained on CICIDS2018 dataset
  - Attack types: Brute Force, DoS, DDoS, Infiltration, Botnet
  - Newer patterns, may detect recent attack variations better
  - Less tested in production

---

## 🧪 Testing Different Models

### **Quick Model Comparison Script**

```bash
# Create a test script
cd /home/sujay/Programming/IDS/tests
nano test_model_comparison.py
```

```python
#!/usr/bin/env python3
"""Test different ML models to compare performance"""
import sys
sys.path.append('../dpdk_suricata_ml_pipeline/src')

from model_loader import MLModelLoader
import numpy as np
import time

models_to_test = [
    'random_forest_model_2017.joblib',
    'lgb_model_2017.joblib',
    'decision_tree_model_2017.joblib',
    'knn_model_2017.joblib',
]

# Generate dummy features (34 features)
test_features = np.random.rand(100, 34)

print("Model Performance Comparison")
print("=" * 60)

for model_name in models_to_test:
    loader = MLModelLoader()
    if loader.load_model(model_name):
        start = time.time()
        predictions = loader.predict(test_features)
        elapsed = time.time() - start
        
        print(f"\n{model_name}:")
        print(f"  Inference time: {elapsed*1000:.2f}ms (100 samples)")
        print(f"  Throughput: {100/elapsed:.0f} predictions/sec")
```

```bash
# Run the comparison
python3 test_model_comparison.py
```

---

## 🎨 Model Configuration Examples

### **Example 1: Switch to LightGBM (High Performance)**

```bash
# Edit config
nano /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf

# Change to:
ML_MODEL_PATH="/home/sujay/Programming/IDS/ML Models/lgb_model_2018.joblib"

# Restart
sudo ./run_afpacket_mode.sh stop
sudo ./run_afpacket_mode.sh start
```

### **Example 2: Use 2018 Random Forest (Newer Patterns)**

```bash
# Edit config
nano /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf

# Change to:
ML_MODEL_PATH="/home/sujay/Programming/IDS/ML Models/random_forest_model_2018.joblib"

# Restart
sudo ./run_afpacket_mode.sh stop
sudo ./run_afpacket_mode.sh start
```

### **Example 3: Fast Decision Tree (Low Resources)**

```bash
# Edit config
nano /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf

# Change to:
ML_MODEL_PATH="/home/sujay/Programming/IDS/ML Models/decision_tree_model_2017.joblib"

# Restart
sudo ./run_afpacket_mode.sh stop
sudo ./run_afpacket_mode.sh start
```

---

## 🔍 Verify Active Model

### **Method 1: Check Running Consumer Logs**

```bash
# View ML consumer logs
tail -f /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log

# Look for lines like:
# "Loading model from /home/sujay/Programming/IDS/ML Models/random_forest_model_2017.joblib"
# "Model loaded successfully: Random Forest"
```

### **Method 2: Check Configuration File**

```bash
# View current config
grep "ML_MODEL_PATH" /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf
```

### **Method 3: Interactive Python Check**

```bash
cd /home/sujay/Programming/IDS
python3 << 'EOF'
import sys
sys.path.append('dpdk_suricata_ml_pipeline/src')
from model_loader import MLModelLoader

loader = MLModelLoader()
# This will use the default model directory
print(f"Model directory: {loader.model_dir}")

# Try loading the configured model
if loader.load_model('random_forest_model_2017.joblib'):
    info = loader.get_model_info()
    print(f"Model type: {info['model_type']}")
    print(f"Features: {info['expected_features']}")
    print(f"Model loaded: {info['loaded']}")
EOF
```

---

## 📦 Adding Your Own Custom Models

### **Step 1: Train Your Model**

```python
#!/usr/bin/env python3
"""Train a custom model"""
from sklearn.ensemble import RandomForestClassifier
import joblib
import numpy as np

# Train your model (example)
X_train = np.random.rand(1000, 34)  # 34 features
y_train = np.random.randint(0, 2, 1000)  # Binary classification

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Save the model
joblib.dump(model, '/home/sujay/Programming/IDS/ML Models/custom_model.joblib')
print("✓ Custom model saved!")
```

### **Step 2: Configure to Use Your Model**

```bash
# Edit config
nano /home/sujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf

# Add your model:
ML_MODEL_PATH="/home/sujay/Programming/IDS/ML Models/custom_model.joblib"
```

### **Step 3: Restart Pipeline**

```bash
sudo ./run_afpacket_mode.sh stop
sudo ./run_afpacket_mode.sh start
```

---

## ⚙️ Advanced: Multiple Model Ensemble

Want to use **multiple models simultaneously** for better detection?

See: `/home/sujay/Programming/IDS/utils/adaptive_ensemble_predictor.py`

This implements an adaptive ensemble that combines predictions from multiple models.

---

## 🐛 Troubleshooting Model Loading

### **Issue: "Model file not found"**

```bash
# Check if model file exists
ls -lh "/home/sujay/Programming/IDS/ML Models/"

# Verify path is correct in config
grep "ML_MODEL_PATH" dpdk_suricata_ml_pipeline/config/pipeline.conf

# Check permissions
ls -l "/home/sujay/Programming/IDS/ML Models/random_forest_model_2017.joblib"
```

### **Issue: "Error loading model: incompatible version"**

```bash
# Check scikit-learn version
python3 -c "import sklearn; print(sklearn.__version__)"

# Models may need retraining with current scikit-learn version
# See notebooks/ directory for training scripts
```

### **Issue: "Model expects 34 features but got X"**

This means feature extraction is not producing 34 features. Check:
```bash
# Verify feature mapper configuration
nano dpdk_suricata_ml_pipeline/src/feature_mapper.py

# Should be:
self.feature_mapper = FeatureMapper(target_features=34)
```

---

## 📚 Related Files

- **Configuration:** `dpdk_suricata_ml_pipeline/config/pipeline.conf`
- **Model Loader:** `dpdk_suricata_ml_pipeline/src/model_loader.py`
- **ML Consumer:** `dpdk_suricata_ml_pipeline/src/ml_kafka_consumer.py`
- **Feature Extractor:** `dpdk_suricata_ml_pipeline/src/feature_extractor.py`
- **Feature Mapper:** `dpdk_suricata_ml_pipeline/src/feature_mapper.py`
- **Training Notebooks:** `notebooks/CICIDS2017.ipynb`, `notebooks/CICIDS2018.ipynb`
- **Model Storage:** `ML Models/` (12 pre-trained models)

---

## 🎯 Quick Reference

```bash
# Current model
grep "ML_MODEL_PATH" dpdk_suricata_ml_pipeline/config/pipeline.conf

# List available models
ls -lh "ML Models/"

# Change model (edit this file)
nano dpdk_suricata_ml_pipeline/config/pipeline.conf

# Restart to apply changes
sudo ./run_afpacket_mode.sh stop
sudo ./run_afpacket_mode.sh start

# View model loading logs
tail -f dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log
```

---

**✅ Recommended Configuration for Production:**
```bash
ML_MODEL_PATH="/home/sujay/Programming/IDS/ML Models/random_forest_model_2017.joblib"
```

**🚀 Recommended Configuration for High Performance:**
```bash
ML_MODEL_PATH="/home/sujay/Programming/IDS/ML Models/lgb_model_2018.joblib"
```

**🧪 Recommended Configuration for Testing:**
```bash
ML_MODEL_PATH="/home/sujay/Programming/IDS/ML Models/decision_tree_model_2017.joblib"
```

---

**Need help choosing a model?** Consider:
- **Accuracy priority** → Random Forest
- **Speed priority** → LightGBM or Decision Tree
- **Memory priority** → Logistic Regression or Naive Bayes
- **Latest patterns** → 2018 models
- **Stability** → 2017 models
