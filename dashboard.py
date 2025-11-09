#!/usr/bin/env python3
"""
IDS Traffic Monitoring Dashboard - Streamlit UI

A comprehensive web-based dashboard for monitoring IDS pipeline metrics in real-time.
Displays latency, throughput, ML predictions, errors, and system resources with
interactive visualizations.

Usage:
    streamlit run dashboard.py
    
    # With custom metrics directory:
    streamlit run dashboard.py -- --metrics-dir /path/to/metrics
"""

import streamlit as st
import json
import time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import argparse
import sys

# Page configuration
st.set_page_config(
    page_title="IDS Traffic Monitor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main > div {
        padding-top: 2rem;
    }
    .stAlert {
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    h1 {
        color: #1f77b4;
    }
    </style>
    """, unsafe_allow_html=True)


def get_metrics_directory():
    """Get metrics directory from command line args or default location."""
    # Check if running via streamlit with args
    if '--' in sys.argv:
        idx = sys.argv.index('--')
        parser = argparse.ArgumentParser()
        parser.add_argument('--metrics-dir', default=None)
        args = parser.parse_args(sys.argv[idx+1:])
        if args.metrics_dir:
            return Path(args.metrics_dir)
    
    # Default location - use the actual metrics directory
    script_dir = Path(__file__).parent
    return script_dir / 'dpdk_suricata_ml_pipeline' / 'logs' / 'metrics'


def load_metrics_file(metrics_dir, lookback_minutes=10):
    """Load recent metrics from JSONL file."""
    metrics_dir = Path(metrics_dir)
    today = datetime.now().strftime('%Y%m%d')
    json_file = metrics_dir / f'metrics_{today}.jsonl'
    
    if not json_file.exists():
        return None
    
    cutoff_time = time.time() - (lookback_minutes * 60)
    
    metrics = {
        'latency': [],
        'throughput': [],
        'ml': [],
        'errors': [],
        'system': []
    }
    
    try:
        with open(json_file, 'r') as f:
            lines = f.readlines()
            for line in lines:
                try:
                    record = json.loads(line)
                    metric_type = record.get('type')
                    
                    # Filter by time (only load recent data)
                    if record.get('timestamp', 0) >= cutoff_time:
                        if metric_type in metrics:
                            metrics[metric_type].append(record)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        st.error(f"Error loading metrics: {e}")
        return None
    
    return metrics


def calculate_statistics(metrics):
    """Calculate comprehensive statistics from metrics."""
    stats = {}
    
    # Latency statistics by component
    latencies_by_comp = defaultdict(list)
    for m in metrics['latency']:
        key = f"{m.get('component', 'unknown')}.{m.get('operation', 'unknown')}"
        latencies_by_comp[key].append(m.get('latency_ms', 0))
    
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
                'p99': sorted_values[int(n * 0.99)] if n > 2 else sorted_values[-1],
            }
    
    # Throughput statistics
    throughput_by_comp = defaultdict(int)
    throughput_rate_by_comp = defaultdict(list)
    for m in metrics['throughput']:
        comp = m.get('component', 'unknown')
        throughput_by_comp[comp] += m.get('events_count', 0)
        throughput_rate_by_comp[comp].append(m.get('events_per_second', 0))
    
    stats['throughput'] = dict(throughput_by_comp)
    stats['throughput_rate'] = {k: sum(v)/len(v) if v else 0 
                                for k, v in throughput_rate_by_comp.items()}
    
    # ML predictions
    ml_predictions = defaultdict(int)
    ml_inference_times = []
    ml_confidence = []
    for m in metrics['ml']:
        ml_predictions[m.get('prediction', 'unknown')] += 1
        ml_inference_times.append(m.get('inference_time_ms', 0))
        ml_confidence.append(m.get('confidence', 0))
    
    stats['ml_predictions'] = dict(ml_predictions)
    stats['ml_inference_mean'] = (sum(ml_inference_times) / len(ml_inference_times) 
                                   if ml_inference_times else 0)
    stats['ml_confidence_mean'] = (sum(ml_confidence) / len(ml_confidence) 
                                    if ml_confidence else 0)
    
    # Error statistics
    error_by_comp = defaultdict(int)
    error_by_severity = defaultdict(int)
    error_by_type = defaultdict(int)
    for m in metrics['errors']:
        error_by_comp[m.get('component', 'unknown')] += 1
        error_by_severity[m.get('severity', 'unknown')] += 1
        error_by_type[m.get('error_type', 'unknown')] += 1
    
    stats['error_counts'] = dict(error_by_comp)
    stats['error_by_severity'] = dict(error_by_severity)
    stats['error_by_type'] = dict(error_by_type)
    
    # System metrics (latest)
    if metrics['system']:
        latest_system = metrics['system'][-1]
        stats['system'] = {
            'cpu_percent': latest_system.get('cpu_percent', 0),
            'memory_percent': latest_system.get('memory_percent', 0),
            'memory_mb': latest_system.get('memory_mb', 0),
            'disk_read_mb': latest_system.get('disk_io_read_mb', 0),
            'disk_write_mb': latest_system.get('disk_io_write_mb', 0),
            'network_rx_mb': latest_system.get('network_rx_mb', 0),
            'network_tx_mb': latest_system.get('network_tx_mb', 0),
        }
    else:
        stats['system'] = {}
    
    return stats


def create_latency_chart(metrics):
    """Create latency time series chart."""
    if not metrics['latency']:
        return None
    
    df = pd.DataFrame(metrics['latency'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    df['component_op'] = df['component'] + '.' + df['operation']
    
    fig = px.line(df, x='datetime', y='latency_ms', color='component_op',
                  title='Latency Over Time',
                  labels={'latency_ms': 'Latency (ms)', 'datetime': 'Time'},
                  height=400)
    
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Latency (ms)",
        hovermode='x unified',
        legend_title="Component"
    )
    
    return fig


def create_throughput_chart(metrics):
    """Create throughput time series chart."""
    if not metrics['throughput']:
        return None
    
    df = pd.DataFrame(metrics['throughput'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    
    fig = px.line(df, x='datetime', y='events_per_second', color='component',
                  title='Throughput Over Time',
                  labels={'events_per_second': 'Events/Second', 'datetime': 'Time'},
                  height=400)
    
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Events/Second",
        hovermode='x unified',
        legend_title="Component"
    )
    
    return fig


def create_ml_predictions_pie(stats):
    """Create ML predictions pie chart."""
    if not stats.get('ml_predictions'):
        return None
    
    predictions = stats['ml_predictions']
    labels = list(predictions.keys())
    values = list(predictions.values())
    
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
    fig.update_layout(
        title="ML Prediction Distribution",
        height=400,
        showlegend=True
    )
    
    return fig


def create_latency_distribution_chart(stats):
    """Create latency distribution comparison chart."""
    if not stats.get('latency'):
        return None
    
    components = []
    p50_values = []
    p95_values = []
    p99_values = []
    
    for comp, values in stats['latency'].items():
        components.append(comp.split('.')[-1][:20])  # Shorten names
        p50_values.append(values['p50'])
        p95_values.append(values['p95'])
        p99_values.append(values['p99'])
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='P50', x=components, y=p50_values))
    fig.add_trace(go.Bar(name='P95', x=components, y=p95_values))
    fig.add_trace(go.Bar(name='P99', x=components, y=p99_values))
    
    fig.update_layout(
        title='Latency Percentiles by Operation',
        xaxis_title='Operation',
        yaxis_title='Latency (ms)',
        barmode='group',
        height=400
    )
    
    return fig


def create_system_metrics_gauges(stats):
    """Create system resource gauge charts."""
    system = stats.get('system', {})
    
    if not system:
        return None
    
    fig = go.Figure()
    
    # CPU gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=system.get('cpu_percent', 0),
        title={'text': "CPU"},
        domain={'row': 0, 'column': 0},
        gauge={'axis': {'range': [None, 100]},
               'bar': {'color': "darkblue"},
               'threshold': {
                   'line': {'color': "red", 'width': 4},
                   'thickness': 0.75,
                   'value': 90
               }}
    ))
    
    # Memory gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=system.get('memory_percent', 0),
        title={'text': "Memory"},
        domain={'row': 0, 'column': 1},
        gauge={'axis': {'range': [None, 100]},
               'bar': {'color': "green"},
               'threshold': {
                   'line': {'color': "red", 'width': 4},
                   'thickness': 0.75,
                   'value': 90
               }}
    ))
    
    fig.update_layout(
        grid={'rows': 1, 'columns': 2, 'pattern': "independent"},
        height=300
    )
    
    return fig


def display_header(metrics_dir, last_update):
    """Display dashboard header."""
    st.title("🛡️ IDS Traffic Monitoring Dashboard")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"**Monitoring:** `{metrics_dir}`")
    with col2:
        st.markdown(f"**Last Update:** {last_update.strftime('%H:%M:%S')}")
    with col3:
        if st.button("🔄 Refresh Now"):
            st.rerun()


def display_overview_metrics(stats):
    """Display overview metrics in cards."""
    st.subheader("📊 Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Total throughput
    with col1:
        total_events = sum(stats.get('throughput', {}).values())
        st.metric(
            label="Total Events Processed",
            value=f"{total_events:,}",
            delta=None
        )
    
    # ML predictions
    with col2:
        total_predictions = sum(stats.get('ml_predictions', {}).values())
        st.metric(
            label="ML Predictions",
            value=f"{total_predictions:,}",
            delta=None
        )
    
    # Average latency
    with col3:
        if stats.get('latency'):
            avg_latency = sum(v['mean'] for v in stats['latency'].values()) / len(stats['latency'])
            st.metric(
                label="Avg Latency",
                value=f"{avg_latency:.2f} ms",
                delta=None
            )
        else:
            st.metric(label="Avg Latency", value="N/A")
    
    # Errors
    with col4:
        total_errors = sum(stats.get('error_counts', {}).values())
        st.metric(
            label="Total Errors",
            value=f"{total_errors:,}",
            delta=None,
            delta_color="inverse" if total_errors > 0 else "off"
        )


def display_latency_section(metrics, stats):
    """Display latency metrics section."""
    st.subheader("⚡ Latency Metrics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Time series chart
        fig = create_latency_chart(metrics)
        if fig:
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No latency data available")
    
    with col2:
        # Distribution chart
        fig = create_latency_distribution_chart(stats)
        if fig:
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No latency statistics available")
    
    # Detailed table
    if stats.get('latency'):
        with st.expander("📋 Detailed Latency Statistics"):
            df = pd.DataFrame.from_dict(stats['latency'], orient='index')
            df = df.round(2)
            df.index.name = 'Component.Operation'
            st.dataframe(df, width='stretch')


def display_throughput_section(metrics, stats):
    """Display throughput metrics section."""
    st.subheader("🚀 Throughput Metrics")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Time series chart
        fig = create_throughput_chart(metrics)
        if fig:
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No throughput data available")
    
    with col2:
        # Summary table
        if stats.get('throughput'):
            st.markdown("**Events Processed by Component**")
            df = pd.DataFrame([
                {'Component': k, 'Events': v, 'Avg Rate/s': stats['throughput_rate'].get(k, 0)}
                for k, v in stats['throughput'].items()
            ])
            df = df.sort_values('Events', ascending=False)
            st.dataframe(df, width='stretch', hide_index=True)
        else:
            st.info("No throughput data available")


def display_ml_section(stats):
    """Display ML predictions section."""
    st.subheader("🤖 ML Predictions")
    
    if not stats.get('ml_predictions'):
        st.info("No ML prediction data available")
        return
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Pie chart
        fig = create_ml_predictions_pie(stats)
        if fig:
            st.plotly_chart(fig, width='stretch')
    
    with col2:
        # Statistics
        st.markdown("**ML Performance**")
        
        total = sum(stats['ml_predictions'].values())
        st.metric("Total Predictions", f"{total:,}")
        st.metric("Avg Inference Time", f"{stats.get('ml_inference_mean', 0):.2f} ms")
        st.metric("Avg Confidence", f"{stats.get('ml_confidence_mean', 0):.2%}")
        
        # Prediction breakdown
        st.markdown("**Prediction Breakdown**")
        for pred, count in sorted(stats['ml_predictions'].items(), key=lambda x: x[1], reverse=True):
            pct = (count / total * 100) if total > 0 else 0
            st.markdown(f"- **{pred}**: {count:,} ({pct:.1f}%)")


def display_system_section(stats):
    """Display system resources section."""
    st.subheader("💻 System Resources")
    
    if not stats.get('system'):
        st.info("No system metrics available")
        return
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Gauges
        fig = create_system_metrics_gauges(stats)
        if fig:
            st.plotly_chart(fig, width='stretch')
    
    with col2:
        # Detailed metrics
        system = stats['system']
        st.markdown("**Resource Usage**")
        
        st.metric("CPU Usage", f"{system.get('cpu_percent', 0):.1f}%")
        st.metric("Memory Usage", f"{system.get('memory_mb', 0):.1f} MB ({system.get('memory_percent', 0):.1f}%)")
        
        st.markdown("**I/O Statistics**")
        st.metric("Disk Read", f"{system.get('disk_read_mb', 0):.2f} MB")
        st.metric("Disk Write", f"{system.get('disk_write_mb', 0):.2f} MB")
        st.metric("Network RX", f"{system.get('network_rx_mb', 0):.2f} MB")
        st.metric("Network TX", f"{system.get('network_tx_mb', 0):.2f} MB")


def display_errors_section(stats):
    """Display errors section."""
    st.subheader("⚠️ Errors & Warnings")
    
    if not stats.get('error_counts'):
        st.success("✅ No errors detected!")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Errors by Component**")
        for comp, count in sorted(stats['error_counts'].items(), key=lambda x: x[1], reverse=True):
            st.markdown(f"- **{comp}**: {count}")
    
    with col2:
        st.markdown("**Errors by Severity**")
        for severity, count in sorted(stats['error_by_severity'].items()):
            if severity == 'critical':
                st.error(f"🔴 {severity.upper()}: {count}")
            elif severity == 'error':
                st.warning(f"🟠 {severity.upper()}: {count}")
            else:
                st.info(f"🟡 {severity.upper()}: {count}")


def display_sidebar(metrics_dir):
    """Display sidebar with controls and information."""
    with st.sidebar:
        st.header("⚙️ Dashboard Settings")
        
        # Auto-refresh control
        refresh_interval = st.slider(
            "Auto-refresh interval (seconds)",
            min_value=1,
            max_value=60,
            value=5,
            help="How often to refresh the dashboard"
        )
        
        # Lookback window
        lookback_minutes = st.slider(
            "Data lookback window (minutes)",
            min_value=1,
            max_value=60,
            value=10,
            help="How much historical data to display"
        )
        
        st.divider()
        
        # Pipeline status
        st.header("📡 Pipeline Status")
        
        metrics_file = metrics_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl"
        if metrics_file.exists():
            file_size = metrics_file.stat().st_size / (1024 * 1024)  # MB
            mod_time = datetime.fromtimestamp(metrics_file.stat().st_mtime)
            
            st.success("✅ Metrics file active")
            st.metric("File Size", f"{file_size:.2f} MB")
            st.metric("Last Modified", mod_time.strftime("%H:%M:%S"))
        else:
            st.error("❌ No metrics file found")
            st.info("Start your IDS pipeline to generate metrics")
        
        st.divider()
        
        # Information
        st.header("ℹ️ Information")
        st.markdown("""
        **About:**
        Real-time monitoring dashboard for the IDS pipeline.
        
        **Metrics Tracked:**
        - ⚡ Latency (per component)
        - 🚀 Throughput (events/sec)
        - 🤖 ML Predictions
        - ⚠️ Errors & Warnings
        - 💻 System Resources
        
        **How to Use:**
        1. Start your IDS pipeline
        2. Metrics will appear automatically
        3. Use controls above to adjust view
        """)
        
        return refresh_interval, lookback_minutes


def main():
    """Main dashboard application."""
    # Get metrics directory
    metrics_dir = get_metrics_directory()
    
    # Sidebar controls
    refresh_interval, lookback_minutes = display_sidebar(metrics_dir)
    
    # Check if metrics directory exists
    if not metrics_dir.exists():
        st.error(f"❌ Metrics directory not found: {metrics_dir}")
        st.info("""
        **To fix this:**
        1. Make sure your IDS pipeline is running
        2. Check that metrics are being generated in `logs/metrics/`
        3. Or specify a custom directory: `streamlit run dashboard.py -- --metrics-dir /path/to/metrics`
        """)
        st.stop()
    
    # Load metrics
    metrics = load_metrics_file(metrics_dir, lookback_minutes)
    
    if not metrics:
        st.warning("⏳ Waiting for metrics data...")
        st.info(f"""
        **Monitoring:** `{metrics_dir}`
        
        **Waiting for:** `metrics_{datetime.now().strftime('%Y%m%d')}.jsonl`
        
        **Next steps:**
        1. Start your IDS pipeline: `sudo ./run_afpacket_mode.sh` or `sudo ./run_dpdk_mode.sh`
        2. Wait for metrics to be generated
        3. This dashboard will update automatically
        """)
        
        # Auto-refresh
        time.sleep(refresh_interval)
        st.rerun()
        return
    
    # Calculate statistics
    stats = calculate_statistics(metrics)
    
    # Display dashboard
    display_header(metrics_dir, datetime.now())
    
    st.divider()
    
    # Overview metrics
    display_overview_metrics(stats)
    
    st.divider()
    
    # Main sections
    display_latency_section(metrics, stats)
    
    st.divider()
    
    display_throughput_section(metrics, stats)
    
    st.divider()
    
    display_ml_section(stats)
    
    st.divider()
    
    display_system_section(stats)
    
    st.divider()
    
    display_errors_section(stats)
    
    # Auto-refresh
    time.sleep(refresh_interval)
    st.rerun()


if __name__ == "__main__":
    main()
