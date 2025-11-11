#!/usr/bin/env python3
"""
Diagnose Feature Mismatch Between Engine and Models

This script identifies which features the training removed vs what the engine produces.
"""

import pandas as pd
import json
from kafka import KafkaConsumer
from pathlib import Path

print("=" * 80)
print("FEATURE MISMATCH DIAGNOSIS")
print("=" * 80)

# Step 1: Get features from CSV (what training script sees initially)
print("\n📄 Step 1: Loading CSV to see original features...")
csv_path = "dataset/CICIDS2017_raw/Monday-WorkingHours.pcap_ISCX.csv"
df = pd.read_csv(csv_path, nrows=100)
csv_features = [col for col in df.columns if col != 'Label']
print(f"✓ CSV has {len(csv_features)} features (excluding Label)")

# Step 2: Get features from Kafka (what engine produces)
print("\n📡 Step 2: Reading from Kafka to see engine features...")
try:
    consumer = KafkaConsumer(
        'ml-features',
        bootstrap_servers='localhost:9092',
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest',
        consumer_timeout_ms=5000
    )
    
    engine_features = None
    for message in consumer:
        engine_features = list(message.value['features'].keys())
        break
    
    consumer.close()
    
    if engine_features:
        print(f"✓ Engine extracts {len(engine_features)} features")
    else:
        print("✗ No messages in Kafka yet")
        exit(1)
        
except Exception as e:
    print(f"✗ Failed to read from Kafka: {e}")
    exit(1)

# Step 3: Compare
print("\n🔍 Step 3: Comparing feature sets...")

# Features in CSV but NOT in engine
missing_in_engine = set(csv_features) - set(engine_features)
if missing_in_engine:
    print(f"\n❌ Features in CSV but NOT in engine ({len(missing_in_engine)}):")
    for feat in sorted(missing_in_engine):
        print(f"   - {feat}")
else:
    print("\n✓ All CSV features are in engine")

# Features in engine but NOT in CSV
extra_in_engine = set(engine_features) - set(csv_features)
if extra_in_engine:
    print(f"\n➕ Features in engine but NOT in CSV ({len(extra_in_engine)}):")
    for feat in sorted(extra_in_engine):
        print(f"   - {feat}")
else:
    print("\n✓ No extra features in engine")

# Step 4: Check what training script drops
print("\n🧹 Step 4: Simulating training preprocessing...")

# Drop Label
data = df.copy()
if 'Label' in data.columns:
    data = data.drop('Label', axis=1)
    print(f"✓ Dropped 'Label': {len(data.columns)} features remain")

# Drop zero-variance columns
num_unique = data.nunique()
zero_var = num_unique[num_unique == 1]
if len(zero_var) > 0:
    print(f"\n📉 Zero-variance columns ({len(zero_var)}):")
    for col in zero_var.index:
        print(f"   - {col}")
    data = data[[col for col in data.columns if col not in zero_var.index]]
    print(f"✓ After removing zero-variance: {len(data.columns)} features")

# Drop duplicate columns
if 'Fwd Header Length.1' in data.columns:
    data = data.drop('Fwd Header Length.1', axis=1)
    print(f"✓ Dropped 'Fwd Header Length.1': {len(data.columns)} features")

training_features = list(data.columns)
print(f"\n✅ After preprocessing: {len(training_features)} features for training")

# Step 5: Final comparison
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"CSV original:         {len(csv_features)} features")
print(f"Training preprocessed: {len(training_features)} features")
print(f"Engine extracts:      {len(engine_features)} features")
print(f"Models expect:        69 features (from scaler)")

# What needs to be fixed?
print("\n🔧 REQUIRED FIXES:")

if len(engine_features) != len(training_features):
    print(f"\n1. ❌ Feature count mismatch: engine={len(engine_features)}, training={len(training_features)}")
    
    # Which features are missing?
    missing = set(training_features) - set(engine_features)
    if missing:
        print(f"\n   Features in training but NOT in engine:")
        for feat in sorted(missing):
            print(f"   - {feat}")
    
    extra = set(engine_features) - set(training_features)
    if extra:
        print(f"\n   Features in engine but NOT in training:")
        for feat in sorted(extra):
            print(f"   - {feat}")
            
    print("\n   ✅ Solution: Retrain models with exact engine feature set")
    print("      OR: Update engine to extract exact training features")
else:
    print("✓ Feature counts match!")

# Save feature lists for reference
with open('/tmp/csv_features.txt', 'w') as f:
    f.write('\n'.join(sorted(csv_features)))
    
with open('/tmp/training_features.txt', 'w') as f:
    f.write('\n'.join(sorted(training_features)))
    
with open('/tmp/engine_features.txt', 'w') as f:
    f.write('\n'.join(sorted(engine_features)))

print("\n📝 Feature lists saved:")
print("   - /tmp/csv_features.txt")
print("   - /tmp/training_features.txt")
print("   - /tmp/engine_features.txt")
print("\n" + "=" * 80)
