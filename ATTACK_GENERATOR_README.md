# Advanced Attack Generator for ML-Enhanced IDS Testing

This module provides comprehensive attack traffic generation capabilities to test your ML-enhanced Intrusion Detection System. It generates realistic attack patterns that match the Random Forest model's trained attack categories.

## 🎯 Supported Attack Types

The generator creates traffic patterns for all attack types your Random Forest model can detect:

### 1. **BENIGN** - Normal Traffic
- HTTP/HTTPS requests
- DNS queries
- SSH connections
- SMTP traffic
- Normal application flows

### 2. **DoS** - Denial of Service
- SYN flood attacks
- UDP flood attacks
- ICMP flood attacks
- TCP RST attacks
- High packet rate targeting single host

### 3. **DDoS** - Distributed Denial of Service
- Multi-source SYN floods
- Distributed UDP floods
- HTTP request floods
- Coordinated attacks from multiple IPs

### 4. **RECONNAISSANCE** - Network Scanning
- Port scanning (TCP/UDP)
- SYN scanning
- OS fingerprinting attempts
- Network enumeration
- Service discovery

### 5. **BRUTE_FORCE** - Authentication Attacks
- SSH brute force attempts
- FTP login attacks
- HTTP form brute forcing
- Telnet authentication attacks
- Common credential testing

### 6. **BOTNET** - Command & Control
- DNS queries to C&C domains
- HTTP beacon traffic
- Encrypted C&C communications
- Irregular heartbeat patterns
- Bot registration traffic

### 7. **WEB_ATTACK** - Application Layer Attacks
- SQL injection attempts
- Cross-Site Scripting (XSS)
- Path traversal attacks
- Command injection
- Malicious HTTP requests

## 🚀 Usage Examples

### Basic Attack Generation

```bash
# Generate mixed traffic (recommended for ML testing)
sudo python3 advanced_attack_generator.py --mode mixed --duration 300 --rate 50

# Generate only benign traffic
sudo python3 advanced_attack_generator.py --mode benign --duration 180 --rate 30

# Generate specific attack flood
sudo python3 advanced_attack_generator.py --mode flood --attack-type DoS --duration 60 --rate 100
```

### Using with ML Pipeline

```bash
# Test complete ML pipeline with mixed attacks
sudo ./ml_enhanced_pipeline.sh --traffic-mode mixed --duration 600 --rate 100

# Test only benign traffic (baseline)
sudo ./ml_enhanced_pipeline.sh --traffic-mode benign --duration 300

# Test specific attack detection
sudo ./ml_enhanced_pipeline.sh --traffic-mode flood --attack-type RECONNAISSANCE --duration 120

# Disable ML for rule-based testing only
sudo ./ml_enhanced_pipeline.sh --traffic-mode mixed --no-ml
```

### Testing Individual Attack Types

```bash
# Test all attack types sequentially
sudo python3 test_attack_generator.py --all

# Test specific attack type
sudo python3 test_attack_generator.py --attack-type DoS --duration 60 --rate 50
```

## 📊 ML Model Integration

The attack generator is specifically designed to test your Random Forest model:

### Feature Generation
- Generates traffic with **65 CICIDS2017-style features**
- Creates realistic flow patterns, timing, and packet characteristics
- Ensures feature values match model training data distribution

### Attack Pattern Realism
- **DoS attacks**: High packet rates, single target, various protocols
- **DDoS attacks**: Multiple sources, coordinated timing
- **Reconnaissance**: Sequential port scanning, low-rate probes
- **Brute Force**: Repeated authentication attempts, realistic timing delays
- **Botnet**: Irregular beaconing, DNS tunneling patterns
- **Web Attacks**: Malicious payloads in HTTP requests, various injection types

### ML Testing Capabilities
- **Mixed Traffic**: 40% benign, 60% various attacks (realistic distribution)
- **Attack Floods**: Pure attack traffic for detection threshold testing
- **Benign Baseline**: Clean traffic for false positive testing
- **Rate Control**: Adjustable packet rates for load testing

## 🛠️ Configuration Options

### Command Line Arguments

```bash
advanced_attack_generator.py [OPTIONS]

Options:
  --interface, -i       Network interface (default: enp2s0)
  --target-network, -t  Target network range (default: 192.168.1.0/24)
  --mode, -m           Traffic mode: mixed, benign, flood
  --attack-type, -a    Attack type for flood mode
  --duration, -d       Duration in seconds (default: 300)
  --rate, -r           Packet rate in pps (default: 50.0)
  --count, -c          Total packet count (overrides duration)
```

### ML Pipeline Integration

```bash
ml_enhanced_pipeline.sh [OPTIONS]

New Options:
  --traffic-mode MODE     mixed, benign, or flood
  --attack-type TYPE      For flood mode
  --target-network NET    Target network range
```

## 📈 Monitoring and Validation

### Real-time Monitoring
The pipeline provides real-time feedback:
- **Packet generation stats** by attack type
- **Suricata rule triggers** for signature-based detection
- **ML predictions** with confidence scores
- **Combined threat scoring** from both systems

### Validation Metrics
- **Detection Rate**: Percentage of attacks detected
- **False Positive Rate**: Benign traffic flagged as malicious
- **Confidence Distribution**: ML model certainty levels
- **Attack Type Accuracy**: Correct classification by category

### Log Analysis
```bash
# Monitor Suricata detections
tail -f /var/log/suricata/eve.json | grep '"event_type":"alert"'

# Monitor ML predictions
python3 ml_alert_consumer.py

# Check Kafka topics
kafka-console-consumer.sh --topic ml-enhanced-alerts --bootstrap-server localhost:9092
```

## 🔬 Testing Scenarios

### 1. **Baseline Testing**
```bash
# Pure benign traffic - establish false positive baseline
sudo ./ml_enhanced_pipeline.sh --traffic-mode benign --duration 300
```

### 2. **Attack Detection Testing**
```bash
# Mixed realistic traffic
sudo ./ml_enhanced_pipeline.sh --traffic-mode mixed --duration 600 --rate 100
```

### 3. **Specific Attack Validation**
```bash
# Test each attack type individually
for attack in DoS DDoS RECONNAISSANCE BRUTE_FORCE BOTNET WEB_ATTACK; do
    sudo ./ml_enhanced_pipeline.sh --traffic-mode flood --attack-type $attack --duration 120
done
```

### 4. **Load Testing**
```bash
# High-rate mixed traffic
sudo ./ml_enhanced_pipeline.sh --traffic-mode mixed --duration 300 --rate 500
```

### 5. **ML Model Tuning**
```bash
# Generate labeled datasets for model improvement
sudo python3 advanced_attack_generator.py --mode flood --attack-type DoS --count 1000
# Analyze resulting features and tune model thresholds
```

## 🎛️ Attack Customization

### Modifying Attack Patterns
Edit `advanced_attack_generator.py` to customize:
- **Payload patterns**: SQL injection strings, XSS payloads
- **Source IP ranges**: Attacker geographic distribution  
- **Timing patterns**: Attack rates, burst vs. sustained
- **Target selection**: Specific services, port ranges

### Adding New Attack Types
1. Add new attack method to `AdvancedAttackGenerator` class
2. Update attack type mapping in `ml_enhanced_ids_pipeline.py`
3. Retrain Random Forest model with new attack samples
4. Test detection accuracy

## 🚨 Security Considerations

### Network Impact
- **Use isolated networks** for testing
- **Monitor bandwidth usage** during high-rate generation
- **Coordinate with network team** before large-scale testing

### Legal Compliance
- **Only test on networks you own** or have explicit permission
- **Follow responsible disclosure** for any vulnerabilities found
- **Document testing activities** for compliance

### Ethical Usage
- **Educational and defensive purposes only**
- **Do not use against unauthorized targets**
- **Respect network capacity and availability**

## 📊 Expected ML Results

When testing with your Random Forest model, expect:

### High Confidence Detections (>0.9)
- **DoS/DDoS attacks**: High packet rates, single targets
- **Web attacks**: Clear malicious payloads
- **Brute force**: Repeated authentication patterns

### Medium Confidence Detections (0.7-0.9)
- **Reconnaissance**: Scanning patterns may vary
- **Botnet traffic**: Can appear similar to normal HTTP

### Challenges
- **Encrypted attacks**: Limited feature visibility
- **Low-rate attacks**: May blend with normal traffic
- **Zero-day patterns**: Not in training data

### Model Improvement
- **Collect false positives/negatives** for retraining
- **Adjust confidence thresholds** based on results
- **Add new features** for better discrimination

## 🎯 Success Metrics

A well-functioning ML-enhanced IDS should achieve:
- **Detection Rate**: >95% for clear attack patterns
- **False Positive Rate**: <2% for benign traffic
- **Response Time**: <1 second for real-time alerts
- **Accuracy**: >90% correct attack type classification

Use this attack generator to validate these metrics and improve your ML model performance!