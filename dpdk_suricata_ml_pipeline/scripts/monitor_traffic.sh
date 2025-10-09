#!/bin/bash

# Traffic & Alert Monitoring Script
# Easy way to view live IDS pipeline activity

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

clear
echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║  IDS Traffic & Alert Monitor                           ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo

echo -e "${YELLOW}Select monitoring option:${NC}\n"
echo -e "  ${GREEN}1${NC}) Live Suricata Events (all types)"
echo -e "  ${GREEN}2${NC}) Live Alerts Only"
echo -e "  ${GREEN}3${NC}) Live Flow Events"
echo -e "  ${GREEN}4${NC}) Live DNS Queries"
echo -e "  ${GREEN}5${NC}) Live HTTP Requests"
echo -e "  ${GREEN}6${NC}) Event Statistics"
echo -e "  ${GREEN}7${NC}) Recent Alerts (last 20)"
echo -e "  ${GREEN}8${NC}) Search by IP Address"
echo -e "  ${GREEN}9${NC}) ML Consumer Output (live)"
echo -e "  ${CYAN}10${NC}) Kafka Events Stream"
echo -e "  ${RED}0${NC}) Exit"
echo

read -p "Enter choice [0-10]: " choice

case $choice in
    1)
        echo -e "\n${BOLD}${CYAN}=== Live Suricata Events (Press Ctrl+C to stop) ===${NC}\n"
        tail -f /var/log/suricata/eve.json | jq --color-output '
            {
                time: .timestamp,
                type: .event_type,
                src: (.src_ip // "N/A"),
                dst: (.dest_ip // "N/A"),
                proto: (.proto // "N/A")
            }'
        ;;
        
    2)
        echo -e "\n${BOLD}${RED}=== Live Alerts (Press Ctrl+C to stop) ===${NC}\n"
        tail -f /var/log/suricata/eve.json | grep --line-buffered '"event_type":"alert"' | jq --color-output '
            {
                time: .timestamp,
                severity: .alert.severity,
                signature: .alert.signature,
                category: .alert.category,
                src: (.src_ip + ":" + (.src_port|tostring)),
                dst: (.dest_ip + ":" + (.dest_port|tostring)),
                proto: .proto
            }'
        ;;
        
    3)
        echo -e "\n${BOLD}${GREEN}=== Live Flow Events (Press Ctrl+C to stop) ===${NC}\n"
        tail -f /var/log/suricata/eve.json | grep --line-buffered '"event_type":"flow"' | jq --color-output '
            {
                time: .timestamp,
                src: (.src_ip + ":" + (.src_port|tostring)),
                dst: (.dest_ip + ":" + (.dest_port|tostring)),
                proto: .proto,
                pkts: .flow.pkts_toserver,
                bytes: .flow.bytes_toserver,
                state: .flow.state
            }'
        ;;
        
    4)
        echo -e "\n${BOLD}${MAGENTA}=== Live DNS Queries (Press Ctrl+C to stop) ===${NC}\n"
        tail -f /var/log/suricata/eve.json | grep --line-buffered '"event_type":"dns"' | jq --color-output '
            {
                time: .timestamp,
                query: .dns.rrname,
                type: .dns.rrtype,
                answer: (.dns.answers[0].rdata // "no answer"),
                src_ip: .src_ip
            }'
        ;;
        
    5)
        echo -e "\n${BOLD}${CYAN}=== Live HTTP Requests (Press Ctrl+C to stop) ===${NC}\n"
        tail -f /var/log/suricata/eve.json | grep --line-buffered '"event_type":"http"' | jq --color-output '
            {
                time: .timestamp,
                method: .http.http_method,
                host: .http.hostname,
                url: .http.url,
                status: .http.status,
                src: .src_ip
            }'
        ;;
        
    6)
        echo -e "\n${BOLD}${BLUE}=== Event Statistics ===${NC}\n"
        
        echo -e "${CYAN}Event Type Counts:${NC}"
        grep -o '"event_type":"[^"]*"' /var/log/suricata/eve.json | \
            cut -d'"' -f4 | sort | uniq -c | sort -rn
        
        echo -e "\n${CYAN}Total Events:${NC} $(wc -l < /var/log/suricata/eve.json)"
        
        echo -e "\n${CYAN}Alerts by Severity:${NC}"
        grep '"event_type":"alert"' /var/log/suricata/eve.json | \
            jq -r '.alert.severity' | sort | uniq -c | sort -n || echo "No alerts"
        
        echo -e "\n${CYAN}Top 10 Source IPs:${NC}"
        grep '"src_ip"' /var/log/suricata/eve.json | \
            grep -o '"src_ip":"[^"]*"' | cut -d'"' -f4 | \
            sort | uniq -c | sort -rn | head -10
        
        echo -e "\n${CYAN}Top 10 Destination IPs:${NC}"
        grep '"dest_ip"' /var/log/suricata/eve.json | \
            grep -o '"dest_ip":"[^"]*"' | cut -d'"' -f4 | \
            sort | uniq -c | sort -rn | head -10
        
        echo -e "\n${CYAN}Top Alert Signatures:${NC}"
        grep '"event_type":"alert"' /var/log/suricata/eve.json | \
            jq -r '.alert.signature' | sort | uniq -c | sort -rn | head -10 || echo "No alerts"
        ;;
        
    7)
        echo -e "\n${BOLD}${RED}=== Recent Alerts (Last 20) ===${NC}\n"
        grep '"event_type":"alert"' /var/log/suricata/eve.json | tail -20 | jq --color-output '
            {
                time: .timestamp,
                severity: .alert.severity,
                signature: .alert.signature,
                src: (.src_ip + ":" + (.src_port|tostring)),
                dst: (.dest_ip + ":" + (.dest_port|tostring))
            }' || echo "No alerts found"
        ;;
        
    8)
        echo
        read -p "Enter IP address to search: " ip_addr
        echo -e "\n${BOLD}${CYAN}=== Events involving ${ip_addr} ===${NC}\n"
        
        grep "$ip_addr" /var/log/suricata/eve.json | jq --color-output '
            {
                time: .timestamp,
                type: .event_type,
                src: (.src_ip // "N/A"),
                dst: (.dest_ip // "N/A"),
                signature: (.alert.signature // "N/A")
            }'
        ;;
        
    9)
        echo -e "\n${BOLD}${GREEN}=== ML Consumer Output (Press Ctrl+C to stop) ===${NC}\n"
        
        # Show current ML consumer log
        echo -e "${YELLOW}Recent ML Predictions:${NC}\n"
        grep "ML Alert:" ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log | tail -10
        
        echo -e "\n${YELLOW}Live ML Consumer Output:${NC}\n"
        tail -f ~/Programming/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.out
        ;;
        
    10)
        echo -e "\n${BOLD}${CYAN}=== Kafka Events Stream (Press Ctrl+C to stop) ===${NC}\n"
        
        echo -e "${YELLOW}Choose Kafka topic:${NC}"
        echo -e "  1) suricata-alerts (from Suricata)"
        echo -e "  2) ml-predictions (ML results)"
        read -p "Choice [1-2]: " kafka_choice
        
        if [ "$kafka_choice" = "1" ]; then
            echo -e "\n${CYAN}Streaming from suricata-alerts...${NC}\n"
            /opt/kafka/bin/kafka-console-consumer.sh \
                --bootstrap-server localhost:9092 \
                --topic suricata-alerts | jq --color-output .
        elif [ "$kafka_choice" = "2" ]; then
            echo -e "\n${CYAN}Streaming from ml-predictions...${NC}\n"
            /opt/kafka/bin/kafka-console-consumer.sh \
                --bootstrap-server localhost:9092 \
                --topic ml-predictions | jq --color-output .
        fi
        ;;
        
    0)
        echo -e "${GREEN}Goodbye!${NC}"
        exit 0
        ;;
        
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo
echo -e "\n${GREEN}Monitoring session ended${NC}"
