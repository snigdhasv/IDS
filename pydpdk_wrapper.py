#!/usr/bin/env python3
"""
Simple PyDPDK Wrapper using cffi to call DPDK C libraries directly

This provides basic DPDK functionality for packet capture without
requiring the full PyDPDK package which is not available in PyPI.
"""

import cffi
import os
import sys

ffi = cffi.FFI()

# Define DPDK structures and functions we need
ffi.cdef("""
    // Basic DPDK initialization
    int rte_eal_init(int argc, char **argv);
    unsigned rte_lcore_count(void);
    
    // Memory pool
    struct rte_mempool;
    struct rte_mempool *rte_pktmbuf_pool_create(const char *name,
        unsigned n, unsigned cache_size, uint16_t priv_size,
        uint16_t data_room_size, int socket_id);
    
    // Ethernet device
    struct rte_eth_conf;
    int rte_eth_dev_count_avail(void);
    int rte_eth_dev_configure(uint16_t port_id, uint16_t nb_rx_queue,
        uint16_t nb_tx_queue, const struct rte_eth_conf *eth_conf);
    int rte_eth_dev_start(uint16_t port_id);
    
    // Packet mbuf
    struct rte_mbuf;
    uint16_t rte_eth_rx_burst(uint16_t port_id, uint16_t queue_id,
        struct rte_mbuf **rx_pkts, const uint16_t nb_pkts);
    
    // Get packet data
    void *rte_pktmbuf_mtod(struct rte_mbuf *m, void *);
    uint16_t rte_pktmbuf_data_len(struct rte_mbuf *m);
    
    // Queue setup
    struct rte_eth_rxconf;
    struct rte_eth_txconf;
    int rte_eth_rx_queue_setup(uint16_t port_id, uint16_t rx_queue_id,
        uint16_t nb_rx_desc, unsigned int socket_id,
        const struct rte_eth_rxconf *rx_conf, struct rte_mempool *mb_pool);
    int rte_eth_tx_queue_setup(uint16_t port_id, uint16_t tx_queue_id,
        uint16_t nb_tx_desc, unsigned int socket_id,
        const struct rte_eth_txconf *tx_conf);
""")

class PyDPDK:
    """Simple DPDK wrapper for packet capture"""
    
    def __init__(self):
        self.dpdk_lib = None
        self._load_dpdk_library()
    
    def _load_dpdk_library(self):
        """Load DPDK shared library"""
        try:
            # Try to load the main DPDK library
            self.dpdk_lib = ffi.dlopen("librte_eal.so.24")
            print("✅ Loaded DPDK library: librte_eal.so.24")
        except OSError as e:
            print(f"❌ Failed to load DPDK library: {e}")
            print("Available DPDK libraries:")
            os.system("ls /usr/lib/x86_64-linux-gnu/librte_*.so.* | head -5")
            raise
    
    def init(self, eal_args):
        """Initialize DPDK EAL"""
        argc = len(eal_args)
        argv = [ffi.new("char[]", arg.encode()) for arg in eal_args]
        argv_p = ffi.new("char *[]", argv)
        
        ret = self.dpdk_lib.rte_eal_init(argc, argv_p)
        if ret < 0:
            raise RuntimeError(f"EAL initialization failed: {ret}")
        
        print(f"✅ DPDK EAL initialized with {self.dpdk_lib.rte_lcore_count()} cores")
        return ret
    
    def init_dpdk(self):
        """Initialize DPDK with default args"""
        eal_args = ['--proc-type=primary', '--socket-mem=1024', '--file-prefix=dpdk_feature']
        return self.init(eal_args)
    
    def init_port(self, port_id, nb_rx_desc, nb_tx_desc):
        """Initialize a DPDK port"""
        # Create mempool
        self.mempool = self.dpdk_lib.rte_pktmbuf_pool_create(
            b"mbuf_pool", 8192, 256, 0, 2048, 0
        )
        if self.mempool == ffi.NULL:
            raise RuntimeError("Failed to create mempool")
        
        # Configure port
        eth_conf = ffi.new("struct rte_eth_conf *")
        ret = self.dpdk_lib.rte_eth_dev_configure(port_id, 1, 1, eth_conf)
        if ret != 0:
            raise RuntimeError(f"Port configuration failed: {ret}")
        
        # Setup RX queue
        ret = self.dpdk_lib.rte_eth_rx_queue_setup(port_id, 0, nb_rx_desc, 0, ffi.NULL, self.mempool)
        if ret != 0:
            raise RuntimeError(f"RX queue setup failed: {ret}")
        
        # Setup TX queue
        ret = self.dpdk_lib.rte_eth_tx_queue_setup(port_id, 0, nb_tx_desc, 0, ffi.NULL)
        if ret != 0:
            raise RuntimeError(f"TX queue setup failed: {ret}")
        
        # Start port
        ret = self.dpdk_lib.rte_eth_dev_start(port_id)
        if ret != 0:
            raise RuntimeError(f"Port start failed: {ret}")
        
        print(f"✅ Port {port_id} initialized")
    
    def rx_burst(self, port_id, nb_pkts):
        """Receive a burst of packets"""
        rx_pkts = ffi.new("struct rte_mbuf *[]", nb_pkts)
        nb_rx = self.dpdk_lib.rte_eth_rx_burst(port_id, 0, rx_pkts, nb_pkts)
        
        packets = []
        for i in range(nb_rx):
            mbuf = rx_pkts[i]
            pkt_data = self.dpdk_lib.rte_pktmbuf_mtod(mbuf, ffi.typeof("void *"))
            pkt_len = self.dpdk_lib.rte_pktmbuf_data_len(mbuf)
            # Copy packet data
            pkt_bytes = bytes(ffi.buffer(pkt_data, pkt_len))
            packets.append(pkt_bytes)
        
        return packets


# Test if it works
if __name__ == "__main__":
    try:
        dpdk = PyDPDK()
        print(f"DPDK wrapper loaded successfully")
        print(f"Run with EAL args to initialize: dpdk.init(['python', '-l', '0-1'])")
    except Exception as e:
        print(f"Failed to load DPDK wrapper: {e}")
        sys.exit(1)
