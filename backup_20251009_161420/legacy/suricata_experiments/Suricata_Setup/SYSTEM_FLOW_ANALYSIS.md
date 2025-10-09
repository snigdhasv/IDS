# System Flow Analysis: How Your Suricata-Kafka Pipeline Works

## 🔍 Current System Status (Based on Your Output)

Your system is working! Here's what's happening:

### ✅ What's Working
- **Suricata**: Running and detecting traffic ✅
- **Kafka**: Running with topics created ✅  
- **Bridge**: EVE.json → Kafka streaming active ✅
- **Consumer**: Kafka consumer connected ✅
- **Event Flow**: 231 events successfully streamed ✅

### 📊 Event Statistics from Your Run
```
Total Events in Kafka: 231
├── suricata-events: 100 messages  
├── suricata-alerts: 100 messages
└── suricata-stats: 31 messages

Bridge Processing Stats:
├── Total: 200 events processed
├── Events: 38 (network events)
├── Alerts: 68 (security alerts) 
└── Flows: 84 (connection flows)
```

## 🌊 Complete Data Flow Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PACKET        │───▶│    SURICATA     │───▶│  EVE KAFKA      │───▶│     KAFKA       │
│   SOURCES       │    │   (AF_PACKET)   │    │    BRIDGE       │    │    TOPICS       │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
   • System traffic        • Packet capture        • File monitoring      • suricata-events
   • Web browsing          • Rule matching         • JSON parsing         • suricata-alerts  
   • DNS queries           • Event generation      • Topic routing        • suricata-stats
   • Network apps          • EVE.json logging      • Real-time stream     • Consumer groups
```

## 📡 Packet Sources (Where Traffic Comes From)

### 1. **Normal System Traffic** (Primary Source)
Your Suricata is monitoring the `enp2s0` network interface, capturing:

#### Automatic Traffic:
- **Operating System**: Background network activity
- **System Services**: DNS lookups, NTP sync, package updates
- **Background Apps**: Browser sync, cloud services, auto-updates

#### Your Generated Traffic:
- **Test Script**: `quick_validate.sh` generated HTTP and DNS requests
- **Manual Commands**: Any curl, ping, nslookup commands you run
- **Web Browsing**: When you visit websites

### 2. **Suricata's Monitoring Method**
```bash
# Suricata is running with AF_PACKET mode on enp2s0
suricata -c /etc/suricata/suricata.yaml -i enp2s0
```

**AF_PACKET Mode**:
- Captures packets directly from network interface
- Monitors ALL traffic passing through `enp2s0`
- Analyzes packets against security rules
- Generates events for suspicious/interesting activity

## 🔄 Real-Time Event Processing Pipeline

### Step 1: Packet Capture
```
Network Interface (enp2s0) → Suricata AF_PACKET → Rule Engine
```

### Step 2: Event Generation  
```
Suricata Rules → Event Detection → EVE.json Format → /var/log/suricata/eve.json
```

### Step 3: Kafka Streaming (Your Bridge)
```python
# eve_kafka_bridge.py monitors the file
tail -f /var/log/suricata/eve.json → Parse JSON → Send to Kafka Topics

Event Types:
├── "alert" → suricata-alerts
├── "flow" → suricata-flows  
├── "stats" → suricata-stats
└── others → suricata-events
```

### Step 4: Kafka Consumption
```python
# kafka_consumer.py reads from topics
Kafka Topics → Consumer Group → Event Processing → Statistics
```

## 🚨 Why You're Seeing Events

### Alert Events (68 alerts):
- **Rule Matches**: Suricata rules detected suspicious patterns
- **Protocol Anomalies**: Unusual network behavior
- **Signature Matches**: Known attack patterns or malware signatures

### Flow Events (84 flows):
- **Connection Tracking**: TCP/UDP connection establishment/teardown
- **Session Monitoring**: HTTP requests, DNS queries
- **Bandwidth Tracking**: Data transfer statistics

### Network Events (38 events):
- **Protocol Events**: HTTP, DNS, TLS handshakes
- **Application Layer**: Web traffic, file transfers
- **Service Detection**: Port scans, service enumeration

## 🔧 Issue in Your Consumer

I noticed this error in your consumer:
```
UnsupportedCodecError: Libraries for snappy compression codec not found
```

The bridge is using `gzip` compression, but there might be a mismatch. Let me fix this:
