import React, { useState, useEffect } from 'react';
import './MonitoringPanel.css';

const MonitoringPanel = () => {
  const [metrics, setMetrics] = useState({});
  const [systemHealth, setSystemHealth] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [timeRange, setTimeRange] = useState(60); // minutes

  useEffect(() => {
    fetchMetrics();
    fetchSystemHealth();
    
    const interval = setInterval(() => {
      fetchMetrics();
      fetchSystemHealth();
    }, 30000); // Update every 30 seconds
    
    return () => clearInterval(interval);
  }, [timeRange]);

  const fetchMetrics = async () => {
    try {
      const response = await fetch(`http://localhost:8000/monitoring/metrics?time_range=${timeRange}`);
      if (response.ok) {
        const data = await response.json();
        setMetrics(data);
      }
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchSystemHealth = async () => {
    try {
      const response = await fetch('http://localhost:8000/monitoring/health');
      if (response.ok) {
        const data = await response.json();
        setSystemHealth(data);
      }
    } catch (error) {
      console.error('Failed to fetch system health:', error);
    }
  };

  const formatMetricValue = (value, unit) => {
    if (typeof value === 'number') {
      return value.toFixed(2) + (unit ? ` ${unit}` : '');
    }
    return value;
  };

  const getHealthStatusColor = (healthy) => {
    return healthy ? '#28a745' : '#dc3545';
  };

  if (isLoading) {
    return (
      <div className="monitoring-panel loading">
        <div className="loading-spinner"></div>
        <p>Loading monitoring data...</p>
      </div>
    );
  }

  return (
    <div className="monitoring-panel">
      <div className="panel-header">
        <h2>System Monitoring</h2>
        <div className="time-range-selector">
          <select 
            value={timeRange} 
            onChange={(e) => setTimeRange(parseInt(e.target.value))}
          >
            <option value={15}>Last 15 minutes</option>
            <option value={60}>Last hour</option>
            <option value={240}>Last 4 hours</option>
            <option value={1440}>Last 24 hours</option>
          </select>
        </div>
      </div>

      {/* System Health Overview */}
      <div className="health-overview">
        <h3>System Health</h3>
        <div className={`health-status ${systemHealth.overall_healthy ? 'healthy' : 'degraded'}`}>
          <span className="status-indicator">
            {systemHealth.overall_healthy ? '🟢' : '🔴'}
          </span>
          <span className="status-text">
            {systemHealth.status || 'Unknown'}
          </span>
        </div>

        {systemHealth.checks && (
          <div className="health-checks">
            {Object.entries(systemHealth.checks).map(([check, data]) => (
              <div key={check} className="health-check">
                <span 
                  className="check-indicator"
                  style={{ color: getHealthStatusColor(data.healthy) }}
                >
                  {data.healthy ? '✓' : '✗'}
                </span>
                <span className="check-name">{check.toUpperCase()}</span>
                <span className="check-value">
                  {formatMetricValue(data.value, check === 'error_rate' ? '' : '%')}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* System Metrics */}
      {metrics.system_stats && (
        <div className="system-metrics">
          <h3>System Resources</h3>
          <div className="metrics-grid">
            <div className="metric-card">
              <h4>CPU Usage</h4>
              <div className="metric-value">
                {metrics.system_stats.cpu_percent?.toFixed(1) || 'N/A'}%
              </div>
              <div className="metric-bar">
                <div 
                  className="metric-progress"
                  style={{ width: `${metrics.system_stats.cpu_percent || 0}%` }}
                ></div>
              </div>
            </div>

            <div className="metric-card">
              <h4>Memory Usage</h4>
              <div className="metric-value">
                {metrics.system_stats.memory_percent?.toFixed(1) || 'N/A'}%
              </div>
              <div className="metric-bar">
                <div 
                  className="metric-progress"
                  style={{ width: `${metrics.system_stats.memory_percent || 0}%` }}
                ></div>
              </div>
            </div>

            <div className="metric-card">
              <h4>Disk Usage</h4>
              <div className="metric-value">
                {metrics.system_stats.disk_usage?.toFixed(1) || 'N/A'}%
              </div>
              <div className="metric-bar">
                <div 
                  className="metric-progress"
                  style={{ width: `${metrics.system_stats.disk_usage || 0}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Performance Counters */}
      {metrics.counters && (
        <div className="performance-counters">
          <h3>Performance Counters</h3>
          <div className="counters-grid">
            {Object.entries(metrics.counters).map(([counter, value]) => (
              <div key={counter} className="counter-card">
                <div className="counter-name">
                  {counter.replace(/_/g, ' ').toUpperCase()}
                </div>
                <div className="counter-value">{value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Metrics Summary */}
      {metrics.aggregated_metrics && Object.keys(metrics.aggregated_metrics).length > 0 && (
        <div className="aggregated-metrics">
          <h3>Recent Metrics ({timeRange} minutes)</h3>
          <div className="metrics-table">
            <div className="metrics-header">
              <span>Metric</span>
              <span>Count</span>
              <span>Average</span>
              <span>Min</span>
              <span>Max</span>
              <span>Latest</span>
            </div>
            {Object.entries(metrics.aggregated_metrics).map(([name, data]) => (
              <div key={name} className="metric-row">
                <span className="metric-name">{name}</span>
                <span>{data.count}</span>
                <span>{formatMetricValue(data.avg, data.unit)}</span>
                <span>{formatMetricValue(data.min, data.unit)}</span>
                <span>{formatMetricValue(data.max, data.unit)}</span>
                <span>{formatMetricValue(data.latest, data.unit)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Export Controls */}
      <div className="export-controls">
        <h3>Data Export</h3>
        <div className="export-buttons">
          <button 
            className="export-btn"
            onClick={() => window.open('http://localhost:8000/monitoring/export?format=json', '_blank')}
          >
            Export JSON
          </button>
          <button 
            className="cleanup-btn"
            onClick={async () => {
              try {
                await fetch('http://localhost:8000/monitoring/cleanup', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ older_than_hours: 24 })
                });
                alert('Old metrics cleaned up successfully');
                fetchMetrics();
              } catch (error) {
                alert('Failed to clean up metrics');
              }
            }}
          >
            Cleanup Old Data
          </button>
        </div>
      </div>
    </div>
  );
};

export default MonitoringPanel;
