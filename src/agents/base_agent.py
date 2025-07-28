import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Import MCP for context management
try:
    from ..mcp.model_context_protocol import MCPContext
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

class BaseAgent:
    """A base class for all agents."""

    def __init__(self, name: str, mcp_context: Optional['MCPContext'] = None):
        self.name = name
        self.status = "ready"
        self.logger = logging.getLogger(self.__class__.__name__)
        self.websocket_manager = None  # Will be injected by coordinator
        self.mcp_context = mcp_context  # MCP context for agent operations
        self.last_activity = datetime.now()
        self.task_count = 0
        self.error_count = 0
        self.metadata = {}

    def set_websocket_manager(self, websocket_manager):
        """Inject WebSocket manager for real-time updates."""
        self.websocket_manager = websocket_manager
    
    def update_status(self, new_status: str, metadata: Optional[Dict[str, Any]] = None):
        """Update agent status and broadcast to WebSocket clients."""
        old_status = self.status
        self.status = new_status
        self.last_activity = datetime.now()
        
        if metadata:
            self.metadata.update(metadata)
        
        self.logger.info(f"Agent {self.name} status changed: {old_status} -> {new_status}")
        
        # Broadcast status change via WebSocket
        if self.websocket_manager:
            status_update = {
                "type": "agent_status_update",
                "agent_name": self.name,
                "agent_type": self.__class__.__name__,
                "old_status": old_status,
                "new_status": new_status,
                "timestamp": self.last_activity.isoformat(),
                "metadata": metadata or {},
                "task_count": self.task_count,
                "error_count": self.error_count
            }
            # Fire and forget - don't await to avoid blocking
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.websocket_manager.broadcast_message(status_update))
            except Exception as e:
                self.logger.warning(f"Failed to broadcast status update: {e}")
    
    def increment_task_count(self):
        """Increment task count and update activity."""
        self.task_count += 1
        self.last_activity = datetime.now()
    
    def increment_error_count(self):
        """Increment error count and update activity."""
        self.error_count += 1
        self.last_activity = datetime.now()
    
    def get_status(self):
        """Get the current status of the agent."""
        return {
            "name": self.name,
            "agent_type": self.__class__.__name__,
            "status": self.status,
            "last_activity": self.last_activity.isoformat(),
            "task_count": self.task_count,
            "error_count": self.error_count,
            "uptime_seconds": (datetime.now() - self.last_activity).total_seconds(),
            "metadata": self.metadata
        }
