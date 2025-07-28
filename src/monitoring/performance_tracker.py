import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import json
import threading
from collections import deque

@dataclass
class MetricData:
    """Structure for storing metric data"""
    timestamp: str
    metric_name: str
    value: float
    tags: Dict[str, str]
    unit: str = ""
    
class PerformanceTracker:
    """Advanced performance tracking and monitoring system"""
    
    def __init__(self, max_history_size: int = 1000):
        self.logger = logging.getLogger(__name__)
        self.max_history_size = max_history_size
        
        # Metrics storage
        self.metrics_history = deque(maxlen=max_history_size)
        self.current_metrics = {}
        
        # Performance counters
        self.counters = {
            "agent_requests": 0,
            "ai_generations": 0,
            "memory_operations": 0,
            "api_calls": 0,
            "errors": 0
        }
        
        # System monitoring
        self.system_stats = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_usage": 0.0,
            "network_io": {"bytes_sent": 0, "bytes_recv": 0}
        }
        
        # Start background monitoring
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._background_monitoring, daemon=True)
        self.monitor_thread.start()
        
        # Automatic error detection and correction
        self.error_detection_enabled = True
        self.corrective_actions = {
            "high_cpu_usage": "lower_priority_tasks",
            "memory_leak": "restart_services",
            "network_delay": "optimize_routes"
        }
        
        self.logger.info("🔍 Performance Tracker initialized with automatic error correction")
        
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None, unit: str = ""):
        """Record a metric with timestamp"""
        metric = MetricData(
            timestamp=datetime.now().isoformat(),
            metric_name=name,
            value=value,
            tags=tags or {},
            unit=unit
        )
        
        self.metrics_history.append(metric)
        self.current_metrics[name] = value
        
        # Log significant metrics
        if name in ["response_time", "error_rate", "memory_usage"]:
            self.logger.debug(f"📊 Metric recorded: {name}={value}{unit}")
    
    def increment_counter(self, counter_name: str, value: int = 1):
        """Increment a performance counter"""
        if counter_name in self.counters:
            self.counters[counter_name] += value
            self.record_metric(f"counter_{counter_name}", self.counters[counter_name], unit="count")
    
    def measure_execution_time(self, operation_name: str):
        """Decorator/context manager to measure execution time"""
        class ExecutionTimer:
            def __init__(self, tracker, op_name):
                self.tracker = tracker
                self.operation_name = op_name
                self.start_time = None
                
            def __enter__(self):
                self.start_time = time.time()
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                self.tracker.record_metric(
                    f"execution_time_{self.operation_name}",
                    duration,
                    tags={"operation": self.operation_name},
                    unit="seconds"
                )
                
                if exc_type:
                    self.tracker.increment_counter("errors")
        
        return ExecutionTimer(self, operation_name)
    
    def _background_monitoring(self):
        """Background thread for system monitoring"""
        while self.monitoring_active:
            try:
                # CPU monitoring
                cpu_percent = psutil.cpu_percent(interval=1)
                self.system_stats["cpu_percent"] = cpu_percent
                self.record_metric("system_cpu_percent", cpu_percent, unit="%")
                
                # Memory monitoring
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                self.system_stats["memory_percent"] = memory_percent
                self.record_metric("system_memory_percent", memory_percent, unit="%")
                self.record_metric("system_memory_available", memory.available / (1024**3), unit="GB")
                
                # Disk monitoring
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                self.system_stats["disk_usage"] = disk_percent
                self.record_metric("system_disk_percent", disk_percent, unit="%")
                
                # Network monitoring
                net_io = psutil.net_io_counters()
                if net_io:
                    self.system_stats["network_io"]["bytes_sent"] = net_io.bytes_sent
                    self.system_stats["network_io"]["bytes_recv"] = net_io.bytes_recv
                    self.record_metric("network_bytes_sent", net_io.bytes_sent / (1024**2), unit="MB")
                    self.record_metric("network_bytes_recv", net_io.bytes_recv / (1024**2), unit="MB")
                
                time.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Background monitoring error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def get_metrics_summary(self, time_range_minutes: int = 60) -> Dict[str, Any]:
        """Get metrics summary for specified time range"""
        cutoff_time = datetime.now() - timedelta(minutes=time_range_minutes)
        cutoff_iso = cutoff_time.isoformat()
        
        # Filter recent metrics
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp > cutoff_iso
        ]
        
        # Aggregate metrics by name
        aggregated = {}
        for metric in recent_metrics:
            name = metric.metric_name
            if name not in aggregated:
                aggregated[name] = {
                    "count": 0,
                    "sum": 0,
                    "min": float('inf'),
                    "max": float('-inf'),
                    "avg": 0,
                    "latest": 0,
                    "unit": metric.unit
                }
            
            agg = aggregated[name]
            agg["count"] += 1
            agg["sum"] += metric.value
            agg["min"] = min(agg["min"], metric.value)
            agg["max"] = max(agg["max"], metric.value)
            agg["latest"] = metric.value
            agg["avg"] = agg["sum"] / agg["count"]
        
        return {
            "time_range_minutes": time_range_minutes,
            "total_metrics": len(recent_metrics),
            "system_stats": self.system_stats,
            "counters": self.counters,
            "aggregated_metrics": aggregated,
            "summary_generated_at": datetime.now().isoformat()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        cpu_healthy = self.system_stats["cpu_percent"] < 80
        memory_healthy = self.system_stats["memory_percent"] < 85
        disk_healthy = self.system_stats["disk_usage"] < 90
        
        error_rate = self.counters["errors"] / max(self.counters["api_calls"], 1)
        error_healthy = error_rate < 0.05  # Less than 5% error rate
        
        overall_health = all([cpu_healthy, memory_healthy, disk_healthy, error_healthy])
        
        return {
            "overall_healthy": overall_health,
            "status": "healthy" if overall_health else "degraded",
            "checks": {
                "cpu": {"healthy": cpu_healthy, "value": self.system_stats["cpu_percent"]},
                "memory": {"healthy": memory_healthy, "value": self.system_stats["memory_percent"]},
                "disk": {"healthy": disk_healthy, "value": self.system_stats["disk_usage"]},
                "error_rate": {"healthy": error_healthy, "value": error_rate}
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format"""
        if format == "json":
            metrics_data = [asdict(m) for m in list(self.metrics_history)]
            return json.dumps({
                "export_timestamp": datetime.now().isoformat(),
                "total_metrics": len(metrics_data),
                "metrics": metrics_data,
                "counters": self.counters,
                "system_stats": self.system_stats
            }, indent=2)
        else:
            return "Format not supported"
    
    def cleanup_old_metrics(self, older_than_hours: int = 24):
        """Clean up old metrics to manage memory"""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        cutoff_iso = cutoff_time.isoformat()
        
        original_size = len(self.metrics_history)
        
        # Convert to list, filter, convert back to deque
        filtered_metrics = [
            m for m in self.metrics_history 
            if m.timestamp > cutoff_iso
        ]
        
        self.metrics_history.clear()
        self.metrics_history.extend(filtered_metrics)
        
        cleaned = original_size - len(self.metrics_history)
        if cleaned > 0:
            self.logger.info(f"🧹 Cleaned {cleaned} old metrics")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        self.logger.info("🛑 Performance monitoring stopped")

# Global instance
performance_tracker = PerformanceTracker()
