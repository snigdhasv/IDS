#!/usr/bin/env python3
"""
Ensemble ML Consumer with CSV Logging for Accuracy Metrics

Logs predictions with confidence scores to CSV for accuracy calculation:
- Feature vector ID
- Ground truth label (if available from PCAP metadata)
- Ensemble prediction
- Per-model predictions
- Confidence scores
- Timestamp

Usage with PCAP replay:
    python3 realtime_ensemble_consumer_with_csv.py --csv-output predictions.csv
"""

import json
import logging
import sys
import signal
import warnings
import os
import csv
import time
from typing import Any, Dict, List, Tuple
from pathlib import Path
from collections import Counter
from datetime import datetime
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import numpy as np
from metrics_logger import MetricsLogger

# Suppress ALL warnings (sklearn feature name warnings)
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

# Import ML model loader
sys.path.insert(0, str(Path(__file__).parent))
from model_loader import MLModelLoader
import joblib

# Configuration
KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "ml-features"
KAFKA_GROUP = "ml-inference-ensemble"

# Ensemble Models - using NEW RAW feature models (NO PCA, 99%+ accuracy)
ENSEMBLE_MODELS = [
    "/home/ifscr/SE_02_2025/IDS/ML Models/random_forest_model_2017_raw.joblib",
    "/home/ifscr/SE_02_2025/IDS/ML Models/decision_tree_model_2017_raw.joblib",
    "/home/ifscr/SE_02_2025/IDS/ML Models/lgb_model_2017_raw.joblib",
    "/home/ifscr/SE_02_2025/IDS/ML Models/knn_model_2017_raw.joblib",
    "/home/ifscr/SE_02_2025/IDS/ML Models/lr_model_2017_raw.joblib",
]

# Scaler for raw features (models were trained on standardized features)
SCALER_PATH = "/home/ifscr/SE_02_2025/IDS/ML Models/scaler_2017_raw.joblib"

# Model features - EXACT 67 features the models were trained on (after preprocessing)
MODEL_FEATURES = [
    'Destination Port', 'Flow Duration', 'Total Fwd Packets', 'Total Backward Packets',
    'Total Length of Fwd Packets', 'Total Length of Bwd Packets', 'Fwd Packet Length Max',
    'Fwd Packet Length Min', 'Fwd Packet Length Mean', 'Fwd Packet Length Std',
    'Bwd Packet Length Max', 'Bwd Packet Length Min', 'Bwd Packet Length Mean',
    'Bwd Packet Length Std', 'Flow Bytes/s', 'Flow Packets/s', 'Flow IAT Mean',
    'Flow IAT Std', 'Flow IAT Max', 'Flow IAT Min', 'Fwd IAT Total', 'Fwd IAT Mean',
    'Fwd IAT Std', 'Fwd IAT Max', 'Fwd IAT Min', 'Bwd IAT Total', 'Bwd IAT Mean',
    'Bwd IAT Std', 'Bwd IAT Max', 'Bwd IAT Min', 'Fwd PSH Flags', 'Fwd Header Length',
    'Bwd Header Length', 'Fwd Packets/s', 'Bwd Packets/s', 'Min Packet Length',
    'Max Packet Length', 'Packet Length Mean', 'Packet Length Std', 'Packet Length Variance',
    'FIN Flag Count', 'SYN Flag Count', 'RST Flag Count', 'PSH Flag Count', 'ACK Flag Count',
    'URG Flag Count', 'ECE Flag Count', 'Down/Up Ratio', 'Average Packet Size',
    'Avg Fwd Segment Size', 'Avg Bwd Segment Size', 'Subflow Fwd Packets', 'Subflow Fwd Bytes',
    'Subflow Bwd Packets', 'Subflow Bwd Bytes', 'Init_Win_bytes_forward',
    'Init_Win_bytes_backward', 'act_data_pkt_fwd', 'min_seg_size_forward', 'Active Mean',
    'Active Std', 'Active Max', 'Active Min', 'Idle Mean', 'Idle Std', 'Idle Max', 'Idle Min'
]

# Logging - only show INFO level (predictions only)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',  # Simplified format
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Silence all other loggers (kafka, etc)
logging.getLogger('kafka').setLevel(logging.ERROR)
logging.getLogger('kafka.conn').setLevel(logging.ERROR)
logging.getLogger('kafka.coordinator').setLevel(logging.ERROR)
logging.getLogger('kafka.consumer').setLevel(logging.ERROR)
logging.getLogger('model_loader').setLevel(logging.ERROR)

# Label mapping
LABEL_MAP = {
    0: "BENIGN",
    1: "Attack"
}

def normalize_label(raw_label: Any) -> str:
    """Return a printable label for predictions/ground-truth values."""
    if raw_label is None:
        return "UNKNOWN"
    # Numeric labels → look up in LABEL_MAP, else keep numeric representation
    if isinstance(raw_label, (int, np.integer)):
        return LABEL_MAP.get(int(raw_label), str(raw_label))
    # scikit-learn models trained on strings already output human-readable classes
    if isinstance(raw_label, str):
        return raw_label
    return str(raw_label)


class EnsembleMLConsumerWithCSV:
    """Ensemble ML Consumer with CSV logging for accuracy metrics"""
    
    def __init__(self, kafka_bootstrap: str, kafka_topic: str, model_paths: List[str], 
                 csv_output: str = None):
        self.kafka_bootstrap = kafka_bootstrap
        self.kafka_topic = kafka_topic
        self.model_paths = model_paths
        self.running = True
        self.csv_output = csv_output
        self.csv_writer = None
        self.csv_file = None
        
        # Load all models
        self.models = []
        logger.info("🔄 Loading ensemble models...")
        for i, model_path in enumerate(model_paths, 1):
            loader = MLModelLoader()
            if loader.load_model(model_path):
                self.models.append({
                    'loader': loader,
                    'name': Path(model_path).stem,
                    'path': model_path
                })
                logger.info(f"  [{i}/{len(model_paths)}] ✓ {Path(model_path).name}")
            else:
                logger.warning(f"  [{i}/{len(model_paths)}] ✗ Failed: {Path(model_path).name}")
        
        if not self.models:
            raise ValueError("No models loaded successfully!")
        
        logger.info(f"✓ Loaded {len(self.models)}/{len(model_paths)} models for ensemble")
        
        # Load scaler for raw features
        try:
            self.scaler = joblib.load(SCALER_PATH)
            logger.info(f"✓ Loaded feature scaler from {Path(SCALER_PATH).name}")
        except Exception as e:
            logger.warning(f"⚠️  Could not load scaler: {e}. Using unscaled features.")
            self.scaler = None
        
        # Initialize Kafka consumer
        try:
            self.consumer = KafkaConsumer(
                kafka_topic,
                bootstrap_servers=kafka_bootstrap,
                group_id=KAFKA_GROUP,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            logger.info(f"✓ Connected to Kafka: {kafka_topic}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
        
        # Initialize CSV logging
        if csv_output:
            self._init_csv(csv_output)

        # Metrics logger (records JSON/CSV for dashboard)
        self.metrics_logger = MetricsLogger(enable_console=False, enable_file=True, enable_csv=True)
        self.metrics_logger.start()
        logger.info(f"✓ Metrics logging enabled (dir: {self.metrics_logger.metrics_dir})")
        
        # Statistics
        self.stats = {
            'total': 0,
            'benign': 0,
            'attacks': 0,
            'high_confidence': 0,  # >80% agreement
            'medium_confidence': 0,  # 60-80% agreement
            'low_confidence': 0,  # <60% agreement
            'correct': 0,  # Only if ground truth available
            'incorrect': 0,
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _init_csv(self, csv_path: str):
        """Initialize CSV file for logging predictions"""
        try:
            self.csv_file = open(csv_path, 'w', newline='')
            
            # CSV columns
            fieldnames = [
                'timestamp',
                'flow_id',
                'ground_truth',
                'ensemble_prediction',
                'ensemble_confidence',
                'agreement_ratio',
                'model_rf_pred',
                'model_rf_conf',
                'model_dt_pred',
                'model_dt_conf',
                'model_lgb_pred',
                'model_lgb_conf',
                'model_knn_pred',
                'model_knn_conf',
                'model_lr_pred',
                'model_lr_conf',
                'correct'
            ]
            
            self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
            self.csv_writer.writeheader()
            self.csv_file.flush()
            
            logger.info(f"✓ CSV output initialized: {csv_path}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize CSV: {e}")
            self.csv_writer = None
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Shutting down... (signal {signum})")
        self.running = False
    
    def start(self):
        """Start consuming and processing messages"""
        logger.info("🚀 Starting Ensemble ML Consumer (with CSV logging)")
        logger.info(f"   Consuming from: {self.kafka_topic}")
        logger.info(f"   Ensemble size: {len(self.models)}")
        if self.csv_output:
            logger.info(f"   CSV output: {self.csv_output}")
        logger.info("")
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                self._process_message(message.value)
                
                # Log stats every 100 messages
                if self.stats['total'] % 100 == 0:
                    logger.info(f"📊 Processed: {self.stats['total']} | "
                                f"Benign: {self.stats['benign']} | "
                                f"Attacks: {self.stats['attacks']} | "
                                f"High-conf: {self.stats['high_confidence']}")
        
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
        
        finally:
            self.consumer.close()
            if self.csv_file:
                self.csv_file.close()
            self.metrics_logger.stop()
            logger.info(f"✅ Consumer stopped. Final stats: {self.stats}")
    
    def _process_message(self, data: Dict):
        """Process feature vector with ensemble voting"""
        try:
            self.stats['total'] += 1
            inference_start = time.perf_counter()
            
            # Extract features dictionary from engine
            features_dict = data['features']
            flow_id = data.get('flow_id', f"flow_{self.stats['total']}")
            ground_truth = data.get('ground_truth', None)  # Optional: from PCAP metadata
            
            # DEBUG: Log first time
            if self.stats['total'] == 1:
                logger.info(f"🔍 Engine sent {len(features_dict)} features, selecting {len(MODEL_FEATURES)} for models")
            
            # Select ONLY the 67 features that models were trained on
            selected_features = [features_dict.get(fname, 0.0) for fname in MODEL_FEATURES]
            
            # HACK: Models expect 69 features but we only have 67
            # Add 2 dummy features with value 0.0 to match
            selected_features.extend([0.0, 0.0])
            
            # Build feature vector (69 features to match model expectation)
            feature_vector = np.array(selected_features, dtype=np.float32).reshape(1, -1)
            
            # Handle inf/nan BEFORE scaling
            feature_vector = np.nan_to_num(feature_vector, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Get predictions from all models
            all_predictions = {}
            predictions = []
            confidences = []
            
            for model_info in self.models:
                model_name = model_info['name']
                try:
                    pred = model_info['loader'].predict(feature_vector)[0]
                    proba = model_info['loader'].predict_proba(feature_vector)[0]
                    conf = proba.max()
                    
                    predictions.append(pred)
                    confidences.append(conf)
                    all_predictions[model_name] = {
                        'pred': normalize_label(pred),
                        'conf': float(conf)
                    }
                except Exception as e:
                    logger.error(f"❌ Model {model_name} prediction failed: {type(e).__name__}: {e}")
                    all_predictions[model_name] = {'pred': 'ERROR', 'conf': 0.0}
                    continue
            
            if not predictions:
                logger.error(f"❌ All models failed! Feature vector shape: {feature_vector.shape}")
                return
            
            # Voting: majority wins
            vote_counts = Counter(predictions)
            final_prediction = vote_counts.most_common(1)[0][0]
            agreement = vote_counts[final_prediction] / len(predictions)
            
            # Average confidence of models that agreed with majority
            agreeing_confidences = [conf for pred, conf in zip(predictions, confidences) 
                                   if pred == final_prediction]
            avg_confidence = np.mean(agreeing_confidences) if agreeing_confidences else 0.0
            inference_time_ms = (time.perf_counter() - inference_start) * 1000
            
            # Update confidence category
            if agreement >= 0.80:
                self.stats['high_confidence'] += 1
            elif agreement >= 0.60:
                self.stats['medium_confidence'] += 1
            else:
                self.stats['low_confidence'] += 1
            
            # Count predictions
            final_label = normalize_label(final_prediction)
            if final_label.upper() == "BENIGN":
                self.stats['benign'] += 1
            elif final_label.upper() == "ATTACK":
                self.stats['attacks'] += 1
            else:
                # Treat any other non-benign class as attack for stats
                self.stats['attacks'] += 1
            
            # Check accuracy (if ground truth available)
            correct = None
            if ground_truth is not None:
                gt_label = normalize_label(ground_truth)
                correct = (final_label.lower() == gt_label.lower())
                if correct:
                    self.stats['correct'] += 1
                else:
                    self.stats['incorrect'] += 1
            
            # Log prediction
            log_msg = f"[{self.stats['total']:6d}] {final_label:8s} (conf: {avg_confidence:.2%}, agree: {agreement:.0%})"
            if ground_truth is not None:
                gt_label = normalize_label(ground_truth)
                accuracy_marker = "✓" if correct else "✗"
                log_msg += f" | GT: {gt_label:8s} {accuracy_marker}"
            logger.info(log_msg)
            
            # Write to CSV
            if self.csv_writer:
                try:
                    csv_row = {
                        'timestamp': datetime.now().isoformat(),
                        'flow_id': flow_id,
                        'ground_truth': normalize_label(ground_truth) if ground_truth is not None else '',
                        'ensemble_prediction': final_label,
                        'ensemble_confidence': f"{avg_confidence:.4f}",
                        'agreement_ratio': f"{agreement:.4f}",
                        'correct': str(correct) if correct is not None else '',
                    }
                    
                    # Add per-model predictions
                    for i, model_info in enumerate(self.models):
                        model_name = model_info['name']
                        prefix = f"model_{model_name[:3].lower()}"
                        if model_name in all_predictions:
                            csv_row[f"{prefix}_pred"] = all_predictions[model_name]['pred']
                            csv_row[f"{prefix}_conf"] = f"{all_predictions[model_name]['conf']:.4f}"
                    
                    self.csv_writer.writerow(csv_row)
                    self.csv_file.flush()
                except Exception as e:
                    logger.error(f"❌ CSV write failed: {e}")

            # Log structured metrics for dashboard
            self.metrics_logger.log_ml_inference(
                model_name='realtime_ensemble',
                inference_time_ms=inference_time_ms,
                prediction=final_label,
                confidence=avg_confidence,
                features_count=feature_vector.shape[1],
                batch_size=1
            )
            self.metrics_logger.log_throughput(component='ml_consumer', events_count=1)
        
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Ensemble ML Consumer with CSV logging')
    parser.add_argument('--csv-output', type=str, default=None,
                       help='Output CSV file for predictions (default: disabled)')
    parser.add_argument('--kafka-bootstrap', type=str, default=KAFKA_BOOTSTRAP,
                       help='Kafka bootstrap servers (default: localhost:9092)')
    parser.add_argument('--kafka-topic', type=str, default=KAFKA_TOPIC,
                       help='Kafka topic to consume from (default: ml-features)')
    
    args = parser.parse_args()
    
    # Create output dir if needed
    if args.csv_output:
        output_dir = Path(args.csv_output).parent
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Start consumer
    consumer = EnsembleMLConsumerWithCSV(
        kafka_bootstrap=args.kafka_bootstrap,
        kafka_topic=args.kafka_topic,
        model_paths=ENSEMBLE_MODELS,
        csv_output=args.csv_output
    )
    
    try:
        consumer.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
