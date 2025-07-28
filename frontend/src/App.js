import React, { useState, useEffect } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';
import AgentStatus from './components/AgentStatus';
import MemoryViewer from './components/MemoryViewer';
import MonitoringPanel from './components/MonitoringPanel';
import TaskOrchestrator from './components/TaskOrchestrator';
import AiInterface from './components/AiInterface';
import GraphVisualization from './components/GraphVisualization';
import AdvancedAnalytics from './components/AdvancedAnalytics';
import { WebSocketProvider } from './contexts/WebSocketContext';

function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [systemStatus, setSystemStatus] = useState({});
  
  const navigationItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '🏠' },
    { id: 'ai', label: 'AI Chat', icon: '💬' },
    { id: 'agents', label: 'Agents', icon: '🤖' },
    { id: 'memory', label: 'Memory', icon: '🧠' },
    { id: 'graph', label: 'Knowledge Graph', icon: '🕸️' },
    { id: 'monitoring', label: 'Monitoring', icon: '📊' },
    { id: 'orchestration', label: 'Tasks', icon: '🎭' },
    { id: 'analytics', label: 'Advanced Analytics', icon: '📊' }
  ];
  
  // Handle URL hash changes for navigation
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '');
      if (hash && navigationItems.find(item => item.id === hash)) {
        setCurrentView(hash);
      }
    };
    
    // Check initial hash
    handleHashChange();
    
    // Listen for hash changes
    window.addEventListener('hashchange', handleHashChange);
    
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, [navigationItems]);

  useEffect(() => {
    // Fetch initial system status
    fetchSystemStatus();
    
    // Set up periodic status updates
    const interval = setInterval(fetchSystemStatus, 30000); // Every 30 seconds
    
    return () => clearInterval(interval);
  }, []);

  const fetchSystemStatus = async () => {
    try {
      const response = await fetch('/status');
      const data = await response.json();
      setSystemStatus(data);
    } catch (error) {
      console.error('Failed to fetch system status:', error);
    }
  };


  const renderCurrentView = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard systemStatus={systemStatus} />;
      case 'ai':
        return <AiInterface />;
      case 'agents':
        return <AgentStatus />;
      case 'memory':
        return <MemoryViewer />;
      case 'graph':
        return <GraphVisualization />;
      case 'monitoring':
        return <MonitoringPanel />;
      case 'orchestration':
        return <TaskOrchestrator />;
      case 'analytics':
        return <AdvancedAnalytics />;
      default:
        return <Dashboard systemStatus={systemStatus} />;
    }
  };

  return (
    <WebSocketProvider>
      <div className="app">
        <header className="app-header">
          <div className="header-content">
            <h1 className="app-title">
              🌌 Kairos: The Context Keeper
            </h1>
            <div className="system-status">
              <span className={`status-indicator ${systemStatus.daemon === 'running' ? 'active' : 'inactive'}`}>
                {systemStatus.daemon === 'running' ? '🟢' : '🔴'}
              </span>
              <span className="status-text">
                {systemStatus.daemon === 'running' ? 'Active' : 'Inactive'}
              </span>
            </div>
          </div>
        </header>

        <div className="app-body">
          <nav className="sidebar">
            <ul className="nav-list">
              {navigationItems.map(item => (
                <li key={item.id} className="nav-item">
                  <button
                    className={`nav-button ${currentView === item.id ? 'active' : ''}`}
                    onClick={() => {
                      setCurrentView(item.id);
                      window.location.hash = item.id;
                    }}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <span className="nav-label">{item.label}</span>
                  </button>
                </li>
              ))}
            </ul>
          </nav>

          <main className="main-content">
            {renderCurrentView()}
          </main>
        </div>
      </div>
    </WebSocketProvider>
  );
}

export default App;
