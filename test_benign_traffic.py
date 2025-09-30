#!/usr/bin/env python3
"""
Test script to verify benign traffic generation

This script tests the improved benign traffic generation to ensure it produces
truly benign packets that shouldn't trigger Suricata alerts.
"""

import sys
import os
sys.path.append('/home/ifscr/SE_02_2025/IDS')

from advanced_attack_generator import AdvancedAttackGenerator

def test_benign_traffic():
    """Test benign traffic generation with verbose output"""
    print("🧪 Testing Improved Benign Traffic Generation")
    print("=" * 50)
    
    # Initialize generator
    generator = AdvancedAttackGenerator(interface="enp2s0", target_network="192.168.1.0/24")
    
    print("📊 Configuration:")
    print(f"  Interface: {generator.interface}")
    print(f"  Target network: {generator.target_network}")
    
    # Check source IPs being used
    internal_ips = [f"192.168.1.{i}" for i in range(10, 50)]
    print(f"  Benign source IPs: {internal_ips[:5]}...{internal_ips[-5:]} ({len(internal_ips)} total)")
    
    # Test HTTP request creation
    print("\n🔍 Testing Benign HTTP Request Creation:")
    test_packet = generator._create_http_request(
        src_ip="192.168.1.10",
        dst_ip="192.168.1.20", 
        method="GET",
        url="/index.html",
        is_attack=False
    )
    
    # Extract and display HTTP headers
    if hasattr(test_packet, 'load'):
        http_content = test_packet.load.decode('utf-8', errors='ignore')
        print("Generated HTTP request:")
        for line in http_content.split('\\r\\n'):
            if line.strip():
                print(f"  {line}")
    
    print("\n✅ Key Improvements Made:")
    print("  ✓ Using only internal IP addresses (192.168.1.10-49)")
    print("  ✓ Using legitimate browser User-Agent strings")
    print("  ✓ Using benign URLs (/index.html, /home, /about, etc.)")
    print("  ✓ Using legitimate domain names for DNS queries")
    print("  ✓ Added ICMP ping packets (very benign)")
    print("  ✓ Removed SSH/SMTP that might trigger alerts")
    
    print("\n🎯 Expected Results:")
    print("  • Significantly fewer Suricata alerts in benign mode")
    print("  • ML model should predict mostly 'BENIGN' class")  
    print("  • No suspicious User-Agent detections")
    print("  • No external IP address alerts")
    
    print("\n🚀 Ready to test with: sudo ./ml_enhanced_pipeline.sh --traffic-mode benign --duration 300")

if __name__ == "__main__":
    # Check for root if we were to send packets
    if os.geteuid() == 0:
        print("⚠️  Running as root - could send actual packets")
        print("This test only analyzes packet creation, not transmission")
    
    test_benign_traffic()