# 🚀 Real-time DPDK-Suricata-Kafka IDS Pipeline

## 📋 Overview

This is a complete **real-time intrusion detection system** that integrates:
- **DPDK** high-performance packet generation
- **Suricata** IDS for feature extraction and threat detection  
- **Kafka** streaming for real-time event processing
- **Real-time monitoring** and validation tools

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌──────────────────┐
│  DPDK Packet    │    │    Suricata      │    │   Kafka         │    │   Monitoring     │
│  Generation     ├───▶│  Feature         ├───▶│  Streaming      ├───▶│   & Analysis     │
│                 │    │  Extraction      │    │                 │    │                  │
│ • High rate     │    │ • Flow analysis  │    │ • Real-time     │    │ • Dashboard      │
│ • Attack sims   │    │ • Threat detect  │    │ • Event topics  │    │ • Metrics        │
│ • Normal traffic│    │ • Rule matching  │    │ • Scalability   │    │ • Alerts         │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └──────────────────┘
```

## 🔧 Quick Start

### 1. Complete System Setup
```bash
# Install DPDK environment and dependencies
sudo ./setup_realtime_dpdk.sh

# Ensure Kafka is running (from previous setup)
cd /home/ifscr/SE_02_2025/IDS/Suricata_Setup
./setup_kafka.sh
```

### 2. Validate Complete Pipeline
```bash
# Run comprehensive validation
sudo ./validate_complete_pipeline.sh
```

### 3. Start Real-time Demo
```bash
# Generate packets + monitor events (integrated demo)
sudo python3 realtime_dpdk_pipeline.py --mode demo --duration 120

# OR run components separately:

# Terminal 1: Start packet generation
sudo python3 realtime_dpdk_pipeline.py --mode generate --rate 100 --duration 300

# Terminal 2: Monitor events in real-time
python3 realtime_ids_monitor.py
```

## 📊 Core Components

### 🎯 Real-time DPDK Pipeline (`realtime_dpdk_pipeline.py`)
**High-performance packet generation and integration orchestrator**

**Features:**
- Multiple traffic patterns (HTTP, DNS, SSH, attacks)
- Configurable packet generation rates (1-10,000+ pps)
- Real-time Kafka event monitoring
- Integrated validation and testing
- Attack simulation for IDS testing

**Usage:**
```bash
# Generate packets at 500 pps for 60 seconds
sudo python3 realtime_dpdk_pipeline.py --mode generate --rate 500 --duration 60

# Monitor Kafka events only
python3 realtime_dpdk_pipeline.py --mode monitor --duration 120

# Quick validation test
sudo python3 realtime_dpdk_pipeline.py --mode validate

# Full integrated demo
sudo python3 realtime_dpdk_pipeline.py --mode demo --duration 180
```

### 📡 Real-time IDS Monitor (`realtime_ids_monitor.py`)
**Comprehensive monitoring dashboard for the entire pipeline**

**Features:**
- Live event statistics and rates
- Alert categorization and severity tracking
- System performance metrics (CPU, memory, I/O)
- Service status monitoring
- Real-time dashboard updates

**Dashboard Shows:**
- Event counts and rates (per minute)
- Security alerts by category and severity
- System performance (CPU, memory, network I/O)
- Service status (Suricata, Kafka)
- High-severity alert notifications

**Usage:**
```bash
python3 realtime_ids_monitor.py
```

### 🏗️ DPDK Setup (`setup_realtime_dpdk.sh`)
**Complete DPDK environment configuration**

**What it installs:**
- DPDK 24.07 with optimized build
- Hugepage configuration (1GB)
- Network interface binding utilities
- Python dependencies (scapy, kafka-python, psutil)
- High-performance packet generator
- System performance optimizations

**Usage:**
```bash
sudo ./setup_realtime_dpdk.sh
```

### ✅ Complete Pipeline Validator (`validate_complete_pipeline.sh`)
**End-to-end pipeline validation and testing**

**Validation phases:**
1. **System Prerequisites** - Root access, dependencies, interface
2. **Service Status** - Suricata, Kafka process checks
3. **Configuration** - Config files, log paths, interface setup
4. **Kafka Topics** - Topic existence and accessibility
5. **Real-time Test** - Live packet generation and event flow
6. **Results Analysis** - Event counts, performance metrics
7. **Integration Score** - Overall system health (0-100%)

**Usage:**
```bash
sudo ./validate_complete_pipeline.sh
```

## 🎮 Usage Scenarios

### Scenario 1: Development Testing
```bash
# Quick validation
sudo ./validate_complete_pipeline.sh

# Low-rate testing (good for development)
sudo python3 realtime_dpdk_pipeline.py --mode demo --duration 60
```

### Scenario 2: Performance Testing
```bash
# High-rate packet generation
sudo python3 realtime_dpdk_pipeline.py --mode generate --rate 2000 --duration 300

# Monitor system performance
python3 realtime_ids_monitor.py
```

### Scenario 3: Attack Simulation
```bash
# Generate attack patterns for IDS testing
sudo python3 realtime_dpdk_pipeline.py --mode generate --rate 50 --duration 600

# Monitor alerts in real-time
python3 realtime_ids_monitor.py
```

### Scenario 4: Long-term Monitoring
```bash
# Continuous monitoring
python3 realtime_ids_monitor.py

# Background packet generation
nohup sudo python3 realtime_dpdk_pipeline.py --mode generate --rate 100 --duration 3600 &
```

## 📈 Performance Characteristics

### Packet Generation Rates
- **Low rate**: 10-100 pps (development/testing)
- **Medium rate**: 100-1,000 pps (normal operation)  
- **High rate**: 1,000-10,000 pps (stress testing)
- **Max rate**: 10,000+ pps (DPDK optimized)

### System Requirements
- **CPU**: 2+ cores recommended for high rates
- **Memory**: 4GB+ (includes hugepages)
- **Network**: Gigabit+ for high-rate testing
- **Storage**: SSD recommended for log processing

## 🔍 Monitoring and Metrics

### Real-time Dashboard Metrics
- **Event Statistics**: Total events, alerts, flows
- **Rate Tracking**: Events per minute, alerts per minute
- **Alert Analysis**: Categories, severities, signatures  
- **System Performance**: CPU, memory, network I/O
- **Service Status**: Suricata, Kafka connectivity

### Event Types Tracked
- **Alerts**: Security threats and suspicious activity
- **Flows**: Network connection metadata
- **HTTP**: Web traffic analysis
- **DNS**: Domain name queries
- **Stats**: Suricata performance metrics

## 🚨 Alert Categories

The system detects and categorizes:
- **Port Scans**: Systematic port probing
- **Web Attacks**: SQL injection, XSS attempts
- **Malware**: Suspicious payloads and signatures
- **DDoS**: High-volume connection attempts
- **Protocol Violations**: Malformed packets
- **Custom Rules**: User-defined threat patterns

## 🔧 Configuration

### Key Configuration Files
- `realtime_dpdk_pipeline.py`: Packet generation patterns
- `realtime_ids_monitor.py`: Monitoring thresholds  
- `/etc/suricata/suricata.yaml`: Suricata IDS config
- `/home/ifscr/SE_02_2025/IDS/Suricata_Setup/`: Kafka integration

### Tuning Parameters
```python
# In realtime_dpdk_pipeline.py
self.interface = "enp2s0"          # Network interface
self.kafka_broker = "localhost:9092"  # Kafka connection
rate = 100                         # Packets per second
duration = 120                     # Test duration
```

## 🐛 Troubleshooting

### Common Issues

**1. Permission Errors**
```bash
# Ensure root privileges for packet injection
sudo python3 realtime_dpdk_pipeline.py --mode validate
```

**2. Suricata Not Running**
```bash
# Check and start Suricata
sudo systemctl status suricata
sudo systemctl start suricata
```

**3. Kafka Connection Issues**
```bash
# Verify Kafka is running
./Suricata_Setup/setup_kafka.sh
pgrep -f kafka
```

**4. No Events Generated**
```bash
# Check Suricata logs
tail -f /var/log/suricata/eve.json

# Verify interface is correct
ip link show
```

**5. High CPU Usage**
```bash
# Reduce packet generation rate
sudo python3 realtime_dpdk_pipeline.py --mode generate --rate 10
```

### Debug Commands
```bash
# System validation
sudo ./validate_complete_pipeline.sh

# Check service logs
journalctl -u suricata -f
journalctl -u kafka -f

# Monitor system resources
htop
iotop
nethogs
```

## 📊 Expected Results

### Successful Pipeline Operation
- **Validation Score**: 90-100%
- **Event Generation**: 10+ events/minute
- **Alert Detection**: Security alerts triggered  
- **Kafka Streaming**: Events flowing to topics
- **System Performance**: <80% CPU, <80% memory

### Performance Benchmarks
- **100 pps**: Low resource usage, good for testing
- **500 pps**: Medium load, realistic traffic simulation
- **1000+ pps**: High performance, stress testing
- **Real network**: Variable rates based on actual traffic

## 🚀 Advanced Features

### DPDK Integration
- Hugepage memory management
- User-space networking
- Kernel bypass for maximum performance
- High-rate packet generation (10K+ pps)

### Machine Learning Ready
- Structured event data in Kafka
- Feature extraction via Suricata
- Real-time streaming for ML models
- Historical data for training

### Scalability
- Multiple Kafka partitions
- Distributed Suricata instances
- Load balancing across interfaces
- Horizontal scaling support

## 📚 Integration with Existing System

This integrated DPDK pipeline builds on your existing:
- **Suricata Setup**: Uses existing configurations
- **Kafka Streaming**: Leverages current topics and bridge
- **Monitoring Tools**: Extends current validation scripts
- **Service Management**: Works with existing systemd services

## 🎯 Next Steps

1. **Performance Optimization**: Tune for your specific hardware
2. **Rule Customization**: Add custom Suricata rules for your environment
3. **ML Integration**: Connect Kafka streams to machine learning models
4. **Distributed Deployment**: Scale across multiple systems
5. **Custom Analytics**: Build application-specific event processing

---

**🔥 Your real-time DPDK-Suricata-Kafka IDS pipeline is ready for high-performance threat detection!**
