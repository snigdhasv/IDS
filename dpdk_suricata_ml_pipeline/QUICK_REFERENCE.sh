#!/bin/bash

# Quick Reference for IDS Pipeline
# Display this anytime for quick help

cat << 'EOF'

╔══════════════════════════════════════════════════════════════════╗
║                  IDS Pipeline Quick Reference                    ║
╚══════════════════════════════════════════════════════════════════╝

📚 DOCUMENTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📖 START_HERE.md                  Complete overview
⚡ QUICKSTART.md                  5-min PCAP testing
🚀 PRODUCTION_DPDK_GUIDE.md       Production DPDK setup
🔄 MODES_COMPARISON.md            Test vs Production
📖 RUNTIME_GUIDE.md               Detailed execution
📦 PACKAGES_INSTALLED.md          Package inventory

🎯 QUICK COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Check status
./scripts/status_check.sh

# Start Kafka
./scripts/02_setup_kafka.sh

# Start ML Consumer
source ../venv/bin/activate
python src/ml_kafka_consumer.py --config config/pipeline.conf

# Stop everything
./scripts/stop_all.sh

🧪 TEST MODE (PCAP)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 1. Start Kafka
./scripts/02_setup_kafka.sh

# 2. Start ML Consumer (new terminal)
source ../venv/bin/activate
python src/ml_kafka_consumer.py --config config/pipeline.conf

# 3. Replay traffic
./scripts/05_replay_traffic.sh

📖 Guide: QUICKSTART.md

🚀 PRODUCTION MODE (DPDK)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 1. Start Kafka
./scripts/02_setup_kafka.sh

# 2. Bind interface (⚠️ takes interface offline!)
sudo ./scripts/01_bind_interface.sh

# 3. Start Suricata DPDK
sudo ./scripts/03_start_suricata.sh

# 4. Start ML Consumer (new terminal)
source ../venv/bin/activate
python src/ml_kafka_consumer.py --config config/pipeline.conf

# 5. Send traffic from external device

# 6. Monitor predictions
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
    --topic ml-predictions --from-beginning

📖 Guide: PRODUCTION_DPDK_GUIDE.md

🔍 MONITORING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Pipeline status
./scripts/status_check.sh

# Suricata logs
sudo tail -f /var/log/suricata/suricata.log
sudo tail -f /var/log/suricata/stats.log

# ML consumer logs
tail -f logs/ml/ml_consumer.log

# Kafka topics
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
    --topic suricata-alerts
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
    --topic ml-predictions

# DPDK status
dpdk-devbind.py --status

🐛 TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Kafka won't start
pkill -9 -f kafka
./scripts/02_setup_kafka.sh

# Missing Python packages
./install_missing_packages.sh

# Unbind DPDK interface
sudo ./scripts/unbind_interface.sh

# Check Kafka topics
kafka-topics.sh --list --bootstrap-server localhost:9092

# Test ML model
python -c "import joblib; m=joblib.load('../ML Models/random_forest_model_2017.joblib'); print('OK')"

⚙️ CONFIGURATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Edit configuration
nano config/pipeline.conf

# Key settings:
NETWORK_INTERFACE="eth1"              # Interface to bind
SURICATA_HOME_NET="192.168.0.0/16"    # Your network range
ML_MODEL_PATH="../ML Models/random_forest_model_2017.joblib"

📊 ARCHITECTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Traffic → Suricata → Kafka → ML Engine → Predictions
            ↓         ↓         ↓           ↓
         Packets   Flows    Features    BENIGN/ATTACK

✅ Flow-based ML (ALL traffic analyzed)
✅ 65 CICIDS2017 features per flow
✅ 15 attack types detected
✅ Real-time processing

🔗 RESOURCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Suricata:  https://suricata.io/
DPDK:      https://doc.dpdk.org/
Kafka:     https://kafka.apache.org/
CICIDS2017: https://www.unb.ca/cic/datasets/ids-2017.html

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For help: cat START_HERE.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF
