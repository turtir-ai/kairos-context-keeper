"""
Real-time API endpoints for live system state and monitoring
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from datetime import datetime
import asyncio
import json
import logging
from typing import Dict, List, Any, Optional

# Import components with support for both module and direct execution
try:
    from ..orchestration.agent_coordinator import agent_coordinator
    from ..memory.memory_manager import MemoryManager
    from .websocket_manager import websocket_manager
    from .auth import verify_api_key, check_rate_limit
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from orchestration.agent_coordinator import agent_coordinator
    from memory.memory_manager import MemoryManager
    from api.websocket_manager import websocket_manager
    from api.auth import verify_api_key, check_rate_limit

router = APIRouter(prefix="/api/live", tags=["live"])
logger = logging.getLogger(__name__)

# Memory manager instance
memory_manager = None

def get_memory_manager():
    """Get or create memory manager instance"""
    global memory_manager
    if memory_manager is None:
        memory_manager = MemoryManager()
    return memory_manager

@router.get("/agents/status")
async def get_live_agent_status():
    """Get real-time agent status"""
    try:
        agents_status = {}
        
        for agent_type, agent in agent_coordinator.registered_agents.items():
            # Get agent health
            health = agent_coordinator.check_agent_health(agent_type)
            
            # Get agent status
            if hasattr(agent, 'get_status'):
                status = agent.get_status()
            else:
                status = {"status": "unknown"}
                
            agents_status[agent_type] = {
                "health": health,
                "status": status,
                "metrics": agent_coordinator.coordination_stats["agent_utilization"].get(agent_type, {})
            }
            
        return {
            "timestamp": datetime.now().isoformat(),
            "agents": agents_status,
            "total_agents": len(agents_status),
            "healthy_agents": sum(1 for a in agents_status.values() if a["health"]["status"] == "healthy")
        }
        
    except Exception as e:
        logger.error(f"Failed to get agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflows/active")
async def get_active_workflows():
    """Get currently active workflows"""
    try:
        active_workflows = []
        
        for workflow_id, workflow in agent_coordinator.active_workflows.items():
            workflow_data = {
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "status": workflow.status.value,
                "created_at": workflow.created_at,
                "total_tasks": len(workflow.tasks),
                "completed_tasks": sum(1 for t in workflow.tasks if t.status.value == "completed"),
                "failed_tasks": sum(1 for t in workflow.tasks if t.status.value == "failed"),
                "running_tasks": sum(1 for t in workflow.tasks if t.status.value == "running"),
                "progress": (sum(1 for t in workflow.tasks if t.status.value == "completed") / len(workflow.tasks) * 100) if workflow.tasks else 0
            }
            active_workflows.append(workflow_data)
            
        return {
            "timestamp": datetime.now().isoformat(),
            "active_workflows": active_workflows,
            "total_workflows": len(agent_coordinator.workflows),
            "active_count": len(active_workflows)
        }
        
    except Exception as e:
        logger.error(f"Failed to get active workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/metrics")
async def get_system_metrics():
    """Get comprehensive system metrics"""
    try:
        # Get coordinator metrics
        coord_metrics = agent_coordinator.get_detailed_metrics()
        
        # Get memory metrics
        mem_manager = get_memory_manager()
        memory_metrics = mem_manager.get_memory_stats()
        
        # Get WebSocket metrics
        ws_metrics = {
            "total_connections": len(websocket_manager.active_connections),
            "subscriptions": {topic: len(subs) for topic, subs in websocket_manager.subscriptions.items()}
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "coordination": coord_metrics,
            "memory": memory_metrics,
            "websocket": ws_metrics,
            "system_health": {
                "status": "healthy" if coord_metrics["system_efficiency"] > 0.7 else "degraded",
                "efficiency": coord_metrics["system_efficiency"],
                "bottlenecks": coord_metrics["load_balancing"]["bottlenecks"]
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory/graph/stats")
async def get_graph_stats():
    """Get knowledge graph statistics"""
    try:
        mem_manager = get_memory_manager()
        graph_stats = mem_manager.knowledge_graph.get_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "graph": graph_stats,
            "storage_type": mem_manager.semantic_storage
        }
        
    except Exception as e:
        logger.error(f"Failed to get graph stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/queue")
async def get_task_queue():
    """Get current task queue status"""
    try:
        # Get pending tasks
        pending_tasks = []
        for task in agent_coordinator.pending_tasks:
            pending_tasks.append({
                "id": task.id,
                "name": task.name,
                "agent_type": task.agent_type,
                "priority": task.priority.name,
                "created_at": task.created_at,
                "dependencies": task.dependencies
            })
            
        # Get running tasks
        running_tasks = []
        for task_id, task in agent_coordinator.running_tasks.items():
            running_tasks.append({
                "id": task.id,
                "name": task.name,
                "agent_type": task.agent_type,
                "priority": task.priority.name,
                "started_at": task.started_at,
                "progress": 50  # Mock progress
            })
            
        return {
            "timestamp": datetime.now().isoformat(),
            "pending": pending_tasks,
            "running": running_tasks,
            "paused": list(agent_coordinator.paused_tasks.keys()),
            "stats": {
                "pending_count": len(pending_tasks),
                "running_count": len(running_tasks),
                "paused_count": len(agent_coordinator.paused_tasks),
                "max_concurrent": agent_coordinator.max_concurrent_tasks
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get task queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/{task_id}/pause")
async def pause_task(task_id: str):
    """Pause a running task"""
    try:
        success = agent_coordinator.pause_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found or not running")
            
        # Broadcast task pause
        await websocket_manager.broadcast({
            "type": "task_paused",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        })
        
        return {"status": "paused", "task_id": task_id}
        
    except Exception as e:
        logger.error(f"Failed to pause task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/{task_id}/resume")
async def resume_task(task_id: str):
    """Resume a paused task"""
    try:
        success = agent_coordinator.resume_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found or not paused")
            
        # Broadcast task resume
        await websocket_manager.broadcast({
            "type": "task_resumed",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        })
        
        return {"status": "resumed", "task_id": task_id}
        
    except Exception as e:
        logger.error(f"Failed to resume task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workflows/{workflow_id}/checkpoint")
async def create_workflow_checkpoint(workflow_id: str):
    """Create a checkpoint for a workflow"""
    try:
        agent_coordinator._save_workflow_checkpoint(workflow_id)
        
        return {
            "status": "checkpoint_created",
            "workflow_id": workflow_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to create checkpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workflows/{workflow_id}/recover")
async def recover_workflow(workflow_id: str):
    """Recover a workflow from checkpoint"""
    try:
        success = agent_coordinator.recover_workflow(workflow_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"No checkpoint found for workflow {workflow_id}")
            
        return {
            "status": "recovered",
            "workflow_id": workflow_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to recover workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflows/{workflow_id}/validate")
async def validate_workflow(workflow_id: str):
    """Validate workflow integrity"""
    try:
        validation_result = agent_coordinator.validate_workflow_integrity(workflow_id)
        return validation_result
        
    except Exception as e:
        logger.error(f"Failed to validate workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates
@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time system updates"""
    await websocket_manager.connect(websocket)
    
    try:
        # Send initial system state
        initial_state = {
            "type": "system_state",
            "data": {
                "agents": await get_live_agent_status(),
                "workflows": await get_active_workflows(),
                "tasks": await get_task_queue()
            },
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send_json(initial_state)
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for client messages
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                
                # Handle subscription requests
                if data.get("action") == "subscribe":
                    topics = data.get("topics", [])
                    for topic in topics:
                        websocket_manager.subscribe(websocket, topic)
                        
                elif data.get("action") == "unsubscribe":
                    topics = data.get("topics", [])
                    for topic in topics:
                        websocket_manager.unsubscribe(websocket, topic)
                        
                # Send acknowledgment
                await websocket.send_json({
                    "type": "ack",
                    "action": data.get("action"),
                    "timestamp": datetime.now().isoformat()
                })
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({
                    "type": "ping",
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)

# Background task to broadcast system updates
async def broadcast_system_updates():
    """Periodically broadcast system updates to all connected clients"""
    while True:
        try:
            # Get current metrics
            metrics = await get_system_metrics()
            
            # Broadcast to subscribers
            await websocket_manager.broadcast_to_topic("system_updates", {
                "type": "metrics_update",
                "data": metrics,
                "timestamp": datetime.now().isoformat()
            })
            
            # Wait before next update
            await asyncio.sleep(5)  # Update every 5 seconds
            
        except Exception as e:
            logger.error(f"Failed to broadcast system updates: {e}")
            await asyncio.sleep(10)  # Wait longer on error

# Background tasks will be started by the application lifespan
