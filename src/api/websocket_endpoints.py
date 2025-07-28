"""
WebSocket Endpoints for Kairos Real-Time API

This module defines the WebSocket endpoints and handlers that integrate with
the main FastAPI application to provide real-time communication capabilities.
"""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.routing import APIRouter

# Handle imports for both module and direct execution
try:
    from .websocket_manager import websocket_manager, MessageType, WebSocketMessage
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from api.websocket_manager import websocket_manager, MessageType, WebSocketMessage

logger = logging.getLogger(__name__)

# Create WebSocket router
websocket_router = APIRouter()


@websocket_router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """Main WebSocket endpoint for client connections"""
    try:
        # Accept connection
        actual_client_id = await websocket_manager.connect(websocket, client_id)
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Handle the message
                await websocket_manager.handle_client_message(actual_client_id, message_data)
                
        except WebSocketDisconnect:
            logger.info(f"Client {actual_client_id} disconnected normally")
            
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        
    finally:
        await websocket_manager.disconnect(actual_client_id)


@websocket_router.websocket("/ws")
async def websocket_endpoint_auto_id(websocket: WebSocket):
    """WebSocket endpoint with auto-generated client ID"""
    try:
        # Accept connection with auto-generated ID
        client_id = await websocket_manager.connect(websocket)
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Handle the message
                await websocket_manager.handle_client_message(client_id, message_data)
                
        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected normally")
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        
    finally:
        await websocket_manager.disconnect(client_id)


class WebSocketIntegration:
    """Integration class to connect WebSocket manager with system components"""
    
    def __init__(self):
        self.setup_message_handlers()
        
    def setup_message_handlers(self):
        """Register message handlers for system integration"""
        
        # Handle user actions (like starting workflows, querying agents, etc.)
        websocket_manager.register_message_handler(
            MessageType.USER_ACTION, 
            self.handle_user_action
        )
        
        # Handle subscription requests
        websocket_manager.register_message_handler(
            MessageType.SUBSCRIPTION,
            self.handle_subscription_request
        )
        
        # Handle memory-related requests
        websocket_manager.register_message_handler(
            MessageType.MEMORY_STATS,
            self.handle_memory_stats_request
        )
        
        websocket_manager.register_message_handler(
            MessageType.MEMORY_NODES,
            self.handle_memory_nodes_request
        )
        
    async def handle_user_action(self, client_id: str, message: WebSocketMessage):
        """Handle user action messages from WebSocket clients"""
        try:
            action_type = message.data.get("action_type")
            payload = message.data.get("payload", {})
            
            if action_type == "start_workflow":
                await self.handle_start_workflow(client_id, payload)
            elif action_type == "query_agent":
                await self.handle_query_agent(client_id, payload)
            elif action_type == "get_memory":
                await self.handle_get_memory(client_id, payload)
            elif action_type == "search_knowledge":
                await self.handle_search_knowledge(client_id, payload)
            else:
                await websocket_manager.send_error_message(
                    client_id, 
                    f"Unknown action type: {action_type}"
                )
                
        except Exception as e:
            logger.error(f"Error handling user action: {e}")
            await websocket_manager.send_error_message(client_id, f"Action failed: {e}")
            
    async def handle_subscription_request(self, client_id: str, message: WebSocketMessage):
        """Handle subscription management requests"""
        try:
            action = message.data.get("action")
            message_types_str = message.data.get("message_types", [])
            message_types = [MessageType(mt) for mt in message_types_str]
            filters = message.data.get("filters", {})
            
            if action == "subscribe":
                await websocket_manager.subscribe(client_id, message_types, filters)
                await websocket_manager.send_personal_message(
                    client_id,
                    WebSocketMessage(
                        message_type=MessageType.SUBSCRIPTION,
                        data={
                            "status": "subscribed",
                            "message_types": message_types_str,
                            "filters": filters
                        },
                        timestamp=datetime.now()
                    )
                )
            elif action == "unsubscribe":
                await websocket_manager.unsubscribe(client_id, message_types)
                await websocket_manager.send_personal_message(
                    client_id,
                    WebSocketMessage(
                        message_type=MessageType.SUBSCRIPTION,
                        data={
                            "status": "unsubscribed",
                            "message_types": message_types_str
                        },
                        timestamp=datetime.now()
                    )
                )
                
        except Exception as e:
            logger.error(f"Error handling subscription request: {e}")
            await websocket_manager.send_error_message(client_id, f"Subscription failed: {e}")
            
    async def handle_start_workflow(self, client_id: str, payload: Dict[str, Any]):
        """Handle workflow start requests"""
        # TODO: Integrate with workflow orchestrator
        workflow_id = payload.get("workflow_id")
        parameters = payload.get("parameters", {})
        
        logger.info(f"Starting workflow {workflow_id} for client {client_id}")
        
        # Send workflow update
        await websocket_manager.send_personal_message(
            client_id,
            WebSocketMessage(
                message_type=MessageType.WORKFLOW_UPDATE,
                data={
                    "workflow_id": workflow_id,
                    "status": "started",
                    "parameters": parameters,
                    "message": f"Workflow {workflow_id} has been started"
                },
                timestamp=datetime.now()
            )
        )
        
    async def handle_query_agent(self, client_id: str, payload: Dict[str, Any]):
        """Handle agent query requests"""
        # TODO: Integrate with agent coordinator
        agent_id = payload.get("agent_id")
        query = payload.get("query")
        
        logger.info(f"Querying agent {agent_id} for client {client_id}")
        
        # Send conversation stream update
        await websocket_manager.send_personal_message(
            client_id,
            WebSocketMessage(
                message_type=MessageType.CONVERSATION_STREAM,
                data={
                    "agent_id": agent_id,
                    "query": query,
                    "status": "processing",
                    "message": f"Agent {agent_id} is processing your query"
                },
                timestamp=datetime.now()
            )
        )
        
    async def handle_get_memory(self, client_id: str, payload: Dict[str, Any]):
        """Handle memory retrieval requests"""
        # TODO: Integrate with memory manager
        memory_type = payload.get("memory_type")
        query = payload.get("query")
        
        logger.info(f"Retrieving {memory_type} memory for client {client_id}")
        
        # Send memory update
        await websocket_manager.send_personal_message(
            client_id,
            WebSocketMessage(
                message_type=MessageType.MEMORY_UPDATE,
                data={
                    "memory_type": memory_type,
                    "query": query,
                    "status": "retrieved",
                    "message": f"Memory of type {memory_type} has been retrieved"
                },
                timestamp=datetime.now()
            )
        )
        
    async def handle_search_knowledge(self, client_id: str, payload: Dict[str, Any]):
        """Handle knowledge search requests"""
        # TODO: Integrate with Neo4j and Qdrant
        search_query = payload.get("query")
        search_type = payload.get("search_type", "semantic")
        
        logger.info(f"Searching knowledge for client {client_id}: {search_query}")
        
        # Send graph update
        await websocket_manager.send_personal_message(
            client_id,
            WebSocketMessage(
                message_type=MessageType.GRAPH_UPDATE,
                data={
                    "search_query": search_query,
                    "search_type": search_type,
                    "status": "completed",
                    "message": f"Knowledge search completed for: {search_query}"
                },
                timestamp=datetime.now()
            )
        )
        
    async def handle_memory_stats_request(self, client_id: str, message: WebSocketMessage):
        """Handle memory statistics requests"""
        try:
            from memory.memory_manager import MemoryManager
            
            # Get memory statistics
            memory_manager = MemoryManager()
            stats = {
                "semantic_memory": {
                    "total_nodes": 0,
                    "total_relationships": 0,
                    "status": "connected"
                },
                "episodic_memory": {
                    "total_episodes": 0,
                    "status": "connected"
                },
                "contextual_memory": {
                    "total_contexts": 0,
                    "status": "connected"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Try to get actual stats
            try:
                if hasattr(memory_manager, 'neo4j_store') and hasattr(memory_manager.neo4j_store, 'get_stats'):
                    semantic_stats = memory_manager.neo4j_store.get_stats()
                    stats["semantic_memory"].update(semantic_stats)
                elif hasattr(memory_manager, 'get_stats'):
                    all_stats = memory_manager.get_stats()
                    if "semantic_memory" in all_stats:
                        stats["semantic_memory"].update(all_stats["semantic_memory"])
            except Exception as e:
                logger.warning(f"Could not get semantic memory stats: {e}")
                
            await websocket_manager.send_personal_message(
                client_id,
                WebSocketMessage(
                    message_type=MessageType.MEMORY_STATS,
                    data=stats,
                    timestamp=datetime.now()
                )
            )
            
        except Exception as e:
            logger.error(f"Error handling memory stats request: {e}")
            await websocket_manager.send_error_message(client_id, f"Memory stats failed: {e}")
            
    async def handle_memory_nodes_request(self, client_id: str, message: WebSocketMessage):
        """Handle memory nodes requests"""
        try:
            from memory.memory_manager import MemoryManager
            
            query = message.data.get("query", "*")
            node_type = message.data.get("node_type")
            limit = message.data.get("limit", 10)
            
            memory_manager = MemoryManager()
            nodes = []
            
            try:
                # Query semantic memory nodes
                if hasattr(memory_manager, 'neo4j_store') and hasattr(memory_manager.neo4j_store, 'query_nodes'):
                    nodes = memory_manager.neo4j_store.query_nodes(query, node_type, limit)
                elif hasattr(memory_manager, 'query_nodes'):
                    nodes = memory_manager.query_nodes(query, node_type, limit)
                else:
                    nodes = []
            except Exception as e:
                logger.warning(f"Could not query memory nodes: {e}")
                nodes = []
                
            await websocket_manager.send_personal_message(
                client_id,
                WebSocketMessage(
                    message_type=MessageType.MEMORY_NODES,
                    data={
                        "query": query,
                        "node_type": node_type,
                        "limit": limit,
                        "nodes": nodes,
                        "count": len(nodes),
                        "timestamp": datetime.now().isoformat()
                    },
                    timestamp=datetime.now()
                )
            )
            
        except Exception as e:
            logger.error(f"Error handling memory nodes request: {e}")
            await websocket_manager.send_error_message(client_id, f"Memory nodes failed: {e}")


# System event broadcasting functions
async def broadcast_agent_status(agent_id: str, status: str, data: Dict[str, Any] = None):
    """Broadcast agent status updates to all subscribed clients"""
    message = WebSocketMessage(
        message_type=MessageType.AGENT_STATUS,
        data={
            "agent_id": agent_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        },
        timestamp=datetime.now()
    )
    
    await websocket_manager.broadcast_message(message)
    

async def broadcast_workflow_update(workflow_id: str, status: str, data: Dict[str, Any] = None):
    """Broadcast workflow updates to all subscribed clients"""
    message = WebSocketMessage(
        message_type=MessageType.WORKFLOW_UPDATE,
        data={
            "workflow_id": workflow_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        },
        timestamp=datetime.now()
    )
    
    await websocket_manager.broadcast_message(message)
    

async def broadcast_system_metrics(metrics: Dict[str, Any]):
    """Broadcast system metrics to all subscribed clients"""
    message = WebSocketMessage(
        message_type=MessageType.SYSTEM_METRICS,
        data={
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        },
        timestamp=datetime.now()
    )
    
    await websocket_manager.broadcast_message(message)
    

async def broadcast_memory_update(memory_type: str, operation: str, data: Dict[str, Any] = None):
    """Broadcast memory updates to all subscribed clients"""
    message = WebSocketMessage(
        message_type=MessageType.MEMORY_UPDATE,
        data={
            "memory_type": memory_type,
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        },
        timestamp=datetime.now()
    )
    
    await websocket_manager.broadcast_message(message)
    

async def broadcast_graph_update(update_type: str, data: Dict[str, Any] = None):
    """Broadcast knowledge graph updates to all subscribed clients"""
    message = WebSocketMessage(
        message_type=MessageType.GRAPH_UPDATE,
        data={
            "update_type": update_type,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        },
        timestamp=datetime.now()
    )
    
    await websocket_manager.broadcast_message(message)
    

async def broadcast_error_alert(error_type: str, message: str, severity: str = "warning"):
    """Broadcast system errors/alerts to all subscribed clients"""
    alert_message = WebSocketMessage(
        message_type=MessageType.ERROR_ALERT,
        data={
            "error_type": error_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        },
        timestamp=datetime.now()
    )
    
    await websocket_manager.broadcast_message(alert_message)


# Initialize integration
websocket_integration = WebSocketIntegration()


# REST endpoints for WebSocket management
@websocket_router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return websocket_manager.get_connection_stats()


@websocket_router.post("/ws/broadcast")
async def broadcast_message_endpoint(
    message_type: str,
    data: Dict[str, Any],
    exclude_client: str = None
):
    """REST endpoint to broadcast messages to WebSocket clients"""
    try:
        msg_type = MessageType(message_type)
        message = WebSocketMessage(
            message_type=msg_type,
            data=data,
            timestamp=datetime.now()
        )
        
        await websocket_manager.broadcast_message(message, exclude_client)
        
        return {"status": "broadcasted", "message_type": message_type}
        
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid message type: {message_type}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Broadcast failed: {e}")


@websocket_router.get("/ws/clients")
async def get_active_clients():
    """Get list of active WebSocket clients"""
    stats = websocket_manager.get_connection_stats()
    return {
        "active_clients": list(websocket_manager.active_connections.keys()),
        "connection_count": stats["active_connections"],
        "total_messages": stats["total_messages_sent"]
    }
