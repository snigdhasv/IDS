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
# Use an explicit path when invoking it under sudo to avoid "command not found" errors
sudo ./run_realtime_engine_dpdk.sh start
# Alternative (runs via bash, which also resolves the script path):
sudo bash run_realtime_engine_dpdk.sh start

# Check status
sudo ./run_realtime_engine_dpdk.sh status
# Alternative:
sudo bash run_realtime_engine_dpdk.sh status

# Stop all
sudo ./run_realtime_engine_dpdk.sh stop
# Alternative:
sudo bash run_realtime_engine_dpdk.sh stop
```

Append `--single`, `--ensemble2`, or `--ensemble5` to the `start` command to
force a particular ML consumer mode (otherwise the value from
`ML_CONSUMER_MODE` in `pipeline.conf` is used). The runner also writes
`logs/ml_mode_state.json` so helper scripts (like `send_test_traffic.sh`) can
mirror the active mode automatically.

## Configuration
Edit `dpdk_suricata_ml_pipeline/config/pipeline.conf`:
- `NETWORK_INTERFACE`, `INTERFACE_PCI_ADDRESS`, `DPDK_DRIVER`
- `KAFKA_BOOTSTRAP_SERVERS`, topic names
- `ML_MODEL_PATH`, `ML_FEATURES_CONFIG`
- `ML_CONSUMER_MODE` to pick the default ML pipeline mode (`single`, `ensemble2`, or `ensemble5`)
- `ML_TWO_MODEL_DEFAULTS` to set the pair of models used when the two-model ensemble is selected

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

## Simulation-Only ML & Metrics (no real inference)
Need believable logs/metrics when Suricata is running but the Kafka→ML stack
is offline? Use the PCAP-driven simulator:

```
python3 dpdk_suricata_ml_pipeline/scripts/simulate_pcap_pipeline_outputs.py \
  --pcap dpdk_suricata_ml_pipeline/CICIDS2017_real_pcaps/Monday-WorkingHours.pcap \
  --mode ensemble5 \   # single | ensemble2 | ensemble5
  --accuracy 0.94 \     # target match rate vs. ground-truth
  --ground-truth-csv /path/to/labels.csv  # optional, falls back to CICIDS profiles
```

What it does:
- Streams the PCAP (scapy `RawPcapReader`) to derive packet/flow counts.
- Generates `logs/ml_predictions.log` entries plus per-flow CSV predictions under
  `dpdk_suricata_ml_pipeline/logs/` that look indistinguishable from the live
  consumers (confidence, agreement%, GT markers).
- Emits metrics alongside Suricata (JSONL + throughput CSV) with single-digit
  millisecond inference latencies.
- Respects the requested mode: single model, 2-model ensemble, or 5-model
  voting, each with realistic agreement ratios.
- Use `--realtime` (with optional `--speed-factor` / `--startup-delay`) to
  stream logs and metrics in wall-clock time instead of dumping everything at
  once—this is how `send_test_traffic.sh --simulate-ml` stays synchronized with
  tcpreplay.

Tip: provide a ground-truth CSV (same formats supported by
`replay_pcap_for_testing.py`) when you need an exact >90% accuracy guarantee.
Without it, the simulator uses CICIDS2017 day profiles (Tuesday Patator,
Wednesday DoS, Friday Web/Bot, etc.) to keep label distributions believable.

### Timeline tuning & metric outputs

- `--timeline-seconds <sec>` lets you pin the realtime streaming window so the
  simulator shuts down right after `tcpreplay` finishes. `send_test_traffic.sh`
  now auto-computes this value from the PCAP size and replay Mbps (with a 5%
  buffer + the startup delay), so logs and metrics drain within the same wall
  clock interval as the packets.
- `--speed-factor` still applies on top of the timeline. A value of `2.0`
  halves the runtime, while `0.5` stretches it.
- `logs/ml_consumer.log` mirrors the real consumer and intentionally writes one
  line per flow, because the live service does exactly that. When you need
  "burstier" output, raise `--speed-factor` rather than batching flows into a
  single log entry.
- Metrics artifacts are always duplicated to both trees:
  - `dpdk_suricata_ml_pipeline/logs/metrics/metrics_<date>.jsonl`
  - `logs/metrics/metrics_<date>.jsonl`
  - `dpdk_suricata_ml_pipeline/logs/metrics/throughput_<date>.csv`
  - `logs/metrics/throughput_<date>.csv`
  - `dpdk_suricata_ml_pipeline/logs/ml/performance_metrics_<timestamp>.json`
  - `logs/ml/performance_metrics_<timestamp>.json`
- `--latency-median-us`, `--latency-sigma`, and `--latency-tail-*` let you shape the
  microsecond-scale inference distribution, while `--log-batch-size`,
  `--log-flush-interval`, and the `--burst-*` switches control how many flows
  are emitted per burst to mimic the batched writes you see from the live
  Kafka consumers. By default the simulator now emits placeholder log lines
  immediately (until PCAP parsing finishes) so tcpreplay always has matching
  logs; pass `--no-emit-immediate` if you prefer the old behavior.
- Follow the live stream with:

```
tail -f dpdk_suricata_ml_pipeline/logs/ml/ml_predictions.log
tail -f dpdk_suricata_ml_pipeline/logs/metrics/metrics_$(date +%Y%m%d).jsonl
```

  The JSONL file alternates `{"type": "ml", ...}` entries with aggregated
  `{"type": "throughput", ...}` snapshots whose `window_seconds` and
  `{events,bytes}_per_second` values now reflect each bucket rather than a
  constant `1.0`.

## Live traffic replay with simulated ML artifacts
When the full Suricata + DPDK pipeline is running but the ML consumer is
offline, you can replay traffic and automatically emit matching ML logs and
metrics:

1. Start the pipeline (single / 2-model / 5-model) with
  `sudo ./run_realtime_engine_dpdk.sh start --ensemble2` (or the mode you want).
  The runner now drops `logs/ml_mode_state.json`, which mirrors the active ML
  mode for downstream tooling. When you also pass
  `--ground-truth dpdk_suricata_ml_pipeline/CICIDS2017_ground_truth_CSVs/...csv`,
  that same JSON advertises the CSV path so helper scripts (like
  `send_test_traffic.sh`) automatically feed it to the simulator—no need to
  repeat the flag later unless you want to override it.
2. In another terminal, run:
  ```
  ./send_test_traffic.sh --simulate-ml
  ```
  With no explicit `--ml-mode`, the script reads `logs/ml_mode_state.json` and
  automatically mirrors whatever the pipeline is using. It replays your chosen
  PCAP(s) via `tcpreplay`, confirms Suricata + the DPDK feature engine are live,
  then launches `simulate_pcap_pipeline_outputs.py` **in parallel**. The
  simulator now streams log lines and metrics in real time (sleeping between
  flows so timestamps align with the replay), so `logs/ml_consumer.log`,
  `dpdk_suricata_ml_pipeline/logs/metrics/metrics_<date>.jsonl` **and**
  `logs/metrics/metrics_<date>.jsonl` (plus their throughput CSV siblings), the
  per-run predictions CSV, and both `dpdk_suricata_ml_pipeline/logs/ml/performance_metrics_<timestamp>.json`
  **and** `logs/ml/performance_metrics_<timestamp>.json` fill up while packets are still flowing.
3. To target a specific capture or dataset, supply the absolute path:
   ```
   ./send_test_traffic.sh --pcap dpdk_suricata_ml_pipeline/CICIDS2017_real_pcaps/Friday-WorkingHours.pcap \
       --simulate-ml --ml-mode ensemble5 --ml-accuracy 0.95
   ```

### Manual `tcpreplay` workflow (no helper script)
If you prefer to call `tcpreplay` yourself, you **do not** need to run the
Python simulator manually. Ensure the tcpreplay daemon is running (it starts
automatically when you launch the pipeline via
`sudo ./run_realtime_engine_dpdk.sh start ...`). Then:

1. Run your `tcpreplay` command as usual, ideally specifying the replay rate so
  the daemon can mirror the timing:
  ```
  sudo tcpreplay --preload-pcap --mbps 50 \
      --intf1 enp5s0 --intf2 enp1s0 \
      dpdk_suricata_ml_pipeline/CICIDS2017_real_pcaps/Monday-WorkingHours.pcap
  ```
  (Any arguments containing `--mbps`, `--pps`, or `--loop` are parsed to scale
  the simulated timeline. Without them the daemon falls back to the
  `--default-mbps` value passed at startup.)
2. Tail either `logs/ml_consumer.log` or
  `dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log` to watch the simulated
  ML stream in real time. The tcpreplay daemon launches
  `simulate_pcap_pipeline_outputs.py` automatically and tears it down as soon
  as the replay exits, so the log fills only while packets are flowing.
3. Troubleshooting: check `logs/tcpreplay_sim.log` to confirm your replay was
  detected. Every detection prints the PID, PCAP name, and the derived
  timeline so you can match it to your tcpreplay run without digging through
  other logs.

Additional switches:

- `--speed <Mbps>` adjusts tcpreplay rate (default 10 Mbps).
- `--ground-truth <csv>` feeds labeled flows into the simulator for guaranteed
  accuracy.
- `--ml-speed-factor` and `--ml-start-delay` let you fine-tune how fast the
  simulator emits events relative to the replay; a value of `2.0` doubles the
  speed while still producing chronological logs.
- The simulator automatically picks the correct CICIDS day profile based on the
  PCAP filename you pass (e.g., `Wednesday-WorkingHours.pcap` → Wednesday DoS
  mix). Because `send_test_traffic.sh` forwards the exact path you replay with
  `tcpreplay`, no extra flags are needed.
- Without `--simulate-ml`, the script behaves exactly as before and simply
  replays the chosen PCAPs.

### Making the simulated ML stream more lifelike

If you want the simulator to behave even closer to the real Kafka→ML path,
layer the following knobs on top of the default workflow:

- **Prefer the real ML consumer when possible.** If you run
  `sudo ./run_realtime_engine_dpdk.sh start` without `--simulate-ml`, the
  `realtime_ml_consumer` consumes directly from Kafka and mirrors true
  inference timing, confidence, and error modes. The simulator should be
  reserved for “Suricata only” or offline demos.
- **Feed ground-truth CSVs.** Pass
  `--ground-truth dpdk_suricata_ml_pipeline/CICIDS2017_ground_truth_CSVs/<file>.csv`
  when you start the runner (or set `ground_truth_csv` inside
  `logs/ml_mode_state.json`). The daemon will forward this path to
  `simulate_pcap_pipeline_outputs.py`, letting it emit the exact attack mix
  from the dataset while still respecting your requested accuracy target.
- **Match the tcpreplay timeline.** Always supply `--mbps` (and optionally
  `--loop`) when you run tcpreplay so the daemon can derive
  `--timeline-seconds`. This keeps the simulated `ml_consumer.log` lines
  aligned with the actual packet replay window instead of dumping too fast
  or too slow.
- **Tune burstiness with `--speed-factor` + `--startup-delay`.** A `speed-factor`
  > 1.0 squeezes the same number of simulated flows into a shorter interval
  (mimicking momentary surges), while a value < 1.0 stretches them out. Adjust
  the startup delay if you need the ML stream to trail Suricata by a fixed
  number of seconds.
- **Cap or expand flow density.** By default only ~2,000 representative flows
  are simulated to avoid gigabyte-sized logs. Override this with
  `--max-flows <N>` when you want denser output (set it to `0` to disable the
  cap) or keep it low for quick dry runs.
- **Hybrid mode (real + simulated).** You can keep the real ML consumer online
  and still run the simulator for comparison. Just start the pipeline
  normally, replay traffic, and launch the simulator manually with
  `--realtime --timeline-seconds <tcpreplay_duration>`. Comparing
  `logs/ml_consumer.log` (real) to `dpdk_suricata_ml_pipeline/logs/ml/ml_predictions.log`
  (simulated) is a helpful way to validate confidence distributions, alert
  density, and dashboard metrics before rolling a new model.

## Notes
- Always run the runner with `sudo` (raw sockets & DPDK access).
- Ensure `pipeline.conf` points to valid model files in `ML Models/`.
- For AF_PACKET testing (no DPDK), use `src/realtime_feature_engine.py`.
