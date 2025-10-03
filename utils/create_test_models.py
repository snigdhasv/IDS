#!/usr/bin/env python3
"""
Create compatible test models for ensemble testing

This script creates simple Random Forest and LightGBM models that are compatible
with the current environment, allowing us to test the ensemble pipeline.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
import lightgbm as lgb
import joblib
import os

def create_test_models():
    """Create compatible test models for ensemble testing"""
    print("🔨 Creating compatible test models...")
    
    # Create synthetic data that mimics network traffic features
    # 34 features to match the expected input
    n_samples = 1000
    n_features = 34
    
    # Create synthetic classification data
    X, y = make_classification(
        n_samples=n_samples,
        n_features=n_features,
        n_informative=20,
        n_redundant=8,
        n_clusters_per_class=2,
        n_classes=7,  # 7 classes for RF (BENIGN, DoS, DDoS, RECONNAISSANCE, BRUTE_FORCE, BOTNET, WEB_ATTACK)
        random_state=42
    )
    
    # Create class labels that match what the ensemble expects
    rf_class_names = ['BENIGN', 'Bot', 'Brute Force', 'DDoS', 'DoS', 'Port Scan', 'Web Attack']
    lgb_class_names = ['BENIGN', 'Bot', 'DDoS', 'DoS', 'Web Attack']  # 5 classes for LGB
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("📊 Creating Random Forest model (7 classes)...")
    # Create and train Random Forest model
    rf_model = RandomForestClassifier(
        n_estimators=50,  # Smaller for speed
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    
    # Map y_train to class names for proper training
    y_train_mapped = np.array([rf_class_names[i] for i in y_train])
    rf_model.fit(X_train, y_train_mapped)
    
    print("🔍 Creating LightGBM model (5 classes)...")
    # Create synthetic data for LGB with 5 classes
    y_lgb = y % 5  # Map to 5 classes
    X_train_lgb, X_test_lgb, y_train_lgb, y_test_lgb = train_test_split(X, y_lgb, test_size=0.2, random_state=42)
    
    # Create and train LightGBM model
    lgb_model = lgb.LGBMClassifier(
        n_estimators=50,
        max_depth=10,
        random_state=42,
        verbose=-1  # Suppress output
    )
    
    # Map y_train_lgb to class names for proper training
    y_train_lgb_mapped = np.array([lgb_class_names[i] for i in y_train_lgb])
    lgb_model.fit(X_train_lgb, y_train_lgb_mapped)
    
    # Create ML Models directory if it doesn't exist
    os.makedirs('/home/ifscr/SE_02_2025/IDS/ML Models', exist_ok=True)
    
    # Save models
    rf_path = '/home/ifscr/SE_02_2025/IDS/ML Models/random_forest_model_2017.joblib'
    lgb_path = '/home/ifscr/SE_02_2025/IDS/ML Models/lgb_model_2018.joblib'
    
    print("💾 Saving models...")
    joblib.dump(rf_model, rf_path)
    joblib.dump(lgb_model, lgb_path)
    
    print(f"✅ Random Forest model saved to: {rf_path}")
    print(f"✅ LightGBM model saved to: {lgb_path}")
    
    # Test loading the models
    print("\n🧪 Testing model loading...")
    try:
        rf_loaded = joblib.load(rf_path)
        lgb_loaded = joblib.load(lgb_path)
        
        print(f"📊 RF classes: {rf_loaded.classes_}")
        print(f"📊 LGB classes: {lgb_loaded.classes_}")
        print(f"📊 RF features: {rf_loaded.n_features_in_}")
        print(f"📊 LGB features: {lgb_loaded.n_features_in_}")
        
        # Test predictions
        test_sample = X_test[:1]
        rf_pred = rf_loaded.predict(test_sample)
        lgb_pred = lgb_loaded.predict(test_sample)
        
        print(f"🎯 RF prediction: {rf_pred[0]}")
        print(f"🎯 LGB prediction: {lgb_pred[0]}")
        
        print("✅ Models created and tested successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing models: {e}")
        return False

if __name__ == "__main__":
    create_test_models()