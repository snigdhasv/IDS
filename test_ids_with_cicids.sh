#!/bin/bash

################################################################################
# IDS Testing with CICIDS Ground Truth Validation
################################################################################
# This script:
# 1. Starts your IDS pipeline (Kafka + Suricata + ML Model)
# 2. Waits for you to replay CICIDS PCAP from external device
# 3. Validates predictions against CICIDS ground truth
# 4. Generates accuracy metrics report
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/test_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Virtual environment
VENV_PATH="${SCRIPT_DIR}/venv"
if [ ! -d "$VENV_PATH" ]; then
    VENV_PATH="${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/venv"
fi

# Ground truth CSV
CICIDS_CSV="${SCRIPT_DIR}/dpdk_suricata_ml_pipeline/dataset/Wednesday-workingHours.pcap_ISCX.csv"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Models to test (edit this list as needed)
# Use full paths to avoid confusion
MODEL_DIR="${SCRIPT_DIR}/ML Models"
MODELS=(
    "${MODEL_DIR}/random_forest_model_2017.joblib"
    "${MODEL_DIR}/lgb_model_2018.joblib"
    "${MODEL_DIR}/random_forest_model_2018.joblib"
    "${MODEL_DIR}/decision_tree_model_2017.joblib"
)

# Ensemble combinations (format: "model1:model2")
# RF + LGB = Best (different algorithms)
ENSEMBLES=(
    "${MODEL_DIR}/random_forest_model_2017.joblib:${MODEL_DIR}/lgb_model_2018.joblib"
    "${MODEL_DIR}/lgb_model_2017.joblib:${MODEL_DIR}/lgb_model_2018.joblib"
    "${MODEL_DIR}/random_forest_model_2017.joblib:${MODEL_DIR}/random_forest_model_2018.joblib"
)

print_header() {
    clear
    echo -e "${BOLD}${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║         IDS Testing with CICIDS Ground Truth                  ║"
    echo "║         External Device PCAP Replay Mode                      ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"
    
    # Check virtual environment
    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${RED}❌ Virtual environment not found: $VENV_PATH${NC}"
        echo -e "${YELLOW}Please create venv first: python3 -m venv venv${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Virtual environment found: $VENV_PATH${NC}"
    
    # Check ground truth CSV
    if [ ! -f "$CICIDS_CSV" ]; then
        echo -e "${RED}❌ Ground truth CSV not found: $CICIDS_CSV${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Ground truth CSV found: $(basename $CICIDS_CSV)${NC}"
    
    # Check if models exist
    local model_dir="${SCRIPT_DIR}/ML Models"
    if [ ! -d "$model_dir" ]; then
        echo -e "${RED}❌ ML Models directory not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ ML Models directory found${NC}"
    
    # Create results directory
    mkdir -p "$RESULTS_DIR"
    echo -e "${GREEN}✓ Results directory: $RESULTS_DIR${NC}"
    
    echo
}

cleanup_before_test() {
    echo -e "${YELLOW}Cleaning up before test...${NC}"
    
    # Stop all services
    sudo ./run_afpacket_mode.sh stop > /dev/null 2>&1 || true
    sleep 2
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p dpdk_suricata_ml_pipeline/logs/ml
    mkdir -p logs/metrics
    
    # Fix permissions if owned by root
    sudo chown -R $(whoami):$(whoami) dpdk_suricata_ml_pipeline/logs/ 2>/dev/null || true
    sudo chown -R $(whoami):$(whoami) logs/ 2>/dev/null || true
    
    # Clear old logs
    rm -f dpdk_suricata_ml_pipeline/logs/ml/*.log
    rm -f logs/metrics/*.csv 2>/dev/null || true
    
    # Clean Kafka topics
    sudo ./run_afpacket_mode.sh cleanup > /dev/null 2>&1 || true
    
    sleep 2
    echo -e "${GREEN}✓ Cleanup complete${NC}\n"
}

start_ids_pipeline() {
    echo -e "${CYAN}Starting IDS pipeline...${NC}"
    
    # Start Kafka
    echo -e "  ${BLUE}→${NC} Starting Kafka..."
    sudo ./run_afpacket_mode.sh kafka > /dev/null 2>&1
    sleep 5
    echo -e "  ${GREEN}✓${NC} Kafka ready"
    
    # Start Suricata
    echo -e "  ${BLUE}→${NC} Starting Suricata..."
    sudo ./run_afpacket_mode.sh suricata > /dev/null 2>&1
    sleep 3
    echo -e "  ${GREEN}✓${NC} Suricata ready"
    
    # Start bridge
    echo -e "  ${BLUE}→${NC} Starting network bridge..."
    sudo ./run_afpacket_mode.sh bridge > /dev/null 2>&1
    sleep 2
    echo -e "  ${GREEN}✓${NC} Bridge ready"
    
    echo -e "${GREEN}✓ IDS pipeline ready${NC}\n"
}

test_single_model() {
    local model_file=$1
    local model_name=$(basename "$model_file" .joblib)
    local test_name="${model_name}_${TIMESTAMP}"
    
    echo -e "${BOLD}${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  Testing Model: ${model_name}$(printf '%*s' $((42 - ${#model_name})) '')"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Start ML consumer (with venv activated)
    cd dpdk_suricata_ml_pipeline/src
    source "${VENV_PATH}/bin/activate"
    python3 ml_kafka_consumer.py --model "$model_file" 2>&1 | tee "${SCRIPT_DIR}/logs/ml_consumer_${test_name}.log" &
    ML_PID=$!
    deactivate
    cd "$SCRIPT_DIR"
    
    echo -e "${GREEN}✓ ML consumer started (PID: $ML_PID)${NC}"
    
    # Wait a moment and check if it's still running
    sleep 3
    if ! kill -0 $ML_PID 2>/dev/null; then
        echo -e "${RED}❌ ML consumer failed to start!${NC}"
        echo -e "${YELLOW}Check log file: logs/ml_consumer_${test_name}.log${NC}"
        echo -e "${YELLOW}Last 20 lines:${NC}"
        tail -20 "${SCRIPT_DIR}/logs/ml_consumer_${test_name}.log" 2>/dev/null || echo "No log file found"
        return 1
    fi
    
    # Wait for user to replay traffic
    echo -e "\n${BOLD}${YELLOW}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${YELLOW}║                                                               ║${NC}"
    echo -e "${BOLD}${YELLOW}║  ⚠️  READY TO RECEIVE TRAFFIC                                  ║${NC}"
    echo -e "${BOLD}${YELLOW}║                                                               ║${NC}"
    echo -e "${BOLD}${YELLOW}║  Please replay CICIDS PCAP from your external device now:    ║${NC}"
    echo -e "${BOLD}${YELLOW}║                                                               ║${NC}"
    echo -e "${BOLD}${YELLOW}║  Example command (on Windows):                                ║${NC}"
    echo -e "${BOLD}${YELLOW}║  > tcpreplay -i eth0 Wednesday-workingHours.pcap              ║${NC}"
    echo -e "${BOLD}${YELLOW}║                                                               ║${NC}"
    echo -e "${BOLD}${YELLOW}║  Press ENTER when replay is complete...                       ║${NC}"
    echo -e "${BOLD}${YELLOW}║                                                               ║${NC}"
    echo -e "${BOLD}${YELLOW}╚═══════════════════════════════════════════════════════════════╝${NC}\n"
    
    # Monitor in real-time while waiting
    echo -e "${CYAN}Monitoring predictions (Ctrl+C when replay done)...${NC}\n"
    
    # Show live stats
    local start_time=$(date +%s)
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        # Check if process is still running
        if ! kill -0 $ML_PID 2>/dev/null; then
            echo -e "\n${RED}❌ ML consumer stopped unexpectedly${NC}"
            break
        fi
        
        # Show stats if CSV exists
        local csv_file="logs/metrics/ml_$(date +%Y%m%d).csv"
        if [ -f "$csv_file" ]; then
            local total_predictions=$(wc -l < "$csv_file")
            local attacks=$(grep -v "BENIGN" "$csv_file" 2>/dev/null | wc -l)
            local benign=$(grep "BENIGN" "$csv_file" 2>/dev/null | wc -l)
            
            echo -ne "\r${CYAN}[${elapsed}s]${NC} Predictions: ${BOLD}${total_predictions}${NC} | Attacks: ${RED}${attacks}${NC} | Benign: ${GREEN}${benign}${NC}   "
        else
            echo -ne "\r${CYAN}[${elapsed}s]${NC} Waiting for predictions...   "
        fi
        
        sleep 1
        
        # Check if user wants to stop
        read -t 0.1 -n 1 && break
    done
    
    echo -e "\n\n${YELLOW}Stopping ML consumer...${NC}"
    kill $ML_PID 2>/dev/null || true
    sleep 2
    
    # Save results
    local result_file="${RESULTS_DIR}/${test_name}_predictions.csv"
    if [ -f "logs/metrics/ml_$(date +%Y%m%d).csv" ]; then
        cp "logs/metrics/ml_$(date +%Y%m%d).csv" "$result_file"
        echo -e "${GREEN}✓ Predictions saved: $result_file${NC}"
    else
        echo -e "${RED}❌ No predictions file found${NC}"
    fi
    
    echo
}

test_ensemble_model() {
    local model_pair=$1
    local model1=$(echo "$model_pair" | cut -d: -f1)
    local model2=$(echo "$model_pair" | cut -d: -f2)
    local name1=$(basename "$model1" .joblib)
    local name2=$(basename "$model2" .joblib)
    local test_name="ensemble_${name1}_${name2}_${TIMESTAMP}"
    
    echo -e "${BOLD}${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  Testing Ensemble:                                            ║"
    echo "║    Model 1: ${name1}$(printf '%*s' $((42 - ${#name1})) '')"
    echo "║    Model 2: ${name2}$(printf '%*s' $((42 - ${#name2})) '')"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Start two-model consumer (with venv activated)
    cd dpdk_suricata_ml_pipeline/src
    source "${VENV_PATH}/bin/activate"
    python3 two_model_consumer.py "$model1" "$model2" --train 2>&1 | tee "${SCRIPT_DIR}/logs/ml_consumer_${test_name}.log" &
    ML_PID=$!
    deactivate
    cd "$SCRIPT_DIR"
    
    echo -e "${GREEN}✓ Ensemble consumer started (PID: $ML_PID)${NC}"
    
    # Wait a moment and check if it's still running
    sleep 3
    if ! kill -0 $ML_PID 2>/dev/null; then
        echo -e "${RED}❌ Ensemble consumer failed to start!${NC}"
        echo -e "${YELLOW}Check log file: logs/ml_consumer_${test_name}.log${NC}"
        echo -e "${YELLOW}Last 20 lines:${NC}"
        tail -20 "${SCRIPT_DIR}/logs/ml_consumer_${test_name}.log" 2>/dev/null || echo "No log file found"
        return 1
    fi
    
    # Wait for replay (same as single model)
    echo -e "\n${BOLD}${YELLOW}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${YELLOW}║  ⚠️  READY - Replay CICIDS PCAP from external device          ║${NC}"
    echo -e "${BOLD}${YELLOW}║  Press ENTER when complete...                                 ║${NC}"
    echo -e "${BOLD}${YELLOW}╚═══════════════════════════════════════════════════════════════╝${NC}\n"
    
    echo -e "${CYAN}Monitoring predictions (Ctrl+C when replay done)...${NC}\n"
    
    local start_time=$(date +%s)
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if ! kill -0 $ML_PID 2>/dev/null; then
            echo -e "\n${RED}❌ Ensemble consumer stopped unexpectedly${NC}"
            break
        fi
        
        local csv_file="logs/metrics/ml_$(date +%Y%m%d).csv"
        if [ -f "$csv_file" ]; then
            local total_predictions=$(wc -l < "$csv_file")
            local attacks=$(grep -v "BENIGN" "$csv_file" 2>/dev/null | wc -l)
            local benign=$(grep "BENIGN" "$csv_file" 2>/dev/null | wc -l)
            
            echo -ne "\r${CYAN}[${elapsed}s]${NC} Predictions: ${BOLD}${total_predictions}${NC} | Attacks: ${RED}${attacks}${NC} | Benign: ${GREEN}${benign}${NC}   "
        else
            echo -ne "\r${CYAN}[${elapsed}s]${NC} Waiting for predictions...   "
        fi
        
        sleep 1
        read -t 0.1 -n 1 && break
    done
    
    echo -e "\n\n${YELLOW}Stopping ensemble consumer...${NC}"
    kill $ML_PID 2>/dev/null || true
    sleep 2
    
    local result_file="${RESULTS_DIR}/${test_name}_predictions.csv"
    if [ -f "logs/metrics/ml_$(date +%Y%m%d).csv" ]; then
        cp "logs/metrics/ml_$(date +%Y%m%d).csv" "$result_file"
        echo -e "${GREEN}✓ Predictions saved: $result_file${NC}"
    else
        echo -e "${RED}❌ No predictions file found${NC}"
    fi
    
    echo
}

validate_with_ground_truth() {
    echo -e "\n${BOLD}${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  Validating Predictions Against Ground Truth                 ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    # Create validation script
    cat > "${RESULTS_DIR}/validate_predictions.py" << 'PYEOF'
#!/usr/bin/env python3
"""
Validate ML predictions against CICIDS ground truth
"""

import pandas as pd
import numpy as np
import glob
import os
import sys
from datetime import datetime
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)

def load_ground_truth(csv_path):
    """Load CICIDS ground truth labels"""
    print(f"Loading ground truth from: {csv_path}")
    
    try:
        df = pd.read_csv(csv_path, low_memory=False)
        print(f"  ✓ Loaded {len(df)} ground truth samples")
        
        # Show label distribution
        if 'Label' in df.columns:
            print("\n  Ground Truth Label Distribution:")
            label_counts = df['Label'].value_counts()
            for label, count in label_counts.items():
                pct = (count / len(df)) * 100
                print(f"    {label:30s}: {count:8d} ({pct:5.2f}%)")
        
        return df
    except Exception as e:
        print(f"  ❌ Error loading ground truth: {e}")
        return None

def load_predictions(csv_path):
    """Load ML predictions"""
    print(f"\nLoading predictions from: {os.path.basename(csv_path)}")
    
    try:
        df = pd.read_csv(csv_path)
        print(f"  ✓ Loaded {len(df)} predictions")
        
        # Show prediction distribution
        if 'prediction' in df.columns:
            print("\n  Prediction Distribution:")
            pred_counts = df['prediction'].value_counts()
            for pred, count in pred_counts.items():
                pct = (count / len(df)) * 100
                print(f"    {pred:30s}: {count:8d} ({pct:5.2f}%)")
        
        return df
    except Exception as e:
        print(f"  ❌ Error loading predictions: {e}")
        return None

def simple_validation(predictions_df, ground_truth_df):
    """
    Simplified validation by comparing label distributions
    
    Note: Full validation requires flow-level matching (5-tuple + timestamp)
    This gives approximate metrics based on label distributions
    """
    print("\n" + "="*70)
    print("VALIDATION RESULTS (Distribution-based Approximation)")
    print("="*70)
    
    # Get label distributions
    gt_labels = ground_truth_df['Label'].value_counts()
    pred_labels = predictions_df['prediction'].value_counts()
    
    print("\nLabel Distribution Comparison:")
    print(f"{'Label':<30s} {'Ground Truth':>15s} {'Predicted':>15s} {'Difference':>15s}")
    print("-" * 70)
    
    all_labels = set(gt_labels.index) | set(pred_labels.index)
    for label in sorted(all_labels):
        gt_count = gt_labels.get(label, 0)
        pred_count = pred_labels.get(label, 0)
        diff = pred_count - gt_count
        diff_pct = (diff / gt_count * 100) if gt_count > 0 else 0
        
        print(f"{label:<30s} {gt_count:>15d} {pred_count:>15d} {diff:>10d} ({diff_pct:+.1f}%)")
    
    # Calculate basic metrics
    print("\n" + "="*70)
    print("BASIC METRICS")
    print("="*70)
    
    total_gt = len(ground_truth_df)
    total_pred = len(predictions_df)
    
    gt_benign = gt_labels.get('BENIGN', 0)
    gt_attacks = total_gt - gt_benign
    
    pred_benign = pred_labels.get('BENIGN', 0)
    pred_attacks = total_pred - pred_benign
    
    print(f"\nTotal Samples:")
    print(f"  Ground Truth:  {total_gt:,}")
    print(f"  Predictions:   {total_pred:,}")
    print(f"  Coverage:      {(total_pred/total_gt)*100:.2f}%")
    
    print(f"\nBenign vs Attack:")
    print(f"  Ground Truth - Benign:  {gt_benign:,} ({(gt_benign/total_gt)*100:.2f}%)")
    print(f"  Ground Truth - Attacks: {gt_attacks:,} ({(gt_attacks/total_gt)*100:.2f}%)")
    print(f"  Predicted - Benign:     {pred_benign:,} ({(pred_benign/total_pred)*100:.2f}%)")
    print(f"  Predicted - Attacks:    {pred_attacks:,} ({(pred_attacks/total_pred)*100:.2f}%)")
    
    # Approximate detection rate
    detection_rate = (pred_attacks / gt_attacks * 100) if gt_attacks > 0 else 0
    print(f"\nApproximate Detection Rate: {detection_rate:.2f}%")
    
    # Check for common issues
    print("\n" + "="*70)
    print("OBSERVATIONS")
    print("="*70)
    
    if pred_benign > gt_benign * 1.5:
        print("⚠️  WARNING: High benign predictions - possible false negatives")
    
    if pred_attacks > gt_attacks * 1.5:
        print("⚠️  WARNING: High attack predictions - possible false positives")
    
    if total_pred < total_gt * 0.5:
        print("⚠️  WARNING: Low prediction coverage - many flows not classified")
    
    if abs(detection_rate - 100) < 10:
        print("✓  Good: Detection rate close to 100%")
    
    print("\n" + "="*70)
    print("NOTE: For accurate metrics, implement flow-level matching")
    print("      Match on: Source IP, Dest IP, Source Port, Dest Port, Timestamp")
    print("="*70 + "\n")

def main():
    results_dir = os.path.dirname(os.path.abspath(__file__))
    ground_truth_csv = os.path.join(
        os.path.dirname(results_dir),
        "dpdk_suricata_ml_pipeline/dataset/Wednesday-workingHours.pcap_ISCX.csv"
    )
    
    # Load ground truth
    ground_truth = load_ground_truth(ground_truth_csv)
    if ground_truth is None:
        sys.exit(1)
    
    # Process each prediction file
    prediction_files = glob.glob(os.path.join(results_dir, "*_predictions.csv"))
    
    if not prediction_files:
        print("\n❌ No prediction files found in results directory")
        sys.exit(1)
    
    print(f"\nFound {len(prediction_files)} prediction file(s) to validate\n")
    
    for pred_file in sorted(prediction_files):
        print("\n" + "#"*70)
        print(f"# {os.path.basename(pred_file)}")
        print("#"*70)
        
        predictions = load_predictions(pred_file)
        if predictions is not None:
            simple_validation(predictions, ground_truth)
    
    print("\n✓ Validation complete!\n")

if __name__ == "__main__":
    main()
PYEOF
    
    chmod +x "${RESULTS_DIR}/validate_predictions.py"
    
    # Run validation (with venv)
    source "${VENV_PATH}/bin/activate"
    python3 "${RESULTS_DIR}/validate_predictions.py"
    deactivate
}

generate_summary_report() {
    local report_file="${RESULTS_DIR}/test_summary_${TIMESTAMP}.txt"
    
    echo -e "\n${CYAN}Generating summary report...${NC}"
    
    cat > "$report_file" << EOF
================================================================================
IDS Testing Summary Report
================================================================================
Generated: $(date)
Dataset: Wednesday-workingHours (CICIDS2017)

TEST CONFIGURATION:
-------------------
Models Tested: ${#MODELS[@]} single models + ${#ENSEMBLES[@]} ensemble models
Ground Truth: dpdk_suricata_ml_pipeline/dataset/Wednesday-workingHours.pcap_ISCX.csv

PREDICTION FILES:
-----------------
EOF
    
    for result in "$RESULTS_DIR"/*_predictions.csv; do
        if [ -f "$result" ]; then
            local filename=$(basename "$result")
            local line_count=$(wc -l < "$result")
            echo "$filename: $line_count predictions" >> "$report_file"
        fi
    done
    
    cat >> "$report_file" << EOF

VALIDATION:
-----------
See validation results above for detailed metrics

NEXT STEPS:
-----------
1. Review validation results for each model
2. Compare detection rates and false positive rates
3. Identify best performing model/ensemble
4. Analyze specific attack types in CSV files
5. Consider implementing flow-level matching for exact metrics

FILES LOCATION:
---------------
All results saved in: $RESULTS_DIR

================================================================================
EOF
    
    echo -e "${GREEN}✓ Summary report saved: $report_file${NC}"
}

show_menu() {
    echo -e "${BOLD}${CYAN}Test Options:${NC}"
    echo -e "  ${BOLD}1)${NC} Test single models only"
    echo -e "  ${BOLD}2)${NC} Test ensemble models only"
    echo -e "  ${BOLD}3)${NC} Test all models (single + ensemble)"
    echo -e "  ${BOLD}4)${NC} Test specific model (custom)"
    echo -e "  ${BOLD}0)${NC} Exit"
    echo
}

test_custom_model() {
    echo -e "\n${CYAN}Available models:${NC}"
    ls -1 "ML Models/"*.joblib | nl -w2 -s') '
    echo
    read -p "Enter model filename (or two models separated by space for ensemble): " model_input
    
    if [[ "$model_input" == *" "* ]]; then
        # Ensemble
        local model1=$(echo "$model_input" | awk '{print $1}')
        local model2=$(echo "$model_input" | awk '{print $2}')
        cleanup_before_test
        start_ids_pipeline
        test_ensemble_model "${model1}:${model2}"
    else
        # Single model
        cleanup_before_test
        start_ids_pipeline
        test_single_model "$model_input"
    fi
}

main() {
    print_header
    check_prerequisites
    
    while true; do
        show_menu
        read -p "Select option: " choice
        
        case $choice in
            1)
                echo -e "\n${BOLD}${GREEN}Testing single models...${NC}\n"
                for model in "${MODELS[@]}"; do
                    cleanup_before_test
                    start_ids_pipeline
                    test_single_model "$model"
                done
                validate_with_ground_truth
                generate_summary_report
                echo -e "\n${BOLD}${GREEN}✓ All single model tests complete!${NC}"
                break
                ;;
            2)
                echo -e "\n${BOLD}${GREEN}Testing ensemble models...${NC}\n"
                for ensemble in "${ENSEMBLES[@]}"; do
                    cleanup_before_test
                    start_ids_pipeline
                    test_ensemble_model "$ensemble"
                done
                validate_with_ground_truth
                generate_summary_report
                echo -e "\n${BOLD}${GREEN}✓ All ensemble tests complete!${NC}"
                break
                ;;
            3)
                echo -e "\n${BOLD}${GREEN}Testing all models...${NC}\n"
                for model in "${MODELS[@]}"; do
                    cleanup_before_test
                    start_ids_pipeline
                    test_single_model "$model"
                done
                for ensemble in "${ENSEMBLES[@]}"; do
                    cleanup_before_test
                    start_ids_pipeline
                    test_ensemble_model "$ensemble"
                done
                validate_with_ground_truth
                generate_summary_report
                echo -e "\n${BOLD}${GREEN}✓ All tests complete!${NC}"
                break
                ;;
            4)
                test_custom_model
                validate_with_ground_truth
                generate_summary_report
                echo -e "\n${BOLD}${GREEN}✓ Custom test complete!${NC}"
                break
                ;;
            0)
                echo -e "${YELLOW}Exiting...${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option. Please try again.${NC}\n"
                ;;
        esac
    done
    
    echo -e "\n${CYAN}Results saved in: ${BOLD}$RESULTS_DIR${NC}"
    echo -e "${CYAN}You can now analyze the CSV files and validation results${NC}\n"
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}Test interrupted. Cleaning up...${NC}"; sudo ./run_afpacket_mode.sh stop > /dev/null 2>&1; exit 1' INT

main "$@"
