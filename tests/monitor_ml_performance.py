#!/usr/bin/env python3
"""
Real-time ML Performance Monitor

Monitors and displays live performance metrics of the ML IDS pipeline.
Reads performance data from the ML consumer logs and metrics files.
"""

import os
import sys
import time
import json
import glob
from pathlib import Path
from datetime import datetime
from collections import deque

# Add src directory to path
sys.path.append(str(Path(__file__).parent.parent / 'dpdk_suricata_ml_pipeline' / 'src'))

import numpy as np


class Colors:
    """Terminal colors"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'
    CLEAR = '\033[2J\033[H'  # Clear screen and move to top


class PerformanceMonitor:
    """Real-time performance monitor for ML IDS."""
    
    def __init__(self, metrics_dir: str = None):
        """Initialize monitor."""
        if metrics_dir is None:
            self.metrics_dir = Path(__file__).parent.parent / 'dpdk_suricata_ml_pipeline' / 'logs' / 'ml'
        else:
            self.metrics_dir = Path(metrics_dir)
        
        self.history = deque(maxlen=60)  # Keep last 60 samples
        self.running = False
    
    def get_latest_metrics(self):
        """Get the most recent metrics file."""
        try:
            metrics_files = glob.glob(str(self.metrics_dir / 'performance_metrics_*.json'))
            if not metrics_files:
                return None
            
            # Get most recent file
            latest_file = max(metrics_files, key=os.path.getctime)
            
            with open(latest_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            return None
    
    def calculate_rates(self):
        """Calculate processing rates from history."""
        if len(self.history) < 2:
            return None
        
        old = self.history[0]
        new = self.history[-1]
        
        time_diff = (datetime.fromisoformat(new['timestamp']) - 
                    datetime.fromisoformat(old['timestamp'])).total_seconds()
        
        if time_diff == 0:
            return None
        
        return {
            'events_per_sec': (new['throughput']['events_processed'] - 
                             old['throughput']['events_processed']) / time_diff,
            'predictions_per_sec': (new['throughput']['ml_predictions'] - 
                                   old['throughput']['ml_predictions']) / time_diff,
        }
    
    def display_dashboard(self, metrics, rates):
        """Display real-time dashboard."""
        print(Colors.CLEAR)  # Clear screen
        
        # Header
        print(f"{Colors.BOLD}{Colors.CYAN}╔════════════════════════════════════════════════════════════════╗{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}║           ML IDS Real-Time Performance Dashboard               ║{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}╚════════════════════════════════════════════════════════════════╝{Colors.END}\n")
        
        timestamp = metrics.get('timestamp', 'Unknown')
        runtime = metrics.get('runtime_seconds', 0)
        
        print(f"{Colors.BOLD}Timestamp:{Colors.END} {timestamp}")
        print(f"{Colors.BOLD}Runtime:{Colors.END} {runtime:.0f}s ({runtime/60:.1f} min)")
        print(f"{Colors.BOLD}Model:{Colors.END} {metrics.get('model_name', 'Unknown')}")
        print()
        
        # === REAL-TIME RATES ===
        if rates:
            print(f"{Colors.BOLD}{Colors.GREEN}🚀 REAL-TIME THROUGHPUT{Colors.END}")
            print(f"  Events/sec:      {rates['events_per_sec']:.2f}")
            print(f"  Predictions/sec: {rates['predictions_per_sec']:.2f}")
            print()
        
        # === THROUGHPUT ===
        throughput = metrics.get('throughput', {})
        print(f"{Colors.BOLD}{Colors.BLUE}📊 CUMULATIVE THROUGHPUT{Colors.END}")
        print(f"  Events processed:    {throughput.get('events_processed', 0):,}")
        print(f"  Flows processed:     {throughput.get('flows_processed', 0):,}")
        print(f"  ML predictions:      {throughput.get('ml_predictions', 0):,}")
        print(f"  Avg events/sec:      {throughput.get('events_per_sec', 0):.2f}")
        print(f"  Avg predictions/sec: {throughput.get('predictions_per_sec', 0):.2f}")
        print()
        
        # === LATENCY ===
        latency = metrics.get('latency_ms', {})
        print(f"{Colors.BOLD}{Colors.MAGENTA}⚡ LATENCY (milliseconds){Colors.END}")
        
        inf_latency = latency.get('inference', {})
        print(f"  ML Inference:")
        print(f"    Mean:   {inf_latency.get('mean', 0):.3f} ms")
        print(f"    Median: {inf_latency.get('median', 0):.3f} ms")
        print(f"    P95:    {inf_latency.get('p95', 0):.3f} ms")
        print(f"    P99:    {inf_latency.get('p99', 0):.3f} ms")
        
        total_latency = latency.get('total_processing', {})
        print(f"  Total Processing:")
        print(f"    Mean:   {total_latency.get('mean', 0):.3f} ms")
        print(f"    P95:    {total_latency.get('p95', 0):.3f} ms")
        print()
        
        # === PREDICTIONS ===
        predictions = metrics.get('predictions_by_class', {})
        if predictions:
            print(f"{Colors.BOLD}{Colors.YELLOW}🎯 PREDICTION DISTRIBUTION{Colors.END}")
            total_preds = sum(predictions.values())
            for pred_class, count in sorted(predictions.items(), key=lambda x: x[1], reverse=True)[:5]:
                percentage = (count / total_preds * 100) if total_preds > 0 else 0
                bar_length = int(percentage / 2)
                bar = "█" * bar_length
                print(f"  {pred_class:<15s} {count:>6,} ({percentage:>5.1f}%) {bar}")
            print()
        
        # === CONFIDENCE ===
        confidence = metrics.get('confidence_stats', {})
        print(f"{Colors.BOLD}{Colors.CYAN}📈 CONFIDENCE SCORES{Colors.END}")
        print(f"  Mean:   {confidence.get('mean', 0):.2%}")
        print(f"  Median: {confidence.get('median', 0):.2%}")
        print(f"  Std:    {confidence.get('std', 0):.2%}")
        print()
        
        # === STATUS ===
        errors = metrics.get('errors', 0)
        status_color = Colors.GREEN if errors == 0 else Colors.RED
        print(f"{Colors.BOLD}{status_color}🔧 STATUS{Colors.END}")
        print(f"  Errors: {errors}")
        print()
        
        print(f"{Colors.BOLD}{Colors.CYAN}{'─' * 64}{Colors.END}")
        print(f"{Colors.YELLOW}Press Ctrl+C to stop monitoring{Colors.END}")
    
    def run(self, refresh_interval=5):
        """Run the monitoring dashboard."""
        self.running = True
        print(f"{Colors.GREEN}Starting ML IDS Performance Monitor...{Colors.END}\n")
        print(f"Monitoring directory: {self.metrics_dir}")
        print(f"Refresh interval: {refresh_interval}s\n")
        print("Waiting for metrics data...")
        time.sleep(2)
        
        try:
            while self.running:
                metrics = self.get_latest_metrics()
                
                if metrics:
                    self.history.append(metrics)
                    rates = self.calculate_rates()
                    self.display_dashboard(metrics, rates)
                else:
                    print(f"{Colors.YELLOW}No metrics data found. Waiting...{Colors.END}")
                    print(f"Expected location: {self.metrics_dir}")
                    print(f"\nMake sure the ML consumer is running:")
                    print(f"  cd /home/sujay/Programming/IDS")
                    print(f"  sudo ./run_afpacket_mode.sh start")
                
                time.sleep(refresh_interval)
        
        except KeyboardInterrupt:
            print(f"\n\n{Colors.GREEN}✓ Monitoring stopped{Colors.END}")
    
    def stop(self):
        """Stop monitoring."""
        self.running = False


def generate_report(metrics_dir: str = None):
    """Generate a summary report from all metrics files."""
    if metrics_dir is None:
        metrics_dir = Path(__file__).parent.parent / 'dpdk_suricata_ml_pipeline' / 'logs' / 'ml'
    else:
        metrics_dir = Path(metrics_dir)
    
    print(f"{Colors.BOLD}{Colors.CYAN}╔════════════════════════════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}║           ML IDS Performance Summary Report                    ║{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚════════════════════════════════════════════════════════════════╝{Colors.END}\n")
    
    metrics_files = glob.glob(str(metrics_dir / 'performance_metrics_*.json'))
    
    if not metrics_files:
        print(f"{Colors.RED}No metrics files found in {metrics_dir}{Colors.END}")
        return
    
    print(f"Found {len(metrics_files)} metrics file(s)\n")
    
    all_metrics = []
    for mfile in sorted(metrics_files):
        try:
            with open(mfile, 'r') as f:
                metrics = json.load(f)
                all_metrics.append(metrics)
        except Exception as e:
            print(f"{Colors.RED}Error reading {mfile}: {e}{Colors.END}")
    
    if not all_metrics:
        print(f"{Colors.RED}No valid metrics data found{Colors.END}")
        return
    
    # Aggregate statistics
    print(f"{Colors.BOLD}{Colors.BLUE}📊 AGGREGATE STATISTICS{Colors.END}")
    print(f"  Total sessions: {len(all_metrics)}")
    
    total_events = sum(m['throughput']['events_processed'] for m in all_metrics)
    total_predictions = sum(m['throughput']['ml_predictions'] for m in all_metrics)
    
    print(f"  Total events processed: {total_events:,}")
    print(f"  Total predictions: {total_predictions:,}")
    print()
    
    # Average latency
    print(f"{Colors.BOLD}{Colors.MAGENTA}⚡ AVERAGE LATENCY{Colors.END}")
    avg_inference = np.mean([m['latency_ms']['inference']['mean'] for m in all_metrics])
    avg_total = np.mean([m['latency_ms']['total_processing']['mean'] for m in all_metrics])
    print(f"  Inference: {avg_inference:.3f} ms")
    print(f"  Total:     {avg_total:.3f} ms")
    print()
    
    # List individual sessions
    print(f"{Colors.BOLD}{Colors.YELLOW}📝 SESSION DETAILS{Colors.END}")
    for i, metrics in enumerate(all_metrics[:10], 1):  # Show last 10
        print(f"\n  Session {i}:")
        print(f"    Timestamp: {metrics['timestamp']}")
        print(f"    Model: {metrics['model_name']}")
        print(f"    Runtime: {metrics['runtime_seconds']:.0f}s")
        print(f"    Events: {metrics['throughput']['events_processed']:,}")
        print(f"    Avg latency: {metrics['latency_ms']['inference']['mean']:.3f}ms")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='ML IDS Performance Monitor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor in real-time (default 5s refresh)
  python3 monitor_ml_performance.py
  
  # Monitor with 10s refresh interval
  python3 monitor_ml_performance.py --interval 10
  
  # Generate summary report
  python3 monitor_ml_performance.py --report
  
  # Monitor custom metrics directory
  python3 monitor_ml_performance.py --dir /path/to/metrics
        """
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Refresh interval in seconds (default: 5)'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate summary report instead of live monitoring'
    )
    parser.add_argument(
        '--dir',
        type=str,
        help='Custom metrics directory'
    )
    
    args = parser.parse_args()
    
    if args.report:
        generate_report(args.dir)
    else:
        monitor = PerformanceMonitor(args.dir)
        monitor.run(refresh_interval=args.interval)


if __name__ == '__main__':
    main()
