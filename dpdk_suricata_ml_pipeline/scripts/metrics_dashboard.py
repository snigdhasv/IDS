#!/usr/bin/env python3
"""
Real-time Metrics Dashboard

Monitors and displays real-time metrics from the IDS pipeline.
Refreshes every 5 seconds to show current performance.

Usage:
    ./metrics_dashboard.py [--metrics-dir DIR] [--refresh-interval SECONDS]
"""

import time
import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def clear_screen():
    """Clear terminal screen."""
    os.system('clear' if os.name != 'nt' else 'cls')

def load_latest_metrics(metrics_dir):
    """Load latest metrics from JSON file."""
    metrics_dir = Path(metrics_dir)
    today = datetime.now().strftime('%Y%m%d')
    json_file = metrics_dir / f'metrics_{today}.jsonl'
    
    if not json_file.exists():
        return None
    
    # Read last 1000 lines
    metrics = {
        'latency': [],
        'throughput': [],
        'ml': [],
        'errors': [],
        'system': []
    }
    
    try:
        with open(json_file, 'r') as f:
            # Read last N lines efficiently
            lines = f.readlines()[-1000:]
            for line in lines:
                try:
                    record = json.loads(line)
                    metric_type = record.get('type')
                    if metric_type in metrics:
                        metrics[metric_type].append(record)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error loading metrics: {e}")
        return None
    
    return metrics

def calculate_stats(metrics):
    """Calculate statistics from metrics."""
    stats = {}
    
    # Latency stats by component
    latencies_by_comp = defaultdict(list)
    for m in metrics['latency']:
        key = f"{m['component']}.{m['operation']}"
        latencies_by_comp[key].append(m['latency_ms'])
    
    stats['latency'] = {}
    for key, values in latencies_by_comp.items():
        if values:
            sorted_values = sorted(values)
            n = len(sorted_values)
            stats['latency'][key] = {
                'count': n,
                'mean': sum(values) / n,
                'min': min(values),
                'max': max(values),
                'p50': sorted_values[int(n * 0.5)],
                'p95': sorted_values[int(n * 0.95)],
                'p99': sorted_values[int(n * 0.99)],
            }
    
    # Throughput stats
    throughput_by_comp = defaultdict(int)
    for m in metrics['throughput']:
        throughput_by_comp[m['component']] += m['events_count']
    stats['throughput'] = dict(throughput_by_comp)
    
    # ML prediction counts
    ml_predictions = defaultdict(int)
    ml_inference_times = []
    for m in metrics['ml']:
        ml_predictions[m['prediction']] += 1
        ml_inference_times.append(m['inference_time_ms'])
    
    stats['ml_predictions'] = dict(ml_predictions)
    stats['ml_inference_mean'] = sum(ml_inference_times) / len(ml_inference_times) if ml_inference_times else 0
    
    # Error counts
    error_by_comp = defaultdict(int)
    error_by_severity = defaultdict(int)
    for m in metrics['errors']:
        error_by_comp[m['component']] += 1
        error_by_severity[m.get('severity', 'unknown')] += 1
    stats['error_counts'] = dict(error_by_comp)
    stats['error_by_severity'] = dict(error_by_severity)
    
    # System metrics (latest)
    if metrics['system']:
        latest_system = metrics['system'][-1]
        stats['system'] = {
            'cpu_percent': latest_system.get('cpu_percent', 0),
            'memory_percent': latest_system.get('memory_percent', 0),
            'memory_mb': latest_system.get('memory_mb', 0),
        }
    else:
        stats['system'] = {}
    
    return stats

def display_dashboard(stats):
    """Display metrics dashboard."""
    clear_screen()
    
    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║                  IDS PIPELINE METRICS DASHBOARD                         ║")
    print("╚══════════════════════════════════════════════════════════════════════════╝")
    print(f"⏰ Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # System resources (if available)
    if stats.get('system'):
        sys_stats = stats['system']
        print(f"💻 System: CPU {sys_stats['cpu_percent']:.1f}% | "
              f"Memory {sys_stats['memory_percent']:.1f}% ({sys_stats['memory_mb']:.0f} MB)")
    
    print()
    
    # Latency Section
    print("┌─ LATENCY (milliseconds) ───────────────────────────────────────────────┐")
    if stats.get('latency'):
        # Show top components by p95 latency
        sorted_components = sorted(
            stats['latency'].items(),
            key=lambda x: x[1]['p95'],
            reverse=True
        )[:5]  # Show top 5
        
        print("│ Component.Operation                      Mean    P50    P95    P99    │")
        print("├─────────────────────────────────────────────────────────────────────────┤")
        for component, values in sorted_components:
            comp_short = component[:35] + '...' if len(component) > 35 else component
            print(f"│ {comp_short:<35} {values['mean']:6.2f} {values['p50']:6.2f} "
                  f"{values['p95']:6.2f} {values['p99']:6.2f} │")
    else:
        print("│ No data available                                                       │")
    print("└─────────────────────────────────────────────────────────────────────────┘")
    print()
    
    # Throughput Section
    print("┌─ THROUGHPUT (total events processed) ───────────────────────────────────┐")
    if stats.get('throughput'):
        print("│ Component                            Events                             │")
        print("├─────────────────────────────────────────────────────────────────────────┤")
        for component, count in sorted(stats['throughput'].items(), key=lambda x: x[1], reverse=True):
            comp_short = component[:30] + '...' if len(component) > 30 else component
            print(f"│ {comp_short:<30} {count:>15,}                          │")
    else:
        print("│ No data available                                                       │")
    print("└─────────────────────────────────────────────────────────────────────────┘")
    print()
    
    # ML Predictions Section
    print("┌─ ML PREDICTIONS ─────────────────────────────────────────────────────────┐")
    if stats.get('ml_predictions'):
        total = sum(stats['ml_predictions'].values())
        print(f"│ Total Predictions: {total:,}")
        if stats.get('ml_inference_mean'):
            print(f"│ Avg Inference Time: {stats['ml_inference_mean']:.2f} ms")
        print("│                                                                         │")
        print("│ Prediction Class                     Count          Percentage         │")
        print("├─────────────────────────────────────────────────────────────────────────┤")
        for prediction, count in sorted(stats['ml_predictions'].items(), key=lambda x: x[1], reverse=True):
            pct = (count / total * 100) if total > 0 else 0
            pred_short = prediction[:30] + '...' if len(prediction) > 30 else prediction
            bar_length = int(pct / 2)  # Max 50 chars
            bar = '█' * bar_length
            print(f"│ {pred_short:<30} {count:>8,}   {pct:>5.1f}% {bar:<15}│")
    else:
        print("│ No data available                                                       │")
    print("└─────────────────────────────────────────────────────────────────────────┘")
    print()
    
    # Errors Section
    print("┌─ ERRORS ─────────────────────────────────────────────────────────────────┐")
    if stats.get('error_counts'):
        total_errors = sum(stats['error_counts'].values())
        print(f"│ Total Errors: {total_errors}")
        print("│                                                                         │")
        print("│ Component                            Errors                             │")
        print("├─────────────────────────────────────────────────────────────────────────┤")
        for component, count in sorted(stats['error_counts'].items(), key=lambda x: x[1], reverse=True):
            comp_short = component[:30] + '...' if len(component) > 30 else component
            print(f"│ {comp_short:<30} {count:>8}                               │")
        
        if stats.get('error_by_severity'):
            print("│                                                                         │")
            print("│ By Severity:                                                            │")
            for severity, count in sorted(stats['error_by_severity'].items()):
                print(f"│   {severity}: {count}                                                │")
    else:
        print("│ No errors 🎉                                                            │")
    print("└─────────────────────────────────────────────────────────────────────────┘")
    print()
    
    print("Press Ctrl+C to exit | Dashboard refreshes automatically")

def main():
    """Main dashboard loop."""
    parser = argparse.ArgumentParser(description='IDS Pipeline Metrics Dashboard')
    parser.add_argument('--metrics-dir', 
                       default=None,
                       help='Path to metrics directory')
    parser.add_argument('--refresh-interval', 
                       type=int,
                       default=5,
                       help='Dashboard refresh interval in seconds (default: 5)')
    
    args = parser.parse_args()
    
    # Determine metrics directory
    if args.metrics_dir:
        metrics_dir = Path(args.metrics_dir)
    else:
        # Try to find metrics directory relative to script location
        script_dir = Path(__file__).parent
        metrics_dir = script_dir.parent / 'logs' / 'metrics'
    
    if not metrics_dir.exists():
        print(f"❌ Metrics directory not found: {metrics_dir}")
        print(f"\nPlease specify correct path with --metrics-dir option")
        sys.exit(1)
    
    print(f"🚀 Starting IDS Metrics Dashboard...")
    print(f"📊 Monitoring: {metrics_dir}")
    print(f"🔄 Refresh interval: {args.refresh_interval}s")
    print(f"⌨️  Press Ctrl+C to exit\n")
    
    time.sleep(2)
    
    try:
        first_run = True
        while True:
            metrics = load_latest_metrics(metrics_dir)
            
            if metrics and any(len(v) > 0 for v in metrics.values()):
                stats = calculate_stats(metrics)
                display_dashboard(stats)
            else:
                if first_run:
                    clear_screen()
                    print("╔══════════════════════════════════════════════════════════════════════════╗")
                    print("║                  IDS PIPELINE METRICS DASHBOARD                         ║")
                    print("╚══════════════════════════════════════════════════════════════════════════╝")
                    print()
                    print("⏳ Waiting for metrics data...")
                    print()
                    print(f"📂 Monitoring directory: {metrics_dir}")
                    print(f"📅 Looking for file: metrics_{datetime.now().strftime('%Y%m%d')}.jsonl")
                    print()
                    print("💡 Make sure the IDS pipeline is running and generating metrics.")
                    print("   The dashboard will automatically update when data becomes available.")
                    print()
                    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print()
                    print("Press Ctrl+C to exit")
                    first_run = False
            
            time.sleep(args.refresh_interval)
            
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard stopped. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
