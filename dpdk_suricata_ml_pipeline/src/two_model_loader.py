#!/usr/bin/env python3
"""
Two-Model Loader

Simple interface to load any two models and create an ensemble.
Provides flexibility to choose which models to combine.
"""

import os
import joblib
import logging
from pathlib import Path
from typing import Tuple, List, Optional
from two_model_ensemble import TwoModelEnsemble

logger = logging.getLogger(__name__)

# Default model directory
DEFAULT_MODEL_DIR = "/home/ifscr/SE_02_2025/IDS/ML Models"


def list_available_models(model_dir: str = DEFAULT_MODEL_DIR) -> List[str]:
    """
    List all available model files in the directory.
    
    Returns:
        List of model filenames
    """
    model_path = Path(model_dir)
    if not model_path.exists():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")
    
    models = sorted([f.name for f in model_path.glob("*.joblib")])
    return models


def load_two_models(
    model1_file: str,
    model2_file: str,
    model_dir: str = DEFAULT_MODEL_DIR,
    train_data: Optional[Tuple] = None,
    verbose: bool = True
) -> TwoModelEnsemble:
    """
    Load two models and create an ensemble with meta-learner.
    
    Args:
        model1_file: Filename of first model (e.g., "random_forest_model_2017.joblib")
        model2_file: Filename of second model (e.g., "lgb_model_2018.joblib")
        model_dir: Directory containing model files
        train_data: Optional (X_train, y_train) tuple for training meta-learner
        verbose: Print loading info
        
    Returns:
        TwoModelEnsemble instance
    """
    model_path = Path(model_dir)
    
    # Load models
    model1_path = model_path / model1_file
    model2_path = model_path / model2_file
    
    if not model1_path.exists():
        raise FileNotFoundError(f"Model 1 not found: {model1_path}")
    if not model2_path.exists():
        raise FileNotFoundError(f"Model 2 not found: {model2_path}")
    
    if verbose:
        print(f"📦 Loading models from: {model_dir}")
        print(f"   Model 1: {model1_file}")
        print(f"   Model 2: {model2_file}")
    
    model1 = joblib.load(model1_path)
    model2 = joblib.load(model2_path)
    
    if verbose:
        print(f"   ✓ Models loaded successfully")
    
    # Extract model names (remove .joblib extension)
    model1_name = model1_file.replace(".joblib", "").replace("_model_", "_")
    model2_name = model2_file.replace(".joblib", "").replace("_model_", "_")
    
    # Create ensemble
    ensemble = TwoModelEnsemble(model1, model2, model1_name, model2_name)
    
    # Train meta-learner if training data provided
    if train_data is not None:
        X_train, y_train = train_data
        ensemble.train_meta_learner(X_train, y_train, verbose=verbose)
    
    return ensemble


def interactive_model_selection(model_dir: str = DEFAULT_MODEL_DIR) -> Tuple[str, str]:
    """
    Interactive CLI for selecting two models.
    
    Returns:
        (model1_file, model2_file) tuple
    """
    models = list_available_models(model_dir)
    
    if len(models) < 2:
        raise ValueError(f"Need at least 2 models in directory. Found: {len(models)}")
    
    print("\n" + "="*70)
    print("🎯 TWO-MODEL ENSEMBLE - Select Your Models")
    print("="*70)
    print(f"\nAvailable models in: {model_dir}\n")
    
    for i, model in enumerate(models, 1):
        print(f"  {i}. {model}")
    
    print("\n" + "-"*70)
    
    # Select first model
    while True:
        try:
            choice1 = int(input("\n👉 Select MODEL 1 (enter number): "))
            if 1 <= choice1 <= len(models):
                model1 = models[choice1 - 1]
                break
            print(f"❌ Invalid choice. Enter 1-{len(models)}")
        except (ValueError, KeyboardInterrupt):
            print("\n❌ Cancelled")
            exit(1)
    
    # Select second model
    print(f"\n✓ Model 1: {model1}")
    
    while True:
        try:
            choice2 = int(input(f"👉 Select MODEL 2 (enter number, must differ from {choice1}): "))
            if 1 <= choice2 <= len(models) and choice2 != choice1:
                model2 = models[choice2 - 1]
                break
            if choice2 == choice1:
                print("❌ Model 2 must be different from Model 1")
            else:
                print(f"❌ Invalid choice. Enter 1-{len(models)}")
        except (ValueError, KeyboardInterrupt):
            print("\n❌ Cancelled")
            exit(1)
    
    print(f"\n✓ Model 2: {model2}")
    print("\n" + "="*70)
    print(f"🎯 Selected Ensemble: {model1} + {model2}")
    print("="*70 + "\n")
    
    return model1, model2


if __name__ == "__main__":
    """Test the loader."""
    import sys
    
    # Test with interactive selection
    if len(sys.argv) == 1:
        model1_file, model2_file = interactive_model_selection()
        ensemble = load_two_models(model1_file, model2_file)
        print(f"\n✓ Ensemble created: {ensemble.model1_name} + {ensemble.model2_name}")
        print(f"  Label space: {len(ensemble.full_label_space)} classes")
        print(f"  Meta-learner trained: {ensemble.is_trained}")
    
    # Test with command-line arguments
    elif len(sys.argv) == 3:
        model1_file = sys.argv[1]
        model2_file = sys.argv[2]
        ensemble = load_two_models(model1_file, model2_file)
        print(f"\n✓ Ensemble created: {ensemble.model1_name} + {ensemble.model2_name}")
    
    else:
        print("Usage:")
        print("  python two_model_loader.py                    # Interactive mode")
        print("  python two_model_loader.py model1.joblib model2.joblib  # Direct mode")
