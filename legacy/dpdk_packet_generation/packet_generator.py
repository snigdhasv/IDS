from scapy.all import Ether, IP, TCP, UDP, ICMP, Raw, sendp, RandIP, RandMAC, Packet
from scapy.layers.dns import DNS, DNSQR
import random
import time

def generate_benign_http_packet(src_ip, dst_ip, src_port, dst_port, payload="GET /index.html HTTP/1.1\r\nHost: example.com\r\n\r\n"):
    """Generates a benign HTTP GET request packet."""
    ether_layer = Ether(src=RandMAC(), dst=RandMAC())
    ip_layer = IP(src=src_ip, dst=dst_ip)
    tcp_layer = TCP(sport=src_port, dport=dst_port, flags="S", seq=random.randint(1000, 65000))
    raw_layer = Raw(load=payload)
    return ether_layer / ip_layer / tcp_layer / raw_layer

def generate_benign_dns_packet(src_ip, dst_ip, src_port, dst_port, qname="example.com"):
    """Generates a benign DNS query packet."""
    ether_layer = Ether(src=RandMAC(), dst=RandMAC())
    ip_layer = IP(src=src_ip, dst=dst_ip)
    udp_layer = UDP(sport=src_port, dport=dst_port)
    dns_layer = DNS(rd=1, qd=DNSQR(qname=qname))
    return ether_layer / ip_layer / udp_layer / dns_layer

def generate_malicious_syn_flood_packet(src_ip, dst_ip, dst_port):
    """Generates a malicious SYN flood packet with a spoofed source IP."""
    ether_layer = Ether(src=RandMAC(), dst=RandMAC())
    ip_layer = IP(src=RandIP(), dst=dst_ip) # Spoofed source IP
    tcp_layer = TCP(sport=random.randint(1024, 65535), dport=dst_port, flags="S")
    return ether_layer / ip_layer / tcp_layer

def generate_malicious_udp_flood_packet(src_ip, dst_ip, dst_port, payload_size=1000):
    """Generates a malicious UDP flood packet with a large payload."""
    ether_layer = Ether(src=RandMAC(), dst=RandMAC())
    ip_layer = IP(src=RandIP(), dst=dst_ip) # Spoofed source IP
    udp_layer = UDP(sport=random.randint(1024, 65535), dport=dst_port)
    raw_layer = Raw(load="X" * payload_size) # Large payload
    return ether_layer / ip_layer / udp_layer / raw_layer

def generate_malicious_port_scan_packet(src_ip, dst_ip, dst_port):
    """Generates a malicious TCP SYN packet for a port scan."""
    ether_layer = Ether(src=RandMAC(), dst=RandMAC())
    ip_layer = IP(src=src_ip, dst=dst_ip)
    tcp_layer = TCP(sport=random.randint(1024, 65535), dport=dst_port, flags="S")
    return ether_layer / ip_layer / tcp_layer

def send_packets(packets, count=1, interval=0.1, iface=None):
    """Sends a list of packets."""
    print(f"Sending {len(packets)} packets, {count} times each, with {interval}s interval...")
    for _ in range(count):
        for pkt in packets:
            sendp(pkt, iface=iface, verbose=0)
            time.sleep(interval)
    print("Packet sending complete.")

if __name__ == "__main__":
    # Example Usage:
    # NOTE: To send packets on a real interface, you need to run this script with root privileges
    # and specify the correct interface name (e.g., iface="eth0").
    # In a sandboxed environment, actual packet sending might not be possible.

    target_ip = "192.168.1.100" # Example target IP
    dns_server_ip = "8.8.8.8" # Example DNS server IP
    my_ip = "192.168.1.10" # Example source IP
    interface = None # Set to your network interface, e.g., "eth0" or "enp0s3"

    print("--- Generating Benign Packets ---")
    benign_http_pkt = generate_benign_http_packet(my_ip, target_ip, 12345, 80)
    print(f"Benign HTTP Packet: {benign_http_pkt.summary()}")

    # DNS layer requires DNS import, which is not in the default scapy.all
    # from scapy.layers.dns import DNS, DNSQR
    # benign_dns_pkt = generate_benign_dns_packet(my_ip, dns_server_ip, 54321, 53)
    # print(f"Benign DNS Packet: {benign_dns_pkt.summary()}")

    print("\n--- Generating Malicious Packets ---")
    malicious_syn_pkt = generate_malicious_syn_flood_packet(my_ip, target_ip, 80)
    print(f"Malicious SYN Flood Packet: {malicious_syn_pkt.summary()}")

    malicious_udp_pkt = generate_malicious_udp_flood_packet(my_ip, target_ip, 53, payload_size=1500)
    print(f"Malicious UDP Flood Packet: {malicious_udp_pkt.summary()}")

    malicious_port_scan_pkt = generate_malicious_port_scan_packet(my_ip, target_ip, 22) # Scan port 22
    print(f"Malicious Port Scan Packet (to port 22): {malicious_port_scan_pkt.summary()}")

    # To actually send packets, uncomment the following lines and run with sudo
    # print("\n--- Sending Benign Packets (conceptual) ---")
    # send_packets([benign_http_pkt], count=5, interval=0.5, iface=interface)

    # print("\n--- Sending Malicious Packets (conceptual) ---")
    # send_packets([malicious_syn_pkt], count=10, interval=0.1, iface=interface)

    print("\nPython packet generation script created. Actual sending requires root and a network interface.")


