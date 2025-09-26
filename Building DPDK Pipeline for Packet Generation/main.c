#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#include <stdio.h>

#define RX_RING_SIZE 1024
#define MBUF_POOL_SIZE 8191
#define MBUF_CACHE_SIZE 250
#define BURST_SIZE 32

static const struct rte_eth_conf port_conf_default = {
    .rxmode = {
        .mtu = RTE_ETHER_MTU, // Maximum transmission unit
    },
};

int main(int argc, char *argv[]) {
    int ret;
    uint16_t port_id;
    struct rte_mempool *mbuf_pool;

    // Initialize the Environment Abstraction Layer (EAL)
    ret = rte_eal_init(argc, argv);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Error with EAL initialization\n");
    }

    argc -= ret;
    argv += ret;

    // Check if at least one port is available
    uint16_t nb_ports = rte_eth_dev_count_avail();
    if (nb_ports == 0) {
        rte_exit(EXIT_FAILURE, "No Ethernet ports available\n");
    }

    // Create a mbuf pool
    mbuf_pool = rte_pktmbuf_pool_create("MBUF_POOL", MBUF_POOL_SIZE, MBUF_CACHE_SIZE, 0, RTE_MBUF_DEFAULT_BUF_SIZE, rte_socket_id());
    if (mbuf_pool == NULL) {
        rte_exit(EXIT_FAILURE, "Cannot create mbuf pool\n");
    }

    // For simplicity, we'll use the first available port
    port_id = 0;

    // Configure the Ethernet port
    ret = rte_eth_dev_configure(port_id, 1, 1, &port_conf_default);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Cannot configure device: err=%d, port=%u\n", ret, port_id);
    }

    // Setup RX queue
    ret = rte_eth_rx_queue_setup(port_id, 0, RX_RING_SIZE, rte_eth_dev_socket_id(port_id), NULL, mbuf_pool);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "rte_eth_rx_queue_setup:err=%d, port=%u\n", ret, port_id);
    }

    // Start the Ethernet port
    ret = rte_eth_dev_start(port_id);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "rte_eth_dev_start:err=%d, port=%u\n", ret, port_id);
    }

    // Enable promiscuous mode
    rte_eth_promiscuous_enable(port_id);

    printf("Entering main loop on port %u\n", port_id);

    // Main loop: receive and process packets
    for (;;) {
        struct rte_mbuf *bufs[BURST_SIZE];
        uint16_t nb_rx = rte_eth_rx_burst(port_id, 0, bufs, BURST_SIZE);

        if (nb_rx == 0) {
            continue;
        }

        // Process received packets
        for (uint16_t i = 0; i < nb_rx; i++) {
            // Here you would add your packet processing logic
            // For example, print packet length or parse headers
            printf("Received packet of length %u\n", rte_pktmbuf_pkt_len(bufs[i]));
            rte_pktmbuf_free(bufs[i]); // Free the mbuf after processing
        }
    }

    // Cleanup (unreachable in this infinite loop, but good practice)
    rte_eth_dev_stop(port_id);
    rte_eth_dev_close(port_id);
    rte_eal_cleanup();

    return 0;
}


