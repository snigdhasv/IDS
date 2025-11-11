#!/bin/bash

################################################################################
# Kafka Cleanup Script
################################################################################
# This script cleans up stale Kafka/Zookeeper state
# Use this when Kafka fails to start with NodeExistsException
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║  Kafka/Zookeeper Cleanup                       ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo

# Find Kafka directory
KAFKA_DIR=""
if [ -d "/usr/local/kafka" ]; then
    KAFKA_DIR="/usr/local/kafka"
elif [ -d "/opt/kafka" ]; then
    KAFKA_DIR="/opt/kafka"
else
    echo -e "${RED}❌ Kafka installation not found${NC}"
    exit 1
fi

KAFKA_BIN="$KAFKA_DIR/bin"

# Stop Kafka if running
echo -e "${BLUE}Stopping Kafka services...${NC}"

if pgrep -f "kafka.Kafka" > /dev/null; then
    echo -e "${CYAN}Stopping Kafka broker...${NC}"
    $KAFKA_BIN/kafka-server-stop.sh
    sleep 3
fi

if pgrep -f "zookeeper" > /dev/null; then
    echo -e "${CYAN}Stopping Zookeeper...${NC}"
    $KAFKA_BIN/zookeeper-server-stop.sh
    sleep 3
fi

# Force kill if still running
if pgrep -f "kafka.Kafka" > /dev/null; then
    echo -e "${YELLOW}Force killing Kafka...${NC}"
    pkill -9 -f "kafka.Kafka"
    sleep 2
fi

if pgrep -f "zookeeper" > /dev/null; then
    echo -e "${YELLOW}Force killing Zookeeper...${NC}"
    pkill -9 -f "zookeeper"
    sleep 2
fi

echo -e "${GREEN}✓ Services stopped${NC}"

# Clean up Kafka and Zookeeper data
echo -e "\n${BLUE}Cleaning up data directories...${NC}"

# Remove Kafka logs
if [ -d "/tmp/kafka-logs" ]; then
    echo -e "${CYAN}Removing /tmp/kafka-logs${NC}"
    rm -rf /tmp/kafka-logs
fi

# Remove Zookeeper data
if [ -d "/tmp/zookeeper" ]; then
    echo -e "${CYAN}Removing /tmp/zookeeper${NC}"
    rm -rf /tmp/zookeeper
fi

# Alternative Zookeeper data locations
if [ -d "/var/lib/zookeeper" ]; then
    echo -e "${CYAN}Removing /var/lib/zookeeper${NC}"
    rm -rf /var/lib/zookeeper
fi

echo -e "${GREEN}✓ Data directories cleaned${NC}"

# Clean up log files if they exist
if [ -d "$KAFKA_DIR/logs" ]; then
    echo -e "\n${BLUE}Cleaning old log files...${NC}"
    rm -f "$KAFKA_DIR/logs/"*.log
    echo -e "${GREEN}✓ Log files cleaned${NC}"
fi

echo -e "\n${BOLD}${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  Cleanup Complete                              ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo
echo -e "${CYAN}You can now restart Kafka with:${NC}"
echo -e "  ${YELLOW}sudo ./run_afpacket_mode.sh${NC}"
echo
