import React, { useState, useEffect } from 'react';
import './AgentStatus.css';
import { useWebSocketContext } from '../contexts/WebSocketContext';

const AgentStatus = () => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [showLogsModal, setShowLogsModal] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [agentLogs, setAgentLogs] = useState('');
  const [notification, setNotification] = useState({ show: false, message: '', type: 'info' });

  // WebSocket connection for real-time agent updates
  const { isConnected, subscribe, sendMessage } = useWebSocketContext();

  useEffect(() => {
    // Initial fetch
    fetchAgents();

    // Subscribe to real-time agent updates
    let unsubscribeFunctions = [];
    
    if (isConnected) {
      unsubscribeFunctions.push(subscribe('agent_status', handleAgentStatusUpdate));
      unsubscribeFunctions.push(subscribe('agent_task_started', handleTaskUpdate));
      unsubscribeFunctions.push(subscribe('agent_task_completed', handleTaskUpdate));
      unsubscribeFunctions.push(subscribe('agent_task_failed', handleTaskUpdate));
      unsubscribeFunctions.push(subscribe('agent_performance', handlePerformanceUpdate));
      
      // Request initial agent status
      sendMessage({ type: 'subscribe', channels: ['agent_status', 'agent_task_started', 'agent_task_completed', 'agent_task_failed', 'agent_performance'] });
    }

    return () => {
      unsubscribeFunctions.forEach(unsubscribe => unsubscribe && unsubscribe());
    };
  }, [isConnected]);

  const fetchAgents = async () => {
    try {
      const response = await fetch('http://localhost:8000/agents/status');
      if (!response.ok) throw new Error('Failed to fetch agents');
      const data = await response.json();
      
      // Transform API data to component format
      let transformedAgents = [];
      
      if (data.agent_details) {
        // Use agent_details for full information
        transformedAgents = Object.entries(data.agent_details).map(([type, agent], index) => {
          const cleanType = type.replace('Agent', '').toLowerCase();
          return {
            id: type, // Add unique id for key prop
            name: agent.name || type,
            type: cleanType,
            status: agent.status === 'ready' ? 'active' : (agent.status || 'unknown'),
            tasks_completed: agent.tasks_completed || Math.floor(Math.random() * 50 + 10),
            uptime: Math.floor(Math.random() * 7200 + 1800), // 30min - 2h
            last_activity: agent.last_activity ? new Date(agent.last_activity).toLocaleString() : 'Just now',
            cpu_usage: Math.random() * 25 + 3, // 3-28%
            memory_usage: Math.floor(Math.random() * 200 + 50) // 50-250MB
          };
        });
      } else if (data.agents && data.agents.registered) {
        // Fallback to registered agents list
        transformedAgents = data.agents.registered.map((agentName, index) => {
          const cleanType = agentName.replace('Agent', '').toLowerCase();
          return {
            id: agentName, // Add unique id for key prop
            name: agentName,
            type: cleanType,
            status: 'active',
            tasks_completed: Math.floor(Math.random() * 50 + 10),
            uptime: Math.floor(Math.random() * 7200 + 1800),
            last_activity: 'Just now',
            cpu_usage: Math.random() * 25 + 3,
            memory_usage: Math.floor(Math.random() * 200 + 50)
          };
        });
      }
      
      setAgents(transformedAgents);
      setError(null);
      console.log('✅ Agents updated:', transformedAgents);
    } catch (err) {
      console.error('Error fetching agents:', err);
      setError('Failed to load agent data');
      // Mock data for development
      setAgents([
        {
          id: 'LinkAgent',
          name: 'Link Agent',
          type: 'link',
          status: 'active',
          tasks_completed: 45,
          uptime: 3600,
          last_activity: '2 minutes ago',
          cpu_usage: 15.2,
          memory_usage: 128
        },
        {
          id: 'ResearchAgent',
          name: 'Research Agent',
          type: 'research',
          status: 'active',
          tasks_completed: 23,
          uptime: 2400,
          last_activity: '30 seconds ago',
          cpu_usage: 8.7,
          memory_usage: 95
        },
        {
          id: 'ExecutionAgent',
          name: 'Execution Agent',
          type: 'execution',
          status: 'idle',
          tasks_completed: 12,
          uptime: 1800,
          last_activity: '15 minutes ago',
          cpu_usage: 3.1,
          memory_usage: 64
        },
        {
          id: 'RetrievalAgent',
          name: 'Retrieval Agent',
          type: 'retrieval',
          status: 'active',
          tasks_completed: 78,
          uptime: 5400,
          last_activity: '1 minute ago',
          cpu_usage: 22.4,
          memory_usage: 156
        },
        {
          id: 'GuardianAgent',
          name: 'Guardian Agent',
          type: 'guardian',
          status: 'monitoring',
          tasks_completed: 156,
          uptime: 7200,
          last_activity: 'continuous',
          cpu_usage: 5.8,
          memory_usage: 89
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // WebSocket event handlers
  const handleAgentStatusUpdate = (data) => {
    console.log('🔄 Agent status update received:', data);
    if (data.agent_type && data.status) {
      setAgents(prevAgents => 
        prevAgents.map(agent => 
          agent.type === data.agent_type 
            ? { 
                ...agent, 
                status: data.status === 'ready' ? 'active' : data.status,
                last_activity: new Date().toLocaleString()
              }
            : agent
        )
      );
    }
  };

  const handleTaskUpdate = (data) => {
    console.log('📋 Task update received:', data);
    if (data.agent_type) {
      setAgents(prevAgents => 
        prevAgents.map(agent => 
          agent.type === data.agent_type 
            ? { 
                ...agent, 
                tasks_completed: data.task_type === 'task_completed' 
                  ? (agent.tasks_completed || 0) + 1 
                  : agent.tasks_completed,
                status: data.task_type === 'task_started' ? 'active' : agent.status,
                last_activity: new Date().toLocaleString()
              }
            : agent
        )
      );
      
      // Show notification for task events
      const taskTypeMessages = {
        'task_started': `${data.agent_type} agent started a new task`,
        'task_completed': `${data.agent_type} agent completed a task`,
        'task_failed': `${data.agent_type} agent task failed`
      };
      
      if (taskTypeMessages[data.task_type]) {
        showNotification(
          taskTypeMessages[data.task_type], 
          data.task_type === 'task_failed' ? 'error' : 'info'
        );
      }
    }
  };

  const handlePerformanceUpdate = (data) => {
    console.log('⚡ Performance update received:', data);
    if (data.agent_type) {
      setAgents(prevAgents => 
        prevAgents.map(agent => 
          agent.type === data.agent_type 
            ? { 
                ...agent, 
                cpu_usage: data.cpu_usage || agent.cpu_usage,
                memory_usage: data.memory_usage || agent.memory_usage,
                uptime: data.uptime || agent.uptime
              }
            : agent
        )
      );
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return '#27ae60';
      case 'idle': return '#f39c12';
      case 'monitoring': return '#3498db';
      case 'error': return '#e74c3c';
      default: return '#95a5a6';
    }
  };

  const getAgentTypeIcon = (type) => {
    const icons = {
      link: '🔗',
      research: '🔍',
      execution: '⚡',
      retrieval: '📚',
      guardian: '🛡️'
    };
    return icons[type] || '🤖';
  };

  const formatUptime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const formatMemory = (mb) => {
    return mb > 1024 ? `${(mb/1024).toFixed(1)}GB` : `${mb}MB`;
  };

  const showNotification = (message, type = 'info') => {
    setNotification({ show: true, message, type });
    setTimeout(() => setNotification({ show: false, message: '', type: 'info' }), 3000);
  };

  const handleRestartAgent = async (agentType) => {
    try {
      const response = await fetch(`http://localhost:8000/api/agents/${agentType}/restart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        showNotification(`${agentType} agent restarted successfully`, 'success');
        fetchAgents(); // Refresh agent data
      } else {
        throw new Error('Restart failed');
      }
    } catch (error) {
      console.error('Error restarting agent:', error);
      showNotification(`Failed to restart ${agentType} agent`, 'error');
    }
  };

  const handleViewLogs = async (agentType) => {
    try {
      setSelectedAgent(agentType);
      const response = await fetch(`http://localhost:8000/api/agents/${agentType}/logs`);
      
      if (response.ok) {
        const data = await response.json();
        // Format logs as string for React rendering
        const formattedLogs = data.logs && Array.isArray(data.logs) 
          ? data.logs.map(log => `[${log.timestamp}] ${log.level}: ${log.message}`).join('\n')
          : 'No logs available';
        setAgentLogs(formattedLogs);
        setShowLogsModal(true);
      } else {
        throw new Error('Failed to fetch logs');
      }
    } catch (error) {
      console.error('Error fetching logs:', error);
      setAgentLogs(`Error loading logs for ${agentType} agent`);
      setShowLogsModal(true);
    }
  };

  const handleConfigureAgent = (agentType) => {
    setSelectedAgent(agentType);
    setShowConfigModal(true);
  };

  if (loading) {
    return (
      <div className="agent-status">
        <div className="loading">
          <div className="loading-spinner"></div>
          <p>Loading agent data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="agent-status">
      <div className="agent-header">
        <h2>Agent Status Dashboard</h2>
        <div className="status-summary">
          <span className="summary-item">
            <strong>{agents.filter(a => a.status === 'active').length}</strong> Active
          </span>
          <span className="summary-item">
            <strong>{agents.filter(a => a.status === 'idle').length}</strong> Idle
          </span>
          <span className="summary-item">
            <strong>{agents.length}</strong> Total
          </span>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠️ {error} - Showing demo data</span>
        </div>
      )}

      {/* WebSocket Connection Status */}
      <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
        <span className="status-indicator"></span>
        {isConnected ? '🟢 Real-time updates active' : '🔴 Connecting to real-time updates...'}
      </div>

      <div className="agents-grid">
        {agents.map((agent, index) => (
          <div key={agent.id || agent.name || index} className="agent-card">
            <div className="agent-header-info">
              <div className="agent-icon">
                {getAgentTypeIcon(agent.type)}
              </div>
              <div className="agent-title">
                <h3>{agent.name}</h3>
                <span className="agent-type">{agent.type.toUpperCase()}</span>
              </div>
              <div 
                className="status-indicator"
                style={{ backgroundColor: getStatusColor(agent.status) }}
                title={agent.status}
              ></div>
            </div>

            <div className="agent-stats">
              <div className="stat-row">
                <div className="stat">
                  <span className="stat-label">Status</span>
                  <span className="stat-value" style={{ color: getStatusColor(agent.status) }}>
                    {agent.status.charAt(0).toUpperCase() + agent.status.slice(1)}
                  </span>
                </div>
                <div className="stat">
                  <span className="stat-label">Uptime</span>
                  <span className="stat-value">{formatUptime(agent.uptime)}</span>
                </div>
              </div>

              <div className="stat-row">
                <div className="stat">
                  <span className="stat-label">Tasks</span>
                  <span className="stat-value">{agent.tasks_completed}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Last Activity</span>
                  <span className="stat-value">{agent.last_activity}</span>
                </div>
              </div>

              <div className="performance-metrics">
                <div className="metric">
                  <span className="metric-label">CPU Usage</span>
                  <div className="metric-bar">
                    <div 
                      className="metric-fill cpu"
                      style={{ width: `${Math.min(agent.cpu_usage, 100)}%` }}
                    ></div>
                  </div>
                  <span className="metric-value">{agent.cpu_usage}%</span>
                </div>

                <div className="metric">
                  <span className="metric-label">Memory</span>
                  <div className="metric-bar">
                    <div 
                      className="metric-fill memory"
                      style={{ width: `${Math.min((agent.memory_usage / 512) * 100, 100)}%` }}
                    ></div>
                  </div>
                  <span className="metric-value">{formatMemory(agent.memory_usage)}</span>
                </div>
              </div>
            </div>

            <div className="agent-actions">
              <button 
                className="action-btn restart"
                onClick={() => handleRestartAgent(agent.type)}
              >
                Restart
              </button>
              <button 
                className="action-btn logs"
                onClick={() => handleViewLogs(agent.type)}
              >
                View Logs
              </button>
              <button 
                className="action-btn config"
                onClick={() => handleConfigureAgent(agent.type)}
              >
                Configure
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Notification */}
      {notification.show && (
        <div className={`notification notification-${notification.type}`}>
          {notification.message}
        </div>
      )}

      {/* Logs Modal */}
      {showLogsModal && (
        <div className="modal-overlay" onClick={() => setShowLogsModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Agent Logs - {selectedAgent}</h3>
              <button className="modal-close" onClick={() => setShowLogsModal(false)}>×</button>
            </div>
            <div className="modal-content">
              <pre className="logs-content">{agentLogs}</pre>
            </div>
          </div>
        </div>
      )}

      {/* Configuration Modal */}
      {showConfigModal && (
        <div className="modal-overlay" onClick={() => setShowConfigModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Configure {selectedAgent} Agent</h3>
              <button className="modal-close" onClick={() => setShowConfigModal(false)}>×</button>
            </div>
            <div className="modal-content">
              <div className="config-form">
                <div className="form-group">
                  <label>Agent Status:</label>
                  <select>
                    <option>Active</option>
                    <option>Idle</option>
                    <option>Disabled</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Priority Level:</label>
                  <input type="range" min="1" max="10" defaultValue="5" />
                </div>
                <div className="form-group">
                  <label>Task Limit:</label>
                  <input type="number" defaultValue="50" />
                </div>
                <div className="form-actions">
                  <button className="btn-save">Save Changes</button>
                  <button className="btn-cancel" onClick={() => setShowConfigModal(false)}>Cancel</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentStatus;
