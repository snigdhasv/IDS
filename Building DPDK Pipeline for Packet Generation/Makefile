APP = dpdk_capture
SRCS = main.c

DPDK_DIR = /home/ubuntu/dpdk-22.11
DPDK_BUILD_DIR = $(DPDK_DIR)/build

# DPDK EAL and Libraries
CFLAGS += -O3 -I$(DPDK_BUILD_DIR)/include
LDFLAGS += -L$(DPDK_BUILD_DIR)/lib
LDLIBS += -lrte_eal -lrte_ethdev -lrte_mbuf -lrte_mempool -lrte_ring -lrte_cmdline -lrte_hash -lrte_lpm -lrte_power -lrte_meter -lrte_sched -lrte_port -lrte_table -lrte_pipeline -lrte_flow_classify -lrte_kni -lrte_acl -lrte_metrics -lrte_timer -lrte_cfgfile -lrte_cryptodev -lrte_compressdev -lrte_eventdev -lrte_rawdev -lrte_regexdev -lrte_security -lrte_bbdev -lrte_ip_frag -lrte_member -lrte_rib -lrte_stack -lrte_vhost -lrte_ipsec -lrte_efd -lrte_graph -lrte_node -lrte_rcu -lrte_kvargs -lrte_telemetry -lrte_bpf -lrte_bitratestats -lrte_jobstats -lrte_latencystats -lrte_gro -lrte_gso -lrte_distributor -lrte_pmd_af_packet -lrte_pmd_bond -lrte_pmd_e1000 -lrte_pmd_i40e -lrte_pmd_ixgbe -lrte_pmd_null -lrte_pmd_pcap -lrte_pmd_ring -lrte_pmd_softnic -lrte_pmd_tap -lrte_pmd_vhost -lrte_pmd_virtio -lrte_pmd_vmxnet3 -pthread -lm -ldl

all: $(APP)

$(APP): $(SRCS)
	$(CC) $(CFLAGS) $(SRCS) -o $@ $(LDFLAGS) $(LDLIBS)

clean:
	rm -f $(APP)


