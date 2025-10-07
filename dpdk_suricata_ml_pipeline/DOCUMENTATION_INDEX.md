# 📚 Documentation Index - IDS External Traffic Setup

## 🎯 What You Need

You want to send traffic from an **external device** (Windows/Linux) through an **Ethernet cable** to your IDS system's **USB adapter**, where it will be analyzed by Suricata + ML pipeline.

---

## 🚀 Quick Start (Pick Your Platform)

### For Windows Users
👉 **Start Here**: [`WINDOWS_QUICK_SETUP.md`](WINDOWS_QUICK_SETUP.md)
- 5-minute setup with PowerShell
- **No installation required!**
- Built-in traffic generation

👉 **No tcpreplay?** [`WINDOWS_NO_TCPREPLAY.md`](WINDOWS_NO_TCPREPLAY.md)
- PowerShell only (zero install!)
- 10+ ready-to-use attack scripts
- Python/Scapy alternatives

📖 **Detailed Guide**: [`WINDOWS_EXTERNAL_DEVICE_GUIDE.md`](WINDOWS_EXTERNAL_DEVICE_GUIDE.md)
- Complete setup instructions
- Multiple traffic generation tools
- Python/Scapy examples
- Attack simulation scripts

### For Linux Users
👉 **Start Here**: [`EXTERNAL_TRAFFIC_GUIDE.md`](EXTERNAL_TRAFFIC_GUIDE.md)
- Complete Linux setup
- Works with: Kali, Ubuntu, Raspberry Pi, etc.
- tcpreplay, hping3, nmap examples
- Professional attack tools

---

## 📋 Complete Documentation

### Setup Guides

| Guide | Description | Best For |
|-------|-------------|----------|
| **[WINDOWS_QUICK_SETUP.md](WINDOWS_QUICK_SETUP.md)** | 5-min Windows setup | Quick start |
| **[WINDOWS_EXTERNAL_DEVICE_GUIDE.md](WINDOWS_EXTERNAL_DEVICE_GUIDE.md)** | Complete Windows guide | Windows users |
| **[EXTERNAL_TRAFFIC_GUIDE.md](EXTERNAL_TRAFFIC_GUIDE.md)** | Complete Linux guide | Linux users |
| **[AF_PACKET_QUICK_START.md](AF_PACKET_QUICK_START.md)** | IDS system setup | Your laptop |
| **[USB_ADAPTER_GUIDE.md](USB_ADAPTER_GUIDE.md)** | Why DPDK doesn't work | USB adapter info |

### Comparison Guides

| Guide | Description | Best For |
|-------|-------------|----------|
| **[PLATFORM_COMPARISON.md](PLATFORM_COMPARISON.md)** | Linux vs Windows | Choosing platform |
| **[ARCHITECTURE_COMPARISON.md](ARCHITECTURE_COMPARISON.md)** | DPDK vs AF_PACKET | Understanding tech |
| **[MODES_COMPARISON.md](MODES_COMPARISON.md)** | All capture modes | Technical details |

### Advanced Guides

| Guide | Description | Best For |
|-------|-------------|----------|
| **[PRODUCTION_DPDK_GUIDE.md](PRODUCTION_DPDK_GUIDE.md)** | Production DPDK setup | Future reference |
| **[RUNTIME_GUIDE.md](RUNTIME_GUIDE.md)** | Runtime operations | Operations |
| **[SETUP_GUIDE.md](SETUP_GUIDE.md)** | Initial setup | First-time setup |

---

## 🎯 Step-by-Step Workflow

### Your IDS System (Linux Laptop - Ubuntu)

```bash
# 1. Navigate to scripts
cd ~/Programming/IDS/dpdk_suricata_ml_pipeline/scripts

# 2. Setup USB adapter for external traffic
sudo ./00_setup_external_capture.sh

# 3. Start IDS pipeline
sudo ./quick_start.sh
# Select option 1: Start Complete Pipeline

# 4. Verify it's running
./status_check.sh
```

### External Device (Windows)

```powershell
# 1. Configure network (PowerShell as Admin)
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 192.168.100.2 -PrefixLength 24 -DefaultGateway 192.168.100.1

# 2. Test connectivity
ping 192.168.100.1

# 3. Generate traffic (choose one)
# Option A: Simple HTTP flood
1..100 | ForEach-Object { curl "http://192.168.100.1" }

# Option B: Run script
.\attack_simulator.ps1

# Option C: Replay PCAP
tcpreplay -i "Ethernet" --mbps=10 attack.pcap
```

### External Device (Linux)

```bash
# 1. Configure network
sudo ip addr add 192.168.100.2/24 dev eth0
sudo ip link set eth0 up

# 2. Test connectivity
ping 192.168.100.1

# 3. Generate traffic (choose one)
# Option A: Replay PCAP
sudo tcpreplay -i eth0 --mbps=10 attack.pcap

# Option B: Port scan
sudo nmap -sS 192.168.100.1

# Option C: SYN flood
sudo hping3 -S 192.168.100.1 -p 80 --flood
```

---

## 🎮 Monitoring (On IDS System)

```bash
# Terminal 1: Watch packets
sudo tcpdump -i enx00e04c36074c -n

# Terminal 2: Watch Suricata alerts
tail -f logs/suricata/eve.json | jq 'select(.event_type=="alert")'

# Terminal 3: Watch ML predictions
tail -f logs/ml/consumer.log

# Terminal 4: Check stats
suricatasc -c dump-counters
```

---

## 🔧 Architecture Overview

```
┌──────────────────────┐              ┌──────────────────────┐
│  External Device     │  Ethernet    │   IDS System         │
│  (Windows/Linux)     │─────────────▶│   (Your Laptop)      │
│                      │    Cable     │                      │
│  192.168.100.2       │              │  USB Ethernet        │
│                      │              │  enx00e04c36074c     │
│  Traffic Generator:  │              │  192.168.100.1       │
│  • tcpreplay         │              │                      │
│  • Python/Scapy      │              │  ┌────────────────┐  │
│  • PowerShell        │              │  │  AF_PACKET     │  │
│  • hping3            │              │  │  Suricata      │  │
│  • nmap              │              │  └────────┬───────┘  │
│                      │              │           │          │
└──────────────────────┘              │           ▼          │
                                      │  ┌────────────────┐  │
                                      │  │     Kafka      │  │
                                      │  └────────┬───────┘  │
                                      │           │          │
                                      │           ▼          │
                                      │  ┌────────────────┐  │
                                      │  │  ML Consumer   │  │
                                      │  │  (Detection)   │  │
                                      │  └────────────────┘  │
                                      └──────────────────────┘
```

---

## 📊 Network Configuration

| Device | Interface | IP Address | Gateway |
|--------|-----------|------------|---------|
| **IDS System** | enx00e04c36074c | 192.168.100.1/24 | - |
| **External Device** | eth0 / Ethernet | 192.168.100.2/24 | 192.168.100.1 |

---

## 🛠️ Required Tools

### On IDS System (Your Laptop)
- ✅ Linux (Ubuntu) - Already installed
- ✅ Suricata - Installed
- ✅ Kafka - Installed
- ✅ Python + ML libraries - Installed
- ✅ USB Ethernet adapter - Connected

### On External Device (Windows)
- ✅ Windows 10/11
- ✅ PowerShell (built-in)
- ⚠️ Npcap (for packet tools) - Optional
- ⚠️ Python + Scapy - Optional
- ⚠️ tcpreplay - Optional

### On External Device (Linux)
- ✅ Any Linux distro
- ⚠️ tcpreplay - `sudo apt install tcpreplay`
- ⚠️ hping3 - `sudo apt install hping3`
- ⚠️ nmap - `sudo apt install nmap`
- ⚠️ Python + Scapy - `pip install scapy`

---

## 🐛 Troubleshooting Quick Reference

### Can't Ping Between Devices?

**Check IDS System:**
```bash
# Is interface up?
ip link show enx00e04c36074c

# Is IP configured?
ip addr show enx00e04c36074c

# Is cable connected?
ethtool enx00e04c36074c | grep "Link detected"
```

**Check External Device:**
```powershell
# Windows
Get-NetAdapter | Where-Object {$_.Name -eq "Ethernet"} | Select Status
Get-NetIPAddress -InterfaceAlias "Ethernet"
ping 192.168.100.1
```

```bash
# Linux
ip link show eth0
ip addr show eth0
ping 192.168.100.1
```

### No Traffic Captured?

**On IDS System:**
```bash
# Test with tcpdump
sudo tcpdump -i enx00e04c36074c -n

# Check Suricata is running
ps aux | grep suricata

# Check promiscuous mode
ip link show enx00e04c36074c | grep PROMISC
```

**On External Device:**
```bash
# Generate simple traffic
ping 192.168.100.1  # Should show up in tcpdump
```

### Suricata Not Detecting?

```bash
# Check Suricata logs
sudo tail -50 /var/log/suricata/suricata.log

# Check eve.json is being written
ls -lh logs/suricata/eve.json
tail logs/suricata/eve.json

# Check Suricata stats
suricatasc -c dump-counters | grep -E "(capture|decode)"
```

---

## 📚 Learning Path

### Beginner → Start Here
1. Read: [`WINDOWS_QUICK_SETUP.md`](WINDOWS_QUICK_SETUP.md) or [`EXTERNAL_TRAFFIC_GUIDE.md`](EXTERNAL_TRAFFIC_GUIDE.md)
2. Setup: Configure your external device network
3. Test: Ping between devices
4. Generate: Simple HTTP traffic with curl/PowerShell
5. Monitor: Watch alerts on IDS system

### Intermediate → Go Further
1. Read: [`WINDOWS_EXTERNAL_DEVICE_GUIDE.md`](WINDOWS_EXTERNAL_DEVICE_GUIDE.md)
2. Install: Python + Scapy or tcpreplay
3. Replay: Use PCAP files
4. Script: Create attack simulation scripts
5. Analyze: Study detection patterns

### Advanced → Master It
1. Read: [`PLATFORM_COMPARISON.md`](PLATFORM_COMPARISON.md)
2. Compare: Different attack tools
3. Optimize: Tune IDS performance
4. Research: Train ML models on captured data
5. Contribute: Add new attack patterns

---

## 🎓 Example Use Cases

### 1. Quick Demo
**Goal**: Show IDS detecting attacks in 5 minutes

**Steps**:
1. Setup external device (Windows PowerShell)
2. Run: `.\attack_simulator.ps1`
3. Watch IDS alerts in real-time

**Documentation**: [`WINDOWS_QUICK_SETUP.md`](WINDOWS_QUICK_SETUP.md)

### 2. ML Model Training
**Goal**: Collect diverse traffic for ML training

**Steps**:
1. Setup external device (Linux with tcpreplay)
2. Replay multiple PCAP files
3. Collect labeled data from Suricata
4. Train ML models on captured features

**Documentation**: [`EXTERNAL_TRAFFIC_GUIDE.md`](EXTERNAL_TRAFFIC_GUIDE.md)

### 3. IDS Performance Testing
**Goal**: Test IDS under load

**Steps**:
1. Setup multiple external devices
2. Generate high-volume traffic
3. Monitor IDS performance metrics
4. Tune Suricata configuration

**Documentation**: [`RUNTIME_GUIDE.md`](RUNTIME_GUIDE.md)

### 4. Security Research
**Goal**: Research new attack detection methods

**Steps**:
1. Setup Linux with full toolkit (Kali)
2. Generate various attack patterns
3. Analyze detection rates
4. Develop new detection rules

**Documentation**: [`EXTERNAL_TRAFFIC_GUIDE.md`](EXTERNAL_TRAFFIC_GUIDE.md)

---

## 💡 Pro Tips

### For Windows Users
- ✅ PowerShell is surprisingly powerful - start there!
- ✅ No need to install anything for basic testing
- ✅ Use `Get-Help` to learn PowerShell commands
- ✅ Scripts can be scheduled with Task Scheduler

### For Linux Users
- ✅ Raspberry Pi makes a great dedicated traffic generator
- ✅ tmux/screen for running multiple attacks simultaneously
- ✅ cron jobs for automated testing
- ✅ iptables for advanced traffic manipulation

### For Everyone
- ✅ Start simple - ping and curl first!
- ✅ Watch both sender and receiver to debug issues
- ✅ Use Wireshark on external device to verify packets are sent
- ✅ Save your scripts - reuse for future testing
- ✅ Label your Ethernet cables to avoid confusion

---

## 🎯 Summary Checklist

Before you start:
- [ ] External device available (Windows or Linux)
- [ ] Ethernet cable
- [ ] IDS system configured (run `00_setup_external_capture.sh`)
- [ ] Chosen which guide to follow

Setup:
- [ ] External device network configured (192.168.100.2)
- [ ] Can ping IDS system (192.168.100.1)
- [ ] IDS pipeline running (Kafka + Suricata + ML)

Testing:
- [ ] Traffic generation tool chosen
- [ ] Test traffic sent
- [ ] tcpdump shows packets on IDS
- [ ] Suricata alerts appearing
- [ ] ML predictions working

---

## 📞 Quick Reference

| Need | Documentation |
|------|---------------|
| **Windows 5-min setup** | [WINDOWS_QUICK_SETUP.md](WINDOWS_QUICK_SETUP.md) |
| **Windows detailed guide** | [WINDOWS_EXTERNAL_DEVICE_GUIDE.md](WINDOWS_EXTERNAL_DEVICE_GUIDE.md) |
| **Linux setup** | [EXTERNAL_TRAFFIC_GUIDE.md](EXTERNAL_TRAFFIC_GUIDE.md) |
| **Choose platform** | [PLATFORM_COMPARISON.md](PLATFORM_COMPARISON.md) |
| **IDS setup** | [AF_PACKET_QUICK_START.md](AF_PACKET_QUICK_START.md) |
| **Troubleshooting** | Any guide has troubleshooting section |

---

## 🚀 Ready to Start?

**Windows Users** → [`WINDOWS_QUICK_SETUP.md`](WINDOWS_QUICK_SETUP.md)

**Linux Users** → [`EXTERNAL_TRAFFIC_GUIDE.md`](EXTERNAL_TRAFFIC_GUIDE.md)

**Need Help Choosing?** → [`PLATFORM_COMPARISON.md`](PLATFORM_COMPARISON.md)

---

**Your complete IDS testing environment is ready! 🎉**
