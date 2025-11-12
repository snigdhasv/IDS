#!/usr/bin/env python3
"""
PCAP Replay for Accuracy Testing

Replays PCAP files through DPDK pipeline to test accuracy on known datasets.

Supports:
- CICIDS2017, CICIDS2018, CICIDS2019, CICIDS2020
- KDD99, NSL-KDD
- Custom labeled PCAP files

Usage:
    # Replay entire dataset
    python3 replay_pcap_for_testing.py \
        --pcap-file cicids2017.pcap \
        --ground-truth cicids2017_labels.csv \
        --output predictions.csv

    # Replay with speed control
    python3 replay_pcap_for_testing.py \
        --pcap-file dataset.pcap \
        --speed 0.5 \
        --ground-truth labels.csv

    # Inject packets at real-time speed
    python3 replay_pcap_for_testing.py \
        --pcap-file dataset.pcap \
        --real-time
"""

import argparse
import csv
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    import dpkt
    from dpkt.compat import compat_ord
except ImportError:
    print("❌ dpkt not found. Install with: pip install dpkt")
    sys.exit(1)

try:
    from kafka import KafkaProducer
except ImportError:
    print("❌ kafka-python not found. Install with: pip install kafka-python")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Kafka config
KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "pcap-data"  # Raw packets from PCAP


@dataclass
class PacketMetadata:
    """Metadata extracted from packet"""
    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    payload_len: int
    flags: str = ""
    ground_truth: Optional[str] = None


class PCAPReplayer:
    """Replay PCAP files with optional speed control and ground truth labeling"""
    
    def __init__(self, pcap_file: str, speed: float = 1.0, real_time: bool = False,
                 ground_truth_file: Optional[str] = None):
        self.pcap_file = Path(pcap_file)
        self.speed = speed
        self.real_time = real_time
        self.ground_truth = {}
        self.kafka_producer = None
        
        # Validate PCAP file
        if not self.pcap_file.exists():
            raise FileNotFoundError(f"PCAP file not found: {pcap_file}")
        
        logger.info(f"📁 PCAP file: {pcap_file}")
        logger.info(f"📊 Size: {self.pcap_file.stat().st_size / 1024 / 1024:.2f} MB")
        
        # Load ground truth if provided
        if ground_truth_file:
            self._load_ground_truth(ground_truth_file)
        
        # Initialize Kafka producer
        self._init_kafka()
    
    def _init_kafka(self):
        """Initialize Kafka producer"""
        try:
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3
            )
            logger.info(f"✓ Connected to Kafka: {KAFKA_BOOTSTRAP}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Kafka: {e}")
            raise
    
    def _load_ground_truth(self, gt_file: str):
        """Load ground truth labels from CSV
        
        Expected CSV format (one of):
        1. flow_id, label
        2. src_ip, dst_ip, src_port, dst_port, label
        3. src_ip, dst_ip, protocol, label
        """
        try:
            with open(gt_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Try different key formats
                    if 'flow_id' in row:
                        key = row['flow_id']
                    elif all(k in row for k in ['src_ip', 'dst_ip', 'src_port', 'dst_port']):
                        key = f"{row['src_ip']}:{row['src_port']}-{row['dst_ip']}:{row['dst_port']}"
                    elif all(k in row for k in ['src_ip', 'dst_ip', 'protocol']):
                        key = f"{row['src_ip']}-{row['dst_ip']}-{row['protocol']}"
                    else:
                        continue
                    
                    label = row.get('label', row.get('class', row.get('Label', '')))
                    self.ground_truth[key] = label.strip()
            
            logger.info(f"✓ Loaded {len(self.ground_truth)} ground truth labels")
        except Exception as e:
            logger.warning(f"⚠️  Failed to load ground truth: {e}")
    
    def _get_ground_truth(self, metadata: PacketMetadata) -> Optional[str]:
        """Retrieve ground truth label for packet"""
        if not self.ground_truth:
            return None
        
        # Try multiple key formats
        keys_to_try = [
            f"{metadata.src_ip}:{metadata.src_port}-{metadata.dst_ip}:{metadata.dst_port}",
            f"{metadata.src_ip}-{metadata.dst_ip}-{metadata.protocol}",
            f"{metadata.src_ip}/{metadata.dst_ip}",
        ]
        
        for key in keys_to_try:
            if key in self.ground_truth:
                return self.ground_truth[key]
        
        return None
    
    def _parse_packet(self, timestamp: float, data: bytes) -> Optional[PacketMetadata]:
        """Parse packet with dpkt"""
        try:
            eth = dpkt.ethernet.Ethernet(data)
            
            # Only handle IP packets
            if not isinstance(eth.data, (dpkt.ip.IP, dpkt.ip6.IP6)):
                return None
            
            ip = eth.data
            
            # Get IP addresses
            src_ip = self._format_ip(ip.src)
            dst_ip = self._format_ip(ip.dst)
            
            # Get transport layer info
            protocol = self._get_protocol_name(ip.p)
            src_port = 0
            dst_port = 0
            flags = ""
            
            if isinstance(ip.data, dpkt.tcp.TCP):
                src_port = ip.data.sport
                dst_port = ip.data.dport
                flags = self._parse_tcp_flags(ip.data.flags)
            elif isinstance(ip.data, dpkt.udp.UDP):
                src_port = ip.data.sport
                dst_port = ip.data.dport
            elif isinstance(ip.data, dpkt.icmp.ICMP):
                protocol = f"ICMP-{ip.data.type}"
            
            payload_len = len(ip.data.data) if hasattr(ip.data, 'data') else 0
            
            metadata = PacketMetadata(
                timestamp=timestamp,
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_port=src_port,
                dst_port=dst_port,
                protocol=protocol,
                payload_len=payload_len,
                flags=flags
            )
            
            # Enrich with ground truth
            metadata.ground_truth = self._get_ground_truth(metadata)
            
            return metadata
        
        except Exception as e:
            logger.debug(f"Failed to parse packet: {e}")
            return None
    
    @staticmethod
    def _format_ip(ip_bytes: bytes) -> str:
        """Format IP address bytes to string"""
        return '.'.join(map(str, ip_bytes))
    
    @staticmethod
    def _get_protocol_name(protocol_num: int) -> str:
        """Get protocol name from number"""
        protocol_names = {
            1: "ICMP",
            6: "TCP",
            17: "UDP",
        }
        return protocol_names.get(protocol_num, f"P{protocol_num}")
    
    @staticmethod
    def _parse_tcp_flags(flags: int) -> str:
        """Parse TCP flags"""
        flag_names = []
        if flags & dpkt.tcp.TH_FIN:
            flag_names.append('FIN')
        if flags & dpkt.tcp.TH_SYN:
            flag_names.append('SYN')
        if flags & dpkt.tcp.TH_RST:
            flag_names.append('RST')
        if flags & dpkt.tcp.TH_PUSH:
            flag_names.append('PUSH')
        if flags & dpkt.tcp.TH_ACK:
            flag_names.append('ACK')
        if flags & dpkt.tcp.TH_URG:
            flag_names.append('URG')
        return ','.join(flag_names)
    
    def replay(self, max_packets: Optional[int] = None) -> Dict:
        """Replay PCAP file
        
        Args:
            max_packets: Max packets to send (None = all)
        
        Returns:
            Statistics dict
        """
        stats = {
            'total_packets': 0,
            'parsed_packets': 0,
            'sent_packets': 0,
            'skipped_packets': 0,
            'with_ground_truth': 0,
            'start_time': time.time(),
            'first_timestamp': None,
            'last_timestamp': None,
        }
        
        logger.info(f"\n🚀 Starting PCAP replay...")
        logger.info(f"   Speed factor: {self.speed}x")
        logger.info(f"   Real-time mode: {self.real_time}")
        if max_packets:
            logger.info(f"   Max packets: {max_packets}")
        logger.info("")
        
        try:
            with open(self.pcap_file, 'rb') as f:
                pcap = dpkt.pcap.Reader(f)
                
                last_pkt_time = None
                start_wall_time = time.time()
                
                for ts, buf in pcap:
                    stats['total_packets'] += 1
                    
                    # Limit to max packets
                    if max_packets and stats['parsed_packets'] >= max_packets:
                        break
                    
                    # Parse packet
                    metadata = self._parse_packet(ts, buf)
                    if not metadata:
                        stats['skipped_packets'] += 1
                        continue
                    
                    stats['parsed_packets'] += 1
                    if metadata.ground_truth:
                        stats['with_ground_truth'] += 1
                    
                    # Track timestamps
                    if stats['first_timestamp'] is None:
                        stats['first_timestamp'] = ts
                    stats['last_timestamp'] = ts
                    
                    # Respect timing if requested
                    if self.real_time and last_pkt_time is not None:
                        pkt_delay = ts - last_pkt_time
                        wall_delay = pkt_delay / self.speed
                        elapsed_wall = time.time() - start_wall_time
                        if elapsed_wall < (ts - stats['first_timestamp']) / self.speed:
                            sleep_time = ((ts - stats['first_timestamp']) / self.speed) - elapsed_wall
                            time.sleep(max(0, sleep_time))
                    
                    last_pkt_time = ts
                    
                    # Send to Kafka
                    try:
                        message = {
                            'timestamp': ts,
                            'src_ip': metadata.src_ip,
                            'dst_ip': metadata.dst_ip,
                            'src_port': metadata.src_port,
                            'dst_port': metadata.dst_port,
                            'protocol': metadata.protocol,
                            'payload_len': metadata.payload_len,
                            'tcp_flags': metadata.flags,
                            'ground_truth': metadata.ground_truth,
                        }
                        
                        self.kafka_producer.send(KAFKA_TOPIC, value=message)
                        stats['sent_packets'] += 1
                    
                    except Exception as e:
                        logger.error(f"❌ Failed to send packet {stats['parsed_packets']}: {e}")
                        continue
                    
                    # Log progress
                    if stats['sent_packets'] % 1000 == 0:
                        rate = stats['sent_packets'] / (time.time() - stats['start_time'])
                        logger.info(f"📊 Sent {stats['sent_packets']:8d} packets "
                                   f"({rate:8.0f} pps) | "
                                   f"With GT: {stats['with_ground_truth']:6d}")
        
        except KeyboardInterrupt:
            logger.info("\n⏹️  Stopped by user")
        except Exception as e:
            logger.error(f"❌ Error during replay: {e}")
        
        finally:
            if self.kafka_producer:
                self.kafka_producer.flush()
                self.kafka_producer.close()
        
        # Final stats
        elapsed = time.time() - stats['start_time']
        stats['elapsed_time'] = elapsed
        
        logger.info(f"\n✅ Replay complete!")
        logger.info(f"   Total packets in file: {stats['total_packets']}")
        logger.info(f"   Parsed packets: {stats['parsed_packets']}")
        logger.info(f"   Sent to Kafka: {stats['sent_packets']}")
        logger.info(f"   With ground truth: {stats['with_ground_truth']}")
        logger.info(f"   Skipped: {stats['skipped_packets']}")
        logger.info(f"   Elapsed time: {elapsed:.2f}s")
        if stats['sent_packets'] > 0:
            logger.info(f"   Throughput: {stats['sent_packets'] / elapsed:.0f} pps")
        
        if stats['first_timestamp'] and stats['last_timestamp']:
            pcap_duration = stats['last_timestamp'] - stats['first_timestamp']
            logger.info(f"   PCAP duration: {pcap_duration:.2f}s")
        
        return stats


def main():
    parser = argparse.ArgumentParser(
        description='Replay PCAP files for accuracy testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Replay with ground truth labels
  python3 replay_pcap_for_testing.py \\
      --pcap-file cicids2017.pcap \\
      --ground-truth cicids2017_labels.csv

  # Replay at 50% speed with timing preserved
  python3 replay_pcap_for_testing.py \\
      --pcap-file dataset.pcap \\
      --speed 0.5 \\
      --real-time

  # Replay first 10000 packets at real-time speed
  python3 replay_pcap_for_testing.py \\
      --pcap-file large_dataset.pcap \\
      --max-packets 10000 \\
      --real-time
        """
    )
    
    parser.add_argument('--pcap-file', type=str, required=True,
                       help='Path to PCAP file to replay')
    parser.add_argument('--ground-truth', type=str, default=None,
                       help='CSV file with ground truth labels')
    parser.add_argument('--speed', type=float, default=1.0,
                       help='Replay speed factor (1.0 = original timing, default: 1.0)')
    parser.add_argument('--real-time', action='store_true',
                       help='Preserve packet timing (slow down fast replays)')
    parser.add_argument('--max-packets', type=int, default=None,
                       help='Max packets to replay (default: all)')
    
    args = parser.parse_args()
    
    # Create replayer
    replayer = PCAPReplayer(
        pcap_file=args.pcap_file,
        speed=args.speed,
        real_time=args.real_time,
        ground_truth_file=args.ground_truth
    )
    
    # Replay
    stats = replayer.replay(max_packets=args.max_packets)
    
    # Exit with success/failure code
    sys.exit(0 if stats['sent_packets'] > 0 else 1)


if __name__ == '__main__':
    main()
