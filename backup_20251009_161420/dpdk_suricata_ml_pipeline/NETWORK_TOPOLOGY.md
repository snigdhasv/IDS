# Network Topology Diagrams

## 🔴 Old Setup: Local PCAP Replay (Not What You Want)

```
┌─────────────────────────────────────────────┐
│        Your IDS System (Laptop)             │
│                                             │
│  ┌─────────────────┐                       │
│  │ 05_replay       │                       │
│  │ _traffic.sh     │                       │
│  │ (tcpreplay)     │                       │
│  └────────┬────────┘                       │
│           │                                 │
│           ▼ (loopback/same interface)      │
│  ┌─────────────────┐                       │
│  │  USB Adapter    │                       │
│  │  enx00e04c...   │                       │
│  │  AF_PACKET      │                       │
│  └────────┬────────┘                       │
│           │                                 │
│           ▼                                 │
│  ┌─────────────────┐                       │
│  │    Suricata     │→ Kafka → ML Pipeline  │
│  └─────────────────┘                       │
└─────────────────────────────────────────────┘

❌ Problem: Everything runs on same system
```

---

## ✅ New Setup: External Traffic Source (What You Want!)

```
┌──────────────────────┐              ┌──────────────────────────┐
│  External Device     │              │   Your IDS System        │
│  (Traffic Source)    │              │   (Laptop)               │
│                      │              │                          │
│  ┌────────────────┐  │   Ethernet   │  ┌────────────────────┐ │
│  │  tcpreplay     │  │    Cable     │  │   USB Adapter      │ │
│  │  or            │  │ ════════════▶│  │   enx00e04c...     │ │
│  │  scapy         │  │              │  │   192.168.100.1    │ │
│  │  or            │  │              │  │   (AF_PACKET)      │ │
│  │  hping3        │  │              │  └─────────┬──────────┘ │
│  │  or            │  │              │            │            │
│  │  metasploit    │  │              │            ▼            │
│  └────────────────┘  │              │  ┌────────────────────┐ │
│                      │              │  │    Suricata        │ │
│  eth0: 192.168.100.2 │              │  │    (IDS)           │ │
│                      │              │  └─────────┬──────────┘ │
│  Examples:           │              │            │            │
│  • Kali Linux        │              │            ▼            │
│  • Raspberry Pi      │              │  ┌────────────────────┐ │
│  • Another PC        │              │  │      Kafka         │ │
│  • VM                │              │  └─────────┬──────────┘ │
└──────────────────────┘              │            │            │
                                      │            ▼            │
                                      │  ┌────────────────────┐ │
                                      │  │   ML Consumer      │ │
                                      │  │   (Predictions)    │ │
                                      │  └────────────────────┘ │
                                      └──────────────────────────┘

✅ Benefits:
   • Realistic traffic flow
   • Separate attack generation
   • Can use any PCAP replay tool
   • External device dedicated to traffic generation
   • Your laptop focuses on detection
```

---

## 🌐 Network Addressing

```
192.168.100.0/24 Network

┌─────────────────────────────────────────────────────────┐
│                                                         │
│  192.168.100.1        USB Adapter                       │
│  ┌──────────────┐     (Your IDS System)                │
│  │ enx00e04c... │                                       │
│  └──────────────┘                                       │
│         │                                               │
│         │ Ethernet Cable                                │
│         │                                               │
│  ┌──────────────┐                                       │
│  │     eth0     │     192.168.100.2                     │
│  └──────────────┘     (External Device)                │
│                                                         │
│  You can add more devices:                             │
│  • 192.168.100.3 - Second attack generator             │
│  • 192.168.100.4 - Third attack generator              │
│  • etc.                                                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📡 Traffic Flow Diagram

```
External Device → USB Adapter → Suricata → Kafka → ML Consumer
(192.168.100.2)   (enx00e04c..)  (IDS)     (Bus)   (Detector)
                  (192.168.100.1)

Step-by-Step:
┌─────┐
│  1  │ External device sends packets via Ethernet
└──┬──┘
   │
   ▼
┌─────┐
│  2  │ USB adapter receives packets (promiscuous mode)
└──┬──┘
   │
   ▼
┌─────┐
│  3  │ AF_PACKET passes packets to Suricata
└──┬──┘
   │
   ▼
┌─────┐
│  4  │ Suricata analyzes traffic, generates alerts
└──┬──┘
   │
   ▼
┌─────┐
│  5  │ Alerts sent to Kafka topic
└──┬──┘
   │
   ▼
┌─────┐
│  6  │ ML Consumer reads from Kafka
└──┬──┘
   │
   ▼
┌─────┐
│  7  │ ML model predicts attack type
└──┬──┘
   │
   ▼
┌─────┐
│  8  │ Results logged and can trigger actions
└─────┘
```

---

## 🔧 Physical Connection Options

### Option 1: Direct Connection (Simplest)
```
┌──────────────┐                    ┌──────────────┐
│  External    │  Ethernet Cable    │  IDS System  │
│  Device      │═══════════════════▶│  USB Adapter │
│  (eth0)      │                    │  (enx00e0..) │
└──────────────┘                    └──────────────┘
```

### Option 2: Through Switch (Multiple Devices)
```
┌──────────────┐
│  External    │
│  Device 1    │════╗
└──────────────┘    ║
                    ║     ┌──────────┐     ┌──────────────┐
┌──────────────┐    ║     │          │     │  IDS System  │
│  External    │════╬════▶│  Switch  │════▶│  USB Adapter │
│  Device 2    │════╣     │          │     │  (enx00e0..) │
└──────────────┘    ║     └──────────┘     └──────────────┘
                    ║
┌──────────────┐    ║
│  External    │════╝
│  Device 3    │
└──────────────┘
```

### Option 3: SPAN/Mirror Port (Production Network)
```
┌──────────────┐                ┌──────────┐
│  Production  │                │ Managed  │
│  Device A    │═══════════════▶│ Switch   │
└──────────────┘                │          │
                                │  SPAN    │════▶ ┌──────────────┐
┌──────────────┐                │  Port    │      │  IDS System  │
│  Production  │═══════════════▶│  Mirror  │      │  USB Adapter │
│  Device B    │                │          │      └──────────────┘
└──────────────┘                └──────────┘
                                     ▲
                        Copies all traffic to IDS
```

---

## 🎯 Use Case Examples

### Use Case 1: Malware Analysis Lab
```
┌───────────────────────────────────────────────────┐
│  Isolated Lab Network (192.168.100.0/24)         │
│                                                   │
│  ┌──────────────┐         ┌──────────────────┐   │
│  │ Kali Linux   │         │ Your IDS         │   │
│  │ (Attacker)   │════════▶│ (Defender)       │   │
│  │ .100.2       │         │ .100.1           │   │
│  └──────────────┘         └──────────────────┘   │
│                                                   │
│  Run attacks, capture everything!                │
└───────────────────────────────────────────────────┘
```

### Use Case 2: PCAP Replay Testing
```
┌───────────────────────────────────────────────────┐
│  Testing Environment                              │
│                                                   │
│  ┌──────────────┐         ┌──────────────────┐   │
│  │ Raspberry Pi │         │ Your IDS         │   │
│  │ (Replayer)   │════════▶│ (Analyzer)       │   │
│  │ .100.2       │         │ .100.1           │   │
│  │              │         │                  │   │
│  │ tcpreplay    │         │ Suricata + ML    │   │
│  │ CICIDS2017   │         │                  │   │
│  └──────────────┘         └──────────────────┘   │
│                                                   │
└───────────────────────────────────────────────────┘
```

### Use Case 3: Multi-Attacker Simulation
```
┌──────────────────────────────────────────────────────┐
│  Advanced Testing Environment                        │
│                                                      │
│  ┌──────────┐                                        │
│  │ Device 1 │                                        │
│  │ DDoS     │════╗                                   │
│  └──────────┘    ║                                   │
│                  ║    ┌────────┐   ┌─────────────┐  │
│  ┌──────────┐    ║    │        │   │  Your IDS   │  │
│  │ Device 2 │════╬═══▶│ Switch │══▶│  All-in-One │  │
│  │ Scan     │════╣    │        │   │  Detection  │  │
│  └──────────┘    ║    └────────┘   └─────────────┘  │
│                  ║                                   │
│  ┌──────────┐    ║                                   │
│  │ Device 3 │════╝                                   │
│  │ Exploit  │                                        │
│  └──────────┘                                        │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 📊 Data Flow with Protocols

```
External Device (192.168.100.2)
         │
         │ Ethernet Frame
         │ [Src MAC: aa:bb:cc:dd:ee:ff]
         │ [Dst MAC: 00:e0:4c:36:07:4c]
         │
         │ IP Packet
         │ [Src IP: 192.168.100.2]
         │ [Dst IP: 192.168.100.1 or any target]
         │
         │ TCP/UDP/ICMP
         │ [Various ports and protocols]
         │
         ▼
USB Adapter (enx00e04c36074c)
         │ Promiscuous mode captures ALL packets
         │ Not just packets destined for this IP
         │
         ▼
AF_PACKET Socket
         │ Raw packet delivery to userspace
         │ Zero-copy when possible
         │
         ▼
Suricata IDS
         │ Deep packet inspection
         │ Pattern matching
         │ Protocol analysis
         │
         ▼
Kafka Topic (suricata-alerts)
         │ JSON formatted alerts
         │ {event_type: "alert", ...}
         │
         ▼
ML Consumer
         │ Feature extraction
         │ Model inference
         │ Threat classification
         │
         ▼
Logs & Actions
         │ Alert logs
         │ ML predictions
         │ Optional: Block IP, notify admin, etc.
         │
         ▼
```

---

## 🎮 Quick Start Topology

```
┌──────────────────────────────────────────────────────────┐
│                     QUICK START                          │
└──────────────────────────────────────────────────────────┘

Step 1: On IDS System
┌────────────────────────────────────────┐
│ $ sudo ./00_setup_external_capture.sh  │
│   ✓ Configures USB adapter            │
│   ✓ IP: 192.168.100.1/24               │
│   ✓ Promiscuous mode                   │
└────────────────────────────────────────┘
                 │
                 ▼
Step 2: Connect Cable
┌────────────────────────────────────────┐
│  External Device ═══════▶ USB Adapter  │
│   (eth0)                  (enx00e0..)  │
└────────────────────────────────────────┘
                 │
                 ▼
Step 3: Configure External Device
┌────────────────────────────────────────┐
│ $ sudo ip addr add 192.168.100.2/24   │
│   dev eth0                             │
│ $ sudo ip link set eth0 up            │
│ $ ping 192.168.100.1  # Test!         │
└────────────────────────────────────────┘
                 │
                 ▼
Step 4: Start IDS Pipeline
┌────────────────────────────────────────┐
│ $ sudo ./quick_start.sh                │
│   Select: 1 (Start Complete Pipeline)  │
│   ✓ Kafka                              │
│   ✓ Suricata                           │
│   ✓ ML Consumer                        │
└────────────────────────────────────────┘
                 │
                 ▼
Step 5: Replay Traffic from External Device
┌────────────────────────────────────────┐
│ $ sudo tcpreplay -i eth0 attack.pcap  │
│   → Packets flow to IDS                │
│   → Suricata detects attacks           │
│   → ML classifies threats              │
└────────────────────────────────────────┘
```

---

## ✅ Verification Checklist

```
IDS System Checks:
├─ [ ] USB adapter has IP 192.168.100.1
├─ [ ] Interface is UP and PROMISC
├─ [ ] Can ping 192.168.100.2
├─ [ ] Suricata is running
├─ [ ] Kafka is running
├─ [ ] ML consumer is running
└─ [ ] tcpdump shows packets on enx00e04c36074c

External Device Checks:
├─ [ ] Has IP 192.168.100.2/24
├─ [ ] Interface is UP
├─ [ ] Can ping 192.168.100.1
├─ [ ] ARP entry exists for .100.1
├─ [ ] Can replay PCAPs
└─ [ ] tcpdump shows outgoing packets

Data Flow Checks:
├─ [ ] Packets visible in tcpdump on IDS
├─ [ ] Suricata eve.json being written
├─ [ ] Kafka has messages in topic
├─ [ ] ML consumer processing alerts
└─ [ ] Predictions appearing in logs
```

**All green? You're capturing external traffic! 🎉**
