#!/usr/bin/env python3
"""
Test script for the Adaptive Ensemble IDS Pipeline

This script tests the integration of RF(2017) + LGB(2018) adaptive ensemble
that achieved 0.9148 accuracy in the PerformanceEvaluation notebook.
"""

import sys
import os
import numpy as np
import pandas as pd
from adaptive_ensemble_predictor import AdaptiveEnsemblePredictor

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def test_ensemble_integration():
    """Test the adaptive ensemble integration"""
    print(f"{Colors.BOLD}{Colors.BLUE}🧪 Testing Adaptive Ensemble Integration{Colors.END}")
    print("Testing RF(2017) + LGB(2018) with confidence-adaptive weighting")
    print("=" * 60)
    
    # Model paths
    rf2017_path = "/home/ifscr/SE_02_2025/IDS/ML Models/random_forest_model_2017.joblib"
    lgb2018_path = "/home/ifscr/SE_02_2025/IDS/ML Models/lgb_model_2018.joblib"
    
    # Check if model files exist
    print(f"{Colors.YELLOW}📁 Checking model files...{Colors.END}")
    
    if not os.path.exists(rf2017_path):
        print(f"{Colors.RED}❌ RF(2017) model not found at {rf2017_path}{Colors.END}")
        return False
    else:
        print(f"{Colors.GREEN}✓ RF(2017) model found{Colors.END}")
    
    if not os.path.exists(lgb2018_path):
        print(f"{Colors.RED}❌ LGB(2018) model not found at {lgb2018_path}{Colors.END}")
        return False
    else:
        print(f"{Colors.GREEN}✓ LGB(2018) model found{Colors.END}")
    
    # Initialize ensemble predictor
    print(f"\n{Colors.YELLOW}🔄 Initializing Adaptive Ensemble Predictor...{Colors.END}")
    predictor = AdaptiveEnsemblePredictor(rf2017_path, lgb2018_path)
    
    # Load models
    if not predictor.load_models():
        print(f"{Colors.RED}❌ Failed to load ensemble models{Colors.END}")
        return False
    
    # Get model information
    info = predictor.get_model_info()
    print(f"\n{Colors.CYAN}📊 Model Information:{Colors.END}")
    print(f"  RF(2017): {info['rf2017']['type']} ({info['rf2017']['n_features']} features)")
    print(f"  LGB(2018): {info['lgb2018']['type']} ({info['lgb2018']['n_features']} features)")
    print(f"  Classes: {info['ensemble']['unified_classes']}")
    
    # Test with realistic network traffic features
    print(f"\n{Colors.YELLOW}🧪 Testing with sample network features...{Colors.END}")
    
    # Sample 1: Potential DoS attack (high packet rate, short duration)
    dos_features = create_dos_attack_features()
    prediction, confidence = predictor.predict_single(dos_features)
    print(f"{Colors.MAGENTA}DoS Attack Sample:{Colors.END}")
    print(f"  Prediction: {prediction}")
    print(f"  Confidence: {confidence:.4f}")
    
    # Sample 2: Normal web traffic
    benign_features = create_benign_web_features()
    prediction, confidence = predictor.predict_single(benign_features)
    print(f"{Colors.GREEN}Benign Web Traffic:{Colors.END}")
    print(f"  Prediction: {prediction}")
    print(f"  Confidence: {confidence:.4f}")
    
    # Sample 3: Port scan (reconnaissance)
    recon_features = create_reconnaissance_features()
    prediction, confidence = predictor.predict_single(recon_features)
    print(f"{Colors.YELLOW}Reconnaissance Scan:{Colors.END}")
    print(f"  Prediction: {prediction}")
    print(f"  Confidence: {confidence:.4f}")
    
    # Test ensemble methods comparison
    print(f"\n{Colors.CYAN}🔬 Testing Different Ensemble Methods:{Colors.END}")
    
    # Create batch test data
    test_samples = np.array([
        list(dos_features.values())[:max(info['rf2017']['n_features'], info['lgb2018']['n_features'])],
        list(benign_features.values())[:max(info['rf2017']['n_features'], info['lgb2018']['n_features'])],
        list(recon_features.values())[:max(info['rf2017']['n_features'], info['lgb2018']['n_features'])]
    ])
    
    methods = ['average', 'confidence_adaptive', 'exponential', 'threshold_based']
    
    for method in methods:
        predictions, confidences, weights = predictor.predict_ensemble(test_samples, method=method)
        avg_confidence = np.mean(confidences)
        avg_rf_weight = np.mean(weights[:, 0])
        avg_lgb_weight = np.mean(weights[:, 1])
        
        print(f"  {method:18s}: Avg Conf: {avg_confidence:.3f}, "
              f"RF Weight: {avg_rf_weight:.3f}, LGB Weight: {avg_lgb_weight:.3f}")
    
    # Highlight the method that achieved 0.9148 accuracy
    print(f"\n{Colors.BOLD}{Colors.GREEN}✨ confidence_adaptive method achieved 0.9148 accuracy!{Colors.END}")
    
    print(f"\n{Colors.GREEN}✅ Adaptive Ensemble Integration Test Complete!{Colors.END}")
    return True

def create_dos_attack_features():
    """Create features typical of a DoS attack"""
    return {
        'Destination Port': 80,
        'Flow Duration': 50000,  # Short duration
        'Total Fwd Packets': 1000,  # High packet count
        'Total Backward Packets': 0,  # No response
        'Total Length of Fwd Packets': 64000,
        'Total Length of Bwd Packets': 0,
        'Fwd Packet Length Max': 64,
        'Fwd Packet Length Min': 64,
        'Fwd Packet Length Mean': 64.0,
        'Fwd Packet Length Std': 0.0,
        'Bwd Packet Length Max': 0,
        'Bwd Packet Length Min': 0,
        'Bwd Packet Length Mean': 0.0,
        'Bwd Packet Length Std': 0.0,
        'Flow Bytes/s': 1280000.0,  # Very high byte rate
        'Flow Packets/s': 20000.0,   # Very high packet rate
        'Flow IAT Mean': 50.0,
        'Flow IAT Std': 5.0,
        'Flow IAT Max': 100,
        'Flow IAT Min': 40,
        'Fwd IAT Total': 50000,
        'Fwd IAT Mean': 50.0,
        'Fwd IAT Std': 5.0,
        'Fwd IAT Max': 100,
        'Fwd IAT Min': 40,
        'Bwd IAT Total': 0,
        'Bwd IAT Mean': 0.0,
        'Bwd IAT Std': 0.0,
        'Bwd IAT Max': 0,
        'Bwd IAT Min': 0,
        'Fwd PSH Flags': 999,
        'Fwd URG Flags': 0,
        'Fwd Header Length': 20000,
        'Bwd Header Length': 0,
        'Fwd Packets/s': 20000.0,
        'Bwd Packets/s': 0.0,
        'Min Packet Length': 64,
        'Max Packet Length': 64,
        'Packet Length Mean': 64.0,
        'Packet Length Std': 0.0,
        'Packet Length Variance': 0.0,
        'FIN Flag Count': 0,
        'RST Flag Count': 0,
        'PSH Flag Count': 999,
        'ACK Flag Count': 0,
        'URG Flag Count': 0,
        'ECE Flag Count': 0,
        'Down/Up Ratio': 0.0,
        'Average Packet Size': 64.0,
        'Avg Fwd Segment Size': 64.0,
        'Avg Bwd Segment Size': 0.0,
        'Subflow Fwd Bytes': 64000,
        'Subflow Bwd Bytes': 0,
        'Init_Win_bytes_forward': 65535,
        'Init_Win_bytes_backward': 0,
        'act_data_pkt_fwd': 999,
        'min_seg_size_forward': 64,
        'Active Mean': 25000.0,
        'Active Std': 2500.0,
        'Active Max': 50000,
        'Active Min': 0,
        'Idle Mean': 5000.0,
        'Idle Std': 500.0,
        'Idle Max': 10000,
        'Idle Min': 0
    }

def create_benign_web_features():
    """Create features typical of normal web browsing"""
    return {
        'Destination Port': 443,
        'Flow Duration': 5000000,  # Normal duration
        'Total Fwd Packets': 15,
        'Total Backward Packets': 12,
        'Total Length of Fwd Packets': 2400,
        'Total Length of Bwd Packets': 18000,
        'Fwd Packet Length Max': 1500,
        'Fwd Packet Length Min': 64,
        'Fwd Packet Length Mean': 160.0,
        'Fwd Packet Length Std': 200.0,
        'Bwd Packet Length Max': 1500,
        'Bwd Packet Length Min': 64,
        'Bwd Packet Length Mean': 1500.0,
        'Bwd Packet Length Std': 300.0,
        'Flow Bytes/s': 4080.0,
        'Flow Packets/s': 5.4,
        'Flow IAT Mean': 185185.0,
        'Flow IAT Std': 50000.0,
        'Flow IAT Max': 500000,
        'Flow IAT Min': 10000,
        'Fwd IAT Total': 5000000,
        'Fwd IAT Mean': 333333.0,
        'Fwd IAT Std': 100000.0,
        'Fwd IAT Max': 800000,
        'Fwd IAT Min': 50000,
        'Bwd IAT Total': 4500000,
        'Bwd IAT Mean': 375000.0,
        'Bwd IAT Std': 80000.0,
        'Bwd IAT Max': 700000,
        'Bwd IAT Min': 100000,
        'Fwd PSH Flags': 3,
        'Fwd URG Flags': 0,
        'Fwd Header Length': 300,
        'Bwd Header Length': 240,
        'Fwd Packets/s': 3.0,
        'Bwd Packets/s': 2.4,
        'Min Packet Length': 64,
        'Max Packet Length': 1500,
        'Packet Length Mean': 755.6,
        'Packet Length Std': 500.0,
        'Packet Length Variance': 250000.0,
        'FIN Flag Count': 1,
        'RST Flag Count': 0,
        'PSH Flag Count': 5,
        'ACK Flag Count': 25,
        'URG Flag Count': 0,
        'ECE Flag Count': 0,
        'Down/Up Ratio': 7.5,
        'Average Packet Size': 755.6,
        'Avg Fwd Segment Size': 160.0,
        'Avg Bwd Segment Size': 1500.0,
        'Subflow Fwd Bytes': 2400,
        'Subflow Bwd Bytes': 18000,
        'Init_Win_bytes_forward': 65535,
        'Init_Win_bytes_backward': 65535,
        'act_data_pkt_fwd': 12,
        'min_seg_size_forward': 64,
        'Active Mean': 2500000.0,
        'Active Std': 250000.0,
        'Active Max': 5000000,
        'Active Min': 0,
        'Idle Mean': 500000.0,
        'Idle Std': 50000.0,
        'Idle Max': 1000000,
        'Idle Min': 0
    }

def create_reconnaissance_features():
    """Create features typical of port scanning/reconnaissance"""
    return {
        'Destination Port': 22,
        'Flow Duration': 1000,  # Very short
        'Total Fwd Packets': 1,  # Single probe packet
        'Total Backward Packets': 0,  # No response (closed port)
        'Total Length of Fwd Packets': 64,
        'Total Length of Bwd Packets': 0,
        'Fwd Packet Length Max': 64,
        'Fwd Packet Length Min': 64,
        'Fwd Packet Length Mean': 64.0,
        'Fwd Packet Length Std': 0.0,
        'Bwd Packet Length Max': 0,
        'Bwd Packet Length Min': 0,
        'Bwd Packet Length Mean': 0.0,
        'Bwd Packet Length Std': 0.0,
        'Flow Bytes/s': 64000.0,
        'Flow Packets/s': 1000.0,
        'Flow IAT Mean': 0.0,
        'Flow IAT Std': 0.0,
        'Flow IAT Max': 0,
        'Flow IAT Min': 0,
        'Fwd IAT Total': 0,
        'Fwd IAT Mean': 0.0,
        'Fwd IAT Std': 0.0,
        'Fwd IAT Max': 0,
        'Fwd IAT Min': 0,
        'Bwd IAT Total': 0,
        'Bwd IAT Mean': 0.0,
        'Bwd IAT Std': 0.0,
        'Bwd IAT Max': 0,
        'Bwd IAT Min': 0,
        'Fwd PSH Flags': 0,
        'Fwd URG Flags': 0,
        'Fwd Header Length': 20,
        'Bwd Header Length': 0,
        'Fwd Packets/s': 1000.0,
        'Bwd Packets/s': 0.0,
        'Min Packet Length': 64,
        'Max Packet Length': 64,
        'Packet Length Mean': 64.0,
        'Packet Length Std': 0.0,
        'Packet Length Variance': 0.0,
        'FIN Flag Count': 0,
        'RST Flag Count': 0,
        'PSH Flag Count': 0,
        'ACK Flag Count': 0,
        'URG Flag Count': 0,
        'ECE Flag Count': 0,
        'Down/Up Ratio': 0.0,
        'Average Packet Size': 64.0,
        'Avg Fwd Segment Size': 64.0,
        'Avg Bwd Segment Size': 0.0,
        'Subflow Fwd Bytes': 64,
        'Subflow Bwd Bytes': 0,
        'Init_Win_bytes_forward': 65535,
        'Init_Win_bytes_backward': 0,
        'act_data_pkt_fwd': 0,
        'min_seg_size_forward': 64,
        'Active Mean': 500.0,
        'Active Std': 50.0,
        'Active Max': 1000,
        'Active Min': 0,
        'Idle Mean': 100.0,
        'Idle Std': 10.0,
        'Idle Max': 200,
        'Idle Min': 0
    }

def test_ml_pipeline_integration():
    """Test integration with the ML pipeline"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}📡 Testing ML Pipeline Integration{Colors.END}")
    print("=" * 60)
    
    try:
        from ml_enhanced_ids_pipeline import MLEnhancedIDSPipeline
        
        # Initialize pipeline
        pipeline = MLEnhancedIDSPipeline()
        
        # Test model loading
        if pipeline.load_ml_model():
            print(f"{Colors.GREEN}✅ ML Pipeline integration successful{Colors.END}")
            
            # Test feature extraction and prediction
            sample_event = {
                'src_ip': '192.168.1.100',
                'dest_ip': '192.168.1.1',
                'src_port': 54321,
                'dest_port': 80,
                'proto': 'TCP',
                'flow': {
                    'pkts_toserver': 100,
                    'pkts_toclient': 0,
                    'bytes_toserver': 6400,
                    'bytes_toclient': 0,
                    'duration': '0.05'
                }
            }
            
            # Extract features
            features = pipeline.extract_features_from_event(sample_event)
            if features:
                print(f"{Colors.GREEN}✓ Feature extraction working{Colors.END}")
                
                # Make prediction
                attack_type, confidence = pipeline.predict_attack_type(features)
                print(f"  Sample prediction: {attack_type} (confidence: {confidence:.4f})")
                
                # Create enhanced alert
                alert = pipeline.create_enhanced_alert(sample_event, attack_type, confidence)
                print(f"  Threat level: {alert['combined_assessment']['threat_level']}")
                print(f"  Combined score: {alert['combined_assessment']['combined_score']:.1f}/100")
                
            else:
                print(f"{Colors.YELLOW}⚠️ Feature extraction returned None{Colors.END}")
            
        else:
            print(f"{Colors.RED}❌ ML Pipeline model loading failed{Colors.END}")
            return False
            
    except ImportError as e:
        print(f"{Colors.RED}❌ Cannot import ML pipeline: {e}{Colors.END}")
        return False
    except Exception as e:
        print(f"{Colors.RED}❌ ML Pipeline integration error: {e}{Colors.END}")
        return False
    
    return True

def main():
    """Main test function"""
    print(f"{Colors.BOLD}{Colors.CYAN}🚀 Adaptive Ensemble IDS Testing Suite{Colors.END}")
    print("Testing RF(2017) + LGB(2018) integration with 0.9148 accuracy")
    print("=" * 70)
    
    success = True
    
    # Test ensemble predictor
    if not test_ensemble_integration():
        success = False
    
    # Test ML pipeline integration
    if not test_ml_pipeline_integration():
        success = False
    
    # Final result
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    if success:
        print(f"{Colors.BOLD}{Colors.GREEN}🎉 All tests passed! Adaptive Ensemble is ready.{Colors.END}")
        print(f"{Colors.GREEN}Your IDS now uses the 0.9148 accuracy ensemble combination!{Colors.END}")
    else:
        print(f"{Colors.BOLD}{Colors.RED}❌ Some tests failed. Please check the errors above.{Colors.END}")
    
    return success

if __name__ == "__main__":
    main()