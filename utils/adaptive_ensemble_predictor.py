#!/usr/bin/env python3
"""
Adaptive Ensemble Predictor

Implements the adaptive ensemble technique from PerformanceEvaluation_AdaptiveEnsembles.ipynb
that achieved 0.9148 accuracy with RF(2017) + LGB(2018) combination.

This module provides adaptive ensemble prediction using confidence-based weighting
between Random Forest (CICIDS2017) and LightGBM (CICIDS2018) models.
"""

import os
import numpy as np
import pandas as pd
import joblib
from typing import Tuple, Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

class AdaptiveEnsemblePredictor:
    """
    Enhanced ensemble prediction with adaptive confidence-based weighting
    
    This implements the adaptive ensemble technique that combines:
    - Random Forest model trained on CICIDS2017
    - LightGBM model trained on CICIDS2018
    
    Using confidence-based adaptive weighting that achieved 0.9148 accuracy.
    """
    
    def __init__(self, rf2017_path: str, lgb2018_path: str):
        self.rf2017_path = rf2017_path
        self.lgb2018_path = lgb2018_path
        self.rf2017_model = None
        self.lgb2018_model = None
        self.full_label_space = None
        self.confidence_threshold = 0.5
        self.weighting_history = []
        
    def load_models(self) -> bool:
        """Load both ensemble models"""
        try:
            print("🧠 Loading RF(2017) model...")
            if not os.path.exists(self.rf2017_path):
                print(f"❌ RF(2017) model not found at {self.rf2017_path}")
                return False
            self.rf2017_model = joblib.load(self.rf2017_path)
            print(f"✓ RF(2017) model loaded: {self.rf2017_model.n_features_in_} features")
            
            print("🧠 Loading LGB(2018) model...")
            if not os.path.exists(self.lgb2018_path):
                print(f"❌ LGB(2018) model not found at {self.lgb2018_path}")
                return False
            self.lgb2018_model = joblib.load(self.lgb2018_path)
            print(f"✓ LGB(2018) model loaded: {self.lgb2018_model.n_features_in_} features")
            
            # Setup unified label space
            self._setup_label_space()
            print(f"✓ Ensemble ready with {len(self.full_label_space)} classes: {self.full_label_space}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading ensemble models: {e}")
            return False
    
    def _setup_label_space(self):
        """Create unified label space from both models"""
        if self.rf2017_model is None or self.lgb2018_model is None:
            return
            
        rf_classes = self.rf2017_model.classes_.tolist()
        lgb_classes = self.lgb2018_model.classes_.tolist()
        self.full_label_space = sorted(list(set(rf_classes + lgb_classes)))
    
    def _align_probabilities(self, model_proba: np.ndarray, model_classes: np.ndarray) -> np.ndarray:
        """Align model probabilities to full label space"""
        aligned = np.zeros((model_proba.shape[0], len(self.full_label_space)))
        
        for i, label in enumerate(model_classes):
            if label in self.full_label_space:
                idx = self.full_label_space.index(label)
                aligned[:, idx] = model_proba[:, i]
        
        return aligned
    
    def _calculate_confidence_metrics(self, proba_array: np.ndarray) -> Dict[str, np.ndarray]:
        """Calculate multiple confidence metrics for probability distributions"""
        # Max probability (highest probability for any class)
        max_conf = np.max(proba_array, axis=1)
        
        # Entropy-based confidence (lower entropy = higher confidence)
        entropy = -np.sum(proba_array * np.log(proba_array + 1e-10), axis=1)
        entropy_conf = 1 - (entropy / np.log(len(self.full_label_space)))  # Normalized
        
        # Margin confidence (difference between top 2 predictions)
        sorted_proba = np.sort(proba_array, axis=1)
        margin_conf = sorted_proba[:, -1] - sorted_proba[:, -2]
        
        # Gini coefficient based confidence (higher gini = more confidence)
        gini_conf = 1 - np.sum(proba_array ** 2, axis=1)
        gini_conf = 1 - gini_conf  # Invert so higher = more confident
        
        return {
            'max_prob': max_conf,
            'entropy': entropy_conf,
            'margin': margin_conf,
            'gini': gini_conf
        }
    
    def _confidence_based_weighting(self, conf1: np.ndarray, conf2: np.ndarray, 
                                   method: str = 'adaptive_ratio') -> Tuple[np.ndarray, np.ndarray]:
        """Calculate adaptive weights based on confidence scores"""
        
        if method == 'adaptive_ratio':
            # Higher confidence gets higher weight
            total_conf = conf1 + conf2 + 1e-10  # Avoid division by zero
            w1 = conf1 / total_conf
            w2 = conf2 / total_conf
            
        elif method == 'exponential':
            # Exponential weighting emphasizes high confidence more
            exp_conf1 = np.exp(conf1 * 3)  # Scale factor of 3
            exp_conf2 = np.exp(conf2 * 3)
            total_exp = exp_conf1 + exp_conf2
            w1 = exp_conf1 / total_exp
            w2 = exp_conf2 / total_exp
            
        elif method == 'threshold_based':
            # If one model is very confident, give it more weight
            w1 = np.where(conf1 > self.confidence_threshold,
                         np.minimum(conf1 * 1.5, 0.9), 0.5)
            w2 = 1 - w1
            
        elif method == 'softmax':
            # Softmax weighting
            logits = np.column_stack([conf1, conf2])
            softmax_weights = np.exp(logits) / np.sum(np.exp(logits), axis=1, keepdims=True)
            w1 = softmax_weights[:, 0]
            w2 = softmax_weights[:, 1]
            
        else:  # default to simple ratio
            total_conf = conf1 + conf2 + 1e-10
            w1 = conf1 / total_conf
            w2 = conf2 / total_conf
        
        return w1, w2
    
    def predict_ensemble(self, X_input: np.ndarray, method: str = 'confidence_adaptive',
                        confidence_metric: str = 'max_prob') -> Tuple[List[str], np.ndarray, np.ndarray]:
        """
        Enhanced ensemble prediction with adaptive weighting strategies
        
        Parameters:
        - X_input: Input features for prediction
        - method: 'average', 'confidence_adaptive', 'exponential', 'threshold_based', 'softmax'
        - confidence_metric: 'max_prob', 'entropy', 'margin', 'gini'
        
        Returns:
        - predictions: List of predicted class labels
        - confidence_scores: Array of confidence scores
        - weights_used: Array of weights used for each prediction [w_rf, w_lgb]
        """
        try:
            if self.rf2017_model is None or self.lgb2018_model is None:
                raise ValueError("Models not loaded. Call load_models() first.")
            
            # Convert to DataFrame to avoid feature name warnings
            if isinstance(X_input, np.ndarray):
                # Create dummy feature names if needed
                n_features = X_input.shape[1]
                feature_names = [f'feature_{i}' for i in range(n_features)]
                X_df = pd.DataFrame(X_input, columns=feature_names)
            else:
                X_df = X_input
            
            # Get probabilities from both models
            proba_rf = self.rf2017_model.predict_proba(X_df)
            proba_lgb = self.lgb2018_model.predict_proba(X_df)
            
            # Align probabilities to unified label space
            aligned_rf = self._align_probabilities(proba_rf, self.rf2017_model.classes_)
            aligned_lgb = self._align_probabilities(proba_lgb, self.lgb2018_model.classes_)
            
            # Calculate confidence metrics
            conf_metrics_rf = self._calculate_confidence_metrics(aligned_rf)
            conf_metrics_lgb = self._calculate_confidence_metrics(aligned_lgb)
            
            # Select confidence metric
            conf_rf = conf_metrics_rf[confidence_metric]
            conf_lgb = conf_metrics_lgb[confidence_metric]
            
            # Calculate weights based on method
            if method == 'average':
                # Simple average (baseline)
                combined = (aligned_rf + aligned_lgb) / 2
                weights_used = np.full((len(X_df), 2), 0.5)
                
            elif method == 'confidence_adaptive':
                # Adaptive weighting based on confidence (this achieved 0.9148 accuracy)
                w_rf, w_lgb = self._confidence_based_weighting(conf_rf, conf_lgb, 'adaptive_ratio')
                combined = (aligned_rf.T * w_rf).T + (aligned_lgb.T * w_lgb).T
                weights_used = np.column_stack([w_rf, w_lgb])
                
            elif method == 'exponential':
                # Exponential weighting for high confidence emphasis
                w_rf, w_lgb = self._confidence_based_weighting(conf_rf, conf_lgb, 'exponential')
                combined = (aligned_rf.T * w_rf).T + (aligned_lgb.T * w_lgb).T
                weights_used = np.column_stack([w_rf, w_lgb])
                
            elif method == 'threshold_based':
                # Threshold-based weighting
                w_rf, w_lgb = self._confidence_based_weighting(conf_rf, conf_lgb, 'threshold_based')
                combined = (aligned_rf.T * w_rf).T + (aligned_lgb.T * w_lgb).T
                weights_used = np.column_stack([w_rf, w_lgb])
                
            elif method == 'softmax':
                # Softmax weighting
                w_rf, w_lgb = self._confidence_based_weighting(conf_rf, conf_lgb, 'softmax')
                combined = (aligned_rf.T * w_rf).T + (aligned_lgb.T * w_lgb).T
                weights_used = np.column_stack([w_rf, w_lgb])
                
            else:
                # Default to simple average
                combined = (aligned_rf + aligned_lgb) / 2
                weights_used = np.full((len(X_df), 2), 0.5)
            
            # Get final predictions
            predictions = [self.full_label_space[i] for i in np.argmax(combined, axis=1)]
            confidence_scores = np.max(combined, axis=1)
            
            # Store weighting information for analysis
            self.weighting_history.append({
                'method': method,
                'weights': weights_used,
                'confidences': np.column_stack([conf_rf, conf_lgb]),
                'predictions': predictions
            })
            
            return predictions, confidence_scores, weights_used
            
        except Exception as e:
            print(f"❌ Error in adaptive ensemble prediction: {e}")
            return [], np.array([]), np.array([])
    
    def predict_single(self, features: Dict) -> Tuple[str, float]:
        """
        Predict attack type for a single sample using adaptive ensemble
        
        Parameters:
        - features: Dictionary of feature names and values
        
        Returns:
        - prediction: Predicted attack type
        - confidence: Confidence score (0-1)
        """
        try:
            # Convert features dict to array format expected by models
            # For now, we'll use a simplified approach - in production you'd want proper feature alignment
            feature_values = list(features.values())
            
            # Ensure we have enough features (pad with zeros if needed)
            expected_features = max(self.rf2017_model.n_features_in_, self.lgb2018_model.n_features_in_)
            while len(feature_values) < expected_features:
                feature_values.append(0.0)
            
            # Truncate if too many features
            feature_values = feature_values[:expected_features]
            
            # Convert to numpy array and reshape for single prediction
            X_input = np.array([feature_values])
            
            # Make ensemble prediction using the method that achieved 0.9148 accuracy
            predictions, confidences, weights = self.predict_ensemble(
                X_input, method='confidence_adaptive', confidence_metric='max_prob'
            )
            
            if len(predictions) > 0:
                return predictions[0], confidences[0]
            else:
                return "UNKNOWN", 0.0
                
        except Exception as e:
            print(f"❌ Error in single prediction: {e}")
            return "ERROR", 0.0
    
    def get_model_info(self) -> Dict:
        """Get information about the loaded models"""
        if self.rf2017_model is None or self.lgb2018_model is None:
            return {"error": "Models not loaded"}
        
        return {
            "rf2017": {
                "type": type(self.rf2017_model).__name__,
                "n_features": self.rf2017_model.n_features_in_,
                "classes": self.rf2017_model.classes_.tolist()
            },
            "lgb2018": {
                "type": type(self.lgb2018_model).__name__,
                "n_features": self.lgb2018_model.n_features_in_,
                "classes": self.lgb2018_model.classes_.tolist()
            },
            "ensemble": {
                "unified_classes": self.full_label_space,
                "total_classes": len(self.full_label_space) if self.full_label_space else 0
            }
        }
    
    def analyze_weighting_patterns(self):
        """Analyze how weights are distributed across different methods"""
        if not self.weighting_history:
            print("No weighting history available")
            return
        
        print("\n🔍 ADAPTIVE WEIGHTING ANALYSIS")
        print("=" * 50)
        
        for i, history in enumerate(self.weighting_history):
            method = history['method']
            weights = history['weights']
            
            print(f"\n📊 Method: {method}")
            print(f"Weight Statistics:")
            print(f"  RF(2017) - Mean: {np.mean(weights[:, 0]):.4f}, Std: {np.std(weights[:, 0]):.4f}")
            print(f"  LGB(2018) - Mean: {np.mean(weights[:, 1]):.4f}, Std: {np.std(weights[:, 1]):.4f}")
            
            # Show distribution of weights
            rf_bins = np.histogram(weights[:, 0], bins=10, range=(0, 1))[0]
            print(f"  RF(2017) weight distribution: {rf_bins}")


def test_adaptive_ensemble():
    """Test the adaptive ensemble predictor"""
    print("🧪 Testing Adaptive Ensemble Predictor")
    print("=" * 50)
    
    # Model paths
    rf2017_path = "/home/ifscr/SE_02_2025/IDS/ML Models/random_forest_model_2017.joblib"
    lgb2018_path = "/home/ifscr/SE_02_2025/IDS/ML Models/lgb_model_2018.joblib"
    
    # Initialize predictor
    predictor = AdaptiveEnsemblePredictor(rf2017_path, lgb2018_path)
    
    # Load models
    if not predictor.load_models():
        print("❌ Failed to load models")
        return
    
    # Show model info
    info = predictor.get_model_info()
    print("\n📋 Model Information:")
    print(f"RF(2017): {info['rf2017']['type']} with {info['rf2017']['n_features']} features")
    print(f"LGB(2018): {info['lgb2018']['type']} with {info['lgb2018']['n_features']} features")
    print(f"Unified classes: {info['ensemble']['unified_classes']}")
    
    # Test with sample features (create dummy features for testing)
    print("\n🧪 Testing prediction with sample features...")
    
    # Create sample features matching the expected format
    sample_features = {
        'Destination Port': 80,
        'Flow Duration': 120000,
        'Total Fwd Packets': 10,
        'Total Backward Packets': 8,
        'Total Length of Fwd Packets': 1500,
        'Total Length of Bwd Packets': 1200,
        'Flow Bytes/s': 2250.0,
        'Flow Packets/s': 150.0,
        'Fwd Packet Length Mean': 150.0,
        'Bwd Packet Length Mean': 150.0,
    }
    
    # Pad with zeros to match expected features
    expected_features = max(info['rf2017']['n_features'], info['lgb2018']['n_features'])
    for i in range(len(sample_features), expected_features):
        sample_features[f'feature_{i}'] = 0.0
    
    # Make prediction
    prediction, confidence = predictor.predict_single(sample_features)
    print(f"✓ Prediction: {prediction}")
    print(f"✓ Confidence: {confidence:.4f}")
    
    # Test different ensemble methods
    print("\n🔬 Testing different ensemble methods...")
    
    # Convert features to array for batch testing
    feature_values = list(sample_features.values())[:expected_features]
    X_test = np.array([feature_values] * 5)  # Create 5 duplicate samples for testing
    
    methods = ['average', 'confidence_adaptive', 'exponential', 'threshold_based', 'softmax']
    
    for method in methods:
        predictions, confidences, weights = predictor.predict_ensemble(X_test, method=method)
        avg_confidence = np.mean(confidences)
        avg_rf_weight = np.mean(weights[:, 0])
        avg_lgb_weight = np.mean(weights[:, 1])
        
        print(f"  {method:20s} - Pred: {predictions[0]:15s} Conf: {avg_confidence:.4f} "
              f"RF: {avg_rf_weight:.3f} LGB: {avg_lgb_weight:.3f}")
    
    # Analyze weighting patterns
    predictor.analyze_weighting_patterns()
    
    print("\n✅ Adaptive Ensemble Test Complete!")


if __name__ == "__main__":
    test_adaptive_ensemble()