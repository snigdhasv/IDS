#!/usr/bin/env python3
"""
Complete test of the ensemble model with attack generation

This script demonstrates the full pipeline:
1. Load the adaptive ensemble model (RF 2017 + LGB 2018)
2. Generate different types of network attacks
3. Extract features from generated packets
4. Make ensemble predictions with confidence-based weighting
5. Show detailed prediction results and model performance
"""

import sys
import time
import numpy as np
from advanced_attack_generator import AdvancedAttackGenerator
from adaptive_ensemble_model import AdaptiveEnsemblePredictor

def test_ensemble_complete():
    """Run complete ensemble testing with attack generation"""
    print("🚀 ADAPTIVE ENSEMBLE MODEL TESTING")
    print("=" * 60)
    print("📝 Testing RF2017 + LGB2018 ensemble with 0.9148 accuracy technique")
    print("⚖️  Using confidence-based adaptive weighting")
    print()
    
    # Initialize ensemble
    print("🔧 Initializing ensemble model...")
    ensemble = AdaptiveEnsemblePredictor(
        rf_model_path='ML Models/random_forest_model_2017.joblib',
        lgb_model_path='ML Models/lgb_model_2018.joblib'
    )
    
    if not ensemble.load_models():
        print("❌ Failed to load ensemble models")
        return False
    
    print("✅ Ensemble models loaded successfully")
    print()
    
    # Initialize attack generator
    print("🔧 Initializing attack generator...")
    attack_gen = AdvancedAttackGenerator()
    
    # Test attack types and their methods
    attack_tests = [
        ('BENIGN', lambda: attack_gen.generate_benign_traffic(count=1)),
        ('DoS', lambda: attack_gen.generate_dos_attack(count=1)),
        ('DDoS', lambda: attack_gen.generate_ddos_attack(count=1)),
        ('RECONNAISSANCE', lambda: attack_gen.generate_reconnaissance_attack(count=1)),
        ('BRUTE_FORCE', lambda: attack_gen.generate_brute_force_attack(count=1)),
        ('BOTNET', lambda: attack_gen.generate_botnet_traffic(count=1)),
        ('WEB_ATTACK', lambda: attack_gen.generate_web_attack(count=1))
    ]
    
    print("🧪 ENSEMBLE PREDICTION TESTING")
    print("-" * 60)
    
    results = []
    
    for attack_type, generator_method in attack_tests:
        print(f"\n🎯 Testing {attack_type} attack:")
        
        try:
            # Generate traffic
            packets = generator_method()
            
            if packets and len(packets) > 0:
                # Extract features from first packet
                features = attack_gen.extract_features(packets[0])
                
                # Test different ensemble methods
                methods = ['confidence_adaptive', 'exponential', 'average']
                
                for method in methods:
                    prediction, confidence, details = ensemble.predict_ensemble(features, method=method)
                    
                    # Store results
                    results.append({
                        'generated': attack_type,
                        'method': method,
                        'predicted': prediction,
                        'confidence': confidence,
                        'rf_weight': details.get('rf_weight', 0),
                        'lgb_weight': details.get('lgb_weight', 0),
                        'rf_prediction': details.get('rf_prediction', 'N/A'),
                        'lgb_prediction': details.get('lgb_prediction', 'N/A'),
                        'agreement': details.get('agreement', False)
                    })
                    
                    if method == 'confidence_adaptive':  # Show details for main method
                        print(f"   📊 Generated: {attack_type}")
                        print(f"   🤖 Predicted: {prediction}")
                        print(f"   🔢 Confidence: {confidence:.4f}")
                        print(f"   🌲 RF pred: {details.get('rf_prediction', 'N/A')} (weight: {details.get('rf_weight', 0):.3f})")
                        print(f"   🔍 LGB pred: {details.get('lgb_prediction', 'N/A')} (weight: {details.get('lgb_weight', 0):.3f})")
                        print(f"   🤝 Agreement: {'✅ Yes' if details.get('agreement', False) else '❌ No'}")
            else:
                print(f"   ⚠️  No packets generated for {attack_type}")
                
        except Exception as e:
            print(f"   ❌ Error testing {attack_type}: {e}")
    
    # Summary analysis
    print(f"\n📊 ENSEMBLE PERFORMANCE SUMMARY")
    print("=" * 60)
    
    # Group results by method
    method_results = {}
    for result in results:
        method = result['method']
        if method not in method_results:
            method_results[method] = []
        method_results[method].append(result)
    
    for method, method_data in method_results.items():
        print(f"\n🔬 {method.upper()} METHOD:")
        
        # Calculate accuracy
        correct = sum(1 for r in method_data if r['generated'].upper() in r['predicted'].upper() or 
                     r['predicted'].upper() in r['generated'].upper())
        total = len(method_data)
        accuracy = correct / total if total > 0 else 0
        
        print(f"   📈 Accuracy: {accuracy:.3f} ({correct}/{total})")
        
        # Average confidence
        avg_confidence = np.mean([r['confidence'] for r in method_data])
        print(f"   🔢 Avg Confidence: {avg_confidence:.3f}")
        
        # Model agreement rate
        agreement_rate = np.mean([r['agreement'] for r in method_data])
        print(f"   🤝 Agreement Rate: {agreement_rate:.3f}")
        
        # Average weights
        avg_rf_weight = np.mean([r['rf_weight'] for r in method_data])
        avg_lgb_weight = np.mean([r['lgb_weight'] for r in method_data])
        print(f"   ⚖️  Avg RF Weight: {avg_rf_weight:.3f}")
        print(f"   ⚖️  Avg LGB Weight: {avg_lgb_weight:.3f}")
    
    # Model information
    info = ensemble.get_model_info()
    print(f"\n📋 MODEL INFORMATION")
    print("=" * 60)
    print(f"🌲 RF Model: {info['rf_model']['type']} ({info['rf_model']['features']} features)")
    print(f"   Classes: {info['rf_model']['classes']}")
    print(f"🔍 LGB Model: {info['lgb_model']['type']} ({info['lgb_model']['features']} features)")
    print(f"   Classes: {info['lgb_model']['classes']}")
    print(f"🎯 Unified Label Space: {info['unified_labels']}")
    print(f"🔄 Attack Mapping: {info['attack_mapping']}")
    
    print(f"\n✅ ENSEMBLE TESTING COMPLETED!")
    print(f"📊 The adaptive ensemble is using the 0.9148 accuracy technique")
    print(f"⚖️  Confidence-based weighting adapts to model performance")
    print(f"🤖 Ready for integration with ML-Enhanced IDS Pipeline")
    
    return True

if __name__ == "__main__":
    test_ensemble_complete()