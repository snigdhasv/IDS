#!/usr/bin/env python3
"""
ML Model Integration Test

Quick test to verify the Random Forest model loads correctly
and can make predictions on sample network data.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

try:
    import joblib
    from sklearn.ensemble import RandomForestClassifier
except ImportError as e:
    print(f"Missing libraries: {e}")
    print("Install with: pip install joblib scikit-learn")
    sys.exit(1)

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def test_ml_model():
    """Test the ML model loading and prediction"""
    
    print(f"{Colors.BOLD}{Colors.BLUE}🧠 ML Model Integration Test{Colors.END}")
    print("=" * 40)
    
    # Model path
    model_path = "/home/ifscr/SE_02_2025/IDS/src/ML_Model/intrusion_detection_model.joblib"
    
    # Check if model exists
    if not Path(model_path).exists():
        print(f"{Colors.RED}❌ Model file not found: {model_path}{Colors.END}")
        return False
    
    file_size = Path(model_path).stat().st_size / (1024 * 1024)  # MB
    print(f"{Colors.GREEN}✓ Model file found ({file_size:.1f} MB){Colors.END}")
    
    try:
        # Load the model
        print(f"{Colors.YELLOW}🔄 Loading Random Forest model...{Colors.END}")
        model = joblib.load(model_path)
        print(f"{Colors.GREEN}✓ Model loaded successfully{Colors.END}")
        
        # Model information
        print(f"  Model type: {type(model).__name__}")
        print(f"  Features expected: {model.n_features_in_}")
        print(f"  Number of classes: {model.n_classes_}")
        print(f"  Number of trees: {model.n_estimators}")
        
        # Test predictions with sample data
        print(f"\n{Colors.YELLOW}🧪 Testing model predictions...{Colors.END}")
        
        # Create sample network features (matching expected input size)
        n_features = model.n_features_in_
        
        # Sample 1: Normal traffic
        normal_sample = np.zeros(n_features).reshape(1, -1)
        normal_sample[0, 0] = 80    # dest_port (HTTP)
        normal_sample[0, 1] = 1234  # src_port
        normal_sample[0, 2] = 6     # TCP protocol
        
        # Sample 2: Suspicious traffic  
        suspicious_sample = np.zeros(n_features).reshape(1, -1)
        suspicious_sample[0, 0] = 22      # dest_port (SSH)
        suspicious_sample[0, 1] = 31337   # suspicious src_port
        suspicious_sample[0, 2] = 6       # TCP protocol
        suspicious_sample[0, 10] = 100    # High connection rate
        suspicious_sample[0, 15] = 50     # Port scan indicator
        
        # Sample 3: Web attack pattern
        web_attack_sample = np.zeros(n_features).reshape(1, -1)
        web_attack_sample[0, 0] = 80      # HTTP port
        web_attack_sample[0, 1] = 666     # suspicious source
        web_attack_sample[0, 2] = 6       # TCP
        web_attack_sample[0, 8] = 2       # POST method
        web_attack_sample[0, 12] = 500    # Long URL
        web_attack_sample[0, 14] = 20     # Suspicious characters
        
        samples = [
            ("Normal HTTP traffic", normal_sample),
            ("Suspicious SSH connection", suspicious_sample), 
            ("Potential web attack", web_attack_sample)
        ]
        
        # Attack type mapping (from your notebook)
        attack_types = {
            0: 'BENIGN',
            1: 'DoS', 
            2: 'DDoS',
            3: 'RECONNAISSANCE',
            4: 'BRUTE_FORCE',
            5: 'BOTNET',
            6: 'WEB_ATTACK'
        }
        
        print(f"\n{Colors.BOLD}Prediction Results:{Colors.END}")
        print("-" * 50)
        
        for i, (description, sample) in enumerate(samples, 1):
            try:
                # Make prediction
                prediction = model.predict(sample)[0]
                probabilities = model.predict_proba(sample)[0]
                confidence = np.max(probabilities)
                
                attack_type = attack_types.get(prediction, f"Class_{prediction}")
                
                # Color based on prediction
                if attack_type == 'BENIGN':
                    color = Colors.GREEN
                    icon = "✅"
                else:
                    color = Colors.RED
                    icon = "🚨"
                
                print(f"{icon} Sample {i}: {description}")
                print(f"   Prediction: {color}{attack_type}{Colors.END}")
                print(f"   Confidence: {confidence:.3f}")
                print(f"   All probabilities: {probabilities[:3]}")  # Show first 3
                print()
                
            except Exception as e:
                print(f"{Colors.RED}❌ Prediction error for sample {i}: {e}{Colors.END}")
                return False
        
        print(f"{Colors.GREEN}✅ All ML model tests passed!{Colors.END}")
        print(f"\n{Colors.BLUE}🎯 Model is ready for integration with IDS pipeline{Colors.END}")
        return True
        
    except Exception as e:
        print(f"{Colors.RED}❌ Model loading error: {e}{Colors.END}")
        return False

def main():
    success = test_ml_model()
    if success:
        print(f"\n{Colors.BOLD}Next steps:{Colors.END}")
        print("1. Run the ML-enhanced pipeline: sudo ./ml_enhanced_pipeline.sh")
        print("2. Monitor ML alerts: python3 ml_alert_consumer.py")
        print("3. Generate test traffic to see ML predictions in action")
    else:
        print(f"\n{Colors.RED}Fix the issues above before running the ML pipeline{Colors.END}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())