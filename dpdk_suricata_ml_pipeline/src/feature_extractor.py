#!/usr/bin/env python3
"""
CICIDS2017 Feature Extraction Module

Extracts 65 network flow features from Suricata events that are compatible
with the CICIDS2017 dataset format for ML model inference.

Features extracted include:
- Flow duration and packet counts
- Packet length statistics (min, max, mean, std)
- Inter-arrival time (IAT) statistics
- TCP flag counts
- Header lengths
- Packet rates and byte rates
- Activity and idle time estimates
"""

import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CICIDS2017FeatureExtractor:
    """
    Extracts CICIDS2017-compatible features from Suricata flow events.
    
    This class implements feature extraction that matches the 65-feature
    CICIDS2017 dataset format, allowing trained ML models to make predictions
    on live network traffic captured by Suricata.
    """
    
    # Feature names in exact order expected by CICIDS2017-trained models
    FEATURE_NAMES = [
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
    
    def __init__(self):
        """Initialize the feature extractor."""
        self.feature_count = len(self.FEATURE_NAMES)
        logger.info(f"Initialized CICIDS2017 feature extractor with {self.feature_count} features")
    
    def extract_from_flow(self, event: Dict) -> Optional[Dict[str, float]]:
        """
        Extract CICIDS2017 features from a Suricata flow event.
        
        Args:
            event: Suricata event dictionary (must have event_type='flow')
            
        Returns:
            Dictionary mapping feature names to values, or None if extraction fails
        """
        try:
            if event.get('event_type') != 'flow':
                logger.debug(f"Skipping non-flow event: {event.get('event_type')}")
                return None
            
            # Initialize all features to 0.0
            features = {name: 0.0 for name in self.FEATURE_NAMES}
            
            # Extract flow data from Suricata event
            flow_data = event.get('flow', {})
            
            # Basic flow statistics
            fwd_pkts = flow_data.get('pkts_toserver', 1)
            bwd_pkts = flow_data.get('pkts_toclient', 0)
            fwd_bytes = flow_data.get('bytes_toserver', 64)
            bwd_bytes = flow_data.get('bytes_toclient', 0)
            
            # Parse duration (format can be like "0.123456" or already a number)
            duration = self._parse_duration(flow_data.get('age', 0))
            if duration == 0:
                duration = 0.001  # Avoid division by zero
            
            # === BASIC FEATURES ===
            features['Destination Port'] = event.get('dest_port', 0)
            features['Flow Duration'] = int(duration * 1000000)  # Convert to microseconds
            features['Total Fwd Packets'] = fwd_pkts
            features['Total Backward Packets'] = bwd_pkts
            features['Total Length of Fwd Packets'] = fwd_bytes
            features['Total Length of Bwd Packets'] = bwd_bytes
            
            # === PACKET LENGTH STATISTICS ===
            # Forward direction
            avg_fwd_len = fwd_bytes / max(fwd_pkts, 1)
            features['Fwd Packet Length Mean'] = avg_fwd_len
            features['Fwd Packet Length Max'] = avg_fwd_len * 1.5  # Estimated
            features['Fwd Packet Length Min'] = avg_fwd_len * 0.5  # Estimated
            features['Fwd Packet Length Std'] = avg_fwd_len * 0.2  # Estimated
            
            # Backward direction
            if bwd_pkts > 0:
                avg_bwd_len = bwd_bytes / bwd_pkts
                features['Bwd Packet Length Mean'] = avg_bwd_len
                features['Bwd Packet Length Max'] = avg_bwd_len * 1.5
                features['Bwd Packet Length Min'] = avg_bwd_len * 0.5
                features['Bwd Packet Length Std'] = avg_bwd_len * 0.2
            
            # === FLOW RATE FEATURES ===
            duration_sec = max(duration, 0.001)
            features['Flow Bytes/s'] = (fwd_bytes + bwd_bytes) / duration_sec
            features['Flow Packets/s'] = (fwd_pkts + bwd_pkts) / duration_sec
            features['Fwd Packets/s'] = fwd_pkts / duration_sec
            features['Bwd Packets/s'] = bwd_pkts / duration_sec
            
            # === INTER-ARRIVAL TIME (IAT) FEATURES ===
            total_packets = fwd_pkts + bwd_pkts
            
            # Overall flow IAT
            if total_packets > 1:
                iat_mean = duration * 1000000 / (total_packets - 1)  # Microseconds
                features['Flow IAT Mean'] = iat_mean
                features['Flow IAT Std'] = iat_mean * 0.3  # Estimated
                features['Flow IAT Max'] = iat_mean * 3.0  # Estimated
                features['Flow IAT Min'] = iat_mean * 0.3  # Estimated
            
            # Forward IAT
            if fwd_pkts > 1:
                fwd_iat_mean = duration * 1000000 / (fwd_pkts - 1)
                features['Fwd IAT Total'] = duration * 1000000
                features['Fwd IAT Mean'] = fwd_iat_mean
                features['Fwd IAT Std'] = fwd_iat_mean * 0.3
                features['Fwd IAT Max'] = fwd_iat_mean * 3.0
                features['Fwd IAT Min'] = fwd_iat_mean * 0.3
            
            # Backward IAT
            if bwd_pkts > 1:
                bwd_iat_mean = duration * 1000000 / (bwd_pkts - 1)
                features['Bwd IAT Total'] = duration * 1000000
                features['Bwd IAT Mean'] = bwd_iat_mean
                features['Bwd IAT Std'] = bwd_iat_mean * 0.3
                features['Bwd IAT Max'] = bwd_iat_mean * 3.0
                features['Bwd IAT Min'] = bwd_iat_mean * 0.3
            
            # === TCP FLAG FEATURES ===
            proto = event.get('proto', 'UDP').upper()
            
            if proto == 'TCP':
                tcp_data = event.get('tcp', {})
                
                # Extract actual TCP flags if available
                features['FIN Flag Count'] = tcp_data.get('fin', False) * 1
                features['RST Flag Count'] = tcp_data.get('rst', False) * 1
                features['PSH Flag Count'] = tcp_data.get('psh', False) * 1
                features['ACK Flag Count'] = tcp_data.get('ack', False) * 1
                features['URG Flag Count'] = tcp_data.get('urg', False) * 1
                features['ECE Flag Count'] = tcp_data.get('ece', False) * 1
                
                # PSH and URG flags per direction (estimated)
                features['Fwd PSH Flags'] = features['PSH Flag Count']
                features['Fwd URG Flags'] = features['URG Flag Count']
                
                # TCP header size
                header_size = 20
            else:
                # UDP or other protocols - no flags
                features['FIN Flag Count'] = 0
                features['RST Flag Count'] = 0
                features['PSH Flag Count'] = 0
                features['ACK Flag Count'] = 0
                features['URG Flag Count'] = 0
                features['ECE Flag Count'] = 0
                features['Fwd PSH Flags'] = 0
                features['Fwd URG Flags'] = 0
                
                # UDP header size
                header_size = 8
            
            # === HEADER LENGTH FEATURES ===
            features['Fwd Header Length'] = header_size * fwd_pkts
            features['Bwd Header Length'] = header_size * bwd_pkts
            
            # === PACKET SIZE STATISTICS ===
            min_pkt_len = avg_fwd_len * 0.5
            max_pkt_len = max(avg_fwd_len * 1.5, avg_bwd_len * 1.5 if bwd_pkts > 0 else 0)
            
            avg_pkt_size = (fwd_bytes + bwd_bytes) / max(total_packets, 1)
            
            features['Min Packet Length'] = min_pkt_len
            features['Max Packet Length'] = max_pkt_len
            features['Packet Length Mean'] = avg_pkt_size
            features['Packet Length Std'] = avg_pkt_size * 0.2  # Estimated
            features['Packet Length Variance'] = (avg_pkt_size * 0.2) ** 2
            
            # === RATIO AND AVERAGE FEATURES ===
            features['Down/Up Ratio'] = bwd_bytes / max(fwd_bytes, 1)
            features['Average Packet Size'] = avg_pkt_size
            features['Avg Fwd Segment Size'] = avg_fwd_len
            features['Avg Bwd Segment Size'] = avg_bwd_len if bwd_pkts > 0 else 0
            
            # === SUBFLOW FEATURES ===
            # In single-flow analysis, subflow = full flow
            features['Subflow Fwd Bytes'] = fwd_bytes
            features['Subflow Bwd Bytes'] = bwd_bytes
            
            # === TCP WINDOW FEATURES ===
            if proto == 'TCP':
                tcp_data = event.get('tcp', {})
                features['Init_Win_bytes_forward'] = tcp_data.get('syn_window', 65535)
                features['Init_Win_bytes_backward'] = tcp_data.get('syn_window', 65535)
            else:
                features['Init_Win_bytes_forward'] = 0
                features['Init_Win_bytes_backward'] = 0
            
            # === DATA PACKET FEATURES ===
            # Estimate active data packets (exclude handshake packets)
            features['act_data_pkt_fwd'] = max(0, fwd_pkts - 1)
            features['min_seg_size_forward'] = features['Fwd Packet Length Min']
            
            # === ACTIVE/IDLE TIME FEATURES ===
            # These are estimates based on flow duration
            # Assume 70% active, 30% idle
            active_time = duration * 1000000 * 0.7
            idle_time = duration * 1000000 * 0.3
            
            features['Active Mean'] = active_time / 2 if active_time > 0 else 0
            features['Active Std'] = active_time * 0.1 if active_time > 0 else 0
            features['Active Max'] = active_time
            features['Active Min'] = 0
            
            features['Idle Mean'] = idle_time / 2 if idle_time > 0 else 0
            features['Idle Std'] = idle_time * 0.1 if idle_time > 0 else 0
            features['Idle Max'] = idle_time
            features['Idle Min'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features from flow event: {e}", exc_info=True)
            return None
    
    def extract_from_alert(self, event: Dict) -> Optional[Dict[str, float]]:
        """
        Extract features from a Suricata alert event.
        
        Alert events may have less detailed flow information, but we can
        still extract basic features.
        
        Args:
            event: Suricata event dictionary (must have event_type='alert')
            
        Returns:
            Dictionary mapping feature names to values, or None if extraction fails
        """
        try:
            if event.get('event_type') != 'alert':
                return None
            
            # Initialize all features to 0.0
            features = {name: 0.0 for name in self.FEATURE_NAMES}
            
            # Extract basic information
            flow_data = event.get('flow', {})
            
            fwd_pkts = flow_data.get('pkts_toserver', 1)
            bwd_pkts = flow_data.get('pkts_toclient', 0)
            fwd_bytes = flow_data.get('bytes_toserver', 64)
            bwd_bytes = flow_data.get('bytes_toclient', 0)
            
            # Basic features
            features['Destination Port'] = event.get('dest_port', 0)
            features['Total Fwd Packets'] = fwd_pkts
            features['Total Backward Packets'] = bwd_pkts
            features['Total Length of Fwd Packets'] = fwd_bytes
            features['Total Length of Bwd Packets'] = bwd_bytes
            
            # Packet size averages
            avg_fwd_len = fwd_bytes / max(fwd_pkts, 1)
            avg_bwd_len = bwd_bytes / max(bwd_pkts, 1) if bwd_pkts > 0 else 0
            
            features['Fwd Packet Length Mean'] = avg_fwd_len
            features['Bwd Packet Length Mean'] = avg_bwd_len
            features['Packet Length Mean'] = (fwd_bytes + bwd_bytes) / max(fwd_pkts + bwd_pkts, 1)
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features from alert event: {e}", exc_info=True)
            return None
    
    def _parse_duration(self, duration) -> float:
        """
        Parse duration from various formats.
        
        Args:
            duration: Duration as float, int, or string
            
        Returns:
            Duration in seconds as float
        """
        try:
            if isinstance(duration, (int, float)):
                return float(duration)
            elif isinstance(duration, str):
                return float(duration)
            else:
                logger.warning(f"Unknown duration format: {type(duration)}")
                return 0.001
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse duration: {duration}")
            return 0.001
    
    def get_feature_vector(self, features: Dict[str, float]) -> list:
        """
        Convert feature dictionary to ordered list for ML model input.
        
        Args:
            features: Dictionary of feature name -> value
            
        Returns:
            List of feature values in correct order for ML model
        """
        return [features.get(name, 0.0) for name in self.FEATURE_NAMES]
    
    def get_feature_names(self) -> list:
        """
        Get the list of feature names in order.
        
        Returns:
            List of 65 CICIDS2017 feature names
        """
        return self.FEATURE_NAMES.copy()


if __name__ == "__main__":
    # Quick test with sample Suricata flow event
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    sample_flow_event = {
        "timestamp": "2024-01-15T10:30:45.123456+0000",
        "event_type": "flow",
        "src_ip": "192.168.1.100",
        "src_port": 54321,
        "dest_ip": "8.8.8.8",
        "dest_port": 53,
        "proto": "UDP",
        "flow": {
            "pkts_toserver": 10,
            "pkts_toclient": 10,
            "bytes_toserver": 640,
            "bytes_toclient": 1280,
            "age": 2.5
        }
    }
    
    extractor = CICIDS2017FeatureExtractor()
    features = extractor.extract_from_flow(sample_flow_event)
    
    if features:
        print(f"\n✓ Extracted {len(features)} features:")
        print(json.dumps({k: round(v, 2) for k, v in list(features.items())[:10]}, indent=2))
        print("...")
        
        feature_vector = extractor.get_feature_vector(features)
        print(f"\n✓ Feature vector length: {len(feature_vector)}")
    else:
        print("✗ Feature extraction failed")
