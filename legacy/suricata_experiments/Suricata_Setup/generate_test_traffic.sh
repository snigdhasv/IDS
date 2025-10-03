#!/bin/bash

# Advanced Traffic Generator for Suricata Testing
# Generates various types of network traffic to trigger Suricata events

set -e

# Configuration
INTERFACE="eth0"  # Update with your interface
TARGET_IP="8.8.8.8"
LOCAL_IP=$(ip route get 8.8.8.8 | awk '{print $7; exit}')
TEST_DURATION=60
PACKETS_PER_SECOND=100

echo "=== Advanced Traffic Generator for Suricata Testing ==="
echo "Interface: $INTERFACE"
echo "Local IP: $LOCAL_IP"
echo "Test Duration: ${TEST_DURATION}s"
echo "=================================================="

function install_dependencies() {
    echo "Checking and installing dependencies..."
    
    # Check for required tools
    local tools=("hping3" "nmap" "curl" "nc" "dig")
    local missing_tools=()
    
    for tool in "${tools[@]}"; do
        if ! command -v $tool &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        echo "Installing missing tools: ${missing_tools[*]}"
        sudo apt-get update
        sudo apt-get install -y "${missing_tools[@]}"
    fi
    
    echo "✅ All dependencies available"
}

function generate_http_traffic() {
    echo "🌐 Generating HTTP traffic..."
    
    # Normal HTTP requests
    curl -s http://www.google.com > /dev/null &
    curl -s http://www.github.com > /dev/null &
    curl -s http://httpbin.org/get > /dev/null &
    
    # HTTP requests that might trigger alerts
    curl -s "http://testmyids.com/uid/index.html?testparam=../../../../etc/passwd" > /dev/null &
    curl -s -H "User-Agent: sqlmap/1.0" http://httpbin.org/get > /dev/null &
    curl -s -H "User-Agent: <script>alert('xss')</script>" http://httpbin.org/get > /dev/null &
    
    # Large HTTP requests
    curl -s -d "$(head -c 10000 /dev/zero | tr '\0' 'A')" http://httpbin.org/post > /dev/null &
    
    echo "HTTP traffic generated"
}

function generate_dns_traffic() {
    echo "🔍 Generating DNS traffic..."
    
    # Normal DNS queries
    dig @8.8.8.8 google.com > /dev/null &
    dig @8.8.8.8 github.com > /dev/null &
    dig @1.1.1.1 cloudflare.com > /dev/null &
    
    # Suspicious DNS queries
    dig @8.8.8.8 malware.testcategory.com > /dev/null &
    dig @8.8.8.8 botnet.example.com > /dev/null &
    dig @8.8.8.8 $(head -c 200 /dev/urandom | base64 | tr -d '\n' | head -c 50).com > /dev/null &
    
    # DNS tunneling simulation
    for i in {1..5}; do
        dig @8.8.8.8 TXT "$(head -c 100 /dev/urandom | base64 | tr -d '\n' | head -c 60).tunnel.example.com" > /dev/null &
    done
    
    echo "DNS traffic generated"
}

function generate_port_scans() {
    echo "🔍 Generating port scan traffic..."
    
    # TCP SYN scan simulation
    if command -v hping3 &> /dev/null; then
        # Scan common ports
        for port in 21 22 23 25 53 80 110 143 443 993 995 3389 5432 3306; do
            timeout 1 hping3 -S -p $port -c 1 $TARGET_IP > /dev/null 2>&1 &
        done
        
        # UDP scan simulation
        for port in 53 67 68 69 123 161 162; do
            timeout 1 hping3 -2 -p $port -c 1 $TARGET_IP > /dev/null 2>&1 &
        done
    else
        # Fallback to nc
        for port in 21 22 23 25 53 80 110 143 443; do
            timeout 1 nc -z $TARGET_IP $port > /dev/null 2>&1 &
        done
    fi
    
    echo "Port scan traffic generated"
}

function generate_ssh_traffic() {
    echo "🔐 Generating SSH-like traffic..."
    
    # Simulate SSH brute force attempts
    for user in admin root administrator test guest; do
        timeout 2 ssh -o ConnectTimeout=1 -o StrictHostKeyChecking=no $user@$TARGET_IP exit > /dev/null 2>&1 &
    done
    
    echo "SSH traffic generated"
}

function generate_ftp_traffic() {
    echo "📁 Generating FTP-like traffic..."
    
    # Simulate FTP connections
    for i in {1..3}; do
        timeout 2 nc -w 1 $TARGET_IP 21 > /dev/null 2>&1 &
    done
    
    echo "FTP traffic generated"
}

function generate_smtp_traffic() {
    echo "📧 Generating SMTP-like traffic..."
    
    # Simulate SMTP connections
    for i in {1..3}; do
        timeout 2 nc -w 1 $TARGET_IP 25 > /dev/null 2>&1 &
    done
    
    echo "SMTP traffic generated"
}

function generate_malware_signatures() {
    echo "🦠 Generating malware signature traffic..."
    
    # Simulate malware communication patterns
    curl -s -H "User-Agent: Malware-Agent" http://httpbin.org/get > /dev/null &
    curl -s "http://httpbin.org/get?cmd=whoami" > /dev/null &
    curl -s "http://httpbin.org/get?exec=id" > /dev/null &
    
    # Simulate C&C communication
    curl -s -d "infected_host=$LOCAL_IP" http://httpbin.org/post > /dev/null &
    
    echo "Malware signature traffic generated"
}

function generate_dos_simulation() {
    echo "💥 Generating DoS simulation traffic..."
    
    if command -v hping3 &> /dev/null; then
        # TCP flood simulation (low rate to avoid actual DoS)
        timeout 5 hping3 -S -p 80 -i u1000 $TARGET_IP > /dev/null 2>&1 &
        
        # UDP flood simulation
        timeout 5 hping3 -2 -p 53 -i u1000 $TARGET_IP > /dev/null 2>&1 &
        
        # ICMP flood simulation
        timeout 5 hping3 -1 -i u1000 $TARGET_IP > /dev/null 2>&1 &
    fi
    
    echo "DoS simulation traffic generated"
}

function generate_protocol_anomalies() {
    echo "⚠️ Generating protocol anomaly traffic..."
    
    if command -v hping3 &> /dev/null; then
        # Malformed packets
        timeout 2 hping3 -S -p 80 -M 1234 -L 5678 $TARGET_IP > /dev/null 2>&1 &
        
        # Fragmented packets
        timeout 2 hping3 -S -p 80 -f $TARGET_IP > /dev/null 2>&1 &
        
        # Large packets
        timeout 2 hping3 -S -p 80 -d 65000 $TARGET_IP > /dev/null 2>&1 &
    fi
    
    echo "Protocol anomaly traffic generated"
}

function monitor_progress() {
    echo "📊 Monitoring traffic generation progress..."
    
    local start_time=$(date +%s)
    local end_time=$((start_time + TEST_DURATION))
    
    while [ $(date +%s) -lt $end_time ]; do
        local elapsed=$(($(date +%s) - start_time))
        local remaining=$((TEST_DURATION - elapsed))
        
        echo -ne "\rProgress: ${elapsed}/${TEST_DURATION}s | Remaining: ${remaining}s | Active jobs: $(jobs -r | wc -l)"
        sleep 1
    done
    
    echo -e "\n✅ Traffic generation completed"
}

function cleanup() {
    echo "🧹 Cleaning up background processes..."
    
    # Kill all background jobs
    jobs -p | xargs -r kill > /dev/null 2>&1 || true
    wait > /dev/null 2>&1 || true
    
    echo "Cleanup completed"
}

function main() {
    trap cleanup EXIT
    
    echo "Starting traffic generation at $(date)"
    echo "========================================"
    
    # Install dependencies
    install_dependencies
    
    echo "Generating diverse network traffic..."
    echo "This will create various types of network traffic to trigger Suricata events:"
    echo "- HTTP requests (normal and suspicious)"
    echo "- DNS queries (normal and tunneling attempts)"
    echo "- Port scans"
    echo "- SSH brute force simulation"
    echo "- FTP/SMTP connection attempts"
    echo "- Malware signature traffic"
    echo "- DoS simulation (low intensity)"
    echo "- Protocol anomalies"
    echo ""
    
    # Generate different types of traffic
    generate_http_traffic
    sleep 2
    
    generate_dns_traffic
    sleep 2
    
    generate_port_scans
    sleep 2
    
    generate_ssh_traffic
    sleep 2
    
    generate_ftp_traffic
    sleep 2
    
    generate_smtp_traffic
    sleep 2
    
    generate_malware_signatures
    sleep 2
    
    generate_dos_simulation
    sleep 2
    
    generate_protocol_anomalies
    sleep 2
    
    # Monitor progress
    monitor_progress
    
    echo "========================================"
    echo "🎉 Traffic generation completed!"
    echo "Generated traffic should trigger various Suricata events:"
    echo "- Alerts for suspicious patterns"
    echo "- Flow records for connections"
    echo "- HTTP events for web traffic"
    echo "- DNS events for queries"
    echo "- Anomaly events for protocol violations"
    echo ""
    echo "Check Kafka topics for events:"
    echo "- suricata-events: All events"
    echo "- suricata-alerts: Security alerts"
    echo "- suricata-stats: Performance statistics"
    echo "========================================"
}

# Check if running as root for some operations
if [ "$EUID" -ne 0 ] && command -v hping3 &> /dev/null; then
    echo "⚠️  Warning: Some traffic generation features require root privileges"
    echo "   Run with 'sudo' for full functionality"
fi

# Run main function
main "$@"
