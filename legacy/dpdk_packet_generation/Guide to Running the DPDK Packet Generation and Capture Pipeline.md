# Guide to Running the DPDK Packet Generation and Capture Pipeline

This guide provides detailed instructions on how to set up and run the `pktgen → NIC → DPDK` segment of your line speed intrusion detection model. It includes steps for configuring DPDK, generating packets using a Python Scapy script, and capturing them with a DPDK application. Please note that some steps involving direct hardware interaction and root privileges cannot be fully demonstrated or executed within a sandboxed environment.

## 1. System Requirements and Setup (Outside Sandbox)

To run this pipeline effectively, you will need a Linux system with specific hardware and software configurations:

*   **Operating System:** Ubuntu 20.04 LTS or newer (or a similar Linux distribution).
*   **CPU:** Modern multi-core processor (Intel or AMD) with virtualization extensions (VT-x/AMD-V) enabled in BIOS.
*   **RAM:** At least 8GB RAM, with a significant portion allocated for huge pages (e.g., 2GB or more).
*   **Network Interface Card (NIC):** An Intel or Mellanox NIC officially supported by DPDK. Ensure your NIC has multiple ports if you plan to use one for generation and another for capture.
*   **Root Privileges:** Many DPDK operations require `sudo` or root access.

### 1.1. Install Dependencies

Install essential build tools, libraries, and Python packages:

```bash
sudo apt update
sudo apt install -y build-essential libnuma-dev libpcap-dev meson ninja-build python3 python3-pip
pip3 install scapy pyelftools
```

### 1.2. Configure Huge Pages

DPDK relies on huge pages for efficient memory management. You need to allocate these pages before running DPDK applications. These settings are typically temporary and reset on reboot. For persistent configuration, you would modify `/etc/sysctl.conf` and `/etc/fstab`.

```bash
# Create a mount point for hugepages
sudo mkdir -p /mnt/huge

# Mount hugetlbfs
sudo mount -t hugetlbfs nodev /mnt/huge

# Allocate 1024 hugepages of 2MB each (total 2GB). Adjust as needed.
echo 1024 | sudo tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages

# Verify hugepage allocation
cat /proc/meminfo | grep HugePages
```

## 2. DPDK Installation and Compilation

This section details how to download, compile, and install DPDK.

### 2.1. Download DPDK

```bash
cd /home/ubuntu # Or your preferred working directory
wget https://fast.dpdk.org/rel/dpdk-22.11.tar.xz
tar xf dpdk-22.11.tar.xz
cd dpdk-22.11
```

### 2.2. Compile DPDK

DPDK uses Meson and Ninja for its build system.

```bash
meson build
cd build
ninja
```

This process can take a significant amount of time depending on your system's resources. Once complete, you will have the DPDK libraries and tools compiled.

## 3. NIC Binding to DPDK Drivers (Crucial Step - Outside Sandbox)

For DPDK applications to access your NICs directly, the NICs must be unbound from their kernel drivers and bound to DPDK-compatible user-space drivers. This is a critical step and requires careful execution on your physical machine.

### 3.1. Load DPDK Kernel Modules

```bash
sudo modprobe uio
sudo insmod /home/ubuntu/dpdk-22.11/build/kmod/igb_uio.ko # Path might vary based on DPDK version and build
# Alternatively, for vfio-pci (recommended for better isolation and security):
# sudo modprobe vfio-pci
```

### 3.2. Identify NIC PCI Address

Find the PCI bus address of the NICs you intend to use with DPDK. You'll typically need two: one for packet generation (Pktgen-DPDK) and one for packet capture (your DPDK application).

```bash
lspci -nn | grep -i ethernet
```

Example output:
`0000:01:00.0 Ethernet controller [0200]: Intel Corporation 82599ES 10-Gigabit SFI/SFP+ Network Connection [8086:10fb] (rev 01)`
`0000:01:00.1 Ethernet controller [0200]: Intel Corporation 82599ES 10-Gigabit SFI/SFP+ Network Connection [8086:10fb] (rev 01)`

Note down the PCI addresses (e.g., `0000:01:00.0` and `0000:01:00.1`).

### 3.3. Unbind and Bind NICs

Use the `dpdk-devbind.py` script to unbind the NICs from their kernel drivers and bind them to `igb_uio` (or `vfio-pci`).

```bash
# Assuming 0000:01:00.0 and 0000:01:00.1 are your NICs
sudo /home/ubuntu/dpdk-22.11/usertools/dpdk-devbind.py --bind=igb_uio 0000:01:00.0
sudo /home/ubuntu/dpdk-22.11/usertools/dpdk-devbind.py --bind=igb_uio 0000:01:00.1

# Verify the binding status
sudo /home/ubuntu/dpdk-22.11/usertools/dpdk-devbind.py --status
```

Ensure that the NICs you intend to use are listed under `Network devices using DPDK-compatible driver`.

## 4. Packet Generation with Python (Scapy)

This step uses the `packet_generator.py` script to create benign and malicious packets. These packets can be sent directly (if uncommented and run with root) or saved to PCAP files for Pktgen-DPDK to replay.

### 4.1. The `packet_generator.py` Script

**Location:** `/home/ubuntu/python_pktgen/packet_generator.py`

This script defines functions to generate various packet types:

*   `generate_benign_http_packet`
*   `generate_benign_dns_packet` (requires `from scapy.layers.dns import DNS, DNSQR`)
*   `generate_malicious_syn_flood_packet`
*   `generate_malicious_udp_flood_packet`
*   `generate_malicious_port_scan_packet`

It also includes a `send_packets` function that uses `sendp` from Scapy to transmit packets.

### 4.2. Running the Python Script

```bash
cd /home/ubuntu/python_pktgen
python3 packet_generator.py
```

**To actually send packets:**

1.  **Edit `packet_generator.py`:**
    *   Uncomment the `send_packets` calls at the end of the script.
    *   Set the `interface` variable to the name of one of your DPDK-bound NICs (e.g., `interface = 


"eth0"` or `interface = "enp0s3"`). Note that the interface name here refers to the *kernel* name of the interface, even though it's bound to DPDK, Scapy still needs a kernel-level interface to send packets.
2.  **Run with `sudo`:**
    ```bash
    sudo python3 packet_generator.py
    ```
    This will send the generated packets out of the specified network interface.

## 5. Packet Generation with Pktgen-DPDK (Optional, for higher performance)

For line-rate packet generation, especially when testing high-speed NICs, Pktgen-DPDK is the preferred tool. The `pktgen_script.sh` provides conceptual commands for this.

### 5.1. The `pktgen_script.sh` Script

**Location:** `/home/ubuntu/pktgen_script.sh`

This script contains commented-out examples of how to launch Pktgen-DPDK to generate benign and malicious traffic, either through direct command-line configuration or by replaying PCAP files.

### 5.2. Running the Pktgen-DPDK Script

1.  **Edit `pktgen_script.sh`:**
    *   Replace `/path/to/pktgen-dpdk/app/app/pktgen` with the actual path to your compiled Pktgen-DPDK executable (e.g., `/home/ubuntu/dpdk-22.11/build/app/pktgen`).
    *   Adjust `EAL_ARGS` as necessary for your system (e.g., core mask, number of memory channels, hugepage memory).
    *   If using PCAP replay, ensure the PCAP files (`benign_traffic.pcap`, `malicious_traffic.pcap`) exist and their paths are correct.
    *   Uncomment the specific traffic generation commands you wish to use.
2.  **Make the script executable:**
    ```bash
    chmod +x /home/ubuntu/pktgen_script.sh
    ```
3.  **Run with `sudo`:**
    ```bash
    sudo /home/ubuntu/pktgen_script.sh
    ```
    Pktgen-DPDK will start generating packets on the specified DPDK-bound port.

## 6. Packet Capture and Printing with DPDK Application

This step involves compiling and running the provided DPDK application (`dpdk_capture_app/main.c`) to capture packets from a DPDK-bound NIC and print their Ethernet, IP, TCP, and UDP header details to the console.

### 6.1. The `dpdk_capture_app/main.c` Application

**Location:** `/home/ubuntu/dpdk_capture_app/main.c`

This C application initializes DPDK, configures a specified port (defaulting to port 0), enables promiscuous mode, and then enters a polling loop to receive packets. For each received packet, it parses and prints key header information.

### 6.2. Compiling the DPDK Capture Application

1.  **Navigate to the application directory:**
    ```bash
    cd /home/ubuntu/dpdk_capture_app
    ```
2.  **Edit `Makefile`:** Ensure `DPDK_DIR` and `DPDK_BUILD_DIR` variables correctly point to your DPDK installation. For example:
    ```makefile
    DPDK_DIR = /home/ubuntu/dpdk-22.11
    DPDK_BUILD_DIR = $(DPDK_DIR)/build
    ```
3.  **Compile:**
    ```bash
    make
    ```
    This will create an executable named `dpdk_capture` in the current directory.

### 6.3. Running the DPDK Capture Application

1.  **Run with `sudo` and DPDK EAL arguments:**
    ```bash
    sudo ./dpdk_capture -l 0-1 -n 4 --proc-type auto --socket-mem 512,512 --file-prefix myapp -- -p 0
    ```
    *   **Important:** The `-p 0` argument tells the application to use DPDK port 0. Ensure this corresponds to a DPDK-bound NIC that is *receiving* traffic from your packet generator. If your generator is sending on port 0, your capture app should listen on a different port (e.g., port 1) or a loopback setup.
    *   Adjust EAL arguments (`-l`, `-n`, `--socket-mem`, `--file-prefix`) as per your system configuration and DPDK requirements.

    Once running, this application will continuously print details of the packets it receives to the console.

## 7. Putting It All Together: The Pipeline Flow

To see the `pktgen → NIC → DPDK` pipeline in action, you would typically follow these steps on a physical Linux machine:

1.  **Prepare System:** Install dependencies, configure huge pages, and install/compile DPDK.
2.  **Bind NICs:** Bind at least two NIC ports to DPDK drivers (e.g., `igb_uio`). Let's say `port 0` for sending and `port 1` for receiving.
3.  **Compile DPDK Capture App:** Compile the `dpdk_capture` application.
4.  **Start Capture Application:** In one terminal, run the `dpdk_capture` application, configured to listen on `port 1`:
    ```bash
    sudo /home/ubuntu/dpdk_capture_app/dpdk_capture -l 0-1 -n 4 --proc-type auto --socket-mem 512,512 --file-prefix capture_app -- -p 1
    ```
5.  **Generate Traffic:** In a separate terminal, run either the Python Scapy script (with `sudo` and `iface` set to the kernel name of `port 0`) or the Pktgen-DPDK script (configured to send on `port 0`):
    *   **Using Python Scapy:**
        ```bash
        cd /home/ubuntu/python_pktgen
        # Edit packet_generator.py to uncomment send_packets and set interface='<your_port0_kernel_name>'
        sudo python3 packet_generator.py
        ```
    *   **Using Pktgen-DPDK:**
        ```bash
        cd /home/ubuntu
        # Edit pktgen_script.sh to uncomment desired traffic and set Pktgen to send on port 0
        sudo ./pktgen_script.sh
        ```

As packets are generated and sent out of `port 0`, they will be received by `port 1` and processed by the `dpdk_capture` application, which will print their details to its console. This confirms the basic functionality of the DPDK kernel bypass for both packet generation and capture.

This setup forms the crucial first step for your line speed intrusion detection model, providing a high-performance mechanism for ingesting network traffic for further analysis by Suricata and other components.

