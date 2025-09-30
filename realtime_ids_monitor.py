#!/usr/bin/env python3
"""
Real-time IDS Pipeline Monitor
Comprehensive monitoring for DPDK packet generation, Suricata feature extraction, and Kafka streaming

This script provides real-time monitoring and visualization of the complete IDS pipeline:
- Packet generation rates and patterns
- Suricata processing statistics
- Kafka event streaming metrics
- System performance indicators
- Alert detection and analysis
"""

import os
import sys
import time
import json
import threading
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict, deque
import signal

try:
    from kafka import KafkaConsumer
    import psutil
except ImportError as e:
    print(f"Missing libraries: {e}")
    print("Install with: pip install kafka-python psutil")
    sys.exit(1)

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

class RealTimeIDSMonitor:
    """Real-time monitoring system for the complete IDS pipeline"""
    
    def __init__(self):
        self.kafka_broker = "localhost:9092"
        self.kafka_topics = ["suricata-events", "suricata-alerts", "suricata-stats"]
        self.running = False
        
        # Statistics tracking
        self.stats = {
            'events_total': 0,
            'alerts_total': 0,
            'flows_total': 0,
            'http_events': 0,
            'dns_events': 0,
            'start_time': None,
            'last_update': None
        }
        
        # Rate tracking (events per minute)
        self.rate_windows = {
            'events': deque(maxlen=60),  # Last 60 seconds
            'alerts': deque(maxlen=60),
            'flows': deque(maxlen=60)
        }
        
        # Alert classification
        self.alert_categories = defaultdict(int)
        self.severity_counts = defaultdict(int)
        
        # System metrics
        self.system_metrics = {
            'cpu_usage': 0,
            'memory_usage': 0,
            'network_io': {'bytes_sent': 0, 'bytes_recv': 0},
            'disk_io': {'read_bytes': 0, 'write_bytes': 0}
        }
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def get_system_metrics(self):
        """Collect current system performance metrics"""
        try:
            # CPU and memory
            self.system_metrics['cpu_usage'] = psutil.cpu_percent(interval=1)
            self.system_metrics['memory_usage'] = psutil.virtual_memory().percent
            
            # Network I/O
            net_io = psutil.net_io_counters()
            self.system_metrics['network_io'] = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv
            }
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                self.system_metrics['disk_io'] = {
                    'read_bytes': disk_io.read_bytes,
                    'write_bytes': disk_io.write_bytes
                }
        except Exception as e:
            print(f"Error collecting system metrics: {e}")
    
    def check_suricata_status(self):
        """Check Suricata service status and recent activity"""
        try:
            # Process information (check for any running Suricata processes)
            suricata_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']):
                if 'suricata' in proc.info['name'].lower():
                    suricata_processes.append(proc.info)
            
            # Determine service status based on running processes and log activity
            if suricata_processes:
                # Check log file activity to confirm it's working
                log_files = ["/var/log/suricata/eve.json", "/tmp/suricata/eve.json"]
                active_log = None
                recent_activity = False
                
                for log_file in log_files:
                    if os.path.exists(log_file):
                        stat = os.stat(log_file)
                        if time.time() - stat.st_mtime < 60:  # Modified in last minute
                            active_log = log_file
                            recent_activity = True
                            break
                
                # Determine status based on processes and log activity
                if recent_activity:
                    service_status = "running"  # Process running AND generating logs
                else:
                    service_status = "idle"     # Process running but no recent logs
            else:
                # No Suricata processes found
                service_status = "stopped"
                active_log = None
            
            return {
                'service_status': service_status,
                'processes': suricata_processes,
                'active_log': active_log
            }
        except Exception as e:
            return {'error': str(e)}
    
    def check_kafka_status(self):
        """Check Kafka connectivity and topic status"""
        try:
            # Check if Kafka processes are running
            kafka_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'kafka' in proc.info['name'].lower() or \
                   (proc.info['cmdline'] and any('kafka' in arg.lower() for arg in proc.info['cmdline'])):
                    kafka_processes.append(proc.info)
            
            if not kafka_processes:
                return {'status': 'not_running', 'processes': []}
            
            # Quick connection test
            consumer = KafkaConsumer(
                bootstrap_servers=[self.kafka_broker],
                consumer_timeout_ms=2000
            )
            
            # Try to get topic metadata
            metadata = consumer.list_consumer_groups()
            consumer.close()
            
            return {'status': 'connected', 'processes': kafka_processes}
        except Exception as e:
            # Kafka processes running but connection failed
            if kafka_processes:
                return {'status': 'connection_error', 'error': str(e), 'processes': kafka_processes}
            else:
                return {'status': 'not_running', 'error': str(e), 'processes': []}
    
    def display_dashboard(self):
        """Display real-time monitoring dashboard"""
        self.clear_screen()
        
        # Header
        print(f"{Colors.BOLD}{Colors.BLUE}🔥 Real-time IDS Pipeline Monitor{Colors.END}")
        print(f"{Colors.CYAN}{'='*80}{Colors.END}")
        
        # Runtime information
        if self.stats['start_time']:
            runtime = datetime.now() - self.stats['start_time']
            print(f"{Colors.GREEN}⏱️  Runtime: {runtime}{Colors.END}")
            print(f"{Colors.GREEN}🕐 Last Update: {self.stats['last_update']}{Colors.END}")
        
        print()
        
        # Event Statistics
        print(f"{Colors.BOLD}{Colors.YELLOW}📊 Event Statistics{Colors.END}")
        print(f"  Total Events: {Colors.GREEN}{self.stats['events_total']}{Colors.END}")
        print(f"  Security Alerts: {Colors.RED}{self.stats['alerts_total']}{Colors.END}")
        print(f"  Network Flows: {Colors.BLUE}{self.stats['flows_total']}{Colors.END}")
        print(f"  HTTP Events: {Colors.CYAN}{self.stats['http_events']}{Colors.END}")
        print(f"  DNS Events: {Colors.MAGENTA}{self.stats['dns_events']}{Colors.END}")
        
        # Rate calculations
        if len(self.rate_windows['events']) > 0:
            events_per_min = sum(self.rate_windows['events'])
            alerts_per_min = sum(self.rate_windows['alerts'])
            print(f"  Event Rate: {Colors.GREEN}{events_per_min}/min{Colors.END}")
            print(f"  Alert Rate: {Colors.RED}{alerts_per_min}/min{Colors.END}")
        
        print()
        
        # Alert Analysis
        if self.alert_categories:
            print(f"{Colors.BOLD}{Colors.RED}🚨 Alert Categories{Colors.END}")
            for category, count in sorted(self.alert_categories.items(), 
                                        key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {category}: {Colors.RED}{count}{Colors.END}")
            print()
        
        if self.severity_counts:
            print(f"{Colors.BOLD}{Colors.RED}⚠️  Alert Severities{Colors.END}")
            for severity, count in sorted(self.severity_counts.items(), reverse=True):
                color = Colors.RED if severity == '1' else Colors.YELLOW if severity == '2' else Colors.GREEN
                print(f"  Severity {severity}: {color}{count}{Colors.END}")
            print()
        
        # System Performance
        print(f"{Colors.BOLD}{Colors.BLUE}💻 System Performance{Colors.END}")
        cpu_color = Colors.RED if self.system_metrics['cpu_usage'] > 80 else Colors.YELLOW if self.system_metrics['cpu_usage'] > 60 else Colors.GREEN
        mem_color = Colors.RED if self.system_metrics['memory_usage'] > 80 else Colors.YELLOW if self.system_metrics['memory_usage'] > 60 else Colors.GREEN
        
        print(f"  CPU Usage: {cpu_color}{self.system_metrics['cpu_usage']:.1f}%{Colors.END}")
        print(f"  Memory Usage: {mem_color}{self.system_metrics['memory_usage']:.1f}%{Colors.END}")
        
        # Network I/O
        net_sent_mb = self.system_metrics['network_io']['bytes_sent'] / (1024*1024)
        net_recv_mb = self.system_metrics['network_io']['bytes_recv'] / (1024*1024)
        print(f"  Network I/O: {Colors.CYAN}↑{net_sent_mb:.1f}MB ↓{net_recv_mb:.1f}MB{Colors.END}")
        
        print()
        
        # Service Status
        suricata_status = self.check_suricata_status()
        kafka_status = self.check_kafka_status()
        
        print(f"{Colors.BOLD}{Colors.CYAN}🔧 Service Status{Colors.END}")
        
        # Suricata status
        if 'error' not in suricata_status:
            # Choose color based on status
            if suricata_status['service_status'] == 'running':
                status_color = Colors.GREEN
                status_icon = "✓"
            elif suricata_status['service_status'] == 'idle':
                status_color = Colors.YELLOW
                status_icon = "⏸️"
            else:
                status_color = Colors.RED
                status_icon = "❌"
                
            print(f"  Suricata: {status_color}{status_icon} {suricata_status['service_status']}{Colors.END}")
            
            if suricata_status['processes']:
                for proc in suricata_status['processes']:
                    print(f"    PID {proc['pid']}: CPU {proc['cpu_percent']:.1f}% Memory {proc['memory_percent']:.1f}%")
            
            if suricata_status['active_log']:
                print(f"  Active Log: {Colors.GREEN}{suricata_status['active_log']}{Colors.END}")
        else:
            print(f"  Suricata: {Colors.RED}❌ Error - {suricata_status['error']}{Colors.END}")
        
        # Kafka status
        if kafka_status['status'] == 'connected':
            kafka_color = Colors.GREEN
            kafka_icon = "✓"
            kafka_text = "connected"
        elif kafka_status['status'] == 'connection_error':
            kafka_color = Colors.YELLOW
            kafka_icon = "⚠️"
            kafka_text = "running (connection issues)"
        elif kafka_status['status'] == 'not_running':
            kafka_color = Colors.RED
            kafka_icon = "❌"
            kafka_text = "not running"
        else:
            kafka_color = Colors.RED
            kafka_icon = "❌"
            kafka_text = kafka_status['status']
            
        print(f"  Kafka: {kafka_color}{kafka_icon} {kafka_text}{Colors.END}")
        
        print()
        print(f"{Colors.YELLOW}Press Ctrl+C to stop monitoring{Colors.END}")
    
    def process_kafka_event(self, event):
        """Process and categorize Kafka events"""
        self.stats['events_total'] += 1
        self.stats['last_update'] = datetime.now().strftime("%H:%M:%S")
        
        event_type = event.get('event_type', 'unknown')
        
        # Update rate windows
        current_second = int(time.time())
        
        # Ensure rate windows are current
        for window in self.rate_windows.values():
            while len(window) < 60:
                window.append(0)
        
        self.rate_windows['events'][current_second % 60] += 1
        
        # Process specific event types
        if event_type == 'alert':
            self.stats['alerts_total'] += 1
            self.rate_windows['alerts'][current_second % 60] += 1
            
            # Alert categorization
            alert_info = event.get('alert', {})
            category = alert_info.get('category', 'Unknown')
            severity = str(alert_info.get('severity', 'Unknown'))
            signature = alert_info.get('signature', 'Unknown')
            
            self.alert_categories[category] += 1
            self.severity_counts[severity] += 1
            
            # Print significant alerts
            if severity in ['1', '2']:  # High severity
                src_ip = event.get('src_ip', 'unknown')
                dest_ip = event.get('dest_ip', 'unknown')
                print(f"\n{Colors.RED}🚨 HIGH SEVERITY ALERT:{Colors.END}")
                print(f"  {signature}")
                print(f"  {src_ip} → {dest_ip} (Severity: {severity})")
        
        elif event_type == 'flow':
            self.stats['flows_total'] += 1
            self.rate_windows['flows'][current_second % 60] += 1
        
        elif event_type == 'http':
            self.stats['http_events'] += 1
        
        elif event_type == 'dns':
            self.stats['dns_events'] += 1
    
    def kafka_monitor_thread(self):
        """Background thread for Kafka event monitoring"""
        try:
            consumer = KafkaConsumer(
                *self.kafka_topics,
                bootstrap_servers=[self.kafka_broker],
                auto_offset_reset='latest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            
            print(f"{Colors.GREEN}✓ Connected to Kafka topics{Colors.END}")
            
            while self.running:
                message_batch = consumer.poll(timeout_ms=1000)
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        if not self.running:
                            break
                        self.process_kafka_event(message.value)
                        
        except Exception as e:
            print(f"{Colors.RED}❌ Kafka monitoring error: {e}{Colors.END}")
        finally:
            consumer.close()
    
    def system_monitor_thread(self):
        """Background thread for system metrics collection"""
        while self.running:
            self.get_system_metrics()
            time.sleep(5)  # Update every 5 seconds
    
    def start_monitoring(self):
        """Start real-time monitoring"""
        print(f"{Colors.BOLD}🎯 Starting Real-time IDS Pipeline Monitoring{Colors.END}\n")
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        # Start background threads
        kafka_thread = threading.Thread(target=self.kafka_monitor_thread, daemon=True)
        system_thread = threading.Thread(target=self.system_monitor_thread, daemon=True)
        
        kafka_thread.start()
        system_thread.start()
        
        # Main display loop
        try:
            while self.running:
                self.display_dashboard()
                time.sleep(2)  # Refresh every 2 seconds
                
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}🛑 Monitoring stopped by user{Colors.END}")
        finally:
            self.running = False
            
        # Final statistics
        runtime = datetime.now() - self.stats['start_time']
        print(f"\n{Colors.BOLD}📊 Final Statistics:{Colors.END}")
        print(f"  Runtime: {runtime}")
        print(f"  Total Events: {self.stats['events_total']}")
        print(f"  Total Alerts: {self.stats['alerts_total']}")
        if runtime.total_seconds() > 0:
            rate = self.stats['events_total'] / (runtime.total_seconds() / 60)
            print(f"  Average Rate: {rate:.1f} events/minute")

def signal_handler(signum, frame):
    """Handle graceful shutdown"""
    print(f"\n{Colors.YELLOW}🛑 Shutting down monitor...{Colors.END}")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    monitor = RealTimeIDSMonitor()
    monitor.start_monitoring()

if __name__ == "__main__":
    main()
