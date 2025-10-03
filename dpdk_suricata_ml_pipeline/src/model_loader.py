#!/usr/bin/env python3
"""
ML Model Loader Module

Handles loading and validation of trained ML models for intrusion detection.
Supports Random Forest and LightGBM models trained on CICIDS2017/2018 datasets.
"""

import os
import logging
from typing import Optional, Tuple, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Try importing required ML libraries
try:
    import joblib
    import numpy as np
except ImportError as e:
    logger.error(f"Missing required libraries: {e}")
    logger.error("Install with: pip install joblib numpy")
    raise

# Optional: scikit-learn and lightgbm
try:
    from sklearn.ensemble import RandomForestClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available")

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logger.warning("LightGBM not available")


class MLModelLoader:
    """
    Loads and manages ML models for intrusion detection.
    
    Supports:
    - Random Forest models (scikit-learn)
    - LightGBM models
    - Model validation
    - Feature count verification
    """
    
    def __init__(self, model_dir: str = None):
        """
        Initialize the model loader.
        
        Args:
            model_dir: Directory containing model files. If None, uses default.
        """
        if model_dir is None:
            # Default to ML Models directory in IDS project
            self.model_dir = Path(__file__).parent.parent.parent / "ML Models"
        else:
            self.model_dir = Path(model_dir)
        
        self.model = None
        self.model_type = None
        self.model_path = None
        self.expected_features = None
        
        logger.info(f"Model loader initialized with directory: {self.model_dir}")
    
    def load_model(self, model_path: str = None, model_name: str = None) -> bool:
        """
        Load a trained ML model from file.
        
        Args:
            model_path: Full path to model file. If None, tries to find model by name.
            model_name: Name of model file (e.g., 'random_forest_model_2017.joblib')
                       Only used if model_path is None.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            # Determine model file path
            if model_path:
                model_file = Path(model_path)
            elif model_name:
                model_file = self.model_dir / model_name
            else:
                # Try to auto-detect model
                model_file = self._find_model()
                if not model_file:
                    logger.error("No model path or name provided, and auto-detection failed")
                    return False
            
            if not model_file.exists():
                logger.error(f"Model file not found: {model_file}")
                return False
            
            logger.info(f"Loading model from: {model_file}")
            
            # Load model using joblib
            self.model = joblib.load(model_file)
            self.model_path = str(model_file)
            
            # Determine model type and features
            self._analyze_model()
            
            logger.info(f"✓ Model loaded successfully")
            logger.info(f"  Type: {self.model_type}")
            logger.info(f"  Expected features: {self.expected_features}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}", exc_info=True)
            return False
    
    def _find_model(self) -> Optional[Path]:
        """
        Auto-detect model file in model directory.
        
        Priority:
        1. random_forest_model_2017.joblib
        2. lgb_model_2018.joblib
        3. Any .joblib file
        
        Returns:
            Path to model file, or None if not found
        """
        if not self.model_dir.exists():
            logger.warning(f"Model directory does not exist: {self.model_dir}")
            return None
        
        # Priority list
        priority_models = [
            "random_forest_model_2017.joblib",
            "lgb_model_2018.joblib"
        ]
        
        for model_name in priority_models:
            model_path = self.model_dir / model_name
            if model_path.exists():
                logger.info(f"Auto-detected model: {model_name}")
                return model_path
        
        # Fallback: find any .joblib file
        joblib_files = list(self.model_dir.glob("*.joblib"))
        if joblib_files:
            logger.info(f"Using first available model: {joblib_files[0].name}")
            return joblib_files[0]
        
        logger.warning("No model files found in directory")
        return None
    
    def _analyze_model(self):
        """
        Analyze loaded model to determine type and expected features.
        """
        if self.model is None:
            return
        
        # Determine model type
        model_class_name = type(self.model).__name__
        
        if 'RandomForest' in model_class_name:
            self.model_type = 'RandomForest'
        elif 'LGB' in model_class_name or 'LightGBM' in model_class_name or 'Booster' in model_class_name:
            self.model_type = 'LightGBM'
        elif 'GradientBoosting' in model_class_name:
            self.model_type = 'GradientBoosting'
        else:
            self.model_type = model_class_name
        
        # Get expected feature count
        try:
            if hasattr(self.model, 'n_features_in_'):
                self.expected_features = self.model.n_features_in_
            elif hasattr(self.model, 'n_features_'):
                self.expected_features = self.model.n_features_
            elif hasattr(self.model, 'num_feature'):
                # LightGBM
                self.expected_features = self.model.num_feature()
            else:
                logger.warning("Could not determine expected feature count")
                self.expected_features = None
        except Exception as e:
            logger.warning(f"Error getting feature count: {e}")
            self.expected_features = None
    
    def predict(self, features: np.ndarray) -> Tuple[Optional[Any], Optional[float]]:
        """
        Make prediction using loaded model.
        
        Args:
            features: Feature array (1D or 2D numpy array)
        
        Returns:
            Tuple of (prediction, confidence)
            - prediction: Class label or value
            - confidence: Confidence score (0-1) if available
        """
        if self.model is None:
            logger.error("No model loaded")
            return None, None
        
        try:
            # Ensure 2D array
            if features.ndim == 1:
                features = features.reshape(1, -1)
            
            # Validate feature count
            if self.expected_features and features.shape[1] != self.expected_features:
                logger.warning(
                    f"Feature count mismatch: expected {self.expected_features}, "
                    f"got {features.shape[1]}"
                )
            
            # Make prediction
            prediction = self.model.predict(features)[0]
            
            # Get confidence if available
            confidence = None
            if hasattr(self.model, 'predict_proba'):
                try:
                    proba = self.model.predict_proba(features)[0]
                    confidence = float(np.max(proba))
                except Exception as e:
                    logger.debug(f"Could not get prediction probability: {e}")
            
            return prediction, confidence
            
        except Exception as e:
            logger.error(f"Error making prediction: {e}", exc_info=True)
            return None, None
    
    def predict_proba(self, features: np.ndarray) -> Optional[np.ndarray]:
        """
        Get prediction probabilities for all classes.
        
        Args:
            features: Feature array (1D or 2D numpy array)
        
        Returns:
            Array of probabilities for each class, or None if not supported
        """
        if self.model is None:
            logger.error("No model loaded")
            return None
        
        try:
            # Ensure 2D array
            if features.ndim == 1:
                features = features.reshape(1, -1)
            
            if hasattr(self.model, 'predict_proba'):
                return self.model.predict_proba(features)[0]
            else:
                logger.warning("Model does not support probability prediction")
                return None
                
        except Exception as e:
            logger.error(f"Error getting prediction probabilities: {e}", exc_info=True)
            return None
    
    def get_feature_importances(self) -> Optional[np.ndarray]:
        """
        Get feature importances from model if available.
        
        Returns:
            Array of feature importances, or None if not supported
        """
        if self.model is None:
            logger.error("No model loaded")
            return None
        
        try:
            if hasattr(self.model, 'feature_importances_'):
                return self.model.feature_importances_
            elif hasattr(self.model, 'feature_importance'):
                # LightGBM
                return self.model.feature_importance()
            else:
                logger.warning("Model does not provide feature importances")
                return None
                
        except Exception as e:
            logger.error(f"Error getting feature importances: {e}", exc_info=True)
            return None
    
    def get_model_info(self) -> dict:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model information
        """
        info = {
            'loaded': self.model is not None,
            'model_path': self.model_path,
            'model_type': self.model_type,
            'expected_features': self.expected_features,
        }
        
        if self.model:
            info['model_class'] = type(self.model).__name__
            
            # Get additional model-specific info
            if hasattr(self.model, 'n_estimators'):
                info['n_estimators'] = self.model.n_estimators
            if hasattr(self.model, 'max_depth'):
                info['max_depth'] = self.model.max_depth
        
        return info
    
    def is_loaded(self) -> bool:
        """Check if a model is loaded."""
        return self.model is not None


if __name__ == "__main__":
    # Test model loading
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create loader
    loader = MLModelLoader()
    
    # Try to load model
    if loader.load_model():
        print("\n✓ Model loaded successfully")
        
        # Display model info
        info = loader.get_model_info()
        print("\nModel Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        # Test prediction with dummy data
        print("\nTesting prediction with dummy data...")
        if loader.expected_features:
            dummy_features = np.zeros(loader.expected_features)
            prediction, confidence = loader.predict(dummy_features)
            
            print(f"  Prediction: {prediction}")
            if confidence:
                print(f"  Confidence: {confidence:.2%}")
        else:
            print("  Skipping test prediction (unknown feature count)")
    else:
        print("\n✗ Failed to load model")
        sys.exit(1)
