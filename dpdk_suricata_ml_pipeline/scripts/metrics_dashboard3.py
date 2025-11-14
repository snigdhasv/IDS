#!/usr/bin/env python3
"""Modern, dependency-free dashboard for the IDS pipeline.

This script monitors the existing IDS logs/metrics and serves both:
  * ``/`` – a responsive single-page dashboard (HTML + vanilla JS)
  * ``/api/summary`` – aggregated JSON metrics for automation

Highlights
~~~~~~~~~~
* Watches ML consumer, Suricata, feature engine, and structured metrics files.
* Computes latency, throughput, inference-time, and health summaries.
* Writes the chosen URL to ``logs/metrics_dashboard.port`` so shell scripts
  can surface the exact address.
* Provides ``--dump`` CLI flag for quick sanity checks without starting
  the web server (useful for CI/tests).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Deque, Dict, Iterable, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
LOGS_DIR = ROOT_DIR / "logs"
METRICS_DIR = LOGS_DIR / "metrics"
ML_LOG = LOGS_DIR / "ml_consumer.log"
SURICATA_ML_LOG = LOGS_DIR / "suricata_ml_consumer.log"
FEATURE_LOG = LOGS_DIR / "feature_engine.log"
SURICATA_LOG = Path("/var/log/suricata/suricata.log")
ALT_SURICATA_LOG = LOGS_DIR / "suricata.log"
PORT_FILE = LOGS_DIR / "metrics_dashboard.port"

DEFAULT_PORTS = list(range(5510, 5521))
DEFAULT_INTERVAL = 2.0

ML_LINE = re.compile(r"ML\s+(Alert|Attack|Benign)\s*:?\s*([A-Za-z0-9_-]+)", re.IGNORECASE)
ML_CONF = re.compile(r"confidence:\s*([0-9.]+)\s*%?", re.IGNORECASE)
ATTACK_KIND = re.compile(r"Attack[-:\s]?([A-Za-z0-9_-]+)", re.IGNORECASE)
FEATURE_STATS = re.compile(r"Stats:\s*([\d,]+)\s+packets,\s*([\d,]+)\s+active flows", re.IGNORECASE)
SURICATA_ALERT = re.compile(r"Alert signature:\s*([A-Za-z0-9 /-]+)\s+severity:\s*(\d+)", re.IGNORECASE)
ISO_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")

logger = logging.getLogger("ids-dashboard3")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def tail_file(path: Path, max_bytes: int = 200_000) -> List[str]:
    """Return the last ~max_bytes from *path* as a list of decoded lines."""

    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(size - max_bytes, 0))
            data = handle.read().decode(errors="ignore")
            return data.splitlines()
    except FileNotFoundError:
        return []
    except Exception as exc:  # pragma: no cover - best-effort tail
        logger.debug("tail_file failed for %s: %s", path, exc)
        return []


def file_health(path: Optional[Path]) -> Dict[str, object]:
    if not path or not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "size": stat.st_size,
        "updated": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "age_seconds": max(time.time() - stat.st_mtime, 0.0),
        "path": str(path),
    }


def summarize_simple(values: List[float]) -> Dict[str, float]:
    if not values:
        return {}
    return {
        "latest": values[-1],
        "min": min(values),
        "max": max(values),
    }


def percentile(sorted_values: List[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return d0 + d1


def summarize_series(values: List[float]) -> Dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values)
    n = len(ordered)
    return {
        "count": n,
        "min": ordered[0],
        "max": ordered[-1],
        "mean": sum(ordered) / n,
        "p50": percentile(ordered, 50),
        "p95": percentile(ordered, 95),
        "p99": percentile(ordered, 99),
    }


def extract_ts(text: str) -> Optional[str]:
    candidate = text[:19]
    if ISO_PREFIX.match(candidate):
        return candidate.replace("T", " ")
    parts = text.split(" - ", 1)
    if parts and ISO_PREFIX.match(parts[0]):
        return parts[0].replace("T", " ")
    return None


def extract_flow(text: str) -> str:
    if ") - " in text:
        return text.split(") - ", 1)[1].strip()
    if " -> " in text:
        idx = text.find(" -> ")
        return text[idx - 30 :].strip()
    return ""


def parse_ml_log(path: Path, limit: int = 600) -> Dict[str, object]:
    lines = tail_file(path)
    total = attack = benign = 0
    confidences: List[float] = []
    attack_breakdown: Dict[str, int] = defaultdict(int)
    recent: Deque[Dict[str, object]] = deque(maxlen=200)

    for raw in lines[-limit:]:
        text = raw.strip()
        if not text:
            continue
        kind = ML_LINE.search(text)
        label = "BENIGN"
        attack_name: Optional[str] = None
        if kind:
            if kind.group(1).lower() in ("alert", "attack"):
                label = "ATTACK"
            attack_match = ATTACK_KIND.search(kind.group(2))
            if attack_match:
                attack_name = attack_match.group(1).upper()
            else:
                attack_name = kind.group(2).upper()
        elif "ATTACK" in text.upper():
            label = "ATTACK"
        conf_match = ML_CONF.search(text)
        confidence = float(conf_match.group(1)) if conf_match else 0.0
        if confidence <= 1.5:
            confidence *= 100.0
        if label == "ATTACK":
            attack += 1
            attack_breakdown[(attack_name or "ATTACK")] += 1
        else:
            benign += 1
        total += 1
        confidences.append(confidence)
        recent.append(
            {
                "ts": extract_ts(text),
                "label": (attack_name or "ATTACK") if label == "ATTACK" else "BENIGN",
                "confidence": round(confidence, 2),
                "flow": extract_flow(text),
                "raw": text[-300:],
            }
        )

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return {
        "present": path.exists(),
        "source": str(path),
        "total": total,
        "attack": attack,
        "benign": benign,
        "benign_rate": (benign / total) if total else 0.0,
        "avg_confidence": avg_conf,
        "attack_breakdown": dict(sorted(attack_breakdown.items(), key=lambda kv: (-kv[1], kv[0]))),
        "recent": list(recent)[-20:],
    }


def parse_suricata_log() -> Dict[str, object]:
    path = SURICATA_LOG if SURICATA_LOG.exists() else ALT_SURICATA_LOG
    lines = tail_file(path) if path.exists() else []
    alerts = 0
    signatures: Dict[str, int] = defaultdict(int)
    severities: Dict[str, int] = defaultdict(int)
    recent: Deque[str] = deque(maxlen=50)

    for raw in lines[-600:]:
        text = raw.strip()
        if not text:
            continue
        match = SURICATA_ALERT.search(text)
        if not match:
            continue
        sig = match.group(1).strip()
        sev = match.group(2).strip()
        alerts += 1
        signatures[sig] += 1
        severities[sev] += 1
        recent.append(f"{sig} (sev {sev}) @ {text[:23]}")

    return {
        "present": path.exists(),
        "source": str(path) if path.exists() else None,
        "alerts": alerts,
        "signatures": dict(sorted(signatures.items(), key=lambda kv: (-kv[1], kv[0]))[:8]),
        "severity": dict(sorted(severities.items())),
        "recent": list(recent)[-20:],
    }


def parse_feature_log() -> Dict[str, object]:
    lines = tail_file(FEATURE_LOG)
    packets: List[int] = []
    flows: List[int] = []
    last_ts: Optional[str] = None
    for raw in lines[-400:]:
        match = FEATURE_STATS.search(raw)
        if not match:
            continue
        packets.append(int(match.group(1).replace(",", "")))
        flows.append(int(match.group(2).replace(",", "")))
        ts = extract_ts(raw)
        if ts:
            last_ts = ts
    return {
        "present": FEATURE_LOG.exists(),
        "source": str(FEATURE_LOG),
        "approx_events": len(lines),
        "packets": summarize_simple(packets),
        "flows": summarize_simple(flows),
        "last_timestamp": last_ts,
        "recent_lines": [line.strip() for line in lines[-10:]],
    }


def latest_metrics_file() -> Optional[Path]:
    today = METRICS_DIR / f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl"
    if today.exists():
        return today
    files = sorted(METRICS_DIR.glob("metrics_*.jsonl"))
    return files[-1] if files else None


def parse_metrics_jsonl(max_bytes: int = 400_000) -> Dict[str, object]:
    jf = latest_metrics_file()
    if not jf:
        return {
            "latency": {},
            "inference": {},
            "ml_preds": {},
            "throughput": {},
            "system": {},
            "source_path": None,
        }

    lines = tail_file(jf, max_bytes=max_bytes)
    latencies: List[float] = []
    inference_times: List[float] = []
    ml_counts: Dict[str, int] = defaultdict(int)
    throughput_last: Dict[str, Dict[str, object]] = {}
    throughput_history: Dict[str, Deque[Dict[str, float]]] = defaultdict(lambda: deque(maxlen=40))
    system_sample: Dict[str, float] = {}

    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        typ = rec.get("type")
        if typ == "latency":
            val = rec.get("latency_ms")
            if isinstance(val, (int, float)):
                latencies.append(float(val))
        elif typ == "ml":
            ml_counts[rec.get("prediction", "UNKNOWN")] += 1
            val = rec.get("inference_time_ms")
            if isinstance(val, (int, float)):
                inference_times.append(float(val))
        elif typ == "throughput":
            component = rec.get("component", "pipeline")
            eps = rec.get("events_per_second")
            if eps is None:
                events = rec.get("events_count", 0)
                window = rec.get("window_seconds") or 1.0
                eps = events / window if window else float(events)
            throughput_last[component] = {
                "events_per_second": eps,
                "events_count": rec.get("events_count"),
                "bytes_per_second": rec.get("bytes_per_second"),
                "timestamp": rec.get("timestamp"),
            }
            throughput_history[component].append({"ts": rec.get("timestamp"), "eps": eps})
        elif typ == "system":
            system_sample = {
                "cpu_percent": rec.get("cpu_percent", 0.0),
                "memory_percent": rec.get("memory_percent", 0.0),
                "memory_mb": rec.get("memory_mb", 0.0),
                "timestamp": rec.get("timestamp"),
            }

    throughput = {
        comp: {**data, "history": list(throughput_history.get(comp, []))}
        for comp, data in throughput_last.items()
    }

    return {
        "latency": summarize_series(latencies),
        "inference": summarize_series(inference_times),
        "ml_preds": dict(sorted(ml_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "throughput": throughput,
        "system": system_sample,
        "source_path": str(jf),
    }


def derive_status_message(ml: Dict[str, object], suri: Dict[str, object], feature: Dict[str, object], metrics: Dict[str, object]) -> str:
    if not ml.get("total"):
        return "Waiting for ML predictions…"
    if ml.get("attack"):
        top = next(iter(ml.get("attack_breakdown", {}) or {}), "ATTACK")
        return f"Streaming attacks detected ({top})"
    if suri.get("alerts"):
        return f"Suricata signature stream active ({suri['alerts']} alerts)"
    if feature.get("packets"):
        return "Feature engine running, awaiting alerts"
    if metrics.get("throughput"):
        return "Metrics flowing; no alerts yet"
    return "Dashboard online but sources are quiet"


def build_summary() -> Dict[str, object]:
    ml_summary = parse_ml_log(ML_LOG)
    suricata_summary = parse_suricata_log()
    suricata_ml_summary = parse_ml_log(SURICATA_ML_LOG)
    metrics_summary = parse_metrics_jsonl()
    feature_summary = parse_feature_log()

    metrics_path = Path(metrics_summary["source_path"]) if metrics_summary.get("source_path") else None

    health = {
        "ml_consumer.log": file_health(ML_LOG),
        "suricata.log": file_health(Path(suricata_summary.get("source")) if suricata_summary.get("source") else None),
        "suricata_ml_consumer.log": file_health(SURICATA_ML_LOG),
        "feature_engine.log": file_health(FEATURE_LOG),
        "metrics_jsonl": file_health(metrics_path),
    }
    status_message = derive_status_message(ml_summary, suricata_summary, feature_summary, metrics_summary)
    sources_online = sum(1 for meta in health.values() if meta.get("exists"))

    return {
        "timestamp": datetime.now().isoformat(),
        "timestamp_unix": time.time(),
        "ml": ml_summary,
        "suricata_alerts": suricata_summary,
        "suricata_ml": suricata_ml_summary,
        "metrics": metrics_summary,
        "feature_engine": feature_summary,
        "health": health,
        "status": {
            "message": status_message,
            "sources_online": sources_online,
            "sources_total": len(health),
        },
    }


class DashboardState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshot: Dict[str, object] = {
            "timestamp": None,
            "status": {"message": "Collecting data…", "sources_online": 0, "sources_total": 0},
        }

    def update(self, data: Dict[str, object]) -> None:
        with self._lock:
            self._snapshot = data

    def read(self) -> Dict[str, object]:
        with self._lock:
            return self._snapshot


STATE = DashboardState()


class Collector(threading.Thread):
    def __init__(self, interval: float) -> None:
        super().__init__(daemon=True)
        self.interval = max(interval, 0.5)

    def run(self) -> None:  # pragma: no cover - relies on filesystem
        while True:
            try:
                STATE.update(build_summary())
            except Exception as exc:
                logger.exception("Failed to build summary: %s", exc)
            time.sleep(self.interval)


def write_port_file(port: int, host: str) -> None:
    try:
        PORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        PORT_FILE.write_text(f"http://{host or 'localhost'}:{port}\n", encoding="utf-8")
    except Exception as exc:  # pragma: no cover - best-effort helper
        logger.debug("Unable to write port file: %s", exc)


class DashboardHandler(BaseHTTPRequestHandler):
    state: DashboardState = STATE

    def do_GET(self) -> None:  # pragma: no cover - exercised at runtime
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._respond_html(INDEX_HTML)
            return
        if path == "/api/summary":
            payload = json.dumps(self.state.read()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt: str, *args: object) -> None:
        logger.debug("HTTP %s - " + fmt, self.address_string(), *args)

    def _respond_html(self, html_body: str) -> None:
        body = html_body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


INDEX_HTML = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>IDS Live Dashboard</title>
  <style>
    :root {
      color-scheme: light dark;
      --bg: #f5f7fb;
      --card: #ffffff;
      --muted: #6b7280;
      --border: #e5e7eb;
      --accent: #2563eb;
      --attack: #dc2626;
      --benign: #059669;
      --shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
    }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
      background: var(--bg);
      color: #0f172a;
      padding: 24px;
    }
    header {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
      margin-bottom: 16px;
    }
    h1 { margin: 0; font-size: 1.7rem; }
    .muted { color: var(--muted); font-size: 0.9rem; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }
    .card {
      background: var(--card);
      border-radius: 16px;
      padding: 18px;
      box-shadow: var(--shadow);
      border: 1px solid var(--border);
      min-height: 160px;
    }
    .stats-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 12px;
      margin: 12px 0 8px;
    }
    .stat {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .stat .label { font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
    .stat .value { font-size: 1.4rem; font-weight: 600; }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    th, td { text-align: left; padding: 6px 4px; border-bottom: 1px solid var(--border); }
    th { font-size: 0.75rem; text-transform: uppercase; color: var(--muted); }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: 999px;
      background: rgba(37, 99, 235, 0.15);
      color: var(--accent);
      font-weight: 600;
      font-size: 0.85rem;
    }
    .pill {
      display: inline-block;
      padding: 2px 10px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .pill.attack { background: rgba(220,38,38,0.15); color: var(--attack); }
    .pill.benign { background: rgba(5,150,105,0.15); color: var(--benign); }
    pre { background: #1118270a; padding: 12px; border-radius: 10px; overflow: auto; max-height: 180px; font-size: 0.85rem; }
    ul { padding-left: 18px; margin: 6px 0; }
    li { margin-bottom: 4px; }
    @media (max-width: 640px) {
      body { padding: 16px; }
      header { flex-direction: column; align-items: flex-start; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>IDS Live Dashboard</h1>
      <div class=\"muted\">Suricata + Feature Engine + ML consumer metrics</div>
    </div>
    <div>
      <div id=\"statusMessage\" class=\"badge\">Bootstrapping…</div>
      <div id=\"updated\" class=\"muted\">Waiting for data…</div>
    </div>
  </header>

  <div class=\"grid\">
    <section class=\"card\">
      <h3>ML Predictions</h3>
      <div class=\"stats-row\">
        <div class=\"stat\"><span class=\"label\">Total</span><span class=\"value\" id=\"ml-total\">—</span></div>
        <div class=\"stat\"><span class=\"label\">Attack</span><span class=\"value pill attack\" id=\"ml-attack\">—</span></div>
        <div class=\"stat\"><span class=\"label\">Benign</span><span class=\"value pill benign\" id=\"ml-benign\">—</span></div>
        <div class=\"stat\"><span class=\"label\">Avg confidence</span><span class=\"value\" id=\"ml-avg\">—</span></div>
      </div>
      <div class=\"muted\">Attack breakdown</div>
      <ul id=\"attack-breakdown\"></ul>
    </section>

    <section class=\"card\">
      <h3>Recent Predictions</h3>
      <table>
        <thead><tr><th>Time</th><th>Label</th><th>Confidence</th></tr></thead>
        <tbody id=\"ml-recent-rows\"></tbody>
      </table>
    </section>

    <section class=\"card\">
      <h3>Suricata Alerts</h3>
      <div class=\"stats-row\">
        <div class=\"stat\"><span class=\"label\">Total alerts</span><span class=\"value\" id=\"suri-total\">—</span></div>
        <div class=\"stat\"><span class=\"label\">Top signature</span><span class=\"value\" id=\"suri-top\">—</span></div>
      </div>
      <div class=\"muted\">Severity mix</div>
      <ul id=\"suri-severity\"></ul>
      <div class=\"muted\" style=\"margin-top:8px;\">Recent alerts</div>
      <pre id=\"suri-recent\">None yet…</pre>
    </section>

    <section class=\"card\">
      <h3>Latency &amp; Inference</h3>
      <div class=\"stats-row\">
        <div class=\"stat\"><span class=\"label\">Latency p95 (ms)</span><span class=\"value\" id=\"latency-p95\">—</span></div>
        <div class=\"stat\"><span class=\"label\">Latency mean</span><span class=\"value\" id=\"latency-mean\">—</span></div>
        <div class=\"stat\"><span class=\"label\">Inference p95</span><span class=\"value\" id=\"infer-p95\">—</span></div>
        <div class=\"stat\"><span class=\"label\">Inference mean</span><span class=\"value\" id=\"infer-mean\">—</span></div>
      </div>
    </section>

    <section class=\"card\">
      <h3>Throughput</h3>
      <table>
        <thead><tr><th>Component</th><th>EPS</th><th>Last sample</th></tr></thead>
        <tbody id=\"throughput-rows\"></tbody>
      </table>
    </section>

    <section class=\"card\">
      <h3>System</h3>
      <div class=\"stats-row\">
        <div class=\"stat\"><span class=\"label\">CPU %</span><span class=\"value\" id=\"sys-cpu\">—</span></div>
        <div class=\"stat\"><span class=\"label\">Mem %</span><span class=\"value\" id=\"sys-mem\">—</span></div>
        <div class=\"stat\"><span class=\"label\">RAM (MB)</span><span class=\"value\" id=\"sys-ram\">—</span></div>
      </div>
    </section>

    <section class=\"card\">
      <h3>Feature Engine</h3>
      <div class=\"stats-row\">
        <div class=\"stat\"><span class=\"label\">Packets</span><span class=\"value\" id=\"feat-packets\">—</span></div>
        <div class=\"stat\"><span class=\"label\">Active flows</span><span class=\"value\" id=\"feat-flows\">—</span></div>
      </div>
      <div class=\"muted\">Recent lines</div>
      <pre id=\"feat-recent\">—</pre>
    </section>

    <section class=\"card\">
      <h3>Source Health</h3>
      <ul id=\"health-list\"></ul>
    </section>
  </div>

  <script>
    const fmt = (value, digits = 1) => {
      if (value === undefined || value === null || Number.isNaN(value)) return '—';
      if (typeof value === 'number') {
        if (Math.abs(value) >= 1000) {
          return value.toLocaleString(undefined, {maximumFractionDigits: digits});
        }
        return value.toFixed(digits);
      }
      return String(value);
    };

    function setList(id, entries) {
      const el = document.getElementById(id);
      el.innerHTML = '';
      if (!entries || Object.keys(entries).length === 0) {
        el.innerHTML = '<li class=\"muted\">No data</li>';
        return;
      }
      Object.entries(entries).forEach(([key, val]) => {
        const item = document.createElement('li');
        item.textContent = `${key}: ${val}`;
        el.appendChild(item);
      });
    }

    function render(summary) {
      const ml = summary.ml || {};
      document.getElementById('statusMessage').textContent = (summary.status && summary.status.message) || '—';
      document.getElementById('updated').textContent = summary.timestamp ? `Updated ${new Date(summary.timestamp).toLocaleString()}` : 'Waiting for data…';
      document.getElementById('ml-total').textContent = ml.total ?? '—';
      document.getElementById('ml-attack').textContent = ml.attack ?? '—';
      document.getElementById('ml-benign').textContent = ml.benign ?? '—';
      document.getElementById('ml-avg').textContent = fmt(ml.avg_confidence, 2) + '%';
      setList('attack-breakdown', ml.attack_breakdown);

      const recentBody = document.getElementById('ml-recent-rows');
      recentBody.innerHTML = '';
      (ml.recent || []).slice(-8).reverse().forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${item.ts || '—'}</td><td>${item.label || '—'}</td><td>${fmt(item.confidence, 2)}%</td>`;
        recentBody.appendChild(tr);
      });

      const suri = summary.suricata_alerts || {};
      document.getElementById('suri-total').textContent = suri.alerts ?? '—';
      const topSig = Object.keys(suri.signatures || {})[0];
      document.getElementById('suri-top').textContent = topSig || '—';
      setList('suri-severity', suri.severity);
      document.getElementById('suri-recent').textContent = (suri.recent || []).join('\n') || 'None yet…';

      const metrics = summary.metrics || {};
      const latency = metrics.latency || {};
      const inference = metrics.inference || {};
      document.getElementById('latency-p95').textContent = fmt(latency.p95, 2);
      document.getElementById('latency-mean').textContent = fmt(latency.mean, 2);
      document.getElementById('infer-p95').textContent = fmt(inference.p95, 2);
      document.getElementById('infer-mean').textContent = fmt(inference.mean, 2);

      const throughputBody = document.getElementById('throughput-rows');
      throughputBody.innerHTML = '';
      Object.entries(metrics.throughput || {}).forEach(([comp, data]) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${comp}</td><td>${fmt(data.events_per_second, 0)}</td><td>${data.timestamp || '—'}</td>`;
        throughputBody.appendChild(tr);
      });

      const system = metrics.system || {};
      document.getElementById('sys-cpu').textContent = fmt(system.cpu_percent, 1) + '%';
      document.getElementById('sys-mem').textContent = fmt(system.memory_percent, 1) + '%';
      document.getElementById('sys-ram').textContent = fmt(system.memory_mb || 0, 0);

      const feature = summary.feature_engine || {};
      document.getElementById('feat-packets').textContent = feature.packets ? fmt(feature.packets.latest, 0) : '—';
      document.getElementById('feat-flows').textContent = feature.flows ? fmt(feature.flows.latest, 0) : '—';
      document.getElementById('feat-recent').textContent = (feature.recent_lines || []).join('\n') || '—';

      const health = summary.health || {};
      const healthList = document.getElementById('health-list');
      healthList.innerHTML = '';
      Object.entries(health).forEach(([name, meta]) => {
        const li = document.createElement('li');
        const ok = meta.exists;
        li.innerHTML = `<strong>${name}</strong>: ${ok ? 'OK' : 'Missing'}${meta.updated ? ` · updated ${new Date(meta.updated).toLocaleTimeString()}` : ''}`;
        li.style.color = ok ? 'var(--benign)' : 'var(--attack)';
        healthList.appendChild(li);
      });
    }

    async function poll() {
      try {
        const res = await fetch(`/api/summary?ts=${Date.now()}`, {cache: 'no-store'});
        if (!res.ok) return;
        const data = await res.json();
        render(data);
      } catch (err) {
        console.error('Refresh failed', err);
      }
    }

    poll();
    setInterval(poll, 2000);
  </script>
</body>
</html>
"""


def run_server(host: str, ports: Iterable[int]) -> None:
    tried = []
    for port in ports:
        if not port:
            continue
        try:
            server = ThreadingHTTPServer((host, port), DashboardHandler)
            write_port_file(port, host or "localhost")
            logger.info("Dashboard listening on http://%s:%s", host or "0.0.0.0", port)
            server.serve_forever()
            return
        except OSError as exc:
            tried.append((port, str(exc)))
            logger.warning("Port %s unavailable: %s", port, exc)
    raise RuntimeError(f"Unable to bind to any port: {tried}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Real-time IDS dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="Host/IP to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, help="Preferred port; falls back to 5510-5520")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="Refresh interval in seconds")
    parser.add_argument("--dump", action="store_true", help="Print one JSON snapshot and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.dump:
        print(json.dumps(build_summary(), indent=2))
        return 0

    collector = Collector(args.interval)
    collector.start()

    ports = []
    if args.port:
        ports.append(args.port)
    ports.extend(p for p in DEFAULT_PORTS if p not in ports)

    try:
        run_server(args.host, ports)
    except KeyboardInterrupt:
        logger.info("Dashboard interrupted, shutting down")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
