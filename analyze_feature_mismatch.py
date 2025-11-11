#!/usr/bin/env python3
"""
Feature Extraction Diagnostic

Shows what features Suricata provides vs what CICIDS models need
Helps identify feature mismatch issues
"""

import json
import sys

print("╔═══════════════════════════════════════════════════════════════╗")
print("║       Feature Extraction Diagnostic Tool                     ║")
print("╚═══════════════════════════════════════════════════════════════╝\n")

# Sample Suricata flow event (from your actual data)
suricata_event = {
    "timestamp": "2025-11-11T03:25:32.831130+0530",
    "flow_id": 1331069519918514,
    "event_type": "flow",
    "src_ip": "23.63.226.146",
    "src_port": 80,
    "dest_ip": "192.168.10.87",
    "dest_port": 49454,
    "proto": "TCP",
    "flow": {
        "pkts_toserver": 3,
        "pkts_toclient": 0,
        "bytes_toserver": 421,
        "bytes_toclient": 0,
        "start": "2025-11-11T03:25:16.899737+0530",
        "end": "2025-11-11T03:25:16.944260+0530",
        "age": 0,
        "state": "new",
        "reason": "shutdown",
        "alerted": False
    },
    "tcp": {
        "tcp_flags": "00",
        "tcp_flags_ts": "00",
        "tcp_flags_tc": "00"
    }
}

# CICIDS required features
cicids_features = [
    'Destination Port', 'Flow Duration', 'Total Fwd Packets', 'Total Backward Packets',
    'Total Length of Fwd Packets', 'Total Length of Bwd Packets', 'Fwd Packet Length Max',
    'Fwd Packet Length Min', 'Fwd Packet Length Mean', 'Fwd Packet Length Std',
    'Bwd Packet Length Max', 'Bwd Packet Length Min', 'Bwd Packet Length Mean',
    'Bwd Packet Length Std', 'Flow Bytes/s', 'Flow Packets/s', 'Flow IAT Mean',
    'Flow IAT Std', 'Flow IAT Max', 'Flow IAT Min', 'Fwd IAT Total', 'Fwd IAT Mean',
    'Fwd IAT Std', 'Fwd IAT Max', 'Fwd IAT Min', 'Bwd IAT Total', 'Bwd IAT Mean',
    'Bwd IAT Std', 'Bwd IAT Max', 'Bwd IAT Min', 'Fwd PSH Flags',
    'Fwd URG Flags', 'Fwd Header Length', 'Bwd Header Length',
    'Fwd Packets/s', 'Bwd Packets/s', 'Min Packet Length', 'Max Packet Length',
    'Packet Length Mean', 'Packet Length Std', 'Packet Length Variance',
    'FIN Flag Count', 'RST Flag Count', 'PSH Flag Count',
    'ACK Flag Count', 'URG Flag Count', 'ECE Flag Count',
    'Down/Up Ratio', 'Average Packet Size', 'Avg Fwd Segment Size',
    'Avg Bwd Segment Size', 'Subflow Fwd Bytes',
    'Subflow Bwd Bytes', 'Init_Win_bytes_forward',
    'Init_Win_bytes_backward', 'act_data_pkt_fwd', 'min_seg_size_forward',
    'Active Mean', 'Active Std', 'Active Max', 'Active Min', 
    'Idle Mean', 'Idle Std', 'Idle Max', 'Idle Min'
]

print("="*70)
print("WHAT SURICATA PROVIDES:")
print("="*70)

flow = suricata_event['flow']
print(f"\n✓ Direct measurements (ACCURATE):")
print(f"  • pkts_toserver:   {flow['pkts_toserver']}")
print(f"  • pkts_toclient:   {flow['pkts_toclient']}")
print(f"  • bytes_toserver:  {flow['bytes_toserver']}")
print(f"  • bytes_toclient:  {flow['bytes_toclient']}")
print(f"  • age (duration):  {flow['age']}")
print(f"  • TCP flags:       {suricata_event.get('tcp', {})}")

print(f"\n❌ What Suricata DOES NOT provide:")
print(f"  • Individual packet lengths (min/max/std)")
print(f"  • Packet arrival timestamps (for IAT calculation)")
print(f"  • Per-packet TCP flags")
print(f"  • Window sizes")
print(f"  • Active/Idle timing")
print(f"  • Detailed header information")

print("\n" + "="*70)
print("FEATURE EXTRACTION STATUS:")
print("="*70)

# Categorize features
direct_features = [
    'Destination Port', 'Flow Duration', 'Total Fwd Packets', 'Total Backward Packets',
    'Total Length of Fwd Packets', 'Total Length of Bwd Packets'
]

calculated_features = [
    'Flow Bytes/s', 'Flow Packets/s', 'Fwd Packets/s', 'Bwd Packets/s',
    'Average Packet Size', 'Avg Fwd Segment Size', 'Avg Bwd Segment Size'
]

estimated_features = [feat for feat in cicids_features 
                      if feat not in direct_features and feat not in calculated_features]

print(f"\n✓ DIRECT from Suricata ({len(direct_features)} features):")
for feat in direct_features[:5]:
    print(f"    {feat}")
print(f"    ... {len(direct_features)} total")

print(f"\n⚠️  CALCULATED (may be accurate) ({len(calculated_features)} features):")
for feat in calculated_features[:5]:
    print(f"    {feat}")
print(f"    ... {len(calculated_features)} total")

print(f"\n❌ ESTIMATED/GUESSED ({len(estimated_features)} features):")
for feat in estimated_features[:10]:
    print(f"    {feat}")
print(f"    ... {len(estimated_features)} total")

print("\n" + "="*70)
print("WHY LOW CONFIDENCE?")
print("="*70)

pct_estimated = (len(estimated_features) / len(cicids_features)) * 100
print(f"\n{pct_estimated:.1f}% of features are ESTIMATED/GUESSED!")
print("\nThe model was trained on:")
print("  • Real packet-level statistics from PCAP files")
print("  • Detailed timing information (IAT)")
print("  • Individual packet sizes and distributions")

print("\nBut your pipeline gives it:")
print("  • Flow-level aggregates from Suricata")
print("  • Estimated packet size distributions (avg * 1.5)")
print("  • Guessed inter-arrival times")

print("\n" + "="*70)
print("SOLUTIONS:")
print("="*70)

print("\n1️⃣  BEST: Process PCAP directly for training-quality features")
print("   Tools: CICFlowMeter, Argus, nProbe")
print("   Pros: Accurate features, high confidence")
print("   Cons: More CPU intensive")

print("\n2️⃣  GOOD: Retrain models on Suricata-extracted features")
print("   Process: Extract features from training PCAPs using Suricata")
print("   Pros: Perfect match, will work")
print("   Cons: Need to retrain all models")

print("\n3️⃣  OK: Improve Suricata feature extraction")
print("   Enable: Detailed per-packet logging")
print("   Process: Post-process eve.json for better stats")
print("   Pros: Uses existing infrastructure")
print("   Cons: Still won't match CICIDS exactly")

print("\n4️⃣  QUICK FIX: Use ensemble with uncertainty handling")
print("   Idea: Ensemble can learn to handle noisy features")
print("   Pros: May improve confidence")
print("   Cons: Won't fix root cause")

print("\n" + "="*70)
print("RECOMMENDED ACTION:")
print("="*70)

print("\nFor NOW (quick validation):")
print("  1. Test ensemble to see if it helps")
print("  2. Lower confidence threshold (accept 30-40%)")
print("  3. Focus on relative differences (DDoS vs BENIGN)")

print("\nFor PRODUCTION (proper solution):")
print("  1. Install CICFlowMeter or similar")
print("  2. Process PCAPs to extract proper 65 features")
print("  3. Feed those features to ML models")
print("  4. OR retrain models on Suricata features")

print("\n" + "="*70)
