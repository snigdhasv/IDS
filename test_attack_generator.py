#!/usr/bin/env python3
"""
Quick test for the Advanced Attack Generator
Tests each attack type individually to verify ML model can detect them
"""

import sys
import time
import subprocess
import argparse
from advanced_attack_generator import AdvancedAttackGenerator, Colors

def test_attack_type(attack_type, duration=30, rate=20):
    """Test a specific attack type"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}🧪 Testing {attack_type} Attack Generation{Colors.END}")
    print(f"Duration: {duration}s, Rate: {rate} pps")
    
    generator = AdvancedAttackGenerator()
    
    try:
        if attack_type.upper() == 'BENIGN':
            generator.running = True
            generator.generate_benign_traffic(count=duration*rate, rate=rate)
        elif attack_type.upper() == 'DOS':
            generator.running = True
            generator.generate_dos_attack(count=duration*rate, rate=rate)
        elif attack_type.upper() == 'DDOS':
            generator.running = True
            generator.generate_ddos_attack(count=duration*rate, rate=rate)
        elif attack_type.upper() == 'RECONNAISSANCE':
            generator.running = True
            generator.generate_reconnaissance_attack(count=duration*rate)
        elif attack_type.upper() == 'BRUTE_FORCE':
            generator.running = True
            generator.generate_brute_force_attack(count=duration*rate)
        elif attack_type.upper() == 'BOTNET':
            generator.running = True
            generator.generate_botnet_traffic(count=duration*rate)
        elif attack_type.upper() == 'WEB_ATTACK':
            generator.running = True
            generator.generate_web_attack(count=duration*rate)
        else:
            print(f"{Colors.RED}❌ Unknown attack type: {attack_type}{Colors.END}")
            return False
            
        generator._print_final_stats()
        return True
        
    except Exception as e:
        print(f"{Colors.RED}❌ Error testing {attack_type}: {e}{Colors.END}")
        return False
    finally:
        generator.running = False

def test_all_attacks():
    """Test all attack types sequentially"""
    print(f"{Colors.BOLD}{Colors.MAGENTA}🚀 Testing All Attack Types for ML Model Validation{Colors.END}")
    
    attack_types = ['BENIGN', 'DoS', 'DDoS', 'RECONNAISSANCE', 'BRUTE_FORCE', 'BOTNET', 'WEB_ATTACK']
    results = {}
    
    for attack_type in attack_types:
        print(f"\n{'='*60}")
        success = test_attack_type(attack_type, duration=20, rate=10)
        results[attack_type] = success
        
        # Short break between tests
        if attack_type != attack_types[-1]:
            print(f"{Colors.YELLOW}⏸️ Waiting 10 seconds before next test...{Colors.END}")
            time.sleep(10)
    
    # Summary
    print(f"\n{Colors.BOLD}{Colors.BLUE}📊 Test Summary{Colors.END}")
    print("="*40)
    
    for attack_type, success in results.items():
        status = f"{Colors.GREEN}✅ PASS{Colors.END}" if success else f"{Colors.RED}❌ FAIL{Colors.END}"
        print(f"{attack_type:<15}: {status}")
    
    total_passed = sum(results.values())
    print(f"\nTotal: {total_passed}/{len(attack_types)} tests passed")
    
    if total_passed == len(attack_types):
        print(f"{Colors.GREEN}🎉 All attack generators working correctly!{Colors.END}")
        print(f"{Colors.CYAN}Ready for ML model testing with full attack spectrum{Colors.END}")
    else:
        print(f"{Colors.YELLOW}⚠️ Some tests failed. Check error messages above.{Colors.END}")
    
    return total_passed == len(attack_types)

def main():
    parser = argparse.ArgumentParser(description="Test Advanced Attack Generator")
    parser.add_argument("--attack-type", "-a", 
                       choices=['BENIGN', 'DoS', 'DDoS', 'RECONNAISSANCE', 'BRUTE_FORCE', 'BOTNET', 'WEB_ATTACK'],
                       help="Test specific attack type")
    parser.add_argument("--duration", "-d", type=int, default=30, help="Test duration in seconds")
    parser.add_argument("--rate", "-r", type=float, default=20, help="Packet rate (pps)")
    parser.add_argument("--all", action="store_true", help="Test all attack types")
    
    args = parser.parse_args()
    
    # Check root privileges
    import os
    if os.geteuid() != 0:
        print(f"{Colors.RED}❌ Root privileges required for packet injection{Colors.END}")
        print("Please run: sudo python3 test_attack_generator.py")
        sys.exit(1)
    
    try:
        if args.all:
            success = test_all_attacks()
            sys.exit(0 if success else 1)
        elif args.attack_type:
            success = test_attack_type(args.attack_type, args.duration, args.rate)
            sys.exit(0 if success else 1)
        else:
            print(f"{Colors.YELLOW}Please specify --attack-type or --all{Colors.END}")
            parser.print_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⏹️ Test interrupted by user{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()