#!/usr/bin/env python3
"""
ML Model Loader

Handles loading and management of ML models for the IDS pipeline.
"""

import os
import joblib
import numpy as np
from pathlib import Path
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class MLModelLoader:
    """
    Loads and manages ML models for intrusion detection.
    
    Supports both single models and ensemble models.
    """
    
    def __init__(self, model_dir: Optional[str] = None):
        """
        Initialize model loader.
        
        Args:
            model_dir: Directory containing model files. Defaults to ../models/ML Models
        """
        if model_dir is None:
            # Default to models directory relative to src
            self.model_dir = Path(__file__).parent.parent / 'models' / 'ML Models'
        else:
            self.model_dir = Path(model_dir)
        
        self.model = None
        self.model_name = None
        self.model_type = None
        
    def load_model(self, model_name: str) -> bool:
        """
        Load a trained model from file.
        
        Args:
            model_name: Name of the model file (e.g., 'random_forest_model_2017.joblib')
            
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            model_path = self.model_dir / model_name
            
            if not model_path.exists():
                logger.error(f"Model file not found: {model_path}")
                print(f"❌ Model not found: {model_path}")
                return False
            
            logger.info(f"Loading model from {model_path}")
            self.model = joblib.load(model_path)
            self.model_name = model_name
            
            # Detect model type
            model_class = self.model.__class__.__name__
            if 'RandomForest' in model_class:
                self.model_type = 'Random Forest'
            elif 'LGB' in model_class or 'LightGBM' in model_class:
                self.model_type = 'LightGBM'
            elif 'XGB' in model_class:
                self.model_type = 'XGBoost'
            else:
                self.model_type = model_class
            
            logger.info(f"Model loaded successfully: {self.model_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}", exc_info=True)
            print(f"❌ Error loading model: {e}")
            return False
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """
        Make predictions using the loaded model.
        
        Args:
            features: Feature array of shape (n_samples, n_features)
            
        Returns:
            Predictions array
        """
        if self.model is None:
            raise ValueError("No model loaded. Call load_model() first.")
        
        return self.model.predict(features)
    
    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """
        Make probability predictions using the loaded model.
        
        Args:
            features: Feature array of shape (n_samples, n_features)
            
        Returns:
            Probability predictions array of shape (n_samples, n_classes)
        """
        if self.model is None:
            raise ValueError("No model loaded. Call load_model() first.")
        
        if not hasattr(self.model, 'predict_proba'):
            raise AttributeError(f"Model {self.model_type} does not support predict_proba")
        
        return self.model.predict_proba(features)
    
    def get_model_info(self) -> Dict:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary containing model information
        """
        if self.model is None:
            return {
                'loaded': False,
                'model_name': None,
                'model_type': None,
                'expected_features': None,
                'classes': None
            }
        
        info = {
            'loaded': True,
            'model_name': self.model_name,
            'model_type': self.model_type,
            'expected_features': getattr(self.model, 'n_features_in_', 'unknown'),
            'classes': None
        }
        
        # Get class information if available
        if hasattr(self.model, 'classes_'):
            info['classes'] = self.model.classes_.tolist()
        
        return info
    
    def get_feature_count(self) -> int:
        """
        Get the number of features expected by the model.
        
        Returns:
            Number of features
        """
        if self.model is None:
            return 0
        
        return getattr(self.model, 'n_features_in_', 0)
    
    def is_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self.model is not None
