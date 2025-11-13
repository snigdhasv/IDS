## Goal
- Make `run_realtime_engine_dpdk.sh` the single entrypoint in project root.
- Keep all subfolders and the dependencies it uses intact.
- Delete all other `.sh` and `.md` files in the project root only (no subfolder changes).

## Dependencies To Keep
- `dpdk_suricata_ml_pipeline/` (entire): `config/`, `scripts/`, `src/`.
- `ML Models/` (entire): model `.joblib` files and `model_features_69.json`.
- `config/` (entire): `ids_config.yaml` used by feature/ML components.
- Root files to keep: `run_realtime_engine_dpdk.sh`, `requirements.txt`, `.gitignore`.
- All other subfolders in root (e.g., `notebooks/`, `tests/`, `backup_*/`) remain untouched.

## Root Files To Delete
- Root shell scripts (delete all except runner):
  - `ensemble_demo.sh`, `fix_and_replay_pcaps.sh`, `monitor_metrics.sh`, `quick_test_model.sh`, `replay_pcaps.sh`, `replay_with_full_features.sh`, `run_afpacket_mode.sh`, `run_dpdk_mode.sh`, `run_ids_with_replay.sh`, `run_realtime_engine.sh`, `setup_dashboard.sh`, `setup_dpdk_capture.sh`, `start_feature_engine.sh`, `start_ids_with_metrics.sh`, `test_dpdk_replay.sh`, `test_replay_complete.sh`, `test_ids_with_cicids.sh`.
- Root markdown files (delete all):
  - All `.md` in root including `AFPACKET_MODE_ARCHITECTURE.md`, `DPDK_MODE_ARCHITECTURE.md`, `README.md`, `STATUS_REPORT_AND_ROADMAP.md`, and the rest enumerated by discovery.
- Note: This scope intentionally does NOT delete root `.pdf`/`.txt` unless requested; we can include them if you want a completely minimal root.

## Script Consistency Fixes (post-cleanup)
- Align process name checks in `run_realtime_engine_dpdk.sh`:
  - Start checks use `pgrep -f "dpdk_feature_engine"` (run_realtime_engine_dpdk.sh:180–185).
  - Stop/status use `realtime_feature_engine` (run_realtime_engine_dpdk.sh:453–455, 513–518). Unify to `dpdk_feature_engine` everywhere so stop/status match start.
- Confirm Suricata stop pattern matches DPDK invocation `suricata.*--dpdk` (already present at run_realtime_engine_dpdk.sh:457–458).

## Config Adjustments
- Update `dpdk_suricata_ml_pipeline/config/pipeline.conf` for local paths and environment:
  - `ML_MODEL_PATH` → `"/Users/sujayschakravarthy/Programming/IDS/ML Models/decision_tree_model_2017.joblib"` (current points to a Linux path) (pipeline.conf:40).
  - `ML_FEATURES_CONFIG` currently `../config/ids_config.yaml` (pipeline.conf:43). Verify it resolves correctly from the working directory used by scripts; adjust to an absolute path if needed.
  - Verify `SURICATA_CONFIG` exists at `"/etc/suricata/suricata-dpdk.yaml"` (pipeline.conf:26) or point to the right file.

## Venv And Requirements
- Ensure a Python venv exists at project root (`venv`) with required packages:
  - Create venv and install: `python3 -m venv venv` then `source venv/bin/activate && pip install -r requirements.txt`.
- The runner expects `venv` at `SCRIPT_DIR/venv` (run_realtime_engine_dpdk.sh:31, 197).

## Validation Steps
- Run `sudo ./run_realtime_engine_dpdk.sh start` and confirm:
  - Kafka port check, Suricata DPDK starts, Feature Engine PID, ML Consumer PID.
  - Summary prints with NIC/DPDK details.
- Run `sudo ./run_realtime_engine_dpdk.sh status` to confirm stop/status process name fixes.
- Optional: `sudo ./run_realtime_engine_dpdk.sh test` for foreground Feature Engine with logs.

## What Will Change
- Root will contain only: `run_realtime_engine_dpdk.sh`, `requirements.txt`, `.gitignore` (plus any non-deleted docs you choose to keep).
- No subfolder contents will be removed.
- `run_realtime_engine_dpdk.sh` will have consistent process name checks to ensure reliable status/stop.

## Next Actions
- Confirm the deletion scope (root `.sh` and `.md` only) and whether to also remove root `.pdf`/`.txt`.
- After confirmation, I will execute the cleanup, update `pipeline.conf` paths, fix the runner process name checks, and validate the pipeline start/status.