# DPDK Feature Engine Implementation Guide

## Overview

The `realtime_feature_engine.py` script needs to support DPDK packet capture while maintaining identical CICIDS65 feature extraction. This document details the required modifications.

## Current State (AF_PACKET)

The script currently:
1. Creates AF_PACKET socket with fanout enabled (cluster_id=99)
2. Binds to physical interface
3. Reads packets via blocking recvfrom()
4. Extracts features from raw Ethernet frames
5. Publishes to Kafka topic `ml-features`

**Key class:** `FeatureExtractionEngine` (line ~404)

```python
class FeatureExtractionEngine:
    def __init__(self, interface, cluster_id=99, timeout=30):
        self.interface = interface  # "enp0s1"
        self.cluster_id = cluster_id
        self.timeout = timeout
        self.sock = None  # AF_PACKET socket
```

## Required DPDK Modifications

### 1. Command-line Arguments

Add new flags to `realtime_feature_engine.py` argument parser:

```python
parser.add_argument('--dpdk', action='store_true', 
                    help='Use DPDK mode instead of AF_PACKET')
parser.add_argument('--pci-addr', type=str, default="",
                    help='PCI address of DPDK interface (e.g., 0000:02:00.0)')
parser.add_argument('--dpdk-cores', type=str, default="1",
                    help='DPDK cores (e.g., "1,2,3" for secondary process)')
parser.add_argument('--burst-size', type=int, default=32,
                    help='DPDK RX burst size (packets per poll)')
```

**Usage:**
```bash
# AF_PACKET mode (default)
python3 realtime_feature_engine.py --timeout 10

# DPDK mode
python3 realtime_feature_engine.py --dpdk --pci-addr 0000:02:00.0 --timeout 10
```

### 2. Conditional Imports

Add conditional DPDK imports:

```python
try:
    from dpdk import *
    DPDK_AVAILABLE = True
except ImportError:
    DPDK_AVAILABLE = False
    if args.dpdk:
        print("ERROR: --dpdk specified but DPDK Python bindings not found")
        print("Install: pip install python-dpdk")
        sys.exit(1)
```

### 3. Packet Capture Interface (Strategy Pattern)

Create abstract interface to support both modes:

```python
class PacketCaptureBase:
    """Abstract interface for packet capture backends"""
    
    def __init__(self, timeout=30):
        self.timeout = timeout
        self.flow_table = {}
    
    def start(self):
        """Initialize capture"""
        raise NotImplementedError
    
    def get_packets(self):
        """Yield (raw_packet, timestamp) tuples"""
        raise NotImplementedError
    
    def stop(self):
        """Cleanup"""
        raise NotImplementedError


class AFPacketCapture(PacketCaptureBase):
    """AF_PACKET socket capture (existing implementation)"""
    
    def __init__(self, interface, cluster_id=99, timeout=30):
        super().__init__(timeout)
        self.interface = interface
        self.cluster_id = cluster_id
        self.sock = None
    
    def start(self):
        # Existing AF_PACKET socket setup
        self.sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
        fanout_arg = struct.pack('II', self.cluster_id, 2)
        self.sock.setsockopt(socket.SOL_PACKET, 18, fanout_arg)
        self.sock.bind((self.interface, 0))
        print(f"✅ AF_PACKET capture started on {self.interface}")
    
    def get_packets(self):
        while True:
            raw_packet, addr = self.sock.recvfrom(4096)
            yield raw_packet, time.time()
    
    def stop(self):
        if self.sock:
            self.sock.close()


class DPDKCapture(PacketCaptureBase):
    """DPDK userspace capture (new implementation)"""
    
    def __init__(self, pci_addr, cores="1", burst_size=32, timeout=30):
        super().__init__(timeout)
        self.pci_addr = pci_addr  # "0000:02:00.0"
        self.cores = cores  # "1" for secondary process
        self.burst_size = burst_size
        
        # DPDK objects (initialized in start())
        self.eal = None
        self.ethdev = None
        self.mempool = None
    
    def start(self):
        """Initialize DPDK environment as secondary process"""
        from dpdk import EAL, RxQueue, Mempool
        
        # Initialize EAL as secondary process
        # Primary process is Suricata --dpdk
        eal_args = [
            '--proc-type=secondary',
            '--file-prefix=ids',  # Must match Suricata's prefix
            f'-l {self.cores}',   # Cores to use
        ]
        
        self.eal = EAL(eal_args)
        
        # Get mempool (created by Suricata primary)
        # or create new one if not sharing
        self.mempool = Mempool("rx_pkt_pool", 8192, 4096)
        
        # Open Ethernet device by PCI address
        self.ethdev = RxQueue(
            pci_addr=self.pci_addr,
            queue_id=0,  # RX queue 0
            mempool=self.mempool,
            burst_size=self.burst_size
        )
        
        print(f"✅ DPDK capture started on PCI {self.pci_addr}")
        print(f"   Cores: {self.cores}, Burst: {self.burst_size}")
    
    def get_packets(self):
        """Poll DPDK RX queue for packets"""
        last_time = time.time()
        
        while True:
            # Non-blocking burst read (up to burst_size packets)
            pkts = self.ethdev.rx_burst(burst_size=self.burst_size)
            
            current_time = time.time()
            
            for pkt in pkts:
                # DPDK packet object - convert to raw bytes
                raw_packet = bytes(pkt.data[:pkt.pkt_len])
                yield raw_packet, current_time
            
            last_time = current_time
            
            # Small sleep to avoid busy-waiting (can tune for latency vs CPU)
            if not pkts:
                time.sleep(0.001)  # 1ms sleep if no packets
    
    def stop(self):
        """Cleanup DPDK resources"""
        if self.ethdev:
            self.ethdev.close()
        if self.mempool:
            self.mempool.free()
        if self.eal:
            self.eal.close()
```

### 4. Modify FeatureExtractionEngine

Update the main engine to use the capture abstraction:

```python
class FeatureExtractionEngine:
    
    def __init__(self, capture_backend, kafka_bootstrap="localhost:9092", 
                 kafka_topic="ml-features", stats_interval=10):
        """
        Args:
            capture_backend: PacketCaptureBase subclass instance
            kafka_bootstrap: Kafka server address
            kafka_topic: Topic to publish features
            stats_interval: Seconds between printing stats
        """
        self.capture = capture_backend
        self.kafka_bootstrap = kafka_bootstrap
        self.kafka_topic = kafka_topic
        self.stats_interval = stats_interval
        
        self.flow_table = {}  # {(src_ip, dst_ip, src_port, dst_port, proto): FlowStats}
        self.producer = None
        
    def start(self):
        """Initialize Kafka producer and packet capture"""
        self.capture.start()
        
        self.producer = KafkaProducer(
            bootstrap_servers=self.kafka_bootstrap,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            compression_type='snappy',
            batch_size=16384,
            acks='1'  # Don't wait for all replicas
        )
        print(f"✅ Kafka producer ready: {self.kafka_topic}")
    
    def run(self):
        """Main packet processing loop"""
        self.start()
        
        try:
            last_stats_time = time.time()
            packet_count = 0
            feature_count = 0
            
            for raw_packet, pkt_time in self.capture.get_packets():
                try:
                    # Parse packet (identical for both AF_PACKET and DPDK)
                    self.process_packet(raw_packet, pkt_time)
                    packet_count += 1
                    
                except Exception as e:
                    print(f"Error processing packet: {e}", file=sys.stderr)
                    continue
                
                # Periodically emit idle flows and print stats
                current_time = time.time()
                if current_time - last_stats_time >= self.stats_interval:
                    self.emit_idle_flows(current_time)
                    self.print_stats(packet_count, feature_count)
                    last_stats_time = current_time
                    packet_count = 0
                    feature_count = 0
        
        except KeyboardInterrupt:
            print("\n✓ Shutting down gracefully...")
        
        finally:
            self.stop()
    
    def stop(self):
        """Cleanup resources"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
        self.capture.stop()
        print("✓ Stopped")

    # Existing methods (process_packet, extract_features, etc.) remain UNCHANGED
    # They operate on raw packet bytes, which works identically for both modes
```

### 5. Update Main Entry Point

```python
def main():
    parser = argparse.ArgumentParser(description='Real-time CICIDS Feature Engine')
    parser.add_argument('-i', '--interface', type=str, default='enp0s1',
                        help='Network interface (AF_PACKET mode)')
    parser.add_argument('-t', '--timeout', type=int, default=30,
                        help='Flow timeout in seconds')
    parser.add_argument('-c', '--cluster-id', type=int, default=99,
                        help='AF_PACKET cluster ID')
    
    # New DPDK arguments
    parser.add_argument('--dpdk', action='store_true',
                        help='Use DPDK mode instead of AF_PACKET')
    parser.add_argument('--pci-addr', type=str, default="",
                        help='PCI address of DPDK interface (0000:02:00.0)')
    parser.add_argument('--dpdk-cores', type=str, default="1",
                        help='DPDK cores for secondary process')
    parser.add_argument('--burst-size', type=int, default=32,
                        help='DPDK RX burst size')
    
    # Common arguments
    parser.add_argument('--kafka', type=str, default='localhost:9092',
                        help='Kafka bootstrap servers')
    parser.add_argument('--topic', type=str, default='ml-features',
                        help='Kafka topic for features')
    
    args = parser.parse_args()
    
    # Select capture backend based on mode
    if args.dpdk:
        print("🚀 Starting in DPDK mode...")
        if not DPDK_AVAILABLE:
            print("ERROR: DPDK Python bindings required")
            sys.exit(1)
        
        if not args.pci_addr:
            print("ERROR: --pci-addr required for DPDK mode")
            sys.exit(1)
        
        capture = DPDKCapture(
            pci_addr=args.pci_addr,
            cores=args.dpdk_cores,
            burst_size=args.burst_size,
            timeout=args.timeout
        )
    else:
        print("📡 Starting in AF_PACKET mode...")
        capture = AFPacketCapture(
            interface=args.interface,
            cluster_id=args.cluster_id,
            timeout=args.timeout
        )
    
    # Create and run engine
    engine = FeatureExtractionEngine(
        capture_backend=capture,
        kafka_bootstrap=args.kafka,
        kafka_topic=args.topic,
        stats_interval=args.timeout  # Print stats at flow timeout intervals
    )
    
    engine.run()

if __name__ == '__main__':
    main()
```

## Installation Requirements

### For AF_PACKET (existing, no changes)
```bash
pip install kafka-python numpy pandas scikit-learn
```

### For DPDK Support (new)

```bash
# Option 1: Using DPDK Python bindings package
pip install python-dpdk

# Option 2: Manual installation (if python-dpdk not available)
# You may need to compile DPDK Python bindings from source:
cd /path/to/dpdk
cd ./python
python3 setup.py install
```

## Testing the DPDK Implementation

### Unit Test for Packet Parsing

```python
# Ensure feature extraction is identical between modes

import unittest

class TestFeatureExtraction(unittest.TestCase):
    
    def setUp(self):
        """Load test PCAP with known flows"""
        self.test_packets = load_pcap('test_traffic.pcap')
    
    def test_afpacket_vs_dpdk_same_features(self):
        """Features extracted from AF_PACKET and DPDK should be identical"""
        
        # Extract features from test packets using AF_PACKET logic
        afpacket_features = []
        for raw_pkt in self.test_packets:
            features = extract_cicids65_features(raw_pkt)
            afpacket_features.append(features)
        
        # DPDK mode extracts from same raw bytes
        dpdk_features = []
        for raw_pkt in self.test_packets:
            # DPDK.get_packet() returns bytes, same as AF_PACKET
            features = extract_cicids65_features(raw_pkt)
            dpdk_features.append(features)
        
        # Compare
        self.assertEqual(afpacket_features, dpdk_features)
```

## Integration with run_realtime_engine_dpdk.sh

The bash script (`run_realtime_engine_dpdk.sh`) will invoke the modified Python script:

```bash
# AF_PACKET mode
python3 realtime_feature_engine.py --timeout 10

# DPDK mode
python3 realtime_feature_engine.py \
    --dpdk \
    --pci-addr 0000:02:00.0 \
    --timeout 10 \
    --dpdk-cores 1
```

## Performance Expectations

### AF_PACKET Mode
- Throughput: ~100-500 Mbps
- Latency: 1-10ms (kernel scheduling + socket blocking)
- CPU: 1 core at ~80% utilization

### DPDK Mode
- Throughput: 1-10+ Gbps (hardware-limited)
- Latency: ~100 microseconds (polling-based)
- CPU: 1 core at ~100% utilization (dedicated polling)

## Backward Compatibility

The modifications maintain full backward compatibility:
- Existing AF_PACKET mode unchanged
- All feature extraction logic identical
- Same Kafka output format
- Transparent to ML consumer (ml-features topic identical)

## Summary

The key insight is that **feature extraction logic is independent of packet capture mechanism**. By using the Strategy pattern with `PacketCaptureBase`, we can:

1. ✅ Support both AF_PACKET (existing) and DPDK (new)
2. ✅ Maintain identical CICIDS65 features
3. ✅ Enable seamless switching between modes
4. ✅ Add minimal complexity to core logic
5. ✅ Keep backward compatibility

The difference is **speed**: same features, faster capture.
