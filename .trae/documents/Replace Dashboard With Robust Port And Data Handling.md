## Goals
- Build a new lightweight dashboard that avoids port conflicts, reliably fetches logs and metrics, and renders even in restricted preview environments.
- Keep the same data sources and parsing logic, but harden the client code (no fragile fetch/JSON parsing) and server port selection/printing.

## Data Sources
- `logs/ml_consumer.log` (format from ml_kafka_consumer.py)
- `logs/feature_engine.log` (feature engine stats)
- `logs/metrics/metrics_YYYYMMDD.jsonl` (structured metrics)
- `logs/suricata.log` or `/var/log/suricata/suricata.log` (alerts)

## Server Changes
- New script: `scripts/metrics_dashboard2.py` (keeps current endpoints: `/` and `/api/summary`).
- Port selection: probe safe range (e.g., 5500–5510), skip 5000 altogether; print the exact bound URL in stdout and write it to `logs/metrics_dashboard.port`.
- Summary builder: parse both current structured metrics schema (`type`, `component`, `events_count`, `bytes_count`, etc.) and the simpler one; normalize `component` names (`ml_consumer` vs `kafka_ml`).
- Log parsing: support `ML Benign: BENIGN (confidence: XX.XX%)` and `ML Alert: Attack-<Type> (confidence: XX.XX%)` from ml_kafka_consumer.py; treat `Attack-<Type>` as attack for chart counts, keep type names for a recent list.
- Suricata parser: read `/var/log/suricata/suricata.log` if present, else `logs/suricata.log`.
- Health endpoint `/api/health`: returns discovered files, sizes, last-modified times; helps troubleshooting.

## Client Changes
- Minimal HTML + CSS with no external dependencies (remove Chart.js if necessary). If Chart.js is available, render a bar chart; otherwise show numeric stats.
- Use XMLHttpRequest for `/api/summary` with strict try/catch and JSON parse fallback; update DOM even if some sections are empty.
- Sanitize recent log lines (escape, trim) before insertion into `<pre>` to avoid invalid tokens.
- Poll every 2 seconds; show last update time; never crash on parse failures.

## UX Improvements
- Show the exact bound port in the start output and in a log file for easy opening.
- Display source discovery status at the top (e.g., "ml_consumer.log: OK, feature_engine.log: OK, metrics: OK").
- Show a warning if no replay detected (no updates in last 5s), matching simulator’s grace period.

## Implementation Steps
1. Create `metrics_dashboard2.py` with hardened server, port logic, endpoints.
2. Implement robust summary parsing from all sources with normalization and defensive coding.
3. Build simple, dependency-free HTML/JS client with XHR and DOM updates; optional Chart.js only if loaded.
4. Add `api/health` for troubleshooting and print exact URL at startup.
5. Update the start script to launch the new dashboard and print its port.

## Verification
- Start pipeline in sim, start replay, open printed URL (e.g., `http://localhost:5500/`).
- Confirm `/api/summary` returns data; check health endpoint for source status.
- Validate that charts update or text stats display if Chart.js is unavailable.

## Notes
- No changes to existing log formats; only parsing and presentation are hardened.
- Avoid port 5000 on macOS; use 5500+ range by default for reliability.