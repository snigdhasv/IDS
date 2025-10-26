#!/usr/bin/env python3
"""
Two-Model Ensemble with Meta-Learner

Based on AdaptiveEnsemblePredictor from PerformanceEvaluation_AdaptiveEnsembles.ipynb

Combines EXACTLY TWO models using a meta-learner (Random Forest Regressor) that learns
optimal weights for each prediction based on confidence metrics and model agreement.
"""

import numpy as np
import logging
from typing import Dict, Tuple, Optional
from collections import defaultdict
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score

logger = logging.getLogger(__name__)


class TwoModelEnsemble:
    """
    Two-model ensemble with meta-learner for adaptive weighting.
    
    The meta-learner learns to predict optimal weights (w1, w2) for each sample
    based on confidence metrics from both models.
    """
    
    def __init__(self, model1, model2, model1_name: str, model2_name: str):
        """
        Initialize with exactly TWO models.
        
        Args:
            model1: First ML model (must have predict_proba and classes_)
            model2: Second ML model (must have predict_proba and classes_)
            model1_name: Name/identifier for model 1
            model2_name: Name/identifier for model 2
        """
        self.model1 = model1
        self.model2 = model2
        self.model1_name = model1_name
        self.model2_name = model2_name
        
        # Create unified label space
        self.full_label_space = self._create_label_space()
        
        # Meta-learner (Random Forest Regressor)
        self.meta_learner = None
        self.is_trained = False
        
        # Metrics
        self.metrics = {
            'predictions': defaultdict(int),
            'model1_confidence': [],
            'model2_confidence': [],
            'ensemble_confidence': [],
            'agreement_rate': [],
            'weights_model1': [],
            'weights_model2': [],
        }
        
        logger.info(f"Two-model ensemble created: {model1_name} + {model2_name}")
        logger.info(f"Label space: {len(self.full_label_space)} classes")
    
    def _create_label_space(self):
        """Create unified label space from both models."""
        labels1 = set(self.model1.classes_) if hasattr(self.model1, 'classes_') else set()
        labels2 = set(self.model2.classes_) if hasattr(self.model2, 'classes_') else set()
        return sorted(list(labels1 | labels2))
    
    def _align_probabilities(self, proba, model_classes):
        """
        Align model probabilities to full label space.
        
        Args:
            proba: Probability array from model (n_samples, n_model_classes)
            model_classes: Classes array from model
            
        Returns:
            Aligned probabilities (n_samples, n_full_classes)
        """
        aligned = np.zeros((proba.shape[0], len(self.full_label_space)))
        for i, label in enumerate(model_classes):
            if label in self.full_label_space:
                idx = self.full_label_space.index(label)
                aligned[:, idx] = proba[:, i]
        return aligned
    
    def _calculate_confidence_metrics(self, proba_array):
        """
        Calculate multiple confidence metrics for probability distributions.
        
        From notebook: max_prob, entropy, margin, gini
        """
        # Max probability
        max_conf = np.max(proba_array, axis=1)
        
        # Entropy-based confidence (lower entropy = higher confidence)
        entropy = -np.sum(proba_array * np.log(proba_array + 1e-10), axis=1)
        entropy_conf = 1 - (entropy / np.log(len(self.full_label_space)))
        
        # Margin confidence (difference between top 2 predictions)
        sorted_proba = np.sort(proba_array, axis=1)
        margin_conf = sorted_proba[:, -1] - sorted_proba[:, -2]
        
        # Gini coefficient
        gini_conf = 1 - np.sum(proba_array ** 2, axis=1)
        gini_conf = 1 - gini_conf  # Invert so higher = more confident
        
        return {
            'max_prob': max_conf,
            'entropy': entropy_conf,
            'margin': margin_conf,
            'gini': gini_conf
        }
    
    def train_meta_learner(self, X_train, y_train, verbose=True):
        """
        Train the meta-learner on training data.
        
        The meta-learner learns to predict optimal weight for model1
        based on confidence metrics and agreement.
        
        Args:
            X_train: Training features
            y_train: Training labels
            verbose: Print training progress
        """
        if verbose:
            print(f"🧠 Training meta-learner for {self.model1_name} + {self.model2_name}...")
        
        # Get predictions from both models
        proba1 = self.model1.predict_proba(X_train)
        proba2 = self.model2.predict_proba(X_train)
        
        # Align to common label space
        aligned1 = self._align_probabilities(proba1, self.model1.classes_)
        aligned2 = self._align_probabilities(proba2, self.model2.classes_)
        
        # Calculate confidence metrics
        conf_metrics1 = self._calculate_confidence_metrics(aligned1)
        conf_metrics2 = self._calculate_confidence_metrics(aligned2)
        
        # Get predictions
        pred1 = np.argmax(aligned1, axis=1)
        pred2 = np.argmax(aligned2, axis=1)
        
        # Agreement: do both models predict the same class?
        agreement = (pred1 == pred2).astype(float)
        
        # KL divergence: how different are the probability distributions?
        kl_div = np.sum(aligned1 * np.log((aligned1 + 1e-10) / (aligned2 + 1e-10)), axis=1)
        
        # Create meta-features (8 features total)
        meta_features = np.column_stack([
            conf_metrics1['max_prob'],     # Model 1 max probability
            conf_metrics1['entropy'],      # Model 1 entropy confidence
            conf_metrics1['margin'],       # Model 1 margin confidence
            conf_metrics2['max_prob'],     # Model 2 max probability
            conf_metrics2['entropy'],      # Model 2 entropy confidence
            conf_metrics2['margin'],       # Model 2 margin confidence
            agreement,                     # Do models agree?
            kl_div                         # How different are distributions?
        ])
        
        # Create target: optimal weight for model 1
        # Map true labels to indices in full label space
        y_true_indices = np.array([self.full_label_space.index(label) for label in y_train])
        
        # Which model predicted correctly?
        acc1 = (pred1 == y_true_indices).astype(float)
        acc2 = (pred2 == y_true_indices).astype(float)
        
        # Target weight: give higher weight to more accurate model
        # If model1 is correct, weight = 0.6-0.9
        # If model2 is correct, weight = 0.1-0.4
        optimal_weights = np.where(
            acc1 >= acc2,
            np.minimum(acc1 + 0.1, 0.9),  # Model 1 better
            np.maximum(acc1 - 0.1, 0.1)   # Model 2 better
        )
        
        # Train Random Forest Regressor as meta-learner
        self.meta_learner = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=10,
            random_state=42,
            n_jobs=-1
        )
        
        self.meta_learner.fit(meta_features, optimal_weights)
        self.is_trained = True
        
        # Evaluate with cross-validation
        if verbose:
            cv_scores = cross_val_score(
                self.meta_learner, meta_features, optimal_weights, 
                cv=5, scoring='r2'
            )
            print(f"   Meta-learner R² Score: {cv_scores.mean():.4f} (±{cv_scores.std()*2:.4f})")
            print(f"   ✓ Meta-learner trained on {len(X_train):,} samples")
        
        return meta_features, optimal_weights
    
    def _predict_weights_with_meta_learner(self, aligned1, aligned2):
        """
        Use meta-learner to predict optimal weights for each sample.
        
        Returns:
            w1, w2: Weights for model1 and model2 (arrays)
        """
        if not self.is_trained:
            raise ValueError("Meta-learner not trained. Call train_meta_learner() first.")
        
        # Calculate same features as during training
        conf_metrics1 = self._calculate_confidence_metrics(aligned1)
        conf_metrics2 = self._calculate_confidence_metrics(aligned2)
        
        pred1 = np.argmax(aligned1, axis=1)
        pred2 = np.argmax(aligned2, axis=1)
        agreement = (pred1 == pred2).astype(float)
        
        kl_div = np.sum(aligned1 * np.log((aligned1 + 1e-10) / (aligned2 + 1e-10)), axis=1)
        
        meta_features = np.column_stack([
            conf_metrics1['max_prob'],
            conf_metrics1['entropy'],
            conf_metrics1['margin'],
            conf_metrics2['max_prob'],
            conf_metrics2['entropy'],
            conf_metrics2['margin'],
            agreement,
            kl_div
        ])
        
        # Predict weights
        w1 = self.meta_learner.predict(meta_features)
        w1 = np.clip(w1, 0.1, 0.9)  # Keep weights reasonable
        w2 = 1 - w1
        
        return w1, w2
    
    def predict(self, X_input, method='meta_learner'):
        """
        Make predictions using the two-model ensemble.
        
        Args:
            X_input: Input features (n_samples, n_features)
            method: 'meta_learner' or 'average' or 'confidence_adaptive'
            
        Returns:
            predictions: Predicted class labels (list)
            confidences: Confidence scores (array)
            metrics: Dictionary with detailed metrics
        """
        # Get probabilities from both models
        proba1 = self.model1.predict_proba(X_input)
        proba2 = self.model2.predict_proba(X_input)
        
        # Align to common label space
        aligned1 = self._align_probabilities(proba1, self.model1.classes_)
        aligned2 = self._align_probabilities(proba2, self.model2.classes_)
        
        # Track individual model confidences
        conf1 = np.max(proba1, axis=1)
        conf2 = np.max(proba2, axis=1)
        self.metrics['model1_confidence'].extend(conf1)
        self.metrics['model2_confidence'].extend(conf2)
        
        # Calculate agreement
        pred1 = np.argmax(aligned1, axis=1)
        pred2 = np.argmax(aligned2, axis=1)
        agreement = (pred1 == pred2)
        self.metrics['agreement_rate'].extend(agreement)
        
        # Choose weighting method
        if method == 'meta_learner':
            if not self.is_trained:
                logger.warning("Meta-learner not trained. Falling back to average.")
                method = 'average'
            else:
                w1, w2 = self._predict_weights_with_meta_learner(aligned1, aligned2)
        
        elif method == 'confidence_adaptive':
            # Simple confidence-based weighting
            total_conf = conf1 + conf2 + 1e-10
            w1 = conf1 / total_conf
            w2 = conf2 / total_conf
        
        else:  # average
            w1 = np.full(len(X_input), 0.5)
            w2 = np.full(len(X_input), 0.5)
        
        # Store weights
        self.metrics['weights_model1'].extend(w1)
        self.metrics['weights_model2'].extend(w2)
        
        # Weighted combination
        combined = (aligned1.T * w1).T + (aligned2.T * w2).T
        
        # Get final predictions
        pred_indices = np.argmax(combined, axis=1)
        predictions = [self.full_label_space[i] for i in pred_indices]
        confidences = np.max(combined, axis=1)
        
        # Track predictions
        for pred in predictions:
            self.metrics['predictions'][pred] += 1
        self.metrics['ensemble_confidence'].extend(confidences)
        
        # Return metrics for this batch
        metrics = {
            'method': method,
            'agreement_rate': np.mean(agreement),
            'avg_confidence': np.mean(confidences),
            'avg_weight_model1': np.mean(w1),
            'avg_weight_model2': np.mean(w2),
            'model1_avg_conf': np.mean(conf1),
            'model2_avg_conf': np.mean(conf2),
        }
        
        return predictions, confidences, metrics
    
    def get_metrics_summary(self) -> Dict:
        """Get comprehensive metrics summary."""
        if not self.metrics['predictions']:
            return {'total_predictions': 0}
        
        return {
            'total_predictions': sum(self.metrics['predictions'].values()),
            'predictions_by_class': dict(self.metrics['predictions']),
            'model1_performance': {
                'name': self.model1_name,
                'avg_confidence': np.mean(self.metrics['model1_confidence']) if self.metrics['model1_confidence'] else 0,
                'avg_weight': np.mean(self.metrics['weights_model1']) if self.metrics['weights_model1'] else 0,
            },
            'model2_performance': {
                'name': self.model2_name,
                'avg_confidence': np.mean(self.metrics['model2_confidence']) if self.metrics['model2_confidence'] else 0,
                'avg_weight': np.mean(self.metrics['weights_model2']) if self.metrics['weights_model2'] else 0,
            },
            'ensemble': {
                'avg_confidence': np.mean(self.metrics['ensemble_confidence']) if self.metrics['ensemble_confidence'] else 0,
                'agreement_rate': np.mean(self.metrics['agreement_rate']) if self.metrics['agreement_rate'] else 0,
            }
        }
    
    def reset_metrics(self):
        """Reset metrics for new experiment."""
        self.metrics = {
            'predictions': defaultdict(int),
            'model1_confidence': [],
            'model2_confidence': [],
            'ensemble_confidence': [],
            'agreement_rate': [],
            'weights_model1': [],
            'weights_model2': [],
        }
