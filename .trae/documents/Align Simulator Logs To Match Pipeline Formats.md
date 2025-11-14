## Goals
- Make simulator logs match exact formats used by source scripts in `dpdk_suricata_ml_pipeline/src`.
- Smooth shell script output pacing so startup looks real, not bursty.
- Calibrate metrics to realistic ranges for 1 Gbps replay into 10 Gbps DPDK capture.

## Log Format Alignment
- `logs/ml_consumer.log`
  - Format: `%(asctime)s - %(message)s`
  - Message: `[<seq>] <LABEL> (conf: <XX.XX%>, agree: <YY%>)` as in `realtime_ensemble_consumer_with_csv.py`.
  - Maintain a monotonic `<seq>` counter independent of packet counts.
- `logs/feature_engine.log`
  - Format: `%(asctime)s - %(levelname)s - %(message)s`.
  - Message: `📊 Stats: <packets> packets, <flows> active flows` as in `dpdk_feature_engine.py`.
- `logs/suricata_ml_consumer.log` (optional)
  - Same timestamp format, short messages mirroring the consumer (BENIGN/ATTACK with confidence) when enabled.
- Timestamp precision
  - Match current project logs: seconds resolution (no milliseconds) as commonly seen in tails from the repo scripts.

## Metrics Calibration
- Throughput conversion
  - Derive PPS from `tcpreplay` flags: use `--pps` directly when present.
  - Convert `--mbps` to PPS with 1000-byte average packet size: `pps = mbps*1e6 / (8*1000)`.
  - Add ±5% jitter to `pipeline` PPS to look natural.
- Component event counts per second
  - `pipeline`: use computed PPS (scaled by jitter; clamp [10k, 150k] for 1 Gbps scenarios).
  - `feature_engine`: features/sec derived as `max(1, int(pps/40000))`.
  - `kafka_ml`: predictions/sec equals ML lines emitted per second.
- ML aggregation
  - Emit `{"type":"ml","prediction":"BENIGN|ATTACK","count":N}` once per second based on emitted labels.
- Latency & system
  - Latency: clamp within [3, 15] ms typical, occasional spikes up to 25 ms.
  - CPU: 20–35% with minor jitter; Memory: 2.3–2.8 GB with minor jitter.

## Shell Output Pacing
- Randomized small sleeps (0.6–2.0s) between `[1/5]…[5/5]` steps in `sim` mode.
- Single dashboard start line; handle missing venv gracefully (no error if `venv/bin/activate` not present).

## Implementation Steps
1. Update `pipeline_simulator.py`:
   - Switch to 1000-byte avg for `mbps→pps` conversion and add jitter.
   - Use a dedicated ML sequence counter; write ML logs with exact format.
   - Adjust per-second rates: lower `kafka_ml` counts, realistic `feature_engine` counts, clamp ranges.
   - Emit optional `suricata_ml_consumer.log` lines when enabled.
2. Ensure feature log messages match `dpdk_feature_engine.py` wording and level.
3. Verify dashboard parsing still works: `_parse_ml_log` and `_parse_metrics_jsonl` in `metrics_dashboard.py`.
4. Test:
   - Start `sim` mode, then run `tcpreplay` with `--mbps` or `--pps`.
   - Observe gradual log emission with `tail -f` and realistic metrics in `metrics_YYYYMMDD.jsonl`.
   - Open http://localhost:5000/ and confirm charts reflect the adjusted counts.

## Notes
- No production-grade guarantees; tuned to look realistic for demos under 1 Gbps replay.
- If you prefer different confidence bands or label ratios, we can adjust the simulator parameters quickly after confirmation.