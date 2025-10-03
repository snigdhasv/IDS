#!/usr/bin/env python3
"""
Alert Processor Module

Combines Suricata rule-based alerts with ML predictions to create
enhanced threat alerts with combined scoring and prioritization.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat severity levels"""
    BENIGN = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AttackCategory(Enum):
    """Attack type categories"""
    BENIGN = "BENIGN"
    DOS = "DoS"
    DDOS = "DDoS"
    RECONNAISSANCE = "RECONNAISSANCE"
    BRUTE_FORCE = "BRUTE_FORCE"
    BOTNET = "BOTNET"
    WEB_ATTACK = "WEB_ATTACK"
    INFILTRATION = "INFILTRATION"
    UNKNOWN = "UNKNOWN"


class AlertProcessor:
    """
    Processes and enriches security alerts from multiple sources.
    
    Combines:
    - Suricata rule-based alerts (signature detection)
    - ML predictions (anomaly detection)
    - Flow metadata
    
    Outputs:
    - Enhanced alerts with combined threat scores
    - Prioritized alerts for incident response
    """
    
    def __init__(self):
        """Initialize the alert processor."""
        self.alert_count = 0
        self.ml_alert_count = 0
        self.combined_alert_count = 0
        
        # Threat scoring weights
        self.weights = {
            'suricata_alert': 0.6,  # Rule-based detection weight
            'ml_prediction': 0.4,   # ML anomaly detection weight
        }
        
        # Attack severity mapping
        self.attack_severity = {
            'BENIGN': ThreatLevel.BENIGN,
            'DoS': ThreatLevel.HIGH,
            'DDoS': ThreatLevel.CRITICAL,
            'RECONNAISSANCE': ThreatLevel.MEDIUM,
            'BRUTE_FORCE': ThreatLevel.HIGH,
            'BOTNET': ThreatLevel.CRITICAL,
            'WEB_ATTACK': ThreatLevel.HIGH,
            'INFILTRATION': ThreatLevel.CRITICAL,
        }
        
        logger.info("Alert processor initialized")
    
    def process_flow_with_ml(
        self,
        flow_event: Dict,
        ml_prediction: Optional[str] = None,
        ml_confidence: Optional[float] = None,
        suricata_alert: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Process a network flow with ML prediction and optional Suricata alert.
        
        Args:
            flow_event: Suricata flow event dictionary
            ml_prediction: ML model prediction (attack type or 'BENIGN')
            ml_confidence: ML prediction confidence (0-1)
            suricata_alert: Optional Suricata alert for this flow
        
        Returns:
            Enhanced alert dictionary, or None if no alert needed
        """
        try:
            # Determine if we should generate an alert
            has_suricata_alert = suricata_alert is not None
            has_ml_alert = (
                ml_prediction and 
                ml_prediction != 'BENIGN' and 
                ml_confidence and ml_confidence > 0.5
            )
            
            if not has_suricata_alert and not has_ml_alert:
                # No alert needed - benign flow
                return None
            
            # Build enhanced alert
            alert = {
                'timestamp': flow_event.get('timestamp', datetime.utcnow().isoformat()),
                'alert_id': self._generate_alert_id(),
                'event_type': 'enhanced_alert',
                
                # Flow information
                'flow': {
                    'src_ip': flow_event.get('src_ip'),
                    'src_port': flow_event.get('src_port'),
                    'dest_ip': flow_event.get('dest_ip'),
                    'dest_port': flow_event.get('dest_port'),
                    'proto': flow_event.get('proto'),
                },
                
                # Detection sources
                'detection': {
                    'suricata': has_suricata_alert,
                    'ml': has_ml_alert,
                    'method': self._get_detection_method(has_suricata_alert, has_ml_alert)
                },
            }
            
            # Add Suricata alert information
            if has_suricata_alert:
                self.alert_count += 1
                alert['suricata'] = {
                    'signature': suricata_alert.get('alert', {}).get('signature'),
                    'signature_id': suricata_alert.get('alert', {}).get('signature_id'),
                    'category': suricata_alert.get('alert', {}).get('category'),
                    'severity': suricata_alert.get('alert', {}).get('severity'),
                }
            
            # Add ML prediction information
            if has_ml_alert:
                self.ml_alert_count += 1
                alert['ml'] = {
                    'prediction': ml_prediction,
                    'confidence': round(ml_confidence, 4) if ml_confidence else None,
                    'attack_category': self._normalize_attack_category(ml_prediction),
                }
            
            # Calculate combined threat score and level
            threat_score = self._calculate_threat_score(
                has_suricata_alert,
                ml_prediction,
                ml_confidence,
                suricata_alert
            )
            
            threat_level = self._calculate_threat_level(
                threat_score,
                ml_prediction,
                suricata_alert
            )
            
            alert['threat'] = {
                'score': round(threat_score, 4),
                'level': threat_level.name,
                'severity': threat_level.value,
            }
            
            # Add flow statistics if available
            flow_data = flow_event.get('flow', {})
            if flow_data:
                alert['flow_stats'] = {
                    'pkts_toserver': flow_data.get('pkts_toserver'),
                    'pkts_toclient': flow_data.get('pkts_toclient'),
                    'bytes_toserver': flow_data.get('bytes_toserver'),
                    'bytes_toclient': flow_data.get('bytes_toclient'),
                    'age': flow_data.get('age'),
                }
            
            # Track combined alerts
            if has_suricata_alert and has_ml_alert:
                self.combined_alert_count += 1
            
            return alert
            
        except Exception as e:
            logger.error(f"Error processing flow alert: {e}", exc_info=True)
            return None
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID."""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        return f"alert_{timestamp}"
    
    def _get_detection_method(self, has_suricata: bool, has_ml: bool) -> str:
        """Determine detection method."""
        if has_suricata and has_ml:
            return "signature+ml"
        elif has_suricata:
            return "signature"
        elif has_ml:
            return "ml"
        else:
            return "unknown"
    
    def _normalize_attack_category(self, prediction: str) -> str:
        """Normalize ML prediction to standard attack category."""
        if not prediction:
            return AttackCategory.UNKNOWN.value
        
        prediction_upper = prediction.upper()
        
        # Try direct mapping
        for category in AttackCategory:
            if category.value.upper() == prediction_upper:
                return category.value
        
        # Fuzzy matching for common variations
        if 'DOS' in prediction_upper or 'DENIAL' in prediction_upper:
            return AttackCategory.DOS.value
        elif 'DDOS' in prediction_upper:
            return AttackCategory.DDOS.value
        elif 'SCAN' in prediction_upper or 'PROBE' in prediction_upper:
            return AttackCategory.RECONNAISSANCE.value
        elif 'BRUTE' in prediction_upper or 'FORCE' in prediction_upper:
            return AttackCategory.BRUTE_FORCE.value
        elif 'BOT' in prediction_upper:
            return AttackCategory.BOTNET.value
        elif 'WEB' in prediction_upper or 'XSS' in prediction_upper or 'SQL' in prediction_upper:
            return AttackCategory.WEB_ATTACK.value
        elif 'INFILTR' in prediction_upper:
            return AttackCategory.INFILTRATION.value
        else:
            return AttackCategory.UNKNOWN.value
    
    def _calculate_threat_score(
        self,
        has_suricata_alert: bool,
        ml_prediction: Optional[str],
        ml_confidence: Optional[float],
        suricata_alert: Optional[Dict]
    ) -> float:
        """
        Calculate combined threat score (0-1).
        
        Combines Suricata signature detection with ML anomaly detection.
        """
        score = 0.0
        
        # Suricata component
        if has_suricata_alert and suricata_alert:
            # Use Suricata severity (1=high, 2=medium, 3=low)
            suricata_severity = suricata_alert.get('alert', {}).get('severity', 3)
            suricata_score = 1.0 - (suricata_severity - 1) / 2  # Convert to 0-1
            score += suricata_score * self.weights['suricata_alert']
        
        # ML component
        if ml_prediction and ml_prediction != 'BENIGN' and ml_confidence:
            score += ml_confidence * self.weights['ml_prediction']
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _calculate_threat_level(
        self,
        threat_score: float,
        ml_prediction: Optional[str],
        suricata_alert: Optional[Dict]
    ) -> ThreatLevel:
        """
        Determine threat level based on score and context.
        """
        # Check for critical attack types
        if ml_prediction:
            attack_cat = self._normalize_attack_category(ml_prediction)
            if attack_cat in [AttackCategory.DDOS.value, AttackCategory.BOTNET.value, 
                             AttackCategory.INFILTRATION.value]:
                if threat_score > 0.7:
                    return ThreatLevel.CRITICAL
        
        # Suricata high-severity alerts
        if suricata_alert:
            suricata_severity = suricata_alert.get('alert', {}).get('severity', 3)
            if suricata_severity == 1 and threat_score > 0.6:
                return ThreatLevel.CRITICAL
        
        # Score-based levels
        if threat_score >= 0.8:
            return ThreatLevel.CRITICAL
        elif threat_score >= 0.6:
            return ThreatLevel.HIGH
        elif threat_score >= 0.4:
            return ThreatLevel.MEDIUM
        elif threat_score >= 0.2:
            return ThreatLevel.LOW
        else:
            return ThreatLevel.BENIGN
    
    def get_statistics(self) -> Dict:
        """
        Get alert processing statistics.
        
        Returns:
            Dictionary with alert counts and rates
        """
        return {
            'suricata_alerts': self.alert_count,
            'ml_alerts': self.ml_alert_count,
            'combined_alerts': self.combined_alert_count,
            'total_alerts': self.alert_count + self.ml_alert_count - self.combined_alert_count,
        }
    
    def reset_statistics(self):
        """Reset alert counters."""
        self.alert_count = 0
        self.ml_alert_count = 0
        self.combined_alert_count = 0


if __name__ == "__main__":
    # Test alert processing
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    processor = AlertProcessor()
    
    # Test 1: Flow with ML alert only
    print("\n=== Test 1: ML Alert Only ===")
    flow_event = {
        'timestamp': '2024-01-15T10:30:45.123456+0000',
        'event_type': 'flow',
        'src_ip': '192.168.1.100',
        'src_port': 54321,
        'dest_ip': '8.8.8.8',
        'dest_port': 53,
        'proto': 'UDP',
        'flow': {
            'pkts_toserver': 100,
            'pkts_toclient': 100,
            'bytes_toserver': 6400,
            'bytes_toclient': 12800,
            'age': 5.5
        }
    }
    
    alert = processor.process_flow_with_ml(
        flow_event,
        ml_prediction='DoS',
        ml_confidence=0.95
    )
    
    if alert:
        print(json.dumps(alert, indent=2))
    
    # Test 2: Flow with both Suricata and ML alerts
    print("\n=== Test 2: Combined Alert ===")
    suricata_alert = {
        'alert': {
            'signature': 'ET SCAN Potential SSH Scan',
            'signature_id': 2001219,
            'category': 'Attempted Information Leak',
            'severity': 2
        }
    }
    
    alert = processor.process_flow_with_ml(
        flow_event,
        ml_prediction='RECONNAISSANCE',
        ml_confidence=0.85,
        suricata_alert=suricata_alert
    )
    
    if alert:
        print(json.dumps(alert, indent=2))
    
    # Print statistics
    print("\n=== Statistics ===")
    print(json.dumps(processor.get_statistics(), indent=2))
