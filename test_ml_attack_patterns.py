#!/usr/bin/env python3
"""
ML Model Attack Testing Suite

This script demonstrates the sophisticated attack patterns generated for testing
the Random Forest ML model with CICIDS2017-style attack categories.

Shows detailed breakdown of attack features that the ML model will analyze.
"""

import sys
import os
sys.path.append('/home/ifscr/SE_02_2025/IDS')

from advanced_attack_generator import AdvancedAttackGenerator
import random

def analyze_attack_features(packets, attack_type):
    """Analyze the features that ML model will extract from these attacks"""
    
    print(f"\n🔍 {attack_type} Attack Analysis")
    print("=" * 50)
    
    if not packets:
        print("No packets generated for this attack type")
        return
    
    # Sample analysis of first few packets
    sample_packets = packets[:5]
    
    for i, packet in enumerate(sample_packets, 1):
        print(f"\nPacket {i}:")
        
        if packet.haslayer('IP'):
            ip = packet['IP']
            print(f"  Source IP: {ip.src}")
            print(f"  Destination IP: {ip.dst}")
            print(f"  Protocol: {ip.proto}")
            print(f"  Packet Length: {len(packet)} bytes")
            
            if packet.haslayer('TCP'):
                tcp = packet['TCP']
                print(f"  Source Port: {tcp.sport}")
                print(f"  Destination Port: {tcp.dport}")
                print(f"  TCP Flags: {tcp.flags}")
                
                if packet.haslayer('Raw'):
                    payload = packet['Raw'].load
                    print(f"  Payload Length: {len(payload)} bytes")
                    if len(payload) < 100:
                        print(f"  Payload Preview: {payload[:50]}...")
            
            elif packet.haslayer('UDP'):
                udp = packet['UDP']
                print(f"  Source Port: {udp.sport}")
                print(f"  Destination Port: {udp.dport}")
                
                if packet.haslayer('Raw'):
                    payload = packet['Raw'].load
                    print(f"  Payload Length: {len(payload)} bytes")
    
    # ML Feature Analysis
    print(f"\n🧠 ML Features This Attack Will Generate:")
    
    if attack_type == "BENIGN":
        print("  • Normal flow duration patterns")
        print("  • Standard packet sizes (64-1500 bytes)")
        print("  • Typical inter-arrival times")
        print("  • Common port usage (80, 443, 53)")
        print("  • Low connection rates")
        
    elif attack_type == "DoS":
        print("  • HIGH packet rates (1000+ packets)")
        print("  • Same source IP, multiple dest ports")
        print("  • Short flow durations")
        print("  • SYN flood patterns (flags='S')")
        print("  • Large payload sizes in UDP floods")
        print("  • Abnormal packet/second ratios")
        
    elif attack_type == "DDoS":
        print("  • Multiple diverse source IPs")
        print("  • Coordinated timing patterns")
        print("  • Similar payload characteristics")
        print("  • High total flow volume")
        print("  • Distributed port targeting")
        
    elif attack_type == "RECONNAISSANCE":
        print("  • Sequential port scanning (21,22,23,25...)")
        print("  • Short connection attempts")
        print("  • RST/ACK response patterns")
        print("  • Multiple destination IPs in network")
        print("  • ICMP probing patterns")
        print("  • OS fingerprinting signatures")
        
    elif attack_type == "BRUTE_FORCE":
        print("  • Repeated connections to same port (22, 21, 3389)")
        print("  • Failed authentication patterns")
        print("  • Dictionary attack payloads")
        print("  • High connection frequency")
        print("  • SSH/FTP/RDP protocol patterns")
        
    elif attack_type == "BOTNET":
        print("  • Periodic beacon intervals")
        print("  • C&C server communication patterns")
        print("  • Data exfiltration volumes")
        print("  • P2P communication between bots")
        print("  • DNS tunneling for covert channels")
        print("  • Encrypted payload patterns")
        
    elif attack_type == "WEB_ATTACK":
        print("  • SQL injection payload signatures")
        print("  • XSS script patterns in HTTP")
        print("  • Directory traversal attempts")
        print("  • Command injection payloads")
        print("  • Vulnerability scanning patterns")
        print("  • Malicious User-Agent strings")

def main():
    print("🎯 ML Model Attack Testing Suite")
    print("=" * 50)
    print("Generating sophisticated attacks for Random Forest model testing")
    print("Attack categories: BENIGN, DoS, DDoS, RECONNAISSANCE, BRUTE_FORCE, BOTNET, WEB_ATTACK")
    print()
    
    generator = AdvancedAttackGenerator("enp2s0")
    
    # Generate each attack type separately for analysis
    attack_types = {
        "BENIGN": lambda: generator.generate_benign_traffic(20),
        "DoS": lambda: generator.generate_dos_attack()[:50],  # Limit for analysis
        "DDoS": lambda: generator.generate_ddos_attack()[:50],
        "RECONNAISSANCE": lambda: generator.generate_reconnaissance_attack()[:50],
        "BRUTE_FORCE": lambda: generator.generate_brute_force_attack()[:50],
        "BOTNET": lambda: generator.generate_botnet_traffic()[:50],
        "WEB_ATTACK": lambda: generator.generate_web_attack()[:50]
    }
    
    print("🔬 Analyzing Attack Patterns for ML Model:")
    print()
    
    for attack_name, generator_func in attack_types.items():
        packets = generator_func()
        analyze_attack_features(packets, attack_name)
        
        # Show packet count and key characteristics
        if packets:
            src_ips = set()
            dst_ips = set()
            ports = set()
            
            for packet in packets[:20]:  # Sample first 20
                if packet.haslayer('IP'):
                    src_ips.add(packet['IP'].src)
                    dst_ips.add(packet['IP'].dst)
                    
                    if packet.haslayer('TCP'):
                        ports.add(packet['TCP'].dport)
                    elif packet.haslayer('UDP'):
                        ports.add(packet['UDP'].dport)
            
            print(f"\n📊 Attack Statistics:")
            print(f"  Total Packets: {len(packets)}")
            print(f"  Unique Source IPs: {len(src_ips)}")
            print(f"  Unique Destination IPs: {len(dst_ips)}")
            print(f"  Unique Target Ports: {len(ports)}")
            if ports:
                print(f"  Port Range: {sorted(list(ports))[:10]}{'...' if len(ports) > 10 else ''}")
        
        print("\n" + "─" * 70)
    
    # Show overall statistics
    generator.print_attack_statistics()
    
    print(f"\n🎯 ML Model Testing Capabilities:")
    print("✓ Realistic attack timing and volumes")
    print("✓ Diverse source/destination patterns") 
    print("✓ Protocol-specific attack signatures")
    print("✓ Payload-based detection features")
    print("✓ Network behavior anomalies")
    print("✓ Multi-stage attack scenarios")
    
    print(f"\n🧠 Random Forest Features Exercised:")
    print("✓ Flow Duration, Packet Counts, Byte Counts")
    print("✓ Inter-arrival Time Patterns")
    print("✓ Packet Size Distribution")
    print("✓ Flag Combinations (SYN, ACK, RST, etc.)")
    print("✓ Port Scan Indicators")
    print("✓ Connection Rate Anomalies")
    print("✓ Payload Size Variations")
    print("✓ Protocol-specific Patterns")
    
    print(f"\n🎉 Your Random Forest model will receive comprehensive")
    print(f"    feature-rich data covering all 7 attack categories!")

if __name__ == "__main__":
    main()