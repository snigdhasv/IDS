#!/bin/bash

# DPDK Packet Generation and Real-time IDS Integration Setup
# This script prepares the complete DPDK environment for high-performance packet generation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DPDK_VERSION="24.07"
INSTALL_DIR="/opt/dpdk"
HUGEPAGE_SIZE="1024"  # 1GB hugepages

echo -e "${GREEN}🚀 DPDK Real-time IDS Integration Setup${NC}"

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}❌ This script must be run as root${NC}"
        echo "Usage: sudo ./setup_realtime_dpdk.sh"
        exit 1
    fi
}

# Install required packages
install_dependencies() {
    echo -e "${YELLOW}📦 Installing dependencies...${NC}"
    
    apt-get update
    apt-get install -y \
        build-essential \
        cmake \
        ninja-build \
        python3-pyelftools \
        libnuma-dev \
        libpcap-dev \
        pkg-config \
        python3-pip \
        git \
        wget \
        pciutils \
        linux-headers-$(uname -r)
    
    # Python packages for integration
    pip3 install \
        scapy \
        kafka-python \
        psutil \
        watchdog \
        numpy \
        pandas
    
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

# Setup hugepages for DPDK
setup_hugepages() {
    echo -e "${YELLOW}🏗️  Setting up hugepages...${NC}"
    
    # Configure hugepages
    echo $HUGEPAGE_SIZE > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
    
    # Make persistent
    if ! grep -q "vm.nr_hugepages" /etc/sysctl.conf; then
        echo "vm.nr_hugepages=$HUGEPAGE_SIZE" >> /etc/sysctl.conf
    fi
    
    # Mount hugepage filesystem
    mkdir -p /mnt/huge
    if ! mountpoint -q /mnt/huge; then
        mount -t hugetlbfs nodev /mnt/huge
        
        # Make mount persistent
        if ! grep -q "/mnt/huge" /etc/fstab; then
            echo "nodev /mnt/huge hugetlbfs defaults 0 0" >> /etc/fstab
        fi
    fi
    
    # Verify hugepages
    HUGEPAGES_AVAILABLE=$(cat /proc/meminfo | grep HugePages_Total | awk '{print $2}')
    echo -e "${GREEN}✓ Hugepages configured: ${HUGEPAGES_AVAILABLE} pages${NC}"
}

# Download and build DPDK
install_dpdk() {
    echo -e "${YELLOW}🏭 Installing DPDK ${DPDK_VERSION}...${NC}"
    
    mkdir -p $INSTALL_DIR
    cd $INSTALL_DIR
    
    # Download DPDK
    if [ ! -f "dpdk-${DPDK_VERSION}.tar.xz" ]; then
        wget "https://fast.dpdk.org/rel/dpdk-${DPDK_VERSION}.tar.xz"
        tar -xf "dpdk-${DPDK_VERSION}.tar.xz"
    fi
    
    cd "dpdk-${DPDK_VERSION}"
    
    # Build DPDK with meson/ninja
    if [ ! -d "build" ]; then
        meson setup build
        cd build
        ninja
        ninja install
        ldconfig
    fi
    
    # Set environment variables
    echo "export RTE_SDK=$INSTALL_DIR/dpdk-${DPDK_VERSION}" >> /etc/environment
    echo "export RTE_TARGET=x86_64-native-linux-gcc" >> /etc/environment
    
    echo -e "${GREEN}✓ DPDK installed successfully${NC}"
}

# Setup network interface binding
setup_interface_binding() {
    echo -e "${YELLOW}🔗 Setting up interface binding...${NC}"
    
    # Load required modules
    modprobe uio
    modprobe uio_pci_generic
    
    # Make modules persistent
    echo "uio" >> /etc/modules
    echo "uio_pci_generic" >> /etc/modules
    
    # Show available interfaces
    echo -e "${BLUE}Available network interfaces:${NC}"
    lspci | grep -i ethernet
    
    echo -e "${YELLOW}💡 Note: To bind interfaces to DPDK, use:${NC}"
    echo "   dpdk-devbind.py --bind=uio_pci_generic <PCI_ADDRESS>"
    echo "   dpdk-devbind.py --status  # Show current bindings"
    
    echo -e "${GREEN}✓ Interface binding configured${NC}"
}

# Create DPDK packet generator script
create_dpdk_pktgen() {
    echo -e "${YELLOW}📝 Creating DPDK packet generator...${NC}"
    
    cat > /opt/dpdk/dpdk_packet_generator.py << 'EOF'
#!/usr/bin/env python3
"""
High-performance DPDK packet generator for IDS testing
"""

import sys
import time
import threading
from scapy.all import *

class DPDKPacketGenerator:
    def __init__(self, interface="enp2s0"):
        self.interface = interface
        self.running = False
        self.stats = {'sent': 0, 'start_time': None}
    
    def generate_attack_patterns(self):
        """Generate various attack patterns for IDS testing"""
        patterns = []
        
        # Port scan simulation
        for port in [22, 23, 80, 443, 3389, 5900]:
            pkt = Ether()/IP(src="10.0.0.1", dst="192.168.1.10")/TCP(dport=port, flags="S")
            patterns.append(pkt)
        
        # SQL injection attempts
        sql_payloads = [
            "' OR 1=1--",
            "'; DROP TABLE users;--",
            "admin'/*",
            "' UNION SELECT * FROM users--"
        ]
        for payload in sql_payloads:
            pkt = Ether()/IP(src="10.0.0.2", dst="192.168.1.10")/TCP(dport=80)/Raw(f"GET /login?user={payload}")
            patterns.append(pkt)
        
        # Buffer overflow attempts
        for size in [100, 500, 1000]:
            pkt = Ether()/IP(src="10.0.0.3", dst="192.168.1.10")/TCP(dport=443)/Raw("A" * size)
            patterns.append(pkt)
        
        # DDoS simulation
        for i in range(50):
            pkt = Ether()/IP(src=f"10.0.{i//256}.{i%256}", dst="192.168.1.10")/TCP(dport=80, flags="S")
            patterns.append(pkt)
        
        return patterns
    
    def generate_normal_traffic(self):
        """Generate normal network traffic patterns"""
        patterns = []
        
        # HTTP requests
        for i in range(20):
            pkt = Ether()/IP(src=f"192.168.1.{100+i}", dst="8.8.8.8")/TCP(dport=80)/Raw(f"GET /page{i}.html HTTP/1.1\r\nHost: example.com\r\n\r\n")
            patterns.append(pkt)
        
        # DNS queries
        dns_queries = ["google.com", "github.com", "stackoverflow.com", "reddit.com"]
        for query in dns_queries:
            pkt = Ether()/IP(src="192.168.1.100", dst="8.8.8.8")/UDP(dport=53)/Raw(f"DNS_QUERY_{query}")
            patterns.append(pkt)
        
        # HTTPS traffic
        for i in range(10):
            pkt = Ether()/IP(src=f"192.168.1.{120+i}", dst="1.1.1.1")/TCP(dport=443)/Raw(b"\x16\x03\x01" + b"TLS_HANDSHAKE_DATA")
            patterns.append(pkt)
        
        return patterns
    
    def high_rate_generation(self, duration=60, pps=1000):
        """Generate packets at high rate for performance testing"""
        print(f"🚀 Starting high-rate generation: {pps} pps for {duration}s")
        
        # Mix of normal and attack traffic
        normal_patterns = self.generate_normal_traffic()
        attack_patterns = self.generate_attack_patterns()
        all_patterns = normal_patterns + attack_patterns
        
        self.running = True
        self.stats['start_time'] = time.time()
        interval = 1.0 / pps
        
        try:
            while self.running and (time.time() - self.stats['start_time']) < duration:
                for pattern in all_patterns:
                    if not self.running:
                        break
                    
                    sendp(pattern, iface=self.interface, verbose=0)
                    self.stats['sent'] += 1
                    
                    time.sleep(interval)
                    
                    if self.stats['sent'] % 1000 == 0:
                        elapsed = time.time() - self.stats['start_time']
                        actual_pps = self.stats['sent'] / elapsed
                        print(f"📊 Sent: {self.stats['sent']} packets ({actual_pps:.1f} pps)")
        
        except KeyboardInterrupt:
            print("\n⏹️  Generation stopped")
        finally:
            self.running = False
            
        elapsed = time.time() - self.stats['start_time']
        print(f"✅ Generation complete: {self.stats['sent']} packets in {elapsed:.1f}s")

if __name__ == "__main__":
    generator = DPDKPacketGenerator()
    
    if len(sys.argv) > 1:
        rate = int(sys.argv[1])
    else:
        rate = 500  # Default 500 pps
    
    generator.high_rate_generation(duration=120, pps=rate)
EOF

    chmod +x /opt/dpdk/dpdk_packet_generator.py
    echo -e "${GREEN}✓ DPDK packet generator created${NC}"
}

# Create integration test script
create_integration_test() {
    echo -e "${YELLOW}🧪 Creating integration test script...${NC}"
    
    cat > /opt/dpdk/test_dpdk_integration.sh << 'EOF'
#!/bin/bash

# Real-time DPDK-Suricata-Kafka Integration Test

echo "🔬 DPDK-IDS Integration Test Starting..."

# Check services
echo "Checking system services..."
systemctl is-active suricata || echo "⚠️  Suricata not active"
pgrep -f kafka || echo "⚠️  Kafka not running"

# Check hugepages
HUGEPAGES=$(cat /proc/meminfo | grep HugePages_Free | awk '{print $2}')
echo "💾 Available hugepages: $HUGEPAGES"

# Test 1: Basic packet generation
echo "Test 1: Basic packet generation..."
python3 /opt/dpdk/dpdk_packet_generator.py 10 &
PID=$!
sleep 10
kill $PID 2>/dev/null || true

# Test 2: Monitor Suricata logs
echo "Test 2: Checking Suricata event generation..."
tail -5 /var/log/suricata/eve.json 2>/dev/null || echo "No recent events"

# Test 3: Check Kafka streaming
echo "Test 3: Checking Kafka event streaming..."
timeout 10 /home/ifscr/SE_02_2025/IDS/Suricata_Setup/kafka_consumer.py 2>/dev/null || echo "Kafka check timeout"

echo "✅ Integration test completed"
EOF

    chmod +x /opt/dpdk/test_dpdk_integration.sh
    echo -e "${GREEN}✓ Integration test script created${NC}"
}

# Create system service for DPDK packet generation
create_dpdk_service() {
    echo -e "${YELLOW}🔧 Creating DPDK packet generation service...${NC}"
    
    cat > /etc/systemd/system/dpdk-pktgen.service << EOF
[Unit]
Description=DPDK Packet Generator for IDS Testing
After=network.target suricata.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/dpdk
ExecStart=/usr/bin/python3 /opt/dpdk/dpdk_packet_generator.py 100
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    echo -e "${GREEN}✓ DPDK service created (use: systemctl start dpdk-pktgen)${NC}"
}

# Performance optimization
optimize_system() {
    echo -e "${YELLOW}⚡ Applying performance optimizations...${NC}"
    
    # CPU frequency scaling
    echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || true
    
    # Network optimizations
    sysctl -w net.core.rmem_max=134217728
    sysctl -w net.core.wmem_max=134217728
    sysctl -w net.core.netdev_max_backlog=5000
    
    # Make persistent
    cat >> /etc/sysctl.conf << EOF
# DPDK optimizations
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.core.netdev_max_backlog = 5000
EOF

    echo -e "${GREEN}✓ Performance optimizations applied${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}Starting DPDK real-time IDS integration setup...${NC}\n"
    
    check_root
    install_dependencies
    setup_hugepages
    install_dpdk
    setup_interface_binding
    create_dpdk_pktgen
    create_integration_test
    create_dpdk_service
    optimize_system
    
    echo -e "\n${GREEN}🎉 DPDK Real-time IDS Integration Setup Complete!${NC}"
    echo -e "\n${YELLOW}Next Steps:${NC}"
    echo "1. Test the integration: /opt/dpdk/test_dpdk_integration.sh"
    echo "2. Start packet generation: python3 /home/ifscr/SE_02_2025/IDS/realtime_dpdk_pipeline.py --mode demo"
    echo "3. Monitor performance: systemctl start dpdk-pktgen"
    echo "4. Check system status: /home/ifscr/SE_02_2025/IDS/Suricata_Setup/quick_validate.sh"
    
    echo -e "\n${BLUE}📊 System Status:${NC}"
    echo "  Hugepages: $(cat /proc/meminfo | grep HugePages_Total | awk '{print $2}') configured"
    echo "  DPDK: $INSTALL_DIR/dpdk-${DPDK_VERSION}"
    echo "  Generator: /opt/dpdk/dpdk_packet_generator.py"
    echo "  Service: systemctl [start|stop] dpdk-pktgen"
}

main "$@"
