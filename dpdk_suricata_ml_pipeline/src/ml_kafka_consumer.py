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
from feature_mapper import FeatureMapper
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
        self.feature_mapper = FeatureMapper(target_features=34)  # Map 65→34 features
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
        
        # Performance metrics
        self.performance_metrics = {
            'inference_times': [],  # Track ML inference latency
            'feature_extraction_times': [],  # Track feature extraction time
            'total_processing_times': [],  # Track end-to-end processing time
            'predictions_by_class': {},  # Count predictions per class
            'confidence_scores': [],  # Track confidence distribution
            'batch_sizes': [],  # Track batch processing sizes
        }
        
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
                enable_auto_commit=True
                # Using poll() method, no consumer_timeout_ms needed
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
            # Use polling loop instead of iterator for better control
            while self.running:
                # Poll for messages (10 second timeout per poll)
                messages = self.consumer.poll(timeout_ms=10000, max_records=100)
                
                if not messages:
                    # No messages in this poll, continue waiting
                    continue
                
                # Process all messages from this poll
                for topic_partition, records in messages.items():
                    for message in records:
                        if not self.running:
                            break
                        
                        try:
                            event = message.value
                            self.process_event(event)
                            
                        except Exception as e:
                            logger.error(f"Error processing message: {e}", exc_info=True)
                            self.stats['errors'] += 1
                
                # Print periodic stats
                if time.time() - last_stats_time > stats_interval:
                    self._print_stats()
                    last_stats_time = time.time()
        
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
            processing_start = time.time()
            self.stats['flows_processed'] += 1
            
            # Extract CICIDS2017 features (measure time)
            feature_start = time.time()
            features = self.feature_extractor.extract_from_flow(flow_event)
            feature_time = time.time() - feature_start
            self.performance_metrics['feature_extraction_times'].append(feature_time)
            
            if not features:
                logger.debug("Feature extraction failed for flow")
                return
            
            # Map 65 features to 34 features for model compatibility
            feature_array = self.feature_mapper.map_to_34(features)
            
            # ML prediction with confidence (measure time)
            inference_start = time.time()
            predictions = self.model_loader.predict(feature_array)
            probabilities = self.model_loader.predict_proba(feature_array)
            inference_time = time.time() - inference_start
            self.performance_metrics['inference_times'].append(inference_time)
            
            prediction = predictions[0] if len(predictions) > 0 else 'BENIGN'
            confidence = float(np.max(probabilities[0])) if len(probabilities) > 0 else 0.0
            self.stats['ml_predictions'] += 1
            
            # Track prediction distribution
            if prediction not in self.performance_metrics['predictions_by_class']:
                self.performance_metrics['predictions_by_class'][prediction] = 0
            self.performance_metrics['predictions_by_class'][prediction] += 1
            
            # Track confidence scores
            self.performance_metrics['confidence_scores'].append(confidence)
            
            if prediction and prediction != 'BENIGN':
                logger.info(
                    f"ML Alert: {prediction} (confidence: {confidence:.2%}) - "
                    f"{flow_event.get('src_ip')}:{flow_event.get('src_port')} → "
                    f"{flow_event.get('dest_ip')}:{flow_event.get('dest_port')}"
                )
            
            # Process ML alert (no correlation with Suricata alerts)
            enhanced_alert = self.alert_processor.process_flow_with_ml(
                flow_event,
                ml_prediction=prediction,
                ml_confidence=confidence,
                suricata_alert=None
            )
            
            # Send enhanced alert to Kafka if generated
            if enhanced_alert:
                self._send_to_kafka(enhanced_alert)
                self.stats['ml_alerts_generated'] += 1
            
            # Track total processing time
            total_time = time.time() - processing_start
            self.performance_metrics['total_processing_times'].append(total_time)
        
        except Exception as e:
            logger.error(f"Error processing flow event: {e}", exc_info=True)
            self.stats['errors'] += 1
    
    def _process_alert_event(self, alert_event: Dict):
        """
        Process a Suricata alert event.
        
        Forward Suricata alerts directly without correlation.
        """
        try:
            self.stats['alerts_processed'] += 1
            
            # Process and forward Suricata alert
            enhanced_alert = self.alert_processor.process_flow_with_ml(
                alert_event,
                suricata_alert=alert_event
            )
            if enhanced_alert:
                self._send_to_kafka(enhanced_alert)
        
        except Exception as e:
            logger.error(f"Error processing alert event: {e}", exc_info=True)
            self.stats['errors'] += 1
    
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
        """Print comprehensive processing statistics and performance metrics."""
        runtime = time.time() - self.stats['start_time']
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}╔════════════════════════════════════════════════════════════════╗{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}║         ML IDS Performance Metrics ({runtime:.0f}s runtime)            ║{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}╚════════════════════════════════════════════════════════════════╝{Colors.END}\n")
        
        # === THROUGHPUT METRICS ===
        print(f"{Colors.BOLD}{Colors.BLUE}📊 THROUGHPUT METRICS{Colors.END}")
        print(f"  Events processed:      {self.stats['events_processed']:,}")
        print(f"  Flows processed:       {self.stats['flows_processed']:,}")
        print(f"  Alerts processed:      {self.stats['alerts_processed']:,}")
        print(f"  ML predictions:        {self.stats['ml_predictions']:,}")
        print(f"  ML alerts generated:   {self.stats['ml_alerts_generated']:,}")
        print(f"  Enhanced alerts sent:  {self.stats['enhanced_alerts_sent']:,}")
        if runtime > 0:
            print(f"  Events/sec:            {self.stats['events_processed']/runtime:.2f}")
            print(f"  Flows/sec:             {self.stats['flows_processed']/runtime:.2f}")
            print(f"  Predictions/sec:       {self.stats['ml_predictions']/runtime:.2f}")
        print()
        
        # === LATENCY METRICS ===
        print(f"{Colors.BOLD}{Colors.MAGENTA}⚡ LATENCY METRICS{Colors.END}")
        if self.performance_metrics['inference_times']:
            inf_times = np.array(self.performance_metrics['inference_times']) * 1000  # Convert to ms
            print(f"  ML Inference Latency:")
            print(f"    Average:   {np.mean(inf_times):.3f} ms")
            print(f"    Median:    {np.median(inf_times):.3f} ms")
            print(f"    Min:       {np.min(inf_times):.3f} ms")
            print(f"    Max:       {np.max(inf_times):.3f} ms")
            print(f"    P95:       {np.percentile(inf_times, 95):.3f} ms")
            print(f"    P99:       {np.percentile(inf_times, 99):.3f} ms")
        
        if self.performance_metrics['feature_extraction_times']:
            feat_times = np.array(self.performance_metrics['feature_extraction_times']) * 1000
            print(f"  Feature Extraction Latency:")
            print(f"    Average:   {np.mean(feat_times):.3f} ms")
            print(f"    Median:    {np.median(feat_times):.3f} ms")
        
        if self.performance_metrics['total_processing_times']:
            total_times = np.array(self.performance_metrics['total_processing_times']) * 1000
            print(f"  Total Processing Latency:")
            print(f"    Average:   {np.mean(total_times):.3f} ms")
            print(f"    Median:    {np.median(total_times):.3f} ms")
            print(f"    P95:       {np.percentile(total_times, 95):.3f} ms")
            print(f"    P99:       {np.percentile(total_times, 99):.3f} ms")
        print()
        
        # === PREDICTION DISTRIBUTION ===
        print(f"{Colors.BOLD}{Colors.YELLOW}🎯 PREDICTION DISTRIBUTION{Colors.END}")
        if self.performance_metrics['predictions_by_class']:
            total_preds = sum(self.performance_metrics['predictions_by_class'].values())
            for pred_class, count in sorted(self.performance_metrics['predictions_by_class'].items(), 
                                           key=lambda x: x[1], reverse=True):
                percentage = (count / total_preds * 100) if total_preds > 0 else 0
                bar_length = int(percentage / 2)  # Scale to 50 chars max
                bar = "█" * bar_length
                print(f"  {pred_class:<20s} {count:>6,} ({percentage:>5.1f}%) {bar}")
        print()
        
        # === CONFIDENCE DISTRIBUTION ===
        print(f"{Colors.BOLD}{Colors.CYAN}📈 CONFIDENCE DISTRIBUTION{Colors.END}")
        if self.performance_metrics['confidence_scores']:
            conf_scores = np.array(self.performance_metrics['confidence_scores'])
            print(f"  Average Confidence:    {np.mean(conf_scores):.2%}")
            print(f"  Median Confidence:     {np.median(conf_scores):.2%}")
            print(f"  Min Confidence:        {np.min(conf_scores):.2%}")
            print(f"  Max Confidence:        {np.max(conf_scores):.2%}")
            print(f"  Std Deviation:         {np.std(conf_scores):.2%}")
            
            # Confidence ranges
            high_conf = np.sum(conf_scores >= 0.9)
            med_conf = np.sum((conf_scores >= 0.7) & (conf_scores < 0.9))
            low_conf = np.sum(conf_scores < 0.7)
            print(f"  High confidence (≥90%): {high_conf:,}")
            print(f"  Med confidence (70-90%): {med_conf:,}")
            print(f"  Low confidence (<70%):  {low_conf:,}")
        print()
        
        # === MODEL INFO ===
        print(f"{Colors.BOLD}{Colors.MAGENTA}🤖 MODEL INFORMATION{Colors.END}")
        model_info = self.model_loader.get_model_info()
        print(f"  Model Name:            {self.config.get('ml_model_name', 'Unknown')}")
        print(f"  Model Type:            {model_info.get('model_type', 'Unknown')}")
        print(f"  Expected Features:     {model_info.get('expected_features', 'Unknown')}")
        print()
        
        # === ALERT PROCESSOR STATS ===
        ap_stats = self.alert_processor.get_statistics()
        print(f"{Colors.BOLD}{Colors.RED}🚨 ALERT STATISTICS{Colors.END}")
        print(f"  Suricata alerts:       {ap_stats['suricata_alerts']:,}")
        print(f"  Combined alerts:       {ap_stats['combined_alerts']:,}")
        print(f"  Errors:                {self.stats['errors']:,}")
        print()
        
        print(f"{Colors.BOLD}{Colors.GREEN}{'─' * 64}{Colors.END}\n")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        self.running = False
    
    def save_metrics_to_file(self):
        """Save performance metrics to JSON file for later analysis."""
        try:
            metrics_file = LOG_DIR / f'performance_metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            
            # Calculate summary metrics
            runtime = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
            
            metrics_summary = {
                'timestamp': datetime.now().isoformat(),
                'runtime_seconds': runtime,
                'model_name': self.config.get('ml_model_name', 'Unknown'),
                'model_type': self.model_loader.get_model_info().get('model_type', 'Unknown'),
                'throughput': {
                    'events_processed': self.stats['events_processed'],
                    'flows_processed': self.stats['flows_processed'],
                    'alerts_processed': self.stats['alerts_processed'],
                    'ml_predictions': self.stats['ml_predictions'],
                    'events_per_sec': self.stats['events_processed'] / runtime if runtime > 0 else 0,
                    'predictions_per_sec': self.stats['ml_predictions'] / runtime if runtime > 0 else 0,
                },
                'latency_ms': {
                    'inference': {
                        'mean': float(np.mean(self.performance_metrics['inference_times']) * 1000) if self.performance_metrics['inference_times'] else 0,
                        'median': float(np.median(self.performance_metrics['inference_times']) * 1000) if self.performance_metrics['inference_times'] else 0,
                        'p95': float(np.percentile(self.performance_metrics['inference_times'], 95) * 1000) if self.performance_metrics['inference_times'] else 0,
                        'p99': float(np.percentile(self.performance_metrics['inference_times'], 99) * 1000) if self.performance_metrics['inference_times'] else 0,
                    },
                    'feature_extraction': {
                        'mean': float(np.mean(self.performance_metrics['feature_extraction_times']) * 1000) if self.performance_metrics['feature_extraction_times'] else 0,
                    },
                    'total_processing': {
                        'mean': float(np.mean(self.performance_metrics['total_processing_times']) * 1000) if self.performance_metrics['total_processing_times'] else 0,
                        'p95': float(np.percentile(self.performance_metrics['total_processing_times'], 95) * 1000) if self.performance_metrics['total_processing_times'] else 0,
                    }
                },
                'predictions_by_class': self.performance_metrics['predictions_by_class'],
                'confidence_stats': {
                    'mean': float(np.mean(self.performance_metrics['confidence_scores'])) if self.performance_metrics['confidence_scores'] else 0,
                    'median': float(np.median(self.performance_metrics['confidence_scores'])) if self.performance_metrics['confidence_scores'] else 0,
                    'std': float(np.std(self.performance_metrics['confidence_scores'])) if self.performance_metrics['confidence_scores'] else 0,
                },
                'errors': self.stats['errors']
            }
            
            # Save to file
            with open(metrics_file, 'w') as f:
                json.dump(metrics_summary, f, indent=2)
            
            print(f"{Colors.GREEN}✓ Performance metrics saved to: {metrics_file}{Colors.END}")
            logger.info(f"Performance metrics saved to {metrics_file}")
            
        except Exception as e:
            logger.error(f"Error saving metrics to file: {e}", exc_info=True)
    
    def stop(self):
        """Stop the consumer and cleanup."""
        print(f"\n{Colors.YELLOW}Stopping consumer...{Colors.END}")
        self.running = False
        
        # Print final stats
        self._print_stats()
        
        # Save metrics to file
        self.save_metrics_to_file()
        
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
