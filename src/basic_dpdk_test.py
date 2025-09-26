#!/usr/bin/env python3
"""
Basic DPDK Functionality Test

This script tests DPDK without requiring interface binding,
focusing on environment setup and basic functionality verification.
"""

import os
import sys
import subprocess
import time
from config import DEFAULT_CONFIG


def test_dpdk_environment():
    """Test basic DPDK environment setup"""
    print("=== Testing DPDK Environment ===")
    
    # Set environment variables
    os.environ['RTE_SDK'] = DEFAULT_CONFIG.dpdk.rte_sdk
    os.environ['RTE_TARGET'] = DEFAULT_CONFIG.dpdk.rte_target
    
    # Check hugepages
    try:
        with open('/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages', 'r') as f:
            nr_hugepages = int(f.read().strip())
        
        with open('/sys/kernel/mm/hugepages/hugepages-2048kB/free_hugepages', 'r') as f:
            free_hugepages = int(f.read().strip())
        
        print(f"✓ Hugepages: {nr_hugepages} total, {free_hugepages} free, {nr_hugepages * 2}MB total")
        
        if nr_hugepages < 100:
            print("⚠ Warning: Low hugepage count, may affect performance")
        
        return True
    except Exception as e:
        print(f"✗ Hugepage check failed: {e}")
        return False


def test_dpdk_tools():
    """Test DPDK tools availability"""
    print("\n=== Testing DPDK Tools ===")
    
    tools = [
        '/usr/local/bin/dpdk-devbind.py',
        '/usr/local/bin/dpdk-hugepages.py',
        'pktgen',
    ]
    
    success = True
    for tool in tools:
        try:
            if tool.startswith('/'):
                if os.path.exists(tool):
                    print(f"✓ {tool} - Available")
                else:
                    print(f"✗ {tool} - Not found")
                    success = False
            else:
                result = subprocess.run(['which', tool], capture_output=True)
                if result.returncode == 0:
                    path = result.stdout.decode().strip()
                    print(f"✓ {tool} - Available at {path}")
                else:
                    print(f"✗ {tool} - Not found in PATH")
                    success = False
        except Exception as e:
            print(f"✗ {tool} - Error: {e}")
            success = False
    
    return success


def test_dpdk_libs():
    """Test DPDK library availability"""
    print("\n=== Testing DPDK Libraries ===")
    
    try:
        result = subprocess.run(['pkg-config', '--exists', 'libdpdk'], capture_output=True)
        if result.returncode == 0:
            print("✓ DPDK pkg-config available")
            
            # Get version
            result = subprocess.run(['pkg-config', '--modversion', 'libdpdk'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✓ DPDK version: {version}")
            
            # Get libraries
            result = subprocess.run(['pkg-config', '--libs', 'libdpdk'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                libs = result.stdout.strip()
                print(f"✓ DPDK libraries: {len(libs.split())} libraries linked")
            
            return True
        else:
            print("✗ DPDK pkg-config not available")
            return False
    except Exception as e:
        print(f"✗ Library check failed: {e}")
        return False


def test_simple_dpdk_app():
    """Test a simple DPDK application"""
    print("\n=== Testing Simple DPDK Application ===")
    
    # Create a minimal DPDK test application
    test_code = '''
#include <rte_eal.h>
#include <rte_common.h>
#include <rte_log.h>
#include <rte_lcore.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    int ret = rte_eal_init(argc, argv);
    if (ret < 0) {
        printf("ERROR: EAL initialization failed\\n");
        return -1;
    }
    
    printf("SUCCESS: DPDK EAL initialized successfully\\n");
    printf("Available lcores: %u\\n", rte_lcore_count());
    
    rte_eal_cleanup();
    return 0;
}
'''
    
    try:
        # Write test application
        with open('/tmp/dpdk_test.c', 'w') as f:
            f.write(test_code)
        
        # Compile test application using pkg-config for proper linking
        try:
            # Get DPDK compile and link flags
            cflags_result = subprocess.run(['pkg-config', '--cflags', 'libdpdk'], 
                                         capture_output=True, text=True)
            libs_result = subprocess.run(['pkg-config', '--libs', 'libdpdk'], 
                                       capture_output=True, text=True)
            
            if cflags_result.returncode != 0 or libs_result.returncode != 0:
                raise Exception("Failed to get DPDK flags from pkg-config")
            
            cflags = cflags_result.stdout.strip().split()
            libs = libs_result.stdout.strip().split()
            
            compile_cmd = ['gcc', '-o', '/tmp/dpdk_test', '/tmp/dpdk_test.c'] + cflags + libs
            
        except Exception as e:
            print(f"⚠ pkg-config failed, using fallback flags: {e}")
            # Fallback to basic flags
            compile_cmd = [
                'gcc', '-o', '/tmp/dpdk_test', '/tmp/dpdk_test.c',
                '-I/usr/local/include',
                '-L/usr/local/lib/x86_64-linux-gnu',
                '-lrte_eal', '-lrte_mbuf', '-lrte_mempool', '-lrte_ring',
                '-lpthread', '-lnuma', '-ldl'
            ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("✗ Failed to compile DPDK test application")
            print(f"Compile error: {result.stderr}")
            return False
        
        print("✓ DPDK test application compiled successfully")
        
        # Run test application with in-memory mode to avoid hugepage permission issues
        run_cmd = ['/tmp/dpdk_test', '--in-memory', '--log-level=*:info']
        result = subprocess.run(run_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and "SUCCESS" in result.stdout:
            print("✓ DPDK test application ran successfully")
            print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print("✗ DPDK test application failed")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False
        
    except subprocess.TimeoutExpired:
        print("✗ DPDK test application timed out")
        return False
    except Exception as e:
        print(f"✗ DPDK test application error: {e}")
        return False
    finally:
        # Clean up
        for f in ['/tmp/dpdk_test.c', '/tmp/dpdk_test']:
            try:
                os.unlink(f)
            except:
                pass


def test_pktgen_basic():
    """Test basic pktgen functionality"""
    print("\n=== Testing Pktgen Functionality ===")
    
    try:
        # Test pktgen help
        result = subprocess.run(['pktgen', '--help'], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("✓ Pktgen help command works")
            
            # Check for key indicators in output
            if "Usage:" in result.stdout or "Pktgen" in result.stdout:
                print("✓ Pktgen output format correct")
                return True
            else:
                print("⚠ Pktgen output format unexpected")
                return False
        else:
            print("✗ Pktgen help command failed")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ Pktgen command timed out")
        return False
    except Exception as e:
        print(f"✗ Pktgen test error: {e}")
        return False


def generate_traffic_test():
    """Generate some basic network traffic for testing"""
    print("\n=== Generating Test Traffic ===")
    
    try:
        # Generate some loopback traffic using ping
        print("Generating loopback traffic...")
        result = subprocess.run(['ping', '-c', '5', '127.0.0.1'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✓ Loopback traffic generated successfully")
            
            # Parse ping statistics
            lines = result.stdout.split('\n')
            for line in lines:
                if 'packets transmitted' in line:
                    print(f"  {line.strip()}")
            
            return True
        else:
            print("✗ Failed to generate loopback traffic")
            return False
            
    except Exception as e:
        print(f"✗ Traffic generation error: {e}")
        return False


def monitor_interface_stats():
    """Monitor interface statistics"""
    print("\n=== Interface Statistics ===")
    
    try:
        # Read /proc/net/dev for interface statistics
        with open('/proc/net/dev', 'r') as f:
            content = f.read()
        
        print("Interface statistics:")
        lines = content.split('\n')
        
        # Print header
        for line in lines:
            if 'Inter-|   Receive' in line or 'face |bytes' in line:
                print(f"  {line}")
        
        # Print interface data
        for line in lines:
            if ':' in line and ('lo' in line or 'enp' in line or 'eth' in line):
                parts = line.split()
                if len(parts) >= 10:
                    iface = parts[0].rstrip(':')
                    rx_bytes = int(parts[1])
                    rx_packets = int(parts[2])
                    tx_bytes = int(parts[9])
                    tx_packets = int(parts[10])
                    
                    print(f"  {iface:8} RX: {rx_packets:8} packets, {rx_bytes:12} bytes")
                    print(f"  {iface:8} TX: {tx_packets:8} packets, {tx_bytes:12} bytes")
        
        return True
        
    except Exception as e:
        print(f"✗ Interface monitoring error: {e}")
        return False


def main():
    """Main test function"""
    print("DPDK Basic Functionality Test")
    print("=" * 40)
    
    tests = [
        ("Environment Check", test_dpdk_environment),
        ("DPDK Tools", test_dpdk_tools), 
        ("DPDK Libraries", test_dpdk_libs),
        ("Simple DPDK App", test_simple_dpdk_app),
        ("Pktgen Basic", test_pktgen_basic),
        ("Traffic Generation", generate_traffic_test),
        ("Interface Monitoring", monitor_interface_stats),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*50}")
            success = test_func()
            results.append((test_name, success))
            
            if success:
                print(f"✓ {test_name}: PASSED")
            else:
                print(f"✗ {test_name}: FAILED")
                
        except KeyboardInterrupt:
            print(f"\n⚠ Test interrupted by user")
            break
        except Exception as e:
            print(f"✗ {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"Tests run: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    print("\nDetailed Results:")
    for test_name, success in results:
        status = "PASSED" if success else "FAILED"
        symbol = "✓" if success else "✗"
        print(f"  {symbol} {test_name}: {status}")
    
    if passed == total:
        print("\n🎉 All tests passed! DPDK environment is working correctly.")
        return 0
    else:
        print(f"\n⚠ {total-passed} test(s) failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
