#!/bin/bash

# Install and Configure Kafka for IDS Pipeline

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/pipeline.conf"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║  Kafka Setup for IDS Pipeline                  ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo

# Load configuration
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo -e "${YELLOW}⚠️  Using default configuration${NC}"
    KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
    KAFKA_TOPIC_ALERTS="suricata-alerts"
    KAFKA_TOPIC_ML_PREDICTIONS="ml-predictions"
fi

# Check if Kafka is already installed
KAFKA_DIR="/opt/kafka"
if [ -d "$KAFKA_DIR" ] && [ -f "$KAFKA_DIR/bin/kafka-server-start.sh" ]; then
    echo -e "${GREEN}✓ Kafka already installed at $KAFKA_DIR${NC}"
    KAFKA_INSTALLED=true
    # Add to PATH for this session
    export PATH=$PATH:$KAFKA_DIR/bin
elif command -v kafka-server-start.sh &> /dev/null; then
    echo -e "${GREEN}✓ Kafka already installed (in PATH)${NC}"
    KAFKA_INSTALLED=true
    KAFKA_DIR=$(dirname $(dirname $(which kafka-server-start.sh)))
else
    echo -e "${YELLOW}Kafka not found. Installing...${NC}"
    KAFKA_INSTALLED=false
fi

# Install Kafka if needed
if [ "$KAFKA_INSTALLED" = false ]; then
    KAFKA_VERSION="3.6.0"
    SCALA_VERSION="2.13"
    KAFKA_DIR="/opt/kafka"
    
    echo -e "\n${BLUE}Downloading Kafka ${KAFKA_VERSION}...${NC}"
    cd /tmp
    wget -q --show-progress "https://downloads.apache.org/kafka/${KAFKA_VERSION}/kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz"
    
    echo -e "${BLUE}Installing Kafka...${NC}"
    sudo tar -xzf "kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz" -C /opt/
    sudo mv "/opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}" "$KAFKA_DIR"
    
    # Add to PATH
    if ! grep -q "kafka/bin" ~/.bashrc; then
        echo 'export PATH=$PATH:/opt/kafka/bin' >> ~/.bashrc
    fi
    
    echo -e "${GREEN}✓ Kafka installed to $KAFKA_DIR${NC}"
fi

# Always use full path to Kafka commands
KAFKA_BIN="$KAFKA_DIR/bin"

# Check if Kafka is running
if netstat -tuln 2>/dev/null | grep -q ":9092"; then
    echo -e "${GREEN}✓ Kafka already running${NC}"
else
    echo -e "\n${BLUE}Starting Kafka services...${NC}"
    
    # Start Zookeeper in background
    echo -e "${CYAN}Starting Zookeeper...${NC}"
    $KAFKA_BIN/zookeeper-server-start.sh -daemon $KAFKA_DIR/config/zookeeper.properties
    sleep 5
    
    # Start Kafka in background
    echo -e "${CYAN}Starting Kafka broker...${NC}"
    $KAFKA_BIN/kafka-server-start.sh -daemon $KAFKA_DIR/config/server.properties
    sleep 5
    
    # Verify
    if netstat -tuln | grep -q ":9092"; then
        echo -e "${GREEN}✓ Kafka started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start Kafka${NC}"
        exit 1
    fi
fi

# Create topics
echo -e "\n${BLUE}Creating Kafka topics...${NC}"

# Suricata alerts topic
$KAFKA_BIN/kafka-topics.sh --create \
    --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
    --topic "$KAFKA_TOPIC_ALERTS" \
    --partitions 3 \
    --replication-factor 1 \
    --if-not-exists 2>/dev/null && \
    echo -e "${GREEN}✓ Created topic: $KAFKA_TOPIC_ALERTS${NC}" || \
    echo -e "${YELLOW}⚠️  Topic $KAFKA_TOPIC_ALERTS already exists${NC}"

# ML predictions topic
$KAFKA_BIN/kafka-topics.sh --create \
    --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
    --topic "$KAFKA_TOPIC_ML_PREDICTIONS" \
    --partitions 3 \
    --replication-factor 1 \
    --if-not-exists 2>/dev/null && \
    echo -e "${GREEN}✓ Created topic: $KAFKA_TOPIC_ML_PREDICTIONS${NC}" || \
    echo -e "${YELLOW}⚠️  Topic $KAFKA_TOPIC_ML_PREDICTIONS already exists${NC}"

# List topics
echo -e "\n${BOLD}Available Topics:${NC}"
$KAFKA_BIN/kafka-topics.sh --list --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS"

# Install Python Kafka library
echo -e "\n${BLUE}Installing Python Kafka library...${NC}"

# Determine venv path
VENV_PATH="$(dirname "$SCRIPT_DIR")/venv"

# Create venv if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}Virtual environment not found at $VENV_PATH${NC}"
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv "$VENV_PATH"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate venv and install packages
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
    pip install --upgrade pip > /dev/null 2>&1
    pip install kafka-python confluent-kafka > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Python Kafka libraries installed in venv${NC}"
    else
        echo -e "${RED}❌ Failed to install Python Kafka libraries${NC}"
        echo -e "${YELLOW}⚠️  You can install manually:${NC}"
        echo -e "    ${CYAN}source $VENV_PATH/bin/activate${NC}"
        echo -e "    ${CYAN}pip install kafka-python confluent-kafka${NC}"
    fi
    deactivate
else
    echo -e "${RED}❌ Failed to create/activate virtual environment${NC}"
    echo -e "${YELLOW}⚠️  You can install manually:${NC}"
    echo -e "    ${CYAN}python3 -m venv $VENV_PATH${NC}"
    echo -e "    ${CYAN}source $VENV_PATH/bin/activate${NC}"
    echo -e "    ${CYAN}pip install kafka-python confluent-kafka${NC}"
fi

echo -e "\n${BOLD}${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  Kafka Setup Complete                          ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo

echo -e "${BOLD}Kafka Configuration:${NC}"
echo -e "  Bootstrap Servers: ${CYAN}$KAFKA_BOOTSTRAP_SERVERS${NC}"
echo -e "  Alerts Topic: ${CYAN}$KAFKA_TOPIC_ALERTS${NC}"
echo -e "  Predictions Topic: ${CYAN}$KAFKA_TOPIC_ML_PREDICTIONS${NC}"
echo

echo -e "${BOLD}Useful Commands:${NC}"
echo -e "  List topics:  ${CYAN}$KAFKA_BIN/kafka-topics.sh --list --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS${NC}"
echo -e "  Consume:      ${CYAN}$KAFKA_BIN/kafka-console-consumer.sh --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS --topic $KAFKA_TOPIC_ALERTS${NC}"
echo -e "  Produce:      ${CYAN}$KAFKA_BIN/kafka-console-producer.sh --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS --topic $KAFKA_TOPIC_ALERTS${NC}"
echo -e "  Stop Kafka:   ${CYAN}$KAFKA_BIN/kafka-server-stop.sh${NC}"
echo -e "  Stop Zookeeper: ${CYAN}$KAFKA_BIN/zookeeper-server-stop.sh${NC}"
echo

echo -e "${GREEN}✓ Done!${NC}"
