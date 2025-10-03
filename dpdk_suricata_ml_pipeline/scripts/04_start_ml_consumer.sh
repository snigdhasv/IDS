#!/bin/bash

# Start ML Inference Consumer

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/pipeline.conf"
VENV_PATH="$(dirname "$(dirname "$SCRIPT_DIR")")/venv"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║  ML Kafka Consumer Start Script                ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo

# Load configuration
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo -e "${YELLOW}⚠️  Using default configuration${NC}"
fi

# Check virtual environment
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}❌ Virtual environment not found: $VENV_PATH${NC}"
    echo "Run: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source "$VENV_PATH/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Check Python dependencies
echo -e "\n${BLUE}Checking dependencies...${NC}"
python3 -c "import kafka" 2>/dev/null || {
    echo -e "${YELLOW}Installing kafka-python...${NC}"
    pip install kafka-python confluent-kafka > /dev/null
}
python3 -c "import joblib" 2>/dev/null || {
    echo -e "${YELLOW}Installing joblib...${NC}"
    pip install joblib > /dev/null
}
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Check Kafka is running
if ! netstat -tuln 2>/dev/null | grep -q ":9092"; then
    echo -e "${RED}❌ Kafka not running on port 9092${NC}"
    echo "Start Kafka first: ./02_setup_kafka.sh"
    exit 1
fi
echo -e "${GREEN}✓ Kafka is running${NC}"

# Check ML model exists
if [ ! -z "$ML_MODEL_PATH" ] && [ ! -f "$ML_MODEL_PATH" ]; then
    echo -e "${YELLOW}⚠️  ML model not found: $ML_MODEL_PATH${NC}"
    echo "Using default model if available..."
fi

# Create log directory
mkdir -p "${SCRIPT_DIR}/../logs/ml"

# Check if already running
if pgrep -f "ml_kafka_consumer.py" > /dev/null; then
    echo -e "${YELLOW}⚠️  ML consumer already running${NC}"
    read -p "Kill existing process? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "ml_kafka_consumer.py"
        sleep 2
    else
        echo "Aborted."
        exit 0
    fi
fi

# Start ML consumer
echo -e "\n${BOLD}${BLUE}Starting ML Kafka Consumer...${NC}"
echo -e "${CYAN}Log: ${SCRIPT_DIR}/../logs/ml/ml_consumer.log${NC}"
echo

cd "${SCRIPT_DIR}/../src"

# Start in background
nohup python3 ml_kafka_consumer.py \
    --config "${CONFIG_FILE}" \
    ${ML_MODEL_PATH:+--model "$ML_MODEL_PATH"} \
    > "${SCRIPT_DIR}/../logs/ml/ml_consumer.out" 2>&1 &

CONSUMER_PID=$!
sleep 2

# Verify it's running
if ps -p $CONSUMER_PID > /dev/null; then
    echo -e "${GREEN}✓ ML Consumer started (PID: $CONSUMER_PID)${NC}"
else
    echo -e "${RED}❌ ML Consumer failed to start${NC}"
    echo "Check logs: tail -f ${SCRIPT_DIR}/../logs/ml/ml_consumer.out"
    exit 1
fi

echo -e "\n${BOLD}${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  ML Consumer Started Successfully              ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo

echo -e "${BOLD}Process Info:${NC}"
echo -e "  PID: ${CYAN}$CONSUMER_PID${NC}"
echo -e "  Input Topic: ${CYAN}${KAFKA_TOPIC_ALERTS:-suricata-alerts}${NC}"
echo -e "  Output Topic: ${CYAN}${KAFKA_TOPIC_ML_PREDICTIONS:-ml-predictions}${NC}"
echo

echo -e "${BOLD}Monitor Logs:${NC}"
echo -e "  ${CYAN}tail -f ${SCRIPT_DIR}/../logs/ml/ml_consumer.log${NC}"
echo -e "  ${CYAN}tail -f ${SCRIPT_DIR}/../logs/ml/ml_consumer.out${NC}"
echo

echo -e "${BOLD}Monitor Predictions:${NC}"
echo -e "  ${CYAN}kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic ml-predictions${NC}"
echo

echo -e "${BOLD}Stop Consumer:${NC}"
echo -e "  ${CYAN}pkill -f ml_kafka_consumer.py${NC}"
echo

echo -e "${GREEN}✓ Done!${NC}"
