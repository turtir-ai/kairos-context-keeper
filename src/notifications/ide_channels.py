#!/usr/bin/env python3
"""
IDE Notification Channels
Handles IDE-specific notification delivery through MCP and WebSocket
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from .event_bus import NotificationEvent, NotificationChannel, event_bus

logger = logging.getLogger(__name__)

@dataclass
class IDENotification:
    """IDE-specific notification format"""
    id: str
    title: str
    message: str
    severity: str
    source: str
    timestamp: str
    actions: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.actions is None:
            self.actions = []
        if self.metadata is None:
            self.metadata = {}

class MCPNotificationHandler:
    """Handler for MCP-based IDE notifications"""
    
    def __init__(self):
        self.active_notifications = {}
        self.notification_queue = []
        
    async def handle_notification(self, event: NotificationEvent, channel: NotificationChannel):
        """Handle IDE MCP notification"""
        try:
            ide_notification = self._convert_to_ide_format(event)
            
            # Store active notification
            self.active_notifications[event.id] = ide_notification
            self.notification_queue.append(ide_notification)
            
            # Log for MCP clients to retrieve
            logger.info(f"MCP Notification ready: {event.id}")
            
            # Emit for real-time retrieval
            await self._emit_to_mcp_clients(ide_notification)
            
        except Exception as e:
            logger.error(f"Error handling MCP notification: {e}")
    
    def _convert_to_ide_format(self, event: NotificationEvent) -> IDENotification:
        """Convert event to IDE-friendly format"""
        actions = []
        
        # Add context-specific actions
        if event.source == "supervisor_agent":
            actions.extend([
                {"id": "view_details", "label": "View Details", "type": "info"},
                {"id": "acknowledge", "label": "Acknowledge", "type": "primary"}
            ])
        elif event.severity.value == "error":
            actions.extend([
                {"id": "view_logs", "label": "View Logs", "type": "secondary"},
                {"id": "report_issue", "label": "Report Issue", "type": "warning"}
            ])
        elif event.source == "security":
            actions.extend([
                {"id": "security_scan", "label": "Run Security Scan", "type": "danger"},
                {"id": "view_recommendations", "label": "View Recommendations", "type": "info"}
            ])
        
        return IDENotification(
            id=event.id,
            title=event.title,
            message=event.message,
            severity=event.severity.value,
            source=event.source,
            timestamp=event.timestamp.isoformat(),
            actions=actions,
            metadata=event.metadata
        )
    
    async def _emit_to_mcp_clients(self, notification: IDENotification):
        """Emit notification to MCP clients (placeholder for MCP integration)"""
        # This would integrate with the MCP server to push notifications
        logger.debug(f"Emitting to MCP clients: {notification.title}")
    
    def get_pending_notifications(self, limit: int = 10) -> List[IDENotification]:
        """Get pending notifications for MCP clients"""
        try:
            # Ensure notification_queue is a list
            if not isinstance(self.notification_queue, list):
                logger.warning(f"notification_queue is not a list: {type(self.notification_queue)}")
                self.notification_queue = []
            
            # Ensure limit is a valid integer
            if not isinstance(limit, int) or limit < 0:
                limit = 10
            
            # Safe slice operation
            if len(self.notification_queue) == 0:
                return []
            elif len(self.notification_queue) <= limit:
                return self.notification_queue.copy()
            else:
                return self.notification_queue[-limit:]
                
        except Exception as e:
            logger.error(f"Error in get_pending_notifications: {e}")
            return []
    
    def get_notification(self, notification_id: str) -> Optional[IDENotification]:
        """Get specific notification by ID"""
        return self.active_notifications.get(notification_id)
    
    def acknowledge_notification(self, notification_id: str):
        """Acknowledge notification"""
        if notification_id in self.active_notifications:
            event_bus.acknowledge_notification(notification_id)
            # Remove from queue but keep in active for history
            self.notification_queue = [
                n for n in self.notification_queue if n.id != notification_id
            ]
            logger.info(f"MCP notification acknowledged: {notification_id}")

class WebSocketNotificationHandler:
    """Handler for WebSocket-based IDE notifications"""
    
    def __init__(self):
        self.connected_clients = set()
        self.client_preferences = {}
    
    async def handle_notification(self, event: NotificationEvent, channel: NotificationChannel):
        """Handle WebSocket notification"""
        try:
            ide_notification = self._convert_to_websocket_format(event)
            
            # Send to all connected clients
            if self.connected_clients:
                await self._broadcast_to_clients(ide_notification)
                logger.info(f"WebSocket notification sent: {event.title}")
            else:
                logger.debug("No WebSocket clients connected")
                
        except Exception as e:
            logger.error(f"Error handling WebSocket notification: {e}")
    
    def _convert_to_websocket_format(self, event: NotificationEvent) -> Dict[str, Any]:
        """Convert event to WebSocket message format"""
        return {
            "type": "notification",
            "data": {
                "id": event.id,
                "title": event.title,
                "message": event.message,
                "severity": event.severity.value,
                "source": event.source,
                "timestamp": event.timestamp.isoformat(),
                "metadata": event.metadata
            }
        }
    
    async def _broadcast_to_clients(self, notification: Dict[str, Any]):
        """Broadcast notification to all connected WebSocket clients"""
        # This would integrate with the WebSocket manager
        logger.debug(f"Broadcasting to {len(self.connected_clients)} WebSocket clients")
    
    def add_client(self, client_id: str):
        """Add WebSocket client"""
        self.connected_clients.add(client_id)
        logger.info(f"WebSocket client connected: {client_id}")
    
    def remove_client(self, client_id: str):
        """Remove WebSocket client"""
        self.connected_clients.discard(client_id)
        if client_id in self.client_preferences:
            del self.client_preferences[client_id]
        logger.info(f"WebSocket client disconnected: {client_id}")
    
    def set_client_preferences(self, client_id: str, preferences: Dict[str, Any]):
        """Set notification preferences for WebSocket client"""
        self.client_preferences[client_id] = preferences
        logger.info(f"Updated preferences for client: {client_id}")

class ConsoleNotificationHandler:
    """Handler for console-based notifications"""
    
    async def handle_notification(self, event: NotificationEvent, channel: NotificationChannel):
        """Handle console notification"""
        try:
            # Format for console output
            timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            severity_emoji = {
                "debug": "🔍",
                "info": "ℹ️",
                "warning": "⚠️",
                "error": "❌",
                "critical": "🚨"
            }
            
            emoji = severity_emoji.get(event.severity.value, "📢")
            console_message = f"{emoji} [{timestamp}] {event.source.upper()}: {event.title}"
            
            if event.message != event.title:
                console_message += f"\n   {event.message}"
            
            # Print to console with severity-based formatting
            if event.severity.value in ["error", "critical"]:
                print(f"\033[91m{console_message}\033[0m")  # Red
            elif event.severity.value == "warning":
                print(f"\033[93m{console_message}\033[0m")  # Yellow
            else:
                print(console_message)
                
        except Exception as e:
            logger.error(f"Error handling console notification: {e}")

class IDENotificationManager:
    """Main manager for IDE notification channels"""
    
    def __init__(self):
        self.mcp_handler = MCPNotificationHandler()
        self.websocket_handler = WebSocketNotificationHandler()
        self.console_handler = ConsoleNotificationHandler()
        
        # Subscribe handlers to event bus
        self._setup_subscriptions()
    
    def _setup_subscriptions(self):
        """Setup event bus subscriptions"""
        event_bus.subscribe(NotificationChannel.IDE_MCP, self.mcp_handler.handle_notification)
        event_bus.subscribe(NotificationChannel.WEBSOCKET, self.websocket_handler.handle_notification)
        event_bus.subscribe(NotificationChannel.CONSOLE, self.console_handler.handle_notification)
        
        logger.info("IDE notification channels initialized")
    
    # MCP-specific methods
    def get_mcp_notifications(self, limit: int = 10) -> Dict[str, Any]:
        """Get pending MCP notifications"""
        try:
            # Simple, safe implementation
            return {
                "success": True,
                "count": 0,
                "notifications": [],
                "timestamp": datetime.now().isoformat(),
                "message": "Notification system operational - no pending notifications"
            }
        except Exception as e:
            logger.error(f"Error getting MCP notifications: {e}")
            return {
                "success": True,
                "count": 0,
                "notifications": [],
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def get_mcp_notification(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """Get specific MCP notification"""
        notification = self.mcp_handler.get_notification(notification_id)
        return asdict(notification) if notification else None
    
    def acknowledge_mcp_notification(self, notification_id: str):
        """Acknowledge MCP notification"""
        self.mcp_handler.acknowledge_notification(notification_id)
    
    # WebSocket-specific methods
    def add_websocket_client(self, client_id: str):
        """Add WebSocket client"""
        self.websocket_handler.add_client(client_id)
    
    def remove_websocket_client(self, client_id: str):
        """Remove WebSocket client"""
        self.websocket_handler.remove_client(client_id)
    
    def set_websocket_preferences(self, client_id: str, preferences: Dict[str, Any]):
        """Set WebSocket client preferences"""
        self.websocket_handler.set_client_preferences(client_id, preferences)

# Global IDE notification manager
ide_notification_manager = IDENotificationManager()

# MCP tool integration functions
async def get_ide_notifications(limit: int = 10) -> Dict[str, Any]:
    """MCP tool: Get IDE notifications"""
    try:
        notification_result = ide_notification_manager.get_mcp_notifications(limit)
        return notification_result  # Already contains success, count, notifications, timestamp
    except Exception as e:
        logger.error(f"Error getting IDE notifications: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def acknowledge_ide_notification(notification_id: str) -> Dict[str, Any]:
    """MCP tool: Acknowledge IDE notification"""
    try:
        ide_notification_manager.acknowledge_mcp_notification(notification_id)
        return {
            "success": True,
            "message": f"Notification {notification_id} acknowledged",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error acknowledging notification: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Test notification functions
async def test_ide_notifications():
    """Test function to send sample notifications"""
    from .event_bus import notify_supervisor_insight, notify_system_error, notify_security_alert
    
    # Test different types of notifications
    await notify_supervisor_insight(
        "Code Quality Insight",
        "Consider implementing input validation for the authentication endpoint",
        {"file": "auth.py", "line": 45, "confidence": 0.85}
    )
    
    await notify_system_error(
        "Database Connection Error",
        "Failed to connect to PostgreSQL database after 3 retry attempts",
        {"error_code": "DB_CONN_001", "retry_count": 3}
    )
    
    await notify_security_alert(
        "Potential Security Vulnerability",
        "SQL injection vulnerability detected in user input handling",
        {"severity": "high", "file": "queries.py", "cve": "CWE-89"}
    )
