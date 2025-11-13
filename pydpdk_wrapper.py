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
    
    def get_port_count(self):
        """Get number of available DPDK ports"""
        return self.dpdk_lib.rte_eth_dev_count_avail()


# Test if it works
if __name__ == "__main__":
    try:
        dpdk = PyDPDK()
        print(f"DPDK wrapper loaded successfully")
        print(f"Run with EAL args to initialize: dpdk.init(['python', '-l', '0-1'])")
    except Exception as e:
        print(f"Failed to load DPDK wrapper: {e}")
        sys.exit(1)
