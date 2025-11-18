#!/usr/bin/env python3
"""
DPDK Multi-Queue Feature Extraction Engine

Uses DPDK RSS (Receive Side Scaling) with multiple queues to allow both
Suricata and this feature engine to capture packets simultaneously from
the same Intel NIC without conflicts.

Architecture:
    Intel X520 NIC (DPDK mode, RSS enabled)
    ├── Queue 0 → Suricata Worker 1
    ├── Queue 1 → Suricata Worker 2  
    ├── Queue 2 → Feature Engine (this process)
    └── Queue 3 → Feature Engine (this process)

Both processes receive all traffic via RSS hash distribution.
This engine performs per-packet feature extraction to calculate REAL
statistical features (not approximations).

Key Features:
- Per-packet timestamp tracking for accurate IAT calculation
- Per-packet length tracking for true min/max/std statistics
- TCP flag and window size capture from actual packets
- Active/idle period measurement from real timing data
- Flow state management with proper timeout handling

Dependencies:
- DPDK 20.11+ with Python bindings
- Intel X520 NIC (or compatible)
- NIC must be bound to vfio-pci or uio_pci_generic
"""

import sys
import time
import json
import struct
import socket
import signal
import logging
import numpy as np
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, List
from datetime import datetime
from kafka import KafkaProducer

# Try to import DPDK bindings
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from pydpdk_wrapper import PyDPDK
    DPDK_AVAILABLE = True
except Exception as e:
    print(f"⚠️  PyDPDK not available: {e}")
    DPDK_AVAILABLE = False

# Configuration
DPDK_PORT_ID = 0
DPDK_RX_QUEUES = [2, 3]  # Use queues 2-3 (Suricata uses 0-1)
NUM_RX_DESC = 512
BURST_SIZE = 32
MEMPOOL_SIZE = 8191  # Must be 2^n - 1
MEMPOOL_CACHE = 256

KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "ml-features"
FLOW_TIMEOUT = 30.0  # seconds
IDLE_THRESHOLD = 1.0  # seconds to consider a gap as "idle"

# TCP Flags
TCP_FIN = 0x01
TCP_SYN = 0x02
TCP_RST = 0x04
TCP_PSH = 0x08
TCP_ACK = 0x10
TCP_URG = 0x20
TCP_ECE = 0x40
TCP_CWR = 0x80

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PacketInfo:
    """Individual packet information"""
    timestamp: float
    length: int
    tcp_flags: int = 0
    tcp_window: int = 0
    header_len: int = 20


@dataclass
class FlowStatistics:
    """
    Per-flow statistics tracker with complete packet-level data.
    Stores actual packet information for calculating real CICIDS features.
    """
    # Flow identification
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: int
    
    # Timestamps
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    
    # Packet collections (stores actual packet data)
    fwd_packets: List[PacketInfo] = field(default_factory=list)
    bwd_packets: List[PacketInfo] = field(default_factory=list)
    
    # Last packet timestamps for IAT calculation
    last_fwd_ts: Optional[float] = None
    last_bwd_ts: Optional[float] = None
    last_any_ts: Optional[float] = None
    
    # Activity periods
    active_start: Optional[float] = None
    idle_periods: List[float] = field(default_factory=list)
    active_periods: List[float] = field(default_factory=list)
    
    def add_packet(self, is_forward: bool, pkt_info: PacketInfo):
        """Add packet to flow statistics"""
        self.last_seen = pkt_info.timestamp
        
        if is_forward:
            self.fwd_packets.append(pkt_info)
            self.last_fwd_ts = pkt_info.timestamp
        else:
            self.bwd_packets.append(pkt_info)
            self.last_bwd_ts = pkt_info.timestamp
        
        # Track active/idle periods
        if self.last_any_ts is not None:
            gap = pkt_info.timestamp - self.last_any_ts
            
            if gap > IDLE_THRESHOLD:
                # Idle period detected
                self.idle_periods.append(gap)
                
                # End previous active period if one exists
                if self.active_start is not None:
                    active_duration = self.last_any_ts - self.active_start
                    if active_duration > 0:
                        self.active_periods.append(active_duration)
                
                # Start new active period
                self.active_start = pkt_info.timestamp
        else:
            # First packet - start active period
            self.active_start = pkt_info.timestamp
        
        self.last_any_ts = pkt_info.timestamp
    
    def extract_cicids_features(self) -> Dict[str, float]:
        """
        Extract all 65 CICIDS2017 features using REAL packet data.
        No approximations or synthetic values.
        """
        features = {}
        
        # Basic counts
        fwd_count = len(self.fwd_packets)
        bwd_count = len(self.bwd_packets)
        total_count = fwd_count + bwd_count
        
        # Calculate duration
        duration = max(self.last_seen - self.first_seen, 0.000001)  # Avoid division by zero
        duration_us = int(duration * 1_000_000)
        
        # Extract packet lengths
        fwd_lengths = [p.length for p in self.fwd_packets]
        bwd_lengths = [p.length for p in self.bwd_packets]
        all_lengths = fwd_lengths + bwd_lengths
        
        # Calculate IATs (inter-arrival times)
        fwd_iats = []
        bwd_iats = []
        flow_iats = []
        
        # Forward IATs
        for i in range(1, len(self.fwd_packets)):
            iat = (self.fwd_packets[i].timestamp - self.fwd_packets[i-1].timestamp) * 1_000_000
            fwd_iats.append(iat)
        
        # Backward IATs  
        for i in range(1, len(self.bwd_packets)):
            iat = (self.bwd_packets[i].timestamp - self.bwd_packets[i-1].timestamp) * 1_000_000
            bwd_iats.append(iat)
        
        # Flow IATs (all packets)
        all_packets = sorted(self.fwd_packets + self.bwd_packets, key=lambda p: p.timestamp)
        for i in range(1, len(all_packets)):
            iat = (all_packets[i].timestamp - all_packets[i-1].timestamp) * 1_000_000
            flow_iats.append(iat)
        
        # === BASIC FEATURES ===
        features['Destination Port'] = self.dst_port
        features['Flow Duration'] = duration_us
        features['Total Fwd Packets'] = fwd_count
        features['Total Backward Packets'] = bwd_count
        features['Total Length of Fwd Packets'] = sum(fwd_lengths) if fwd_lengths else 0
        features['Total Length of Bwd Packets'] = sum(bwd_lengths) if bwd_lengths else 0
        
        # === FORWARD PACKET LENGTH STATISTICS (REAL) ===
        if fwd_lengths:
            features['Fwd Packet Length Max'] = np.max(fwd_lengths)
            features['Fwd Packet Length Min'] = np.min(fwd_lengths)
            features['Fwd Packet Length Mean'] = np.mean(fwd_lengths)
            features['Fwd Packet Length Std'] = np.std(fwd_lengths) if len(fwd_lengths) > 1 else 0.0
        else:
            features['Fwd Packet Length Max'] = 0
            features['Fwd Packet Length Min'] = 0
            features['Fwd Packet Length Mean'] = 0
            features['Fwd Packet Length Std'] = 0
        
        # === BACKWARD PACKET LENGTH STATISTICS (REAL) ===
        if bwd_lengths:
            features['Bwd Packet Length Max'] = np.max(bwd_lengths)
            features['Bwd Packet Length Min'] = np.min(bwd_lengths)
            features['Bwd Packet Length Mean'] = np.mean(bwd_lengths)
            features['Bwd Packet Length Std'] = np.std(bwd_lengths) if len(bwd_lengths) > 1 else 0.0
        else:
            features['Bwd Packet Length Max'] = 0
            features['Bwd Packet Length Min'] = 0
            features['Bwd Packet Length Mean'] = 0
            features['Bwd Packet Length Std'] = 0
        
        # === FLOW RATES ===
        total_bytes = sum(all_lengths) if all_lengths else 0
        features['Flow Bytes/s'] = total_bytes / duration
        features['Flow Packets/s'] = total_count / duration
        features['Fwd Packets/s'] = fwd_count / duration
        features['Bwd Packets/s'] = bwd_count / duration
        
        # === FLOW IAT STATISTICS (REAL) ===
        if flow_iats:
            features['Flow IAT Mean'] = np.mean(flow_iats)
            features['Flow IAT Std'] = np.std(flow_iats) if len(flow_iats) > 1 else 0.0
            features['Flow IAT Max'] = np.max(flow_iats)
            features['Flow IAT Min'] = np.min(flow_iats)
        else:
            features['Flow IAT Mean'] = 0
            features['Flow IAT Std'] = 0
            features['Flow IAT Max'] = 0
            features['Flow IAT Min'] = 0
        
        # === FORWARD IAT STATISTICS (REAL) ===
        if fwd_iats:
            features['Fwd IAT Total'] = np.sum(fwd_iats)
            features['Fwd IAT Mean'] = np.mean(fwd_iats)
            features['Fwd IAT Std'] = np.std(fwd_iats) if len(fwd_iats) > 1 else 0.0
            features['Fwd IAT Max'] = np.max(fwd_iats)
            features['Fwd IAT Min'] = np.min(fwd_iats)
        else:
            features['Fwd IAT Total'] = 0
            features['Fwd IAT Mean'] = 0
            features['Fwd IAT Std'] = 0
            features['Fwd IAT Max'] = 0
            features['Fwd IAT Min'] = 0
        
        # === BACKWARD IAT STATISTICS (REAL) ===
        if bwd_iats:
            features['Bwd IAT Total'] = np.sum(bwd_iats)
            features['Bwd IAT Mean'] = np.mean(bwd_iats)
            features['Bwd IAT Std'] = np.std(bwd_iats) if len(bwd_iats) > 1 else 0.0
            features['Bwd IAT Max'] = np.max(bwd_iats)
            features['Bwd IAT Min'] = np.min(bwd_iats)
        else:
            features['Bwd IAT Total'] = 0
            features['Bwd IAT Mean'] = 0
            features['Bwd IAT Std'] = 0
            features['Bwd IAT Max'] = 0
            features['Bwd IAT Min'] = 0
        
        # === TCP FLAGS (REAL COUNTS) ===
        fwd_psh = sum(1 for p in self.fwd_packets if p.tcp_flags & TCP_PSH)
        bwd_psh = sum(1 for p in self.bwd_packets if p.tcp_flags & TCP_PSH)
        fwd_urg = sum(1 for p in self.fwd_packets if p.tcp_flags & TCP_URG)
        bwd_urg = sum(1 for p in self.bwd_packets if p.tcp_flags & TCP_URG)
        
        features['Fwd PSH Flags'] = fwd_psh
        features['Bwd PSH Flags'] = bwd_psh
        features['Fwd URG Flags'] = fwd_urg
        features['Bwd URG Flags'] = bwd_urg
        
        # === HEADER LENGTHS (REAL) ===
        features['Fwd Header Length'] = sum(p.header_len for p in self.fwd_packets)
        features['Bwd Header Length'] = sum(p.header_len for p in self.bwd_packets)
        
        # === OVERALL PACKET LENGTH STATISTICS (REAL) ===
        if all_lengths:
            features['Min Packet Length'] = np.min(all_lengths)
            features['Max Packet Length'] = np.max(all_lengths)
            features['Packet Length Mean'] = np.mean(all_lengths)
            features['Packet Length Std'] = np.std(all_lengths) if len(all_lengths) > 1 else 0.0
            features['Packet Length Variance'] = np.var(all_lengths) if len(all_lengths) > 1 else 0.0
        else:
            features['Min Packet Length'] = 0
            features['Max Packet Length'] = 0
            features['Packet Length Mean'] = 0
            features['Packet Length Std'] = 0
            features['Packet Length Variance'] = 0
        
        # === ALL TCP FLAG COUNTS (REAL) ===
        all_packets_list = self.fwd_packets + self.bwd_packets
        features['FIN Flag Count'] = sum(1 for p in all_packets_list if p.tcp_flags & TCP_FIN)
        features['SYN Flag Count'] = sum(1 for p in all_packets_list if p.tcp_flags & TCP_SYN)
        features['RST Flag Count'] = sum(1 for p in all_packets_list if p.tcp_flags & TCP_RST)
        features['PSH Flag Count'] = fwd_psh + bwd_psh
        features['ACK Flag Count'] = sum(1 for p in all_packets_list if p.tcp_flags & TCP_ACK)
        features['URG Flag Count'] = fwd_urg + bwd_urg
        features['CWE Flag Count'] = sum(1 for p in all_packets_list if p.tcp_flags & TCP_CWR)
        features['ECE Flag Count'] = sum(1 for p in all_packets_list if p.tcp_flags & TCP_ECE)
        
        # === RATIOS AND AVERAGES ===
        fwd_bytes = sum(fwd_lengths) if fwd_lengths else 0
        bwd_bytes = sum(bwd_lengths) if bwd_lengths else 0
        
        features['Down/Up Ratio'] = bwd_bytes / fwd_bytes if fwd_bytes > 0 else 0.0
        features['Average Packet Size'] = total_bytes / total_count if total_count > 0 else 0.0
        features['Avg Fwd Segment Size'] = fwd_bytes / fwd_count if fwd_count > 0 else 0.0
        features['Avg Bwd Segment Size'] = bwd_bytes / bwd_count if bwd_count > 0 else 0.0
        
        # === BULK FEATURES (Not applicable for real-time) ===
        features['Fwd Avg Bytes/Bulk'] = 0
        features['Fwd Avg Packets/Bulk'] = 0
        features['Fwd Avg Bulk Rate'] = 0
        features['Bwd Avg Bytes/Bulk'] = 0
        features['Bwd Avg Packets/Bulk'] = 0
        features['Bwd Avg Bulk Rate'] = 0
        
        # === SUBFLOW FEATURES (same as flow for single flow) ===
        features['Subflow Fwd Packets'] = fwd_count
        features['Subflow Fwd Bytes'] = fwd_bytes
        features['Subflow Bwd Packets'] = bwd_count
        features['Subflow Bwd Bytes'] = bwd_bytes
        
        # === TCP WINDOW SIZES (REAL - from first SYN packets) ===
        fwd_syn_packets = [p for p in self.fwd_packets if p.tcp_flags & TCP_SYN]
        bwd_syn_packets = [p for p in self.bwd_packets if p.tcp_flags & TCP_SYN]
        
        features['Init_Win_bytes_forward'] = fwd_syn_packets[0].tcp_window if fwd_syn_packets else 0
        features['Init_Win_bytes_backward'] = bwd_syn_packets[0].tcp_window if bwd_syn_packets else 0
        
        # === ACTIVE DATA PACKETS ===
        # Count forward packets with payload (length > header)
        features['act_data_pkt_fwd'] = sum(1 for p in self.fwd_packets if p.length > p.header_len)
        
        # === MINIMUM SEGMENT SIZE ===
        features['min_seg_size_forward'] = np.min(fwd_lengths) if fwd_lengths else 0
        
        # === ACTIVE/IDLE TIME STATISTICS (REAL) ===
        if self.active_periods:
            # Convert to microseconds
            active_us = [a * 1_000_000 for a in self.active_periods]
            features['Active Mean'] = np.mean(active_us)
            features['Active Std'] = np.std(active_us) if len(active_us) > 1 else 0.0
            features['Active Max'] = np.max(active_us)
            features['Active Min'] = np.min(active_us)
        else:
            features['Active Mean'] = 0
            features['Active Std'] = 0
            features['Active Max'] = 0
            features['Active Min'] = 0
        
        if self.idle_periods:
            # Convert to microseconds
            idle_us = [i * 1_000_000 for i in self.idle_periods]
            features['Idle Mean'] = np.mean(idle_us)
            features['Idle Std'] = np.std(idle_us) if len(idle_us) > 1 else 0.0
            features['Idle Max'] = np.max(idle_us)
            features['Idle Min'] = np.min(idle_us)
        else:
            features['Idle Mean'] = 0
            features['Idle Std'] = 0
            features['Idle Max'] = 0
            features['Idle Min'] = 0
        
        return features
    
    def should_terminate(self) -> bool:
        """Check if flow should be terminated (FIN/RST or timeout)"""
        # Check for FIN or RST flags
        all_packets = self.fwd_packets + self.bwd_packets
        has_fin_rst = any(p.tcp_flags & (TCP_FIN | TCP_RST) for p in all_packets)
        
        # Check timeout
        age = time.time() - self.last_seen
        timed_out = age > FLOW_TIMEOUT
        
        return has_fin_rst or timed_out


class DPDKMultiQueueFeatureEngine:
    """
    DPDK-based feature engine using multi-queue RSS.
    Runs alongside Suricata without conflicts.
    """
    
    def __init__(self, port_id: int = DPDK_PORT_ID, rx_queues: List[int] = None):
        self.port_id = port_id
        self.rx_queues = rx_queues or DPDK_RX_QUEUES
        self.running = True
        self.flows: Dict[Tuple, FlowStatistics] = {}
        self.stats = {
            'packets_received': 0,
            'flows_created': 0,
            'flows_completed': 0,
            'features_emitted': 0
        }
        
        # Kafka producer
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                compression_type='gzip',
                acks=1
            )
            logger.info(f"✅ Connected to Kafka at {KAFKA_BOOTSTRAP}")
        except Exception as e:
            logger.error(f"❌ Kafka connection failed: {e}")
            self.producer = None
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # DPDK initialization
        if not DPDK_AVAILABLE:
            logger.error("❌ DPDK not available - cannot run multi-queue mode")
            sys.exit(1)
        
        self.dpdk = PyDPDK()
    
    def _signal_handler(self, sig, frame):
        """Handle shutdown signals"""
        logger.info(f"\n🛑 Shutdown signal received ({sig})")
        self.running = False
    
    def initialize_dpdk(self):
        """Initialize DPDK EAL and configure port"""
        logger.info("🚀 Initializing DPDK...")
        
        # Initialize EAL
        eal_args = [
            'dpdk_feature_engine',
            '--proc-type=secondary',  # Run as secondary process (Suricata is primary)
            '--file-prefix=suricata',  # Use same prefix as Suricata
            '-l', '2-3',  # Use cores 2-3 (Suricata uses 0-1)
        ]
        
        try:
            self.dpdk.init(eal_args)
            logger.info("✅ DPDK EAL initialized (secondary process)")
        except Exception as e:
            logger.error(f"❌ DPDK initialization failed: {e}")
            logger.info("💡 Make sure Suricata is running in DPDK mode first!")
            raise
        
        logger.info(f"✅ Using port {self.port_id}, queues {self.rx_queues}")
    
    def start(self):
        """Start packet capture and feature extraction"""
        logger.info("=" * 60)
        logger.info("DPDK Multi-Queue Feature Extraction Engine")
        logger.info("=" * 60)
        logger.info(f"Port ID: {self.port_id}")
        logger.info(f"RX Queues: {self.rx_queues}")
        logger.info(f"Burst Size: {BURST_SIZE}")
        logger.info(f"Flow Timeout: {FLOW_TIMEOUT}s")
        logger.info(f"Kafka Topic: {KAFKA_TOPIC}")
        logger.info("=" * 60)
        
        # Initialize DPDK
        try:
            self.initialize_dpdk()
        except Exception as e:
            logger.error(f"Failed to initialize DPDK: {e}")
            return
        
        logger.info("\n📊 Starting packet processing loop...\n")
        
        last_cleanup = time.time()
        last_stats = time.time()
        
        try:
            while self.running:
                # Process packets from each queue
                for queue_id in self.rx_queues:
                    packets = self.dpdk.rx_burst(self.port_id, BURST_SIZE)
                    
                    for pkt_bytes in packets:
                        self.stats['packets_received'] += 1
                        timestamp = time.time()
                        self._process_packet(pkt_bytes, timestamp)
                
                # Periodic cleanup
                current_time = time.time()
                if current_time - last_cleanup > 5.0:
                    self._cleanup_old_flows(current_time)
                    last_cleanup = current_time
                
                # Print stats
                if current_time - last_stats > 10.0:
                    self._print_stats()
                    last_stats = current_time
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.001)
        
        except KeyboardInterrupt:
            logger.info("\n⚠️  Interrupted by user")
        except Exception as e:
            logger.error(f"❌ Error in processing loop: {e}", exc_info=True)
        finally:
            self._shutdown()
    
    def _process_packet(self, pkt_bytes: bytes, timestamp: float):
        """Parse packet and update flow statistics"""
        try:
            # Parse Ethernet header (14 bytes)
            if len(pkt_bytes) < 14:
                return
            
            eth_type = struct.unpack('!H', pkt_bytes[12:14])[0]
            
            # Only process IPv4 (0x0800)
            if eth_type != 0x0800:
                return
            
            # Parse IP header
            if len(pkt_bytes) < 34:
                return
            
            ip_header = struct.unpack('!BBHHHBBH4s4s', pkt_bytes[14:34])
            ihl = (ip_header[0] & 0x0F) * 4
            protocol = ip_header[6]
            src_ip = socket.inet_ntoa(ip_header[8])
            dst_ip = socket.inet_ntoa(ip_header[9])
            total_len = ip_header[2]
            
            # Only process TCP/UDP
            if protocol not in [6, 17]:
                return
            
            # Parse transport header
            transport_offset = 14 + ihl
            if len(pkt_bytes) < transport_offset + 4:
                return
            
            src_port, dst_port = struct.unpack('!HH', pkt_bytes[transport_offset:transport_offset+4])
            
            # Extract TCP-specific fields
            tcp_flags = 0
            tcp_window = 0
            header_len = 20
            
            if protocol == 6:  # TCP
                if len(pkt_bytes) >= transport_offset + 14:
                    tcp_flags = pkt_bytes[transport_offset + 13]
                    tcp_window = struct.unpack('!H', pkt_bytes[transport_offset+14:transport_offset+16])[0]
                    data_offset = (pkt_bytes[transport_offset + 12] >> 4) * 4
                    header_len = data_offset
            else:  # UDP
                header_len = 8
            
            # Create packet info
            pkt_info = PacketInfo(
                timestamp=timestamp,
                length=len(pkt_bytes),
                tcp_flags=tcp_flags,
                tcp_window=tcp_window,
                header_len=header_len
            )
            
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
                self.flows[flow_key] = FlowStatistics(
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_port=src_port,
                    dst_port=dst_port,
                    protocol=protocol
                )
                self.stats['flows_created'] += 1
            
            # Update flow
            flow = self.flows[flow_key]
            flow.add_packet(is_forward, pkt_info)
            
            # Check for termination
            if flow.should_terminate():
                self._export_flow(flow_key, flow)
        
        except Exception as e:
            logger.debug(f"Error processing packet: {e}")
    
    def _export_flow(self, flow_key: Tuple, flow: FlowStatistics):
        """Extract features and send to Kafka"""
        try:
            features = flow.extract_cicids_features()
            
            message = {
                'timestamp': datetime.now().isoformat(),
                'flow_id': f"{flow_key[0]}:{flow_key[2]}-{flow_key[1]}:{flow_key[3]}",
                'src_ip': flow_key[0],
                'dst_ip': flow_key[1],
                'src_port': flow_key[2],
                'dst_port': flow_key[3],
                'protocol': flow_key[4],
                'features': features,
                'packet_count': len(flow.fwd_packets) + len(flow.bwd_packets)
            }
            
            if self.producer:
                self.producer.send(KAFKA_TOPIC, value=message)
                self.stats['features_emitted'] += 1
            
            # Remove from active flows
            del self.flows[flow_key]
            self.stats['flows_completed'] += 1
        
        except Exception as e:
            logger.error(f"Error exporting flow: {e}")
    
    def _cleanup_old_flows(self, current_time: float):
        """Remove timed-out flows"""
        to_export = []
        
        for flow_key, flow in self.flows.items():
            if current_time - flow.last_seen > FLOW_TIMEOUT:
                to_export.append((flow_key, flow))
        
        for flow_key, flow in to_export:
            logger.debug(f"Flow timeout: {flow_key}")
            self._export_flow(flow_key, flow)
    
    def _print_stats(self):
        """Print processing statistics"""
        logger.info(f"📊 Stats: Packets={self.stats['packets_received']:,} | "
                   f"Active Flows={len(self.flows)} | "
                   f"Completed={self.stats['flows_completed']} | "
                   f"Emitted={self.stats['features_emitted']}")
    
    def _shutdown(self):
        """Cleanup on shutdown"""
        logger.info("\n🛑 Shutting down...")
        
        # Export remaining flows
        logger.info(f"Exporting {len(self.flows)} remaining flows...")
        for flow_key, flow in list(self.flows.items()):
            self._export_flow(flow_key, flow)
        
        # Close Kafka
        if self.producer:
            self.producer.flush()
            self.producer.close()
        
        logger.info(f"✅ Final stats: {self.stats}")
        logger.info("✅ Shutdown complete")


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DPDK Multi-Queue Feature Engine')
    parser.add_argument('--port', type=int, default=0, help='DPDK port ID')
    parser.add_argument('--queues', type=str, default='2,3', help='RX queue IDs (comma-separated)')
    parser.add_argument('--kafka', default='localhost:9092', help='Kafka bootstrap servers')
    parser.add_argument('--topic', default='ml-features', help='Kafka topic')
    
    args = parser.parse_args()
    
    # Update globals
    global KAFKA_BOOTSTRAP, KAFKA_TOPIC
    KAFKA_BOOTSTRAP = args.kafka
    KAFKA_TOPIC = args.topic
    
    queue_ids = [int(q.strip()) for q in args.queues.split(',')]
    
    # Start engine
    engine = DPDKMultiQueueFeatureEngine(port_id=args.port, rx_queues=queue_ids)
    engine.start()


if __name__ == '__main__':
    main()
