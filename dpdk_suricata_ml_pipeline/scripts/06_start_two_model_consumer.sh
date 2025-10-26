#!/bin/bash

# Two-Model Ensemble Consumer Startup Script
# Interactive interface for selecting and running the two-model ML ensemble

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_ROOT/src"
MODEL_DIR="/home/sujay/Programming/IDS/ML Models"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${CYAN}"
echo "═══════════════════════════════════════════════════════════════"
echo "   🎯 TWO-MODEL ENSEMBLE ML CONSUMER"
echo "═══════════════════════════════════════════════════════════════"
echo -e "${NC}"

# Check if model directory exists
if [ ! -d "$MODEL_DIR" ]; then
    echo -e "${RED}❌ Model directory not found: $MODEL_DIR${NC}"
    exit 1
fi

# Get list of available models
cd "$MODEL_DIR"
models=(*.joblib)

if [ ${#models[@]} -eq 0 ]; then
    echo -e "${RED}❌ No model files found in $MODEL_DIR${NC}"
    exit 1
fi

if [ ${#models[@]} -lt 2 ]; then
    echo -e "${RED}❌ Need at least 2 models. Found only ${#models[@]}${NC}"
    exit 1
fi

echo -e "${BOLD}📦 Available Models:${NC}"
echo ""
for i in "${!models[@]}"; do
    num=$((i + 1))
    echo -e "  ${GREEN}${num}.${NC} ${models[$i]}"
done
echo ""

# Select first model
echo -e "${BOLD}─────────────────────────────────────────────────────────────${NC}"
while true; do
    echo -ne "${BOLD}👉 Select MODEL 1 (enter number 1-${#models[@]}): ${NC}"
    read model1_choice
    
    if [[ "$model1_choice" =~ ^[0-9]+$ ]] && [ "$model1_choice" -ge 1 ] && [ "$model1_choice" -le "${#models[@]}" ]; then
        model1_idx=$((model1_choice - 1))
        MODEL1="${models[$model1_idx]}"
        echo -e "${GREEN}✓ Model 1: $MODEL1${NC}"
        break
    else
        echo -e "${RED}❌ Invalid choice. Enter a number between 1 and ${#models[@]}${NC}"
    fi
done

echo ""

# Select second model
while true; do
    echo -ne "${BOLD}👉 Select MODEL 2 (enter number 1-${#models[@]}, must differ from $model1_choice): ${NC}"
    read model2_choice
    
    if [[ "$model2_choice" =~ ^[0-9]+$ ]] && [ "$model2_choice" -ge 1 ] && [ "$model2_choice" -le "${#models[@]}" ]; then
        if [ "$model2_choice" -eq "$model1_choice" ]; then
            echo -e "${RED}❌ Model 2 must be different from Model 1${NC}"
        else
            model2_idx=$((model2_choice - 1))
            MODEL2="${models[$model2_idx]}"
            echo -e "${GREEN}✓ Model 2: $MODEL2${NC}"
            break
        fi
    else
        echo -e "${RED}❌ Invalid choice. Enter a number between 1 and ${#models[@]}${NC}"
    fi
done

echo ""
echo -e "${BOLD}─────────────────────────────────────────────────────────────${NC}"
echo ""

# Ask about meta-learner training
echo -e "${BOLD}🧠 Meta-Learner Training${NC}"
echo ""
echo "The meta-learner learns to optimally weight the two models based on"
echo "confidence metrics and agreement. Training requires labeled data."
echo ""
echo -e "Options:"
echo -e "  ${GREEN}1.${NC} Use meta-learner with online training (collect first 1000 samples)"
echo -e "  ${GREEN}2.${NC} Use confidence-adaptive weighting (no training needed)"
echo ""

while true; do
    echo -ne "${BOLD}👉 Select option (1 or 2): ${NC}"
    read train_choice
    
    case $train_choice in
        1)
            TRAIN_FLAG="--train"
            echo -e "${GREEN}✓ Will train meta-learner on first 1000 samples${NC}"
            break
            ;;
        2)
            TRAIN_FLAG=""
            echo -e "${GREEN}✓ Using confidence-adaptive weighting${NC}"
            break
            ;;
        *)
            echo -e "${RED}❌ Invalid choice. Enter 1 or 2${NC}"
            ;;
    esac
done

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}   🎯 ENSEMBLE CONFIGURATION${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Model 1:      ${CYAN}$MODEL1${NC}"
echo -e "  Model 2:      ${CYAN}$MODEL2${NC}"
echo -e "  Meta-learner: ${YELLOW}$([ -n "$TRAIN_FLAG" ] && echo "Enabled" || echo "Disabled")${NC}"
echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Confirmation
while true; do
    echo -ne "${BOLD}Start consumer with this configuration? (y/n): ${NC}"
    read confirm
    
    case $confirm in
        [Yy]*)
            break
            ;;
        [Nn]*)
            echo -e "${YELLOW}Cancelled${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Please answer y or n${NC}"
            ;;
    esac
done

echo ""
echo -e "${GREEN}🚀 Starting two-model ensemble consumer in background...${NC}"
echo ""

# Change to src directory
cd "$SRC_DIR"

# Activate virtual environment if it exists
if [ -f "$PROJECT_ROOT/../venv/bin/activate" ]; then
    source "$PROJECT_ROOT/../venv/bin/activate"
fi

# Run the consumer in background, redirecting output to log file
LOG_FILE="$PROJECT_ROOT/logs/ml/two_model_ensemble.log"
mkdir -p "$(dirname "$LOG_FILE")"

nohup python3 two_model_consumer.py "$MODEL1" "$MODEL2" $TRAIN_FLAG >> "$LOG_FILE" 2>&1 &
CONSUMER_PID=$!

# Wait a moment to check if it started successfully
sleep 3

if ps -p $CONSUMER_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Two-model ensemble consumer started successfully${NC}"
    echo -e "  ${CYAN}PID:${NC} $CONSUMER_PID"
    echo -e "  ${CYAN}Log:${NC} $LOG_FILE"
    echo ""
    echo -e "${YELLOW}💡 Tip: View logs with:${NC}"
    echo -e "   tail -f $LOG_FILE"
else
    echo -e "${RED}❌ Failed to start consumer${NC}"
    echo -e "Check log file: $LOG_FILE"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Consumer running in background${NC}"

