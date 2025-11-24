# Eve.json Real Feature Extraction for ML Pipeline Simulation

## Overview

The `simulate_pcap_pipeline_outputs.py` script has been updated to extract **real packet and flow features directly from Suricata's `eve.json` logs** instead of generating random synthetic data. This approach provides more realistic simulation of ML pipeline predictions by using actual network statistics.

## Key Features

### 1. **Real Flow Data Extraction**
The script now reads Suricata `eve.json` and extracts actual flow statistics:
- **Source/Destination IPs**: Real IP addresses from captured flows
- **Ports**: Actual source and destination ports
- **Protocol**: TCP, UDP, ICMP, etc.
- **Packet Counts**: `pkts_toserver` and `pkts_toclient`
- **Byte Counts**: `bytes_toserver` and `bytes_toclient`
- **Flow Duration**: Start and end timestamps parsed from Suricata timestamps
- **Flow State**: Connection state information

### 2. **Similar to eve_labeler.py Approach**
The feature extraction uses a similar mapping strategy to `eve_labeler.py`:
- Flexible timestamp parsing supporting Suricata's ISO 8601 format with timezone
- Robust JSON parsing with error handling for malformed events
- Filters for flow events specifically (`event_type == "flow"`)
- Aggregates all flows from the entire eve.json file

### 3. **Fallback to Synthetic Generation**
If eve.json cannot be loaded or contains no flows:
- Script gracefully falls back to PCAP-based synthetic flow generation
- All previous functionality remains intact
- Useful for testing or when real eve.json is unavailable

## Usage

### Basic Usage: Extract Features from eve.json

```bash
python3 simulate_pcap_pipeline_outputs.py \
    --eve-json /var/log/suricata/eve.json \
    --mode ensemble5 \
    --accuracy 0.95 \
    --no-require-tcpreplay
```

### With Ground-Truth Labels

```bash
python3 simulate_pcap_pipeline_outputs.py \
    --eve-json /var/log/suricata/eve.json \
    --ground-truth-csv dpdk_suricata_ml_pipeline/CICIDS2017_ground_truth_CSVs/Wednesday-workingHours.pcap_ISCX.csv \
    --mode ensemble5 \
    --accuracy 0.93 \
    --realtime
```

### With Flow Limit (Faster Testing)

```bash
python3 simulate_pcap_pipeline_outputs.py \
    --eve-json /var/log/suricata/eve.json \
    --mode single \
    --max-flows 100 \
    --no-require-tcpreplay
```

### Traditional PCAP Mode (Fallback)

```bash
python3 simulate_pcap_pipeline_outputs.py \
    --pcap /path/to/file.pcap \
    --mode single \
    --accuracy 0.93
```

## New Command-Line Arguments

### `--eve-json <PATH>`
- **Type**: Optional path
- **Default**: Not set (uses PCAP mode if `--eve-json` not provided)
- **Priority**: Takes precedence over `--pcap` if both are specified
- **Description**: Path to Suricata `eve.json` file to extract real flow features

### `--pcap <PATH>` (Updated)
- **Type**: Now optional (previously required)
- **Required only if**: `--eve-json` is not provided
- **Description**: Path to CICIDS PCAP file (used for fallback synthetic generation)

## Technical Details

### Feature Extraction Process

1. **Eve.json Loading** (`load_flows_from_eve()`)
   - Reads eve.json line-by-line (JSONL format)
   - Filters for `event_type == "flow"` events
   - Extracts flow record structure

2. **Timestamp Parsing** (`_parse_suricata_ts()`)
   - Handles Suricata ISO 8601 format with timezone: `2025-11-24T12:10:51.781088+0530`
   - Supports multiple formats and timezone info
   - Falls back to float epoch if all else fails

3. **Flow Record Creation**
   - Combines src/dst IPs, ports, and protocol
   - Stores packet and byte counts as-is from eve.json
   - Preserves flow start and end times

4. **Statistics Aggregation**
   - Totals packets and bytes across all flows
   - Tracks minimum and maximum timestamps
   - Creates normalized statistics dictionary

### Supported Eve.json Format

```json
{
  "timestamp":"2025-11-24T12:10:51.781088+0530",
  "flow_id":801021916063939,
  "in_iface":"0000:01:00.0",
  "event_type":"flow",
  "src_ip":"192.168.10.17",
  "src_port":5353,
  "dest_ip":"224.0.0.251",
  "dest_port":5353,
  "proto":"UDP",
  "app_proto":"failed",
  "flow":{
    "pkts_toserver":508,
    "pkts_toclient":0,
    "bytes_toserver":77350,
    "bytes_toclient":0,
    "start":"2025-11-24T12:09:22.252038+0530",
    "end":"2025-11-24T12:10:20.519689+0530",
    "state":"new",
    "reason":"timeout",
    "alerted":false
  }
}
```

## Output Artifacts

The simulation produces the same artifacts as before, but now with realistic feature values:

- **ml_predictions.log**: ML consumer logs with real flow statistics
- **predictions_<mode>_<timestamp>.csv**: Predictions CSV with actual IPs, ports, and packet counts
- **metrics_<date>.jsonl**: Performance metrics (JSONL format)
- **throughput_<date>.csv**: Throughput metrics (CSV format)
- **performance_metrics_<timestamp>.json**: JSON performance metrics

## Example Output

```
📁 eve.json: /var/log/suricata/eve.json
   loaded 3,137 real flows from eve.json
   packets=1,267,076 bytes=1,078,385,150 flows=3,137
   realtime streaming: enabled (speed ×4.00, delay 1.00s)

✓ Simulation complete
   ml_predictions log  → /home/ifscr/SE_02_2025/IDS/dpdk_suricata_ml_pipeline/logs/ml/ml_consumer.log
   predictions CSV  → /home/ifscr/SE_02_2025/IDS/dpdk_suricata_ml_pipeline/logs/predictions_ensemble5_20251124_121530.csv
   metrics JSONL    → /home/ifscr/SE_02_2025/IDS/dpdk_suricata_ml_pipeline/logs/metrics/metrics_20251124.jsonl
                     ↳ /home/ifscr/SE_02_2025/IDS/logs/metrics/metrics_20251124.jsonl
   throughput CSV   → /home/ifscr/SE_02_2025/IDS/dpdk_suricata_ml_pipeline/logs/metrics/throughput_20251124.csv
                     ↳ /home/ifscr/SE_02_2025/IDS/logs/metrics/throughput_20251124.csv
   perf metrics JSON → /home/ifscr/SE_02_2025/IDS/dpdk_suricata_ml_pipeline/logs/ml/performance_metrics_20251124_121530.json
                     ↳ /home/ifscr/SE_02_2025/IDS/logs/ml/performance_metrics_20251124_121530.json
```

## Comparison: Random vs. Real Features

### Random Synthetic Features (Old)
```csv
src_ip,dst_ip,src_port,dst_port,packets,bytes
10.45.123.67,172.18.234.19,43201,443,87,9200
192.168.145.102,10.89.23.14,52310,80,42,5100
```

### Real Features from eve.json (New)
```csv
src_ip,dst_ip,src_port,dst_port,packets,bytes
192.168.10.12,202.55.13.210,36910,443,7,518
192.168.10.14,221.122.85.184,49537,443,3,194
fe80::266e:96ff:fe4a:377a,ff02::fb,5353,5353,2,198
```

## Benefits

✅ **Realistic Network Characteristics**: Packet/byte distributions match actual traffic patterns  
✅ **Accurate IP/Port Ranges**: Uses real IPs captured by Suricata  
✅ **Real Flow Durations**: Start/end times reflect actual flow lifetime  
✅ **Better ML Testing**: Predictions trained on real data can be evaluated more accurately  
✅ **Seamless Integration**: Works with existing ground-truth CSV workflow  
✅ **Backward Compatible**: Falls back to synthetic generation if eve.json unavailable

## Troubleshooting

### Error: eve.json not found
```
parser.error(f"eve.json not found: {eve_path}")
```
**Solution**: Verify the path to eve.json:
```bash
ls -la /var/log/suricata/eve.json
# Or check custom location and use --eve-json <PATH>
```

### Error: No flow events found in eve.json
```
⚠️  No flow events found in eve.json, falling back to generation mode
```
**Solution**: Eve.json may contain only stats events. Ensure Suricata is configured to log flow events:
```yaml
# In suricata-dpdk-intel.yaml
eve-log:
  - enabled: yes
    filetype: regular
    filename: eve.json
    types:
      - alert
      - http
      - dns
      - flow  # ← Ensure this is enabled
      - stats
```

### Permission denied on metrics files
```
PermissionError: [Errno 13] Permission denied: '.../metrics_20251124.jsonl'
```
**Solution**: Remove old metrics files created by root:
```bash
sudo rm -f /path/to/metrics/metrics_*.jsonl
```

## Migration Guide

### For Users Currently Using PCAP Mode

**Before:**
```bash
python3 simulate_pcap_pipeline_outputs.py \
    --pcap /home/user/data/Wednesday.pcap
```

**After (using real eve.json):**
```bash
python3 simulate_pcap_pipeline_outputs.py \
    --eve-json /var/log/suricata/eve.json
```

The output format and all downstream processing remain the same!

## Performance Notes

- **Loading Time**: ~1-5 seconds depending on eve.json size (typically 10-50MB)
- **Processing Time**: Scales with number of flows (~3,000+ flows typical)
  - With 100 flows: ~30-60 seconds
  - With 1,000 flows: ~5-10 minutes
  - Use `--max-flows` to limit for faster testing

## Advanced Usage

### Cache Real Features for Repeated Runs
```bash
python3 simulate_pcap_pipeline_outputs.py \
    --eve-json /var/log/suricata/eve.json \
    --flow-cache /tmp/eve_flows_cache.json \
    --write-flow-cache
```

Then reuse cached flows:
```bash
python3 simulate_pcap_pipeline_outputs.py \
    --flow-cache /tmp/eve_flows_cache.json \
    --mode ensemble5 \
    --accuracy 0.95
```

### Batch Testing Multiple Modes
```bash
for mode in single ensemble2 ensemble5; do
  python3 simulate_pcap_pipeline_outputs.py \
      --eve-json /var/log/suricata/eve.json \
      --mode $mode \
      --accuracy 0.93 \
      --no-require-tcpreplay
done
```

## Integration with Ground-Truth Labels

Combine real features with ground-truth CSV for labeled simulation:

```bash
python3 simulate_pcap_pipeline_outputs.py \
    --eve-json /var/log/suricata/eve.json \
    --ground-truth-csv /path/to/labels.csv \
    --mode ensemble5 \
    --accuracy 0.92
```

The ground-truth matching works on the real flow tuples (src_ip, dst_ip, src_port, dst_port, proto), providing accurate labels for your actual captured flows.

## Related Scripts

- **eve_labeler.py**: Labels eve.json flows with ground-truth CSV (complementary tool)
- **replay_pcap_for_testing.py**: Original PCAP-based simulation (fallback mode)

