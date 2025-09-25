#!/bin/bash

# IDS Environment Setup Script
# This script sets up DPDK and pktgen for the IDS system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DPDK_VERSION="24.07"
PKTGEN_VERSION="24.03.0"
INSTALL_DIR="/opt/ids"
HUGEPAGE_SIZE="2048"  # 2GB in MB

echo -e "${GREEN}=== IDS Environment Setup ===${NC}"

# Check if running as root for certain operations
check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}This script needs to be run with sudo for system-level configurations${NC}"
        echo "Usage: sudo ./setup_dpdk_pktgen.sh"
        exit 1
    fi
}

# Create installation directory
setup_directories() {
    echo -e "${YELLOW}Creating installation directories...${NC}"
    mkdir -p $INSTALL_DIR
    mkdir -p $INSTALL_DIR/downloads
    mkdir -p $INSTALL_DIR/logs
}

# Configure hugepages
setup_hugepages() {
    echo -e "${YELLOW}Setting up hugepages...${NC}"
    
    # Set hugepages
    echo $HUGEPAGE_SIZE > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
    
    # Make hugepages persistent
    if ! grep -q "vm.nr_hugepages" /etc/sysctl.conf; then
        echo "vm.nr_hugepages=1024" >> /etc/sysctl.conf
    fi
    
    # Mount hugepage filesystem
    if ! mountpoint -q /mnt/huge; then
        mkdir -p /mnt/huge
        mount -t hugetlbfs nodev /mnt/huge
        
        # Make mount persistent
        if ! grep -q "/mnt/huge" /etc/fstab; then
            echo "nodev /mnt/huge hugetlbfs defaults 0 0" >> /etc/fstab
        fi
    fi
    
    echo -e "${GREEN}Hugepages configured${NC}"
}

# Download and compile DPDK
install_dpdk() {
    echo -e "${YELLOW}Installing DPDK ${DPDK_VERSION}...${NC}"
    
    cd $INSTALL_DIR/downloads
    
    # Download DPDK if not already present
    if [ ! -f "dpdk-${DPDK_VERSION}.tar.xz" ]; then
        wget "https://fast.dpdk.org/rel/dpdk-${DPDK_VERSION}.tar.xz"
    fi
    
    # Extract and build
    if [ ! -d "dpdk-${DPDK_VERSION}" ]; then
        tar -xf "dpdk-${DPDK_VERSION}.tar.xz"
    fi
    
    cd "dpdk-${DPDK_VERSION}"
    
    # Configure build
    meson setup -Dexamples=all build
    cd build
    
    # Compile
    ninja
    ninja install
    ldconfig
    
    # Set environment variables
    echo "export RTE_SDK=$INSTALL_DIR/downloads/dpdk-${DPDK_VERSION}" >> /etc/environment
    echo "export RTE_TARGET=build" >> /etc/environment
    
    echo -e "${GREEN}DPDK installation completed${NC}"
}

# Download and compile pktgen
install_pktgen() {
    echo -e "${YELLOW}Installing pktgen ${PKTGEN_VERSION}...${NC}"
    
    cd $INSTALL_DIR/downloads
    
    # Download pktgen if not already present
    if [ ! -f "pktgen-${PKTGEN_VERSION}.tar.gz" ]; then
        wget "https://git.dpdk.org/apps/pktgen-dpdk/snapshot/pktgen-${PKTGEN_VERSION}.tar.gz" || \
        wget "https://github.com/pktgen/Pktgen-DPDK/archive/refs/tags/pktgen-${PKTGEN_VERSION}.tar.gz" -O "pktgen-${PKTGEN_VERSION}.tar.gz"
    fi
    
    # Extract and build
    if [ ! -d "pktgen-${PKTGEN_VERSION}" ]; then
        tar -xf "pktgen-${PKTGEN_VERSION}.tar.gz"
        # Handle GitHub archive naming (Pktgen-DPDK-pktgen-version)
        if [ -d "Pktgen-DPDK-pktgen-${PKTGEN_VERSION}" ]; then
            mv "Pktgen-DPDK-pktgen-${PKTGEN_VERSION}" "pktgen-${PKTGEN_VERSION}"
        fi
    fi
    
    cd "pktgen-${PKTGEN_VERSION}"
    
    # Set DPDK environment
    export RTE_SDK=$INSTALL_DIR/downloads/dpdk-${DPDK_VERSION}
    export RTE_TARGET=build
    
    # Build pktgen
    meson setup build
    cd build
    ninja
    
    # Create symlink for easy access
    ln -sf $INSTALL_DIR/downloads/pktgen-${PKTGEN_VERSION}/build/app/pktgen /usr/local/bin/pktgen
    
    echo -e "${GREEN}Pktgen installation completed${NC}"
}

# Setup DPDK interfaces
setup_dpdk_interfaces() {
    echo -e "${YELLOW}Setting up DPDK interfaces...${NC}"
    
    # Load necessary modules
    modprobe uio
    modprobe uio_pci_generic
    
    # Make module loading persistent
    if ! grep -q "uio" /etc/modules; then
        echo "uio" >> /etc/modules
        echo "uio_pci_generic" >> /etc/modules
    fi
    
    echo -e "${GREEN}DPDK interfaces configured${NC}"
}

# Create configuration files
create_configs() {
    echo -e "${YELLOW}Creating configuration files...${NC}"
    
    # Create pktgen configuration
    cat > $INSTALL_DIR/pktgen_config.lua << 'EOF'
-- Pktgen configuration for IDS testing

package.path = package.path ..";?.lua;test/?.lua;app/?.lua;"

printf("Pktgen Configuration for IDS System\n");

-- Basic packet configuration
pktgen.set_mac("0", "00:11:22:33:44:55");
pktgen.set_ipaddr("0", "src", "192.168.1.1/24");
pktgen.set_ipaddr("0", "dst", "192.168.1.2");

-- Set packet size and count
pktgen.set("all", "size", 64);
pktgen.set("all", "count", 0);  -- Continuous generation
pktgen.set("all", "rate", 10);   -- 10% line rate

-- Enable packet capture for testing
pktgen.set("all", "capture", "enable");

printf("Configuration loaded successfully\n");
EOF

    # Create DPDK environment script
    cat > $INSTALL_DIR/setup_env.sh << 'EOF'
#!/bin/bash
# DPDK Environment Setup

export RTE_SDK=/opt/ids/downloads/dpdk-24.07
export RTE_TARGET=build
export LD_LIBRARY_PATH=/usr/local/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# Hugepage setup
if [ ! -d "/mnt/huge" ]; then
    sudo mkdir -p /mnt/huge
    sudo mount -t hugetlbfs nodev /mnt/huge
fi

echo "DPDK environment configured"
echo "RTE_SDK: $RTE_SDK"
echo "Hugepages: $(cat /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages)"
EOF
    
    chmod +x $INSTALL_DIR/setup_env.sh
    
    echo -e "${GREEN}Configuration files created${NC}"
}

# Main installation function
main() {
    echo -e "${GREEN}Starting IDS environment setup...${NC}"
    echo "This will install DPDK ${DPDK_VERSION} and pktgen ${PKTGEN_VERSION}"
    
    check_root
    setup_directories
    setup_hugepages
    install_dpdk
    install_pktgen
    setup_dpdk_interfaces
    create_configs
    
    echo -e "${GREEN}=== Setup Complete ===${NC}"
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Source the environment: source $INSTALL_DIR/setup_env.sh"
    echo "2. Bind network interfaces: dpdk-devbind.py --status"
    echo "3. Run pktgen: pktgen -c 0x3 -n 4 -- -P -m '[1:2].0' -f $INSTALL_DIR/pktgen_config.lua"
    echo ""
    echo -e "${YELLOW}Important Notes:${NC}"
    echo "- Reboot may be required for all changes to take effect"
    echo "- Network interfaces need to be bound to DPDK before use"
    echo "- Check $INSTALL_DIR/logs/ for detailed installation logs"
}

# Run main function
main "$@"
