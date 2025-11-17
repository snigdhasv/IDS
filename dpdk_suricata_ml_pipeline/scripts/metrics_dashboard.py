#!/usr/bin/env python3
"""
Web Metrics Dashboard (no external dependencies)

Serves a lightweight web UI on http://localhost:5000 to visualize real-time
IDS pipeline metrics from existing logs and metrics files.

Endpoints:
  - /            : Single-page dashboard (HTML + JS)
  - /api/summary : Aggregated metrics JSON (updated on each request)

Reads from:
  - logs/ml_consumer.log (ensemble or single ML consumer)
  - logs/suricata_ml_consumer.log (alerts ML consumer, optional)
  - logs/feature_engine.log (feature engine)
  - logs/metrics/metrics_YYYYMMDD.jsonl (structured metrics if present)
  - /var/log/suricata/suricata.log (Suricata)
"""

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from datetime import datetime
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = PIPELINE_ROOT / 'logs'
ROOT_METRICS_DIR = ROOT_DIR / 'logs' / 'metrics'
PIPELINE_METRICS_DIR = LOGS_DIR / 'metrics'
ML_LOG = ROOT_DIR / 'logs' / 'ml_predictions.log'  # Use workspace predictions log
SURICATA_ML_LOG = LOGS_DIR / 'suricata_ml_consumer.log'
FEATURE_LOG = LOGS_DIR / 'feature_engine.log'
SURICATA_LOG = Path('/var/log/suricata/suricata.log')
SURICATA_EVE_LOG = Path('/var/log/suricata/eve.json')

def _tail_lines(path: Path, max_lines: int = 500):
    try:
        with open(path, 'r') as f:
            return f.readlines()[-max_lines:]
    except Exception:
        return []

def _parse_ml_log(lines):
    total = 0
    benign = 0
    attack = 0
    confidences = []
    recent = []
    label_counts = {}
    pat = re.compile(r"\]\s*([A-Za-z0-9 _./-]+?)\s*\(conf:\s*([0-9.]+)")
    for line in lines[-200:]:
        m = pat.search(line)
        if m:
            raw_label = m.group(1).strip()
            label_upper = raw_label.upper()
            display_label = raw_label or label_upper
            conf = float(m.group(2)) if m.group(2) else 0.0
            total += 1
            if label_upper.startswith('BENIGN'):
                benign += 1
            else:
                attack += 1
                label_counts[display_label] = label_counts.get(display_label, 0) + 1
            confidences.append(conf)
            recent.append({
                'ts': line.split(' - ')[0],
                'label': display_label,
                'raw_label': raw_label,
                'confidence': conf
            })
    avg_conf = sum(confidences)/len(confidences) if confidences else 0.0
    return {
        'total': total,
        'benign': benign,
        'attack': attack,
        'avg_confidence': avg_conf,
        'recent': recent[-20:],
        'label_counts': label_counts
    }

def _parse_suricata_log(lines):
    alerts = 0
    recent = []
    for line in lines[-500:]:
        if 'Alert' in line or 'ALERT' in line:
            alerts += 1
            recent.append(line.strip()[:180])
    return {'alerts': alerts, 'recent': recent[-20:]}

def _parse_eve_json():
  try:
    if not SURICATA_EVE_LOG.exists():
      return {'events': [], 'alerts': 0, 'flows': 0}

    events = []
    alerts = 0
    flows = set()

    with open(SURICATA_EVE_LOG, 'r') as f:
      for line in f.readlines()[-1000:]:  # Read last 1000 lines
        try:
          event = json.loads(line.strip())
        except json.JSONDecodeError:
          continue

        event_type = event.get('event_type', '')

        if event_type == 'alert':
          alerts += 1
          events.append({
            'timestamp': event.get('timestamp', ''),
            'type': 'alert',
            'signature': event.get('alert', {}).get('signature', 'Unknown'),
            'src_ip': event.get('src_ip', ''),
            'dest_ip': event.get('dest_ip', ''),
            'proto': event.get('proto', ''),
            'severity': event.get('alert', {}).get('severity', 3)
          })
        elif event_type in ['dns', 'http', 'tls', 'ntp', 'flow']:
          flows.add(event.get('flow_id', 0))
          events.append({
            'timestamp': event.get('timestamp', ''),
            'type': event_type,
            'src_ip': event.get('src_ip', ''),
            'dest_ip': event.get('dest_ip', ''),
            'proto': event.get('proto', ''),
            'details': str(event.get(event_type, {}))[:100]  # Truncate details
          })

    return {
      'events': events[-20:],
      'total_events': len(events),
      'alerts': alerts,
      'flows': len(flows)
    }
  except Exception:
    return {'events': [], 'alerts': 0, 'flows': 0}

def _resolve_metrics_file(daystamp: str) -> Optional[Path]:
  for base in (ROOT_METRICS_DIR, PIPELINE_METRICS_DIR):
    candidate = base / f'metrics_{daystamp}.jsonl'
    if candidate.exists():
      return candidate
  return None

def _parse_metrics_jsonl():
  try:
    today = datetime.now().strftime('%Y%m%d')
    jf = _resolve_metrics_file(today)
    if jf is None:
      return {}
    latencies = []
    ml_preds = {}
    throughput = {}
    system = {}
    with open(jf, 'r') as f:
      for line in f.readlines()[-1000:]:
        rec = json.loads(line)
        t = rec.get('type')
        if t == 'latency':
          latencies.append(rec.get('latency_ms', 0))
        elif t == 'ml':
          p = rec.get('prediction', 'UNKNOWN')
          ml_preds[p] = ml_preds.get(p, 0) + 1
          if 'inference_time_ms' in rec:
            latencies.append(rec.get('inference_time_ms', 0))
        elif t == 'throughput':
          c = rec.get('component', 'pipeline')
          throughput[c] = throughput.get(c, 0) + rec.get('events_count', 0)
        elif t == 'system':
          system = {
            'cpu_percent': rec.get('cpu_percent', 0),
            'memory_percent': rec.get('memory_percent', 0),
            'memory_mb': rec.get('memory_mb', 0),
          }
    lat_stats = {}
    if latencies:
      s = sorted(latencies)
      n = len(s)
      lat_stats = {
        'count': n,
        'mean_ms': sum(s)/n,
        'p50_ms': s[int(n*0.5)],
        'p95_ms': s[int(n*0.95)],
        'p99_ms': s[int(n*0.99)] if n > 0 else 0,
      }
    return {'latency': lat_stats, 'ml_preds': ml_preds, 'throughput': throughput, 'system': system}
  except Exception:
    return {}

def build_summary():
    ml_summary = _parse_ml_log(_tail_lines(ML_LOG, 2000)) if ML_LOG.exists() else {}
    suri_summary = _parse_suricata_log(_tail_lines(SURICATA_LOG, 2000)) if SURICATA_LOG.exists() else {}
    metrics_structured = _parse_metrics_jsonl()
    feature_lines = _tail_lines(FEATURE_LOG, 500)
    features_processed = len(feature_lines)
    eve_summary = _parse_eve_json()
    return {
        'timestamp': datetime.now().isoformat(),
        'ml': ml_summary,
        'suricata_alerts': suri_summary,
        'metrics': metrics_structured,
        'feature_engine': {'recent_lines': feature_lines[-10:], 'approx_events': features_processed},
        'suricata_events': eve_summary
    }

INDEX_HTML = """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>IDS Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/modern-css-reset/dist/reset.min.css" />
    <style>
      body { font-family: -apple-system, system-ui, Segoe UI, Roboto, Helvetica, Arial, sans-serif; padding: 20px; }
      h1 { margin-bottom: 10px; }
      .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
      .card { border: 1px solid #ddd; border-radius: 8px; padding: 14px; }
      .muted { color: #666; font-size: 12px; }
      pre { background: #f7f7f7; padding: 8px; border-radius: 6px; overflow: auto; max-height: 200px; }
      .metric { font-size: 24px; font-weight: 600; margin: 8px 0; }
      .status { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
      .status.good { background: #d4edda; color: #155724; }
      .status.warning { background: #fff3cd; color: #856404; }
      .status.error { background: #f8d7da; color: #721c24; }
      @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  </head>
  <body>
    <h1>IDS Real‑Time Dashboard</h1>
  <div class="muted">Live metrics from ML predictions, Suricata alerts, and system performance (snapshot refresh every 2 seconds)</div>
  <div class="muted" style="margin-top:4px; font-size:11px;">Values reflect the latest window only. <!-- Use the cumulative toggle (coming soon) for rolling aggregates. --></div>
  <div id="updated" class="muted" style="margin-top:8px;"></div>

    <div class="grid" style="margin-top:16px; grid-template-columns: repeat(2, 1fr);">
      <div class="card">
        <h3>ML Predictions</h3>
        <canvas id="mlChart" height="120"></canvas>
        <div id="mlStats" class="muted"></div>
      </div>
      <div class="card">
        <h3>System Performance</h3>
        <div id="sysStats" class="muted"></div>
        <div class="muted">Processing Latency (p95)</div>
        <div id="latencyP95" class="metric">— ms</div>
        <div id="latencyStatus" class="status good" style="margin-top: 8px;">Normal</div>
      </div>
    </div>

    <div class="grid" style="margin-top:16px; grid-template-columns: repeat(2, 1fr);">
      <div class="card">
        <h3>Suricata Events</h3>
        <div id="eveStats" class="muted"></div>
        <div class="muted">Recent Events</div>
        <pre id="eveRecent"></pre>
      </div>
      <div class="card">
        <h3>Throughput</h3>
        <div id="throughputStats" class="muted"></div>
        <div class="muted">Events per Second</div>
        <div id="throughputRate" class="metric">—</div>
      </div>
    </div>

    <script>
      let mlChart;
      let lastUpdate = Date.now();

      async function refresh() {
        try {
          const res = await fetch('/api/summary');
          if (!res.ok) {
            console.error('API error:', res.status);
            document.getElementById('updated').textContent = 'Error: API returned ' + res.status;
            return;
          }
          const data = await res.json();
          lastUpdate = Date.now();
          document.getElementById('updated').textContent = 'Updated: ' + new Date(data.timestamp).toLocaleString();

          // ML stats
          const ml = data.ml || {};
          const total = ml.total || 0;
          const benign = ml.benign || 0;
          const attack = ml.attack || 0;
          const avgConf = (ml.avg_confidence || 0).toFixed(3);
          document.getElementById('mlStats').textContent = `Total: ${total} | Benign: ${benign} | Attack: ${attack} | Avg conf: ${avgConf}`;

          const ctx = document.getElementById('mlChart');
          const chartData = {
            labels: ['BENIGN', 'ATTACK'],
            datasets: [{
              label: 'Predictions',
              data: [benign, attack],
              backgroundColor: ['#2a9d8f', '#e76f51']
            }]
          };
          if (!mlChart) {
            mlChart = new Chart(ctx, {
              type: 'bar',
              data: chartData,
              options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
              }
            });
          } else {
            mlChart.data = chartData;
            mlChart.update();
          }

          // System + latency
          const sys = (data.metrics && data.metrics.system) || {};
          document.getElementById('sysStats').textContent =
            `CPU: ${(sys.cpu_percent||0).toFixed(1)}% | Mem: ${(sys.memory_percent||0).toFixed(1)}% (${(sys.memory_mb||0).toFixed(0)} MB)`;

          const lat = (data.metrics && data.metrics.latency) || {};
          const latencyValue = lat.p95_ms || 0;
          document.getElementById('latencyP95').textContent = latencyValue.toFixed(2) + ' ms';

          // Latency status indicator
          const latencyStatus = document.getElementById('latencyStatus');
          if (latencyValue > 100) {
            latencyStatus.textContent = 'High Latency';
            latencyStatus.className = 'status error';
          } else if (latencyValue > 50) {
            latencyStatus.textContent = 'Elevated';
            latencyStatus.className = 'status warning';
          } else {
            latencyStatus.textContent = 'Normal';
            latencyStatus.className = 'status good';
          }

          // Suricata Events
          const eve = data.suricata_events || {};
          const eveEvents = eve.events || [];
          document.getElementById('eveStats').textContent =
            `Events: ${eveEvents.length} | Alerts: ${eve.alerts||0} | Flows: ${eve.flows||0}`;
          const eveRecent = eveEvents.slice(-10).map(function(e) {
            return new Date(e.timestamp).toLocaleTimeString() + ' ' + e.type.toUpperCase() + ': ' + (e.src_ip||'') + ' → ' + (e.dest_ip||'') + ' ' + (e.signature||e.details||'');
          }).join('\n');
          document.getElementById('eveRecent').textContent = eveRecent;

          // Throughput
          const tp = (data.metrics && data.metrics.throughput) || {};
          const totalEvents = Object.values(tp).reduce((sum, val) => sum + val, 0);
          document.getElementById('throughputStats').textContent =
            Object.entries(tp).map(([k, v]) => `${k}: ${v}`).join(' | ') || 'No throughput data';
          document.getElementById('throughputRate').textContent = totalEvents + ' events';

        } catch (error) {
          console.error('Error in refresh():', error);
          document.getElementById('updated').textContent = 'Error: ' + error.message;

          // Show offline status if no updates for 30 seconds
          if (Date.now() - lastUpdate > 30000) {
            document.getElementById('latencyStatus').textContent = 'Offline';
            document.getElementById('latencyStatus').className = 'status error';
          }
        }
      }

      // Call refresh on page load and then every 2 seconds
      document.addEventListener('DOMContentLoaded', function() {
        refresh();
        setInterval(refresh, 2000);
      });
    </script>
  </body>
</html>
"""

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress normal logging, only log errors
        pass
    
    def do_GET(self):
        try:
            path = self.path.split('?', 1)[0]
            if path == '/' or path.startswith('/index.html'):
                body = INDEX_HTML.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path.startswith('/api/summary'):
                summary = build_summary()
                body = json.dumps(summary).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404)
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected, ignore
            pass
        except Exception:
            try:
                self.send_response(500)
                self.end_headers()
            except (BrokenPipeError, ConnectionResetError):
                pass

def run_server(host='0.0.0.0', port=5000):
    for p in [port] + list(range(5001, 5011)):
        try:
            httpd = HTTPServer((host, p), DashboardHandler)
            httpd.serve_forever()
            break
        except OSError:
            continue

def main():
    run_server()

if __name__ == '__main__':
    main()
