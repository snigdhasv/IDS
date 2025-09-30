#!/usr/bin/env python3
"""
Kafka Consumer for Suricata Events
Validates that Suricata is correctly sending events to Kafka topics
"""

import json
import signal
import sys
from datetime import datetime
from collections import defaultdict, Counter
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SuricataKafkaConsumer:
    def __init__(self, bootstrap_servers=['localhost:9092'], topics=['suricata-events']):
        self.bootstrap_servers = bootstrap_servers
        self.topics = topics
        self.consumer = None
        self.running = False
        self.stats = {
            'total_messages': 0,
            'event_types': Counter(),
            'protocols': Counter(),
            'alerts': 0,
            'flows': 0,
            'http_events': 0,
            'dns_events': 0,
            'start_time': datetime.now()
        }
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        if self.consumer:
            self.consumer.close()
    
    def connect(self):
        """Connect to Kafka"""
        try:
            logger.info(f"Connecting to Kafka brokers: {self.bootstrap_servers}")
            logger.info(f"Subscribing to topics: {self.topics}")
            
            self.consumer = KafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                key_deserializer=lambda x: x.decode('utf-8') if x else None,
                consumer_timeout_ms=1000,
                auto_offset_reset='latest',  # Start from latest messages
                enable_auto_commit=True,
                group_id='suricata-validator',
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000
            )
            
            logger.info("✅ Connected to Kafka successfully")
            return True
            
        except KafkaError as e:
            logger.error(f"❌ Failed to connect to Kafka: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error connecting to Kafka: {e}")
            return False
    
    def process_event(self, event_data):
        """Process a single Suricata event"""
        try:
            self.stats['total_messages'] += 1
            
            # Extract basic information
            event_type = event_data.get('event_type', 'unknown')
            self.stats['event_types'][event_type] += 1
            
            protocol = event_data.get('proto', 'unknown')
            self.stats['protocols'][protocol] += 1
            
            # Count specific event types
            if event_type == 'alert':
                self.stats['alerts'] += 1
                self.process_alert(event_data)
            elif event_type == 'flow':
                self.stats['flows'] += 1
                self.process_flow(event_data)
            elif event_type == 'http':
                self.stats['http_events'] += 1
                self.process_http(event_data)
            elif event_type == 'dns':
                self.stats['dns_events'] += 1
                self.process_dns(event_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            return False
    
    def process_alert(self, event_data):
        """Process alert events"""
        alert = event_data.get('alert', {})
        signature_id = alert.get('signature_id', 'N/A')
        signature = alert.get('signature', 'N/A')
        severity = alert.get('severity', 'N/A')
        category = alert.get('category', 'N/A')
        
        src_ip = event_data.get('src_ip', 'N/A')
        dest_ip = event_data.get('dest_ip', 'N/A')
        src_port = event_data.get('src_port', 'N/A')
        dest_port = event_data.get('dest_port', 'N/A')
        
        logger.info(f"🚨 ALERT: SID={signature_id} | {src_ip}:{src_port} → {dest_ip}:{dest_port} | {signature}")
    
    def process_flow(self, event_data):
        """Process flow events"""
        flow = event_data.get('flow', {})
        pkts_toserver = flow.get('pkts_toserver', 0)
        pkts_toclient = flow.get('pkts_toclient', 0)
        bytes_toserver = flow.get('bytes_toserver', 0)
        bytes_toclient = flow.get('bytes_toclient', 0)
        
        src_ip = event_data.get('src_ip', 'N/A')
        dest_ip = event_data.get('dest_ip', 'N/A')
        
        logger.debug(f"📊 FLOW: {src_ip} → {dest_ip} | Pkts: {pkts_toserver}→{pkts_toclient} | Bytes: {bytes_toserver}→{bytes_toclient}")
    
    def process_http(self, event_data):
        """Process HTTP events"""
        http = event_data.get('http', {})
        method = http.get('http_method', 'N/A')
        hostname = http.get('hostname', 'N/A')
        url = http.get('url', 'N/A')
        status = http.get('status', 'N/A')
        
        logger.debug(f"🌐 HTTP: {method} {hostname}{url} | Status: {status}")
    
    def process_dns(self, event_data):
        """Process DNS events"""
        dns = event_data.get('dns', {})
        query_type = dns.get('type', 'N/A')
        rrname = dns.get('rrname', 'N/A')
        rrtype = dns.get('rrtype', 'N/A')
        
        logger.debug(f"🔍 DNS: {query_type} | {rrname} | {rrtype}")
    
    def print_stats(self):
        """Print consumption statistics"""
        runtime = datetime.now() - self.stats['start_time']
        rate = self.stats['total_messages'] / max(runtime.total_seconds(), 1)
        
        print(f"\n📊 KAFKA CONSUMPTION STATISTICS")
        print(f"=" * 50)
        print(f"Runtime: {runtime}")
        print(f"Total Messages: {self.stats['total_messages']:,}")
        print(f"Messages/sec: {rate:.2f}")
        print(f"Alerts: {self.stats['alerts']:,}")
        print(f"Flows: {self.stats['flows']:,}")
        print(f"HTTP Events: {self.stats['http_events']:,}")
        print(f"DNS Events: {self.stats['dns_events']:,}")
        
        print(f"\nEvent Types:")
        for event_type, count in self.stats['event_types'].most_common():
            print(f"  {event_type}: {count:,}")
        
        print(f"\nProtocols:")
        for protocol, count in self.stats['protocols'].most_common():
            print(f"  {protocol}: {count:,}")
    
    def consume(self, show_messages=True, stats_interval=30):
        """Main consumption loop"""
        if not self.connect():
            return False
        
        logger.info("🚀 Starting Kafka consumption...")
        logger.info("Press Ctrl+C to stop")
        
        self.running = True
        last_stats_time = datetime.now()
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                try:
                    # Process the event
                    event_data = message.value
                    success = self.process_event(event_data)
                    
                    if show_messages and success:
                        timestamp = event_data.get('timestamp', 'N/A')
                        event_type = event_data.get('event_type', 'unknown')
                        src_ip = event_data.get('src_ip', 'N/A')
                        dest_ip = event_data.get('dest_ip', 'N/A')
                        
                        print(f"📨 {timestamp} | {event_type} | {src_ip} → {dest_ip}")
                    
                    # Print periodic statistics
                    now = datetime.now()
                    if (now - last_stats_time).total_seconds() >= stats_interval:
                        self.print_stats()
                        last_stats_time = now
                
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in consumption loop: {e}")
        finally:
            self.running = False
            if self.consumer:
                self.consumer.close()
            
            # Print final statistics
            self.print_stats()
        
        return True


    def validate(self, timeout=30):
        """Validation mode - consume for a limited time and report results"""
        if not self.connect():
            return False
        
        logger.info(f"🔍 Starting validation mode (timeout: {timeout}s)")
        self.running = True
        start_time = datetime.now()
        
        try:
            # Set consumer timeout
            for message in self.consumer:
                if not self.running:
                    break
                
                # Check timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= timeout:
                    logger.info(f"Validation timeout reached ({timeout}s)")
                    break
                
                try:
                    event_data = message.value
                    self.process_event(event_data)
                    
                    # Log first few events for validation
                    if self.stats['total_messages'] <= 5:
                        event_type = event_data.get('event_type', 'unknown')
                        timestamp = event_data.get('timestamp', 'N/A')
                        logger.info(f"✅ Event received: {event_type} at {timestamp}")
                
                except Exception as e:
                    logger.error(f"Error processing validation event: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error in validation: {e}")
            return False
        finally:
            self.running = False
            if self.consumer:
                self.consumer.close()
        
        # Report validation results
        print(f"\n🔍 VALIDATION RESULTS")
        print(f"=" * 40)
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"Validation time: {elapsed:.1f}s")
        print(f"Messages received: {self.stats['total_messages']}")
        
        if self.stats['total_messages'] > 0:
            print(f"✅ VALIDATION PASSED - Events are flowing from Suricata to Kafka")
            print(f"Event types detected: {list(self.stats['event_types'].keys())}")
            return True
        else:
            print(f"❌ VALIDATION FAILED - No events received")
            return False


def main():
    parser = argparse.ArgumentParser(description='Consume Suricata events from Kafka')
    parser.add_argument('--brokers', default='localhost:9092',
                        help='Kafka bootstrap servers (default: localhost:9092)')
    parser.add_argument('--topics', nargs='+', default=['suricata-events'],
                        help='Topics to consume (default: suricata-events)')
    parser.add_argument('--quiet', action='store_true',
                        help='Don\'t show individual messages')
    parser.add_argument('--stats-interval', type=int, default=30,
                        help='Statistics reporting interval in seconds (default: 30)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        default='INFO', help='Logging level')
    parser.add_argument('--validate', action='store_true',
                        help='Run in validation mode (consume for limited time)')
    parser.add_argument('--timeout', type=int, default=30,
                        help='Timeout for validation mode in seconds (default: 30)')
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Parse brokers
    brokers = args.brokers.split(',')
    
    # Create and run consumer
    consumer = SuricataKafkaConsumer(bootstrap_servers=brokers, topics=args.topics)
    
    logger.info(f"Starting Suricata Kafka consumer...")
    logger.info(f"Brokers: {brokers}")
    logger.info(f"Topics: {args.topics}")
    
    if args.validate:
        success = consumer.validate(timeout=args.timeout)
    else:
        success = consumer.consume(show_messages=not args.quiet, stats_interval=args.stats_interval)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
