#!/usr/bin/env python3
"""
DPDK NIC Binding Demonstration Script

This script demonstrates how to bind and unbind NICs to/from DPDK drivers,
showing the complete process for high-performance packet processing.

⚠️  WARNING: This will temporarily disconnect your network interface!
"""

import subprocess
import time
import sys
import os

class DPDKBindingDemo:
    def __init__(self):
        self.pci_id = "0000:02:00.0"  # Your NIC's PCI ID
        self.interface_name = "enp2s0"
        self.original_driver = "r8169"
        self.dpdk_driver = "uio_pci_generic"
        self.dpdk_devbind_script = "/usr/local/bin/dpdk-devbind.py"
    
    def show_header(self, title):
        """Display formatted header"""
        print(f"\n{'='*60}")
        print(f"{title.center(60)}")
        print(f"{'='*60}")
    
    def run_command(self, cmd, description="", check_root=True):
        """Run a command and display results"""
        if check_root and os.geteuid() != 0:
            print(f"❌ Root privileges required for: {description}")
            return False, "", ""
        
        print(f"\n🔧 {description}")
        print(f"   Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"   ✅ Success")
                if result.stdout.strip():
                    print(f"   Output: {result.stdout.strip()}")
                return True, result.stdout, result.stderr
            else:
                print(f"   ❌ Failed (exit code: {result.returncode})")
                if result.stderr.strip():
                    print(f"   Error: {result.stderr.strip()}")
                return False, result.stdout, result.stderr
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ Command timed out")
            return False, "", "Timeout"
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return False, "", str(e)
    
    def check_current_status(self):
        """Check current NIC binding status"""
        self.show_header("CURRENT NIC STATUS")
        
        # Check interface status
        success, stdout, stderr = self.run_command(
            ['ip', 'link', 'show', self.interface_name],
            "Checking interface status",
            check_root=False
        )
        
        # Check PCI device info
        success, stdout, stderr = self.run_command(
            ['lspci', '-v', '-s', self.pci_id],
            "Checking PCI device details",
            check_root=False
        )
        
        # Check DPDK binding status
        success, stdout, stderr = self.run_command(
            ['sudo', self.dpdk_devbind_script, '--status-dev', 'net'],
            "Checking DPDK binding status"
        )
        
        return success
    
    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        self.show_header("PREREQUISITE CHECK")
        
        print("🔍 Checking DPDK prerequisites...")
        
        # Check if DPDK tools exist
        if os.path.exists(self.dpdk_devbind_script):
            print("   ✅ DPDK devbind script found")
        else:
            print(f"   ❌ DPDK devbind script not found at {self.dpdk_devbind_script}")
            return False
        
        # Check if hugepages are configured
        try:
            with open('/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages', 'r') as f:
                hugepages = int(f.read().strip())
                if hugepages > 0:
                    print(f"   ✅ Hugepages configured: {hugepages}")
                else:
                    print("   ⚠️  No hugepages configured")
        except:
            print("   ⚠️  Could not check hugepage status")
        
        # Check if required kernel modules are available
        modules_to_check = ['uio', 'uio_pci_generic']
        for module in modules_to_check:
            success, stdout, stderr = self.run_command(
                ['modprobe', '-n', '-v', module],
                f"Checking if {module} module is available",
                check_root=False
            )
            if success:
                print(f"   ✅ Module {module} is available")
            else:
                print(f"   ❌ Module {module} not available")
        
        return True
    
    def load_kernel_modules(self):
        """Load required kernel modules"""
        self.show_header("LOADING KERNEL MODULES")
        
        modules = ['uio', 'uio_pci_generic']
        for module in modules:
            success, stdout, stderr = self.run_command(
                ['sudo', 'modprobe', module],
                f"Loading {module} module"
            )
            
            if success:
                # Verify module is loaded
                success, stdout, stderr = self.run_command(
                    ['lsmod'],
                    f"Verifying {module} module is loaded",
                    check_root=False
                )
                if module in stdout:
                    print(f"   ✅ {module} successfully loaded")
                else:
                    print(f"   ⚠️  {module} load status unclear")
        
        return True
    
    def bind_to_dpdk(self):
        """Bind NIC to DPDK driver"""
        self.show_header("BINDING NIC TO DPDK")
        
        print(f"⚠️  WARNING: This will disconnect interface {self.interface_name}")
        print(f"   You will lose network connectivity temporarily!")
        print(f"   PCI Device: {self.pci_id}")
        print(f"   Current Driver: {self.original_driver}")
        print(f"   Target DPDK Driver: {self.dpdk_driver}")
        
        response = input(f"\n❓ Proceed with binding? (yes/no): ").lower().strip()
        if response not in ['yes', 'y']:
            print("❌ Binding aborted by user")
            return False
        
        # Bind to DPDK driver
        success, stdout, stderr = self.run_command(
            ['sudo', self.dpdk_devbind_script, '--bind', self.dpdk_driver, self.pci_id],
            f"Binding {self.pci_id} to {self.dpdk_driver}"
        )
        
        if success:
            print(f"   ✅ Successfully bound to DPDK!")
            
            # Verify binding
            time.sleep(2)  # Give system time to update
            success, stdout, stderr = self.run_command(
                ['sudo', self.dpdk_devbind_script, '--status-dev', 'dpdk'],
                "Verifying DPDK binding"
            )
            
            if self.pci_id in stdout:
                print(f"   ✅ Binding verified - NIC is now under DPDK control")
                return True
            else:
                print(f"   ⚠️  Binding verification unclear")
                return False
        else:
            print(f"   ❌ Binding failed")
            return False
    
    def test_dpdk_application(self):
        """Test DPDK application with bound NIC"""
        self.show_header("TESTING DPDK APPLICATION")
        
        print("🚀 Testing DPDK capture application with bound NIC...")
        
        # Test our DPDK capture application
        if os.path.exists('./dpdk_capture'):
            print("   📱 DPDK capture application found")
            
            print("   🔧 Running DPDK capture application...")
            print("      (This should now detect the bound NIC)")
            
            success, stdout, stderr = self.run_command(
                ['sudo', './dpdk_capture', '--log-level=*:info'],
                "Running DPDK capture application",
                check_root=True
            )
            
            if "Ethernet ports available" in stderr or "Available lcores" in stderr:
                print("   ✅ DPDK application can see the bound NIC!")
            else:
                print("   ⚠️  DPDK application output unclear")
                if stdout:
                    print(f"   stdout: {stdout[:200]}...")
                if stderr:
                    print(f"   stderr: {stderr[:200]}...")
        else:
            print("   ❌ DPDK capture application not found")
            print("      You can compile it with: make")
    
    def restore_original_driver(self):
        """Restore NIC to original kernel driver"""
        self.show_header("RESTORING ORIGINAL DRIVER")
        
        print(f"🔄 Restoring {self.interface_name} to kernel driver...")
        print(f"   This will restore your network connectivity")
        
        # Bind back to original driver
        success, stdout, stderr = self.run_command(
            ['sudo', self.dpdk_devbind_script, '--bind', self.original_driver, self.pci_id],
            f"Binding {self.pci_id} back to {self.original_driver}"
        )
        
        if success:
            print(f"   ✅ Successfully restored to kernel driver!")
            
            # Wait for interface to come back up
            time.sleep(3)
            
            # Check if interface is back
            success, stdout, stderr = self.run_command(
                ['ip', 'link', 'show', self.interface_name],
                "Checking if interface is restored",
                check_root=False
            )
            
            if 'UP' in stdout:
                print(f"   ✅ Interface {self.interface_name} is back up!")
                
                # Test connectivity
                success, stdout, stderr = self.run_command(
                    ['ping', '-c', '3', '8.8.8.8'],
                    "Testing network connectivity",
                    check_root=False
                )
                
                if success and '0% packet loss' in stdout:
                    print(f"   ✅ Network connectivity restored!")
                else:
                    print(f"   ⚠️  Network connectivity test unclear")
            else:
                print(f"   ⚠️  Interface status unclear")
        else:
            print(f"   ❌ Failed to restore original driver")
    
    def run_full_demo(self):
        """Run the complete DPDK binding demonstration"""
        print("🔧 DPDK NIC Binding Demonstration")
        print("=" * 60)
        print("This demo will show you how to:")
        print("1. Check current NIC status")
        print("2. Load DPDK kernel modules")
        print("3. Bind NIC to DPDK driver")
        print("4. Test DPDK application")
        print("5. Restore original driver")
        print()
        print("⚠️  WARNING: This will temporarily disconnect your network!")
        
        if os.geteuid() != 0:
            print("\n❌ This demo requires root privileges")
            print("   Please run with: sudo python3 dpdk_binding_demo.py")
            return
        
        response = input("\n❓ Proceed with full demo? (yes/no): ").lower().strip()
        if response not in ['yes', 'y']:
            print("❌ Demo aborted by user")
            return
        
        try:
            # Step 1: Check current status
            self.check_current_status()
            
            # Step 2: Check prerequisites
            if not self.check_prerequisites():
                print("\n❌ Prerequisites not met. Aborting.")
                return
            
            # Step 3: Load kernel modules
            self.load_kernel_modules()
            
            # Step 4: Bind to DPDK
            if self.bind_to_dpdk():
                # Step 5: Test DPDK application
                self.test_dpdk_application()
                
                # Wait a bit to show the effect
                print(f"\n⏳ NIC is now bound to DPDK. Waiting 5 seconds...")
                time.sleep(5)
            
            # Step 6: Always try to restore
            self.restore_original_driver()
            
            print("\n🎉 DPDK binding demonstration complete!")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Demo interrupted by user")
            print("🔄 Attempting to restore original driver...")
            self.restore_original_driver()
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            print("🔄 Attempting to restore original driver...")
            self.restore_original_driver()

def main():
    demo = DPDKBindingDemo()
    demo.run_full_demo()

if __name__ == "__main__":
    main()
