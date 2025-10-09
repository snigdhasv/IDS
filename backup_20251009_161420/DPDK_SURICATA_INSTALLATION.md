# DPDK and Suricata Installation Guide

## Quick Installation

Run the automated installation script:

```bash
sudo ./install_dpdk_suricata.sh
```

This script will:
1. ✓ Check system prerequisites
2. ✓ Install all required system dependencies
3. ✓ Download and build DPDK 23.11
4. ✓ Configure hugepages (2GB)
5. ✓ Download and build Suricata 7.0.7 with DPDK support
6. ✓ Update Suricata rules
7. ✓ Create helper scripts
8. ✓ Configure Python integration

**Installation time:** Approximately 15-30 minutes depending on your system

## Manual Installation (Alternative)

If you prefer to install components separately:

### DPDK Installation

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y build-essential meson ninja-build \
    libnuma-dev libpcap-dev python3-pyelftools pkg-config

# Download and build DPDK
cd /opt/ids
sudo wget https://fast.dpdk.org/rel/dpdk-23.11.tar.xz
sudo tar xf dpdk-23.11.tar.xz
cd dpdk-23.11
sudo meson setup build
cd build
sudo ninja
sudo ninja install
sudo ldconfig
```

### Suricata Installation

```bash
# Install dependencies
sudo apt-get install -y libpcre2-dev libjansson-dev libyaml-dev \
    libmagic-dev liblz4-dev libssl-dev libcap-ng-dev cargo rustc

# Download and build Suricata with DPDK
cd /opt/ids
sudo wget https://www.openinfosecfoundation.org/download/suricata-7.0.7.tar.gz
sudo tar xzf suricata-7.0.7.tar.gz
cd suricata-7.0.7
sudo ./configure --enable-dpdk --with-dpdk=/usr/local --enable-rust
sudo make -j$(nproc)
sudo make install
sudo make install-conf
sudo ldconfig
```

### Hugepages Configuration

```bash
# Configure 1GB hugepages
sudo mkdir -p /mnt/huge
sudo mount -t hugetlbfs nodev /mnt/huge
echo 2 | sudo tee /sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages

# Make permanent (add to GRUB)
sudo nano /etc/default/grub
# Add: default_hugepagesz=1G hugepagesz=1G hugepages=2
sudo update-grub
```

## Verification

After installation, verify everything is working:

```bash
# Check DPDK installation
dpdk-status

# Check Suricata installation
suricata-status

# Or manually check
suricata --build-info | grep DPDK
pkg-config --modversion libdpdk

# Check hugepages
grep Huge /proc/meminfo
```

## System Requirements

### Minimum Requirements
- **CPU:** 2+ cores
- **RAM:** 4GB (6GB recommended for hugepages)
- **OS:** Ubuntu 20.04+ or Debian 11+
- **Kernel:** 5.4+
- **Disk:** 10GB free space

### Recommended Requirements
- **CPU:** 4+ cores
- **RAM:** 8GB+ 
- **NIC:** Intel or Mellanox (best DPDK support)
- **Hugepages:** 2-4GB allocated

## Post-Installation Steps

### 1. Reboot System (Recommended)
```bash
sudo reboot
```
This ensures hugepages are properly allocated.

### 2. Bind Network Interface to DPDK (Optional)

**WARNING:** This will take the network interface offline!

```bash
# Find your network interface PCI address
lspci | grep -i ethernet

# Check current driver
dpdk-devbind.py --status

# Bind to DPDK (example)
sudo modprobe vfio-pci
sudo dpdk-devbind.py -b vfio-pci 0000:02:00.0

# Unbind (to restore normal networking)
sudo dpdk-devbind.py -u 0000:02:00.0
sudo dpdk-devbind.py -b <original_driver> 0000:02:00.0
```

### 3. Configure Suricata

Edit the Suricata configuration file:

```bash
sudo nano /etc/suricata/suricata.yaml
```

Key sections to configure:
- `dpdk:` - DPDK interface settings
- `af-packet:` - Regular interface settings (if not using DPDK)
- `vars:` - Network variables (HOME_NET, EXTERNAL_NET)
- `outputs:` - Where to send alerts (eve.json, kafka, etc.)

### 4. Update Suricata Rules

```bash
sudo suricata-update
sudo suricata-update list-sources  # See available rule sources
sudo suricata-update enable-source <source-name>
```

### 5. Test Suricata

```bash
# Test configuration
sudo suricata -T -c /etc/suricata/suricata.yaml

# Run in live mode (AF_PACKET)
sudo suricata -c /etc/suricata/suricata.yaml -i eth0

# Run in DPDK mode
sudo suricata -c /etc/suricata/suricata.yaml --dpdk
```

## Integration with IDS Project

### Python Integration

Activate your virtual environment first:
```bash
source ~/Programming/IDS/venv/bin/activate
```

### Testing DPDK Integration

```bash
python src/basic_dpdk_test.py
python src/dpdk_pktgen_test.py
```

### Running Complete Pipeline

```bash
./ml_enhanced_pipeline.sh
```

## Troubleshooting

### DPDK Issues

**Problem:** "EAL: No free hugepages reported"
```bash
# Check hugepages
grep Huge /proc/meminfo

# Allocate more hugepages
echo 2 | sudo tee /sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages

# Or reboot for GRUB settings to take effect
sudo reboot
```

**Problem:** "Cannot bind device to vfio-pci"
```bash
# Load vfio-pci module
sudo modprobe vfio-pci

# Check IOMMU
dmesg | grep -i iommu

# May need to enable IOMMU in BIOS/UEFI
```

### Suricata Issues

**Problem:** "Failed to initialize DPDK"
```bash
# Check if hugepages are allocated
grep Huge /proc/meminfo

# Check if DPDK interfaces are bound
dpdk-devbind.py --status

# Verify Suricata DPDK support
suricata --build-info | grep DPDK
```

**Problem:** "Permission denied" when running Suricata
```bash
# Run with sudo
sudo suricata ...

# Or add user to necessary groups
sudo usermod -aG suricata $USER
```

### Performance Issues

**Low packet capture rate:**
- Increase hugepages allocation
- Use more CPU cores
- Enable CPU isolation
- Tune NIC ring buffer sizes

**High CPU usage:**
- Reduce rule set size
- Disable unused Suricata features
- Use hardware offload (if available)

## Useful Commands

```bash
# System Status
dpdk-status                    # Check DPDK status
suricata-status                # Check Suricata status
lscpu                          # CPU information
free -h                        # Memory usage
grep Huge /proc/meminfo        # Hugepages status

# DPDK Tools
dpdk-devbind.py --status       # Show device status
dpdk-testpmd                   # Test DPDK setup
dpdk-pktgen                    # Packet generator

# Suricata Management
suricata --build-info          # Build information
suricata -T                    # Test configuration
suricata-update                # Update rules
sudo systemctl start suricata  # Start as service
sudo systemctl status suricata # Check service status
tail -f /var/log/suricata/eve.json  # Watch alerts

# Network Information
ip link show                   # Network interfaces
ethtool -i eth0                # Driver information
lspci | grep -i ethernet       # PCI network devices
```

## Resources

- **DPDK Documentation:** https://doc.dpdk.org/
- **Suricata Documentation:** https://docs.suricata.io/
- **DPDK with Suricata:** https://docs.suricata.io/en/latest/capture-hardware/dpdk.html
- **Your Project Setup Scripts:** `/home/sujay/Programming/IDS/setup_*.sh`

## Support

If you encounter issues:
1. Check logs: `/var/log/suricata/` and `dmesg | tail`
2. Review configuration: `/etc/suricata/suricata.yaml`
3. Test DPDK separately: `dpdk-testpmd`
4. Verify hugepages: `grep Huge /proc/meminfo`

---

**Created:** October 2, 2025  
**Last Updated:** October 2, 2025  
**Version:** 1.0
