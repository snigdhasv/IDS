#!/usr/bin/env python3
"""
Retrain CICIDS models WITHOUT PCA - using raw 78 features
This matches the real-time feature extraction exactly.
"""

import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import StandardScaler
import sys

def load_and_prepare_data(csv_path):
    """Load CICIDS CSV with raw features (no PCA)"""
    print(f"📂 Loading {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    # Drop metadata columns
    drop_cols = ['Flow ID', 'Source IP', 'Source Port', 'Destination IP', 'Protocol', 'Timestamp']
    df = df.drop(drop_cols, axis=1, errors='ignore')
    
    # Get features and labels
    if 'Label' in df.columns:
        X = df.drop('Label', axis=1)
        y = df['Label']
    elif 'Attack Type' in df.columns:
        X = df.drop('Attack Type', axis=1)
        y = df['Attack Type']
    else:
        raise ValueError("No label column found!")
    
    # Clean data
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0)
    
    print(f"✓ Loaded: {X.shape[0]:,} samples, {X.shape[1]} features")
    print(f"✓ Classes: {y.nunique()}")
    print(f"\nClass distribution:")
    for cls, count in y.value_counts().head(10).items():
        print(f"  {cls}: {count:,}")
    
    return X, y

def train_all_models(X_train, X_test, y_train, y_test):
    """Train all 5 models"""
    models = {}
    
    # 1. Random Forest
    print("\n🌲 Training Random Forest...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_acc = accuracy_score(y_test, rf_pred)
    print(f"   Accuracy: {rf_acc:.4f}")
    models['random_forest'] = rf
    
    # 2. Decision Tree
    print("\n🌳 Training Decision Tree...")
    dt = DecisionTreeClassifier(max_depth=15, random_state=42)
    dt.fit(X_train, y_train)
    dt_pred = dt.predict(X_test)
    dt_acc = accuracy_score(y_test, dt_pred)
    print(f"   Accuracy: {dt_acc:.4f}")
    models['decision_tree'] = dt
    
    # 3. LightGBM
    print("\n💡 Training LightGBM...")
    lgbm = lgb.LGBMClassifier(n_estimators=100, max_depth=10, learning_rate=0.1, n_jobs=-1, random_state=42)
    lgbm.fit(X_train, y_train)
    lgbm_pred = lgbm.predict(X_test)
    lgbm_acc = accuracy_score(y_test, lgbm_pred)
    print(f"   Accuracy: {lgbm_acc:.4f}")
    models['lgb'] = lgbm
    
    # 4. KNN (smaller n_neighbors for speed)
    print("\n👥 Training KNN...")
    knn = KNeighborsClassifier(n_neighbors=5, n_jobs=-1)
    knn.fit(X_train, y_train)
    knn_pred = knn.predict(X_test)
    knn_acc = accuracy_score(y_test, knn_pred)
    print(f"   Accuracy: {knn_acc:.4f}")
    models['knn'] = knn
    
    # 5. Logistic Regression
    print("\n📈 Training Logistic Regression...")
    lr = LogisticRegression(multi_class='multinomial', solver='saga', max_iter=500, n_jobs=-1, random_state=42)
    lr.fit(X_train, y_train)
    lr_pred = lr.predict(X_test)
    lr_acc = accuracy_score(y_test, lr_pred)
    print(f"   Accuracy: {lr_acc:.4f}")
    models['lr'] = lr
    
    return models

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 retrain_models_no_pca.py <cicids_csv_path>")
        print("\nExample:")
        print("  python3 retrain_models_no_pca.py dpdk_suricata_ml_pipeline/dataset/Wednesday-workingHours.pcap_ISCX.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    
    print("╔═══════════════════════════════════════════════════════╗")
    print("║   Retrain Models WITHOUT PCA (Raw 78 Features)       ║")
    print("╚═══════════════════════════════════════════════════════╝\n")
    
    # Load data
    X, y = load_and_prepare_data(csv_path)
    
    # Split data
    print("\n✂️  Splitting data (75% train, 25% test)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
    print(f"   Train: {X_train.shape[0]:,} samples")
    print(f"   Test:  {X_test.shape[0]:,} samples")
    
    # Train models
    models = train_all_models(X_train, X_test, y_train, y_test)
    
    # Save models
    print("\n💾 Saving models...")
    output_dir = "ML Models"
    
    for name, model in models.items():
        filename = f"{output_dir}/{name}_model_2017_raw.joblib"
        joblib.dump(model, filename)
        print(f"   ✓ Saved: {filename}")
    
    print("\n✅ Done! Models trained on raw features (no PCA)")
    print("\n🚀 To use in real-time:")
    print("   1. Update ENSEMBLE_MODELS in realtime_ensemble_consumer.py")
    print("   2. Remove feature_selector.py usage (use raw features)")
    print("   3. Restart: sudo ./run_realtime_engine.sh restart")

if __name__ == '__main__':
    main()
