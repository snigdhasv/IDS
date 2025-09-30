#!/bin/bash

# Quick Ensemble Demo Script
# Demonstrates the RF 2017 + LightGBM 2018 adaptive ensemble in action

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

echo -e "${BOLD}${BLUE}🎯 Adaptive Ensemble ML Model Demo${NC}"
echo -e "${CYAN}====================================${NC}"
echo "Showcasing RF 2017 + LightGBM 2018 ensemble with 0.9148 accuracy"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}❌ Root privileges required for packet injection${NC}"
    echo "Please run: sudo $0"
    exit 1
fi

echo -e "${YELLOW}📋 Demo Plan:${NC}"
echo "1. Quick ensemble model test (30 seconds)"
echo "2. Mixed traffic with ensemble predictions (60 seconds)"
echo "3. Specific attack detection showcase (45 seconds)"
echo

read -p "Press Enter to start the ensemble demo..."
echo

# Test 1: Quick ensemble verification
echo -e "\n${GREEN}🧪 Test 1: Ensemble Model Verification${NC}"
echo "Testing the adaptive ensemble functionality..."
echo

python3 test_ensemble_model.py

echo -e "\n${YELLOW}⏸️ Waiting 10 seconds...${NC}"
sleep 10

# Test 2: Mixed traffic with ensemble
echo -e "\n${BLUE}🎯 Test 2: Mixed Traffic Ensemble Detection${NC}"
echo "Generating mixed traffic to test ensemble predictions..."
echo -e "${CYAN}Command: ./ml_enhanced_pipeline.sh --traffic-mode mixed --duration 60 --rate 30${NC}"
echo

./ml_enhanced_pipeline.sh --traffic-mode mixed --duration 60 --rate 30

echo -e "\n${YELLOW}⏸️ Waiting 10 seconds...${NC}"
sleep 10

# Test 3: Specific attack showcase
echo -e "\n${MAGENTA}🚨 Test 3: DDoS Attack Detection Showcase${NC}"
echo "Testing ensemble's ability to detect coordinated DDoS attacks..."
echo -e "${CYAN}Command: ./ml_enhanced_pipeline.sh --traffic-mode flood --attack-type DDoS --duration 45 --rate 40${NC}"
echo

./ml_enhanced_pipeline.sh --traffic-mode flood --attack-type DDoS --duration 45 --rate 40

# Demo Summary
echo -e "\n${BOLD}${GREEN}🎉 Adaptive Ensemble Demo Complete!${NC}"
echo -e "${CYAN}=====================================${NC}"
echo
echo -e "${BOLD}What was demonstrated:${NC}"
echo "✅ RF 2017 + LightGBM 2018 ensemble loading"
echo "✅ Confidence-based adaptive weighting"
echo "✅ Unified label space handling"
echo "✅ Real-time ensemble predictions"
echo "✅ Mixed traffic analysis"
echo "✅ Specific attack detection"
echo
echo -e "${BOLD}Ensemble Advantages:${NC}"
echo "🧠 Combines strengths of both models"
echo "⚖️ Adaptive weighting based on confidence"
echo "🎯 0.9148 accuracy performance"
echo "🔄 Handles different class spaces"
echo "📊 Detailed prediction analytics"
echo
echo -e "${BOLD}Key Metrics:${NC}"
echo "• RF Model: RandomForestClassifier (7 classes, 34 features)"
echo "• LGB Model: LGBMClassifier (5 classes, 34 features)"
echo "• Unified Space: 8 attack categories"
echo "• Weighting: Confidence-adaptive (exponential/softmax)"
echo
echo -e "${CYAN}📊 Analysis Commands:${NC}"
echo "• View ensemble alerts: python3 ml_alert_consumer.py"
echo "• Test individual attacks: python3 test_ensemble_model.py"
echo "• Run full pipeline: sudo ./ml_enhanced_pipeline.sh --traffic-mode mixed"
echo
echo -e "${GREEN}🏆 Your IDS now uses state-of-the-art ensemble learning!${NC}"