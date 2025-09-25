#!/usr/bin/env python3
"""
Simple DPDK Packet Generator and Monitor

This script provides a simple way to generate packets with pktgen
and monitor the results.
"""

import os
import sys
import time
import subprocess
import signal
import threading
from typing import Optional, Dict, List
from config import DEFAULT_CONFIG


class SimplePacketMonitor:
    """Simple packet monitoring using system tools"""
    
    def __init__(self, interface: str = "lo"):
        self.interface = interface
        self.monitoring = False
        self.stats = {
            'packets_seen': 0,
            'bytes_seen': 0,
            'start_time': None,
            'end_time': None
        }
    
    def start_monitoring(self, duration: int = 30):
        """Start monitoring packets"""
        print(f"Starting packet monitoring on {self.interface} for {duration} seconds...")
        
        self.stats['start_time'] = time.time()
        self.monitoring = True
        
        def monitor_thread():
            try:
                # Use netstat to monitor interface statistics
                cmd = ['cat', f'/proc/net/dev']
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                # Parse initial stats
                initial_stats = self._parse_interface_stats(result.stdout)
                
                time.sleep(duration)
                
                # Parse final stats
                result = subprocess.run(cmd, capture_output=True, text=True)
                final_stats = self._parse_interface_stats(result.stdout)
                
                # Calculate differences
                if initial_stats and final_stats:
                    self.stats['packets_seen'] = final_stats['rx_packets'] - initial_stats['rx_packets']
                    self.stats['bytes_seen'] = final_stats['rx_bytes'] - initial_stats['rx_bytes']
                
                self.stats['end_time'] = time.time()
                self.monitoring = False
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                self.monitoring = False
        
        thread = threading.Thread(target=monitor_thread)
        thread.daemon = True
        thread.start()
        
        return thread
    
    def _parse_interface_stats(self, proc_dev_content: str) -> Optional[Dict]:
        """Parse /proc/net/dev content for interface stats"""
        for line in proc_dev_content.split('\n'):
            if self.interface + ':' in line:
                parts = line.split()
                if len(parts) >= 10:
                    return {
                        'rx_bytes': int(parts[1]),
                        'rx_packets': int(parts[2]),
                        'tx_bytes': int(parts[9]),
                        'tx_packets': int(parts[10])
                    }
        return None
    
    def get_stats(self) -> Dict:
        """Get monitoring statistics"""
        stats = self.stats.copy()
        if stats['start_time'] and stats['end_time']:
            duration = stats['end_time'] - stats['start_time']
            stats['duration'] = duration
            if duration > 0:
                stats['pps'] = stats['packets_seen'] / duration
                stats['bps'] = stats['bytes_seen'] / duration
        return stats


class SimplePktgenRunner:
    """Simple pktgen runner for basic testing"""
    
    def __init__(self, config=None):
        self.config = config or DEFAULT_CONFIG
        self.process: Optional[subprocess.Popen] = None
    
    def create_test_config(self, output_file: str, test_duration: int = 10):
        """Create a simple test configuration file"""
        config_content = f'''-- Simple Pktgen Test Configuration
package.path = package.path ..";?.lua;test/?.lua;app/?.lua;"

printf("=== Simple Pktgen Test ===\\n");

-- Display system information
printf("Available ports: ");
pktgen.portCount();

-- Basic configuration for port 0 (if available)
if pktgen.portCount() > 0 then
    printf("Configuring port 0\\n");
    
    -- Set packet parameters
    pktgen.set("0", "size", {self.config.pktgen.packet_size});
    pktgen.set("0", "rate", {self.config.pktgen.packet_rate});
    pktgen.set("0", "count", {test_duration * 100});  -- Approximate packet count
    
    -- Set addresses
    pktgen.set_mac("0", "{self.config.pktgen.src_mac}");
    pktgen.set_ipaddr("0", "src", "{self.config.pktgen.src_ip}/24");
    pktgen.set_ipaddr("0", "dst", "{self.config.pktgen.dst_ip}");
    
    -- Set protocol
    pktgen.set_proto("0", "udp");
    pktgen.set_port_value("0", "sport", {self.config.pktgen.src_port});
    pktgen.set_port_value("0", "dport", {self.config.pktgen.dst_port});
    
    printf("Configuration complete\\n");
    
    -- Start transmission
    printf("Starting packet transmission...\\n");
    pktgen.start("0");
    
    -- Run for specified duration
    sleep({test_duration});
    
    -- Stop transmission
    pktgen.stop("0");
    printf("Transmission stopped\\n");
    
    -- Show statistics
    pktgen.page("stats");
    sleep(2);
    
    -- Show final stats
    printf("=== Final Statistics ===\\n");
    pktgen.show("stats");
    
else
    printf("ERROR: No ports available for testing\\n");
    printf("Make sure DPDK interfaces are properly bound\\n");
end

printf("Test completed\\n");
'''
        
        with open(output_file, 'w') as f:
            f.write(config_content)
        
        return output_file
    
    def run_loopback_test(self, duration: int = 10) -> bool:
        """Run a loopback test using software interfaces"""
        try:
            print("=== Running Loopback Test ===")
            
            # Create configuration
            config_file = f"/tmp/pktgen_loopback_{int(time.time())}.lua"
            self.create_test_config(config_file, duration)
            
            # Prepare command for loopback testing
            cmd = [
                'sudo', 'pktgen',
                '-c', '0x3',  # Use cores 0 and 1
                '-n', '4',    # 4 memory channels
                '--vdev', 'net_pcap0,iface=lo',  # Use loopback interface
                '--',
                '-P',  # Promiscuous mode
                '-m', '[1].0',  # Map core 1 to port 0
                '-f', config_file
            ]
            
            print(f"Running command: {' '.join(cmd)}")
            print(f"Test duration: {duration} seconds")
            print("Starting pktgen...")
            
            # Run pktgen
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for completion
            stdout, stderr = self.process.communicate(timeout=duration + 30)
            
            print("=== Pktgen Output ===")
            print(stdout)
            
            if stderr:
                print("=== Pktgen Errors ===")
                print(stderr)
            
            # Clean up
            os.unlink(config_file)
            
            return self.process.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("Pktgen test timed out")
            if self.process:
                self.process.kill()
            return False
        except Exception as e:
            print(f"Error running loopback test: {e}")
            return False
    
    def run_basic_interface_test(self, pci_device: str, duration: int = 10) -> bool:
        """Run test with a specific PCI device"""
        try:
            print(f"=== Running Interface Test on {pci_device} ===")
            
            # Create configuration
            config_file = f"/tmp/pktgen_interface_{int(time.time())}.lua"
            self.create_test_config(config_file, duration)
            
            # Prepare command
            cmd = [
                'sudo', 'pktgen',
                '-c', self.config.pktgen.cores,
                '-n', str(self.config.pktgen.memory_channels),
                '--',
                '-P',  # Promiscuous mode
                '-m', self.config.pktgen.ports_mapping,
                '-f', config_file
            ]
            
            print(f"Running command: {' '.join(cmd)}")
            print(f"Test duration: {duration} seconds")
            
            # Run pktgen
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for completion
            stdout, stderr = self.process.communicate(timeout=duration + 30)
            
            print("=== Pktgen Output ===")
            print(stdout)
            
            if stderr:
                print("=== Pktgen Errors ===")
                print(stderr)
            
            # Clean up
            os.unlink(config_file)
            
            return self.process.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("Pktgen test timed out")
            if self.process:
                self.process.kill()
            return False
        except Exception as e:
            print(f"Error running interface test: {e}")
            return False


def show_network_interfaces():
    """Display available network interfaces"""
    print("=== Available Network Interfaces ===")
    
    try:
        # Show kernel interfaces
        result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
        print("Kernel interfaces:")
        for line in result.stdout.split('\n'):
            if ': ' in line and 'state' in line.lower():
                print(f"  {line.strip()}")
        
        print()
        
        # Show DPDK status
        if os.path.exists('/usr/local/bin/dpdk-devbind.py'):
            result = subprocess.run(['/usr/local/bin/dpdk-devbind.py', '--status'], 
                                  capture_output=True, text=True)
            print("DPDK interface status:")
            print(result.stdout)
        else:
            print("DPDK devbind tool not found")
    
    except Exception as e:
        print(f"Error showing interfaces: {e}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("""
Simple DPDK Packet Generator and Monitor

Usage:
    python3 simple_packet_test.py <command> [options]

Commands:
    interfaces      - Show available network interfaces
    loopback       - Run loopback test (no interface binding required)
    interface <pci> - Run test with specific PCI device (requires binding)
    monitor <iface> - Monitor packets on interface

Examples:
    python3 simple_packet_test.py interfaces
    python3 simple_packet_test.py loopback
    python3 simple_packet_test.py interface 0000:02:00.0
    python3 simple_packet_test.py monitor lo
""")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'interfaces':
        show_network_interfaces()
    
    elif command == 'loopback':
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        
        print("Setting up environment...")
        os.environ['RTE_SDK'] = DEFAULT_CONFIG.dpdk.rte_sdk
        os.environ['RTE_TARGET'] = DEFAULT_CONFIG.dpdk.rte_target
        
        runner = SimplePktgenRunner()
        success = runner.run_loopback_test(duration)
        
        if success:
            print("✓ Loopback test completed successfully")
        else:
            print("✗ Loopback test failed")
    
    elif command == 'interface':
        if len(sys.argv) < 3:
            print("Error: PCI device required for interface test")
            return
        
        pci_device = sys.argv[2]
        duration = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        
        print("Setting up environment...")
        os.environ['RTE_SDK'] = DEFAULT_CONFIG.dpdk.rte_sdk
        os.environ['RTE_TARGET'] = DEFAULT_CONFIG.dpdk.rte_target
        
        print(f"WARNING: This will use PCI device {pci_device}")
        print("Make sure it's bound to DPDK driver first!")
        
        runner = SimplePktgenRunner()
        success = runner.run_basic_interface_test(pci_device, duration)
        
        if success:
            print("✓ Interface test completed successfully")
        else:
            print("✗ Interface test failed")
    
    elif command == 'monitor':
        if len(sys.argv) < 3:
            interface = 'lo'
        else:
            interface = sys.argv[2]
        
        duration = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        
        monitor = SimplePacketMonitor(interface)
        monitor_thread = monitor.start_monitoring(duration)
        
        print(f"Monitoring {interface} for {duration} seconds...")
        print("You can now run packet generation in another terminal")
        
        monitor_thread.join()
        
        stats = monitor.get_stats()
        print(f"\n=== Monitoring Results ===")
        print(f"Packets seen: {stats['packets_seen']}")
        print(f"Bytes seen: {stats['bytes_seen']}")
        if 'pps' in stats:
            print(f"Packets per second: {stats['pps']:.2f}")
            print(f"Bytes per second: {stats['bps']:.2f}")
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
