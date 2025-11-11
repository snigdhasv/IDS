# Quick Start Guide - AF_PACKET Mode

## ✅ Installation Complete!

All dependencies have been installed successfully. You can now run the IDS pipeline.

## Available Network Interfaces

Your system has the following network interfaces:
- `lo` - Loopback interface (not for capturing external traffic)
- `enp0s1` - Primary network interface (use this for capturing traffic)

## Before You Start

1. **Configure the network interface:**
   ```bash
   # Edit the pipeline configuration
   nano /home/s-ujay/Programming/IDS/dpdk_suricata_ml_pipeline/config/pipeline.conf
   
   # Set NETWORK_INTERFACE to your interface, e.g.:
   NETWORK_INTERFACE="enp0s1"
   ```

2. **Make the script executable:**
   ```bash
   chmod +x /home/s-ujay/Programming/IDS/run_afpacket_mode.sh
   ```

## Running the Pipeline

### Option 1: Start Complete Pipeline (Recommended)
```bash
sudo /home/s-ujay/Programming/IDS/run_afpacket_mode.sh start
```
This will start:
- Kafka message broker
- Suricata IDS in AF_PACKET mode
- Kafka bridge (Suricata → Kafka)
- ML consumer for threat detection

### Option 2: Interactive Menu
```bash
sudo /home/s-ujay/Programming/IDS/run_afpacket_mode.sh
```
This opens an interactive menu where you can:
- Start individual components
- Check system status
- View logs
- Monitor metrics
- Stop services

## Common Commands

### Check Status
```bash
sudo /home/s-ujay/Programming/IDS/run_afpacket_mode.sh status
```

### View Logs
```bash
sudo /home/s-ujay/Programming/IDS/run_afpacket_mode.sh logs
```

### Monitor Metrics
```bash
sudo /home/s-ujay/Programming/IDS/run_afpacket_mode.sh metrics
```

### Stop All Services
```bash
sudo /home/s-ujay/Programming/IDS/run_afpacket_mode.sh stop
```

## What Each Component Does

1. **Kafka** - Message broker that receives alerts from Suricata
2. **Suricata** - IDS that analyzes network traffic and generates alerts
3. **Kafka Bridge** - Reads Suricata's EVE JSON logs and sends to Kafka
4. **ML Consumer** - Processes alerts from Kafka using machine learning models

## Testing with Sample Traffic

You can test the system with tcpreplay:
```bash
# Find a sample pcap file or download one
sudo tcpreplay -i enp0s1 /path/to/sample.pcap
```

## Troubleshooting

### Kafka won't start
```bash
# Check if Java is installed
java -version

# Check if port 9092 is already in use
sudo netstat -tulpn | grep 9092
```

### Suricata can't capture packets
```bash
# Verify interface is up
sudo ip link set enp0s1 up

# Check if you're running as root
whoami  # should show 'root' when using sudo
```

### Python script errors
```bash
# Add Python scripts to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Next Steps

1. Configure your network interface in `pipeline.conf`
2. Run the complete pipeline: `sudo ./run_afpacket_mode.sh start`
3. Monitor the system: `sudo ./run_afpacket_mode.sh status`
4. Check logs: `sudo ./run_afpacket_mode.sh logs`

## Need Help?

Check these files for more information:
- `DEPENDENCIES_INSTALLED.md` - Full list of installed dependencies
- `README.md` - Project overview
- `AFPACKET_MODE_ARCHITECTURE.md` - Architecture details
- `PIPELINE_RUNNERS_DOCUMENTATION.md` - Runner scripts documentation

## Important Notes

⚠️ **Always run with sudo** - Network packet capture requires root privileges
✅ **No DPDK needed** - AF_PACKET mode works with any network interface
🎯 **USB adapters supported** - Can use USB network adapters for monitoring
