import React, { useState, useEffect } from 'react';
import useWebSocket from '../hooks/useWebSocket';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar } from 'recharts';
import './PerformanceMonitor.css';

const PerformanceMonitor = () => {
  const [metrics, setMetrics] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedMetric, setSelectedMetric] = useState('cpu');
  const [alertsEnabled, setAlertsEnabled] = useState(true);
  
  // WebSocket connection for real-time updates
  const { isConnected, subscribe } = useWebSocket();

  // Mock historical data for demonstration
  const generateMockHistoricalData = () => {
    const data = [];
    const now = Date.now();
    for (let i = 29; i >= 0; i--) {
      const timestamp = new Date(now - i * 60000); // Every minute for last 30 minutes
      data.push({
        timestamp: timestamp.toLocaleTimeString(),
        fullTimestamp: timestamp,
        cpu: Math.random() * 100,
        memory: 20 + Math.random() * 60,
        disk: 10 + Math.random() * 30,
        network_in: Math.random() * 1000,
        network_out: Math.random() * 800,
        active_tasks: Math.floor(Math.random() * 20),
        response_time: 50 + Math.random() * 200
      });
    }
    return data;
  };

  const fetchInitialData = async () => {
    try {
      const axios = (await import('axios')).default;
      const [metricsRes, healthRes] = await Promise.all([
        axios.get('http://localhost:8000/monitoring/metrics'),
        axios.get('http://localhost:8000/monitoring/health')
      ]);
      
      setMetrics(metricsRes.data);
      setHealthData(healthRes.data);
      setHistoricalData(generateMockHistoricalData());
      setError(null);
    } catch (err) {
      console.error('Error fetching initial data:', err);
      setError('Failed to fetch performance metrics');
    } finally {
      setLoading(false);
    }
  };

  const updateHistoricalData = (newMetrics) => {
    const currentTime = new Date();
    const newDataPoint = {
      timestamp: currentTime.toLocaleTimeString(),
      fullTimestamp: currentTime,
      cpu: newMetrics.cpu_percent,
      memory: newMetrics.memory_percent,
      disk: newMetrics.disk_percent,
      network_in: Math.random() * 1000, // Mock network data
      network_out: Math.random() * 800,
      active_tasks: Math.floor(Math.random() * 20),
      response_time: 50 + Math.random() * 200
    };
    
    setHistoricalData(prev => [...prev.slice(1), newDataPoint]);
  };

  useEffect(() => {
    // Load initial data
    fetchInitialData();
    
    // Set up WebSocket subscriptions for real-time updates
    if (isConnected) {
      const unsubscribeMetrics = subscribe('system_metrics', (data) => {
        console.log('Received system metrics update:', data);
        setMetrics(data);
        updateHistoricalData(data);
      });
      
      const unsubscribeHealth = subscribe('system_health', (data) => {
        console.log('Received system health update:', data);
        setHealthData(data);
      });
      
      return () => {
        unsubscribeMetrics();
        unsubscribeHealth();
      };
    }
  }, [isConnected, subscribe]);

  const getMetricColor = (value, thresholds) => {
    if (value >= thresholds.critical) return '#e74c3c';
    if (value >= thresholds.warning) return '#f39c12';
    return '#27ae60';
  };

  const getSystemHealth = () => {
    if (!metrics) return 'unknown';
    const cpu = metrics.cpu_percent;
    const memory = metrics.memory_percent;
    const disk = metrics.disk_percent;
    
    if (cpu > 90 || memory > 90 || disk > 95) return 'critical';
    if (cpu > 70 || memory > 80 || disk > 85) return 'warning';
    return 'healthy';
  };

  const formatBytes = (bytes) => {
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatUptime = (seconds) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  if (loading) {
    return (
      <div className="performance-monitor">
        <div className="loading">
          <div className="loading-spinner"></div>
          <p>Loading performance metrics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="performance-monitor">
        <div className="error-banner">
          {error}
        </div>
        <button onClick={fetchInitialData} className="retry-btn">
          Retry
        </button>
      </div>
    );
  }

  const systemHealth = getSystemHealth();

  return (
    <div className="performance-monitor">
      <div className="monitor-header">
        <div className="header-left">
          <h2>Performance Monitor</h2>
          <div className={`system-health ${systemHealth}`}>
            <div className="health-indicator"></div>
            <span>System: {systemHealth.charAt(0).toUpperCase() + systemHealth.slice(1)}</span>
          </div>
        </div>
        
        <div className="header-controls">
          <div className={`websocket-status ${isConnected ? 'connected' : 'disconnected'}`}>
            <div className="status-indicator"></div>
            <span>{isConnected ? 'Real-time Connected' : 'Disconnected'}</span>
          </div>
          
          <button 
            className={`alerts-toggle ${alertsEnabled ? 'enabled' : 'disabled'}`}
            onClick={() => setAlertsEnabled(!alertsEnabled)}
          >
            🔔 Alerts {alertsEnabled ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>

      {/* System Overview Cards */}
      <div className="metrics-grid">
        <div className="metric-card cpu">
          <div className="metric-header">
            <h3>💻 CPU Usage</h3>
            <span className={`metric-status ${getMetricColor(metrics.cpu_percent, {warning: 70, critical: 90}) === '#27ae60' ? 'good' : getMetricColor(metrics.cpu_percent, {warning: 70, critical: 90}) === '#f39c12' ? 'warning' : 'critical'}`}>
              {metrics.cpu_percent.toFixed(1)}%
            </span>
          </div>
          <div className="metric-bar">
            <div 
              className="metric-fill"
              style={{
                width: `${metrics.cpu_percent}%`,
                backgroundColor: getMetricColor(metrics.cpu_percent, {warning: 70, critical: 90})
              }}
            ></div>
          </div>
          <div className="metric-details">
            <span>Cores: {metrics.cpu_count}</span>
            <span>Load Avg: {healthData?.load_average?.toFixed(2) || 'N/A'}</span>
          </div>
        </div>

        <div className="metric-card memory">
          <div className="metric-header">
            <h3>🧠 Memory Usage</h3>
            <span className={`metric-status ${getMetricColor(metrics.memory_percent, {warning: 80, critical: 90}) === '#27ae60' ? 'good' : getMetricColor(metrics.memory_percent, {warning: 80, critical: 90}) === '#f39c12' ? 'warning' : 'critical'}`}>
              {metrics.memory_percent.toFixed(1)}%
            </span>
          </div>
          <div className="metric-bar">
            <div 
              className="metric-fill"
              style={{
                width: `${metrics.memory_percent}%`,
                backgroundColor: getMetricColor(metrics.memory_percent, {warning: 80, critical: 90})
              }}
            ></div>
          </div>
          <div className="metric-details">
            <span>Used: {formatBytes(metrics.memory_used)}</span>
            <span>Total: {formatBytes(metrics.memory_total)}</span>
          </div>
        </div>

        <div className="metric-card disk">
          <div className="metric-header">
            <h3>💾 Disk Usage</h3>
            <span className={`metric-status ${getMetricColor(metrics.disk_percent, {warning: 85, critical: 95}) === '#27ae60' ? 'good' : getMetricColor(metrics.disk_percent, {warning: 85, critical: 95}) === '#f39c12' ? 'warning' : 'critical'}`}>
              {metrics.disk_percent.toFixed(1)}%
            </span>
          </div>
          <div className="metric-bar">
            <div 
              className="metric-fill"
              style={{
                width: `${metrics.disk_percent}%`,
                backgroundColor: getMetricColor(metrics.disk_percent, {warning: 85, critical: 95})
              }}
            ></div>
          </div>
          <div className="metric-details">
            <span>Used: {formatBytes(metrics.disk_used)}</span>
            <span>Free: {formatBytes(metrics.disk_free)}</span>
          </div>
        </div>

        <div className="metric-card uptime">
          <div className="metric-header">
            <h3>⏱️ System Uptime</h3>
            <span className="metric-status good">
              {formatUptime(healthData?.uptime || 0)}
            </span>
          </div>
          <div className="metric-details">
            <span>Process: {healthData?.process_count || 'N/A'} processes</span>
            <span>Boot: {healthData?.boot_time ? new Date(healthData.boot_time * 1000).toLocaleDateString() : 'N/A'}</span>
          </div>
        </div>
      </div>

      {/* Chart Section */}
      <div className="chart-section">
        <div className="chart-header">
          <h3>Historical Performance Data</h3>
          <div className="chart-controls">
            <div className="metric-selector">
              {['cpu', 'memory', 'disk', 'response_time'].map(metric => (
                <button
                  key={metric}
                  className={`metric-btn ${selectedMetric === metric ? 'active' : ''}`}
                  onClick={() => setSelectedMetric(metric)}
                >
                  {metric.charAt(0).toUpperCase() + metric.slice(1).replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="chart-container">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={historicalData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <Tooltip 
                formatter={(value) => [
                  selectedMetric.includes('time') ? `${value.toFixed(0)}ms` : 
                  selectedMetric === 'cpu' || selectedMetric === 'memory' || selectedMetric === 'disk' ? `${value.toFixed(1)}%` : 
                  value.toFixed(0),
                  selectedMetric.charAt(0).toUpperCase() + selectedMetric.slice(1).replace('_', ' ')
                ]}
              />
              <Area 
                type="monotone" 
                dataKey={selectedMetric}
                stroke="#667eea" 
                fill="url(#colorGradient)" 
                strokeWidth={2}
              />
              <defs>
                <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#667eea" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#667eea" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Performance Insights */}
      <div className="insights-section">
        <h3>Performance Insights</h3>
        <div className="insights-grid">
          <div className="insight-card">
            <div className="insight-icon">📈</div>
            <div className="insight-content">
              <h4>CPU Trend</h4>
              <p>
                {metrics.cpu_percent < 30 ? 'CPU usage is low and stable' :
                 metrics.cpu_percent < 70 ? 'CPU usage is moderate' :
                 'High CPU usage detected - consider optimization'}
              </p>
            </div>
          </div>

          <div className="insight-card">
            <div className="insight-icon">🧠</div>
            <div className="insight-content">
              <h4>Memory Analysis</h4>
              <p>
                {metrics.memory_percent < 50 ? 'Memory usage is optimal' :
                 metrics.memory_percent < 80 ? 'Memory usage is acceptable' :
                 'High memory usage - consider freeing resources'}
              </p>
            </div>
          </div>

          <div className="insight-card">
            <div className="insight-icon">💿</div>
            <div className="insight-content">
              <h4>Storage Health</h4>
              <p>
                {metrics.disk_percent < 70 ? 'Storage has plenty of free space' :
                 metrics.disk_percent < 90 ? 'Storage is getting full - monitor closely' :
                 'Critical storage levels - cleanup required'}
              </p>
            </div>
          </div>

          <div className="insight-card">
            <div className="insight-icon">⚡</div>
            <div className="insight-content">
              <h4>Overall Health</h4>
              <p>
                {systemHealth === 'healthy' ? 'All systems operating within normal parameters' :
                 systemHealth === 'warning' ? 'Some metrics approaching warning thresholds' :
                 'Critical issues detected - immediate attention required'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PerformanceMonitor;
