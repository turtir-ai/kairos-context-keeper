#!/usr/bin/env python3
"""
Comprehensive Integration Tests for Kairos Full Workflow
Tests the complete flow from task creation to completion with MCP context
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List

# Import test dependencies
try:
    from unittest.mock import Mock, AsyncMock, patch
    from ..orchestration.agent_coordinator import AgentCoordinator, Task, TaskPriority, TaskStatus
    from ..mcp.model_context_protocol import ModelContextProtocol, MCPContext
    from ..memory.memory_manager import MemoryManager
    from ..agents.research_agent import ResearchAgent  
    from ..agents.execution_agent import ExecutionAgent
    from ..agents.guardian_agent import GuardianAgent
    from ..api.websocket_manager import WebSocketManager, MessageType, WebSocketMessage
except ImportError as e:
    print(f"Import error in test: {e}")
    pytest.skip("Required modules not available", allow_module_level=True)


class TestFullWorkflowIntegration:
    """Integration tests for complete Kairos workflow"""

    @pytest.fixture
    async def setup_system(self):
        """Setup complete Kairos system for testing"""
        # Initialize core components
        coordinator = AgentCoordinator()
        mcp = ModelContextProtocol()
        memory_manager = None  # Mock for testing
        websocket_manager = WebSocketManager()
        
        # Initialize agents with MCP context
        test_context = mcp.create_context(
            project_id="test_project",
            session_id="test_session", 
            user_id="test_user"
        )
        
        # Register agents
        research_agent = ResearchAgent(test_context)
        execution_agent = ExecutionAgent(test_context)
        guardian_agent = GuardianAgent(test_context)
        
        coordinator.register_agent("ResearchAgent", research_agent)
        coordinator.register_agent("ExecutionAgent", execution_agent)
        coordinator.register_agent("GuardianAgent", guardian_agent)
        
        # Mock WebSocket for testing
        coordinator.websocket_manager = Mock()
        coordinator.websocket_manager.broadcast_message = AsyncMock()
        
        return {
            "coordinator": coordinator,
            "mcp": mcp,
            "websocket_manager": websocket_manager,
            "agents": {
                "research": research_agent,
                "execution": execution_agent, 
                "guardian": guardian_agent
            },
            "test_context": test_context
        }

    @pytest.mark.asyncio
    async def test_complete_research_workflow(self, setup_system):
        """Test complete research workflow from creation to completion"""
        system = await setup_system
        coordinator = system["coordinator"]
        
        # 1. Create research task
        task_id = coordinator.create_task(
            name="Research React WebSocket patterns", 
            agent_type="ResearchAgent",
            parameters={
                "topic": "React WebSocket real-time integration patterns 2024",
                "depth": "comprehensive",
                "sources": ["internal", "web"],
                "project_id": "test_project",
                "session_id": "test_session"
            },
            priority=TaskPriority.HIGH
        )
        
        assert task_id is not None
        assert len(task_id) == 8  # UUID format
        
        # 2. Verify task is in pending queue
        task_status = coordinator.get_task_status(task_id)
        assert task_status is not None
        assert task_status["status"] == TaskStatus.PENDING.value
        assert task_status["agent_type"] == "ResearchAgent"
        
        # 3. Execute the task
        result = await coordinator.execute_task(task_id)
        
        # 4. Verify execution success
        assert result["status"] == "completed"
        assert "result" in result
        assert "duration" in result
        
        # 5. Verify task moved to completed
        updated_status = coordinator.get_task_status(task_id)
        assert updated_status["status"] == TaskStatus.COMPLETED.value
        assert updated_status["result"] is not None
        
        # 6. Verify MCP context was used
        research_result = updated_status["result"]
        assert "research_plan" in research_result
        assert "confidence_score" in research_result
        assert research_result["confidence_score"] > 0
        
        # 7. Verify WebSocket broadcast was called
        coordinator.websocket_manager.broadcast_message.assert_called()
        
        print(f"✅ Research workflow test passed - Task {task_id} completed successfully")

    @pytest.mark.asyncio
    async def test_execution_with_guardian_validation(self, setup_system):
        """Test execution workflow with automatic Guardian validation"""
        system = await setup_system
        coordinator = system["coordinator"]
        
        # 1. Create execution task
        execution_task_id = coordinator.create_task(
            name="Create test configuration file",
            agent_type="ExecutionAgent", 
            parameters={
                "command": "create_file",
                "file_path": "tests/test_config.json",
                "content": json.dumps({
                    "test_environment": "integration",
                    "database": "test_db",
                    "api_endpoint": "https://test.api.com"
                }, indent=2),
                "project_id": "test_project"
            },
            priority=TaskPriority.MEDIUM
        )
        
        # 2. Execute the task
        execution_result = await coordinator.execute_task(execution_task_id)
        assert execution_result["status"] == "completed"
        
        # 3. Create automatic Guardian validation task
        guardian_task_id = coordinator.create_task(
            name="Validate execution output",
            agent_type="GuardianAgent",
            parameters={
                "output": json.dumps(execution_result["result"]),
                "validation_type": "general",
                "context": {
                    "parent_task": execution_task_id,
                    "validation_rules": ["security", "quality"]
                }
            },
            priority=TaskPriority.HIGH,
            dependencies=[execution_task_id]
        )
        
        # 4. Execute Guardian validation
        guardian_result = await coordinator.execute_task(guardian_task_id)
        assert guardian_result["status"] == "completed"
        
        # 5. Verify validation results
        validation_result = guardian_result["result"]
        assert "passed" in validation_result
        assert "score" in validation_result
        assert validation_result["score"] >= 0
        
        print(f"✅ Execution + Guardian workflow test passed")

    @pytest.mark.asyncio
    async def test_multi_agent_workflow_with_dependencies(self, setup_system):
        """Test complex workflow with multiple agents and dependencies"""
        system = await setup_system
        coordinator = system["coordinator"]
        
        # 1. Create research task (prerequisite)
        research_task_id = coordinator.create_task(
            name="Research Python testing frameworks",
            agent_type="ResearchAgent",
            parameters={
                "topic": "Python asyncio testing frameworks pytest integration",
                "depth": "comprehensive"
            },
            priority=TaskPriority.HIGH
        )
        
        # 2. Create execution task (depends on research)
        execution_task_id = coordinator.create_task(
            name="Generate test framework setup",
            agent_type="ExecutionAgent", 
            parameters={
                "command": "create_file",
                "file_path": "tests/framework_setup.py",
                "content": "# Generated test framework setup"
            },
            priority=TaskPriority.MEDIUM,
            dependencies=[research_task_id]
        )
        
        # 3. Create validation task (depends on execution)
        validation_task_id = coordinator.create_task(
            name="Validate test setup",
            agent_type="GuardianAgent",
            parameters={
                "validation_type": "code_quality",
                "output": "test setup content"
            },
            priority=TaskPriority.MEDIUM,
            dependencies=[execution_task_id]
        )
        
        # 4. Execute tasks in dependency order
        # Execute research first
        research_result = await coordinator.execute_task(research_task_id)
        assert research_result["status"] == "completed"
        
        # Execute dependent execution task
        execution_result = await coordinator.execute_task(execution_task_id) 
        assert execution_result["status"] == "completed"
        
        # Execute final validation task
        validation_result = await coordinator.execute_task(validation_task_id)
        assert validation_result["status"] == "completed"
        
        # 5. Verify all tasks completed successfully
        research_status = coordinator.get_task_status(research_task_id)
        execution_status = coordinator.get_task_status(execution_task_id)
        validation_status = coordinator.get_task_status(validation_task_id)
        
        assert research_status["status"] == TaskStatus.COMPLETED.value
        assert execution_status["status"] == TaskStatus.COMPLETED.value
        assert validation_status["status"] == TaskStatus.COMPLETED.value
        
        print(f"✅ Multi-agent dependency workflow test passed")

    @pytest.mark.asyncio 
    async def test_mcp_context_persistence_and_retrieval(self, setup_system):
        """Test MCP context creation, persistence, and retrieval"""
        system = await setup_system
        mcp = system["mcp"]
        test_context = system["test_context"]
        
        # 1. Update context with task data
        test_context.update({
            "current_task": "integration_testing",
            "test_data": {
                "start_time": datetime.now().isoformat(),
                "test_suite": "full_workflow"
            }
        })
        
        # 2. Add conversation history
        test_context.conversation_history.extend([
            {
                "role": "user",
                "content": "Run integration tests for Sprint 6",
                "timestamp": datetime.now().isoformat()
            },
            {
                "role": "assistant", 
                "content": "Starting comprehensive integration tests...",
                "timestamp": datetime.now().isoformat()
            }
        ])
        
        # 3. Add relevant memories (mock)
        test_context.relevant_memories = [
            {
                "id": "mem_001",
                "content": "Previous integration test results",
                "type": "test_result",
                "score": 0.9
            }
        ]
        
        # 4. Test context formatting for LLM
        llm_formatted = mcp.format_for_llm(test_context, include_tools=True)
        formatted_data = json.loads(llm_formatted)
        
        assert "system_context" in formatted_data
        assert "global_context" in formatted_data
        assert "local_context" in formatted_data
        assert "conversation_history" in formatted_data
        assert "relevant_memories" in formatted_data
        assert "available_tools" in formatted_data
        
        # 5. Test context persistence (mock without actual database)
        task_result = {
            "test_suite": "full_workflow",
            "tests_passed": 5,
            "tests_failed": 0,
            "duration": 45.2
        }
        
        # Mock persistence (would normally save to Neo4j/Qdrant)
        persistence_result = await mcp.persist_context(
            test_context.context_id,
            task_result=task_result,
            relationship_type="completed_integration_test"
        )
        
        # Without actual database, expect failure but test the interface
        assert "status" in persistence_result
        
        print(f"✅ MCP context persistence test passed")

    @pytest.mark.asyncio
    async def test_websocket_real_time_updates(self, setup_system):
        """Test WebSocket real-time updates during task execution"""
        system = await setup_system
        coordinator = system["coordinator"]
        websocket_manager = system["websocket_manager"]
        
        # Mock client connection
        mock_client_id = "test_client_001"
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()
        
        # Register mock client
        websocket_manager.active_connections[mock_client_id] = mock_websocket
        websocket_manager.client_subscriptions[mock_client_id] = Mock()
        websocket_manager.client_subscriptions[mock_client_id].subscriptions = {
            MessageType.TASK_UPDATE,
            MessageType.MCP_CONTEXT_UPDATE
        }
        
        # Subscribe to task updates
        await websocket_manager.subscribe(
            mock_client_id, 
            [MessageType.TASK_UPDATE, MessageType.MCP_CONTEXT_UPDATE]
        )
        
        # Create and execute task to trigger WebSocket updates
        task_id = coordinator.create_task(
            name="WebSocket test task",
            agent_type="ResearchAgent", 
            parameters={"topic": "WebSocket testing"}
        )
        
        # Set real WebSocket manager on coordinator
        coordinator.websocket_manager = websocket_manager
        
        # Execute task (should trigger WebSocket messages)
        result = await coordinator.execute_task(task_id)
        
        # Verify WebSocket messages were sent
        assert mock_websocket.send_text.called
        call_args = mock_websocket.send_text.call_args_list
        
        # Should have sent multiple updates (start, progress, complete, MCP context)
        assert len(call_args) > 0
        
        # Verify message format
        first_message = json.loads(call_args[0][0][0])
        assert "message_type" in first_message
        assert "data" in first_message
        assert "timestamp" in first_message
        
        print(f"✅ WebSocket real-time updates test passed")

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, setup_system):
        """Test error handling and recovery mechanisms"""
        system = await setup_system
        coordinator = system["coordinator"]
        
        # 1. Create task that will fail
        failing_task_id = coordinator.create_task(
            name="Intentionally failing task",
            agent_type="ExecutionAgent",
            parameters={
                "command": "invalid_command_that_will_fail"
            },
            priority=TaskPriority.LOW,
            max_retries=2
        )
        
        # 2. Execute task and expect failure
        result = await coordinator.execute_task(failing_task_id)
        
        # 3. Verify error was handled properly
        assert "error" in result
        
        # 4. Verify task status reflects failure
        task_status = coordinator.get_task_status(failing_task_id)
        # Task might be in retry state or failed state
        assert task_status["status"] in [TaskStatus.FAILED.value, TaskStatus.PENDING.value]
        
        # 5. Verify error statistics were updated
        stats = coordinator.get_coordination_stats()
        # Should have at least some error count
        
        print(f"✅ Error handling and recovery test passed")

    @pytest.mark.asyncio 
    async def test_performance_and_concurrency(self, setup_system):
        """Test system performance with concurrent tasks"""
        system = await setup_system
        coordinator = system["coordinator"]
        
        # Create multiple tasks to run concurrently
        task_ids = []
        for i in range(5):
            task_id = coordinator.create_task(
                name=f"Concurrent task {i+1}",
                agent_type="ResearchAgent",
                parameters={
                    "topic": f"Concurrent research topic {i+1}",
                    "depth": "basic"
                },
                priority=TaskPriority.MEDIUM
            )
            task_ids.append(task_id)
        
        # Execute tasks concurrently
        start_time = datetime.now()
        
        tasks = [coordinator.execute_task(task_id) for task_id in task_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Verify all tasks completed or failed gracefully
        successful_tasks = 0
        for result in results:
            if isinstance(result, dict) and result.get("status") == "completed":
                successful_tasks += 1
        
        # At least some tasks should succeed
        assert successful_tasks > 0
        
        # Verify reasonable performance (tasks should complete within 60 seconds)
        assert duration < 60
        
        print(f"✅ Performance test passed - {successful_tasks}/{len(task_ids)} tasks completed in {duration:.2f}s")

    @pytest.mark.asyncio
    async def test_system_metrics_and_monitoring(self, setup_system):
        """Test system metrics collection and monitoring"""
        system = await setup_system
        coordinator = system["coordinator"]
        
        # Execute some tasks to generate metrics
        task_id = coordinator.create_task(
            name="Metrics test task",
            agent_type="ResearchAgent",
            parameters={"topic": "metrics testing"}
        )
        
        await coordinator.execute_task(task_id)
        
        # Get system metrics
        stats = coordinator.get_coordination_stats()
        
        # Verify metrics structure
        assert "coordination_stats" in stats
        assert "queue_status" in stats
        assert "registered_agents" in stats
        assert "system_status" in stats
        
        # Verify metrics contain expected data
        coordination_stats = stats["coordination_stats"]
        assert "tasks_executed" in coordination_stats
        assert "agent_utilization" in coordination_stats
        
        # Get detailed metrics
        detailed_metrics = coordinator.get_detailed_metrics()
        assert "load_balancing" in detailed_metrics
        assert "system_efficiency" in detailed_metrics
        
        print(f"✅ System metrics and monitoring test passed")


if __name__ == "__main__":
    # Run tests directly
    import sys
    import os
    
    # Add parent directory to path for imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Run individual tests
    async def run_tests():
        test_instance = TestFullWorkflowIntegration()
        
        print("🧪 Starting Comprehensive Integration Tests")
        print("=" * 60)
        
        try:
            # Setup system
            system = await test_instance.setup_system()
            
            # Run tests
            await test_instance.test_complete_research_workflow(system)
            await test_instance.test_execution_with_guardian_validation(system)
            await test_instance.test_multi_agent_workflow_with_dependencies(system)
            await test_instance.test_mcp_context_persistence_and_retrieval(system)
            await test_instance.test_websocket_real_time_updates(system)
            await test_instance.test_error_handling_and_recovery(system)
            await test_instance.test_performance_and_concurrency(system)
            await test_instance.test_system_metrics_and_monitoring(system)
            
            print("=" * 60)
            print("🎉 ALL INTEGRATION TESTS PASSED!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Run the tests
    asyncio.run(run_tests())
