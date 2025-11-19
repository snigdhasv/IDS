#!/usr/bin/env python3
"""
Read Suricata /var/log/suricata/eve.json and write alert events to CSV.
Usage examples:
  - one-shot convert: sudo python3 eve_alerts_to_csv.py --input /var/log/suricata/eve.json --output ./suricata_alerts.csv
  - follow new entries (like tail -f): sudo python3 eve_alerts_to_csv.py --follow
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import signal
import sys
import time
from typing import Dict, Optional

DEFAULT_INPUT = "/var/log/suricata/eve.json"
DEFAULT_OUTPUT = "./suricata_alerts.csv"

FIELDNAMES = [
    "timestamp",
    "flow_id",
    "in_iface",
    "event_type",
    "src_ip",
    "src_port",
    "dest_ip",
    "dest_port",
    "proto",
    "pkt_src",
    "direction",
    # alert fields
    "alert_gid",
    "alert_signature_id",
    "alert_rev",
    "alert_signature",
    "alert_category",
    "alert_severity",
    # flow summary
    "flow_pkts_toserver",
    "flow_pkts_toclient",
    "flow_bytes_toserver",
    "flow_bytes_toclient",
    "flow_start",
    "flow_end",
    "flow_state",
    "flow_reason",
    "flow_alerted",
]

_running = True


def _sigint(signum, frame):
    global _running
    _running = False


signal.signal(signal.SIGINT, _sigint)
signal.signal(signal.SIGTERM, _sigint)


def parse_alert_line(line: str) -> Optional[Dict[str, str]]:
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except Exception:
        return None
    if obj.get("event_type") != "alert":
        return None
    row: Dict[str, str] = {}
    row["timestamp"] = obj.get("timestamp", "")
    row["flow_id"] = str(obj.get("flow_id", ""))
    row["in_iface"] = obj.get("in_iface", "")
    row["event_type"] = obj.get("event_type", "")
    row["src_ip"] = obj.get("src_ip", "")
    row["src_port"] = str(obj.get("src_port", "")) if "src_port" in obj else ""
    row["dest_ip"] = obj.get("dest_ip", "")
    row["dest_port"] = str(obj.get("dest_port", "")) if "dest_port" in obj else ""
    row["proto"] = obj.get("proto", "")
    row["pkt_src"] = obj.get("pkt_src", "")
    row["direction"] = obj.get("direction", "")
    alert = obj.get("alert", {}) or {}
    row["alert_gid"] = str(alert.get("gid", ""))
    row["alert_signature_id"] = str(alert.get("signature_id", ""))
    row["alert_rev"] = str(alert.get("rev", ""))
    row["alert_signature"] = alert.get("signature", "")
    row["alert_category"] = alert.get("category", "")
    row["alert_severity"] = str(alert.get("severity", ""))
    flow = obj.get("flow", {}) or {}
    row["flow_pkts_toserver"] = str(flow.get("pkts_toserver", ""))
    row["flow_pkts_toclient"] = str(flow.get("pkts_toclient", ""))
    row["flow_bytes_toserver"] = str(flow.get("bytes_toserver", ""))
    row["flow_bytes_toclient"] = str(flow.get("bytes_toclient", ""))
    row["flow_start"] = flow.get("start", "")
    row["flow_end"] = flow.get("end", "")
    row["flow_state"] = flow.get("state", "")
    row["flow_reason"] = flow.get("reason", "")
    row["flow_alerted"] = str(flow.get("alerted", ""))
    return row


def ensure_header(csv_path: str):
    write_header = not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0
    if write_header:
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
            writer.writeheader()


def process_file_once(input_path: str, csv_path: str) -> int:
    ensure_header(csv_path)
    written = 0
    with open(input_path, "r", encoding="utf-8", errors="ignore") as fh, open(
        csv_path, "a", newline="", encoding="utf-8"
    ) as outfh:
        writer = csv.DictWriter(outfh, fieldnames=FIELDNAMES)
        for raw in fh:
            parsed = parse_alert_line(raw)
            if parsed:
                writer.writerow({k: parsed.get(k, "") for k in FIELDNAMES})
                written += 1
    return written


def follow_file(input_path: str, csv_path: str, poll_interval: float = 0.25):
    # open file and seek to end, then process new lines as they arrive
    ensure_header(csv_path)
    with open(input_path, "r", encoding="utf-8", errors="ignore") as fh, open(
        csv_path, "a", newline="", encoding="utf-8"
    ) as outfh:
        writer = csv.DictWriter(outfh, fieldnames=FIELDNAMES)
        fh.seek(0, os.SEEK_END)
        while _running:
            line = fh.readline()
            if not line:
                time.sleep(poll_interval)
                continue
            parsed = parse_alert_line(line)
            if parsed:
                writer.writerow({k: parsed.get(k, "") for k in FIELDNAMES})
                outfh.flush()


def build_parser():
    p = argparse.ArgumentParser(description="Extract Suricata alert events from eve.json to CSV.")
    p.add_argument("--input", "-i", default=DEFAULT_INPUT, help="Path to eve.json")
    p.add_argument("--output", "-o", default=DEFAULT_OUTPUT, help="CSV output path")
    p.add_argument("--follow", "-f", action="store_true", help="Follow file and append new alerts")
    return p


def main():
    args = build_parser().parse_args()
    if not os.path.exists(args.input):
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 2
    try:
        if args.follow:
            print(f"Following {args.input} → appending alerts to {args.output}")
            follow_file(args.input, args.output)
        else:
            cnt = process_file_once(args.input, args.output)
            print(f"Wrote {cnt} alert rows to {args.output}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())