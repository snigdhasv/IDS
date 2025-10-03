#!/bin/bash

# Complete DPDK and Suricata Installation Script for IDS Project
# Date: October 2, 2025
# This script installs DPDK and Suricata with proper configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
DPDK_VERSION="23.11"
SURICATA_VERSION="7.0.7"
INSTALL_DIR="/opt/ids"
DPDK_DIR="${INSTALL_DIR}/dpdk-${DPDK_VERSION}"
HUGEPAGE_SIZE="1048576"  # 1GB hugepages
NUM_HUGEPAGES="2"        # 2GB total

echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║   DPDK + Suricata Installation for IDS Project            ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo

# Function to print section headers
print_section() {
    echo -e "\n${BOLD}${CYAN}▶ $1${NC}"
    echo -e "${CYAN}$(printf '─%.0s' {1..60})${NC}"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}❌ This script must be run as root${NC}"
        echo "Usage: sudo ./install_dpdk_suricata.sh"
        exit 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_section "Checking System Prerequisites"
    
    # Check CPU cores
    CORES=$(nproc)
    echo -e "CPU cores: ${GREEN}$CORES${NC}"
    if [ $CORES -lt 2 ]; then
        echo -e "${YELLOW}⚠️  Warning: Less than 2 CPU cores. Performance may be limited.${NC}"
    fi
    
    # Check memory
    MEM_GB=$(free -g | awk '/^Mem:/{print $2}')
    echo -e "Available memory: ${GREEN}${MEM_GB}GB${NC}"
    if [ $MEM_GB -lt 4 ]; then
        echo -e "${YELLOW}⚠️  Warning: Less than 4GB RAM. May need to reduce hugepages.${NC}"
        NUM_HUGEPAGES="1"
    fi
    
    # Check kernel version
    KERNEL_VERSION=$(uname -r)
    echo -e "Kernel version: ${GREEN}$KERNEL_VERSION${NC}"
    
    echo -e "${GREEN}✓ System check complete${NC}"
}

# Function to install system dependencies
install_system_dependencies() {
    print_section "Installing System Dependencies"
    
    echo "Updating package lists..."
    apt-get update -qq
    
    echo "Installing build tools and libraries..."
    apt-get install -y \
        build-essential \
        cmake \
        meson \
        ninja-build \
        pkg-config \
        python3-pyelftools \
        libnuma-dev \
        libpcap-dev \
        libpcre2-dev \
        libjansson-dev \
        libyaml-dev \
        libmagic-dev \
        liblz4-dev \
        libssl-dev \
        libcap-ng-dev \
        libnetfilter-queue-dev \
        libnetfilter-log-dev \
        libhtp-dev \
        libevent-dev \
        cargo \
        rustc \
        git \
        wget \
        curl \
        autoconf \
        automake \
        libtool \
        make \
        libgeoip-dev \
        liblzma-dev \
        zlib1g-dev \
        pciutils \
        ethtool \
        net-tools \
        linux-headers-$(uname -r) > /dev/null
    
    echo -e "${GREEN}✓ System dependencies installed${NC}"
}

# Function to install DPDK
install_dpdk() {
    print_section "Installing DPDK ${DPDK_VERSION}"
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    if [ -d "$DPDK_DIR" ]; then
        echo -e "${YELLOW}⚠️  DPDK already installed at $DPDK_DIR${NC}"
        read -p "Reinstall? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Skipping DPDK installation"
            return 0
        fi
        rm -rf "$DPDK_DIR"
    fi
    
    echo "Downloading DPDK ${DPDK_VERSION}..."
    if [ ! -f "dpdk-${DPDK_VERSION}.tar.xz" ]; then
        wget -q --show-progress "https://fast.dpdk.org/rel/dpdk-${DPDK_VERSION}.tar.xz"
    fi
    
    echo "Extracting DPDK..."
    tar xf "dpdk-${DPDK_VERSION}.tar.xz"
    cd "$DPDK_DIR"
    
    echo "Configuring DPDK build..."
    meson setup build -Dplatform=generic -Dexamples=all
    
    echo "Building DPDK (this may take a few minutes)..."
    cd build
    ninja
    
    echo "Installing DPDK..."
    ninja install
    ldconfig
    
    # Add DPDK to PKG_CONFIG_PATH
    if ! grep -q "PKG_CONFIG_PATH.*dpdk" /etc/environment; then
        echo "export PKG_CONFIG_PATH=\$PKG_CONFIG_PATH:/usr/local/lib/x86_64-linux-gnu/pkgconfig" >> /etc/environment
    fi
    export PKG_CONFIG_PATH=$PKG_CONFIG_PATH:/usr/local/lib/x86_64-linux-gnu/pkgconfig
    
    echo -e "${GREEN}✓ DPDK ${DPDK_VERSION} installed successfully${NC}"
}

# Function to configure hugepages
configure_hugepages() {
    print_section "Configuring Hugepages"
    
    # Configure 1GB hugepages
    echo "Setting up ${NUM_HUGEPAGES} x 1GB hugepages..."
    
    # Enable hugepages at boot
    if ! grep -q "default_hugepagesz=1G" /etc/default/grub; then
        echo "Adding hugepage configuration to GRUB..."
        sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/GRUB_CMDLINE_LINUX_DEFAULT="default_hugepagesz=1G hugepagesz=1G hugepages='$NUM_HUGEPAGES' /' /etc/default/grub
        update-grub
        echo -e "${YELLOW}⚠️  Hugepages will be available after reboot${NC}"
    fi
    
    # Set hugepages for current session
    mkdir -p /mnt/huge
    if ! mount | grep -q "/mnt/huge"; then
        mount -t hugetlbfs nodev /mnt/huge
    fi
    
    # Add to fstab for persistence
    if ! grep -q "/mnt/huge" /etc/fstab; then
        echo "nodev /mnt/huge hugetlbfs defaults 0 0" >> /etc/fstab
    fi
    
    # Try to allocate hugepages now (may fail if not enough memory)
    echo $NUM_HUGEPAGES > /sys/kernel/mm/hugepages/hugepages-${HUGEPAGE_SIZE}kB/nr_hugepages 2>/dev/null || true
    
    ALLOCATED=$(cat /sys/kernel/mm/hugepages/hugepages-${HUGEPAGE_SIZE}kB/nr_hugepages)
    if [ "$ALLOCATED" -eq "$NUM_HUGEPAGES" ]; then
        echo -e "${GREEN}✓ Hugepages configured: ${ALLOCATED} x 1GB${NC}"
    else
        echo -e "${YELLOW}⚠️  Could only allocate ${ALLOCATED} hugepages. Reboot recommended.${NC}"
    fi
}

# Function to install Suricata
install_suricata() {
    print_section "Installing Suricata ${SURICATA_VERSION}"
    
    cd "$INSTALL_DIR"
    
    if command -v suricata &> /dev/null; then
        CURRENT_VERSION=$(suricata --version | head -n1 | awk '{print $2}')
        echo -e "${YELLOW}⚠️  Suricata ${CURRENT_VERSION} already installed${NC}"
        read -p "Reinstall? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Skipping Suricata installation"
            return 0
        fi
    fi
    
    echo "Downloading Suricata ${SURICATA_VERSION}..."
    if [ ! -f "suricata-${SURICATA_VERSION}.tar.gz" ]; then
        wget -q --show-progress "https://www.openinfosecfoundation.org/download/suricata-${SURICATA_VERSION}.tar.gz"
    fi
    
    echo "Extracting Suricata..."
    tar xzf "suricata-${SURICATA_VERSION}.tar.gz"
    cd "suricata-${SURICATA_VERSION}"
    
    echo "Configuring Suricata with DPDK support..."
    ./configure \
        --prefix=/usr \
        --sysconfdir=/etc \
        --localstatedir=/var \
        --enable-dpdk \
        --with-dpdk=/usr/local \
        --enable-rust \
        --enable-lua
    
    echo "Building Suricata (this may take several minutes)..."
    make -j$(nproc)
    
    echo "Installing Suricata..."
    make install
    make install-conf
    ldconfig
    
    # Create log directory
    mkdir -p /var/log/suricata
    mkdir -p /etc/suricata/rules
    
    echo -e "${GREEN}✓ Suricata ${SURICATA_VERSION} installed successfully${NC}"
}

# Function to update Suricata rules
update_suricata_rules() {
    print_section "Updating Suricata Rules"
    
    echo "Installing suricata-update..."
    pip3 install --upgrade suricata-update
    
    echo "Updating Suricata rules..."
    suricata-update || echo -e "${YELLOW}⚠️  Rule update may complete in background${NC}"
    
    echo -e "${GREEN}✓ Suricata rules updated${NC}"
}

# Function to configure DPDK for Python bindings
setup_python_dpdk() {
    print_section "Setting up Python DPDK Integration"
    
    # Install Python DPDK bindings
    source /home/${SUDO_USER}/Programming/IDS/venv/bin/activate
    
    pip3 install meson ninja pyelftools
    
    echo -e "${GREEN}✓ Python DPDK tools installed${NC}"
    deactivate
}

# Function to create startup scripts
create_startup_scripts() {
    print_section "Creating Helper Scripts"
    
    # DPDK status check script
    cat > /usr/local/bin/dpdk-status << 'EOF'
#!/bin/bash
echo "DPDK Status:"
echo "============"
echo -n "DPDK Version: "
pkg-config --modversion libdpdk 2>/dev/null || echo "Not found"
echo ""
echo "Hugepages:"
grep Huge /proc/meminfo
echo ""
echo "DPDK devices:"
dpdk-devbind.py --status 2>/dev/null || echo "dpdk-devbind.py not found"
EOF
    chmod +x /usr/local/bin/dpdk-status
    
    # Suricata status script
    cat > /usr/local/bin/suricata-status << 'EOF'
#!/bin/bash
echo "Suricata Status:"
echo "================"
suricata --build-info | grep -E "Version|DPDK|AF_PACKET|Rust"
echo ""
systemctl status suricata 2>/dev/null || echo "Suricata service not running"
EOF
    chmod +x /usr/local/bin/suricata-status
    
    echo -e "${GREEN}✓ Helper scripts created:${NC}"
    echo "  - dpdk-status: Check DPDK installation"
    echo "  - suricata-status: Check Suricata installation"
}

# Function to print installation summary
print_summary() {
    echo
    echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}║         Installation Complete!                             ║${NC}"
    echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${BOLD}Installed Components:${NC}"
    echo -e "  ${GREEN}✓${NC} DPDK ${DPDK_VERSION} - /usr/local"
    echo -e "  ${GREEN}✓${NC} Suricata ${SURICATA_VERSION} - /usr/bin/suricata"
    echo -e "  ${GREEN}✓${NC} Hugepages configured (${NUM_HUGEPAGES} x 1GB)"
    echo
    echo -e "${BOLD}Quick Commands:${NC}"
    echo -e "  ${CYAN}dpdk-status${NC}        - Check DPDK installation and devices"
    echo -e "  ${CYAN}suricata-status${NC}    - Check Suricata installation"
    echo -e "  ${CYAN}suricata --build-info${NC} - Detailed Suricata build info"
    echo
    echo -e "${BOLD}Configuration Files:${NC}"
    echo -e "  Suricata config: ${CYAN}/etc/suricata/suricata.yaml${NC}"
    echo -e "  Suricata rules:  ${CYAN}/etc/suricata/rules/${NC}"
    echo -e "  Logs:            ${CYAN}/var/log/suricata/${NC}"
    echo
    echo -e "${BOLD}${YELLOW}Important Notes:${NC}"
    echo -e "  • Hugepages are configured but may require ${BOLD}reboot${NC} to take full effect"
    echo -e "  • DPDK devices must be bound before use: ${CYAN}dpdk-devbind.py -b vfio-pci <device>${NC}"
    echo -e "  • Suricata DPDK mode requires hugepages and bound interfaces"
    echo -e "  • Run test scripts from: ${CYAN}/home/${SUDO_USER}/Programming/IDS/${NC}"
    echo
    echo -e "${BOLD}Next Steps:${NC}"
    echo -e "  1. ${CYAN}Reboot system${NC} (recommended for hugepages)"
    echo -e "  2. Activate Python venv: ${CYAN}source ~/Programming/IDS/venv/bin/activate${NC}"
    echo -e "  3. Run tests: ${CYAN}python src/basic_dpdk_test.py${NC}"
    echo -e "  4. Configure Suricata for your network interface"
    echo
}

# Main installation flow
main() {
    check_root
    check_prerequisites
    install_system_dependencies
    install_dpdk
    configure_hugepages
    install_suricata
    update_suricata_rules
    setup_python_dpdk
    create_startup_scripts
    print_summary
}

# Run main function
main
