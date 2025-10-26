#!/usr/bin/env python3
"""
Comprehensive Metrics Logger for IDS Pipeline

Tracks and logs performance metrics including:
- Latency (end-to-end, per-component)
- Throughput (events/sec, bytes/sec)
- ML model performance (inference time, accuracy)
- System resource usage
- Error rates
- Queue depths
- Event statistics

Metrics are logged to:
1. JSON file (for time-series analysis)
2. CSV file (for spreadsheet analysis)
3. Real-time console output
4. Prometheus-compatible format (optional)
"""

import json
import csv
import time
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import statistics

logger = logging.getLogger(__name__)


@dataclass
class LatencyMetric:
    """Individual latency measurement"""
    timestamp: float
    component: str
    operation: str
    latency_ms: float
    event_type: Optional[str] = None
    flow_id: Optional[str] = None


@dataclass
class ThroughputMetric:
    """Throughput measurement over time window"""
    timestamp: float
    component: str
    events_count: int
    bytes_count: int
    window_seconds: float
    events_per_second: float
    bytes_per_second: float


@dataclass
class MLMetric:
    """ML model performance metric"""
    timestamp: float
    model_name: str
    inference_time_ms: float
    prediction: str
    confidence: float
    features_count: int
    batch_size: int


@dataclass
class ErrorMetric:
    """Error tracking metric"""
    timestamp: float
    component: str
    error_type: str
    error_message: str
    severity: str  # 'warning', 'error', 'critical'


@dataclass
class SystemMetric:
    """System resource usage metric"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_rx_mb: float
    network_tx_mb: float


class MetricsLogger:
    """
    Centralized metrics collection and logging system.
    
    Thread-safe, low-overhead metrics collection with multiple output formats.
    """
    
    def __init__(self, 
                 metrics_dir: str = None,
                 enable_console: bool = True,
                 enable_file: bool = True,
                 enable_csv: bool = True,
                 buffer_size: int = 1000,
                 flush_interval: int = 30):
        """
        Initialize metrics logger.
        
        Args:
            metrics_dir: Directory to store metrics files
            enable_console: Enable real-time console output
            enable_file: Enable JSON file logging
            enable_csv: Enable CSV file logging
            buffer_size: Number of metrics to buffer before flush
            flush_interval: Seconds between automatic flushes
        """
        # Setup metrics directory
        if metrics_dir is None:
            metrics_dir = Path(__file__).parent.parent / 'logs' / 'metrics'
        else:
            metrics_dir = Path(metrics_dir)
        
        metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_dir = metrics_dir
        
        # Configuration
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.enable_csv = enable_csv
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        
        # Metric buffers (thread-safe with locks)
        self.latency_buffer = deque(maxlen=buffer_size)
        self.throughput_buffer = deque(maxlen=buffer_size)
        self.ml_buffer = deque(maxlen=buffer_size)
        self.error_buffer = deque(maxlen=buffer_size)
        self.system_buffer = deque(maxlen=buffer_size)
        
        # Locks for thread safety
        self.latency_lock = threading.Lock()
        self.throughput_lock = threading.Lock()
        self.ml_lock = threading.Lock()
        self.error_lock = threading.Lock()
        self.system_lock = threading.Lock()
        
        # Running statistics (lightweight, real-time)
        self.stats = {
            'latency': defaultdict(list),  # component -> [latencies]
            'throughput': defaultdict(int),  # component -> event_count
            'ml_predictions': defaultdict(int),  # prediction_class -> count
            'errors': defaultdict(int),  # component -> error_count
            'start_time': time.time(),
        }
        
        # Rolling window for percentile calculations (last 1000 measurements)
        self.latency_windows = defaultdict(lambda: deque(maxlen=1000))
        
        # File handles (opened lazily)
        self.json_file = None
        self.csv_files = {}
        
        # Background flush thread
        self.running = False
        self.flush_thread = None
        
        logger.info(f"Metrics logger initialized: {self.metrics_dir}")
    
    def start(self):
        """Start background metrics flushing."""
        if self.running:
            return
        
        self.running = True
        self.flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self.flush_thread.start()
        logger.info("Metrics logger started")
    
    def stop(self):
        """Stop and flush all metrics."""
        if not self.running:
            return
        
        self.running = False
        if self.flush_thread:
            self.flush_thread.join(timeout=5)
        
        # Final flush
        self.flush_all()
        
        # Close file handles
        if self.json_file:
            self.json_file.close()
        for f in self.csv_files.values():
            f.close()
        
        logger.info("Metrics logger stopped")
    
    def _flush_loop(self):
        """Background thread that periodically flushes metrics."""
        while self.running:
            time.sleep(self.flush_interval)
            if self.running:  # Check again after sleep
                self.flush_all()
    
    # ========== Latency Tracking ==========
    
    def log_latency(self, 
                    component: str,
                    operation: str,
                    latency_ms: float,
                    event_type: str = None,
                    flow_id: str = None):
        """
        Log a latency measurement.
        
        Args:
            component: Component name (e.g., 'suricata', 'ml_consumer', 'kafka_bridge')
            operation: Operation name (e.g., 'packet_processing', 'ml_inference', 'kafka_send')
            latency_ms: Latency in milliseconds
            event_type: Optional event type
            flow_id: Optional flow identifier
        """
        metric = LatencyMetric(
            timestamp=time.time(),
            component=component,
            operation=operation,
            latency_ms=latency_ms,
            event_type=event_type,
            flow_id=flow_id
        )
        
        with self.latency_lock:
            self.latency_buffer.append(metric)
            
            # Update running statistics
            key = f"{component}.{operation}"
            self.stats['latency'][key].append(latency_ms)
            self.latency_windows[key].append(latency_ms)
            
            # Keep running stats lightweight (last 100 samples)
            if len(self.stats['latency'][key]) > 100:
                self.stats['latency'][key] = self.stats['latency'][key][-100:]
    
    def get_latency_stats(self, component: str = None, operation: str = None) -> Dict:
        """
        Get latency statistics.
        
        Returns:
            Dict with min, max, mean, median, p95, p99
        """
        with self.latency_lock:
            if component and operation:
                key = f"{component}.{operation}"
                latencies = list(self.latency_windows[key])
            else:
                # All latencies
                latencies = []
                for values in self.latency_windows.values():
                    latencies.extend(values)
            
            if not latencies:
                return {}
            
            sorted_latencies = sorted(latencies)
            n = len(sorted_latencies)
            
            return {
                'count': n,
                'min_ms': min(sorted_latencies),
                'max_ms': max(sorted_latencies),
                'mean_ms': statistics.mean(sorted_latencies),
                'median_ms': statistics.median(sorted_latencies),
                'p95_ms': sorted_latencies[int(n * 0.95)] if n > 0 else 0,
                'p99_ms': sorted_latencies[int(n * 0.99)] if n > 0 else 0,
                'stdev_ms': statistics.stdev(sorted_latencies) if n > 1 else 0,
            }
    
    # ========== Throughput Tracking ==========
    
    def log_throughput(self,
                       component: str,
                       events_count: int,
                       bytes_count: int = 0,
                       window_seconds: float = 1.0):
        """
        Log throughput measurement.
        
        Args:
            component: Component name
            events_count: Number of events processed
            bytes_count: Number of bytes processed (optional)
            window_seconds: Time window for measurement
        """
        metric = ThroughputMetric(
            timestamp=time.time(),
            component=component,
            events_count=events_count,
            bytes_count=bytes_count,
            window_seconds=window_seconds,
            events_per_second=events_count / window_seconds if window_seconds > 0 else 0,
            bytes_per_second=bytes_count / window_seconds if window_seconds > 0 else 0
        )
        
        with self.throughput_lock:
            self.throughput_buffer.append(metric)
            self.stats['throughput'][component] += events_count
    
    def get_throughput_stats(self, component: str = None) -> Dict:
        """Get throughput statistics."""
        with self.throughput_lock:
            if component:
                total_events = self.stats['throughput'][component]
            else:
                total_events = sum(self.stats['throughput'].values())
            
            uptime = time.time() - self.stats['start_time']
            avg_events_per_sec = total_events / uptime if uptime > 0 else 0
            
            return {
                'total_events': total_events,
                'uptime_seconds': uptime,
                'avg_events_per_second': avg_events_per_sec,
            }
    
    # ========== ML Metrics Tracking ==========
    
    def log_ml_inference(self,
                        model_name: str,
                        inference_time_ms: float,
                        prediction: str,
                        confidence: float,
                        features_count: int,
                        batch_size: int = 1):
        """
        Log ML model inference metrics.
        
        Args:
            model_name: Name of the ML model
            inference_time_ms: Inference latency in milliseconds
            prediction: Prediction result (class name)
            confidence: Prediction confidence (0-1)
            features_count: Number of features used
            batch_size: Batch size (if batch inference)
        """
        metric = MLMetric(
            timestamp=time.time(),
            model_name=model_name,
            inference_time_ms=inference_time_ms,
            prediction=prediction,
            confidence=confidence,
            features_count=features_count,
            batch_size=batch_size
        )
        
        with self.ml_lock:
            self.ml_buffer.append(metric)
            self.stats['ml_predictions'][prediction] += 1
    
    def get_ml_stats(self) -> Dict:
        """Get ML inference statistics."""
        with self.ml_lock:
            # Get inference time stats from last N samples
            inference_times = [m.inference_time_ms for m in list(self.ml_buffer)]
            
            stats = {
                'total_predictions': sum(self.stats['ml_predictions'].values()),
                'predictions_by_class': dict(self.stats['ml_predictions']),
            }
            
            if inference_times:
                stats['inference_latency'] = {
                    'min_ms': min(inference_times),
                    'max_ms': max(inference_times),
                    'mean_ms': statistics.mean(inference_times),
                    'median_ms': statistics.median(inference_times),
                }
            
            return stats
    
    # ========== Error Tracking ==========
    
    def log_error(self,
                  component: str,
                  error_type: str,
                  error_message: str,
                  severity: str = 'error'):
        """
        Log an error.
        
        Args:
            component: Component where error occurred
            error_type: Type of error (e.g., 'KafkaError', 'ModelError')
            error_message: Error message
            severity: 'warning', 'error', or 'critical'
        """
        metric = ErrorMetric(
            timestamp=time.time(),
            component=component,
            error_type=error_type,
            error_message=error_message,
            severity=severity
        )
        
        with self.error_lock:
            self.error_buffer.append(metric)
            self.stats['errors'][component] += 1
        
        # Log to standard logger too
        log_func = {
            'warning': logger.warning,
            'error': logger.error,
            'critical': logger.critical
        }.get(severity, logger.error)
        
        log_func(f"[{component}] {error_type}: {error_message}")
    
    def get_error_stats(self) -> Dict:
        """Get error statistics."""
        with self.error_lock:
            return {
                'total_errors': sum(self.stats['errors'].values()),
                'errors_by_component': dict(self.stats['errors']),
            }
    
    # ========== System Metrics Tracking ==========
    
    def log_system_metrics(self):
        """
        Log current system resource usage.
        
        Requires psutil library. Safe to call even if psutil not installed.
        """
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            mem = psutil.virtual_memory()
            memory_mb = mem.used / (1024 * 1024)
            memory_percent = mem.percent
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            disk_read_mb = disk_io.read_bytes / (1024 * 1024)
            disk_write_mb = disk_io.write_bytes / (1024 * 1024)
            
            # Network I/O
            net_io = psutil.net_io_counters()
            network_rx_mb = net_io.bytes_recv / (1024 * 1024)
            network_tx_mb = net_io.bytes_sent / (1024 * 1024)
            
            metric = SystemMetric(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                disk_io_read_mb=disk_read_mb,
                disk_io_write_mb=disk_write_mb,
                network_rx_mb=network_rx_mb,
                network_tx_mb=network_tx_mb
            )
            
            with self.system_lock:
                self.system_buffer.append(metric)
                
        except ImportError:
            # psutil not installed, skip system metrics
            pass
        except Exception as e:
            logger.debug(f"Error collecting system metrics: {e}")
    
    # ========== Summary Report ==========
    
    def get_summary_report(self) -> Dict:
        """
        Get comprehensive summary of all metrics.
        
        Returns:
            Dict containing all metric summaries
        """
        uptime = time.time() - self.stats['start_time']
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': uptime,
            'uptime_human': self._format_duration(uptime),
            'latency': self.get_latency_stats(),
            'throughput': self.get_throughput_stats(),
            'ml': self.get_ml_stats(),
            'errors': self.get_error_stats(),
        }
        
        return report
    
    def print_summary_report(self):
        """Print human-readable summary report to console."""
        report = self.get_summary_report()
        
        print("\n" + "="*70)
        print("METRICS SUMMARY REPORT")
        print("="*70)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Uptime: {report['uptime_human']}")
        print()
        
        # Throughput
        print("THROUGHPUT:")
        tp = report['throughput']
        print(f"  Total Events: {tp.get('total_events', 0):,}")
        print(f"  Avg Events/sec: {tp.get('avg_events_per_second', 0):.2f}")
        print()
        
        # Latency
        print("LATENCY:")
        lat = report['latency']
        if lat:
            print(f"  Mean: {lat.get('mean_ms', 0):.2f} ms")
            print(f"  Median: {lat.get('median_ms', 0):.2f} ms")
            print(f"  P95: {lat.get('p95_ms', 0):.2f} ms")
            print(f"  P99: {lat.get('p99_ms', 0):.2f} ms")
            print(f"  Min: {lat.get('min_ms', 0):.2f} ms")
            print(f"  Max: {lat.get('max_ms', 0):.2f} ms")
        else:
            print("  No data")
        print()
        
        # ML
        print("ML INFERENCE:")
        ml = report['ml']
        print(f"  Total Predictions: {ml.get('total_predictions', 0):,}")
        if 'predictions_by_class' in ml:
            print("  Predictions by Class:")
            for cls, count in sorted(ml['predictions_by_class'].items()):
                print(f"    {cls}: {count:,}")
        if 'inference_latency' in ml:
            inf_lat = ml['inference_latency']
            print(f"  Inference Latency: {inf_lat.get('mean_ms', 0):.2f} ms (mean)")
        print()
        
        # Errors
        print("ERRORS:")
        err = report['errors']
        print(f"  Total Errors: {err.get('total_errors', 0)}")
        if err.get('errors_by_component'):
            print("  Errors by Component:")
            for comp, count in sorted(err['errors_by_component'].items()):
                print(f"    {comp}: {count}")
        print()
        
        print("="*70)
    
    # ========== File Output ==========
    
    def flush_all(self):
        """Flush all metric buffers to files."""
        if self.enable_file:
            self._flush_to_json()
        if self.enable_csv:
            self._flush_to_csv()
    
    def _flush_to_json(self):
        """Flush metrics to JSON lines file."""
        timestamp = datetime.now().strftime('%Y%m%d')
        json_path = self.metrics_dir / f'metrics_{timestamp}.jsonl'
        
        try:
            with open(json_path, 'a') as f:
                # Flush latency metrics
                with self.latency_lock:
                    for metric in self.latency_buffer:
                        record = {
                            'type': 'latency',
                            **asdict(metric)
                        }
                        f.write(json.dumps(record) + '\n')
                    self.latency_buffer.clear()
                
                # Flush throughput metrics
                with self.throughput_lock:
                    for metric in self.throughput_buffer:
                        record = {
                            'type': 'throughput',
                            **asdict(metric)
                        }
                        f.write(json.dumps(record) + '\n')
                    self.throughput_buffer.clear()
                
                # Flush ML metrics
                with self.ml_lock:
                    for metric in self.ml_buffer:
                        record = {
                            'type': 'ml',
                            **asdict(metric)
                        }
                        f.write(json.dumps(record) + '\n')
                    self.ml_buffer.clear()
                
                # Flush error metrics
                with self.error_lock:
                    for metric in self.error_buffer:
                        record = {
                            'type': 'error',
                            **asdict(metric)
                        }
                        f.write(json.dumps(record) + '\n')
                    self.error_buffer.clear()
                
                # Flush system metrics
                with self.system_lock:
                    for metric in self.system_buffer:
                        record = {
                            'type': 'system',
                            **asdict(metric)
                        }
                        f.write(json.dumps(record) + '\n')
                    self.system_buffer.clear()
                
        except Exception as e:
            logger.error(f"Error flushing metrics to JSON: {e}")
    
    def _flush_to_csv(self):
        """Flush metrics to CSV files (one per metric type)."""
        timestamp = datetime.now().strftime('%Y%m%d')
        
        try:
            # Latency CSV
            self._write_csv('latency', timestamp, 
                          ['timestamp', 'component', 'operation', 'latency_ms', 'event_type', 'flow_id'],
                          self.latency_buffer, self.latency_lock)
            
            # Throughput CSV
            self._write_csv('throughput', timestamp,
                          ['timestamp', 'component', 'events_count', 'bytes_count', 
                           'window_seconds', 'events_per_second', 'bytes_per_second'],
                          self.throughput_buffer, self.throughput_lock)
            
            # ML CSV
            self._write_csv('ml', timestamp,
                          ['timestamp', 'model_name', 'inference_time_ms', 'prediction', 
                           'confidence', 'features_count', 'batch_size'],
                          self.ml_buffer, self.ml_lock)
            
            # Error CSV
            self._write_csv('error', timestamp,
                          ['timestamp', 'component', 'error_type', 'error_message', 'severity'],
                          self.error_buffer, self.error_lock)
            
        except Exception as e:
            logger.error(f"Error flushing metrics to CSV: {e}")
    
    def _write_csv(self, metric_type: str, date: str, fieldnames: List[str], 
                   buffer: deque, lock: threading.Lock):
        """Write metrics from buffer to CSV file."""
        csv_path = self.metrics_dir / f'{metric_type}_{date}.csv'
        
        # Check if file exists to determine if we need to write header
        file_exists = csv_path.exists()
        
        with lock:
            if not buffer:
                return  # Nothing to write
            
            with open(csv_path, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                if not file_exists:
                    writer.writeheader()
                
                for metric in buffer:
                    row = asdict(metric)
                    writer.writerow(row)
                
                buffer.clear()
    
    # ========== Context Manager Support ==========
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
    
    # ========== Helper Methods ==========
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        else:
            return f"{seconds/86400:.1f}d"


# ========== Context Manager for Latency Measurement ==========

class LatencyTimer:
    """
    Context manager for easy latency measurement.
    
    Usage:
        with LatencyTimer(metrics_logger, 'ml_consumer', 'feature_extraction'):
            # Code to measure
            extract_features()
    """
    
    def __init__(self, 
                 metrics_logger: MetricsLogger,
                 component: str,
                 operation: str,
                 event_type: str = None,
                 flow_id: str = None):
        self.metrics_logger = metrics_logger
        self.component = component
        self.operation = operation
        self.event_type = event_type
        self.flow_id = flow_id
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            latency_ms = (time.time() - self.start_time) * 1000
            self.metrics_logger.log_latency(
                component=self.component,
                operation=self.operation,
                latency_ms=latency_ms,
                event_type=self.event_type,
                flow_id=self.flow_id
            )


# ========== Global Instance (Optional) ==========

# You can create a global instance for easy access across modules
_global_metrics_logger = None

def get_metrics_logger() -> MetricsLogger:
    """Get or create global metrics logger instance."""
    global _global_metrics_logger
    if _global_metrics_logger is None:
        _global_metrics_logger = MetricsLogger()
        _global_metrics_logger.start()
    return _global_metrics_logger


# ========== Example Usage ==========

if __name__ == '__main__':
    """Example usage and testing."""
    print("Testing Metrics Logger...\n")
    
    # Create metrics logger
    metrics = MetricsLogger(enable_console=True)
    metrics.start()
    
    # Simulate some metrics
    print("Generating sample metrics...")
    
    # Log latency
    for i in range(100):
        metrics.log_latency('ml_consumer', 'ml_inference', 10.5 + i*0.1)
        metrics.log_latency('kafka_bridge', 'kafka_send', 2.0 + i*0.05)
    
    # Log throughput
    metrics.log_throughput('suricata', events_count=1000, bytes_count=1500000, window_seconds=1.0)
    metrics.log_throughput('ml_consumer', events_count=950, bytes_count=0, window_seconds=1.0)
    
    # Log ML inference
    for i in range(50):
        metrics.log_ml_inference(
            model_name='random_forest',
            inference_time_ms=12.3,
            prediction='benign' if i % 10 != 0 else 'malicious',
            confidence=0.95,
            features_count=34,
            batch_size=1
        )
    
    # Log some errors
    metrics.log_error('kafka_bridge', 'KafkaTimeout', 'Connection timeout', severity='warning')
    metrics.log_error('ml_consumer', 'ModelError', 'Invalid feature shape', severity='error')
    
    # Wait a bit
    time.sleep(2)
    
    # Print summary
    metrics.print_summary_report()
    
    # Stop and cleanup
    metrics.stop()
    
    print("\nMetrics saved to:", metrics.metrics_dir)
    print("\nTest complete!")
