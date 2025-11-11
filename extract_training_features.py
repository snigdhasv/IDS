#!/usr/bin/env python3
"""
Extract the exact 69 features that models were trained on
"""

import pandas as pd
import numpy as np

# Load CSV and apply same preprocessing as training script
csv_path = "dataset/CICIDS2017_raw/Monday-WorkingHours.pcap_ISCX.csv"
print("Loading CSV to extract training features...")

df = pd.read_csv(csv_path, nrows=10000)

# Strip whitespace from column names (line 183 in training script)
df.columns = [col.strip() for col in df.columns]
print(f"After strip whitespace: {len(df.columns)} columns")

# Drop Label
if 'Label' in df.columns:
    df = df.drop('Label', axis=1)
    print(f"After drop Label: {len(df.columns)} columns")

# Drop zero-variance columns
num_unique = df.nunique()
zero_var = num_unique[num_unique == 1]
if len(zero_var) > 0:
    print(f"\nDropping {len(zero_var)} zero-variance columns:")
    for col in zero_var.index:
        print(f"  - {col}")
    df = df[[col for col in df.columns if col not in zero_var.index]]
    print(f"After drop zero-variance: {len(df.columns)} columns")

# Drop duplicate Fwd Header Length.1
if 'Fwd Header Length.1' in df.columns:
    df = df.drop('Fwd Header Length.1', axis=1)
    print(f"After drop duplicate: {len(df.columns)} columns")

# These are the features used for training
training_features = list(df.columns)

print(f"\n{'='*80}")
print(f"FINAL: {len(training_features)} features for training")
print(f"{'='*80}\n")

# Save to file
import json
with open('ML Models/model_features_69.json', 'w') as f:
    json.dump(training_features, f, indent=2)

print("✅ Saved feature list to: ML Models/model_features_69.json")

# Also print them
print("\nFeature list:")
for i, feat in enumerate(training_features, 1):
    print(f"{i:2d}. {feat}")
