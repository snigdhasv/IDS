#!/usr/bin/env python3
"""
ML Consumer for Real-time Feature Engine

Consumes accurate CICIDS features from the sidecar feature engine
and performs ML inference with high confidence.
"""

import json
import logging
import sys
import signal
from typing import Dict
from pathlib import Path
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import numpy as np

# Import ML model loader and feature selector
sys.path.insert(0, str(Path(__file__).parent))
from model_loader import MLModelLoader
from feature_selector import select_features

# Configuration
KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "ml-features"
KAFKA_GROUP = "ml-inference-realtime"
# Use the well-trained 34-feature PCA model
MODEL_PATH = "/home/ifscr/SE_02_2025/IDS/ML Models/random_forest_model_2017.joblib"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RealtimeMLConsumer:
    """ML Consumer for accurate CICIDS features"""
    
    def __init__(self, kafka_bootstrap: str, kafka_topic: str, model_path: str):
        self.kafka_bootstrap = kafka_bootstrap
        self.kafka_topic = kafka_topic
        self.model_path = model_path
        self.running = True
        self.stats = {'total': 0, 'benign': 0, 'attacks': 0}
        
        # Load ML model
        self.model_loader = MLModelLoader()
        if not self.model_loader.load_model(model_path):
            logger.error("Failed to load ML model")
            sys.exit(1)
        
        logger.info(f"✓ Model loaded: {model_path}")
        
        # Create Kafka consumer
        try:
            self.consumer = KafkaConsumer(
                kafka_topic,
                bootstrap_servers=kafka_bootstrap,
                group_id=KAFKA_GROUP,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            logger.info(f"✓ Connected to Kafka: {kafka_topic}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            sys.exit(1)
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown"""
        logger.info(f"Shutting down... (signal {signum})")
        self.running = False
    
    def start(self):
        """Start consuming and predicting"""
        logger.info("🚀 Starting Real-time ML Consumer")
        logger.info(f"   Consuming from: {self.kafka_topic}")
        logger.info(f"   Model: {Path(self.model_path).name}")
        logger.info("")
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                self._process_message(message.value)
                
                # Print stats periodically
                if self.stats['total'] % 100 == 0:
                    logger.info(f"📊 Processed: {self.stats['total']} | "
                               f"Benign: {self.stats['benign']} | "
                               f"Attacks: {self.stats['attacks']}")
        
        except KeyboardInterrupt:
            pass
        finally:
            self.consumer.close()
            logger.info(f"✅ Consumer stopped. Final stats: {self.stats}")
    
    def _process_message(self, data: Dict):
        """Process feature vector and make prediction"""
        try:
            self.stats['total'] += 1
            
            # Extract features dictionary (65 features from engine)
            features_dict = data['features']
            
            # Select the 34 most important features for PCA model
            selected_features = select_features(features_dict)
            
            # Build feature vector (34 features)
            feature_vector = np.array(selected_features, dtype=np.float32).reshape(1, -1)
            
            # Handle inf/nan
            feature_vector = np.nan_to_num(feature_vector, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Predict
            predictions = self.model_loader.predict(feature_vector)
            probabilities = self.model_loader.predict_proba(feature_vector)
            
            prediction = predictions[0]
            confidence = probabilities[0].max()  # Highest probability
            
            # Update stats
            if prediction == 'BENIGN':
                self.stats['benign'] += 1
            else:
                self.stats['attacks'] += 1
            
            # Log prediction
            flow_id = data.get('flow_id', 'unknown')
            
            if prediction != 'BENIGN':
                logger.info(f"🚨 {prediction} (confidence: {confidence:.2%}) - {flow_id}")
            else:
                # Log first 10 BENIGN predictions, then only attacks
                if self.stats['total'] <= 10:
                    logger.info(f"✓ BENIGN (confidence: {confidence:.2%}) - {flow_id}")
                else:
                    logger.debug(f"✓ BENIGN (confidence: {confidence:.2%}) - {flow_id}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Real-time ML Consumer for Accurate Features')
    parser.add_argument('--kafka', default=KAFKA_BOOTSTRAP, help='Kafka bootstrap servers')
    parser.add_argument('--topic', default=KAFKA_TOPIC, help='Kafka topic')
    parser.add_argument('--model', default=MODEL_PATH, help='ML model path')
    
    args = parser.parse_args()
    
    consumer = RealtimeMLConsumer(args.kafka, args.topic, args.model)
    consumer.start()


if __name__ == '__main__':
    main()
