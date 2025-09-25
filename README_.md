# High level pipeline
pktgen → NIC → DPDK (kernel bypass) → Suricata (DPDK capture + feature extraction) → EVE JSON (or Kafka plugin) → Kafka topics → Stream processor (Flink / Kafka Streams / ksqlDB) → Model inference (Triton / TF-Serving or embedded in stream app) → Decisions → (a) Alerts → SIEM/DB (b) Controls → block/forward via DPDK forwarder or Suricata/NFQ
