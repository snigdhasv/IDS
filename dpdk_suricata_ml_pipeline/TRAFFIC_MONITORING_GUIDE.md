# 🎯 Quick Reference: Viewing Traffic & Alerts

## 🚀 **Interactive Monitor (RECOMMENDED)**

```bash
cd ~/Programming/IDS/dpdk_suricata_ml_pipeline/scripts
./monitor_traffic.sh
```

This gives you a menu with 10 options for different views!

---

## 📊 **Quick Commands**

### **1. Live Suricata Events (All Types)**
```bash
tail -f /var/log/suricata/eve.json | jq '.'
```

### **2. Live Alerts Only** 🚨
```bash
tail -f /var/log/suricata/eve.json | grep '"event_type":"alert"' | jq '{
    time: .timestamp,
    severity: .alert.severity,
    signature: .alert.signature,
    src: (.src_ip + ":" + (.src_port|tostring)),
    dst: (.dest_ip + ":" + (.dest_port|tostring))
}'
```

### **3. Live Flow Events** 🌊
```bash
tail -f /var/log/suricata/eve.json | grep '"event_type":"flow"' | jq '{
    src: (.src_ip + ":" + (.src_port|tostring)),
    dst: (.dest_ip + ":" + (.dest_port|tostring)),
    proto: .proto,
    bytes: .flow.bytes_toserver
}'
```

### **4. Live DNS Queries** 🔍
```bash
tail -f /var/log/suricata/eve.json | grep '"event_type":"dns"' | jq '{
    query: .dns.rrname,
    type: .dns.rrtype,
    src: .src_ip
}'
```

### **5. Live HTTP Requests** 🌐
```bash
tail -f /var/log/suricata/eve.json | grep '"event_type":"http"' | jq '{
    method: .http.http_method,
    host: .http.hostname,
    url: .http.url,
    src: .src_ip
}'
```

### **6. Live ML Predictions** 🤖
```bash
tail -f ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.out
```

### **7. ML Alerts Only**
```bash
tail -f ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log | grep "ML Alert:"
```

---

## 📈 **Statistics Commands**

### **Event Type Counts**
```bash
grep -o '"event_type":"[^"]*"' /var/log/suricata/eve.json | \
    cut -d'"' -f4 | sort | uniq -c | sort -rn
```

### **Total Alerts**
```bash
grep -c '"event_type":"alert"' /var/log/suricata/eve.json
```

### **Alerts by Severity**
```bash
grep '"event_type":"alert"' /var/log/suricata/eve.json | \
    jq -r '.alert.severity' | sort | uniq -c
```

### **Top Source IPs**
```bash
grep '"src_ip"' /var/log/suricata/eve.json | \
    grep -o '"src_ip":"[^"]*"' | cut -d'"' -f4 | \
    sort | uniq -c | sort -rn | head -10
```

### **Top Alert Types**
```bash
grep '"event_type":"alert"' /var/log/suricata/eve.json | \
    jq -r '.alert.signature' | sort | uniq -c | sort -rn | head -10
```

---

## 🔎 **Search Commands**

### **Search by IP Address**
```bash
grep "192.168.100.2" /var/log/suricata/eve.json | jq '.'
```

### **Search by Port**
```bash
grep '"dest_port":80' /var/log/suricata/eve.json | jq '.'
```

### **Search for Specific Attack**
```bash
grep -i "sql injection" /var/log/suricata/eve.json | jq '.'
```

### **Recent Alerts (Last 20)**
```bash
grep '"event_type":"alert"' /var/log/suricata/eve.json | tail -20 | jq '.'
```

---

## 📡 **Kafka Streams**

### **Suricata Events from Kafka**
```bash
/opt/kafka/bin/kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic suricata-alerts | jq '.'
```

### **ML Predictions from Kafka**
```bash
/opt/kafka/bin/kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic ml-predictions | jq '.'
```

### **Count Kafka Messages**
```bash
/opt/kafka/bin/kafka-run-class.sh kafka.tools.GetOffsetShell \
    --broker-list localhost:9092 \
    --topic suricata-alerts
```

---

## 🎨 **Pretty Display Commands**

### **Compact Event View**
```bash
tail /var/log/suricata/eve.json | jq -c '{
    time: .timestamp,
    type: .event_type,
    src: .src_ip,
    dst: .dest_ip
}'
```

### **Alert Summary**
```bash
grep '"event_type":"alert"' /var/log/suricata/eve.json | jq -c '{
    severity: .alert.severity,
    signature: .alert.signature,
    src: .src_ip,
    dst: .dest_ip
}' | tail -10
```

### **Flow Summary**
```bash
grep '"event_type":"flow"' /var/log/suricata/eve.json | jq -c '{
    src: .src_ip,
    dst: .dest_ip,
    proto: .proto,
    pkts: .flow.pkts_toserver,
    bytes: .flow.bytes_toserver
}' | tail -10
```

---

## 🎯 **Multi-Terminal Setup**

For complete monitoring, open **4 terminals**:

**Terminal 1: Suricata Alerts**
```bash
tail -f /var/log/suricata/eve.json | grep '"event_type":"alert"' | jq '.'
```

**Terminal 2: ML Predictions**
```bash
tail -f ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.out
```

**Terminal 3: Flow Events**
```bash
tail -f /var/log/suricata/eve.json | grep '"event_type":"flow"' | jq -c '{src: .src_ip, dst: .dest_ip, proto: .proto}'
```

**Terminal 4: Statistics**
```bash
watch -n 5 'grep -o "\"event_type\":\"[^\"]*\"" /var/log/suricata/eve.json | cut -d"\"" -f4 | sort | uniq -c | sort -rn'
```

---

## 🚀 **Your Current Activity**

Based on your system right now:
- ✅ **50 alerts detected** (mostly timestamp warnings)
- ✅ **ML detecting DDoS patterns** (20-21% confidence)
- ✅ **Traffic from**: 192.168.100.2 (your external device)
- ✅ **Traffic to**: 169.254.169.254 (link-local address)
- ✅ **Flow events**: Active network flows being analyzed
- ✅ **DNS queries**: 112 DNS events captured
- ✅ **HTTP requests**: 16 HTTP events captured

---

## 💡 **Pro Tips**

1. **Use `jq` for pretty JSON**: `| jq '.'`
2. **Use `jq -c` for compact output**: `| jq -c '.'`
3. **Use `grep --line-buffered` for live filtering**
4. **Press `Ctrl+C` to stop any live tail**
5. **Use `head` or `tail -n X` to limit output**

---

## 📝 **Example: Finding Attack Patterns**

```bash
# Find all DDoS-related events
grep -i "ddos" /var/log/suricata/eve.json | jq '.'

# Find all SQL injection attempts
grep -i "sql" /var/log/suricata/eve.json | jq '.'

# Find traffic from specific IP
grep "192.168.100.2" /var/log/suricata/eve.json | \
    jq '{time: .timestamp, type: .event_type, dst: .dest_ip}'

# Find high-severity alerts (severity 1 = critical)
grep '"event_type":"alert"' /var/log/suricata/eve.json | \
    jq 'select(.alert.severity == 1)'
```

---

*Quick access: `./monitor_traffic.sh` for interactive menu!*
