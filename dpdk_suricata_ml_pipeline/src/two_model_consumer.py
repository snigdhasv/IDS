#!/usr/bin/env python3
"""
Two-Model Ensemble Kafka Consumer

Consumes Suricata events from Kafka, performs ML inference using a two-model
ensemble with meta-learner, and publishes enhanced alerts.

Usage:
    python two_model_consumer.py <model1> <model2> [--train]
    
Example:
    python two_model_consumer.py random_forest_model_2017.joblib lgb_model_2018.joblib --train
"""

import json
import logging
import sys
import time
import signal
import argparse
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from collections import defaultdict, deque

import numpy as np
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

# Import custom modules
from feature_extractor import CICIDS2017FeatureExtractor
from feature_mapper import FeatureMapper
from two_model_loader import load_two_models, list_available_models, DEFAULT_MODEL_DIR
from alert_processor import AlertProcessor
from metrics_logger import MetricsLogger, LatencyTimer

# Configure logging
LOG_DIR = Path(__file__).parent.parent / 'logs' / 'ml'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'two_model_ensemble.log'

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
    """Terminal colors for output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


class TwoModelKafkaConsumer:
    """
    Two-Model Ensemble Kafka Consumer.
    
    Uses a meta-learner to adaptively weight two models based on confidence.
    """
    
    def __init__(self, model1_file: str, model2_file: str, 
                 train_meta_learner: bool = False, config_file: str = None):
        """
        Initialize consumer with two models.
        
        Args:
            model1_file: First model filename
            model2_file: Second model filename
            train_meta_learner: Whether to collect training data for meta-learner
            config_file: Pipeline config file
        """
        self.model1_file = model1_file
        self.model2_file = model2_file
        self.train_meta_learner = train_meta_learner
        
        # Load configuration
        self.config = self._load_config(config_file)
        
        # Initialize components
        self.feature_extractor = CICIDS2017FeatureExtractor()
        self.feature_mapper = FeatureMapper(target_features=34)
        self.alert_processor = AlertProcessor()
        
        # Initialize metrics logger
        self.metrics = MetricsLogger(enable_console=False, enable_file=True, enable_csv=True)
        self.metrics.start()
        logger.info("Metrics logger initialized for ensemble consumer")
        
        # Load ensemble (meta-learner will be trained later if needed)
        print(f"\n{Colors.BOLD}🎯 Initializing Two-Model Ensemble{Colors.END}")
        self.ensemble = load_two_models(
            model1_file, model2_file, 
            model_dir=DEFAULT_MODEL_DIR,
            train_data=None,  # Will train later
            verbose=True
        )
        
        # Training data buffer (if training meta-learner)
        self.training_buffer = {
            'X': [],
            'y': []
        }
        self.training_samples_needed = 1000  # Collect 1000 labeled samples
        
        # Kafka components
        self.consumer = None
        self.producer = None
        
        # Statistics
        self.stats = {
            'events_processed': 0,
            'flows_processed': 0,
            'ml_predictions': 0,
            'ml_alerts_generated': 0,
            'enhanced_alerts_sent': 0,
            'training_samples_collected': 0,
            'meta_learner_trained': False,
            'errors': 0,
            'start_time': None,
            'model1_wins': 0,
            'model2_wins': 0,
            'agreement_count': 0,
        }
        
        # Shutdown flag
        self.running = True
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)
    
    def _load_config(self, config_file: Optional[str]) -> Dict:
        """Load pipeline configuration."""
        if config_file is None:
            config_file = Path(__file__).parent.parent.parent / 'config' / 'ids_config.yaml'
        
        try:
            import yaml
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Ensure kafka config has required fields
            if 'kafka' in config:
                # Add default topics if not present
                if 'input_topic' not in config['kafka']:
                    config['kafka']['input_topic'] = 'suricata-events'
                if 'output_topic' not in config['kafka']:
                    config['kafka']['output_topic'] = 'enhanced-alerts'
                if 'group_id' not in config['kafka']:
                    config['kafka']['group_id'] = 'two-model-ml-consumer'
            
            # Add ML config if not present
            if 'ml' not in config:
                config['ml'] = {
                    'prediction_threshold': 0.7,
                    'batch_size': 10
                }
            
            logger.info(f"Configuration loaded from {config_file}")
            return config
            
        except Exception as e:
            logger.warning(f"Could not load config: {e}. Using defaults.")
            return {
                'kafka': {
                    'bootstrap_servers': 'localhost:9092',
                    'input_topic': 'suricata-events',
                    'output_topic': 'enhanced-alerts',
                    'group_id': 'two-model-ml-consumer'
                },
                'ml': {
                    'prediction_threshold': 0.7,
                    'batch_size': 10
                }
            }
    
    def _shutdown_handler(self, signum, frame):
        """Handle graceful shutdown."""
        print(f"\n{Colors.YELLOW}📊 Shutting down gracefully...{Colors.END}")
        self.running = False
    
    def initialize_kafka(self):
        """Initialize Kafka consumer and producer."""
        kafka_config = self.config['kafka']
        
        try:
            # Consumer
            self.consumer = KafkaConsumer(
                kafka_config['input_topic'],
                bootstrap_servers=kafka_config['bootstrap_servers'],
                group_id=kafka_config.get('group_id', 'two-model-ml-consumer'),
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True,
                session_timeout_ms=30000,
                max_poll_records=100
            )
            
            # Producer
            self.producer = KafkaProducer(
                bootstrap_servers=kafka_config['bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3
            )
            
            logger.info(f"✓ Kafka initialized: {kafka_config['bootstrap_servers']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka: {e}")
            return False
    
    def process_event(self, event: Dict) -> Optional[Dict]:
        """
        Process a single Suricata event.
        
        Returns:
            Enhanced alert if threat detected, else None
        """
        self.stats['events_processed'] += 1
        
        try:
            event_type = event.get('event_type', '')
            
            # Process flow events through ML
            if event_type == 'flow':
                return self._process_flow(event)
            
            # Log other event types
            elif event_type in ['alert', 'anomaly', 'dns', 'http', 'tls']:
                logger.debug(f"Received {event_type} event")
            
            return None
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error processing event: {e}")
            return None
    
    def _process_flow(self, flow_event: Dict) -> Optional[Dict]:
        """Process flow event through ensemble."""
        self.stats['flows_processed'] += 1
        flow_start_time = time.time()
        
        try:
            # Extract features
            with LatencyTimer(self.metrics, 'ensemble_consumer', 'feature_extraction'):
                features = self.feature_extractor.extract_from_flow(flow_event)
                if features is None:
                    return None
                
                # Map to 34-feature format
                mapped_features = self.feature_mapper.map_features(features)
                X = np.array([mapped_features])
            
            # If collecting training data, buffer this sample
            if self.train_meta_learner and not self.ensemble.is_trained:
                self._collect_training_sample(X, flow_event)
                
                # Train meta-learner when enough samples collected
                if len(self.training_buffer['X']) >= self.training_samples_needed:
                    self._train_meta_learner_now()
            
            # Make prediction with latency tracking
            prediction_method = 'meta_learner' if self.ensemble.is_trained else 'confidence_adaptive'
            
            inference_start = time.time()
            predictions, confidences, metrics = self.ensemble.predict(X, method=prediction_method)
            inference_time_ms = (time.time() - inference_start) * 1000
            
            self.stats['ml_predictions'] += 1
            
            # Log ML inference metrics
            prediction = predictions[0]
            confidence = float(confidences[0])
            self.metrics.log_ml_inference(
                model_name=f"ensemble_{prediction_method}",
                inference_time_ms=inference_time_ms,
                prediction=prediction,
                confidence=confidence,
                features_count=34,
                batch_size=1
            )
            
            # Log ensemble-specific latency metrics
            self.metrics.log_latency(
                component='ensemble_consumer',
                operation='model1_inference',
                latency_ms=metrics.get('model1_time_ms', 0)
            )
            self.metrics.log_latency(
                component='ensemble_consumer',
                operation='model2_inference',
                latency_ms=metrics.get('model2_time_ms', 0)
            )
            self.metrics.log_latency(
                component='ensemble_consumer',
                operation='meta_learner_inference',
                latency_ms=metrics.get('meta_time_ms', 0)
            )
            
            # Update statistics
            if metrics['agreement_rate'] > 0.5:
                self.stats['agreement_count'] += 1
            if metrics['avg_weight_model1'] > 0.5:
                self.stats['model1_wins'] += 1
            else:
                self.stats['model2_wins'] += 1
            
            # Check if attack detected
            if prediction != 'BENIGN' and confidence >= self.config['ml']['prediction_threshold']:
                self.stats['ml_alerts_generated'] += 1
                
                # Create enhanced alert
                enhanced_alert = self._create_enhanced_alert(
                    flow_event, prediction, confidence, metrics
                )
                
                # Log total flow processing latency
                flow_latency_ms = (time.time() - flow_start_time) * 1000
                self.metrics.log_latency(
                    component='ensemble_consumer',
                    operation='flow_processing_total',
                    latency_ms=flow_latency_ms,
                    event_type=prediction
                )
                
                return enhanced_alert
            
            # Log latency for benign flows too
            flow_latency_ms = (time.time() - flow_start_time) * 1000
            self.metrics.log_latency(
                component='ensemble_consumer',
                operation='flow_processing_total',
                latency_ms=flow_latency_ms,
                event_type='BENIGN'
            )
            
            return None
            
        except Exception as e:
            self.stats['errors'] += 1
            self.metrics.log_error(
                component='ensemble_consumer',
                error_type=type(e).__name__,
                error_message=str(e),
                severity='error'
            )
            logger.error(f"Error processing flow: {e}")
            return None
    
    def _collect_training_sample(self, X: np.ndarray, flow_event: Dict):
        """Collect samples for training meta-learner."""
        # For now, we'll use Suricata alerts as labels
        # In production, you'd want manually verified labels
        
        # Simple heuristic: if Suricata flagged it, assume attack
        # This is imperfect but allows autonomous meta-learner training
        if 'alert' in flow_event or flow_event.get('event_type') == 'alert':
            label = 'ATTACK'  # Simplified - would map to actual attack type
        else:
            label = 'BENIGN'
        
        self.training_buffer['X'].append(X[0])
        self.training_buffer['y'].append(label)
        self.stats['training_samples_collected'] += 1
        
        if self.stats['training_samples_collected'] % 100 == 0:
            print(f"   Training samples: {self.stats['training_samples_collected']}/{self.training_samples_needed}")
    
    def _train_meta_learner_now(self):
        """Train the meta-learner on collected samples."""
        print(f"\n{Colors.BOLD}🧠 Training meta-learner...{Colors.END}")
        
        X_train = np.array(self.training_buffer['X'])
        y_train = np.array(self.training_buffer['y'])
        
        try:
            self.ensemble.train_meta_learner(X_train, y_train, verbose=True)
            self.stats['meta_learner_trained'] = True
            print(f"{Colors.GREEN}✓ Meta-learner trained successfully!{Colors.END}\n")
        except Exception as e:
            logger.error(f"Failed to train meta-learner: {e}")
    
    def _create_enhanced_alert(self, flow_event: Dict, prediction: str, 
                              confidence: float, metrics: Dict) -> Dict:
        """Create enhanced alert with ensemble metrics."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'alert_type': 'ml_ensemble',
            'prediction': prediction,
            'confidence': confidence,
            'ensemble_method': metrics['method'],
            'model1': {
                'name': self.ensemble.model1_name,
                'weight': metrics['avg_weight_model1'],
                'confidence': metrics['model1_avg_conf']
            },
            'model2': {
                'name': self.ensemble.model2_name,
                'weight': metrics['avg_weight_model2'],
                'confidence': metrics['model2_avg_conf']
            },
            'agreement': metrics['agreement_rate'] > 0.5,
            'flow': {
                'src_ip': flow_event.get('src_ip', 'unknown'),
                'src_port': flow_event.get('src_port', 0),
                'dest_ip': flow_event.get('dest_ip', 'unknown'),
                'dest_port': flow_event.get('dest_port', 0),
                'proto': flow_event.get('proto', 'unknown'),
            },
            'severity': 'HIGH' if confidence > 0.9 else 'MEDIUM',
        }
    
    def run(self):
        """Main consumer loop."""
        if not self.initialize_kafka():
            logger.error("Failed to initialize. Exiting.")
            return
        
        self.stats['start_time'] = time.time()
        last_throughput_log = time.time()
        events_since_last_log = 0
        
        print(f"\n{Colors.BOLD}{Colors.GREEN}🚀 Two-Model Ensemble Consumer Running{Colors.END}")
        print(f"   Model 1: {Colors.CYAN}{self.ensemble.model1_name}{Colors.END}")
        print(f"   Model 2: {Colors.CYAN}{self.ensemble.model2_name}{Colors.END}")
        print(f"   Meta-learner: {Colors.YELLOW}{'Enabled' if self.train_meta_learner else 'Disabled'}{Colors.END}")
        print(f"   Input: {Colors.BLUE}{self.config['kafka']['input_topic']}{Colors.END}")
        print(f"   Output: {Colors.BLUE}{self.config['kafka']['output_topic']}{Colors.END}\n")
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                # Process event
                event = message.value
                enhanced_alert = self.process_event(event)
                events_since_last_log += 1
                
                # Publish alert if generated
                if enhanced_alert:
                    self.producer.send(
                        self.config['kafka']['output_topic'],
                        value=enhanced_alert
                    )
                    self.stats['enhanced_alerts_sent'] += 1
                    
                    # Log alert
                    print(f"{Colors.RED}🚨 ALERT{Colors.END}: {enhanced_alert['prediction']} "
                          f"(conf: {enhanced_alert['confidence']:.3f}, "
                          f"w1: {enhanced_alert['model1']['weight']:.2f})")
                
                # Log throughput metrics every 10 seconds
                current_time = time.time()
                if current_time - last_throughput_log >= 10.0:
                    window_seconds = current_time - last_throughput_log
                    self.metrics.log_throughput(
                        component='ensemble_consumer',
                        events_count=events_since_last_log,
                        window_seconds=window_seconds
                    )
                    last_throughput_log = current_time
                    events_since_last_log = 0
                
                # Print stats periodically
                if self.stats['events_processed'] % 100 == 0:
                    self._print_stats()
        
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Interrupted by user{Colors.END}")
        
        finally:
            self._cleanup()
    
    def _print_stats(self):
        """Print current statistics."""
        runtime = time.time() - self.stats['start_time']
        eps = self.stats['events_processed'] / runtime if runtime > 0 else 0
        
        print(f"\n{Colors.BOLD}📊 Statistics{Colors.END}")
        print(f"   Events: {self.stats['events_processed']:,} ({eps:.1f}/sec)")
        print(f"   Flows: {self.stats['flows_processed']:,}")
        print(f"   ML Predictions: {self.stats['ml_predictions']:,}")
        print(f"   Alerts Generated: {self.stats['ml_alerts_generated']:,}")
        print(f"   Model 1 Preferred: {self.stats['model1_wins']:,}")
        print(f"   Model 2 Preferred: {self.stats['model2_wins']:,}")
        print(f"   Agreement: {self.stats['agreement_count']:,}")
        print(f"   Meta-learner: {'✓ Trained' if self.stats['meta_learner_trained'] else '✗ Not trained'}")
    
    def _cleanup(self):
        """Cleanup resources."""
        print(f"\n{Colors.YELLOW}Cleaning up...{Colors.END}")
        
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()
        
        # Final stats
        self._print_stats()
        
        # Ensemble metrics
        ensemble_metrics = self.ensemble.get_metrics_summary()
        print(f"\n{Colors.BOLD}🎯 Ensemble Metrics{Colors.END}")
        print(f"   Total predictions: {ensemble_metrics['total_predictions']:,}")
        print(f"   {self.ensemble.model1_name} avg confidence: {ensemble_metrics['model1_performance']['avg_confidence']:.3f}")
        print(f"   {self.ensemble.model2_name} avg confidence: {ensemble_metrics['model2_performance']['avg_confidence']:.3f}")
        print(f"   Agreement rate: {ensemble_metrics['ensemble']['agreement_rate']:.3f}")
        
        # Print metrics summary
        print(f"\n{Colors.BOLD}📊 Performance Metrics Summary{Colors.END}")
        self.metrics.print_summary_report()
        
        # Stop metrics logger
        self.metrics.stop()
        logger.info(f"Metrics saved to: {self.metrics.metrics_dir}")
        
        print(f"\n{Colors.GREEN}✓ Shutdown complete{Colors.END}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Two-Model Ensemble Kafka Consumer')
    parser.add_argument('model1', help='First model filename (in ML Models/)')
    parser.add_argument('model2', help='Second model filename (in ML Models/)')
    parser.add_argument('--train', action='store_true', 
                       help='Collect data and train meta-learner')
    parser.add_argument('--config', help='Config file path')
    
    args = parser.parse_args()
    
    # Validate models exist
    available = list_available_models()
    if args.model1 not in available:
        print(f"❌ Model not found: {args.model1}")
        print(f"Available models: {', '.join(available)}")
        sys.exit(1)
    if args.model2 not in available:
        print(f"❌ Model not found: {args.model2}")
        print(f"Available models: {', '.join(available)}")
        sys.exit(1)
    
    # Create and run consumer
    consumer = TwoModelKafkaConsumer(
        args.model1, args.model2,
        train_meta_learner=args.train,
        config_file=args.config
    )
    consumer.run()


if __name__ == "__main__":
    main()
