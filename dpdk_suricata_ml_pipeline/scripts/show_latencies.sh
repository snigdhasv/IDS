#!/bin/bash
#
# Quick Latency Breakdown
#
# Shows current latency metrics for each pipeline component.
# Useful for quickly identifying bottlenecks.
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
METRICS_DIR="$(dirname "$SCRIPT_DIR")/logs/metrics"
DATE=$(date +%Y%m%d)
METRICS_FILE="${METRICS_DIR}/metrics_${DATE}.jsonl"

if [ ! -f "$METRICS_FILE" ]; then
    echo -e "${RED}❌ No metrics file found for today${NC}"
    echo -e "${YELLOW}Looking for: $METRICS_FILE${NC}"
    echo ""
    echo "Make sure the pipeline is running and generating metrics."
    exit 1
fi

echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║         PIPELINE COMPONENT LATENCY BREAKDOWN               ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to calculate stats for a component/operation
calc_stats() {
    local component=$1
    local operation=$2
    local label=$3
    
    # Extract latencies for this component.operation
    latencies=$(grep '"type":"latency"' "$METRICS_FILE" | \
                grep "\"component\":\"$component\"" | \
                grep "\"operation\":\"$operation\"" | \
                jq -r '.latency_ms' 2>/dev/null)
    
    if [ -z "$latencies" ]; then
        return 1
    fi
    
    # Calculate stats using awk
    stats=$(echo "$latencies" | awk '
    BEGIN { 
        count=0; sum=0; min=999999; max=0; 
    }
    {
        values[count++]=$1
        sum+=$1
        if($1<min) min=$1
        if($1>max) max=$1
    }
    END {
        if(count==0) exit 1
        mean=sum/count
        
        # Sort for percentiles
        n = asort(values)
        p50 = values[int(n*0.50)]
        p95 = values[int(n*0.95)]
        p99 = values[int(n*0.99)]
        
        printf "%d %.2f %.2f %.2f %.2f %.2f %.2f\n", count, mean, min, max, p50, p95, p99
    }')
    
    if [ $? -eq 0 ] && [ -n "$stats" ]; then
        read count mean min max p50 p95 p99 <<< "$stats"
        printf "${CYAN}%-40s${NC} ${GREEN}%6.2f${NC} ${YELLOW}%6.2f${NC} ${RED}%6.2f${NC} (n=%d)\n" \
               "$label" "$mean" "$p95" "$p99" "$count"
        return 0
    fi
    
    return 1
}

echo -e "${BOLD}Component / Operation                       Mean    P95    P99  ${NC}"
echo -e "────────────────────────────────────────────────────────────────"

# Ensemble Consumer Components
echo -e "${BOLD}Ensemble ML Consumer:${NC}"
calc_stats "ensemble_consumer" "feature_extraction" "  ↳ Feature Extraction" || echo -e "  ↳ Feature Extraction: ${YELLOW}No data${NC}"
calc_stats "ensemble_consumer" "model1_inference" "  ↳ Model 1 Inference" || echo -e "  ↳ Model 1 Inference: ${YELLOW}No data${NC}"
calc_stats "ensemble_consumer" "model2_inference" "  ↳ Model 2 Inference" || echo -e "  ↳ Model 2 Inference: ${YELLOW}No data${NC}"
calc_stats "ensemble_consumer" "meta_learner_inference" "  ↳ Meta-Learner" || echo -e "  ↳ Meta-Learner: ${YELLOW}No data${NC}"
calc_stats "ensemble_consumer" "flow_processing_total" "  ↳ Total Flow Processing" || echo -e "  ↳ Total Flow Processing: ${YELLOW}No data${NC}"
echo ""

# Single Model Consumer
echo -e "${BOLD}Single Model ML Consumer:${NC}"
calc_stats "ml_consumer" "feature_extraction" "  ↳ Feature Extraction" || echo -e "  ↳ Feature Extraction: ${YELLOW}No data${NC}"
calc_stats "ml_consumer" "ml_inference" "  ↳ ML Inference" || echo -e "  ↳ ML Inference: ${YELLOW}No data${NC}"
calc_stats "ml_consumer" "flow_processing" "  ↳ Flow Processing" || echo -e "  ↳ Flow Processing: ${YELLOW}No data${NC}"
echo ""

# Kafka Bridge
echo -e "${BOLD}Kafka Bridge:${NC}"
calc_stats "kafka_bridge" "kafka_send" "  ↳ Kafka Send" || echo -e "  ↳ Kafka Send: ${YELLOW}No data${NC}"
calc_stats "kafka_bridge" "event_processing" "  ↳ Event Processing" || echo -e "  ↳ Event Processing: ${YELLOW}No data${NC}"
calc_stats "kafka_bridge" "json_parse" "  ↳ JSON Parse" || echo -e "  ↳ JSON Parse: ${YELLOW}No data${NC}"
echo ""

# Suricata
echo -e "${BOLD}Suricata:${NC}"
calc_stats "suricata" "packet_processing" "  ↳ Packet Processing" || echo -e "  ↳ Packet Processing: ${YELLOW}No data${NC}"
calc_stats "suricata" "flow_export" "  ↳ Flow Export" || echo -e "  ↳ Flow Export: ${YELLOW}No data${NC}"
echo ""

echo -e "────────────────────────────────────────────────────────────────"
echo -e "${CYAN}Legend:${NC} Mean = Average | P95 = 95th percentile | P99 = 99th percentile"
echo -e "${CYAN}All times in milliseconds${NC}"
echo ""

# Show recommendations based on latencies
echo -e "${BOLD}${YELLOW}💡 Performance Tips:${NC}"
echo ""

# Check if any component is slow
total_flow=$(grep '"operation":"flow_processing_total"' "$METRICS_FILE" 2>/dev/null | jq -r '.latency_ms' | awk '{sum+=$1; count++} END {if(count>0) print sum/count; else print 0}')

if [ -n "$total_flow" ] && [ $(echo "$total_flow > 50" | bc -l 2>/dev/null || echo 0) -eq 1 ]; then
    echo -e "${YELLOW}⚠️  High total latency detected (>50ms average)${NC}"
    echo -e "   Consider:"
    echo -e "   • Using lighter ML models (Decision Tree, Logistic Regression)"
    echo -e "   • Checking system resources (CPU/RAM)"
    echo -e "   • Verifying network connectivity"
    echo ""
fi

# Check if specific stages are slow
model1_latency=$(grep '"operation":"model1_inference"' "$METRICS_FILE" 2>/dev/null | jq -r '.latency_ms' | awk '{sum+=$1; count++} END {if(count>0) print sum/count; else print 0}')
if [ -n "$model1_latency" ] && [ $(echo "$model1_latency > 20" | bc -l 2>/dev/null || echo 0) -eq 1 ]; then
    echo -e "${YELLOW}⚠️  Model 1 inference is slow (>20ms average)${NC}"
    echo -e "   Model 1 may be complex - consider using a faster algorithm"
    echo ""
fi

model2_latency=$(grep '"operation":"model2_inference"' "$METRICS_FILE" 2>/dev/null | jq -r '.latency_ms' | awk '{sum+=$1; count++} END {if(count>0) print sum/count; else print 0}')
if [ -n "$model2_latency" ] && [ $(echo "$model2_latency > 20" | bc -l 2>/dev/null || echo 0) -eq 1 ]; then
    echo -e "${YELLOW}⚠️  Model 2 inference is slow (>20ms average)${NC}"
    echo -e "   Model 2 may be complex - consider using a faster algorithm"
    echo ""
fi

echo -e "${GREEN}✓ Latency analysis complete${NC}"
echo -e "${CYAN}For real-time monitoring, use:${NC} ./monitor_metrics.sh"
echo ""
