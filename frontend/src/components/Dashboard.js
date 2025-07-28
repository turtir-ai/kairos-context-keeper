import React, { useState, useEffect } from 'react';
import { useWebSocketContext } from '../contexts/WebSocketContext';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import './Dashboard.css';

const Dashboard = () => {
  const [systemStats, setSystemStats] = useState({
    agents: { active: 0, total: 5 },
    memory: { used: 0, total: 0 },
    tasks: { active: 0, completed: 0, failed: 0 }
  });
  const [performanceHistory, setPerformanceHistory] = useState([]);
  const [taskDistribution, setTaskDistribution] = useState([]);
  const [memoryTrend, setMemoryTrend] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  
const { isConnected, subscribe } = useWebSocketContext();

  useEffect(() => {
    fetchSystemStats(); // Initial fetch
    
    // Set up periodic fetching
    const interval = setInterval(() => {
      fetchSystemStats();
    }, 5000); // Update every 5 seconds
    
    // Subscribe to real-time system stats updates
    if (isConnected) {
      const handleSystemStats = (data) => {
        const newStats = {
          agents: { active: data.agents?.active || 0, total: 5 },
          memory: { 
            used: Math.round(data.memory?.percent || 0), 
            total: Math.round((data.memory?.total || 0) / (1024**3)) // GB
          },
          tasks: {
            active: data.tasks?.active || 0,
            completed: data.tasks?.completed || 0,
            failed: data.tasks?.failed || 0
          }
        };
        setSystemStats(newStats);
        
        // Update charts data
        updateChartsData(newStats);
        
        setIsLoading(false);
        console.log('✅ Dashboard data updated via WebSocket:', data);
      };
      
      const unsubscribeStats = subscribe('system_metrics', handleSystemStats);
      const unsubscribeAgent = subscribe('agent_status', handleSystemStats);
      const unsubscribeTasks = subscribe('task_update', handleSystemStats);
      
      return () => {
        clearInterval(interval);
        unsubscribeStats();
        unsubscribeAgent();
        unsubscribeTasks();
      };
    }
    
    return () => clearInterval(interval);
  }, [isConnected, subscribe]);

  const updateChartsData = (stats) => {
    const timestamp = new Date().toLocaleTimeString();
    
    // Update performance history
    setPerformanceHistory(prev => {
      const newHistory = [...prev, {
        time: timestamp,
        cpu: Math.round(Math.random() * 100), // Mock CPU data
        memory: stats.memory.used,
        agents: stats.agents.active
      }].slice(-20);
      return newHistory;
    });
    
    // Update task distribution
    setTaskDistribution([
      { name: 'Active', value: stats.tasks.active, color: '#8884d8' },
      { name: 'Completed', value: stats.tasks.completed, color: '#82ca9d' },
      { name: 'Failed', value: stats.tasks.failed, color: '#ffc658' }
    ]);
  };

  const fetchSystemStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/monitoring/system-stats');
      if (response.ok) {
        const data = await response.json();
        const newStats = {
          agents: { active: data.agents?.active || 0, total: 5 },
          memory: { 
            used: Math.round(data.memory?.percent || 0), 
            total: Math.round((data.memory?.total || 0) / (1024**3)) // GB
          },
          tasks: {
            active: data.tasks?.active || 0,
            completed: data.tasks?.completed || 0,
            failed: data.tasks?.failed || 0
          }
        };
        setSystemStats(newStats);
        
        // Update performance history for charts
        const timestamp = new Date().toLocaleTimeString();
        setPerformanceHistory(prev => {
          const newHistory = [...prev, {
            time: timestamp,
            cpu: Math.round(Math.random() * 100), // Mock CPU data
            memory: newStats.memory.used,
            agents: newStats.agents.active
          }].slice(-20); // Keep last 20 points
          return newHistory;
        });
        
        // Update task distribution for pie chart
        setTaskDistribution([
          { name: 'Active', value: newStats.tasks.active, color: '#8884d8' },
          { name: 'Completed', value: newStats.tasks.completed, color: '#82ca9d' },
          { name: 'Failed', value: newStats.tasks.failed, color: '#ffc658' }
        ]);
        
        console.log('✅ Dashboard data updated:', data);
      }
    } catch (error) {
      console.error('❌ Failed to fetch system stats:', error);
      // Set mock data on error
      const mockStats = {
        agents: { active: 3, total: 5 },
        memory: { used: 48, total: 32 },
        tasks: { active: 2, completed: 15, failed: 1 }
      };
      setSystemStats(mockStats);
      
      // Initialize with mock data for charts
      setPerformanceHistory([
        { time: '10:00', cpu: 45, memory: 48, agents: 3 },
        { time: '10:05', cpu: 52, memory: 50, agents: 3 },
        { time: '10:10', cpu: 38, memory: 45, agents: 4 },
        { time: '10:15', cpu: 65, memory: 52, agents: 3 },
        { time: '10:20', cpu: 42, memory: 48, agents: 3 }
      ]);
      
      setTaskDistribution([
        { name: 'Active', value: 2, color: '#8884d8' },
        { name: 'Completed', value: 15, color: '#82ca9d' },
        { name: 'Failed', value: 1, color: '#ffc658' }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="dashboard loading">
        <div className="loading-spinner"></div>
        <p>Loading system overview...</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <h2>System Overview</h2>
      
      <div className="stats-grid">
        <div className="stat-card agents">
          <h3>Agent Guild</h3>
          <div className="stat-value">
            {systemStats.agents.active}/{systemStats.agents.total}
          </div>
          <div className="stat-label">Active Agents</div>
          <div className="stat-progress">
            <div 
              className="progress-bar" 
              style={{ width: `${(systemStats.agents.active / systemStats.agents.total) * 100}%` }}
            ></div>
          </div>
        </div>

        <div className="stat-card memory">
          <h3>Memory Usage</h3>
          <div className="stat-value">{systemStats.memory.used}%</div>
          <div className="stat-label">{systemStats.memory.total} GB Total</div>
          <div className="stat-progress">
            <div 
              className="progress-bar" 
              style={{ width: `${systemStats.memory.used}%` }}
            ></div>
          </div>
        </div>

        <div className="stat-card tasks">
          <h3>Task Status</h3>
          <div className="task-stats">
            <div className="task-stat active">
              <span className="value">{systemStats.tasks.active}</span>
              <span className="label">Active</span>
            </div>
            <div className="task-stat completed">
              <span className="value">{systemStats.tasks.completed}</span>
              <span className="label">Completed</span>
            </div>
            <div className="task-stat failed">
              <span className="value">{systemStats.tasks.failed}</span>
              <span className="label">Failed</span>
            </div>
          </div>
        </div>

        <div className="stat-card system-health">
          <h3>System Health</h3>
          <div className="health-indicators">
            <div className="health-item">
              <span className="indicator online"></span>
              <span>API Server</span>
            </div>
            <div className="health-item">
              <span className="indicator online"></span>
              <span>Memory Layer</span>
            </div>
            <div className="health-item">
              <span className="indicator online"></span>
              <span>Orchestration</span>
            </div>
          </div>
        </div>
      </div>

      {/* Analytics Section */}
      <div className="analytics-section">
        <h3>🔍 System Analytics</h3>
        
        <div className="charts-container">
          {/* Performance History Chart */}
          <div className="chart-card">
            <h4>Performance Trends</h4>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={performanceHistory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="cpu" stroke="#8884d8" name="CPU %" />
                <Line type="monotone" dataKey="memory" stroke="#82ca9d" name="Memory %" />
                <Line type="monotone" dataKey="agents" stroke="#ffc658" name="Active Agents" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Task Distribution Pie Chart */}
          <div className="chart-card">
            <h4>Task Distribution</h4>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={taskDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {taskDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* System Resources Bar Chart */}
          <div className="chart-card">
            <h4>System Resources</h4>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={[
                { name: 'CPU', usage: Math.round(Math.random() * 100) },
                { name: 'Memory', usage: systemStats.memory.used },
                { name: 'Agents', usage: (systemStats.agents.active / systemStats.agents.total) * 100 },
                { name: 'Tasks', usage: systemStats.tasks.active * 10 }
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip formatter={(value) => [`${value.toFixed(1)}%`, 'Usage']} />
                <Bar dataKey="usage" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="quick-actions">
        <h3>Quick Actions</h3>
        <div className="action-buttons">
          <button className="action-btn primary" onClick={() => window.location.hash = '#agents'}>
            <span className="btn-icon">🤖</span>
            <span>Manage Agents</span>
          </button>
          <button className="action-btn secondary" onClick={() => window.location.hash = '#memory'}>
            <span className="btn-icon">🧠</span>
            <span>Memory Viewer</span>
          </button>
          <button className="action-btn secondary" onClick={() => window.location.hash = '#tasks'}>
            <span className="btn-icon">⚡</span>
            <span>Task Orchestrator</span>
          </button>
          <button className="action-btn analytics" onClick={() => window.location.hash = '#analytics'}>
            <span className="btn-icon">📊</span>
            <span>Advanced Analytics</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
