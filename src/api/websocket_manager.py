"""
WebSocket Manager for Kairos Real-Time Communication

This module handles WebSocket connections, message routing, and real-time data streaming
for the Kairos system. It provides a centralized way to manage multiple client connections
and broadcast system updates.
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, Optional, Any, Callable
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import uuid
from enum import Enum

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types"""
    AGENT_STATUS = "agent_status"
    WORKFLOW_UPDATE = "workflow_update" 
    SYSTEM_METRICS = "system_metrics"
    CONVERSATION_STREAM = "conversation_stream"
    MEMORY_UPDATE = "memory_update"
    MEMORY_STATS = "memory_stats"
    MEMORY_NODES = "memory_nodes"
    GRAPH_UPDATE = "graph_update"
    ERROR_ALERT = "error_alert"
    USER_ACTION = "user_action"
    HEARTBEAT = "heartbeat"
    SUBSCRIPTION = "subscription"
    # Task related types
    TASK_UPDATE = "task_update"
    AGENT_TASK_STARTED = "agent_task_started"
    AGENT_TASK_COMPLETED = "agent_task_completed"
    AGENT_TASK_FAILED = "agent_task_failed"
    AGENT_PERFORMANCE = "agent_performance"
    # Additional types from frontend that were causing errors
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    # MCP context updates
    MCP_CONTEXT_UPDATE = "mcp_context_update"


class WebSocketMessage(BaseModel):
    """Standard WebSocket message format"""
    message_type: MessageType
    data: Any
    timestamp: datetime
    client_id: Optional[str] = None
    session_id: Optional[str] = None


class ClientSubscription(BaseModel):
    """Client subscription preferences"""
    client_id: str
    subscriptions: Set[MessageType]
    filters: Dict[str, Any] = {}
    created_at: datetime


class WebSocketManager:
    """Manages WebSocket connections and message distribution"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_subscriptions: Dict[str, ClientSubscription] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.message_queue: Dict[str, List[WebSocketMessage]] = {}
        self.heartbeat_interval: int = 30  # seconds
        self.max_queue_size: int = 1000
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        
        # Start background tasks
        self._heartbeat_task = None
        self._cleanup_task = None
        
    async def connect(self, websocket: WebSocket, client_id: str = None) -> str:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        if not client_id:
            client_id = str(uuid.uuid4())
            
        self.active_connections[client_id] = websocket
        self.client_subscriptions[client_id] = ClientSubscription(
            client_id=client_id,
            subscriptions=set(),
            created_at=datetime.now()
        )
        self.connection_metadata[client_id] = {
            "connected_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "message_count": 0
        }
        self.message_queue[client_id] = []
        
        logger.info(f"WebSocket client {client_id} connected")
        
        # Send welcome message
        await self.send_personal_message(
            client_id,
            WebSocketMessage(
                message_type=MessageType.HEARTBEAT,
                data={"status": "connected", "client_id": client_id},
                timestamp=datetime.now()
            )
        )
        
        # Start heartbeat if this is the first connection
        if len(self.active_connections) == 1:
            await self._start_background_tasks()
            
        return client_id
        
    async def disconnect(self, client_id: str):
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.client_subscriptions[client_id]
            del self.connection_metadata[client_id]
            del self.message_queue[client_id]
            
            logger.info(f"WebSocket client {client_id} disconnected")
            
        # Stop background tasks if no connections
        if len(self.active_connections) == 0:
            await self._stop_background_tasks()
            
    async def subscribe(self, client_id: str, message_types: List[MessageType], filters: Dict[str, Any] = None):
        """Subscribe client to specific message types"""
        if client_id in self.client_subscriptions:
            subscription = self.client_subscriptions[client_id]
            subscription.subscriptions.update(message_types)
            if filters:
                subscription.filters.update(filters)
                
            logger.info(f"Client {client_id} subscribed to {message_types}")
            
    async def unsubscribe(self, client_id: str, message_types: List[MessageType]):
        """Unsubscribe client from specific message types"""
        if client_id in self.client_subscriptions:
            subscription = self.client_subscriptions[client_id]
            subscription.subscriptions.difference_update(message_types)
            
            logger.info(f"Client {client_id} unsubscribed from {message_types}")
            
    async def send_personal_message(self, client_id: str, message: WebSocketMessage):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                message_dict = {
                    "message_type": message.message_type,
                    "data": message.data,
                    "timestamp": message.timestamp.isoformat(),
                    "client_id": message.client_id
                }
                await websocket.send_text(json.dumps(message_dict))
                
                # Update metadata
                self.connection_metadata[client_id]["message_count"] += 1
                
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {e}")
                await self.disconnect(client_id)
                
    async def broadcast_message(self, message: WebSocketMessage, exclude_client: str = None):
        """Broadcast message to all subscribed clients"""
        message_type = message.message_type
        
        for client_id, subscription in self.client_subscriptions.items():
            if exclude_client and client_id == exclude_client:
                continue
                
            if message_type in subscription.subscriptions:
                # Apply filters if any
                if subscription.filters and not self._passes_filters(message, subscription.filters):
                    continue
                    
                await self.send_personal_message(client_id, message)
                
    async def queue_message(self, client_id: str, message: WebSocketMessage):
        """Queue message for offline client"""
        if client_id in self.message_queue:
            queue = self.message_queue[client_id]
            
            # Prevent queue overflow
            if len(queue) >= self.max_queue_size:
                queue.pop(0)  # Remove oldest message
                
            queue.append(message)
            
    async def send_queued_messages(self, client_id: str):
        """Send all queued messages to reconnected client"""
        if client_id in self.message_queue:
            queue = self.message_queue[client_id]
            
            for message in queue:
                await self.send_personal_message(client_id, message)
                
            queue.clear()
            
    def register_message_handler(self, message_type: MessageType, handler: Callable):
        """Register handler for specific message type"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
            
        self.message_handlers[message_type].append(handler)
        
    async def handle_client_message(self, client_id: str, message_data: dict):
        """Handle incoming message from client"""
        try:
            message_type_str = message_data.get("message_type")
            if not message_type_str:
                logger.warning(f"Received message without message_type from client {client_id}")
                await self.send_error_message(client_id, "Message type is required")
                return
                
            try:
                message_type = MessageType(message_type_str)
            except ValueError:
                # Handle invalid message types gracefully
                logger.warning(f"Invalid message type '{message_type_str}' from client {client_id}")
                # Try to parse as TASK_UPDATE if it looks like a task message
                if message_type_str in ['task_started', 'task_progress', 'task_completed', 'task_failed']:
                    message_type = MessageType.TASK_UPDATE
                    data = {
                        "type": message_type_str,
                        **message_data.get("data", {})
                    }
                else:
                    await self.send_error_message(client_id, f"Invalid message type: {message_type_str}")
                    return
            else:
                data = message_data.get("data", {})
            
            message = WebSocketMessage(
                message_type=message_type,
                data=data,
                timestamp=datetime.now(),
                client_id=client_id
            )
            
            # Execute registered handlers
            if message_type in self.message_handlers:
                for handler in self.message_handlers[message_type]:
                    try:
                        await handler(client_id, message)
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")
                        
            # Handle built-in message types
            if message_type == MessageType.SUBSCRIPTION:
                await self._handle_subscription_message(client_id, data)
            elif message_type == MessageType.HEARTBEAT:
                await self._handle_heartbeat_message(client_id, data)
                
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
            await self.send_error_message(client_id, f"Invalid message format: {e}")
            
    async def send_error_message(self, client_id: str, error: str):
        """Send error message to client"""
        message = WebSocketMessage(
            message_type=MessageType.ERROR_ALERT,
            data={"error": error, "severity": "warning"},
            timestamp=datetime.now()
        )
        await self.send_personal_message(client_id, message)
        
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        total_messages = sum(
            metadata["message_count"] 
            for metadata in self.connection_metadata.values()
        )
        
        return {
            "active_connections": len(self.active_connections),
            "total_messages_sent": total_messages,
            "message_queue_sizes": {
                client_id: len(queue) 
                for client_id, queue in self.message_queue.items()
            },
            "subscription_counts": {
                client_id: len(sub.subscriptions)
                for client_id, sub in self.client_subscriptions.items()
            }
        }
        
    async def _handle_subscription_message(self, client_id: str, data: dict):
        """Handle subscription management message"""
        action = data.get("action")
        message_types = [MessageType(mt) for mt in data.get("message_types", [])]
        filters = data.get("filters", {})
        
        if action == "subscribe":
            await self.subscribe(client_id, message_types, filters)
        elif action == "unsubscribe":
            await self.unsubscribe(client_id, message_types)
            
    async def _handle_heartbeat_message(self, client_id: str, data: dict):
        """Handle heartbeat message"""
        if client_id in self.connection_metadata:
            self.connection_metadata[client_id]["last_heartbeat"] = datetime.now()
            
    def _passes_filters(self, message: WebSocketMessage, filters: Dict[str, Any]) -> bool:
        """Check if message passes client filters"""
        # Implement filter logic based on message data
        for key, value in filters.items():
            if hasattr(message.data, key):
                if getattr(message.data, key) != value:
                    return False
            elif isinstance(message.data, dict):
                if message.data.get(key) != value:
                    return False
                    
        return True
        
    async def _start_background_tasks(self):
        """Start background maintenance tasks"""
        if not self._heartbeat_task:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
    async def _stop_background_tasks(self):
        """Stop background maintenance tasks"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
            
    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                heartbeat_message = WebSocketMessage(
                    message_type=MessageType.HEARTBEAT,
                    data={"timestamp": datetime.now().isoformat()},
                    timestamp=datetime.now()
                )
                
                await self.broadcast_message(heartbeat_message)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                
    async def _cleanup_loop(self):
        """Clean up stale connections and old messages"""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                
                current_time = datetime.now()
                stale_clients = []
                
                # Find stale connections
                for client_id, metadata in self.connection_metadata.items():
                    last_heartbeat = metadata["last_heartbeat"]
                    if (current_time - last_heartbeat).seconds > self.heartbeat_interval * 3:
                        stale_clients.append(client_id)
                        
                # Remove stale connections
                for client_id in stale_clients:
                    logger.warning(f"Removing stale connection: {client_id}")
                    await self.disconnect(client_id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")


    async def start_background_tasks(self):
        """Public method to start background tasks"""
        await self._start_background_tasks()
        
    async def stop_background_tasks(self):
        """Public method to stop background tasks"""
        await self._stop_background_tasks()


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
