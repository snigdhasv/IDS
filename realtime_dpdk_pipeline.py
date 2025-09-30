#!/usr/bin/env python3
"""
Real-time DPDK Packet Generation and IDS Pipeline Integration

This script creates a complete real-time pipeline that:
1. Generates high-volume packets using DPDK/Scapy
2. Injects them into the monitored network interface
3. Allows Suricata to process and extract features
4. Streams events to Kafka topics in real-time
5. Provides monitoring and validation capabilities

Usage:
    sudo python3 realtime_dpdk_pipeline.py --mode generate
    sudo python3 realtime_dpdk_pipeline.py --mode monitor
    sudo python3 realtime_dpdk_pipeline.py --mode validate
"""

import os
import sys
import time
import json
import threading
import argparse
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
import signal

# Import required libraries
try:
    from scapy.all import Ether, IP, TCP, UDP, ICMP, sendp, Raw
    from kafka import KafkaConsumer, KafkaProducer
    import psutil
except ImportError as e:
    print(f"Missing required libraries: {e}")
    print("Install with: pip install scapy kafka-python psutil")
    sys.exit(1)

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

class RealTimeDPDKPipeline:
    """Real-time DPDK packet generation and IDS integration system"""
    
    def __init__(self):
        self.interface = "enp2s0"  # Your monitored interface
        self.kafka_broker = "localhost:9092"
        self.kafka_topics = ["suricata-events", "suricata-alerts", "suricata-stats"]
        self.running = False
        self.stats = {
            'packets_sent': 0,
            'events_received': 0,
            'alerts_received': 0,
            'start_time': None
        }
        
    def check_prerequisites(self) -> bool:
        """Verify system is ready for real-time operation"""
        print(f"{Colors.YELLOW}🔍 Checking system prerequisites...{Colors.END}")
        
        # Check root privileges
        if os.geteuid() != 0:
            print(f"{Colors.RED}❌ Root privileges required for packet injection{Colors.END}")
            return False
        print(f"{Colors.GREEN}✓ Root privileges confirmed{Colors.END}")
        
        # Check Suricata status (check both standard and custom services)
        suricata_running = False
        try:
            # Check standard Suricata service
            result = subprocess.run(['systemctl', 'is-active', 'suricata'], 
                                  capture_output=True, text=True)
            if 'active' in result.stdout:
                suricata_running = True
                print(f"{Colors.GREEN}✓ Suricata service is active{Colors.END}")
            else:
                # Check custom Suricata services
                for service in ['suricata-simple', 'suricata-kafka']:
                    result = subprocess.run(['systemctl', 'is-active', service], 
                                          capture_output=True, text=True)
                    if 'active' in result.stdout:
                        suricata_running = True
                        print(f"{Colors.GREEN}✓ {service} service is active{Colors.END}")
                        break
            
            if not suricata_running:
                print(f"{Colors.RED}❌ No Suricata service is active{Colors.END}")
                return False
        except:
            print(f"{Colors.RED}❌ Cannot check Suricata status{Colors.END}")
            return False
            
        # Check Kafka status
        try:
            result = subprocess.run(['systemctl', 'is-active', 'kafka'], 
                                  capture_output=True, text=True)
            if 'active' not in result.stdout:
                print(f"{Colors.YELLOW}⚠️  Kafka service not found, checking manual installation{Colors.END}")
        except:
            pass
            
        # Check network interface
        try:
            result = subprocess.run(['ip', 'link', 'show', self.interface], 
                                  capture_output=True)
            if result.returncode != 0:
                print(f"{Colors.RED}❌ Interface {self.interface} not found{Colors.END}")
                return False
            print(f"{Colors.GREEN}✓ Interface {self.interface} available{Colors.END}")
        except:
            print(f"{Colors.RED}❌ Cannot check interface status{Colors.END}")
            return False
            
        return True
    
    def generate_realistic_packets(self) -> List:
        """Generate sophisticated attack patterns using advanced generator"""
        try:
            # Import the advanced attack generator
            import sys
            sys.path.append('/home/ifscr/SE_02_2025/IDS')
            from advanced_attack_generator import AdvancedAttackGenerator
            
            generator = AdvancedAttackGenerator(self.interface)
            
            # Generate a mixed scenario with all attack types
            packets = generator.generate_mixed_attack_scenario()
            
            print(f"{Colors.GREEN}✓ Generated {len(packets)} sophisticated attack packets{Colors.END}")
            generator.print_attack_statistics()
            
            return packets
            
        except ImportError:
            print(f"{Colors.YELLOW}⚠️  Advanced generator not available, using basic patterns{Colors.END}")
            return self._generate_basic_packets()
    
    def _generate_basic_packets(self) -> List:
        """Fallback basic packet generation"""
        packets = []
        
        # HTTP traffic patterns
        for i in range(10):
            http_pkt = (Ether() / 
                       IP(src=f"10.0.1.{100+i}", dst="192.168.1.10") / 
                       TCP(sport=12345+i, dport=80) / 
                       Raw(f"GET /api/data?id={i} HTTP/1.1\r\nHost: testapi.com\r\n\r\n"))
            packets.append(http_pkt)
        
        # Basic attack patterns
        attack_patterns = [
            # Port scan
            (Ether() / IP(src="10.0.0.1", dst="192.168.1.10") / 
             TCP(sport=666, dport=22, flags="S")),
            # SQL injection attempt
            (Ether() / IP(src="10.0.0.2", dst="192.168.1.10") / 
             TCP(sport=1337, dport=80) / 
             Raw("GET /login.php?user=admin'%20OR%201=1-- HTTP/1.1\r\n\r\n")),
        ]
        packets.extend(attack_patterns)
        
        return packets
    
    def continuous_packet_generation(self, duration: int = 60, rate: float = 10.0):
        """Generate packets continuously at specified rate"""
        print(f"{Colors.BLUE}🚀 Starting continuous packet generation...{Colors.END}")
        print(f"Duration: {duration}s, Rate: {rate} packets/second")
        
        self.running = True
        self.stats['start_time'] = time.time()
        
        packet_templates = self.generate_realistic_packets()
        interval = 1.0 / rate
        
        try:
            while self.running and (time.time() - self.stats['start_time']) < duration:
                for packet in packet_templates:
                    if not self.running:
                        break
                        
                    # Send packet
                    sendp(packet, iface=self.interface, verbose=0)
                    self.stats['packets_sent'] += 1
                    
                    # Rate limiting
                    time.sleep(interval)
                    
                    # Progress update
                    if self.stats['packets_sent'] % 100 == 0:
                        elapsed = time.time() - self.stats['start_time']
                        rate_actual = self.stats['packets_sent'] / elapsed
                        print(f"{Colors.GREEN}📊 Sent {self.stats['packets_sent']} packets "
                              f"({rate_actual:.1f} pps){Colors.END}")
                        
        except KeyboardInterrupt:
            print(f"{Colors.YELLOW}\n⏹️  Packet generation stopped by user{Colors.END}")
        finally:
            self.running = False
            
    def monitor_kafka_events(self, duration: int = 60):
        """Monitor Kafka topics for real-time events"""
        print(f"{Colors.BLUE}📡 Starting Kafka event monitoring...{Colors.END}")
        
        consumer = None
        try:
            consumer = KafkaConsumer(
                *self.kafka_topics,
                bootstrap_servers=[self.kafka_broker],
                auto_offset_reset='latest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            
            print(f"{Colors.GREEN}✓ Connected to Kafka topics: {', '.join(self.kafka_topics)}{Colors.END}")
            
            start_time = time.time()
            while (time.time() - start_time) < duration:
                message_batch = consumer.poll(timeout_ms=1000)
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        self.stats['events_received'] += 1
                        
                        # Parse event
                        event = message.value
                        event_type = event.get('event_type', 'unknown')
                        
                        if event_type == 'alert':
                            self.stats['alerts_received'] += 1
                            severity = event.get('alert', {}).get('severity', 'unknown')
                            signature = event.get('alert', {}).get('signature', 'unknown')
                            print(f"{Colors.RED}🚨 ALERT: {signature} (severity: {severity}){Colors.END}")
                        
                        elif event_type == 'flow':
                            src_ip = event.get('src_ip', 'unknown')
                            dest_ip = event.get('dest_ip', 'unknown')
                            proto = event.get('proto', 'unknown')
                            print(f"{Colors.BLUE}🔄 FLOW: {src_ip} → {dest_ip} ({proto}){Colors.END}")
                        
                        elif event_type == 'http':
                            hostname = event.get('http', {}).get('hostname', 'unknown')
                            method = event.get('http', {}).get('http_method', 'unknown')
                            print(f"{Colors.GREEN}🌐 HTTP: {method} {hostname}{Colors.END}")
                        
                        # Show periodic stats
                        if self.stats['events_received'] % 10 == 0:
                            print(f"{Colors.YELLOW}📈 Events received: {self.stats['events_received']} "
                                  f"(Alerts: {self.stats['alerts_received']}){Colors.END}")
                
        except Exception as e:
            print(f"{Colors.RED}❌ Kafka monitoring error: {e}{Colors.END}")
        finally:
            if consumer:
                consumer.close()
    
    def validate_pipeline(self):
        """Validate the complete pipeline integration"""
        print(f"{Colors.BOLD}🔬 Pipeline Validation Starting...{Colors.END}\n")
        
        if not self.check_prerequisites():
            return False
        
        print(f"{Colors.BLUE}Phase 1: Generate test packets{Colors.END}")
        test_packets = self.generate_realistic_packets()[:5]  # Limited set for validation
        
        for i, packet in enumerate(test_packets, 1):
            print(f"  Sending packet {i}: {packet[IP].src} → {packet[IP].dst}")
            sendp(packet, iface=self.interface, verbose=0)
            time.sleep(1)
        
        print(f"{Colors.GREEN}✓ Test packets sent{Colors.END}\n")
        
        print(f"{Colors.BLUE}Phase 2: Check Suricata event generation{Colors.END}")
        time.sleep(5)  # Allow processing time
        
        # Check eve.json for recent events
        eve_paths = ["/var/log/suricata/eve.json", "/tmp/suricata/eve.json"]
        for eve_path in eve_paths:
            if os.path.exists(eve_path):
                try:
                    result = subprocess.run(['tail', '-10', eve_path], 
                                          capture_output=True, text=True)
                    if result.stdout.strip():
                        print(f"{Colors.GREEN}✓ Recent events found in {eve_path}{Colors.END}")
                        break
                except:
                    continue
        
        print(f"{Colors.BLUE}Phase 3: Check Kafka streaming{Colors.END}")
        # Brief Kafka monitoring
        try:
            consumer = KafkaConsumer(
                *self.kafka_topics,
                bootstrap_servers=[self.kafka_broker],
                auto_offset_reset='latest',
                consumer_timeout_ms=5000,
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            
            event_count = 0
            for message in consumer:
                event_count += 1
                if event_count >= 3:  # Sample a few events
                    break
            
            if event_count > 0:
                print(f"{Colors.GREEN}✓ Kafka events flowing ({event_count} events sampled){Colors.END}")
            else:
                print(f"{Colors.YELLOW}⚠️  No recent Kafka events detected{Colors.END}")
                
            consumer.close()
        except Exception as e:
            print(f"{Colors.RED}❌ Kafka validation failed: {e}{Colors.END}")
        
        print(f"\n{Colors.BOLD}🎯 Pipeline validation completed{Colors.END}")
        return True
    
    def run_integrated_demo(self, duration: int = 120):
        """Run integrated demonstration of packet generation + monitoring"""
        print(f"{Colors.BOLD}🎭 Starting Integrated Real-Time Demo{Colors.END}")
        print(f"Duration: {duration} seconds\n")
        
        if not self.check_prerequisites():
            return
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(
            target=self.monitor_kafka_events, 
            args=(duration,),
            daemon=True
        )
        monitor_thread.start()
        
        # Wait a moment for monitoring to initialize
        time.sleep(2)
        
        # Generate packets
        self.continuous_packet_generation(duration=duration-5, rate=5.0)
        
        # Wait for monitoring to complete
        monitor_thread.join(timeout=10)
        
        # Final statistics
        elapsed = time.time() - self.stats['start_time']
        print(f"\n{Colors.BOLD}📊 Demo Results:{Colors.END}")
        print(f"  Packets sent: {self.stats['packets_sent']}")
        print(f"  Events received: {self.stats['events_received']}")
        print(f"  Alerts triggered: {self.stats['alerts_received']}")
        print(f"  Duration: {elapsed:.1f}s")
        print(f"  Average rate: {self.stats['packets_sent']/elapsed:.1f} packets/second")
        
def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print(f"\n{Colors.YELLOW}🛑 Shutting down gracefully...{Colors.END}")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(description='Real-time DPDK Packet Generation and IDS Pipeline')
    parser.add_argument('--mode', choices=['generate', 'monitor', 'validate', 'demo'], 
                       default='demo', help='Operation mode')
    parser.add_argument('--duration', type=int, default=60, 
                       help='Duration in seconds')
    parser.add_argument('--rate', type=float, default=10.0, 
                       help='Packet generation rate (packets/second)')
    
    args = parser.parse_args()
    
    pipeline = RealTimeDPDKPipeline()
    
    print(f"{Colors.BOLD}🔥 Real-time DPDK-IDS Pipeline{Colors.END}")
    print(f"Mode: {args.mode}, Duration: {args.duration}s\n")
    
    if args.mode == 'generate':
        pipeline.continuous_packet_generation(args.duration, args.rate)
    elif args.mode == 'monitor':
        pipeline.monitor_kafka_events(args.duration)
    elif args.mode == 'validate':
        pipeline.validate_pipeline()
    elif args.mode == 'demo':
        pipeline.run_integrated_demo(args.duration)

if __name__ == "__main__":
    main()
