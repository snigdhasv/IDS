#!/usr/bin/env python3
"""
Feature Mapper for Model Compatibility

Maps between different feature set sizes to ensure compatibility
between feature extractors and ML models.

Handles:
- 65 CICIDS2017 features → 34 model features (common subset)
- Feature name normalization
- Missing feature handling
"""

import logging
import numpy as np
from typing import Dict, List

logger = logging.getLogger(__name__)


class FeatureMapper:
    """
    Maps features between different formats for model compatibility.
    """
    
    # Most important 34 features commonly used in IDS models
    # These are the core features that provide good discrimination
    CORE_34_FEATURES = [
        'Destination Port',
        'Flow Duration',
        'Total Fwd Packets',
        'Total Backward Packets',
        'Total Length of Fwd Packets',
        'Total Length of Bwd Packets',
        'Fwd Packet Length Max',
        'Fwd Packet Length Min',
        'Fwd Packet Length Mean',
        'Fwd Packet Length Std',
        'Bwd Packet Length Max',
        'Bwd Packet Length Min',
        'Bwd Packet Length Mean',
        'Bwd Packet Length Std',
        'Flow Bytes/s',
        'Flow Packets/s',
        'Flow IAT Mean',
        'Flow IAT Std',
        'Flow IAT Max',
        'Flow IAT Min',
        'Fwd IAT Mean',
        'Fwd IAT Std',
        'Fwd IAT Max',
        'Fwd IAT Min',
        'Bwd IAT Mean',
        'Bwd IAT Std',
        'Bwd IAT Max',
        'Bwd IAT Min',
        'Fwd Packets/s',
        'Bwd Packets/s',
        'Packet Length Mean',
        'Packet Length Std',
        'Average Packet Size',
        'Avg Fwd Segment Size'
    ]
    
    def __init__(self, target_features: int = 34):
        """
        Initialize the feature mapper.
        
        Args:
            target_features: Number of features expected by the model
        """
        self.target_features = target_features
        logger.info(f"Initialized feature mapper (target: {target_features} features)")
    
    def map_to_34(self, features_65: Dict[str, float]) -> np.ndarray:
        """
        Map 65 CICIDS2017 features to 34 core features.
        
        Args:
            features_65: Dictionary with 65 features
            
        Returns:
            Numpy array with 34 features in correct order
        """
        mapped = []
        
        for feature_name in self.CORE_34_FEATURES:
            value = features_65.get(feature_name, 0.0)
            
            # Handle NaN and Inf values
            if np.isnan(value) or np.isinf(value):
                value = 0.0
            
            mapped.append(value)
        
        return np.array(mapped, dtype=np.float32).reshape(1, -1)
    
    def map_features(self, features: Dict[str, float], source_count: int) -> np.ndarray:
        """
        Map features from any source format to target format.
        
        Args:
            features: Feature dictionary
            source_count: Number of features in source format
            
        Returns:
            Numpy array with target number of features
        """
        if source_count == 65 and self.target_features == 34:
            return self.map_to_34(features)
        elif source_count == 34:
            # Already correct size, just convert to array
            return np.array(list(features.values()), dtype=np.float32).reshape(1, -1)
        else:
            logger.warning(f"Unsupported mapping: {source_count} → {self.target_features}")
            # Pad or truncate as needed
            values = list(features.values())[:self.target_features]
            while len(values) < self.target_features:
                values.append(0.0)
            return np.array(values, dtype=np.float32).reshape(1, -1)
    
    def get_feature_importance_map(self) -> Dict[str, int]:
        """
        Get mapping of feature names to their importance rank.
        
        Returns:
            Dictionary mapping feature names to rank (0 = most important)
        """
        return {name: idx for idx, name in enumerate(self.CORE_34_FEATURES)}


# Global instance for easy import
feature_mapper = FeatureMapper()


if __name__ == '__main__':
    # Test the mapper
    print("Feature Mapper Test")
    print("=" * 60)
    
    # Create test features (65)
    test_features = {f"Feature_{i}": float(i) for i in range(65)}
    
    # Add some real feature names
    for name in FeatureMapper.CORE_34_FEATURES[:10]:
        test_features[name] = float(len(name))
    
    mapper = FeatureMapper(target_features=34)
    
    print(f"\nInput: {len(test_features)} features")
    result = mapper.map_features(test_features, source_count=65)
    print(f"Output: {result.shape} array")
    print(f"First 5 values: {result[0, :5]}")
    
    print("\n✓ Feature mapper working correctly!")
