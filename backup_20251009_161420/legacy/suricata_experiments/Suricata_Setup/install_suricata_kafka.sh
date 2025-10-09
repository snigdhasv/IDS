#!/bin/bash

# Suricata Installation with Kafka Support for Direct Event Streaming
# This script installs Suricata with DPDK and Kafka support

set -e

echo "=== Suricata Installation with Kafka Support ==="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)" 
   exit 1
fi

# Update system packages
echo "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install required dependencies
echo "Installing dependencies..."
apt-get install -y \
    build-essential \
    pkg-config \
    libpcre3-dev \
    libnet1-dev \
    libyaml-0-2 \
    libyaml-dev \
    libpcap-dev \
    libcap-ng-dev \
    libcap-ng0 \
    make \
    libmagic-dev \
    zlib1g-dev \
    libjansson-dev \
    rustc \
    cargo \
    python3-yaml \
    liblua5.1-dev \
    libhiredis-dev \
    libevent-dev \
    libpcre2-dev \
    libssl-dev \
    liblz4-dev \
    wget \
    git

# Install DPDK dependencies
echo "Installing DPDK dependencies..."
apt-get install -y \
    dpdk \
    dpdk-dev \
    libdpdk-dev \
    libnuma-dev \
    meson \
    ninja-build

# Install Kafka dependencies
echo "Installing Kafka client libraries..."
apt-get install -y \
    librdkafka-dev \
    librdkafka1

# Create suricata user
echo "Creating suricata user..."
if ! id "suricata" &>/dev/null; then
    useradd -r -s /bin/false suricata
fi

# Download and compile Suricata with DPDK and Kafka support
SURICATA_VERSION="7.0.2"
cd /tmp

echo "Downloading Suricata ${SURICATA_VERSION}..."
wget https://www.openinfosecfoundation.org/download/suricata-${SURICATA_VERSION}.tar.gz
tar -xzf suricata-${SURICATA_VERSION}.tar.gz
cd suricata-${SURICATA_VERSION}

echo "Configuring Suricata build with DPDK and Kafka support..."
./configure \
    --prefix=/usr/local \
    --sysconfdir=/etc/suricata \
    --localstatedir=/var \
    --enable-dpdk \
    --enable-lua \
    --enable-hiredis \
    --enable-geoip \
    --enable-nfqueue \
    --enable-nflog \
    --enable-unix-socket \
    --with-librdkafka-includes=/usr/include/librdkafka \
    --with-librdkafka-libraries=/usr/lib/x86_64-linux-gnu

echo "Building Suricata..."
make -j$(nproc)

echo "Installing Suricata..."
make install

# Create necessary directories
echo "Creating directories..."
mkdir -p /var/log/suricata
mkdir -p /var/lib/suricata
mkdir -p /etc/suricata/rules
chown -R suricata:suricata /var/log/suricata
chown -R suricata:suricata /var/lib/suricata

# Copy default configuration
echo "Setting up configuration..."
cp etc/suricata.yaml /etc/suricata/
cp etc/classification.config /etc/suricata/
cp etc/reference.config /etc/suricata/

# Download and install Suricata rules
echo "Installing Suricata rules..."
cd /tmp
wget https://rules.emergingthreats.net/open/suricata/emerging.rules.tar.gz
tar -xzf emerging.rules.tar.gz -C /etc/suricata/

echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "1. Configure Kafka settings in suricata-kafka.yaml"
echo "2. Update PCI address for your DPDK interface"
echo "3. Start Kafka server"
echo "4. Start Suricata: sudo systemctl start suricata-kafka"
echo "5. Check Kafka topics for incoming events"
echo ""
echo "Configuration files:"
echo "- Main config: /etc/suricata/suricata-kafka.yaml"
echo "- Service: suricata-kafka.service"
