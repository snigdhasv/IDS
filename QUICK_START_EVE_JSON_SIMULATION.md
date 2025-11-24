# Quick Start: Real Features from eve.json

## One-Liner Examples

### Extract Real Features (Fastest)
```bash
cd /home/ifscr/SE_02_2025/IDS
python3 dpdk_suricata_ml_pipeline/scripts/simulate_pcap_pipeline_outputs.py \
  --eve-json /var/log/suricata/eve.json \
  --mode single \
  --no-require-tcpreplay
```

### With Labels (Ground-Truth CSV)
```bash
python3 dpdk_suricata_ml_pipeline/scripts/simulate_pcap_pipeline_outputs.py \
  --eve-json /var/log/suricata/eve.json \
  --ground-truth-csv dpdk_suricata_ml_pipeline/CICIDS2017_ground_truth_CSVs/Wednesday-workingHours.pcap_ISCX.csv \
  --mode ensemble5 \
  --accuracy 0.93 \
  --no-require-tcpreplay
```

### Real-Time Streaming (4x Speed)
```bash
python3 dpdk_suricata_ml_pipeline/scripts/simulate_pcap_pipeline_outputs.py \
  --eve-json /var/log/suricata/eve.json \
  --mode ensemble5 \
  --realtime \
  --speed-factor 4.0 \
  --no-require-tcpreplay
```

### Quick Test (20 Flows Only)
```bash
python3 dpdk_suricata_ml_pipeline/scripts/simulate_pcap_pipeline_outputs.py \
  --eve-json /var/log/suricata/eve.json \
  --max-flows 20 \
  --no-require-tcpreplay
```

## What Changed

### Before (Random Synthetic)
```bash
python3 simulate_pcap_pipeline_outputs.py --pcap file.pcap --mode single
# → Generates 1200-6000 random flows with random IPs/ports
```

### After (Real eve.json Features)
```bash
python3 simulate_pcap_pipeline_outputs.py --eve-json /var/log/suricata/eve.json --mode single
# → Loads 3,137 actual flows with REAL IPs, ports, packet counts, byte counts from Suricata
```

## Key New Feature

**`--eve-json` flag**: Path to Suricata eve.json file
- Takes precedence over `--pcap`
- Extracts: IPs, ports, protocols, packet counts, byte counts, flow duration
- Much more realistic than random synthetic data

## Output Files Created

The simulation creates these artifacts with **real feature values**:

1. **ml_consumer.log** - Log entries with predictions
2. **predictions_<mode>_<timestamp>.csv** - Predictions with actual network data
3. **metrics_<date>.jsonl** - Performance metrics
4. **throughput_<date>.csv** - Throughput measurements

## Example Log Output

Before (random):
```
src_ip=10.45.123.67, dst_ip=172.18.234.19, src_port=43201, dst_port=443, packets=87, bytes=9200
```

After (real from eve.json):
```
src_ip=192.168.10.12, dst_ip=202.55.13.210, src_port=36910, dst_port=443, packets=7, bytes=518
src_ip=192.168.10.14, dst_ip=221.122.85.184, src_port=49537, dst_port=443, packets=3, bytes=194
```

## Performance

- **Small run (20 flows)**: ~30 seconds
- **Medium run (100 flows)**: ~2-5 minutes  
- **Large run (1000+ flows)**: ~10-30 minutes

Tip: Use `--max-flows` to limit for faster testing

## Options Cheat Sheet

| Flag | Purpose | Example |
|------|---------|---------|
| `--eve-json PATH` | Real features from eve.json | `/var/log/suricata/eve.json` |
| `--pcap PATH` | Fallback: synthetic from PCAP | `/path/to/file.pcap` |
| `--mode` | Model mode | `single`, `ensemble2`, `ensemble5` |
| `--accuracy` | Prediction match rate | `0.93` (0.5-0.999) |
| `--ground-truth-csv` | Labels CSV | `./labels.csv` |
| `--max-flows` | Limit flows for testing | `100` |
| `--realtime` | Stream in real-time | (flag, no value) |
| `--speed-factor` | Timeline speed | `2.0` (2x speed) |
| `--no-require-tcpreplay` | Skip tcpreplay check | (flag, no value) |

## Troubleshooting

**Q: Script loads flows but hangs?**  
A: It's processing 3,000+ flows through prediction simulation. This can take 15-30 minutes. Use `--max-flows 50` for testing.

**Q: Permission denied on metrics files?**  
A: Remove old root-owned files:
```bash
sudo rm -f /home/ifscr/SE_02_2025/IDS/dpdk_suricata_ml_pipeline/logs/metrics/metrics_*.jsonl
```

**Q: No flows found in eve.json?**  
A: Ensure Suricata is logging flow events (not just stats). Check configuration.

**Q: Want to use both eve.json features AND PCAP labels?**  
A: Sure! eve.json has the features, CSV has labels:
```bash
python3 simulate_pcap_pipeline_outputs.py \
  --eve-json /var/log/suricata/eve.json \
  --ground-truth-csv Wednesday-workingHours.pcap_ISCX.csv \
  --mode ensemble5
```

## Complete Documentation

See: `EVE_JSON_FEATURE_EXTRACTION_GUIDE.md`

