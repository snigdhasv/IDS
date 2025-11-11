#!/usr/bin/env python3
"""
Retrain CICIDS2017 Models WITHOUT PCA - Using All Raw Features
Based on CICIDS2017.ipynb but trains on full 65 features to match real-time extraction
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
import lightgbm as lgb
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
import joblib
import gc
import os
import time
from typing import List

# Configuration
CSV_FOLDER = 'dataset/CICIDS2017_raw'  # Put your CSV files here
OUTPUT_DIR = 'ML Models'
MIN_CLASS_SAMPLES = 1950  # Minimum samples per class to include
MAX_CLASS_SAMPLES = 5000  # Max samples per class after downsampling
TEST_SIZE = 0.25
RANDOM_STATE = 0

# Feature mapping from engine format to CSV format (if needed)
FEATURE_MAPPING = {
    'Destination Port': 'Dst Port',
    'Flow Duration': 'Flow Duration',
    'Total Fwd Packets': 'Tot Fwd Pkts',
    'Total Backward Packets': 'Tot Bwd Pkts',
    'Total Length of Fwd Packets': 'TotLen Fwd Pkts',
    'Total Length of Bwd Packets': 'TotLen Bwd Pkts',
    'Fwd Packet Length Max': 'Fwd Pkt Len Max',
    'Fwd Packet Length Min': 'Fwd Pkt Len Min',
    'Fwd Packet Length Mean': 'Fwd Pkt Len Mean',
    'Fwd Packet Length Std': 'Fwd Pkt Len Std',
    'Bwd Packet Length Max': 'Bwd Pkt Len Max',
    'Bwd Packet Length Min': 'Bwd Pkt Len Min',
    'Bwd Packet Length Mean': 'Bwd Pkt Len Mean',
    'Bwd Packet Length Std': 'Bwd Pkt Len Std',
    'Flow Bytes/s': 'Flow Byts/s',
    'Flow Packets/s': 'Flow Pkts/s',
    'Flow IAT Mean': 'Flow IAT Mean',
    'Flow IAT Std': 'Flow IAT Std',
    'Flow IAT Max': 'Flow IAT Max',
    'Flow IAT Min': 'Flow IAT Min',
    'Fwd IAT Total': 'Fwd IAT Tot',
    'Fwd IAT Mean': 'Fwd IAT Mean',
    'Fwd IAT Std': 'Fwd IAT Std',
    'Fwd IAT Max': 'Fwd IAT Max',
    'Fwd IAT Min': 'Fwd IAT Min',
    'Bwd IAT Total': 'Bwd IAT Tot',
    'Bwd IAT Mean': 'Bwd IAT Mean',
    'Bwd IAT Std': 'Bwd IAT Std',
    'Bwd IAT Max': 'Bwd IAT Max',
    'Bwd IAT Min': 'Bwd IAT Min',
    'Fwd PSH Flags': 'Fwd PSH Flags',
    'Fwd URG Flags': 'Fwd URG Flags',
    'Fwd Header Length': 'Fwd Header Len',
    'Bwd Header Length': 'Bwd Header Len',
    'Fwd Packets/s': 'Fwd Pkts/s',
    'Bwd Packets/s': 'Bwd Pkts/s',
    'Min Packet Length': 'Pkt Len Min',
    'Max Packet Length': 'Pkt Len Max',
    'Packet Length Mean': 'Pkt Len Mean',
    'Packet Length Std': 'Pkt Len Std',
    'Packet Length Variance': 'Pkt Len Var',
    'FIN Flag Count': 'FIN Flag Cnt',
    'SYN Flag Count': 'SYN Flag Cnt',
    'RST Flag Count': 'RST Flag Cnt',
    'PSH Flag Count': 'PSH Flag Cnt',
    'ACK Flag Count': 'ACK Flag Cnt',
    'URG Flag Count': 'URG Flag Cnt',
    'CWE Flag Count': 'CWE Flag Count',
    'ECE Flag Count': 'ECE Flag Cnt',
    'Down/Up Ratio': 'Down/Up Ratio',
    'Average Packet Size': 'Pkt Size Avg',
    'Avg Fwd Segment Size': 'Fwd Seg Size Avg',
    'Avg Bwd Segment Size': 'Bwd Seg Size Avg',
    'Subflow Fwd Packets': 'Subflow Fwd Pkts',
    'Subflow Fwd Bytes': 'Subflow Fwd Byts',
    'Subflow Bwd Packets': 'Subflow Bwd Pkts',
    'Subflow Bwd Bytes': 'Subflow Bwd Byts',
    'Init_Win_bytes_forward': 'Init Fwd Win Byts',
    'Init_Win_bytes_backward': 'Init Bwd Win Byts',
    'act_data_pkt_fwd': 'Fwd Act Data Pkts',
    'min_seg_size_forward': 'Fwd Seg Size Min',
    'Active Mean': 'Active Mean',
    'Active Std': 'Active Std',
    'Active Max': 'Active Max',
    'Active Min': 'Active Min',
    'Idle Mean': 'Idle Mean',
    'Idle Std': 'Idle Std',
    'Idle Max': 'Idle Max',
    'Idle Min': 'Idle Min',
}

# Attack type mapping
ATTACK_MAP = {
    'BENIGN': 'BENIGN',
    'DDoS': 'DDoS',
    'DoS Hulk': 'DoS',
    'DoS GoldenEye': 'DoS',
    'DoS slowloris': 'DoS',
    'DoS Slowhttptest': 'DoS',
    'PortScan': 'Port Scan',
    'FTP-Patator': 'Brute Force',
    'SSH-Patator': 'Brute Force',
    'Bot': 'Bot',
    'Web Attack – Brute Force': 'Web Attack',
    'Web Attack – XSS': 'Web Attack',
    'Web Attack – Sql Injection': 'Web Attack',
    'Infiltration': 'Infiltration',
    'Heartbleed': 'Heartbleed'
}


def load_cicids_data(folder_path: str, chunksize: int = 100000) -> pd.DataFrame:
    """
    Load CICIDS2017 dataset in a memory-efficient manner.
    """
    combined_df = None
    
    print(f"Loading CSV files from: {folder_path}")
    
    for dirname, _, filenames in os.walk(folder_path):
        csv_files = [f for f in filenames if f.endswith('.csv')]
        
        if not csv_files:
            print(f"⚠️  No CSV files found in {folder_path}")
            continue
            
        for filename in csv_files:
            file_path = os.path.join(dirname, filename)
            
            # Get total rows
            total_rows = sum(1 for _ in open(file_path)) - 1
            print(f"\n📂 Processing {filename} ({total_rows:,} rows)")
            
            # Read file in chunks
            chunk_iterator = pd.read_csv(
                file_path,
                chunksize=chunksize,
                low_memory=True
            )
            
            for i, chunk in enumerate(chunk_iterator):
                if combined_df is None:
                    combined_df = chunk
                else:
                    combined_df = pd.concat([combined_df, chunk], ignore_index=True)
                
                rows_processed = min((i + 1) * chunksize, total_rows)
                print(f"Progress: {rows_processed:,}/{total_rows:,} rows", end='\r')
                
                gc.collect()
            
            print(f"\n✅ Completed {filename}")
    
    return combined_df


def preprocess_data(data: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess the dataset following CICIDS2017.ipynb workflow.
    """
    print("\n" + "="*60)
    print("PREPROCESSING DATA")
    print("="*60)
    
    print(f"\n📊 Initial shape: {data.shape}")
    print(f"💾 Initial memory: {data.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    
    # Strip whitespace from column names
    data.rename(columns={col: col.strip() for col in data.columns}, inplace=True)
    
    # Optimize dtypes
    print("\n🔧 Optimizing data types...")
    for col in data.columns:
        if data[col].dtype == 'float64':
            data[col] = data[col].astype('float32')
        elif data[col].dtype == 'int64':
            data[col] = data[col].astype('int32')
    
    print(f"💾 Optimized memory: {data.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    
    # Remove duplicates
    print("\n🗑️  Removing duplicates...")
    before = len(data)
    data = data.drop_duplicates(keep='first')
    after = len(data)
    print(f"   Removed {before - after:,} duplicates ({(before-after)/before*100:.2f}%)")
    
    # Handle missing values
    print("\n🔍 Handling missing values...")
    print(f"   Initial missing values: {data.isna().sum().sum()}")
    
    # Replace infinities with NaN
    data.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    # Fill Flow Bytes/s and Flow Packets/s with median
    if 'Flow Bytes/s' in data.columns:
        med = data['Flow Bytes/s'].median()
        data['Flow Bytes/s'].fillna(med, inplace=True)
        print(f"   Filled 'Flow Bytes/s' with median: {med:.2f}")
    
    if 'Flow Packets/s' in data.columns:
        med = data['Flow Packets/s'].median()
        data['Flow Packets/s'].fillna(med, inplace=True)
        print(f"   Filled 'Flow Packets/s' with median: {med:.2f}")
    
    print(f"   Final missing values: {data.isna().sum().sum()}")
    
    # Map attack types
    print("\n🏷️  Mapping attack types...")
    if 'Label' in data.columns:
        data['Attack Type'] = data['Label'].map(ATTACK_MAP)
        data.drop('Label', axis=1, inplace=True)
        print(f"   Attack types mapped:")
        print(data['Attack Type'].value_counts())
    
    # Drop columns with zero variance
    print("\n📉 Removing zero-variance columns...")
    num_unique = data.nunique()
    zero_var = num_unique[num_unique == 1]
    if len(zero_var) > 0:
        print(f"   Dropping {len(zero_var)} columns with single value:")
        for col in zero_var.index:
            print(f"     - {col}")
        data = data[[col for col in data.columns if col not in zero_var.index]]
    
    # Drop duplicate columns (e.g., Fwd Header Length.1)
    if 'Fwd Header Length.1' in data.columns:
        data.drop('Fwd Header Length.1', axis=1, inplace=True)
        print("   Dropped duplicate column: 'Fwd Header Length.1'")
    
    # Rename columns to match feature selector format
    print("\n📝 Renaming columns to match engine format...")
    data.rename(columns=FEATURE_MAPPING, inplace=True)
    
    print(f"\n✅ Preprocessing complete!")
    print(f"   Final shape: {data.shape}")
    print(f"   Features: {data.shape[1] - 1}")  # Exclude 'Attack Type'
    print(f"   Samples: {data.shape[0]:,}")
    
    return data


def balance_dataset(data: pd.DataFrame) -> pd.DataFrame:
    """
    Balance the dataset using downsampling + SMOTE.
    """
    print("\n" + "="*60)
    print("BALANCING DATASET")
    print("="*60)
    
    print(f"\n📊 Original class distribution:")
    class_counts = data['Attack Type'].value_counts()
    print(class_counts)
    
    # Select classes with sufficient samples
    selected_classes = class_counts[class_counts > MIN_CLASS_SAMPLES]
    class_names = selected_classes.index
    print(f"\n✅ Selected {len(class_names)} classes with >{MIN_CLASS_SAMPLES} samples")
    
    selected = data[data['Attack Type'].isin(class_names)]
    
    # Downsample large classes
    print(f"\n⬇️  Downsampling classes with >{MAX_CLASS_SAMPLES} samples...")
    dfs = []
    for name in class_names:
        df = selected[selected['Attack Type'] == name]
        if len(df) > MAX_CLASS_SAMPLES:
            df = df.sample(n=MAX_CLASS_SAMPLES, random_state=RANDOM_STATE)
            print(f"   {name}: {len(selected[selected['Attack Type'] == name]):,} → {len(df):,}")
        dfs.append(df)
    
    df = pd.concat(dfs, ignore_index=True)
    
    print(f"\n📊 After downsampling:")
    print(df['Attack Type'].value_counts())
    
    # Apply SMOTE for upsampling minority classes
    print(f"\n⬆️  Applying SMOTE for upsampling...")
    X = df.drop('Attack Type', axis=1)
    y = df['Attack Type']
    
    smote = SMOTE(sampling_strategy='auto', random_state=RANDOM_STATE)
    X_upsampled, y_upsampled = smote.fit_resample(X, y)
    
    balanced_data = pd.DataFrame(X_upsampled, columns=X.columns)
    balanced_data['Attack Type'] = y_upsampled
    balanced_data = balanced_data.sample(frac=1, random_state=RANDOM_STATE)  # Shuffle
    
    print(f"\n📊 Final balanced distribution:")
    print(balanced_data['Attack Type'].value_counts())
    
    return balanced_data


def train_models(X_train, X_test, y_train, y_test):
    """
    Train all 6 models and save them.
    """
    print("\n" + "="*60)
    print("TRAINING MODELS (WITHOUT PCA)")
    print("="*60)
    
    models = {}
    results = {}
    
    # 1. Random Forest
    print("\n🌲 Training Random Forest...")
    rf = RandomForestClassifier(n_estimators=15, max_depth=8, max_features=20, random_state=RANDOM_STATE, n_jobs=-1)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    acc_rf = accuracy_score(y_test, y_pred_rf)
    cv_rf = cross_val_score(rf, X_train, y_train, cv=3, n_jobs=-1)  # Reduced cv from 5 to 3 for speed
    models['random_forest'] = rf
    results['Random Forest'] = {'accuracy': acc_rf, 'cv_mean': cv_rf.mean()}
    print(f"   Accuracy: {acc_rf:.4f}")
    print(f"   CV Score: {cv_rf.mean():.4f}")
    
    # 2. Decision Tree
    print("\n🌳 Training Decision Tree...")
    dt = DecisionTreeClassifier(max_depth=8, random_state=RANDOM_STATE)
    dt.fit(X_train, y_train)
    y_pred_dt = dt.predict(X_test)
    acc_dt = accuracy_score(y_test, y_pred_dt)
    cv_dt = cross_val_score(dt, X_train, y_train, cv=3, n_jobs=-1)
    models['decision_tree'] = dt
    results['Decision Tree'] = {'accuracy': acc_dt, 'cv_mean': cv_dt.mean()}
    print(f"   Accuracy: {acc_dt:.4f}")
    print(f"   CV Score: {cv_dt.mean():.4f}")
    
    # 3. K-Nearest Neighbors
    print("\n👥 Training K-Nearest Neighbors...")
    knn = KNeighborsClassifier(n_neighbors=8, n_jobs=-1)
    knn.fit(X_train, y_train)
    y_pred_knn = knn.predict(X_test)
    acc_knn = accuracy_score(y_test, y_pred_knn)
    cv_knn = cross_val_score(knn, X_train, y_train, cv=3, n_jobs=-1)
    models['knn'] = knn
    results['KNN'] = {'accuracy': acc_knn, 'cv_mean': cv_knn.mean()}
    print(f"   Accuracy: {acc_knn:.4f}")
    print(f"   CV Score: {cv_knn.mean():.4f}")
    
    # 4. Naive Bayes
    print("\n📊 Training Naive Bayes...")
    nb = GaussianNB()
    nb.fit(X_train, y_train)
    y_pred_nb = nb.predict(X_test)
    acc_nb = accuracy_score(y_test, y_pred_nb)
    cv_nb = cross_val_score(nb, X_train, y_train, cv=3, n_jobs=-1)
    models['naive_bayes'] = nb
    results['Naive Bayes'] = {'accuracy': acc_nb, 'cv_mean': cv_nb.mean()}
    print(f"   Accuracy: {acc_nb:.4f}")
    print(f"   CV Score: {cv_nb.mean():.4f}")
    
    # 5. Logistic Regression
    print("\n📈 Training Logistic Regression...")
    lr = LogisticRegression(multi_class='multinomial', solver='saga', max_iter=1000, n_jobs=-1, random_state=RANDOM_STATE)
    lr.fit(X_train, y_train)
    y_pred_lr = lr.predict(X_test)
    acc_lr = accuracy_score(y_test, y_pred_lr)
    cv_lr = cross_val_score(lr, X_train, y_train, cv=3, n_jobs=-1)
    models['logistic_regression'] = lr
    results['Logistic Regression'] = {'accuracy': acc_lr, 'cv_mean': cv_lr.mean()}
    print(f"   Accuracy: {acc_lr:.4f}")
    print(f"   CV Score: {cv_lr.mean():.4f}")
    
    # 6. LightGBM
    print("\n💡 Training LightGBM...")
    lgbm = lgb.LGBMClassifier(
        objective='multiclass',
        num_class=len(np.unique(y_train)),
        n_estimators=100,
        max_depth=7,
        learning_rate=0.1,
        n_jobs=-1,
        random_state=RANDOM_STATE
    )
    lgbm.fit(X_train, y_train)
    y_pred_lgb = lgbm.predict(X_test)
    acc_lgb = accuracy_score(y_test, y_pred_lgb)
    cv_lgb = cross_val_score(lgbm, X_train, y_train, cv=3, n_jobs=-1)
    models['lightgbm'] = lgbm
    results['LightGBM'] = {'accuracy': acc_lgb, 'cv_mean': cv_lgb.mean()}
    print(f"   Accuracy: {acc_lgb:.4f}")
    print(f"   CV Score: {cv_lgb.mean():.4f}")
    
    return models, results


def save_models(models: dict):
    """
    Save trained models to disk.
    """
    print("\n" + "="*60)
    print("SAVING MODELS")
    print("="*60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    model_files = {
        'random_forest': 'random_forest_model_2017_raw.joblib',
        'decision_tree': 'decision_tree_model_2017_raw.joblib',
        'knn': 'knn_model_2017_raw.joblib',
        'naive_bayes': 'nb_model_2017_raw.joblib',
        'logistic_regression': 'lr_model_2017_raw.joblib',
        'lightgbm': 'lgb_model_2017_raw.joblib'
    }
    
    for model_name, filename in model_files.items():
        filepath = os.path.join(OUTPUT_DIR, filename)
        joblib.dump(models[model_name], filepath)
        print(f"✅ Saved {model_name}: {filepath}")


def main():
    """
    Main training pipeline.
    """
    start_time = time.time()
    
    print("\n" + "="*60)
    print("CICIDS2017 MODEL TRAINING - RAW FEATURES (NO PCA)")
    print("="*60)
    print(f"CSV Folder: {CSV_FOLDER}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"Test Size: {TEST_SIZE * 100}%")
    print(f"Random State: {RANDOM_STATE}")
    
    # Check if CSV folder exists
    if not os.path.exists(CSV_FOLDER):
        print(f"\n❌ ERROR: CSV folder not found: {CSV_FOLDER}")
        print("\n📥 Please download CSV files from Google Drive to:")
        print(f"   {os.path.abspath(CSV_FOLDER)}")
        print("\nGoogle Drive link: https://drive.google.com/drive/folders/1zmjzn9GVWfJ9aB02M7kTYXFepNF5DMvm")
        return
    
    # Load data
    data = load_cicids_data(CSV_FOLDER)
    
    if data is None or len(data) == 0:
        print("\n❌ ERROR: No data loaded!")
        return
    
    # Preprocess
    data = preprocess_data(data)
    
    # Balance dataset
    balanced_data = balance_dataset(data)
    
    # Split features and labels
    print("\n" + "="*60)
    print("TRAIN-TEST SPLIT")
    print("="*60)
    
    features = balanced_data.drop('Attack Type', axis=1)
    labels = balanced_data['Attack Type']
    
    print(f"\n📊 Feature shape: {features.shape}")
    print(f"📊 Number of features: {features.shape[1]}")
    print(f"📊 Number of samples: {features.shape[0]:,}")
    
    X_train, X_test, y_train, y_test = train_test_split(
        features, labels, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    
    print(f"\n✅ Train set: {X_train.shape[0]:,} samples")
    print(f"✅ Test set: {X_test.shape[0]:,} samples")
    
    # Standardize features (important for KNN, LR, NB)
    print("\n🔧 Standardizing features...")
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)
    
    # Save scaler for real-time use
    scaler_path = os.path.join(OUTPUT_DIR, 'scaler_2017_raw.joblib')
    joblib.dump(scaler, scaler_path)
    print(f"✅ Saved scaler: {scaler_path}")
    
    # Train models
    models, results = train_models(X_train, X_test, y_train, y_test)
    
    # Save models
    save_models(models)
    
    # Summary
    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print("TRAINING SUMMARY")
    print("="*60)
    print(f"\n{'Model':<25} {'Accuracy':<12} {'CV Score':<12}")
    print("-" * 60)
    for model_name, metrics in results.items():
        print(f"{model_name:<25} {metrics['accuracy']:<12.4f} {metrics['cv_mean']:<12.4f}")
    
    print(f"\n⏱️  Total training time: {elapsed/60:.2f} minutes")
    print(f"✅ All models saved to: {os.path.abspath(OUTPUT_DIR)}")
    print("\n🚀 Ready to use with real-time feature engine!")


if __name__ == '__main__':
    main()
