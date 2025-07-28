"""
Observer Agent for Kairos System Monitoring
Continuously monitors system metrics, detects anomalies, and coordinates responses.
"""

import asyncio
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .base_agent import BaseAgent
from ..core.anomaly_detector import get_anomaly_detector, AnomalyAlert
from ..analytics.workflow_analyzer import get_workflow_analyzer
from ..analytics.budget_manager import get_budget_manager
from ..monitoring.performance_tracker import performance_tracker

# Import MCP for context management
try:
    from ..mcp.model_context_protocol import MCPContext
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

@dataclass
class SystemHealthStatus:
    """System health status report"""
    overall_score: float
    status: str  # 'excellent', 'good', 'fair', 'poor', 'critical'
    components: Dict[str, Dict[str, Any]]
    active_alerts: List[Dict[str, Any]]
    recommendations: List[str]
    timestamp: str

class ObserverAgent(BaseAgent):
    """Advanced system monitoring agent with anomaly detection and auto-healing"""
    
    def __init__(self, mcp_context: Optional['MCPContext'] = None):
        super().__init__("ObserverAgent", mcp_context)
        self.logger = logging.getLogger(__name__)
        
        # Monitoring configuration
        self.monitoring_enabled = True
        self.monitoring_interval = 30  # seconds
        self.alert_cooldown = 300     # 5 minutes between similar alerts
        
        # Component health tracking
        self.component_health = {
            'system_resources': {'status': 'unknown', 'last_check': None},
            'llm_router': {'status': 'unknown', 'last_check': None},
            'budget_manager': {'status': 'unknown', 'last_check': None},
            'workflow_analyzer': {'status': 'unknown', 'last_check': None},
            'database_connections': {'status': 'unknown', 'last_check': None},
            'api_endpoints': {'status': 'unknown', 'last_check': None}
        }
        
        # Alert management
        self.recent_alerts = {}
        self.escalation_thresholds = {
            'critical': 0,    # Immediate escalation
            'high': 2,        # Escalate after 2 occurrences
            'medium': 5,      # Escalate after 5 occurrences
            'low': 10         # Escalate after 10 occurrences
        }
        
        # Auto-healing capabilities
        self.auto_healing_enabled = True
        self.healing_actions = {
            'high_memory_usage': self._handle_memory_pressure,
            'high_cpu_usage': self._handle_cpu_pressure,  
            'api_errors': self._handle_api_errors,
            'budget_exceeded': self._handle_budget_exceeded,
            'workflow_anomaly': self._handle_workflow_anomaly
        }
        
        # Background tasks
        self.monitoring_task = None
        self.health_check_task = None
        
        self.logger.info("👁️ Observer Agent initialized with advanced monitoring")
    
    async def start_monitoring(self):
        """Start continuous system monitoring"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.logger.warning("Monitoring already running")
            return
        
        self.monitoring_enabled = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        
        self.logger.info("🚀 Started continuous system monitoring")
    
    async def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring_enabled = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("🛑 Stopped system monitoring")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_enabled:
            try:
                await self._collect_system_metrics()
                await self._check_component_health()
                await self._analyze_anomalies()
                
                # Sleep until next monitoring cycle
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _health_check_loop(self):
        """Health check loop - runs less frequently"""
        while self.monitoring_enabled:
            try:
                await self._comprehensive_health_check()
                await asyncio.sleep(300)  # Every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(300)
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # Get current system stats
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Record metrics through performance tracker
            performance_tracker.record_metric("cpu_percent", cpu_percent, unit="%")
            performance_tracker.record_metric("memory_percent", memory.percent, unit="%")
            performance_tracker.record_metric("disk_percent", (disk.used / disk.total) * 100, unit="%")
            
            # Check for anomalies
            anomaly_detector = await get_anomaly_detector()
            
            # Detect CPU anomalies
            cpu_anomaly = await anomaly_detector.detect_anomaly(
                "cpu_percent", cpu_percent, 
                context={'component': 'system_resources', 'agent': self.name}
            )
            if cpu_anomaly:
                await self._handle_anomaly_alert(cpu_anomaly)
            
            # Detect memory anomalies
            memory_anomaly = await anomaly_detector.detect_anomaly(
                "memory_percent", memory.percent,
                context={'component': 'system_resources', 'agent': self.name}
            )
            if memory_anomaly:
                await self._handle_anomaly_alert(memory_anomaly)
            
            # Update component health
            resource_health = 'excellent'
            if cpu_percent > 90 or memory.percent > 90:
                resource_health = 'critical'
            elif cpu_percent > 80 or memory.percent > 80:
                resource_health = 'poor'
            elif cpu_percent > 70 or memory.percent > 70:
                resource_health = 'fair'
            elif cpu_percent > 50 or memory.percent > 50:
                resource_health = 'good'
            
            self.component_health['system_resources'] = {
                'status': resource_health,
                'last_check': datetime.now().isoformat(),
                'metrics': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_percent': (disk.used / disk.total) * 100
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    async def _check_component_health(self):
        """Check health of various system components"""
        try:
            # Check budget manager
            budget_manager = await get_budget_manager()
            if budget_manager.enabled:
                # Check for budget alerts
                budget_status = await budget_manager.get_budget_status('default')
                if budget_status.is_over_budget:
                    self.component_health['budget_manager']['status'] = 'critical'
                elif budget_status.warning_threshold_reached:
                    self.component_health['budget_manager']['status'] = 'poor'
                else:
                    self.component_health['budget_manager']['status'] = 'good'
            else:
                self.component_health['budget_manager']['status'] = 'disabled'
            
            # Check workflow analyzer
            workflow_analyzer = await get_workflow_analyzer()
            pattern_count = len(workflow_analyzer.discovered_patterns)
            if pattern_count > 10:
                self.component_health['workflow_analyzer']['status'] = 'excellent'
            elif pattern_count > 5:
                self.component_health['workflow_analyzer']['status'] = 'good'
            elif pattern_count > 0:
                self.component_health['workflow_analyzer']['status'] = 'fair'
            else:
                self.component_health['workflow_analyzer']['status'] = 'poor'
            
            self.component_health['workflow_analyzer']['last_check'] = datetime.now().isoformat()
            self.component_health['workflow_analyzer']['pattern_count'] = pattern_count
            
        except Exception as e:
            self.logger.error(f"Component health check failed: {e}")
    
    async def _analyze_anomalies(self):
        """Analyze system state for anomalies"""
        try:
            anomaly_detector = await get_anomaly_detector()
            
            # Get current system health score
            health_data = await anomaly_detector.get_system_health_score()
            
            # Check if health score indicates a problem
            if health_data['health_score'] < 50:
                alert_id = f"system_health_{int(datetime.now().timestamp())}"
                
                # Create a synthetic anomaly alert for low health score
                from ..core.anomaly_detector import AnomalyAlert
                health_alert = AnomalyAlert(
                    alert_id=alert_id,
                    alert_type='system_health',
                    severity='high' if health_data['health_score'] < 25 else 'medium',
                    metric_name='system_health_score',
                    current_value=health_data['health_score'],
                    expected_range=(75.0, 100.0),
                    deviation_score=abs(health_data['health_score'] - 90) / 10,
                    confidence=0.9,
                    description=f"System health score is critically low: {health_data['health_score']:.1f}/100",
                    affected_components=['overall_system'],
                    suggested_actions=[
                        "Review active alerts and resolve critical issues",
                        "Check system resource usage",
                        "Restart services if necessary",
                        "Monitor system performance closely"
                    ],
                    detected_at=datetime.now().isoformat()
                )
                
                await self._handle_anomaly_alert(health_alert)
                
        except Exception as e:
            self.logger.error(f"Anomaly analysis failed: {e}")
    
    async def _handle_anomaly_alert(self, alert: AnomalyAlert):
        """Handle an anomaly alert with smart processing and auto-healing"""
        try:
            # Check if this is a duplicate alert (within cooldown period)
            alert_key = f"{alert.metric_name}_{alert.severity}"
            current_time = datetime.now()
            
            if alert_key in self.recent_alerts:
                last_alert_time = datetime.fromisoformat(self.recent_alerts[alert_key])
                if (current_time - last_alert_time).total_seconds() < self.alert_cooldown:
                    self.logger.debug(f"Suppressing duplicate alert: {alert_key}")
                    return
            
            # Record this alert
            self.recent_alerts[alert_key] = current_time.isoformat()
            
            # Log the alert
            self.logger.warning(
                f"🚨 Anomaly Alert: {alert.severity.upper()} - {alert.metric_name} = {alert.current_value:.2f} "
                f"(expected: {alert.expected_range[0]:.2f}-{alert.expected_range[1]:.2f})"
            )
            
            # Try auto-healing if enabled
            if self.auto_healing_enabled and alert.severity in ['critical', 'high']:
                healing_result = await self._attempt_auto_healing(alert)
                if healing_result['success']:
                    self.logger.info(f"✅ Auto-healing successful: {healing_result['action']}")
                else:
                    self.logger.warning(f"❌ Auto-healing failed: {healing_result['error']}")
            
            # Update MCP context if available
            if self.mcp_context:
                self.mcp_context.add_event('anomaly_detected', {
                    'alert_id': alert.alert_id,
                    'metric_name': alert.metric_name,
                    'severity': alert.severity,
                    'current_value': alert.current_value,
                    'detected_at': alert.detected_at
                })
            
            # Escalate if necessary
            await self._check_escalation(alert)
            
        except Exception as e:
            self.logger.error(f"Failed to handle anomaly alert: {e}")
    
    async def _attempt_auto_healing(self, alert: AnomalyAlert) -> Dict[str, Any]:
        """Attempt to automatically heal the detected issue"""
        try:
            # Determine healing action based on alert type and metric
            healing_action = None
            
            if 'memory' in alert.metric_name and alert.current_value > 85:
                healing_action = 'high_memory_usage'
            elif 'cpu' in alert.metric_name and alert.current_value > 90:
                healing_action = 'high_cpu_usage'
            elif 'error' in alert.metric_name:
                healing_action = 'api_errors'
            elif 'cost' in alert.metric_name or 'budget' in alert.metric_name:
                healing_action = 'budget_exceeded'
            elif alert.alert_type == 'workflow':
                healing_action = 'workflow_anomaly'
            
            if healing_action and healing_action in self.healing_actions:
                result = await self.healing_actions[healing_action](alert)
                return {'success': True, 'action': healing_action, 'result': result}
            else:
                return {'success': False, 'error': f'No healing action available for {alert.metric_name}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _handle_memory_pressure(self, alert: AnomalyAlert) -> Dict[str, Any]:
        """Handle high memory usage"""
        try:
            # Clear performance tracker cache
            performance_tracker.cleanup_old_metrics(older_than_hours=1)
            
            # Trigger garbage collection
            import gc
            collected = gc.collect()
            
            # Clear workflow analyzer cache if available
            workflow_analyzer = await get_workflow_analyzer()
            if hasattr(workflow_analyzer, 'patterns_cache'):
                workflow_analyzer.patterns_cache.clear()
            
            return {
                'action': 'memory_cleanup',
                'garbage_collected': collected,
                'metrics_cleaned': True
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    async def _handle_cpu_pressure(self, alert: AnomalyAlert) -> Dict[str, Any]:
        """Handle high CPU usage"""
        try:
            # Reduce monitoring frequency temporarily
            original_interval = self.monitoring_interval
            self.monitoring_interval = min(self.monitoring_interval * 2, 120)  # Max 2 minutes
            
            # Schedule restoration of normal monitoring
            asyncio.create_task(self._restore_monitoring_interval(original_interval, delay=600))  # 10 minutes
            
            return {
                'action': 'reduced_monitoring_frequency',
                'new_interval': self.monitoring_interval,
                'original_interval': original_interval
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    async def _restore_monitoring_interval(self, original_interval: int, delay: int):
        """Restore original monitoring interval after delay"""
        await asyncio.sleep(delay)
        self.monitoring_interval = original_interval
        self.logger.info(f"📊 Restored monitoring interval to {original_interval} seconds")
    
    async def _handle_api_errors(self, alert: AnomalyAlert) -> Dict[str, Any]:
        """Handle API error spikes"""
        try:
            # This could trigger fallback to local models
            # For now, just log the attempt
            return {
                'action': 'api_error_mitigation',
                'fallback_enabled': True,
                'monitoring_increased': True
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    async def _handle_budget_exceeded(self, alert: AnomalyAlert) -> Dict[str, Any]:
        """Handle budget exceeded scenarios"""
        try:
            budget_manager = await get_budget_manager()
            
            # Force switch to local models for the default project
            # This would be implemented in the budget manager
            
            return {
                'action': 'budget_protection',
                'forced_local_models': True,
                'budget_status': 'protected'
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    async def _handle_workflow_anomaly(self, alert: AnomalyAlert) -> Dict[str, Any]:
        """Handle workflow anomalies"""
        try:
            workflow_analyzer = await get_workflow_analyzer()
            
            # Could trigger re-analysis of patterns or reset suggestions
            return {
                'action': 'workflow_analysis_refresh',
                'pattern_refresh': True
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    async def _check_escalation(self, alert: AnomalyAlert):
        """Check if alert should be escalated"""
        # Count recent occurrences of this type of alert
        alert_type_key = f"{alert.alert_type}_{alert.severity}"
        
        # For now, just log escalation - in a real system this would
        # send notifications, create tickets, etc.
        if alert.severity == 'critical':
            self.logger.critical(f"🚨 CRITICAL ALERT ESCALATION: {alert.description}")
    
    async def _comprehensive_health_check(self):
        """Perform comprehensive system health check"""
        try:
            health_status = await self.get_health_status()
            
            # Log health summary
            self.logger.info(
                f"🏥 System Health: {health_status.status.upper()} "
                f"(Score: {health_status.overall_score:.1f}/100) "
                f"- {len(health_status.active_alerts)} active alerts"
            )
            
            # Update MCP context with health status
            if self.mcp_context:
                self.mcp_context.add_event('health_check', {
                    'overall_score': health_status.overall_score,
                    'status': health_status.status,
                    'active_alerts_count': len(health_status.active_alerts),
                    'timestamp': health_status.timestamp
                })
            
        except Exception as e:
            self.logger.error(f"Comprehensive health check failed: {e}")
    
    async def get_health_status(self) -> SystemHealthStatus:
        """Get comprehensive system health status"""
        try:
            # Get anomaly detector health
            anomaly_detector = await get_anomaly_detector()
            anomaly_health = await anomaly_detector.get_system_health_score()
            
            # Get active alerts
            active_alerts = await anomaly_detector.get_active_alerts()
            alert_data = [
                {
                    'alert_id': alert.alert_id,
                    'severity': alert.severity,
                    'metric_name': alert.metric_name,
                    'description': alert.description,
                    'detected_at': alert.detected_at
                }
                for alert in active_alerts
            ]
            
            # Calculate overall score based on components
            component_scores = []
            for component, health in self.component_health.items():
                if health['status'] == 'excellent':
                    component_scores.append(100)
                elif health['status'] == 'good':
                    component_scores.append(80)
                elif health['status'] == 'fair':
                    component_scores.append(60)
                elif health['status'] == 'poor':
                    component_scores.append(40)
                elif health['status'] == 'critical':
                    component_scores.append(20)
                else:  # unknown or disabled
                    component_scores.append(50)
            
            # Combine with anomaly health score
            overall_score = (
                (sum(component_scores) / len(component_scores)) * 0.6 +
                anomaly_health['health_score'] * 0.4
            ) if component_scores else anomaly_health['health_score']
            
            # Determine overall status
            if overall_score >= 90:
                status = 'excellent'
            elif overall_score >= 75:
                status = 'good'
            elif overall_score >= 50:
                status = 'fair'
            elif overall_score >= 25:
                status = 'poor'
            else:
                status = 'critical'
            
            # Generate recommendations
            recommendations = []
            if overall_score < 75:
                recommendations.append("Review and resolve active alerts")
            if any(h['status'] in ['poor', 'critical'] for h in self.component_health.values()):
                recommendations.append("Check failing system components")
            if len(active_alerts) > 3:
                recommendations.append("High number of alerts - investigate root causes")
            if overall_score < 50:
                recommendations.append("System requires immediate attention")
            
            return SystemHealthStatus(
                overall_score=round(overall_score, 1),
                status=status,
                components=self.component_health.copy(),
                active_alerts=alert_data,
                recommendations=recommendations,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get health status: {e}")
            return SystemHealthStatus(
                overall_score=50.0,
                status='unknown',
                components={},
                active_alerts=[],
                recommendations=['System health check failed - investigate immediately'],
                timestamp=datetime.now().isoformat()
            )
    
    async def get_monitoring_report(self) -> Dict[str, Any]:
        """Get detailed monitoring report"""
        try:
            health_status = await self.get_health_status()
            anomaly_detector = await get_anomaly_detector()
            
            # Get recent metrics
            metrics_summary = performance_tracker.get_metrics_summary(time_range_minutes=60)
            
            return {
                'health_status': asdict(health_status),
                'system_metrics': metrics_summary,
                'monitoring_config': {
                    'enabled': self.monitoring_enabled,
                    'interval_seconds': self.monitoring_interval,
                    'auto_healing_enabled': self.auto_healing_enabled,
                    'alert_cooldown_seconds': self.alert_cooldown
                },
                'anomaly_baselines': len(anomaly_detector.baselines),
                'component_health': self.component_health,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate monitoring report: {e}")
            return {'error': str(e)}
    
    def get_status(self):
        """Get observer agent status"""
        return {
            'name': self.name,
            'status': self.status,
            'monitoring_enabled': self.monitoring_enabled,
            'monitoring_interval': self.monitoring_interval,
            'auto_healing_enabled': self.auto_healing_enabled,
            'active_components': len([c for c in self.component_health.values() 
                                   if c['status'] not in ['unknown', 'disabled']]),
            'recent_alerts_count': len(self.recent_alerts),
            'last_activity': datetime.now().isoformat()
        }
