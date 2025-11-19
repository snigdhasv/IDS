#!/usr/bin/env python3
"""
Label Suricata eve.json flows using a ground-truth CSV for a pcap.

Produces a CSV of flows with an assigned label (from ground-truth) and
other useful fields. Can run one-shot or follow the `eve.json` file.

Assumptions (inferred from repository):
- Ground-truth CSV (for a pcap) contains at least columns for source IP,
  destination IP, optionally source/destination ports, protocol, start and
  end times, and a label column. The script attempts to normalize common
  column names. If start/end times are missing for a ground-truth row, the
  row will match flows based on 4-tuple/proto only.

Usage examples:
  sudo python3 eve_labeler.py --input /var/log/suricata/eve.json \
      --gt dpdk_suricata_ml_pipeline/CICIDS2017_ground_truth_CSVs/Wednesday-workingHours.pcap_ISCX.csv \
      --output /tmp/labeled_flows.csv

  # follow new events (append):
  sudo python3 eve_labeler.py -i /var/log/suricata/eve.json -g /path/to/GT.csv -o ./out.csv -f
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_EVE = "/var/log/suricata/eve.json"
DEFAULT_OUT = "./labeled_flows.csv"

# Output fields for flows
FLOW_FIELDS = [
    "timestamp",
    "flow_id",
    "in_iface",
    "src_ip",
    "src_port",
    "dest_ip",
    "dest_port",
    "proto",
    "pkts_toserver",
    "pkts_toclient",
    "bytes_toserver",
    "bytes_toclient",
    "start",
    "end",
    "state",
    "reason",
    "alerted",
    # labeling
    "label",
    "matched_gt_index",
    "overlap_seconds",
]


def parse_ts_to_epoch(ts: Optional[str]) -> Optional[float]:
    """Parse Suricata timestamps like 2025-11-19T12:19:16.182783+0530 to epoch seconds.
    Returns None if ts is falsy or can't be parsed.
    """
    if not ts:
        return None
    # Try several parse patterns
    patterns = ["%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"]
    for p in patterns:
        try:
            dt = datetime.strptime(ts, p)
            return dt.timestamp()
        except Exception:
            continue
    # Fallback: try ISO without timezone
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        pass
    # try float epoch string
    try:
        return float(ts)
    except Exception:
        return None


def normalize_str(s: Any) -> str:
    return str(s).strip() if s is not None else ""


def load_ground_truth(gt_csv: str) -> List[Dict[str, Any]]:
    """Load ground-truth CSV and return normalized rows.

    The loader is permissive about column names; it attempts to map common
    field names.
    Expected resulting dict keys: src_ip, src_port, dest_ip, dest_port, proto,
    start (epoch or None), end (epoch or None), label
    """
    if not os.path.exists(gt_csv):
        raise FileNotFoundError(gt_csv)
    rows: List[Dict[str, Any]] = []
    with open(gt_csv, "r", encoding="utf-8", errors="ignore") as fh:
        reader = csv.DictReader(fh)
        # build header mapping heuristics
        headers = [h.lower() for h in reader.fieldnames or []]
        for r in reader:
            rr = {k.lower(): v for k, v in (r.items() if isinstance(r, dict) else [])}
            # helper to find a column value by possible names
            def find(*cands):
                for c in cands:
                    if c.lower() in rr and rr[c.lower()] != "":
                        return rr[c.lower()]
                return ""

            src_ip = normalize_str(find("src_ip", "source_ip", "source ip", "sip", "saddr"))
            dest_ip = normalize_str(find("dest_ip", "destination_ip", "destination ip", "dip", "daddr"))
            src_port = normalize_str(find("src_port", "source_port", "sport"))
            dest_port = normalize_str(find("dest_port", "destination_port", "dport"))
            proto = normalize_str(find("proto", "protocol", "protocol_name")).upper()
            label = normalize_str(find("label", "attack_label", "class", "tag"))
            start_raw = normalize_str(find("start", "start_time", "starttime", "begin"))
            end_raw = normalize_str(find("end", "end_time", "endtime", "stop"))
            start = parse_ts_to_epoch(start_raw) if start_raw else None
            end = parse_ts_to_epoch(end_raw) if end_raw else None
            rows.append({
                "src_ip": src_ip,
                "dest_ip": dest_ip,
                "src_port": src_port,
                "dest_port": dest_port,
                "proto": proto,
                "start": start,
                "end": end,
                "label": label or "UNKNOWN",
            })
    return rows


def flow_dict_from_eve(obj: Dict[str, Any]) -> Dict[str, Any]:
    flow = obj.get("flow", {}) or {}
    row: Dict[str, Any] = {}
    row["timestamp"] = obj.get("timestamp", "")
    row["flow_id"] = str(obj.get("flow_id", ""))
    row["in_iface"] = obj.get("in_iface", "")
    row["src_ip"] = obj.get("src_ip", "")
    row["src_port"] = str(obj.get("src_port", "")) if "src_port" in obj else ""
    row["dest_ip"] = obj.get("dest_ip", "")
    row["dest_port"] = str(obj.get("dest_port", "")) if "dest_port" in obj else ""
    row["proto"] = (obj.get("proto") or "").upper()
    row["pkts_toserver"] = str(flow.get("pkts_toserver", ""))
    row["pkts_toclient"] = str(flow.get("pkts_toclient", ""))
    row["bytes_toserver"] = str(flow.get("bytes_toserver", ""))
    row["bytes_toclient"] = str(flow.get("bytes_toclient", ""))
    row["start"] = flow.get("start", "")
    row["end"] = flow.get("end", "")
    row["state"] = flow.get("state", "")
    row["reason"] = flow.get("reason", "")
    row["alerted"] = str(flow.get("alerted", ""))
    # numeric epoch
    row["_start_epoch"] = parse_ts_to_epoch(row["start"])
    row["_end_epoch"] = parse_ts_to_epoch(row["end"])
    return row


def time_overlap_seconds(a_start: Optional[float], a_end: Optional[float], b_start: Optional[float], b_end: Optional[float]) -> float:
    if a_start is None or b_start is None:
        return 0.0
    a_end_val = a_end if a_end is not None else a_start
    b_end_val = b_end if b_end is not None else b_start
    latest_start = max(a_start, b_start)
    earliest_end = min(a_end_val, b_end_val)
    overlap = earliest_end - latest_start
    return max(0.0, overlap)


def match_label_for_flow(flow: Dict[str, Any], gt_rows: List[Dict[str, Any]]) -> Tuple[str, Optional[int], float]:
    """Return (label, gt_index_or_None, overlap_seconds). """
    best_label = "UNKNOWN"
    best_idx = None
    best_overlap = 0.0
    f_src = flow.get("src_ip", "")
    f_dst = flow.get("dest_ip", "")
    f_spt = flow.get("src_port", "")
    f_dpt = flow.get("dest_port", "")
    f_proto = (flow.get("proto") or "").upper()
    f_start = flow.get("_start_epoch")
    f_end = flow.get("_end_epoch")

    for i, gt in enumerate(gt_rows):
        # protocol match if provided in GT
        gt_proto = (gt.get("proto") or "").upper()
        if gt_proto and gt_proto != f_proto:
            continue
        # check 4-tuple either direction (allow blank ports in GT)
        direct = (gt.get("src_ip") == f_src and gt.get("dest_ip") == f_dst)
        ports_ok = True
        if gt.get("src_port"):
            ports_ok = ports_ok and (gt.get("src_port") == f_spt)
        if gt.get("dest_port"):
            ports_ok = ports_ok and (gt.get("dest_port") == f_dpt)
        reverse = (gt.get("src_ip") == f_dst and gt.get("dest_ip") == f_src)
        ports_ok_rev = True
        if gt.get("src_port"):
            ports_ok_rev = ports_ok_rev and (gt.get("src_port") == f_dpt)
        if gt.get("dest_port"):
            ports_ok_rev = ports_ok_rev and (gt.get("dest_port") == f_spt)

        if not ((direct and ports_ok) or (reverse and ports_ok_rev)):
            # allow matching if gt has no IPs (some GT rows may be general) or IPs match partially
            # if GT row has no IPs/ports, skip matching here
            if not (gt.get("src_ip") or gt.get("dest_ip")):
                continue
            # partial IP match: try if either src or dest matches
            if not (gt.get("src_ip") == f_src or gt.get("dest_ip") == f_dst or gt.get("src_ip") == f_dst or gt.get("dest_ip") == f_src):
                continue

        # compute time overlap
        overlap = time_overlap_seconds(f_start, f_end, gt.get("start"), gt.get("end"))
        # If ground truth has no start/end, treat as a match with minimal overlap metric 0.1
        if gt.get("start") is None and gt.get("end") is None:
            overlap = max(overlap, 0.1)

        if overlap > best_overlap:
            best_overlap = overlap
            best_label = gt.get("label", "UNKNOWN")
            best_idx = i

    return best_label, best_idx, best_overlap


def ensure_header(path: str):
    write_header = not os.path.exists(path) or os.path.getsize(path) == 0
    if write_header:
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=FLOW_FIELDS)
            writer.writeheader()


def process_once(eve_path: str, gt_csv: str, out_csv: str) -> int:
    gt_rows = load_ground_truth(gt_csv)
    ensure_header(out_csv)
    written = 0
    with open(eve_path, "r", encoding="utf-8", errors="ignore") as fh, open(out_csv, "a", newline="", encoding="utf-8") as outfh:
        writer = csv.DictWriter(outfh, fieldnames=FLOW_FIELDS)
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except Exception:
                continue
            if obj.get("event_type") != "flow":
                continue
            flow = flow_dict_from_eve(obj)
            label, idx, overlap = match_label_for_flow(flow, gt_rows)
            flow["label"] = label
            flow["matched_gt_index"] = str(idx) if idx is not None else ""
            flow["overlap_seconds"] = f"{overlap:.3f}"
            # write only fields defined
            row = {k: flow.get(k, "") for k in FLOW_FIELDS}
            writer.writerow(row)
            written += 1
    return written


def follow(eve_path: str, gt_csv: str, out_csv: str, poll: float = 0.25):
    gt_rows = load_ground_truth(gt_csv)
    ensure_header(out_csv)
    with open(eve_path, "r", encoding="utf-8", errors="ignore") as fh, open(out_csv, "a", newline="", encoding="utf-8") as outfh:
        writer = csv.DictWriter(outfh, fieldnames=FLOW_FIELDS)
        fh.seek(0, os.SEEK_END)
        try:
            while True:
                line = fh.readline()
                if not line:
                    time.sleep(poll)
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("event_type") != "flow":
                    continue
                flow = flow_dict_from_eve(obj)
                label, idx, overlap = match_label_for_flow(flow, gt_rows)
                flow["label"] = label
                flow["matched_gt_index"] = str(idx) if idx is not None else ""
                flow["overlap_seconds"] = f"{overlap:.3f}"
                row = {k: flow.get(k, "") for k in FLOW_FIELDS}
                writer.writerow(row)
                outfh.flush()
        except KeyboardInterrupt:
            print("Interrupted, exiting")


def build_parser():
    p = argparse.ArgumentParser(description="Label Suricata eve.json flows using a ground-truth CSV")
    p.add_argument("-i", "--input", default=DEFAULT_EVE, help="path to eve.json")
    p.add_argument("-g", "--gt", required=True, help="path to ground-truth CSV for the pcap")
    p.add_argument("-o", "--output", default=DEFAULT_OUT, help="output CSV path")
    p.add_argument("-f", "--follow", action="store_true", help="follow eve.json and append new flows")
    return p


def main():
    args = build_parser().parse_args()
    if not os.path.exists(args.input):
        print(f"eve.json not found: {args.input}", file=sys.stderr)
        return 2
    if not os.path.exists(args.gt):
        print(f"ground-truth CSV not found: {args.gt}", file=sys.stderr)
        return 2
    if args.follow:
        print(f"Following {args.input} and appending labeled flows to {args.output}")
        follow(args.input, args.gt, args.output)
    else:
        cnt = process_once(args.input, args.gt, args.output)
        print(f"Wrote {cnt} labeled flow rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
