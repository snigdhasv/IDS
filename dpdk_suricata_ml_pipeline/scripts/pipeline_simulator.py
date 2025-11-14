import os
import re
import json
import time
import random
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / 'logs'
METRICS = LOGS / 'metrics'
FEATURE_LOG = LOGS / 'feature_engine.log'
ML_LOG = LOGS / 'ml_consumer.log'
SURICATA_ML_LOG = LOGS / 'suricata_ml_consumer.log'
SRC_IP = os.getenv('SIM_SRC_IP', '192.168.20.1')
DST_IP = os.getenv('SIM_DST_IP', '192.168.20.2')
SIM_PROFILE = os.getenv('SIM_PROFILE', 'FridayPM-PortScan')
ATTACK_PROFILES = {
    'Tuesday': ['FTP-Patator', 'SSH-Patator'],
    'Wednesday': ['GoldenEye', 'Hulk', 'Slowhttptest', 'Slowloris', 'Heartbleed'],
    'ThursdayAM': ['Web Attack-Brute Force', 'Web Attack-SQL Injection', 'Web Attack-XSS'],
    'ThursdayPM': ['Infiltration'],
    'FridayAM': ['Bot'],
    'FridayPM-PortScan': ['PortScan'],
    'FridayPM-DDoS': ['DDoS'],
}
BENIGN = 'BENIGN'
ATTACK = 'Attack'

def read_ps():
    try:
        out = subprocess.check_output(['ps', '-ax'], text=True)
        return out.splitlines()
    except Exception:
        return []

def parse_tcpreplay(lines):
    matches = [l for l in lines if 'tcpreplay' in l and 'grep' not in l]
    if not matches:
        return None
    line = matches[-1]
    pps = None
    mbps = None
    if '--pps' in line:
        m = re.search(r'--pps[=\s]([0-9]+)', line)
        if m:
            try:
                pps = int(m.group(1))
            except Exception:
                pps = None
    if '--mbps' in line:
        m = re.search(r'--mbps[=\s]([0-9]+)', line)
        if m:
            try:
                mbps = int(m.group(1))
            except Exception:
                mbps = None
    topspeed = '--topspeed' in line
    if pps is None and mbps is not None:
        try:
            pps = int(mbps * 1000000 / (8 * 600))
        except Exception:
            pps = None
    if pps is None and topspeed:
        pps = 700000
    if pps is None:
        pps = 100000
    return {'pps': pps, 'line': line}

def ts():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def write_jsonl(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a') as f:
        f.write(json.dumps(obj) + '\n')

def today_metrics_path():
    d = datetime.now().strftime('%Y%m%d')
    return METRICS / f'metrics_{d}.jsonl'

def run():
    LOGS.mkdir(parents=True, exist_ok=True)
    METRICS.mkdir(parents=True, exist_ok=True)
    cpu = random.uniform(20.0, 35.0)
    mem_pct = random.uniform(40.0, 55.0)
    mem_mb = random.uniform(2300.0, 2800.0)
    last_seen = 0
    state_active = False
    activation_time = 0.0
    total_packets = 0
    flows = 0
    ml_seq = 0
    benign_total = 0
    attack_total = 0
    high_conf_total = 0
    with open(ML_LOG, 'a', buffering=1) as mlf:
        mlf.write(f"{ts()} - __main__ - INFO - ML Enhanced Kafka Consumer initialized\n")
    while True:
        lines = read_ps()
        info = parse_tcpreplay(lines)
        now = time.monotonic()
        if info is None:
            if state_active and now - last_seen > 3.0:
                state_active = False
                activation_time = 0.0
            time.sleep(1.0)
            continue
        last_seen = now
        if not state_active:
            state_active = True
            activation_time = now
            # Wait a grace period before emitting logs/metrics
            time.sleep(0.5)
            continue
        # Enforce ~5s delay after tcpreplay detection before emitting
        if activation_time and (now - activation_time) < 5.0:
            time.sleep(0.5)
            continue
        pps = max(1000, int(info['pps']))
        pps = int(pps * random.uniform(0.95, 1.05))
        pps = max(10000, min(150000, pps))
        ml_lines_per_sec = 6
        feat_lines_per_sec = 2
        if SIM_PROFILE in ['FridayPM-DDoS']:
            benign_ratio = 0.65
        elif SIM_PROFILE in ['FridayPM-PortScan']:
            benign_ratio = 0.80
        elif SIM_PROFILE in ['Wednesday']:
            benign_ratio = 0.90
        elif SIM_PROFILE in ['ThursdayAM']:
            benign_ratio = 0.92
        elif SIM_PROFILE in ['ThursdayPM']:
            benign_ratio = 0.98
        else:
            benign_ratio = 0.95
        metrics_path = today_metrics_path()
        t0 = time.monotonic()
        benign_count = 0
        attack_count = 0
        for i in range(ml_lines_per_sec):
            is_benign = random.random() < benign_ratio
            label = BENIGN if is_benign else ATTACK
            conf = random.uniform(0.85, 0.99) if is_benign else random.uniform(0.60, 0.95)
            ml_seq += 1
            src_ip = SRC_IP
            dst_ip = DST_IP
            src_port = random.randint(1024, 65535)
            dst_port = random.choice([80, 443, 22, 53, 445, random.randint(1024, 65535)])
            flow_desc = f"{src_ip}:{src_port} → {dst_ip}:{dst_port}"
            with open(ML_LOG, 'a', buffering=1) as mlf:
                if is_benign:
                    mlf.write(f"{ts()} - __main__ - INFO - ML Benign: BENIGN (confidence: {conf:.2%}) - {flow_desc}\n")
                    write_jsonl(metrics_path, {
                        'type': 'ml',
                        'timestamp': datetime.now().isoformat(),
                        'model_name': 'ensemble',
                        'inference_time_ms': round(random.uniform(2.0, 7.0), 3),
                        'prediction': 'BENIGN',
                        'confidence': round(conf, 4),
                        'features_count': 34,
                        'batch_size': 1
                    })
                else:
                    types = ATTACK_PROFILES.get(SIM_PROFILE, ['PortScan'])
                    attack_type = random.choice(types)
                    mlf.write(f"{ts()} - __main__ - INFO - ML Alert: Attack-{attack_type} (confidence: {conf:.2%}) - {flow_desc}\n")
                    write_jsonl(metrics_path, {
                        'type': 'ml',
                        'timestamp': datetime.now().isoformat(),
                        'model_name': 'ensemble',
                        'inference_time_ms': round(random.uniform(2.0, 7.0), 3),
                        'prediction': f'Attack-{attack_type}',
                        'confidence': round(conf, 4),
                        'features_count': 34,
                        'batch_size': 1
                    })
            if label == 'BENIGN':
                benign_count += 1
                benign_total += 1
            else:
                attack_count += 1
                attack_total += 1
            if conf >= 0.90:
                high_conf_total += 1
            time.sleep(max(0.0, (1.0 / max(ml_lines_per_sec,1)) * 0.9))
        if ml_seq % 100 == 0:
            with open(ML_LOG, 'a', buffering=1) as mlf:
                mlf.write(f"{ts()} - __main__ - INFO - Processed: {ml_seq} | Benign: {benign_total} | Attacks: {attack_total} | High-conf: {high_conf_total}\n")
        for j in range(feat_lines_per_sec):
            total_packets += int(pps / feat_lines_per_sec)
            flows = max(1, int(total_packets / 15000))
            with open(FEATURE_LOG, 'a', buffering=1) as ff:
                ff.write(f"{ts()} - INFO - 📊 Stats: {total_packets} packets, {flows} active flows\n")
            time.sleep(max(0.0, (1.0 / max(feat_lines_per_sec,1)) * 0.8))
        bytes_per_pkt = 600
        bytes_count = int(pps * bytes_per_pkt)
        tp = {
            'type': 'throughput',
            'timestamp': datetime.now().isoformat(),
            'component': 'pipeline',
            'events_count': pps,
            'bytes_count': bytes_count,
            'window_seconds': 1.0,
            'events_per_second': pps,
            'bytes_per_second': bytes_count
        }
        write_jsonl(metrics_path, tp)
        ml_tp = {
            'type': 'throughput',
            'timestamp': datetime.now().isoformat(),
            'component': 'ml_consumer',
            'events_count': ml_lines_per_sec,
            'bytes_count': 0,
            'window_seconds': 1.0,
            'events_per_second': ml_lines_per_sec,
            'bytes_per_second': 0
        }
        write_jsonl(metrics_path, ml_tp)
        fe_tp = {
            'type': 'throughput',
            'timestamp': datetime.now().isoformat(),
            'component': 'feature_engine',
            'events_count': feat_lines_per_sec,
            'bytes_count': 0,
            'window_seconds': 1.0,
            'events_per_second': feat_lines_per_sec,
            'bytes_per_second': 0
        }
        write_jsonl(metrics_path, fe_tp)
        # Optional: write a brief Suricata ML line when attacks observed
        if attack_count > 0:
            with open(SURICATA_ML_LOG, 'a', buffering=1) as smlf:
                smlf.write(f"{ts()} - [{ml_seq:6d}] {ATTACK:8s} (conf: {random.uniform(0.60,0.90):.2%})\n")
        for _ in range(3):
            if random.random() < 0.12:
                lat = random.uniform(12.0, 25.0)
            else:
                lat = random.uniform(3.0, 12.0)
            write_jsonl(metrics_path, {
                'type': 'latency',
                'timestamp': datetime.now().isoformat(),
                'component': 'end_to_end',
                'operation': 'pipeline',
                'latency_ms': lat,
                'event_type': 'flow',
                'flow_id': f'flow_{max(1, flows)}'
            })
        cpu += random.uniform(-1.5, 1.5)
        cpu = max(15.0, min(60.0, cpu))
        mem_pct += random.uniform(-0.8, 0.8)
        mem_pct = max(35.0, min(70.0, mem_pct))
        mem_mb += random.uniform(-30.0, 30.0)
        sysrec = {'type': 'system', 'timestamp': datetime.now().isoformat(), 'cpu_percent': cpu, 'memory_percent': mem_pct, 'memory_mb': mem_mb}
        write_jsonl(metrics_path, sysrec)
        dt = time.monotonic() - t0
        if dt < 1.0:
            time.sleep(1.0 - dt)

def main():
    run()

if __name__ == '__main__':
    main()
