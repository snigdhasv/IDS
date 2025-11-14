#!/usr/bin/env python3
import json
import re
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parents[2]
LOGS_DIR = ROOT_DIR / 'logs'
METRICS_DIR = LOGS_DIR / 'metrics'
ML_LOG = LOGS_DIR / 'ml_consumer.log'
FEATURE_LOG = LOGS_DIR / 'feature_engine.log'
SURICATA_LOG = Path('/var/log/suricata/suricata.log')
ALT_SURICATA_LOG = LOGS_DIR / 'suricata.log'
PORT_FILE = LOGS_DIR / 'metrics_dashboard.port'

def tail_lines(path: Path, max_lines: int = 500):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.readlines()[-max_lines:]
    except Exception:
        return []

def parse_ml_log(lines):
    total = 0
    benign = 0
    attack = 0
    recent = []
    pat_benign = re.compile(r"ML\s+Benign:\s+BENIGN\s+\(confidence:\s*([0-9.]+)%\)")
    pat_attack = re.compile(r"ML\s+Alert:\s+Attack[-:]?([\w-]+)?\s*\(confidence:\s*([0-9.]+)%\)")
    for line in lines[-400:]:
        u = line.strip()
        m1 = pat_benign.search(u)
        m2 = pat_attack.search(u)
        if m1:
            total += 1
            benign += 1
            conf = float(m1.group(1)) / 100.0
            recent.append({
                'ts': u.split(' - ')[0],
                'label': 'BENIGN',
                'confidence': conf
            })
        elif m2:
            total += 1
            attack += 1
            conf = float(m2.group(2)) / 100.0
            label = 'ATTACK'
            recent.append({
                'ts': u.split(' - ')[0],
                'label': label,
                'confidence': conf,
                'type': m2.group(1) or 'UNKNOWN'
            })
    avg_conf = 0.0
    if recent:
        avg_conf = sum(r.get('confidence', 0.0) for r in recent) / len(recent)
    return {'total': total, 'benign': benign, 'attack': attack, 'avg_confidence': avg_conf, 'recent': recent[-20:]}

def parse_suricata_log(lines):
    alerts = 0
    recent = []
    for line in lines[-500:]:
        if 'Alert signature:' in line:
            alerts += 1
            recent.append(line.strip()[:180])
    return {'alerts': alerts, 'recent': recent[-20:]}

def parse_metrics_jsonl():
    today = datetime.now().strftime('%Y%m%d')
    jf = METRICS_DIR / f'metrics_{today}.jsonl'
    if not jf.exists():
        return {}
    latencies = []
    ml_preds = {}
    throughput = {}
    system = {}
    try:
        with open(jf, 'r', encoding='utf-8', errors='ignore') as f:
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
    except Exception:
        pass
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

def build_summary():
    ml_summary = parse_ml_log(tail_lines(ML_LOG, 2000)) if ML_LOG.exists() else {}
    if SURICATA_LOG.exists():
        suri_summary = parse_suricata_log(tail_lines(SURICATA_LOG, 2000))
    elif ALT_SURICATA_LOG.exists():
        suri_summary = parse_suricata_log(tail_lines(ALT_SURICATA_LOG, 2000))
    else:
        suri_summary = {}
    metrics_structured = parse_metrics_jsonl()
    feature_lines = tail_lines(FEATURE_LOG, 500)
    # escape lines to avoid invalid tokens in the client
    safe_lines = [html.escape(l) for l in feature_lines[-10:]]
    health = {
        'ml_consumer.log': ML_LOG.exists(),
        'feature_engine.log': FEATURE_LOG.exists(),
        'metrics_jsonl': (METRICS_DIR / f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl").exists(),
        'suricata': SURICATA_LOG.exists() or ALT_SURICATA_LOG.exists(),
    }
    return {
        'timestamp': datetime.now().isoformat(),
        'ml': ml_summary,
        'suricata_alerts': suri_summary,
        'metrics': metrics_structured,
        'feature_engine': {'recent_lines': safe_lines, 'approx_events': len(feature_lines)},
        'health': health,
    }

INDEX_HTML = """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>IDS Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      body { font-family: -apple-system, system-ui, Segoe UI, Roboto, Helvetica, Arial, sans-serif; padding: 20px; }
      h1 { margin-bottom: 10px; }
      .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
      .card { border: 1px solid #ddd; border-radius: 8px; padding: 14px; }
      .muted { color: #666; font-size: 12px; }
      pre { background: #f7f7f7; padding: 8px; border-radius: 6px; overflow: auto; }
      @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
    </style>
  </head>
  <body>
    <h1>IDS Real‑Time Dashboard</h1>
    <div class="muted">Live metrics from ML predictions, Suricata alerts, and feature engine</div>
    <div id="updated" class="muted" style="margin-top:8px;"></div>
    <div id="health" class="muted" style="margin-top:4px;"></div>
    <div class="grid" style="margin-top:16px;">
      <div class="card">
        <h3>ML Predictions</h3>
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
        <h3>Kafka Throughput</h3>
        <pre id="throughput"></pre>
      </div>
      <div class="card">
        <h3>Replay Status</h3>
        <div id="status" class="muted">Waiting for replay (grace ~5s)…</div>
      </div>
    </div>

    <script>
      function esc(s){return (s||'').toString();}
      function refresh(){
        try{
          var xhr=new XMLHttpRequest();
          xhr.open('GET','/api/summary',true);
          xhr.setRequestHeader('Cache-Control','no-cache');
          xhr.onreadystatechange=function(){
            if(xhr.readyState===4){
              if(xhr.status!==200){return;}
              var data; try{data=JSON.parse(xhr.responseText);}catch(e){return;}
              document.getElementById('updated').textContent='Updated: '+new Date(data.timestamp).toLocaleString();
              var ml=data.ml||{}; var total=ml.total||0; var benign=ml.benign||0; var attack=ml.attack||0; var avg=ml.avg_confidence||0;
              document.getElementById('mlStats').textContent='Total: '+total+' | Benign: '+benign+' | Attack: '+attack+' | Avg conf: '+(avg.toFixed?avg.toFixed(3):avg);
              var suri=data.suricata_alerts||{}; document.getElementById('suriCount').textContent=suri.alerts||0; document.getElementById('suriRecent').textContent=(suri.recent||[]).join('\n');
              var sys=(data.metrics&&data.metrics.system)||{}; var cpu=sys.cpu_percent||0; var memp=sys.memory_percent||0; var memb=sys.memory_mb||0;
              document.getElementById('sysStats').textContent='CPU: '+(cpu.toFixed?cpu.toFixed(1):cpu)+'% | Mem: '+(memp.toFixed?memp.toFixed(1):memp)+'% ('+(memb.toFixed?memb.toFixed(0):memb)+' MB)';
              var lat=(data.metrics&&data.metrics.latency)||{}; var p95=lat.p95_ms||0; document.getElementById('latencyP95').textContent=(p95.toFixed?p95.toFixed(2):p95)+' ms';
              var feat=data.feature_engine||{}; document.getElementById('featCount').textContent=feat.approx_events||0; document.getElementById('featRecent').innerHTML=(feat.recent_lines||[]).join('');
              var tp=(data.metrics&&data.metrics.throughput)||{}; document.getElementById('throughput').textContent=JSON.stringify(tp,null,2);
              var h=data.health||{}; document.getElementById('health').textContent='Sources: ml_consumer.log '+(h['ml_consumer.log']?'OK':'—')+', feature_engine.log '+(h['feature_engine.log']?'OK':'—')+', metrics '+(h['metrics_jsonl']?'OK':'—')+', suricata '+(h['suricata']?'OK':'—');
              document.getElementById('status').textContent = total>0 ? 'Replay detected, streaming' : 'Waiting for replay…';
            }
          }; xhr.send();
        }catch(e){}
      }
      refresh(); setInterval(refresh,2000);
    </script>
  </body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
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
            if path.startswith('/api/health'):
                today = datetime.now().strftime('%Y%m%d')
                status = {
                    'ml_consumer.log': ML_LOG.exists(),
                    'feature_engine.log': FEATURE_LOG.exists(),
                    f'metrics_{today}.jsonl': (METRICS_DIR / f'metrics_{today}.jsonl').exists(),
                    'suricata': SURICATA_LOG.exists() or ALT_SURICATA_LOG.exists(),
                }
                body = json.dumps({'status': status}).encode('utf-8')
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

def run_server(host='0.0.0.0', ports=None):
    if ports is None:
        ports = list(range(5500, 5511))
    for p in ports:
        try:
            httpd = HTTPServer((host, p), Handler)
            try:
                LOGS_DIR.mkdir(parents=True, exist_ok=True)
                PORT_FILE.write_text(f"http://localhost:{p}\n", encoding='utf-8')
            except Exception:
                pass
            httpd.serve_forever()
            break
        except OSError:
            continue

def main():
    run_server()

if __name__ == '__main__':
    main()

