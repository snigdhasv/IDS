#!/usr/bin/env python3
"""
Quick Model Retrainer for 65 CICIDS Features

Trains a new Random Forest model using the full 65-feature vectors
from the sidecar feature engine for higher confidence predictions.
"""

import sys
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

# Model configuration optimized for real-time inference
MODEL_CONFIG = {
    'n_estimators': 50,       # Fewer trees for faster inference
    'max_depth': 10,          # Reasonable depth
    'min_samples_split': 5,
    'min_samples_leaf': 2,
    'max_features': 'sqrt',   # Speed optimization
    'n_jobs': -1,             # Use all CPUs
    'random_state': 42
}

def load_cicids_data(csv_path: str) -> tuple:
    """Load CICIDS dataset with exact 65 features matching the feature engine"""
    print(f"📂 Loading data from {csv_path}...")
    
    df = pd.read_csv(csv_path)
    print(f"   Raw shape: {df.shape}")
    
    # Clean column names (remove leading/trailing spaces)
    df.columns = df.columns.str.strip()
    
    # Exact 65 features that the feature engine produces (from extract_features method)
    CICIDS_65_FEATURES = [
        'Destination Port', 'Flow Duration', 'Total Fwd Packets', 'Total Backward Packets',
        'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
        'Fwd Packet Length Max', 'Fwd Packet Length Min', 'Fwd Packet Length Mean', 'Fwd Packet Length Std',
        'Bwd Packet Length Max', 'Bwd Packet Length Min', 'Bwd Packet Length Mean', 'Bwd Packet Length Std',
        'Flow Bytes/s', 'Flow Packets/s', 'Fwd Packets/s', 'Bwd Packets/s',
        'Flow IAT Mean', 'Flow IAT Std', 'Flow IAT Max', 'Flow IAT Min',
        'Fwd IAT Total', 'Fwd IAT Mean', 'Fwd IAT Std', 'Fwd IAT Max', 'Fwd IAT Min',
        'Bwd IAT Total', 'Bwd IAT Mean', 'Bwd IAT Std', 'Bwd IAT Max', 'Bwd IAT Min',
        'Fwd PSH Flags', 'Fwd URG Flags', 'Fwd Header Length', 'Bwd Header Length',
        'Min Packet Length', 'Max Packet Length', 'Packet Length Mean', 'Packet Length Std', 'Packet Length Variance',
        'FIN Flag Count', 'SYN Flag Count', 'RST Flag Count', 'PSH Flag Count', 'ACK Flag Count', 'URG Flag Count', 'ECE Flag Count',
        'Down/Up Ratio', 'Average Packet Size', 'Avg Fwd Segment Size', 'Avg Bwd Segment Size',
        'Subflow Fwd Bytes', 'Subflow Bwd Bytes',
        'Init_Win_bytes_forward', 'Init_Win_bytes_backward',
        'act_data_pkt_fwd', 'min_seg_size_forward',
        'Active Mean', 'Active Std', 'Active Max', 'Active Min',
        'Idle Mean', 'Idle Std', 'Idle Max', 'Idle Min'
    ]
    
    # Get label column
    label_col = None
    for col in ['Label', 'Attack Type']:
        if col in df.columns:
            label_col = col
            break
    
    if not label_col:
        raise ValueError(f"No label column found. Available columns: {list(df.columns)[:10]}")
    
    # Select only the 65 features that match our feature engine
    available_features = [f for f in CICIDS_65_FEATURES if f in df.columns]
    missing_features = [f for f in CICIDS_65_FEATURES if f not in df.columns]
    
    if missing_features:
        print(f"   ⚠️  Missing {len(missing_features)} features: {missing_features[:3]}...")
    
    print(f"   ✓ Using {len(available_features)}/65 features that match feature engine")
    
    X = df[available_features].copy()
    y = df[label_col].copy()
    
    print(f"   Features: {X.shape[1]}")
    print(f"   Samples: {X.shape[0]}")
    print(f"   Classes: {y.nunique()}")
    
    # Clean data
    print(f"\n🧹 Cleaning data...")
    
    # Replace infinity with NaN
    X = X.replace([np.inf, -np.inf], np.nan)
    
    # Fill NaN with median for each column
    for col in X.columns:
        if X[col].isna().any():
            median = X[col].median()
            X[col] = X[col].fillna(median)
    
    # Handle any remaining NaN (fill with 0)
    X = X.fillna(0)
    
    print(f"   ✓ Data cleaned")
    
    return X, y

def train_model(X_train, y_train, X_test, y_test):
    """Train Random Forest model"""
    print(f"\n🎯 Training Random Forest...")
    print(f"   Config: {MODEL_CONFIG}")
    
    model = RandomForestClassifier(**MODEL_CONFIG)
    model.fit(X_train, y_train)
    
    # Evaluate
    print(f"\n📊 Evaluating...")
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"   Accuracy: {accuracy:.4f}")
    print(f"\n{classification_report(y_test, y_pred)}")
    
    return model

def main():
    """Main training pipeline"""
    print("╔═══════════════════════════════════════════════════════╗")
    print("║   Quick Model Retrainer for Real-time IDS            ║")
    print("║   Trains on Full 65 CICIDS Features                  ║")
    print("╚═══════════════════════════════════════════════════════╝\n")
    
    if len(sys.argv) < 2:
        print("Usage: python3 retrain_model.py <cicids_csv_path> [output_path]")
        print("\nExample:")
        print("  python3 retrain_model.py dpdk_suricata_ml_pipeline/dataset/Wednesday-workingHours.pcap_ISCX.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "random_forest_65features.joblib"
    
    # Load data
    X, y = load_cicids_data(csv_path)
    
    # Split
    print(f"\n✂️  Splitting data (75% train, 25% test)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    
    # Train
    model = train_model(X_train, y_train, X_test, y_test)
    
    # Save
    print(f"\n💾 Saving model to {output_path}...")
    joblib.dump(model, output_path)
    
    print(f"\n✅ Done! Model saved with {model.n_features_in_} features")
    print(f"\n🚀 To use in real-time pipeline:")
    print(f"   sudo ./run_realtime_engine.sh stop")
    print(f"   # Update MODEL_PATH in realtime_ml_consumer.py to: {Path(output_path).absolute()}")
    print(f"   sudo ./run_realtime_engine.sh start")

if __name__ == '__main__':
    main()
