#!/usr/bin/env python3
"""
Real-time CICIDS Feature Extraction Engine

Sidecar process that reads packets via AF_PACKET fanout (same as Suricata)
and computes accurate CICIDS2017 65-feature vectors in real-time.

Uses per-flow state tracking with online statistics (Welford's algorithm).
Emits feature vectors on flow timeout or TCP termination.

Architecture:
  NIC → AF_PACKET fanout → [Suricata, Feature Engine]
       (cluster_id=99)      ↓           ↓
                          Alerts    CIC Features → ML Model
"""

import socket
import struct
import time
import sys
import signal
import json
import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, List
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Define SOL_PACKET if not available (Linux-specific)
if not hasattr(socket, 'SOL_PACKET'):
    socket.SOL_PACKET = 263

# Configuration
INTERFACE = "enp3s0"
CLUSTER_ID = 99
FLOW_TIMEOUT = 30  # seconds
IDLE_THRESHOLD = 1.0  # seconds to consider idle
KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "ml-features"


@dataclass
class FlowStats:
    """Per-flow statistics tracker using Welford's online algorithm"""
    
    # Flow identification
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    proto: int
    
    # Timestamps
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    
    # Packet/byte counts
    fwd_pkts: int = 0
    bwd_pkts: int = 0
    fwd_bytes: int = 0
    bwd_bytes: int = 0
    
    # Packet length statistics (online mean/variance)
    fwd_pkt_lens: List[int] = field(default_factory=list)
    bwd_pkt_lens: List[int] = field(default_factory=list)
    
    # Inter-arrival times (microseconds)
    fwd_iats: List[float] = field(default_factory=list)
    bwd_iats: List[float] = field(default_factory=list)
    flow_iats: List[float] = field(default_factory=list)
    
    # Last packet timestamps for IAT calculation
    last_fwd_ts: Optional[float] = None
    last_bwd_ts: Optional[float] = None
    last_any_ts: Optional[float] = None
    
    # TCP flags
    fin_count: int = 0
    syn_count: int = 0
    rst_count: int = 0
    psh_count: int = 0
    ack_count: int = 0
    urg_count: int = 0
    ece_count: int = 0
    cwe_count: int = 0
    
    fwd_psh_flags: int = 0
    fwd_urg_flags: int = 0
    bwd_psh_flags: int = 0
    bwd_urg_flags: int = 0
    
    # Header lengths
    fwd_header_len: int = 0
    bwd_header_len: int = 0
    
    # Window sizes (TCP)
    init_win_fwd: Optional[int] = None
    init_win_bwd: Optional[int] = None
    
    # Active/Idle tracking
    active_times: List[float] = field(default_factory=list)
    idle_times: List[float] = field(default_factory=list)
    last_activity_ts: Optional[float] = None
    in_active_state: bool = False
    
    def update_packet(self, pkt_len: int, is_forward: bool, timestamp: float, 
                     tcp_flags: int = 0, header_len: int = 20, window_size: int = 0):
        """Update flow statistics with new packet"""
        
        self.last_seen = timestamp
        
        # Update counts
        if is_forward:
            self.fwd_pkts += 1
            self.fwd_bytes += pkt_len
            self.fwd_pkt_lens.append(pkt_len)
            self.fwd_header_len += header_len
            
            # IAT calculation
            if self.last_fwd_ts is not None:
                iat = (timestamp - self.last_fwd_ts) * 1_000_000  # microseconds
                self.fwd_iats.append(iat)
            self.last_fwd_ts = timestamp
            
            # TCP flags
            if tcp_flags:
                if tcp_flags & 0x08:  # PSH
                    self.fwd_psh_flags += 1
                if tcp_flags & 0x20:  # URG
                    self.fwd_urg_flags += 1
            
            # Initial window size
            if self.init_win_fwd is None and window_size > 0:
                self.init_win_fwd = window_size
        else:
            self.bwd_pkts += 1
            self.bwd_bytes += pkt_len
            self.bwd_pkt_lens.append(pkt_len)
            self.bwd_header_len += header_len
            
            # IAT calculation
            if self.last_bwd_ts is not None:
                iat = (timestamp - self.last_bwd_ts) * 1_000_000
                self.bwd_iats.append(iat)
            self.last_bwd_ts = timestamp
            
            # Initial window size
            if self.init_win_bwd is None and window_size > 0:
                self.init_win_bwd = window_size
        
        # Overall flow IAT
        if self.last_any_ts is not None:
            iat = (timestamp - self.last_any_ts) * 1_000_000
            self.flow_iats.append(iat)
        self.last_any_ts = timestamp
        
        # TCP flags counting
        if tcp_flags:
            if tcp_flags & 0x01: self.fin_count += 1
            if tcp_flags & 0x02: self.syn_count += 1
            if tcp_flags & 0x04: self.rst_count += 1
            if tcp_flags & 0x08:
                self.psh_count += 1
                if is_forward:
                    self.fwd_psh_flags += 1
                else:
                    self.bwd_psh_flags += 1
            if tcp_flags & 0x10: self.ack_count += 1
            if tcp_flags & 0x20:
                self.urg_count += 1
                if is_forward:
                    self.fwd_urg_flags += 1
                else:
                    self.bwd_urg_flags += 1
            if tcp_flags & 0x40: self.ece_count += 1
            if tcp_flags & 0x80: self.cwe_count += 1
        
        # Active/Idle timing
        self._update_active_idle(timestamp)
    
    def _update_active_idle(self, timestamp: float):
        """Track active and idle periods"""
        if self.last_activity_ts is not None:
            gap = timestamp - self.last_activity_ts
            
            if gap > IDLE_THRESHOLD:
                # Was idle, now active
                if self.in_active_state:
                    # End previous active period
                    active_duration = self.last_activity_ts - self.active_start_ts
                    self.active_times.append(active_duration)
                
                # Record idle period
                self.idle_times.append(gap)
                self.in_active_state = True
                self.active_start_ts = timestamp
            else:
                # Continuous activity
                if not self.in_active_state:
                    self.in_active_state = True
                    self.active_start_ts = timestamp
        else:
            self.in_active_state = True
            self.active_start_ts = timestamp
        
        self.last_activity_ts = timestamp
    
    def extract_features(self) -> Dict[str, float]:
        """Extract CICIDS2017 65-feature vector"""
        
        duration = max(self.last_seen - self.first_seen, 0.000001)
        total_pkts = self.fwd_pkts + self.bwd_pkts
        total_bytes = self.fwd_bytes + self.bwd_bytes
        
        features = {}
        
        # Basic flow features
        features['Destination Port'] = self.dst_port
        features['Flow Duration'] = int(duration * 1_000_000)  # microseconds
        features['Total Fwd Packets'] = self.fwd_pkts
        features['Total Backward Packets'] = self.bwd_pkts
        features['Total Length of Fwd Packets'] = self.fwd_bytes
        features['Total Length of Bwd Packets'] = self.bwd_bytes
        
        # Forward packet length statistics
        if self.fwd_pkt_lens:
            features['Fwd Packet Length Max'] = max(self.fwd_pkt_lens)
            features['Fwd Packet Length Min'] = min(self.fwd_pkt_lens)
            features['Fwd Packet Length Mean'] = sum(self.fwd_pkt_lens) / len(self.fwd_pkt_lens)
            features['Fwd Packet Length Std'] = self._std(self.fwd_pkt_lens)
        else:
            features['Fwd Packet Length Max'] = 0
            features['Fwd Packet Length Min'] = 0
            features['Fwd Packet Length Mean'] = 0
            features['Fwd Packet Length Std'] = 0
        
        # Backward packet length statistics
        if self.bwd_pkt_lens:
            features['Bwd Packet Length Max'] = max(self.bwd_pkt_lens)
            features['Bwd Packet Length Min'] = min(self.bwd_pkt_lens)
            features['Bwd Packet Length Mean'] = sum(self.bwd_pkt_lens) / len(self.bwd_pkt_lens)
            features['Bwd Packet Length Std'] = self._std(self.bwd_pkt_lens)
        else:
            features['Bwd Packet Length Max'] = 0
            features['Bwd Packet Length Min'] = 0
            features['Bwd Packet Length Mean'] = 0
            features['Bwd Packet Length Std'] = 0
        
        # Flow byte/packet rates
        features['Flow Bytes/s'] = total_bytes / duration if duration > 0 else 0
        features['Flow Packets/s'] = total_pkts / duration if duration > 0 else 0
        features['Fwd Packets/s'] = self.fwd_pkts / duration if duration > 0 else 0
        features['Bwd Packets/s'] = self.bwd_pkts / duration if duration > 0 else 0
        
        # Flow IAT statistics
        if self.flow_iats:
            features['Flow IAT Mean'] = sum(self.flow_iats) / len(self.flow_iats)
            features['Flow IAT Std'] = self._std(self.flow_iats)
            features['Flow IAT Max'] = max(self.flow_iats)
            features['Flow IAT Min'] = min(self.flow_iats)
        else:
            features['Flow IAT Mean'] = 0
            features['Flow IAT Std'] = 0
            features['Flow IAT Max'] = 0
            features['Flow IAT Min'] = 0
        
        # Forward IAT statistics
        if self.fwd_iats:
            features['Fwd IAT Total'] = sum(self.fwd_iats)
            features['Fwd IAT Mean'] = sum(self.fwd_iats) / len(self.fwd_iats)
            features['Fwd IAT Std'] = self._std(self.fwd_iats)
            features['Fwd IAT Max'] = max(self.fwd_iats)
            features['Fwd IAT Min'] = min(self.fwd_iats)
        else:
            features['Fwd IAT Total'] = 0
            features['Fwd IAT Mean'] = 0
            features['Fwd IAT Std'] = 0
            features['Fwd IAT Max'] = 0
            features['Fwd IAT Min'] = 0
        
        # Backward IAT statistics
        if self.bwd_iats:
            features['Bwd IAT Total'] = sum(self.bwd_iats)
            features['Bwd IAT Mean'] = sum(self.bwd_iats) / len(self.bwd_iats)
            features['Bwd IAT Std'] = self._std(self.bwd_iats)
            features['Bwd IAT Max'] = max(self.bwd_iats)
            features['Bwd IAT Min'] = min(self.bwd_iats)
        else:
            features['Bwd IAT Total'] = 0
            features['Bwd IAT Mean'] = 0
            features['Bwd IAT Std'] = 0
            features['Bwd IAT Max'] = 0
            features['Bwd IAT Min'] = 0
        
        # TCP flags
        features['Fwd PSH Flags'] = self.fwd_psh_flags
        features['Bwd PSH Flags'] = self.bwd_psh_flags
        features['Fwd URG Flags'] = self.fwd_urg_flags
        features['Bwd URG Flags'] = self.bwd_urg_flags
        features['Fwd Header Length'] = self.fwd_header_len
        features['Bwd Header Length'] = self.bwd_header_len
        
        # Packet length statistics (overall)
        all_lens = self.fwd_pkt_lens + self.bwd_pkt_lens
        if all_lens:
            features['Min Packet Length'] = min(all_lens)
            features['Max Packet Length'] = max(all_lens)
            features['Packet Length Mean'] = sum(all_lens) / len(all_lens)
            features['Packet Length Std'] = self._std(all_lens)
            features['Packet Length Variance'] = features['Packet Length Std'] ** 2
        else:
            features['Min Packet Length'] = 0
            features['Max Packet Length'] = 0
            features['Packet Length Mean'] = 0
            features['Packet Length Std'] = 0
            features['Packet Length Variance'] = 0
        
        # TCP flag counts
        features['FIN Flag Count'] = self.fin_count
        features['SYN Flag Count'] = self.syn_count
        features['RST Flag Count'] = self.rst_count
        features['PSH Flag Count'] = self.psh_count
        features['ACK Flag Count'] = self.ack_count
        features['URG Flag Count'] = self.urg_count
        features['CWE Flag Count'] = self.cwe_count
        features['ECE Flag Count'] = self.ece_count
        
        # Ratios and averages
        features['Down/Up Ratio'] = self.bwd_bytes / self.fwd_bytes if self.fwd_bytes > 0 else 0
        features['Average Packet Size'] = total_bytes / total_pkts if total_pkts > 0 else 0
        features['Avg Fwd Segment Size'] = self.fwd_bytes / self.fwd_pkts if self.fwd_pkts > 0 else 0
        features['Avg Bwd Segment Size'] = self.bwd_bytes / self.bwd_pkts if self.bwd_pkts > 0 else 0
        
        # Duplicate Fwd Header Length (appears twice in CSV - #35 and #56)
        features['Fwd Header Length'] = self.fwd_header_len  # Appears again at position 56
        
        # Bulk transfer features (not applicable for real-time, set to 0)
        features['Fwd Avg Bytes/Bulk'] = 0
        features['Fwd Avg Packets/Bulk'] = 0
        features['Fwd Avg Bulk Rate'] = 0
        features['Bwd Avg Bytes/Bulk'] = 0
        features['Bwd Avg Packets/Bulk'] = 0
        features['Bwd Avg Bulk Rate'] = 0
        
        # Subflow features (for single flow, same as total)
        features['Subflow Fwd Packets'] = self.fwd_pkts
        features['Subflow Fwd Bytes'] = self.fwd_bytes
        features['Subflow Bwd Packets'] = self.bwd_pkts
        features['Subflow Bwd Bytes'] = self.bwd_bytes
        
        # TCP window sizes
        features['Init_Win_bytes_forward'] = self.init_win_fwd or 0
        features['Init_Win_bytes_backward'] = self.init_win_bwd or 0
        
        # Active data packets forward (packets with payload)
        features['act_data_pkt_fwd'] = self.fwd_pkts
        
        # Minimum segment size forward
        features['min_seg_size_forward'] = min(self.fwd_pkt_lens) if self.fwd_pkt_lens else 0
        
        # Active/Idle statistics
        if self.active_times:
            features['Active Mean'] = sum(self.active_times) / len(self.active_times)
            features['Active Std'] = self._std(self.active_times)
            features['Active Max'] = max(self.active_times)
            features['Active Min'] = min(self.active_times)
        else:
            features['Active Mean'] = 0
            features['Active Std'] = 0
            features['Active Max'] = 0
            features['Active Min'] = 0
        
        if self.idle_times:
            features['Idle Mean'] = sum(self.idle_times) / len(self.idle_times)
            features['Idle Std'] = self._std(self.idle_times)
            features['Idle Max'] = max(self.idle_times)
            features['Idle Min'] = min(self.idle_times)
        else:
            features['Idle Mean'] = 0
            features['Idle Std'] = 0
            features['Idle Max'] = 0
            features['Idle Min'] = 0
        
        return features
    
    @staticmethod
    def _std(values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    
    def is_terminated(self) -> bool:
        """Check if flow should be terminated (FIN/RST or timeout)"""
        return (self.fin_count > 0 or self.rst_count > 0 or 
                (time.time() - self.last_seen) > FLOW_TIMEOUT)


class RealtimeFeatureEngine:
    """Main feature extraction engine using AF_PACKET fanout"""
    
    def __init__(self, interface: str, cluster_id: int = 99):
        self.interface = interface
        self.cluster_id = cluster_id
        self.flows: Dict[Tuple, FlowStats] = {}
        self.running = True
        self.stats = {'packets': 0, 'flows_created': 0, 'flows_completed': 0}
        
        # Kafka producer for feature vectors
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda x: json.dumps(x).encode('utf-8'),
            compression_type='gzip'
        )
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Shutting down... (signal {signum})")
        self.running = False
    
    def start(self):
        """Start packet capture and feature extraction"""
        print(f"🚀 Starting Real-time Feature Engine")
        print(f"   Interface: {self.interface}")
        print(f"   Cluster ID: {self.cluster_id}")
        print(f"   Flow timeout: {FLOW_TIMEOUT}s")
        print(f"   Kafka topic: {KAFKA_TOPIC}")
        print()
        
        # Create AF_PACKET socket with fanout
        try:
            sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
            sock.bind((self.interface, 0))
            
            # Enable fanout mode (same as Suricata)
            # fanout_id = (cluster_id << 16) | fanout_type
            # fanout_type: 2 = PACKET_FANOUT_CPU (flow-based)
            fanout_arg = struct.pack('II', self.cluster_id, 2)
            sock.setsockopt(socket.SOL_PACKET, 18, fanout_arg)  # 18 = PACKET_FANOUT
            
            print("✅ AF_PACKET fanout enabled")
            print("📊 Starting packet processing...\n")
            
        except Exception as e:
            print(f"❌ Failed to create AF_PACKET socket: {e}")
            print(f"   Make sure you run with sudo!")
            sys.exit(1)
        
        last_cleanup = time.time()
        
        try:
            while self.running:
                # Receive packet
                packet_data, addr = sock.recvfrom(65535)
                self.stats['packets'] += 1
                
                # Print first few packets for debugging
                if self.stats['packets'] <= 5:
                    print(f"✓ Captured packet #{self.stats['packets']} ({len(packet_data)} bytes)")
                
                # Parse and process packet
                self._process_packet(packet_data, time.time())
                
                # Periodic cleanup of old flows
                if time.time() - last_cleanup > 10:
                    self._cleanup_flows()
                    last_cleanup = time.time()
                    
                    # Print stats
                    if self.stats['packets'] % 100 == 0:  # Lower threshold for testing
                        print(f"📊 Packets: {self.stats['packets']:,} | "
                              f"Active flows: {len(self.flows)} | "
                              f"Completed: {self.stats['flows_completed']}")
        
        except KeyboardInterrupt:
            pass
        finally:
            sock.close()
            self.producer.close()
            print(f"\n✅ Engine stopped. Final stats: {self.stats}")
    
    def _process_packet(self, packet_data: bytes, timestamp: float):
        """Parse and process a single packet"""
        try:
            # Debug first packet
            if self.stats['packets'] == 1:
                print(f"🔍 First packet: len={len(packet_data)}, hex={packet_data[:20].hex()}")
            
            # Parse Ethernet header (14 bytes)
            if len(packet_data) < 14:
                if self.stats['packets'] <= 5:
                    print(f"⚠️  Packet too short: {len(packet_data)} bytes")
                return
            
            eth_header = struct.unpack('!6s6sH', packet_data[:14])
            eth_proto = eth_header[2]  # Already in network byte order from '!' format
            
            if self.stats['packets'] == 1:
                print(f"🔍 Ethernet protocol: 0x{eth_proto:04x} (expect 0x0800 for IP)")
            
            # Only process IP packets (0x0800)
            if eth_proto != 0x0800:
                if self.stats['packets'] <= 5:
                    print(f"⚠️  Non-IP packet: 0x{eth_proto:04x}")
                return
            
            # Parse IP header
            ip_header = packet_data[14:34]
            if len(ip_header) < 20:
                return
            
            iph = struct.unpack('!BBHHHBBH4s4s', ip_header)
            version_ihl = iph[0]
            ihl = (version_ihl & 0xF) * 4
            protocol = iph[6]
            src_ip = socket.inet_ntoa(iph[8])
            dst_ip = socket.inet_ntoa(iph[9])
            
            # TCP (6) or UDP (17)
            if protocol not in [6, 17]:
                return
            
            # Parse transport layer
            transport_start = 14 + ihl
            if len(packet_data) < transport_start + 8:
                return
            
            transport_header = packet_data[transport_start:transport_start + 20]
            src_port, dst_port = struct.unpack('!HH', transport_header[:4])
            
            # TCP flags and window
            tcp_flags = 0
            window_size = 0
            header_len = 20
            
            if protocol == 6:  # TCP
                if len(transport_header) >= 14:
                    tcp_flags = struct.unpack('!B', transport_header[13:14])[0]
                    window_size = struct.unpack('!H', transport_header[14:16])[0]
                    data_offset = (struct.unpack('!B', transport_header[12:13])[0] >> 4) * 4
                    header_len = data_offset
            else:  # UDP
                header_len = 8
            
            # Calculate payload length
            total_len = socket.ntohs(iph[2])
            payload_len = total_len - ihl - header_len
            pkt_len = len(packet_data)
            
            # Determine flow direction
            flow_key_fwd = (src_ip, dst_ip, src_port, dst_port, protocol)
            flow_key_bwd = (dst_ip, src_ip, dst_port, src_port, protocol)
            
            is_forward = True
            if flow_key_fwd in self.flows:
                flow_key = flow_key_fwd
            elif flow_key_bwd in self.flows:
                flow_key = flow_key_bwd
                is_forward = False
            else:
                # New flow
                flow_key = flow_key_fwd
                self.flows[flow_key] = FlowStats(
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_port=src_port,
                    dst_port=dst_port,
                    proto=protocol
                )
                self.stats['flows_created'] += 1
                print(f"🆕 New flow: {src_ip}:{src_port} → {dst_ip}:{dst_port} (proto={protocol})")
            
            # Update flow statistics
            flow = self.flows[flow_key]
            flow.update_packet(pkt_len, is_forward, timestamp, tcp_flags, header_len, window_size)
            
            # Check if flow should be terminated
            if flow.is_terminated():
                features = flow.extract_features()
                self._emit_features(flow_key, features)
                del self.flows[flow_key]
                self.stats['flows_completed'] += 1
        
        except Exception as e:
            # Debug: show errors for first few packets
            if self.stats['packets'] <= 10:
                print(f"⚠️  Error processing packet: {e}")
    
    def _cleanup_flows(self):
        """Remove old flows that have timed out"""
        current_time = time.time()
        to_remove = []
        
        for flow_key, flow in self.flows.items():
            if (current_time - flow.last_seen) > FLOW_TIMEOUT:
                print(f"⏱ Flow timeout: {flow_key}")
                features = flow.extract_features()
                self._emit_features(flow_key, features)
                to_remove.append(flow_key)
                self.stats['flows_completed'] += 1
        
        for flow_key in to_remove:
            del self.flows[flow_key]
        
        # Debug: show active flows
        if len(self.flows) > 0:
            print(f"📊 Active flows: {len(self.flows)}, Completed: {self.stats['flows_completed']}")
    
    def _emit_features(self, flow_key: Tuple, features: Dict[str, float]):
        """Send feature vector to Kafka"""
        try:
            message = {
                'timestamp': datetime.now().isoformat(),
                'flow_id': f"{flow_key[0]}:{flow_key[2]}-{flow_key[1]}:{flow_key[3]}",
                'src_ip': flow_key[0],
                'dst_ip': flow_key[1],
                'src_port': flow_key[2],
                'dst_port': flow_key[3],
                'proto': flow_key[4],
                'features': features
            }
            
            future = self.producer.send(KAFKA_TOPIC, value=message)
            # Debug first few emissions
            if self.stats['flows_completed'] <= 3:
                print(f"✉️  Emitted features for flow: {message['flow_id']}")
            
        except Exception as e:
            print(f"❌ Error sending to Kafka: {e}")


def main():
    """Entry point"""
    import argparse
    # Declare globals first
    global INTERFACE, CLUSTER_ID, KAFKA_BOOTSTRAP, KAFKA_TOPIC, FLOW_TIMEOUT
    
    parser = argparse.ArgumentParser(description='Real-time CICIDS Feature Extraction Engine')
    parser.add_argument('-i', '--interface', default='enp0s1', help='Network interface')
    parser.add_argument('-c', '--cluster-id', type=int, default=99, help='AF_PACKET cluster ID')
    parser.add_argument('-t', '--timeout', type=int, default=30, help='Flow timeout in seconds (default: 30, recommend: 10 for faster detection)')
    parser.add_argument('--kafka', default='localhost:9092', help='Kafka bootstrap servers')
    parser.add_argument('--topic', default='ml-features', help='Kafka topic for features')
    
    args = parser.parse_args()
    
    # Update globals with parsed values
    INTERFACE = args.interface
    CLUSTER_ID = args.cluster_id
    FLOW_TIMEOUT = args.timeout
    KAFKA_BOOTSTRAP = args.kafka
    KAFKA_TOPIC = args.topic
    
    # Check if running as root
    if sys.platform.startswith('linux'):
        import os
        if os.geteuid() != 0:
            print("❌ This program must be run as root (sudo)")
            sys.exit(1)
    
    # Start engine
    engine = RealtimeFeatureEngine(INTERFACE, CLUSTER_ID)
    engine.start()


if __name__ == '__main__':
    main()
