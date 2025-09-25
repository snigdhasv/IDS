"""
DPDK and Pktgen Management Module for IDS System
"""

import subprocess
import os
import time
import logging
from typing import Dict, List, Optional
import json
import psutil

class DPDKManager:
    """Manages DPDK configuration and operations"""
    
    def __init__(self, rte_sdk: str = "/opt/ids/downloads/dpdk-24.07", 
                 rte_target: str = "build"):
        self.rte_sdk = rte_sdk
        self.rte_target = rte_target
        self.logger = logging.getLogger(__name__)
        
        # Set environment variables
        os.environ['RTE_SDK'] = rte_sdk
        os.environ['RTE_TARGET'] = rte_target
        
    def check_hugepages(self) -> Dict[str, int]:
        """Check hugepage configuration"""
        try:
            with open('/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages', 'r') as f:
                nr_hugepages = int(f.read().strip())
            
            with open('/sys/kernel/mm/hugepages/hugepages-2048kB/free_hugepages', 'r') as f:
                free_hugepages = int(f.read().strip())
                
            return {
                'total': nr_hugepages,
                'free': free_hugepages,
                'used': nr_hugepages - free_hugepages
            }
        except Exception as e:
            self.logger.error(f"Failed to read hugepages: {e}")
            return {'total': 0, 'free': 0, 'used': 0}
    
    def list_network_devices(self) -> List[Dict]:
        """List available network devices"""
        try:
            result = subprocess.run(['dpdk-devbind.py', '--status'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return self._parse_devbind_output(result.stdout)
            else:
                self.logger.error(f"Failed to list devices: {result.stderr}")
                return []
        except FileNotFoundError:
            self.logger.error("dpdk-devbind.py not found. Ensure DPDK is installed.")
            return []
    
    def _parse_devbind_output(self, output: str) -> List[Dict]:
        """Parse dpdk-devbind.py output"""
        devices = []
        lines = output.split('\n')
        
        for line in lines:
            if 'drv=' in line and 'unused=' in line:
                # Parse device information
                parts = line.split()
                if len(parts) >= 3:
                    device_info = {
                        'pci_id': parts[0],
                        'description': ' '.join(parts[1:-2]),
                        'driver': parts[-2].replace('drv=', ''),
                        'unused': parts[-1].replace('unused=', '')
                    }
                    devices.append(device_info)
        
        return devices
    
    def bind_device_to_dpdk(self, pci_id: str, driver: str = "uio_pci_generic") -> bool:
        """Bind a network device to DPDK"""
        try:
            result = subprocess.run(['dpdk-devbind.py', '--bind', driver, pci_id],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info(f"Successfully bound {pci_id} to {driver}")
                return True
            else:
                self.logger.error(f"Failed to bind {pci_id}: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Error binding device: {e}")
            return False


class PktgenManager:
    """Manages pktgen operations"""
    
    def __init__(self, pktgen_path: str = "/usr/local/bin/pktgen"):
        self.pktgen_path = pktgen_path
        self.logger = logging.getLogger(__name__)
        self.process = None
        
    def start_pktgen(self, config_file: str = "/opt/ids/pktgen_config.lua",
                     cores: str = "0x3", ports: str = '[1:2].0') -> bool:
        """Start pktgen with specified configuration"""
        try:
            cmd = [
                self.pktgen_path,
                '-c', cores,
                '-n', '4',
                '--',
                '-P',
                '-m', ports,
                '-f', config_file
            ]
            
            self.logger.info(f"Starting pktgen: {' '.join(cmd)}")
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE)
            
            # Give it a moment to start
            time.sleep(2)
            
            if self.process.poll() is None:
                self.logger.info("Pktgen started successfully")
                return True
            else:
                stdout, stderr = self.process.communicate()
                self.logger.error(f"Pktgen failed to start: {stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting pktgen: {e}")
            return False
    
    def stop_pktgen(self) -> bool:
        """Stop pktgen process"""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
                self.logger.info("Pktgen stopped successfully")
                return True
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.logger.warning("Pktgen force killed")
                return True
            except Exception as e:
                self.logger.error(f"Error stopping pktgen: {e}")
                return False
        return True
    
    def get_stats(self) -> Dict:
        """Get pktgen statistics (requires pktgen API integration)"""
        # This would require connecting to pktgen's Lua interface
        # For now, return basic process information
        if self.process and self.process.poll() is None:
            try:
                proc = psutil.Process(self.process.pid)
                return {
                    'status': 'running',
                    'pid': self.process.pid,
                    'cpu_percent': proc.cpu_percent(),
                    'memory_mb': proc.memory_info().rss / 1024 / 1024
                }
            except Exception as e:
                self.logger.error(f"Error getting stats: {e}")
                return {'status': 'error', 'error': str(e)}
        else:
            return {'status': 'stopped'}


class IDSNetworkManager:
    """High-level network management for IDS system"""
    
    def __init__(self):
        self.dpdk = DPDKManager()
        self.pktgen = PktgenManager()
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def system_check(self) -> Dict:
        """Perform comprehensive system check"""
        check_results = {
            'hugepages': self.dpdk.check_hugepages(),
            'network_devices': self.dpdk.list_network_devices(),
            'pktgen_status': self.pktgen.get_stats(),
            'timestamp': time.time()
        }
        
        return check_results
    
    def setup_test_environment(self, device_pci_id: Optional[str] = None) -> bool:
        """Setup complete test environment"""
        self.logger.info("Setting up IDS test environment...")
        
        # Check hugepages
        hugepages = self.dpdk.check_hugepages()
        if hugepages['total'] < 512:  # Minimum 1GB
            self.logger.warning("Insufficient hugepages configured")
            return False
        
        # If device specified, bind it to DPDK
        if device_pci_id:
            if not self.dpdk.bind_device_to_dpdk(device_pci_id):
                self.logger.error("Failed to bind network device")
                return False
        
        self.logger.info("Test environment setup complete")
        return True
    
    def generate_traffic(self, duration: int = 60) -> bool:
        """Generate test traffic for specified duration"""
        self.logger.info(f"Starting traffic generation for {duration} seconds...")
        
        if not self.pktgen.start_pktgen():
            return False
        
        try:
            time.sleep(duration)
            return True
        finally:
            self.pktgen.stop_pktgen()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='IDS Network Manager')
    parser.add_argument('--check', action='store_true', help='Perform system check')
    parser.add_argument('--setup', action='store_true', help='Setup test environment')
    parser.add_argument('--bind-device', type=str, help='Bind device to DPDK (PCI ID)')
    parser.add_argument('--generate-traffic', type=int, metavar='SECONDS', 
                        help='Generate traffic for specified duration')
    
    args = parser.parse_args()
    
    manager = IDSNetworkManager()
    
    if args.check:
        results = manager.system_check()
        print(json.dumps(results, indent=2))
    
    if args.setup:
        success = manager.setup_test_environment(args.bind_device)
        print(f"Setup {'successful' if success else 'failed'}")
    
    if args.generate_traffic:
        success = manager.generate_traffic(args.generate_traffic)
        print(f"Traffic generation {'completed' if success else 'failed'}")
