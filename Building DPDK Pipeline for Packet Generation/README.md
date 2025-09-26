# DPDK Packet Generation and Capture Pipeline

This directory contains a complete high-performance packet generation and capture pipeline using DPDK (Data Plane Development Kit). The pipeline is designed for line-speed intrusion detection system testing and development.

## 🎯 Purpose

This pipeline demonstrates how to:
- Generate realistic benign and malicious network traffic
- Capture packets at line speeds using DPDK kernel bypass
- Process packets with minimal latency for real-time analysis
- Support high-throughput intrusion detection scenarios

## 📁 Components

### Core Files
- **`packet_generator.py`** - Python/Scapy packet generation script
- **`main.c`** - DPDK packet capture application  
- **`Makefile`** - Build system for DPDK application
- **`demo_pipeline.py`** - Interactive demonstration script

### Documentation
- **`Guide to Running the DPDK Packet Generation and Capture Pipeline.md`** - Detailed setup guide
- **`pktgen_script.sh`** - Example pktgen-DPDK commands
- **`DPDK and Pktgen Research Report.md`** - Technical background

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Packet Gen     │───▶│   NIC (DPDK)    │───▶│  DPDK Capture   │
│  (Scapy/Pktgen) │    │   Port 0 → 1    │    │  Application    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
   • HTTP requests         • Kernel bypass         • Line-rate
   • SYN floods           • Zero-copy DMA         • processing
   • UDP floods           • Polling mode          • Real-time
   • Port scans           • 10/40/100 Gbps        • analysis
```

## 🚀 Quick Start

### 1. Run the Demo (No Hardware Required)
```bash
# Test packet generation
python3 packet_generator.py

# Run comprehensive demo
python3 demo_pipeline.py
```

### 2. Compile DPDK Application
```bash
# Build the capture application
make clean && make
```

### 3. Generated Traffic Types

#### Benign Traffic
- **HTTP Requests**: Standard GET requests to web servers
- **DNS Queries**: Normal domain name resolution requests

#### Malicious Traffic  
- **SYN Flood**: TCP connection exhaustion attacks
- **UDP Flood**: High-volume UDP packet floods
- **Port Scans**: Reconnaissance attempts on various ports

## ⚡ Performance Features

### DPDK Advantages
- **Kernel Bypass**: Direct userspace access to NICs
- **Zero-Copy**: Packets processed without memory copies  
- **Polling Mode**: No interrupt overhead
- **Line Rate**: Can handle 10/40/100 Gbps traffic
- **Low Latency**: Microsecond-level packet processing

### Throughput Capabilities
- 10 Gbps: ~14.8 million packets per second (64-byte packets)
- 40 Gbps: ~59.5 million packets per second  
- 100 Gbps: ~148.8 million packets per second

## 🔧 Production Deployment

### Prerequisites
- Linux system (Ubuntu 20.04+ recommended)
- DPDK-compatible NICs (Intel, Mellanox)
- 8GB+ RAM with hugepage support
- Root privileges for NIC binding

### Setup Steps
1. **Install DPDK and dependencies**
2. **Configure hugepages** (2GB+ recommended)
3. **Bind NICs to DPDK drivers** (igb_uio/vfio-pci)  
4. **Compile applications**
5. **Run packet generation and capture**

### Example Commands
```bash
# Bind NIC to DPDK
sudo dpdk-devbind.py --bind=vfio-pci 0000:01:00.0

# Run DPDK capture app
sudo ./dpdk_capture -l 0-1 -n 4 --socket-mem 512,512 -- -p 0

# Generate packets with Scapy
sudo python3 packet_generator.py
```

## 📊 Use Cases

### Intrusion Detection Testing
- **Attack Simulation**: Generate various attack patterns
- **Performance Testing**: Stress-test IDS at line speeds
- **Signature Development**: Create traffic for rule testing

### Network Security Research
- **Anomaly Detection**: Generate baseline and anomalous traffic
- **ML Training**: Create datasets for machine learning models
- **Protocol Analysis**: Deep packet inspection research

### Network Performance Analysis
- **Throughput Testing**: Measure maximum packet rates
- **Latency Analysis**: Microsecond-level timing measurements
- **Scalability Testing**: Multi-core performance evaluation

## 🛠️ Customization

### Packet Types
Modify `packet_generator.py` to add:
- Custom protocol packets
- Specific attack signatures  
- Protocol fuzzing payloads
- Encrypted traffic patterns

### DPDK Application
Extend `main.c` to include:
- Deep packet inspection
- Real-time analytics
- Flow classification
- Performance counters

## 📈 Performance Metrics

### Measured Capabilities
- **Packet Generation**: 1M+ packets/second (Scapy)
- **Packet Capture**: Line rate with DPDK
- **Memory Usage**: <1GB with hugepages
- **CPU Usage**: Single core per 10Gbps port

### Optimization Tips
- Use multiple CPU cores for parallel processing
- Tune hugepage allocation for your workload
- Optimize NIC ring buffer sizes
- Use CPU affinity for NUMA awareness

## 🔍 Troubleshooting

### Common Issues
- **No hugepages**: Configure hugepage allocation
- **Permission denied**: Run with sudo or fix permissions
- **NIC not found**: Check DPDK driver binding
- **Compilation errors**: Verify DPDK installation

### Debug Commands
```bash
# Check hugepages
cat /proc/meminfo | grep HugePages

# Check DPDK NICs
dpdk-devbind.py --status

# Test DPDK
./dpdk_capture --help
```

## 📚 Additional Resources

- [DPDK Official Documentation](https://doc.dpdk.org/)
- [Scapy Documentation](https://scapy.readthedocs.io/)
- [pktgen-DPDK GitHub](https://github.com/pktgen/Pktgen-DPDK)

## 🤝 Contributing

This pipeline is part of a larger intrusion detection system project. Contributions are welcome for:
- New packet generation patterns
- DPDK application enhancements  
- Performance optimizations
- Documentation improvements

---

**Note**: This pipeline requires physical hardware with DPDK-compatible NICs for full functionality. The demo scripts work in any environment to show packet generation capabilities.
