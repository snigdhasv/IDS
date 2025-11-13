# IDS: DPDK + Suricata + ML (Real‑Time)

A consolidated, high‑performance IDS pipeline using DPDK for packet capture, Suricata for signature alerts, and ML inference for behavior‑based detection. Orchestrated by a single runner.

## Features
- DPDK packet capture (kernel bypass, low latency)
- Suricata (DPDK) signature detection → Kafka `suricata-alerts`
- Real‑time CICIDS features → Kafka `ml-features`
- ML inference (ensemble/single) → Kafka `ml-predictions`
- Optional metrics dashboard (`http://localhost:5000`)

## Repository Structure
- `run_realtime_engine_dpdk.sh` — single entrypoint for the full pipeline
- `dpdk_suricata_ml_pipeline/config/` — `pipeline.conf`, `feature_engine.conf`
- `dpdk_suricata_ml_pipeline/src/` — feature engine and ML consumers
- `dpdk_suricata_ml_pipeline/scripts/` — DPDK binding, Kafka setup, Suricata start
- `config/ids_config.yaml` — features/schema for ML
- `ML Models/` — joblib models and scaler
- `logs/` — runtime logs (created on first run)

## Prerequisites
- Suricata compiled with DPDK support (`suricata --build-info | grep DPDK` → `yes`)
- NIC bound to DPDK (e.g., Intel X520)
- Kafka accessible at `localhost:9092` (runner can start it)
- Python 3 venv with required packages (`kafka-python`, `scapy`, `joblib`, etc.)

## Quick Start
```
# Bind NIC and configure DPDK input
bash dpdk_suricata_ml_pipeline/scripts/01_bind_interface.sh
bash dpdk_suricata_ml_pipeline/scripts/04_configure_dpdk_input.sh

# Start full pipeline (requires sudo)
sudo bash run_realtime_engine_dpdk.sh start

# Check status
sudo bash run_realtime_engine_dpdk.sh status

# Stop all
sudo bash run_realtime_engine_dpdk.sh stop
```

## Configuration
Edit `dpdk_suricata_ml_pipeline/config/pipeline.conf`:
- `NETWORK_INTERFACE`, `INTERFACE_PCI_ADDRESS`, `DPDK_DRIVER`
- `KAFKA_BOOTSTRAP_SERVERS`, topic names
- `ML_MODEL_PATH`, `ML_FEATURES_CONFIG`

Example macOS paths:
```
ML_MODEL_PATH="/Users/sujayschakravarthy/Programming/IDS/ML Models/decision_tree_model_2017.joblib"
ML_FEATURES_CONFIG="/Users/sujayschakravarthy/Programming/IDS/config/ids_config.yaml"
```

## Topics
- `suricata-alerts` — Suricata EVE alerts/signatures
- `ml-features` — CICIDS feature vectors
- `ml-predictions` — ML predictions with confidence

## Monitoring
- Feature Engine: `tail -f logs/feature_engine.log`
- ML Consumer: `tail -f logs/ml_consumer.log`
- Suricata: `tail -f /var/log/suricata/suricata.log`
- Dashboard: `http://localhost:5000`

## Optional: PCAP Testing & Accuracy
Replay labeled PCAPs and compute accuracy metrics.
```
python3 dpdk_suricata_ml_pipeline/src/replay_pcap_for_testing.py \
  --pcap-file path/to/dataset.pcap \
  --ground-truth path/to/labels.csv \
  --real-time --speed 1.0

python3 dpdk_suricata_ml_pipeline/src/calculate_accuracy_metrics.py \
  --predictions logs/ml_predictions.csv \
  --output logs/accuracy_report.json \
  --confusion-matrix logs/confusion_matrix.png
```

## Notes
- Always run the runner with `sudo` (raw sockets & DPDK access).
- Ensure `pipeline.conf` points to valid model files in `ML Models/`.
- For AF_PACKET testing (no DPDK), use `src/realtime_feature_engine.py`.
