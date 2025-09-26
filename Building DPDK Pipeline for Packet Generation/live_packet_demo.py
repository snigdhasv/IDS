#!/usr/bin/env python3
"""
Live Packet Sending Demo

This script demonstrates actual packet transmission using your connected NIC.
It will send packets over the network interface enp2s0.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scapy.all import *
from packet_generator import *
import time
import subprocess
from threading import Thread

def check_interface_status():
    """Check if the target interface is available and active"""
    try:
        result = subprocess.run(['ip', 'link', 'show', 'enp2s0'], 
                              capture_output=True, text=True)
        if 'UP' in result.stdout:
            print("✅ Interface enp2s0 is UP and ready")
            return True
        else:
            print("❌ Interface enp2s0 is not UP")
            return False
    except Exception as e:
        print(f"❌ Error checking interface: {e}")
        return False

def send_test_packets_live():
    """Send actual packets using the network interface"""
    print("=" * 60)
    print("LIVE PACKET TRANSMISSION DEMO")
    print("=" * 60)
    
    if not check_interface_status():
        print("Cannot proceed - interface not available")
        return
    
    # Use your actual network configuration
    my_ip = "10.1.12.45"  # Your actual IP
    target_ip = "8.8.8.8"  # Google DNS (safe target)
    interface = "enp2s0"   # Your actual interface
    
    print(f"\n🔧 Configuration:")
    print(f"   Source IP: {my_ip}")
    print(f"   Target IP: {target_ip}")
    print(f"   Interface: {interface}")
    
    # Create different types of packets
    packets_to_send = []
    
    print(f"\n📦 Creating test packets...")
    
    # 1. ICMP Ping packet (safe)
    icmp_pkt = IP(src=my_ip, dst=target_ip) / ICMP()
    packets_to_send.append(("ICMP Ping", icmp_pkt))
    
    # 2. UDP packet to DNS port (safe)
    udp_pkt = IP(src=my_ip, dst=target_ip) / UDP(sport=12345, dport=53) / Raw(b"test")
    packets_to_send.append(("UDP DNS Query", udp_pkt))
    
    # 3. TCP SYN packet (safe)
    tcp_pkt = IP(src=my_ip, dst=target_ip) / TCP(sport=12345, dport=80, flags="S")
    packets_to_send.append(("TCP SYN", tcp_pkt))
    
    # Display packet details
    for name, pkt in packets_to_send:
        print(f"   ✓ {name}: {pkt.summary()}")
    
    print(f"\n⚠️  WARNING: This will send actual packets on your network!")
    print(f"   Target: {target_ip} (Google DNS - safe)")
    print(f"   Interface: {interface}")
    
    # Ask for confirmation
    response = input("\n❓ Do you want to proceed? (yes/no): ").lower().strip()
    
    if response not in ['yes', 'y']:
        print("❌ Aborted by user")
        return
    
    print(f"\n🚀 Sending packets...")
    
    # Send packets one by one
    for name, pkt in packets_to_send:
        try:
            print(f"   📤 Sending {name}...")
            
            # Send the packet using Scapy
            send(pkt, iface=interface, verbose=0)
            
            print(f"   ✅ {name} sent successfully")
            time.sleep(0.5)  # Small delay between packets
            
        except Exception as e:
            print(f"   ❌ Failed to send {name}: {e}")
    
    print(f"\n✅ Packet transmission complete!")

def monitor_traffic_while_sending():
    """Monitor network traffic while sending packets"""
    print("\n" + "=" * 60)
    print("LIVE TRAFFIC MONITORING + PACKET SENDING")
    print("=" * 60)
    
    if not check_interface_status():
        return
    
    print("This will:")
    print("1. Start monitoring network traffic on enp2s0")
    print("2. Send test packets")
    print("3. Show you the packets being transmitted")
    
    response = input("\n❓ Proceed with live monitoring demo? (yes/no): ").lower().strip()
    if response not in ['yes', 'y']:
        print("❌ Aborted")
        return
    
    try:
        print(f"\n🔍 Method 1: Using tcpdump (if available)")
        
        # Try tcpdump first - but we're already running as root
        monitor_cmd = [
            'tcpdump', 
            '-i', 'enp2s0',
            '-c', '5',  # Capture just 5 packets
            '-v',       # Verbose output
            '-n',       # Don't resolve hostnames
            'host', '8.8.8.8'  # Only packets to/from 8.8.8.8
        ]
        
        print(f"   Starting monitor: {' '.join(monitor_cmd)}")
        
        # Start monitoring
        monitor_process = subprocess.Popen(
            monitor_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give tcpdump time to start
        time.sleep(2)
        print("   🎯 Monitor started, now sending packets...")
        
        # Now send packets
        my_ip = "10.1.12.45"
        target_ip = "8.8.8.8"
        
        print(f"\n📤 Sending test packets to {target_ip}...")
        
        # Send ICMP ping
        print("   📤 Sending ICMP ping...")
        icmp_pkt = IP(src=my_ip, dst=target_ip) / ICMP()
        send(icmp_pkt, verbose=0)
        time.sleep(0.5)
        
        # Send UDP packet
        print("   📤 Sending UDP packet...")
        udp_pkt = IP(src=my_ip, dst=target_ip) / UDP(sport=12345, dport=53) / Raw(b"test")
        send(udp_pkt, verbose=0)
        time.sleep(0.5)
        
        # Send TCP packet
        print("   📤 Sending TCP SYN...")
        tcp_pkt = IP(src=my_ip, dst=target_ip) / TCP(sport=12345, dport=80, flags="S")
        send(tcp_pkt, verbose=0)
        time.sleep(0.5)
        
        print("   ⏳ Waiting for tcpdump to finish capturing...")
        
        # Wait for monitor to complete
        try:
            stdout, stderr = monitor_process.communicate(timeout=15)
            
            print(f"\n📊 Captured Traffic:")
            print("=" * 50)
            if stdout.strip():
                print("CAPTURED PACKETS:")
                print(stdout)
            else:
                print("No packets captured in stdout")
            
            if stderr.strip():
                print("\nTCPDUMP STATUS:")
                # Filter out normal tcpdump startup messages
                error_lines = [line for line in stderr.split('\n') if line.strip() and 
                             not any(x in line.lower() for x in ['listening on', 'link-type', 'capture size'])]
                if error_lines:
                    print('\n'.join(error_lines))
                else:
                    print("tcpdump completed normally")
                    
        except subprocess.TimeoutExpired:
            print("   ⏰ tcpdump timeout - killing process")
            monitor_process.kill()
            monitor_process.wait()
        
        # Alternative method: Check interface statistics
        print(f"\n🔍 Method 2: Interface Statistics Check")
        print("=" * 50)
        
        try:
            # Read interface stats before
            with open('/proc/net/dev', 'r') as f:
                before_stats = f.read()
            
            print("   📤 Sending additional test packets...")
            
            # Send a few more packets
            for i in range(3):
                ping_pkt = IP(dst="8.8.8.8") / ICMP()
                send(ping_pkt, verbose=0)
                time.sleep(0.2)
            
            time.sleep(1)
            
            # Read interface stats after
            with open('/proc/net/dev', 'r') as f:
                after_stats = f.read()
            
            # Parse and compare stats
            def parse_interface_stats(stats_text, interface='enp2s0'):
                for line in stats_text.split('\n'):
                    if interface + ':' in line:
                        parts = line.split()
                        if len(parts) >= 10:
                            return {
                                'rx_packets': int(parts[2]),
                                'tx_packets': int(parts[10]),
                                'rx_bytes': int(parts[1]),
                                'tx_bytes': int(parts[9])
                            }
                return None
            
            before = parse_interface_stats(before_stats)
            after = parse_interface_stats(after_stats)
            
            if before and after:
                tx_diff = after['tx_packets'] - before['tx_packets']
                rx_diff = after['rx_packets'] - before['rx_packets']
                
                print(f"   📊 Interface Statistics Change:")
                print(f"      TX packets increased by: {tx_diff}")
                print(f"      RX packets increased by: {rx_diff}")
                
                if tx_diff > 0:
                    print(f"   ✅ Successfully detected outgoing packets!")
                else:
                    print(f"   ⚠️  No TX packet change detected")
            else:
                print("   ❌ Could not parse interface statistics")
                
        except Exception as e:
            print(f"   ❌ Error checking interface stats: {e}")
        
        # Method 3: Use scapy's sniff function
        print(f"\n🔍 Method 3: Scapy Packet Sniffing")
        print("=" * 50)
        
        try:
            print("   🎯 Starting scapy sniffer for 5 seconds...")
            
            captured_packets = []
            
            def packet_handler(pkt):
                if IP in pkt and (pkt[IP].src == "10.1.12.45" or pkt[IP].dst == "10.1.12.45"):
                    captured_packets.append(pkt)
                    print(f"      📦 Captured: {pkt.summary()}")
            
            # Start sniffing in background
            def sniff_packets():
                sniff(iface="enp2s0", prn=packet_handler, timeout=3, store=0)
            
            sniffer_thread = Thread(target=sniff_packets)
            sniffer_thread.start()
            
            # Give sniffer time to start
            time.sleep(0.5)
            
            print("   📤 Sending packets while sniffing...")
            
            # Send packets while sniffing
            for i in range(2):
                test_pkt = IP(dst="8.8.8.8") / ICMP()
                send(test_pkt, verbose=0)
                time.sleep(0.5)
            
            # Wait for sniffer to complete
            sniffer_thread.join()
            
            if captured_packets:
                print(f"   ✅ Scapy captured {len(captured_packets)} packets!")
                for i, pkt in enumerate(captured_packets[:3]):  # Show first 3
                    print(f"      {i+1}. {pkt.summary()}")
            else:
                print("   ⚠️  Scapy didn't capture any packets")
                
        except Exception as e:
            print(f"   ❌ Error with scapy sniffing: {e}")
            
    except Exception as e:
        print(f"❌ Error during monitoring: {e}")

def simple_packet_monitor():
    """Simple packet monitoring without tcpdump"""
    print("\n" + "=" * 60)
    print("SIMPLE PACKET MONITORING")
    print("=" * 60)
    
    print("This method uses interface statistics to detect packet transmission")
    
    try:
        print("🔍 Reading initial interface statistics...")
        
        # Read initial stats
        with open('/proc/net/dev', 'r') as f:
            initial_stats = f.read()
        
        def get_interface_stats(stats_text):
            for line in stats_text.split('\n'):
                if 'enp2s0:' in line:
                    parts = line.split()
                    if len(parts) >= 10:
                        return {
                            'rx_packets': int(parts[2]),
                            'tx_packets': int(parts[10]),
                            'rx_bytes': int(parts[1]),
                            'tx_bytes': int(parts[9])
                        }
            return None
        
        initial = get_interface_stats(initial_stats)
        if not initial:
            print("❌ Could not read interface statistics")
            return
        
        print(f"📊 Initial stats - TX: {initial['tx_packets']} packets, RX: {initial['rx_packets']} packets")
        
        input("\n⏸️  Press Enter to send test packets...")
        
        print("📤 Sending 5 test packets...")
        
        # Send test packets
        for i in range(5):
            pkt = IP(dst="8.8.8.8") / ICMP()
            send(pkt, verbose=0)
            print(f"   ✅ Packet {i+1} sent")
            time.sleep(0.5)
        
        time.sleep(2)  # Wait for stats to update
        
        # Read final stats
        with open('/proc/net/dev', 'r') as f:
            final_stats = f.read()
        
        final = get_interface_stats(final_stats)
        if final:
            tx_diff = final['tx_packets'] - initial['tx_packets']
            rx_diff = final['rx_packets'] - initial['rx_packets']
            
            print(f"\n📊 Final Results:")
            print(f"   TX packets sent: {tx_diff}")
            print(f"   RX packets received: {rx_diff}")
            
            if tx_diff >= 5:
                print("   ✅ SUCCESS: All packets were transmitted!")
            elif tx_diff > 0:
                print(f"   ⚠️  PARTIAL: Only {tx_diff} packets detected")
            else:
                print("   ❌ FAILED: No packet transmission detected")
        else:
            print("❌ Could not read final statistics")
            
    except Exception as e:
        print(f"❌ Error in simple monitoring: {e}")

def main():
    """Main demo function"""
    print("🌐 Live Packet Transmission Demo")
    print("This script will send actual packets using your network interface")
    print("\nAvailable demos:")
    print("1. Send test packets to 8.8.8.8 (safe)")
    print("2. Advanced monitoring + packet sending")
    print("3. Simple packet monitoring (statistics-based)")
    print("4. Exit")
    
    while True:
        try:
            choice = input("\n❓ Choose option (1-4): ").strip()
            
            if choice == '1':
                send_test_packets_live()
            elif choice == '2':
                monitor_traffic_while_sending()
            elif choice == '3':
                simple_packet_monitor()
            elif choice == '4':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    # Check if running as root (required for packet sending)
    if os.geteuid() != 0:
        print("⚠️  This script requires root privileges to send packets.")
        print("   Please run with: sudo python3 live_packet_demo.py")
        sys.exit(1)
    
    main()
