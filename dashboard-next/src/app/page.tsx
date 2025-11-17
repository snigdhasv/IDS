'use client';

import { useState, useEffect, useRef } from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface MetricsData {
  timestamp: string;
  ml: {
    total: number;
    benign: number;
    attack: number;
    avg_confidence: number;
    recent: Array<{ ts: string; label: string; raw_label?: string; confidence: number }>;
    label_counts?: Record<string, number>;
  };
  suricata_alerts: {
    alerts: number;
    recent: string[];
  };
  metrics: {
    latency?: {
      p95_ms: number;
    };
    system?: {
      cpu_percent: number;
      memory_percent: number;
      memory_mb: number;
    };
    throughput?: Record<string, number>;
  };
  feature_engine: {
    approx_events: number;
    recent_lines: string[];
  };
  suricata_events: {
    events: Array<{
      timestamp: string;
      type: string;
      src_ip?: string;
      dest_ip?: string;
      signature?: string;
      details?: string;
    }>;
    alerts: number;
    flows: number;
  };
}

interface AggregatedMetrics {
  ml: {
    total: number;
    benign: number;
    attack: number;
    labels: Record<string, number>;
  };
  suricataEvents: {
    events: number;
    alerts: number;
    flows: number;
  };
  throughput: Record<string, number>;
}

const createEmptyAggregates = (): AggregatedMetrics => ({
  ml: { total: 0, benign: 0, attack: 0, labels: {} },
  suricataEvents: { events: 0, alerts: 0, flows: 0 },
  throughput: {},
});

const deriveLabelCounts = (
  recent: MetricsData['ml']['recent'] | undefined
): Record<string, number> => {
  const counts: Record<string, number> = {};
  (recent || []).forEach((entry) => {
    const label = entry?.label || entry?.raw_label;
    if (!label) {
      return;
    }
    if (label.toUpperCase().startsWith('BENIGN')) {
      return;
    }
    counts[label] = (counts[label] || 0) + 1;
  });
  return counts;
};

export default function Dashboard() {
  const [data, setData] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cumulativeMode, setCumulativeMode] = useState(false);
  const [aggregates, setAggregates] = useState<AggregatedMetrics>(() => createEmptyAggregates());
  const prevSnapshotRef = useRef<MetricsData | null>(null);
  const aggregateStartRef = useRef<string | null>(null);

  const fetchData = async () => {
    try {
      const response = await fetch('/api/summary');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  const computeIncrement = (current?: number, previous?: number) => {
    const curr = current ?? 0;
    const prevVal = previous ?? 0;
    const delta = curr - prevVal;
    return delta > 0 ? delta : 0;
  };

  const resetAggregates = () => {
    setAggregates(createEmptyAggregates());
    prevSnapshotRef.current = data;
    aggregateStartRef.current = new Date().toISOString();
  };

  const handleCumulativeToggle = () => {
    if (!cumulativeMode) {
      resetAggregates();
      setCumulativeMode(true);
    } else {
      setCumulativeMode(false);
      aggregateStartRef.current = null;
    }
  };

  useEffect(() => {
    if (!data) return;
    const prev = prevSnapshotRef.current;
    if (!prev) {
      prevSnapshotRef.current = data;
      return;
    }

    setAggregates((prevAgg) => {
      const snapshotMl = data.ml || { total: 0, benign: 0, attack: 0, label_counts: {} };
      const prevMl = prev.ml || { total: 0, benign: 0, attack: 0, label_counts: {} };
      const nextMlLabels = { ...prevAgg.ml.labels };
      const snapshotLabelCounts = Object.keys(snapshotMl.label_counts || {}).length
        ? snapshotMl.label_counts!
        : deriveLabelCounts(snapshotMl.recent);
      const prevLabelCounts = Object.keys(prevMl.label_counts || {}).length
        ? prevMl.label_counts!
        : deriveLabelCounts(prevMl.recent);
      Object.keys(snapshotLabelCounts).forEach((label) => {
        const diff = computeIncrement(snapshotLabelCounts[label], prevLabelCounts[label]);
        if (diff > 0) {
          nextMlLabels[label] = (nextMlLabels[label] || 0) + diff;
        }
      });

      const throughputSnapshot = data.metrics?.throughput || {};
      const prevThroughput = prev.metrics?.throughput || {};
      const nextThroughput = { ...prevAgg.throughput };
      Object.keys(throughputSnapshot).forEach((key) => {
        const diff = computeIncrement(throughputSnapshot[key], prevThroughput[key]);
        if (diff > 0) {
          nextThroughput[key] = (nextThroughput[key] || 0) + diff;
        }
      });

      return {
        ml: {
          total: prevAgg.ml.total + computeIncrement(snapshotMl.total, prevMl.total),
          benign: prevAgg.ml.benign + computeIncrement(snapshotMl.benign, prevMl.benign),
          attack: prevAgg.ml.attack + computeIncrement(snapshotMl.attack, prevMl.attack),
          labels: nextMlLabels,
        },
        suricataEvents: {
          events:
            prevAgg.suricataEvents.events +
            computeIncrement(data.suricata_events?.events?.length, prev.suricata_events?.events?.length),
          alerts:
            prevAgg.suricataEvents.alerts +
            computeIncrement(data.suricata_events?.alerts, prev.suricata_events?.alerts),
          flows:
            prevAgg.suricataEvents.flows +
            computeIncrement(data.suricata_events?.flows, prev.suricata_events?.flows),
        },
        throughput: nextThroughput,
      };
    });

    prevSnapshotRef.current = data;
  }, [data]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">IDS Dashboard</h1>
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">IDS Dashboard</h1>
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            <strong>Error:</strong> {error}
          </div>
          <button
            onClick={fetchData}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">IDS Dashboard</h1>
          <div className="text-center py-12">
            <p className="text-gray-600">No data available</p>
          </div>
        </div>
      </div>
    );
  }

  const aggregatesEmpty =
    aggregates.ml.total === 0 &&
    aggregates.suricataEvents.events === 0 &&
    aggregates.suricataEvents.alerts === 0 &&
    aggregates.suricataEvents.flows === 0 &&
    Object.values(aggregates.throughput).length === 0;

  const isCumulativeView = cumulativeMode;
  const snapshotMl = {
    total: data?.ml?.total ?? 0,
    benign: data?.ml?.benign ?? 0,
    attack: data?.ml?.attack ?? 0,
  };
  const mlView = isCumulativeView
    ? {
        total: aggregates.ml.total,
        benign: aggregates.ml.benign,
        attack: aggregates.ml.attack,
      }
    : snapshotMl;
  const snapshotLabelCounts = data.ml?.label_counts;
  const fallbackSnapshotLabelCounts = deriveLabelCounts(data.ml?.recent);
  const labelCounts = isCumulativeView
    ? aggregates.ml.labels
    : Object.keys(snapshotLabelCounts || {}).length
      ? snapshotLabelCounts!
      : fallbackSnapshotLabelCounts;
  const labelEntries = Object.entries(labelCounts)
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1]);
  const suricataEventsCounts = isCumulativeView
    ? aggregates.suricataEvents
    : {
        events: data?.suricata_events?.events?.length ?? 0,
        alerts: data?.suricata_events?.alerts ?? 0,
        flows: data?.suricata_events?.flows ?? 0,
      };
  const throughputSource = isCumulativeView
    ? aggregates.throughput
    : data.metrics?.throughput || {};
  const totalThroughput = Object.values(throughputSource).reduce((sum, val) => sum + val, 0);
  const throughputDetails =
    Object.entries(throughputSource).length > 0
      ? Object.entries(throughputSource)
          .map(([k, v]) => `${k}: ${v}`)
          .join(' | ')
      : 'No throughput data';
  const aggregateStartLabel = aggregateStartRef.current
    ? new Date(aggregateStartRef.current).toLocaleTimeString()
    : null;
  const aggregateDurationSeconds = aggregateStartRef.current
    ? Math.max(1, (Date.now() - new Date(aggregateStartRef.current).getTime()) / 1000)
    : null;
  const aggregatedThroughputPerSecond =
    isCumulativeView && aggregateDurationSeconds && aggregateDurationSeconds > 0
      ? totalThroughput / aggregateDurationSeconds
      : null;

  const mlChartData = {
    labels: ['BENIGN', 'ATTACK'],
    datasets: [
      {
        label: 'Predictions',
        data: [mlView.benign, mlView.attack],
        backgroundColor: ['#2a9d8f', '#e76f51'],
      },
    ],
  };

  const getLatencyStatus = (latency: number) => {
    if (latency > 100) return { status: 'High Latency', color: 'bg-red-100 text-red-800' };
    if (latency > 50) return { status: 'Elevated', color: 'bg-yellow-100 text-yellow-800' };
    return { status: 'Normal', color: 'bg-green-100 text-green-800' };
  };

  const latency = data?.metrics?.latency?.p95_ms ?? 0;
  const latencyStatus = getLatencyStatus(latency);

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">IDS Real-Time Dashboard</h1>
          <p className="text-gray-600 mt-2">
            Live metrics from ML predictions, Suricata alerts, and system performance (refreshed every 2 seconds)
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Snapshot view: each card shows the latest 2-second window; use the cumulative mode toggle below to aggregate over time.
          </p>
          <p className="text-sm text-gray-500 mt-1">
            Last updated: {data?.timestamp ? new Date(data.timestamp).toLocaleString() : 'Never'}
          </p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6 flex flex-wrap items-start gap-4 justify-between">
          <div>
            <p className="text-sm font-semibold text-gray-900">View mode</p>
            <p className="text-xs text-gray-500 mt-1">
              {cumulativeMode
                ? aggregatesEmpty
                  ? 'Cumulative mode enabled — waiting for the next refresh to start counting.'
                  : `Aggregating positive deltas since ${aggregateStartLabel ?? 'this reset'}.`
                : 'Snapshot view reflects only the most recent 2-second window.'}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {/* Commented out the cumulative mode toggle button
            <button
              onClick={handleCumulativeToggle}
              className={`px-4 py-2 rounded font-medium text-sm ${
                cumulativeMode
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-white text-gray-800 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              {cumulativeMode ? 'Disable cumulative mode' : 'Enable cumulative mode'}
            </button>
            */}
            <button
              onClick={resetAggregates}
              disabled={!cumulativeMode}
              className={`px-4 py-2 rounded border text-sm font-medium ${
                cumulativeMode
                  ? 'border-gray-300 text-gray-800 hover:bg-gray-50'
                  : 'border-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              Reset totals
            </button>
          </div>
        </div>

        {/* Top Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* ML Predictions */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">ML Predictions</h3>
            <div className="h-32">
              <Bar
                data={mlChartData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: { legend: { display: false } },
                  scales: { y: { beginAtZero: true } },
                }}
              />
            </div>
            <div className="mt-2 text-sm text-gray-600">
              {isCumulativeView ? 'Cumulative totals' : 'Snapshot totals'} — Total: {mlView.total} | Benign: {mlView.benign} | Attack: {mlView.attack} | Avg conf: {(data?.ml?.avg_confidence ?? 0).toFixed(1)}%
            </div>
            <div className="mt-4">
              <div className="text-xs uppercase tracking-wide text-gray-500">
                Attack labels {isCumulativeView ? '(cumulative counts)' : '(latest window)'}
              </div>
              {labelEntries.length > 0 ? (
                <div className="flex flex-wrap gap-2 mt-2">
                  {labelEntries.map(([label, count]) => (
                    <span
                      key={label}
                      className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs text-gray-700"
                    >
                      <span className="font-semibold text-gray-900">{label}</span>
                      <span className="rounded-full bg-gray-900 px-2 py-0.5 text-[10px] font-semibold text-white">
                        {count}
                      </span>
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-500 mt-2">No attack labels detected in this window.</p>
              )}
            </div>
          </div>

          {/* System Performance */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">System Performance</h3>
            {data?.metrics?.system && (
              <div className="text-sm text-gray-600 mb-3">
                CPU: {(data.metrics.system.cpu_percent ?? 0).toFixed(1)}% | Mem: {(data.metrics.system.memory_percent ?? 0).toFixed(1)}% ({(data.metrics.system.memory_mb ?? 0).toFixed(0)} MB)
              </div>
            )}
            <div className="text-sm text-gray-600 mb-2">Processing Latency (p95)</div>
            <div className="text-2xl font-bold text-gray-900 mb-2">{latency.toFixed(2)} ms</div>
            <div className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${latencyStatus.color}`}>
              {latencyStatus.status}
            </div>
          </div>
        </div>

        {/* Bottom Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Suricata Events */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Suricata Events</h3>
            <div className="text-sm text-gray-600 mb-3">
              {isCumulativeView ? 'Cumulative counts' : 'Snapshot counts'} — Events: {suricataEventsCounts.events} | Alerts: {suricataEventsCounts.alerts} | Flows: {suricataEventsCounts.flows}
            </div>
            <div className="text-sm text-gray-600 mb-3">Recent Events (snapshot)</div>
            <div className="bg-gray-50 p-3 rounded text-xs font-mono max-h-24 overflow-y-auto">
              {(data?.suricata_events?.events ?? []).slice(0, 5).map((event, i) => (
                <div key={i} className="mb-1 truncate">
                  {new Date(event.timestamp).toLocaleTimeString()} {event.type.toUpperCase()}: {event.src_ip || ''} → {event.dest_ip || ''} {event.signature || event.details || ''}
                </div>
              ))}
            </div>
          </div>

          {/* Throughput */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Throughput</h3>
            <div className="text-sm text-gray-600 mb-3">{throughputDetails}</div>
            {isCumulativeView ? (
              <>
                <div className="text-sm text-gray-600 mb-1">Avg events per second since reset</div>
                <div className="text-3xl font-bold text-gray-900">
                  {aggregatedThroughputPerSecond ? aggregatedThroughputPerSecond.toFixed(1) : '0.0'}
                </div>
                <div className="text-xs text-gray-500 mt-1">{totalThroughput} total events in this cumulative window</div>
              </>
            ) : (
              <>
                <div className="text-sm text-gray-600 mb-2">Events per Second</div>
                <div className="text-3xl font-bold text-gray-900">{totalThroughput}</div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
