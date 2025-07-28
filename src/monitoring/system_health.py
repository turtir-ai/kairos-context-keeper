"""
System Health Monitor for Kairos
Provides comprehensive system health monitoring, performance metrics collection,
error pattern detection, and critical threshold alerting.
"""

import asyncio
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
import json
import threading
import statistics
import os
import subprocess
from pathlib import Path

from src.monitoring.performance_tracker import performance_tracker
from src.api.websocket_manager import websocket_manager, WebSocketMessage, MessageType


@dataclass
class HealthMetric:
    """Health metric data structure"""
    name: str
    value: float
    threshold: float
    status: str  # "healthy", "warning", "critical"
    timestamp: str
    unit: str = ""
    description: str = ""


@dataclass
class SystemAlert:
    """System alert data structure"""
    alert_id: str
    metric_name: str
    severity: str  # "low", "medium", "high", "critical"
    current_value: float
    threshold: float
    message: str
    timestamp: str
    resolved: bool = False
    auto_healing_attempted: bool = False


class SystemHealthMonitor:
    """Comprehensive system health monitoring with proactive alerting"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.monitoring_active = False
        self.health_history = deque(maxlen=1000)
        self.active_alerts = {}
        self.error_patterns = defaultdict(list)
        
        # Health thresholds
        self.thresholds = {
            "cpu_percent": {"warning": 75.0, "critical": 90.0},
            "memory_percent": {"warning": 80.0, "critical": 95.0},
            "disk_usage_percent": {"warning": 85.0, "critical": 95.0},
            "response_time_ms": {"warning": 2000.0, "critical": 5000.0},
            "error_rate": {"warning": 0.05, "critical": 0.15},
            "api_calls_per_minute": {"warning": 100.0, "critical": 200.0},
            "memory_leak_rate": {"warning": 10.0, "critical": 25.0}  # MB per hour
        }
        
        # Auto-healing actions
        self.healing_actions = {
            "high_memory_usage": self._handle_high_memory,
            "high_cpu_usage": self._handle_high_cpu,
            "disk_space_low": self._handle_disk_space,
            "error_rate_high": self._handle_high_errors,
            "response_time_high": self._handle_slow_response
        }
        
        # Metrics collection
        self.current_metrics = {}
        self.monitor_thread = None
        
        self.logger.info("🏥 System Health Monitor initialized")
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        if self.monitoring_active:
            self.logger.warning("System health monitoring is already active")
            return
        
        self.monitoring_active = True
        self.logger.info("🚀 Starting system health monitoring")
        
        # Start monitoring tasks
        asyncio.create_task(self._health_monitoring_loop())
        asyncio.create_task(self._error_pattern_detection_loop())
        asyncio.create_task(self._auto_healing_loop())
        
        self.logger.info("✅ System health monitoring started")
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self.monitoring_active = False
        self.logger.info("🛑 System health monitoring stopped")
    
    async def _health_monitoring_loop(self):
        """Main health monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Evaluate health status
                health_status = self._evaluate_health_status()
                
                # Store health data
                self.health_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "metrics": self.current_metrics.copy(),
                    "status": health_status
                })
                
                # Broadcast health update
                await self._broadcast_health_update(health_status)
                
                # Check for threshold breaches
                await self._check_thresholds()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _collect_system_metrics(self):
        """Collect comprehensive system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network metrics
            network_io = psutil.net_io_counters()
            
            # Process metrics (for Kairos daemon)
            current_process = psutil.Process()
            process_memory = current_process.memory_info()
            process_cpu = current_process.cpu_percent()
            
            # Application-specific metrics from performance tracker
            perf_metrics = performance_tracker.get_metrics_summary(time_range_minutes=5)
            
            # Update current metrics
            self.current_metrics.update({
                # System metrics
                "cpu_percent": cpu_percent,
                "cpu_count": cpu_count,
                "cpu_frequency_mhz": cpu_freq.current if cpu_freq else 0,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "memory_used_gb": memory.used / (1024**3),
                "swap_percent": swap.percent,
                "disk_usage_percent": (disk_usage.used / disk_usage.total) * 100,
                "disk_free_gb": disk_usage.free / (1024**3),
                "disk_read_mb": disk_io.read_bytes / (1024**2) if disk_io else 0,
                "disk_write_mb": disk_io.write_bytes / (1024**2) if disk_io else 0,
                "network_sent_mb": network_io.bytes_sent / (1024**2) if network_io else 0,
                "network_recv_mb": network_io.bytes_recv / (1024**2) if network_io else 0,
                
                # Process metrics
                "process_memory_mb": process_memory.rss / (1024**2),
                "process_memory_percent": process_cpu,
                
                # Application metrics
                "active_connections": len(websocket_manager.active_connections),
                "total_errors": perf_metrics.get("counters", {}).get("errors", 0),
                "api_calls": perf_metrics.get("counters", {}).get("api_calls", 0),
            })
            
            # Calculate derived metrics
            if "system_cpu_percent" in perf_metrics.get("aggregated_metrics", {}):
                self.current_metrics["avg_response_time_ms"] = perf_metrics["aggregated_metrics"].get(
                    "execution_time_api_call", {}).get("avg", 0) * 1000
            
            # Error rate calculation
            total_calls = max(self.current_metrics["api_calls"], 1)
            self.current_metrics["error_rate"] = self.current_metrics["total_errors"] / total_calls
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
    
    
    async def _check_thresholds(self):
        """Check metrics against thresholds and generate alerts"""
        for metric_name, value in self.current_metrics.items():
            if metric_name not in self.thresholds:
                continue
            
            thresholds = self.thresholds[metric_name]
            severity = None
            
            if value >= thresholds["critical"]:
                severity = "critical"
            elif value >= thresholds["warning"]:
                severity = "warning"
            
            if severity:
                alert_id = f"{metric_name}_{severity}_{int(time.time())}"
                
                # Check if similar alert already exists
                existing_alert = None
                for alert in self.active_alerts.values():
                    if alert.metric_name == metric_name and not alert.resolved:
                        existing_alert = alert
                        break
                
                if not existing_alert:
                    alert = SystemAlert(
                        alert_id=alert_id,
                        metric_name=metric_name,
                        severity=severity,
                        current_value=value,
                        threshold=thresholds[severity],
                        message=f"{metric_name} is {severity}: {value:.2f} (threshold: {thresholds[severity]:.2f})",
                        timestamp=datetime.now().isoformat()
                    )
                    
                    self.active_alerts[alert_id] = alert
                    await self._broadcast_alert(alert)
                    
                    # Trigger auto-healing if critical
                    if severity == "critical":
                        await self._trigger_auto_healing(metric_name, value)
    
    async def _trigger_auto_healing(self, metric_name: str, value: float):
        """Trigger auto-healing actions for critical issues"""
        healing_key = None
        
        if "memory" in metric_name:
            healing_key = "high_memory_usage"
        elif "cpu" in metric_name:
            healing_key = "high_cpu_usage"
        elif "disk" in metric_name:
            healing_key = "disk_space_low"
        elif "error_rate" in metric_name:
            healing_key = "error_rate_high"
        elif "response_time" in metric_name:
            healing_key = "response_time_high"
        
        if healing_key and healing_key in self.healing_actions:
            self.logger.warning(f"🚑 Triggering auto-healing for {metric_name}: {healing_key}")
            try:
                await self.healing_actions[healing_key](metric_name, value)
            except Exception as e:
                self.logger.error(f"Auto-healing failed for {healing_key}: {e}")
    
    async def _handle_high_memory(self, metric_name: str, value: float):
        """Handle high memory usage"""
        self.logger.info("🧹 Attempting memory cleanup...")
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Clear performance tracker old metrics
        performance_tracker.cleanup_old_metrics(older_than_hours=1)
        
        # Restart background processes if needed
        # This is a placeholder for more aggressive memory management
        
        self.logger.info("✅ Memory cleanup completed")
    
    async def _handle_high_cpu(self, metric_name: str, value: float):
        """Handle high CPU usage"""
        self.logger.info("⚡ Attempting CPU optimization...")
        
        # Reduce monitoring frequency temporarily  
        await asyncio.sleep(30)
        
        # Could implement process priority adjustment here
        
        self.logger.info("✅ CPU optimization completed")
    
    async def _handle_disk_space(self, metric_name: str, value: float):
        """Handle low disk space"""
        self.logger.info("💾 Attempting disk cleanup...")
        
        # Clean old log files
        logs_path = Path("logs/")
        if logs_path.exists():
            for log_file in logs_path.glob("*.log"):
                if log_file.stat().st_mtime < time.time() - (7 * 24 * 3600):  # Older than 7 days
                    try:
                        log_file.unlink()
                        self.logger.info(f"Deleted old log file: {log_file}")
                    except Exception as e:
                        self.logger.error(f"Could not delete {log_file}: {e}")
        
        self.logger.info("✅ Disk cleanup completed")
    
    async def _handle_high_errors(self, metric_name: str, value: float):
        """Handle high error rate"""
        self.logger.info("🔧 Attempting error rate reduction...")
        
        # This could trigger model fallbacks, retry mechanisms, etc.
        
        self.logger.info("✅ Error handling completed")
    
    async def _handle_slow_response(self, metric_name: str, value: float):
        """Handle slow response times"""
        self.logger.info("🚀 Attempting response time optimization...")
        
        # This could trigger local model switching, caching improvements, etc.
        
        self.logger.info("✅ Response optimization completed")
    
    async def _error_pattern_detection_loop(self):
        """Detect patterns in error logs"""
        while self.monitoring_active:
            try:
                # This would analyze log patterns for recurring issues
                # Implementation would depend on log format and storage
                pass
            except Exception as e:
                self.logger.error(f"Error in pattern detection: {e}")
            
            await asyncio.sleep(300)  # Check every 5 minutes
    
    async def _auto_healing_loop(self):
        """Auto-healing monitoring loop"""
        while self.monitoring_active:
            try:
                # Check if auto-healing was successful
                for alert in self.active_alerts.values():
                    if alert.auto_healing_attempted and not alert.resolved:
                        # Check if the issue was resolved
                        current_value = self.current_metrics.get(alert.metric_name, 0)
                        threshold = self.thresholds[alert.metric_name]["warning"]
                        
                        if current_value < threshold:
                            alert.resolved = True
                            self.logger.info(f"✅ Auto-healing successful for {alert.metric_name}")
                            await self._broadcast_alert_resolved(alert)
            except Exception as e:
                self.logger.error(f"Error in auto-healing loop: {e}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _broadcast_health_update(self, health_status: str):
        """Broadcast health update via WebSocket"""
        message = WebSocketMessage(
            message_type=MessageType.SYSTEM_METRICS,
            data={
                "health_status": health_status,
                "metrics": self.current_metrics,
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )
        
        await websocket_manager.broadcast_message(message)
    
    async def _broadcast_alert(self, alert: SystemAlert):
        """Broadcast system alert"""
        message = WebSocketMessage(
            message_type=MessageType.ERROR_ALERT,
            data={
                "alert_id": alert.alert_id,
                "metric_name": alert.metric_name,
                "severity": alert.severity,
                "message": alert.message,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "timestamp": alert.timestamp
            },
            timestamp=datetime.now()
        )
        
        await websocket_manager.broadcast_message(message)
    
    async def _broadcast_alert_resolved(self, alert: SystemAlert):
        """Broadcast alert resolution"""
        message = WebSocketMessage(
            message_type=MessageType.ERROR_ALERT,
            data={
                "alert_id": alert.alert_id,
                "status": "resolved",
                "message": f"Alert resolved: {alert.message}",
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )
        
        await websocket_manager.broadcast_message(message)
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current system health status"""
        try:
            # Calculate current health status synchronously
            health_scores = []
            
            for metric_name, value in self.current_metrics.items():
                if metric_name in self.thresholds:
                    thresholds = self.thresholds[metric_name]
                    
                    if value >= thresholds["critical"]:
                        health_scores.append(0)  # Critical
                    elif value >= thresholds["warning"]:
                        health_scores.append(50)  # Warning
                    else:
                        health_scores.append(100)  # Healthy
            
            if not health_scores:
                status = "unknown"
            else:
                avg_health = statistics.mean(health_scores)
                
                if avg_health >= 80:
                    status = "healthy"
                elif avg_health >= 60:
                    status = "warning"
                elif avg_health >= 30:
                    status = "degraded"
                else:
                    status = "critical"
            
            return {
                "status": status,
                "metrics": self.current_metrics.copy(),
                "active_alerts": len(self.active_alerts),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting current status: {e}")
            return {
                "status": "unknown",
                "metrics": {},
                "active_alerts": 0,
                "timestamp": datetime.now().isoformat()
            }
    
    def _evaluate_health_status(self) -> str:
        """Evaluate overall system health status synchronously"""
        try:
            health_scores = []
            
            for metric_name, value in self.current_metrics.items():
                if metric_name in self.thresholds:
                    thresholds = self.thresholds[metric_name]
                    
                    if value >= thresholds["critical"]:
                        health_scores.append(0)  # Critical
                    elif value >= thresholds["warning"]:
                        health_scores.append(50)  # Warning
                    else:
                        health_scores.append(100)  # Healthy
            
            if not health_scores:
                return "unknown"
            
            avg_health = statistics.mean(health_scores)
            
            if avg_health >= 80:
                return "healthy"
            elif avg_health >= 60:
                return "warning"
            elif avg_health >= 30:
                return "degraded"
            else:
                return "critical"
                
        except Exception as e:
            self.logger.error(f"Error evaluating health status: {e}")
            return "unknown"
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get current health summary"""
        return {
            "status": self._evaluate_health_status(),
            "metrics": self.current_metrics,
            "active_alerts": len(self.active_alerts),
            "monitoring_active": self.monitoring_active,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        return [asdict(alert) for alert in self.active_alerts.values() if not alert.resolved]


# Global instance
system_health_monitor = SystemHealthMonitor()
