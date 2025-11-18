does# IDS Pipeline Deep Dive

This document summarizes how the current DPDK + Suricata + ML stack is wired together inside this repository, where packet features are built, and what each major file/script is responsible for.

## 1. End-to-End Architecture

- **NIC / DPDK binding** – `dpdk_suricata_ml_pipeline/scripts/01_bind_interface.sh` binds the Intel NIC (e.g., X520 at `0000:01:00.0`) to `vfio-pci` or another poll-mode driver so user space can own the device.
- **Suricata PMD** – `scripts/03_start_suricata_dpdk.sh` launches Suricata with the DPDK input described in `/etc/suricata/suricata-dpdk-intel.yaml`, pushing alerts into Kafka topic `suricata-alerts`.
- **Feature sidecar** – `src/dpdk_feature_engine.py` (or `src/realtime_feature_engine.py` for AF_PACKET) taps the same traffic, builds CICIDS2017 features, and writes them to Kafka topic `ml-features`.
- **ML Consumers** – `src/ml_kafka_consumer.py`, `realtime_ml_consumer.py`, and the ensemble variants read `ml-features`, map them to the 34-feature model schema, run sklearn/LGBM models from `ML Models/`, and post predictions (and metrics) to Kafka topic `ml-predictions` plus log files.
- **Orchestration** – `run_realtime_engine_dpdk.sh` ties everything together (Kafka, Suricata, feature engine, ML consumer, optional dashboard) with start/stop/status flows and state persisted in `logs/ml_mode_state.json`.

The default configuration for interfaces, Kafka topics, ML assets, and feature counts lives in `dpdk_suricata_ml_pipeline/config/pipeline.conf` and `feature_engine.conf`.

## 2. Data Flow Walkthrough

1. **Interface prep** – `00_setup_external_capture.sh` (optional) wires the mirrored traffic source. `01_bind_interface.sh` unbinds the NIC from the kernel and attaches it to the configured DPDK driver; `04_configure_dpdk_input.sh` updates Suricata’s YAML with PCI and queue information. `run_realtime_engine_dpdk.sh` double-checks this before starting services.
2. **Kafka bring-up** – `scripts/02_setup_kafka.sh` starts/validates the broker and creates topics (`suricata-alerts`, `ml-features`, `ml-predictions`). The runner waits for port `9092` to be reachable.
3. **Suricata** – `03_start_suricata_dpdk.sh` (or `_afpacket.sh` for fallback) launches Suricata; if Suricata is configured to emit EVE to Kafka directly the alerts go straight to the broker. Otherwise `scripts/suricata_kafka_bridge.py` tails `/var/log/suricata/eve.json` and publishes each JSON event to `suricata-alerts`.
4. **Feature generation** – `dpdk_feature_engine.py` attempts to use the local `PyDPDK` binding (`pydpdk_wrapper.py`) to read packets via `rte_eth_rx_burst`. If Suricata already owns the port, it gracefully falls back to tailing `eve.json`, extracts Suricata’s per-flow counters, and creates the 65-feature vector before emitting to Kafka.
5. **ML inference** – `ml_kafka_consumer.py` (single-model mode) or the ensemble consumers:
   - Pull EVE flow events from Kafka, convert to the full 65-feature dict via `feature_extractor.py`.
   - Map down to the 34-feature schema with `feature_mapper.py`/`feature_selector.py`.
   - Load the requested model(s) via `model_loader.py` or `two_model_loader.py`.
   - Run `predict`/`predict_proba`, log latency metrics through `metrics_logger.py`, and write predictions + confidence back to Kafka and `logs/ml_consumer.log`.
6. **Dashboards & testing** – `scripts/start_dashboard.sh` spawns the Flask metrics UI. `send_test_traffic.sh`/`test_packet_capture_simple.sh` replay PCAPs and optionally engage `scripts/simulate_pcap_pipeline_outputs.py` so logs/metrics continue even when the real ML consumer is offline. `tests/monitor_ml_performance.py` is a CLI probe into consumer latency and accuracy.

## 3. DPDK Attachment Details

- **Configuration** – `dpdk_suricata_ml_pipeline/config/pipeline.conf` contains `NETWORK_INTERFACE`, `INTERFACE_PCI_ADDRESS`, `DPDK_DRIVER`, core pinning, hugepages, and Suricata log paths. `feature_engine.conf` hosts DPDK queue counts and Kafka topic names for the feature engine timer loop.
- **Binding workflow** – `01_bind_interface.sh` uses `dpdk-devbind.py` to rebind the NIC, optionally backs up the old `ip addr` state, and honors `DPDK_DRIVER`. The `run_realtime_engine_dpdk.sh` helper repeats the check via `ensure_interface_bound_to_dpdk`.
- **PyDPDK wrapper** – `pydpdk_wrapper.py` wraps `librte_eal.so.24` via CFFI, exposing `rte_eal_init`, queue setup, mempool creation, and `rte_eth_rx_burst`. It is only invoked when `dpdk_feature_engine.py` is run in pure DPDK-capture mode; otherwise the engine operates in Suricata-tail mode.

## 4. Feature Extraction Paths

There are two primary feature engines:

1. **Suricata Flow Tail** (`dpdk_feature_engine.py` fallback):

```62:114:dpdk_suricata_ml_pipeline/src/feature_extractor.py
    def extract_from_flow(self, event: Dict) -> Optional[Dict[str, float]]:
        if event.get('event_type') != 'flow':
            return None
        features = {name: 0.0 for name in self.FEATURE_NAMES}
        flow_data = event.get('flow', {})
        fwd_pkts = flow_data.get('pkts_toserver', 1)
        bwd_pkts = flow_data.get('pkts_toclient', 0)
        duration = self._parse_duration(flow_data.get('age', 0)) or 0.001
        features['Destination Port'] = event.get('dest_port', 0)
        features['Flow Duration'] = int(duration * 1_000_000)
        features['Total Fwd Packets'] = fwd_pkts
        features['Total Backward Packets'] = bwd_pkts
        # ...plus packet-length, rate, IAT, flag, active/idle, and TCP window features ...
```

`feature_extractor.py` is the canonical implementation used by every ML consumer. It loads the full 65-name schema (matching `config/ids_config.yaml`), normalizes durations, and back-fills any missing values so downstream models always receive a complete vector.

2. **AF_PACKET Fanout** (`realtime_feature_engine.py`):
   - Opens a raw socket with `PACKET_FANOUT` (cluster `99`) so both Suricata and the engine see identical traffic, even without DPDK.
   - Maintains rich per-flow state (`FlowStats`) including direction-aware packet lengths, inter-arrival times, TCP flags, idle/active windows, and header lengths, then calls `extract_features()` when a flow terminates or times out.

3. **DPDK Capture Attempt** (`dpdk_feature_engine.py`):
   - Initializes the NIC via `PyDPDK` when available, but presently `_run_dpdk_mode()` just logs that Suricata already owns the port and redirects to `_run_fallback_mode()`. This guarantees feature extraction keeps working even if only Suricata holds the PMD queue.

## 5. ML & Kafka Consumers

```325:358:dpdk_suricata_ml_pipeline/src/ml_kafka_consumer.py
            features = self.feature_extractor.extract_from_flow(flow_event)
            if not features:
                return
            feature_array = self.feature_mapper.map_to_34(features)
            predictions = self.model_loader.predict(feature_array)
            probabilities = self.model_loader.predict_proba(feature_array)
            prediction = predictions[0] if len(predictions) > 0 else 'BENIGN'
            confidence = float(np.max(probabilities[0])) if len(probabilities) > 0 else 0.0
            # class counts, metrics, and Kafka/CSV writes follow ...
```

- **`ml_kafka_consumer.py`** – single-model, latency-tracked inference path. Uses `metrics_logger.py` to emit per-stage timings, `feature_extractor.py` for 65-feature building, and `feature_mapper.py` to align with models trained on 34 features.
- **`two_model_consumer.py` / `two_model_ensemble.py`** – adaptively weight two models (configurable via `ML_TWO_MODEL_DEFAULTS`) using a meta-learner. Includes warm-up data collection, buffer management, and fallbacks if the ensemble is not yet trained.
- **`realtime_ml_consumer.py` & `realtime_ensemble_consumer*.py`** – lower-latency consumers meant for live dashboards; optionally dump CSVs for offline evaluation.
- **`model_loader.py` / `two_model_loader.py`** – locate `joblib` artifacts inside `dpdk_suricata_ml_pipeline/models/ML Models/` (or the top-level `ML Models/` directory) and expose `predict`/`predict_proba`.
- **`metrics_logger.py`** – common utility that timestamps each pipeline stage (Kafka poll, feature extraction, mapping, inference) and persists JSONL metrics under `dpdk_suricata_ml_pipeline/logs/metrics/`.

## 6. File-Level Reference

### Repository Root

| Path | Purpose |
| --- | --- |
| `run_realtime_engine_dpdk.sh` | Main orchestrator for start/stop/status of Kafka, Suricata, feature engine, ML consumer, dashboard, and tcpreplay daemon. Handles CLI flags (`--single`, `--ensemble2`, `--ensemble5`, `--ground-truth`). |
| `send_test_traffic.sh` | High-level traffic replay + ML simulator harness (reads `logs/ml_mode_state.json` to mirror active ML mode). |
| `test_packet_capture_simple.sh` | Smoke-test for capturing packets and verifying Suricata/feature engine health. |
| `setup_realtek_to_intel_ids.sh`, `REALTEK_TO_INTEL_GUIDE.md` | Guides for bridging USB/Realtek adapters to Intel cards. |
| `pydpdk_wrapper.py` | Thin CFFI bridge into DPDK libraries for packet RX and queue management. |
| `requirements.txt` | Python dependencies for the feature engine and ML consumers. |
| `config/ids_config.yaml` | Authoritative schema for 65 CICIDS features and their order. |
| `ML Models/` | Production-ready `.joblib` classifiers and scalers (2017/2018 datasets, RandomForest, LightGBM, etc.). |
| `notebooks/` | Exploratory notebooks for CICIDS feature engineering, model training, and ensemble evaluation. |
| `tests/monitor_ml_performance.py` | Polls ML consumers, aggregating latency and accuracy over time. |

### `dpdk_suricata_ml_pipeline/scripts/`

| Script | Summary |
| --- | --- |
| `00_setup_external_capture.sh` | Optional helper to create a dedicated VLAN/subnet for external traffic generators. |
| `01_bind_interface.sh` / `unbind_interface.sh` | Bind/unbind NICs to DPDK drivers, with safety prompts and config backups. |
| `02_setup_kafka.sh` | Start Kafka/ZooKeeper, create topics, verify reachability. |
| `03_start_suricata_dpdk.sh` / `03_start_suricata_afpacket.sh` | Launch Suricata in either DPDK or AF_PACKET mode with proper YAML. |
| `04_configure_dpdk_input.sh` / `04_start_kafka_bridge.sh` | Patch Suricata configs for DPDK input and start the `suricata_kafka_bridge.py` if Suricata cannot publish directly. |
| `05_start_ml_consumer.sh`, `06_start_two_model_consumer.sh` | Standalone launchers when the full runner isn’t used. |
| `metrics_dashboard.py`, `start_dashboard.sh`, `monitor_traffic.sh`, `status_check.sh`, `stop_all.sh` | Operational tooling for observability and lifecycle management. |
| `SCRIPT_FILES_DETAILS.md/pdf` | Reference documentation for each script (human-friendly). |

### `dpdk_suricata_ml_pipeline/src/`

| File | Responsibility |
| --- | --- |
| `alert_processor.py` | Shared utilities for parsing Suricata alerts and forwarding them to Kafka or other sinks. |
| `calculate_accuracy_metrics.py` | Offline evaluator that compares `logs/ml_predictions.csv` against ground-truth CSVs and produces accuracy/confusion reports. |
| `dpdk_feature_engine.py` | DPDK-capable feature sidecar with a Suricata-flow fallback. |
| `feature_extractor.py` | Converts Suricata flow JSON into the canonical 65-feature dict (used everywhere). |
| `feature_mapper.py` / `feature_selector.py` | Reduce or remap feature sets to the 34-feature model schema. |
| `metrics_logger.py` | Latency/throughput logging helper for consumers and ensembles. |
| `ml_kafka_consumer.py` | Single-model Kafka consumer performing ingestion → features → inference. |
| `model_loader.py` | Loads `.joblib` models, exposes `predict`/`predict_proba`. |
| `realtime_feature_engine.py` | AF_PACKET-based feature sidecar with rich per-flow state. |
| `realtime_ml_consumer.py` | Lightweight consumer for real-time dashboards (CSV outputs, simplified logging). |
| `realtime_ensemble_consumer.py` / `_with_csv.py` | Ensemble versions that fan out predictions and optionally record per-flow CSVs. |
| `replay_pcap_for_testing.py` | Replays labeled PCAPs into Kafka to validate accuracy with the live pipeline. |
| `two_model_consumer.py`, `two_model_ensemble.py`, `two_model_loader.py` | Adaptive two-model ensemble implementation with meta-learner training and runtime selection. |

## 7. Observability, Testing, and Docs

- **Logs** – `run_realtime_engine_dpdk.sh` standardizes log locations under `logs/` and `dpdk_suricata_ml_pipeline/logs/`. Feature engine logs (`feature_engine.log`), ML consumer logs (`ml_consumer.log`), Kafka bridge stats, and metrics JSONL/CSV files allow verifying throughput and latency in real time.
- **Testing workflows** – `TESTING_WORKFLOW.md`, `CICIDS2017_WEEKDAY_TESTING.md`, and `TEST_PLAN_RESULTS.md` document repeatable validation flows and historical accuracy numbers. `TESTING_WORKFLOW.pdf` and `SCRIPT_FILES_DETAILS.pdf` are printable references.
- **Dashboard** – `dashboard-next/` is a Next.js UI that reads the metrics JSON/CSV outputs and renders health/status cards. `scripts/start_dashboard.sh` runs both the Python metrics service and the Next.js frontend.

## 8. Key Takeaways

- DPDK binding happens through the shell scripts and `pydpdk_wrapper.py`, but feature extraction currently relies on Suricata’s flow feed for stability when Suricata already controls the NIC.
- `feature_extractor.py` is the definitive place where Suricata flow JSON turns into the ML-ready 65-feature vector; every consumer imports it before calling any model.
- Kafka topics are the glue between Suricata, the feature engines, and the ML consumers; all relevant config is centralized in `pipeline.conf`.
- The runner script is the safest way to start/stop the stack because it enforces prerequisites, writes state for helper scripts, and keeps logs consistent.

Use this file as a launchpad when diving into any portion of the IDS pipeline—each path above links directly back to the code implementing that stage.

