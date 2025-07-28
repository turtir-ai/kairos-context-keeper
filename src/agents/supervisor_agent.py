import asyncio
import logging
import os
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import deque
from pathlib import Path
import json
import uuid
import threading
import queue
import re
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.agents.base_agent import BaseAgent
from src.api.websocket_manager import websocket_manager, WebSocketMessage, MessageType
from src.monitoring.performance_tracker import performance_tracker
from src.monitoring.system_health import system_health_monitor
from src.core.anomaly_detector import get_anomaly_detector
from src.core.proactive_analyzer import proactive_analyzer


class SupervisorAgent(BaseAgent):
    """Supervisor Agent for overseeing the system functionality and health"""

    def __init__(self, name="Supervisor", mcp_context=None):
        super().__init__(name=name, mcp_context=mcp_context)
        self.anomaly_detector = None
        self.log_observer = None  # For real-time log monitoring
        self.event_queue = supervisor_event_queue
        self.monitoring_active = True
        self.proactive_suggestions = deque(maxlen=50)
        self.alert_count = 0

    async def initialize(self):
        """Initialize Supervisor Agent and its components"""
        self.anomaly_detector = await get_anomaly_detector()
        self.set_websocket_manager(websocket_manager)
        self.setup_log_monitoring()
        self.logger.info("Supervisor Agent initialized")
        await self.broadcast_status("initialized")

    def setup_log_monitoring(self):
        """Setup real-time log monitoring using filesystem events"""
        logs_path = Path("logs/")
        if not logs_path.exists():
            os.makedirs(logs_path)
        event_handler = LogEventHandler(queue=self.event_queue)
        self.log_observer = Observer()
        self.log_observer.schedule(event_handler, path=str(logs_path), recursive=False)
        self.log_observer.start()

    async def monitor_performance(self):
        """Continuously monitor system performance metrics"""
        while True:
            try:
                # Get current performance metrics
                metrics = performance_tracker.get_metrics_summary()
                await self.broadcast_metrics(metrics)

                # Check for anomalies
                for metric_name, data in metrics['aggregated_metrics'].items():
                    value = data['latest']
                    alert = await self.anomaly_detector.detect_anomaly(metric_name, value)
                    if alert:
                        await self.broadcast_alert(alert)

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Error in monitoring performance: {e}")

    async def broadcast_status(self, status):
        status_update = {
            "message_type": "supervisor_status",
            "data": {
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
        }
        await self.websocket_manager.broadcast_message(status_update)

    async def broadcast_metrics(self, metrics):
        metrics_message = {
            "message_type": "system_metrics",
            "data": metrics,
            "timestamp": datetime.now().isoformat()
        }
        await self.websocket_manager.broadcast_message(metrics_message)

    async def broadcast_alert(self, alert):
        alert_message = {
            "message_type": "anomaly_alert",
            "data": {
                "alert_id": alert.alert_id,
                "message": alert.description,
                "severity": alert.severity,
                "timestamp": alert.detected_at
            }
        }
        await self.websocket_manager.broadcast_message(alert_message)

    def stop(self):
        """Stop the Supervisor Agent and its components"""
        if self.log_observer:
            self.log_observer.stop()
            self.log_observer.join()
        self.logger.info("Supervisor Agent stopped")


class LogEventHandler(FileSystemEventHandler):
    """Handles file system events for log monitoring"""
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def on_modified(self, event):
        if event.src_path.endswith(".log"):
            with open(event.src_path, 'r') as file:
                lines = file.readlines()
                self.queue.put(lines[-1].strip())

    def on_created(self, event):
        self.on_modified(event)

# Background event queue for handling events
class EventQueue:
    def __init__(self):
        self.queue = deque()

    def put(self, item):
        self.queue.append(item)

    def get(self):
        if self.queue:
            return self.queue.popleft()
    
    def is_empty(self):
        return len(self.queue) == 0

# Init queue
supervisor_event_queue = EventQueue()
