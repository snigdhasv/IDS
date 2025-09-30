#!/usr/bin/env python3
"""
ML-Enhanced IDS Pipeline Integration

This script integrates your trained Random Forest model with the existing 
DPDK-Suricata-Kafka pipeline to provide:
1. Rule-based detection (Suricata alerts)
2. ML-based anomaly detection (Random Forest predictions)  
3. Feature extraction from network events
4. Real-time ML inference on streaming data
5. Combined threat scoring and alert prioritization

Architecture:
DPDK Packets → Suricata → EVE Events → Feature Extraction → ML Inference → Enhanced Alerts → Kafka
"""

import os
import sys
import json
import time
import numpy as np
import pandas as pd
import threading
from datetime import datetime
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
import signal

try:
    import joblib
    from kafka import KafkaConsumer, KafkaProducer
    from sklearn.preprocessing import StandardScaler
    import psutil
except ImportError as e:
    print(f"Missing required libraries: {e}")
    print("Install with: pip install joblib kafka-python scikit-learn psutil")
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

class MLEnhancedIDSPipeline:
    """ML-Enhanced Intrusion Detection System Pipeline"""
    
    def __init__(self):
        self.kafka_broker = "localhost:9092"
        self.input_topics = ["suricata-events", "suricata-alerts", "suricata-stats"]
        self.output_topic = "ml-enhanced-alerts"
        
        # ML Model configuration
        self.model_path = "/home/ifscr/SE_02_2025/IDS/src/ML_Model/intrusion_detection_model.joblib"
        self.model = None
        self.scaler = StandardScaler()
        
        # Feature extraction
        self.feature_window = deque(maxlen=100)  # Rolling window for features
        self.flow_features = {}
        
        # Statistics
        self.stats = {
            'events_processed': 0,
            'ml_predictions': 0,
            'suricata_alerts': 0,
            'ml_alerts': 0,
            'combined_alerts': 0,
            'start_time': None
        }
        
        # Attack type mapping (from your model)
        # Note: The actual model uses string labels, not numeric
        self.attack_mapping = {
            'BENIGN': 'BENIGN',
            'DoS': 'DoS', 
            'DDoS': 'DDoS',
            'RECONNAISSANCE': 'RECONNAISSANCE',
            'BRUTE_FORCE': 'BRUTE_FORCE',
            'BOTNET': 'BOTNET',
            'WEB_ATTACK': 'WEB_ATTACK'
        }
        
        # The model returns string predictions directly
        self.reverse_mapping = self.attack_mapping
        
        # Feature names expected by the CICIDS2017 trained model (65 features)
        # These must match EXACTLY what the model was trained with
        self.feature_names = [
            'Destination Port', 'Flow Duration', 'Total Fwd Packets', 'Total Backward Packets',
            'Total Length of Fwd Packets', 'Total Length of Bwd Packets', 'Fwd Packet Length Max',
            'Fwd Packet Length Min', 'Fwd Packet Length Mean', 'Fwd Packet Length Std',
            'Bwd Packet Length Max', 'Bwd Packet Length Min', 'Bwd Packet Length Mean',
            'Bwd Packet Length Std', 'Flow Bytes/s', 'Flow Packets/s', 'Flow IAT Mean',
            'Flow IAT Std', 'Flow IAT Max', 'Flow IAT Min', 'Fwd IAT Total', 'Fwd IAT Mean',
            'Fwd IAT Std', 'Fwd IAT Max', 'Fwd IAT Min', 'Bwd IAT Total', 'Bwd IAT Mean',
            'Bwd IAT Std', 'Bwd IAT Max', 'Bwd IAT Min', 'Fwd PSH Flags',
            'Fwd URG Flags', 'Fwd Header Length', 'Bwd Header Length',
            'Fwd Packets/s', 'Bwd Packets/s', 'Min Packet Length', 'Max Packet Length',
            'Packet Length Mean', 'Packet Length Std', 'Packet Length Variance',
            'FIN Flag Count', 'RST Flag Count', 'PSH Flag Count',
            'ACK Flag Count', 'URG Flag Count', 'ECE Flag Count',
            'Down/Up Ratio', 'Average Packet Size', 'Avg Fwd Segment Size',
            'Avg Bwd Segment Size', 'Subflow Fwd Bytes',
            'Subflow Bwd Bytes', 'Init_Win_bytes_forward',
            'Init_Win_bytes_backward', 'act_data_pkt_fwd', 'min_seg_size_forward',
            'Active Mean', 'Active Std', 'Active Max', 'Active Min', 
            'Idle Mean', 'Idle Std', 'Idle Max', 'Idle Min'
        ]
        
        self.running = False
        
    def load_ml_model(self) -> bool:
        """Load the trained Random Forest model"""
        try:
            if not os.path.exists(self.model_path):
                print(f"{Colors.RED}❌ ML model not found at {self.model_path}{Colors.END}")
                return False
                
            print(f"{Colors.YELLOW}🧠 Loading ML model...{Colors.END}")
            self.model = joblib.load(self.model_path)
            print(f"{Colors.GREEN}✓ ML model loaded successfully{Colors.END}")
            print(f"  Model type: {type(self.model).__name__}")
            print(f"  Features expected: {self.model.n_features_in_}")
            return True
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error loading ML model: {e}{Colors.END}")
            return False
    
    def extract_features_from_event(self, event: Dict) -> Optional[Dict]:
        """Extract CICIDS2017-style features from Suricata events for ML prediction"""
        try:
            # Initialize features dict with all CICIDS2017 feature names set to 0
            features = {name: 0.0 for name in self.feature_names}
            
            # Extract flow data
            flow_data = event.get('flow', {})
            fwd_pkts = flow_data.get('pkts_toserver', 1)
            bwd_pkts = flow_data.get('pkts_toclient', 0)
            fwd_bytes = flow_data.get('bytes_toserver', 64)
            bwd_bytes = flow_data.get('bytes_toclient', 0)
            duration = self._parse_duration(flow_data.get('duration', '0.1'))
            
            # Basic features
            features['Destination Port'] = event.get('dest_port', 53)
            features['Flow Duration'] = int(duration * 1000000)  # Microseconds
            features['Total Fwd Packets'] = fwd_pkts
            features['Total Backward Packets'] = bwd_pkts
            features['Total Length of Fwd Packets'] = fwd_bytes
            features['Total Length of Bwd Packets'] = bwd_bytes
            
            # Packet length statistics
            avg_fwd_len = fwd_bytes / max(fwd_pkts, 1)
            avg_bwd_len = bwd_bytes / max(bwd_pkts, 1) if bwd_pkts > 0 else 0
            
            features['Fwd Packet Length Max'] = avg_fwd_len * 1.5
            features['Fwd Packet Length Min'] = avg_fwd_len * 0.5
            features['Fwd Packet Length Mean'] = avg_fwd_len
            features['Fwd Packet Length Std'] = avg_fwd_len * 0.2
            
            features['Bwd Packet Length Max'] = avg_bwd_len * 1.5
            features['Bwd Packet Length Min'] = avg_bwd_len * 0.5
            features['Bwd Packet Length Mean'] = avg_bwd_len
            features['Bwd Packet Length Std'] = avg_bwd_len * 0.2
            
            # Flow rate features
            duration_sec = max(duration, 0.001)
            features['Flow Bytes/s'] = (fwd_bytes + bwd_bytes) / duration_sec
            features['Flow Packets/s'] = (fwd_pkts + bwd_pkts) / duration_sec
            
            # Inter-arrival time features
            total_packets = fwd_pkts + bwd_pkts
            if total_packets > 1:
                iat_mean = duration * 1000000 / total_packets
                features['Flow IAT Mean'] = iat_mean
                features['Flow IAT Std'] = iat_mean * 0.3
                features['Flow IAT Max'] = iat_mean * 3
                features['Flow IAT Min'] = iat_mean * 0.3
            
            if fwd_pkts > 1:
                fwd_iat = duration * 1000000 / fwd_pkts
                features['Fwd IAT Total'] = duration * 1000000
                features['Fwd IAT Mean'] = fwd_iat
                features['Fwd IAT Std'] = fwd_iat * 0.3
                features['Fwd IAT Max'] = fwd_iat * 3
                features['Fwd IAT Min'] = fwd_iat * 0.3
            
            if bwd_pkts > 1:
                bwd_iat = duration * 1000000 / bwd_pkts
                features['Bwd IAT Total'] = duration * 1000000
                features['Bwd IAT Mean'] = bwd_iat
                features['Bwd IAT Std'] = bwd_iat * 0.3
                features['Bwd IAT Max'] = bwd_iat * 3
                features['Bwd IAT Min'] = bwd_iat * 0.3
            
            # Protocol-based flags
            proto = event.get('proto', 'UDP').upper()
            if proto == 'TCP':
                features['Fwd PSH Flags'] = max(0, fwd_pkts - 1)
                features['Fwd URG Flags'] = 0
                features['FIN Flag Count'] = 1
                features['RST Flag Count'] = 0
                features['PSH Flag Count'] = max(0, fwd_pkts - 1)
                features['ACK Flag Count'] = max(1, total_packets - 1)
                features['URG Flag Count'] = 0
                features['ECE Flag Count'] = 0
            
            # Header lengths
            header_size = 20 if proto == 'TCP' else 8
            features['Fwd Header Length'] = header_size * fwd_pkts
            features['Bwd Header Length'] = header_size * bwd_pkts
            
            # Packet rates
            features['Fwd Packets/s'] = fwd_pkts / duration_sec
            features['Bwd Packets/s'] = bwd_pkts / duration_sec
            
            # Packet size statistics
            features['Min Packet Length'] = min(avg_fwd_len, avg_bwd_len) if avg_bwd_len > 0 else avg_fwd_len
            features['Max Packet Length'] = max(avg_fwd_len, avg_bwd_len)
            features['Packet Length Mean'] = (fwd_bytes + bwd_bytes) / max(total_packets, 1)
            features['Packet Length Std'] = features['Packet Length Mean'] * 0.2
            features['Packet Length Variance'] = features['Packet Length Std'] ** 2
            
            # Additional derived features
            features['Down/Up Ratio'] = bwd_bytes / max(fwd_bytes, 1)
            features['Average Packet Size'] = features['Packet Length Mean']
            features['Avg Fwd Segment Size'] = avg_fwd_len
            features['Avg Bwd Segment Size'] = avg_bwd_len
            
            # Subflow features
            features['Subflow Fwd Bytes'] = fwd_bytes
            features['Subflow Bwd Bytes'] = bwd_bytes
            
            # Window and data features
            features['Init_Win_bytes_forward'] = 65535
            features['Init_Win_bytes_backward'] = 65535
            features['act_data_pkt_fwd'] = max(0, fwd_pkts - 1)
            features['min_seg_size_forward'] = features['Fwd Packet Length Min']
            
            # Activity timing features
            features['Active Mean'] = duration * 1000000 / 2
            features['Active Std'] = features['Active Mean'] * 0.1
            features['Active Max'] = duration * 1000000
            features['Active Min'] = 0
            features['Idle Mean'] = duration * 1000000 / 10
            features['Idle Std'] = features['Idle Mean'] * 0.1
            features['Idle Max'] = duration * 1000000 / 5
            features['Idle Min'] = 0
            
            return features
            
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Feature extraction error: {e}{Colors.END}")
            return None
    
    def _parse_duration(self, duration_str: str) -> float:
        """Parse duration string to seconds"""
        try:
            if isinstance(duration_str, (int, float)):
                return float(duration_str)
            return float(duration_str.replace('s', ''))
        except:
            return 0.0
    
    def _encode_http_method(self, method: str) -> int:
        """Encode HTTP method to numerical value"""
        method_map = {'GET': 1, 'POST': 2, 'PUT': 3, 'DELETE': 4, 'HEAD': 5, 'OPTIONS': 6}
        return method_map.get(method.upper(), 0)
    
    def _count_suspicious_chars(self, text: str) -> int:
        """Count suspicious characters in text"""
        suspicious = ['<', '>', '"', "'", '&', '%', ';', '(', ')', '{', '}', '|']
        return sum(text.count(char) for char in suspicious)
    
    def _add_statistical_features(self, features: Dict, event: Dict):
        """Add statistical features from recent events"""
        src_ip = event.get('src_ip', '')
        dest_ip = event.get('dest_ip', '')
        
        # Count recent connections from same source
        recent_events = list(self.feature_window)
        features['src_ip_frequency'] = sum(1 for e in recent_events if e.get('src_ip') == src_ip)
        features['dest_ip_frequency'] = sum(1 for e in recent_events if e.get('dest_ip') == dest_ip)
        
        # Port scan detection
        unique_dest_ports = len(set(e.get('dest_port', 0) for e in recent_events if e.get('src_ip') == src_ip))
        features['port_scan_indicator'] = min(unique_dest_ports, 100)  # Cap at 100
        
        # Connection rate features
        features['connection_rate'] = len(recent_events)  # Events in window
        
    def _get_expected_feature_names(self) -> List[str]:
        """Get list of expected feature names for the model"""
        # Use the same feature names as defined in __init__ (65 CICIDS2017 features)
        return self.feature_names
    
    def predict_attack_type(self, features: Dict) -> Tuple[str, float]:
        """Predict attack type using ML model"""
        try:
            if self.model is None:
                return "UNKNOWN", 0.0
            
            # Convert features to DataFrame
            feature_names = self._get_expected_feature_names()
            feature_values = [features.get(name, 0.0) for name in feature_names]
            
            # Ensure we have the right number of features
            while len(feature_values) < self.model.n_features_in_:
                feature_values.append(0.0)
            feature_values = feature_values[:self.model.n_features_in_]
            
            # Make prediction using DataFrame with proper feature names to avoid warnings
            import pandas as pd
            feature_df = pd.DataFrame([feature_values], columns=self.feature_names[:len(feature_values)])
            prediction = self.model.predict(feature_df)[0]
            probabilities = self.model.predict_proba(feature_df)[0]
            
            # Get attack type and confidence (model returns string labels directly)
            attack_type = prediction
            confidence = np.max(probabilities)
            
            return attack_type, confidence
            
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ ML prediction error: {e}{Colors.END}")
            return "ERROR", 0.0
    
    def create_enhanced_alert(self, event: Dict, ml_prediction: str, ml_confidence: float) -> Dict:
        """Create enhanced alert combining Suricata and ML predictions"""
        enhanced_alert = {
            'timestamp': datetime.now().isoformat(),
            'event_id': event.get('flow_id', int(time.time())),
            'src_ip': event.get('src_ip', 'unknown'),
            'dest_ip': event.get('dest_ip', 'unknown'),
            'src_port': event.get('src_port', 0),
            'dest_port': event.get('dest_port', 0),
            'proto': event.get('proto', 'unknown'),
            
            # Original Suricata detection
            'suricata_detection': {
                'event_type': event.get('event_type', 'unknown'),
                'alert': event.get('alert', {}),
                'rule_triggered': event.get('event_type') == 'alert'
            },
            
            # ML-based detection
            'ml_detection': {
                'predicted_attack': ml_prediction,
                'confidence': ml_confidence,
                'is_malicious': ml_prediction != 'BENIGN',
                'threat_level': self._calculate_threat_level(ml_prediction, ml_confidence)
            },
            
            # Combined assessment
            'combined_assessment': self._create_combined_assessment(event, ml_prediction, ml_confidence),
            
            # Original event data
            'original_event': event
        }
        
        return enhanced_alert
    
    def _calculate_threat_level(self, prediction: str, confidence: float) -> str:
        """Calculate threat level based on prediction and confidence"""
        if prediction == 'BENIGN':
            return 'LOW'
        elif confidence > 0.9:
            return 'CRITICAL'
        elif confidence > 0.7:
            return 'HIGH'
        elif confidence > 0.5:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _create_combined_assessment(self, event: Dict, ml_prediction: str, ml_confidence: float) -> Dict:
        """Create combined assessment from Suricata rules and ML prediction"""
        suricata_alert = event.get('event_type') == 'alert'
        ml_alert = ml_prediction != 'BENIGN' and ml_confidence > 0.5
        
        if suricata_alert and ml_alert:
            threat_level = 'CRITICAL'
            description = f"Both Suricata rules and ML model detect threat ({ml_prediction})"
        elif suricata_alert:
            threat_level = 'HIGH'
            description = f"Suricata rule triggered: {event.get('alert', {}).get('signature', 'Unknown')}"
        elif ml_alert:
            threat_level = 'MEDIUM'
            description = f"ML model predicts {ml_prediction} (confidence: {ml_confidence:.2f})"
        else:
            threat_level = 'LOW'
            description = "No threats detected"
        
        return {
            'threat_level': threat_level,
            'description': description,
            'requires_attention': threat_level in ['CRITICAL', 'HIGH'],
            'combined_score': self._calculate_combined_score(suricata_alert, ml_alert, ml_confidence)
        }
    
    def _calculate_combined_score(self, suricata_alert: bool, ml_alert: bool, ml_confidence: float) -> float:
        """Calculate combined threat score (0-100)"""
        score = 0.0
        
        if suricata_alert:
            score += 50.0  # Suricata rule match
        
        if ml_alert:
            score += ml_confidence * 50.0  # ML prediction weighted by confidence
        
        return min(score, 100.0)
    
    def process_event_stream(self):
        """Process streaming events with ML enhancement"""
        print(f"{Colors.BLUE}🧠 Starting ML-Enhanced Event Processing...{Colors.END}")
        
        consumer = None
        producer = None
        
        try:
            # Initialize Kafka consumer and producer
            consumer = KafkaConsumer(
                *self.input_topics,
                bootstrap_servers=[self.kafka_broker],
                auto_offset_reset='latest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            
            producer = KafkaProducer(
                bootstrap_servers=[self.kafka_broker],
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            
            print(f"{Colors.GREEN}✓ Connected to Kafka topics{Colors.END}")
            print(f"  Input topics: {', '.join(self.input_topics)}")
            print(f"  Output topic: {self.output_topic}")
            
            while self.running:
                message_batch = consumer.poll(timeout_ms=1000)
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        if not self.running:
                            break
                        
                        event = message.value
                        self.stats['events_processed'] += 1
                        
                        # Add to feature window
                        self.feature_window.append(event)
                        
                        # Extract features for ML
                        features = self.extract_features_from_event(event)
                        if features:
                            # Make ML prediction
                            ml_prediction, ml_confidence = self.predict_attack_type(features)
                            self.stats['ml_predictions'] += 1
                            
                            # Count alerts
                            if event.get('event_type') == 'alert':
                                self.stats['suricata_alerts'] += 1
                            
                            if ml_prediction != 'BENIGN' and ml_confidence > 0.5:
                                self.stats['ml_alerts'] += 1
                            
                            # Create enhanced alert
                            enhanced_alert = self.create_enhanced_alert(event, ml_prediction, ml_confidence)
                            
                            # Send to output topic if significant
                            if enhanced_alert['combined_assessment']['requires_attention']:
                                producer.send(self.output_topic, enhanced_alert)
                                self.stats['combined_alerts'] += 1
                                
                                # Print significant alerts
                                threat_level = enhanced_alert['combined_assessment']['threat_level']
                                if threat_level in ['CRITICAL', 'HIGH']:
                                    src_ip = enhanced_alert['src_ip']
                                    dest_ip = enhanced_alert['dest_ip']
                                    description = enhanced_alert['combined_assessment']['description']
                                    score = enhanced_alert['combined_assessment']['combined_score']
                                    
                                    color = Colors.RED if threat_level == 'CRITICAL' else Colors.YELLOW
                                    print(f"{color}🚨 {threat_level} ALERT: {src_ip} → {dest_ip}{Colors.END}")
                                    print(f"  {description}")
                                    print(f"  Threat Score: {score:.1f}/100")
                        
                        # Periodic stats
                        if self.stats['events_processed'] % 100 == 0:
                            self._print_processing_stats()
        
        except Exception as e:
            print(f"{Colors.RED}❌ Event processing error: {e}{Colors.END}")
        finally:
            if consumer:
                consumer.close()
            if producer:
                producer.close()
    
    def _print_processing_stats(self):
        """Print processing statistics"""
        elapsed = time.time() - self.stats['start_time']
        rate = self.stats['events_processed'] / elapsed if elapsed > 0 else 0
        
        print(f"{Colors.CYAN}📊 Processing Stats:{Colors.END}")
        print(f"  Events processed: {self.stats['events_processed']}")
        print(f"  ML predictions: {self.stats['ml_predictions']}")
        print(f"  Suricata alerts: {self.stats['suricata_alerts']}")
        print(f"  ML alerts: {self.stats['ml_alerts']}")
        print(f"  Combined alerts: {self.stats['combined_alerts']}")
        print(f"  Processing rate: {rate:.1f} events/second")
    
    def start_ml_pipeline(self):
        """Start the ML-enhanced IDS pipeline"""
        print(f"{Colors.BOLD}{Colors.BLUE}🧠 ML-Enhanced IDS Pipeline Starting...{Colors.END}")
        
        # Load ML model
        if not self.load_ml_model():
            print(f"{Colors.RED}❌ Cannot start without ML model{Colors.END}")
            return False
        
        self.running = True
        self.stats['start_time'] = time.time()
        
        try:
            self.process_event_stream()
        except KeyboardInterrupt:
            print(f"{Colors.YELLOW}\n⏹️ ML pipeline stopped by user{Colors.END}")
        finally:
            self.running = False
            self._print_final_stats()
        
        return True
    
    def _print_final_stats(self):
        """Print final processing statistics"""
        elapsed = time.time() - self.stats['start_time']
        
        print(f"\n{Colors.BOLD}📊 Final ML Pipeline Statistics:{Colors.END}")
        print(f"  Runtime: {elapsed:.1f} seconds")
        print(f"  Total events processed: {self.stats['events_processed']}")
        print(f"  ML predictions made: {self.stats['ml_predictions']}")
        print(f"  Suricata alerts: {self.stats['suricata_alerts']}")
        print(f"  ML-detected threats: {self.stats['ml_alerts']}")
        print(f"  Combined alerts generated: {self.stats['combined_alerts']}")
        
        if elapsed > 0:
            print(f"  Average processing rate: {self.stats['events_processed']/elapsed:.1f} events/second")
        
        # Detection effectiveness
        if self.stats['events_processed'] > 0:
            suricata_rate = (self.stats['suricata_alerts'] / self.stats['events_processed']) * 100
            ml_rate = (self.stats['ml_alerts'] / self.stats['events_processed']) * 100
            combined_rate = (self.stats['combined_alerts'] / self.stats['events_processed']) * 100
            
            print(f"  Suricata detection rate: {suricata_rate:.2f}%")
            print(f"  ML detection rate: {ml_rate:.2f}%")
            print(f"  Combined alert rate: {combined_rate:.2f}%")

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print(f"\n{Colors.YELLOW}🛑 Shutting down ML pipeline...{Colors.END}")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"{Colors.BOLD}🧠 ML-Enhanced IDS Pipeline{Colors.END}")
    print("Combining Suricata rule-based detection with Random Forest ML predictions")
    print()
    
    pipeline = MLEnhancedIDSPipeline()
    pipeline.start_ml_pipeline()

if __name__ == "__main__":
    main()