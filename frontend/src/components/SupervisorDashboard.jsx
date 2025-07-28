import React, { useState, useEffect, useCallback } from 'react';
import './SupervisorDashboard.css';

const SupervisorDashboard = () => {
  const [supervisorStatus, setSupervisorStatus] = useState('initializing');
  const [alerts, setAlerts] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [healthStatus, setHealthStatus] = useState('unknown');
  const [suggestions, setSuggestions] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [autoPilotMode, setAutoPilotMode] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');

  // Handle WebSocket connection and message routing
  useEffect(() => {
    let socket;
    let reconnectTimeout;

    const connectWebSocket = () => {
      socket = new WebSocket('ws://localhost:8000/ws');
      
      socket.onopen = () => {
        setConnectionStatus('connected');
        console.log('Supervisor Dashboard connected to WebSocket');
        
        // Subscribe to supervisor updates
        socket.send(JSON.stringify({
          message_type: 'subscription',
          data: {
            action: 'subscribe',
            message_types: ['supervisor_status', 'anomaly_alert', 'system_metrics', 'optimization_suggestion']
          }
        }));
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      socket.onclose = () => {
        setConnectionStatus('disconnected');
        // Attempt to reconnect after 3 seconds
        reconnectTimeout = setTimeout(connectWebSocket, 3000);
      };

      socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
      };
    };

    connectWebSocket();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (socket) socket.close();
    };
  }, []);

  const handleWebSocketMessage = useCallback((data) => {
    switch (data.message_type) {
      case 'supervisor_status':
        setSupervisorStatus(data.data.status);
        addNotification(`Supervisor status: ${data.data.status}`, 'info');
        break;
      
      case 'anomaly_alert':
        const alert = {
          id: data.data.alert_id,
          severity: data.data.severity,
          message: data.data.message,
          timestamp: data.data.timestamp,
          resolved: false
        };
        setAlerts(prev => [alert, ...prev.slice(0, 49)]); // Keep last 50 alerts
        addNotification(`Alert: ${alert.message}`, alert.severity);
        break;
      
      case 'system_metrics':
        setMetrics(data.data.metrics || {});
        setHealthStatus(data.data.health_status || 'unknown');
        break;
      
      case 'optimization_suggestion':
        const suggestion = {
          id: data.data.suggestion_id,
          title: data.data.title,
          description: data.data.description,
          priority: data.data.priority,
          timestamp: data.data.timestamp
        };
        setSuggestions(prev => [suggestion, ...prev.slice(0, 19)]); // Keep last 20 suggestions
        addNotification(`New suggestion: ${suggestion.title}`, 'suggestion');
        break;
      
      default:
        console.log('Unknown message type:', data.message_type);
    }
  }, []);

  const addNotification = (message, type) => {
    const notification = {
      id: Date.now(),
      message,
      type,
      timestamp: new Date().toISOString()
    };
    setNotifications(prev => [notification, ...prev.slice(0, 9)]); // Keep last 10 notifications
    
    // Auto-remove notification after 5 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== notification.id));
    }, 5000);
  };

  const approveSuggestion = async (suggestionId) => {
    try {
      const response = await fetch('/api/supervisor/approve/' + suggestionId, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved: true })
      });
      
      if (response.ok) {
        setSuggestions(prev => prev.filter(s => s.id !== suggestionId));
        addNotification('Suggestion approved successfully', 'success');
      }
    } catch (error) {
      console.error('Error approving suggestion:', error);
      addNotification('Failed to approve suggestion', 'error');
    }
  };

  const dismissAlert = (alertId) => {
    setAlerts(prev => prev.map(alert => 
      alert.id === alertId ? { ...alert, resolved: true } : alert
    ));
  };

  const toggleAutoPilot = () => {
    setAutoPilotMode(!autoPilotMode);
    addNotification(`Auto-pilot mode ${!autoPilotMode ? 'enabled' : 'disabled'}`, 'info');
  };

  const getHealthStatusColor = (status) => {
    switch (status) {
      case 'healthy': return '#4CAF50';
      case 'warning': return '#FF9800';
      case 'degraded': return '#FF5722';
      case 'critical': return '#F44336';
      default: return '#9E9E9E';
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return '#F44336';
      case 'high': return '#FF5722';
      case 'medium': return '#FF9800';
      case 'low': return '#4CAF50';
      default: return '#9E9E9E';
    }
  };

  return (
    <div className="supervisor-dashboard">
      {/* Header with status indicators */}
      <header className="dashboard-header">
        <h1>🧠 Supervisor Dashboard</h1>
        <div className="status-indicators">
          <div className="status-indicator">
            <span className="label">Connection:</span>
            <span className={`status ${connectionStatus}`}>{connectionStatus}</span>
          </div>
          <div className="status-indicator">
            <span className="label">Supervisor:</span>
            <span className={`status ${supervisorStatus}`}>{supervisorStatus}</span>
          </div>
          <div className="status-indicator">
            <span className="label">Health:</span>
            <span className="status" style={{ color: getHealthStatusColor(healthStatus) }}>
              {healthStatus}
            </span>
          </div>
          <div className="autopilot-toggle">
            <label>
              <input
                type="checkbox"
                checked={autoPilotMode}
                onChange={toggleAutoPilot}
              />
              Auto-pilot Mode
            </label>
          </div>
        </div>
      </header>

      {/* Notifications */}
      {notifications.length > 0 && (
        <div className="notifications">
          {notifications.map(notification => (
            <div key={notification.id} className={`notification ${notification.type}`}>
              {notification.message}
            </div>
          ))}
        </div>
      )}

      <div className="dashboard-content">
        {/* System Health Overview */}
        <section className="health-overview">
          <h2>🏥 System Health</h2>
          <div className="health-grid">
            <div className="health-card">
              <h3>CPU Usage</h3>
              <div className="metric-value">
                {metrics.cpu_percent ? `${metrics.cpu_percent.toFixed(1)}%` : 'N/A'}
                <div className={`progress-bar ${metrics.cpu_percent > 80 ? 'critical' : metrics.cpu_percent > 60 ? 'warning' : 'normal'}`}>
                  <div 
                    className="progress-fill" 
                    style={{ width: `${Math.min(metrics.cpu_percent || 0, 100)}%` }}
                  ></div>
                </div>
              </div>
            </div>
            <div className="health-card">
              <h3>Memory Usage</h3>
              <div className="metric-value">
                {metrics.memory_percent ? `${metrics.memory_percent.toFixed(1)}%` : 'N/A'}
                <div className={`progress-bar ${metrics.memory_percent > 85 ? 'critical' : metrics.memory_percent > 70 ? 'warning' : 'normal'}`}>
                  <div 
                    className="progress-fill" 
                    style={{ width: `${Math.min(metrics.memory_percent || 0, 100)}%` }}
                  ></div>
                </div>
              </div>
            </div>
            <div className="health-card">
              <h3>Active Connections</h3>
              <div className="metric-value">
                {metrics.active_connections || 0}
              </div>
            </div>
            <div className="health-card">
              <h3>Response Time</h3>
              <div className="metric-value">
                {metrics.avg_response_time_ms ? `${metrics.avg_response_time_ms.toFixed(0)}ms` : 'N/A'}
              </div>
            </div>
          </div>
        </section>

        {/* Active Alerts */}
        <section className="alerts-section">
          <h2>🚨 Active Alerts ({alerts.filter(a => !a.resolved).length})</h2>
          <div className="alerts-container">
            {alerts.filter(alert => !alert.resolved).length > 0 ? (
              alerts
                .filter(alert => !alert.resolved)
                .slice(0, 10)
                .map(alert => (
                  <div key={alert.id} className={`alert-card ${alert.severity}`}>
                    <div className="alert-header">
                      <span 
                        className="severity-badge" 
                        style={{ backgroundColor: getSeverityColor(alert.severity) }}
                      >
                        {alert.severity.toUpperCase()}
                      </span>
                      <span className="alert-time">
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </span>
                      <button 
                        className="dismiss-btn"
                        onClick={() => dismissAlert(alert.id)}
                        title="Dismiss alert"
                      >
                        ✕
                      </button>
                    </div>
                    <div className="alert-message">{alert.message}</div>
                  </div>
                ))
            ) : (
              <div className="no-alerts">✅ No active alerts</div>
            )}
          </div>
        </section>

        {/* Optimization Suggestions */}
        <section className="suggestions-section">
          <h2>💡 Optimization Suggestions ({suggestions.length})</h2>
          <div className="suggestions-container">
            {suggestions.length > 0 ? (
              suggestions.slice(0, 5).map(suggestion => (
                <div key={suggestion.id} className={`suggestion-card ${suggestion.priority}`}>
                  <div className="suggestion-header">
                    <h3>{suggestion.title}</h3>
                    <span className={`priority-badge ${suggestion.priority}`}>
                      {suggestion.priority.toUpperCase()}
                    </span>
                  </div>
                  <p className="suggestion-description">{suggestion.description}</p>
                  <div className="suggestion-actions">
                    <button 
                      className="approve-btn"
                      onClick={() => approveSuggestion(suggestion.id)}
                    >
                      ✓ Approve
                    </button>
                    <button className="dismiss-btn">✕ Dismiss</button>
                  </div>
                </div>
              ))
            ) : (
              <div className="no-suggestions">No optimization suggestions at this time</div>
            )}
          </div>
        </section>

        {/* Detailed Metrics */}
        <section className="detailed-metrics">
          <h2>📊 Detailed Metrics</h2>
          <div className="metrics-grid">
            {Object.entries(metrics).map(([key, value]) => (
              <div key={key} className="metric-item">
                <span className="metric-key">{key.replace(/_/g, ' ').toUpperCase()}</span>
                <span className="metric-value">
                  {typeof value === 'number' ? value.toFixed(2) : value}
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};

export default SupervisorDashboard;

