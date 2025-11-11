#!/usr/bin/env python3
"""
Feature Selector for Real-time ML Inference

Reduces 65 CICIDS features to the 34 most important features
based on correlation analysis from CICIDS2017 training.
"""

import numpy as np
from typing import Dict, List

# Feature name mapping: Engine format → CSV/Model format
# The engine uses full names, but models were trained on abbreviated CSV names
FEATURE_NAME_MAP = {
    # Engine name → CSV name
    'Destination Port': 'Destination Port',
    'Flow Duration': 'Flow Duration',
    'Total Fwd Packets': 'Total Fwd Packets',
    'Total Backward Packets': 'Total Backward Packets',
    'Total Length of Fwd Packets': 'Total Length of Fwd Packets',
    'Total Length of Bwd Packets': 'Total Length of Bwd Packets',
    'Fwd Packet Length Max': 'Fwd Packet Length Max',
    'Fwd Packet Length Min': 'Fwd Packet Length Min',
    'Fwd Packet Length Mean': 'Fwd Packet Length Mean',
    'Fwd Packet Length Std': 'Fwd Packet Length Std',
    'Bwd Packet Length Max': 'Bwd Packet Length Max',
    'Bwd Packet Length Min': 'Bwd Packet Length Min',
    'Bwd Packet Length Mean': 'Bwd Packet Length Mean',
    'Bwd Packet Length Std': 'Bwd Packet Length Std',
    'Flow Bytes/s': 'Flow Bytes/s',
    'Flow Packets/s': 'Flow Packets/s',
    'Flow IAT Mean': 'Flow IAT Mean',
    'Flow IAT Std': 'Flow IAT Std',
    'Flow IAT Max': 'Flow IAT Max',
    'Flow IAT Min': 'Flow IAT Min',
    'Fwd IAT Total': 'Fwd IAT Total',
    'Fwd IAT Mean': 'Fwd IAT Mean',
    'Fwd IAT Std': 'Fwd IAT Std',
    'Fwd IAT Max': 'Fwd IAT Max',
    'Fwd IAT Min': 'Fwd IAT Min',
    'Bwd IAT Total': 'Bwd IAT Total',
    'Bwd IAT Mean': 'Bwd IAT Mean',
    'Bwd IAT Std': 'Bwd IAT Std',
    'Bwd IAT Max': 'Bwd IAT Max',
    'Bwd IAT Min': 'Bwd IAT Min',
    'Fwd PSH Flags': 'Fwd PSH Flags',
    'Bwd PSH Flags': 'Bwd PSH Flags',
    'Fwd URG Flags': 'Fwd URG Flags',
    'Bwd URG Flags': 'Bwd URG Flags',
}

# Top 34 most important features (using engine names)
SELECTED_FEATURES = list(FEATURE_NAME_MAP.keys())


def select_features(features: Dict[str, float]) -> np.ndarray:
    """
    Select the 34 most important features from the full feature vector.
    
    Maps feature names from engine format to CSV format, then selects the 34 best.
    
    Args:
        features: Dictionary with CICIDS feature names from the engine
        
    Returns:
        numpy array with 34 selected features in correct order
    """
    selected_values = []
    
    # Extract the 34 most important features in order
    for engine_name in SELECTED_FEATURES:
        # Get feature value directly (engine uses exact names)
        value = features.get(engine_name, 0.0)
        selected_values.append(value)
    
    # Return as 2D array (1 sample × 34 features) for model input
    return np.array(selected_values, dtype=np.float32)


def get_feature_names() -> List[str]:
    """Return list of selected feature names"""
    return SELECTED_FEATURES.copy()


if __name__ == '__main__':
    # Test the selector
    print(f"Selected {len(SELECTED_FEATURES)} features:")
    for i, name in enumerate(SELECTED_FEATURES, 1):
        print(f"{i:2d}. {name}")
    
    # Test with dummy data
    test_features = {name: float(i) for i, name in enumerate(SELECTED_FEATURES)}
    selected = select_features(test_features)
    print(f"\nOutput shape: {selected.shape}")
    print(f"Expected: (1, 34)")
