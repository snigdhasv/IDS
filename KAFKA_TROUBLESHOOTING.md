# Kafka Troubleshooting Guide

## Common Issues and Solutions

### Issue 1: Kafka Fails to Start with NodeExistsException

**Symptoms:**
```
ERROR Exiting Kafka due to fatal exception during startup. (kafka.Kafka$)
org.apache.zookeeper.KeeperException$NodeExistsException: KeeperErrorCode = NodeExists
```

**Cause:** Stale broker registration in Zookeeper from a previous unclean shutdown.

**Solution:**
```bash
sudo ./dpdk_suricata_ml_pipeline/scripts/cleanup_kafka.sh
sudo ./run_afpacket_mode.sh
```

**What the cleanup script does:**
- Stops all Kafka and Zookeeper processes
- Removes `/tmp/kafka-logs` (Kafka data)
- Removes `/tmp/zookeeper` (Zookeeper data)
- Cleans old log files

### Issue 2: Port 9092 Already in Use

**Check if Kafka is running:**
```bash
# Using ss (modern)
ss -tuln | grep 9092

# Using netstat (older systems)
netstat -tuln | grep 9092

# Check process
ps aux | grep kafka.Kafka
```

**Solution:** Stop existing Kafka instance first:
```bash
/usr/local/kafka/bin/kafka-server-stop.sh
# or
pkill -f kafka.Kafka
```

### Issue 3: Zookeeper Connection Timeout

**Symptoms:**
- Kafka logs show "Connection timed out" to Zookeeper
- Zookeeper not responding

**Check Zookeeper status:**
```bash
# Check if running
ps aux | grep zookeeper | grep -v grep

# Check port
ss -tuln | grep 2181
```

**Solution:**
```bash
# Restart Zookeeper
/usr/local/kafka/bin/zookeeper-server-stop.sh
rm -rf /tmp/zookeeper
/usr/local/kafka/bin/zookeeper-server-start.sh -daemon /usr/local/kafka/config/zookeeper.properties
```

### Issue 4: Topics Not Created

**Check existing topics:**
```bash
/usr/local/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
```

**Manually create topics:**
```bash
# Suricata alerts topic
/usr/local/kafka/bin/kafka-topics.sh --create \
    --bootstrap-server localhost:9092 \
    --topic suricata-alerts \
    --partitions 3 \
    --replication-factor 1

# ML predictions topic
/usr/local/kafka/bin/kafka-topics.sh --create \
    --bootstrap-server localhost:9092 \
    --topic ml-predictions \
    --partitions 3 \
    --replication-factor 1
```

### Issue 5: Consumer Not Receiving Messages

**Test message flow:**
```bash
# Terminal 1: Start a test consumer
/usr/local/kafka/bin/kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic suricata-alerts \
    --from-beginning

# Terminal 2: Send test message
echo '{"test": "message"}' | /usr/local/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server localhost:9092 \
    --topic suricata-alerts
```

**Check consumer groups:**
```bash
/usr/local/kafka/bin/kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 \
    --list

# Get details for specific group
/usr/local/kafka/bin/kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 \
    --group ml-consumer-group \
    --describe
```

## Complete Cleanup and Fresh Start

If all else fails, perform a complete cleanup:

```bash
# 1. Stop all services
sudo pkill -f suricata
sudo pkill -f kafka
sudo pkill -f zookeeper
sudo pkill -f suricata_kafka_bridge
sudo pkill -f ml_kafka_consumer

# 2. Clean all data
sudo rm -rf /tmp/kafka-logs
sudo rm -rf /tmp/zookeeper
sudo rm -rf /usr/local/kafka/logs/*.log

# 3. Restart
sudo ./dpdk_suricata_ml_pipeline/scripts/cleanup_kafka.sh
sudo ./run_afpacket_mode.sh
```

## Useful Commands

### Check Service Status
```bash
# All services
sudo ./run_afpacket_mode.sh status

# Individual checks
pgrep -f kafka.Kafka && echo "Kafka running" || echo "Kafka not running"
pgrep -f zookeeper && echo "Zookeeper running" || echo "Zookeeper not running"
pgrep -f suricata && echo "Suricata running" || echo "Suricata not running"
```

### View Logs
```bash
# Kafka
tail -f /usr/local/kafka/logs/server.log

# Zookeeper
tail -f /usr/local/kafka/logs/zookeeper.log

# Suricata
tail -f /var/log/suricata/eve.json | jq .

# ML Consumer
tail -f ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log

# Bridge
tail -f ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/bridge/bridge.log
```

### Monitor Metrics
```bash
# Use the built-in monitor
sudo ./run_afpacket_mode.sh
# Then select option 6 for metrics

# Or directly:
./monitor_metrics.sh --dashboard
./monitor_metrics.sh --status
./monitor_metrics.sh --tail
```

## Prevention Tips

1. **Always use the stop_all script:**
   ```bash
   sudo ./run_afpacket_mode.sh stop
   ```

2. **Check logs before restarting:**
   - Look for errors in `/usr/local/kafka/logs/server.log`
   - Check Suricata logs in `/var/log/suricata/`

3. **Monitor disk space:**
   ```bash
   df -h /tmp
   ```
   Kafka and Zookeeper store data in `/tmp` by default

4. **Regular cleanup:**
   - Clean old logs periodically
   - Remove old Kafka topic data if not needed

## Emergency Recovery

If the system becomes unresponsive:

```bash
# Force kill everything
sudo pkill -9 -f kafka
sudo pkill -9 -f zookeeper
sudo pkill -9 -f suricata

# Complete data wipe
sudo rm -rf /tmp/kafka-logs /tmp/zookeeper

# Check no processes remain
ps aux | grep -E "(kafka|zookeeper|suricata)" | grep -v grep

# Fresh start
sudo ./run_afpacket_mode.sh
```

## Updated Run Script Features

The `run_afpacket_mode.sh` script now includes:

1. **Automatic stale registration cleanup** - Detects and cleans stale broker registrations
2. **Better error reporting** - Shows log excerpts on failure
3. **Zookeeper state management** - Properly handles existing Zookeeper instances
4. **Extended wait times** - Gives Kafka more time to initialize (8 seconds)

The script will automatically handle most common issues without manual intervention.
