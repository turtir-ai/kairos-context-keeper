import asyncio
import logging
import uuid
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union, Set
from dataclasses import dataclass, asdict
from enum import Enum
import json
from collections import deque
from abc import ABC, abstractmethod
from pathlib import Path

# Import WebSocket types
try:
    from ..api.websocket_manager import WebSocketMessage, MessageType
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from api.websocket_manager import WebSocketMessage, MessageType

# Import memory systems
try:
    from ..memory.neo4j_memory import Neo4jMemory
    from ..memory.qdrant_memory import QdrantMemory
    from ..memory.memory_manager import MemoryManager
except ImportError:
    try:
        from memory.neo4j_memory import Neo4jMemory
        from memory.qdrant_memory import QdrantMemory
        from memory.memory_manager import MemoryManager
    except ImportError:
        Neo4jMemory = None
        QdrantMemory = None
        MemoryManager = None

# Import MCP for context management
try:
    from ..mcp.model_context_protocol import ModelContextProtocol, MCPContext
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

# Import plugin system
# from src.plugins.plugin_loader import PluginLoader  # Will be implemented later

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Task:
    """Represents a task to be executed by agents"""
    id: str
    name: str
    agent_type: str
    parameters: Dict[str, Any]
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    dependencies: List[str] = None
    max_retries: int = 3
    retry_count: int = 0
    timeout_seconds: int = 300
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class AgentWorkflow:
    """Represents a workflow of connected tasks"""
    id: str
    name: str
    description: str
    tasks: List[Task]
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

class AgentCoordinator:
    """Enhanced coordination system for multiple agents with advanced metrics and communication"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Task management
        self.pending_tasks = deque()
        self.running_tasks = {}
        self.completed_tasks = deque(maxlen=1000)
        self.failed_tasks = deque(maxlen=100)
        self.paused_tasks = {}
        
        # Workflow management
        self.workflows = {}
        self.active_workflows = {}
        self.workflow_templates = {}
        
        # Workflow persistence
        self.persistence_path = Path("data/workflows")
        self.persistence_path.mkdir(parents=True, exist_ok=True)
        self.checkpoint_interval = 60  # seconds
        
        # Agent registry and communication
        self.registered_agents = {}
        self.agent_capabilities = {}
        self.agent_health = {}
        self.agent_communication_log = deque(maxlen=500)
        
        # Execution control
        self.max_concurrent_tasks = 5
        self.executor_running = False
        self.executor_task = None
        self.auto_scaling_enabled = True
        
        # Enhanced performance tracking
        self.coordination_stats = {
            "tasks_executed": 0,
            "tasks_failed": 0,
            "tasks_paused": 0,
            "workflows_completed": 0,
            "average_task_duration": 0.0,
            "agent_utilization": {},
            "inter_agent_communications": 0,
            "system_efficiency": 0.0
        }

        # Advanced metrics
        self.performance_history = deque(maxlen=1000)
        self.task_success_rate = 0.0
        self.agent_load_balancing = {}

        # Task prioritization weights
        self.priority_weights = {
            TaskPriority.CRITICAL: 4.0,
            TaskPriority.HIGH: 3.0,
            TaskPriority.MEDIUM: 2.0,
            TaskPriority.LOW: 1.0
        }

        # WebSocket manager for real-time updates
        self.websocket_manager = None
        
        # Database connection for fine-tuning data collection
        self.db_pool = None
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'kairos_db',
            'user': 'kairos_user',
            'password': 'secure_password'
        }
        
        # Database will be initialized when needed
        self.db_initialized = False

        # Initialize Plugin Loader (will be implemented later)
        self.plugin_loader = None  # PluginLoader()
        self.plugins_initialized = False
        
        # Initialize MCP and MemoryManager if available
        self.mcp = None
        self.memory_manager = None
        if MCP_AVAILABLE and MemoryManager:
            try:
                self.mcp = ModelContextProtocol()
                self.memory_manager = MemoryManager()
                self.logger.info("✅ MCP and MemoryManager initialized for context-aware task execution")
            except Exception as e:
                self.logger.warning(f"Failed to initialize MCP/MemoryManager: {e}")

        self.logger.info("🎭 Enhanced Agent Coordinator initialized with advanced metrics and plugin support")

        # Load saved workflows on startup
        self._load_saved_workflows()
    
    async def _initialize_plugins(self):
        """Initialize and load plugins"""
        try:
            # Discover available plugins
            discovered_plugins = await self.plugin_loader.discover_plugins()
            self.logger.info(f"🔌 Discovered {len(discovered_plugins)} plugins: {discovered_plugins}")
            
            # Load all discovered plugins
            for plugin_name in discovered_plugins:
                try:
                    success = await self.plugin_loader.load_plugin(plugin_name)
                    if success:
                        # Register plugin as an available agent type
                        plugin_instance = self.plugin_loader.get_plugin(plugin_name)
                        if plugin_instance:
                            metadata = plugin_instance.get_metadata()
                            capabilities = [cap.name for cap in metadata.capabilities]
                            self.register_agent(f"{plugin_name}_plugin", plugin_instance, capabilities)
                            self.logger.info(f"✅ Loaded and registered plugin: {plugin_name}")
                    else:
                        self.logger.warning(f"⚠️ Failed to load plugin: {plugin_name}")
                except Exception as e:
                    self.logger.error(f"❌ Error loading plugin {plugin_name}: {e}")
            
            # Log final plugin status
            loaded_plugins = self.plugin_loader.list_loaded_plugins()
            self.logger.info(f"🚀 {len(loaded_plugins)} plugins loaded successfully: {loaded_plugins}")
            
        except Exception as e:
            self.logger.error(f"❌ Plugin initialization failed: {e}")

    async def _persist_task_results(self, task: Task):
        """Persist task results to memory systems (Neo4j and Qdrant)"""
        if Neo4jMemory:
            try:
                neo4j_memory = Neo4jMemory()
                await neo4j_memory.save_task_result(task.id, task.result)
                self.logger.info(f"🔗 Task {task.id} results saved to Neo4j")
            except Exception as e:
                self.logger.error(f"⚠️ Failed to save task {task.id} to Neo4j: {str(e)}")
        if QdrantMemory:
            try:
                qdrant_memory = QdrantMemory()
                await qdrant_memory.save_task_result(task.id, task.result)
                self.logger.info(f"🧠 Task {task.id} results saved to Qdrant")
            except Exception as e:
                self.logger.error(f"⚠️ Failed to save task {task.id} to Qdrant: {str(e)}")
        
    
    def register_agent(self, agent_type: str, agent_instance, capabilities: List[str] = None):
        """Register an agent with the coordinator"""
        self.registered_agents[agent_type] = agent_instance
        self.agent_capabilities[agent_type] = capabilities or []
        self.coordination_stats["agent_utilization"][agent_type] = {
            "tasks_assigned": 0,
            "tasks_completed": 0,
            "average_execution_time": 0.0
        }
        
        self.logger.info(f"📝 Registered agent: {agent_type} with capabilities: {capabilities}")
    
    def get_agent(self, agent_type: str):
        """Get a registered agent instance"""
        return self.registered_agents.get(agent_type)
    
    def create_task(self, name: str, agent_type: str, parameters: Dict[str, Any], 
                   priority: TaskPriority = TaskPriority.MEDIUM, 
                   dependencies: List[str] = None,
                   timeout_seconds: int = 300) -> str:
        """Create a new task"""
        task_id = str(uuid.uuid4())[:8]
        
        task = Task(
            id=task_id,
            name=name,
            agent_type=agent_type,
            parameters=parameters,
            priority=priority,
            dependencies=dependencies or [],
            timeout_seconds=timeout_seconds
        )
        
        # Add to pending queue (sorted by priority)
        self._insert_task_by_priority(task)
        
        self.logger.info(f"📋 Created task {task_id}: {name} for {agent_type}")
        return task_id
    
    def _insert_task_by_priority(self, task: Task):
        """Insert task into pending queue sorted by priority"""
        # Simple insertion sort by priority
        inserted = False
        temp_queue = deque()
        
        while self.pending_tasks and not inserted:
            current_task = self.pending_tasks.popleft()
            if task.priority.value > current_task.priority.value:
                temp_queue.append(task)
                temp_queue.append(current_task)
                inserted = True
            else:
                temp_queue.append(current_task)
        
        if not inserted:
            temp_queue.append(task)
        
        # Add remaining tasks
        while self.pending_tasks:
            temp_queue.append(self.pending_tasks.popleft())
        
        self.pending_tasks = temp_queue
    
    def create_workflow(self, name: str, description: str, task_definitions: List[Dict]) -> str:
        """Create a workflow with multiple connected tasks"""
        workflow_id = str(uuid.uuid4())[:8]
        
        tasks = []
        for task_def in task_definitions:
            task_id = str(uuid.uuid4())[:8]
            task = Task(
                id=task_id,
                name=task_def["name"],
                agent_type=task_def["agent_type"],
                parameters=task_def["parameters"],
                priority=TaskPriority(task_def.get("priority", TaskPriority.MEDIUM.value)),
                dependencies=task_def.get("dependencies", []),
                timeout_seconds=task_def.get("timeout_seconds", 300)
            )
            tasks.append(task)
        
        workflow = AgentWorkflow(
            id=workflow_id,
            name=name,
            description=description,
            tasks=tasks
        )
        
        self.workflows[workflow_id] = workflow
        self.logger.info(f"🔄 Created workflow {workflow_id}: {name} with {len(tasks)} tasks")
        
        return workflow_id
    
    async def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a single task"""
        task = None
        
        # Find task in pending queue
        temp_queue = deque()
        while self.pending_tasks:
            current_task = self.pending_tasks.popleft()
            if current_task.id == task_id:
                task = current_task
                break
            temp_queue.append(current_task)
        
        # Restore queue
        while temp_queue:
            self.pending_tasks.appendleft(temp_queue.pop())
        
        if not task:
            return {"error": f"Task {task_id} not found"}
        
        return await self._execute_single_task(task)
    
    async def _execute_single_task(self, task: Task) -> Dict[str, Any]:
        """Execute a single task with the appropriate agent"""
        if task.agent_type not in self.registered_agents:
            error_msg = f"Agent type {task.agent_type} not registered"
            task.status = TaskStatus.FAILED
            task.error = error_msg
            self.failed_tasks.append(task)
            
            # Broadcast task failure
            if self.websocket_manager:
                await self.websocket_manager.broadcast_message(WebSocketMessage(
                    message_type=MessageType.TASK_UPDATE,
                    data={
                        "type": "task_failed",
                    "task_id": task.id,
                    "error": error_msg,
                    },
                    timestamp=datetime.now()
                ))
            
            return {"error": error_msg}
        
        # Check dependencies
        if not self._check_dependencies(task):
            error_msg = f"Task {task.id} dependencies not satisfied"
            task.error = error_msg
            return {"error": error_msg}
        
        # Move to running
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        self.running_tasks[task.id] = task
        
        # Broadcast task start
        if self.websocket_manager:
            await self.websocket_manager.broadcast_message(WebSocketMessage(
                message_type=MessageType.TASK_UPDATE,
                data={
                    "type": "task_started",
                    "task_id": task.id,
                    "agent_type": task.agent_type,
                    "name": task.name,
                    "priority": task.priority.value
                },
                timestamp=datetime.now()
            ))
        
        start_time = datetime.now()
        
        try:
            agent = self.registered_agents[task.agent_type]
            
            # Create MCP context for this task if available
            mcp_context = None
            if self.mcp and self.memory_manager:
                try:
                    # Create MCP context with task information
                    mcp_context = self.mcp.create_context(
                        project_id=task.parameters.get('project_id'),
                        session_id=task.parameters.get('session_id'),
                        user_id=task.parameters.get('user_id'),
                        initial_data={
                            'task_id': task.id,
                            'task_name': task.name,
                            'agent_type': task.agent_type,
                            'task_parameters': task.parameters
                        }
                    )
                    
                    # Retrieve relevant context from memory
                    if task.parameters.get('query') or task.parameters.get('topic'):
                        search_query = task.parameters.get('query', task.parameters.get('topic', task.name))
                        relevant_memories = self.memory_manager.recall_relevant_context(search_query, limit=5)
                        mcp_context.relevant_memories = relevant_memories.get('context_memories', [])
                        
                    # Update agent with MCP context if it supports it
                    if hasattr(agent, 'mcp_context'):
                        agent.mcp_context = mcp_context
                        
                    # Broadcast MCP context update to frontend
                    if self.websocket_manager:
                        await self.websocket_manager.broadcast_message(WebSocketMessage(
                            message_type=MessageType.MCP_CONTEXT_UPDATE,
                            data={
                                "task_id": task.id,
                                "context_id": mcp_context.context_id,
                                "project_id": mcp_context.project_id,
                                "session_id": mcp_context.session_id,
                                "global_context": mcp_context.global_context,
                                "local_context": mcp_context.local_context,
                                "relevant_memories": mcp_context.relevant_memories[:3],  # Limit for UI
                                "available_tools": [tool.to_dict() for tool in self.mcp.tools.values()][:5],  # Top 5 tools
                                "context_summary": {
                                    "memories_count": len(mcp_context.relevant_memories),
                                    "tools_count": len(self.mcp.tools),
                                    "context_size": len(str(mcp_context.global_context)) + len(str(mcp_context.local_context))
                                }
                            },
                            timestamp=datetime.now()
                        ))
                        
                except Exception as e:
                    self.logger.warning(f"Failed to create MCP context for task {task.id}: {e}")
            
            # Send progress update - 25%
            if self.websocket_manager:
                await self.websocket_manager.broadcast_message(WebSocketMessage(
                    message_type=MessageType.TASK_UPDATE,
                    data={
                        "type": "task_progress",
                        "task_id": task.id,
                        "progress": 25,
                        "message": "Initializing agent..."
                    },
                    timestamp=datetime.now()
                ))
            
            # Route to appropriate agent method based on task name
            if task.agent_type == "ExecutionAgent":
                result = agent.execute(task.parameters.get("command", ""))
            elif task.agent_type == "GuardianAgent":
                result = agent.guard(task.parameters.get("output", ""))
            elif task.agent_type == "RetrievalAgent":
                # Send progress update - 50%
                if self.websocket_manager:
                    await self.websocket_manager.broadcast_message(WebSocketMessage(
                        message_type=MessageType.TASK_UPDATE,
                        data={
                            "type": "task_progress",
                            "task_id": task.id,
                            "progress": 50,
                            "message": "Retrieving information..."
                        },
                        timestamp=datetime.now()
                    ))
                result = await agent.retrieve(task.parameters.get("query", ""))
            elif task.agent_type == "ResearchAgent":
                # Send progress update - 50%
                if self.websocket_manager:
                    await self.websocket_manager.broadcast_message(WebSocketMessage(
                        message_type=MessageType.TASK_UPDATE,
                        data={
                            "type": "task_progress",
                            "task_id": task.id,
                            "progress": 50,
                            "message": f"Researching: {task.parameters.get('topic', 'topic')}..."
                        },
                        timestamp=datetime.now()
                    ))
                result = await agent.research(
                    task.parameters.get("topic", task.parameters.get("description", "")),
                    context=task.parameters
                )
            elif task.agent_type == "LinkAgent":
                result = agent.link(task.parameters.get("concept", ""))
            elif task.agent_type == "PluginAgent":
                plugin_name = task.parameters.get("plugin_name", "")
                task_parameters = task.parameters.get("parameters", {})
                plugin_loader = self.get_agent("PluginLoader")
                result = await plugin_loader.execute_plugin_task(plugin_name, {
                    "action": task_parameters.get("action", ""),
                    "parameters": task_parameters
                })
            else:
                # Generic execution
                if hasattr(agent, 'execute'):
                    result = await agent.execute(task.parameters)
                else:
                    result = {"error": f"Agent {task.agent_type} has no execute method"}
            
            # Plugin handling is already done above in the routing logic
            # No additional plugin handling needed here
                
            # Send progress update - 75%
            if self.websocket_manager:
                await self.websocket_manager.broadcast_message(WebSocketMessage(
                    message_type=MessageType.TASK_UPDATE,
                    data={
                        "type": "task_progress",
                        "task_id": task.id,
                        "progress": 75,
                        "message": "Processing results..."
                    },
                    timestamp=datetime.now()
                ))

            # Task completed successfully
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.result = result
            
            # Update statistics
            duration = (datetime.now() - start_time).total_seconds()
            self._update_agent_stats(task.agent_type, duration, True)
            
            # Move to completed
            del self.running_tasks[task.id]
            self.completed_tasks.append(task)
            
            self.coordination_stats["tasks_executed"] += 1
            
            # Persist task results to memory systems
            await self._persist_task_results(task)
            
            # Send progress update - 100%
            if self.websocket_manager:
                await self.websocket_manager.broadcast_message(WebSocketMessage(
                    message_type=MessageType.TASK_UPDATE,
                    data={
                        "type": "task_completed",
                        "task_id": task.id,
                        "name": task.name,
                        "agent_type": task.agent_type,
                        "duration": duration
                    },
                    timestamp=datetime.now()
                ))
            
            self.logger.info(f"✅ Task {task.id} completed successfully")
            
            return {
                "task_id": task.id,
                "status": "completed",
                "result": result,
                "duration": duration
            }
            
        except asyncio.TimeoutError:
            error_msg = f"Task {task.id} timed out"
            task.status = TaskStatus.FAILED
            task.error = error_msg
            self._handle_task_failure(task)
            return {"error": error_msg}
            
        except Exception as e:
            error_msg = f"Task {task.id} failed: {str(e)}"
            task.status = TaskStatus.FAILED
            task.error = error_msg
            self._handle_task_failure(task)
            
            duration = (datetime.now() - start_time).total_seconds()
            self._update_agent_stats(task.agent_type, duration, False)
            
            return {"error": error_msg}
    
    def _check_dependencies(self, task: Task) -> bool:
        """Check if task dependencies are satisfied"""
        if not task.dependencies:
            return True
        
        for dep_id in task.dependencies:
            # Check if dependency is completed
            dep_completed = any(
                t.id == dep_id and t.status == TaskStatus.COMPLETED 
                for t in self.completed_tasks
            )
            if not dep_completed:
                return False
        
        return True
    
    def _handle_task_failure(self, task: Task):
        """Handle task failure with retry logic"""
        # Move from running to failed/retry
        if task.id in self.running_tasks:
            del self.running_tasks[task.id]
        
        # Check retry logic
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.PENDING
            task.started_at = None
            task.error = None
            self._insert_task_by_priority(task)
            self.logger.info(f"🔄 Retrying task {task.id} (attempt {task.retry_count})")
        else:
            self.failed_tasks.append(task)
            self.coordination_stats["tasks_failed"] += 1
            self.logger.error(f"❌ Task {task.id} failed after {task.max_retries} retries")
    
    def _update_agent_stats(self, agent_type: str, duration: float, success: bool):
        """Update agent performance statistics"""
        stats = self.coordination_stats["agent_utilization"][agent_type]
        stats["tasks_assigned"] += 1
        
        if success:
            stats["tasks_completed"] += 1
            # Update running average
            current_avg = stats["average_execution_time"]
            completed = stats["tasks_completed"]
            stats["average_execution_time"] = ((current_avg * (completed - 1)) + duration) / completed
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Execute a complete workflow"""
        if workflow_id not in self.workflows:
            return {"error": f"Workflow {workflow_id} not found"}
        
        workflow = self.workflows[workflow_id]
        workflow.status = TaskStatus.RUNNING
        self.active_workflows[workflow_id] = workflow
        
        self.logger.info(f"🚀 Starting workflow {workflow_id}: {workflow.name}")
        
        try:
            # Add all workflow tasks to pending queue
            for task in workflow.tasks:
                self._insert_task_by_priority(task)
            
            # Execute tasks respecting dependencies
            results = {}
            while any(t.status in [TaskStatus.PENDING, TaskStatus.RUNNING] for t in workflow.tasks):
                # Find ready tasks (no unmet dependencies)
                ready_tasks = [
                    t for t in workflow.tasks 
                    if t.status == TaskStatus.PENDING and self._check_dependencies(t)
                ]
                
                if not ready_tasks:
                    # Check if we're deadlocked
                    pending_tasks = [t for t in workflow.tasks if t.status == TaskStatus.PENDING]
                    if pending_tasks:
                        error_msg = f"Workflow {workflow_id} deadlocked - unmet dependencies"
                        workflow.status = TaskStatus.FAILED
                        return {"error": error_msg}
                    break
                
                # Execute ready tasks concurrently (up to max_concurrent_tasks)
                batch_size = min(len(ready_tasks), self.max_concurrent_tasks)
                batch_tasks = ready_tasks[:batch_size]
                
                # Execute batch concurrently
                batch_results = await asyncio.gather(
                    *[self._execute_single_task(task) for task in batch_tasks],
                    return_exceptions=True
                )
                
                # Process results
                for task, result in zip(batch_tasks, batch_results):
                    results[task.id] = result
                
                await asyncio.sleep(0.1)  # Small delay between batches
            
            # Check workflow completion
            if all(t.status == TaskStatus.COMPLETED for t in workflow.tasks):
                workflow.status = TaskStatus.COMPLETED
                self.coordination_stats["workflows_completed"] += 1
                self.logger.info(f"✅ Workflow {workflow_id} completed successfully")
            else:
                workflow.status = TaskStatus.FAILED
                self.logger.error(f"❌ Workflow {workflow_id} failed")
            
            return {
                "workflow_id": workflow_id,
                "status": workflow.status.value,
                "task_results": results,
                "total_tasks": len(workflow.tasks),
                "completed_tasks": sum(1 for t in workflow.tasks if t.status == TaskStatus.COMPLETED)
            }
            
        except Exception as e:
            workflow.status = TaskStatus.FAILED
            error_msg = f"Workflow {workflow_id} execution failed: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
        
        finally:
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
    
    async def create_and_submit_task(
        self, 
        name: str, 
        description: str, 
        agent_type: str, 
        priority: str = "medium", 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a task with parameters and submit it to the coordinator"""
        try:
            # Map priority string to enum
            priority_map = {
                "low": TaskPriority.LOW,
                "medium": TaskPriority.MEDIUM, 
                "high": TaskPriority.HIGH,
                "critical": TaskPriority.CRITICAL
            }
            
            task_priority = priority_map.get(priority.lower(), TaskPriority.MEDIUM)
            
            # Create task
            task = Task(
                id=str(uuid.uuid4()),
                name=name,
                agent_type=agent_type,
                parameters={
                    "description": description,
                    "metadata": metadata or {}
                },
                priority=task_priority
            )
            
            # Submit task
            success = await self.submit_task(task)
            
            if success:
                return {
                    "success": True,
                    "task_id": task.id,
                    "name": task.name,
                    "agent_type": task.agent_type,
                    "priority": task.priority.name,
                    "status": task.status.value
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to submit task"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def submit_task(self, task: Task) -> bool:
        """Submit a task to the coordinator"""
        try:
            # Add to pending queue (sorted by priority)
            self._insert_task_by_priority(task)
            
            self.logger.info(f"📋 Submitted task {task.id}: {task.name} for {task.agent_type}")
            
            # Broadcast task creation via WebSocket
            if self.websocket_manager:
                await self.websocket_manager.broadcast_message(WebSocketMessage(
                    message_type=MessageType.TASK_UPDATE,
                    data={
                        "type": "task_created",
                        "task_id": task.id,
                        "name": task.name,
                        "agent_type": task.agent_type,
                        "priority": task.priority.name,
                        "status": task.status.value
                    },
                    timestamp=datetime.now()
                ))
            
            # Auto-start executor if not running
            if not self.executor_running:
                await self.start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to submit task {task.id}: {e}")
            return False
    
    async def get_all_tasks(self) -> List[Task]:
        """Get all tasks from all queues"""
        all_tasks = []
        
        # Add pending tasks
        all_tasks.extend(list(self.pending_tasks))
        
        # Add running tasks
        all_tasks.extend(list(self.running_tasks.values()))
        
        # Add completed tasks
        all_tasks.extend(list(self.completed_tasks))
        
        # Add failed tasks
        all_tasks.extend(list(self.failed_tasks))
        
        # Add paused tasks
        all_tasks.extend(list(self.paused_tasks.values()))
        
        return all_tasks
    
    async def get_recent_tasks(self, limit: int = 20) -> List[Task]:
        """Get recent tasks ordered by creation date"""
        all_tasks = await self.get_all_tasks()
        
        # Sort by created_at timestamp (most recent first)
        all_tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return all_tasks[:limit]
    
    async def start(self):
        """Start the task executor"""
        if self.executor_running:
            self.logger.info("Executor already running")
            return
        
        self.executor_running = True
        self.executor_task = asyncio.create_task(self._task_executor())
        self.logger.info("🚀 AgentCoordinator executor started")
    
    async def stop(self):
        """Stop the task executor"""
        self.executor_running = False
        if self.executor_task:
            self.executor_task.cancel()
            try:
                await self.executor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("🛑 AgentCoordinator executor stopped")
    
    async def _task_executor(self):
        """Main task execution loop"""
        while self.executor_running:
            try:
                # Execute pending tasks up to max_concurrent_tasks
                if len(self.running_tasks) < self.max_concurrent_tasks and self.pending_tasks:
                    task = self.pending_tasks.popleft()
                    
                    # Execute task in background
                    asyncio.create_task(self._execute_single_task(task))
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                self.logger.error(f"Error in task executor: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    def get_coordination_stats(self) -> Dict[str, Any]:
        """Get coordination system statistics"""
        return {
            "coordination_stats": self.coordination_stats,
            "queue_status": {
                "pending_tasks": len(self.pending_tasks),
                "running_tasks": len(self.running_tasks),
                "completed_tasks": len(self.completed_tasks),
                "failed_tasks": len(self.failed_tasks)
            },
            "workflow_status": {
                "total_workflows": len(self.workflows),
                "active_workflows": len(self.active_workflows)
            },
            "registered_agents": list(self.registered_agents.keys()),
            "system_status": {
                "executor_running": self.executor_running,
                "max_concurrent_tasks": self.max_concurrent_tasks
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        # Check running tasks
        if task_id in self.running_tasks:
            return asdict(self.running_tasks[task_id])
        
        # Check completed tasks
        for task in self.completed_tasks:
            if task.id == task_id:
                return asdict(task)
        
        # Check failed tasks
        for task in self.failed_tasks:
            if task.id == task_id:
                return asdict(task)
        
        # Check pending tasks
        for task in self.pending_tasks:
            if task.id == task_id:
                return asdict(task)
        
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task"""
        # Check pending tasks
        temp_queue = deque()
        found = False
        
        while self.pending_tasks:
            task = self.pending_tasks.popleft()
            if task.id == task_id:
                task.status = TaskStatus.CANCELLED
                found = True
                self.logger.info(f"🚫 Cancelled pending task {task_id}")
            else:
                temp_queue.append(task)
        
        self.pending_tasks = temp_queue
        
        # For running tasks, mark as cancelled (actual cancellation depends on agent implementation)
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.status = TaskStatus.CANCELLED
            found = True
            self.logger.info(f"🚫 Marked running task {task_id} as cancelled")
        
        return found
    
    def get_task_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get task execution history"""
        history = []
        
        # Add completed tasks
        for task in list(self.completed_tasks)[-limit//2:]:
            history.append({
                "id": task.id,
                "name": task.name,
                "type": task.parameters.get("type", "unknown"),
                "description": task.parameters.get("description", task.name),
                "status": "completed",
                "priority": task.priority.name.lower(),
                "agent": task.agent_type,
                "created": task.created_at,
                "completed": task.completed_at,
                "duration": self._calculate_duration(task.started_at, task.completed_at) if task.started_at and task.completed_at else None,
                "result": task.result
            })
        
        # Add failed tasks
        for task in list(self.failed_tasks)[-limit//4:]:
            history.append({
                "id": task.id,
                "name": task.name,
                "type": task.parameters.get("type", "unknown"),
                "description": task.parameters.get("description", task.name),
                "status": "failed",
                "priority": task.priority.name.lower(),
                "agent": task.agent_type,
                "created": task.created_at,
                "error": task.error
            })
        
        # Add running tasks
        for task in self.running_tasks.values():
            history.append({
                "id": task.id,
                "name": task.name,
                "type": task.parameters.get("type", "unknown"),
                "description": task.parameters.get("description", task.name),
                "status": "running",
                "priority": task.priority.name.lower(),
                "agent": task.agent_type,
                "created": task.created_at,
                "started": task.started_at,
                "progress": 50  # Mock progress for UI
            })
        
        # Add pending tasks
        for task in list(self.pending_tasks)[:limit//4]:
            history.append({
                "id": task.id,
                "name": task.name,
                "type": task.parameters.get("type", "unknown"),
                "description": task.parameters.get("description", task.name),
                "status": "pending",
                "priority": task.priority.name.lower(),
                "agent": task.agent_type,
                "created": task.created_at
            })
        
        # Sort by creation time (newest first)
        history.sort(key=lambda x: x["created"], reverse=True)
        return history[:limit]
    
    def _calculate_duration(self, start_time: str, end_time: str) -> float:
        """Calculate duration between two ISO timestamps"""
        try:
            start = datetime.fromisoformat(start_time)
            end = datetime.fromisoformat(end_time)
            return (end - start).total_seconds()
        except:
            return 0.0
    
    def pause_task(self, task_id: str) -> bool:
        """Pause a running task"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.status = TaskStatus.PENDING  # Will be moved to paused_tasks
            self.paused_tasks[task_id] = self.running_tasks.pop(task_id)
            self.coordination_stats["tasks_paused"] += 1
            self.logger.info(f"⏸️ Paused task {task_id}")
            return True
        return False
    
    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task"""
        if task_id in self.paused_tasks:
            task = self.paused_tasks.pop(task_id)
            task.status = TaskStatus.PENDING
            self._insert_task_by_priority(task)
            self.logger.info(f"▶️ Resumed task {task_id}")
            return True
        return False
    
    def log_inter_agent_communication(self, from_agent: str, to_agent: str, message_type: str, data: Dict = None):
        """Log communication between agents"""
        communication_log = {
            "timestamp": datetime.now().isoformat(),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_type": message_type,
            "data": data or {},
            "id": str(uuid.uuid4())[:8]
        }
        
        self.agent_communication_log.append(communication_log)
        self.coordination_stats["inter_agent_communications"] += 1
        self.logger.debug(f"📡 Agent communication: {from_agent} -> {to_agent} ({message_type})")
    
    def check_agent_health(self, agent_type: str) -> Dict[str, Any]:
        """Check health status of a specific agent"""
        if agent_type not in self.registered_agents:
            return {"status": "not_registered", "health": "unknown"}
        
        agent = self.registered_agents[agent_type]
        health_status = {
            "status": "healthy",
            "last_checked": datetime.now().isoformat(),
            "response_time": None,
            "error_count": 0
        }
        
        try:
            # Simple health check - try to get agent status
            start_time = datetime.now()
            if hasattr(agent, 'get_status'):
                agent_status = agent.get_status()
                response_time = (datetime.now() - start_time).total_seconds()
                health_status.update({
                    "response_time": response_time,
                    "agent_data": agent_status
                })
            else:
                health_status["status"] = "limited"
                health_status["note"] = "Agent does not support health checks"
                
        except Exception as e:
            health_status.update({
                "status": "unhealthy",
                "error": str(e),
                "error_count": 1
            })
            
        self.agent_health[agent_type] = health_status
        return health_status
    
    def get_system_efficiency(self) -> float:
        """Calculate overall system efficiency"""
        total_tasks = self.coordination_stats["tasks_executed"] + self.coordination_stats["tasks_failed"]
        if total_tasks == 0:
            return 0.0
            
        success_rate = self.coordination_stats["tasks_executed"] / total_tasks
        
        # Factor in agent utilization
        avg_utilization = 0.0
        active_agents = len(self.agent_capabilities)
        
        if active_agents > 0:
            for agent_type, stats in self.coordination_stats["agent_utilization"].items():
                if stats["tasks_assigned"] > 0:
                    agent_success_rate = stats["tasks_completed"] / stats["tasks_assigned"]
                    avg_utilization += agent_success_rate
            avg_utilization /= active_agents
        
        # Combine success rate and utilization (weighted average)
        efficiency = (success_rate * 0.7) + (avg_utilization * 0.3)
        self.coordination_stats["system_efficiency"] = round(efficiency * 100, 2)
        
        return efficiency
    
    def get_load_balancing_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for load balancing between agents"""
        recommendations = {
            "timestamp": datetime.now().isoformat(),
            "agent_loads": {},
            "recommendations": [],
            "bottlenecks": []
        }
        
        # Analyze agent loads
        for agent_type, stats in self.coordination_stats["agent_utilization"].items():
            load_factor = 0.0
            if stats["tasks_assigned"] > 0:
                load_factor = stats["tasks_assigned"] - stats["tasks_completed"]
                
            recommendations["agent_loads"][agent_type] = {
                "load_factor": load_factor,
                "avg_execution_time": stats["average_execution_time"],
                "success_rate": stats["tasks_completed"] / max(stats["tasks_assigned"], 1)
            }
            
            # Identify bottlenecks
            if stats["average_execution_time"] > 30:  # Tasks taking more than 30 seconds
                recommendations["bottlenecks"].append({
                    "agent": agent_type,
                    "issue": "slow_execution",
                    "avg_time": stats["average_execution_time"]
                })
        
        return recommendations
    
    def create_workflow_template(self, template_name: str, workflow_definition: Dict) -> str:
        """Create a reusable workflow template"""
        template_id = str(uuid.uuid4())[:8]
        self.workflow_templates[template_id] = {
            "name": template_name,
            "definition": workflow_definition,
            "created_at": datetime.now().isoformat(),
            "usage_count": 0
        }
        
        self.logger.info(f"📋 Created workflow template: {template_name}")
        return template_id
    
    def create_workflow_from_template(self, template_id: str, parameters: Dict = None) -> str:
        """Create a workflow instance from a template"""
        if template_id not in self.workflow_templates:
            raise ValueError(f"Template {template_id} not found")
            
        template = self.workflow_templates[template_id]
        template["usage_count"] += 1
        
        # Process template with parameters
        workflow_def = template["definition"].copy()
        if parameters:
            # Simple parameter substitution (can be enhanced)
            workflow_def.update(parameters)
            
        return self.create_workflow(
            name=f"{template['name']} Instance",
            description=f"Created from template {template_id}",
            task_definitions=workflow_def.get("tasks", [])
        )
    
    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        return {
            "coordination_stats": self.coordination_stats,
            "queue_metrics": {
                "pending_tasks": len(self.pending_tasks),
                "running_tasks": len(self.running_tasks),
                "completed_tasks": len(self.completed_tasks),
                "failed_tasks": len(self.failed_tasks),
                "paused_tasks": len(self.paused_tasks)
            },
            "agent_health": self.agent_health,
            "communication_stats": {
                "total_communications": len(self.agent_communication_log),
                "recent_communications": list(self.agent_communication_log)[-10:]
            },
            "load_balancing": self.get_load_balancing_recommendations(),
            "system_efficiency": self.get_system_efficiency(),
            "workflow_stats": {
                "total_workflows": len(self.workflows),
                "active_workflows": len(self.active_workflows),
                "templates_available": len(self.workflow_templates)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _save_workflow_checkpoint(self, workflow_id: str):
        """Save workflow state to disk for recovery"""
        if workflow_id not in self.workflows:
            return
            
        try:
            workflow = self.workflows[workflow_id]
            checkpoint_data = {
                "workflow": asdict(workflow),
                "timestamp": datetime.now().isoformat(),
                "running_tasks": {tid: asdict(task) for tid, task in self.running_tasks.items()},
                "completed_task_ids": [t.id for t in self.completed_tasks],
                "failed_task_ids": [t.id for t in self.failed_tasks]
            }
            
            checkpoint_file = self.persistence_path / f"workflow_{workflow_id}_checkpoint.json"
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
                
            self.logger.info(f"💾 Saved checkpoint for workflow {workflow_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
    
    def _load_saved_workflows(self):
        """Load any saved workflows from disk"""
        try:
            if not self.persistence_path.exists():
                return
                
            for checkpoint_file in self.persistence_path.glob("workflow_*_checkpoint.json"):
                try:
                    with open(checkpoint_file, 'r') as f:
                        checkpoint_data = json.load(f)
                        
                    # Reconstruct workflow
                    workflow_data = checkpoint_data["workflow"]
                    workflow = AgentWorkflow(
                        id=workflow_data["id"],
                        name=workflow_data["name"],
                        description=workflow_data["description"],
                        tasks=[],
                        status=TaskStatus(workflow_data["status"]),
                        created_at=workflow_data["created_at"]
                    )
                    
                    # Reconstruct tasks
                    for task_data in workflow_data["tasks"]:
                        task = Task(
                            id=task_data["id"],
                            name=task_data["name"],
                            agent_type=task_data["agent_type"],
                            parameters=task_data["parameters"],
                            priority=TaskPriority(task_data["priority"]),
                            status=TaskStatus(task_data["status"]),
                            created_at=task_data["created_at"],
                            started_at=task_data.get("started_at"),
                            completed_at=task_data.get("completed_at"),
                            result=task_data.get("result"),
                            error=task_data.get("error"),
                            dependencies=task_data.get("dependencies", []),
                            max_retries=task_data.get("max_retries", 3),
                            retry_count=task_data.get("retry_count", 0),
                            timeout_seconds=task_data.get("timeout_seconds", 300)
                        )
                        workflow.tasks.append(task)
                    
                    self.workflows[workflow.id] = workflow
                    self.logger.info(f"📂 Loaded saved workflow: {workflow.name}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to load checkpoint file {checkpoint_file}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to load saved workflows: {e}")
    

    def recover_workflow(self, workflow_id: str) -> bool:
        """Recover a workflow from its last checkpoint"""
        checkpoint_file = self.persistence_path / f"workflow_{workflow_id}_checkpoint.json"
        
        if not checkpoint_file.exists():
            self.logger.error(f"No checkpoint found for workflow {workflow_id}")
            return False
            
        try:
            # Load the checkpoint
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
                
            # Reconstruct workflow state
            workflow = self.workflows.get(workflow_id)
            if not workflow:
                self.logger.error(f"Workflow {workflow_id} not found in registry")
                return False
                
            # Update task statuses based on checkpoint
            for task in workflow.tasks:
                if task.id in checkpoint_data["completed_task_ids"]:
                    task.status = TaskStatus.COMPLETED
                elif task.id in checkpoint_data["failed_task_ids"]:
                    task.status = TaskStatus.FAILED
                    # Persist failed task for fine-tuning
                    # await self._persist_failed_task(task.id, task)
                else:
                    task.status = TaskStatus.PENDING
                    
            # Resume workflow execution
            workflow.status = TaskStatus.RUNNING
            self.active_workflows[workflow_id] = workflow
            
            self.logger.info(f"🔄 Recovered workflow {workflow_id} from checkpoint")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to recover workflow: {e}")
            return False
    
    def validate_workflow_integrity(self, workflow_id: str) -> Dict[str, Any]:
        """Validate workflow for dependency cycles and other issues"""
        if workflow_id not in self.workflows:
            return {"valid": False, "error": "Workflow not found"}
            
        workflow = self.workflows[workflow_id]
        issues = []
        
        # Check for dependency cycles
        task_map = {task.id: task for task in workflow.tasks}
        
        def has_cycle(task_id: str, visited: Set[str], path: Set[str]) -> bool:
            if task_id in path:
                return True
            if task_id in visited:
                return False
                
            visited.add(task_id)
            path.add(task_id)
            
            task = task_map.get(task_id)
            if task and task.dependencies:
                for dep_id in task.dependencies:
                    if dep_id in task_map and has_cycle(dep_id, visited, path):
                        return True
                        
            path.remove(task_id)
            return False
            
        # Check each task for cycles
        visited = set()
        for task in workflow.tasks:
            if task.id not in visited:
                if has_cycle(task.id, visited, set()):
                    issues.append(f"Dependency cycle detected involving task {task.id}")
                    
        # Check for missing dependencies
        all_task_ids = {task.id for task in workflow.tasks}
        for task in workflow.tasks:
            for dep_id in task.dependencies:
                if dep_id not in all_task_ids:
                    issues.append(f"Task {task.id} has missing dependency: {dep_id}")
                    
        # Check for unreachable tasks (tasks that nothing depends on and have dependencies)
        dependent_tasks = set()
        for task in workflow.tasks:
            dependent_tasks.update(task.dependencies)
            
        for task in workflow.tasks:
            if task.dependencies and task.id not in dependent_tasks:
                # Check if this is a root task (no dependencies) or terminal task
                has_dependents = any(task.id in t.dependencies for t in workflow.tasks)
                if not has_dependents and task.dependencies:
                    issues.append(f"Task {task.id} may be unreachable")
                    
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "task_count": len(workflow.tasks),
            "dependency_count": sum(len(t.dependencies) for t in workflow.tasks)
        }
    
    async def _initialize_database(self):
        """Initialize PostgreSQL connection pool for fine-tuning data collection"""
        try:
            import asyncpg
            self.db_pool = await asyncpg.create_pool(**self.db_config)
            self.logger.info("✅ Database connection pool initialized for fine-tuning data collection")
        except ImportError:
            self.logger.warning("asyncpg not available, fine-tuning data collection disabled")
        except Exception as e:
            self.logger.error(f"Failed to initialize database connection: {e}")
    
    async def _persist_failed_task_for_training(self, task: Task, error_msg: str = None, guardian_feedback: str = None):
        """Persist failed task data to fine-tuning dataset"""
        if not self.db_pool:
            return
            
        try:
            async with self.db_pool.acquire() as conn:
                # Extract relevant information from task
                prompt = str(task.parameters.get('prompt', task.name))
                failed_output = str(task.result) if task.result else str(task.error)
                model_key = task.parameters.get('model_key', 'unknown')
                task_type = self._classify_task_type(task)
                
                await conn.execute(
                    """
                    INSERT INTO fine_tuning_dataset (
                        task_id, project_id, prompt, failed_output, 
                        failure_reason, guardian_feedback, error_details, 
                        model_key, task_type
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    task.id,
                    task.parameters.get('project_id', 'default'),
                    prompt,
                    failed_output,
                    'guardian_rejected' if guardian_feedback else 'error',
                    guardian_feedback,
                    error_msg,
                    model_key,
                    task_type
                )
                
            self.logger.info(f"📝 Persisted failed task {task.id} to fine-tuning dataset")
        except Exception as e:
            self.logger.error(f"Failed to persist failed task {task.id}: {e}")
    
    def _classify_task_type(self, task: Task) -> str:
        """Classify task type for fine-tuning categorization"""
        task_name = task.name.lower()
        agent_type = task.agent_type.lower()
        
        if 'code' in task_name or 'execution' in agent_type:
            return 'coding'
        elif 'research' in agent_type or 'research' in task_name:
            return 'research'
        elif 'analysis' in task_name or 'analyze' in task_name:
            return 'reasoning'
        elif 'creative' in task_name or 'generate' in task_name:
            return 'creative'
        else:
            return 'general'
    
    async def collect_guardian_feedback(self, task_id: str, output: str, guardian_feedback: str, approved: bool = False) -> bool:
        """Collect GuardianAgent feedback for fine-tuning"""
        if not self.db_pool:
            return False
            
        try:
            # Find the task
            task = None
            for t in list(self.completed_tasks) + list(self.failed_tasks):
                if t.id == task_id:
                    task = t
                    break
            
            if not task:
                self.logger.warning(f"Task {task_id} not found for guardian feedback collection")
                return False
            
            # If not approved, add to fine-tuning dataset
            if not approved:
                await self._persist_failed_task_for_training(task, guardian_feedback=guardian_feedback)
            
            # Update performance metrics if we have database connection
            if self.db_pool:
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE model_performance_metrics 
                        SET guardian_approved = $1 
                        WHERE task_id = $2
                        """,
                        approved,
                        task_id
                    )
            
            self.logger.info(f"🛡️ Guardian feedback collected for task {task_id}: approved={approved}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to collect guardian feedback for task {task_id}: {e}")
            return False
    
    async def get_fine_tuning_statistics(self) -> Dict[str, Any]:
        """Get statistics about fine-tuning dataset"""
        if not self.db_pool:
            return {"error": "Database not available"}
            
        try:
            async with self.db_pool.acquire() as conn:
                # Get general statistics
                stats = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(*) as total_samples,
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN status = 'labeled' THEN 1 ELSE 0 END) as labeled,
                        SUM(CASE WHEN status = 'trained' THEN 1 ELSE 0 END) as trained,
                        SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
                    FROM fine_tuning_dataset
                    """
                )
                
                # Get breakdown by task type and failure reason
                breakdown = await conn.fetch(
                    """
                    SELECT 
                        task_type,
                        failure_reason,
                        COUNT(*) as count
                    FROM fine_tuning_dataset
                    GROUP BY task_type, failure_reason
                    ORDER BY count DESC
                    """
                )
                
                return {
                    "summary": dict(stats),
                    "breakdown": [dict(row) for row in breakdown],
                    "ready_for_training": stats['labeled'],
                    "collection_active": True,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get fine-tuning statistics: {e}")
            return {"error": str(e)}
    
    async def close_database_connection(self):
        """Close database connection pool"""
        if self.db_pool:
            await self.db_pool.close()
            self.logger.info("Database connection pool closed")

# Global coordinator instance
agent_coordinator = AgentCoordinator()
