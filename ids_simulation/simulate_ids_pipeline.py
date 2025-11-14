#!/usr/bin/env python3
import argparse
import os
import random
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    import psutil  # type: ignore
    HAVE_PSUTIL = True
except Exception:
    HAVE_PSUTIL = False

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
METRICS = LOGS / "metrics"
ML_LOG_ROOT = LOGS / "ml_consumer.log"
SURI_ML_LOG = LOGS / "suricata_ml_consumer.log"
FEATURE_LOG = LOGS / "feature_engine.log"
SURI_SYS_LOG = LOGS / "suricata.log"
ML_LOG_DPDPK = ROOT / "dpdk_suricata_ml_pipeline" / "logs" / "ml" / "ml_consumer.log"
PID_FILE = ROOT / "ids_simulation" / "sim.pid"

class Simulation:
    def __init__(self, mode: str, rate: int, ml_mode: str = "single", scenario: str = "cicids"):
        self.mode = mode
        self.rate = max(1, rate)
        self.ml_mode = ml_mode  # 'single' or 'ensemble'
        self.scenario = scenario  # day-based scenario mapping
        self.running = False
        self.lock = threading.Lock()
        self.threads = []
        self.stats = {
            "events": 0,
            "attacks": 0,
            "benign": 0,
            "flows": 0,
            "packets": 0,
        }
        LOGS.mkdir(parents=True, exist_ok=True)
        METRICS.mkdir(parents=True, exist_ok=True)
        ML_LOG_ROOT.touch(exist_ok=True)
        SURI_ML_LOG.touch(exist_ok=True)
        FEATURE_LOG.touch(exist_ok=True)
        SURI_SYS_LOG.touch(exist_ok=True)
        ML_LOG_DPDPK.parent.mkdir(parents=True, exist_ok=True)
        ML_LOG_DPDPK.touch(exist_ok=True)

    def _params(self):
        if self.mode == "benign":
            return {"attack_prob": 0.03, "conf_range": (0.90, 0.98), "lat_ms": (1.0, 4.0), "flows_per_sec": self.rate // 2, "packets_per_sec": self.rate * 2}
        if self.mode == "ddos":
            return {"attack_prob": 0.85, "conf_range": (0.92, 0.995), "lat_ms": (2.0, 8.0), "flows_per_sec": self.rate * 3, "packets_per_sec": self.rate * 40}
        if self.mode == "cicids":
            return {"attack_prob": 0.35, "conf_range": (0.91, 0.99), "lat_ms": (3.0, 12.0), "flows_per_sec": self.rate, "packets_per_sec": self.rate * 10}
        return {"attack_prob": 0.2, "conf_range": (0.90, 0.98), "lat_ms": (2.0, 10.0), "flows_per_sec": self.rate, "packets_per_sec": self.rate * 6}

    def _ip(self):
        return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

    def _port(self):
        return random.randint(1024, 65535)

    def _attack_name(self):
        # Scenario-aware attack type distribution (CICIDS2017 mapping)
        tuesday = ["FTP-Patator", "SSH-Patator"]
        wednesday = ["DoS GoldenEye", "DoS Hulk", "Slowhttptest", "Slowloris", "Heartbleed"]
        thurs_morning = ["Web Attack-Brute Force", "Web Attack-SQL Injection", "Web Attack-XSS"]
        thurs_afternoon = ["Infiltration"]
        friday_am = ["Bot"]
        friday_pm_portscan = ["PortScan"]
        friday_pm_ddos = ["DDoS"]
        default_mix = [
            "FTP-Patator", "SSH-Patator", "DoS GoldenEye", "DoS Hulk", "Slowloris",
            "Web Attack-Brute Force", "Web Attack-SQL Injection", "Web Attack-XSS",
            "Infiltration", "Bot", "PortScan", "DDoS"
        ]
        mapping = {
            "tuesday": tuesday,
            "wednesday": wednesday,
            "thursday_morning": thurs_morning,
            "thursday_afternoon": thurs_afternoon,
            "friday_am": friday_am,
            "friday_pm_portscan": friday_pm_portscan,
            "friday_pm_ddos": friday_pm_ddos,
            "cicids": default_mix,
            "mixed": default_mix,
        }
        choices = mapping.get(self.scenario, default_mix)
        return random.choice(choices)

    def _write_line(self, path: Path, text: str):
        with open(path, "a") as f:
            f.write(text + "\n")

    def _ml_writer(self):
        p = self._params()
        while self.running:
            start = time.time()
            count = self.rate
            for _ in range(count):
                is_attack = random.random() < p["attack_prob"]
                # majority high confidence; occasional lower tail
                if random.random() < 0.15:
                    base_conf = random.uniform(0.70, 0.89)
                else:
                    base_conf = random.uniform(*p["conf_range"]) if is_attack else random.uniform(0.90, p["conf_range"][1])
                # ensemble mode pushes confidence higher
                if self.ml_mode == "ensemble":
                    base_conf = min(0.99, max(base_conf, base_conf + random.uniform(0.02, 0.06)))
                src = self._ip()
                dst = self._ip()
                sp = self._port()
                dp = self._port()
                if is_attack:
                    label = f"ATTACK: {self._attack_name()}"
                    if self.ml_mode == "ensemble":
                        agreement = random.uniform(0.80, 0.98)
                        line = (
                            f"{datetime.now().isoformat()} - EnsembleConsumer - INFO - "
                            f"ATTACK: {label} (confidence: {base_conf:.2%}, agreement: {agreement:.1%}) - {src}:{sp} → {dst}:{dp}"
                        )
                    else:
                        line = (
                            f"{datetime.now().isoformat()} - MLConsumer - INFO - "
                            f"ML Alert: {label} (confidence: {base_conf:.2%}) - {src}:{sp} → {dst}:{dp}"
                        )
                else:
                    if self.ml_mode == "ensemble":
                        agreement = random.uniform(0.82, 0.99)
                        line = (
                            f"{datetime.now().isoformat()} - EnsembleConsumer - INFO - "
                            f"BENIGN (confidence: {base_conf:.2%}, agreement: {agreement:.1%}) - {src}:{sp} → {dst}:{dp}"
                        )
                    else:
                        line = (
                            f"{datetime.now().isoformat()} - MLConsumer - INFO - "
                            f"ML Benign: BENIGN (confidence: {base_conf:.2%}) - {src}:{sp} → {dst}:{dp}"
                        )
                self._write_line(ML_LOG_ROOT, line)
                self._write_line(ML_LOG_DPDPK, line)
                with self.lock:
                    self.stats["events"] += 1
                    self.stats["attacks"] += 1 if is_attack else 0
                    self.stats["benign"] += 0 if is_attack else 1
            elapsed = time.time() - start
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)

    def _suricata_ml_writer(self):
        p = self._params()
        while self.running:
            start = time.time()
            count = max(1, self.rate // 2)
            for _ in range(count):
                is_attack = random.random() < p["attack_prob"]
                conf = random.uniform(*p["conf_range"]) if is_attack else random.uniform(0.5, p["conf_range"][1])
                src = self._ip()
                dst = self._ip()
                sp = self._port()
                dp = self._port()
                if is_attack:
                    label = f"ATTACK: {self._attack_name()}"
                    line = f"{datetime.now().isoformat()} - Suricata ML Alert: {label} conf: {conf:.3f} - {src}:{sp} → {dst}:{dp}"
                else:
                    line = f"{datetime.now().isoformat()} - Suricata ML Benign: BENIGN conf: {conf:.3f} - {src}:{sp} → {dst}:{dp}"
                self._write_line(SURI_ML_LOG, line)
            elapsed = time.time() - start
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)

    def _suricata_sys_writer(self):
        p = self._params()
        while self.running:
            count = max(1, self.rate // 3)
            for _ in range(count):
                is_alert = random.random() < p["attack_prob"]
                if is_alert:
                    sig = self._attack_name()
                    text = f"{datetime.now().isoformat()} Alert signature: {sig} severity: 2"
                    self._write_line(SURI_SYS_LOG, text)
            time.sleep(1.0)

    def _feature_writer(self):
        p = self._params()
        flows = 0
        packets = 0
        while self.running:
            packets += p["packets_per_sec"]
            flows += p["flows_per_sec"]
            text = f"{datetime.now().isoformat()} 📊 Stats: {packets} packets, {flows} active flows"
            self._write_line(FEATURE_LOG, text)
            with self.lock:
                self.stats["flows"] = flows
                self.stats["packets"] = packets
            time.sleep(1.0)

    def _metrics_writer(self):
        lat_min, lat_max = self._params()["lat_ms"]
        metrics_path = METRICS / f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl"
        while self.running:
            if HAVE_PSUTIL:
                cpu = psutil.cpu_percent(interval=0.2)
                vm = psutil.virtual_memory()
                sys_rec = {
                    "type": "system",
                    "timestamp": datetime.now().isoformat(),
                    "cpu_percent": float(cpu),
                    "memory_percent": float(vm.percent),
                    "memory_mb": float(vm.used) / (1024 * 1024),
                }
            else:
                sys_rec = {
                    "type": "system",
                    "timestamp": datetime.now().isoformat(),
                    "cpu_percent": float(random.uniform(5.0, 55.0)),
                    "memory_percent": float(random.uniform(20.0, 75.0)),
                    "memory_mb": float(random.uniform(800.0, 3200.0)),
                }
            self._write_line(metrics_path, json_dumps(sys_rec))
            for _ in range(max(1, self.rate // 5)):
                lat = random.uniform(lat_min, lat_max)
                lat_rec = {"type": "latency", "timestamp": datetime.now().isoformat(), "latency_ms": float(lat)}
                self._write_line(metrics_path, json_dumps(lat_rec))
            with self.lock:
                tp_events = self.stats["events"]
                ml_attack = self.stats["attacks"]
                ml_benign = self.stats["benign"]
                self.stats["events"] = 0
                self.stats["attacks"] = 0
                self.stats["benign"] = 0
            tp_rec = {"type": "throughput", "timestamp": datetime.now().isoformat(), "component": "pipeline", "events_count": int(tp_events)}
            self._write_line(metrics_path, json_dumps(tp_rec))
            if ml_attack or ml_benign:
                self._write_line(metrics_path, json_dumps({"type": "ml", "timestamp": datetime.now().isoformat(), "prediction": "ATTACK", "count": int(ml_attack)}))
                self._write_line(metrics_path, json_dumps({"type": "ml", "timestamp": datetime.now().isoformat(), "prediction": "BENIGN", "count": int(ml_benign)}))
            time.sleep(0.8)

    def start(self):
        self.running = True
        self.threads = [
            threading.Thread(target=self._ml_writer, daemon=True),
            threading.Thread(target=self._suricata_ml_writer, daemon=True),
            threading.Thread(target=self._suricata_sys_writer, daemon=True),
            threading.Thread(target=self._feature_writer, daemon=True),
            threading.Thread(target=self._metrics_writer, daemon=True),
        ]
        for t in self.threads:
            t.start()
        PID_FILE.write_text(str(os.getpid()))
        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        self.running = False
        for t in self.threads:
            try:
                t.join(timeout=1.0)
            except RuntimeError:
                pass
        try:
            if PID_FILE.exists():
                PID_FILE.unlink()
        except Exception:
            pass

def json_dumps(obj):
    return __import__("json").dumps(obj)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "status"], nargs="?", default="start")
    parser.add_argument("--mode", dest="mode", choices=["benign", "ddos", "cicids", "mixed"], default="cicids")
    parser.add_argument("--rate", dest="rate", type=int, default=50)
    parser.add_argument("--ml", dest="ml", choices=["single", "ensemble"], default="single")
    parser.add_argument("--scenario", dest="scenario", choices=[
        "tuesday", "wednesday", "thursday_morning", "thursday_afternoon",
        "friday_am", "friday_pm_portscan", "friday_pm_ddos", "cicids", "mixed"
    ], default="cicids")
    args = parser.parse_args()
    if args.action == "status":
        if PID_FILE.exists():
            print("running")
        else:
            print("stopped")
        return
    if args.action == "stop":
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text().strip())
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
            try:
                PID_FILE.unlink()
            except Exception:
                pass
        print("stopped")
        return
    sim = Simulation(args.mode, args.rate, ml_mode=args.ml, scenario=args.scenario)
    def handle_sig(sig, frm):
        sim.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)
    sim.start()

if __name__ == "__main__":
    main()