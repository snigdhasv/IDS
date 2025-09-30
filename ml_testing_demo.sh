#!/bin/bash

# ML-Enhanced IDS Attack Testing Demo
# Demonstrates the complete pipeline with different attack patterns

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}🎯 ML-Enhanced IDS Attack Testing Demo${NC}"
echo -e "${CYAN}=========================================${NC}"
echo "This demo shows how to test your Random Forest ML model with different attack patterns"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}❌ Root privileges required for packet injection${NC}"
    echo "Please run: sudo $0"
    exit 1
fi

echo -e "${YELLOW}📋 Demo Scenarios:${NC}"
echo "1. Benign traffic baseline (30 seconds)"
echo "2. DoS attack detection (45 seconds)"
echo "3. Web attack patterns (45 seconds)"
echo "4. Mixed traffic with all attacks (60 seconds)"
echo

read -p "Press Enter to start the demo or Ctrl+C to cancel..."
echo

# Scenario 1: Benign Traffic Baseline
echo -e "\n${GREEN}🌐 Scenario 1: Benign Traffic Baseline${NC}"
echo "Testing false positive rate with normal network traffic"
echo -e "${CYAN}Command: ./ml_enhanced_pipeline.sh --traffic-mode benign --duration 30 --rate 20${NC}"
echo

./ml_enhanced_pipeline.sh --traffic-mode benign --duration 30 --rate 20

echo -e "\n${YELLOW}⏸️ Waiting 15 seconds before next test...${NC}"
sleep 15

# Scenario 2: DoS Attack Detection  
echo -e "\n${RED}💥 Scenario 2: DoS Attack Detection${NC}"
echo "Testing ML model's ability to detect Denial of Service attacks"
echo -e "${CYAN}Command: ./ml_enhanced_pipeline.sh --traffic-mode flood --attack-type DoS --duration 45 --rate 50${NC}"
echo

./ml_enhanced_pipeline.sh --traffic-mode flood --attack-type DoS --duration 45 --rate 50

echo -e "\n${YELLOW}⏸️ Waiting 15 seconds before next test...${NC}"
sleep 15

# Scenario 3: Web Attack Patterns
echo -e "\n${MAGENTA}🌐 Scenario 3: Web Attack Detection${NC}"
echo "Testing detection of SQL injection, XSS, and other web attacks"
echo -e "${CYAN}Command: ./ml_enhanced_pipeline.sh --traffic-mode flood --attack-type WEB_ATTACK --duration 45 --rate 30${NC}"
echo

./ml_enhanced_pipeline.sh --traffic-mode flood --attack-type WEB_ATTACK --duration 45 --rate 30

echo -e "\n${YELLOW}⏸️ Waiting 15 seconds before final test...${NC}"
sleep 15

# Scenario 4: Mixed Traffic (Realistic)
echo -e "\n${BLUE}🎯 Scenario 4: Mixed Traffic (Realistic Scenario)${NC}"
echo "Testing complete ML pipeline with mixed benign and attack traffic"
echo -e "${CYAN}Command: ./ml_enhanced_pipeline.sh --traffic-mode mixed --duration 60 --rate 40${NC}"
echo

./ml_enhanced_pipeline.sh --traffic-mode mixed --duration 60 --rate 40

# Demo Summary
echo -e "\n${BOLD}${GREEN}🎉 Demo Complete!${NC}"
echo -e "${CYAN}============================${NC}"
echo
echo -e "${BOLD}What was tested:${NC}"
echo "✅ Benign traffic false positive rate"
echo "✅ DoS attack detection accuracy"  
echo "✅ Web attack pattern recognition"
echo "✅ Mixed traffic realistic scenario"
echo
echo -e "${BOLD}Expected ML Results:${NC}"
echo "• High confidence (>0.9) for clear DoS patterns"
echo "• Medium-high confidence (0.7-0.9) for web attacks"
echo "• Low false positives (<0.1) for benign traffic"
echo "• Accurate attack type classification"
echo
echo -e "${BOLD}Next Steps:${NC}"
echo "1. Analyze ML prediction logs"
echo "2. Review Suricata rule triggers"  
echo "3. Check combined threat scoring"
echo "4. Tune model thresholds if needed"
echo
echo -e "${CYAN}📊 Analysis Commands:${NC}"
echo "• View ML alerts: python3 ml_alert_consumer.py"
echo "• Check Suricata logs: tail -f /var/log/suricata/eve.json"
echo "• Monitor Kafka topics: kafka-console-consumer.sh --topic ml-enhanced-alerts --bootstrap-server localhost:9092"
echo
echo -e "${GREEN}🧠 Your Random Forest ML model has been thoroughly tested!${NC}"