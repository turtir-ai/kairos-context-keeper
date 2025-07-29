"""
Phase 3: Complex Function Refactoring - Agent Coordinator Optimization
Breaking down large, complex functions into smaller, manageable, and efficient units.
"""

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
    from ..memory.memory_manager import MemoryManager
except ImportError:
    try:
        from memory.memory_manager import MemoryManager
    except ImportError:
        MemoryManager = None

# Task and workflow classes remain the same
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Task to dictionary with serializable enum values"""
        task_dict = asdict(self)
        task_dict['priority'] = self.priority.name.lower()
        task_dict['status'] = self.status.value
        return task_dict

class OptimizedAgentCoordinator:
    """Refactored Agent Coordinator with optimized, smaller functions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Core collections - organized by responsibility
        self._init_task_collections()
        self._init_workflow_collections() 
        self._init_agent_collections()
        self._init_performance_metrics()
        self._init_communication_system()
        
        self.logger.info("🎭 Optimized Agent Coordinator initialized with refactored architecture")
    
    def _init_task_collections(self):
        """Initialize task-related collections"""
        self.pending_tasks = deque()
        self.running_tasks = {}
        self.completed_tasks = deque(maxlen=1000)
        self.failed_tasks = deque(maxlen=100)
        self.paused_tasks = {}
        
    def _init_workflow_collections(self):
        """Initialize workflow-related collections"""
        self.workflows = {}
        self.active_workflows = {}
        self.workflow_templates = {}
        
        # Workflow persistence
        self.persistence_path = Path("data/workflows")
        self.persistence_path.mkdir(parents=True, exist_ok=True)
        self.checkpoint_interval = 60
    
    def _init_agent_collections(self):
        """Initialize agent registry and health tracking"""
        self.registered_agents = {}
        self.agent_capabilities = {}
        self.agent_health = {}
        self.agent_communication_log = deque(maxlen=500)
        
        # Execution control
        self.max_concurrent_tasks = 5
        self.executor_running = False
        self.executor_task = None
        self.auto_scaling_enabled = True
    
    def _init_performance_metrics(self):
        """Initialize performance tracking systems"""
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
    
    def _init_communication_system(self):
        """Initialize WebSocket communication and message batching"""
        self.websocket_manager = None
        
        # Optimized message batching system
        self.message_batch = []
        self.batch_size = 5  # Reduced for better responsiveness
        self.batch_interval = 0.05  # 50ms for faster updates
        self.batch_timer = None
        self.batching_enabled = True
        
        # Memory manager for context-aware operations
        self.memory_manager = None
        if MemoryManager:
            try:
                self.memory_manager = MemoryManager()
                self.logger.info("✅ Memory Manager initialized for context-aware operations")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Memory Manager: {e}")
    
    # === AGENT REGISTRATION (Optimized) ===
    
    def register_agent(self, agent_type: str, agent_instance, capabilities: List[str] = None):
        """Register an agent with optimized capability tracking"""
        self._validate_agent_registration(agent_type, agent_instance)
        
        # Register core agent info
        self.registered_agents[agent_type] = agent_instance
        self.agent_capabilities[agent_type] = capabilities or []
        
        # Initialize performance tracking
        self._init_agent_performance_tracking(agent_type)
        
        self.logger.info(f"📝 Registered agent: {agent_type} with {len(capabilities or [])} capabilities")
    
    def _validate_agent_registration(self, agent_type: str, agent_instance):
        """Validate agent registration parameters"""
        if not agent_type or not isinstance(agent_type, str):
            raise ValueError("Agent type must be a non-empty string")
        
        if agent_instance is None:
            raise ValueError("Agent instance cannot be None")
        
        if agent_type in self.registered_agents:
            self.logger.warning(f"Agent {agent_type} already registered, replacing...")
    
    def _init_agent_performance_tracking(self, agent_type: str):
        """Initialize performance tracking for a new agent"""
        self.coordination_stats["agent_utilization"][agent_type] = {
            "tasks_assigned": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_execution_time": 0.0,
            "success_rate": 0.0
        }
        
        self.agent_health[agent_type] = {
            "status": "healthy",
            "last_heartbeat": datetime.now().isoformat(),
            "response_time_ms": 0,
            "error_count": 0
        }
    
    # === TASK CREATION (Optimized) ===
    
    def create_task(self, name: str, agent_type: str, parameters: Dict[str, Any], 
                   priority: TaskPriority = TaskPriority.MEDIUM, 
                   dependencies: List[str] = None,
                   timeout_seconds: int = 300) -> str:
        """Create a new task with optimized validation and prioritization"""
        
        # Quick validation
        self._validate_task_creation(name, agent_type, parameters)
        
        # Generate optimized task ID
        task_id = self._generate_task_id()
        
        # Create task object
        task = self._build_task_object(task_id, name, agent_type, parameters, 
                                     priority, dependencies, timeout_seconds)
        
        # Add to priority queue with optimized insertion
        self._add_task_to_queue(task)
        
        # Log and return
        self.logger.info(f"📋 Created task {task_id}: {name} for {agent_type}")
        return task_id
    
    def _validate_task_creation(self, name: str, agent_type: str, parameters: Dict[str, Any]):
        """Fast validation for task creation parameters"""
        if not name or not isinstance(name, str):
            raise ValueError("Task name must be a non-empty string")
        
        if not agent_type or not isinstance(agent_type, str):
            raise ValueError("Agent type must be a non-empty string")
        
        if not isinstance(parameters, dict):
            raise ValueError("Parameters must be a dictionary")
    
    def _generate_task_id(self) -> str:
        """Generate optimized task ID"""
        return f"task_{int(datetime.now().timestamp() * 1000000)}"[-12:]  # Last 12 chars for uniqueness
    
    def _build_task_object(self, task_id: str, name: str, agent_type: str, 
                          parameters: Dict[str, Any], priority: TaskPriority,
                          dependencies: List[str], timeout_seconds: int) -> Task:
        """Build task object with optimized defaults"""
        return Task(
            id=task_id,
            name=name,
            agent_type=agent_type,
            parameters=parameters,
            priority=priority,
            dependencies=dependencies or [],
            timeout_seconds=timeout_seconds
        )
    
    def _add_task_to_queue(self, task: Task):
        """Add task to priority queue with optimized insertion"""
        # For small queues, simple append and sort is faster
        if len(self.pending_tasks) < 50:
            self.pending_tasks.append(task)
            # Sort by priority (higher priority first)
            self.pending_tasks = deque(sorted(self.pending_tasks, 
                                            key=lambda t: t.priority.value, reverse=True))
        else:
            # For larger queues, use optimized insertion
            self._insert_task_by_priority_optimized(task)
    
    def _insert_task_by_priority_optimized(self, task: Task):
        """Optimized priority insertion for large queues"""
        inserted = False
        temp_tasks = []
        
        # Extract tasks with lower priority
        while self.pending_tasks:
            current_task = self.pending_tasks.popleft()
            if not inserted and task.priority.value > current_task.priority.value:
                temp_tasks.append(task)
                inserted = True
            temp_tasks.append(current_task)
        
        # Add task at end if not inserted
        if not inserted:
            temp_tasks.append(task)
        
        # Rebuild queue
        self.pending_tasks = deque(temp_tasks)
    
    # === TASK EXECUTION (Optimized) ===
    
    async def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a single task with optimized lookup and execution"""
        task = self._find_and_remove_task(task_id)
        
        if not task:
            return self._create_error_response(f"Task {task_id} not found")
        
        return await self._execute_task_optimized(task)
    
    def _find_and_remove_task(self, task_id: str) -> Optional[Task]:
        """Optimized task lookup and removal from pending queue"""
        temp_tasks = []
        found_task = None
        
        # Search and collect
        while self.pending_tasks:
            current_task = self.pending_tasks.popleft()
            if current_task.id == task_id:
                found_task = current_task
            else:
                temp_tasks.append(current_task)
        
        # Restore queue without found task
        self.pending_tasks = deque(temp_tasks)
        return found_task
    
    async def _execute_task_optimized(self, task: Task) -> Dict[str, Any]:
        """Optimized task execution with better error handling"""
        # Fast agent validation
        if not self._validate_agent_available(task.agent_type):
            return await self._handle_agent_not_available(task)
        
        # Quick dependency check
        if not self._check_dependencies_fast(task):
            return await self._handle_dependencies_not_met(task)
        
        # Execute with timeout and error handling
        return await self._execute_with_timeout_and_retry(task)
    
    def _validate_agent_available(self, agent_type: str) -> bool:
        """Fast agent availability check"""
        return agent_type in self.registered_agents
    
    async def _handle_agent_not_available(self, task: Task) -> Dict[str, Any]:
        """Handle case where agent is not available"""
        error_msg = f"Agent type {task.agent_type} not registered"
        task.status = TaskStatus.FAILED
        task.error = error_msg
        self.failed_tasks.append(task)
        
        # Update stats
        self._update_failure_stats(task.agent_type)
        
        # Broadcast failure
        await self._broadcast_task_failure(task, error_msg)
        
        return self._create_error_response(error_msg)
    
    def _check_dependencies_fast(self, task: Task) -> bool:
        """Fast dependency validation"""
        if not task.dependencies:
            return True
        
        # Check if all dependencies are completed
        completed_task_ids = {t.id for t in self.completed_tasks}
        return all(dep_id in completed_task_ids for dep_id in task.dependencies)
    
    async def _handle_dependencies_not_met(self, task: Task) -> Dict[str, Any]:
        """Handle case where task dependencies are not met"""
        error_msg = f"Dependencies not met for task {task.id}"
        
        # Put back in pending queue for later
        self.pending_tasks.appendleft(task)
        
        return self._create_error_response(error_msg, "dependencies_not_met")
    
    async def _execute_with_timeout_and_retry(self, task: Task) -> Dict[str, Any]:
        """Execute task with timeout and retry logic"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        self.running_tasks[task.id] = task
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self._execute_agent_task(task),
                timeout=task.timeout_seconds
            )
            
            return await self._handle_task_success(task, result)
            
        except asyncio.TimeoutError:
            return await self._handle_task_timeout(task)
        except Exception as e:
            return await self._handle_task_exception(task, e)
        finally:
            # Remove from running tasks
            self.running_tasks.pop(task.id, None)
    
    async def _execute_agent_task(self, task: Task) -> Dict[str, Any]:
        """Execute the actual agent task"""
        agent = self.registered_agents[task.agent_type]
        
        # Update agent utilization stats
        self._update_agent_stats_start(task.agent_type)
        
        # Execute based on agent type
        if hasattr(agent, 'execute_async'):
            result = await agent.execute_async(task.parameters)
        elif hasattr(agent, 'execute'):
            # Run sync method in thread pool to avoid blocking
            result = await asyncio.get_event_loop().run_in_executor(
                None, agent.execute, task.parameters
            )
        else:
            raise ValueError(f"Agent {task.agent_type} has no execute method")
        
        return result
    
    async def _handle_task_success(self, task: Task, result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful task completion"""
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now().isoformat()
        task.result = result
        
        # Move to completed queue
        self.completed_tasks.append(task)
        
        # Update performance metrics
        self._update_success_stats(task)
        
        # Store in memory if available
        await self._store_task_result_in_memory(task)
        
        # Broadcast success
        await self._broadcast_task_success(task)
        
        return {"success": True, "result": result, "task_id": task.id}
    
    async def _handle_task_timeout(self, task: Task) -> Dict[str, Any]:
        """Handle task timeout with retry logic"""
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.PENDING
            
            # Add back to queue with delay
            await asyncio.sleep(1)  # 1 second delay before retry
            self.pending_tasks.appendleft(task)
            
            self.logger.warning(f"⏰ Task {task.id} timed out, retry {task.retry_count}/{task.max_retries}")
            return {"retry": True, "task_id": task.id, "retry_count": task.retry_count}
        else:
            # Max retries reached
            task.status = TaskStatus.FAILED
            task.error = "Task timed out after maximum retries"
            self.failed_tasks.append(task)
            
            self._update_failure_stats(task.agent_type)
            await self._broadcast_task_failure(task, "timeout")
            
            return self._create_error_response("Task timed out after maximum retries")
    
    async def _handle_task_exception(self, task: Task, exception: Exception) -> Dict[str, Any]:
        """Handle task execution exception"""
        error_msg = str(exception)
        task.status = TaskStatus.FAILED
        task.error = error_msg
        self.failed_tasks.append(task)
        
        # Update failure stats
        self._update_failure_stats(task.agent_type)
        
        # Log error
        self.logger.error(f"❌ Task {task.id} failed: {error_msg}")
        
        # Broadcast failure
        await self._broadcast_task_failure(task, error_msg)
        
        return self._create_error_response(error_msg)
    
    # === UTILITY METHODS (Optimized) ===
    
    def _create_error_response(self, error: str, error_type: str = "execution_error") -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "error": error,
            "error_type": error_type,
            "timestamp": datetime.now().isoformat()
        }
    
    def _update_agent_stats_start(self, agent_type: str):
        """Update agent statistics when task starts"""
        if agent_type in self.coordination_stats["agent_utilization"]:
            self.coordination_stats["agent_utilization"][agent_type]["tasks_assigned"] += 1
    
    def _update_success_stats(self, task: Task):
        """Update statistics for successful task completion"""
        agent_type = task.agent_type
        
        # Calculate execution time
        if task.started_at and task.completed_at:
            start_time = datetime.fromisoformat(task.started_at)
            end_time = datetime.fromisoformat(task.completed_at)
            execution_time = (end_time - start_time).total_seconds()
            
            # Update agent-specific stats
            if agent_type in self.coordination_stats["agent_utilization"]:
                stats = self.coordination_stats["agent_utilization"][agent_type]
                stats["tasks_completed"] += 1
                
                # Update average execution time
                total_tasks = stats["tasks_completed"]
                current_avg = stats["average_execution_time"]
                stats["average_execution_time"] = (
                    (current_avg * (total_tasks - 1) + execution_time) / total_tasks
                )
                
                # Update success rate
                success_rate = stats["tasks_completed"] / stats["tasks_assigned"]
                stats["success_rate"] = success_rate
        
        # Update global stats
        self.coordination_stats["tasks_executed"] += 1
    
    def _update_failure_stats(self, agent_type: str):
        """Update statistics for failed task"""
        if agent_type in self.coordination_stats["agent_utilization"]:
            self.coordination_stats["agent_utilization"][agent_type]["tasks_failed"] += 1
        
        self.coordination_stats["tasks_failed"] += 1
    
    async def _store_task_result_in_memory(self, task: Task):
        """Store task result in memory manager if available"""
        if self.memory_manager and task.result:
            try:
                # Store as context memory
                memory_id = self.memory_manager.add_context_memory(
                    f"Task {task.name} completed successfully",
                    "task_execution",
                    {
                        "task_id": task.id,
                        "agent_type": task.agent_type,
                        "result": task.result,
                        "execution_time": task.completed_at
                    }
                )
                
                if memory_id:
                    self.logger.debug(f"📚 Task {task.id} result stored in memory: {memory_id}")
            except Exception as e:
                self.logger.warning(f"Failed to store task result in memory: {e}")
    
    async def _broadcast_task_success(self, task: Task):
        """Broadcast task success via WebSocket"""
        if self.websocket_manager:
            await self.broadcast_task_update({
                "type": "task_completed",
                "task_id": task.id,
                "result": task.result,
                "execution_time": self._calculate_execution_time(task)
            })
    
    async def _broadcast_task_failure(self, task: Task, error: str):
        """Broadcast task failure via WebSocket"""
        if self.websocket_manager:
            await self.broadcast_task_update({
                "type": "task_failed", 
                "task_id": task.id,
                "error": error
            })
    
    def _calculate_execution_time(self, task: Task) -> float:
        """Calculate task execution time in seconds"""
        if task.started_at and task.completed_at:
            start_time = datetime.fromisoformat(task.started_at)
            end_time = datetime.fromisoformat(task.completed_at)
            return (end_time - start_time).total_seconds()
        return 0.0
    
    # === WEBSOCKET COMMUNICATION (Optimized) ===
    
    async def broadcast_task_update(self, message_data: Dict[str, Any]):
        """Optimized WebSocket message broadcasting with batching"""
        if not self.websocket_manager:
            return
        
        message = {
            **message_data,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.batching_enabled:
            await self._add_to_batch(message)
        else:
            await self._send_immediate(message)
    
    async def _add_to_batch(self, message: Dict[str, Any]):
        """Add message to batch for efficient sending"""
        self.message_batch.append(message)
        
        if len(self.message_batch) >= self.batch_size:
            await self._flush_batch()
        elif not self.batch_timer:
            # Start timer for batch flush
            self.batch_timer = asyncio.create_task(self._batch_timer_flush())
    
    async def _batch_timer_flush(self):
        """Timer-based batch flushing"""
        await asyncio.sleep(self.batch_interval)
        await self._flush_batch()
    
    async def _flush_batch(self):
        """Flush accumulated messages as a batch"""
        if not self.message_batch:
            return
        
        # Cancel existing timer
        if self.batch_timer and not self.batch_timer.done():
            self.batch_timer.cancel()
        self.batch_timer = None
        
        # Create batch message
        batch_message = {
            "type": "batch_task_update",
            "messages": self.message_batch.copy(),
            "batch_size": len(self.message_batch),
            "timestamp": datetime.now().isoformat()
        }
        
        # Clear batch
        self.message_batch.clear()
        
        # Send batch
        await self._send_immediate(batch_message)
    
    async def _send_immediate(self, message: Dict[str, Any]):
        """Send message immediately via WebSocket"""
        try:
            await self.websocket_manager.broadcast(json.dumps(message))
        except Exception as e:
            self.logger.error(f"Failed to broadcast message: {e}")
    
    # === PERFORMANCE MONITORING ===
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        total_tasks = (self.coordination_stats["tasks_executed"] + 
                      self.coordination_stats["tasks_failed"])
        
        success_rate = 0.0
        if total_tasks > 0:
            success_rate = (self.coordination_stats["tasks_executed"] / total_tasks) * 100
        
        return {
            "coordinator_stats": self.coordination_stats,
            "task_queues": {
                "pending": len(self.pending_tasks),
                "running": len(self.running_tasks),
                "completed": len(self.completed_tasks),
                "failed": len(self.failed_tasks)
            },
            "agent_health": self.agent_health,
            "success_rate_percent": round(success_rate, 2),
            "system_efficiency": self._calculate_system_efficiency(),
            "memory_usage": self._get_memory_usage_stats(),
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_system_efficiency(self) -> float:
        """Calculate overall system efficiency"""
        if not self.coordination_stats["agent_utilization"]:
            return 0.0
        
        # Average success rate across all agents
        total_success_rate = 0.0
        active_agents = 0
        
        for agent_stats in self.coordination_stats["agent_utilization"].values():
            if agent_stats["tasks_assigned"] > 0:
                total_success_rate += agent_stats.get("success_rate", 0.0)
                active_agents += 1
        
        return (total_success_rate / active_agents) * 100 if active_agents > 0 else 0.0
    
    def _get_memory_usage_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics if memory manager is available"""
        if self.memory_manager:
            try:
                return self.memory_manager.get_performance_stats()
            except Exception as e:
                self.logger.warning(f"Failed to get memory stats: {e}")
        
        return {"status": "memory_manager_not_available"}
    
    # === AGENT HEALTH MONITORING ===
    
    async def check_agent_health(self, agent_type: str) -> Dict[str, Any]:
        """Check health of a specific agent"""
        if agent_type not in self.registered_agents:
            return {"status": "not_registered", "agent_type": agent_type}
        
        agent = self.registered_agents[agent_type]
        
        try:
            # Simple health check - ping with timestamp
            start_time = datetime.now()
            
            if hasattr(agent, 'health_check'):
                health_result = await agent.health_check()
            else:
                # Basic health check - just verify agent is responsive
                health_result = {"status": "healthy", "basic_check": True}
            
            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update health tracking
            self.agent_health[agent_type] = {
                "status": health_result.get("status", "healthy"),
                "last_heartbeat": datetime.now().isoformat(),
                "response_time_ms": response_time,
                "error_count": 0,
                "details": health_result
            }
            
            return self.agent_health[agent_type]
            
        except Exception as e:
            # Update error count
            if agent_type in self.agent_health:
                self.agent_health[agent_type]["error_count"] += 1
                self.agent_health[agent_type]["status"] = "unhealthy"
            
            self.logger.error(f"Health check failed for {agent_type}: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "agent_type": agent_type,
                "timestamp": datetime.now().isoformat()
            }
    
    # === CLEANUP AND MAINTENANCE ===
    
    async def cleanup_completed_tasks(self, older_than_hours: int = 24):
        """Clean up old completed tasks to free memory"""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        initial_count = len(self.completed_tasks)
        
        # Filter out old tasks
        filtered_tasks = deque()
        for task in self.completed_tasks:
            if task.completed_at:
                completed_time = datetime.fromisoformat(task.completed_at)
                if completed_time > cutoff_time:
                    filtered_tasks.append(task)
        
        self.completed_tasks = filtered_tasks
        cleaned_count = initial_count - len(self.completed_tasks)
        
        if cleaned_count > 0:
            self.logger.info(f"🧹 Cleaned up {cleaned_count} old completed tasks")
        
        return {"cleaned_count": cleaned_count}
    
    def get_agent(self, agent_type: str):
        """Get a registered agent instance"""
        return self.registered_agents.get(agent_type)
    
    def get_registered_agents(self) -> List[str]:
        """Get list of all registered agent types"""
        return list(self.registered_agents.keys())
