"""
Configuration management for IDS system
"""

import os
import yaml
from typing import Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class DPDKConfig:
    """DPDK configuration parameters"""
    rte_sdk: str = "/opt/ids/downloads/dpdk-24.07"
    rte_target: str = "build"
    hugepage_size: int = 2048  # MB
    hugepage_count: int = 1024
    driver: str = "uio_pci_generic"

@dataclass 
class PktgenConfig:
    """Pktgen configuration parameters"""
    cores: str = "0x3"  # CPU cores to use
    memory_channels: int = 4
    ports_mapping: str = '[1:2].0'
    packet_size: int = 64
    packet_rate: int = 10  # Percentage of line rate
    src_mac: str = "00:11:22:33:44:55"
    dst_mac: str = "00:11:22:33:44:66"
    src_ip: str = "192.168.1.1"
    dst_ip: str = "192.168.1.2"
    src_port: int = 1234
    dst_port: int = 5678

@dataclass
class SuricataConfig:
    """Suricata configuration parameters"""
    interface: str = "dpdk0"
    rules_directory: str = "/etc/suricata/rules"
    eve_log_path: str = "/var/log/suricata/eve.json"
    stats_interval: int = 8
    capture_mode: str = "dpdk"

@dataclass
class KafkaConfig:
    """Kafka configuration parameters"""
    bootstrap_servers: str = "localhost:9092"
    topic_prefix: str = "ids"
    batch_size: int = 16384
    linger_ms: int = 5
    compression_type: str = "gzip"

@dataclass
class IDSConfig:
    """Main IDS system configuration"""
    dpdk: DPDKConfig
    pktgen: PktgenConfig
    suricata: SuricataConfig
    kafka: KafkaConfig
    
    # System paths
    install_dir: str = "/opt/ids"
    log_dir: str = "/opt/ids/logs"
    config_dir: str = "/opt/ids/config"
    
    # Performance settings
    worker_threads: int = 4
    buffer_size: int = 65536
    
    @classmethod
    def from_file(cls, config_path: str) -> 'IDSConfig':
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(
            dpdk=DPDKConfig(**data.get('dpdk', {})),
            pktgen=PktgenConfig(**data.get('pktgen', {})),
            suricata=SuricataConfig(**data.get('suricata', {})),
            kafka=KafkaConfig(**data.get('kafka', {})),
            **{k: v for k, v in data.items() 
               if k not in ['dpdk', 'pktgen', 'suricata', 'kafka']}
        )
    
    def to_file(self, config_path: str) -> None:
        """Save configuration to YAML file"""
        data = asdict(self)
        with open(config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
    
    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables for the system"""
        return {
            'RTE_SDK': self.dpdk.rte_sdk,
            'RTE_TARGET': self.dpdk.rte_target,
            'IDS_INSTALL_DIR': self.install_dir,
            'IDS_LOG_DIR': self.log_dir,
            'IDS_CONFIG_DIR': self.config_dir,
            'KAFKA_BOOTSTRAP_SERVERS': self.kafka.bootstrap_servers,
        }


# Default configuration instance
DEFAULT_CONFIG = IDSConfig(
    dpdk=DPDKConfig(),
    pktgen=PktgenConfig(),
    suricata=SuricataConfig(),
    kafka=KafkaConfig()
)
