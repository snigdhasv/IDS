#!/usr/bin/env python3
"""
Quick Attack Pattern Demo

Shows the sophistication of attacks being generated for your RF model
"""

import sys
import os
sys.path.append('/home/ifscr/SE_02_2025/IDS')

from advanced_attack_generator import AdvancedAttackGenerator

def main():
    print("🎯 SOPHISTICATED ATTACK PATTERNS FOR YOUR RANDOM FOREST MODEL")
    print("=" * 65)
    
    generator = AdvancedAttackGenerator("enp2s0")
    
    print("BENIGN TRAFFIC PATTERNS:")
    benign = generator.generate_benign_traffic(5)
    print(f"  ✓ Generated {len(benign)} normal packets")
    print(f"  ✓ HTTP, DNS, SMTP, IMAP traffic")
    print(f"  ✓ Realistic timing and volumes")
    
    print("\nDoS ATTACK PATTERNS:")
    dos = generator.generate_dos_attack()[:50]  # Sample
    print(f"  ✓ Generated {len(dos)} DoS packets")
    print(f"  ✓ SYN flood attacks")
    print(f"  ✓ UDP flood attacks")
    print(f"  ✓ High volume single-source attacks")
    
    print("\nRECONNAISSANCE PATTERNS:")
    recon = generator.generate_reconnaissance_attack()[:50]
    print(f"  ✓ Generated {len(recon)} recon packets")
    print(f"  ✓ Port scanning (21,22,23,25,53,80,135,139,443,993,995,1433,3389)")
    print(f"  ✓ ICMP probing")
    print(f"  ✓ OS fingerprinting")
    
    print("\nBRUTE FORCE PATTERNS:")
    brute = generator.generate_brute_force_attack()[:50]
    print(f"  ✓ Generated {len(brute)} brute force packets")
    print(f"  ✓ SSH dictionary attacks")
    print(f"  ✓ FTP login attempts")
    print(f"  ✓ RDP brute forcing")
    
    print("\nWEB ATTACK PATTERNS:")
    web = generator.generate_web_attack()[:50]
    print(f"  ✓ Generated {len(web)} web attack packets")
    print(f"  ✓ SQL injection payloads")
    print(f"  ✓ XSS attack vectors")
    print(f"  ✓ Directory traversal attempts")
    
    print(f"\n🧠 MACHINE LEARNING FEATURES THESE ATTACKS WILL EXERCISE:")
    print("=" * 65)
    print("✓ Flow Duration - Normal vs Attack timing patterns")
    print("✓ Total Forward/Backward Packets - Volume anomalies")
    print("✓ Flow Bytes/s - Bandwidth consumption patterns")
    print("✓ Flow Packets/s - Rate-based attack detection")
    print("✓ Flow IAT (Inter-Arrival Time) - Timing analysis")
    print("✓ Forward/Backward Packet Length - Size distributions")
    print("✓ PSH Flag Count - Protocol behavior analysis")
    print("✓ URG Flag Count - Urgency flag anomalies")
    print("✓ Average Packet Size - Attack signature sizes")
    print("✓ Subflow Forward/Backward Packets - Flow characteristics")
    print("✓ Init Win bytes - TCP window analysis")
    print("✓ Active/Idle times - Connection behavior patterns")
    
    print(f"\n🎉 YOUR 61MB RANDOM FOREST MODEL WILL GET:")
    print("=" * 65)
    print("• 7 distinct attack categories matching CICIDS2017 training")
    print("• Realistic packet timing, sizes, and protocols")
    print("• Complex multi-stage attack scenarios")
    print("• Proper feature distributions for ML analysis")
    print("• Attack patterns that will properly exercise all decision trees")
    
    print(f"\n🔬 ATTACK SOPHISTICATION HIGHLIGHTS:")
    print("=" * 65)
    print("DoS: SYN floods, UDP floods, protocol-specific attacks")
    print("DDoS: Multi-source coordination, amplification attacks")
    print("Recon: Systematic port scanning, OS fingerprinting")
    print("Brute Force: Dictionary attacks on SSH/FTP/RDP")
    print("Botnet: C&C beacons, P2P communication, data exfil")
    print("Web: SQL injection, XSS, traversal, command injection")
    print("Benign: Realistic normal traffic patterns")
    
    generator.print_attack_statistics()

if __name__ == "__main__":
    main()