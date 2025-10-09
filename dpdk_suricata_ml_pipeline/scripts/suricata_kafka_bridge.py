#!/usr/bin/env python3
"""
Suricata to Kafka Bridge

Tails Suricata's eve.json file and forwards events to Kafka in real-time.
This enables Kafka integration for Suricata installations without native Kafka support.
"""

import json
import sys
import time
import signal
from pathlib import Path
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Configuration
EVE_LOG_PATH = '/var/log/suricata/eve.json'
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPIC = 'suricata-alerts'
BUFFER_SIZE = 1024 * 1024  # 1MB buffer

class SuricataKafkaBridge:
    def __init__(self, eve_log_path, kafka_servers, kafka_topic):
        self.eve_log_path = Path(eve_log_path)
        self.kafka_servers = kafka_servers
        self.kafka_topic = kafka_topic
        self.producer = None
        self.running = True
        self.stats = {
            'events_sent': 0,
            'errors': 0,
            'start_time': time.time()
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print("\n\n🛑 Shutting down...")
        self.running = False
    
    def connect_kafka(self):
        """Initialize Kafka producer."""
        try:
            print(f"🔌 Connecting to Kafka: {self.kafka_servers}")
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks=1,  # Wait for leader acknowledgment
                retries=3,
                max_in_flight_requests_per_connection=5,
                compression_type='gzip'
            )
            print(f"✅ Connected to Kafka")
            print(f"📤 Publishing to topic: {self.kafka_topic}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Kafka: {e}")
            return False
    
    def send_to_kafka(self, event_data):
        """Send event to Kafka topic."""
        try:
            future = self.producer.send(self.kafka_topic, value=event_data)
            # Don't wait for each message (async)
            self.stats['events_sent'] += 1
            return True
        except KafkaError as e:
            self.stats['errors'] += 1
            if self.stats['errors'] % 100 == 0:  # Log every 100th error
                print(f"⚠️  Kafka send error: {e}")
            return False
    
    def tail_eve_log(self):
        """Tail eve.json and send events to Kafka."""
        print(f"📖 Tailing: {self.eve_log_path}")
        
        if not self.eve_log_path.exists():
            print(f"❌ Log file not found: {self.eve_log_path}")
            print(f"   Make sure Suricata is running and writing to this path")
            return False
        
        try:
            with open(self.eve_log_path, 'r') as f:
                # Seek to end of file to only process new events
                f.seek(0, 2)  # Go to end
                print("✅ Started monitoring (processing new events only)")
                print("📊 Events will be forwarded to Kafka as they arrive...")
                print()
                
                last_stats_time = time.time()
                
                while self.running:
                    line = f.readline()
                    
                    if line:
                        try:
                            # Parse JSON event
                            event = json.loads(line.strip())
                            
                            # Send to Kafka
                            self.send_to_kafka(event)
                            
                        except json.JSONDecodeError as e:
                            self.stats['errors'] += 1
                            continue
                    else:
                        # No new data, sleep briefly
                        time.sleep(0.1)
                    
                    # Print stats every 10 seconds
                    if time.time() - last_stats_time >= 10:
                        self._print_stats()
                        last_stats_time = time.time()
                
                return True
                
        except Exception as e:
            print(f"❌ Error tailing log: {e}")
            return False
    
    def _print_stats(self):
        """Print statistics."""
        runtime = time.time() - self.stats['start_time']
        rate = self.stats['events_sent'] / runtime if runtime > 0 else 0
        
        print(f"📊 Stats: {self.stats['events_sent']} events sent | "
              f"{self.stats['errors']} errors | "
              f"{rate:.2f} events/sec")
    
    def run(self):
        """Main run loop."""
        print("╔════════════════════════════════════════════════╗")
        print("║  Suricata → Kafka Bridge                       ║")
        print("╚════════════════════════════════════════════════╝")
        print()
        
        # Connect to Kafka
        if not self.connect_kafka():
            return 1
        
        print()
        
        # Start tailing and forwarding
        try:
            self.tail_eve_log()
        finally:
            # Cleanup
            if self.producer:
                print("\n🔄 Flushing remaining messages...")
                self.producer.flush()
                self.producer.close()
            
            print("\n📊 Final Statistics:")
            print(f"   Events sent: {self.stats['events_sent']}")
            print(f"   Errors: {self.stats['errors']}")
            print(f"   Runtime: {time.time() - self.stats['start_time']:.1f}s")
            print("\n✅ Bridge stopped cleanly")
        
        return 0


def main():
    """Entry point."""
    # Load configuration from file if available
    config_file = Path(__file__).parent.parent / 'config' / 'pipeline.conf'
    
    eve_log = EVE_LOG_PATH
    kafka_servers = KAFKA_BOOTSTRAP_SERVERS
    kafka_topic = KAFKA_TOPIC
    
    # Try to load from config file
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('KAFKA_BOOTSTRAP_SERVERS='):
                        kafka_servers = line.split('=', 1)[1].strip('"')
                    elif line.startswith('KAFKA_TOPIC_ALERTS='):
                        kafka_topic = line.split('=', 1)[1].strip('"')
                    elif line.startswith('SURICATA_LOG_DIR='):
                        log_dir = line.split('=', 1)[1].strip('"')
                        eve_log = f"{log_dir}/eve.json"
        except Exception as e:
            print(f"⚠️  Warning: Could not load config file: {e}")
            print(f"   Using defaults")
    
    # Create and run bridge
    bridge = SuricataKafkaBridge(eve_log, kafka_servers, kafka_topic)
    return bridge.run()


if __name__ == '__main__':
    sys.exit(main())
