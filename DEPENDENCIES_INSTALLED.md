# Dependencies Installation Summary

## Date: November 11, 2025

All dependencies for AF_PACKET mode have been successfully installed!

## Core System Dependencies

### 1. Suricata IDS
- **Version:** 7.0.10
- **Installation:** APT package manager
- **Purpose:** Network intrusion detection system
- **Status:** ✅ Installed

### 2. tcpreplay
- **Version:** 4.5.2
- **Installation:** APT package manager
- **Purpose:** Packet replay for testing
- **Status:** ✅ Installed

### 3. Java (OpenJDK)
- **Version:** 21.0.9-ea
- **Installation:** APT package manager (default-jdk)
- **Purpose:** Required for Apache Kafka
- **Status:** ✅ Installed

### 4. Apache Kafka
- **Version:** 3.9.0 (kafka_2.13-3.9.0)
- **Installation:** Downloaded from Apache mirrors, extracted to /usr/local/kafka
- **Purpose:** Message broker for IDS pipeline
- **Status:** ✅ Installed

### 5. Python 3
- **Version:** 3.13.7
- **Installation:** APT package manager
- **Packages:** python3, python3-pip, python3-venv, python3-dev
- **Status:** ✅ Installed

## Python Packages

All packages from requirements.txt have been installed:

### Core Packages
- ✅ numpy>=1.21.0 (2.3.4)
- ✅ pandas>=1.3.0 (2.3.3)
- ✅ scikit-learn>=1.0.0 (1.7.2)
- ✅ psutil>=5.8.0
- ✅ kafka-python>=2.0.2 (2.2.15)
- ✅ requests>=2.26.0
- ✅ pyyaml>=6.0
- ✅ click>=8.0.0

### Network Analysis
- ✅ scapy>=2.4.5 (2.6.1)
- ✅ pyshark>=0.4.5 (0.6)

### Machine Learning
- ✅ tensorflow>=2.8.0 (2.20.0)
- ✅ torch>=1.10.0 (2.9.0)

### Monitoring and Logging
- ✅ prometheus-client>=0.12.0 (0.23.1)
- ✅ structlog>=21.5.0 (25.5.0)

### Development and Testing
- ✅ pytest>=6.2.0 (9.0.0)
- ✅ pytest-cov>=3.0.0 (7.0.0)
- ✅ black>=21.12.0 (25.11.0)
- ✅ flake8>=4.0.0 (7.3.0)
- ✅ mypy>=0.930 (1.18.2)

## Build Tools

### Installed via APT
- ✅ build-essential
- ✅ gcc/g++ (15.2.0)
- ✅ make (4.4.1)

## What Was NOT Installed

### DPDK (As Requested)
DPDK was explicitly skipped as requested. The AF_PACKET mode works without DPDK using standard Linux packet sockets.

## Verification Commands

You can verify installations with:

```bash
# Check Suricata
suricata -V

# Check tcpreplay
tcpreplay --version

# Check Java
java -version

# Check Kafka
ls /usr/local/kafka/bin/

# Check Python packages
python3 -c "import kafka, numpy, pandas, sklearn; print('All packages OK')"
```

## Next Steps

You can now run the AF_PACKET mode:

```bash
# Make the script executable (if needed)
chmod +x /home/s-ujay/Programming/IDS/run_afpacket_mode.sh

# Run the pipeline (requires root for network access)
sudo /home/s-ujay/Programming/IDS/run_afpacket_mode.sh
```

## Notes

1. **Kafka Location:** /usr/local/kafka
2. **Python Scripts:** Installed to ~/.local/bin (add to PATH if needed)
3. **Network Permissions:** Suricata and packet capture require root/sudo
4. **AF_PACKET Mode:** Works with ANY network interface including USB adapters
5. **No DPDK Required:** This mode uses standard Linux AF_PACKET sockets

## Configuration Required

Before running, you need to:

1. Edit `/home/s-ujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf`
2. Set your `NETWORK_INTERFACE` (e.g., eth0, enp0s3, wlan0)
3. Verify Kafka configuration paths

## System Information

- **OS:** Ubuntu 25.10
- **Architecture:** ARM64 (aarch64)
- **Kernel:** Linux

