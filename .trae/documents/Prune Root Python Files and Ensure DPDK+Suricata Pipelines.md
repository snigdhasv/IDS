## Goal

* Keep only the Python sources under `dpdk_suricata_ml_pipeline/src` for the IDS runtime.

* Delete all Python files in the project root (not in subfolders).

* Ensure two working streams:

  1. DPDK → Feature Engine → ML Inference → Dashboard/Results
  2. DPDK Suricata → Signature alerts (Kafka) → Dashboard/Results

## What Stays

* `dpdk_suricata_ml_pipeline/` entire (`src/`, `scripts/`, `config/`).

* `ML Models/`, `config/` subfolders.

* Root: `run_realtime_engine_dpdk.sh`, `.gitignore`, `requirements.txt`.

* All other subfolders (`notebooks/`, `tests/`, `backup_.../`) untouched.

## Root Python Files To Delete (only in project root)

* `verify_features.py`, `verify_features_static.py`, `test_ensemble_model.py`, `test_ensemble_complete.py`

* `retrain_models_raw_features.py`, `retrain_models_no_pca.py`, `retrain_model.py`

* `extract_training_features.py`, `create_test_models.py`

* `diagnose_feature_mismatch.py`, `diagnose_model_confidence.py`, `diagnose_69_features.py`

* `dpdk_pcap_replay.py`, `calculate_accuracy_metrics.py`, `analyze_feature_mismatch.py`

## Required Runtime Components (kept in src/scripts)

* DPDK Feature Engine: `src/dpdk_feature_engine.py` publishes to `ml-features`.

* ML Inference (features stream): `src/realtime_ensemble_consumer_with_csv.py` or `src/realtime_ml_consumer.py` consumes `ml-features`.

* Suricata DPDK: started by `scripts/03_start_suricata_dpdk.sh`, outputs alerts to Kafka (`suricata-alerts`).

* Optional Dashboard: `scripts/metrics_dashboard.py` reads metrics JSONL from `logs/metrics` written by components using `src/metrics_logger.py`.

## Consistency Fixes

* Leave Kafka topics as-is: Feature Engine → `ml-features`; Ensemble/Realtime consumers read `ml-features`; Suricata outputs `suricata-alerts`.

## Parallel Suricata Path

* Suricata DPDK already runs and writes alerts to Kafka (`suricata-alerts`).

* If you want ML on Suricata alerts in parallel, we can also start `src/ml``kafkaconsumer.py` _(consumes_ _`suricata-alerts`, publishes to_ _`ml-predictions`). I can add this start step to the runner after cleanup if desired. Sure yes do this as well but it should be separate suricata ml log file._

## Validation

* Run `sudo ./run_realtime_engine_dpdk.sh start`:

  * Kafka listening on `:9092`.

  * Suricata (DPDK) started, logs at `/var/log/suricata/`.

  * Feature Engine PID and initial log.

  * ML Consumer PID and log; verify model load succeeds with updated paths.

  * Optional metrics dashboard available at `http://localhost:5000` if metrics present.

  * You need to make this dashbaord I think you should probably build a simply next js dashbaord that looks like grafana.

* Check topics: `ml-features`, `ml-predictions`, `suricata-alerts`.

## Next Actions

* I will delete the listed root Python files, update the two consumer scripts’ model/scaler paths to your local workspace, and (optionally) add starting `ml_kafka_consumer.py` to run in parallel with the ensemble/real-time consumer so both paths produce results.

* Confirm if you also want the Suricata ML consumer started by the runner; if yes, I’ll integrate it.

