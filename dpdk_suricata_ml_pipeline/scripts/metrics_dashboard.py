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

ROOT_DIR = Path(__file__).resolve().parents[2]
LOGS_DIR = ROOT_DIR / 'logs'
METRICS_DIR = LOGS_DIR / 'metrics'
ML_LOG = LOGS_DIR / 'ml_consumer.log'
SURICATA_ML_LOG = LOGS_DIR / 'suricata_ml_consumer.log'
FEATURE_LOG = LOGS_DIR / 'feature_engine.log'
SURICATA_LOG = Path('/var/log/suricata/suricata.log')
ALT_SURICATA_LOG = LOGS_DIR / 'suricata.log'

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
    # Support both "conf: 0.987" and "confidence: 98.7%" formats
    pat_decimal = re.compile(r"(BENIGN|Attack|ATTACK).*conf:\s*([0-9.]+)", re.IGNORECASE)
    pat_percent = re.compile(r"(BENIGN|Attack|ATTACK).*confidence:\s*([0-9.]+)%", re.IGNORECASE)
    for line in lines[-400:]:
        line_u = line.strip()
        m = pat_percent.search(line_u)
        if m:
            label = m.group(1).upper()
            conf = float(m.group(2)) / 100.0
        else:
            m = pat_decimal.search(line_u)
            if not m:
                # Try to infer label without patterns
                if 'BENIGN' in line_u.upper():
                    label = 'BENIGN'
                elif 'ATTACK' in line_u.upper():
                    label = 'ATTACK'
                else:
                    continue
                conf = 0.0
            else:
                label = m.group(1).upper()
                conf = float(m.group(2)) if m.group(2) else 0.0
        total += 1
        if label.startswith('BENIGN'):
            benign += 1
        else:
            attack += 1
        confidences.append(conf)
        recent.append({'ts': line_u.split(' - ')[0], 'label': label, 'confidence': conf})
    avg_conf = sum(confidences)/len(confidences) if confidences else 0.0
    return {'total': total, 'benign': benign, 'attack': attack, 'avg_confidence': avg_conf, 'recent': recent[-20:]}

def _parse_suricata_log(lines):
    alerts = 0
    recent = []
    for line in lines[-500:]:
        if 'Alert' in line or 'ALERT' in line:
            alerts += 1
            recent.append(line.strip()[:180])
    return {'alerts': alerts, 'recent': recent[-20:]}

def _parse_metrics_jsonl():
    try:
        today = datetime.now().strftime('%Y%m%d')
        jf = METRICS_DIR / f'metrics_{today}.jsonl'
        if not jf.exists():
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
    if SURICATA_LOG.exists():
        suri_summary = _parse_suricata_log(_tail_lines(SURICATA_LOG, 2000))
    elif ALT_SURICATA_LOG.exists():
        suri_summary = _parse_suricata_log(_tail_lines(ALT_SURICATA_LOG, 2000))
    else:
        suri_summary = {}
    suri_ml_summary = _parse_ml_log(_tail_lines(SURICATA_ML_LOG, 2000)) if SURICATA_ML_LOG.exists() else {}
    metrics_structured = _parse_metrics_jsonl()
    feature_lines = _tail_lines(FEATURE_LOG, 500)
    features_processed = len(feature_lines)
    return {
        'timestamp': datetime.now().isoformat(),
        'ml': ml_summary,
        'suricata_alerts': suri_summary,
        'suricata_ml': suri_ml_summary,
        'metrics': metrics_structured,
        'feature_engine': {'recent_lines': feature_lines[-10:], 'approx_events': features_processed}
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
      pre { background: #f7f7f7; padding: 8px; border-radius: 6px; overflow: auto; }
      @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
    </style>
    <!-- Chart.js optional; page works without it -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  </head>
  <body>
    <h1>IDS Real‑Time Dashboard</h1>
    <div class="muted">Live metrics from ML predictions, Suricata alerts, and feature engine</div>
    <div id="updated" class="muted" style="margin-top:8px;"></div>
    <div class="grid" style="margin-top:16px;">
      <div class="card">
        <h3>ML Predictions</h3>
        <canvas id="mlChart" height="120"></canvas>
        <div id="mlStats" class="muted"></div>
      </div>
      <div class="card">
        <h3>Suricata Alerts</h3>
        <div id="suriCount" style="font-size:24px; font-weight:600;">—</div>
        <div class="muted">Recent Alerts</div>
        <pre id="suriRecent"></pre>
      </div>
      <div class="card">
        <h3>System</h3>
        <div id="sysStats" class="muted"></div>
        <div class="muted">Latency (p95)</div>
        <div id="latencyP95" style="font-size:20px; font-weight:600;">— ms</div>
      </div>
    </div>

    <div class="grid" style="margin-top:16px;">
      <div class="card">
        <h3>Feature Engine</h3>
        <div id="featCount" style="font-size:24px; font-weight:600;">—</div>
        <div class="muted">Recent Lines</div>
        <pre id="featRecent"></pre>
      </div>
      <div class="card">
        <h3>Suricata ML Consumer</h3>
        <div id="suriMlStats" class="muted"></div>
      </div>
      <div class="card">
        <h3>Kafka Throughput</h3>
        <pre id="throughput"></pre>
      </div>
    </div>

    <script>
      var mlChart;
      function refresh() {
        try {
          var xhr = new XMLHttpRequest();
          xhr.open('GET', '/api/summary', true);
          xhr.setRequestHeader('Cache-Control', 'no-cache');
          xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
              if (xhr.status !== 200) {
                console && console.error && console.error('API error', xhr.status);
                return;
              }
              var data;
              try {
                data = JSON.parse(xhr.responseText);
              } catch (e) {
                console && console.error && console.error('JSON parse error', e);
                return;
              }
              document.getElementById('updated').textContent = 'Updated: ' + new Date(data.timestamp).toLocaleString();
              var ml = data.ml || {};
              var total = ml.total || 0;
              var benign = ml.benign || 0;
              var attack = ml.attack || 0;
              var avgConf = (ml.avg_confidence || 0).toFixed ? (ml.avg_confidence || 0).toFixed(3) : (ml.avg_confidence || 0);
              document.getElementById('mlStats').textContent = 'Total: ' + total + ' | Benign: ' + benign + ' | Attack: ' + attack + ' | Avg conf: ' + avgConf;
              var ctx = document.getElementById('mlChart');
              var chartData = {labels: ['BENIGN', 'ATTACK'], datasets: [{label: 'Predictions', data: [benign, attack], backgroundColor: ['#2a9d8f', '#e76f51']}]};
              if (window.Chart) {
                if (!mlChart) {
                  mlChart = new Chart(ctx, { type: 'bar', data: chartData, options: { responsive: true, plugins: { legend: { display: false }}}});
                } else {
                  mlChart.data = chartData; mlChart.update();
                }
              }
              var suri = data.suricata_alerts || {};
              document.getElementById('suriCount').textContent = suri.alerts || 0;
              document.getElementById('suriRecent').textContent = (suri.recent || []).join('\n');
              var sys = (data.metrics && data.metrics.system) || {};
              var cpu = sys.cpu_percent || 0;
              var memp = sys.memory_percent || 0;
              var memb = sys.memory_mb || 0;
              document.getElementById('sysStats').textContent = 'CPU: ' + (cpu.toFixed ? cpu.toFixed(1) : cpu) + '% | Mem: ' + (memp.toFixed ? memp.toFixed(1) : memp) + '% (' + (memb.toFixed ? memb.toFixed(0) : memb) + ' MB)';
              var lat = (data.metrics && data.metrics.latency) || {};
              var p95 = lat.p95_ms || 0;
              document.getElementById('latencyP95').textContent = (p95.toFixed ? p95.toFixed(2) : p95) + ' ms';
              var feat = data.feature_engine || {};
              document.getElementById('featCount').textContent = feat.approx_events || 0;
              document.getElementById('featRecent').textContent = (feat.recent_lines || []).join('');
              var sml = data.suricata_ml || {};
              document.getElementById('suriMlStats').textContent = 'Total: ' + (sml.total||0) + ' | Attack: ' + (sml.attack||0) + ' | Benign: ' + (sml.benign||0);
              var tp = (data.metrics && data.metrics.throughput) || {};
              document.getElementById('throughput').textContent = JSON.stringify(tp, null, 2);
            }
          };
          xhr.send();
        } catch (e) {
          console && console.error && console.error('Refresh failed', e);
        }
      }
      refresh();
      setInterval(refresh, 2000);
    </script>
  </body>
</html>
"""

class DashboardHandler(BaseHTTPRequestHandler):
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
        except Exception:
            self.send_response(500)
            self.end_headers()

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
