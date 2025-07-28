"""
Tests for Agent Coordinator functionality
"""

import pytest
import asyncio
from datetime import datetime
from orchestration.agent_coordinator import (
    AgentCoordinator, 
    Task, 
    TaskStatus, 
    TaskPriority,
    AgentWorkflow
)


class MockAgent:
    """Mock agent for testing"""
    
    def __init__(self, name):
        self.name = name
        self.tasks_executed = []
    
    async def execute(self, params):
        """Mock execute method"""
        self.tasks_executed.append(params)
        return {"status": "success", "result": f"Executed by {self.name}"}
    
    def get_status(self):
        """Mock status method"""
        return {
            "status": "active",
            "tasks_executed": len(self.tasks_executed)
        }


class TestAgentCoordinator:
    """Test AgentCoordinator functionality"""
    
    @pytest.fixture
    def coordinator(self):
        """Create a fresh coordinator instance"""
        return AgentCoordinator()
    
    @pytest.fixture
    def mock_agents(self, coordinator):
        """Register mock agents"""
        agents = {
            "TestAgent": MockAgent("TestAgent"),
            "ResearchAgent": MockAgent("ResearchAgent"),
            "ExecutionAgent": MockAgent("ExecutionAgent")
        }
        
        for agent_type, agent in agents.items():
            coordinator.register_agent(agent_type, agent, ["test", "execute"])
        
        return agents
    
    def test_register_agent(self, coordinator):
        """Test agent registration"""
        agent = MockAgent("TestAgent")
        coordinator.register_agent("TestAgent", agent, ["test"])
        
        assert "TestAgent" in coordinator.registered_agents
        assert coordinator.get_agent("TestAgent") == agent
        assert "TestAgent" in coordinator.agent_capabilities
        assert coordinator.agent_capabilities["TestAgent"] == ["test"]
    
    def test_create_task(self, coordinator):
        """Test task creation"""
        task_id = coordinator.create_task(
            name="Test Task",
            agent_type="TestAgent",
            parameters={"test": "data"},
            priority=TaskPriority.HIGH
        )
        
        assert task_id is not None
        assert len(coordinator.pending_tasks) == 1
        
        # Check task properties
        task = coordinator.pending_tasks[0]
        assert task.name == "Test Task"
        assert task.agent_type == "TestAgent"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
    
    def test_task_priority_ordering(self, coordinator):
        """Test that tasks are ordered by priority"""
        # Create tasks with different priorities
        low_task = coordinator.create_task("Low", "TestAgent", {}, TaskPriority.LOW)
        high_task = coordinator.create_task("High", "TestAgent", {}, TaskPriority.HIGH)
        medium_task = coordinator.create_task("Medium", "TestAgent", {}, TaskPriority.MEDIUM)
        critical_task = coordinator.create_task("Critical", "TestAgent", {}, TaskPriority.CRITICAL)
        
        # Check order in pending queue
        priorities = [task.priority for task in coordinator.pending_tasks]
        assert priorities[0] == TaskPriority.CRITICAL
        assert priorities[1] == TaskPriority.HIGH
        assert priorities[2] == TaskPriority.MEDIUM
        assert priorities[3] == TaskPriority.LOW
    
    @pytest.mark.asyncio
    async def test_execute_task(self, coordinator, mock_agents):
        """Test task execution"""
        task_id = coordinator.create_task(
            name="Test Execution",
            agent_type="TestAgent",
            parameters={"action": "test"}
        )
        
        result = await coordinator.execute_task(task_id)
        
        assert result["status"] == "completed"
        assert "result" in result
        assert len(coordinator.completed_tasks) == 1
        assert len(coordinator.pending_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_task_with_dependencies(self, coordinator, mock_agents):
        """Test task execution with dependencies"""
        # Create first task
        task1_id = coordinator.create_task(
            name="Task 1",
            agent_type="TestAgent",
            parameters={"step": 1}
        )
        
        # Create second task that depends on first
        task2_id = coordinator.create_task(
            name="Task 2",
            agent_type="TestAgent",
            parameters={"step": 2},
            dependencies=[task1_id]
        )
        
        # Second task should not execute until first is complete
        task2 = next(t for t in coordinator.pending_tasks if t.id == task2_id)
        assert not coordinator._check_dependencies(task2)
        
        # Execute first task
        await coordinator.execute_task(task1_id)
        
        # Now second task should be ready
        assert coordinator._check_dependencies(task2)
    
    def test_cancel_task(self, coordinator):
        """Test task cancellation"""
        task_id = coordinator.create_task(
            name="To Cancel",
            agent_type="TestAgent",
            parameters={}
        )
        
        # Cancel the task
        success = coordinator.cancel_task(task_id)
        assert success
        
        # Task should no longer be in pending
        assert len(coordinator.pending_tasks) == 0
    
    def test_pause_resume_task(self, coordinator, mock_agents):
        """Test task pause and resume"""
        task_id = coordinator.create_task(
            name="Pausable Task",
            agent_type="TestAgent",
            parameters={}
        )
        
        # Move task to running state first
        task = coordinator.pending_tasks[0]
        task.status = TaskStatus.RUNNING
        coordinator.running_tasks[task_id] = task
        coordinator.pending_tasks.popleft()
        
        # Pause the task
        success = coordinator.pause_task(task_id)
        assert success
        assert task_id in coordinator.paused_tasks
        assert task_id not in coordinator.running_tasks
        
        # Resume the task
        success = coordinator.resume_task(task_id)
        assert success
        assert task_id not in coordinator.paused_tasks
        assert len(coordinator.pending_tasks) == 1
    
    def test_create_workflow(self, coordinator):
        """Test workflow creation"""
        task_definitions = [
            {
                "name": "Step 1",
                "agent_type": "TestAgent",
                "parameters": {"step": 1},
                "priority": TaskPriority.HIGH.value
            },
            {
                "name": "Step 2",
                "agent_type": "TestAgent",
                "parameters": {"step": 2},
                "priority": TaskPriority.MEDIUM.value,
                "dependencies": []
            }
        ]
        
        workflow_id = coordinator.create_workflow(
            name="Test Workflow",
            description="A test workflow",
            task_definitions=task_definitions
        )
        
        assert workflow_id in coordinator.workflows
        workflow = coordinator.workflows[workflow_id]
        assert workflow.name == "Test Workflow"
        assert len(workflow.tasks) == 2
    
    def test_coordination_stats(self, coordinator, mock_agents):
        """Test coordination statistics tracking"""
        initial_stats = coordinator.get_coordination_stats()
        
        assert initial_stats["coordination_stats"]["tasks_executed"] == 0
        assert initial_stats["queue_status"]["pending_tasks"] == 0
        
        # Create and track some tasks
        task_id = coordinator.create_task(
            name="Stats Test",
            agent_type="TestAgent",
            parameters={}
        )
        
        updated_stats = coordinator.get_coordination_stats()
        assert updated_stats["queue_status"]["pending_tasks"] == 1
    
    def test_agent_health_check(self, coordinator, mock_agents):
        """Test agent health checking"""
        health = coordinator.check_agent_health("TestAgent")
        
        assert health["status"] in ["healthy", "limited"]
        assert "last_checked" in health
        assert health["error_count"] == 0
        
        # Check non-existent agent
        health = coordinator.check_agent_health("NonExistentAgent")
        assert health["status"] == "not_registered"
    
    def test_system_efficiency(self, coordinator):
        """Test system efficiency calculation"""
        efficiency = coordinator.get_system_efficiency()
        
        # With no tasks, efficiency should be 0
        assert efficiency == 0.0
        
        # Update stats to test calculation
        coordinator.coordination_stats["tasks_executed"] = 8
        coordinator.coordination_stats["tasks_failed"] = 2
        
        efficiency = coordinator.get_system_efficiency()
        assert 0 <= efficiency <= 1.0
    
    def test_task_history(self, coordinator, mock_agents):
        """Test task history retrieval"""
        # Create some tasks
        for i in range(5):
            coordinator.create_task(
                name=f"History Task {i}",
                agent_type="TestAgent",
                parameters={"index": i}
            )
        
        history = coordinator.get_task_history(limit=10)
        
        assert isinstance(history, list)
        assert len(history) <= 10
        
        # Check history structure
        if history:
            task_entry = history[0]
            assert "id" in task_entry
            assert "name" in task_entry
            assert "status" in task_entry
            assert "created" in task_entry
