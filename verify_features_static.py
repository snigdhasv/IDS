#!/usr/bin/env python3
"""
Static feature verification - compares feature engine code vs consumer selection
"""

import re

print("=" * 80)
print("STATIC FEATURE VERIFICATION")
print("=" * 80)

# Parse features from feature engine extract_features() method
print("\n📊 Step 1: Parsing features from realtime_feature_engine.py...")
with open('dpdk_suricata_ml_pipeline/src/realtime_feature_engine.py', 'r') as f:
    content = f.read()

# Find all features['...'] = ... lines
engine_features = []
for match in re.finditer(r"features\['([^']+)'\]\s*=", content):
    feature_name = match.group(1)
    engine_features.append(feature_name)

# Remove duplicates while preserving order
seen = set()
engine_features_unique = []
for feat in engine_features:
    if feat not in seen:
        seen.add(feat)
        engine_features_unique.append(feat)

print(f"✓ Found {len(engine_features_unique)} unique features in engine")

# Load selected features from consumer
print("\n📊 Step 2: Loading selected features from consumer...")
import json
with open('ML Models/model_features_69.json', 'r') as f:
    selected_features = json.load(f)

print(f"✓ Consumer selects {len(selected_features)} features")

# Load model requirements
print("\n📊 Step 3: Checking model requirements...")
import joblib
model = joblib.load('ML Models/random_forest_model_2017_raw.joblib')
scaler = joblib.load('ML Models/scaler_2017_raw.joblib')

print(f"✓ Model expects: {model.n_features_in_} features")
print(f"✓ Scaler expects: {scaler.n_features_in_} features")

# Analysis
print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)

engine_set = set(engine_features_unique)
selected_set = set(selected_features)

# Critical: features needed but not extracted
missing = selected_set - engine_set
if missing:
    print(f"\n❌ CRITICAL: {len(missing)} features MISSING from engine:")
    for i, feat in enumerate(sorted(missing), 1):
        print(f"   {i}. {feat}")
    print(f"\n   Impact: These will be 0.0 → REDUCED ACCURACY!")
else:
    print(f"\n✅ All {len(selected_features)} selected features are extracted by engine")

# Wasted features
unused = engine_set - selected_set  
if unused:
    print(f"\n⚠️  {len(unused)} features EXTRACTED but NOT USED:")
    for i, feat in enumerate(sorted(unused), 1):
        print(f"   {i}. {feat}")
    print(f"\n   These could improve accuracy if models were trained with them")

# Feature counts
print(f"\n📊 Feature Count Analysis:")
print(f"   Engine extracts:  {len(engine_features_unique)} features")
print(f"   Consumer selects: {len(selected_features)} features")  
print(f"   Padding added:    +2 features (zeros)")
print(f"   Final vector:     {len(selected_features) + 2} features")
print(f"   Model expects:    {model.n_features_in_} features")

gap = model.n_features_in_ - (len(selected_features) + 2)
if gap == 0:
    print(f"\n✅ Perfect match!")
else:
    print(f"\n❌ Mismatch: {gap} feature difference")

# Detailed feature comparison
print(f"\n📋 Detailed Feature List:")
print(f"\n{'Feature Name':<50} {'Engine':<10} {'Selected':<10}")
print("-" * 70)

all_features = sorted(engine_set | selected_set)
for feat in all_features:
    in_engine = "✓" if feat in engine_set else "✗"
    in_selected = "✓" if feat in selected_set else "✗"
    
    status = ""
    if feat in missing:
        status = " ← MISSING!"
    elif feat in unused:
        status = " (unused)"
        
    print(f"{feat:<50} {in_engine:<10} {in_selected:<10}{status}")

print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)

if missing:
    print(f"\n🔴 HIGH PRIORITY: Add missing features to engine")
    print(f"   File: dpdk_suricata_ml_pipeline/src/realtime_feature_engine.py")
    print(f"   Missing: {', '.join(sorted(missing))}")
elif gap != 0:
    print(f"\n🟡 MEDIUM: Retrain models with exact {len(engine_features_unique)} features")
    print(f"   Or: Find the {abs(gap)} missing features")
else:
    print(f"\n✅ Configuration is OPTIMAL for highest confidence!")
    
print("=" * 80)
