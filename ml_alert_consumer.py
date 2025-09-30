#!/usr/bin/env python3
"""
ML-Enhanced Alerts Consumer

Real-time consumer for ML-enhanced security alerts that combines:
- Suricata rule-based detections
- Random Forest ML predictions  
- Combined threat assessment
- Advanced alert analytics
"""

import json
import time
from datetime import datetime
from collections import defaultdict, Counter
from kafka import KafkaConsumer

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

class MLAlertConsumer:
    """Consumer for ML-enhanced security alerts"""
    
    def __init__(self):
        self.kafka_broker = "localhost:9092"
        self.topic = "ml-enhanced-alerts"
        self.stats = {
            'total_alerts': 0,
            'critical_alerts': 0,
            'high_alerts': 0,
            'medium_alerts': 0,
            'low_alerts': 0,
            'suricata_only': 0,
            'ml_only': 0,
            'combined_detection': 0,
            'start_time': time.time()
        }
        self.attack_types = Counter()
        self.threat_sources = Counter()
        self.threat_targets = Counter()
        
    def process_alert(self, alert):
        """Process and display ML-enhanced alert"""
        self.stats['total_alerts'] += 1
        
        # Extract key information
        threat_level = alert['combined_assessment']['threat_level']
        src_ip = alert['src_ip']
        dest_ip = alert['dest_ip']
        src_port = alert['src_port']
        dest_port = alert['dest_port']
        description = alert['combined_assessment']['description']
        threat_score = alert['combined_assessment']['combined_score']
        
        # ML prediction info
        ml_prediction = alert['ml_detection']['predicted_attack']
        ml_confidence = alert['ml_detection']['confidence']
        ml_threat_level = alert['ml_detection']['threat_level']
        
        # Suricata info
        suricata_triggered = alert['suricata_detection']['rule_triggered']
        event_type = alert['suricata_detection']['event_type']
        
        # Update statistics
        self.stats[f'{threat_level.lower()}_alerts'] += 1
        self.attack_types[ml_prediction] += 1
        self.threat_sources[src_ip] += 1
        self.threat_targets[dest_ip] += 1
        
        if suricata_triggered and alert['ml_detection']['is_malicious']:
            self.stats['combined_detection'] += 1
        elif suricata_triggered:
            self.stats['suricata_only'] += 1
        elif alert['ml_detection']['is_malicious']:
            self.stats['ml_only'] += 1
        
        # Display alert
        self._display_alert(alert, threat_level, src_ip, dest_ip, src_port, dest_port, 
                           description, threat_score, ml_prediction, ml_confidence, 
                           suricata_triggered, event_type)
    
    def _display_alert(self, alert, threat_level, src_ip, dest_ip, src_port, dest_port,
                      description, threat_score, ml_prediction, ml_confidence, 
                      suricata_triggered, event_type):
        """Display formatted alert"""
        
        # Color based on threat level
        if threat_level == 'CRITICAL':
            color = Colors.RED
            icon = '🚨'
        elif threat_level == 'HIGH':
            color = Colors.YELLOW
            icon = '⚠️'
        elif threat_level == 'MEDIUM':
            color = Colors.BLUE
            icon = '🔍'
        else:
            color = Colors.GREEN
            icon = 'ℹ️'
        
        print(f"\n{color}{Colors.BOLD}{icon} {threat_level} ALERT #{self.stats['total_alerts']}{Colors.END}")
        print(f"{Colors.CYAN}Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        print(f"{Colors.CYAN}Connection: {src_ip}:{src_port} → {dest_ip}:{dest_port}{Colors.END}")
        print(f"{Colors.CYAN}Threat Score: {threat_score:.1f}/100{Colors.END}")
        
        print(f"\n{Colors.BOLD}Detection Summary:{Colors.END}")
        print(f"  {description}")
        
        print(f"\n{Colors.BOLD}ML Analysis:{Colors.END}")
        print(f"  Predicted Attack: {Colors.MAGENTA}{ml_prediction}{Colors.END}")
        print(f"  Confidence: {Colors.MAGENTA}{ml_confidence:.3f}{Colors.END}")
        print(f"  ML Threat Level: {Colors.MAGENTA}{alert['ml_detection']['threat_level']}{Colors.END}")
        
        print(f"\n{Colors.BOLD}Suricata Detection:{Colors.END}")
        if suricata_triggered:
            alert_info = alert['suricata_detection'].get('alert', {})
            signature = alert_info.get('signature', 'Unknown signature')
            severity = alert_info.get('severity', 'Unknown')
            category = alert_info.get('category', 'Unknown')
            
            print(f"  Rule Triggered: {Colors.RED}✓ YES{Colors.END}")
            print(f"  Signature: {signature}")
            print(f"  Severity: {severity}")
            print(f"  Category: {category}")
        else:
            print(f"  Rule Triggered: {Colors.GREEN}✗ NO{Colors.END}")
            print(f"  Event Type: {event_type}")
        
        # Show additional context for high-priority alerts
        if threat_level in ['CRITICAL', 'HIGH']:
            self._show_additional_context(alert)
        
        print(f"{Colors.CYAN}{'─' * 80}{Colors.END}")
    
    def _show_additional_context(self, alert):
        """Show additional context for high-priority alerts"""
        print(f"\n{Colors.BOLD}Additional Context:{Colors.END}")
        
        # Protocol analysis
        proto = alert.get('proto', 'Unknown')
        print(f"  Protocol: {proto}")
        
        # Original event details
        original_event = alert.get('original_event', {})
        
        if 'http' in original_event:
            http_data = original_event['http']
            print(f"  HTTP Method: {http_data.get('http_method', 'Unknown')}")
            print(f"  URL: {http_data.get('url', 'Unknown')}")
            print(f"  User Agent: {http_data.get('http_user_agent', 'Unknown')}")
            print(f"  Response Code: {http_data.get('status', 'Unknown')}")
        
        if 'dns' in original_event:
            dns_data = original_event['dns']
            print(f"  DNS Query: {dns_data.get('rrname', 'Unknown')}")
            print(f"  DNS Type: {dns_data.get('rrtype', 'Unknown')}")
        
        if 'flow' in original_event:
            flow_data = original_event['flow']
            print(f"  Packets to server: {flow_data.get('pkts_toserver', 0)}")
            print(f"  Packets to client: {flow_data.get('pkts_toclient', 0)}")
            print(f"  Bytes to server: {flow_data.get('bytes_toserver', 0)}")
            print(f"  Bytes to client: {flow_data.get('bytes_toclient', 0)}")
    
    def print_statistics(self):
        """Print current statistics"""
        elapsed = time.time() - self.stats['start_time']
        rate = self.stats['total_alerts'] / elapsed if elapsed > 0 else 0
        
        print(f"\n{Colors.BOLD}{Colors.BLUE}📊 ML-Enhanced Alert Statistics{Colors.END}")
        print(f"{Colors.BLUE}{'═' * 40}{Colors.END}")
        
        print(f"Runtime: {elapsed:.1f} seconds")
        print(f"Alert Rate: {rate:.2f} alerts/second")
        print()
        
        print(f"{Colors.BOLD}Alert Breakdown:{Colors.END}")
        print(f"  Total Alerts: {self.stats['total_alerts']}")
        print(f"  🚨 Critical: {self.stats['critical_alerts']}")
        print(f"  ⚠️  High: {self.stats['high_alerts']}")
        print(f"  🔍 Medium: {self.stats['medium_alerts']}")
        print(f"  ℹ️  Low: {self.stats['low_alerts']}")
        print()
        
        print(f"{Colors.BOLD}Detection Sources:{Colors.END}")
        print(f"  Suricata Only: {self.stats['suricata_only']}")
        print(f"  ML Only: {self.stats['ml_only']}")
        print(f"  Combined Detection: {self.stats['combined_detection']}")
        print()
        
        if self.attack_types:
            print(f"{Colors.BOLD}Top Attack Types:{Colors.END}")
            for attack_type, count in self.attack_types.most_common(5):
                print(f"  {attack_type}: {count}")
            print()
        
        if self.threat_sources:
            print(f"{Colors.BOLD}Top Threat Sources:{Colors.END}")
            for source, count in self.threat_sources.most_common(5):
                print(f"  {source}: {count}")
            print()
        
        if self.threat_targets:
            print(f"{Colors.BOLD}Top Threat Targets:{Colors.END}")
            for target, count in self.threat_targets.most_common(5):
                print(f"  {target}: {count}")
    
    def start_consuming(self):
        """Start consuming ML-enhanced alerts"""
        print(f"{Colors.BOLD}{Colors.BLUE}🧠 ML-Enhanced Alert Consumer Starting...{Colors.END}")
        print(f"Topic: {self.topic}")
        print(f"Broker: {self.kafka_broker}")
        print(f"Press Ctrl+C to stop\n")
        
        try:
            consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=[self.kafka_broker],
                auto_offset_reset='latest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            
            print(f"{Colors.GREEN}✓ Connected to Kafka topic: {self.topic}{Colors.END}")
            print(f"{Colors.CYAN}Waiting for ML-enhanced alerts...{Colors.END}")
            
            last_stats_time = time.time()
            
            for message in consumer:
                alert = message.value
                self.process_alert(alert)
                
                # Print statistics every 30 seconds
                if time.time() - last_stats_time > 30:
                    self.print_statistics()
                    last_stats_time = time.time()
                    
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}🛑 Stopping alert consumer...{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}❌ Error: {e}{Colors.END}")
        finally:
            print(f"\n{Colors.BOLD}Final Statistics:{Colors.END}")
            self.print_statistics()
            print(f"{Colors.GREEN}Alert consumer stopped.{Colors.END}")

def main():
    consumer = MLAlertConsumer()
    consumer.start_consuming()

if __name__ == "__main__":
    main()