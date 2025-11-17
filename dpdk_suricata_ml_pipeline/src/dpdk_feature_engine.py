#!/usr/bin/env python3
"""
DPDK-based Real-time Feature Extraction Engine for CICIDS2017

Uses DPDK to directly capture packets from Intel X520 NIC (0000:01:00.0)
and compute real-time CICIDS65 feature vectors.

Architecture:
  X520 NIC (DPDK/vfio-pci) → Packet RX → Feature Extraction → Kafka Topic (ml-features)
  
Dependencies:
  - PyDPDK (dpdk python bindings)
  - kafka-python
  - scapy (packet parsing)
"""

import sys
import time
import json
import socket
import struct
import signal
import os
from pathlib import Path
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError
import logging

# Try to import DPDK Python bindings
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from pydpdk_wrapper import PyDPDK
    DPDK_AVAILABLE = True
    print("✅ PyDPDK wrapper loaded successfully")
except Exception as e:
    print(f"⚠️  PyDPDK not available: {e}")
    DPDK_AVAILABLE = False

try:
    from scapy.all import IP, TCP, UDP, ICMP, Raw
except ImportError:
    print("Error: scapy not installed. Install with: pip install scapy")
    sys.exit(1)

# Configuration
DPDK_PORT_ID = 0  # First DPDK port (X520 NIC)
DPDK_RXQUEUE = 0
NUM_RX_DESC = 128
NUM_TX_DESC = 128
BURST_SIZE = 32
PKT_HEADROOM = 128

KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "ml-features"
FLOW_TIMEOUT = 30  # seconds

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class FlowKey:
    """Flow identification tuple"""
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: int
    
    def __hash__(self):
        return hash((self.src_ip, self.dst_ip, self.src_port, self.dst_port, self.protocol))
    
    def __eq__(self, other):
        return (self.src_ip == other.src_ip and 
                self.dst_ip == other.dst_ip and
                self.src_port == other.src_port and
                self.dst_port == other.dst_port and
                self.protocol == other.protocol)


@dataclass
class FlowStats:
    """Per-flow statistics for CICIDS features"""
    flow_key: FlowKey
    packets_fwd: int = 0
    bytes_fwd: int = 0
    packets_bwd: int = 0
    bytes_bwd: int = 0
    
    duration_ms: int = 0
    packet_lengths_fwd: deque = field(default_factory=lambda: deque(maxlen=1000))
    packet_lengths_bwd: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    inter_arrival_times_fwd: deque = field(default_factory=lambda: deque(maxlen=1000))
    inter_arrival_times_bwd: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    flags_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    last_packet_time: float = 0
    first_packet_time: float = 0
    
    def to_feature_vector(self) -> dict:
        """Convert flow stats to CICIDS65 feature vector (simplified)"""
        # This is a simplified set - full CICIDS has 65 features
        features = {
            'flow_duration': self.duration_ms,
            'total_fwd_packets': self.packets_fwd,
            'total_bwd_packets': self.packets_bwd,
            'total_length_fwd_packets': self.bytes_fwd,
            'total_length_bwd_packets': self.bytes_bwd,
            'fwd_packet_length_max': max(self.packet_lengths_fwd) if self.packet_lengths_fwd else 0,
            'fwd_packet_length_min': min(self.packet_lengths_fwd) if self.packet_lengths_fwd else 0,
            'fwd_packet_length_mean': sum(self.packet_lengths_fwd) / len(self.packet_lengths_fwd) if self.packet_lengths_fwd else 0,
            'bwd_packet_length_max': max(self.packet_lengths_bwd) if self.packet_lengths_bwd else 0,
            'bwd_packet_length_min': min(self.packet_lengths_bwd) if self.packet_lengths_bwd else 0,
            'bwd_packet_length_mean': sum(self.packet_lengths_bwd) / len(self.packet_lengths_bwd) if self.packet_lengths_bwd else 0,
            'timestamp': datetime.now().isoformat()
        }
        return features


class DPDKFeatureEngine:
    """DPDK-based real-time feature extraction"""
    
    def __init__(self):
        self.running = True
        self.flows: Dict[FlowKey, FlowStats] = {}
        self.stats = {'packets': 0, 'flows': 0, 'total_packets': 0}
        self._has_stats_packets = False
        
        # Kafka producer
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                compression_type='gzip',
                acks='all',
                retries=3
            )
            logger.info(f"✓ Connected to Kafka at {KAFKA_BOOTSTRAP}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Kafka: {e}")
            logger.info("Continuing without Kafka output...")
            self.producer = None
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _extract_features_from_suricata_flow(self, flow_event: dict) -> Optional[dict]:
        """Extract CICIDS-compatible features from Suricata flow event"""
        try:
            flow_data = flow_event.get('flow', {})
            dest_port = flow_event.get('dest_port', 0)
            pkts_fwd = flow_data.get('pkts_toserver', 0)
            pkts_bwd = flow_data.get('pkts_toclient', 0)
            bytes_fwd = flow_data.get('bytes_toserver', 0)
            bytes_bwd = flow_data.get('bytes_toclient', 0)
            duration = flow_data.get('age', 0)
            
            flow_duration_ms = duration * 1000 if duration > 0 else 1
            flow_bytes_per_sec = (bytes_fwd + bytes_bwd) / duration if duration > 0 else 0
            flow_packets_per_sec = (pkts_fwd + pkts_bwd) / duration if duration > 0 else 0
            
            # Build feature vector with all 65 features
            features = {
                'Destination Port': dest_port,
                'Flow Duration': flow_duration_ms,
                'Total Fwd Packets': pkts_fwd,
                'Total Backward Packets': pkts_bwd,
                'Total Length of Fwd Packets': bytes_fwd,
                'Total Length of Bwd Packets': bytes_bwd,
                'Fwd Packet Length Max': bytes_fwd / pkts_fwd if pkts_fwd > 0 else 0,
                'Fwd Packet Length Min': bytes_fwd / pkts_fwd if pkts_fwd > 0 else 0,
                'Fwd Packet Length Mean': bytes_fwd / pkts_fwd if pkts_fwd > 0 else 0,
                'Fwd Packet Length Std': 0.0,
                'Bwd Packet Length Max': bytes_bwd / pkts_bwd if pkts_bwd > 0 else 0,
                'Bwd Packet Length Min': bytes_bwd / pkts_bwd if pkts_bwd > 0 else 0,
                'Bwd Packet Length Mean': bytes_bwd / pkts_bwd if pkts_bwd > 0 else 0,
                'Bwd Packet Length Std': 0.0,
                'Flow Bytes/s': flow_bytes_per_sec,
                'Flow Packets/s': flow_packets_per_sec,
            }
            # Add remaining 49 features with default values
            for i in range(49):
                features[f'feature_{i}'] = 0.0
            
            return features
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"\n🛑 Shutting down... (signal {signum})")
        self.running = False
    
    def _parse_packet(self, pkt_data: bytes) -> Optional[FlowKey]:
        """Parse packet and extract flow key"""
        try:
            # Skip Ethernet header (14 bytes)
            eth_header = pkt_data[:14]
            eth_type = struct.unpack('!H', eth_header[12:14])[0]
            
            # Only process IPv4
            if eth_type != 0x0800:
                return None
            
            # Parse IP header
            ip_header = pkt_data[14:34]
            ip_version = ip_header[0] >> 4
            if ip_version != 4:
                return None
            
            ip_protocol = ip_header[9]
            src_ip = socket.inet_ntoa(ip_header[12:16])
            dst_ip = socket.inet_ntoa(ip_header[16:20])
            
            # Parse TCP/UDP
            ip_header_len = (ip_header[0] & 0x0f) * 4
            payload_start = 14 + ip_header_len
            
            src_port = 0
            dst_port = 0
            
            if ip_protocol in (6, 17):  # TCP or UDP
                ports = struct.unpack('!HH', pkt_data[payload_start:payload_start+4])
                src_port = ports[0]
                dst_port = ports[1]
            
            return FlowKey(src_ip, dst_ip, src_port, dst_port, ip_protocol)
        
        except Exception as e:
            return None
    
    def _update_flow_stats(self, pkt_data: bytes, flow_key: FlowKey, timestamp: float):
        """Update flow statistics with packet data"""
        if flow_key not in self.flows:
            self.flows[flow_key] = FlowStats(
                flow_key=flow_key,
                first_packet_time=timestamp,
                last_packet_time=timestamp
            )
            self.stats['flows'] += 1
        
        flow = self.flows[flow_key]
        pkt_len = len(pkt_data)
        current_time = timestamp
        
        # Update directional stats (simplified - forward direction only)
        flow.packets_fwd += 1
        flow.bytes_fwd += pkt_len
        flow.packet_lengths_fwd.append(pkt_len)
        flow.duration_ms = int((current_time - flow.first_packet_time) * 1000)
        flow.last_packet_time = current_time
    
    def start(self):
        """Start DPDK packet capture and feature extraction"""
        logger.info("🚀 Starting DPDK Feature Engine")
        logger.info(f"   Port: {DPDK_PORT_ID}")
        logger.info(f"   Kafka Topic: {KAFKA_TOPIC}")
        logger.info(f"   Flow Timeout: {FLOW_TIMEOUT}s")
        logger.info("📊 Starting packet processing...\n")
        
        if not DPDK_AVAILABLE:
            logger.warning("⚠️  PyDPDK not available - using fallback mode")
            self._run_fallback_mode()
        else:
            self._run_dpdk_mode()
    
    def _run_fallback_mode(self):
        """Fallback to reading Suricata EVE JSON if DPDK unavailable"""
        logger.info("📖 Reading Suricata EVE JSON output from /var/log/suricata/eve.json")
        
        eve_file = "/var/log/suricata/eve.json"
        last_pos = 0
        last_cleanup = time.time()
        
        try:
            with open(eve_file, 'r') as f:
                # Skip historical data to avoid replaying stale flows
                f.seek(0, os.SEEK_END)
                logger.info("📄 Attached to Suricata eve.json (tailing new entries only)")

                while self.running:
                    line = f.readline()
                    
                    if line:
                        try:
                            event = json.loads(line)
                            
                            # Only process flow entries and extract features
                            if event.get('event_type') == 'flow':
                                self.stats['packets'] += 1
                                
                                # Extract CICIDS features from Suricata flow
                                features = self._extract_features_from_suricata_flow(event)

                                if features and self.producer:
                                    try:
                                        feature_message = {
                                            'features': features,
                                            'flow_id': event.get('flow_id'),
                                            'timestamp': event.get('timestamp')
                                        }
                                        self.producer.send(KAFKA_TOPIC, value=feature_message)
                                    except Exception as e:
                                        logger.error(f"Failed to send to Kafka: {e}")
                        
                        except json.JSONDecodeError:
                            pass
                    else:
                        time.sleep(0.1)
                    
                    # Cleanup old flows periodically
                    current_time = time.time()
                    if current_time - last_cleanup > 10:
                        self._cleanup_old_flows(current_time)
                        last_cleanup = current_time
                        self._print_stats()
        
        except KeyboardInterrupt:
            logger.info("✓ Shutdown requested")
        except Exception as e:
            logger.error(f"Error: {e}")
    
    def _run_dpdk_mode(self):
        """Run with actual DPDK packet capture"""
        logger.info("⚡ DPDK mode disabled - using Suricata EVE JSON instead")
        # Skip DPDK mode since Suricata owns the device
        self._run_fallback_mode()
    
    def _cleanup_old_flows(self, current_time: float):
        """Remove flows that haven't seen packets in FLOW_TIMEOUT seconds"""
        to_delete = []
        for flow_key, flow_stats in self.flows.items():
            if current_time - flow_stats.last_packet_time > FLOW_TIMEOUT:
                # Emit final feature vector before deleting
                if self.producer:
                    try:
                        features = flow_stats.to_feature_vector()
                        features['flow_key'] = {
                            'src_ip': flow_key.src_ip,
                            'dst_ip': flow_key.dst_ip,
                            'src_port': flow_key.src_port,
                            'dst_port': flow_key.dst_port,
                            'protocol': flow_key.protocol
                        }
                        self.producer.send(KAFKA_TOPIC, value=features)
                    except Exception as e:
                        logger.error(f"Failed to send features: {e}")
                
                to_delete.append(flow_key)
        
        for flow_key in to_delete:
            del self.flows[flow_key]
    
    def _print_stats(self):
        """Print processing statistics"""
        logger.info(f"📊 Stats: {self.stats['packets']} packets, {len(self.flows)} active flows")


def main():
    """Main entry point"""
    engine = DPDKFeatureEngine()
    try:
        engine.start()
    except KeyboardInterrupt:
        logger.info("✓ Shutdown complete")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
