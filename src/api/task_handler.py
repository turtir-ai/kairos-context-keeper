"""
Task Handler for Kairos WebSocket API

This module handles task-related WebSocket messages and integrates with the
orchestration system to manage task execution.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from orchestration.agent_coordinator import AgentCoordinator
from api.websocket_manager import WebSocketManager, WebSocketMessage, MessageType

logger = logging.getLogger(__name__)


class TaskHandler:
    """Handles task-related WebSocket messages and coordination"""
    
    def __init__(self, websocket_manager: WebSocketManager, agent_coordinator: AgentCoordinator):
        self.websocket_manager = websocket_manager
        self.agent_coordinator = agent_coordinator
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        
        # Register message handlers
        self._register_handlers()
        
        logger.info("📋 Task Handler initialized")
    
    def _register_handlers(self):
        """Register handlers for task-related messages"""
        # Task lifecycle messages
        self.websocket_manager.register_message_handler(
            MessageType.TASK_STARTED,
            self.handle_task_started
        )
        self.websocket_manager.register_message_handler(
            MessageType.TASK_PROGRESS,
            self.handle_task_progress
        )
        self.websocket_manager.register_message_handler(
            MessageType.TASK_COMPLETED,
            self.handle_task_completed
        )
        self.websocket_manager.register_message_handler(
            MessageType.TASK_FAILED,
            self.handle_task_failed
        )
        
        # Task management messages
        self.websocket_manager.register_message_handler(
            MessageType.TASK_UPDATE,
            self.handle_task_update
        )
    
    async def handle_task_started(self, client_id: str, message: WebSocketMessage):
        """Handle task started messages"""
        try:
            task_data = message.data
            task_id = task_data.get("task_id", str(uuid.uuid4()))
            
            # Store task info
            self.active_tasks[task_id] = {
                "task_id": task_id,
                "client_id": client_id,
                "started_at": datetime.now(),
                "status": "running",
                "data": task_data
            }
            
            # Notify other clients
            broadcast_message = WebSocketMessage(
                message_type=MessageType.TASK_UPDATE,
                data={
                    "task_id": task_id,
                    "status": "started",
                    "timestamp": datetime.now().isoformat(),
                    **task_data
                },
                timestamp=datetime.now()
            )
            
            await self.websocket_manager.broadcast_message(
                broadcast_message,
                exclude_client=client_id
            )
            
            # If task requires agent coordination
            if task_data.get("requires_agent"):
                await self._assign_task_to_agent(task_id, task_data)
            
            logger.info(f"Task {task_id} started by client {client_id}")
            
        except Exception as e:
            logger.error(f"Error handling task started: {e}")
            await self.websocket_manager.send_error_message(
                client_id,
                f"Failed to start task: {e}"
            )
    
    async def handle_task_progress(self, client_id: str, message: WebSocketMessage):
        """Handle task progress updates"""
        try:
            task_id = message.data.get("task_id")
            progress = message.data.get("progress", 0)
            status_message = message.data.get("message", "")
            
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["progress"] = progress
                self.active_tasks[task_id]["last_update"] = datetime.now()
                
                # Broadcast progress update
                broadcast_message = WebSocketMessage(
                    message_type=MessageType.TASK_UPDATE,
                    data={
                        "task_id": task_id,
                        "status": "progress",
                        "progress": progress,
                        "message": status_message,
                        "timestamp": datetime.now().isoformat()
                    },
                    timestamp=datetime.now()
                )
                
                await self.websocket_manager.broadcast_message(broadcast_message)
                
                logger.debug(f"Task {task_id} progress: {progress}%")
            
        except Exception as e:
            logger.error(f"Error handling task progress: {e}")
    
    async def handle_task_completed(self, client_id: str, message: WebSocketMessage):
        """Handle task completion"""
        try:
            task_id = message.data.get("task_id")
            result = message.data.get("result", {})
            
            if task_id in self.active_tasks:
                task_info = self.active_tasks[task_id]
                task_info["status"] = "completed"
                task_info["completed_at"] = datetime.now()
                task_info["result"] = result
                
                # Calculate duration
                duration = (task_info["completed_at"] - task_info["started_at"]).total_seconds()
                
                # Broadcast completion
                broadcast_message = WebSocketMessage(
                    message_type=MessageType.TASK_UPDATE,
                    data={
                        "task_id": task_id,
                        "status": "completed",
                        "result": result,
                        "duration": duration,
                        "timestamp": datetime.now().isoformat()
                    },
                    timestamp=datetime.now()
                )
                
                await self.websocket_manager.broadcast_message(broadcast_message)
                
                # Clean up after a delay
                asyncio.create_task(self._cleanup_task(task_id, delay=60))
                
                logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error handling task completion: {e}")
    
    async def handle_task_failed(self, client_id: str, message: WebSocketMessage):
        """Handle task failure"""
        try:
            task_id = message.data.get("task_id")
            error = message.data.get("error", "Unknown error")
            
            if task_id in self.active_tasks:
                task_info = self.active_tasks[task_id]
                task_info["status"] = "failed"
                task_info["failed_at"] = datetime.now()
                task_info["error"] = error
                
                # Broadcast failure
                broadcast_message = WebSocketMessage(
                    message_type=MessageType.TASK_UPDATE,
                    data={
                        "task_id": task_id,
                        "status": "failed",
                        "error": error,
                        "timestamp": datetime.now().isoformat()
                    },
                    timestamp=datetime.now()
                )
                
                await self.websocket_manager.broadcast_message(broadcast_message)
                
                # Clean up after a delay
                asyncio.create_task(self._cleanup_task(task_id, delay=60))
                
                logger.error(f"Task {task_id} failed: {error}")
            
        except Exception as e:
            logger.error(f"Error handling task failure: {e}")
    
    async def handle_task_update(self, client_id: str, message: WebSocketMessage):
        """Handle generic task updates"""
        try:
            update_type = message.data.get("type", "unknown")
            
            # Route to specific handlers based on update type
            if update_type == "task_started":
                message.data.pop("type", None)
                await self.handle_task_started(client_id, WebSocketMessage(
                    message_type=MessageType.TASK_STARTED,
                    data=message.data,
                    timestamp=message.timestamp,
                    client_id=message.client_id
                ))
            elif update_type == "task_progress":
                message.data.pop("type", None)
                await self.handle_task_progress(client_id, WebSocketMessage(
                    message_type=MessageType.TASK_PROGRESS,
                    data=message.data,
                    timestamp=message.timestamp,
                    client_id=message.client_id
                ))
            elif update_type == "task_completed":
                message.data.pop("type", None)
                await self.handle_task_completed(client_id, WebSocketMessage(
                    message_type=MessageType.TASK_COMPLETED,
                    data=message.data,
                    timestamp=message.timestamp,
                    client_id=message.client_id
                ))
            elif update_type == "task_failed":
                message.data.pop("type", None)
                await self.handle_task_failed(client_id, WebSocketMessage(
                    message_type=MessageType.TASK_FAILED,
                    data=message.data,
                    timestamp=message.timestamp,
                    client_id=message.client_id
                ))
            else:
                # Generic task update - just broadcast it
                await self.websocket_manager.broadcast_message(message)
        
        except Exception as e:
            logger.error(f"Error handling task update: {e}")
    
    async def _assign_task_to_agent(self, task_id: str, task_data: Dict[str, Any]):
        """Assign task to appropriate agent"""
        try:
            task_description = task_data.get("description", "")
            task_type = task_data.get("type", "general")
            
            # Create task for agent coordinator
            agent_task = {
                "task_id": task_id,
                "description": task_description,
                "type": task_type,
                "parameters": task_data.get("parameters", {}),
                "priority": task_data.get("priority", "normal")
            }
            
            # Execute through agent coordinator
            result = await self.agent_coordinator.execute_task(
                task_description,
                context=agent_task
            )
            
            # Update task with result
            if result.get("success"):
                await self.handle_task_completed("system", WebSocketMessage(
                    message_type=MessageType.TASK_COMPLETED,
                    data={
                        "task_id": task_id,
                        "result": result
                    },
                    timestamp=datetime.now()
                ))
            else:
                await self.handle_task_failed("system", WebSocketMessage(
                    message_type=MessageType.TASK_FAILED,
                    data={
                        "task_id": task_id,
                        "error": result.get("error", "Agent execution failed")
                    },
                    timestamp=datetime.now()
                ))
        
        except Exception as e:
            logger.error(f"Error assigning task to agent: {e}")
            await self.handle_task_failed("system", WebSocketMessage(
                message_type=MessageType.TASK_FAILED,
                data={
                    "task_id": task_id,
                    "error": f"Agent assignment failed: {e}"
                },
                timestamp=datetime.now()
            ))
    
    async def _cleanup_task(self, task_id: str, delay: int = 60):
        """Clean up completed/failed tasks after a delay"""
        await asyncio.sleep(delay)
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
            logger.debug(f"Cleaned up task {task_id}")
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get list of active tasks"""
        return [
            {
                **task_info,
                "duration": (datetime.now() - task_info["started_at"]).total_seconds()
                if task_info["status"] == "running" else None
            }
            for task_info in self.active_tasks.values()
        ]
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        return self.active_tasks.get(task_id)
