#!/usr/bin/env python3
"""
EVE.json to Kafka Bridge
Bridges Suricata's eve.json file output to Kafka topics in real-time
"""

import json
import time
from pathlib import Path
from kafka import KafkaProducer
from kafka.errors import KafkaError
import argparse
import signal
import sys

class EVEKafkaBridge:
    def __init__(self, eve_file, kafka_brokers, base_topic="suricata"):
        self.eve_file = Path(eve_file)
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_brokers.split(','),
            value_serializer=lambda x: json.dumps(x).encode('utf-8'),
            key_serializer=lambda x: x.encode('utf-8') if x else None,
            compression_type='gzip',  # Changed from snappy to gzip
            batch_size=16384,
            linger_ms=10,
            acks=1,
            retries=3
        )
        self.base_topic = base_topic
        self.running = True
        self.stats = {'total': 0, 'events': 0, 'alerts': 0, 'flows': 0}
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
    
    def stop(self, signum=None, frame=None):
        print(f"\n📊 Final Stats: {self.stats}")
        self.running = False
        if self.producer:
            self.producer.close()
    
    def send_to_kafka(self, event):
        """Send event to appropriate Kafka topic based on event type"""
        try:
            event_type = event.get('event_type', 'unknown')
            
            # Choose topic based on event type
            if event_type == 'alert':
                topic = f"{self.base_topic}-alerts"
                self.stats['alerts'] += 1
            elif event_type == 'flow':
                topic = f"{self.base_topic}-events"
                self.stats['flows'] += 1
            elif event_type == 'stats':
                topic = f"{self.base_topic}-stats"
            else:
                topic = f"{self.base_topic}-events"
                self.stats['events'] += 1
            
            # Send to Kafka
            key = str(event.get('flow_id', event.get('timestamp', 'unknown')))
            self.producer.send(
                topic, 
                value=event, 
                key=key
            )
            
            self.stats['total'] += 1
            return True
            
        except Exception as e:
            print(f"❌ Error sending to Kafka: {e}")
            return False
    
    def tail_file(self):
        """Tail the eve.json file and send new lines to Kafka"""
        print(f"🔍 Monitoring: {self.eve_file}")
        print(f"📡 Streaming to Kafka topics: {self.base_topic}-*")
        print("Press Ctrl+C to stop\n")
        
        # Start from end of file
        with open(self.eve_file, 'r') as f:
            f.seek(0, 2)  # Go to end of file
            
            while self.running:
                line = f.readline()
                if line:
                    line = line.strip()
                    if line:
                        try:
                            event = json.loads(line)
                            if self.send_to_kafka(event):
                                if self.stats['total'] % 100 == 0:
                                    print(f"📊 Processed: {self.stats}")
                        except json.JSONDecodeError as e:
                            print(f"⚠️  Invalid JSON: {line[:100]}...")
                else:
                    time.sleep(0.1)  # Wait for new data
    
    def run(self):
        """Run the bridge"""
        try:
            if not self.eve_file.exists():
                print(f"❌ EVE file not found: {self.eve_file}")
                return False
            
            self.tail_file()
            return True
            
        except Exception as e:
            print(f"❌ Bridge error: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Bridge Suricata EVE.json to Kafka')
    parser.add_argument('--eve-file', default='/var/log/suricata/eve.json',
                        help='Path to Suricata eve.json file')
    parser.add_argument('--kafka-brokers', default='localhost:9092',
                        help='Kafka bootstrap servers')
    parser.add_argument('--base-topic', default='suricata',
                        help='Base topic name (events will go to base-events, base-alerts, etc.)')
    
    args = parser.parse_args()
    
    print("🌉 Suricata EVE.json to Kafka Bridge")
    print("=" * 50)
    
    bridge = EVEKafkaBridge(args.eve_file, args.kafka_brokers, args.base_topic)
    success = bridge.run()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
