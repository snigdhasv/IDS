#!/usr/bin/env python3
"""Watch tcpreplay processes and mirror their PCAPs for ML streaming.

The daemon looks for tcpreplay invocations (manual CLI or helper scripts),
infers the PCAP path plus replay speed, and launches
pcap_pipeline_outputs.py in "realtime" mode so logs, metrics, and
predictions stream while traffic replays.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

STOP_EVENT = threading.Event()


def log(message: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


def handle_signal(signum, _frame) -> None:  # type: ignore[override]
    log(f"Signal {signum} received; shutting down tcpreplay monitor.")
    STOP_EVENT.set()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sim-script", required=True, help="Path to pcap_pipeline_outputs.py")
    parser.add_argument("--mode-state", required=True, help="Path to ml_mode_state.json")
    parser.add_argument("--accuracy", type=float, default=0.93, help="Simulator accuracy when mirroring runs")
    parser.add_argument("--startup-delay", type=float, default=1.0, help="Delay before simulator emits logs")
    parser.add_argument("--speed-factor", type=float, default=1.0, help="Timeline acceleration factor")
    parser.add_argument("--default-mbps", type=float, default=10.0, help="Fallback tcpreplay speed when not provided")
    parser.add_argument("--timeline-padding", type=float, default=0.05, help="Extra runtime padding (fraction)")
    parser.add_argument("--min-timeline", type=float, default=1.0, help="Minimum runtime seconds")
    parser.add_argument("--poll-interval", type=float, default=0.5, help="Seconds between /proc scans")
    parser.add_argument("--loop-padding", type=float, default=0.0, help="Additional timeline padding per tcpreplay loop")
    parser.add_argument("--silence-sim-output", action="store_true", help="Drop simulator stdout to keep logs compact")
    parser.add_argument(
        "--max-flows",
        type=int,
        default=2000,
        help="Limit simulator parsing to N flows for faster startup",
    )
    parser.add_argument(
        "--live-only",
        action="store_true",
        help="Run the simulator in eve-live-only mode instead of per-PCAP runs",
    )
    parser.add_argument(
        "--eve-json-path",
        help="Path to Suricata eve.json for live-only streaming",
    )
    parser.add_argument(
        "--eve-poll-interval",
        type=float,
        default=0.5,
        help="Poll interval to use when tailing eve.json in live-only mode",
    )
    return parser.parse_args()


@dataclass
class TcpreplayContext:
    pid: int
    args: List[str]
    cwd: Path


@dataclass
class ReplayConfig:
    sim_script: Path
    mode_state: Path
    accuracy: float
    startup_delay: float
    speed_factor: float
    default_mbps: float
    timeline_padding: float
    min_timeline: float
    loop_padding: float
    silence_sim_output: bool
    max_flows: int
    live_only: bool
    eve_json_path: Optional[Path]
    eve_poll_interval: float


def iter_tcpreplay_processes() -> Dict[int, TcpreplayContext]:
    processes: Dict[int, TcpreplayContext] = {}
    proc_root = Path("/proc")
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        cmdline_path = entry / "cmdline"
        try:
            raw = cmdline_path.read_bytes()
        except Exception:
            continue
        if not raw:
            continue
        parts = [part.decode(errors="ignore") for part in raw.split(b"\0") if part]
        if not parts:
            continue
        executable = Path(parts[0]).name.lower()
        if "tcpreplay" not in executable:
            continue
        # Skip helper invocations that may embed tcpreplay in their own path
        if any("tcpreplay_monitor" in part for part in parts):
            continue
        try:
            cwd_path = Path(os.readlink(entry / "cwd")).resolve()
        except Exception:
            cwd_path = Path.cwd()
        processes[pid] = TcpreplayContext(pid=pid, args=parts, cwd=cwd_path)
    return processes


def extract_numeric(tokens: List[str], names: Iterable[str], default: float) -> float:
    for name in names:
        for idx, token in enumerate(tokens):
            if token.startswith(f"{name}="):
                try:
                    return float(token.split("=", 1)[1])
                except ValueError:
                    continue
            if token == name and idx + 1 < len(tokens):
                try:
                    return float(tokens[idx + 1])
                except ValueError:
                    continue
    return default


def extract_int(tokens: List[str], names: Iterable[str], default: int) -> int:
    return int(extract_numeric(tokens, names, float(default)))


def resolve_pcap_paths(cmd_args: List[str], cwd: Path) -> List[Path]:
    paths: List[Path] = []
    for token in cmd_args[1:]:
        if not token:
            continue
        if token == "--":
            continue
        if token.startswith("-"):
            continue
        candidate = Path(token)
        if not candidate.is_absolute():
            candidate = (cwd / candidate).resolve()
        if candidate.is_file():
            paths.append(candidate)
    return paths


def compute_timeline_seconds(pcap_path: Path, mbps: float, loops: int, cfg: ReplayConfig) -> Optional[float]:
    try:
        size_bytes = pcap_path.stat().st_size
    except FileNotFoundError:
        return None
    if size_bytes <= 0 or mbps <= 0:
        return None
    runtime = (size_bytes * 8.0) / (mbps * 1_000_000.0)
    runtime *= max(1, loops)
    runtime *= 1.0 + cfg.timeline_padding + (cfg.loop_padding * max(0, loops - 1))
    return max(runtime, cfg.min_timeline)


def load_mode_state(path: Path) -> Tuple[str, Optional[Path]]:
    try:
        data = json.loads(path.read_text())
    except Exception:
        return "ensemble5", None
    mode = (data.get("mode") or "ensemble5").strip() or "ensemble5"
    gt_raw = data.get("ground_truth_csv")
    if gt_raw:
        gt_path = Path(gt_raw).expanduser()
        if gt_path.exists():
            return mode, gt_path
    return mode, None


def wait_for_pid_exit(pid: int) -> None:
    while not STOP_EVENT.is_set():
        proc_path = Path("/proc") / str(pid)
        if not proc_path.exists():
            break
        time.sleep(0.5)


def stream_process_output(prefix: str, proc: subprocess.Popen[str]) -> None:
    assert proc.stdout is not None
    for line in proc.stdout:
        log(f"{prefix} {line.rstrip()}")


def launch_simulator(
    cfg: ReplayConfig,
    pcap_path: Path,
    timeline_hint: Optional[float],
    tcpreplay_ctx: TcpreplayContext,
) -> None:
    mode, gt_csv = load_mode_state(cfg.mode_state)
    cmd = [
        sys.executable,
        str(cfg.sim_script),
        "--mode",
        mode,
        "--accuracy",
        f"{cfg.accuracy:.4f}",
        "--realtime",
        "--speed-factor",
        f"{cfg.speed_factor:.3f}",
        "--startup-delay",
        f"{cfg.startup_delay:.3f}",
    ]
    if cfg.live_only and cfg.eve_json_path is not None:
        cmd += [
            "--eve-json",
            str(cfg.eve_json_path),
            "--eve-live-only",
            "--eve-poll-interval",
            f"{cfg.eve_poll_interval:.3f}",
        ]
    else:
        cmd += ["--pcap", str(pcap_path)]
        if timeline_hint:
            cmd += ["--timeline-seconds", f"{timeline_hint:.3f}"]
        if gt_csv:
            cmd += ["--ground-truth-csv", str(gt_csv)]
    if cfg.max_flows > 0:
        cmd += ["--max-flows", str(cfg.max_flows)]

    target_desc = (
        f"live-eve:{cfg.eve_json_path}" if cfg.live_only and cfg.eve_json_path else pcap_path.name
    )
    log(
        f"Launching simulator for {target_desc} (tcpreplay pid={tcpreplay_ctx.pid}, mode={mode}, timeline={timeline_hint or 'auto'})"
    )

    stdout_pipe = subprocess.PIPE if not cfg.silence_sim_output else subprocess.DEVNULL
    proc = subprocess.Popen(
        cmd,
        stdout=stdout_pipe,
        stderr=subprocess.STDOUT if stdout_pipe is not subprocess.DEVNULL else subprocess.DEVNULL,
        text=True,
    )

    reader_thread: Optional[threading.Thread] = None
    if stdout_pipe is not subprocess.DEVNULL and proc.stdout is not None:
        reader_thread = threading.Thread(
            target=stream_process_output,
            args=(f"[sim:{pcap_path.name}]", proc),
            daemon=True,
        )
        reader_thread.start()

    wait_for_pid_exit(tcpreplay_ctx.pid)

    if STOP_EVENT.is_set() and proc.poll() is None:
        proc.terminate()

    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        log(f"Simulator still running for {pcap_path.name}; terminating after tcpreplay exit.")
        proc.terminate()
        proc.wait(timeout=5)

    if reader_thread:
        reader_thread.join(timeout=5)

    log(f"Simulator for {pcap_path.name} finished (return code {proc.returncode}).")


def monitor_loop(cfg: ReplayConfig, poll_interval: float) -> None:
    tracked: Dict[int, threading.Thread] = {}
    while not STOP_EVENT.is_set():
        active = iter_tcpreplay_processes()
        for pid, ctx in active.items():
            if pid in tracked:
                continue
            pcaps = resolve_pcap_paths(ctx.args, ctx.cwd)
            if not pcaps:
                log(f"Detected tcpreplay pid={pid} but no readable PCAP arguments; skipping.")
                continue
            pcap_path = pcaps[0]
            loops = extract_int(ctx.args, ["--loop", "-l"], 1)
            mbps = extract_numeric(ctx.args, ["--mbps", "-M"], cfg.default_mbps)
            timeline_hint = compute_timeline_seconds(pcap_path, mbps, loops, cfg)

            worker = threading.Thread(
                target=launch_simulator,
                args=(cfg, pcap_path, timeline_hint, ctx),
                daemon=True,
            )
            tracked[pid] = worker
            worker.start()

        # Clean up finished workers
        completed = [pid for pid, thread in tracked.items() if not thread.is_alive()]
        for pid in completed:
            tracked.pop(pid, None)

        STOP_EVENT.wait(poll_interval)

    log("Monitor loop exiting; waiting for outstanding simulations to finish.")
    for pid, thread in list(tracked.items()):
        thread.join(timeout=5)
        tracked.pop(pid, None)


def main() -> int:
    args = parse_args()
    sim_script = Path(args.sim_script).expanduser().resolve()
    mode_state = Path(args.mode_state).expanduser().resolve()
    if not sim_script.exists():
        log(f"Simulator script not found: {sim_script}")
        return 1
    if not mode_state.exists():
        log(f"Mode state file not found: {mode_state}")
        return 1

    eve_json_path: Optional[Path] = None
    if args.eve_json_path:
        eve_json_path = Path(args.eve_json_path).expanduser().resolve()
    if args.live_only and eve_json_path is None:
        log("Live-only mode requested but --eve-json-path was not provided; refusing to start.")
        return 1
    if args.live_only and eve_json_path and not eve_json_path.exists():
        log(f"Warning: eve.json not found at {eve_json_path}; simulator will wait for it at runtime.")

    cfg = ReplayConfig(
        sim_script=sim_script,
        mode_state=mode_state,
        accuracy=args.accuracy,
        startup_delay=args.startup_delay,
        speed_factor=args.speed_factor,
        default_mbps=args.default_mbps,
        timeline_padding=args.timeline_padding,
        min_timeline=args.min_timeline,
        loop_padding=args.loop_padding,
        silence_sim_output=args.silence_sim_output,
        max_flows=args.max_flows,
        live_only=args.live_only,
        eve_json_path=eve_json_path,
        eve_poll_interval=args.eve_poll_interval,
    )

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    log(
        "tcpreplay daemon ready (sim=%s, default speed %.2f Mbps)"
        % (sim_script.name, cfg.default_mbps)
    )
    try:
        monitor_loop(cfg, args.poll_interval)
    except KeyboardInterrupt:
        STOP_EVENT.set()
    log("tcpreplay daemon stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())