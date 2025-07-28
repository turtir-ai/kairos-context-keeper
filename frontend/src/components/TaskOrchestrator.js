import React, { useState, useEffect, useCallback } from 'react';
import './TaskOrchestrator.css';
import { useWebSocketContext } from '../contexts/WebSocketContext';

const TaskOrchestrator = () => {
  const { subscribe, isConnected } = useWebSocketContext();
  const [tasks, setTasks] = useState([]);
  const [workflows, setWorkflows] = useState([]);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTask, setSelectedTask] = useState(null);
  const [showCreateTask, setShowCreateTask] = useState(false);
  const [showCreateWorkflow, setShowCreateWorkflow] = useState(false);
  const [mcpContext, setMcpContext] = useState(null);
  const [showMcpPanel, setShowMcpPanel] = useState(false);

  // Form states
  const [taskForm, setTaskForm] = useState({
    type: 'research',
    description: '',
    priority: 'medium',
    dependencies: [],
    agent: '',
    metadata: {}
  });
  
  const [workflowForm, setWorkflowForm] = useState({
    name: '',
    description: '',
    tasks: [],
    trigger: 'manual'
  });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [tasksRes, workflowsRes, agentsRes] = await Promise.all([
        fetch('http://localhost:8000/api/orchestration/tasks'),
        fetch('http://localhost:8000/api/orchestration/workflows'),
        fetch('http://localhost:8000/api/agent/status')
      ]);

      if (!tasksRes.ok || !workflowsRes.ok || !agentsRes.ok) {
        throw new Error('Failed to fetch data');
      }

      const [tasksData, workflowsData, agentsData] = await Promise.all([
        tasksRes.json(),
        workflowsRes.json(),
        agentsRes.json()
      ]);

      // Use real task history from backend
      const taskHistory = tasksData.task_history || [];
      
      // Convert backend task format to frontend format
      const realTasks = taskHistory.map(task => ({
        id: task.id,
        type: task.name || task.type || 'unknown', // Backend uses 'name' field
        description: task.name || task.description || 'No description',
        status: task.status,
        priority: task.priority || 'medium',
        agent: task.agent,
        created: task.created_at || task.created,
        completed: task.completed,
        started: task.started,
        progress: task.progress,
        result: task.result,
        error: task.error,
        duration: task.duration
      }));
      
      // Get workflow data from backend
      const realWorkflows = workflowsData.workflow_history || [];
      const workflows = realWorkflows.map(workflow => ({
        id: workflow.id,
        name: workflow.name,
        description: workflow.description || 'No description available',
        tasks: workflow.tasks || [],
        trigger: workflow.trigger || 'manual',
        lastRun: workflow.lastRun,
        status: workflow.status,
        progress: workflow.progress
      }));
      
      setTasks(realTasks);
      setWorkflows(workflows);
      setAgents(['ResearchAgent', 'ExecutionAgent', 'GuardianAgent', 'RetrievalAgent', 'LinkAgent']);
    } catch (err) {
      console.error('Failed to fetch orchestration data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isConnected) return;

    const handleTaskUpdate = (data) => {
      console.log('Task update received:', data);
      setTasks(prevTasks => {
        const taskExists = prevTasks.some(t => t.id === data.task_id);
        if (taskExists) {
          // Update existing task
          return prevTasks.map(t => t.id === data.task_id ? { ...t, ...data } : t);
        } else {
          // Add new task
          return [...prevTasks, data];
        }
      });
    };

    const handleMcpContextUpdate = (data) => {
      console.log('MCP context update received:', data);
      setMcpContext(data);
      // Auto-show MCP panel when context is updated for selected task
      if (selectedTask && data.task_id === selectedTask.id) {
        setShowMcpPanel(true);
      }
    };

    const unsubscribeTaskUpdate = subscribe('task_update', handleTaskUpdate);
    const unsubscribeMcpUpdate = subscribe('mcp_context_update', handleMcpContextUpdate);
    fetchData(); // Initial data fetch

    return () => {
      unsubscribeTaskUpdate();
      unsubscribeMcpUpdate();
    };
  }, [isConnected, subscribe, fetchData]);

  const handleCreateTask = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('http://localhost:8000/api/orchestration/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(taskForm)
      });

      if (!response.ok) throw new Error('Failed to create task');
      
      setTaskForm({
        type: 'research',
        description: '',
        priority: 'medium',
        dependencies: [],
        agent: '',
        metadata: {}
      });
      setShowCreateTask(false);
      fetchData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCreateWorkflow = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('http://localhost:8000/api/orchestration/workflows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(workflowForm)
      });

      if (!response.ok) throw new Error('Failed to create workflow');
      
      setWorkflowForm({
        name: '',
        description: '',
        tasks: [],
        trigger: 'manual'
      });
      setShowCreateWorkflow(false);
      fetchData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleExecuteTask = async (taskId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/orchestration/tasks/${taskId}/execute`, {
        method: 'POST'
      });
      
      if (!response.ok) throw new Error('Failed to execute task');
      fetchData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleExecuteWorkflow = async (workflowId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/orchestration/workflows/${workflowId}/execute`, {
        method: 'POST'
      });
      
      if (!response.ok) throw new Error('Failed to execute workflow');
      fetchData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCancelTask = async (taskId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/orchestration/tasks/${taskId}/cancel`, {
        method: 'POST'
      });
      
      if (!response.ok) throw new Error('Failed to cancel task');
      fetchData();
    } catch (err) {
      setError(err.message);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      'pending': '#fbbf24',
      'running': '#3b82f6',
      'completed': '#10b981',
      'failed': '#ef4444',
      'cancelled': '#6b7280'
    };
    return colors[status] || '#6b7280';
  };

  const getPriorityColor = (priority) => {
    const colors = {
      'low': '#10b981',
      'medium': '#fbbf24',
      'high': '#f97316',
      'critical': '#ef4444'
    };
    return colors[priority] || '#6b7280';
  };

  if (loading) {
    return (
      <div className="orchestrator-loading">
        <div className="loading-spinner"></div>
        <p>Loading orchestration data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="orchestrator-error">
        <h3>Error Loading Data</h3>
        <p>{error}</p>
        <button onClick={fetchData} className="retry-btn">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="task-orchestrator">
      <div className="orchestrator-header">
        <div className="header-left">
          <h2>Task Orchestrator</h2>
          <div className="orchestrator-stats">
            <div className="stat">
              <span className="stat-label">Active Tasks</span>
              <span className="stat-value">
                {tasks.filter(t => t.status === 'running').length}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Pending Tasks</span>
              <span className="stat-value">
                {tasks.filter(t => t.status === 'pending').length}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Workflows</span>
              <span className="stat-value">{workflows.length}</span>
            </div>
          </div>
        </div>
        
        <div className="header-controls">
          <button 
            onClick={() => setShowCreateTask(true)}
            className="create-btn"
          >
            + Create Task
          </button>
          <button 
            onClick={() => setShowCreateWorkflow(true)}
            className="create-btn secondary"
          >
            + Create Workflow
          </button>
        </div>
      </div>

      <div className="orchestrator-content">
        <div className="content-section">
          <div className="section-header">
            <h3>Active Tasks</h3>
            <span className="task-count">{tasks.length} tasks</span>
          </div>
          
          <div className="tasks-grid">
            {tasks.map((task) => (
              <div 
                key={task.id} 
                className={`task-card ${task.status}`}
                onClick={() => setSelectedTask(task)}
              >
                <div className="task-header">
                  <div className="task-type">{task.type}</div>
                  <div 
                    className="task-status"
                    style={{ backgroundColor: getStatusColor(task.status) }}
                  >
                    {task.status}
                  </div>
                </div>
                
                <div className="task-description">
                  {task.description}
                </div>
                
                <div className="task-meta">
                  <div 
                    className="task-priority"
                    style={{ color: getPriorityColor(task.priority) }}
                  >
                    {task.priority} priority
                  </div>
                  {task.agent && (
                    <div className="task-agent">
                      Agent: {task.agent}
                    </div>
                  )}
                </div>
                
                <div className="task-actions">
                  {task.status === 'pending' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleExecuteTask(task.id);
                      }}
                      className="action-btn execute"
                    >
                      Execute
                    </button>
                  )}
                  {task.status === 'running' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCancelTask(task.id);
                      }}
                      className="action-btn cancel"
                    >
                      Cancel
                    </button>
                  )}
                </div>
                
                {task.progress !== undefined && (
                  <div className="task-progress">
                    <div className="progress-bar">
                      <div 
                        className="progress-fill"
                        style={{ width: `${task.progress}%` }}
                      ></div>
                    </div>
                    <span className="progress-text">{task.progress}%</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="content-section">
          <div className="section-header">
            <h3>Workflows</h3>
            <span className="workflow-count">{workflows.length} workflows</span>
          </div>
          
          <div className="workflows-grid">
            {workflows.map((workflow) => (
              <div key={workflow.id} className="workflow-card">
                <div className="workflow-header">
                  <h4>{workflow.name}</h4>
                  <button
                    onClick={() => handleExecuteWorkflow(workflow.id)}
                    className="action-btn execute"
                  >
                    Execute
                  </button>
                </div>
                
                <div className="workflow-description">
                  {workflow.description}
                </div>
                
                <div className="workflow-tasks">
                  <span className="tasks-label">
                    {workflow.tasks?.length || 0} tasks
                  </span>
                  <span className="trigger-label">
                    Trigger: {workflow.trigger}
                  </span>
                </div>
                
                {workflow.lastRun && (
                  <div className="workflow-lastrun">
                    Last run: {new Date(workflow.lastRun).toLocaleDateString()}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Create Task Modal */}
      {showCreateTask && (
        <div className="modal-overlay" onClick={() => setShowCreateTask(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create New Task</h3>
              <button 
                onClick={() => setShowCreateTask(false)}
                className="close-btn"
              >
                ×
              </button>
            </div>
            
            <form onSubmit={handleCreateTask} className="task-form">
              <div className="form-group">
                <label>Task Type</label>
                <select
                  value={taskForm.type}
                  onChange={(e) => setTaskForm({...taskForm, type: e.target.value})}
                >
                  <option value="research">Research</option>
                  <option value="analysis">Analysis</option>
                  <option value="execution">Execution</option>
                  <option value="monitoring">Monitoring</option>
                </select>
              </div>
              
              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={taskForm.description}
                  onChange={(e) => setTaskForm({...taskForm, description: e.target.value})}
                  placeholder="Describe what this task should accomplish..."
                  required
                />
              </div>
              
              <div className="form-group">
                <label>Priority</label>
                <select
                  value={taskForm.priority}
                  onChange={(e) => setTaskForm({...taskForm, priority: e.target.value})}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              
              <div className="form-group">
                <label>Preferred Agent</label>
                <select
                  value={taskForm.agent}
                  onChange={(e) => setTaskForm({...taskForm, agent: e.target.value})}
                >
                  <option value="">Auto-assign</option>
                  {agents.map(agent => (
                    <option key={agent} value={agent}>{agent}</option>
                  ))}
                </select>
              </div>
              
              <div className="form-actions">
                <button 
                  type="button" 
                  onClick={() => setShowCreateTask(false)}
                  className="cancel-btn"
                >
                  Cancel
                </button>
                <button type="submit" className="submit-btn">
                  Create Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Workflow Modal */}
      {showCreateWorkflow && (
        <div className="modal-overlay" onClick={() => setShowCreateWorkflow(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create New Workflow</h3>
              <button 
                onClick={() => setShowCreateWorkflow(false)}
                className="close-btn"
              >
                ×
              </button>
            </div>
            
            <form onSubmit={handleCreateWorkflow} className="workflow-form">
              <div className="form-group">
                <label>Workflow Name</label>
                <input
                  type="text"
                  value={workflowForm.name}
                  onChange={(e) => setWorkflowForm({...workflowForm, name: e.target.value})}
                  placeholder="Enter workflow name..."
                  required
                />
              </div>
              
              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={workflowForm.description}
                  onChange={(e) => setWorkflowForm({...workflowForm, description: e.target.value})}
                  placeholder="Describe this workflow..."
                  required
                />
              </div>
              
              <div className="form-group">
                <label>Trigger Type</label>
                <select
                  value={workflowForm.trigger}
                  onChange={(e) => setWorkflowForm({...workflowForm, trigger: e.target.value})}
                >
                  <option value="manual">Manual</option>
                  <option value="scheduled">Scheduled</option>
                  <option value="event">Event-based</option>
                </select>
              </div>
              
              <div className="form-actions">
                <button 
                  type="button" 
                  onClick={() => setShowCreateWorkflow(false)}
                  className="cancel-btn"
                >
                  Cancel
                </button>
                <button type="submit" className="submit-btn">
                  Create Workflow
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Task Detail Modal */}
      {selectedTask && (
        <div className="modal-overlay" onClick={() => setSelectedTask(null)}>
          <div className="modal-content large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Task Details: {selectedTask.type}</h3>
              <button 
                onClick={() => setSelectedTask(null)}
                className="close-btn"
              >
                ×
              </button>
            </div>
            
            <div className="task-details">
              <div className="detail-section">
                <h4>Description</h4>
                <p>{selectedTask.description}</p>
              </div>
              
              <div className="detail-row">
                <div className="detail-item">
                  <label>Status</label>
                  <span 
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(selectedTask.status) }}
                  >
                    {selectedTask.status}
                  </span>
                </div>
                <div className="detail-item">
                  <label>Priority</label>
                  <span 
                    className="priority-badge"
                    style={{ color: getPriorityColor(selectedTask.priority) }}
                  >
                    {selectedTask.priority}
                  </span>
                </div>
              </div>
              
              {selectedTask.agent && (
                <div className="detail-section">
                  <h4>Assigned Agent</h4>
                  <p>{selectedTask.agent}</p>
                </div>
              )}
              
              {selectedTask.result && (
                <div className="detail-section">
                  <h4>Result</h4>
                  <pre className="task-result">
                    {typeof selectedTask.result === 'object' 
                      ? JSON.stringify(selectedTask.result, null, 2)
                      : selectedTask.result
                    }
                  </pre>
                </div>
              )}
              
              {selectedTask.error && (
                <div className="detail-section error">
                  <h4>Error</h4>
                  <pre className="task-error">{selectedTask.error}</pre>
                </div>
              )}
              
              {/* MCP Context Section */}
              <div className="detail-section mcp-section">
                <div className="section-header">
                  <h4>MCP Context</h4>
                  <button 
                    onClick={() => setShowMcpPanel(!showMcpPanel)}
                    className={`toggle-btn ${showMcpPanel ? 'active' : ''}`}
                  >
                    {showMcpPanel ? 'Hide Context' : 'Show Context'}
                  </button>
                </div>
                
                {showMcpPanel && mcpContext && (
                  <div className="mcp-context-panel">
                    <div className="context-tabs">
                      <div className="tab-buttons">
                        <button className="tab-btn active">Overview</button>
                        <button className="tab-btn">Memory</button>
                        <button className="tab-btn">Tools</button>
                        <button className="tab-btn">Raw Data</button>
                      </div>
                      
                      <div className="tab-content">
                        <div className="context-overview">
                          <div className="context-stats">
                            <div className="stat-item">
                              <span className="stat-label">Context ID</span>
                              <span className="stat-value">{mcpContext.context_id || 'N/A'}</span>
                            </div>
                            <div className="stat-item">
                              <span className="stat-label">Project ID</span>
                              <span className="stat-value">{mcpContext.project_id || 'N/A'}</span>
                            </div>
                            <div className="stat-item">
                              <span className="stat-label">Memories</span>
                              <span className="stat-value">{mcpContext.context_summary?.memories_count || 0}</span>
                            </div>
                            <div className="stat-item">
                              <span className="stat-label">Tools</span>
                              <span className="stat-value">{mcpContext.context_summary?.tools_count || 0}</span>
                            </div>
                            <div className="stat-item">
                              <span className="stat-label">Context Size</span>
                              <span className="stat-value">{mcpContext.context_summary?.context_size || 0} chars</span>
                            </div>
                          </div>
                          
                          {mcpContext.relevant_memories && mcpContext.relevant_memories.length > 0 && (
                            <div className="memory-preview">
                              <h5>Relevant Memories</h5>
                              <div className="memory-list">
                                {mcpContext.relevant_memories.map((memory, index) => (
                                  <div key={index} className="memory-item">
                                    <div className="memory-title">
                                      {memory.title || `Memory ${index + 1}`}
                                    </div>
                                    <div className="memory-content">
                                      {memory.content ? memory.content.substring(0, 100) + '...' : 'No content'}
                                    </div>
                                    <div className="memory-meta">
                                      <span className="memory-type">{memory.type || 'unknown'}</span>
                                      <span className="memory-score">Score: {memory.score?.toFixed(2) || 'N/A'}</span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          
                          {mcpContext.available_tools && mcpContext.available_tools.length > 0 && (
                            <div className="tools-preview">
                              <h5>Available Tools</h5>
                              <div className="tools-list">
                                {mcpContext.available_tools.map((tool, index) => (
                                  <div key={index} className="tool-item">
                                    <div className="tool-name">{tool.name}</div>
                                    <div className="tool-description">{tool.description}</div>
                                    <div className="tool-id">{tool.tool_id}</div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                
                {!mcpContext && (
                  <div className="no-mcp-context">
                    <p>No MCP context available for this task.</p>
                    <small>MCP context is provided when agents use contextual memory and tools.</small>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TaskOrchestrator;
