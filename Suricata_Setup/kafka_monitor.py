#!/usr/bin/env python3
"""
Quick Kafka Consumer CLI for Suricata Events
Simple command-line tool for monitoring Suricata events in Kafka
"""

import json
import sys
from datetime import datetime
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import argparse

def consume_events(brokers, topic, max_messages=None, show_raw=False):
    """Consume and display events from Kafka topic"""
    
    print(f"🔍 Connecting to Kafka: {brokers}")
    print(f"📡 Consuming from topic: {topic}")
    
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=brokers.split(','),
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='latest',
            consumer_timeout_ms=5000
        )
        
        print(f"✅ Connected! Waiting for events... (Timeout: 5s)")
        print("=" * 80)
        
        count = 0
        for message in consumer:
            try:
                event = message.value
                count += 1
                
                if show_raw:
                    print(json.dumps(event, indent=2))
                else:
                    # Extract key information
                    timestamp = event.get('timestamp', 'N/A')
                    event_type = event.get('event_type', 'unknown')
                    src_ip = event.get('src_ip', 'N/A')
                    dest_ip = event.get('dest_ip', 'N/A')
                    src_port = event.get('src_port', 'N/A')
                    dest_port = event.get('dest_port', 'N/A')
                    proto = event.get('proto', 'N/A')
                    
                    print(f"[{count:4d}] {timestamp}")
                    print(f"       Type: {event_type}")
                    print(f"       Flow: {src_ip}:{src_port} → {dest_ip}:{dest_port} ({proto})")
                    
                    # Show alert details if it's an alert
                    if event_type == 'alert' and 'alert' in event:
                        alert = event['alert']
                        signature = alert.get('signature', 'N/A')
                        severity = alert.get('severity', 'N/A')
                        print(f"       🚨 Alert: {signature} (Severity: {severity})")
                    
                    print()
                
                if max_messages and count >= max_messages:
                    print(f"Reached maximum messages ({max_messages})")
                    break
                    
            except Exception as e:
                print(f"Error processing message: {e}")
                continue
        
        print(f"📊 Total messages processed: {count}")
        
    except KafkaError as e:
        print(f"❌ Kafka error: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n⏹️  Stopped by user. Processed {count} messages.")
        return True
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

def list_topics(brokers):
    """List available Kafka topics"""
    try:
        consumer = KafkaConsumer(bootstrap_servers=brokers.split(','))
        topics = consumer.topics()
        consumer.close()
        
        print(f"📋 Available topics on {brokers}:")
        for topic in sorted(topics):
            print(f"  - {topic}")
        
        return True
    except Exception as e:
        print(f"❌ Error listing topics: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Quick Kafka consumer for Suricata events',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list                                    # List available topics
  %(prog)s suricata-events                          # Consume from events topic
  %(prog)s suricata-alerts --max 10                 # Show 10 alerts
  %(prog)s suricata-events --raw                    # Show raw JSON
  %(prog)s suricata-stats --brokers kafka1:9092    # Use different broker
        """
    )
    
    parser.add_argument('topic', nargs='?', help='Kafka topic to consume from')
    parser.add_argument('--brokers', default='localhost:9092',
                        help='Kafka bootstrap servers (default: localhost:9092)')
    parser.add_argument('--max', type=int, metavar='N',
                        help='Maximum number of messages to consume')
    parser.add_argument('--raw', action='store_true',
                        help='Show raw JSON instead of formatted output')
    parser.add_argument('--list', action='store_true',
                        help='List available Kafka topics')
    
    args = parser.parse_args()
    
    if args.list:
        return 0 if list_topics(args.brokers) else 1
    
    if not args.topic:
        parser.error("Topic is required (unless using --list)")
    
    print(f"🚀 Suricata Kafka Consumer")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = consume_events(args.brokers, args.topic, args.max, args.raw)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
