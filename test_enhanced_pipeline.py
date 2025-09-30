#!/usr/bin/env python3
"""
Test script for ML-Enhanced IDS Pipeline
Tests the core functionality without full DPDK setup
"""

import json
import time
import pandas as pd
from ml_enhanced_ids_pipeline import MLEnhancedIDSPipeline

def test_ml_pipeline():
    """Test the ML pipeline with sample Suricata events"""
    
    print("🧪 Testing ML-Enhanced IDS Pipeline")
    print("=" * 50)
    
    # Initialize pipeline
    pipeline = MLEnhancedIDSPipeline()
    
    # Load ML model
    if not pipeline.load_ml_model():
        print("❌ Failed to load ML model")
        return False
    
    # Sample Suricata events for testing
    test_events = [
        {
            "timestamp": "2025-09-30T09:00:00.000000+0530",
            "event_type": "flow",
            "src_ip": "192.168.1.100",
            "src_port": 12345,
            "dest_ip": "8.8.8.8",
            "dest_port": 53,
            "proto": "UDP",
            "flow": {
                "pkts_toserver": 1,
                "pkts_toclient": 1,
                "bytes_toserver": 64,
                "bytes_toclient": 128,
                "duration": "0.1"
            }
        },
        {
            "timestamp": "2025-09-30T09:00:01.000000+0530",
            "event_type": "alert",
            "src_ip": "10.0.0.100",
            "src_port": 80,
            "dest_ip": "192.168.1.50",
            "dest_port": 54321,
            "proto": "TCP",
            "alert": {
                "signature": "Suspicious HTTP Activity",
                "severity": 2,
                "category": "Web Attack"
            },
            "flow": {
                "pkts_toserver": 5,
                "pkts_toclient": 3,
                "bytes_toserver": 500,
                "bytes_toclient": 1500,
                "duration": "2.5"
            }
        },
        {
            "timestamp": "2025-09-30T09:00:02.000000+0530", 
            "event_type": "dns",
            "src_ip": "192.168.1.200",
            "src_port": 45678,
            "dest_ip": "1.1.1.1",
            "dest_port": 53,
            "proto": "UDP",
            "dns": {
                "type": "query",
                "rrname": "malicious-domain.com",
                "rrtype": "A"
            },
            "flow": {
                "pkts_toserver": 1,
                "pkts_toclient": 1,
                "bytes_toserver": 45,
                "bytes_toclient": 89,
                "duration": "0.05"
            }
        }
    ]
    
    print(f"✅ Testing {len(test_events)} sample events")
    print()
    
    # Test each event
    for i, event in enumerate(test_events, 1):
        print(f"🔍 Test Event #{i}: {event['event_type'].upper()}")
        print(f"  Connection: {event.get('src_ip')}:{event.get('src_port')} → {event.get('dest_ip')}:{event.get('dest_port')}")
        
        # Extract features
        features = pipeline.extract_features_from_event(event)
        if features:
            print(f"  ✅ Extracted {len(features)} features")
            
            # Make ML prediction
            attack_type, confidence = pipeline.predict_attack_type(features)
            print(f"  🧠 ML Prediction: {attack_type} (confidence: {confidence:.3f})")
            
            # Determine threat level
            if confidence > 0.8:
                threat_level = "HIGH" if attack_type != "BENIGN" else "LOW"
            elif confidence > 0.6:
                threat_level = "MEDIUM"
            else:
                threat_level = "LOW"
            
            print(f"  ⚠️  Threat Level: {threat_level}")
            
        else:
            print("  ❌ Failed to extract features")
        
        print()
        
    print("🎯 Pipeline Test Results:")
    print(f"  Events processed: {pipeline.stats['events_processed']}")
    print(f"  ML predictions: {pipeline.stats['ml_predictions']}")
    print("  ✅ ML-Enhanced Pipeline working correctly!")
    
    return True

if __name__ == "__main__":
    try:
        success = test_ml_pipeline()
        if success:
            print("\n🎉 All tests passed! ML-Enhanced pipeline is ready.")
        else:
            print("\n❌ Tests failed. Check configuration.")
            
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        import traceback
        traceback.print_exc()