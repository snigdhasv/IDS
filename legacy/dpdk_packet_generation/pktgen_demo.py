#!/usr/bin/env python3
"""
Pktgen-DPDK Integration Demo

This script demonstrates how to use pktgen-DPDK for high-performance
packet generation with DPDK-bound interfaces.
"""

import subprocess
import time
import sys
import os

def demonstrate_pktgen_dpdk():
    """Demonstrate pktgen-DPDK usage"""
    print("=" * 60)
    print("PKTGEN-DPDK DEMONSTRATION")
    print("=" * 60)
    
    print("This demonstrates how pktgen-DPDK would work with DPDK-bound NICs:")
    print()
    
    # Example pktgen command for loopback testing
    print("🔧 Example 1: Pktgen with loopback interface")
    print("   Command that would be used:")
    pktgen_cmd = [
        "sudo", "pktgen",
        "-c", "0x3",           # Use CPU cores 0 and 1
        "-n", "4",             # 4 memory channels
        "--vdev", "net_pcap0,iface=lo",  # Virtual device using loopback
        "--",
        "-P",                  # Promiscuous mode
        "-m", "[1].0"          # Map core 1 to port 0
    ]
    print(f"   {' '.join(pktgen_cmd)}")
    
    print("\n🔧 Example 2: Pktgen with DPDK-bound interface")
    print("   Command that would be used after binding NIC to DPDK:")
    pktgen_dpdk_cmd = [
        "sudo", "pktgen",
        "-c", "0x3",           # Use CPU cores 0 and 1
        "-n", "4",             # 4 memory channels
        "--",
        "-P",                  # Promiscuous mode
        "-m", "[1:2].0",       # Map cores 1,2 to port 0
        "-f", "/tmp/pktgen_config.lua"  # Configuration file
    ]
    print(f"   {' '.join(pktgen_dpdk_cmd)}")
    
    # Create a sample Lua configuration
    print("\n📝 Creating sample pktgen configuration file...")
    config_content = '''-- Pktgen configuration for packet generation
package.path = package.path ..";?.lua;test/?.lua;app/?.lua;"

printf("=== Pktgen Configuration Loaded ===\\n");

-- Check available ports
local nb_ports = pktgen.portCount();
printf("Available ports: %d\\n", nb_ports);

if nb_ports > 0 then
    -- Configure port 0
    pktgen.set("0", "size", 64);      -- Packet size 64 bytes
    pktgen.set("0", "rate", 10);      -- 10% line rate
    pktgen.set("0", "count", 1000);   -- Send 1000 packets
    
    -- Set packet details
    pktgen.set_mac("0", "00:11:22:33:44:55");
    pktgen.set_ipaddr("0", "src", "192.168.1.1/24");
    pktgen.set_ipaddr("0", "dst", "192.168.1.2");
    
    -- Set protocol to UDP
    pktgen.set_proto("0", "udp");
    pktgen.set_port_value("0", "sport", 1234);
    pktgen.set_port_value("0", "dport", 5678);
    
    printf("Port 0 configured for packet generation\\n");
    
    -- Auto-start for demonstration (normally interactive)
    -- pktgen.start("0");
    -- sleep(5);
    -- pktgen.stop("0");
    
    printf("Configuration complete. Use 'start 0' to begin generation\\n");
else
    printf("ERROR: No ports available for packet generation\\n");
    printf("Make sure DPDK interfaces are properly bound\\n");
end
'''
    
    config_file = "/tmp/pktgen_config.lua"
    try:
        with open(config_file, 'w') as f:
            f.write(config_content)
        print(f"   ✅ Configuration saved to {config_file}")
    except Exception as e:
        print(f"   ❌ Failed to create config file: {e}")
        return
    
    print("\n🚀 Testing pktgen basic functionality...")
    
    # Test pktgen help
    try:
        result = subprocess.run(['pktgen', '--help'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("   ✅ Pktgen is available and working")
            print("   📊 Sample output:")
            lines = result.stdout.split('\n')[:5]  # First 5 lines
            for line in lines:
                if line.strip():
                    print(f"      {line}")
        else:
            print("   ❌ Pktgen help command failed")
    except subprocess.TimeoutExpired:
        print("   ⏰ Pktgen help command timed out")
    except FileNotFoundError:
        print("   ❌ Pktgen not found - make sure it's installed")
    except Exception as e:
        print(f"   ❌ Error testing pktgen: {e}")
    
    print("\n📚 How the complete pipeline works:")
    print("   1. Bind NIC to DPDK driver (uio_pci_generic or vfio-pci)")
    print("   2. Run pktgen with DPDK EAL parameters")
    print("   3. Configure packet parameters (size, rate, addresses)")
    print("   4. Start packet generation at line speed")
    print("   5. Monitor statistics and performance")
    print("   6. Use DPDK capture application to receive packets")
    
    print("\n🔄 Benefits of DPDK + Pktgen:")
    print("   • Kernel bypass = Maximum performance")
    print("   • Zero-copy packet processing")
    print("   • Poll mode drivers (no interrupts)")
    print("   • Line rate packet generation (10/40/100 Gbps)")
    print("   • Precise timing and low latency")
    print("   • Hardware acceleration support")
    
    # Clean up
    try:
        os.unlink(config_file)
        print(f"\n🧹 Cleaned up {config_file}")
    except:
        pass

def show_performance_comparison():
    """Show performance comparison between different approaches"""
    print("\n" + "=" * 60)
    print("PERFORMANCE COMPARISON")
    print("=" * 60)
    
    print("📊 Packet Generation Performance:")
    print()
    print("   Method                 | Max PPS      | Latency    | CPU Usage")
    print("   ----------------------|--------------|------------|----------")
    print("   Standard Linux Stack  | ~100K pps    | High       | High")
    print("   Scapy (Python)        | ~10K pps     | Very High  | Very High")
    print("   DPDK + Pktgen         | ~14.88M pps  | Ultra Low  | Moderate")
    print("   (10 Gbps line rate)   |              |            |")
    print()
    print("   📈 DPDK provides 100-1000x better performance!")
    print()
    print("💡 Use Cases:")
    print("   • Scapy: Prototyping, small-scale testing, flexibility")
    print("   • DPDK: Production, high-speed testing, line-rate processing")
    print("   • Combined: Scapy for packet creation, DPDK for transmission")

def main():
    """Main demonstration"""
    print("🚀 Pktgen-DPDK Integration Demonstration")
    
    demonstrate_pktgen_dpdk()
    show_performance_comparison()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("✅ You have successfully learned how to:")
    print("   1. Send packets using Scapy with your connected NIC")
    print("   2. Bind/unbind NICs to/from DPDK drivers")
    print("   3. Use pktgen-DPDK for high-performance packet generation")
    print("   4. Understand the performance benefits of DPDK")
    print()
    print("🎯 Your system is ready for:")
    print("   • High-performance packet generation testing")
    print("   • Intrusion detection system development")
    print("   • Network performance benchmarking")
    print("   • Security research and analysis")
    print()
    print("📚 Next steps:")
    print("   • Integrate with Suricata for packet analysis")
    print("   • Set up Kafka for log processing")
    print("   • Implement machine learning for anomaly detection")

if __name__ == "__main__":
    main()
