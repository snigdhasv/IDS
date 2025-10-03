# Sample PCAP Files

This directory contains sample PCAP files for testing the IDS pipeline.

## Usage

Replay any PCAP file using:

```bash
cd ../scripts
sudo ./05_replay_traffic.sh ../pcap_samples/<file>.pcap
```

## Sample Files

### Option 1: Use Existing PCAP Files

If you have existing PCAP files from your project, copy them here:

```bash
cp /path/to/your/capture.pcap .
```

### Option 2: Download Public Datasets

#### CICIDS2017 Dataset
```bash
# Download sample from CICIDS2017
wget https://www.unb.ca/cic/datasets/ids-2017.html
# Or use your existing dataset files
```

#### CICIDS2018 Dataset
```bash
# Use files from your project:
# /home/sujay/Programming/IDS/CICIDS2018.ipynb
```

### Option 3: Capture Your Own

Capture live traffic:

```bash
# Capture 1000 packets
sudo tcpdump -i eth0 -c 1000 -w sample_traffic.pcap

# Capture for 60 seconds
sudo tcpdump -i eth0 -G 60 -W 1 -w sample_60s.pcap
```

### Option 4: Generate Synthetic Traffic

Create test PCAP with Scapy:

```python
from scapy.all import *

# Generate benign HTTP traffic
packets = []
for i in range(100):
    pkt = Ether()/IP(dst="192.168.1.100")/TCP(dport=80, sport=1024+i)
    packets.append(pkt)

wrpcap('benign_http.pcap', packets)

# Generate suspicious scan traffic
packets = []
for port in range(1, 1001):
    pkt = Ether()/IP(dst="192.168.1.100")/TCP(dport=port, flags="S")
    packets.append(pkt)

wrpcap('port_scan.pcap', packets)
```

## Quick Test Files

### Create Minimal Test File

```bash
# Single ping packet
python3 << 'EOF'
from scapy.all import *
pkt = Ether()/IP(dst="8.8.8.8")/ICMP()
wrpcap('test_ping.pcap', [pkt])
EOF

# HTTP GET request
python3 << 'EOF'
from scapy.all import *
pkt = Ether()/IP(dst="192.168.1.100")/TCP(dport=80, sport=12345)/"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"
wrpcap('test_http.pcap', [pkt])
EOF
```

## Expected Suricata Alerts

Different traffic types will trigger different alerts:

- **Port Scans:** "Potential TCP Port Scan"
- **SSH Brute Force:** "SSH Authentication Attempted"
- **Web Attacks:** "SQL Injection Attempt", "XSS Attempt"
- **Malware:** "Known Malware C2 Communication"
- **DDoS:** "Potential DDoS Attack"

## Testing Workflow

1. **Replay PCAP:**
   ```bash
   sudo ./05_replay_traffic.sh sample.pcap
   ```

2. **Monitor Suricata:**
   ```bash
   tail -f /var/log/suricata/eve.json | jq
   ```

3. **Check Kafka:**
   ```bash
   kafka-console-consumer.sh --bootstrap-server localhost:9092 \
       --topic suricata-alerts --from-beginning | jq
   ```

4. **View ML Predictions:**
   ```bash
   tail -f ../logs/ml/ml_consumer.log
   ```

## PCAP File Requirements

For best results:
- **Format:** Standard PCAP or PCAPNG
- **Size:** Start with small files (< 100MB) for testing
- **Content:** Mix of benign and malicious traffic
- **Timestamps:** Can be real or synthetic

## Analyzing PCAP Files

Before replaying, inspect the PCAP:

```bash
# Basic info
capinfos sample.pcap

# View packets
tcpdump -r sample.pcap -n

# Statistics
tcpdump -r sample.pcap -n | wc -l  # Packet count

# Filter specific traffic
tcpdump -r sample.pcap -n 'tcp port 80'
```

## Performance Considerations

- **Large Files:** May cause memory issues, split if needed
- **Replay Speed:** Adjust with `-s` flag for realistic traffic
- **Loop Count:** Use `-l` to repeat traffic patterns

## Example Commands

```bash
# Replay at 10 Mbps
sudo ./05_replay_traffic.sh sample.pcap -s 10

# Replay 5 times
sudo ./05_replay_traffic.sh sample.pcap -l 5

# Maximum speed
sudo ./05_replay_traffic.sh sample.pcap -s 0

# Specific interface
sudo ./05_replay_traffic.sh sample.pcap -i eth1
```

---

**Note:** Always test with small PCAP files first to ensure the pipeline is working correctly before using large datasets.
