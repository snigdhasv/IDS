#!/usr/bin/env python3
"""
Quick diagnostic to understand why model confidence is low
Tests model directly on CICIDS dataset to see expected confidence
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
from collections import Counter

# Paths
MODEL_PATH = "ML Models/random_forest_model_2017.joblib"
CICIDS_CSV = "dpdk_suricata_ml_pipeline/dataset/Wednesday-workingHours.pcap_ISCX.csv"

print("╔═══════════════════════════════════════════════════════════════╗")
print("║          Model Confidence Diagnostic                         ║")
print("╚═══════════════════════════════════════════════════════════════╝\n")

# Load model
print(f"Loading model: {MODEL_PATH}")
try:
    model = joblib.load(MODEL_PATH)
    print(f"✓ Model loaded: {type(model).__name__}")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    sys.exit(1)

# Load CICIDS dataset
print(f"\nLoading CICIDS dataset: {CICIDS_CSV}")
try:
    df = pd.read_csv(CICIDS_CSV, low_memory=False)
    print(f"✓ Loaded {len(df)} samples")
except Exception as e:
    print(f"❌ Error loading dataset: {e}")
    sys.exit(1)

# Check label distribution
print("\nLabel Distribution:")
label_counts = df['Label'].value_counts()
for label, count in label_counts.items():
    pct = (count / len(df)) * 100
    print(f"  {label:30s}: {count:8d} ({pct:5.2f}%)")

# Prepare features (remove label and metadata columns)
print("\nPreparing features...")
label_col = 'Label'
exclude_cols = ['Label', 'Flow ID', 'Source IP', 'Destination IP', 'Timestamp']
feature_cols = [col for col in df.columns if col not in exclude_cols]

X = df[feature_cols].copy()
y = df[label_col].copy()

print(f"✓ Features: {X.shape[1]} columns")
print(f"✓ Samples: {X.shape[0]} rows")

# Handle inf/nan
X.replace([np.inf, -np.inf], np.nan, inplace=True)
X.fillna(0, inplace=True)

# Check how many features model expects
try:
    n_features_expected = model.n_features_in_
    print(f"\n⚠️  Model expects: {n_features_expected} features")
    print(f"⚠️  Dataset has: {X.shape[1]} features")
    
    if X.shape[1] != n_features_expected:
        print(f"\n❌ FEATURE MISMATCH!")
        print(f"   This is why confidence is low!")
        print(f"   Model was trained on {n_features_expected} features")
        print(f"   But you're giving it {X.shape[1]} features")
        
        # Try to match features
        if X.shape[1] > n_features_expected:
            print(f"\n   Using first {n_features_expected} features...")
            X = X.iloc[:, :n_features_expected]
        else:
            print(f"\n   Padding with zeros to match...")
            padding = np.zeros((X.shape[0], n_features_expected - X.shape[1]))
            X = np.hstack([X.values, padding])
except AttributeError:
    print("⚠️  Cannot determine expected features from model")

# Test predictions on sample
print("\nTesting predictions on 100 random samples...")
sample_indices = np.random.choice(len(X), min(100, len(X)), replace=False)
X_sample = X.iloc[sample_indices] if hasattr(X, 'iloc') else X[sample_indices]
y_sample = y.iloc[sample_indices]

try:
    # Get predictions
    predictions = model.predict(X_sample)
    
    # Get probabilities
    if hasattr(model, 'predict_proba'):
        probabilities = model.predict_proba(X_sample)
        max_probs = probabilities.max(axis=1)
        
        print(f"\nConfidence Statistics:")
        print(f"  Mean confidence: {max_probs.mean():.2%}")
        print(f"  Min confidence:  {max_probs.min():.2%}")
        print(f"  Max confidence:  {max_probs.max():.2%}")
        print(f"  Median:          {np.median(max_probs):.2%}")
        
        # Confidence distribution
        print(f"\nConfidence Distribution:")
        low_conf = (max_probs < 0.5).sum()
        med_conf = ((max_probs >= 0.5) & (max_probs < 0.8)).sum()
        high_conf = (max_probs >= 0.8).sum()
        
        print(f"  Low (<50%):   {low_conf:3d} ({low_conf/len(max_probs)*100:5.1f}%)")
        print(f"  Medium (50-80%): {med_conf:3d} ({med_conf/len(max_probs)*100:5.1f}%)")
        print(f"  High (>80%):  {high_conf:3d} ({high_conf/len(max_probs)*100:5.1f}%)")
        
        if low_conf > len(max_probs) * 0.5:
            print("\n❌ PROBLEM: Most predictions have LOW confidence!")
            print("   This suggests:")
            print("   1. Feature mismatch (different features than training)")
            print("   2. Feature scaling issues (not normalized)")
            print("   3. Poor model quality")
    else:
        print("⚠️  Model doesn't support probability estimation")
    
    # Check accuracy
    correct = (predictions == y_sample.values).sum()
    accuracy = correct / len(predictions)
    print(f"\nAccuracy on sample: {accuracy:.2%}")
    
    if accuracy < 0.7:
        print("❌ LOW ACCURACY - Model not performing well")
    elif accuracy > 0.9:
        print("✓ HIGH ACCURACY - Model works well on this data")
    
except Exception as e:
    print(f"❌ Error during prediction: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("CONCLUSION:")
print("="*70)
print("If confidence is low (<50%) on the SAME dataset the model was trained on,")
print("there's a fundamental problem with:")
print("  • Feature extraction/mapping")
print("  • Feature preprocessing (scaling/normalization)")
print("  • Model quality itself")
print("\nTry testing with LightGBM 2018 or ensemble models!")
print("="*70)
