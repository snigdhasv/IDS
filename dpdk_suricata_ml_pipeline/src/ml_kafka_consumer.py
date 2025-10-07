#!/usr/bin/env python3
"""
Enhanced ML Kafka Consumer for IDS Pipeline

Consumes ALL Suricata events from Kafka (flows, alerts, etc.) and performs:
1. Feature extraction from flow events (CICIDS2017 65-feature format)
2. ML inference for anomaly detection
3. Combined threat scoring with Suricata alerts
4. Publishing enhanced alerts to Kafka

Architecture:
Kafka (Suricata Events) → Feature Extraction → ML Inference → Alert Processing → Kafka (Enhanced Alerts)
"""

import json
import logging
import sys
import time
import signal
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from collections import defaultdict, deque

import numpy as np
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

# Import our custom modules
from feature_extractor import CICIDS2017FeatureExtractor
from model_loader import MLModelLoader
from alert_processor import AlertProcessor

# Configure logging - create log directory if it doesn't exist
LOG_DIR = Path(__file__).parent.parent / 'logs' / 'ml'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'ml_consumer.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Colors:
    """Terminal colors for pretty output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


class MLEnhancedKafkaConsumer:
    """
    ML-Enhanced Kafka Consumer for IDS Pipeline
    
    Processes all network flows through ML model for comprehensive
    threat detection, not just signature-based alerts.
    """
    
    def __init__(self, config_file: str = None):
        """
        Initialize the ML consumer.
        
        Args:
            config_file: Path to pipeline configuration file
        """
        # Load configuration
        self.config = self._load_config(config_file)
        
        # Initialize components
        self.feature_extractor = CICIDS2017FeatureExtractor()
        self.model_loader = MLModelLoader()
        self.alert_processor = AlertProcessor()
        
        # Kafka components (initialized later)
        self.consumer = None
        self.producer = None
        
        # Statistics
        self.stats = {
            'events_processed': 0,
            'flows_processed': 0,
            'alerts_processed': 0,
            'ml_predictions': 0,
            'ml_alerts_generated': 0,
            'enhanced_alerts_sent': 0,
            'errors': 0,
            'start_time': None,
        }
        
        # Flow tracking for correlation
        # Maps flow_id -> {'alert': alert_event, 'flow': flow_event}
        self.flow_cache = {}
        self.flow_cache_max_size = 10000
        
        # Event processing queue
        self.event_queue = deque(maxlen=1000)
        
        # Running flag
        self.running = False
        
        logger.info("ML Enhanced Kafka Consumer initialized")
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from file."""
        default_config = {
            'kafka_bootstrap_servers': 'localhost:9092',
            'kafka_input_topic': 'suricata-alerts',
            'kafka_output_topic': 'ml-predictions',
            'kafka_group_id': 'ml-consumer-group',
            'ml_model_name': 'random_forest_model_2017.joblib',
            'batch_size': 100,
            'flow_correlation_timeout': 60,  # seconds
        }
        
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r') as f:
                    # Simple key=value parser
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"')
                            if key == 'KAFKA_BOOTSTRAP_SERVERS':
                                default_config['kafka_bootstrap_servers'] = value
                            elif key == 'KAFKA_TOPIC_ALERTS':
                                default_config['kafka_input_topic'] = value
                            elif key == 'KAFKA_TOPIC_ML_PREDICTIONS':
                                default_config['kafka_output_topic'] = value
                logger.info(f"Configuration loaded from {config_file}")
            except Exception as e:
                logger.warning(f"Error loading config file: {e}, using defaults")
        
        return default_config
    
    def initialize(self) -> bool:
        """
        Initialize Kafka connections and load ML model.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            print(f"{Colors.BOLD}{Colors.BLUE}Initializing ML Enhanced IDS Consumer...{Colors.END}")
            
            # Load ML model
            print(f"{Colors.YELLOW}Loading ML model...{Colors.END}")
            if not self.model_loader.load_model(model_name=self.config['ml_model_name']):
                print(f"{Colors.RED}❌ Failed to load ML model{Colors.END}")
                return False
            
            model_info = self.model_loader.get_model_info()
            print(f"{Colors.GREEN}✓ ML model loaded{Colors.END}")
            print(f"  Type: {model_info['model_type']}")
            print(f"  Features: {model_info['expected_features']}")
            
            # Initialize Kafka consumer
            print(f"{Colors.YELLOW}Connecting to Kafka...{Colors.END}")
            self.consumer = KafkaConsumer(
                self.config['kafka_input_topic'],
                bootstrap_servers=self.config['kafka_bootstrap_servers'],
                group_id=self.config['kafka_group_id'],
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True,
                consumer_timeout_ms=1000
            )
            
            # Initialize Kafka producer
            self.producer = KafkaProducer(
                bootstrap_servers=self.config['kafka_bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            print(f"{Colors.GREEN}✓ Kafka connected{Colors.END}")
            print(f"  Input topic: {self.config['kafka_input_topic']}")
            print(f"  Output topic: {self.config['kafka_output_topic']}")
            print()
            
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            print(f"{Colors.RED}❌ Initialization failed: {e}{Colors.END}")
            return False
    
    def start(self):
        """Start consuming and processing events."""
        if not self.initialize():
            logger.error("Cannot start consumer - initialization failed")
            return
        
        self.running = True
        self.stats['start_time'] = time.time()
        
        print(f"{Colors.BOLD}{Colors.GREEN}╔════════════════════════════════════════════════╗{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}║  ML Enhanced IDS Consumer Started             ║{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}╚════════════════════════════════════════════════╝{Colors.END}")
        print()
        print(f"{Colors.CYAN}Processing events... (Press Ctrl+C to stop){Colors.END}")
        print()
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        last_stats_time = time.time()
        stats_interval = 30  # Print stats every 30 seconds
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                try:
                    event = message.value
                    self.process_event(event)
                    
                    # Print periodic stats
                    if time.time() - last_stats_time > stats_interval:
                        self._print_stats()
                        last_stats_time = time.time()
                        
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    self.stats['errors'] += 1
        
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()
    
    def process_event(self, event: Dict):
        """
        Process a single Suricata event.
        
        Args:
            event: Suricata event dictionary (flow, alert, http, dns, etc.)
        """
        try:
            self.stats['events_processed'] += 1
            event_type = event.get('event_type', 'unknown')
            
            # Handle different event types
            if event_type == 'flow':
                self._process_flow_event(event)
            elif event_type == 'alert':
                self._process_alert_event(event)
            else:
                # Other event types (http, dns, tls, etc.) - log for now
                logger.debug(f"Received {event_type} event (not processed)")
        
        except Exception as e:
            logger.error(f"Error in process_event: {e}", exc_info=True)
            self.stats['errors'] += 1
    
    def _process_flow_event(self, flow_event: Dict):
        """
        Process a flow event with ML inference.
        
        This is the main processing path for all network flows.
        """
        try:
            self.stats['flows_processed'] += 1
            
            # Extract CICIDS2017 features
            features = self.feature_extractor.extract_from_flow(flow_event)
            if not features:
                logger.debug("Feature extraction failed for flow")
                return
            
            # Convert features to numpy array
            feature_vector = self.feature_extractor.get_feature_vector(features)
            feature_array = np.array([feature_vector])
            
            # ML prediction
            prediction, confidence = self.model_loader.predict(feature_array)
            self.stats['ml_predictions'] += 1
            
            if prediction and prediction != 'BENIGN':
                logger.info(
                    f"ML Alert: {prediction} (confidence: {confidence:.2%}) - "
                    f"{flow_event.get('src_ip')}:{flow_event.get('src_port')} → "
                    f"{flow_event.get('dest_ip')}:{flow_event.get('dest_port')}"
                )
            
            # Check if we have a correlated Suricata alert for this flow
            flow_id = flow_event.get('flow_id')
            suricata_alert = None
            if flow_id and flow_id in self.flow_cache:
                cached = self.flow_cache[flow_id]
                suricata_alert = cached.get('alert')
            
            # Process combined alert
            enhanced_alert = self.alert_processor.process_flow_with_ml(
                flow_event,
                ml_prediction=prediction,
                ml_confidence=confidence,
                suricata_alert=suricata_alert
            )
            
            # Send enhanced alert to Kafka if generated
            if enhanced_alert:
                self._send_to_kafka(enhanced_alert)
                self.stats['ml_alerts_generated'] += 1
                
                # Remove from cache if correlated
                if flow_id and flow_id in self.flow_cache:
                    del self.flow_cache[flow_id]
        
        except Exception as e:
            logger.error(f"Error processing flow event: {e}", exc_info=True)
            self.stats['errors'] += 1
    
    def _process_alert_event(self, alert_event: Dict):
        """
        Process a Suricata alert event.
        
        Cache the alert and wait for corresponding flow event for correlation.
        """
        try:
            self.stats['alerts_processed'] += 1
            
            # Extract flow ID for correlation
            flow_id = alert_event.get('flow_id')
            if not flow_id:
                logger.debug("Alert without flow_id - processing independently")
                # Process alert without flow correlation
                enhanced_alert = self.alert_processor.process_flow_with_ml(
                    alert_event,
                    suricata_alert=alert_event
                )
                if enhanced_alert:
                    self._send_to_kafka(enhanced_alert)
                return
            
            # Cache alert for flow correlation
            if flow_id not in self.flow_cache:
                self.flow_cache[flow_id] = {}
            self.flow_cache[flow_id]['alert'] = alert_event
            self.flow_cache[flow_id]['timestamp'] = time.time()
            
            # Cleanup old cache entries
            self._cleanup_flow_cache()
        
        except Exception as e:
            logger.error(f"Error processing alert event: {e}", exc_info=True)
            self.stats['errors'] += 1
    
    def _cleanup_flow_cache(self):
        """Remove old entries from flow cache."""
        if len(self.flow_cache) > self.flow_cache_max_size:
            # Remove oldest 10%
            timeout = self.config['flow_correlation_timeout']
            current_time = time.time()
            
            to_remove = []
            for flow_id, data in self.flow_cache.items():
                if current_time - data.get('timestamp', 0) > timeout:
                    to_remove.append(flow_id)
            
            for flow_id in to_remove:
                del self.flow_cache[flow_id]
    
    def _send_to_kafka(self, alert: Dict):
        """Send enhanced alert to Kafka output topic."""
        try:
            future = self.producer.send(self.config['kafka_output_topic'], alert)
            # Wait for send to complete (with timeout)
            future.get(timeout=2)
            self.stats['enhanced_alerts_sent'] += 1
            
        except Exception as e:
            logger.error(f"Error sending to Kafka: {e}")
            self.stats['errors'] += 1
    
    def _print_stats(self):
        """Print processing statistics."""
        runtime = time.time() - self.stats['start_time']
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}═══ Statistics ({runtime:.0f}s) ═══{Colors.END}")
        print(f"  Events processed: {self.stats['events_processed']}")
        print(f"  Flows processed: {self.stats['flows_processed']}")
        print(f"  Alerts processed: {self.stats['alerts_processed']}")
        print(f"  ML predictions: {self.stats['ml_predictions']}")
        print(f"  ML alerts: {self.stats['ml_alerts_generated']}")
        print(f"  Enhanced alerts sent: {self.stats['enhanced_alerts_sent']}")
        print(f"  Errors: {self.stats['errors']}")
        print(f"  Events/sec: {self.stats['events_processed']/runtime:.2f}")
        
        # Alert processor stats
        ap_stats = self.alert_processor.get_statistics()
        print(f"  Suricata alerts: {ap_stats['suricata_alerts']}")
        print(f"  Combined alerts: {ap_stats['combined_alerts']}")
        print()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        self.running = False
    
    def stop(self):
        """Stop the consumer and cleanup."""
        print(f"\n{Colors.YELLOW}Stopping consumer...{Colors.END}")
        self.running = False
        
        # Print final stats
        self._print_stats()
        
        # Close Kafka connections
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.flush()
            self.producer.close()
        
        print(f"{Colors.GREEN}✓ Consumer stopped{Colors.END}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='ML-Enhanced Kafka Consumer for IDS Pipeline'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='../config/pipeline.conf',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--model',
        type=str,
        help='ML model name (overrides config file)'
    )
    
    args = parser.parse_args()
    
    # Create consumer
    consumer = MLEnhancedKafkaConsumer(config_file=args.config)
    
    # Override model if specified
    if args.model:
        consumer.config['ml_model_name'] = args.model
    
    # Start processing
    consumer.start()


if __name__ == '__main__':
    main()
