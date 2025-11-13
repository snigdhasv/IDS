# DPDK IDS Testing Workflow (New Pipeline)

## Workflow Diagram

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         DPDK IDS WORKFLOW - NEW PIPELINE                      ║
╚═══════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Configuration & Verification                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ✓ NIC bound to DPDK (X520)                                                 │
│  ✓ Suricata compiled with DPDK support                                      │
│  ✓ Kafka running on port 9092                                               │
│                                                                             │
│  Command: bash dpdk_suricata_ml_pipeline/scripts/04_configure_dpdk_input.sh │
└─────────────────────────────────────────────────────────────────────────────┘
                                        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Start IDS Pipeline                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Services Started:                                                          │
│  ├─ Kafka (port 9092)                               [Ready]                 │
│  ├─ Suricata DPDK (Signature detection)             [Ready]                 │
│  ├─ Feature Engine (CICIDS65 features)              [Ready]                 │
│  ├─ ML Consumer (Ensemble/Single model)             [Ready]                 │
│  └─ Metrics Dashboard (optional, port 5000)         [Optional]              │
│                                                                             │
│  Command: sudo bash run_realtime_engine_dpdk.sh start                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Feed Traffic                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Live Traffic via DPDK-bound NIC                                            │
│      ↓                                                                      │
│  Optional PCAP Replay for testing                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ replay_pcap_for_testing.py → Kafka (pcap-data)                        │   │
│  │ Example:                                                             │   │
│  │ python3 dpdk_suricata_ml_pipeline/src/replay_pcap_for_testing.py     │   │
│  │   --pcap-file dataset.pcap --ground-truth labels.csv --real-time     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: IDS Processing (Automatic)                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DPDK NIC RX → Suricata (DPDK) → Kafka                                      │
│                             ┌──────────────────┐                            │
│                             │   Suricata       │                            │
│                             │   ─────────────  │                            │
│                             │ • Sig detection  │                            │
│                             │ • Rule matching  │                            │
│                             │ • Alert gen      │                            │
│                             └──────────────────┘                            │
│                                     ↓                                        │
│                               Kafka Topic: suricata-alerts                   │
│                                                                             │
│  DPDK NIC RX → Feature Engine → Kafka → ML Consumer → Kafka                 │
│                   ┌──────────────────┐       ┌──────────────────────┐        │
│                   │ Feature Engine   │       │  ML Consumer         │        │
│                   │ ──────────────── │       │  ──────────────────  │        │
│                   │ • CICIDS65 feats │       │ • Ensemble voting    │        │
│                   │ • Flow analysis  │       │ • Confidence scoring │        │
│                   └──────────────────┘       └──────────────────────┘        │
│                           ↓                          ↓                       │
│                  Kafka Topic: ml-features      Kafka Topic: ml-predictions   │
└─────────────────────────────────────────────────────────────────────────────┘
                                        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 5: Accuracy Calculation (Optional)                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Ground Truth (from PCAP)            Predictions (from ML Consumer)         │
│  ─────────────────────────────        ──────────────────────────────         │
│  labels.csv / packet metadata         logs/ml_predictions.csv                │
│           │                                    │                            │
│           └────────────┬───────────────────────┘                            │
│                        ↓                                                     │
│          ┌──────────────────────────────────────────────────────────────┐    │
│          │ calculate_accuracy_metrics.py                                │    │
│          │ • Accuracy, Precision, Recall, F1                             │    │
│          │ • Confusion matrix, confidence analysis                        │    │
│          └──────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 1. Configuration & Verification

- Ensure DPDK prerequisites and Suricata with DPDK support are installed.
- Bind the target NIC to DPDK and configure input.
- Update the central pipeline configuration.

Commands:

```
# Bind and configure NIC for DPDK input
bash dpdk_suricata_ml_pipeline/scripts/01_bind_interface.sh
bash dpdk_suricata_ml_pipeline/scripts/04_configure_dpdk_input.sh

# Edit pipeline settings (interfaces, Kafka, model paths)
vim dpdk_suricata_ml_pipeline/config/pipeline.conf
```

Key settings to review in `dpdk_suricata_ml_pipeline/config/pipeline.conf`:

- `NETWORK_INTERFACE` and `INTERFACE_PCI_ADDRESS`
- `KAFKA_BOOTSTRAP_SERVERS` and topic names
- `ML_MODEL_PATH` and `ML_FEATURES_CONFIG`

Example model path on macOS:

```
ML_MODEL_PATH="/Users/sujayschakravarthy/Programming/IDS/ML Models/decision_tree_model_2017.joblib"
ML_FEATURES_CONFIG="/Users/sujayschakravarthy/Programming/IDS/config/ids_config.yaml"
```

## 2. Start IDS Pipeline

- Start everything from the single runner.
- The runner orchestrates Kafka, Suricata (DPDK), Feature Engine, ML consumers, and optional dashboard.

Commands:

```
# Start full pipeline (requires sudo)
sudo bash run_realtime_engine_dpdk.sh start

# Check status
sudo bash run_realtime_engine_dpdk.sh status

# Stop all
sudo bash run_realtime_engine_dpdk.sh stop
```

Services started:

- Kafka (`localhost:9092`)
- Suricata in DPDK mode (signature alerts → `suricata-alerts`)
- Feature Engine (CICIDS features → `ml-features`)
- ML Consumer (predictions → `ml-predictions`)
- Suricata Alerts ML Consumer (optional → `ml-predictions`)
- Metrics Dashboard (optional → `http://localhost:5000`)

Code references:

- Runner start sequence: `run_realtime_engine_dpdk.sh:631-636`
- Feature Engine start: `run_realtime_engine_dpdk.sh:173-251`
- Ensemble ML consumer: `run_realtime_engine_dpdk.sh:253-342`
- Suricata alerts ML consumer: `run_realtime_engine_dpdk.sh:344-405`
- Dashboard start: `run_realtime_engine_dpdk.sh:407-438`

## 3. Feed Traffic

- Live capture: Send real traffic through the DPDK-bound NIC.
- Optional PCAP-based testing: Replay labeled PCAPs into Kafka for analysis.

PCAP replay (optional):

```
python3 dpdk_suricata_ml_pipeline/src/replay_pcap_for_testing.py \
  --pcap-file path/to/dataset.pcap \
  --ground-truth path/to/labels.csv \
  --real-time --speed 1.0
```

This publishes packet metadata to Kafka topic `pcap-data` for analysis and ground-truth correlation.

## 4. IDS Processing (Automatic)

- DPDK NIC → Suricata (DPDK) → Kafka `suricata-alerts`
- DPDK NIC → Feature Engine → Kafka `ml-features` → ML Consumer → Kafka `ml-predictions`

Relevant components:

- DPDK feature engine to `ml-features`: `dpdk_suricata_ml_pipeline/src/dpdk_feature_engine.py`
- Ensemble/single model consumers: `dpdk_suricata_ml_pipeline/src/realtime_ensemble_consumer_with_csv.py`, `realtime_ml_consumer.py`
- Suricata alerts ML consumer: `dpdk_suricata_ml_pipeline/src/ml_kafka_consumer.py`

## 5. Accuracy Calculation (Optional)

- Use the CSV produced by the ensemble consumer for metrics.
- Produces JSON reports and optional confusion matrix PNG.

Commands:

```
python3 dpdk_suricata_ml_pipeline/src/calculate_accuracy_metrics.py \
  --predictions logs/ml_predictions.csv \
  --output logs/accuracy_report.json \
  --confusion-matrix logs/confusion_matrix.png
```

## Quick Command Reference

- Configure NIC: `bash dpdk_suricata_ml_pipeline/scripts/04_configure_dpdk_input.sh`
- Start pipeline: `sudo bash run_realtime_engine_dpdk.sh start`
- Status: `sudo bash run_realtime_engine_dpdk.sh status`
- Stop: `sudo bash run_realtime_engine_dpdk.sh stop`
- Check Kafka topics: `kafka-topics.sh --list --bootstrap-server localhost:9092`
- View predictions: `kafka-console-consumer.sh --topic ml-predictions --bootstrap-server localhost:9092`

## Monitoring

- Feature Engine log: `tail -f logs/feature_engine.log`
- ML Consumer log: `tail -f logs/ml_consumer.log`
- Suricata log: `tail -f /var/log/suricata/suricata.log`
- Dashboard: `http://localhost:5000`

## Notes

- Always run the runner with `sudo` to access raw sockets and DPDK.
- Ensure `pipeline.conf` points to valid model files in `ML Models/` and the correct Kafka broker.
- For AF_PACKET testing instead of DPDK, use `dpdk_suricata_ml_pipeline/src/realtime_feature_engine.py` with `sudo`.
