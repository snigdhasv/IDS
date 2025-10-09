# Suricata Direct Kafka Streaming Setup

This setup configures Suricata to stream detection events (alerts, flows, stats) **directly to Kafka** without writing any eve.json or other log files to disk. All events flow through Kafka topics for high-throughput, reliable processing.

## 📋 Overview

### Key Features
- ✅ **Zero File I/O**: No eve.json, fast.log, or other files written to disk
- ✅ **Direct Kafka Streaming**: All events go directly to Kafka topics
- ✅ **DPDK Integration**: High-performance packet capture
- ✅ **Async/Batching**: Optimized Kafka producer settings
- ✅ **Multiple Topics**: Separate topics for events, alerts, and stats
- ✅ **High Throughput**: Optimized for production workloads

### Architecture
```
Network Traffic → DPDK → Suricata → Kafka Topics → Consumers
                                      ├─ suricata-events
                                      ├─ suricata-alerts
                                      └─ suricata-stats
```

## 🚀 Quick Start

### 1. Install Suricata with Kafka Support
```bash
sudo ./install_suricata_kafka.sh
```

### 2. Setup Kafka Topics
```bash
./setup_kafka.sh
```

### 3. Configure Suricata
Update the DPDK interface in `suricata-kafka.yaml`:
```yaml
dpdk:
  interfaces:
    - interface: 0000:XX:XX.X  # Update with your PCI address
```

Update Kafka brokers if needed:
```yaml
kafka:
  bootstrap-servers: "your-kafka-broker:9092"
```

### 4. Start Services
```bash
# Start Kafka (if not already running)
sudo systemctl start zookeeper
sudo systemctl start kafka

# Start Suricata with Kafka streaming
sudo systemctl start suricata-kafka
```

### 5. Validate Setup
```bash
# Run comprehensive validation
./validate_kafka_streaming.sh

# Generate test traffic
./generate_test_traffic.sh

# Monitor events in real-time
python3 kafka_consumer.py
```

## 📁 File Structure

```
Suricata_Setup/
├── install_suricata_kafka.sh     # Installation script with Kafka support
├── suricata-kafka.yaml           # Main Suricata config (NO file outputs)
├── suricata-kafka.service        # Systemd service for DPDK + Kafka
├── setup_kafka.sh               # Kafka topic creation and management
├── kafka_consumer.py            # Python consumer for validation
├── validate_kafka_streaming.sh  # End-to-end validation script
├── generate_test_traffic.sh     # Traffic generator for testing
└── README.md                    # This documentation
```

## ⚙️ Configuration Details

### Suricata Configuration (`suricata-kafka.yaml`)

#### 🚫 NO File Outputs
The configuration explicitly disables all file-based logging:
- No `filename:` parameters in eve-log
- Console logging disabled
- No fast.log, alert.log, or other files

#### 📤 Kafka Outputs
Three separate Kafka outputs for different event types:

1. **Main EVE Log → `suricata-events`**
   ```yaml
   - eve-log:
       enabled: yes
       kafka:
         topic: "suricata-events"
         compression: "snappy"
         batch-size: 16384
         linger-ms: 10
   ```

2. **Alerts → `suricata-alerts`**
   ```yaml
   - alert-kafka:
       enabled: yes
       kafka:
         topic: "suricata-alerts"
         acks: all  # High reliability for alerts
         linger-ms: 5  # Low latency
   ```

3. **Statistics → `suricata-stats`**
   ```yaml
   - stats-kafka:
       enabled: yes
       kafka:
         topic: "suricata-stats"
         compression: "gzip"
   ```

#### 🚀 High-Performance Settings
- **DPDK**: Hardware-accelerated packet capture
- **Threading**: Optimized CPU affinity
- **Memory**: Large buffers for high throughput
- **Async Producer**: Non-blocking Kafka writes

### Kafka Producer Settings

The configuration uses optimal Kafka producer settings:

```yaml
kafka:
  compression: "snappy"
  batch-size: 16384
  linger-ms: 10
  buffer-memory: 33554432
  acks: 1
  retries: 3
  enable-idempotence: yes
  max-in-flight-requests: 5
```

## 🔍 Validation Process

### Automated Validation
Run the comprehensive validation:
```bash
./validate_kafka_streaming.sh
```

This script:
1. ✅ Checks prerequisites (Kafka running, topics exist)
2. ✅ Validates configuration (no file outputs, Kafka enabled)
3. ✅ Generates test traffic
4. ✅ Monitors Kafka topics for events
5. ✅ Reports validation results

### Manual Validation

#### 1. Check Suricata Status
```bash
sudo systemctl status suricata-kafka
journalctl -u suricata-kafka -f
```

#### 2. Monitor Kafka Topics
```bash
# List topics
kafka-topics.sh --bootstrap-server localhost:9092 --list

# Monitor events topic
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic suricata-events --from-beginning

# Monitor alerts topic
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic suricata-alerts --from-beginning
```

#### 3. Python Consumer
```bash
# Real-time monitoring
python3 kafka_consumer.py

# Validation mode
python3 kafka_consumer.py --validate --timeout 30

# Multiple topics
python3 kafka_consumer.py --topics suricata-events suricata-alerts suricata-stats
```

### Expected Output

When working correctly, you should see:
- ✅ Events flowing to Kafka topics
- ✅ No log files in `/var/log/suricata/`
- ✅ Suricata process running with DPDK
- ✅ Consumer receiving events in real-time

## 🧪 Testing

### Generate Test Traffic
```bash
# Comprehensive traffic generation
sudo ./generate_test_traffic.sh

# Manual testing
curl -s "http://testmyids.com/uid/index.html?test=../../../etc/passwd"
nmap -sS localhost
```

### Monitor Results
```bash
# Real-time event monitoring
python3 kafka_consumer.py --topics suricata-events suricata-alerts

# Check topic message counts
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic suricata-events --from-beginning | wc -l
```

## 🔧 Troubleshooting

### No Events in Kafka

1. **Check Suricata Status**
   ```bash
   sudo systemctl status suricata-kafka
   journalctl -u suricata-kafka -n 50
   ```

2. **Verify Network Interface**
   ```bash
   # Find DPDK interface PCI address
   sudo lshw -c network -businfo
   
   # Update suricata-kafka.yaml with correct PCI address
   ```

3. **Check Kafka Connectivity**
   ```bash
   # Test Kafka connection
   kafka-topics.sh --bootstrap-server localhost:9092 --list
   ```

4. **Generate Network Traffic**
   ```bash
   # Ensure traffic reaches Suricata interface
   sudo tcpdump -i eth0 -c 10
   ```

### Performance Issues

1. **CPU Affinity**
   - Verify CPU cores in config match system
   - Check `/proc/cpuinfo` for available cores

2. **Memory**
   - Monitor memory usage: `free -h`
   - Adjust memcap settings if needed

3. **DPDK**
   - Verify DPDK drivers: `dpdk-devbind.py --status`
   - Check huge pages: `cat /proc/meminfo | grep Huge`

### Kafka Issues

1. **Topic Creation**
   ```bash
   # Recreate topics if needed
   ./setup_kafka.sh
   ```

2. **Producer Errors**
   - Check Kafka logs: `journalctl -u kafka -f`
   - Verify broker addresses in config

3. **Consumer Lag**
   ```bash
   # Check consumer group lag
   kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
     --group suricata-validator --describe
   ```

## 📊 Performance Tuning

### Kafka Producer Optimization

For higher throughput, adjust these settings in `suricata-kafka.yaml`:

```yaml
kafka:
  batch-size: 32768        # Larger batches
  linger-ms: 100          # Higher latency for better batching
  buffer-memory: 67108864  # More buffer memory
  compression: "lz4"       # Faster compression
```

### DPDK Optimization

```yaml
dpdk:
  interfaces:
    - interface: 0000:XX:XX.X
      threads: 8           # More threads for high traffic
      rx-queues: 8         # More RX queues
      rx-desc: 2048        # Larger RX descriptors
```

### Threading Optimization

```yaml
threading:
  worker-cpu-set:
    cpu: [ "4-15" ]        # More worker CPUs
```

## 🔒 Security Considerations

### Kafka Security

For production, enable Kafka security:
```yaml
kafka:
  security-protocol: "SASL_SSL"
  sasl-mechanism: "PLAIN"
  sasl-username: "suricata"
  sasl-password: "secure-password"
  ssl-ca-location: "/path/to/ca-cert"
```

### Network Security

- Isolate DPDK interface from production traffic
- Use dedicated VLAN for monitoring
- Implement proper firewall rules

## 📈 Monitoring

### Suricata Metrics
Monitor these key metrics:
- Packet capture rate
- Drop rate
- Memory usage
- CPU utilization

### Kafka Metrics
- Producer throughput
- Topic partition lag
- Consumer group health
- Broker resource usage

### Example Monitoring
```bash
# Suricata stats (from Kafka)
python3 kafka_consumer.py --topics suricata-stats --quiet

# Kafka topic metrics
kafka-topics.sh --bootstrap-server localhost:9092 \
  --topic suricata-events --describe
```

## 🆘 Support

### Log Files
- Suricata: `journalctl -u suricata-kafka -f`
- Kafka: `journalctl -u kafka -f`
- Zookeeper: `journalctl -u zookeeper -f`

### Debug Mode
Enable debug logging in `suricata-kafka.yaml`:
```yaml
logging:
  default-log-level: debug
```

### Common Commands
```bash
# Restart everything
sudo systemctl restart zookeeper kafka suricata-kafka

# Check all services
sudo systemctl status zookeeper kafka suricata-kafka

# Monitor all logs
journalctl -u suricata-kafka -u kafka -u zookeeper -f
```

---

## ✅ Validation Checklist

- [ ] Kafka running and accessible
- [ ] Topics created (`suricata-events`, `suricata-alerts`, `suricata-stats`)
- [ ] Suricata config has NO file outputs
- [ ] DPDK interface configured correctly
- [ ] Suricata service running with DPDK
- [ ] Test traffic generated
- [ ] Events visible in Kafka topics
- [ ] No log files in `/var/log/suricata/`
- [ ] Consumer receiving events in real-time

**Success Criteria**: Events flow directly from Suricata to Kafka topics without any intermediate file storage.
