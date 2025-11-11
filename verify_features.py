#!/usr/bin/env python3
"""
Comprehensive Feature Verification Script

Checks:
1. What features the engine extracts
2. What features the models expect
3. Which features are selected
4. Which features are missing/mismatched
"""

import json
import sys
from kafka import KafkaConsumer
import joblib

print("=" * 80)
print("FEATURE VERIFICATION FOR HIGHEST CONFIDENCE")
print("=" * 80)

# Step 1: Get features from Kafka (what engine sends)
print("\n📡 Step 1: Checking features from Feature Engine...")
try:
    consumer = KafkaConsumer(
        'ml-features',
        bootstrap_servers='localhost:9092',
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest',
        consumer_timeout_ms=10000
    )
    
    engine_features = None
    sample_values = None
    for message in consumer:
        engine_features = list(message.value['features'].keys())
        sample_values = message.value['features']
        break
    
    consumer.close()
    
    if not engine_features:
        print("❌ No messages in Kafka! Start the feature engine first.")
        sys.exit(1)
        
    print(f"✓ Engine extracts {len(engine_features)} features")
    print("\nEngine features:")
    for i, feat in enumerate(sorted(engine_features), 1):
        val = sample_values.get(feat, 0)
        print(f"  {i:2d}. {feat:40s} = {val}")
    
except Exception as e:
    print(f"❌ Failed to read from Kafka: {e}")
    sys.exit(1)

# Step 2: Check what models expect
print(f"\n🤖 Step 2: Checking model requirements...")
try:
    model = joblib.load('/home/s-ujay/Programming/IDS/ML Models/random_forest_model_2017_raw.joblib')
    scaler = joblib.load('/home/s-ujay/Programming/IDS/ML Models/scaler_2017_raw.joblib')
    
    model_feature_count = model.n_features_in_
    scaler_feature_count = scaler.n_features_in_
    
    print(f"✓ Model expects: {model_feature_count} features")
    print(f"✓ Scaler expects: {scaler_feature_count} features")
    
    if model_feature_count != scaler_feature_count:
        print(f"⚠️  WARNING: Model and scaler expect different feature counts!")
        
except Exception as e:
    print(f"❌ Failed to load models: {e}")
    sys.exit(1)

# Step 3: Check what consumer selects
print(f"\n🎯 Step 3: Checking consumer feature selection...")
try:
    with open('/home/s-ujay/Programming/IDS/ML Models/model_features_69.json', 'r') as f:
        selected_features = json.load(f)
    
    print(f"✓ Consumer selects {len(selected_features)} features")
    print("\nSelected features:")
    for i, feat in enumerate(selected_features, 1):
        print(f"  {i:2d}. {feat}")
        
except Exception as e:
    print(f"❌ Failed to load selected features: {e}")
    sys.exit(1)

# Step 4: Analyze mismatches
print(f"\n🔍 Step 4: Analyzing feature matching...")

engine_set = set(engine_features)
selected_set = set(selected_features)

# Features in selected but NOT in engine (will default to 0.0)
missing_in_engine = selected_set - engine_set
if missing_in_engine:
    print(f"\n❌ CRITICAL: {len(missing_in_engine)} features needed by models but NOT extracted by engine:")
    for feat in sorted(missing_in_engine):
        print(f"   - {feat}")
    print("\n   These will be set to 0.0 → REDUCES PREDICTION ACCURACY!")
else:
    print("\n✓ All selected features are available from engine")

# Features in engine but NOT used
unused_in_engine = engine_set - selected_set
if unused_in_engine:
    print(f"\n⚠️  {len(unused_in_engine)} features extracted but NOT used:")
    for feat in sorted(unused_in_engine):
        print(f"   - {feat}")
    print("\n   These features are wasted (could improve accuracy if models trained with them)")
else:
    print("\n✓ All engine features are being used")

# Step 5: Feature count analysis
print(f"\n📊 Step 5: Feature Count Summary")
print(f"   Engine extracts:     {len(engine_features)} features")
print(f"   Consumer selects:    {len(selected_features)} features")
print(f"   Dummy padding added: +2 features (hardcoded zeros)")
print(f"   Final vector:        {len(selected_features) + 2} features")
print(f"   Model expects:       {model_feature_count} features")

if len(selected_features) + 2 == model_feature_count:
    print(f"\n✅ Feature counts match!")
else:
    print(f"\n❌ Feature count mismatch!")
    print(f"   Difference: {model_feature_count - (len(selected_features) + 2)} features")

# Step 6: Recommendations
print(f"\n💡 Recommendations for Highest Confidence:")

if missing_in_engine:
    print(f"\n1. 🔴 URGENT: Fix feature extraction")
    print(f"   The engine is missing {len(missing_in_engine)} critical features.")
    print(f"   These features default to 0.0, significantly reducing prediction accuracy.")
    print(f"\n   Missing features:")
    for feat in sorted(missing_in_engine):
        print(f"   - {feat}")
    print(f"\n   Action: Update realtime_feature_engine.py to extract these features.")

if len(selected_features) + 2 != model_feature_count:
    print(f"\n2. 🟡 Feature count mismatch")
    print(f"   Adding {2} dummy zeros as padding is a temporary workaround.")
    print(f"   For best accuracy, retrain models on exact {len(engine_features)} features.")

if unused_in_engine:
    print(f"\n3. 🟢 Optimize: {len(unused_in_engine)} unused features")
    print(f"   Engine extracts features that models don't use.")
    print(f"   Either:")
    print(f"   - Stop extracting unused features (save CPU)")
    print(f"   - Retrain models to use all features (better accuracy)")

if not missing_in_engine and len(selected_features) + 2 == model_feature_count:
    print(f"\n✅ Configuration is optimal!")
    print(f"   All required features are extracted and matched correctly.")
    print(f"   Predictions should have maximum confidence.")

print("\n" + "=" * 80)
