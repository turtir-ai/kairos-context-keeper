import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area, ScatterChart, Scatter, RadialBarChart, RadialBar } from 'recharts';
import './AdvancedAnalytics.css';

const AdvancedAnalytics = () => {
  const [analyticsData, setAnalyticsData] = useState({
    performanceMetrics: [],
    memoryUsage: [],
    networkActivity: [],
    errorRates: [],
    agentPerformance: []
  });
  const [timeRange, setTimeRange] = useState('1h');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchAnalyticsData();
    const interval = setInterval(fetchAnalyticsData, 10000); // Update every 10 seconds
    return () => clearInterval(interval);
  }, [timeRange]);

  const fetchAnalyticsData = async () => {
    try {
      // Mock data for demonstration
      const mockData = generateMockAnalyticsData();
      setAnalyticsData(mockData);
    } catch (error) {
      console.error('Failed to fetch analytics data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const generateMockAnalyticsData = () => {
    const now = new Date();
    const timePoints = [];
    
    // Generate 30 data points
    for (let i = 29; i >= 0; i--) {
      const time = new Date(now.getTime() - i * 2 * 60 * 1000); // 2-minute intervals
      timePoints.push({
        time: time.toLocaleTimeString('en-US', { hour12: false }),
        timestamp: time.getTime(),
        cpu: Math.round(Math.random() * 100),
        memory: Math.round(Math.random() * 90) + 10,
        networkIn: Math.round(Math.random() * 1000),
        networkOut: Math.round(Math.random() * 800),
        errors: Math.round(Math.random() * 20),
        requests: Math.round(Math.random() * 500) + 100,
        responseTime: Math.round(Math.random() * 1000) + 50,
        agentLoad: Math.round(Math.random() * 100)
      });
    }

    return {
      performanceMetrics: timePoints,
      memoryUsage: timePoints.map(point => ({
        time: point.time,
        used: point.memory,
        free: 100 - point.memory,
        cached: Math.round(Math.random() * 30),
        buffers: Math.round(Math.random() * 15)
      })),
      networkActivity: timePoints.map(point => ({
        time: point.time,
        inbound: point.networkIn,
        outbound: point.networkOut,
        connections: Math.round(Math.random() * 100) + 50
      })),
      errorRates: timePoints.map(point => ({
        time: point.time,
        errors: point.errors,
        warnings: Math.round(Math.random() * 30),
        success: point.requests - point.errors - Math.round(Math.random() * 30)
      })),
      agentPerformance: [
        { name: 'Memory Agent', performance: 95, load: 45, color: '#8884d8' },
        { name: 'Task Agent', performance: 88, load: 67, color: '#82ca9d' },
        { name: 'Monitor Agent', performance: 92, load: 34, color: '#ffc658' },
        { name: 'API Agent', performance: 85, load: 78, color: '#ff7300' },
        { name: 'Cache Agent', performance: 97, load: 23, color: '#00c49f' }
      ]
    };
  };

  if (isLoading) {
    return (
      <div className="advanced-analytics loading">
        <div className="loading-spinner"></div>
        <p>Analyzing system performance...</p>
      </div>
    );
  }

  return (
    <div className="advanced-analytics">
      <div className="analytics-header">
        <h2>🔬 Advanced System Analytics</h2>
        <div className="time-range-controls">
          <label>Time Range:</label>
          <select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
            <option value="15m">Last 15 minutes</option>
            <option value="1h">Last hour</option>
            <option value="6h">Last 6 hours</option>
            <option value="24h">Last 24 hours</option>
          </select>
        </div>
      </div>

      {/* Performance Overview Grid */}
      <div className="analytics-overview">
        <div className="metric-summary">
          <h3>📊 Performance Summary</h3>
          <div className="summary-cards">
            <div className="summary-card">
              <div className="metric-title">Avg CPU Usage</div>
              <div className="metric-value">
                {analyticsData.performanceMetrics.length > 0 
                  ? Math.round(analyticsData.performanceMetrics.reduce((acc, curr) => acc + curr.cpu, 0) / analyticsData.performanceMetrics.length)
                  : 0}%
              </div>
            </div>
            <div className="summary-card">
              <div className="metric-title">Peak Memory</div>
              <div className="metric-value">
                {analyticsData.memoryUsage.length > 0 
                  ? Math.max(...analyticsData.memoryUsage.map(d => d.used))
                  : 0}%
              </div>
            </div>
            <div className="summary-card">
              <div className="metric-title">Total Errors</div>
              <div className="metric-value">
                {analyticsData.errorRates.length > 0 
                  ? analyticsData.errorRates.reduce((acc, curr) => acc + curr.errors, 0)
                  : 0}
              </div>
            </div>
            <div className="summary-card">
              <div className="metric-title">Avg Response Time</div>
              <div className="metric-value">
                {analyticsData.performanceMetrics.length > 0 
                  ? Math.round(analyticsData.performanceMetrics.reduce((acc, curr) => acc + curr.responseTime, 0) / analyticsData.performanceMetrics.length)
                  : 0}ms
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Advanced Charts Grid */}
      <div className="advanced-charts-grid">
        {/* System Performance Area Chart */}
        <div className="chart-container full-width">
          <h4>🏃‍♂️ System Performance Over Time</h4>
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart data={analyticsData.performanceMetrics}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Area type="monotone" dataKey="cpu" stackId="1" stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} name="CPU %" />
              <Area type="monotone" dataKey="memory" stackId="2" stroke="#82ca9d" fill="#82ca9d" fillOpacity={0.6} name="Memory %" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Memory Breakdown */}
        <div className="chart-container">
          <h4>🧠 Memory Usage Breakdown</h4>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={analyticsData.memoryUsage}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Area type="monotone" dataKey="used" stackId="1" stroke="#e74c3c" fill="#e74c3c" name="Used" />
              <Area type="monotone" dataKey="cached" stackId="1" stroke="#f39c12" fill="#f39c12" name="Cached" />
              <Area type="monotone" dataKey="buffers" stackId="1" stroke="#3498db" fill="#3498db" name="Buffers" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Network Activity */}
        <div className="chart-container">
          <h4>🌐 Network Activity</h4>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={analyticsData.networkActivity}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="inbound" stroke="#27ae60" name="Inbound (KB/s)" strokeWidth={2} />
              <Line type="monotone" dataKey="outbound" stroke="#e67e22" name="Outbound (KB/s)" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Agent Performance Radial Chart */}
        <div className="chart-container">
          <h4>🤖 Agent Performance</h4>
          <ResponsiveContainer width="100%" height={300}>
            <RadialBarChart cx="50%" cy="50%" innerRadius="20%" outerRadius="90%" data={analyticsData.agentPerformance}>
              <RadialBar dataKey="performance" cornerRadius={10} fill="#8884d8" />
              <Tooltip formatter={(value) => [`${value}%`, 'Performance']} />
            </RadialBarChart>
          </ResponsiveContainer>
        </div>

        {/* Error Rate Analysis */}
        <div className="chart-container">
          <h4>⚠️ Error Rate Analysis</h4>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={analyticsData.errorRates}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Area type="monotone" dataKey="success" stackId="1" stroke="#27ae60" fill="#27ae60" name="Success" />
              <Area type="monotone" dataKey="warnings" stackId="1" stroke="#f39c12" fill="#f39c12" name="Warnings" />
              <Area type="monotone" dataKey="errors" stackId="1" stroke="#e74c3c" fill="#e74c3c" name="Errors" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Response Time Scatter Plot */}
        <div className="chart-container">
          <h4>⚡ Response Time Distribution</h4>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart data={analyticsData.performanceMetrics}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="requests" name="Requests" />
              <YAxis dataKey="responseTime" name="Response Time (ms)" />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} />
              <Scatter name="Response Times" dataKey="responseTime" fill="#8884d8" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="analytics-actions">
        <button className="action-btn primary" onClick={() => window.open('/monitoring/export?format=csv', '_blank')}>
          📊 Export Data (CSV)
        </button>
        <button className="action-btn secondary" onClick={() => window.open('/monitoring/report', '_blank')}>
          📄 Generate Report
        </button>
        <button className="action-btn secondary" onClick={fetchAnalyticsData}>
          🔄 Refresh Data
        </button>
      </div>
    </div>
  );
};

export default AdvancedAnalytics;
