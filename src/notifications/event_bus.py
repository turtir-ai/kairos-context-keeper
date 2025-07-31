#!/usr/bin/env python3
"""
Notification Event Bus System
Handles multi-channel notifications with rate limiting and spam prevention
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)

class NotificationSeverity(Enum):
    """Notification severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class NotificationChannel(Enum):
    """Available notification channels"""
    IDE_MCP = "ide_mcp"
    WEBSOCKET = "websocket"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    CONSOLE = "console"

@dataclass
class NotificationEvent:
    """Notification event data structure"""
    id: str
    title: str
    message: str
    severity: NotificationSeverity
    source: str
    channels: List[NotificationChannel]
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    acknowledged: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class NotificationSettings:
    """User notification preferences"""
    user_id: str
    enabled_channels: List[NotificationChannel]
    severity_filter: NotificationSeverity
    rate_limit_minutes: int = 5
    max_notifications_per_period: int = 10
    quiet_hours: Dict[str, str] = None  # {"start": "22:00", "end": "08:00"}
    
    def __post_init__(self):
        if self.quiet_hours is None:
            self.quiet_hours = {}

class RateLimiter:
    """Rate limiting for notifications to prevent spam"""
    
    def __init__(self):
        self.notification_counts = defaultdict(list)
    
    def is_allowed(self, source: str, settings: NotificationSettings) -> bool:
        """Check if notification is allowed based on rate limits"""
        now = datetime.now()
        window_start = now - timedelta(minutes=settings.rate_limit_minutes)
        
        # Clean old notifications
        self.notification_counts[source] = [
            timestamp for timestamp in self.notification_counts[source]
            if timestamp > window_start
        ]
        
        current_count = len(self.notification_counts[source])
        return current_count < settings.max_notifications_per_period
    
    def record_notification(self, source: str):
        """Record a sent notification"""
        self.notification_counts[source].append(datetime.now())

class NotificationEventBus:
    """Main event bus for handling notifications"""
    
    def __init__(self):
        self.subscribers: Dict[NotificationChannel, List[Callable]] = defaultdict(list)
        self.rate_limiter = RateLimiter()
        self.user_settings: Dict[str, NotificationSettings] = {}
        self.notification_history: List[NotificationEvent] = []
        self._max_history = 1000
        
    def subscribe(self, channel: NotificationChannel, handler: Callable):
        """Subscribe to notifications for a specific channel"""
        self.subscribers[channel].append(handler)
        logger.info(f"Subscribed handler to {channel.value} channel")
    
    def unsubscribe(self, channel: NotificationChannel, handler: Callable):
        """Unsubscribe from notifications"""
        if handler in self.subscribers[channel]:
            self.subscribers[channel].remove(handler)
            logger.info(f"Unsubscribed handler from {channel.value} channel")
    
    def set_user_settings(self, user_id: str, settings: NotificationSettings):
        """Set notification settings for a user"""
        self.user_settings[user_id] = settings
        logger.info(f"Updated notification settings for user: {user_id}")
    
    def get_user_settings(self, user_id: str) -> NotificationSettings:
        """Get notification settings for a user"""
        return self.user_settings.get(user_id, NotificationSettings(
            user_id=user_id,
            enabled_channels=[NotificationChannel.CONSOLE],
            severity_filter=NotificationSeverity.INFO
        ))
    
    async def publish(self, event: NotificationEvent, user_id: str = "default"):
        """Publish a notification event"""
        try:
            logger.debug(f"Publishing notification: {event.title}")
            
            # Get user settings
            settings = self.get_user_settings(user_id)
            
            # Check if notification should be sent
            if not self._should_send_notification(event, settings):
                logger.debug(f"Notification filtered out: {event.title}")
                return
            
            # Check rate limiting
            if not self.rate_limiter.is_allowed(event.source, settings):
                logger.warning(f"Rate limit exceeded for source: {event.source}")
                return
            
            # Filter channels based on user preferences
            allowed_channels = [
                channel for channel in event.channels
                if channel in settings.enabled_channels
            ]
            
            if not allowed_channels:
                logger.debug(f"No allowed channels for notification: {event.title}")
                return
            
            # Send to each channel
            tasks = []
            for channel in allowed_channels:
                if channel in self.subscribers:
                    for handler in self.subscribers[channel]:
                        tasks.append(self._send_to_handler(handler, event, channel))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                self.rate_limiter.record_notification(event.source)
                self._add_to_history(event)
                logger.info(f"Notification sent: {event.title}")
            
        except Exception as e:
            logger.error(f"Error publishing notification: {e}")
    
    async def _send_to_handler(self, handler: Callable, event: NotificationEvent, channel: NotificationChannel):
        """Send notification to a specific handler"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event, channel)
            else:
                handler(event, channel)
        except Exception as e:
            logger.error(f"Error in notification handler for {channel.value}: {e}")
    
    def _should_send_notification(self, event: NotificationEvent, settings: NotificationSettings) -> bool:
        """Check if notification should be sent based on settings"""
        # Check severity filter
        severity_levels = {
            NotificationSeverity.DEBUG: 0,
            NotificationSeverity.INFO: 1,
            NotificationSeverity.WARNING: 2,
            NotificationSeverity.ERROR: 3,
            NotificationSeverity.CRITICAL: 4
        }
        
        if severity_levels[event.severity] < severity_levels[settings.severity_filter]:
            return False
        
        # Check quiet hours
        if settings.quiet_hours and "start" in settings.quiet_hours and "end" in settings.quiet_hours:
            now = datetime.now().time()
            start_time = datetime.strptime(settings.quiet_hours["start"], "%H:%M").time()
            end_time = datetime.strptime(settings.quiet_hours["end"], "%H:%M").time()
            
            if start_time <= end_time:
                # Same day quiet hours
                if start_time <= now <= end_time:
                    return False
            else:
                # Overnight quiet hours
                if now >= start_time or now <= end_time:
                    return False
        
        return True
    
    def _add_to_history(self, event: NotificationEvent):
        """Add notification to history"""
        self.notification_history.append(event)
        
        # Maintain history size limit
        try:
            max_history = int(self._max_history) if self._max_history is not None else 1000
            if len(self.notification_history) > max_history:
                self.notification_history = self.notification_history[-max_history:]
        except (ValueError, TypeError):
            # Fallback if _max_history is not a valid integer
            if len(self.notification_history) > 1000:
                self.notification_history = self.notification_history[-1000:]
    
    def get_notification_history(self, user_id: str = None, limit: int = 50) -> List[NotificationEvent]:
        """Get notification history"""
        try:
            # Ensure limit is a valid integer
            safe_limit = int(limit) if limit is not None else 50
            if safe_limit < 0:
                safe_limit = 50
            
            # Safe slice operation
            if len(self.notification_history) == 0:
                return []
            elif len(self.notification_history) <= safe_limit:
                return self.notification_history.copy()
            else:
                return self.notification_history[-safe_limit:]
        except (ValueError, TypeError):
            # Fallback if limit is not a valid integer
            return self.notification_history[-50:] if self.notification_history else []
    
    def acknowledge_notification(self, notification_id: str):
        """Mark a notification as acknowledged"""
        for event in self.notification_history:
            if event.id == notification_id:
                event.acknowledged = True
                logger.info(f"Notification acknowledged: {notification_id}")
                break

# Global event bus instance
event_bus = NotificationEventBus()

# Convenience functions for common notification types
async def notify_supervisor_insight(title: str, message: str, metadata: Dict[str, Any] = None):
    """Send supervisor insight notification"""
    import uuid
    event = NotificationEvent(
        id=str(uuid.uuid4()),
        title=title,
        message=message,
        severity=NotificationSeverity.INFO,
        source="supervisor_agent",
        channels=[NotificationChannel.IDE_MCP, NotificationChannel.WEBSOCKET],
        metadata=metadata or {}
    )
    await event_bus.publish(event)

async def notify_system_error(title: str, message: str, metadata: Dict[str, Any] = None):
    """Send system error notification"""
    import uuid
    event = NotificationEvent(
        id=str(uuid.uuid4()),
        title=title,
        message=message,
        severity=NotificationSeverity.ERROR,
        source="system",
        channels=[NotificationChannel.IDE_MCP, NotificationChannel.WEBSOCKET, NotificationChannel.CONSOLE],
        metadata=metadata or {}
    )
    await event_bus.publish(event)

async def notify_security_alert(title: str, message: str, metadata: Dict[str, Any] = None):
    """Send security alert notification"""
    import uuid
    event = NotificationEvent(
        id=str(uuid.uuid4()),
        title=title,
        message=message,
        severity=NotificationSeverity.CRITICAL,
        source="security",
        channels=[NotificationChannel.IDE_MCP, NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL],
        metadata=metadata or {}
    )
    await event_bus.publish(event)

async def notify_performance_warning(title: str, message: str, metadata: Dict[str, Any] = None):
    """Send performance warning notification"""
    import uuid
    event = NotificationEvent(
        id=str(uuid.uuid4()),
        title=title,
        message=message,
        severity=NotificationSeverity.WARNING,
        source="performance_monitor",
        channels=[NotificationChannel.IDE_MCP, NotificationChannel.WEBSOCKET],
        metadata=metadata or {}
    )
    await event_bus.publish(event)
