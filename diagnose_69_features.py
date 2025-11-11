#!/usr/bin/env python3
"""Find the exact 69 features by processing CSV like training does"""

import pandas as pd
import numpy as np
from imblearn.over_sampling import SMOTE

csv_path = "dataset/CICIDS2017_raw/Monday-WorkingHours.pcap_ISCX.csv"
print(f"Loading {csv_path}...")
df = pd.read_csv(csv_path, nrows=10000)

print(f"1. Original: {len(df.columns)} columns")

# Strip whitespace
df.columns = [col.strip() for col in df.columns]
print(f"2. After strip: {len(df.columns)} columns")

# Drop Label
if 'Label' in df.columns:
    df = df.drop('Label', axis=1)
print(f"3. After drop Label: {len(df.columns)} columns")

# Drop zero-variance
num_unique = df.nunique()
zero_var = num_unique[num_unique == 1]
if len(zero_var) > 0:
    print(f"\n   Zero-variance columns: {list(zero_var.index)}")
    df = df[[col for col in df.columns if col not in zero_var.index]]
print(f"4. After drop zero-var: {len(df.columns)} columns")

# Drop duplicate
if 'Fwd Header Length.1' in df.columns:
    df = df.drop('Fwd Header Length.1', axis=1)
print(f"5. After drop duplicate: {len(df.columns)} columns")

# Add Attack Type column
df['Attack Type'] = 'BENIGN'

# Try SMOTE
print("\n6. Applying SMOTE (might add features?)...")
X = df.drop('Attack Type', axis=1)
y = df['Attack Type']

print(f"   Before SMOTE: {X.shape[1]} features")

# This will fail for single class, but let's see
try:
    # Add a fake attack sample to allow SMOTE
    fake_attack = X.iloc[0].copy()
    X = pd.concat([X, pd.DataFrame([fake_attack])], ignore_index=True)
    y = pd.concat([y, pd.Series(['DOS'])], ignore_index=True)
    
    smote = SMOTE(sampling_strategy='auto', random_state=0)
    X_upsampled, y_upsampled = smote.fit_resample(X, y)
    
    print(f"   After SMOTE: {X_upsampled.shape[1]} features")
    
    if X_upsampled.shape[1] != X.shape[1]:
        print(f"\n⚠️  SMOTE changed feature count!")
    
except Exception as e:
    print(f"   SMOTE failed: {e}")

print(f"\n7. Final feature list ({len(X.columns)} features):")
for i, col in enumerate(X.columns, 1):
    print(f"   {i:2d}. {col}")

# Save
import json
with open('/tmp/actual_training_features.json', 'w') as f:
    json.dump(list(X.columns), f, indent=2)
    
print(f"\n✅ Saved to /tmp/actual_training_features.json")
