#!/usr/bin/env python3
"""
Test Metrics Logger

Quick test to verify metrics logging is working correctly.
Generates sample metrics and displays them.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from metrics_logger import MetricsLogger, LatencyTimer

def main():
    print("="*70)
    print("TESTING METRICS LOGGER")
    print("="*70)
    print()
    
    # Create metrics logger
    print("1. Initializing metrics logger...")
    metrics_dir = Path(__file__).parent.parent / 'logs' / 'metrics'
    metrics = MetricsLogger(
        metrics_dir=metrics_dir,
        enable_console=True,
        enable_file=True,
        enable_csv=True,
        flush_interval=5  # Flush every 5 seconds for testing
    )
    metrics.start()
    print(f"   ✓ Metrics directory: {metrics_dir}")
    print()
    
    # Test latency logging
    print("2. Testing latency logging...")
    for i in range(20):
        metrics.log_latency('test_component', 'test_operation', 10.0 + i * 0.5)
        time.sleep(0.1)
    print(f"   ✓ Logged 20 latency measurements")
    print()
    
    # Test with context manager
    print("3. Testing latency timer (context manager)...")
    for i in range(10):
        with LatencyTimer(metrics, 'test_component', 'slow_operation'):
            time.sleep(0.05)  # Simulate work
    print(f"   ✓ Logged 10 timed operations")
    print()
    
    # Test throughput logging
    print("4. Testing throughput logging...")
    metrics.log_throughput('test_component', events_count=1000, bytes_count=1500000, window_seconds=1.0)
    metrics.log_throughput('test_component', events_count=950, bytes_count=1400000, window_seconds=1.0)
    print(f"   ✓ Logged 2 throughput measurements")
    print()
    
    # Test ML inference logging
    print("5. Testing ML inference logging...")
    for i in range(15):
        prediction = 'benign' if i % 3 != 0 else 'malicious'
        confidence = 0.85 + (i % 10) * 0.01
        metrics.log_ml_inference(
            model_name='test_random_forest',
            inference_time_ms=12.5 + i * 0.2,
            prediction=prediction,
            confidence=confidence,
            features_count=34,
            batch_size=1
        )
    print(f"   ✓ Logged 15 ML inference measurements")
    print()
    
    # Test error logging
    print("6. Testing error logging...")
    metrics.log_error('test_component', 'TestError', 'This is a test error', severity='warning')
    metrics.log_error('test_component', 'TestError', 'Another test error', severity='error')
    print(f"   ✓ Logged 2 error events")
    print()
    
    # Test system metrics
    print("7. Testing system metrics logging...")
    try:
        metrics.log_system_metrics()
        print(f"   ✓ Logged system metrics (psutil available)")
    except:
        print(f"   ⚠ System metrics skipped (psutil not installed)")
    print()
    
    # Get statistics
    print("8. Retrieving statistics...")
    print()
    
    print("   Latency Stats:")
    lat_stats = metrics.get_latency_stats('test_component', 'test_operation')
    if lat_stats:
        print(f"     Count: {lat_stats['count']}")
        print(f"     Mean: {lat_stats['mean_ms']:.2f} ms")
        print(f"     Median: {lat_stats['median_ms']:.2f} ms")
        print(f"     P95: {lat_stats['p95_ms']:.2f} ms")
        print(f"     P99: {lat_stats['p99_ms']:.2f} ms")
    print()
    
    print("   Throughput Stats:")
    tp_stats = metrics.get_throughput_stats('test_component')
    if tp_stats:
        print(f"     Total Events: {tp_stats['total_events']:,}")
        print(f"     Avg Events/sec: {tp_stats['avg_events_per_second']:.2f}")
    print()
    
    print("   ML Stats:")
    ml_stats = metrics.get_ml_stats()
    if ml_stats:
        print(f"     Total Predictions: {ml_stats['total_predictions']}")
        print(f"     Predictions by Class:")
        for cls, count in ml_stats.get('predictions_by_class', {}).items():
            print(f"       {cls}: {count}")
    print()
    
    print("   Error Stats:")
    err_stats = metrics.get_error_stats()
    if err_stats:
        print(f"     Total Errors: {err_stats['total_errors']}")
    print()
    
    # Wait for flush
    print("9. Flushing metrics to disk...")
    time.sleep(1)
    metrics.flush_all()
    print(f"   ✓ Metrics flushed")
    print()
    
    # Print summary report
    print("10. Generating summary report...")
    print()
    metrics.print_summary_report()
    
    # Stop metrics logger
    print("\n11. Stopping metrics logger...")
    metrics.stop()
    print(f"   ✓ Stopped")
    print()
    
    # Show output files
    print("12. Generated files:")
    import os
    from datetime import datetime
    date = datetime.now().strftime('%Y%m%d')
    
    files_to_check = [
        f'metrics_{date}.jsonl',
        f'latency_{date}.csv',
        f'throughput_{date}.csv',
        f'ml_{date}.csv',
        f'error_{date}.csv',
    ]
    
    for filename in files_to_check:
        filepath = metrics_dir / filename
        if filepath.exists():
            size = os.path.getsize(filepath)
            print(f"   ✓ {filename} ({size} bytes)")
        else:
            print(f"   - {filename} (not created)")
    print()
    
    print("="*70)
    print("TEST COMPLETE")
    print("="*70)
    print()
    print(f"📂 Metrics saved to: {metrics_dir}")
    print()
    print("Next steps:")
    print("  1. View metrics files:")
    print(f"     ls -lh {metrics_dir}/")
    print()
    print("  2. View JSON metrics:")
    print(f"     tail {metrics_dir}/metrics_{date}.jsonl | jq '.'")
    print()
    print("  3. View CSV metrics:")
    print(f"     column -s, -t < {metrics_dir}/latency_{date}.csv | less -S")
    print()
    print("  4. Run metrics dashboard:")
    print(f"     ./dpdk_suricata_ml_pipeline/scripts/metrics_dashboard.py")
    print()

if __name__ == '__main__':
    main()
